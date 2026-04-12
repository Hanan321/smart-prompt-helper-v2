import stripe
from supabase import Client


PLAN_PRICE_KEY = {
    "pro": "stripe_price_pro",
    "premium": "stripe_price_premium",
}


class BillingService:
    def __init__(self, stripe_secret_key: str):
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
        return stripe.checkout.Session.create(
            mode="subscription",
            customer_email=customer_email,
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
            allow_promotion_codes=True,
            metadata={"user_id": user_id, "plan": plan},
        )

    def create_billing_portal_session(self, customer_id: str, return_url: str) -> stripe.billing_portal.Session:
        return stripe.billing_portal.Session.create(customer=customer_id, return_url=return_url)



def update_plan(admin_client: Client, user_id: str, plan: str) -> None:
    admin_client.table("user_profiles").update({"plan": plan}).eq("id", user_id).execute()
