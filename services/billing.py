import logging
from typing import Optional
from datetime import datetime, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import stripe
from supabase import Client

PRO_MONTHLY_PROMPT_LIMIT = 200
PROMPT_PACK_CREDITS = 10
PROMPT_PACK_PURCHASE_TYPE = "prompt_pack_10"
ACTIVE_SUBSCRIPTION_STATUSES = {"active", "trialing"}
BILLING_SELECT = "*"
logger = logging.getLogger(__name__)


def _ts_to_date_str(ts: int | None) -> str | None:
    if not ts:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()


def _stripe_search_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _stripe_value(obj, key: str, default=None):
    if obj is None:
        return default

    if isinstance(obj, dict):
        return obj.get(key, default)

    return getattr(obj, key, default)


def _safe_id(value: str | None) -> str:
    if not value:
        return "missing"
    if len(value) <= 8:
        return value
    return f"...{value[-6:]}"


def _url_with_query(url: str, params: dict[str, str]) -> str:
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query.update(params)
    encoded_query = urlencode(query)
    encoded_query = encoded_query.replace(
        "%7BCHECKOUT_SESSION_ID%7D",
        "{CHECKOUT_SESSION_ID}",
    )
    return urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            parts.path,
            encoded_query,
            parts.fragment,
        )
    )


def _plan_from_subscription_status(status: str | None) -> str:
    return "pro" if (status or "").lower() in ACTIVE_SUBSCRIPTION_STATUSES else "free"


def _billing_environment(environment: str | None) -> str:
    normalized = (environment or "live").strip().lower()
    if normalized not in {"test", "live"}:
        raise ValueError("Billing environment must be either 'test' or 'live'.")
    return normalized


def _billing_fields_from_subscription(subscription) -> dict:
    status = _stripe_value(subscription, "status")
    plan = _plan_from_subscription_status(status)
    return {
        "plan": plan,
        "subscription_status": status,
        "stripe_subscription_id": _stripe_value(subscription, "id"),
        "cancel_at_period_end": bool(
            _stripe_value(subscription, "cancel_at_period_end", False)
        ),
        "current_period_end": _ts_to_date_str(
            _stripe_value(subscription, "current_period_end")
        ),
    }


def get_user_billing(
    admin_client: Client,
    user_id: str,
    environment: str,
    create_if_missing: bool = True,
) -> dict:
    billing_environment = _billing_environment(environment)
    response = (
        admin_client.table("user_billing")
        .select(BILLING_SELECT)
        .eq("user_id", user_id)
        .eq("environment", billing_environment)
        .maybe_single()
        .execute()
    )
    row = getattr(response, "data", None)
    if row or not create_if_missing:
        return row or {}

    logger.info(
        "Initializing user billing row: user_id=%s environment=%s",
        user_id,
        billing_environment,
    )
    initial_row = {
        "user_id": user_id,
        "environment": billing_environment,
        "plan": "free",
        "subscription_status": None,
        "cancel_at_period_end": False,
        "current_period_end": None,
    }
    try:
        admin_client.table("user_billing").insert(initial_row).execute()
    except Exception:
        response = (
            admin_client.table("user_billing")
            .select(BILLING_SELECT)
            .eq("user_id", user_id)
            .eq("environment", billing_environment)
            .maybe_single()
            .execute()
        )
        row = getattr(response, "data", None)
        if row:
            return row
        raise

    return {**initial_row, "stripe_customer_id": None, "stripe_subscription_id": None}


def update_user_billing(
    admin_client: Client,
    user_id: str,
    environment: str,
    update_data: dict,
) -> dict:
    billing_environment = _billing_environment(environment)
    get_user_billing(admin_client, user_id, billing_environment)
    response = (
        admin_client.table("user_billing")
        .update(update_data)
        .eq("user_id", user_id)
        .eq("environment", billing_environment)
        .execute()
    )
    rows = getattr(response, "data", None) or []
    logger.info(
        "Updated user billing row: user_id=%s environment=%s updated=%s",
        user_id,
        billing_environment,
        bool(rows),
    )
    return rows[0] if rows else {}


class BillingService:
    def __init__(self, stripe_secret_key: str, app_env: str = "live"):
        if not stripe_secret_key:
            raise ValueError("Missing Stripe secret key.")
        stripe.api_key = stripe_secret_key
        self.app_env = _billing_environment(app_env)

    def ensure_customer_for_user(
        self,
        admin_client: Client,
        user_id: str,
        email: str | None,
        existing_customer_id: Optional[str] = None,
    ) -> str:
        if existing_customer_id:
            logger.info(
                "Using existing Stripe customer for checkout: user_id=%s environment=%s customer_id=%s",
                user_id,
                self.app_env,
                _safe_id(existing_customer_id),
            )
            return existing_customer_id

        billing_row = get_user_billing(admin_client, user_id, self.app_env)
        saved_customer_id = billing_row.get("stripe_customer_id")
        if saved_customer_id:
            logger.info(
                "Found persisted Stripe customer before checkout: user_id=%s environment=%s customer_id=%s",
                user_id,
                self.app_env,
                _safe_id(saved_customer_id),
            )
            return saved_customer_id

        profile = (
            admin_client.table("user_profiles")
            .select("email")
            .eq("id", user_id)
            .maybe_single()
            .execute()
        )
        profile_data = getattr(profile, "data", None) or {}
        customer_email = email or profile_data.get("email")
        if not customer_email:
            raise ValueError("Missing user email for Stripe customer creation.")

        logger.info(
            "Creating Stripe customer before checkout: user_id=%s environment=%s",
            user_id,
            self.app_env,
        )
        customer = stripe.Customer.create(
            email=customer_email,
            metadata={
                "user_id": user_id,
                "app_user_id": user_id,
                "environment": self.app_env,
                "source": "smart_prompt_helper",
            },
        )
        customer_id = _stripe_value(customer, "id")
        if not customer_id:
            raise ValueError("Stripe customer creation did not return an ID.")

        update_user_billing(
            admin_client,
            user_id,
            self.app_env,
            {"stripe_customer_id": customer_id},
        )
        logger.info(
            "Saved Stripe customer before checkout: user_id=%s environment=%s customer_id=%s",
            user_id,
            self.app_env,
            _safe_id(customer_id),
        )
        return customer_id

    def create_checkout_session(
        self,
        customer_email: Optional[str],
        plan: str,
        success_url: str,
        cancel_url: str,
        price_id: str,
        user_id: str,
        admin_client: Client,
        stripe_customer_id: Optional[str] = None,
    ) -> stripe.checkout.Session:
        if plan != "pro":
            raise ValueError(f"Unsupported plan: {plan}")

        if not price_id:
            raise ValueError("Missing Stripe price ID for checkout.")

        customer_id = self.ensure_customer_for_user(
            admin_client=admin_client,
            user_id=user_id,
            email=customer_email,
            existing_customer_id=stripe_customer_id,
        )

        payload = {
            "mode": "subscription",
            "payment_method_types": ["card"],
            "line_items": [{"price": price_id, "quantity": 1}],
            "success_url": success_url,
            "cancel_url": cancel_url,
            "customer": customer_id,
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

        logger.info(
            "Creating Stripe Checkout session: user_id=%s customer_id=%s plan=%s success_url=%s cancel_url=%s",
            user_id,
            _safe_id(customer_id),
            plan,
            success_url,
            cancel_url,
        )
        return stripe.checkout.Session.create(**payload)

    def create_prompt_pack_checkout_session(
        self,
        customer_email: Optional[str],
        success_url: str,
        cancel_url: str,
        price_id: str,
        user_id: str,
        admin_client: Client,
        stripe_customer_id: Optional[str] = None,
    ) -> stripe.checkout.Session:
        if self.app_env != "test":
            raise ValueError("Prompt pack checkout is only enabled in test mode.")

        if not price_id:
            raise ValueError("Missing Stripe price ID for prompt pack checkout.")

        customer_id = self.ensure_customer_for_user(
            admin_client=admin_client,
            user_id=user_id,
            email=customer_email,
            existing_customer_id=stripe_customer_id,
        )

        success_url_with_session = _url_with_query(
            success_url,
            {
                "prompt_pack_checkout": "success",
                "checkout_session_id": "{CHECKOUT_SESSION_ID}",
                "session_id": "{CHECKOUT_SESSION_ID}",
            },
        )
        cancel_url_with_context = _url_with_query(
            cancel_url,
            {"prompt_pack_checkout": "cancelled"},
        )

        payload = {
            "mode": "payment",
            "payment_method_types": ["card"],
            "line_items": [{"price": price_id, "quantity": 1}],
            "success_url": success_url_with_session,
            "cancel_url": cancel_url_with_context,
            "customer": customer_id,
            "client_reference_id": user_id,
            "metadata": {
                "user_id": user_id,
                "purchase_type": PROMPT_PACK_PURCHASE_TYPE,
                "credits": str(PROMPT_PACK_CREDITS),
                "environment": self.app_env,
            },
        }

        logger.info(
            "Creating Stripe prompt pack checkout: user_id=%s customer_id=%s credits=%s env=%s success_url=%s",
            user_id,
            _safe_id(customer_id),
            PROMPT_PACK_CREDITS,
            self.app_env,
            success_url_with_session,
        )
        checkout_session = stripe.checkout.Session.create(**payload)
        logger.info(
            "Created Stripe prompt pack checkout: user_id=%s env=%s session_id=%s",
            user_id,
            self.app_env,
            _safe_id(_stripe_value(checkout_session, "id")),
        )
        return checkout_session

    def _is_paid_prompt_pack_session(self, checkout_session, user_id: str) -> bool:
        metadata = _stripe_value(checkout_session, "metadata", {}) or {}
        return (
            _stripe_value(checkout_session, "mode") == "payment"
            and _stripe_value(checkout_session, "payment_status") == "paid"
            and metadata.get("purchase_type") == PROMPT_PACK_PURCHASE_TYPE
            and metadata.get("user_id") == user_id
            and metadata.get("environment") == self.app_env
        )

    def _session_uses_price(self, checkout_session_id: str, price_id: str | None) -> bool:
        if not price_id:
            return False

        line_items = stripe.checkout.Session.list_line_items(
            checkout_session_id,
            limit=10,
        )
        for line_item in getattr(line_items, "data", []) or []:
            price = _stripe_value(line_item, "price", {}) or {}
            if _stripe_value(price, "id") == price_id:
                return True

        return False

    def _is_returned_prompt_pack_session(
        self,
        checkout_session,
        user_id: str,
        stripe_customer_id: str | None,
        price_id: str | None,
    ) -> bool:
        session_id = _stripe_value(checkout_session, "id")
        metadata = _stripe_value(checkout_session, "metadata", {}) or {}
        session_customer_id = _stripe_value(checkout_session, "customer")
        session_user_id = metadata.get("user_id") or _stripe_value(
            checkout_session,
            "client_reference_id",
        )
        session_mode = _stripe_value(checkout_session, "mode")
        payment_status = _stripe_value(checkout_session, "payment_status")
        price_match = bool(session_id and self._session_uses_price(session_id, price_id))
        customer_match = (
            bool(stripe_customer_id)
            and bool(session_customer_id)
            and session_customer_id == stripe_customer_id
        )
        user_match = session_user_id == user_id
        owner_match = user_match or customer_match

        valid = (
            session_mode == "payment"
            and payment_status == "paid"
            and owner_match
            and price_match
        )
        logger.info(
            "Returned prompt pack session validation: user_id=%s env=%s session_id=%s mode=%s paid=%s user_match=%s customer_match=%s price_match=%s owner_match=%s valid=%s",
            user_id,
            self.app_env,
            _safe_id(session_id),
            session_mode,
            payment_status == "paid",
            user_match,
            customer_match,
            price_match,
            owner_match,
            valid,
        )
        return valid

    def grant_prompt_pack_credits(
        self,
        admin_client: Client,
        user_id: str,
        checkout_session_id: str,
        stripe_customer_id: str | None,
    ) -> bool:
        response = admin_client.rpc(
            "grant_prompt_pack_credits",
            {
                "p_user_id": user_id,
                "p_environment": self.app_env,
                "p_checkout_session_id": checkout_session_id,
                "p_credits": PROMPT_PACK_CREDITS,
                "p_stripe_customer_id": stripe_customer_id,
            },
        ).execute()
        granted = bool(getattr(response, "data", False))
        logger.info(
            "Prompt pack credit sync RPC returned %s: user_id=%s env=%s session_id=%s status=%s",
            granted,
            user_id,
            self.app_env,
            _safe_id(checkout_session_id),
            "granted" if granted else "already processed",
        )
        return granted

    def sync_prompt_pack_checkout_session(
        self,
        admin_client: Client,
        user_id: str,
        checkout_session_id: str | None,
        stripe_customer_id: str | None = None,
        price_id: str | None = None,
    ) -> bool:
        if self.app_env != "test" or not checkout_session_id:
            return False

        logger.info(
            "Syncing returned prompt pack checkout session: user_id=%s env=%s session_id=%s",
            user_id,
            self.app_env,
            _safe_id(checkout_session_id),
        )
        checkout_session = stripe.checkout.Session.retrieve(checkout_session_id)
        is_prompt_pack_session = self._is_paid_prompt_pack_session(
            checkout_session,
            user_id,
        )
        if not is_prompt_pack_session:
            is_prompt_pack_session = self._is_returned_prompt_pack_session(
                checkout_session,
                user_id,
                stripe_customer_id,
                price_id,
            )

        if not is_prompt_pack_session:
            logger.info(
                "Checkout session was not a paid prompt pack for this user: user_id=%s env=%s session_id=%s",
                user_id,
                self.app_env,
                _safe_id(checkout_session_id),
            )
            return False

        customer_id = _stripe_value(checkout_session, "customer")
        return self.grant_prompt_pack_credits(
            admin_client,
            user_id,
            checkout_session_id,
            customer_id,
        )

    def sync_completed_prompt_pack_purchases(
        self,
        admin_client: Client,
        user_id: str,
        stripe_customer_id: str | None,
        price_id: str | None = None,
    ) -> int:
        if self.app_env != "test" or not stripe_customer_id:
            return 0

        sessions = stripe.checkout.Session.list(
            customer=stripe_customer_id,
            limit=100,
        )
        grants = 0
        paid_pack_sessions = 0
        for checkout_session in getattr(sessions, "data", []) or []:
            is_prompt_pack_session = self._is_paid_prompt_pack_session(
                checkout_session,
                user_id,
            )
            if not is_prompt_pack_session:
                is_prompt_pack_session = self._is_returned_prompt_pack_session(
                    checkout_session,
                    user_id,
                    stripe_customer_id,
                    price_id,
                )
            if not is_prompt_pack_session:
                continue
            paid_pack_sessions += 1
            session_id = _stripe_value(checkout_session, "id")
            if not session_id:
                continue
            if self.grant_prompt_pack_credits(
                admin_client,
                user_id,
                session_id,
                stripe_customer_id,
            ):
                grants += 1

        logger.info(
            "Synced completed prompt pack purchases: user_id=%s env=%s paid_sessions=%s new_grants=%s",
            user_id,
            self.app_env,
            paid_pack_sessions,
            grants,
        )
        return grants

    def create_billing_portal_session(
        self,
        customer_id: str,
        return_url: str,
    ) -> stripe.billing_portal.Session:
        if not customer_id:
            raise ValueError("Missing Stripe customer ID.")
        logger.info(
            "Creating Stripe billing portal session: customer_id=%s return_url=%s",
            _safe_id(customer_id),
            return_url,
        )
        return stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )

    def cancel_subscription_at_period_end(
        self,
        admin_client: Client,
        user_id: str,
        subscription_id: str,
    ) -> dict:
        if not subscription_id:
            raise ValueError("Missing Stripe subscription ID.")

        billing_row = get_user_billing(admin_client, user_id, self.app_env)
        if billing_row.get("stripe_subscription_id") != subscription_id:
            raise ValueError("Subscription ID does not match the active billing environment.")

        subscription = stripe.Subscription.retrieve(subscription_id)
        if not bool(_stripe_value(subscription, "cancel_at_period_end", False)):
            subscription = stripe.Subscription.modify(
                subscription_id,
                cancel_at_period_end=True,
            )

        update_data = _billing_fields_from_subscription(subscription)
        update_user_billing(admin_client, user_id, self.app_env, update_data)
        return update_data

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

        customers_by_id = {}

        listed_customers = stripe.Customer.list(email=email, limit=10)
        for customer in getattr(listed_customers, "data", []) or []:
            customer_id = _stripe_value(customer, "id")
            if customer_id:
                customers_by_id[customer_id] = customer

        try:
            searched_customers = stripe.Customer.search(
                query=f"email:'{_stripe_search_value(email)}'",
                limit=10,
            )
            for customer in getattr(searched_customers, "data", []) or []:
                customer_id = _stripe_value(customer, "id")
                if customer_id:
                    customers_by_id[customer_id] = customer
        except stripe.error.StripeError:
            pass

        for customer in customers_by_id.values():
            customer_id = _stripe_value(customer, "id")
            if not customer_id:
                continue

            subscriptions = stripe.Subscription.list(
                customer=customer_id,
                status="all",
                limit=100,
            )

            for subscription in getattr(subscriptions, "data", []) or []:
                status = (_stripe_value(subscription, "status", "") or "").lower()
                if status not in ACTIVE_SUBSCRIPTION_STATUSES:
                    continue

                if not active_subscription or (
                    _stripe_value(subscription, "current_period_end", 0) or 0
                ) > (_stripe_value(active_subscription, "current_period_end", 0) or 0):
                    active_subscription = subscription
                    active_customer_id = customer_id

        if not active_subscription:
            return False

        update_data = _billing_fields_from_subscription(active_subscription)
        update_data["stripe_customer_id"] = active_customer_id
        update_user_billing(admin_client, user_id, self.app_env, update_data)

        return True


def update_plan(
    admin_client: Client,
    user_id: str,
    plan: str,
    environment: str = "live",
) -> None:
    normalized_plan = (plan or "").strip().lower()

    if normalized_plan not in {"free", "pro"}:
        raise ValueError(f"Unsupported plan: {plan}")

    if normalized_plan == "free":
        update_data = {
            "plan": "free",
            "stripe_subscription_id": None,
            "subscription_status": None,
            "cancel_at_period_end": False,
            "current_period_end": None,
        }
    else:
        update_data = {
            "plan": "pro",
        }

    update_user_billing(admin_client, user_id, environment, update_data)
