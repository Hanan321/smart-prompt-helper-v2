import streamlit as st


def prompt_result_panel(generated_prompt: str) -> None:
    if not generated_prompt:
        return

    st.markdown("<div class='section-title'>📌 Your Generated Prompt</div>", unsafe_allow_html=True)

    st.text_area(
        "Your prompt",
        value=generated_prompt,
        height=220,
        key="generated_prompt_output",
    )

    st.info("To copy: click inside the box, then press Ctrl+C on Windows or Cmd+C on Mac.")

    st.download_button(
        "Download Prompt",
        data=generated_prompt,
        file_name="generated_prompt.txt",
        mime="text/plain",
        use_container_width=True,
    )