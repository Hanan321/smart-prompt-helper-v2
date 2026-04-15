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
from ui.auth_view import auth_panel
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

# Initialize Session State
if "page" not in st.session_state:
    st.session_state.page = "home"
if "is_password_recovery" not in st.session_state:
    st.session_state.is_password_recovery = False
if "user" not in st.session_state:
    st.session_state.user = None
if "session" not in st.session_state:
    st.session_state.session = None

# --- Load Settings and Services ---
settings = get_settings()
errors = validate_settings(settings)
if errors:
    for err in errors: st.error(err)
    st.stop()

cookies = EncryptedCookieManager(password=settings.cookies_password)
if not cookies.ready():
    st.stop()

# Initialize Clients
supabase_auth = create_supabase_auth_client(settings.supabase_url, settings.supabase_anon_key)
supabase_admin = create_supabase_admin_client(settings.supabase_url, settings.supabase_service_role_key)
prompt_generator = PromptGenerator(settings.openai_api_key)
billing_service = BillingService(settings.stripe_secret_key)

# --- Authentication Logic ---

def handle_auth_from_url():
    """Captures the 'code' from the email link and locks the app into reset mode."""
    params = st.query_params
    if "code" in params:
        try:
            # Trade code for session
            res = supabase_auth.auth.exchange_code_for_session({"auth_code": params["code"]})
            st.session_state.user = res.user
            st.session_state.session = res.session
            
            # FORCE the app into reset mode
            st.session_state.is_password_recovery = True
            st.session_state.page = "reset_password"
            
            save_auth_cookies(cookies, res)
            st.query_params.clear()
            st.rerun()
        except Exception as e:
            st.error(f"Invalid recovery link: {e}")

def reset_password_panel():
    st.markdown("### 🔒 Create New Password")
    with st.form("pw_reset"):
        new_pw = st.text_input("New Password", type="password")
        conf_pw = st.text_input("Confirm Password", type="password")
        if st.form_submit_button("Save Password", type="primary"):
            if new_pw != conf_pw:
                st.error("Passwords do not match.")
            else:
                try:
                    # Manually re-apply session before updating
                    sess = st.session_state.session
                    supabase_auth.auth.set_session(sess.access_token, sess.refresh_token)
                    
                    supabase_auth.auth.update_user({"password": new_pw})
                    st.success("Password updated!")
                    st.session_state.is_password_recovery = False
                    st.session_state.page = "home"
                    st.rerun()
                except Exception as e:
                    st.error(f"Update failed: {e}")

# --- Main App Execution ---
render_styles()
restore_auth_once(cookies, supabase_auth)
handle_auth_from_url()

# ROUTING
if st.session_state.is_password_recovery or st.session_state.page == "reset_password":
    reset_password_panel()
elif not st.session_state.user:
    auth_panel(supabase_auth, supabase_admin, cookies, save_auth_cookies, ensure_user_profile,
               sign_in, sign_up, resend_signup_confirmation, reset_password_for_email, settings)
else:
    # Logic for logged-in user dashboard
    user = st.session_state.user
    profile = get_user_profile(supabase_admin, user["id"])
    if (profile.get("plan") or "free").lower() != "pro":
        try:
            if billing_service.sync_active_subscription_by_email(
                supabase_admin,
                user["id"],
                user.get("email"),
            ):
                st.success("Your Pro subscription is active. Your account has been updated.")
                profile = get_user_profile(supabase_admin, user["id"])
        except Exception:
            st.warning("Could not refresh your billing status automatically. Please contact support if your payment was completed.")

    display_name = profile.get("username") or user.get("email", "User")
    st.markdown(f"## Welcome, {display_name}")
    
    account_summary_panel(display_name, user, (profile.get("plan") or "free").lower(), 
                          get_total_prompt_count(profile), get_monthly_prompt_count(profile), 
                          get_monthly_prompt_limit(profile), supabase_auth, cookies, clear_auth_cookies)
    prompt_form_panel(user, supabase_admin, prompt_generator, can_generate_prompt, increment_prompt_count)
    prompt_result_panel(st.session_state.get("generated_prompt", ""))
    st.divider()
    subscription_panel(profile, user, billing_service, settings)
