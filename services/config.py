import os
import logging
from dataclasses import dataclass

from dotenv import load_dotenv
import streamlit as st

load_dotenv()

logger = logging.getLogger(__name__)


VALID_APP_ENVS = {"test", "live"}


@dataclass(frozen=True)
class BillingConfig:
    app_env: str
    stripe_secret_key: str
    stripe_publishable_key: str
    stripe_price_pro: str
    stripe_webhook_secret: str
    required_secret_names: tuple[str, ...]
    using_legacy_live_names: bool = False


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str
    stripe_secret_key: str
    stripe_publishable_key: str
    stripe_price_pro: str
    stripe_webhook_secret: str
    billing_config: BillingConfig
    app_env: str

    app_base_url: str
    home_url: str

    cookies_password: str  # ✅ NEW

    free_total_prompt_limit: int = 5
    pro_monthly_prompt_limit: int = 200


# ----------------------------
# Safe env loaders
# ----------------------------
def get_config_value(key: str, default: str = "") -> str:
    try:
        return st.secrets[key]
    except Exception:
        return os.getenv(key, default)


def get_config_int(key: str, default: int) -> int:
    value = get_config_value(key)
    if not value:
        return default
    return int(value)


def _has_config_value(key: str) -> bool:
    return bool(get_config_value(key, ""))


def _absolute_url(value: str) -> str:
    clean = value.strip()
    if clean.startswith(("http://", "https://")):
        return clean
    return f"https://{clean}"


def get_billing_config() -> BillingConfig:
    app_env = (get_config_value("APP_ENV", "live") or "live").strip().lower()

    if app_env in VALID_APP_ENVS:
        suffix = app_env.upper()
    else:
        suffix = "LIVE"

    secret_names = {
        "stripe_secret_key": f"STRIPE_SECRET_KEY_{suffix}",
        "stripe_publishable_key": f"STRIPE_PUBLISHABLE_KEY_{suffix}",
        "stripe_price_pro": f"STRIPE_PRICE_PRO_{suffix}",
        "stripe_webhook_secret": f"STRIPE_WEBHOOK_SECRET_{suffix}",
    }

    app_env_is_explicit = _has_config_value("APP_ENV")
    using_legacy_live_names = app_env == "live" and not app_env_is_explicit

    values = {
        field_name: get_config_value(secret_name)
        for field_name, secret_name in secret_names.items()
    }

    if using_legacy_live_names:
        legacy_secret_names = {
            "stripe_secret_key": "STRIPE_SECRET_KEY",
            "stripe_publishable_key": "STRIPE_PUBLISHABLE_KEY",
            "stripe_price_pro": "STRIPE_PRICE_PRO",
            "stripe_webhook_secret": "STRIPE_WEBHOOK_SECRET",
        }
        for field_name, legacy_name in legacy_secret_names.items():
            if not values[field_name]:
                values[field_name] = get_config_value(legacy_name)

    logger.info("Active billing environment: %s", app_env)
    if using_legacy_live_names:
        logger.info(
            "APP_ENV is not set; using live billing environment with legacy Stripe secret names."
        )

    return BillingConfig(
        app_env=app_env,
        stripe_secret_key=values["stripe_secret_key"],
        stripe_publishable_key=values["stripe_publishable_key"],
        stripe_price_pro=values["stripe_price_pro"],
        stripe_webhook_secret=values["stripe_webhook_secret"],
        required_secret_names=tuple(secret_names.values()),
        using_legacy_live_names=using_legacy_live_names,
    )


def validate_billing_config(billing_config: BillingConfig) -> list[str]:
    if billing_config.app_env not in VALID_APP_ENVS:
        return ["APP_ENV must be either 'test' or 'live'."]

    required_values = {
        billing_config.required_secret_names[0]: billing_config.stripe_secret_key,
        billing_config.required_secret_names[1]: billing_config.stripe_publishable_key,
        billing_config.required_secret_names[2]: billing_config.stripe_price_pro,
        billing_config.required_secret_names[3]: billing_config.stripe_webhook_secret,
    }
    missing = [key for key, value in required_values.items() if not value]

    if billing_config.using_legacy_live_names:
        legacy_names = {
            "STRIPE_SECRET_KEY_LIVE": "STRIPE_SECRET_KEY",
            "STRIPE_PUBLISHABLE_KEY_LIVE": "STRIPE_PUBLISHABLE_KEY",
            "STRIPE_PRICE_PRO_LIVE": "STRIPE_PRICE_PRO",
            "STRIPE_WEBHOOK_SECRET_LIVE": "STRIPE_WEBHOOK_SECRET",
        }
        missing = [f"{key} or legacy {legacy_names[key]}" for key in missing]

    errors = [
        f"Missing required secret for {billing_config.app_env}: {key}"
        for key in missing
    ]

    expected_secret_prefix = f"sk_{billing_config.app_env}_"
    expected_publishable_prefix = f"pk_{billing_config.app_env}_"
    prefix_checks = [
        (
            billing_config.stripe_secret_key,
            expected_secret_prefix,
            "active Stripe secret key",
        ),
        (
            billing_config.stripe_publishable_key,
            expected_publishable_prefix,
            "active Stripe publishable key",
        ),
        (billing_config.stripe_price_pro, "price_", "active Stripe Pro price ID"),
        (
            billing_config.stripe_webhook_secret,
            "whsec_",
            "active Stripe webhook secret",
        ),
    ]

    for value, expected_prefix, label in prefix_checks:
        if value and not value.startswith(expected_prefix):
            errors.append(
                f"Invalid {label} for APP_ENV='{billing_config.app_env}': expected prefix '{expected_prefix}'."
            )

    return errors


# ----------------------------
# Main settings loader
# ----------------------------
def get_settings() -> Settings:
    billing_config = get_billing_config()

    return Settings(
        openai_api_key=get_config_value("OPENAI_API_KEY"),
        supabase_url=get_config_value("SUPABASE_URL"),
        supabase_anon_key=get_config_value("SUPABASE_ANON_KEY"),
        supabase_service_role_key=get_config_value("SUPABASE_SERVICE_ROLE_KEY"),
        stripe_secret_key=billing_config.stripe_secret_key,
        stripe_publishable_key=billing_config.stripe_publishable_key,
        stripe_price_pro=billing_config.stripe_price_pro,
        stripe_webhook_secret=billing_config.stripe_webhook_secret,
        billing_config=billing_config,
        app_env=billing_config.app_env,

        app_base_url=get_config_value("APP_BASE_URL", "http://localhost:8501"),
        home_url=_absolute_url(get_config_value("HOME_URL", "https://yourdomain.com")),

        cookies_password=get_config_value("COOKIES_PASSWORD"),  # ✅ NEW

        free_total_prompt_limit=get_config_int("FREE_TOTAL_PROMPT_LIMIT", 5),
        pro_monthly_prompt_limit=get_config_int("PRO_MONTHLY_PROMPT_LIMIT", 200),
    )


# ----------------------------
# Validation
# ----------------------------
def validate_settings(settings: Settings) -> list[str]:
    required = {
        "OPENAI_API_KEY": settings.openai_api_key,
        "SUPABASE_URL": settings.supabase_url,
        "SUPABASE_ANON_KEY": settings.supabase_anon_key,
        "SUPABASE_SERVICE_ROLE_KEY": settings.supabase_service_role_key,
        "COOKIES_PASSWORD": settings.cookies_password,  # ✅ NEW
    }

    missing = [key for key, value in required.items() if not value]
    errors = [f"Missing required secret: {key}" for key in missing]
    errors.extend(validate_billing_config(settings.billing_config))
    return errors
