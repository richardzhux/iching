-- Shared, server-only admission across ephemeral Vercel instances.
create table public.public_calculation_windows (
 identity_hash text primary key check(length(identity_hash)=64),
 window_start timestamptz not null,
 requests integer not null check(requests>0)
);
create index public_calculation_windows_expiry on public.public_calculation_windows(window_start);
alter table public.public_calculation_windows enable row level security;
revoke all on public.public_calculation_windows from public,anon,authenticated;
grant select,insert,update,delete on public.public_calculation_windows to service_role;

create or replace function public.admit_public_calculation(p_identity text,p_limit integer)
returns jsonb language plpgsql set search_path='' as $$
declare tally public.public_calculation_windows; stamp timestamptz := clock_timestamp(); retry integer;
begin
 if p_limit<1 or p_limit>10000 or length(p_identity)<>64 then raise exception 'Invalid calculation admission'; end if;
 perform pg_advisory_xact_lock(482019261001);
 delete from public.public_calculation_windows where window_start<stamp-interval '2 minutes';
 select * into tally from public.public_calculation_windows where identity_hash=p_identity for update;
 if found and tally.window_start>stamp-interval '1 minute' then
  retry=greatest(1,ceil(extract(epoch from tally.window_start+interval '1 minute'-stamp))::integer);
  if tally.requests>=p_limit then return jsonb_build_object('allowed',false,'retry_seconds',retry); end if;
  update public.public_calculation_windows set requests=requests+1 where identity_hash=p_identity;
 else
  if not found and (select count(*) from public.public_calculation_windows)>=10000 then return jsonb_build_object('allowed',false,'retry_seconds',60); end if;
  insert into public.public_calculation_windows(identity_hash,window_start,requests) values(p_identity,stamp,1)
  on conflict(identity_hash) do update set window_start=excluded.window_start,requests=1;
 end if;
 return jsonb_build_object('allowed',true);
end $$;
revoke all on function public.admit_public_calculation(text,integer) from public,anon,authenticated;
grant execute on function public.admit_public_calculation(text,integer) to service_role;
notify pgrst,'reload schema';
