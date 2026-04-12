from datetime import date
from supabase import Client


def ensure_user_profile(admin_client: Client, user_id: str, email: str) -> None:
    admin_client.table("user_profiles").upsert(
        {
            "id": user_id,
            "email": email,
        },
        on_conflict="id",
    ).execute()


def get_user_profile(admin_client: Client, user_id: str) -> dict:
    response = (
        admin_client.table("user_profiles")
        .select("id,email,plan,stripe_customer_id,stripe_subscription_id")
        .eq("id", user_id)
        .maybe_single()
        .execute()
    )
    return (getattr(response, "data", None) or {})


def get_daily_prompt_count(admin_client: Client, user_id: str) -> int:
    today = str(date.today())
    response = (
        admin_client.table("daily_usage")
        .select("prompt_count")
        .eq("user_id", user_id)
        .eq("usage_date", today)
        .maybe_single()
        .execute()
    )

    row = getattr(response, "data", None)
    if not row:
        return 0

    return int(row.get("prompt_count", 0))


def increment_daily_prompt_count(admin_client: Client, user_id: str) -> None:
    today = str(date.today())

    response = (
        admin_client.table("daily_usage")
        .select("id,prompt_count")
        .eq("user_id", user_id)
        .eq("usage_date", today)
        .maybe_single()
        .execute()
    )

    existing = getattr(response, "data", None)

    if existing:
        next_count = int(existing.get("prompt_count", 0)) + 1
        (
            admin_client.table("daily_usage")
            .update({"prompt_count": next_count})
            .eq("id", existing["id"])
            .execute()
        )
        return

    (
        admin_client.table("daily_usage")
        .insert({"user_id": user_id, "usage_date": today, "prompt_count": 1})
        .execute()
    )