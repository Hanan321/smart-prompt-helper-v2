import os
import streamlit as st
from streamlit_cookies_manager_ext import EncryptedCookieManager

# --- Core and Service Imports ---
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

# --- UI Imports ---
from ui.account_view import account_summary_panel
from ui.auth_view import auth_panel # Fixed: Removed the missing import
from ui.prompt_form_view import prompt_form_panel
from ui.prompt_result_view import prompt_result_panel
from ui.styles import render_styles
from ui.subscription_view import subscription_panel

# --- App Config ---
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

# --- Local UI Components ---

def reset_password_panel(supabase_client):
    """
    Renders the password reset form. 
    This is defined here locally to ensure it is always accessible to app.py.
    """
    st.markdown("<div class='main-title'>🔒 Reset Your Password</div>", unsafe_allow_html=True)
    st.write("Please enter your new password below.")

    with st.form("reset_password_form", clear_on_submit=True):
        new_pw = st.text_input("New Password", type="password")
        confirm_pw = st.text_input("Confirm New Password", type="password")
        submit = st.form_submit_button("Update Password", type="primary", use_container_width=True)

        if submit:
            if not new_pw or len(new_pw) < 6:
                st.error("Password must be at least 6 characters.")
            elif new_pw != confirm_pw:
                st.error("Passwords do not match.")
            else:
                try:
                    # This uses the session established by the recovery link
                    supabase_client.auth.update_user({"password": new_pw})
                    st.session_state.is_password_recovery = False
                    st.session_state.password_reset_done = True
                    st.session_state.page = "login"
                    st.rerun()
                except Exception as e:
                    st.error(f"Could not update password: {e}")

def handle_auth_from_url() -> None:
    """
    Handles both PKCE (code) and Implicit (token_hash) recovery flows.
    """
    params = st.query_params
    
    # 1. Check for modern PKCE 'code'
    if "code" in params:
        try:
            auth_res = supabase_auth.auth.exchange_code_for_session({"auth_code": params["code"]})
            st.session_state.session = auth_res.session
            st.session_state.user = auth_res.user
            st.session_state.page = "reset_password"
            st.session_state.is_password_recovery = True
            save_auth_cookies(cookies, auth_res)
            st.query_params.clear()
            st.rerun()
        except:
            pass

    # 2. Check for 'token_hash' (Email OTP flow)
    token_hash = params.get("token_hash")
    if params.get("type") == "recovery" or params.get("mode") == "reset":
        if token_hash:
            try:
                verify_res = supabase_auth.auth.verify_otp({"token_hash": token_hash, "type": "recovery"})
                st.session_state.session = verify_res.session
                st.session_state.user = verify_res.user
                st.session_state.page = "reset_password"
                st.session_state.is_password_recovery = True
                save_auth_cookies(cookies, verify_res)
                st.query_params.clear()
                st.rerun()
            except:
                pass
        else:
            # Fallback if mode=reset is just a routing flag
            st.session_state.page = "reset_password"
            st.session_state.is_password_recovery = True

def main_app_panel() -> None:
    user = st.session_state.user
    if not user: return
    
    profile = get_user_profile(supabase_admin, user["id"])
    if not profile:
        st.error("User profile not found.")
        return

    display_name = profile.get("username") or user.get("email", "User")
    current_plan = (profile.get("plan") or "free").lower()
    total_used = get_total_prompt_count(profile)
    monthly_used = get_monthly_prompt_count(profile)
    monthly_limit = get_monthly_prompt_limit(profile)

    st.markdown("<div class='main-title'>🎓 Smart Prompt Helper</div>", unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>Generate high-quality academic and professional prompts.</div>", unsafe_allow_html=True)

    account_summary_panel(
        display_name, user, current_plan, total_used, monthly_used, monthly_limit,
        supabase_auth, cookies, clear_auth_cookies
    )

    prompt_form_panel(user, supabase_admin, prompt_generator, can_generate_prompt, increment_prompt_count)
    prompt_result_panel(st.session_state.get("generated_prompt", ""))
    st.divider()
    subscription_panel(profile, user, billing_service, settings)

# --- Main App Logic ---
render_styles()
restore_auth_once(cookies, supabase_auth)
handle_auth_from_url()

# Routing Logic
if st.session_state.get("page") == "reset_password" and st.session_state.get("is_password_recovery"):
    reset_password_panel(supabase_auth)

elif not st.session_state.get("user"):
    if st.session_state.get("password_reset_done", False):
        st.success("Your password was reset. Please log in with your new credentials.")
        st.session_state.password_reset_done = False

    auth_panel(
        supabase_auth, supabase_admin, cookies, save_auth_cookies, ensure_user_profile,
        sign_in, sign_up, resend_signup_confirmation, reset_password_for_email, settings
    )
else:
    main_app_panel()