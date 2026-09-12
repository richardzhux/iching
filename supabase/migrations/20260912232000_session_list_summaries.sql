-- Project list metadata inside PostgreSQL so snapshots and AI prose never
-- traverse the Data API merely to populate session history. Full summaries
-- remain available because the history drawer renders them directly.
create or replace function public.list_session_summaries(p_user_id uuid)
returns jsonb
language sql stable security invoker
set search_path = ''
as $$
  with contexts as (
    select
      s.session_id,
      s.summary_text,
      coalesce(s.created_at, s.updated_at) as created_at,
      s.updated_at,
      coalesce(s.initial_ai_text <> '', false) as ai_enabled,
      case
        when jsonb_typeof(s.payload_snapshot -> 'session_dict') = 'object'
          then s.payload_snapshot -> 'session_dict'
        -- Legacy SessionResult snapshots stored the context at the root.
        when jsonb_typeof(s.payload_snapshot) = 'object'
          and s.payload_snapshot ?| array[
            'topic', 'user_question', 'current_time_str', 'method', 'lines',
            'hex_text', 'bazi_output', 'elements_output', 'najia_data'
          ]
          then s.payload_snapshot
        else null
      end as session_context
    from public.sessions s
    where s.user_id = p_user_id
  )
  select jsonb_build_object(
    'sessions', coalesce(jsonb_agg(jsonb_build_object(
      'session_id', session_id,
      'summary_text', summary_text,
      'created_at', created_at,
      'ai_enabled', ai_enabled,
      'followup_available', session_context is not null,
      'topic_label', case when jsonb_typeof(session_context -> 'topic') = 'string'
        then session_context ->> 'topic' end,
      'method_label', case when jsonb_typeof(session_context -> 'method') = 'string'
        then session_context ->> 'method' end
    ) order by updated_at desc), '[]'::jsonb)
  )
  from contexts;
$$;

revoke all on function public.list_session_summaries(uuid) from public, anon, authenticated;
grant execute on function public.list_session_summaries(uuid) to service_role;
notify pgrst, 'reload schema';
