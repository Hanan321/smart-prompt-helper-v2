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
        "<div class='subtitle'>AI prompt support for academic writing, research, and higher education.</div>",
        unsafe_allow_html=True,
    )

    # -----------------------------
    # Handle URL messages properly
    # -----------------------------
    query_params = st.query_params
    error = query_params.get("error")
    error_code = query_params.get("error_code")
    flow_type = query_params.get("type")

    auth_message = None
    show_resend = True

    if error or error_code:
        error_text = f"{error} {error_code}".lower()

        if "otp_expired" in error_text:
            auth_message = ("warning", "This confirmation link has expired. Please request a new one below.")
        elif "access_denied" in error_text:
            auth_message = ("warning", "This confirmation link is invalid or has already been used.")
        else:
            auth_message = ("warning", "There was an issue with the authentication link.")

    elif flow_type == "signup":
        auth_message = ("info", "Please confirm your email using the link sent to your inbox.")

    if auth_message:
        level, message = auth_message

        if level == "success":
            st.success(message)
        elif level == "warning":
            st.warning(message)
        else:
            st.info(message)

    # -----------------------------
    # Tabs
    # -----------------------------
    login_tab, signup_tab, reset_tab = st.tabs(["Log In", "Create Account", "Forgot Password"])

    # -----------------------------
    # LOGIN
    # -----------------------------
    with login_tab:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Log in", use_container_width=True)

            if submitted:
                if not email.strip() or not password:
                    st.error("Please enter both email and password.")
                else:
                    try:
                        auth_response = sign_in(
                            supabase_auth,
                            email=email.strip(),
                            password=password,
                        )

                        st.session_state.session = auth_response.get("session")
                        st.session_state.user = auth_response.get("user")

                        save_auth_cookies(cookies, auth_response)

                        st.success("Logged in successfully.")
                        st.rerun()

                    except Exception as exc:
                        error_msg = str(exc).lower()

                        if "email_not_confirmed" in error_msg:
                            st.error("Please confirm your email before logging in. Check your inbox.")
                        else:
                            st.error("Login failed. Please check your credentials.")

        # Resend confirmation
        if show_resend:
            st.markdown("---")
            st.markdown("**Didn't get the confirmation email?**")

            with st.form("resend_confirmation_form"):
                resend_email = st.text_input("Email for confirmation link", key="resend_email")
                resend_submitted = st.form_submit_button(
                    "Resend confirmation email",
                    use_container_width=True,
                )

                if resend_submitted:
                    clean_email = resend_email.strip()

                    if not clean_email:
                        st.error("Please enter your email address.")
                    else:
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
                                st.error("Too many emails sent. Please wait and try again.")
                            else:
                                st.error(f"Could not resend email: {exc}")

    # -----------------------------
    # SIGN UP
    # -----------------------------
    with signup_tab:
        with st.form("signup_form"):
            username = st.text_input("Username")
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")

            submitted = st.form_submit_button("Create account", use_container_width=True)

            if submitted:
                username = username.strip()
                email = email.strip()

                if not username:
                    st.error("Please enter a username.")
                elif len(username) < 3:
                    st.error("Username must be at least 3 characters.")
                elif not email:
                    st.error("Please enter an email.")
                elif not password:
                    st.error("Please enter a password.")
                elif len(password) < 8:
                    st.error("Password must be at least 8 characters.")
                elif password != confirm_password:
                    st.error("Passwords do not match.")
                else:
                    try:
                        auth_response = sign_up(
                            supabase_auth,
                            email=email,
                            password=password,
                            username=username,
                            email_redirect_to=settings.app_base_url,
                        )

                        created_user = auth_response.get("user")

                        if created_user:
                            ensure_user_profile(
                                supabase_admin,
                                created_user["id"],
                                created_user.get("email", email),
                                username,
                            )

                        st.success("Account created. Please check your email to confirm your account.")

                    except Exception as exc:
                        st.error(f"Sign up failed: {exc}")

    # -----------------------------
    # RESET PASSWORD
    # -----------------------------
    with reset_tab:
        with st.form("forgot_password_form"):
            reset_email = st.text_input("Email")
            submitted = st.form_submit_button("Send password reset email", use_container_width=True)

            if submitted:
                email = reset_email.strip()

                if not email:
                    st.error("Please enter your email.")
                else:
                    try:
                        reset_password_for_email(
                            supabase_auth,
                            email=email,
                            redirect_to=settings.app_base_url,
                        )
                        st.success("Password reset email sent.")
                    except Exception as exc:
                        st.error(f"Could not send reset email: {exc}")