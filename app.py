def subscription_panel(profile: dict, user: dict) -> None:
    current_plan = (profile.get("plan") or "free").lower()

    st.markdown("<div class='section-title'>💳 Plan & Billing</div>", unsafe_allow_html=True)
    st.markdown(
        f"<span class='plan-chip'>Current plan: {current_plan.title()}</span>",
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        st.markdown("**Pro**")
        st.markdown("<div class='price-text'>$20/month</div>", unsafe_allow_html=True)
        st.markdown(
            "<div class='price-subtext'>Up to 200 prompts per month for academic and research workflows</div>",
            unsafe_allow_html=True,
        )

        if current_plan == "pro":
            st.button("Current Plan", disabled=True, use_container_width=True)
        else:
            if st.button("Upgrade to Pro", key="upgrade_pro", use_container_width=True):
                try:
                    session = billing_service.create_checkout_session(
                        customer_email=user["email"],
                        plan="pro",
                        success_url=f"{settings.app_base_url}?checkout=success",
                        cancel_url=f"{settings.app_base_url}?checkout=cancel",
                        price_id=settings.stripe_price_pro,
                        user_id=user["id"],
                    )
                    st.link_button("Continue to Pro checkout", session.url, use_container_width=True)
                except Exception as exc:
                    st.error(f"Could not create checkout session: {exc}")

    customer_id = profile.get("stripe_customer_id")
    if customer_id:
        st.markdown("")
        if st.button("Manage billing portal", use_container_width=True):
            try:
                portal = billing_service.create_billing_portal_session(customer_id, settings.app_base_url)
                st.link_button("Open Stripe billing portal", portal.url, use_container_width=True)
            except Exception as exc:
                st.error(f"Could not open billing portal: {exc}")