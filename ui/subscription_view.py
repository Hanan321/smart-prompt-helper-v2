import streamlit as st


def subscription_panel(profile: dict, user: dict, billing_service, settings) -> None:
    current_plan = (profile.get("plan") or "free").lower()
    customer_id = profile.get("stripe_customer_id")
    subscription_id = profile.get("stripe_subscription_id")
    subscription_status = (profile.get("subscription_status") or "").lower()
    cancel_at_period_end = bool(profile.get("cancel_at_period_end", False))
    billing_period_end = profile.get("billing_period_end")
    monthly_used = int(profile.get("monthly_prompts_used", 0) or 0)
    monthly_limit = int(profile.get("monthly_prompt_limit", 0) or 0)

    is_real_stripe_subscription = bool(customer_id and subscription_id)

    st.markdown("<div class='section-title'>💳 Plan & Billing</div>", unsafe_allow_html=True)
    st.markdown(
        f"<span class='plan-chip'>Current plan: {current_plan.title()}</span>",
        unsafe_allow_html=True,
    )

    if current_plan == "pro":
        if monthly_limit > 0:
            remaining = max(monthly_limit - monthly_used, 0)
            st.caption(
                f"Usage this billing period: {monthly_used}/{monthly_limit} prompts used • {remaining} remaining"
            )
        else:
            st.caption(f"Usage this billing period: {monthly_used} prompts used")

        if is_real_stripe_subscription:
            if cancel_at_period_end:
                if billing_period_end:
                    st.warning(
                        f"Your Pro subscription is scheduled to end on {billing_period_end}."
                    )
                else:
                    st.warning(
                        "Your Pro subscription is scheduled to end at the close of the current billing period."
                    )
            elif subscription_status in {"active", "trialing"}:
                if billing_period_end:
                    st.success(
                        f"Your Pro subscription is active. Current billing period ends on {billing_period_end}."
                    )
                else:
                    st.success("Your Pro subscription is active.")
        else:
            st.info(
                "This account is on a test Pro plan without a real Stripe subscription. "
                "Billing portal, cancellation, invoices, and payment updates are only available for real Stripe test or live subscriptions."
            )
    else:
        st.info("You are currently on the Free plan. Upgrade anytime for more monthly prompts.")

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
                st.markdown(
                    f"<div class='price-text'>{price_label}</div>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"<div class='price-subtext'>{desc}</div>",
                    unsafe_allow_html=True,
                )

                if plan_name == "Free Trial":
                    st.caption("Includes 5 total prompts to test the app.")
                else:
                    if current_plan == "pro":
                        if is_real_stripe_subscription:
                            st.caption("You are currently on the Pro plan.")
                        else:
                            st.caption("This is a test Pro account.")
                    else:
                        if st.button(
                            "Upgrade to Pro",
                            key="upgrade_pro",
                            type="primary",
                            use_container_width=True,
                        ):
                            try:
                                # Temporary checkout identity debug lines.
                                st.write("Checkout user email:", user.get("email"))
                                st.write("Checkout user id:", user.get("id"))

                                session = billing_service.create_checkout_session(
                                    customer_email=None,
                                    plan="pro",
                                    success_url=f"{settings.app_base_url}?checkout=success",
                                    cancel_url=f"{settings.app_base_url}?checkout=cancel",
                                    price_id=price_id,
                                    user_id=user["id"],
                                )
                                st.link_button(
                                    "Continue to secure checkout",
                                    session.url,
                                    use_container_width=True,
                                )
                            except Exception as exc:
                                st.error(f"Could not create checkout session: {exc}")

    st.markdown("---")
    st.markdown("**Manage subscription**")

    if current_plan == "pro":
        if is_real_stripe_subscription:
            st.caption(
                "To cancel your subscription, update your payment method, or view invoices, use the Stripe billing portal below."
            )

            if st.button("Open billing portal", type="primary", use_container_width=True):
                try:
                    portal = billing_service.create_billing_portal_session(
                        customer_id,
                        settings.app_base_url,
                    )
                    st.link_button(
                        "Continue to Stripe billing portal",
                        portal.url,
                        use_container_width=True,
                    )
                except Exception as exc:
                    st.error(f"Could not open billing portal: {exc}")
        else:
            st.caption(
                "This is a manual test Pro account. No Stripe billing tools are attached to it."
            )
    else:
        st.caption(
            "If you upgrade later, billing management will be available through Stripe."
        )

    st.markdown("---")
    st.markdown("**Need help?**")
    st.caption("For billing or account support, contact support@smartprompthelper.com.")
