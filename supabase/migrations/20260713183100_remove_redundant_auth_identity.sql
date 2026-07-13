-- Apply after the backend no longer writes duplicated Supabase Auth profile fields.

alter table public.sessions
  drop column if exists user_email,
  drop column if exists user_display_name,
  drop column if exists user_avatar_url;

alter table public.chat_messages
  drop column if exists user_email,
  drop column if exists user_display_name,
  drop column if exists user_avatar_url;

notify pgrst, 'reload schema';
