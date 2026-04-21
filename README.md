# Smart Prompt Helper (Academic Edition)

Smart Prompt Helper is a SaaS-ready AI application built for **researchers, graduate students, and academic professionals** who want to generate high-quality prompts for writing, analysis, and research workflows.

The app combines **Supabase authentication**, **Stripe billing**, **usage tracking**, and **server-side OpenAI prompt generation** in a clean Streamlit interface.

---

## Features

- Supabase email/password authentication
- Per-user profiles and session support
- Free and Pro subscription plans
- Stripe checkout and billing portal integration
- Secure server-side OpenAI API usage
- Academic-focused AI prompt generation
- Usage tracking with Supabase
- Clean and responsive Streamlit UI
- Downloadable generated prompts

---

## Who It Is For

Smart Prompt Helper is designed for:

- Researchers
- Middle school students
- High school students
- University/College students
- University faculty
- Academic professionals
- Students working on academic writing, summaries, outlines, and research tasks

---

## Pricing

### Free Plan
- 2 prompts total to test the app in staging

### Prompt Pack — $5
- 10 one-time prompts in staging
- Purchased credits accumulate and do not expire

### Pro Plan — $20/month
- Up to 200 prompts per month
- Designed for academic and research workflows
- Better suited for regular and professional use

---

## Stripe Webhook URL

The Stripe webhook handler is the FastAPI app in `stripe_webhook.py`, not the Streamlit UI app.

Run/deploy it with:

```bash
uvicorn stripe_webhook:app --host 0.0.0.0 --port 8000
```

Use one of these paths on the deployed FastAPI webhook host:

- Canonical: `/webhooks/stripe`
- Compatibility alias: `/stripe-webhook`

Do not point Stripe webhooks at the Streamlit app URL unless that same host is explicitly running the FastAPI app.

---

## Tech Stack

- **Frontend:** Streamlit
- **Backend:** Python
- **Authentication & Database:** Supabase
- **Payments:** Stripe
- **AI Integration:** OpenAI API

---

## Project Structure

```bash
smart_prompt_helper/
├── app.py
├── stripe_webhook.py
├── requirements.txt
├── README.md
├── sql/
│   └── schema.sql
└── services/
    ├── auth.py
    ├── billing.py
    ├── config.py
    ├── prompt_service.py
    └── usage.py
