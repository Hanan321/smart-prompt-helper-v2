import streamlit as st

from services.auth import create_supabase_admin_client, create_supabase_auth_client, sign_in, sign_out, sign_up
from services.billing import BillingService, update_plan
from services.config import get_settings, validate_settings
from services.prompt_service import PromptGenerator
from services.usage import (
    can_generate_prompt,
    ensure_user_profile,
    get_monthly_prompt_count,
    get_monthly_prompt_limit,
    get_total_prompt_count,
    get_user_profile,
    increment_prompt_count,
)

st.set_page_config(page_title="Smart Prompt Helper", page_icon="🎓", layout="centered")

settings = get_settings()
missing_settings = validate_settings(settings)
if missing_settings:
    st.error(f"Missing environment variables: {', '.join(missing_settings)}")
    st.stop()

supabase_auth = create_supabase_auth_client(settings.supabase_url, settings.supabase_anon_key)
supabase_admin = create_supabase_admin_client(settings.supabase_url, settings.supabase_service_role_key)
prompt_generator = PromptGenerator(settings.openai_api_key)
billing_service = BillingService(settings.stripe_secret_key)

if "session" not in st.session_state:
    st.session_state.session = None
if "user" not in st.session_state:
    st.session_state.user = None
if "generated_prompt" not in st.session_state:
    st.session_state.generated_prompt = ""


def render_styles() -> None:
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
            max-width: 900px;
        }

        .main-title {
            text-align: center;
            font-size: 2.5rem;
            font-weight: 800;
            margin-bottom: 0.25rem;
        }

        .subtitle {
            text-align: center;
            color: #8b8f98;
            font-size: 1.05rem;
            margin-bottom: 1.8rem;
        }

        .section-title {
            font-size: 1.25rem;
            font-weight: 700;
            margin-top: 1.2rem;
            margin-bottom: 0.8rem;
        }

        .plan-chip {
            display: inline-block;
            padding: 0.35rem 0.7rem;
            border-radius: 999px;
            background: rgba(86, 120, 255, 0.16);
            color: #9db3ff;
            font-size: 0.85rem;
            font-weight: 700;
            margin-top: 0.35rem;
            margin-bottom: 0.35rem;
        }

        .muted {
            color: #9aa0a6;
            font-size: 0.95rem;
        }

        .tip {
            font-size: 0.93rem;
            color: #8b8f98;
            margin-top: 0.45rem;
            margin-bottom: 0.35rem;
        }

        .prompt-box {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.10);
            border-radius: 16px;
            padding: 0.8rem;
            margin-top: 0.5rem;
            margin-bottom: 0.8rem;
        }

        .price-text {
            font-size: 1.1rem;
            font-weight: 700;
            margin-top: 0.25rem;
            margin-bottom: 0.15rem;
        }

        .price-subtext {
            color: #9aa0a6;
            font-size: 0.9rem;
            margin-bottom: 0.8rem;
        }

        div[data-testid="stButton"] > button,
        div[data-testid="stDownloadButton"] > button,
        div[data-testid="stLinkButton"] > a {
            border-radius: 12px;
            font-weight: 600;
            min-height: 44px;
        }

        [data-testid="stToolbar"] {
            visibility: hidden;
        }

        div[data-testid="stDecoration"] {
            display: none !important;
        }

        header[data-testid="stHeader"] {
            background: transparent !important;
        }

        @media (max-width: 640px) {
            .main-title {
                font-size: 1.95rem;
            }

            .subtitle {
                font-size: 0.96rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def auth_panel() -> None:
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
                    st.success("Logged in.")
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
                        ensure_user_profile(supabase_admin, created_user["id"], created_user.get("email", email))
                    st.success("Account created. Check your email if confirmation is enabled.")
                except Exception as exc:
                    st.error(f"Sign up failed: {exc}")


def subscription_panel(profile: dict, user: dict) -> None:
    current_plan = (profile.get("plan") or "free").lower()

    st.markdown("<div class='section-title'>💳 Plan & Billing</div>", unsafe_allow_html=True)
    st.markdown(
        f"<span class='plan-chip'>Current plan: {current_plan.title()}</span>",
        unsafe_allow_html=True,
    )

    plans = [
        ("Free Trial", "$0", "5 prompts total to test the app", None),
        ("Pro", "$20/month", "Up to 200 prompts per month for academic and research workflows", settings.stripe_price_pro),
    ]

    cols = st.columns(2)

    for idx, (plan_name, price_label, desc, price_id) in enumerate(plans):
        with cols[idx]:
            with st.container(border=True):
                st.markdown(f"**{plan_name}**")
                st.markdown(f"<div class='price-text'>{price_label}</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='price-subtext'>{desc}</div>", unsafe_allow_html=True)

                if plan_name == "Free Trial":
                    if st.button("Switch to Free", key="switch_free", use_container_width=True):
                        update_plan(supabase_admin, user["id"], "free")
                        st.success("Plan updated to Free.")
                        st.rerun()
                else:
                    if st.button("Upgrade to Pro", key="upgrade_pro", use_container_width=True):
                        try:
                            session = billing_service.create_checkout_session(
                                customer_email=user["email"],
                                plan="pro",
                                success_url=f"{settings.app_base_url}?checkout=success",
                                cancel_url=f"{settings.app_base_url}?checkout=cancel",
                                price_id=price_id,
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


def app_panel(user: dict) -> None:
    ensure_user_profile(supabase_admin, user["id"], user.get("email", ""))
    profile = get_user_profile(supabase_admin, user["id"])
    current_plan = (profile.get("plan") or "free").lower()

    total_used = get_total_prompt_count(supabase_admin, user["id"])
    monthly_used = get_monthly_prompt_count(supabase_admin, user["id"])
    monthly_limit = get_monthly_prompt_limit(supabase_admin, user["id"])

    st.markdown("<div class='main-title'>🎓 Smart Prompt Helper</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='subtitle'>AI prompt support for academic writing, research, and higher education.</div>",
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        st.write(f"Signed in as **{user.get('email', 'unknown')}**")
        st.markdown(
            f"<span class='plan-chip'>Plan: {current_plan.title()}</span>",
            unsafe_allow_html=True,
        )

        if current_plan == "free":
            st.write(f"Free trial usage: **{total_used}/5 prompts**")
        else:
            if monthly_limit > 0:
                st.write(f"Monthly usage: **{monthly_used}/{monthly_limit} prompts**")
            else:
                st.write(f"Monthly usage: **{monthly_used} prompts used**")

        if st.button("Log out"):
            sign_out(supabase_auth)
            st.session_state.session = None
            st.session_state.user = None
            st.session_state.generated_prompt = ""
            st.rerun()

    with st.expander("ℹ️ How to use"):
        st.markdown(
            """
**1.** Choose your academic use case  
**2.** Select the task you need  
**3.** Paste your draft, notes, abstract, or research text  
**4.** Click **Generate Prompt**  
**5.** Use the result in ChatGPT or another AI tool
"""
        )

    st.markdown("<div class='section-title'>✨ Generate Your Prompt</div>", unsafe_allow_html=True)

    task_map = {
        "Undergraduate": [
            "Explain a topic",
            "Summarize notes",
            "Make quiz questions",
            "Improve writing",
        ],
        "Graduate": [
            "Summarize a research paper",
            "Improve academic writing",
            "Generate research questions",
            "Turn notes into a structured academic outline",
        ],
        "Researcher / Professional": [
            "Summarize a research paper",
            "Improve academic writing",
            "Generate research questions",
            "Refine a literature review",
            "Rewrite for clarity, formality, and precision",
        ],
    }

    placeholder_map = {
        "Undergraduate": "Example: Paste class notes, a difficult concept, or a draft paragraph you want to improve",
        "Graduate": "Example: Paste an abstract, seminar notes, or a graduate-level academic draft here",
        "Researcher / Professional": "Example: Paste a literature review paragraph, research notes, or manuscript text here",
    }

    audience = st.selectbox("Who is this for?", list(task_map.keys()))
    task_name = st.selectbox("What do you need help with?", task_map[audience])

    user_text = st.text_area(
        "📄 Your content",
        height=180,
        placeholder=placeholder_map[audience],
    )

    if audience == "Undergraduate":
        tip_text = "Tip: Add the course topic or class level so the prompt becomes more useful and easier to follow."
    elif audience == "Graduate":
        tip_text = "Tip: Include the subject area, assignment goal, or expected structure for a stronger academic prompt."
    else:
        tip_text = "Tip: Include your discipline, research goal, or target output to get a stronger result."

    st.markdown(
        f"<div class='tip'>{tip_text}</div>",
        unsafe_allow_html=True,
    )

    if st.button("✨ Generate Prompt", use_container_width=True):
        if not user_text.strip():
            st.error("Please enter some text first.")
        else:
            allowed, message = can_generate_prompt(supabase_admin, user["id"])
            if not allowed:
                st.warning(message)
            else:
                with st.spinner("Generating your prompt..."):
                    try:
                        final_prompt = prompt_generator.generate(audience, task_name, user_text, level=None)
                        increment_prompt_count(supabase_admin, user["id"])
                        st.session_state.generated_prompt = final_prompt
                        st.success("Your prompt is ready.")
                    except Exception as exc:
                        st.error(f"Something went wrong: {exc}")

    if st.session_state.generated_prompt:
        st.markdown("### 📌 Your Generated Prompt")
        st.markdown("<div class='prompt-box'>", unsafe_allow_html=True)
        st.code(st.session_state.generated_prompt, language=None)
        st.markdown("</div>", unsafe_allow_html=True)
        st.download_button(
            "Download Prompt",
            data=st.session_state.generated_prompt,
            file_name="generated_prompt.txt",
            mime="text/plain",
            use_container_width=True,
        )
        st.markdown(
            "<div class='muted'>Copy or download this prompt and use it in ChatGPT or another AI tool.</div>",
            unsafe_allow_html=True,
        )

    st.divider()
    subscription_panel(profile, user)


render_styles()

if not st.session_state.user:
    auth_panel()
else:
    app_panel(st.session_state.user)