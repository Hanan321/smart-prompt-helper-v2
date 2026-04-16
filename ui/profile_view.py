from datetime import datetime

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


def _format_billing_date(value: str | None) -> str:
    if not value:
        return "the end of your current billing period"

    try:
        parsed = datetime.fromisoformat(str(value))
        return f"{parsed.strftime('%B')} {parsed.day}, {parsed.year}"
    except ValueError:
        return str(value)


def profile_panel(
    user: dict,
    profile: dict,
    supabase_auth,
    cookies,
    billing_service,
    admin_client,
) -> None:
    display_name = profile.get("username") or user.get("email", "unknown")
    current_plan = (profile.get("plan") or "free").title()
    current_plan_key = (profile.get("plan") or "free").lower()
    customer_id = profile.get("stripe_customer_id")
    subscription_id = profile.get("stripe_subscription_id")
    subscription_status = (profile.get("subscription_status") or "").lower()
    cancel_at_period_end = bool(profile.get("cancel_at_period_end", False))
    billing_period_end = profile.get("billing_period_end")

    if st.button("Back to app", type="primary"):
        st.session_state.page = "app"
        st.rerun()

    st.markdown(
        "<div class='main-title'>User Profile</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div class='subtitle'>Manage your account details, password, and subscription.</div>",
        unsafe_allow_html=True,
    )

    flash_message = st.session_state.pop("profile_billing_message", None)
    if flash_message:
        st.success(flash_message)

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

            if submitted:
                if not new_password:
                    st.error("Please enter a new password.")
                elif len(new_password) < 8:
                    st.error("Password must be at least 8 characters long.")
                elif new_password != confirm_password:
                    st.error("Passwords do not match.")
                elif not _ensure_auth_session(supabase_auth, cookies):
                    st.error(
                        "Your session expired. Please log out, log back in, and try again."
                    )
                else:
                    try:
                        supabase_auth.auth.update_user({"password": new_password})
                        st.success("Password updated successfully.")
                    except Exception as exc:
                        st.error(f"Could not update password: {exc}")

    st.markdown("<div class='section-title'>Subscription</div>", unsafe_allow_html=True)

    with st.container(border=True):
        if current_plan_key != "pro":
            st.caption("You are currently on the Free plan.")
            return

        if not customer_id or not subscription_id:
            st.caption(
                "This Pro account is not connected to a Stripe subscription."
            )
            return

        active_until = _format_billing_date(billing_period_end)

        if cancel_at_period_end:
            st.warning(
                f"Cancellation scheduled. Your plan remains active until {active_until}."
            )
            return

        if subscription_status not in {"active", "trialing"}:
            st.caption(
                "Subscription changes are unavailable while your billing status updates."
            )
            return

        st.caption(
            f"Your Pro plan is active until {active_until}. You can schedule cancellation here."
        )

        if st.button(
            "Cancel Subscription",
            type="secondary",
            use_container_width=True,
        ):
            try:
                billing_service.cancel_subscription_at_period_end(
                    admin_client,
                    user["id"],
                    subscription_id,
                )
                st.session_state.profile_billing_message = (
                    "Your subscription will remain active until the end of your "
                    "current billing period and will not renew after that."
                )
                st.rerun()
            except Exception as exc:
                st.error(f"Could not schedule cancellation: {exc}")
