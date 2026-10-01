-- Reconcile abandoned operations before same-ID replay; retain their reservation.
create or replace function public.admit_ai_operation(
 p_user_id uuid,p_request_id uuid,p_session_id uuid,p_kind text,p_fingerprint text,
 p_reserve bigint,p_daily_limit bigint,p_session_limit bigint,p_turn_limit integer,
 p_initial_limit integer,p_global_limit bigint default 0
) returns jsonb language plpgsql set search_path='' as $$
declare op public.ai_operations; spent bigint; used bigint; turns integer; today timestamptz := date_trunc('day',now() at time zone 'UTC') at time zone 'UTC';
begin
 if p_reserve <= 0 or p_daily_limit <= 0 or p_session_limit <= 0 or p_turn_limit <= 0 then raise exception 'Invalid AI budget'; end if;
 -- Short database transaction serializes admission/settlement across all workers.
 perform pg_advisory_xact_lock(482019260912);
 -- A crashed worker's reservation stays charged; expiration never grants a free retry.
 update public.ai_operations set status='uncertain',updated_at=now() where status='pending' and created_at < now()-interval '15 minutes';
 select * into op from public.ai_operations where user_id=p_user_id and request_id=p_request_id for update;
 if found then
  if op.fingerprint<>p_fingerprint or op.kind<>p_kind or op.session_id is distinct from p_session_id then return jsonb_build_object('status','conflict'); end if;
  return jsonb_build_object('status',op.status,'result',op.result);
 end if;
 if p_kind='chat' then
  select tokens_used,chat_turns into used,turns from public.sessions where user_id=p_user_id and session_id=p_session_id for update;
  if not found then return jsonb_build_object('status','missing'); end if;
  if exists(select 1 from public.ai_operations where user_id=p_user_id and session_id=p_session_id and status='pending') then return jsonb_build_object('status','busy'); end if;
  select coalesce(sum(reserved_tokens),0) into spent from public.ai_operations where user_id=p_user_id and session_id=p_session_id and status='uncertain';
  if used+spent+p_reserve>p_session_limit or turns>=p_turn_limit then return jsonb_build_object('status','session_limit'); end if;
 elsif p_kind='initial' then
  if p_initial_limit>0 and (select count(*) from public.ai_operations where user_id=p_user_id and kind='initial' and created_at>=today and status<>'failed')>=p_initial_limit then return jsonb_build_object('status','daily_limit'); end if;
 else raise exception 'Invalid operation kind'; end if;
 select coalesce(sum(actual_tokens+reserved_tokens),0) into spent from public.ai_operations where user_id=p_user_id and created_at>=today;
 if spent+p_reserve>p_daily_limit then return jsonb_build_object('status','daily_limit'); end if;
 if p_global_limit>0 then
  select coalesce(sum(actual_tokens+reserved_tokens),0) into spent from public.ai_operations where created_at>=today;
  if spent+p_reserve>p_global_limit then return jsonb_build_object('status','global_limit'); end if;
 end if;
 insert into public.ai_operations(user_id,request_id,session_id,kind,fingerprint,reserved_tokens) values(p_user_id,p_request_id,p_session_id,p_kind,p_fingerprint,p_reserve);
 return jsonb_build_object('status','admitted');
end $$;

notify pgrst,'reload schema';
