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
# Handle auth session from email link
# ----------------------------
query_params = st.query_params
url_access_token = query_params.get("access_token")
url_refresh_token = query_params.get("refresh_token")
url_type = query_params.get("type")
url_mode = query_params.get("mode", "")
token_hash = query_params.get("token_hash")

if url_mode == "reset":
    st.session_state.is_password_recovery = True
    st.session_state.page = "reset_password"

# Verify token_hash ONCE, then clear URL so Streamlit doesn't consume it again
if url_mode == "reset" and token_hash and not st.session_state.get("auth_restored", False):
    try:
        verify_response = supabase_auth.auth.verify_otp(
            {
                "token_hash": token_hash,
                "type": "recovery",
            }
        )

        verify_response = verify_response.model_dump() if hasattr(verify_response, "model_dump") else verify_response
        session = verify_response.get("session")
        user = verify_response.get("user")

        if session and user:
            st.session_state.session = session
            st.session_state.user = user
            st.session_state.auth_restored = True
            st.session_state.is_password_recovery = True
            st.session_state.page = "reset_password"

            save_auth_cookies(cookies, {"session": session, "user": user})

            st.query_params.clear()
            st.rerun()
        else:
            st.error("Invalid or expired reset link.")
            st.stop()

    except Exception as e:
        st.error(f"Invalid or expired reset link: {e}")
        st.stop()

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

        if url_type == "recovery" or url_mode == "reset":
            st.session_state.is_password_recovery = True
            st.session_state.page = "reset_password"
        else:
            st.session_state.is_password_recovery = False
            st.session_state.page = "app"

    st.query_params.clear()
    st.rerun()
#----------------------------------------------

def reset_password_panel() -> None:
    st.markdown(
        "<div class='main-title'>Reset your password</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div class='subtitle'>Enter your new password below.</div>",
        unsafe_allow_html=True,
    )

    with st.form("reset_password_form"):
        new_password = st.text_input("New Password", type="password")
        confirm_password = st.text_input("Confirm New Password", type="password")
        submitted = st.form_submit_button("Update Password", use_container_width=True)

        if submitted:
            if not new_password:
                st.error("Please enter a new password.")
            elif len(new_password) < 8:
                st.error("Password must be at least 8 characters long.")
            elif new_password != confirm_password:
                st.error("Passwords do not match.")
            else:
                try:
                    supabase_auth.auth.update_user({"password": new_password})

                    clear_auth_cookies(cookies)
                    st.session_state.session = None
                    st.session_state.user = None
                    st.session_state.generated_prompt = ""
                    st.session_state.auth_restored = False
                    st.session_state.is_password_recovery = False
                    st.session_state.password_reset_done = True
                    st.session_state.page = "home"

                    st.success(
                        "Password updated successfully. Please log in with your new password."
                    )
                    st.rerun()
                except Exception as exc:
                    st.error(f"Could not update password: {exc}")


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


render_styles()
restore_auth_once(cookies, supabase_auth)

if st.session_state.page == "reset_password" and st.session_state.is_password_recovery:
    reset_password_panel()

elif not st.session_state.user:
    if st.session_state.password_reset_done:
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

else:
    app_panel(st.session_state.user)
