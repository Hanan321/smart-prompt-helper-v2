import streamlit as st


def prompt_result_panel(generated_prompt: str) -> None:
    if not generated_prompt:
        return

    st.markdown("<div class='section-title'>📌 Your Generated Prompt</div>", unsafe_allow_html=True)

    st.info("Use the small copy icon in the top-right corner of the prompt box, or download the prompt below.")

    st.code(generated_prompt, language=None)

    st.caption("If copying on desktop: click inside the prompt, then press Ctrl+A and Ctrl+C on Windows, or Cmd+A and Cmd+C on Mac.")

    st.download_button(
        "Download Prompt",
        data=generated_prompt,
        file_name="generated_prompt.txt",
        mime="text/plain",
        use_container_width=True,
    )