from __future__ import annotations

from datetime import datetime

from fastapi.testclient import TestClient

from iching.web.api.main import app


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


def test_create_session_manual_lines() -> None:
    payload = {
        "topic": "事业",
        "user_question": "测试问题",
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
    assert data["session_dict"]["topic"] == "事业"
