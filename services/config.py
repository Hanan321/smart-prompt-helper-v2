import os
from dataclasses import dataclass

from dotenv import load_dotenv
import streamlit as st

load_dotenv()


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str
    stripe_secret_key: str
    stripe_publishable_key: str
    stripe_price_pro: str

    app_base_url: str
    home_url: str

    cookies_password: str  # ✅ NEW

    free_total_prompt_limit: int = 5
    pro_monthly_prompt_limit: int = 200


# ----------------------------
# Safe env loaders
# ----------------------------
def _from_env(key: str, default: str = "") -> str:
    try:
        return st.secrets[key]
    except Exception:
        return os.getenv(key, default)


def _from_env_int(key: str, default: int) -> int:
    value = _from_env(key)
    if not value:
        return default
    return int(value)


def _absolute_url(value: str) -> str:
    clean = value.strip()
    if clean.startswith(("http://", "https://")):
        return clean
    return f"https://{clean}"


# ----------------------------
# Main settings loader
# ----------------------------
def get_settings() -> Settings:
    return Settings(
        openai_api_key=_from_env("OPENAI_API_KEY"),
        supabase_url=_from_env("SUPABASE_URL"),
        supabase_anon_key=_from_env("SUPABASE_ANON_KEY"),
        supabase_service_role_key=_from_env("SUPABASE_SERVICE_ROLE_KEY"),
        stripe_secret_key=_from_env("STRIPE_SECRET_KEY"),
        stripe_publishable_key=_from_env("STRIPE_PUBLISHABLE_KEY"),
        stripe_price_pro=_from_env("STRIPE_PRICE_PRO"),

        app_base_url=_from_env("APP_BASE_URL", "http://localhost:8501"),
        home_url=_absolute_url(_from_env("HOME_URL", "https://yourdomain.com")),

        cookies_password=_from_env("COOKIES_PASSWORD"),  # ✅ NEW

        free_total_prompt_limit=_from_env_int("FREE_TOTAL_PROMPT_LIMIT", 5),
        pro_monthly_prompt_limit=_from_env_int("PRO_MONTHLY_PROMPT_LIMIT", 200),
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
        "STRIPE_SECRET_KEY": settings.stripe_secret_key,
        "STRIPE_PRICE_PRO": settings.stripe_price_pro,
        "COOKIES_PASSWORD": settings.cookies_password,  # ✅ NEW
    }

    missing = [key for key, value in required.items() if not value]
    return missing
