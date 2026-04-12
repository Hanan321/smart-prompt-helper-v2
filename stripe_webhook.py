import os
from datetime import date, timedelta

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

PRO_MONTHLY_PROMPT_LIMIT = 200

app = FastAPI(title="Stripe Webhook")


@app.post("/webhooks/stripe")
async def stripe_webhook(request: Request, stripe_signature: str = Header(alias="Stripe-Signature")):
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
        metadata = data.get("metadata", {})
        user_id = metadata.get("user_id")
        plan = metadata.get("plan", "free")

        if user_id and plan == "pro":
            today = date.today()
            next_end = today + timedelta(days=30)

            (
                supabase.table("user_profiles")
                .update(
                    {
                        "plan": "pro",
                        "stripe_customer_id": data.get("customer"),
                        "stripe_subscription_id": data.get("subscription"),
                        "monthly_prompts_used": 0,
                        "monthly_prompt_limit": PRO_MONTHLY_PROMPT_LIMIT,
                        "billing_period_start": str(today),
                        "billing_period_end": str(next_end),
                    }
                )
                .eq("id", user_id)
                .execute()
            )

    if event_type == "customer.subscription.deleted":
        subscription_id = data.get("id")
        if subscription_id:
            (
                supabase.table("user_profiles")
                .update(
                    {
                        "plan": "free",
                        "stripe_subscription_id": None,
                        "monthly_prompts_used": 0,
                        "monthly_prompt_limit": 0,
                        "billing_period_start": None,
                        "billing_period_end": None,
                    }
                )
                .eq("stripe_subscription_id", subscription_id)
                .execute()
            )

    return {"ok": True}