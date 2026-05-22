from __future__ import annotations

from datetime import datetime

from fastapi.testclient import TestClient

from iching.integrations.ai import AIResponseData
from iching.integrations.supabase_client import SupabaseUser
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
        "gpt-5.5",
        "gpt-5.4-mini",
        "gpt-5.3-codex",
        "gpt-4.1",
    ]


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
            text="# 一句话结论\n- 利成，但需要先控制节奏。",
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
