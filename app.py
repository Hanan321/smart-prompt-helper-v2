import logging
from pathlib import Path
from urllib.parse import parse_qsl

import streamlit as st
import streamlit.components.v1 as components
from streamlit_cookies_manager_ext import EncryptedCookieManager

from core.cookies_auth import clear_auth_cookies, restore_auth_once, save_auth_cookies
from services.auth import (
    create_supabase_admin_client,
    create_supabase_auth_client,
    exchange_code_for_session,
    resend_signup_confirmation,
    restore_session_from_tokens,
    send_sign_in_link,
    sign_in,
    sign_up,
)
from services.billing import BillingService
from services.config import get_settings, validate_settings
from services.prompt_service import PromptGenerator
from services.usage import (
    can_generate_prompt,
    downgrade_if_scheduled_subscription_ended,
    ensure_user_profile,
    get_monthly_prompt_count,
    get_monthly_prompt_limit,
    get_total_prompt_count,
    get_user_profile,
    increment_prompt_count,
)
from ui.account_view import account_summary_panel
from ui.auth_view import auth_panel
from ui.profile_view import profile_panel
from ui.prompt_form_view import prompt_form_panel
from ui.prompt_result_view import prompt_result_panel
from ui.styles import render_styles
from ui.subscription_view import subscription_panel

logger = logging.getLogger(__name__)


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
        "show_welcome": False,
        "show_resend_confirmation_form": False,
        "last_auth_hash_consumed": "",
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


settings = get_settings()
missing_settings = validate_settings(settings)
if missing_settings:
    st.error("Configuration error:")
    for missing_setting in missing_settings:
        st.error(missing_setting)
    st.stop()


cookie_password = settings.cookies_password
if not cookie_password:
    st.error("Missing COOKIES_PASSWORD environment variable.")
    st.stop()


cookies = EncryptedCookieManager(
    prefix="smart-prompt-helper/",
    password=cookie_password,
)

if not cookies.ready():
    st.stop()


init_session_state()

supabase_auth = create_supabase_auth_client(
    settings.supabase_url,
    settings.supabase_anon_key,
)
supabase_admin = create_supabase_admin_client(
    settings.supabase_url,
    settings.supabase_service_role_key,
)
prompt_generator = PromptGenerator(settings.openai_api_key)
billing_config = getattr(settings, "billing_config", None)
active_stripe_secret_key = getattr(
    billing_config,
    "stripe_secret_key",
    settings.stripe_secret_key,
)
billing_service = BillingService(active_stripe_secret_key, settings.app_env)
auth_hash_reader = components.declare_component(
    "auth_hash_reader",
    path=str(Path(__file__).parent / "components" / "auth_hash_reader"),
)


def _read_auth_hash_params() -> tuple[dict[str, str], str]:
    auth_hash = auth_hash_reader(key="auth_hash_reader", default="") or ""

    if not isinstance(auth_hash, str):
        return {}, ""

    clean_hash = auth_hash.lstrip("#")
    if not clean_hash:
        return {}, ""

    return dict(parse_qsl(clean_hash, keep_blank_values=True)), clean_hash


def _query_or_hash_value(
    query_params,
    hash_params: dict[str, str],
    key: str,
    default: str = "",
) -> str:
    return query_params.get(key) or hash_params.get(key) or default


def _set_restored_auth(restored: dict, url_type: str | None, url_mode: str) -> None:
    st.session_state.session = restored.get("session")
    st.session_state.user = restored.get("user")
    st.session_state.auth_restored = True
    st.session_state.show_welcome = url_type != "recovery" and url_mode != "reset"

    save_auth_cookies(cookies, restored)

    if url_type == "recovery" or url_mode == "reset":
        st.session_state.is_password_recovery = True
        st.session_state.page = "reset_password"
    else:
        st.session_state.is_password_recovery = False
        st.session_state.page = "app"


def _ensure_current_auth_client_session() -> bool:
    session = st.session_state.get("session") or {}
    access_token = session.get("access_token") or cookies.get("access_token")
    refresh_token = session.get("refresh_token") or cookies.get("refresh_token")

    restored = restore_session_from_tokens(
        supabase_auth,
        access_token,
        refresh_token,
    )

    if not restored:
        return False

    st.session_state.session = restored.get("session")
    st.session_state.user = restored.get("user")
    save_auth_cookies(cookies, restored)
    return True


def handle_auth_from_url() -> None:
    query_params = st.query_params
    hash_params, auth_hash = _read_auth_hash_params()

    if auth_hash and auth_hash == st.session_state.get("last_auth_hash_consumed"):
        hash_params = {}
        auth_hash = ""

    url_access_token = _query_or_hash_value(query_params, hash_params, "access_token")
    url_refresh_token = _query_or_hash_value(query_params, hash_params, "refresh_token")
    url_type = _query_or_hash_value(query_params, hash_params, "type")
    url_mode = _query_or_hash_value(query_params, hash_params, "mode")
    url_code = _query_or_hash_value(query_params, hash_params, "code")
    token_hash = _query_or_hash_value(query_params, hash_params, "token_hash")
    url_error = _query_or_hash_value(query_params, hash_params, "error")
    url_error_description = _query_or_hash_value(
        query_params,
        hash_params,
        "error_description",
    )
    is_recovery_link = url_mode == "reset" or url_type == "recovery"

    if url_error:
        st.error(
            url_error_description
            or "Supabase could not complete authentication from this link."
        )
        st.stop()

    if is_recovery_link:
        st.session_state.is_password_recovery = True
        st.session_state.page = "reset_password"

    if token_hash:
        otp_type = "recovery" if is_recovery_link else (url_type or "magiclink")

        try:
            verify_response = supabase_auth.auth.verify_otp(
                {
                    "token_hash": token_hash,
                    "type": otp_type,
                }
            )

            if hasattr(verify_response, "model_dump"):
                verify_response = verify_response.model_dump()

            session = verify_response.get("session")
            user = verify_response.get("user")

            if session and user:
                _set_restored_auth(
                    {"session": session, "user": user},
                    url_type,
                    url_mode,
                )
                st.session_state.last_auth_hash_consumed = auth_hash

                st.query_params.clear()
                st.rerun()
            else:
                if is_recovery_link:
                    st.error("Invalid or expired reset link.")
                else:
                    st.error("Invalid or expired sign-in link.")
                st.stop()

        except Exception as exc:
            if is_recovery_link:
                st.error(f"Invalid or expired reset link: {exc}")
            else:
                st.error(f"Invalid or expired sign-in link: {exc}")
            st.stop()

    if url_code:
        restored = exchange_code_for_session(supabase_auth, url_code)

        if restored:
            _set_restored_auth(restored, url_type, url_mode)
            st.session_state.last_auth_hash_consumed = auth_hash
        elif is_recovery_link:
            st.error("Invalid or expired reset link.")
            st.stop()
        else:
            st.error(
                "Could not complete sign-in from this link. Please request a new sign-in link."
            )
            st.stop()

        st.query_params.clear()
        st.rerun()

    if url_access_token and url_refresh_token:
        restored = restore_session_from_tokens(
            supabase_auth,
            url_access_token,
            url_refresh_token,
        )

        if restored:
            _set_restored_auth(restored, url_type, url_mode)
            st.session_state.last_auth_hash_consumed = auth_hash
        elif is_recovery_link:
            st.error("Invalid or expired reset link.")
            st.stop()
        else:
            st.error(
                "Could not complete sign-in from this link. Please request a new sign-in link."
            )
            st.stop()

        st.query_params.clear()
        st.rerun()


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
                    if not _ensure_current_auth_client_session():
                        st.error(
                            "Your reset session expired. Please request a new password reset link."
                        )
                        return

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
    profile = downgrade_if_scheduled_subscription_ended(
        supabase_admin,
        user["id"],
        profile,
    )

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

    if settings.app_env == "test":
        checkout_session_id = st.query_params.get("checkout_session_id") or st.query_params.get(
            "session_id"
        )
        prompt_pack_checkout = st.query_params.get("prompt_pack_checkout")
        logger.info(
            "Prompt pack sync check: env=%s active_base_url=%s has_checkout_return=%s",
            settings.app_env,
            settings.app_base_url,
            bool(prompt_pack_checkout),
        )
        if prompt_pack_checkout:
            safe_checkout_session_id = (
                f"...{checkout_session_id[-6:]}" if checkout_session_id else "missing"
            )
            logger.info(
                "Prompt pack checkout return detected: user_id=%s env=%s status=%s checkout_session_id=%s uses_checkout_session_id=%s",
                user["id"],
                settings.app_env,
                prompt_pack_checkout,
                safe_checkout_session_id,
                bool(checkout_session_id and str(checkout_session_id).startswith("cs_")),
            )
        had_prompt_pack_credits = (
            int(profile.get("credit_balance", 0) or 0) > 0
            or int(profile.get("total_credits_purchased", 0) or 0) > 0
        )
        try:
            synced_from_redirect = False
            prompt_pack_price_id = getattr(
                getattr(settings, "billing_config", None),
                "stripe_price_pack_10",
                getattr(settings, "stripe_price_pack_10", ""),
            )
            if (
                prompt_pack_checkout == "success" and checkout_session_id
            ) or (
                checkout_session_id and str(checkout_session_id).startswith("cs_")
            ):
                synced_from_redirect = billing_service.sync_prompt_pack_checkout_session(
                    supabase_admin,
                    user["id"],
                    checkout_session_id,
                    profile.get("stripe_customer_id"),
                    prompt_pack_price_id,
                )

            synced_from_history = billing_service.sync_completed_prompt_pack_purchases(
                supabase_admin,
                user["id"],
                profile.get("stripe_customer_id"),
                prompt_pack_price_id,
            )

            profile = get_user_profile(supabase_admin, user["id"])
            has_prompt_pack_credits = (
                int(profile.get("credit_balance", 0) or 0) > 0
                or int(profile.get("total_credits_purchased", 0) or 0) > 0
            )

            if synced_from_redirect or synced_from_history:
                st.success("Your prompt-pack credits have been added.")
                if prompt_pack_checkout:
                    st.query_params.clear()
                    st.rerun()
            elif prompt_pack_checkout and has_prompt_pack_credits:
                logger.info(
                    "Prompt pack checkout already reflected in billing: user_id=%s env=%s",
                    user["id"],
                    settings.app_env,
                )
                st.query_params.clear()
                st.rerun()
            elif prompt_pack_checkout:
                st.query_params.clear()
        except Exception:
            profile = get_user_profile(supabase_admin, user["id"])
            has_prompt_pack_credits = (
                int(profile.get("credit_balance", 0) or 0) > 0
                or int(profile.get("total_credits_purchased", 0) or 0) > 0
            )
            if prompt_pack_checkout:
                st.query_params.clear()
            if has_prompt_pack_credits or had_prompt_pack_credits:
                logger.info(
                    "Prompt pack sync warning suppressed because credits are present: user_id=%s env=%s",
                    user["id"],
                    settings.app_env,
                )
            else:
                logger.exception("Could not sync prompt-pack purchase automatically.")
                st.warning(
                    "Could not sync your prompt-pack purchase automatically. Please make sure the Supabase billing migration has been applied."
                )

    current_plan = (profile.get("plan") or "free").lower()
    display_name = profile.get("username") or user.get("email", "unknown")

    total_used = get_total_prompt_count(supabase_admin, user["id"])
    monthly_used = get_monthly_prompt_count(supabase_admin, user["id"])
    monthly_limit = get_monthly_prompt_limit(supabase_admin, user["id"])
    credit_balance = int(profile.get("credit_balance", 0) or 0)
    total_credits_purchased = int(profile.get("total_credits_purchased", 0) or 0)
    free_prompt_limit = int(
        profile.get(
            "free_prompt_limit",
            settings.test_free_total_prompt_limit
            if settings.app_env == "test"
            else settings.free_total_prompt_limit,
        )
    )

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
        credit_balance,
        free_prompt_limit,
        total_credits_purchased,
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
    subscription_panel(profile, user, billing_service, supabase_admin, settings)


def user_profile_page(user: dict) -> None:
    if not user or "id" not in user:
        st.error("User session error. Please log in again.")
        st.stop()

    ensure_user_profile(
        supabase_admin,
        user["id"],
        user.get("email", ""),
    )

    profile = get_user_profile(supabase_admin, user["id"])
    profile = downgrade_if_scheduled_subscription_ended(
        supabase_admin,
        user["id"],
        profile,
    )
    profile_panel(
        user,
        profile,
        supabase_auth,
        cookies,
        billing_service,
        supabase_admin,
    )


render_styles()
handle_auth_from_url()
restore_auth_once(cookies, supabase_auth)

if (
    st.session_state.get("page") == "reset_password"
    and st.session_state.get("is_password_recovery")
):
    reset_password_panel()

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
        send_sign_in_link,
        settings,
    )

elif st.session_state.get("page") == "profile":
    user_profile_page(st.session_state.get("user"))

else:
    app_panel(st.session_state.get("user"))
