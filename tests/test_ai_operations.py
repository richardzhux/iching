from contextvars import Context
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from iching.integrations.ai import AIResponseData
from iching.integrations.ai_budget import AICallBudget, get_ai_budget
from iching.integrations.supabase_client import SupabaseUser
from iching.web.ai_operations import AIOperations, AIOperationLimitError, validate_ai_access
from iching.web.chat_service import ChatService
from iching.web.chat_state import SessionStateStore
from iching.web.errors import AccessDeniedError


@pytest.fixture
def service(monkeypatch):
    monkeypatch.setenv('OPENAI_PW', 'test-only-password')
    client = Mock(enabled=True)
    client.fetch_session.return_value = {
        'session_id': 'session', 'followup_model': 'gpt-5.6-terra',
        'payload_snapshot': {'session_dict': {'topic': 'Work', 'user_question': 'What next?'}},
    }
    client.fetch_chat_messages.return_value = []
    result = ChatService(SessionStateStore(), client)
    result.operations = Mock()
    result.operations.admit.return_value = {'status': 'admitted'}
    return result


def params():
    return dict(session_id='session', user=SupabaseUser(id='owner'), message='Next step?',
                request_id=str(uuid4()), access_password='test-only-password')


def test_owner_cache_cannot_be_claimed_after_database_miss(service):
    service.client.fetch_session.return_value = None
    service.store.register(session_id='session', summary_text='private', ai_text='private',
        ai_enabled=True, ai_model='gpt-5.6-terra', ai_reasoning=None, ai_verbosity=None,
        ai_tone=None, last_response_id='private-response', initial_tokens=20,
        session_payload={'topic': 'private'}, owner_id='victim')
    with pytest.raises(ValueError):
        service.ensure_session_row('session', SupabaseUser(id='attacker'))
    service.client.upsert_session.assert_not_called()
    service.ensure_session_row('session', SupabaseUser(id='victim'))
    assert service.client.upsert_session.call_args.args[0]['user_id'] == 'victim'


def test_paid_followup_password_checked_before_read_or_provider(service):
    with pytest.raises(AccessDeniedError):
        service.send_followup(**{**params(), 'access_password': None})
    service.client.fetch_session.assert_not_called()
    service.operations.admit.assert_not_called()


def test_completed_retry_returns_saved_result_without_provider(service, monkeypatch):
    provider = Mock()
    monkeypatch.setattr('iching.web.chat_service.continue_analysis_from_session', provider)
    service.operations.admit.return_value = {'status': 'completed',
        'result': {'assistant': {'content': 'saved answer'}, 'usage': {'total_tokens': 42}}}
    result = service.send_followup(**params())
    assert result['assistant']['content'] == 'saved answer'
    provider.assert_not_called()
    service.operations.finish.assert_not_called()


def test_actual_usage_is_settled_even_above_old_session_threshold(service, monkeypatch):
    response = AIResponseData('answer', 'response', {'input_tokens': 170000, 'output_tokens': 1, 'total_tokens': 170001})
    monkeypatch.setattr('iching.web.chat_service.continue_analysis_from_session', lambda **_: response)
    assert service.send_followup(**params())['assistant']['content'] == 'answer'
    assert service.operations.finish.call_args.kwargs['tokens'] == 170001
    assert service.operations.finish.call_args.kwargs['status'] == 'completed'


def test_stream_budget_survives_distinct_threadpool_contexts(service, monkeypatch):
    budgets = []
    def provider(**_):
        budget = get_ai_budget()
        budgets.append(budget)
        budget.dispatched = True
        yield {'type': 'delta', 'delta': 'hello'}
        assert get_ai_budget() is budget
        budget.usage = {'total_tokens': 19}
        yield {'type': 'result', 'result': AIResponseData('hello', 'resp', budget.usage)}
    monkeypatch.setattr('iching.web.chat_service.stream_continue_analysis_from_session', provider)
    iterator = service.stream_followup(**params())
    assert Context().run(next, iterator)['type'] == 'delta'
    assert Context().run(next, iterator)['type'] == 'completed'
    with pytest.raises(StopIteration):
        Context().run(next, iterator)
    assert service.operations.finish.call_args.kwargs['tokens'] == 19
    assert budgets[0].dispatched


def test_stream_close_retains_unknown_provider_charge_and_closes_sdk(service, monkeypatch):
    closed = []
    def provider(**_):
        budget = get_ai_budget()
        budget.dispatched = True
        try:
            yield {'type': 'delta', 'delta': 'partial'}
        finally:
            closed.append(True)
    monkeypatch.setattr('iching.web.chat_service.stream_continue_analysis_from_session', provider)
    iterator = service.stream_followup(**params())
    Context().run(next, iterator)
    Context().run(iterator.close)
    assert closed == [True]
    budget = service.operations.fail.call_args.kwargs['budget']
    assert budget.dispatched and budget.usage is None


@pytest.mark.parametrize('dispatched,usage,status,tokens', [
    (True, None, 'uncertain', 0), (False, None, 'failed', 0),
    (True, {'total_tokens': 200000}, 'failed', 200000),
])
def test_failure_settlement_preserves_actual_or_reserved_charge(dispatched, usage, status, tokens):
    client = Mock()
    operations = AIOperations(client)
    operations.fail(user_id='user', request_id='request',
        budget=AICallBudget(dispatched=dispatched, usage=usage))
    payload = client.rpc.call_args.args[1]
    assert payload['p_status'] == status
    assert payload['p_tokens'] == tokens


def test_database_settlement_retry_never_readmits_or_repeats_ai():
    client = Mock()
    client.rpc.side_effect = [TimeoutError(), {'status': 'completed'}]
    operations = AIOperations(client)
    operations.finish(user_id='user', request_id='request', status='completed', tokens=20)
    assert client.rpc.call_count == 2
    assert all(call.args[0] == 'finish_ai_operation' for call in client.rpc.call_args_list)
    assert client.rpc.call_args_list[0] == client.rpc.call_args_list[1]


@pytest.mark.parametrize('status', ['pending', 'uncertain', 'failed', 'daily_limit', 'busy'])
def test_nonadmitted_request_fails_closed(status):
    client = Mock()
    client.rpc.return_value = {'status': status}
    with pytest.raises(AIOperationLimitError):
        AIOperations(client).admit(user_id='user', request_id='request', session_id='session',
            kind='chat', semantics={'message': 'hello'}, reserve=100)


def test_initial_replay_never_recalculates_or_dispatches_paid_work(service):
    from iching.web.models import SessionCreateRequest, SessionPayload
    saved = SessionPayload(summary_text='saved', hex_text='', hex_sections=[], hex_overview={},
        bazi_detail=[], reading_brief={}, najia_text='', najia_table={}, ai_text='answer',
        session_dict={}, archive_path='', full_text='', session_id='session', ai_enabled=True)
    service.operations.admit.return_value = {'status': 'completed', 'result': saved.model_dump(mode='json')}
    request = SessionCreateRequest(topic='Work', method_key='c', enable_ai=True,
        access_password='test-only-password', request_id=uuid4())
    callback = Mock()
    result = service.execute_initial(request=request, user=SupabaseUser(id='owner'), callback=callback)
    assert result == saved
    callback.assert_not_called()
    semantics = service.operations.admit.call_args.kwargs['semantics']
    assert 'access_password' not in semantics and 'request_id' not in semantics


def test_initial_ambiguous_failure_keeps_admitted_reservation(service):
    from iching.web.models import SessionCreateRequest
    request = SessionCreateRequest(topic='Work', method_key='c', enable_ai=True,
        access_password='test-only-password', request_id=uuid4())
    def callback():
        get_ai_budget().dispatched = True
        raise TimeoutError('provider did not confirm completion')
    with pytest.raises(TimeoutError):
        service.execute_initial(request=request, user=SupabaseUser(id='owner'), callback=callback)
    budget = service.operations.fail.call_args.kwargs['budget']
    assert budget.dispatched and budget.usage is None
