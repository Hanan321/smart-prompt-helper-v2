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
                try:
                    auth_response = sign_in(supabase_auth, email=email, password=password)
                    st.session_state.session = auth_response.get("session")
                    st.session_state.user = auth_response.get("user")
                    save_auth_cookies(cookies, auth_response)
                    st.success("Logged in successfully.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Login failed: {exc}")

    with signup_tab:
        with st.form("signup_form"):
            email = st.text_input("Email", key="signup_email")
            password = st.text_input("Password", type="password", key="signup_password")
            submitted = st.form_submit_button("Create account", use_container_width=True)

            if submitted:
                try:
                    auth_response = sign_up(supabase_auth, email=email, password=password)
                    created_user = auth_response.get("user")

                    if created_user:
                        ensure_user_profile(
                            supabase_admin,
                            created_user["id"],
                            created_user.get("email", email),
                        )

                    st.success("Account created. Check your email if confirmation is enabled.")
                except Exception as exc:
                    st.error(f"Sign up failed: {exc}")