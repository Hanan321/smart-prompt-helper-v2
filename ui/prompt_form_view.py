import streamlit as st


def prompt_form_panel(
    user: dict,
    supabase_admin,
    prompt_generator,
    can_generate_prompt,
    increment_prompt_count,
) -> None:
    st.markdown("<div class='section-title'>✨ Generate Your Prompt</div>", unsafe_allow_html=True)

    st.markdown(
        "<div class='subtitle'>Transform your topic, notes, or rough idea into a polished prompt ready for AI tools.</div>",
        unsafe_allow_html=True,
    )

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

    school_tasks = [
        "Explain a topic",
        "Summarize notes",
        "Make quiz questions",
        "Improve writing",
        "Write an essay",
        "Generate study guide",
        "Create presentation outline",
        "Other / Something else",
    ]
    advanced_tasks = [
        "Summarize a research paper",
        "Improve academic writing",
        "Generate research questions",
        "Turn notes into a structured academic outline",
        "Write an essay",
        "Generate study guide",
        "Create presentation outline",
        "Other / Something else",
    ]
    researcher_tasks = [
        "Summarize a research paper",
        "Improve academic writing",
        "Generate research questions",
        "Refine a literature review",
        "Rewrite for clarity, formality, and precision",
        "Write an essay",
        "Generate study guide",
        "Create presentation outline",
        "Other / Something else",
    ]

    task_map = {
        "Middle school": school_tasks,
        "High school": school_tasks,
        "University/College": advanced_tasks,
        "Researchers": researcher_tasks,
        "Higher education level": [
            "Explain a topic",
            "Summarize notes",
            "Summarize a research paper",
            "Improve academic writing",
            "Generate research questions",
            "Turn notes into a structured academic outline",
            "Write an essay",
            "Generate study guide",
            "Create presentation outline",
            "Other / Something else",
        ],
    }

    placeholder_map = {
        "Middle school": "Example: explain photosynthesis, summarize my science notes, make practice questions",
        "High school": "Example: biology summary, improve my essay paragraph, create study questions",
        "University/College": "Example: summarize this abstract, improve discussion section, research questions on addiction",
        "Researchers": "Example: refine literature review, rewrite for journal tone, outline presentation",
        "Higher education level": "Example: explain a complex topic, improve academic writing, summarize research notes",
    }

    col1, col2 = st.columns(2)

    with col1:
        audience = st.selectbox("Who is this for?", list(task_map.keys()))

    with col2:
        task_name = st.selectbox("What do you need help with?", task_map[audience])

    if task_name == "Other / Something else":
        custom_task = st.text_input(
            "Describe what you need",
            placeholder="Example: Write an introduction, create flashcards, analyze data...",
        )
        st.info("Even a short request works — the app will build a strong prompt for you.")
    else:
        custom_task = task_name

    if task_name == "Other / Something else":
        st.caption("Optional: add extra details below if you have them.")
    else:
        st.caption("Required: please provide content for this task.")

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

    if audience in {"Middle school", "High school"}:
        tip_text = "Tip: Adding the class topic can improve results, but it's optional."
    elif audience == "Researchers":
        tip_text = "Tip: Include discipline or research goal for best results."
    else:
        tip_text = "Tip: Include subject area or assignment goal for more precise output."

    st.markdown(f"<div class='tip'>{tip_text}</div>", unsafe_allow_html=True)

    st.divider()

    if st.button("✨ Generate Prompt", type="primary", use_container_width=True):
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
                    st.success("Your prompt has been generated successfully.")
                except Exception as exc:
                    st.error(f"Something went wrong: {exc}")
