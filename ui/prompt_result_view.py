import streamlit as st


def prompt_result_panel(generated_prompt: str) -> None:
    if not generated_prompt:
        return

    st.markdown("### 📌 Your Generated Prompt")
    st.markdown("<div class='prompt-box'>", unsafe_allow_html=True)
    st.code(generated_prompt, language=None)
    st.markdown("</div>", unsafe_allow_html=True)

    st.download_button(
        "Download Prompt",
        data=generated_prompt,
        file_name="generated_prompt.txt",
        mime="text/plain",
        use_container_width=True,
    )

    st.markdown(
        "<div class='muted'>Copy or download this prompt and use it in ChatGPT or another AI tool.</div>",
        unsafe_allow_html=True,
    )