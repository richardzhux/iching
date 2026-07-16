from __future__ import annotations

from datetime import datetime

from fastapi.testclient import TestClient

from iching.integrations.ai import AIResponseData
from iching.integrations.supabase_client import SupabaseUser
from iching.core.bazi_rules.registry import load_packaged_shen_registry
from iching.core.calendar_engine import ENGINE_VERSION as CALENDAR_ENGINE_VERSION
from iching.core.metaphysics_consumer import CONSUMER_RULES_VERSION
from iching.core.metaphysics_statistics import BaselineVersionMismatchError
from iching.core.shensha import RULES_VERSION as SHENSHA_RULES_VERSION
from iching.web.api.main import app
from iching.web.api import routes


client = TestClient(app)


def test_healthcheck() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_config_endpoint() -> None:
    response = client.get("/api/config")
    data = response.json()
    assert response.status_code == 200
    assert "topics" in data and data["topics"]
    assert "methods" in data and data["methods"]
    assert "ai_models" in data and data["ai_models"]
    assert [model["name"] for model in data["ai_models"]] == [
        "gpt-5.6-terra",
        "gpt-5.6-sol",
        "gpt-5.5",
        "gpt-5.3-codex",
        "gpt-4.1",
    ]
    assert data["ai_models"][0]["label"] == "GPT-5.6 Terra"
    assert data["ai_models"][0]["default_verbosity"] == "medium"
    assert data["default_model"] == "gpt-5.6-terra"
    assert data["model_aliases"]["gpt-5.5-mini"] == "gpt-5.6-terra"


def test_metaphysics_chart_endpoint() -> None:
    response = client.post(
        "/api/tools/metaphysics",
        json={
            "timestamp": "2024-02-10T12:00:00",
            "timezone": "Asia/Shanghai",
            "day_boundary": "forward",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["bazi"] == "甲辰 丙寅 甲辰 庚午"
    assert data["lunar_date"] == "2024年正月初一"
    assert len(data["pillars"]) == 4
    assert data["calendar_facts"]["month_command"] == "寅"
    assert data["calendar_facts"]["day_branch"] == "辰"
    assert data["calendar_facts"]["six_spirits"] == ["青龙", "朱雀", "勾陈", "腾蛇", "白虎", "玄武"]
    registry = load_packaged_shen_registry()
    assert data["derived_schema_version"] == 7
    assert data["rule_versions"] == {
        "calendar": CALENDAR_ENGINE_VERSION,
        "pattern_bundle": registry.bundle_id,
        "pattern_digest": registry.bundle_digest,
        "shensha": SHENSHA_RULES_VERSION,
        "consumer": CONSUMER_RULES_VERSION,
    }


def test_pattern_rule_endpoint_returns_compact_verified_source_summary() -> None:
    registry = load_packaged_shen_registry()
    rule = registry.rules[0]
    response = client.get(f"/api/tools/metaphysics/pattern-rules/{registry.bundle_id}/{rule.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["bundle_id"] == registry.bundle_id
    assert data["bundle_digest"] == registry.bundle_digest
    assert data["rule_id"] == rule.id
    assert data["sources"]
    assert all(source["review_state"] == "scan_verified" for source in data["sources"])
    assert all(source["locators"] for source in data["sources"])
    assert "corpus_artifact_digest" not in response.text
    assert "predicate" not in response.text
    assert "full_trace" not in response.text


def test_pattern_rule_endpoint_rejects_unknown_bundle_and_rule() -> None:
    registry = load_packaged_shen_registry()
    assert client.get(f"/api/tools/metaphysics/pattern-rules/unknown-bundle/{registry.rules[0].id}").status_code == 404
    assert client.get(f"/api/tools/metaphysics/pattern-rules/{registry.bundle_id}/unknown-rule").status_code == 404


def test_metaphysics_chart_survives_statistics_version_failure(monkeypatch) -> None:
    import iching.core.metaphysics as metaphysics

    def unavailable_statistics(*args, **kwargs):
        raise BaselineVersionMismatchError("测试基线版本不匹配")

    monkeypatch.setattr(metaphysics, "statistics_for_shensha", unavailable_statistics)
    response = client.post(
        "/api/tools/metaphysics",
        json={
            "timestamp": "2024-02-10T12:00:00",
            "timezone": "Asia/Shanghai",
            "day_boundary": "forward",
            "gender": "male",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["pillars"]) == 4
    assert data["structure"]["patterns"]
    assert data["period_layers"]["dayun"]
    assert data["statistics"]["status"] == "version_mismatch"
    assert data["statistics"]["unavailable_reason"] == "测试基线版本不匹配"
    assert data["statistics"]["baseline"]["id"] == "bazi-calendar-1924-2044-g4-forward"
    assert data["statistics"]["rarity_metrics"] == []
    assert data["statistics"]["theme_profiles"] == []
    assert data["theme_profiles"]


def test_chat_stream_endpoint_emits_sse_events() -> None:
    class FakeChatService:
        def authenticate(self, token: str) -> SupabaseUser:
            return SupabaseUser(id="00000000-0000-0000-0000-000000000001", email="reader@example.com")

        def stream_followup(self, **kwargs):
            assert kwargs["model_override"] == "gpt-5.6-terra"
            assert kwargs["restart"] is False
            yield {"type": "delta", "delta": "先稳"}
            yield {"type": "completed", "assistant": {"role": "assistant", "content": "先稳后进"}, "usage": {"total_tokens": 9}}

    fake_chat_service = FakeChatService()
    app.dependency_overrides[routes._get_chat_service] = lambda: fake_chat_service
    try:
        response = client.post(
            "/api/sessions/session-test/chat/stream",
            json={"message": "接下来怎么做？", "model": "gpt-5.6-terra"},
            headers={"Authorization": "Bearer test-token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: delta" in response.text
    assert '"delta": "先稳"' in response.text
    assert "event: completed" in response.text


def test_create_session_manual_lines() -> None:
    payload = {
        "topic": "事业",
        "user_question": "测试问题",
        "user_context": "我需要在月底前决定。",
        "method_key": "x",
        "manual_lines": [6, 7, 8, 9, 7, 6],
        "use_current_time": False,
        "timestamp": datetime(2024, 5, 1, 8, 30).isoformat(),
        "enable_ai": False,
        "ai_model": "gpt-5-nano",
    }
    response = client.post("/api/sessions", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "summary_text" in data
    assert "hex_text" in data
    assert "session_dict" in data
    assert "reading_brief" in data
    assert data["reading_brief"]["headline"]
    assert data["reading_brief"]["evidence"]
    assert data["reading_brief"]["key_passages"]
    assert data["reading_brief"]["key_passages"][0]["source_id"]
    assert data["reading_brief"]["key_passages"][0]["why_it_matters"]
    assert data["reading_brief"]["source_passages"][0]["source_id"]
    assert any(item.get("source_ids") for item in data["reading_brief"]["evidence"])
    assert data["session_dict"]["topic"] == "事业"
    assert data["session_dict"]["user_context"] == "我需要在月底前决定。"
    assert data["reading_brief"]["source_passages"]
    assert data["reading_brief"]["archive_sources"]["total_passages"] >= len(data["reading_brief"]["source_passages"])
    assert data["reading_brief"]["personal_context"]["status"] == "reserved"


def test_create_session_ai_enabled_returns_reading_brief(monkeypatch) -> None:
    class FakeChatService:
        def authenticate(self, token: str) -> SupabaseUser:
            return SupabaseUser(id="00000000-0000-0000-0000-000000000001", email="reader@example.com")

        def record_session_snapshot(self, *args, **kwargs) -> None:
            return None

    def fake_start_analysis(*args, **kwargs):
        return AIResponseData(
            text=(
                "# 一句话结论\n"
                "- 利成，但需要先控制节奏。\n\n"
                "# 应期与条件\n"
                "- 主应期：一周内｜条件：负责人出现｜置信度：68%\n\n"
                "# 行动建议\n"
                "- 动作：先问清负责人｜节奏：今天｜观察指标：是否明确承诺\n\n"
                "# 继续追问\n"
                "- 应该先问谁？"
            ),
            response_id="resp_test",
            usage={"input_tokens": 4, "output_tokens": 8, "total_tokens": 12},
        )

    monkeypatch.setattr("iching.web.service._validate_ai_password", lambda password: (True, ""))
    monkeypatch.setattr("iching.services.session.start_analysis", fake_start_analysis)
    fake_chat_service = FakeChatService()
    monkeypatch.setattr(routes.get_session_runner(), "chat_service", fake_chat_service)
    app.dependency_overrides[routes._get_chat_service] = lambda: fake_chat_service
    try:
        payload = {
            "topic": "事业",
            "user_question": "是否应该推进这个合作？",
            "method_key": "x",
            "manual_lines": [7, 8, 7, 8, 7, 8],
            "use_current_time": False,
            "timestamp": datetime(2024, 5, 1, 8, 30).isoformat(),
            "enable_ai": True,
            "access_password": "test",
            "ai_model": "gpt-5.5",
        }
        response = client.post(
            "/api/sessions",
            json=payload,
            headers={"Authorization": "Bearer test-token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    data = response.json()
    assert data["ai_enabled"] is True
    assert data["reading_brief"]["headline"]
    assert "利成" in data["reading_brief"]["headline"]
    assert data["reading_brief"]["timing"][0]["window"] == "一周内"
    assert data["reading_brief"]["actions"][0]["action"] == "先问清负责人"
    assert data["reading_brief"]["followup_prompts"][0] == "应该先问谁？"
