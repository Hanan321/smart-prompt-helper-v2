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

def init_session_state() -> None:
    # Ensure these keys exist and don't get reset on rerun
    if "page" not in st.session_state:
        st.session_state.page = "home"
    if "is_password_recovery" not in st.session_state:
        st.session_state.is_password_recovery = False
    
    defaults = {
        "generated_prompt": "",
        "session": None,
        "user": None,
        "auth_restored": False,
        "password_reset_done": False,
        "client_synced": False
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

init_session_state()

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

# --- Session Management ---
def sync_session_to_client():
    """Forces the Supabase client to use the session from Streamlit state."""
    if st.session_state.session:
        try:
            # Check if session is a dict or an object
            sess = st.session_state.session
            access_token = sess.get("access_token") if isinstance(sess, dict) else sess.access_token
            refresh_token = sess.get("refresh_token") if isinstance(sess, dict) else sess.refresh_token
            
            if access_token and refresh_token:
                supabase_auth.auth.set_session(access_token, refresh_token)
        except Exception as e:
            st.error(f"Sync error: {e}")

def handle_auth_from_url() -> None:
    params = st.query_params
    
    # 1. Handle the PKCE 'code' from email
    if "code" in params:
        try:
            auth_res = supabase_auth.auth.exchange_code_for_session({"auth_code": params["code"]})
            
            # Lock the state before the rerun
            st.session_state.session = auth_res.session
            st.session_state.user = auth_res.user
            st.session_state.is_password_recovery = True
            st.session_state.page = "reset_password"
            
            save_auth_cookies(cookies, auth_res)
            st.query_params.clear()
            st.rerun() # This triggers a fresh run where page='reset_password'
        except Exception as e:
            st.error(f"Recovery link failed: {e}")

# --- UI Components ---
def reset_password_panel():
    st.markdown("<div class='main-title'>🔒 Reset Your Password</div>", unsafe_allow_html=True)
    st.info("You are currently in a secure recovery session.")

    with st.form("reset_password_form"):
        new_pw = st.text_input("New Password", type="password", help="Minimum 6 characters")
        confirm_pw = st.text_input("Confirm New Password", type="password")
        submit = st.form_submit_button("Update Password", type="primary", use_container_width=True)

        if submit:
            if len(new_pw) < 6:
                st.error("Password is too short.")
            elif new_pw != confirm_pw:
                st.error("Passwords do not match.")
            else:
                try:
                    # Final sync to ensure the client is authorized
                    sync_session_to_client()
                    supabase_auth.auth.update_user({"password": new_pw})
                    
                    # Success! Clean up state
                    st.session_state.is_password_recovery = False
                    st.session_state.password_reset_done = True
                    st.session_state.page = "login"
                    st.session_state.session = None
                    st.rerun()
                except Exception as e:
                    st.error(f"Update failed: {e}")

def main_app_panel() -> None:
    user = st.session_state.user
    if not user: return
    profile = get_user_profile(supabase_admin, user["id"])
    if not profile:
        st.error("User profile not found.")
        return
    
    display_name = profile.get("username") or user.get("email", "User")
    st.markdown("<div class='main-title'>🎓 Smart Prompt Helper</div>", unsafe_allow_html=True)
    account_summary_panel(display_name, user, (profile.get("plan") or "free").lower(), 
                          get_total_prompt_count(profile), get_monthly_prompt_count(profile), 
                          get_monthly_prompt_limit(profile), supabase_auth, cookies, clear_auth_cookies)
    prompt_form_panel(user, supabase_admin, prompt_generator, can_generate_prompt, increment_prompt_count)
    prompt_result_panel(st.session_state.get("generated_prompt", ""))
    st.divider()
    subscription_panel(profile, user, billing_service, settings)

# --- EXECUTION FLOW ---
render_styles()
restore_auth_once(cookies, supabase_auth)
handle_auth_from_url() # This must run before routing
sync_session_to_client() # This must run to keep the 'update' permission

# 1. Check recovery state FIRST
if st.session_state.is_password_recovery or st.session_state.page == "reset_password":
    reset_password_panel()

# 2. Otherwise handle normal auth/app
elif not st.session_state.user:
    if st.session_state.get("password_reset_done"):
        st.success("Password updated! Please log in.")
        st.session_state.password_reset_done = False
    
    auth_panel(supabase_auth, supabase_admin, cookies, save_auth_cookies, ensure_user_profile,
               sign_in, sign_up, resend_signup_confirmation, reset_password_for_email, settings)
else:
    main_app_panel()