import html
import streamlit as st
import streamlit.components.v1 as components


def prompt_result_panel(generated_prompt: str) -> None:
    if not generated_prompt:
        return

    st.markdown("<div class='section-title'>📌 Your Generated Prompt</div>", unsafe_allow_html=True)

    escaped_prompt = html.escape(generated_prompt)
    js_prompt = generated_prompt.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")

    components.html(
        f"""
        <div style="
            border: 1px solid rgba(255,255,255,0.10);
            border-radius: 16px;
            padding: 16px;
            background: rgba(255,255,255,0.03);
            margin-bottom: 12px;
        ">
            <div style="
                font-size: 14px;
                font-weight: 600;
                margin-bottom: 10px;
                color: #f3f4f6;
            ">
                Your prompt
            </div>

            <pre id="generated-prompt-box" style="
                white-space: pre-wrap;
                word-wrap: break-word;
                background: rgba(0,0,0,0.18);
                border-radius: 12px;
                padding: 14px;
                font-size: 14px;
                line-height: 1.5;
                color: #f9fafb;
                max-height: 320px;
                overflow-y: auto;
                margin: 0 0 12px 0;
            ">{escaped_prompt}</pre>

            <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                <button
                    id="copy-btn"
                    onclick="copyPrompt()"
                    style="
                        border: none;
                        border-radius: 12px;
                        padding: 10px 16px;
                        font-size: 14px;
                        font-weight: 600;
                        cursor: pointer;
                    "
                >
                    📋 Copy Prompt
                </button>
            </div>

            <div id="copy-status" style="
                margin-top: 10px;
                font-size: 13px;
                color: #9ca3af;
            ">
                Click the button to copy the prompt.
            </div>
        </div>

        <script>
            async function copyPrompt() {{
                const text = `{js_prompt}`;
                const status = document.getElementById("copy-status");
                const button = document.getElementById("copy-btn");

                try {{
                    await navigator.clipboard.writeText(text);
                    status.textContent = "Copied to clipboard.";
                    button.textContent = "✅ Copied";
                }} catch (err) {{
                    status.textContent = "Copy failed. Please select the text and copy it manually.";
                    button.textContent = "📋 Copy Prompt";
                }}
            }}
        </script>
        """,
        height=360,
    )

    st.download_button(
        "Download Prompt",
        data=generated_prompt,
        file_name="generated_prompt.txt",
        mime="text/plain",
        use_container_width=True,
    )

    st.caption("You can copy the prompt with the button above or download it as a text file.")