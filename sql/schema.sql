create table if not exists public.user_profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text not null,
  username text not null,
  plan text not null default 'free' check (plan in ('free', 'pro')),
  stripe_customer_id text,
  stripe_subscription_id text,
  subscription_status text,
  cancel_at_period_end boolean not null default false,

  total_prompts_used integer not null default 0,
  monthly_prompts_used integer not null default 0,
  monthly_prompt_limit integer not null default 0,
  billing_period_start date,
  billing_period_end date,

  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table if exists public.user_profiles
  add column if not exists subscription_status text;

alter table if exists public.user_profiles
  add column if not exists cancel_at_period_end boolean not null default false;

create table if not exists public.user_billing (
  user_id uuid not null references auth.users(id) on delete cascade,
  environment text not null check (environment in ('test', 'live')),
  plan text not null default 'free' check (plan in ('free', 'pro')),
  subscription_status text,
  stripe_customer_id text,
  stripe_subscription_id text,
  cancel_at_period_end boolean not null default false,
  current_period_end date,
  credit_balance integer not null default 0,
  total_credits_purchased integer not null default 0,
  monthly_prompts_used integer not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (user_id, environment)
);

create unique index if not exists user_billing_user_environment_idx
  on public.user_billing (user_id, environment);

alter table if exists public.user_billing
  add column if not exists credit_balance integer not null default 0;

alter table if exists public.user_billing
  add column if not exists total_credits_purchased integer not null default 0;

alter table if exists public.user_billing
  add column if not exists monthly_prompts_used integer not null default 0;

create table if not exists public.prompt_credit_purchases (
  environment text not null check (environment in ('test', 'live')),
  stripe_checkout_session_id text not null,
  user_id uuid not null references auth.users(id) on delete cascade,
  credits integer not null check (credits > 0),
  created_at timestamptz not null default now(),
  primary key (environment, stripe_checkout_session_id)
);

create or replace function public.grant_prompt_pack_credits(
  p_user_id uuid,
  p_environment text,
  p_checkout_session_id text,
  p_credits integer,
  p_stripe_customer_id text default null
)
returns boolean
language plpgsql
security definer
as $$
begin
  if p_environment not in ('test', 'live') then
    raise exception 'Invalid billing environment';
  end if;

  insert into public.prompt_credit_purchases (
    environment,
    stripe_checkout_session_id,
    user_id,
    credits
  )
  values (
    p_environment,
    p_checkout_session_id,
    p_user_id,
    p_credits
  )
  on conflict do nothing;

  if not found then
    return false;
  end if;

  insert into public.user_billing (
    user_id,
    environment,
    plan,
    stripe_customer_id,
    credit_balance,
    total_credits_purchased,
    monthly_prompts_used
  )
  values (
    p_user_id,
    p_environment,
    'free',
    p_stripe_customer_id,
    p_credits,
    p_credits,
    0
  )
  on conflict (user_id, environment) do update
  set
    stripe_customer_id = coalesce(
      public.user_billing.stripe_customer_id,
      excluded.stripe_customer_id
    ),
    credit_balance = public.user_billing.credit_balance + excluded.credit_balance,
    total_credits_purchased = public.user_billing.total_credits_purchased + excluded.total_credits_purchased,
    updated_at = now();

  return true;
end;
$$;







-- 1. Create a function that inserts a row into public.user_profiles
create or replace function public.handle_new_user()
returns trigger as $$
begin
  insert into public.user_profiles (id, email, username, plan)
  values (
    new.id, 
    new.email, 
    coalesce(new.raw_user_meta_data->>'username', 'User'), 
    'free'
  );
  return new;
end;
$$ language plpgsql security definer;

-- 2. Create the trigger that calls the function after every signup
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();
