import streamlit as st


def _ensure_auth_session(supabase_auth, cookies) -> bool:
    session = st.session_state.get("session") or {}
    access_token = session.get("access_token") or cookies.get("access_token")
    refresh_token = session.get("refresh_token") or cookies.get("refresh_token")

    if not access_token or not refresh_token:
        return False

    try:
        session_response = supabase_auth.auth.set_session(access_token, refresh_token)

        if hasattr(session_response, "model_dump"):
            session_response = session_response.model_dump()

        refreshed_session = session_response.get("session", session_response)
        if refreshed_session:
            st.session_state.session = refreshed_session

        return True
    except Exception:
        return False


def profile_panel(user: dict, profile: dict, supabase_auth, cookies) -> None:
    display_name = profile.get("username") or user.get("email", "unknown")
    current_plan = (profile.get("plan") or "free").title()

    if st.button("Back to app", type="primary"):
        st.session_state.page = "app"
        st.rerun()

    st.markdown(
        "<div class='main-title'>User Profile</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div class='subtitle'>Manage your account details and password.</div>",
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        st.markdown("**Account**")
        st.write(f"Name: **{display_name}**")
        st.write(f"Email: **{user.get('email', 'unknown')}**")
        st.markdown(
            f"<span class='plan-chip'>Plan: {current_plan}</span>",
            unsafe_allow_html=True,
        )

    st.markdown("<div class='section-title'>Password</div>", unsafe_allow_html=True)

    with st.container(border=True):
        with st.form("profile_change_password_form"):
            new_password = st.text_input("New password", type="password")
            confirm_password = st.text_input("Confirm new password", type="password")
            submitted = st.form_submit_button(
                "Update password",
                use_container_width=True,
            )

            if not submitted:
                return

            if not new_password:
                st.error("Please enter a new password.")
                return

            if len(new_password) < 8:
                st.error("Password must be at least 8 characters long.")
                return

            if new_password != confirm_password:
                st.error("Passwords do not match.")
                return

            if not _ensure_auth_session(supabase_auth, cookies):
                st.error(
                    "Your session expired. Please log out, log back in, and try again."
                )
                return

            try:
                supabase_auth.auth.update_user({"password": new_password})
                st.success("Password updated successfully.")
            except Exception as exc:
                st.error(f"Could not update password: {exc}")
