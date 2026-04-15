from typing import Optional
from datetime import datetime, timezone

import stripe
from supabase import Client

PRO_MONTHLY_PROMPT_LIMIT = 200
ACTIVE_SUBSCRIPTION_STATUSES = {"active", "trialing"}


def _ts_to_date_str(ts: int | None) -> str | None:
    if not ts:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()


class BillingService:
    def __init__(self, stripe_secret_key: str):
        if not stripe_secret_key:
            raise ValueError("Missing Stripe secret key.")
        stripe.api_key = stripe_secret_key

    def create_checkout_session(
        self,
        customer_email: Optional[str],
        plan: str,
        success_url: str,
        cancel_url: str,
        price_id: str,
        user_id: str,
    ) -> stripe.checkout.Session:
        if plan != "pro":
            raise ValueError(f"Unsupported plan: {plan}")

        if not price_id:
            raise ValueError("Missing Stripe price ID for checkout.")

        payload = {
            "mode": "subscription",
            "payment_method_types": ["card"],
            "line_items": [{"price": price_id, "quantity": 1}],
            "success_url": success_url,
            "cancel_url": cancel_url,
            "client_reference_id": user_id,
            "allow_promotion_codes": True,
            "saved_payment_method_options": {
                "payment_method_save": "disabled",
                "payment_method_remove": "disabled",
            },
            "metadata": {
                "user_id": user_id,
                "plan": plan,
            },
            "subscription_data": {
                "metadata": {
                    "user_id": user_id,
                    "plan": plan,
                },
            },
        }

        if customer_email:
            payload["customer_email"] = customer_email

        return stripe.checkout.Session.create(**payload)

    def create_billing_portal_session(
        self,
        customer_id: str,
        return_url: str,
    ) -> stripe.billing_portal.Session:
        if not customer_id:
            raise ValueError("Missing Stripe customer ID.")
        return stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )

    def sync_active_subscription_by_email(
        self,
        admin_client: Client,
        user_id: str,
        email: str | None,
    ) -> bool:
        if not email:
            return False

        active_subscription = None
        active_customer_id = None

        customers = stripe.Customer.list(email=email, limit=10)
        for customer in getattr(customers, "data", []) or []:
            subscriptions = stripe.Subscription.list(
                customer=customer["id"],
                status="all",
                limit=100,
            )

            for subscription in getattr(subscriptions, "data", []) or []:
                status = (subscription.get("status") or "").lower()
                if status not in ACTIVE_SUBSCRIPTION_STATUSES:
                    continue

                if not active_subscription or (
                    subscription.get("current_period_end") or 0
                ) > (active_subscription.get("current_period_end") or 0):
                    active_subscription = subscription
                    active_customer_id = customer["id"]

        if not active_subscription:
            return False

        admin_client.table("user_profiles").update(
            {
                "plan": "pro",
                "stripe_customer_id": active_customer_id,
                "stripe_subscription_id": active_subscription.get("id"),
                "subscription_status": active_subscription.get("status"),
                "cancel_at_period_end": bool(
                    active_subscription.get("cancel_at_period_end", False)
                ),
                "monthly_prompt_limit": PRO_MONTHLY_PROMPT_LIMIT,
                "billing_period_start": _ts_to_date_str(
                    active_subscription.get("current_period_start")
                ),
                "billing_period_end": _ts_to_date_str(
                    active_subscription.get("current_period_end")
                ),
            }
        ).eq("id", user_id).execute()

        return True


def update_plan(admin_client: Client, user_id: str, plan: str) -> None:
    normalized_plan = (plan or "").strip().lower()

    if normalized_plan not in {"free", "pro"}:
        raise ValueError(f"Unsupported plan: {plan}")

    if normalized_plan == "free":
        update_data = {
            "plan": "free",
            "stripe_subscription_id": None,
            "monthly_prompts_used": 0,
            "monthly_prompt_limit": 0,
            "billing_period_start": None,
            "billing_period_end": None,
        }
    else:
        update_data = {
            "plan": "pro",
            "monthly_prompt_limit": PRO_MONTHLY_PROMPT_LIMIT,
        }

    admin_client.table("user_profiles").update(update_data).eq("id", user_id).execute()
