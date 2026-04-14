import streamlit as st


def subscription_panel(profile: dict, user: dict, billing_service, settings) -> None:
    current_plan = (profile.get("plan") or "free").lower()

    st.markdown("<div class='section-title'>💳 Plan & Billing</div>", unsafe_allow_html=True)
    st.markdown(
        f"<span class='plan-chip'>Current plan: {current_plan.title()}</span>",
        unsafe_allow_html=True,
    )

    plans = [
        ("Free Trial", "$0", "5 prompts total to test the app", None),
        (
            "Pro",
            "$20/month",
            "Up to 200 prompts per month for academic and research workflows",
            settings.stripe_price_pro,
        ),
    ]

    cols = st.columns(2)

    for idx, (plan_name, price_label, desc, price_id) in enumerate(plans):
        with cols[idx]:
            with st.container(border=True):
                st.markdown(f"**{plan_name}**")
                st.markdown(f"<div class='price-text'>{price_label}</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='price-subtext'>{desc}</div>", unsafe_allow_html=True)

                if plan_name == "Free Trial":
                    st.caption("Free plan includes 5 total prompts to try the app.")
                else:
                    if current_plan == "pro":
                        st.caption("You are currently on the Pro plan.")
                    else:
                        if st.button(
                            "Upgrade to Pro",
                            key="upgrade_pro",
                            type="primary",
                            use_container_width=True,
                        ):
                            try:
                                session = billing_service.create_checkout_session(
                                    customer_email=user["email"],
                                    plan="pro",
                                    success_url=f"{settings.app_base_url}?checkout=success",
                                    cancel_url=f"{settings.app_base_url}?checkout=cancel",
                                    price_id=price_id,
                                    user_id=user["id"],
                                )
                                st.link_button(
                                    "Continue to Pro checkout",
                                    session.url,
                                    use_container_width=True,
                                )
                            except Exception as exc:
                                st.error(f"Could not create checkout session: {exc}")

    customer_id = profile.get("stripe_customer_id")
    if customer_id:
        st.markdown("")
        if st.button("Manage billing portal", type="primary", use_container_width=True):
            try:
                portal = billing_service.create_billing_portal_session(
                    customer_id,
                    settings.app_base_url,
                )
                st.link_button(
                    "Open Stripe billing portal",
                    portal.url,
                    use_container_width=True,
                )
            except Exception as exc:
                st.error(f"Could not open billing portal: {exc}")
