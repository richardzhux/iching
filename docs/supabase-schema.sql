-- Enable pgcrypto so `gen_random_uuid()` is available.
create extension if not exists "pgcrypto";

-- Sessions table stores one row per I Ching reading.
-- Anonymous sessions use a placeholder user_id (default 00000000-0000-0000-0000-000000000000)
-- until the user logs in, at which point the row is reassigned.
create table if not exists public.sessions (
  session_id uuid not null,
  user_id uuid not null,
  last_response_id text,
  ai_model text,
  followup_model text,
  ai_reasoning text,
  ai_verbosity text,
  ai_tone text,
  chat_turns integer default 0,
  tokens_used integer default 0,
  summary_text text,
  initial_ai_text text,
  payload_snapshot jsonb,
  user_email text,
  user_display_name text,
  user_avatar_url text,
  created_at timestamptz default timezone('utc', now()),
  updated_at timestamptz default timezone('utc', now()),
  primary key (session_id, user_id)
);

create index if not exists idx_sessions_user on public.sessions (user_id);

-- Chat transcript, one row per message (user + assistant).
create table if not exists public.chat_messages (
  id uuid not null default gen_random_uuid(),
  session_id uuid not null,
  user_id uuid not null,
  role text not null check (role in ('user', 'assistant')),
  content text not null,
  tokens_in integer default 0,
  tokens_out integer default 0,
  model text,
  reasoning text,
  verbosity text,
  tone text,
  user_email text,
  user_display_name text,
  user_avatar_url text,
  created_at timestamptz default timezone('utc', now()),
  primary key (id),
  constraint fk_chat_session foreign key (session_id, user_id)
    references public.sessions (session_id, user_id)
    on delete cascade
);

create index if not exists idx_chat_messages_session on public.chat_messages (session_id, created_at);

-- Existing deployments: run these ALTER statements in Supabase SQL Editor to add metadata columns.
alter table public.chat_messages add column if not exists model text null;
alter table public.chat_messages add column if not exists reasoning text null;
alter table public.chat_messages add column if not exists verbosity text null;
alter table public.chat_messages add column if not exists tone text null;

-- Periodic cleanup: delete sessions older than 90 days (chat_messages are cascaded).
create or replace function public.purge_old_sessions() returns void
language plpgsql
as $$
begin
  delete from public.sessions
  where updated_at < timezone('utc', now()) - interval '90 days';
end;
$$;

-- Schedule the cleanup daily at 03:00 UTC. Requires Supabase pg_cron (available on Free & Pro tiers).
select
  cron.schedule(
    'purge-old-sessions',
    '0 4 * * *',
    $$
      select public.purge_old_sessions();
    $$
  );
