import streamlit as st

from services.auth import create_supabase_admin_client, create_supabase_auth_client, sign_in, sign_out, sign_up
from services.billing import BillingService, update_plan
from services.config import get_settings, validate_settings
from services.prompt_service import PromptGenerator
from services.usage import (
    ensure_user_profile,
    get_daily_prompt_count,
    get_user_profile,
    increment_daily_prompt_count,
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

        .soft-card {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.10);
            border-radius: 18px;
            padding: 1.15rem;
            margin-bottom: 1rem;
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

        div[data-testid="stButton"] > button,
        div[data-testid="stDownloadButton"] > button {
            border-radius: 12px;
            font-weight: 600;
            min-height: 44px;
        }

        [data-testid="stToolbar"] {
            visibility: hidden;
        }

        @media (max-width: 640px) {
            .main-title {
                font-size: 1.95rem;
            }

            .subtitle {
                font-size: 0.96rem;
            }

            .soft-card {
                padding: 0.9rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def auth_panel() -> None:
    st.markdown("<div class='main-title'>🎓 Smart Prompt Helper</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='subtitle'>Turn your ideas into high-quality AI prompts instantly.</div>",
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
        ("Free", "5 prompts/day", None),
        ("Pro", "Higher usage + faster support", settings.stripe_price_pro),
        ("Premium", "Unlimited-style workflow", settings.stripe_price_premium),
    ]

    cols = st.columns(3)

    for idx, (plan_name, desc, price_id) in enumerate(plans):
        with cols[idx]:
            with st.container():
                st.markdown(f"**{plan_name}**")
                st.caption(desc)
                plan_key = plan_name.lower()

                if plan_key == "free":
                    if st.button("Switch to Free", key="switch_free", use_container_width=True):
                        update_plan(supabase_admin, user["id"], "free")
                        st.success("Plan updated to Free.")
                        st.rerun()
                else:
                    if st.button(f"Upgrade to {plan_name}", key=f"upgrade_{plan_key}", use_container_width=True):
                        try:
                            session = billing_service.create_checkout_session(
                                customer_email=user["email"],
                                plan=plan_key,
                                success_url=f"{settings.app_base_url}?checkout=success",
                                cancel_url=f"{settings.app_base_url}?checkout=cancel",
                                price_id=price_id,
                                user_id=user["id"],
                            )
                            st.link_button(f"Continue to {plan_name}", session.url, use_container_width=True)
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

    try:
        usage_today = get_daily_prompt_count(supabase_admin, user["id"])
    except Exception as exc:
        st.error(f"Usage lookup failed: {exc}")
        st.stop()

    current_plan = (profile.get("plan") or "free").lower()

    st.markdown("<div class='main-title'>🎓 Smart Prompt Helper</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='subtitle'>Turn your ideas into high-quality AI prompts instantly.</div>",
        unsafe_allow_html=True,
    )

    st.markdown("<div class='soft-card'>", unsafe_allow_html=True)
    st.write(f"Signed in as **{user.get('email', 'unknown')}**")
    st.markdown(
        f"<span class='plan-chip'>Plan: {current_plan.title()}</span>",
        unsafe_allow_html=True,
    )
    if current_plan == "free":
        st.write(f"Daily usage: **{usage_today}/{settings.free_daily_prompt_limit} prompts**")

    if st.button("Log out"):
        sign_out(supabase_auth)
        st.session_state.session = None
        st.session_state.user = None
        st.session_state.generated_prompt = ""
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    with st.expander("ℹ️ How to use"):
        st.markdown(
            """
**1.** Choose whether this is for a **Student** or **Researcher**  
**2.** Select the task you need  
**3.** Paste your topic, notes, paragraph, or abstract  
**4.** Click **Generate Prompt**  
**5.** Copy the result into ChatGPT or another AI tool
"""
        )

    st.markdown("<div class='section-title'>✨ Generate Your Prompt</div>", unsafe_allow_html=True)

    student_tasks = ["Explain a topic", "Summarize notes", "Make quiz questions", "Improve writing"]
    research_tasks = ["Summarize a paper", "Improve academic writing", "Generate research questions"]

    mode = st.selectbox("Who is this for?", ["Student", "Researcher"])

    if mode == "Student":
        task_name = st.selectbox("What do you need help with?", student_tasks)
        level = st.selectbox("Student level", ["Middle School", "High School", "College"])
        user_text = st.text_area(
            "📄 Your content",
            height=180,
            placeholder="Example: Explain photosynthesis for a high school student",
        )
    else:
        task_name = st.selectbox("What do you need help with?", research_tasks)
        level = None
        user_text = st.text_area(
            "📄 Your content",
            height=180,
            placeholder="Example: Generate research questions about telemedicine in rural healthcare",
        )

    st.markdown(
        "<div class='tip'>Tip: The more specific your input, the better your prompt will be.</div>",
        unsafe_allow_html=True,
    )

    if st.button("✨ Generate Prompt", use_container_width=True):
        if not user_text.strip():
            st.error("Please enter some text first.")
        elif current_plan == "free" and usage_today >= settings.free_daily_prompt_limit:
            st.warning("You reached the daily free limit. Upgrade to Pro or Premium to continue.")
        else:
            with st.spinner("Generating your prompt..."):
                try:
                    final_prompt = prompt_generator.generate(mode, task_name, user_text, level)
                    increment_daily_prompt_count(supabase_admin, user["id"])
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