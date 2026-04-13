import streamlit as st


def prompt_form_panel(
    user: dict,
    supabase_admin,
    prompt_generator,
    can_generate_prompt,
    increment_prompt_count,
) -> None:
    with st.expander("ℹ️ How to use"):
        st.markdown(
            """
**1.** Choose who this is for  
**2.** Select the kind of help you need  
**3.** Paste your text, notes, topic, or even just a few words  
**4.** Click **Generate Prompt**  
**5.** Copy the result into ChatGPT or another AI tool
"""
        )

    st.markdown("<div class='section-title'>✨ Generate Your Prompt</div>", unsafe_allow_html=True)

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
        "Undergraduate": "Example: biology summary, fix my paragraph, explain photosynthesis, essay about climate change",
        "Graduate": "Example: summarize this abstract, improve my discussion section, generate research questions on opioid treatment",
        "Researcher / Professional": "Example: refine this literature review, rewrite for journal tone, create a presentation outline on my findings",
    }

    audience = st.selectbox("Who is this for?", list(task_map.keys()))
    task_name = st.selectbox("What do you need help with?", task_map[audience])

    if task_name == "Other / Something else":
        custom_task = st.text_input(
            "Describe what you need",
            placeholder="Example: Create flashcards, write an essay introduction, analyze data, prepare interview answers...",
        )
        st.info("You can describe exactly what you need. Even a short request is okay.")
    else:
        custom_task = task_name

    user_text = st.text_area(
        "📄 What would you like help with?",
        height=180,
        placeholder=placeholder_map[audience],
    )

    st.caption(
        "You can paste a full paragraph, notes, a topic, or even just a few words like 'biology summary' or 'fix grammar'."
    )

    clean_user_text = user_text.strip()
    if clean_user_text and len(clean_user_text) < 8:
        st.info("Short input is okay. The app will try to turn your idea into a stronger prompt.")

    if audience == "Undergraduate":
        tip_text = "Tip: Add the course topic or class level if you can, but short input also works."
    elif audience == "Graduate":
        tip_text = "Tip: Include the subject area, assignment goal, or expected structure for a stronger result."
    else:
        tip_text = "Tip: Include your discipline, research goal, or target output if available."

    st.markdown(
        f"<div class='tip'>{tip_text}</div>",
        unsafe_allow_html=True,
    )

    if st.button("✨ Generate Prompt", use_container_width=True):
        final_task = custom_task.strip() if isinstance(custom_task, str) else ""

        if task_name == "Other / Something else" and not final_task:
            st.error("Please describe what you need help with.")
        elif not clean_user_text:
            st.error("Please enter some text, a topic, or a few words first.")
        else:
            allowed, message = can_generate_prompt(supabase_admin, user["id"])
            if not allowed:
                st.warning(message)
            else:
                with st.spinner("Generating your prompt..."):
                    try:
                        final_prompt = prompt_generator.generate(audience, final_task, clean_user_text)
                        increment_prompt_count(supabase_admin, user["id"])
                        st.session_state.generated_prompt = final_prompt
                        st.success("Your prompt is ready.")
                    except Exception as exc:
                        st.error(f"Something went wrong: {exc}")