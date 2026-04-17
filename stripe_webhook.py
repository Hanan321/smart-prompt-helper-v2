import logging
from datetime import datetime, timezone

import stripe
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request
from supabase import create_client
from services.config import (
    VALID_APP_ENVS,
    get_billing_config,
    get_config_int,
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

PRO_MONTHLY_PROMPT_LIMIT = get_config_int("PRO_MONTHLY_PROMPT_LIMIT", 200)

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


def get_profile_by_subscription_id(subscription_id: str | None) -> dict | None:
    if not subscription_id:
        return None

    try:
        response = (
            supabase.table("user_profiles")
            .select("id,billing_period_start,billing_period_end,stripe_subscription_id")
            .eq("stripe_subscription_id", subscription_id)
            .maybe_single()
            .execute()
        )
    except Exception as exc:
        logger.exception("Could not fetch profile by subscription ID.")
        raise HTTPException(status_code=500, detail="Database lookup failed.") from exc

    return getattr(response, "data", None)


def get_profile_by_user_id(user_id: str | None) -> dict | None:
    if not user_id:
        return None

    try:
        response = (
            supabase.table("user_profiles")
            .select("id,billing_period_start,billing_period_end,stripe_subscription_id")
            .eq("id", user_id)
            .maybe_single()
            .execute()
        )
    except Exception as exc:
        logger.exception("Could not fetch profile by user ID.")
        raise HTTPException(status_code=500, detail="Database lookup failed.") from exc

    return getattr(response, "data", None)


def should_reset_usage(
    profile: dict | None,
    subscription_id: str | None,
    billing_period_start: str | None,
    billing_period_end: str | None,
) -> bool:
    if not profile:
        return False

    if profile.get("stripe_subscription_id") != subscription_id:
        return True

    return (
        profile.get("billing_period_start") != billing_period_start
        or profile.get("billing_period_end") != billing_period_end
    )


def update_user_by_subscription_id(subscription_id: str, update_data: dict) -> bool:
    try:
        response = (
            supabase.table("user_profiles")
            .update(update_data)
            .eq("stripe_subscription_id", subscription_id)
            .execute()
        )
    except Exception as exc:
        logger.exception("Could not update profile by subscription ID.")
        raise HTTPException(status_code=500, detail="Database update failed.") from exc

    updated_rows = getattr(response, "data", None) or []
    updated = bool(updated_rows)
    logger.info(
        "Profile update by subscription_id %s",
        "succeeded" if updated else "matched no rows",
    )
    return updated


def update_user_by_id(user_id: str, update_data: dict) -> bool:
    try:
        response = (
            supabase.table("user_profiles")
            .update(update_data)
            .eq("id", user_id)
            .execute()
        )
    except Exception as exc:
        logger.exception("Could not update profile by user ID.")
        raise HTTPException(status_code=500, detail="Database update failed.") from exc

    updated_rows = getattr(response, "data", None) or []
    updated = bool(updated_rows)
    logger.info(
        "Profile update by user_id %s",
        "succeeded" if updated else "matched no rows",
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


def subscription_fields(subscription, include_usage_reset: bool = False) -> dict:
    status = stripe_value(subscription, "status")
    plan = plan_from_subscription_status(status)
    fields = {
        "plan": plan,
        "subscription_status": status,
        "cancel_at_period_end": bool(
            stripe_value(subscription, "cancel_at_period_end", False)
        ),
        "monthly_prompt_limit": PRO_MONTHLY_PROMPT_LIMIT if plan == "pro" else 0,
        "billing_period_start": ts_to_date_str(
            stripe_value(subscription, "current_period_start")
        ),
        "billing_period_end": ts_to_date_str(
            stripe_value(subscription, "current_period_end")
        ),
    }
    if include_usage_reset:
        fields["monthly_prompts_used"] = 0
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
        billing_period_start = ts_to_date_str(
            stripe_value(subscription, "current_period_start")
        )
        billing_period_end = ts_to_date_str(
            stripe_value(subscription, "current_period_end")
        )
        profile = get_profile_by_user_id(user_id)
        reset_usage = should_reset_usage(
            profile,
            subscription_id,
            billing_period_start,
            billing_period_end,
        )
        update_data = subscription_fields(
            subscription,
            include_usage_reset=reset_usage,
        )
        update_data.update(
            {
                "plan": "pro",
                "stripe_customer_id": customer_id,
                "stripe_subscription_id": subscription_id,
                "monthly_prompt_limit": PRO_MONTHLY_PROMPT_LIMIT,
            }
        )

        update_user_by_id(
            user_id,
            update_data,
        )

    elif event_type == "invoice.payment_succeeded":
        subscription_id = data.get("subscription")

        if not subscription_id:
            logger.warning("invoice.payment_succeeded missing subscription ID.")
            return {"ok": True, "ignored": "missing_subscription_id"}

        subscription = retrieve_subscription(subscription_id)
        billing_period_start = ts_to_date_str(
            stripe_value(subscription, "current_period_start")
        )
        billing_period_end = ts_to_date_str(
            stripe_value(subscription, "current_period_end")
        )
        profile = get_profile_by_subscription_id(subscription_id)
        update_user_by_subscription_id(
            subscription_id,
            subscription_fields(
                subscription,
                include_usage_reset=should_reset_usage(
                    profile,
                    subscription_id,
                    billing_period_start,
                    billing_period_end,
                ),
            )
        )

    elif event_type == "invoice.payment_failed":
        subscription_id = data.get("subscription")

        if not subscription_id:
            logger.warning("invoice.payment_failed missing subscription ID.")
            return {"ok": True, "ignored": "missing_subscription_id"}

        subscription = retrieve_subscription(subscription_id)
        update_user_by_subscription_id(
            subscription_id,
            subscription_fields(subscription),
        )

    elif event_type in {
        "customer.subscription.created",
        "customer.subscription.updated",
    }:
        subscription_id = data.get("id")

        if not subscription_id:
            logger.warning("%s missing subscription ID.", event_type)
            return {"ok": True, "ignored": "missing_subscription_id"}

        updated = update_user_by_subscription_id(
            subscription_id,
            subscription_fields(data),
        )
        if not updated:
            user_id = metadata_user_id(data)
            if user_id:
                billing_period_start = ts_to_date_str(
                    stripe_value(data, "current_period_start")
                )
                billing_period_end = ts_to_date_str(
                    stripe_value(data, "current_period_end")
                )
                profile = get_profile_by_user_id(user_id)
                update_data = subscription_fields(
                    data,
                    include_usage_reset=should_reset_usage(
                        profile,
                        subscription_id,
                        billing_period_start,
                        billing_period_end,
                    ),
                )
                update_data.update(
                    {
                        "stripe_customer_id": customer_id_from_subscription(data),
                        "stripe_subscription_id": subscription_id,
                    }
                )
                update_user_by_id(user_id, update_data)
            else:
                logger.info(
                    "%s had no matching profile and no metadata user_id.",
                    event_type,
                )

    elif event_type == "customer.subscription.deleted":
        subscription_id = data.get("id")

        if not subscription_id:
            logger.warning("customer.subscription.deleted missing subscription ID.")
            return {"ok": True, "ignored": "missing_subscription_id"}

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
    else:
        logger.info("Unhandled Stripe webhook event type=%s id=%s", event_type, event_id)

    return {"ok": True}
