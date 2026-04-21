import streamlit as st


def landing_page() -> None:
    st.markdown(
        """
        <style>
        .lp-hero-title {
            font-size: 2.6rem;
            font-weight: 800;
            line-height: 1.15;
            text-align: center;
            margin-bottom: 0.8rem;
        }

        .lp-hero-subtitle {
            font-size: 1.08rem;
            color: #a0a7b4;
            text-align: center;
            max-width: 760px;
            margin: 0 auto 1.25rem auto;
        }

        .lp-section-title {
            font-size: 1.8rem;
            font-weight: 800;
            margin-bottom: 0.8rem;
        }

        .lp-section-text {
            font-size: 1rem;
            color: #c9ced8;
            line-height: 1.75;
        }

        .lp-step-label {
            font-size: 0.95rem;
            font-weight: 700;
            color: #9db3ff;
            margin-bottom: 0.35rem;
        }

        .lp-step-title {
            font-size: 1.2rem;
            font-weight: 700;
            margin-bottom: 0.45rem;
        }

        .lp-step-text {
            color: #c9ced8;
            line-height: 1.7;
            font-size: 0.98rem;
        }

        .lp-center {
            text-align: center;
        }

        .lp-chip-row {
            margin-top: 1rem;
            margin-bottom: 0.4rem;
        }

        .lp-chip {
            display: inline-block;
            padding: 0.42rem 0.8rem;
            margin: 0.2rem 0.35rem 0.2rem 0;
            border-radius: 999px;
            background: rgba(86, 120, 255, 0.16);
            color: #b8c6ff;
            font-size: 0.88rem;
            font-weight: 700;
        }

        @media (max-width: 640px) {
            .lp-hero-title {
                font-size: 2rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.container():
        st.markdown(
            "<div class='lp-hero-title'>Turn Your Ideas Into Research-Quality AI Prompts — In Seconds</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<div class='lp-hero-subtitle'>Designed for undergraduate students, graduate learners, and researchers who want clear, structured, high-quality results from AI tools like ChatGPT.</div>",
            unsafe_allow_html=True,
        )

        left, center, right = st.columns([1, 1.2, 1])
        with center:
            if st.button("Get Started Free", use_container_width=True):
                st.session_state.page = "app"
                st.rerun()

    st.write("")
    st.write("")

    with st.container(border=True):
        st.markdown(
            "<div class='lp-section-title'>Struggling to Get Good Results from AI?</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<div class='lp-section-text'>You know AI can help, but getting strong results often feels frustrating. Your prompts may feel unclear, the output may sound generic, and too much time gets wasted rewriting and retrying.</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            <div class='lp-section-text'>
            • Your prompts feel unclear<br>
            • The results are weak or too generic<br>
            • You spend too much time rewriting and retrying
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.write("")

    with st.container(border=True):
        st.markdown(
            "<div class='lp-section-title'>We Fix the Hard Part — Writing the Prompt</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<div class='lp-section-text'>Our platform transforms your ideas into structured, professional prompts that help AI tools produce clearer, stronger, and more useful responses. Even if your input is short or messy, the system turns it into something practical and ready to use.</div>",
            unsafe_allow_html=True,
        )

    st.write("")
    st.write("")

    st.markdown(
        "<div class='lp-section-title lp-center'>Simple. Fast. Effective.</div>",
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)

    with c1:
        with st.container(border=True):
            st.markdown("<div class='lp-step-label'>Step 1</div>", unsafe_allow_html=True)
            st.markdown("<div class='lp-step-title'>Choose your audience</div>", unsafe_allow_html=True)
            st.markdown(
                "<div class='lp-step-text'>Select Middle school, High school, University/College, Higher education level, or Researchers to match the right tone and quality level.</div>",
                unsafe_allow_html=True,
            )

    with c2:
        with st.container(border=True):
            st.markdown("<div class='lp-step-label'>Step 2</div>", unsafe_allow_html=True)
            st.markdown("<div class='lp-step-title'>Select your task</div>", unsafe_allow_html=True)
            st.markdown(
                "<div class='lp-step-text'>Choose the kind of help you need, such as summaries, essays, research questions, or structured outlines.</div>",
                unsafe_allow_html=True,
            )

    with c3:
        with st.container(border=True):
            st.markdown("<div class='lp-step-label'>Step 3</div>", unsafe_allow_html=True)
            st.markdown("<div class='lp-step-title'>Enter your idea</div>", unsafe_allow_html=True)
            st.markdown(
                "<div class='lp-step-text'>Paste your notes or type a short idea, then get a clear, ready-to-use prompt instantly.</div>",
                unsafe_allow_html=True,
            )

    st.write("")

    with st.container(border=True):
        st.markdown(
            "<div class='lp-section-title'>Built for Academic and Professional Work</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<div class='lp-section-text'>This is not a generic prompt tool. It is designed for users who need more structure, stronger clarity, and outputs that are actually useful in real academic and professional workflows.</div>",
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            <div class='lp-chip-row'>
                <span class='lp-chip'>Middle school</span>
                <span class='lp-chip'>High school</span>
                <span class='lp-chip'>University/College</span>
                <span class='lp-chip'>Higher education level</span>
                <span class='lp-chip'>Researchers</span>
                <span class='lp-chip'>Clear</span>
                <span class='lp-chip'>Structured</span>
                <span class='lp-chip'>Context-aware</span>
                <span class='lp-chip'>Ready for real use</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.write("")

    with st.container(border=True):
        st.markdown(
            "<div class='lp-section-title'>What You Get</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            <div class='lp-section-text'>
            🔐 Secure account system<br>
            ⚡ Instant prompt generation<br>
            🎯 Prompt quality tailored to your audience and task<br>
            📊 Usage tracking<br>
            💳 Optional Pro plan for extended use
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.write("")

    with st.container(border=True):
        st.markdown(
            "<div class='lp-section-title lp-center'>Start Free — Upgrade When You Need More</div>",
            unsafe_allow_html=True,
        )

        p1, p2 = st.columns(2)

        with p1:
            with st.container(border=True):
                st.subheader("Free Plan")
                st.markdown("### $0")
                st.caption("A simple way to try the platform")
                st.write("• 3 prompts")
                st.write("• Full access to core features")

        with p2:
            with st.container(border=True):
                st.subheader("Pro Plan")
                st.markdown("### $20/month")
                st.caption("For more regular and serious use")
                st.write("• 200 prompts per month")
                st.write("• Designed for academic and professional workflows")

    st.write("")

    with st.container(border=True):
        st.markdown(
            "<div class='lp-section-title'>Built With Care, Not Noise</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<div class='lp-section-text'>This platform was created to make AI more useful, not more complicated. No clutter, no gimmicks, and no unnecessary distractions — just a focused tool that helps people think, write, and work better.</div>",
            unsafe_allow_html=True,
        )

    st.write("")

    with st.container(border=True):
        st.markdown(
            "<div class='lp-section-title lp-center'>Ready to Get Better Results from AI?</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<div class='lp-hero-subtitle'>Start using structured, high-quality prompts today.</div>",
            unsafe_allow_html=True,
        )

        left, center, right = st.columns([1, 1.2, 1])
        with center:
            if st.button("Create Your First Prompt", key="bottom_cta", use_container_width=True):
                st.session_state.page = "app"
                st.rerun()
