import streamlit as st


def landing_page() -> None:
    st.markdown(
        """
        <style>
        .hero-card, .section-card, .pricing-card {
            border: 1px solid rgba(255,255,255,0.10);
            border-radius: 18px;
            padding: 1.4rem;
            margin-bottom: 1rem;
            background: rgba(255,255,255,0.02);
        }

        .hero-title {
            font-size: 2.6rem;
            font-weight: 800;
            line-height: 1.15;
            margin-bottom: 0.7rem;
            text-align: center;
        }

        .hero-subtitle {
            font-size: 1.08rem;
            color: #a0a7b4;
            text-align: center;
            max-width: 760px;
            margin: 0 auto 1.2rem auto;
        }

        .section-title {
            font-size: 1.55rem;
            font-weight: 700;
            margin-bottom: 0.65rem;
        }

        .section-text {
            font-size: 1rem;
            color: #c9ced8;
            line-height: 1.7;
        }

        .bullet {
            font-size: 1rem;
            color: #d7dbe3;
            margin-bottom: 0.45rem;
        }

        .step-card {
            border: 1px solid rgba(255,255,255,0.10);
            border-radius: 16px;
            padding: 1rem;
            background: rgba(255,255,255,0.02);
            height: 100%;
        }

        .step-number {
            font-size: 0.9rem;
            font-weight: 700;
            color: #9db3ff;
            margin-bottom: 0.35rem;
        }

        .step-title {
            font-size: 1.05rem;
            font-weight: 700;
            margin-bottom: 0.35rem;
        }

        .step-text {
            color: #c9ced8;
            font-size: 0.96rem;
            line-height: 1.6;
        }

        .value-chip {
            display: inline-block;
            padding: 0.42rem 0.75rem;
            border-radius: 999px;
            background: rgba(86, 120, 255, 0.16);
            color: #b8c6ff;
            font-size: 0.87rem;
            font-weight: 700;
            margin: 0.22rem 0.3rem 0.22rem 0;
        }

        .pricing-title {
            font-size: 1.15rem;
            font-weight: 700;
            margin-bottom: 0.3rem;
        }

        .price {
            font-size: 1.7rem;
            font-weight: 800;
            margin-bottom: 0.3rem;
        }

        .price-note {
            color: #a0a7b4;
            font-size: 0.95rem;
            margin-bottom: 0.8rem;
        }

        .center-text {
            text-align: center;
        }

        @media (max-width: 640px) {
            .hero-title {
                font-size: 2rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Hero
    st.markdown("<div class='hero-card'>", unsafe_allow_html=True)
    st.markdown(
        "<div class='hero-title'>Turn Your Ideas Into Research-Quality AI Prompts — In Seconds</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div class='hero-subtitle'>Designed for students, researchers, and professionals who want clear, structured, high-quality results from AI tools like ChatGPT.</div>",
        unsafe_allow_html=True,
    )

    col_a, col_b, col_c = st.columns([1, 1, 1])
    with col_b:
        if st.button("Get Started Free", use_container_width=True):
            st.session_state.page = "app"
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    # Problem
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Struggling to Get Good Results from AI?</div>", unsafe_allow_html=True)
    st.markdown(
        """
        <div class='section-text'>
        You know AI can help, but getting strong results often feels frustrating.
        Your prompts may feel unclear, the output can sound generic, and too much time gets wasted rewriting and retrying.
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("<div class='bullet'>• Your prompts feel unclear</div>", unsafe_allow_html=True)
    st.markdown("<div class='bullet'>• The results are weak or too generic</div>", unsafe_allow_html=True)
    st.markdown("<div class='bullet'>• You spend too much time retrying</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Solution
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>We Fix the Hard Part — Writing the Prompt</div>", unsafe_allow_html=True)
    st.markdown(
        """
        <div class='section-text'>
        Our platform transforms your ideas into structured, professional prompts that help AI tools produce clearer,
        stronger, and more useful responses. Even if your input is short or messy, the system turns it into something practical and ready to use.
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    # How it works
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title center-text'>Simple. Fast. Effective.</div>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown(
            """
            <div class='step-card'>
                <div class='step-number'>Step 1</div>
                <div class='step-title'>Choose your audience</div>
                <div class='step-text'>Select undergraduate, graduate, or professional to match the right tone and level.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c2:
        st.markdown(
            """
            <div class='step-card'>
                <div class='step-number'>Step 2</div>
                <div class='step-title'>Select your task</div>
                <div class='step-text'>Choose the kind of help you need, such as summaries, essays, research questions, or structured outlines.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c3:
        st.markdown(
            """
            <div class='step-card'>
                <div class='step-number'>Step 3</div>
                <div class='step-title'>Enter your idea</div>
                <div class='step-text'>Paste your notes or type a short idea, then get a clean, ready-to-use prompt instantly.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)

    # Value
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Built for Academic and Professional Work</div>", unsafe_allow_html=True)
    st.markdown(
        """
        <div class='section-text'>
        This is not a generic prompt tool. It is designed for users who need more structure, stronger clarity,
        and outputs that are actually useful in real academic and professional workflows.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<span class='value-chip'>Students</span>", unsafe_allow_html=True)
    st.markdown("<span class='value-chip'>Researchers</span>", unsafe_allow_html=True)
    st.markdown("<span class='value-chip'>Professionals</span>", unsafe_allow_html=True)
    st.markdown("<span class='value-chip'>Clear</span>", unsafe_allow_html=True)
    st.markdown("<span class='value-chip'>Structured</span>", unsafe_allow_html=True)
    st.markdown("<span class='value-chip'>Context-aware</span>", unsafe_allow_html=True)
    st.markdown("<span class='value-chip'>Ready for real use</span>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Features
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>What You Get</div>", unsafe_allow_html=True)
    st.markdown("<div class='bullet'>🔐 Secure account system</div>", unsafe_allow_html=True)
    st.markdown("<div class='bullet'>⚡ Instant prompt generation</div>", unsafe_allow_html=True)
    st.markdown("<div class='bullet'>🎯 Prompt quality tailored to audience and task</div>", unsafe_allow_html=True)
    st.markdown("<div class='bullet'>📊 Usage tracking</div>", unsafe_allow_html=True)
    st.markdown("<div class='bullet'>💳 Optional Pro plan for extended use</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Pricing
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title center-text'>Start Free — Upgrade When You Need More</div>", unsafe_allow_html=True)

    p1, p2 = st.columns(2)

    with p1:
        st.markdown(
            """
            <div class='pricing-card'>
                <div class='pricing-title'>Free Plan</div>
                <div class='price'>$0</div>
                <div class='price-note'>A simple way to test the platform</div>
                <div class='bullet'>• 5 prompts</div>
                <div class='bullet'>• Full access to core features</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with p2:
        st.markdown(
            """
            <div class='pricing-card'>
                <div class='pricing-title'>Pro Plan</div>
                <div class='price'>$20/month</div>
                <div class='price-note'>For more consistent and serious use</div>
                <div class='bullet'>• 200 prompts per month</div>
                <div class='bullet'>• Designed for regular academic and professional workflows</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)

    # Trust
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Built With Care, Not Noise</div>", unsafe_allow_html=True)
    st.markdown(
        """
        <div class='section-text'>
        This platform was created to make AI more useful, not more complicated.
        No clutter, no gimmicks, and no unnecessary distractions — just a focused tool that helps people think, write, and work better.
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    # Final CTA
    st.markdown("<div class='hero-card'>", unsafe_allow_html=True)
    st.markdown(
        "<div class='section-title center-text'>Ready to Get Better Results from AI?</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div class='hero-subtitle'>Start using structured, high-quality prompts today.</div>",
        unsafe_allow_html=True,
    )

    x1, x2, x3 = st.columns([1, 1, 1])
    with x2:
        if st.button("Create Your First Prompt", key="bottom_cta", use_container_width=True):
            st.session_state.page = "app"
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)