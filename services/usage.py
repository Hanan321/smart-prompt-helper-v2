from datetime import date, datetime

from supabase import Client

from services.billing import PRO_MONTHLY_PROMPT_LIMIT, get_user_billing, update_user_billing
from services.config import get_config_value

FREE_TOTAL_PROMPT_LIMIT = 5


def _active_billing_environment(environment: str | None = None) -> str:
    normalized = (
        environment or get_config_value("APP_ENV", "live") or "live"
    ).strip().lower()
    return normalized if normalized in {"test", "live"} else "live"


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

    billing = get_user_billing(
        admin_client,
        user_id,
        _active_billing_environment(environment),
    )
    plan = (billing.get("plan") or "free").lower()
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
            "monthly_prompt_limit": PRO_MONTHLY_PROMPT_LIMIT if plan == "pro" else 0,
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

    admin_client.table("user_profiles").update(
        {
            "monthly_prompts_used": 0,
        }
    ).eq("id", user_id).execute()


def can_generate_prompt(admin_client: Client, user_id: str) -> tuple[bool, str]:
    profile = downgrade_if_scheduled_subscription_ended(admin_client, user_id)
    if not profile:
        return False, "User profile not found."

    plan = (profile.get("plan") or "free").lower()

    if plan == "free":
        total_used = int(profile.get("total_prompts_used", 0) or 0)
        if total_used >= FREE_TOTAL_PROMPT_LIMIT:
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
