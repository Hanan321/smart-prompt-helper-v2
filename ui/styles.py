def render_styles() -> None:
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
            max-width: 900px;
        }

        .main-title {
            text-align: center;
            font-size: 2.5rem;
            font-weight: 800;
            margin-bottom: 0.25rem;
        }

        .subtitle {
            text-align: center;
            color: #8b8f98;
            font-size: 1.05rem;
            margin-bottom: 1.8rem;
        }

        .section-title {
            font-size: 1.25rem;
            font-weight: 700;
            margin-top: 1.2rem;
            margin-bottom: 0.8rem;
        }

        .plan-chip {
            display: inline-block;
            padding: 0.35rem 0.7rem;
            border-radius: 999px;
            background: rgba(86, 120, 255, 0.16);
            color: #9db3ff;
            font-size: 0.85rem;
            font-weight: 700;
            margin-top: 0.35rem;
            margin-bottom: 0.35rem;
        }

        .muted {
            color: #9aa0a6;
            font-size: 0.95rem;
        }

        .tip {
            font-size: 0.93rem;
            color: #8b8f98;
            margin-top: 0.45rem;
            margin-bottom: 0.35rem;
        }

        .prompt-box {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.10);
            border-radius: 16px;
            padding: 0.8rem;
            margin-top: 0.5rem;
            margin-bottom: 0.8rem;
        }

        .price-text {
            font-size: 1.1rem;
            font-weight: 700;
            margin-top: 0.25rem;
            margin-bottom: 0.15rem;
        }

        .price-subtext {
            color: #9aa0a6;
            font-size: 0.9rem;
            margin-bottom: 0.8rem;
        }

        div[data-testid="stButton"] > button,
        div[data-testid="stDownloadButton"] > button,
        div[data-testid="stLinkButton"] > a {
            border-radius: 12px;
            font-weight: 600;
            min-height: 44px;
        }

        [data-testid="stToolbar"] {
            visibility: hidden;
        }

        div[data-testid="stDecoration"] {
            display: none !important;
        }

        header[data-testid="stHeader"] {
            background: transparent !important;
        }

        @media (max-width: 640px) {
            .main-title {
                font-size: 1.95rem;
            }

            .subtitle {
                font-size: 0.96rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
