import streamlit as st


def account_summary_panel(
    display_name: str,
    user: dict,
    current_plan: str,
    total_used: int,
    monthly_used: int,
    monthly_limit: int,
    supabase_auth,
    cookies,
    clear_auth_cookies,
) -> None:
    with st.container(border=True):
        st.write(f"Signed in as **{display_name}**")
        st.caption(user.get("email", "unknown"))
        st.markdown(
            f"<span class='plan-chip'>Plan: {current_plan.title()}</span>",
            unsafe_allow_html=True,
        )

        if current_plan == "free":
            st.write(f"Free trial usage: **{total_used}/3 prompts**")
        else:
            if monthly_limit > 0:
                st.write(f"Monthly usage: **{monthly_used}/{monthly_limit} prompts**")
            else:
                st.write(f"Monthly usage: **{monthly_used} prompts used**")

        if st.button("Log out", type="primary", use_container_width=True):
            try:
                supabase_auth.auth.sign_out()
            except Exception:
                pass

            clear_auth_cookies(cookies)
            st.session_state.show_welcome = True
            st.session_state.session = None
            st.session_state.user = None
            st.session_state.generated_prompt = ""
            st.session_state.auth_restored = False

            st.rerun()
