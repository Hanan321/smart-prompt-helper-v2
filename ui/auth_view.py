import streamlit as st


def auth_panel(
    supabase_auth,
    supabase_admin,
    cookies,
    save_auth_cookies,
    ensure_user_profile,
    sign_in,
    sign_up,
) -> None:
    st.markdown("<div class='main-title'>🎓 Smart Prompt Helper</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='subtitle'>AI prompt support for academic writing, research, and higher education.</div>",
        unsafe_allow_html=True,
    )

    login_tab, signup_tab = st.tabs(["Log In", "Create Account"])

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

                        if "email not confirmed" in error_msg:
                            st.error("Please confirm your email before logging in. Check your inbox.")
                        else:
                            st.error("Login failed. Please check your credentials.")

    with signup_tab:
        with st.form("signup_form"):
            username = st.text_input("Username", key="signup_username")
            email = st.text_input("Email", key="signup_email")
            password = st.text_input("Password", type="password", key="signup_password")
            confirm_password = st.text_input(
                "Confirm Password",
                type="password",
                key="signup_confirm_password",
            )

            submitted = st.form_submit_button("Create account", use_container_width=True)

            if submitted:
                clean_username = username.strip()
                clean_email = email.strip()

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
                            "Account created successfully. Please check your email and confirm your address before logging in."
                        )
                    except Exception as exc:
                        st.error(f"Sign up failed: {exc}")