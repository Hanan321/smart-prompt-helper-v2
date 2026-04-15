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
# Added reset_password_panel to the imports
from ui.auth_view import auth_panel, reset_password_panel
from ui.prompt_form_view import prompt_form_panel
from ui.prompt_result_view import prompt_result_panel
from ui.styles import render_styles
from ui.subscription_view import subscription_panel

st.set_page_config(
    page_title="Smart Prompt Helper",
    page_icon="🎓",
    layout="centered",
)

def init_session_state() -> None:
    defaults = {
        "generated_prompt": "",
        "session": None,
        "user": None,
        "auth_restored": False,
        "page": "home",
        "is_password_recovery": False,
        "password_reset_done": False,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

init_session_state()

# --- Load Settings and Services ---
settings = get_settings()
errors = validate_settings(settings)
if errors:
    for err in errors:
        st.error(err)
    st.stop()

cookies = EncryptedCookieManager(password=settings.cookies_password)
if not cookies.ready():
    st.stop()

supabase_auth = create_supabase_auth_client(settings.supabase_url, settings.supabase_anon_key)
supabase_admin = create_supabase_admin_client(settings.supabase_url, settings.supabase_service_role_key)
prompt_generator = PromptGenerator(settings.openai_api_key)
billing_service = BillingService(settings.stripe_secret_key)

def handle_auth_from_url() -> None:
    """
    Handles the modern PKCE flow by exchanging the 'code' for a session.
    """
    params = st.query_params
    
    # 1. Look for the 'code' sent by Supabase in the email link
    if "code" in params:
        try:
            # Trade the code for a real authenticated session
            auth_response = supabase_auth.auth.exchange_code_for_session({
                "auth_code": params["code"]
            })
            
            # Store the session and user data
            st.session_state.session = auth_response.session
            st.session_state.user = auth_response.user
            
            # Lock the app into the reset password view
            st.session_state.page = "reset_password"
            st.session_state.is_password_recovery = True
            
            # Persist the login via cookies
            save_auth_cookies(cookies, auth_response)
            
            # Clear query params and rerun to show the form
            st.query_params.clear()
            st.rerun()
            
        except Exception as e:
            st.error(f"Authentication link is invalid or expired: {e}")
            return

    # 2. Check for explicit reset mode (optional fallback)
    if params.get("mode") == "reset":
        st.session_state.page = "reset_password"
        st.session_state.is_password_recovery = True

def main_app_panel() -> None:
    user = st.session_state.user
    if not user:
        return

    profile = get_user_profile(supabase_admin, user["id"])
    if not profile:
        st.error("User profile not found.")
        return

    display_name = profile.get("username") or user.get("email", "User")
    current_plan = (profile.get("plan") or "free").lower()
    total_used = get_total_prompt_count(profile)
    monthly_used = get_monthly_prompt_count(profile)
    monthly_limit = get_monthly_prompt_limit(profile)

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

    prompt_result_panel(st.session_state.get("generated_prompt", ""))
    st.divider()
    subscription_panel(profile, user, billing_service, settings)

# --- Main App Execution ---
render_styles()
restore_auth_once(cookies, supabase_auth)
handle_auth_from_url()

# 1. Priority View: Reset Password
if (
    st.session_state.get("page") == "reset_password"
    and st.session_state.get("is_password_recovery")
):
    # Renders the reset form using the authenticated client
    reset_password_panel(supabase_auth)

# 2. Secondary View: Logged Out (Auth Panel)
elif not st.session_state.get("user"):
    if st.session_state.get("password_reset_done", False):
        st.success("Your password was reset. Please log in with your new password.")
        st.session_state.password_reset_done = False

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

# 3. Final View: Logged In (Dashboard)
else:
    main_app_panel()