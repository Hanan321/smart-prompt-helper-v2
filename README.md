# Smart Prompt Helper v2 (SaaS-ready)

This refactor converts the single-password Streamlit app into a SaaS-ready architecture with:

- Supabase email/password authentication
- Per-user profiles and sessions
- Stripe subscriptions (Free / Pro / Premium)
- Free-tier usage limits (5 prompts/day by default)
- Usage tracking in Supabase
- Upgrade and billing UI
- Server-side OpenAI calls only
- Better mobile responsiveness

## 1) Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2) Create Supabase project and database schema

1. Create a project in Supabase.
2. Open **SQL Editor** and run `sql/schema.sql`.
3. In **Authentication > Providers**, ensure Email provider is enabled.
4. Copy these values from Supabase project settings:
   - `SUPABASE_URL`
   - `SUPABASE_ANON_KEY`
   - `SUPABASE_SERVICE_ROLE_KEY`

## 3) Create Stripe products and prices

1. In Stripe, create two recurring prices:
   - Pro plan price (`STRIPE_PRICE_PRO`)
   - Premium plan price (`STRIPE_PRICE_PREMIUM`)
2. Copy your Stripe keys:
   - `STRIPE_SECRET_KEY`
   - `STRIPE_PUBLISHABLE_KEY` (optional for future client-side use)

## 4) Configure environment variables

Create a `.env` file in project root:

```env
OPENAI_API_KEY=sk-...
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...
STRIPE_SECRET_KEY=sk_live_or_test_...
STRIPE_PUBLISHABLE_KEY=pk_live_or_test_...
STRIPE_PRICE_PRO=price_...
STRIPE_PRICE_PREMIUM=price_...
STRIPE_WEBHOOK_SECRET=whsec_...
APP_BASE_URL=http://localhost:8501
FREE_DAILY_PROMPT_LIMIT=5
```

## 5) Run the Streamlit app

```bash
streamlit run app.py
```

## 6) Configure Stripe webhooks (required for automatic plan sync)

The app includes `stripe_webhook.py` for syncing paid plan state into Supabase.

### Run webhook service locally

```bash
uvicorn stripe_webhook:app --reload --port 8000
```

### Forward webhooks from Stripe CLI

```bash
stripe listen --forward-to localhost:8000/webhooks/stripe
```

Copy the webhook signing secret and set `STRIPE_WEBHOOK_SECRET`.

### Add webhook events

At minimum subscribe to:
- `checkout.session.completed`
- `customer.subscription.deleted`

## 7) How usage limits work

- Free plan users can generate up to `FREE_DAILY_PROMPT_LIMIT` prompts/day.
- Pro and Premium users are not blocked by the free limit.
- Usage is tracked in `daily_usage` table, per `user_id` and date.

## 8) Security notes

- OpenAI and Stripe secret keys are read only on server side.
- Prompt generation is executed server-side by Streamlit backend.
- Supabase service role key must never be exposed in frontend JavaScript.

## 9) Production deployment tips

- Deploy Streamlit and webhook service behind HTTPS.
- Set `APP_BASE_URL` to your production URL.
- Use Stripe live keys only in production.
- Restrict Supabase RLS policies as needed for your org.
- Add monitoring for webhook failures and retries.
