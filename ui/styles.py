import streamlit as st


def render_styles() -> None:
    st.markdown(
        """
        <style>
        @import url("https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap");

        :root {
            --app-bg: #f7f8f5;
            --surface: #ffffff;
            --surface-soft: #edf6f0;
            --ink: #18221d;
            --muted: #5e6c64;
            --line: #dce4dd;
            --accent: #0f766e;
            --accent-dark: #0b4f49;
            --accent-soft: #d9f1ec;
            --coral: #e56b5d;
            --gold: #d49d2f;
            --shadow: 0 18px 45px rgba(24, 34, 29, 0.10);
            --radius: 8px;
        }

        html,
        body,
        [class*="css"],
        .stApp {
            font-family: "Plus Jakarta Sans", system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }

        .stApp,
        [data-testid="stAppViewContainer"],
        [data-testid="stSidebar"] {
            color: var(--ink);
            background: var(--app-bg);
        }

        [data-testid="stHeader"] {
            background: rgba(247, 248, 245, 0.88) !important;
            border-bottom: 1px solid var(--line);
            backdrop-filter: blur(18px);
        }

        [data-testid="stToolbar"],
        div[data-testid="stDecoration"] {
            display: none !important;
            visibility: hidden;
        }

        .block-container {
            max-width: 960px;
            padding-top: 3rem;
            padding-bottom: 4rem;
        }

        .main-title {
            max-width: 760px;
            margin: 0 auto 0.45rem auto;
            color: var(--ink);
            font-size: clamp(2.2rem, 6vw, 4.2rem);
            font-weight: 800;
            line-height: 0.98;
            letter-spacing: 0;
            text-align: center;
        }

        .subtitle {
            max-width: 720px;
            margin: 0 auto 1.8rem auto;
            color: var(--muted);
            font-size: 1.03rem;
            line-height: 1.8;
            text-align: center;
        }

        .section-title {
            margin: 2rem 0 0.85rem 0;
            color: var(--ink);
            font-size: 1.45rem;
            font-weight: 800;
            line-height: 1.2;
        }

        .plan-chip {
            display: inline-flex;
            align-items: center;
            min-height: 30px;
            padding: 0 0.7rem;
            margin: 0.45rem 0;
            border-radius: var(--radius);
            color: var(--accent-dark);
            background: var(--accent-soft);
            border: 1px solid rgba(15, 118, 110, 0.12);
            font-size: 0.82rem;
            font-weight: 800;
        }

        .muted,
        .tip,
        .price-subtext,
        div[data-testid="stCaptionContainer"],
        .stCaptionContainer {
            color: var(--muted) !important;
        }

        .tip {
            margin-top: 0.55rem;
            margin-bottom: 0.4rem;
            font-size: 0.94rem;
            line-height: 1.65;
        }

        .prompt-box {
            margin-top: 0.5rem;
            margin-bottom: 0.8rem;
            padding: 1rem;
            border-left: 4px solid var(--coral);
            border-radius: var(--radius);
            color: var(--ink);
            background: var(--surface-soft);
        }

        .price-text {
            margin-top: 0.25rem;
            margin-bottom: 0.2rem;
            color: var(--ink);
            font-size: 1.75rem;
            font-weight: 800;
            line-height: 1;
        }

        .price-subtext {
            margin-bottom: 0.85rem;
            font-size: 0.92rem;
            line-height: 1.65;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] {
            border: 1px solid var(--line) !important;
            border-radius: var(--radius) !important;
            background: var(--surface) !important;
            box-shadow: var(--shadow);
        }

        div[data-testid="stVerticalBlockBorderWrapper"] > div {
            border-radius: var(--radius) !important;
        }

        hr {
            margin: 1.7rem 0 !important;
            border-color: var(--line) !important;
        }

        h1,
        h2,
        h3,
        h4,
        h5,
        h6,
        p,
        label,
        span,
        li,
        div {
            letter-spacing: 0;
        }

        label,
        [data-testid="stMarkdownContainer"] strong {
            color: var(--ink);
            font-weight: 800;
        }

        div[data-testid="stTextInput"] input,
        div[data-testid="stTextArea"] textarea,
        div[data-baseweb="select"] > div {
            border: 1px solid var(--line) !important;
            border-radius: var(--radius) !important;
            color: var(--ink) !important;
            background: var(--surface) !important;
            box-shadow: none !important;
        }

        div[data-testid="stTextInput"] input:focus,
        div[data-testid="stTextArea"] textarea:focus,
        div[data-baseweb="select"] > div:focus-within {
            border-color: var(--accent) !important;
            box-shadow: 0 0 0 3px rgba(15, 118, 110, 0.14) !important;
        }

        div[data-testid="stTextArea"] textarea {
            min-height: 180px;
            line-height: 1.65;
        }

        div[data-testid="stButton"] > button,
        div[data-testid="stDownloadButton"] > button,
        div[data-testid="stLinkButton"] > a,
        div[data-testid="stFormSubmitButton"] > button {
            min-height: 46px;
            border-radius: var(--radius) !important;
            border: 1px solid transparent !important;
            font-weight: 800 !important;
            transition: transform 0.18s ease, box-shadow 0.18s ease, background 0.18s ease;
        }

        div[data-testid="stButton"] > button[kind="primary"],
        div[data-testid="stButton"] > button[data-testid="stBaseButton-primary"],
        div[data-testid="stFormSubmitButton"] > button,
        div[data-testid="stDownloadButton"] > button,
        div[data-testid="stLinkButton"] > a {
            color: #ffffff !important;
            background: var(--accent) !important;
            box-shadow: 0 12px 24px rgba(15, 118, 110, 0.18);
        }

        div[data-testid="stButton"] > button[kind="primary"] *,
        div[data-testid="stButton"] > button[data-testid="stBaseButton-primary"] *,
        div[data-testid="stFormSubmitButton"] > button *,
        div[data-testid="stDownloadButton"] > button *,
        div[data-testid="stLinkButton"] > a * {
            color: #ffffff !important;
        }

        div[data-testid="stButton"] > button[kind="secondary"] {
            color: var(--ink) !important;
            background: var(--surface) !important;
            border-color: var(--line) !important;
        }

        div[data-testid="stButton"] > button:hover,
        div[data-testid="stDownloadButton"] > button:hover,
        div[data-testid="stLinkButton"] > a:hover,
        div[data-testid="stFormSubmitButton"] > button:hover {
            transform: translateY(-1px);
        }

        div[data-testid="stButton"] > button[kind="primary"]:hover,
        div[data-testid="stButton"] > button[data-testid="stBaseButton-primary"]:hover,
        div[data-testid="stFormSubmitButton"] > button:hover,
        div[data-testid="stDownloadButton"] > button:hover,
        div[data-testid="stLinkButton"] > a:hover {
            color: #ffffff !important;
            background: var(--accent-dark) !important;
        }

        div[data-testid="stButton"] > button[kind="primary"]:hover *,
        div[data-testid="stButton"] > button[data-testid="stBaseButton-primary"]:hover *,
        div[data-testid="stFormSubmitButton"] > button:hover *,
        div[data-testid="stDownloadButton"] > button:hover *,
        div[data-testid="stLinkButton"] > a:hover * {
            color: #ffffff !important;
        }

        div[data-testid="stTabs"] button {
            color: var(--muted) !important;
            font-weight: 800;
        }

        div[data-testid="stTabs"] button[aria-selected="true"] {
            color: var(--accent-dark) !important;
        }

        div[data-testid="stTabs"] [data-baseweb="tab-highlight"] {
            background-color: var(--accent) !important;
        }

        details[data-testid="stExpander"] {
            border: 1px solid var(--line) !important;
            border-radius: var(--radius) !important;
            background: var(--surface) !important;
            box-shadow: var(--shadow);
        }

        details[data-testid="stExpander"] summary {
            color: var(--ink) !important;
            font-weight: 800;
        }

        div[data-testid="stAlert"] {
            border-radius: var(--radius) !important;
            border: 1px solid var(--line) !important;
            color: var(--ink) !important;
            background: #fff8e8 !important;
        }

        .stCodeBlock,
        pre,
        code {
            border-radius: var(--radius) !important;
        }

        pre {
            border: 1px solid var(--line) !important;
            background: #10251f !important;
            color: #f7f8f5 !important;
        }

        @media (max-width: 640px) {
            .block-container {
                padding-top: 2rem;
                padding-left: 1rem;
                padding-right: 1rem;
            }

            .main-title {
                font-size: 2.35rem;
            }

            .subtitle {
                font-size: 0.98rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
