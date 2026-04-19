from datetime import date, datetime
import logging

from supabase import Client

from services.billing import (
    ACTIVE_SUBSCRIPTION_STATUSES,
    PRO_MONTHLY_PROMPT_LIMIT,
    get_user_billing,
    update_user_billing,
)
from services.config import get_config_value

FREE_TOTAL_PROMPT_LIMIT = 5
TEST_FREE_TOTAL_PROMPT_LIMIT = 2

logger = logging.getLogger(__name__)


def _active_billing_environment(environment: str | None = None) -> str:
    normalized = (
        environment or get_config_value("APP_ENV", "live") or "live"
    ).strip().lower()
    return normalized if normalized in {"test", "live"} else "live"


def _is_test_environment(environment: str | None = None) -> bool:
    return _active_billing_environment(environment) == "test"


def _free_prompt_limit(environment: str | None = None) -> int:
    if _is_test_environment(environment):
        configured_limit = get_config_value("TEST_FREE_TOTAL_PROMPT_LIMIT", "")
        if configured_limit:
            return int(configured_limit)
        return TEST_FREE_TOTAL_PROMPT_LIMIT
    configured_limit = get_config_value("FREE_TOTAL_PROMPT_LIMIT", "")
    if configured_limit:
        return int(configured_limit)
    return FREE_TOTAL_PROMPT_LIMIT


def _has_active_monthly_subscription(profile: dict) -> bool:
    return (
        (profile.get("plan") or "free").lower() == "pro"
        and (profile.get("subscription_status") or "").lower()
        in ACTIVE_SUBSCRIPTION_STATUSES
    )


def _billing_has_monthly_usage(profile: dict) -> bool:
    return bool(profile.get("_billing_has_monthly_prompts_used", False))


def ensure_user_profile(
    admin_client: Client,
    user_id: str,
    email: str,
    username: str | None = None,
) -> None:
    existing = (
        admin_client.table("user_profiles")
        .select("id")
        .eq("id", user_id)
        .maybe_single()
        .execute()
    )

    if getattr(existing, "data", None):
        return

    admin_client.table("user_profiles").insert(
        {
            "id": user_id,
            "email": email,
            "username": username,
            "total_prompts_used": 0,
            "monthly_prompts_used": 0,
        }
    ).execute()


def get_user_profile(
    admin_client: Client,
    user_id: str,
    environment: str | None = None,
) -> dict:
    response = (
        admin_client.table("user_profiles")
        .select("id,email,username,total_prompts_used,monthly_prompts_used")
        .eq("id", user_id)
        .maybe_single()
        .execute()
    )
    profile = getattr(response, "data", None) or {}
    if not profile:
        return {}

    active_environment = _active_billing_environment(environment)
    billing = get_user_billing(
        admin_client,
        user_id,
        active_environment,
    )
    plan = (billing.get("plan") or "free").lower()
    billing_monthly_used = int(billing.get("monthly_prompts_used", 0) or 0)
    profile_monthly_used = int(profile.get("monthly_prompts_used", 0) or 0)
    profile.update(
        {
            "plan": plan,
            "stripe_customer_id": billing.get("stripe_customer_id"),
            "stripe_subscription_id": billing.get("stripe_subscription_id"),
            "subscription_status": billing.get("subscription_status"),
            "cancel_at_period_end": bool(billing.get("cancel_at_period_end", False)),
            "billing_period_start": None,
            "billing_period_end": billing.get("current_period_end"),
            "current_period_end": billing.get("current_period_end"),
            "credit_balance": int(billing.get("credit_balance", 0) or 0),
            "total_credits_purchased": int(
                billing.get("total_credits_purchased", 0) or 0
            ),
            "monthly_prompt_limit": PRO_MONTHLY_PROMPT_LIMIT if plan == "pro" else 0,
            "monthly_prompts_used": (
                billing_monthly_used
                if active_environment == "test"
                and "monthly_prompts_used" in billing
                else profile_monthly_used
            ),
            "free_prompt_limit": _free_prompt_limit(active_environment),
            "_billing_has_monthly_prompts_used": "monthly_prompts_used" in billing,
        }
    )
    return profile


def get_total_prompt_count(admin_client: Client, user_id: str) -> int:
    profile = get_user_profile(admin_client, user_id)
    return int(profile.get("total_prompts_used", 0) or 0)


def get_monthly_prompt_count(admin_client: Client, user_id: str) -> int:
    profile = get_user_profile(admin_client, user_id)
    return int(profile.get("monthly_prompts_used", 0) or 0)


def get_monthly_prompt_limit(admin_client: Client, user_id: str) -> int:
    profile = get_user_profile(admin_client, user_id)
    return int(profile.get("monthly_prompt_limit", 0) or 0)


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return datetime.fromisoformat(str(value)).date()


def billing_period_expired(profile: dict) -> bool:
    end_date = _parse_date(profile.get("billing_period_end"))
    if not end_date:
        return False
    return date.today() > end_date


def scheduled_subscription_period_ended(profile: dict) -> bool:
    plan = (profile.get("plan") or "free").lower()
    if plan != "pro" or not bool(profile.get("cancel_at_period_end", False)):
        return False
    return billing_period_expired(profile)


def downgrade_if_scheduled_subscription_ended(
    admin_client: Client,
    user_id: str,
    profile: dict | None = None,
) -> dict:
    current_profile = profile or get_user_profile(admin_client, user_id)
    if not current_profile or not scheduled_subscription_period_ended(current_profile):
        return current_profile or {}

    update_user_billing(
        admin_client,
        user_id,
        _active_billing_environment(),
        {
            "plan": "free",
            "subscription_status": "canceled",
            "cancel_at_period_end": False,
            "stripe_subscription_id": None,
            "current_period_end": None,
        }
    )
    if _is_test_environment() and _billing_has_monthly_usage(current_profile):
        update_user_billing(
            admin_client,
            user_id,
            _active_billing_environment(),
            {"monthly_prompts_used": 0},
        )
    else:
        admin_client.table("user_profiles").update({"monthly_prompts_used": 0}).eq(
            "id", user_id
        ).execute()

    return get_user_profile(admin_client, user_id)


def reset_monthly_usage_if_needed(admin_client: Client, user_id: str) -> None:
    profile = downgrade_if_scheduled_subscription_ended(admin_client, user_id)
    if not profile:
        return

    plan = (profile.get("plan") or "free").lower()
    if plan != "pro":
        return

    if not billing_period_expired(profile):
        return

    if _is_test_environment() and _billing_has_monthly_usage(profile):
        update_user_billing(
            admin_client,
            user_id,
            _active_billing_environment(),
            {"monthly_prompts_used": 0},
        )
    else:
        admin_client.table("user_profiles").update(
            {
                "monthly_prompts_used": 0,
            }
        ).eq("id", user_id).execute()


def can_generate_prompt(admin_client: Client, user_id: str) -> tuple[bool, str]:
    profile = downgrade_if_scheduled_subscription_ended(admin_client, user_id)
    if not profile:
        return False, "User profile not found."

    if _is_test_environment():
        if _has_active_monthly_subscription(profile):
            reset_monthly_usage_if_needed(admin_client, user_id)
            refreshed_profile = get_user_profile(admin_client, user_id)
            monthly_used = int(refreshed_profile.get("monthly_prompts_used", 0) or 0)
            monthly_limit = int(refreshed_profile.get("monthly_prompt_limit", 0) or 0)

            if monthly_limit > 0 and monthly_used >= monthly_limit:
                return False, "You reached your monthly prompt limit for this plan."
            return True, ""

        if int(profile.get("credit_balance", 0) or 0) > 0:
            return True, ""

        total_used = int(profile.get("total_prompts_used", 0) or 0)
        if total_used >= _free_prompt_limit():
            return (
                False,
                "You have used your 2 free prompts. Buy a prompt pack or subscribe to continue.",
            )
        return True, ""

    plan = (profile.get("plan") or "free").lower()
    if plan == "free":
        total_used = int(profile.get("total_prompts_used", 0) or 0)
        if total_used >= _free_prompt_limit():
            return False, "Your free trial is complete. Upgrade to Pro to continue."
        return True, ""

    reset_monthly_usage_if_needed(admin_client, user_id)
    refreshed_profile = get_user_profile(admin_client, user_id)

    monthly_used = int(refreshed_profile.get("monthly_prompts_used", 0) or 0)
    monthly_limit = int(refreshed_profile.get("monthly_prompt_limit", 0) or 0)

    if monthly_limit > 0 and monthly_used >= monthly_limit:
        return False, "You reached your monthly prompt limit for this plan."

    return True, ""


def increment_prompt_count(admin_client: Client, user_id: str) -> None:
    profile = downgrade_if_scheduled_subscription_ended(admin_client, user_id)
    if not profile:
        return

    if _is_test_environment():
        if _has_active_monthly_subscription(profile):
            reset_monthly_usage_if_needed(admin_client, user_id)
            refreshed_profile = get_user_profile(admin_client, user_id)
            current_monthly = int(refreshed_profile.get("monthly_prompts_used", 0) or 0)
            if _billing_has_monthly_usage(refreshed_profile):
                update_user_billing(
                    admin_client,
                    user_id,
                    _active_billing_environment(),
                    {"monthly_prompts_used": current_monthly + 1},
                )
            else:
                admin_client.table("user_profiles").update(
                    {"monthly_prompts_used": current_monthly + 1}
                ).eq("id", user_id).execute()
            logger.info(
                "Recorded monthly prompt usage: user_id=%s env=%s used=%s",
                user_id,
                _active_billing_environment(),
                current_monthly + 1,
            )
            return

        credit_balance = int(profile.get("credit_balance", 0) or 0)
        if credit_balance > 0:
            update_user_billing(
                admin_client,
                user_id,
                _active_billing_environment(),
                {"credit_balance": credit_balance - 1},
            )
            logger.info(
                "Deducted prompt pack credit: user_id=%s env=%s remaining=%s",
                user_id,
                _active_billing_environment(),
                credit_balance - 1,
            )
            return

        current_total = int(profile.get("total_prompts_used", 0) or 0)
        admin_client.table("user_profiles").update(
            {"total_prompts_used": current_total + 1}
        ).eq("id", user_id).execute()
        logger.info(
            "Recorded free prompt usage: user_id=%s env=%s used=%s",
            user_id,
            _active_billing_environment(),
            current_total + 1,
        )
        return

    plan = (profile.get("plan") or "free").lower()
    if plan == "free":
        current_total = int(profile.get("total_prompts_used", 0) or 0)
        admin_client.table("user_profiles").update(
            {"total_prompts_used": current_total + 1}
        ).eq("id", user_id).execute()
        return

    reset_monthly_usage_if_needed(admin_client, user_id)
    refreshed_profile = get_user_profile(admin_client, user_id)
    current_monthly = int(refreshed_profile.get("monthly_prompts_used", 0) or 0)

    admin_client.table("user_profiles").update(
        {"monthly_prompts_used": current_monthly + 1}
    ).eq("id", user_id).execute()
