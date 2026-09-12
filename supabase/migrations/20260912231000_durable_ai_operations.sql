-- Durable, server-only AI admission and accounting. No browser grants.
create table public.ai_operations (
 user_id uuid not null references auth.users(id) on delete cascade,
 request_id uuid not null,
 session_id uuid,
 kind text not null check(kind in ('initial','chat')),
 fingerprint text not null,
 status text not null default 'pending' check(status in ('pending','completed','failed','uncertain')),
 reserved_tokens bigint not null check(reserved_tokens >= 0),
 actual_tokens bigint not null default 0 check(actual_tokens >= 0),
 result jsonb,
 created_at timestamptz not null default now(),
 updated_at timestamptz not null default now(),
 primary key(user_id,request_id)
);
alter table public.ai_operations enable row level security;
revoke all on public.ai_operations from public,anon,authenticated;
grant select,insert,update,delete on public.ai_operations to service_role;
create index ai_operations_daily on public.ai_operations(user_id,created_at);
create index ai_operations_pending_session on public.ai_operations(user_id,session_id) where status='pending';

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
 select * into op from public.ai_operations where user_id=p_user_id and request_id=p_request_id for update;
 if found then
  if op.fingerprint<>p_fingerprint or op.kind<>p_kind or op.session_id is distinct from p_session_id then return jsonb_build_object('status','conflict'); end if;
  return jsonb_build_object('status',op.status,'result',op.result);
 end if;
 -- A crashed worker's reservation stays charged; expiration never grants a free retry.
 update public.ai_operations set status='uncertain',updated_at=now() where status='pending' and created_at < now()-interval '15 minutes';
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

create or replace function public.finish_ai_operation(
 p_user_id uuid,p_request_id uuid,p_status text,p_tokens bigint,p_result jsonb default null
) returns jsonb language plpgsql set search_path='' as $$
declare op public.ai_operations; msg jsonb; patch jsonb;
begin
 if p_status not in ('completed','failed','uncertain') or p_tokens<0 then raise exception 'Invalid settlement'; end if;
 perform pg_advisory_xact_lock(482019260912);
 select * into op from public.ai_operations where user_id=p_user_id and request_id=p_request_id for update;
 if not found then raise exception 'AI reservation missing'; end if;
 if op.status in ('completed','failed') then return jsonb_build_object('status',op.status,'result',op.result); end if;
 if op.kind='chat' and p_tokens>0 then
  update public.sessions set tokens_used=tokens_used+p_tokens,
   chat_turns=chat_turns+case when p_status='completed' then 1 else 0 end
  where user_id=p_user_id and session_id=op.session_id;
 end if;
 if op.kind='chat' and p_status='completed' then
  patch=p_result->'_session_patch';
  update public.sessions set last_response_id=patch->>'last_response_id',followup_model=patch->>'followup_model',
   ai_reasoning=patch->>'ai_reasoning',ai_verbosity=patch->>'ai_verbosity',ai_tone=patch->>'ai_tone'
  where user_id=p_user_id and session_id=op.session_id;
  for msg in select value from jsonb_array_elements(coalesce(p_result->'_messages','[]'::jsonb)) loop
   insert into public.chat_messages(id,session_id,user_id,role,content,tokens_in,tokens_out,model,reasoning,verbosity,tone)
   values(coalesce((msg->>'id')::uuid,gen_random_uuid()),op.session_id,p_user_id,msg->>'role',msg->>'content',
    coalesce((msg->>'tokens_in')::integer,0),coalesce((msg->>'tokens_out')::integer,0),msg->>'model',msg->>'reasoning',msg->>'verbosity',msg->>'tone')
   on conflict(id) do update set content=excluded.content,tokens_in=excluded.tokens_in,tokens_out=excluded.tokens_out,
    model=excluded.model,reasoning=excluded.reasoning,verbosity=excluded.verbosity,tone=excluded.tone
   where public.chat_messages.user_id=p_user_id and public.chat_messages.session_id=op.session_id;
  end loop;
 end if;
 update public.ai_operations set status=p_status,actual_tokens=p_tokens,
  reserved_tokens=case when p_status='uncertain' and p_tokens=0 then reserved_tokens else 0 end,
  result=p_result,updated_at=now() where user_id=p_user_id and request_id=p_request_id;
 return jsonb_build_object('status',p_status,'result',p_result);
end $$;
revoke all on function public.admit_ai_operation(uuid,uuid,uuid,text,text,bigint,bigint,bigint,integer,integer,bigint) from public,anon,authenticated;
revoke all on function public.finish_ai_operation(uuid,uuid,text,bigint,jsonb) from public,anon,authenticated;
grant execute on function public.admit_ai_operation(uuid,uuid,uuid,text,text,bigint,bigint,bigint,integer,integer,bigint) to service_role;
grant execute on function public.finish_ai_operation(uuid,uuid,text,bigint,jsonb) to service_role;
notify pgrst,'reload schema';
