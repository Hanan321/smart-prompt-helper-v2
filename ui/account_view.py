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
    credit_balance: int = 0,
    free_prompt_limit: int = 5,
) -> None:
    with st.container(border=True):
        profile_col, logout_col = st.columns([1, 1])

        with profile_col:
            if st.button("User Profile", type="primary", use_container_width=True):
                st.session_state.page = "profile"
                st.rerun()

        with logout_col:
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
                st.session_state.page = "home"

                st.rerun()

        st.divider()
        st.write(f"Signed in as **{display_name}**")
        st.markdown(
            f"<span class='plan-chip'>Plan: {current_plan.title()}</span>",
            unsafe_allow_html=True,
        )

        if current_plan == "free":
            st.write(f"Free trial usage: **{total_used}/{free_prompt_limit} prompts**")
            if credit_balance > 0:
                st.write(f"Purchased credits: **{credit_balance} prompts**")
        else:
            if monthly_limit > 0:
                st.write(f"Monthly usage: **{monthly_used}/{monthly_limit} prompts**")
            else:
                st.write(f"Monthly usage: **{monthly_used} prompts used**")
