import streamlit as st


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
    st.markdown("<div class='main-title'>🎓 Smart Prompt Helper</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='subtitle'>Generate clear, structured, high-quality prompts for academic and professional work.</div>",
        unsafe_allow_html=True,
    )

    st.link_button("← Back to Home", settings.home_url)

    query_params = st.query_params
    error = query_params.get("error")
    error_code = query_params.get("error_code")

    auth_message = None
    show_resend = True

    # Show only real auth-link errors from the URL
    if error or error_code:
        error_text = f"{error} {error_code}".lower()

        if "otp_expired" in error_text:
            auth_message = (
                "warning",
                "This confirmation link has expired. Please request a new one below.",
            )
        elif "access_denied" in error_text:
            auth_message = (
                "warning",
                "This confirmation link is invalid or has already been used.",
            )
        else:
            auth_message = (
                "warning",
                "There was an issue with the authentication link.",
            )

    if auth_message:
        level, message = auth_message
        if level == "warning":
            st.warning(message)
        else:
            st.info(message)

    login_tab, signup_tab, reset_tab = st.tabs(
        ["Log In", "Create Account", "Forgot Password"]
    )

    with login_tab:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Log in", use_container_width=True)

            if submitted:
                clean_email = email.strip().lower()

                if not clean_email or not password:
                    st.error("Please enter both email and password.")
                else:
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

                        if (
                            "email_not_confirmed" in error_msg
                            or "email not confirmed" in error_msg
                        ):
                            st.error(
                                "Please confirm your email before logging in. Check your inbox, or use the resend option below."
                            )
                        elif "invalid login credentials" in error_msg:
                            st.error("Incorrect email or password.")
                        else:
                            st.error("Login failed. Please check your credentials.")

        if show_resend:
            st.markdown("---")
            st.markdown("**Didn't get the confirmation email?**")

            with st.form("resend_confirmation_form"):
                resend_email = st.text_input(
                    "Email for confirmation link",
                    key="resend_email",
                )
                resend_submitted = st.form_submit_button(
                    "Resend confirmation email",
                    use_container_width=True,
                )

                if resend_submitted:
                    clean_email = resend_email.strip().lower()

                    if not clean_email:
                        st.error("Please enter your email address.")
                    else:
                        try:
                            resend_signup_confirmation(
                                supabase_auth,
                                email=clean_email,
                                email_redirect_to=settings.app_base_url,
                            )
                            st.success(
                                "Confirmation email sent. Please check your inbox."
                            )
                        except Exception as exc:
                            error_msg = str(exc).lower()

                            if "over_email_send_rate_limit" in error_msg:
                                st.error(
                                    "Too many emails were sent recently. Please wait a little and try again."
                                )
                            elif "user not found" in error_msg:
                                st.error(
                                    "We could not find an account with that email address."
                                )
                            else:
                                st.error(
                                    f"Could not resend confirmation email: {exc}"
                                )

    with signup_tab:
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

            if submitted:
                clean_username = username.strip()
                clean_email = email.strip().lower()

                if not clean_username:
                    st.error("Please enter a username.")
                elif len(clean_username) < 3:
                    st.error("Username must be at least 3 characters long.")
                elif not clean_email:
                    st.error("Please enter an email address.")
                elif not password:
                    st.error("Please enter a password.")
                elif len(password) < 8:
                    st.error("Password must be at least 8 characters long.")
                elif not confirm_password:
                    st.error("Please confirm your password.")
                elif password != confirm_password:
                    st.error("Passwords do not match.")
                else:
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

                        if (
                            "over_email_send_rate_limit" in error_msg
                            or "email rate limit" in error_msg
                        ):
                            st.warning(
                                "Your account may have been created, but the confirmation email could not be sent yet because the email sending limit was reached. "
                                "Please wait a little, then use the resend confirmation option in the Log In tab."
                            )
                        elif "user already registered" in error_msg:
                            st.error(
                                "This email is already registered. Please log in or confirm your email."
                            )
                        elif "password should be at least" in error_msg:
                            st.error("Password must be at least 8 characters long.")
                        else:
                            st.error(f"Sign up failed: {exc}")

    with reset_tab:
        with st.form("forgot_password_form"):
            reset_email = st.text_input("Email", key="reset_email")
            reset_submitted = st.form_submit_button(
                "Send password reset email",
                use_container_width=True,
            )

            if reset_submitted:
                clean_email = reset_email.strip().lower()

                if not clean_email:
                    st.error("Please enter your email address.")
                else:
                    try:
                        reset_password_for_email(
                            supabase_auth,
                            email=clean_email,
                            redirect_to=settings.app_base_url,
                        )
                        st.success(
                            "Password reset email sent. Please check your inbox."
                        )
                    except Exception as exc:
                        st.error(f"Could not send reset email: {exc}")
    
