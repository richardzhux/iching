-- Private, owner-scoped metaphysics archive and production permission hardening.

create extension if not exists "pgcrypto";

-- New objects in public are private until a migration grants the exact access needed.
alter default privileges for role postgres in schema public
  revoke select, insert, update, delete, truncate, references, trigger on tables
  from anon, authenticated, service_role;
alter default privileges for role postgres in schema public
  revoke usage, select, update on sequences
  from anon, authenticated, service_role;
alter default privileges for role postgres in schema public
  revoke execute on functions from public, anon, authenticated, service_role;

create schema if not exists private;
revoke all on schema private from public, anon, authenticated;

create or replace function private.set_updated_at()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  new.updated_at = timezone('utc', now());
  return new;
end;
$$;

revoke all on function private.set_updated_at() from public, anon, authenticated, service_role;

-- Existing rows already satisfy these invariants; make the contract explicit.
alter table public.sessions
  alter column chat_turns set not null,
  alter column tokens_used set not null,
  alter column created_at set not null,
  alter column updated_at set not null;

alter table public.chat_messages
  alter column tokens_in set not null,
  alter column tokens_out set not null,
  alter column created_at set not null;

drop index if exists public.idx_sessions_user;
create index if not exists idx_sessions_owner_recent
  on public.sessions (user_id, updated_at desc, session_id);
create index if not exists idx_chat_messages_owner_transcript
  on public.chat_messages (user_id, session_id, created_at, id);

drop trigger if exists sessions_set_updated_at on public.sessions;
create trigger sessions_set_updated_at
before update on public.sessions
for each row execute function private.set_updated_at();

create table public.chart_subjects (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  display_name text,
  birth_local_timestamp timestamp without time zone not null,
  timezone text not null,
  utc_offset_minutes smallint not null,
  calendar_type text not null default 'solar',
  gender text,
  birth_place text,
  location_id text,
  latitude numeric(9, 6),
  longitude numeric(9, 6),
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  constraint chart_subjects_owner_identity unique (id, user_id),
  constraint chart_subjects_display_name_length check (display_name is null or char_length(display_name) <= 80),
  constraint chart_subjects_timezone_length check (char_length(timezone) between 1 and 80),
  constraint chart_subjects_utc_offset_range check (utc_offset_minutes between -840 and 840),
  constraint chart_subjects_calendar_type_check check (calendar_type in ('solar', 'lunar')),
  constraint chart_subjects_gender_check check (gender is null or gender in ('male', 'female')),
  constraint chart_subjects_latitude_range check (latitude is null or latitude between -90 and 90),
  constraint chart_subjects_longitude_range check (longitude is null or longitude between -180 and 180)
);

create table public.metaphysics_charts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  subject_id uuid not null,
  chart_type text not null,
  title text,
  birth_date date not null,
  day_pillar text,
  input_snapshot jsonb not null,
  result_snapshot jsonb not null,
  engine_name text not null,
  engine_version text not null,
  rules_version text not null,
  schema_version smallint not null default 1,
  pinned boolean not null default false,
  last_opened_at timestamptz not null default timezone('utc', now()),
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  constraint metaphysics_charts_subject_owner_fk
    foreign key (subject_id, user_id)
    references public.chart_subjects (id, user_id)
    on delete cascade,
  constraint metaphysics_charts_type_check check (chart_type in ('bazi', 'ziwei')),
  constraint metaphysics_charts_title_length check (title is null or char_length(title) <= 120),
  constraint metaphysics_charts_day_pillar_length check (day_pillar is null or char_length(day_pillar) <= 16),
  constraint metaphysics_charts_input_object check (jsonb_typeof(input_snapshot) = 'object'),
  constraint metaphysics_charts_result_object check (jsonb_typeof(result_snapshot) = 'object'),
  constraint metaphysics_charts_schema_version_check check (schema_version > 0)
);

create index idx_chart_subjects_owner_recent
  on public.chart_subjects (user_id, updated_at desc, id);
create index idx_metaphysics_charts_owner_recent
  on public.metaphysics_charts (user_id, updated_at desc, id);
create index idx_metaphysics_charts_owner_type_recent
  on public.metaphysics_charts (user_id, chart_type, updated_at desc, id);
create index idx_metaphysics_charts_subject_owner
  on public.metaphysics_charts (subject_id, user_id);

drop trigger if exists chart_subjects_set_updated_at on public.chart_subjects;
create trigger chart_subjects_set_updated_at
before update on public.chart_subjects
for each row execute function private.set_updated_at();

drop trigger if exists metaphysics_charts_set_updated_at on public.metaphysics_charts;
create trigger metaphysics_charts_set_updated_at
before update on public.metaphysics_charts
for each row execute function private.set_updated_at();

alter table public.chart_subjects enable row level security;
alter table public.metaphysics_charts enable row level security;

create policy chart_subjects_owner_select on public.chart_subjects
  for select to authenticated
  using ((select auth.uid()) = user_id);
create policy chart_subjects_owner_insert on public.chart_subjects
  for insert to authenticated
  with check ((select auth.uid()) = user_id);
create policy chart_subjects_owner_update on public.chart_subjects
  for update to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);
create policy chart_subjects_owner_delete on public.chart_subjects
  for delete to authenticated
  using ((select auth.uid()) = user_id);

create policy metaphysics_charts_owner_select on public.metaphysics_charts
  for select to authenticated
  using ((select auth.uid()) = user_id);
create policy metaphysics_charts_owner_insert on public.metaphysics_charts
  for insert to authenticated
  with check ((select auth.uid()) = user_id);
create policy metaphysics_charts_owner_update on public.metaphysics_charts
  for update to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);
create policy metaphysics_charts_owner_delete on public.metaphysics_charts
  for delete to authenticated
  using ((select auth.uid()) = user_id);

-- The browser uses Supabase for Auth only. All table access is mediated by FastAPI.
revoke all privileges on table public.sessions, public.chat_messages,
  public.chart_subjects, public.metaphysics_charts
  from anon, authenticated, service_role;
grant select, insert, update, delete on table public.sessions, public.chat_messages,
  public.chart_subjects, public.metaphysics_charts
  to service_role;

revoke all on function public.purge_old_sessions() from public, anon, authenticated, service_role;

notify pgrst, 'reload schema';
