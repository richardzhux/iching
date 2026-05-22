from __future__ import annotations

from iching.integrations.ai import DEFAULT_MODEL, MODEL_CAPABILITIES, normalize_model_name
from iching.web.chat_service import CHAT_FOLLOWUP_MODEL


def test_current_ai_model_catalog_and_aliases() -> None:
    assert list(MODEL_CAPABILITIES) == [
        "gpt-5.5",
        "gpt-5.4-mini",
        "gpt-5.3-codex",
        "gpt-4.1",
    ]
    assert DEFAULT_MODEL == "gpt-5.5"
    assert CHAT_FOLLOWUP_MODEL == "gpt-5.4-mini"
    assert normalize_model_name("gpt-5.2") == "gpt-5.5"
    assert normalize_model_name("gpt-5-mini") == "gpt-5.4-mini"
    assert normalize_model_name("gpt-5.1") == "gpt-5.5"
    assert normalize_model_name("gpt-5.3-codex") == "gpt-5.3-codex"
