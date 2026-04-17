import logging
from datetime import datetime, timezone

import stripe
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request
from supabase import create_client
from services.config import (
    VALID_APP_ENVS,
    get_billing_config,
    get_config_value,
)

load_dotenv()

logger = logging.getLogger(__name__)


def explicit_app_env() -> str:
    return (get_config_value("APP_ENV", "") or "").strip().lower()


def active_secret_name(base_name: str, app_env: str) -> str:
    return f"{base_name}_{app_env.upper()}"


def validate_webhook_config(config) -> list[str]:
    app_env = explicit_app_env()
    if not app_env:
        return ["APP_ENV must be set explicitly to either 'test' or 'live'."]

    if app_env not in VALID_APP_ENVS:
        return ["APP_ENV must be either 'test' or 'live'."]

    if config.app_env != app_env:
        return ["Active billing environment does not match APP_ENV."]

    if config.using_legacy_live_names:
        return [
            "Webhook configuration must use environment-specific Stripe secrets; "
            "set STRIPE_SECRET_KEY_LIVE and STRIPE_WEBHOOK_SECRET_LIVE."
        ]

    missing = []
    if not config.stripe_secret_key:
        missing.append(active_secret_name("STRIPE_SECRET_KEY", config.app_env))
    if not config.stripe_webhook_secret:
        missing.append(active_secret_name("STRIPE_WEBHOOK_SECRET", config.app_env))

    errors = [
        f"Missing required webhook configuration for {config.app_env}: {key}"
        for key in missing
    ]

    expected_secret_prefix = f"sk_{config.app_env}_"
    if config.stripe_secret_key and not config.stripe_secret_key.startswith(
        expected_secret_prefix
    ):
        errors.append(
            "Invalid active Stripe secret key for "
            f"APP_ENV='{config.app_env}': expected prefix '{expected_secret_prefix}'."
        )

    if config.stripe_webhook_secret and not config.stripe_webhook_secret.startswith(
        "whsec_"
    ):
        errors.append("Invalid active Stripe webhook secret: expected prefix 'whsec_'.")

    return errors


def validate_supabase_webhook_config() -> list[str]:
    required = {
        "SUPABASE_URL": get_config_value("SUPABASE_URL", ""),
        "SUPABASE_SERVICE_ROLE_KEY": get_config_value("SUPABASE_SERVICE_ROLE_KEY", ""),
    }
    return [
        f"Missing required webhook configuration: {key}"
        for key, value in required.items()
        if not value
    ]


billing_config = get_billing_config()
billing_config_errors = validate_webhook_config(billing_config)
supabase_config_errors = validate_supabase_webhook_config()
config_errors = billing_config_errors + supabase_config_errors
if config_errors:
    raise RuntimeError("Invalid webhook configuration: " + "; ".join(config_errors))

logger.info("Stripe webhook billing environment: %s", billing_config.app_env)

stripe.api_key = billing_config.stripe_secret_key
webhook_secret = billing_config.stripe_webhook_secret
expected_livemode = billing_config.app_env == "live"

supabase_url = get_config_value("SUPABASE_URL", "")
supabase_service_role_key = get_config_value("SUPABASE_SERVICE_ROLE_KEY", "")
supabase = create_client(
    supabase_url,
    supabase_service_role_key,
)

BILLING_SELECT = (
    "user_id,environment,plan,subscription_status,stripe_customer_id,"
    "stripe_subscription_id,cancel_at_period_end,current_period_end"
)

app = FastAPI(title="Stripe Webhook")


def ts_to_date_str(ts: int | None) -> str | None:
    if not ts:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()


def plan_from_subscription_status(status: str | None) -> str:
    active_statuses = {"active", "trialing"}
    return "pro" if (status or "").lower() in active_statuses else "free"


def stripe_value(obj, key: str, default=None):
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def get_billing_by_subscription_id(subscription_id: str | None) -> dict | None:
    if not subscription_id:
        return None

    try:
        response = (
            supabase.table("user_billing")
            .select(BILLING_SELECT)
            .eq("stripe_subscription_id", subscription_id)
            .eq("environment", billing_config.app_env)
            .maybe_single()
            .execute()
        )
    except Exception as exc:
        logger.exception("Could not fetch billing row by subscription ID.")
        raise HTTPException(status_code=500, detail="Database lookup failed.") from exc

    return getattr(response, "data", None)


def get_billing_by_user_id(user_id: str | None, create_if_missing: bool = True) -> dict | None:
    if not user_id:
        return None

    try:
        response = (
            supabase.table("user_billing")
            .select(BILLING_SELECT)
            .eq("user_id", user_id)
            .eq("environment", billing_config.app_env)
            .maybe_single()
            .execute()
        )
    except Exception as exc:
        logger.exception("Could not fetch billing row by user ID.")
        raise HTTPException(status_code=500, detail="Database lookup failed.") from exc

    billing = getattr(response, "data", None)
    if billing or not create_if_missing:
        return billing

    initial_row = {
        "user_id": user_id,
        "environment": billing_config.app_env,
        "plan": "free",
        "subscription_status": None,
        "cancel_at_period_end": False,
        "current_period_end": None,
    }
    try:
        supabase.table("user_billing").insert(initial_row).execute()
    except Exception as exc:
        try:
            response = (
                supabase.table("user_billing")
                .select(BILLING_SELECT)
                .eq("user_id", user_id)
                .eq("environment", billing_config.app_env)
                .maybe_single()
                .execute()
            )
        except Exception as lookup_exc:
            logger.exception("Could not initialize billing row by user ID.")
            raise HTTPException(
                status_code=500,
                detail="Database insert failed.",
            ) from lookup_exc

        billing = getattr(response, "data", None)
        if billing:
            return billing

        logger.exception("Could not initialize billing row by user ID.")
        raise HTTPException(status_code=500, detail="Database insert failed.") from exc

    logger.info(
        "Initialized billing row from webhook: user_id=%s environment=%s",
        user_id,
        billing_config.app_env,
    )
    return {**initial_row, "stripe_customer_id": None, "stripe_subscription_id": None}


def should_reset_usage(
    billing: dict | None,
    subscription_id: str | None,
    current_period_end: str | None,
) -> bool:
    if not billing:
        return False

    if billing.get("stripe_subscription_id") != subscription_id:
        return True

    return billing.get("current_period_end") != current_period_end


def reset_monthly_usage(user_id: str | None) -> None:
    if not user_id:
        return

    try:
        supabase.table("user_profiles").update({"monthly_prompts_used": 0}).eq(
            "id", user_id
        ).execute()
    except Exception as exc:
        logger.exception("Could not reset monthly usage by user ID.")
        raise HTTPException(status_code=500, detail="Database update failed.") from exc


def update_billing_by_subscription_id(subscription_id: str, update_data: dict) -> bool:
    try:
        response = (
            supabase.table("user_billing")
            .update(update_data)
            .eq("stripe_subscription_id", subscription_id)
            .eq("environment", billing_config.app_env)
            .execute()
        )
    except Exception as exc:
        logger.exception("Could not update billing row by subscription ID.")
        raise HTTPException(status_code=500, detail="Database update failed.") from exc

    updated_rows = getattr(response, "data", None) or []
    updated = bool(updated_rows)
    logger.info(
        "Billing update by subscription_id %s for environment=%s",
        "succeeded" if updated else "matched no rows",
        billing_config.app_env,
    )
    return updated


def update_billing_by_user_id(user_id: str, update_data: dict) -> bool:
    get_billing_by_user_id(user_id)
    try:
        response = (
            supabase.table("user_billing")
            .update(update_data)
            .eq("user_id", user_id)
            .eq("environment", billing_config.app_env)
            .execute()
        )
    except Exception as exc:
        logger.exception("Could not update billing row by user ID.")
        raise HTTPException(status_code=500, detail="Database update failed.") from exc

    updated_rows = getattr(response, "data", None) or []
    updated = bool(updated_rows)
    logger.info(
        "Billing update by user_id %s for environment=%s",
        "succeeded" if updated else "matched no rows",
        billing_config.app_env,
    )
    return updated


def get_user_id_by_email(email: str | None) -> str | None:
    if not email:
        return None

    try:
        response = (
            supabase.table("user_profiles")
            .select("id")
            .eq("email", email)
            .maybe_single()
            .execute()
        )
    except Exception as exc:
        logger.exception("Could not fetch profile by email.")
        raise HTTPException(status_code=500, detail="Database lookup failed.") from exc

    profile = getattr(response, "data", None) or {}
    return profile.get("id")


def subscription_fields(subscription) -> dict:
    status = stripe_value(subscription, "status")
    plan = plan_from_subscription_status(status)
    fields = {
        "plan": plan,
        "subscription_status": status,
        "cancel_at_period_end": bool(
            stripe_value(subscription, "cancel_at_period_end", False)
        ),
        "current_period_end": ts_to_date_str(
            stripe_value(subscription, "current_period_end")
        ),
    }
    return fields


def customer_id_from_subscription(subscription) -> str | None:
    customer = stripe_value(subscription, "customer")
    if isinstance(customer, dict):
        return customer.get("id")
    return customer


def metadata_user_id(obj) -> str | None:
    metadata = stripe_value(obj, "metadata", {}) or {}
    return metadata.get("user_id")


def retrieve_subscription(subscription_id: str):
    try:
        return stripe.Subscription.retrieve(subscription_id)
    except stripe.error.StripeError as exc:
        logger.exception("Could not retrieve Stripe subscription.")
        raise HTTPException(
            status_code=502,
            detail="Could not retrieve Stripe subscription.",
        ) from exc


@app.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
):
    payload = await request.body()

    if not stripe_signature:
        logger.warning("Stripe webhook rejected missing signature header.")
        raise HTTPException(status_code=400, detail="Missing Stripe signature.")

    try:
        event = stripe.Webhook.construct_event(
            payload,
            stripe_signature,
            webhook_secret,
        )
    except ValueError as exc:
        logger.warning("Stripe webhook rejected invalid payload.")
        raise HTTPException(status_code=400, detail=f"Invalid payload: {exc}") from exc
    except stripe.error.SignatureVerificationError as exc:
        logger.warning("Stripe webhook rejected invalid signature.")
        raise HTTPException(status_code=400, detail=f"Invalid signature: {exc}") from exc

    event_type = event.get("type")
    event_id = event.get("id", "unknown")
    event_livemode = bool(event.get("livemode", False))

    logger.info(
        "Stripe webhook signature verified for event type=%s id=%s env=%s",
        event_type,
        event_id,
        billing_config.app_env,
    )

    if event_livemode != expected_livemode:
        logger.error(
            "Stripe webhook livemode mismatch for event type=%s id=%s env=%s livemode=%s",
            event_type,
            event_id,
            billing_config.app_env,
            event_livemode,
        )
        raise HTTPException(status_code=400, detail="Stripe event environment mismatch.")

    data = event.get("data", {}).get("object", {})

    if event_type == "checkout.session.completed":
        metadata = data.get("metadata", {}) or {}
        customer_details = data.get("customer_details", {}) or {}
        customer_email = data.get("customer_email") or customer_details.get("email")
        user_id = (
            metadata.get("user_id")
            or data.get("client_reference_id")
            or get_user_id_by_email(customer_email)
        )
        plan = metadata.get("plan") or ("pro" if data.get("payment_link") else "free")
        subscription_id = data.get("subscription")
        customer_id = data.get("customer")

        if not user_id:
            logger.warning("Checkout session completed without a resolvable user_id.")
            return {"ok": True, "ignored": "missing_user_id"}

        if plan != "pro":
            logger.info("Checkout session completed for non-Pro plan; no profile update.")
            return {"ok": True, "ignored": "non_pro_plan"}

        if not subscription_id:
            logger.warning("Pro checkout session completed without a subscription ID.")
            return {"ok": True, "ignored": "missing_subscription_id"}

        subscription = retrieve_subscription(subscription_id)
        current_period_end = ts_to_date_str(
            stripe_value(subscription, "current_period_end")
        )
        billing = get_billing_by_user_id(user_id)
        reset_usage = should_reset_usage(
            billing,
            subscription_id,
            current_period_end,
        )
        update_data = subscription_fields(subscription)
        update_data.update(
            {
                "plan": "pro",
                "stripe_customer_id": customer_id
                or customer_id_from_subscription(subscription),
                "stripe_subscription_id": subscription_id,
            }
        )

        update_billing_by_user_id(
            user_id,
            update_data,
        )
        if reset_usage:
            reset_monthly_usage(user_id)

    elif event_type == "invoice.payment_succeeded":
        subscription_id = data.get("subscription")

        if not subscription_id:
            logger.warning("invoice.payment_succeeded missing subscription ID.")
            return {"ok": True, "ignored": "missing_subscription_id"}

        subscription = retrieve_subscription(subscription_id)
        current_period_end = ts_to_date_str(
            stripe_value(subscription, "current_period_end")
        )
        billing = get_billing_by_subscription_id(subscription_id)
        reset_usage = should_reset_usage(billing, subscription_id, current_period_end)
        updated = update_billing_by_subscription_id(
            subscription_id,
            subscription_fields(subscription),
        )
        reset_user_id = (billing or {}).get("user_id")
        if not updated:
            user_id = metadata_user_id(subscription)
            if user_id:
                billing = get_billing_by_user_id(user_id)
                reset_usage = should_reset_usage(
                    billing,
                    subscription_id,
                    current_period_end,
                )
                update_data = subscription_fields(subscription)
                update_data.update(
                    {
                        "stripe_customer_id": customer_id_from_subscription(subscription),
                        "stripe_subscription_id": subscription_id,
                    }
                )
                update_billing_by_user_id(user_id, update_data)
                reset_user_id = user_id
        if reset_usage:
            reset_monthly_usage(reset_user_id or metadata_user_id(subscription))

    elif event_type == "invoice.payment_failed":
        subscription_id = data.get("subscription")

        if not subscription_id:
            logger.warning("invoice.payment_failed missing subscription ID.")
            return {"ok": True, "ignored": "missing_subscription_id"}

        subscription = retrieve_subscription(subscription_id)
        updated = update_billing_by_subscription_id(
            subscription_id,
            subscription_fields(subscription),
        )
        if not updated:
            user_id = metadata_user_id(subscription)
            if user_id:
                update_data = subscription_fields(subscription)
                update_data.update(
                    {
                        "stripe_customer_id": customer_id_from_subscription(subscription),
                        "stripe_subscription_id": subscription_id,
                    }
                )
                update_billing_by_user_id(user_id, update_data)

    elif event_type in {
        "customer.subscription.created",
        "customer.subscription.updated",
    }:
        subscription_id = data.get("id")

        if not subscription_id:
            logger.warning("%s missing subscription ID.", event_type)
            return {"ok": True, "ignored": "missing_subscription_id"}

        billing = get_billing_by_subscription_id(subscription_id)
        current_period_end = ts_to_date_str(stripe_value(data, "current_period_end"))
        reset_usage = should_reset_usage(billing, subscription_id, current_period_end)
        updated = update_billing_by_subscription_id(
            subscription_id,
            subscription_fields(data),
        )
        if updated and reset_usage:
            reset_monthly_usage((billing or {}).get("user_id"))
        if not updated:
            user_id = metadata_user_id(data)
            if user_id:
                billing = get_billing_by_user_id(user_id)
                reset_usage = should_reset_usage(
                    billing,
                    subscription_id,
                    current_period_end,
                )
                update_data = subscription_fields(data)
                update_data.update(
                    {
                        "stripe_customer_id": customer_id_from_subscription(data),
                        "stripe_subscription_id": subscription_id,
                    }
                )
                update_billing_by_user_id(user_id, update_data)
                if reset_usage:
                    reset_monthly_usage(user_id)
            else:
                logger.info(
                    "%s had no matching billing row and no metadata user_id.",
                    event_type,
                )

    elif event_type == "customer.subscription.deleted":
        subscription_id = data.get("id")

        if not subscription_id:
            logger.warning("customer.subscription.deleted missing subscription ID.")
            return {"ok": True, "ignored": "missing_subscription_id"}

        billing = get_billing_by_subscription_id(subscription_id)
        updated = update_billing_by_subscription_id(
            subscription_id,
            {
                "plan": "free",
                "subscription_status": "canceled",
                "cancel_at_period_end": False,
                "stripe_subscription_id": None,
                "current_period_end": None,
            },
        )
        reset_user_id = (billing or {}).get("user_id") or metadata_user_id(data)
        if not updated and reset_user_id:
            update_billing_by_user_id(
                reset_user_id,
                {
                    "plan": "free",
                    "subscription_status": "canceled",
                    "cancel_at_period_end": False,
                    "stripe_subscription_id": None,
                    "current_period_end": None,
                },
            )
        reset_monthly_usage(reset_user_id)
    else:
        logger.info("Unhandled Stripe webhook event type=%s id=%s", event_type, event_id)

    return {"ok": True}
