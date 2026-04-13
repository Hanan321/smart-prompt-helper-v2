import os
from datetime import datetime, timezone

import stripe
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request
from supabase import create_client

load_dotenv()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")

supabase = create_client(
    os.getenv("SUPABASE_URL", ""),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""),
)

PRO_MONTHLY_PROMPT_LIMIT = int(os.getenv("PRO_MONTHLY_PROMPT_LIMIT", "200"))

app = FastAPI(title="Stripe Webhook")


def ts_to_date_str(ts: int | None) -> str | None:
    if not ts:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()


def plan_from_subscription_status(status: str | None) -> str:
    active_statuses = {"active", "trialing"}
    return "pro" if (status or "").lower() in active_statuses else "free"


def update_user_by_subscription_id(subscription_id: str, update_data: dict) -> None:
    supabase.table("user_profiles").update(update_data).eq(
        "stripe_subscription_id", subscription_id
    ).execute()


def update_user_by_id(user_id: str, update_data: dict) -> None:
    supabase.table("user_profiles").update(update_data).eq("id", user_id).execute()


@app.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(alias="Stripe-Signature"),
):
    payload = await request.body()

    try:
        event = stripe.Webhook.construct_event(payload, stripe_signature, webhook_secret)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid payload: {exc}") from exc
    except stripe.error.SignatureVerificationError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid signature: {exc}") from exc

    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        metadata = data.get("metadata", {}) or {}
        user_id = metadata.get("user_id")
        plan = metadata.get("plan", "free")
        subscription_id = data.get("subscription")
        customer_id = data.get("customer")

        if user_id and plan == "pro":
            subscription_status = "active"
            billing_period_start = None
            billing_period_end = None
            cancel_at_period_end = False

            if subscription_id:
                subscription = stripe.Subscription.retrieve(subscription_id)
                subscription_status = subscription.get("status") or "active"
                cancel_at_period_end = bool(subscription.get("cancel_at_period_end", False))
                billing_period_start = ts_to_date_str(subscription.get("current_period_start"))
                billing_period_end = ts_to_date_str(subscription.get("current_period_end"))

            update_user_by_id(
                user_id,
                {
                    "plan": "pro",
                    "stripe_customer_id": customer_id,
                    "stripe_subscription_id": subscription_id,
                    "subscription_status": subscription_status,
                    "cancel_at_period_end": cancel_at_period_end,
                    "monthly_prompts_used": 0,
                    "monthly_prompt_limit": PRO_MONTHLY_PROMPT_LIMIT,
                    "billing_period_start": billing_period_start,
                    "billing_period_end": billing_period_end,
                },
            )

    elif event_type == "invoice.payment_succeeded":
        subscription_id = data.get("subscription")

        if subscription_id:
            subscription = stripe.Subscription.retrieve(subscription_id)
            status = subscription.get("status")
            plan = plan_from_subscription_status(status)
            cancel_at_period_end = bool(subscription.get("cancel_at_period_end", False))

            update_user_by_subscription_id(
                subscription_id,
                {
                    "plan": plan,
                    "subscription_status": status,
                    "cancel_at_period_end": cancel_at_period_end,
                    "monthly_prompts_used": 0,
                    "monthly_prompt_limit": PRO_MONTHLY_PROMPT_LIMIT if plan == "pro" else 0,
                    "billing_period_start": ts_to_date_str(subscription.get("current_period_start")),
                    "billing_period_end": ts_to_date_str(subscription.get("current_period_end")),
                },
            )

    elif event_type == "invoice.payment_failed":
        subscription_id = data.get("subscription")

        if subscription_id:
            subscription = stripe.Subscription.retrieve(subscription_id)
            status = subscription.get("status")
            plan = plan_from_subscription_status(status)
            cancel_at_period_end = bool(subscription.get("cancel_at_period_end", False))

            update_user_by_subscription_id(
                subscription_id,
                {
                    "plan": plan,
                    "subscription_status": status,
                    "cancel_at_period_end": cancel_at_period_end,
                    "monthly_prompt_limit": PRO_MONTHLY_PROMPT_LIMIT if plan == "pro" else 0,
                    "billing_period_start": ts_to_date_str(subscription.get("current_period_start")),
                    "billing_period_end": ts_to_date_str(subscription.get("current_period_end")),
                },
            )

    elif event_type == "customer.subscription.updated":
        subscription_id = data.get("id")

        if subscription_id:
            status = data.get("status")
            plan = plan_from_subscription_status(status)
            cancel_at_period_end = bool(data.get("cancel_at_period_end", False))

            update_user_by_subscription_id(
                subscription_id,
                {
                    "plan": plan,
                    "subscription_status": status,
                    "cancel_at_period_end": cancel_at_period_end,
                    "monthly_prompt_limit": PRO_MONTHLY_PROMPT_LIMIT if plan == "pro" else 0,
                    "billing_period_start": ts_to_date_str(data.get("current_period_start")),
                    "billing_period_end": ts_to_date_str(data.get("current_period_end")),
                },
            )

    elif event_type == "customer.subscription.deleted":
        subscription_id = data.get("id")

        if subscription_id:
            update_user_by_subscription_id(
                subscription_id,
                {
                    "plan": "free",
                    "subscription_status": "canceled",
                    "cancel_at_period_end": False,
                    "stripe_subscription_id": None,
                    "monthly_prompts_used": 0,
                    "monthly_prompt_limit": 0,
                    "billing_period_start": None,
                    "billing_period_end": None,
                },
            )

    return {"ok": True}