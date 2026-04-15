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
