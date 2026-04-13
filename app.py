import os
from core.cookies_auth import restore_auth_once, save_auth_cookies, clear_auth_cookies
from services.auth import (
    create_supabase_admin_client,
    create_supabase_auth_client,
    sign_in,
    sign_out,
    sign_up,
)
import streamlit as st
from streamlit_cookies_manager_ext import EncryptedCookieManager
from services.billing import BillingService
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
from ui.styles import render_styles
from ui.subscription_view import subscription_panel
#---------------------------------------------------------------------

st.set_page_config(page_title="Smart Prompt Helper", page_icon="🎓", layout="centered")

settings = get_settings()
missing_settings = validate_settings(settings)
if missing_settings:
    st.error(f"Missing environment variables: {', '.join(missing_settings)}")
    st.stop()

cookies = EncryptedCookieManager(
    prefix="smart-prompt-helper/",
    password=os.getenv("COOKIES_PASSWORD", "change-this-in-production"),
)

if not cookies.ready():
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
if "auth_restored" not in st.session_state:
    st.session_state.auth_restored = False


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
                    save_auth_cookies(cookies, auth_response)
                    st.success("Logged in successfully.")
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
                        ensure_user_profile(
                            supabase_admin,
                            created_user["id"],
                            created_user.get("email", email),
                        )

                    st.success("Account created. Check your email if confirmation is enabled.")
                except Exception as exc:
                    st.error(f"Sign up failed: {exc}")


def app_panel(user: dict) -> None:
    if not user or "id" not in user:
        st.error("User session error. Please log in again.")
        st.stop()

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

        if st.button("Log out", use_container_width=True):
            sign_out(supabase_auth)
            clear_auth_cookies(cookies)
            st.session_state.session = None
            st.session_state.user = None
            st.session_state.generated_prompt = ""
            st.session_state.auth_restored = True
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
                        final_prompt = prompt_generator.generate(audience, task_name, user_text)
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
    subscription_panel(profile, user, billing_service, settings)


render_styles()
restore_auth_once(cookies, supabase_auth)

if not st.session_state.user:
    auth_panel()
else:
    app_panel(st.session_state.user)