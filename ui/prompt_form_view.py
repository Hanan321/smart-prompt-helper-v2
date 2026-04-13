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