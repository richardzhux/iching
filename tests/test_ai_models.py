from __future__ import annotations

from iching.integrations.ai import (
    DEFAULT_MODEL,
    MODEL_CAPABILITIES,
    _reasoning_payload,
    normalize_model_name,
)
from iching.web.chat_service import CHAT_FOLLOWUP_MODEL


def test_current_ai_model_catalog_and_aliases() -> None:
    assert list(MODEL_CAPABILITIES) == [
        "gpt-5.6-terra",
        "gpt-5.6-sol",
        "gpt-5.5",
        "gpt-5.3-codex",
        "gpt-4.1",
    ]
    assert DEFAULT_MODEL == "gpt-5.6-terra"
    assert CHAT_FOLLOWUP_MODEL == "gpt-5.6-terra"
    assert normalize_model_name("gpt-5.2") == "gpt-5.5"
    assert normalize_model_name("gpt-5-mini") == "gpt-5.6-terra"
    assert normalize_model_name("gpt-5.4-mini") == "gpt-5.6-terra"
    assert normalize_model_name("gpt-5.6") == "gpt-5.6-sol"
    assert normalize_model_name("gpt-5.1") == "gpt-5.5"
    assert normalize_model_name("gpt-5.3-codex") == "gpt-5.3-codex"
    assert MODEL_CAPABILITIES["gpt-5.6-terra"]["reasoning"] == [
        "none", "low", "medium", "high", "xhigh", "max"
    ]
    assert MODEL_CAPABILITIES["gpt-5.6-sol"]["default_reasoning"] == "high"
    assert _reasoning_payload("gpt-5.6-terra", "medium") == {
        "effort": "medium",
        "context": "all_turns",
    }
    assert _reasoning_payload("gpt-5.5", "medium") == {"effort": "medium"}


def _request_with_budget(client, budget, **overrides):
    from iching.integrations.ai import _request_openai_response
    from iching.integrations.ai_budget import use_ai_budget

    options = dict(client=client, model_name="gpt-4.1", instructions="规则", user_input="提问", reasoning=None, verbosity=None)
    options.update(overrides)
    with use_ai_budget(budget):
        return _request_openai_response(**options)


def test_ai_budget_rejects_utf8_prompt_before_network():
    import pytest
    from types import SimpleNamespace
    from iching.integrations.ai_budget import AICallBudget

    calls = []
    client = SimpleNamespace(responses=SimpleNamespace(create=lambda **kwargs: calls.append(kwargs)))
    budget = AICallBudget(max_input_bytes=11)
    with pytest.raises(ValueError):
        _request_with_budget(client, budget)
    assert calls == []
    assert budget.dispatched is False


def test_ai_budget_records_empty_billable_response_and_caps_output():
    from types import SimpleNamespace
    from iching.integrations.ai_budget import AICallBudget

    calls = []
    response = {"id": "empty-response", "output_text": "", "usage": {"input_tokens": 10, "output_tokens": 3, "total_tokens": 13}}

    def create(**kwargs):
        calls.append(kwargs)
        return response

    budget = AICallBudget(max_output_tokens=300)
    result = _request_with_budget(SimpleNamespace(responses=SimpleNamespace(create=create)), budget)
    assert result is response
    assert calls[0]["max_output_tokens"] == 300
    assert budget.dispatched is True
    assert budget.response_id == "empty-response"
    assert budget.usage["total_tokens"] == 13


def test_ai_budget_retains_reservation_on_ambiguous_failure_and_clears_known_rejection():
    import pytest
    from types import SimpleNamespace
    from iching.integrations.ai_budget import AICallBudget

    class ProviderFailure(RuntimeError):
        def __init__(self, status_code):
            self.status_code = status_code

    for status_code, expected_dispatch in ((400, False), (401, False), (403, False), (404, False), (422, False), (500, True), (None, True)):
        def create(**kwargs):
            raise ProviderFailure(status_code)

        budget = AICallBudget()
        with pytest.raises(ProviderFailure):
            _request_with_budget(SimpleNamespace(responses=SimpleNamespace(create=create)), budget)
        assert budget.dispatched is expected_dispatch
        assert budget.usage is None


def test_ai_budget_compatibility_retry_tracks_only_successful_usage():
    import httpx
    from types import SimpleNamespace
    from openai import BadRequestError
    from iching.integrations.ai_budget import AICallBudget

    calls = []

    def create(**kwargs):
        calls.append(kwargs)
        if "reasoning" in kwargs:
            raise BadRequestError("reasoning unsupported", response=httpx.Response(400, request=httpx.Request("POST", "https://api.openai.com/v1/responses")), body={})
        return {"id": "ok", "usage": {"total_tokens": 12}}

    budget = AICallBudget()
    _request_with_budget(SimpleNamespace(responses=SimpleNamespace(create=create)), budget, reasoning="low")
    assert len(calls) == 2
    assert "reasoning" not in calls[-1]
    assert budget.dispatched is True
    assert budget.usage == {"total_tokens": 12}


def _stream_with_events(monkeypatch, events):
    from types import SimpleNamespace
    from iching.integrations import ai

    class FakeStream:
        def __enter__(self):
            return iter(events)

        def __exit__(self, *args):
            pass

    captured = {}

    def fake_openai(**kwargs):
        captured["client"] = kwargs

        def create(**payload):
            captured["payload"] = payload
            return FakeStream()

        return SimpleNamespace(responses=SimpleNamespace(create=create))

    monkeypatch.setattr(ai, "OpenAI", fake_openai)
    stream = ai._stream_analysis(user_input="提问", previous_response_id=None, api_key="test", model_name="gpt-4.1", reasoning_effort=None, verbosity=None, tone=None)
    return stream, captured


def test_stream_incomplete_response_records_usage_and_emits_available_text(monkeypatch):
    from iching.integrations.ai_budget import AICallBudget, use_ai_budget

    stream, captured = _stream_with_events(monkeypatch, [
        {"type": "response.output_text.delta", "delta": "已有答案"},
        {"type": "response.incomplete", "response": {"id": "partial", "usage": {"input_tokens": 10, "output_tokens": 50, "total_tokens": 60}}},
    ])
    budget = AICallBudget(max_output_tokens=50)
    with use_ai_budget(budget):
        events = list(stream)
    assert events[-1]["result"].text == "已有答案"
    assert budget.usage["total_tokens"] == 60
    assert captured["payload"]["max_output_tokens"] == 50
    assert captured["client"]["max_retries"] == 0
    assert captured["client"]["timeout"].read == 120.0
    assert captured["client"]["timeout"].connect == 10.0
    assert captured["client"]["http_client"].is_closed


def test_stream_missing_terminal_usage_cannot_emit_success(monkeypatch):
    import pytest
    from iching.integrations.ai_budget import AICallBudget, use_ai_budget

    stream, _ = _stream_with_events(monkeypatch, [{"type": "response.output_text.delta", "delta": "partial"}])
    budget = AICallBudget()
    with use_ai_budget(budget), pytest.raises(RuntimeError, match="terminal usage"):
        list(stream)
    assert budget.dispatched is True
    assert budget.usage is None


def test_stream_failure_preserves_billable_usage(monkeypatch):
    import pytest
    from iching.integrations.ai_budget import AICallBudget, use_ai_budget

    stream, _ = _stream_with_events(monkeypatch, [
        {"type": "response.failed", "response": {"id": "failed", "usage": {"total_tokens": 17}}},
    ])
    budget = AICallBudget()
    with use_ai_budget(budget), pytest.raises(RuntimeError):
        list(stream)
    assert budget.response_id == "failed"
    assert budget.usage == {"total_tokens": 17}


def test_stream_empty_text_preserves_terminal_usage(monkeypatch):
    import pytest
    from iching.integrations.ai_budget import AICallBudget, use_ai_budget

    stream, _ = _stream_with_events(monkeypatch, [
        {"type": "response.completed", "response": {"id": "empty", "usage": {"total_tokens": 17}}},
    ])
    budget = AICallBudget()
    with use_ai_budget(budget), pytest.raises(RuntimeError, match="empty response"):
        list(stream)
    assert budget.usage == {"total_tokens": 17}


def test_sync_response_without_usage_keeps_reservation_and_fails_closed():
    import pytest
    from types import SimpleNamespace
    from iching.integrations.ai_budget import AICallBudget

    client = SimpleNamespace(responses=SimpleNamespace(create=lambda **kwargs: {"id": "unaccounted", "output_text": "answer"}))
    budget = AICallBudget()
    with pytest.raises(RuntimeError, match="usage accounting"):
        _request_with_budget(client, budget)
    assert budget.dispatched is True
    assert budget.response_id == "unaccounted"
    assert budget.usage is None


def test_later_known_rejection_cannot_release_earlier_ambiguous_dispatch():
    import pytest
    from types import SimpleNamespace
    from iching.integrations.ai_budget import AICallBudget

    class KnownRejection(RuntimeError):
        status_code = 400

    def create(**kwargs):
        raise KnownRejection()

    budget = AICallBudget(dispatched=True)
    with pytest.raises(KnownRejection):
        _request_with_budget(SimpleNamespace(responses=SimpleNamespace(create=create)), budget)
    assert budget.dispatched is True


def _network_stream(monkeypatch, chunks):
    """Exercise the real SDK SSE decoder over the production transport wrapper."""
    import httpx
    from iching.integrations import ai, ai_budget

    clock = [0.0]
    monkeypatch.setattr(ai_budget, "monotonic", lambda: clock[0])
    captured = {"dispatches": 0, "reads": 0, "closed": False}

    class ProviderBytes(httpx.SyncByteStream):
        def __iter__(self):
            for elapsed, chunk in chunks:
                captured["reads"] += 1
                clock[0] += elapsed
                yield chunk

        def close(self):
            captured["closed"] = True

    def handle(request):
        captured["dispatches"] += 1
        captured["timeouts"] = request.extensions["timeout"]
        return httpx.Response(200, headers={"Content-Type": "text/event-stream"}, stream=ProviderBytes())

    transport_type = ai._DeadlineTransport
    monkeypatch.setattr(ai, "_DeadlineTransport", lambda budget: transport_type(budget, httpx.MockTransport(handle)))
    stream = ai._stream_analysis(user_input="fixture", previous_response_id=None, api_key="synthetic-test-key",
        model_name="gpt-4.1", reasoning_effort=None, verbosity=None, tone=None)
    return stream, captured


def _sse(event):
    import json
    return ("data: " + json.dumps(event) + "\n\n").encode()


def test_continuous_provider_chunks_cannot_extend_total_deadline(monkeypatch):
    import pytest
    from iching.integrations.ai_budget import AICallBudget, AIDeadlineExceeded, use_ai_budget

    stream, captured = _network_stream(monkeypatch, [
        (0.4, _sse({"type": "response.output_text.delta", "delta": "a"})),
        (0.4, _sse({"type": "response.output_text.delta", "delta": "b"})),
        (0.4, _sse({"type": "response.output_text.delta", "delta": "late"})),
    ])
    budget = AICallBudget(provider_total_seconds=1.0)
    with use_ai_budget(budget):
        assert next(stream)["delta"] == "a"
        assert next(stream)["delta"] == "b"
        with pytest.raises(AIDeadlineExceeded):
            next(stream)
    assert captured["dispatches"] == 1
    assert captured["closed"]
    assert budget.dispatched and budget.usage is None


def test_dripping_sync_response_body_cannot_extend_total_deadline(monkeypatch):
    import pytest
    from iching.integrations import ai
    from iching.integrations.ai_budget import AICallBudget, AIDeadlineExceeded

    _, captured = _network_stream(monkeypatch, [(0.4, b" ")] * 20)
    budget = AICallBudget(provider_total_seconds=1.0)
    with ai._bounded_client("synthetic-test-key", budget) as client:
        with pytest.raises(AIDeadlineExceeded):
            _request_with_budget(client, budget)
    assert captured["reads"] == 3
    assert captured["dispatches"] == 1 and captured["closed"]
    assert budget.dispatched and budget.usage is None


def test_late_terminal_event_keeps_usage_before_deadline_failure(monkeypatch):
    import pytest
    from iching.integrations.ai_budget import AICallBudget, AIDeadlineExceeded, use_ai_budget

    stream, captured = _network_stream(monkeypatch, [
        (0.8, _sse({"type": "response.output_text.delta", "delta": "partial"})),
        (0.4, _sse({"type": "response.completed", "response": {"id": "late-result", "usage": {"total_tokens": 17}}})),
    ])
    budget = AICallBudget(provider_total_seconds=1.0)
    with use_ai_budget(budget), pytest.raises(AIDeadlineExceeded):
        list(stream)
    assert budget.response_id == "late-result"
    assert budget.usage == {"total_tokens": 17}
    assert budget.dispatched and captured["closed"] and captured["dispatches"] == 1


def test_terminal_event_closes_provider_without_waiting_for_connection_end(monkeypatch):
    from iching.integrations.ai_budget import AICallBudget, use_ai_budget

    stream, captured = _network_stream(monkeypatch, [
        (0.1, _sse({"type": "response.output_text.delta", "delta": "complete"})),
        (0.1, _sse({"type": "response.completed", "response": {"id": "done", "usage": {"total_tokens": 9}}})),
        (500.0, b"data: [DONE]\n\n"),
    ])
    budget = AICallBudget(provider_total_seconds=1.0)
    with use_ai_budget(budget):
        events = list(stream)
    assert events[-1]["result"].text == "complete"
    assert captured["reads"] == 2 and captured["closed"]
    assert budget.usage == {"total_tokens": 9}


def test_generator_cancellation_closes_provider_without_another_dispatch(monkeypatch):
    from iching.integrations.ai_budget import AICallBudget, use_ai_budget

    stream, captured = _network_stream(monkeypatch, [
        (0.1, _sse({"type": "response.output_text.delta", "delta": "partial"})),
        (0.1, _sse({"type": "response.output_text.delta", "delta": "unused"})),
    ])
    budget = AICallBudget()
    with use_ai_budget(budget):
        next(stream)
        stream.close()
    assert captured["reads"] == 1 and captured["closed"]
    assert captured["dispatches"] == 1 and budget.dispatched and budget.usage is None


def test_compatibility_retry_cannot_restart_exhausted_deadline(monkeypatch):
    import httpx
    import pytest
    from openai import BadRequestError
    from types import SimpleNamespace
    from iching.integrations import ai_budget

    clock = [0.0]
    monkeypatch.setattr(ai_budget, "monotonic", lambda: clock[0])
    calls = []

    def create(**payload):
        calls.append(payload)
        clock[0] = 2.0
        raise BadRequestError("reasoning unsupported", response=httpx.Response(400,
            request=httpx.Request("POST", "https://api.openai.com/v1/responses")), body={})

    budget = ai_budget.AICallBudget(provider_total_seconds=1.0)
    with pytest.raises(ai_budget.AIDeadlineExceeded):
        _request_with_budget(SimpleNamespace(responses=SimpleNamespace(create=create)), budget, reasoning="low")
    assert len(calls) == 1
    assert budget.dispatched is False


def test_late_sync_response_preserves_usage_without_retry(monkeypatch):
    import pytest
    from types import SimpleNamespace
    from iching.integrations import ai_budget

    clock = [0.0]
    monkeypatch.setattr(ai_budget, "monotonic", lambda: clock[0])
    calls = []

    def create(**payload):
        calls.append(payload)
        clock[0] = 2.0
        return {"id": "late", "usage": {"total_tokens": 13}}

    budget = ai_budget.AICallBudget(provider_total_seconds=1.0)
    with pytest.raises(ai_budget.AIDeadlineExceeded):
        _request_with_budget(SimpleNamespace(responses=SimpleNamespace(create=create)), budget)
    assert len(calls) == 1 and budget.dispatched
    assert budget.response_id == "late" and budget.usage == {"total_tokens": 13}


def test_provider_read_stall_times_out_once_over_real_tcp(monkeypatch):
    import httpx
    import pytest
    import threading
    import time
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from openai import APITimeoutError, DefaultHttpxClient, OpenAI
    from iching.integrations import ai
    from iching.integrations.ai_budget import AICallBudget

    requests = []
    release = threading.Event()

    class StalledProvider(BaseHTTPRequestHandler):
        def do_POST(self):
            requests.append(self.path)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", "1")
            self.end_headers()
            release.wait(1.0)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), StalledProvider)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setattr(ai, "_PROVIDER_TIMEOUT", httpx.Timeout(0.03, connect=1.0, write=1.0, pool=1.0))
    budget = AICallBudget()
    try:
        with DefaultHttpxClient(transport=ai._DeadlineTransport(budget), timeout=ai._PROVIDER_TIMEOUT,
            trust_env=False) as http_client:
            client = OpenAI(api_key="synthetic-test-key", base_url=f"http://127.0.0.1:{server.server_port}/v1",
                max_retries=0, http_client=http_client)
            started = time.monotonic()
            with pytest.raises(APITimeoutError):
                _request_with_budget(client, budget)
            assert time.monotonic() - started < 0.6
        assert requests == ["/v1/responses"]
        assert budget.dispatched and budget.usage is None
    finally:
        release.set()
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
