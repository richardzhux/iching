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
