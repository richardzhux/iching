-- Integration regression: disposable fixtures remain inside a rolled-back transaction.
begin;
do $$
declare
 tester uuid := gen_random_uuid();
 stale_id uuid := gen_random_uuid();
 completed_id uuid := gen_random_uuid();
 identity text := repeat(md5(gen_random_uuid()::text),2);
 result jsonb;
 reserve bigint;
begin
 insert into auth.users(id,email) values(tester,tester::text||'@migration-test.invalid');
 insert into public.ai_operations(user_id,request_id,kind,fingerprint,reserved_tokens,created_at)
 values(tester,stale_id,'initial','stale-test',100,now()-interval '16 minutes');
 result=public.admit_ai_operation(tester,stale_id,null,'initial','stale-test',100,1000,1000,10,50,0);
 if result->>'status'<>'uncertain' then raise exception 'Same-ID abandoned request was not reconciled'; end if;
 select reserved_tokens into reserve from public.ai_operations where user_id=tester and ai_operations.request_id=stale_id;
 if reserve<>100 then raise exception 'Abandoned reservation was released'; end if;
 result=public.admit_ai_operation(tester,stale_id,null,'initial','changed',100,1000,1000,10,50,0);
 if result->>'status'<>'conflict' then raise exception 'Changed request replay was accepted'; end if;
 result=public.admit_ai_operation(tester,completed_id,null,'initial','complete-test',100,1000,1000,10,50,0);
 if result->>'status'<>'admitted' then raise exception 'Fresh request failed'; end if;
 perform public.finish_ai_operation(tester,completed_id,'completed',12,'{"answer":"synthetic"}'::jsonb);
 result=public.admit_ai_operation(tester,completed_id,null,'initial','complete-test',100,1000,1000,10,50,0);
 if result->>'status'<>'completed' or result->'result'->>'answer'<>'synthetic' then raise exception 'Completion replay failed'; end if;
 if (public.admit_public_calculation(identity,2)->>'allowed')::boolean is not true then raise exception 'First public admission failed'; end if;
 if (public.admit_public_calculation(identity,2)->>'allowed')::boolean is not true then raise exception 'Second public admission failed'; end if;
 if (public.admit_public_calculation(identity,2)->>'allowed')::boolean is not false then raise exception 'Shared public limit exceeded'; end if;
 update public.public_calculation_windows set window_start=now()-interval '61 seconds' where identity_hash=identity;
 if (public.admit_public_calculation(identity,2)->>'allowed')::boolean is not true then raise exception 'Expired public limit failed to reset'; end if;
 if has_function_privilege('authenticated','public.admit_public_calculation(text,integer)','EXECUTE') then raise exception 'Browser can bypass shared admission'; end if;
end $$;
select 'serverless admission regressions passed; fixtures rolled back' as result;
rollback;
