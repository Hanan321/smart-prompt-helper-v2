import streamlit as st


def subscription_panel(
    profile: dict,
    user: dict,
    billing_service,
    admin_client,
    settings,
) -> None:
    current_plan = (profile.get("plan") or "free").lower()
    customer_id = profile.get("stripe_customer_id")
    subscription_id = profile.get("stripe_subscription_id")
    subscription_status = (profile.get("subscription_status") or "").lower()
    cancel_at_period_end = bool(profile.get("cancel_at_period_end", False))
    billing_period_end = profile.get("billing_period_end")
    monthly_used = int(profile.get("monthly_prompts_used", 0) or 0)
    monthly_limit = int(profile.get("monthly_prompt_limit", 0) or 0)
    credit_balance = int(profile.get("credit_balance", 0) or 0)
    total_credits_purchased = int(profile.get("total_credits_purchased", 0) or 0)
    app_env = getattr(settings, "app_env", "live")
    is_test_mode = app_env == "test"
    free_prompt_limit = int(
        profile.get(
            "free_prompt_limit",
            getattr(settings, "test_free_total_prompt_limit", 2)
            if is_test_mode
            else getattr(settings, "free_total_prompt_limit", 5),
        )
    )

    is_real_stripe_subscription = bool(customer_id and subscription_id)

    st.markdown("<div class='section-title'>💳 Plan & Billing</div>", unsafe_allow_html=True)
    st.markdown(
        f"<span class='plan-chip'>Current plan: {current_plan.title()}</span>",
        unsafe_allow_html=True,
    )
    if is_test_mode:
        st.caption(
            f"One-time credits: {credit_balance} prompts available. These credits never expire."
        )
        if total_credits_purchased > 0:
            st.caption(f"Total one-time credits purchased: {total_credits_purchased} prompts.")

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
        if is_test_mode and credit_balance > 0:
            st.info(
                f"You are currently on the Free plan with {credit_balance} purchased prompt credits available."
            )
        else:
            st.info("You are currently on the Free plan. Upgrade anytime for more prompts.")

    plans = [
        {
            "name": "Free Trial",
            "price": "$0",
            "desc": f"{free_prompt_limit} prompts total to test the app",
            "kind": "free",
            "price_id": None,
        },
    ]
    if is_test_mode:
        plans.append(
            {
                "name": "Prompt Pack",
                "price": "$5",
                "desc": "10 one-time prompt credits. Credits accumulate and do not expire.",
                "kind": "pack",
                "price_id": getattr(
                    getattr(settings, "billing_config", None),
                    "stripe_price_pack_10",
                    getattr(settings, "stripe_price_pack_10", ""),
                ),
            }
        )
    plans.append(
        {
            "name": "Pro",
            "price": "$20/month",
            "desc": "Up to 200 prompts per month. Monthly prompts reset each billing cycle.",
            "kind": "pro",
            "price_id": getattr(
                getattr(settings, "billing_config", None),
                "stripe_price_pro",
                settings.stripe_price_pro,
            ),
        }
    )

    cols = st.columns(len(plans))

    for idx, plan in enumerate(plans):
        plan_name = plan["name"]
        price_label = plan["price"]
        desc = plan["desc"]
        price_id = plan["price_id"]
        kind = plan["kind"]
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

                if kind == "free":
                    st.caption(f"Includes {free_prompt_limit} total prompts to test the app.")
                elif kind == "pack":
                    st.caption(
                        f"One-time credits available: {credit_balance}. They never expire."
                    )
                    if st.button(
                        "Buy 10 prompts",
                        type="secondary",
                        use_container_width=True,
                    ):
                        try:
                            checkout_session = billing_service.create_prompt_pack_checkout_session(
                                customer_email=user.get("email"),
                                success_url=settings.app_base_url,
                                cancel_url=settings.app_base_url,
                                price_id=price_id,
                                user_id=user["id"],
                                admin_client=admin_client,
                                stripe_customer_id=customer_id,
                            )
                            st.link_button(
                                "Continue to secure checkout",
                                checkout_session.url,
                                type="primary",
                                use_container_width=True,
                            )
                        except Exception as exc:
                            st.error(f"Could not start checkout: {exc}")
                else:
                    if current_plan == "pro":
                        if is_real_stripe_subscription:
                            st.caption("You are currently on the Pro plan.")
                        else:
                            st.caption("This is a test Pro account.")
                    else:
                        if st.button(
                            "Upgrade to Pro",
                            type="primary",
                            use_container_width=True,
                        ):
                            try:
                                checkout_session = billing_service.create_checkout_session(
                                    customer_email=user.get("email"),
                                    plan="pro",
                                    success_url=settings.app_base_url,
                                    cancel_url=settings.app_base_url,
                                    price_id=price_id,
                                    user_id=user["id"],
                                    admin_client=admin_client,
                                    stripe_customer_id=customer_id,
                                )
                                st.link_button(
                                    "Continue to secure checkout",
                                    checkout_session.url,
                                    type="primary",
                                    use_container_width=True,
                                )
                            except Exception as exc:
                                st.error(f"Could not start checkout: {exc}")

    st.markdown("---")
    st.markdown("**Manage subscription**")

    if current_plan == "pro":
        if is_real_stripe_subscription:
            st.caption(
                "Subscription changes are available from your user profile."
            )
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
