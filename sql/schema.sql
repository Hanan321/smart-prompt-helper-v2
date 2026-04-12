-- Enable required extension for UUID generation (optional if already enabled)
create extension if not exists "uuid-ossp";

create table if not exists public.user_profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text not null,
  plan text not null default 'free' check (plan in ('free', 'pro', 'premium')),
  stripe_customer_id text,
  stripe_subscription_id text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.daily_usage (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid not null references auth.users(id) on delete cascade,
  usage_date date not null,
  prompt_count integer not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, usage_date)
);

alter table public.user_profiles enable row level security;
alter table public.daily_usage enable row level security;

create policy if not exists "users can read own profile"
  on public.user_profiles
  for select
  using (auth.uid() = id);

create policy if not exists "users can update own profile"
  on public.user_profiles
  for update
  using (auth.uid() = id)
  with check (auth.uid() = id);

create policy if not exists "users can read own usage"
  on public.daily_usage
  for select
  using (auth.uid() = user_id);

-- Optional RPC for atomic usage increment
create or replace function public.increment_prompt_usage(p_user_id uuid)
returns void
language plpgsql
security definer
as $$
begin
  insert into public.daily_usage (user_id, usage_date, prompt_count)
  values (p_user_id, current_date, 1)
  on conflict (user_id, usage_date)
  do update set
    prompt_count = public.daily_usage.prompt_count + 1,
    updated_at = now();
end;
$$;
