from datetime import date, datetime, timedelta

from supabase import Client

FREE_TOTAL_PROMPT_LIMIT = 5
PRO_MONTHLY_PROMPT_LIMIT = 200


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
            "plan": "free",
            "total_prompts_used": 0,
            "monthly_prompts_used": 0,
            "monthly_prompt_limit": 0,
            "billing_period_start": None,
            "billing_period_end": None,
        }
    ).execute()
#---------------------------------------------------------

def get_user_profile(admin_client: Client, user_id: str) -> dict:
    response = (
        admin_client.table("user_profiles")
        
        .select(
            "id,email,username,plan,stripe_customer_id,stripe_subscription_id,"
            "total_prompts_used,monthly_prompts_used,monthly_prompt_limit,"
            "billing_period_start,billing_period_end"
        )

        .eq("id", user_id)
        .maybe_single()
        .execute()
    )
    return getattr(response, "data", None) or {}


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


def reset_monthly_usage_if_needed(admin_client: Client, user_id: str) -> None:
    profile = get_user_profile(admin_client, user_id)
    if not profile:
        return

    plan = (profile.get("plan") or "free").lower()
    if plan != "pro":
        return

    if not billing_period_expired(profile):
        return

    today = date.today()
    next_end = today + timedelta(days=30)

    admin_client.table("user_profiles").update(
        {
            "monthly_prompts_used": 0,
            "monthly_prompt_limit": PRO_MONTHLY_PROMPT_LIMIT,
            "billing_period_start": str(today),
            "billing_period_end": str(next_end),
        }
    ).eq("id", user_id).execute()


def can_generate_prompt(admin_client: Client, user_id: str) -> tuple[bool, str]:
    profile = get_user_profile(admin_client, user_id)
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
    profile = get_user_profile(admin_client, user_id)
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