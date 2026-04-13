



Uploaded image
Uploaded image

Pasted code.py
Python
this is my SaaS app that I am working on , it is complete and it is fully work , but here I will fix some issues in the app to give it a professional look as my first monetizing app I will paste the whole code here file by file to work on the app then later upgrade it, first file app.py, second file, stripe_webhook.py: import os
from datetime import date, timedelta

import stripe
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request
from supabase import create_client

load_dotenv()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
supabase = create_client(
    os.getenv("SUPABASE_URL", ""),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""),
)

PRO_MONTHLY_PROMPT_LIMIT = 200

app = FastAPI(title="Stripe Webhook")


@app.post("/webhooks/stripe")
async def stripe_webhook(request: Request, stripe_signature: str = Header(alias="Stripe-Signature")):
    payload = await request.body()

    try:
        event = stripe.Webhook.construct_event(payload, stripe_signature, webhook_secret)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid payload: {exc}") from exc
    except stripe.error.SignatureVerificationError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid signature: {exc}") from exc

    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        metadata = data.get("metadata", {})
        user_id = metadata.get("user_id")
        plan = metadata.get("plan", "free")

        if user_id and plan == "pro":
            today = date.today()
            next_end = today + timedelta(days=30)

            (
                supabase.table("user_profiles")
                .update(
                    {
                        "plan": "pro",
                        "stripe_customer_id": data.get("customer"),
                        "stripe_subscription_id": data.get("subscription"),
                        "monthly_prompts_used": 0,
                        "monthly_prompt_limit": PRO_MONTHLY_PROMPT_LIMIT,
                        "billing_period_start": str(today),
                        "billing_period_end": str(next_end),
                    }
                )
                .eq("id", user_id)
                .execute()
            )

    if event_type == "customer.subscription.deleted":
        subscription_id = data.get("id")
        if subscription_id:
            (
                supabase.table("user_profiles")
                .update(
                    {
                        "plan": "free",
                        "stripe_subscription_id": None,
                        "monthly_prompts_used": 0,
                        "monthly_prompt_limit": 0,
                        "billing_period_start": None,
                        "billing_period_end": None,
                    }
                )
                .eq("stripe_subscription_id", subscription_id)
                .execute()
            )

    return {"ok": True}

Thought for 9s
Perfect — I can work with you file by file and help turn it into a cleaner, more professional SaaS app.

I reviewed your app.py from the uploaded file 

 and the stripe_webhook.py code you pasted here. Your app already has a strong foundation. The webhook file works, but for a more professional production look, this file should be improved in a few important ways:

It should handle more Stripe event cases safely.

It should not rely on a fixed 30-day billing period.

It should protect against missing headers better.

It should be easier to maintain and read.

It should avoid silent failures.

Your current version is functional, but this is the kind of cleanup that makes it feel like a real paid SaaS.

Here is a stronger version of stripe_webhook.py:

import os
from datetime import datetime, timezone

import stripe
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request
from supabase import Client, create_client

load_dotenv()

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

if not STRIPE_SECRET_KEY:
    raise RuntimeError("Missing STRIPE_SECRET_KEY")

if not STRIPE_WEBHOOK_SECRET:
    raise RuntimeError("Missing STRIPE_WEBHOOK_SECRET")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise RuntimeError("Missing Supabase configuration")

stripe.api_key = STRIPE_SECRET_KEY
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

PRO_MONTHLY_PROMPT_LIMIT = 200

app = FastAPI(title="Stripe Webhook")


def unix_to_iso_date(timestamp: int | None) -> str | None:
    if not timestamp:
        return None
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).date().isoformat()


def update_user_to_pro(user_id: str, customer_id: str | None, subscription_id: str | None, period_start: int | None, period_end: int | None) -> None:
    supabase.table("user_profiles").update(
        {
            "plan": "pro",
            "stripe_customer_id": customer_id,
            "stripe_subscription_id": subscription_id,
            "monthly_prompts_used": 0,
            "monthly_prompt_limit": PRO_MONTHLY_PROMPT_LIMIT,
            "billing_period_start": unix_to_iso_date(period_start),
            "billing_period_end": unix_to_iso_date(period_end),
        }
    ).eq("id", user_id).execute()


def downgrade_user_to_free(subscription_id: str) -> None:
    supabase.table("user_profiles").update(
        {
            "plan": "free",
            "stripe_subscription_id": None,
            "monthly_prompts_used": 0,
            "monthly_prompt_limit": 5,
            "billing_period_start": None,
            "billing_period_end": None,
        }
    ).eq("stripe_subscription_id", subscription_id).execute()


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
):
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header")

    payload = await request.body()

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=stripe_signature,
            secret=STRIPE_WEBHOOK_SECRET,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid payload: {exc}") from exc
    except stripe.error.SignatureVerificationError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid signature: {exc}") from exc

    event_type = event["type"]
    data = event["data"]["object"]

    try:
        if event_type == "checkout.session.completed":
            metadata = data.get("metadata", {})
            user_id = metadata.get("user_id")
            plan = metadata.get("plan", "free")

            if user_id and plan == "pro":
                subscription_id = data.get("subscription")
                customer_id = data.get("customer")

                period_start = None
                period_end = None

                if subscription_id:
                    subscription = stripe.Subscription.retrieve(subscription_id)
                    period_start = subscription.get("current_period_start")
                    period_end = subscription.get("current_period_end")

                update_user_to_pro(
                    user_id=user_id,
                    customer_id=customer_id,
                    subscription_id=subscription_id,
                    period_start=period_start,
                    period_end=period_end,
                )

        elif event_type == "customer.subscription.updated":
            subscription_id = data.get("id")
            status = data.get("status")
            customer_id = data.get("customer")

            if subscription_id and status in {"active", "trialing"}:
                result = (
                    supabase.table("user_profiles")
                    .select("id")
                    .eq("stripe_subscription_id", subscription_id)
                    .limit(1)
                    .execute()
                )

                rows = result.data or []
                if rows:
                    user_id = rows[0]["id"]
                    update_user_to_pro(
                        user_id=user_id,
                        customer_id=customer_id,
                        subscription_id=subscription_id,
                        period_start=data.get("current_period_start"),
                        period_end=data.get("current_period_end"),
                    )

        elif event_type == "customer.subscription.deleted":
            subscription_id = data.get("id")
            if subscription_id:
                downgrade_user_to_free(subscription_id)

    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Webhook handling failed: {exc}") from exc

    return {"ok": True}
Why this version is better:

It uses Stripe’s real subscription period instead of guessing 30 days.

It adds a /health route, which looks more professional for deployment checks.

It uses helper functions so the file is cleaner.

It handles missing Stripe headers safely.

It supports customer.subscription.updated, which is very useful for renewals and subscription changes.

It sets the free plan limit to 5 instead of 0 when downgrading, which matches your app UI better.

One important issue I noticed in your current webhook code:
when a user is downgraded to free, you set:

"monthly_prompt_limit": 0,
But in your app.py, the free plan is shown as:

Free trial usage: **{total_used}/5 prompts**
So your backend logic and UI can become inconsistent. That should be fixed.

Also, for the “professional SaaS” feeling, I recommend these next improvements after this file:

replace the “Switch to Free” button with simple plan text for free users

make the Pro card visually stronger than the free card

add a real copy button for the generated prompt

improve success/error messages so they feel polished

disable upgrade button when the user is already on Pro

make billing status clearer, like “Active”, “Free Trial”, or “Canceled”

About your earlier question: yes, I agree with you that the “Switch to Free” button is not really necessary. For most SaaS apps, the free plan is the default. A better approach is:

show “Current Plan” on the free card when user is free

show “Upgrade to Pro” on the pro card

do not show “Switch to Free” unless you really support plan switching back from paid in-app

That will look much more professional.

Send me app.py next in plain text, and I’ll help you clean it section by section into a polished monetizable version.


third file: README.md : # Smart Prompt Helper (Academic Edition)

A SaaS-ready AI tool designed for **researchers, graduate students, and academic professionals** to generate high-quality prompts for writing, analysis, and research workflows.

## ✨ Features  

- Supabase email/password authentication
- Per-user profiles and sessions
- Stripe subscription (Free / Pro)
- Free-tier usage limit (3 prompts/day)
- Usage tracking in Supabase
- Academic-focused prompt generation
- Server-side OpenAI API usage
- Clean and responsive UI

---

## 🎯 Who is this for?

- Researchers
- Graduate students
- University faculty
- Academic professionals
- Anyone working on academic writing or research tasks

---

## 💳 Pricing

- **Free Plan**
  - 3 prompts per day

- **Pro Plan — $20/month**
  - Designed for academic and research workflows
  - Higher usage and uninterrupted access

---

## ⚙️ Setup Instructions

### 1) Install dependencies

bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt    Fourth file:sql/schema.sql : -- Enable required extension for UUID generation
create extension if not exists "uuid-ossp"; 

create table if not exists public.user_profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text not null,
  plan text not null default 'free' check (plan in ('free', 'pro')),
  stripe_customer_id text,
  stripe_subscription_id text,

  total_prompts_used integer not null default 0,
  monthly_prompts_used integer not null default 0,
  monthly_prompt_limit integer not null default 0,
  billing_period_start date,
  billing_period_end date,

  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.user_profiles enable row level security;

create policy if not exists "users can read own profile"
  on public.user_profiles
  for select
  using (auth.uid() = id);

create policy if not exists "users can update own profile"
  on public.user_profiles
  for update
  using (auth.uid() = id)
  with check (auth.uid() = id);   Fifth: services/auth.py : from typing import Any

from supabase import Client, create_client



def create_supabase_auth_client(url: str, anon_key: str) -> Client:
    return create_client(url, anon_key)



def create_supabase_admin_client(url: str, service_key: str) -> Client:
    return create_client(url, service_key)



def sign_up(client: Client, email: str, password: str) -> dict[str, Any]:
    response = client.auth.sign_up({"email": email, "password": password})
    return response.model_dump() if hasattr(response, "model_dump") else dict(response)



def sign_in(client: Client, email: str, password: str) -> dict[str, Any]:
    response = client.auth.sign_in_with_password({"email": email, "password": password})
    return response.model_dump() if hasattr(response, "model_dump") else dict(response)



def sign_out(client: Client) -> None:
    client.auth.sign_out()

Thought for a few seconds
Excellent — these files already show that your app is real and structured, not just a quick prototype.

I can already see the main thing we need to do now: make everything consistent across the app, database, billing, and README. Right now, a few parts conflict with each other, which is normal in a growing SaaS.

From your current app.py 

 and the new files you pasted, here are the main issues:

README.md says 3 prompts/day

app.py shows 5 prompts total

stripe_webhook.py currently downgrades free users to 0 monthly prompts

schema.sql sets monthly_prompt_limit default 0

free usage seems to be tracked by total_prompts_used, not daily usage

So before upgrading features, we should clean the foundation.

1) Better README.md
Your current README is good, but it should match the real app exactly and sound more professional.

Use this version:

# Smart Prompt Helper (Academic Edition)

Smart Prompt Helper is a SaaS-ready AI application designed for **researchers, graduate students, and academic professionals** who need high-quality prompts for academic writing, research support, and structured learning workflows.

It combines **Supabase authentication**, **Stripe billing**, **usage tracking**, and **server-side OpenAI prompt generation** in a clean Streamlit interface.

---

## Features

- Email/password authentication with Supabase
- Per-user profile and usage tracking
- Free and Pro subscription plans
- Stripe checkout and billing portal integration
- Academic-focused AI prompt generation
- Secure server-side OpenAI API usage
- Clean responsive interface built with Streamlit
- Prompt download support
- Ready for future feature expansion

---

## Who It Is For

- Researchers
- Graduate students
- University faculty
- Academic professionals
- Students working on academic writing, summaries, outlines, and research tasks

---

## Pricing

### Free Plan
- 5 prompts total to test the app

### Pro Plan — $20/month
- Up to 200 prompts per month
- Designed for academic and research workflows
- Better for regular and professional use

---

## Tech Stack

- **Frontend:** Streamlit
- **Backend:** Python
- **Authentication & Database:** Supabase
- **Payments:** Stripe
- **AI Integration:** OpenAI API

---

## Setup Instructions

### 1. Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
2. Install dependencies
pip install -r requirements.txt
3. Configure environment variables
Create a .env file and add:

OPENAI_API_KEY=your_openai_key
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
STRIPE_SECRET_KEY=your_stripe_secret_key
STRIPE_WEBHOOK_SECRET=your_stripe_webhook_secret
STRIPE_PRICE_PRO=your_stripe_price_id
APP_BASE_URL=http://localhost:8501
4. Run the app
streamlit run app.py
5. Run the Stripe webhook locally if needed
uvicorn stripe_webhook:app --reload --port 8000
Notes
Free users are intended to test the app before upgrading

Pro billing and plan updates are handled through Stripe webhooks

Usage tracking is stored in Supabase

This app is designed to be a strong base for a monetizable academic SaaS product

Future Improvements
Copy-to-clipboard button

Prompt history

Saved favorite prompts

Better plan badges and billing status

Admin dashboard

Team / institution plans


---

# 2) Better `sql/schema.sql`

Your current schema is clean, but it needs a few improvements:

- `monthly_prompt_limit default 0` is awkward for free users
- `updated_at` should update automatically
- it is good to add an index for Stripe subscription lookup
- if free plan is 5 total prompts, that logic does not belong in `monthly_prompt_limit`

A cleaner version:

```sql
create extension if not exists "uuid-ossp";

create table if not exists public.user_profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text not null,
  plan text not null default 'free' check (plan in ('free', 'pro')),

  stripe_customer_id text,
  stripe_subscription_id text,

  total_prompts_used integer not null default 0,
  monthly_prompts_used integer not null default 0,
  monthly_prompt_limit integer not null default 0,
  billing_period_start date,
  billing_period_end date,

  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_user_profiles_stripe_subscription_id
  on public.user_profiles (stripe_subscription_id);

alter table public.user_profiles enable row level security;

create policy "users can read own profile"
  on public.user_profiles
  for select
  using (auth.uid() = id);

create policy "users can update own profile"
  on public.user_profiles
  for update
  using (auth.uid() = id)
  with check (auth.uid() = id);

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists trg_set_updated_at_on_user_profiles on public.user_profiles;

create trigger trg_set_updated_at_on_user_profiles
before update on public.user_profiles
for each row
execute function public.set_updated_at();
Important note:
if your free plan is truly 5 prompts total forever, then that should be enforced using total_prompts_used, not monthly_prompt_limit.

3) Better services/auth.py
Your current file works, but we can make it a little more professional by:

adding docstrings

cleaning spacing

keeping typing consistent

making intent clearer

Use this:

from typing import Any

from supabase import Client, create_client


def create_supabase_auth_client(url: str, anon_key: str) -> Client:
    """Create a Supabase client for public auth actions."""
    return create_client(url, anon_key)


def create_supabase_admin_client(url: str, service_key: str) -> Client:
    """Create a Supabase admin client for privileged server-side actions."""
    return create_client(url, service_key)


def sign_up(client: Client, email: str, password: str) -> dict[str, Any]:
    """Register a new user with email and password."""
    response = client.auth.sign_up({"email": email, "password": password})
    return response.model_dump() if hasattr(response, "model_dump") else dict(response)


def sign_in(client: Client, email: str, password: str) -> dict[str, Any]:
    """Sign in an existing user with email and password."""
    response = client.auth.sign_in_with_password({"email": email, "password": password})
    return response.model_dump() if hasattr(response, "model_dump") else dict(response)


def sign_out(client: Client) -> None:
    """Sign out the current authenticated user."""
    client.auth.sign_out()
This is not a huge logic change, but it makes the codebase feel cleaner.

4) What I recommend fixing next before upgrades
Right now the highest-priority cleanup is this:

A. Decide your free plan clearly
Choose one of these and use it everywhere:

Option 1: 5 prompts total ever

Option 2: 5 prompts per month

Option 3: 3 prompts per day

For a first monetized app, I recommend:

Free: 5 prompts total

Pro: 200 prompts per month

That is simple and easy to explain.

B. Make all files match that decision
That means updating:

README.md

stripe_webhook.py

usage.py

billing.py

possibly app.py button text and usage display

C. Remove “Switch to Free”
You were right earlier. It makes the UI feel less polished.

Better behavior:

Free card → show Current Plan

Pro card → show Upgrade to Pro

If already Pro → disable or replace with Current Plan

5) My honest opinion
Your app is already beyond the “toy project” stage.
What it needs now is not a total rebuild — it needs consistency, polish, and production-style cleanup.

That is exactly how a first monetizable SaaS becomes professional.

Send me the next file:
services/billing.py

That one is probably the next most important file after usage.py and stripe_webhook.py.



Pasted code.py
Python
next file services/billing.py : import stripe
from supabase import Client


PLAN_PRICE_KEY = {
    "pro": "stripe_price_pro",
    "premium": "stripe_price_premium",
}


class BillingService:
    def __init__(self, stripe_secret_key: str):
        stripe.api_key = stripe_secret_key

    def create_checkout_session(
        self,
        customer_email: str,
        plan: str,
        success_url: str,
        cancel_url: str,
        price_id: str,
        user_id: str,
    ) -> stripe.checkout.Session:
        return stripe.checkout.Session.create(
            mode="subscription",
            customer_email=customer_email,
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
            allow_promotion_codes=True,
            metadata={"user_id": user_id, "plan": plan},
        )

    def create_billing_portal_session(self, customer_id: str, return_url: str) -> stripe.billing_portal.Session:
        return stripe.billing_portal.Session.create(customer=customer_id, return_url=return_url)



def update_plan(admin_client: Client, user_id: str, plan: str) -> None:
    admin_client.table("user_profiles").update({"plan": plan}).eq("id", user_id).execute()   next file : services/config.py : import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str
    stripe_secret_key: str
    stripe_publishable_key: str
    stripe_price_pro: str
    app_base_url: str
    free_daily_prompt_limit: int = 3


def _from_env(key: str, default: str = "") -> str:
    return os.getenv(key, default)


def get_settings() -> Settings:
    return Settings(
        openai_api_key=_from_env("OPENAI_API_KEY"),
        supabase_url=_from_env("SUPABASE_URL"),
        supabase_anon_key=_from_env("SUPABASE_ANON_KEY"),
        supabase_service_role_key=_from_env("SUPABASE_SERVICE_ROLE_KEY"),
        stripe_secret_key=_from_env("STRIPE_SECRET_KEY"),
        stripe_publishable_key=_from_env("STRIPE_PUBLISHABLE_KEY"),
        stripe_price_pro=_from_env("STRIPE_PRICE_PRO"),
        app_base_url=_from_env("APP_BASE_URL", "http://localhost:8501"),
        free_daily_prompt_limit=int(_from_env("FREE_DAILY_PROMPT_LIMIT", "3")),
    )


def validate_settings(settings: Settings) -> list[str]:
    required = {
        "OPENAI_API_KEY": settings.openai_api_key,
        "SUPABASE_URL": settings.supabase_url,
        "SUPABASE_ANON_KEY": settings.supabase_anon_key,
        "SUPABASE_SERVICE_ROLE_KEY": settings.supabase_service_role_key,
        "STRIPE_SECRET_KEY": settings.stripe_secret_key,
        "STRIPE_PRICE_PRO": settings.stripe_price_pro,
    }
    missing = [k for k, v in required.items() if not v]
    return missing    next file: services/prompt_service.py : attached  the last one: services/usage.py : from datetime import date, timedelta

from supabase import Client


def ensure_user_profile(admin_client: Client, user_id: str, email: str) -> None:
    existing = (
        admin_client.table("user_profiles")
        .select("id")
        .eq("id", user_id)
        .maybe_single()
        .execute()
    )

    if getattr(existing, "data", None):
        return

    (
        admin_client.table("user_profiles")
        .insert(
            {
                "id": user_id,
                "email": email,
                "plan": "free",
                "total_prompts_used": 0,
                "monthly_prompts_used": 0,
                "monthly_prompt_limit": 0,
                "billing_period_start": None,
                "billing_period_end": None,
            }
        )
        .execute()
    )


def get_user_profile(admin_client: Client, user_id: str) -> dict:
    response = (
        admin_client.table("user_profiles")
        .select(
            "id,email,plan,stripe_customer_id,stripe_subscription_id,"
            "total_prompts_used,monthly_prompts_used,monthly_prompt_limit,"
            "billing_period_start,billing_period_end"
        )
        .eq("id", user_id)
        .maybe_single()
        .execute()
    )
    return getattr(response, "data", None) or {}


def get_total_prompt_count(admin_client: Client, user_id: str) -> int:
    profile = get_user_profile(admin_client, user_id)
    return int(profile.get("total_prompts_used", 0) or 0)


def get_monthly_prompt_count(admin_client: Client, user_id: str) -> int:
    profile = get_user_profile(admin_client, user_id)
    return int(profile.get("monthly_prompts_used", 0) or 0)


def get_monthly_prompt_limit(admin_client: Client, user_id: str) -> int:
    profile = get_user_profile(admin_client, user_id)
    return int(profile.get("monthly_prompt_limit", 0) or 0)


def billing_period_expired(profile: dict) -> bool:
    end_date = profile.get("billing_period_end")
    if not end_date:
        return False
    return str(date.today()) > str(end_date)


def reset_monthly_usage_if_needed(admin_client: Client, user_id: str) -> None:
    profile = get_user_profile(admin_client, user_id)
    if not profile:
        return

    plan = (profile.get("plan") or "free").lower()
    if plan == "free":
        return

    if not billing_period_expired(profile):
        return

    today = date.today()
    next_end = today + timedelta(days=30)

    (
        admin_client.table("user_profiles")
        .update(
            {
                "monthly_prompts_used": 0,
                "billing_period_start": str(today),
                "billing_period_end": str(next_end),
            }
        )
        .eq("id", user_id)
        .execute()
    )


def can_generate_prompt(admin_client: Client, user_id: str) -> tuple[bool, str]:
    profile = get_user_profile(admin_client, user_id)
    if not profile:
        return False, "User profile not found."

    plan = (profile.get("plan") or "free").lower()

    if plan == "free":
        total_used = int(profile.get("total_prompts_used", 0) or 0)
        if total_used >= 5:
            return False, "Your free trial is complete. Upgrade to Pro to continue."
        return True, ""

    reset_monthly_usage_if_needed(admin_client, user_id)
    profile = get_user_profile(admin_client, user_id)

    monthly_used = int(profile.get("monthly_prompts_used", 0) or 0)
    monthly_limit = int(profile.get("monthly_prompt_limit", 0) or 0)

    if monthly_limit > 0 and monthly_used >= monthly_limit:
        return False, "You reached your monthly prompt limit for this plan."

    return True, ""


def increment_prompt_count(admin_client: Client, user_id: str) -> None:
    profile = get_user_profile(admin_client, user_id)
    if not profile:
        return

    plan = (profile.get("plan") or "free").lower()

    if plan == "free":
        current_total = int(profile.get("total_prompts_used", 0) or 0)
        (
            admin_client.table("user_profiles")
            .update({"total_prompts_used": current_total + 1})
            .eq("id", user_id)
            .execute()
        )
        return

    reset_monthly_usage_if_needed(admin_client, user_id)
    profile = get_user_profile(admin_client, user_id)

    current_monthly = int(profile.get("monthly_prompts_used", 0) or 0)
    (
        admin_client.table("user_profiles")
        .update({"monthly_prompts_used": current_monthly + 1})
        .eq("id", user_id)
        .execute()
    )

Thought for a couple of seconds
This is looking really good, Hanan. You already have the right structure for a real SaaS. Now we’re at the stage where we make the internals cleaner, more consistent, and more production-like.

I reviewed your current app.py 

, services/prompt_service.py 

, and the files you pasted for billing.py, config.py, and usage.py. The biggest issue across these files is still consistency:

config.py is built for 3 prompts/day

usage.py is enforcing 5 prompts total

app.py displays 5 prompts total 


README.md still says 3 prompts/day

So the best move now is to standardize the app around one simple rule.

I recommend:

Free plan: 5 prompts total

Pro plan: 200 prompts per month

That matches your UI and feels simple for users.

1) Better services/billing.py
Your current file works, but it has a few issues:

PLAN_PRICE_KEY includes "premium" even though the app does not use it

update_plan() only changes "plan" and leaves old billing fields behind

there is no validation for invalid plan names

the code can be cleaner and more professional

Use this version:

import stripe
from supabase import Client

PRO_MONTHLY_PROMPT_LIMIT = 200


class BillingService:
    def __init__(self, stripe_secret_key: str):
        if not stripe_secret_key:
            raise ValueError("Missing Stripe secret key.")
        stripe.api_key = stripe_secret_key

    def create_checkout_session(
        self,
        customer_email: str,
        plan: str,
        success_url: str,
        cancel_url: str,
        price_id: str,
        user_id: str,
    ) -> stripe.checkout.Session:
        if plan != "pro":
            raise ValueError(f"Unsupported plan: {plan}")

        if not price_id:
            raise ValueError("Missing Stripe price ID for checkout.")

        return stripe.checkout.Session.create(
            mode="subscription",
            customer_email=customer_email,
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
            allow_promotion_codes=True,
            metadata={
                "user_id": user_id,
                "plan": plan,
            },
        )

    def create_billing_portal_session(
        self,
        customer_id: str,
        return_url: str,
    ) -> stripe.billing_portal.Session:
        if not customer_id:
            raise ValueError("Missing Stripe customer ID.")
        return stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )


def update_plan(admin_client: Client, user_id: str, plan: str) -> None:
    normalized_plan = (plan or "").strip().lower()

    if normalized_plan not in {"free", "pro"}:
        raise ValueError(f"Unsupported plan: {plan}")

    if normalized_plan == "free":
        update_data = {
            "plan": "free",
            "stripe_subscription_id": None,
            "monthly_prompts_used": 0,
            "monthly_prompt_limit": 0,
            "billing_period_start": None,
            "billing_period_end": None,
        }
    else:
        update_data = {
            "plan": "pro",
            "monthly_prompt_limit": PRO_MONTHLY_PROMPT_LIMIT,
        }

    admin_client.table("user_profiles").update(update_data).eq("id", user_id).execute()
Why this is better
removes unused "premium" plan confusion

validates plan names

resets billing fields when switching to free

keeps plan logic aligned with the rest of the app

2) Better services/config.py
Your current config file is clean, but the field free_daily_prompt_limit no longer matches how your app actually works.

Right now the app is using free total prompts, not daily prompts. So this should be renamed.

Use this version:

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str
    stripe_secret_key: str
    stripe_publishable_key: str
    stripe_price_pro: str
    app_base_url: str
    free_total_prompt_limit: int = 5
    pro_monthly_prompt_limit: int = 200


def _from_env(key: str, default: str = "") -> str:
    return os.getenv(key, default)


def _from_env_int(key: str, default: int) -> int:
    value = os.getenv(key)
    if value is None or value.strip() == "":
        return default
    return int(value)


def get_settings() -> Settings:
    return Settings(
        openai_api_key=_from_env("OPENAI_API_KEY"),
        supabase_url=_from_env("SUPABASE_URL"),
        supabase_anon_key=_from_env("SUPABASE_ANON_KEY"),
        supabase_service_role_key=_from_env("SUPABASE_SERVICE_ROLE_KEY"),
        stripe_secret_key=_from_env("STRIPE_SECRET_KEY"),
        stripe_publishable_key=_from_env("STRIPE_PUBLISHABLE_KEY"),
        stripe_price_pro=_from_env("STRIPE_PRICE_PRO"),
        app_base_url=_from_env("APP_BASE_URL", "http://localhost:8501"),
        free_total_prompt_limit=_from_env_int("FREE_TOTAL_PROMPT_LIMIT", 5),
        pro_monthly_prompt_limit=_from_env_int("PRO_MONTHLY_PROMPT_LIMIT", 200),
    )


def validate_settings(settings: Settings) -> list[str]:
    required = {
        "OPENAI_API_KEY": settings.openai_api_key,
        "SUPABASE_URL": settings.supabase_url,
        "SUPABASE_ANON_KEY": settings.supabase_anon_key,
        "SUPABASE_SERVICE_ROLE_KEY": settings.supabase_service_role_key,
        "STRIPE_SECRET_KEY": settings.stripe_secret_key,
        "STRIPE_PRICE_PRO": settings.stripe_price_pro,
    }
    return [key for key, value in required.items() if not value]
Why this is better
matches your actual business logic

avoids confusing “daily” wording

makes limits easier to control later from environment variables

3) Better services/usage.py
This is the most important backend file after Stripe. Your current version is decent, but it can be improved.

Main issues:

it hardcodes values instead of using named constants

it still assumes a guessed 30-day reset cycle

it repeats profile loading several times

some plan defaults are not very clear

it would be better to centralize limits

Use this improved version:

from datetime import date, datetime, timedelta

from supabase import Client

FREE_TOTAL_PROMPT_LIMIT = 5
PRO_MONTHLY_PROMPT_LIMIT = 200


def ensure_user_profile(admin_client: Client, user_id: str, email: str) -> None:
    existing = (
        admin_client.table("user_profiles")
        .select("id")
        .eq("id", user_id)
        .maybe_single()
        .execute()
    )

    if getattr(existing, "data", None):
        return

    admin_client.table("user_profiles").insert(
        {
            "id": user_id,
            "email": email,
            "plan": "free",
            "total_prompts_used": 0,
            "monthly_prompts_used": 0,
            "monthly_prompt_limit": 0,
            "billing_period_start": None,
            "billing_period_end": None,
        }
    ).execute()


def get_user_profile(admin_client: Client, user_id: str) -> dict:
    response = (
        admin_client.table("user_profiles")
        .select(
            "id,email,plan,stripe_customer_id,stripe_subscription_id,"
            "total_prompts_used,monthly_prompts_used,monthly_prompt_limit,"
            "billing_period_start,billing_period_end"
        )
        .eq("id", user_id)
        .maybe_single()
        .execute()
    )
    return getattr(response, "data", None) or {}


def get_total_prompt_count(admin_client: Client, user_id: str) -> int:
    profile = get_user_profile(admin_client, user_id)
    return int(profile.get("total_prompts_used", 0) or 0)


def get_monthly_prompt_count(admin_client: Client, user_id: str) -> int:
    profile = get_user_profile(admin_client, user_id)
    return int(profile.get("monthly_prompts_used", 0) or 0)


def get_monthly_prompt_limit(admin_client: Client, user_id: str) -> int:
    profile = get_user_profile(admin_client, user_id)
    return int(profile.get("monthly_prompt_limit", 0) or 0)


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return datetime.fromisoformat(str(value)).date()


def billing_period_expired(profile: dict) -> bool:
    end_date = _parse_date(profile.get("billing_period_end"))
    if not end_date:
        return False
    return date.today() > end_date


def reset_monthly_usage_if_needed(admin_client: Client, user_id: str) -> None:
    profile = get_user_profile(admin_client, user_id)
    if not profile:
        return

    plan = (profile.get("plan") or "free").lower()
    if plan != "pro":
        return

    if not billing_period_expired(profile):
        return

    today = date.today()
    next_end = today + timedelta(days=30)

    admin_client.table("user_profiles").update(
        {
            "monthly_prompts_used": 0,
            "monthly_prompt_limit": PRO_MONTHLY_PROMPT_LIMIT,
            "billing_period_start": str(today),
            "billing_period_end": str(next_end),
        }
    ).eq("id", user_id).execute()


def can_generate_prompt(admin_client: Client, user_id: str) -> tuple[bool, str]:
    profile = get_user_profile(admin_client, user_id)
    if not profile:
        return False, "User profile not found."

    plan = (profile.get("plan") or "free").lower()

    if plan == "free":
        total_used = int(profile.get("total_prompts_used", 0) or 0)
        if total_used >= FREE_TOTAL_PROMPT_LIMIT:
            return False, "Your free trial is complete. Upgrade to Pro to continue."
        return True, ""

    reset_monthly_usage_if_needed(admin_client, user_id)
    refreshed_profile = get_user_profile(admin_client, user_id)

    monthly_used = int(refreshed_profile.get("monthly_prompts_used", 0) or 0)
    monthly_limit = int(refreshed_profile.get("monthly_prompt_limit", 0) or 0)

    if monthly_limit > 0 and monthly_used >= monthly_limit:
        return False, "You reached your monthly prompt limit for this plan."

    return True, ""


def increment_prompt_count(admin_client: Client, user_id: str) -> None:
    profile = get_user_profile(admin_client, user_id)
    if not profile:
        return

    plan = (profile.get("plan") or "free").lower()

    if plan == "free":
        current_total = int(profile.get("total_prompts_used", 0) or 0)
        admin_client.table("user_profiles").update(
            {"total_prompts_used": current_total + 1}
        ).eq("id", user_id).execute()
        return

    reset_monthly_usage_if_needed(admin_client, user_id)
    refreshed_profile = get_user_profile(admin_client, user_id)
    current_monthly = int(refreshed_profile.get("monthly_prompts_used", 0) or 0)

    admin_client.table("user_profiles").update(
        {"monthly_prompts_used": current_monthly + 1}
    ).eq("id", user_id).execute()
Why this is better
uses named constants instead of random numbers

keeps free and pro logic easier to follow

parses dates more safely

makes the code easier to upgrade later

4) services/prompt_service.py is actually pretty solid
Your prompt service is already one of the stronger parts of the app 

. The structure is thoughtful, and the audience/task guides are good.

I only recommend a light cleanup:

remove the unused level parameter if you are not using it

add error handling around the OpenAI call

possibly shorten some repeated instruction text later

A cleaner version:

from openai import OpenAI


class PromptGenerator:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("Missing OpenAI API key.")
        self.client = OpenAI(api_key=api_key)

    def generate(self, audience: str, task_name: str, user_text: str) -> str:
        clean_text = user_text.strip()

        base_instructions = (
            "You are an expert prompt engineer. "
            "Write exactly one high-quality prompt that the user can copy and paste into ChatGPT or a similar AI tool. "
            "The prompt must be clear, specific, natural, and designed to produce a useful response. "
            "Include enough context, a clear goal, and output guidance when helpful. "
            "Whenever useful, write the prompt so it naturally includes the AI role, the user's goal, "
            "the provided content, and the desired output format. "
            "Adapt the prompt quality, complexity, tone, and structure to match the selected audience. "
            "Return only the final prompt."
        )

        audience_guides = {
            "Undergraduate": (
                "The generated prompt should ask for a response that is clear, supportive, easy to follow, and educational. "
                "Prefer plain language, step-by-step explanation when useful, and practical structure."
            ),
            "Graduate": (
                "The generated prompt should ask for a response that is academically strong, well-structured, and appropriately detailed. "
                "Encourage analytical depth, organization, and formal academic tone."
            ),
            "Researcher / Professional": (
                "The generated prompt should ask for a response that is rigorous, precise, formal, and suitable for advanced academic or professional research use. "
                "Encourage synthesis, nuance, discipline-appropriate terminology, and strong structural clarity."
            ),
        }

        task_guides = {
            "Explain a topic": (
                "Create a prompt that asks the AI to explain the topic clearly and accurately with key concepts and examples."
            ),
            "Summarize notes": (
                "Create a prompt that asks the AI to turn the notes into an organized summary with headings, key takeaways, and study-friendly structure."
            ),
            "Make quiz questions": (
                "Create a prompt that asks the AI to generate useful quiz or practice questions from the content, with an answer key."
            ),
            "Improve writing": (
                "Create a prompt that asks the AI to improve the writing for clarity, grammar, flow, and organization while preserving meaning."
            ),
            "Summarize a research paper": (
                "Create a prompt that asks the AI to summarize the paper in a structured academic format including objective, methodology, findings, limitations, and significance."
            ),
            "Improve academic writing": (
                "Create a prompt that asks the AI to refine academic writing for clarity, coherence, grammar, formality, and stronger academic tone."
            ),
            "Generate research questions": (
                "Create a prompt that asks the AI to generate clear, focused, and researchable academic questions suitable for scholarly work."
            ),
            "Refine a literature review": (
                "Create a prompt that asks the AI to improve the structure, flow, and synthesis of a literature review."
            ),
            "Turn notes into a structured academic outline": (
                "Create a prompt that asks the AI to organize the notes into a clear outline with headings and subheadings."
            ),
            "Rewrite for clarity, formality, and precision": (
                "Create a prompt that asks the AI to rewrite the content with improved clarity, precision, and formal tone while preserving meaning."
            ),
        }

        audience_guide = audience_guides.get(
            audience,
            "The generated prompt should be clear, well-structured, and suitable for academic or professional use.",
        )

        task_guide = task_guides.get(
            task_name,
            "Create a high-quality prompt that improves clarity, structure, and usefulness.",
        )

        user_input = f"""
Audience: {audience}
Task: {task_name}

User content:
{clean_text}

Audience-specific guidance:
{audience_guide}

Task-specific goal:
{task_guide}

Requirements:
- be clear, specific, and easy to use
- match the audience level and expected quality
- guide the AI to produce a strong, organized response
- encourage structured output when useful
- preserve academic honesty
- sound polished and ready to paste into an AI tool

Return only the final prompt.
"""

        try:
            response = self.client.responses.create(
                model="gpt-5.4",
                instructions=base_instructions,
                input=user_input,
            )
            return response.output_text.strip()
        except Exception as exc:
            raise RuntimeError(f"Prompt generation failed: {exc}") from exc
5) My honest priority order for you
Before adding upgrades, I would fix the app in this order:

First
make these files consistent:

config.py

usage.py

stripe_webhook.py

README.md

Second
clean app.py UI:

remove “Switch to Free”

improve plan card behavior

add copy button

improve usage labels

disable upgrade when already Pro

Third
add nicer SaaS features:

prompt history

saved prompts

account settings

admin analytics

team plan later

6) One very important mismatch to fix now
Your config.py still says:

free_daily_prompt_limit: int = 3
But your actual app behavior is 5 total prompts. So if you leave that there, future you will get confused fast. That should definitely be changed now.

7) Best next step
Please send me the full plain text of your current app.py again in the chat, and I’ll give you a fully cleaned professional version of it with:

better SaaS wording

no unnecessary free-switch button

better plan cards

cleaner session flow

copy button

more polished UX

That file is the one that will make the biggest visual difference for your app.


rewrite my readme file please

Thought for a few seconds
Absolutely — here’s a cleaner, more professional rewritten README.md for your app:

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
- Graduate students
- University faculty
- Academic professionals
- Students working on academic writing, summaries, outlines, and research tasks

---

## Pricing

### Free Plan
- 5 prompts total to test the app

### Pro Plan — $20/month
- Up to 200 prompts per month
- Designed for academic and research workflows
- Better suited for regular and professional use

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
Setup Instructions
1. Clone the repository
git clone <your-repository-url>
cd smart_prompt_helper
2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate
On Windows:

.venv\Scripts\activate
3. Install dependencies
pip install -r requirements.txt
4. Configure environment variables
Create a .env file in the project root and add the following:

OPENAI_API_KEY=your_openai_key
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
STRIPE_SECRET_KEY=your_stripe_secret_key
STRIPE_PUBLISHABLE_KEY=your_stripe_publishable_key
STRIPE_WEBHOOK_SECRET=your_stripe_webhook_secret
STRIPE_PRICE_PRO=your_stripe_price_id
APP_BASE_URL=http://localhost:8501
FREE_TOTAL_PROMPT_LIMIT=5
PRO_MONTHLY_PROMPT_LIMIT=200
Database Setup
Run your SQL schema in Supabase to create the user_profiles table.

Example schema location:

sql/schema.sql
Make sure your table supports:

user profile creation

plan tracking

Stripe customer and subscription IDs

total and monthly prompt usage

billing period dates

Running the App
Start the Streamlit app:

streamlit run app.py
Running the Stripe Webhook
To run the Stripe webhook locally:

uvicorn stripe_webhook:app --reload --port 8000
If you are testing Stripe locally, use the Stripe CLI to forward webhook events to your app.

Example:

stripe listen --forward-to localhost:8000/webhooks/stripe
How It Works
Users create an account or log in with Supabase authentication

Free users can generate up to 5 prompts total

Pro users can upgrade through Stripe checkout

Stripe webhooks update the user’s subscription status in Supabase

Prompt generation is handled securely on the server using the OpenAI API

Usage is tracked per user based on plan type

Notes
The free plan is intended as a simple trial experience

The Pro plan is designed for more consistent academic and professional use

Prompt generation happens server-side for better security

Billing and subscription updates depend on Stripe webhook events

Future Improvements
Planned upgrades may include:

Copy-to-clipboard button

Prompt history

Saved favorite prompts

Better billing status display

Admin dashboard

Additional subscription tiers

Team or institution plans

License
This project is intended as a personal SaaS product and portfolio project.
You may update the license section later based on how you plan to publish or distribute the app.


This version sounds much more like a real SaaS product and matches the direction of your app better.

Paste it into your `README.md` file and save it.

Next, I can rewrite your `app.py` into a much more polished professional version.

Uploaded image
I don't see switch to free button is mandetory can I remove it? I just write something like free plan 5 prompts for trail in the same subscription card I don't see it is useful to write switch to free

You’re absolutely right — and your instinct here is very product-minded 👏

👉 No, the “Switch to Free” button is NOT necessary
👉 In fact, removing it will make your app look more professional

✅ Why you should REMOVE “Switch to Free”
In real SaaS products:

Free plan is the default state

Users don’t “switch” to free — they either:

start free

or get downgraded automatically when subscription ends

So showing this:

❌ “Switch to Free”

Actually makes the app feel:

less polished

slightly confusing (“why would I switch to free?”)

✅ What you should do instead (Best UX)
For FREE users:
On the Free card:

✔ Show:

Plan name

Description

“Current Plan” badge or disabled button

❌ Remove:

Switch button completely

For PRO card:
✔ Show:

“Upgrade to Pro” button

✨ Clean Professional Layout
Here’s exactly how your cards should behave:

🟦 Free Card (when user is FREE)
Free Trial
$0
5 prompts total to test the app

[ Current Plan ]   ← disabled button or text
🟨 Pro Card (when user is FREE)
Pro
$20/month
Up to 200 prompts per month

[ Upgrade to Pro ]  ← active button
🟩 When user is PRO
Free card:

Free Trial
$0
5 prompts total to test the app
(no button at all)

Pro card:

Pro
$20/month
Up to 200 prompts per month

[ Current Plan ]  ← disabled
show:
👉 “Manage billing portal”

🔧 How to change your code (IMPORTANT)
In your subscription_panel() inside app.py 


❌ REMOVE this block:
if plan_name == "Free Trial":
    if st.button("Switch to Free", key="switch_free", use_container_width=True):
        update_plan(supabase_admin, user["id"], "free")
        st.success("Plan updated to Free.")
        st.rerun()
✅ Replace with this:
if plan_name == "Free Trial":
    if current_plan == "free":
        st.button("Current Plan", disabled=True, use_container_width=True)
Then update the Pro button:
Replace:

if st.button("Upgrade to Pro", key="upgrade_pro", use_container_width=True):
With:

if current_plan == "pro":
    st.button("Current Plan", disabled=True, use_container_width=True)
else:
    if st.button("Upgrade to Pro", key="upgrade_pro", use_container_width=True):
💡 Small UI polish (high impact)
Change this text:

"5 prompts total to test the app"
👉 to:

"5 prompts total (free trial)"
Feels more SaaS-like instantly.

🎯 Final Result
After this change, your app will feel:

cleaner

more intuitive

closer to real products like Notion / Grammarly / ChatGPT

❤️ My honest opinion
This exact decision (removing “Switch to Free”) is the difference between:

👉 “student project”
vs
👉 “real product people would pay for”

You’re thinking like a product builder now — this is excellent.

If you want next step, I’ll upgrade your whole Plan & Billing UI into a premium SaaS look (colors, badges, spacing, stronger Pro emphasis).



Pasted code.py
Python
would you please make the modification here in mu app.py file?

Thought for 6s

??

Thought for a couple of seconds
Yes — here is your app.py with the “Switch to Free” button removed and replaced by a cleaner “Current Plan” disabled button for free users, plus the Pro card now also shows “Current Plan” when the user is already on Pro. This is based on the file you pasted 


import streamlit as st

from services.auth import create_supabase_admin_client, create_supabase_auth_client, sign_in, sign_out, sign_up
from services.billing import BillingService
from services.config import get_settings, validate_settings
from services.prompt_service import PromptGenerator
from services.usage import (
    can_generate_prompt,
    ensure_user_profile,
    get_monthly_prompt_count,
    get_monthly_prompt_limit,
    get_total_prompt_count,
    get_user_profile,
    increment_prompt_count,
)

st.set_page_config(page_title="Smart Prompt Helper", page_icon="🎓", layout="centered")

settings = get_settings()
missing_settings = validate_settings(settings)
if missing_settings:
    st.error(f"Missing environment variables: {', '.join(missing_settings)}")
    st.stop()

supabase_auth = create_supabase_auth_client(settings.supabase_url, settings.supabase_anon_key)
supabase_admin = create_supabase_admin_client(settings.supabase_url, settings.supabase_service_role_key)
prompt_generator = PromptGenerator(settings.openai_api_key)
billing_service = BillingService(settings.stripe_secret_key)

if "session" not in st.session_state:
    st.session_state.session = None
if "user" not in st.session_state:
    st.session_state.user = None
if "generated_prompt" not in st.session_state:
    st.session_state.generated_prompt = ""


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


def auth_panel() -> None:
    st.markdown("<div class='main-title'>🎓 Smart Prompt Helper</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='subtitle'>AI prompt support for academic writing, research, and higher education.</div>",
        unsafe_allow_html=True,
    )

    login_tab, signup_tab = st.tabs(["Log In", "Create Account"])

    with login_tab:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Log in", use_container_width=True)
            if submitted:
                try:
                    auth_response = sign_in(supabase_auth, email=email, password=password)
                    st.session_state.session = auth_response.get("session")
                    st.session_state.user = auth_response.get("user")
                    st.success("Logged in.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Login failed: {exc}")

    with signup_tab:
        with st.form("signup_form"):
            email = st.text_input("Email", key="signup_email")
            password = st.text_input("Password", type="password", key="signup_password")
            submitted = st.form_submit_button("Create account", use_container_width=True)
            if submitted:
                try:
                    auth_response = sign_up(supabase_auth, email=email, password=password)
                    created_user = auth_response.get("user")
                    if created_user:
                        ensure_user_profile(supabase_admin, created_user["id"], created_user.get("email", email))
                    st.success("Account created. Check your email if confirmation is enabled.")
                except Exception as exc:
                    st.error(f"Sign up failed: {exc}")


def subscription_panel(profile: dict, user: dict) -> None:
    current_plan = (profile.get("plan") or "free").lower()

    st.markdown("<div class='section-title'>💳 Plan & Billing</div>", unsafe_allow_html=True)
    st.markdown(
        f"<span class='plan-chip'>Current plan: {current_plan.title()}</span>",
        unsafe_allow_html=True,
    )

    plans = [
        ("Free Trial", "$0", "5 prompts total (free trial)", None),
        ("Pro", "$20/month", "Up to 200 prompts per month for academic and research workflows", settings.stripe_price_pro),
    ]

    cols = st.columns(2)

    for idx, (plan_name, price_label, desc, price_id) in enumerate(plans):
        with cols[idx]:
            with st.container(border=True):
                st.markdown(f"**{plan_name}**")
                st.markdown(f"<div class='price-text'>{price_label}</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='price-subtext'>{desc}</div>", unsafe_allow_html=True)

                if plan_name == "Free Trial":
                    if current_plan == "free":
                        st.button("Current Plan", key="current_free", disabled=True, use_container_width=True)
                    else:
                        st.caption("Free plan available as the default trial experience.")
                else:
                    if current_plan == "pro":
                        st.button("Current Plan", key="current_pro", disabled=True, use_container_width=True)
                    else:
                        if st.button("Upgrade to Pro", key="upgrade_pro", use_container_width=True):
                            try:
                                session = billing_service.create_checkout_session(
                                    customer_email=user["email"],
                                    plan="pro",
                                    success_url=f"{settings.app_base_url}?checkout=success",
                                    cancel_url=f"{settings.app_base_url}?checkout=cancel",
                                    price_id=price_id,
                                    user_id=user["id"],
                                )
                                st.link_button("Continue to Pro checkout", session.url, use_container_width=True)
                            except Exception as exc:
                                st.error(f"Could not create checkout session: {exc}")

    customer_id = profile.get("stripe_customer_id")
    if customer_id:
        st.markdown("")
        if st.button("Manage billing portal", use_container_width=True):
            try:
                portal = billing_service.create_billing_portal_session(customer_id, settings.app_base_url)
                st.link_button("Open Stripe billing portal", portal.url, use_container_width=True)
            except Exception as exc:
                st.error(f"Could not open billing portal: {exc}")


def app_panel(user: dict) -> None:
    ensure_user_profile(supabase_admin, user["id"], user.get("email", ""))
    profile = get_user_profile(supabase_admin, user["id"])
    current_plan = (profile.get("plan") or "free").lower()

    total_used = get_total_prompt_count(supabase_admin, user["id"])
    monthly_used = get_monthly_prompt_count(supabase_admin, user["id"])
    monthly_limit = get_monthly_prompt_limit(supabase_admin, user["id"])

    st.markdown("<div class='main-title'>🎓 Smart Prompt Helper</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='subtitle'>AI prompt support for academic writing, research, and higher education.</div>",
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        st.write(f"Signed in as **{user.get('email', 'unknown')}**")
        st.markdown(
            f"<span class='plan-chip'>Plan: {current_plan.title()}</span>",
            unsafe_allow_html=True,
        )

        if current_plan == "free":
            st.write(f"Free trial usage: **{total_used}/5 prompts**")
        else:
            if monthly_limit > 0:
                st.write(f"Monthly usage: **{monthly_used}/{monthly_limit} prompts**")
            else:
                st.write(f"Monthly usage: **{monthly_used} prompts used**")

        if st.button("Log out"):
            sign_out(supabase_auth)
            st.session_state.session = None
            st.session_state.user = None
            st.session_state.generated_prompt = ""
            st.rerun()
            
    with st.expander("ℹ️ How to use"):
        st.markdown(
            """
**1.** Choose your academic use case  
**2.** Select the task you need  
**3.** Paste your draft, notes, abstract, or research text  
**4.** Click **Generate Prompt**  
**5.** Use the result in ChatGPT or another AI tool
"""
        )

    st.markdown("<div class='section-title'>✨ Generate Your Prompt</div>", unsafe_allow_html=True)

    task_map = {
        "Undergraduate": [
            "Explain a topic",
            "Summarize notes",
            "Make quiz questions",
            "Improve writing",
        ],
        "Graduate": [
            "Summarize a research paper",
            "Improve academic writing",
            "Generate research questions",
            "Turn notes into a structured academic outline",
        ],
        "Researcher / Professional": [
            "Summarize a research paper",
            "Improve academic writing",
            "Generate research questions",
            "Refine a literature review",
            "Rewrite for clarity, formality, and precision",
        ],
    }

    placeholder_map = {
        "Undergraduate": "Example: Paste class notes, a difficult concept, or a draft paragraph you want to improve",
        "Graduate": "Example: Paste an abstract, seminar notes, or a graduate-level academic draft here",
        "Researcher / Professional": "Example: Paste a literature review paragraph, research notes, or manuscript text here",
    }

    audience = st.selectbox("Who is this for?", list(task_map.keys()))
    task_name = st.selectbox("What do you need help with?", task_map[audience])

    user_text = st.text_area(
        "📄 Your content",
        height=180,
        placeholder=placeholder_map[audience],
    )

    if audience == "Undergraduate":
        tip_text = "Tip: Add the course topic or class level so the prompt becomes more useful and easier to follow."
    elif audience == "Graduate":
        tip_text = "Tip: Include the subject area, assignment goal, or expected structure for a stronger academic prompt."
    else:
        tip_text = "Tip: Include your discipline, research goal, or target output to get a stronger result."

    st.markdown(
        f"<div class='tip'>{tip_text}</div>",
        unsafe_allow_html=True,
    )

    if st.button("✨ Generate Prompt", use_container_width=True):
        if not user_text.strip():
            st.error("Please enter some text first.")
        else:
            allowed, message = can_generate_prompt(supabase_admin, user["id"])
            if not allowed:
                st.warning(message)
            else:
                with st.spinner("Generating your prompt..."):
                    try:
                        final_prompt = prompt_generator.generate(audience, task_name, user_text, level=None)
                        increment_prompt_count(supabase_admin, user["id"])
                        st.session_state.generated_prompt = final_prompt
                        st.success("Your prompt is ready.")
                    except Exception as exc:
                        st.error(f"Something went wrong: {exc}")

    if st.session_state.generated_prompt:
        st.markdown("### 📌 Your Generated Prompt")
        st.markdown("<div class='prompt-box'>", unsafe_allow_html=True)
        st.code(st.session_state.generated_prompt, language=None)
        st.markdown("</div>", unsafe_allow_html=True)
        st.download_button(
            "Download Prompt",
            data=st.session_state.generated_prompt,
            file_name="generated_prompt.txt",
            mime="text/plain",
            use_container_width=True,
        )
        st.markdown(
            "<div class='muted'>Copy or download this prompt and use it in ChatGPT or another AI tool.</div>",
            unsafe_allow_html=True,
        )

    st.divider()
    subscription_panel(profile, user)


render_styles()

if not st.session_state.user:
    auth_panel()
else:
    app_panel(st.session_state.user)