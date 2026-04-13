import streamlit as st


def prompt_form_panel(
    user: dict,
    supabase_admin,
    prompt_generator,
    can_generate_prompt,
    increment_prompt_count,
) -> None:

    # -----------------------------
    # Header
    # -----------------------------
    st.markdown("<div class='section-title'>✨ Generate Your Prompt</div>", unsafe_allow_html=True)

    st.markdown(
        "<div class='subtitle'>Turn your idea into a high-quality AI prompt in seconds.</div>",
        unsafe_allow_html=True,
    )

    # -----------------------------
    # How to use (collapsed help)
    # -----------------------------
    with st.expander("ℹ️ How it works"):
        st.markdown(
            """
**1.** Choose who this is for  
**2.** Select the kind of help you need  
**3.** Enter your topic, notes, or idea  
**4.** Click **Generate Prompt**  
**5.** Copy and use it in ChatGPT or another AI tool  
"""
        )

    st.divider()

    # -----------------------------
    # Task options
    # -----------------------------
    task_map = {
        "Undergraduate": [
            "Explain a topic",
            "Summarize notes",
            "Make quiz questions",
            "Improve writing",
            "Write an essay",
            "Generate study guide",
            "Create presentation outline",
            "Other / Something else",
        ],
        "Graduate": [
            "Summarize a research paper",
            "Improve academic writing",
            "Generate research questions",
            "Turn notes into a structured academic outline",
            "Write an essay",
            "Generate study guide",
            "Create presentation outline",
            "Other / Something else",
        ],
        "Researcher / Professional": [
            "Summarize a research paper",
            "Improve academic writing",
            "Generate research questions",
            "Refine a literature review",
            "Rewrite for clarity, formality, and precision",
            "Write an essay",
            "Generate study guide",
            "Create presentation outline",
            "Other / Something else",
        ],
    }

    placeholder_map = {
        "Undergraduate": "Example: biology summary, explain photosynthesis, improve my paragraph",
        "Graduate": "Example: summarize this abstract, improve discussion section, research questions on addiction",
        "Researcher / Professional": "Example: refine literature review, rewrite for journal tone, outline presentation",
    }

    # -----------------------------
    # Audience & Task
    # -----------------------------
    col1, col2 = st.columns(2)

    with col1:
        audience = st.selectbox("Who is this for?", list(task_map.keys()))

    with col2:
        task_name = st.selectbox("What do you need help with?", task_map[audience])

    # -----------------------------
    # Custom task (only for "Other")
    # -----------------------------
    if task_name == "Other / Something else":
        custom_task = st.text_input(
            "Describe what you need",
            placeholder="Example: Write an introduction, create flashcards, analyze data...",
        )
        st.info("Even a short request works — the app will build a strong prompt for you.")
    else:
        custom_task = task_name

    # -----------------------------
    # Input guidance
    # -----------------------------
    if task_name == "Other / Something else":
        st.caption("Optional: add extra details below if you have them.")
    else:
        st.caption("Required: please provide content for this task.")

    # -----------------------------
    # Main input
    # -----------------------------
    user_text = st.text_area(
        "📄 Topic, notes, or text",
        height=180,
        placeholder=placeholder_map[audience],
    )

    st.caption(
        "You can paste full notes, a paragraph, or just a few words like 'biology summary' or 'fix grammar'."
    )

    clean_user_text = user_text.strip()

    if clean_user_text and len(clean_user_text) < 8:
        st.info("Short input is okay — the app will expand it into a strong prompt.")

    # -----------------------------
    # Smart tips
    # -----------------------------
    if audience == "Undergraduate":
        tip_text = "Tip: Adding the course topic can improve results, but it's optional."
    elif audience == "Graduate":
        tip_text = "Tip: Include subject area or assignment goal for more precise output."
    else:
        tip_text = "Tip: Include discipline or research goal for best results."

    st.markdown(f"<div class='tip'>{tip_text}</div>", unsafe_allow_html=True)

    st.divider()

    # -----------------------------
    # Generate button
    # -----------------------------
    if st.button("✨ Generate Prompt", use_container_width=True):

        final_task = custom_task.strip() if isinstance(custom_task, str) else ""

        if task_name == "Other / Something else":
            if not final_task:
                st.error("Please describe what you need help with.")
                return

            final_input = clean_user_text or final_task

        else:
            if not clean_user_text:
                st.error("Please enter your content for this task.")
                return

            final_input = clean_user_text

        allowed, message = can_generate_prompt(supabase_admin, user["id"])

        if not allowed:
            st.warning(message)
        else:
            with st.spinner("Generating your prompt..."):
                try:
                    final_prompt = prompt_generator.generate(
                        audience,
                        final_task,
                        final_input,
                    )

                    increment_prompt_count(supabase_admin, user["id"])
                    st.session_state.generated_prompt = final_prompt

                    st.success("Your prompt is ready.")

                except Exception as exc:
                    st.error(f"Something went wrong: {exc}")