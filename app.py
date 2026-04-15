import os

import streamlit as st
import streamlit.components.v1 as components
from streamlit_cookies_manager_ext import EncryptedCookieManager

from core.cookies_auth import clear_auth_cookies, restore_auth_once, save_auth_cookies
from services.auth import (
    create_supabase_admin_client,
    create_supabase_auth_client,
    exchange_code_for_session,
    resend_signup_confirmation,
    reset_password_for_email,
    restore_session_from_tokens,
    sign_in,
    sign_up,
    update_user_password,
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


def init_session_state() -> None:
    defaults = {
        "session": None,
        "user": None,
        "generated_prompt": "",
        "auth_restored": False,
        "show_welcome": True,
        "page": "app",
        "password_recovery_active": False,
        "password_reset_complete": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get_cookie_password() -> str:
    try:
        if "COOKIES_PASSWORD" in st.secrets:
            return str(st.secrets["COOKIES_PASSWORD"]).strip()
    except Exception:
        pass

    return os.getenv("COOKIES_PASSWORD", "").strip()


def build_clients():
    settings = get_settings()
    missing_settings = validate_settings(settings)
    if missing_settings:
        st.error(f"Missing environment variables: {', '.join(missing_settings)}")
        st.stop()

    cookie_password = settings.cookies_password
    if not cookie_password:
        st.error("Missing COOKIES_PASSWORD in Streamlit secrets or environment variables.")
        st.stop()

    cookies = EncryptedCookieManager(
        prefix="smart-prompt-helper/",
        password=cookie_password,
    )

    if not cookies.ready():
        st.stop()

    try:
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
    except Exception as exc:
        st.error(f"App startup failed: {exc}")
        st.stop()

    return settings, cookies, supabase_auth, supabase_admin, prompt_generator, billing_service


def handle_auth_link(supabase_auth, cookies) -> None:
    query_params = st.query_params
    url_code = query_params.get("code")
    url_access_token = query_params.get("access_token")
    url_refresh_token = query_params.get("refresh_token")
    link_type = (query_params.get("type") or "").lower()
    reset_requested = query_params.get("reset_password") == "1"
    is_password_recovery = reset_requested or link_type == "recovery"

    if not url_code and (not url_access_token or not url_refresh_token):
        if reset_requested:
            clear_auth_cookies(cookies)
            st.session_state.session = None
            st.session_state.user = None
            st.session_state.page = "reset_password"
        return

    clear_auth_cookies(cookies)

    if url_code:
        restored = exchange_code_for_session(supabase_auth, url_code)
    else:
        try:
            restored = restore_session_from_tokens(
                supabase_auth,
                url_access_token,
                url_refresh_token,
            )
        except Exception:
            restored = None

    if restored:
        st.session_state.session = restored.get("session")
        st.session_state.user = restored.get("user")
        save_auth_cookies(cookies, restored)
        st.session_state.auth_restored = True
        st.session_state.show_welcome = True
        if is_password_recovery:
            st.session_state.password_recovery_active = True
            st.session_state.page = "reset_password"
        else:
            st.session_state.page = "app"

    st.query_params.clear()
    st.rerun()


def sync_supabase_hash_params() -> None:
    components.html(
        """
        <script>
        const parentLocation = window.parent.location;
        const hash = parentLocation.hash ? parentLocation.hash.substring(1) : "";

        if (hash.includes("access_token=") || hash.includes("refresh_token=")) {
            const hashParams = new URLSearchParams(hash);
            const searchParams = new URLSearchParams(parentLocation.search);

            ["access_token", "refresh_token", "type", "token_type", "expires_in"].forEach((key) => {
                const value = hashParams.get(key);
                if (value) {
                    searchParams.set(key, value);
                }
            });

            if (hashParams.get("type") === "recovery") {
                searchParams.set("reset_password", "1");
            }

            parentLocation.replace(`${parentLocation.pathname}?${searchParams.toString()}`);
        }
        </script>
        """,
        height=0,
    )


def app_panel(
    user: dict,
    settings,
    cookies,
    supabase_auth,
    supabase_admin,
    prompt_generator,
    billing_service,
) -> None:
    if not user or "id" not in user:
        st.error("User session error. Please log in again.")
        clear_auth_cookies(cookies)
        st.session_state.session = None
        st.session_state.user = None
        st.session_state.generated_prompt = ""
        st.rerun()

    try:
        ensure_user_profile(
            supabase_admin,
            user["id"],
            user.get("email", ""),
            user.get("user_metadata", {}).get("username"),
        )
    except TypeError:
        # Fallback in case deployed code still expects the older function signature
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


def reset_password_panel(supabase_auth, cookies) -> None:
    st.markdown(
        "<div class='main-title'>🎓 Smart Prompt Helper</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div class='subtitle'>Create a new password for your account.</div>",
        unsafe_allow_html=True,
    )

    if st.session_state.password_reset_complete:
        st.success("Your password has been updated. Please log in with your new password.")
        if st.button("Go to log in", type="primary", use_container_width=True):
            st.session_state.password_reset_complete = False
            st.session_state.page = "app"
            st.rerun()
        return

    if not st.session_state.user:
        st.info("Opening your secure password reset link. If this message stays here, please send yourself a new reset email and open the newest link.")
        return

    with st.form("update_password_form"):
        password = st.text_input("New password", type="password")
        confirm_password = st.text_input("Confirm new password", type="password")
        submitted = st.form_submit_button("Update password", use_container_width=True)

        if submitted:
            if not password:
                st.error("Please enter a new password.")
            elif len(password) < 8:
                st.error("Password must be at least 8 characters long.")
            elif not confirm_password:
                st.error("Please confirm your new password.")
            elif password != confirm_password:
                st.error("Passwords do not match.")
            else:
                try:
                    update_user_password(supabase_auth, password)
                    clear_auth_cookies(cookies)
                    st.session_state.session = None
                    st.session_state.user = None
                    st.session_state.generated_prompt = ""
                    st.session_state.password_recovery_active = False
                    st.session_state.password_reset_complete = True
                    st.session_state.page = "app"
                    st.rerun()
                except Exception as exc:
                    st.error(f"Could not update password: {exc}")


def main() -> None:
    init_session_state()
    render_styles()

    (
        settings,
        cookies,
        supabase_auth,
        supabase_admin,
        prompt_generator,
        billing_service,
    ) = build_clients()

    sync_supabase_hash_params()
    handle_auth_link(supabase_auth, cookies)
    restore_auth_once(cookies, supabase_auth)

    if st.session_state.user and st.session_state.page != "reset_password":
        st.session_state.page = "app"

    if st.session_state.page == "reset_password" or st.session_state.password_reset_complete:
        reset_password_panel(supabase_auth, cookies)
        return

    if not st.session_state.user:
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
        return

    app_panel(
        st.session_state.user,
        settings,
        cookies,
        supabase_auth,
        supabase_admin,
        prompt_generator,
        billing_service,
    )


if __name__ == "__main__":
    main()
