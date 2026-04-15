from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import streamlit as st


def _with_query_param(url: str, key: str, value: str) -> str:
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query[key] = value
    return urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            parts.path,
            urlencode(query),
            parts.fragment,
        )
    )


def _show_auth_link_message() -> None:
    query_params = st.query_params
    error = query_params.get("error")
    error_code = query_params.get("error_code")

    if not error and not error_code:
        return

    error_text = f"{error} {error_code}".lower()

    if "otp_expired" in error_text:
        st.warning("This confirmation link has expired. Please request a new one below.")
    elif "access_denied" in error_text:
        st.warning("This confirmation link is invalid or has already been used.")
    else:
        st.warning("There was an issue with the authentication link.")


def _handle_login(
    supabase_auth,
    cookies,
    save_auth_cookies,
    sign_in,
) -> None:
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log in", use_container_width=True)

        if not submitted:
            return

        clean_email = email.strip().lower()

        if not clean_email or not password:
            st.error("Please enter both email and password.")
            return

        try:
            auth_response = sign_in(
                supabase_auth,
                email=clean_email,
                password=password,
            )

            st.session_state.session = auth_response.get("session")
            st.session_state.user = auth_response.get("user")
            save_auth_cookies(cookies, auth_response)

            st.success("Logged in successfully.")
            st.rerun()

        except Exception as exc:
            error_msg = str(exc).lower()

            if "email_not_confirmed" in error_msg or "email not confirmed" in error_msg:
                st.error(
                    "Please confirm your email before logging in. Check your inbox, or use the resend option below."
                )
            elif "invalid login credentials" in error_msg:
                st.error("Incorrect email or password.")
            else:
                st.error(f"Login failed: {exc}")


def _handle_resend_confirmation(
    supabase_auth,
    resend_signup_confirmation,
    settings,
) -> None:
    st.markdown("---")
    st.markdown("**Didn't get the confirmation email?**")

    if "show_resend_confirmation_form" not in st.session_state:
        st.session_state.show_resend_confirmation_form = False

    if not st.session_state.show_resend_confirmation_form:
        if st.button(
            "Click here",
            key="show_resend_confirmation_button",
            type="secondary",
        ):
            st.session_state.show_resend_confirmation_form = True
            st.rerun()

    if not st.session_state.show_resend_confirmation_form:
        return

    with st.form("resend_confirmation_form"):
        resend_email = st.text_input(
            "Email for confirmation link",
            key="resend_email",
        )
        resend_submitted = st.form_submit_button(
            "Resend confirmation email",
            use_container_width=True,
        )

        if not resend_submitted:
            return

        clean_email = resend_email.strip().lower()

        if not clean_email:
            st.error("Please enter your email address.")
            return

        try:
            resend_signup_confirmation(
                supabase_auth,
                email=clean_email,
                email_redirect_to=settings.app_base_url,
            )
            st.success("Confirmation email sent. Please check your inbox.")
        except Exception as exc:
            error_msg = str(exc).lower()

            if "over_email_send_rate_limit" in error_msg:
                st.error(
                    "Too many emails were sent recently. Please wait a little and try again."
                )
            elif "user not found" in error_msg:
                st.error("We could not find an account with that email address.")
            else:
                st.error(f"Could not resend confirmation email: {exc}")


def _handle_signup(
    supabase_auth,
    supabase_admin,
    ensure_user_profile,
    sign_up,
    settings,
) -> None:
    with st.form("signup_form"):
        username = st.text_input("Username", key="signup_username")
        email = st.text_input("Email", key="signup_email")
        password = st.text_input(
            "Password",
            type="password",
            key="signup_password",
        )
        confirm_password = st.text_input(
            "Confirm Password",
            type="password",
            key="signup_confirm_password",
        )

        submitted = st.form_submit_button(
            "Create account",
            use_container_width=True,
        )

        if not submitted:
            return

        clean_username = username.strip()
        clean_email = email.strip().lower()

        if not clean_username:
            st.error("Please enter a username.")
            return

        if len(clean_username) < 3:
            st.error("Username must be at least 3 characters long.")
            return

        if not clean_email:
            st.error("Please enter an email address.")
            return

        if not password:
            st.error("Please enter a password.")
            return

        if len(password) < 8:
            st.error("Password must be at least 8 characters long.")
            return

        if not confirm_password:
            st.error("Please confirm your password.")
            return

        if password != confirm_password:
            st.error("Passwords do not match.")
            return

        try:
            auth_response = sign_up(
                supabase_auth,
                email=clean_email,
                password=password,
                username=clean_username,
                email_redirect_to=settings.app_base_url,
            )

            created_user = auth_response.get("user")

            if created_user:
                ensure_user_profile(
                    supabase_admin,
                    created_user["id"],
                    created_user.get("email", clean_email),
                    clean_username,
                )

            st.success(
                "Your account has been created successfully. Please check your email to confirm your address before logging in."
            )
            st.info(
                "If you do not receive the confirmation email right away, use the resend confirmation option in the Log In tab."
            )

        except Exception as exc:
            error_msg = str(exc).lower()

            if "over_email_send_rate_limit" in error_msg or "email rate limit" in error_msg:
                st.warning(
                    "Your account may have been created, but the confirmation email could not be sent yet because the email sending limit was reached. Please wait a little, then use the resend confirmation option in the Log In tab."
                )
            elif "user already registered" in error_msg:
                st.error("This email is already registered. Please log in or confirm your email.")
            elif "password should be at least" in error_msg:
                st.error("Password must be at least 8 characters long.")
            else:
                st.error(f"Sign up failed: {exc}")


def _handle_password_reset(
    supabase_auth,
    reset_password_for_email,
    settings,
) -> None:
    with st.form("forgot_password_form"):
        reset_email = st.text_input("Email", key="reset_email")
        reset_submitted = st.form_submit_button(
            "Send password reset email",
            use_container_width=True,
        )

        if not reset_submitted:
            return

        clean_email = reset_email.strip().lower()

        if not clean_email:
            st.error("Please enter your email address.")
            return

        try:
            reset_password_for_email(
                supabase_auth,
                clean_email,
                redirect_to=_with_query_param(
                    settings.app_base_url,
                    "mode",
                    "reset",
                ),
            )
            st.success("Password reset email sent. Please check your inbox.")
            st.info(
                "If the link opens the reset page but does not complete the password change yet, you can keep this feature hidden for now while the rest of the app remains fully usable."
            )
        except Exception as exc:
            error_msg = str(exc).lower()

            if "error sending recovery email" in error_msg:
                st.error(
                    "Supabase could not send the recovery email. Check that APP_BASE_URL is your live app URL and that the same URL is added in Supabase Authentication redirect settings."
                )
            elif "over_email_send_rate_limit" in error_msg:
                st.error(
                    "Too many reset emails were requested recently. Please wait a little and try again."
                )
            else:
                st.error(f"Could not send reset email: {exc}")


def auth_panel(
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
) -> None:
    st.markdown(
        "<div class='main-title'>🎓 Smart Prompt Helper</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div class='subtitle'>Generate clear, structured, high-quality prompts for academic and professional work.</div>",
        unsafe_allow_html=True,
    )

    _show_auth_link_message()

    login_tab, signup_tab, reset_tab = st.tabs(
        ["Log In", "Create Account", "Forgot Password"]
    )

    with login_tab:
        _handle_login(
            supabase_auth,
            cookies,
            save_auth_cookies,
            sign_in,
        )
        _handle_resend_confirmation(
            supabase_auth,
            resend_signup_confirmation,
            settings,
        )

    with signup_tab:
        _handle_signup(
            supabase_auth,
            supabase_admin,
            ensure_user_profile,
            sign_up,
            settings,
        )

    with reset_tab:
        _handle_password_reset(
            supabase_auth,
            reset_password_for_email,
            settings,
        )