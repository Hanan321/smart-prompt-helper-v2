-- Enable required extension for UUID generation
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
  with check (auth.uid() = id);