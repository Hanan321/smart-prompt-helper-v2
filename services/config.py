import os
from dataclasses import dataclass

from dotenv import load_dotenv

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
    stripe_price_premium: str
    app_base_url: str
    free_daily_prompt_limit: int = 5



def _from_env(key: str, default: str = "") -> str:
    return os.getenv(key, default)



def get_settings() -> Settings:
    return Settings(
        openai_api_key=_from_env("OPENAI_API_KEY"),
        supabase_url=_from_env("SUPABASE_URL"),
        supabase_anon_key=_from_env("SUPABASE_ANON_KEY"),
        supabase_service_role_key=_from_env("SUPABASE_SERVICE_ROLE_KEY"),
        stripe_secret_key=_from_env("STRIPE_SECRET_KEY"),
        stripe_publishable_key=_from_env("STRIPE_PUBLISHABLE_KEY"),
        stripe_price_pro=_from_env("STRIPE_PRICE_PRO"),
        stripe_price_premium=_from_env("STRIPE_PRICE_PREMIUM"),
        app_base_url=_from_env("APP_BASE_URL", "http://localhost:8501"),
        free_daily_prompt_limit=int(_from_env("FREE_DAILY_PROMPT_LIMIT", "5")),
    )



def validate_settings(settings: Settings) -> list[str]:
    required = {
        "OPENAI_API_KEY": settings.openai_api_key,
        "SUPABASE_URL": settings.supabase_url,
        "SUPABASE_ANON_KEY": settings.supabase_anon_key,
        "SUPABASE_SERVICE_ROLE_KEY": settings.supabase_service_role_key,
        "STRIPE_SECRET_KEY": settings.stripe_secret_key,
        "STRIPE_PRICE_PRO": settings.stripe_price_pro,
        "STRIPE_PRICE_PREMIUM": settings.stripe_price_premium,
    }
    missing = [k for k, v in required.items() if not v]
    return missing
