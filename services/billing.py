import stripe
from supabase import Client

PRO_MONTHLY_PROMPT_LIMIT = 200


class BillingService:
    def __init__(self, stripe_secret_key: str):
        if not stripe_secret_key:
            raise ValueError("Missing Stripe secret key.")
        stripe.api_key = stripe_secret_key

    def create_checkout_session(
        self,
        customer_email: str,
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

        return stripe.checkout.Session.create(
            mode="subscription",
            customer_email=customer_email,
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
            allow_promotion_codes=True,
            metadata={
                "user_id": user_id,
                "plan": plan,
            },
        )

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