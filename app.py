import os

import streamlit as st
from streamlit_cookies_manager_ext import EncryptedCookieManager

from core.cookies_auth import clear_auth_cookies, restore_auth_once, save_auth_cookies
from services.auth import (
    create_supabase_admin_client,
    create_supabase_auth_client,
    resend_signup_confirmation,
    reset_password_for_email,
    restore_session_from_tokens,
    sign_in,
    sign_up,
)
from services.billing import BillingService
from services.config import get_settings, validate_settings
from services.prompt_service import PromptGenerator
from services.usage import (
    can_generate_prompt,
    ensure_user_profile,
    get_monthly_prompt_count,
    get_monthly_prompt_limit,
    get_total_prompt_count,
    get_user_profile,
    increment_prompt_count,
)
from ui.account_view import account_summary_panel
from ui.auth_view import auth_panel
from ui.landing_view import landing_page
from ui.prompt_form_view import prompt_form_panel
from ui.prompt_result_view import prompt_result_panel
from ui.styles import render_styles
from ui.subscription_view import subscription_panel


st.set_page_config(
    page_title="Smart Prompt Helper",
    page_icon="🎓",
    layout="centered",
)


settings = get_settings()
missing_settings = validate_settings(settings)
if missing_settings:
    st.error(f"Missing environment variables: {', '.join(missing_settings)}")
    st.stop()


cookie_password = os.getenv("COOKIES_PASSWORD", "")
if not cookie_password:
    st.error("Missing COOKIES_PASSWORD environment variable.")
    st.stop()


cookies = EncryptedCookieManager(
    prefix="smart-prompt-helper/",
    password=cookie_password,
)

if not cookies.ready():
    st.stop()


supabase_auth = create_supabase_auth_client(
    settings.supabase_url,
    settings.supabase_anon_key,
)
supabase_admin = create_supabase_admin_client(
    settings.supabase_url,
    settings.supabase_service_role_key,
)
prompt_generator = PromptGenerator(settings.openai_api_key)
billing_service = BillingService(settings.stripe_secret_key)


# ----------------------------
# Session State Defaults
# ----------------------------
if "session" not in st.session_state:
    st.session_state.session = None

if "user" not in st.session_state:
    st.session_state.user = None

if "generated_prompt" not in st.session_state:
    st.session_state.generated_prompt = ""

if "auth_restored" not in st.session_state:
    st.session_state.auth_restored = False

if "show_welcome" not in st.session_state:
    st.session_state.show_welcome = True

if "page" not in st.session_state:
    st.session_state.page = "home"


# ----------------------------
# Handle auth session from email link
# Must happen BEFORE restoring old cookies
# ----------------------------
query_params = st.query_params
url_access_token = query_params.get("access_token")
url_refresh_token = query_params.get("refresh_token")

if url_access_token and url_refresh_token:
    clear_auth_cookies(cookies)

    restored = restore_session_from_tokens(
        supabase_auth,
        url_access_token,
        url_refresh_token,
    )

    if restored:
        st.session_state.session = restored.get("session")
        st.session_state.user = restored.get("user")
        save_auth_cookies(cookies, restored)
        st.session_state.auth_restored = True
        st.session_state.show_welcome = True
        st.session_state.page = "app"

    st.query_params.clear()
    st.rerun()


def app_panel(user: dict) -> None:
    if not user or "id" not in user:
        st.error("User session error. Please log in again.")
        st.stop()

    ensure_user_profile(
        supabase_admin,
        user["id"],
        user.get("email", ""),
    )

    profile = get_user_profile(supabase_admin, user["id"])
    current_plan = (profile.get("plan") or "free").lower()
    display_name = profile.get("username") or user.get("email", "unknown")

    total_used = get_total_prompt_count(supabase_admin, user["id"])
    monthly_used = get_monthly_prompt_count(supabase_admin, user["id"])
    monthly_limit = get_monthly_prompt_limit(supabase_admin, user["id"])

    st.markdown(
        "<div class='main-title'>🎓 Smart Prompt Helper</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div class='subtitle'>Generate clear, structured, high-quality prompts for academic and professional work.</div>",
        unsafe_allow_html=True,
    )

    account_summary_panel(
        display_name,
        user,
        current_plan,
        total_used,
        monthly_used,
        monthly_limit,
        supabase_auth,
        cookies,
        clear_auth_cookies,
    )

    prompt_form_panel(
        user,
        supabase_admin,
        prompt_generator,
        can_generate_prompt,
        increment_prompt_count,
    )

    prompt_result_panel(st.session_state.generated_prompt)

    st.divider()
    subscription_panel(profile, user, billing_service, settings)


# ----------------------------
# Global styling + auth restore
# ----------------------------
render_styles()
restore_auth_once(cookies, supabase_auth)

if st.session_state.user:
    st.session_state.page = "app"


# ----------------------------
# Routing
# ----------------------------
if st.session_state.page == "home" and not st.session_state.user:
    landing_page()

elif not st.session_state.user:
    auth_panel(
        supabase_auth,
        supabase_admin,
        cookies,
        save_auth_cookies,
        ensure_user_profile,
        sign_in,
        sign_up,
        resend_signup_confirmation,
        reset_password_for_email,
        settings,
    )

else:
    app_panel(st.session_state.user)