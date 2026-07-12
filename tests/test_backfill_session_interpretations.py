from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import sys
from urllib.parse import parse_qs

import httpx

from iching.config import build_app_config
from iching.integrations.interpretation_repository import InterpretationRepository
from iching.integrations.najia_repository import NajiaRepository
from iching.integrations.supabase_client import SupabaseRestClient


_BACKFILL_PATH = Path(__file__).parents[1] / "tools" / "backfill_session_interpretations.py"
_BACKFILL_SPEC = importlib.util.spec_from_file_location(
    "backfill_session_interpretations", _BACKFILL_PATH
)
assert _BACKFILL_SPEC and _BACKFILL_SPEC.loader
_BACKFILL = importlib.util.module_from_spec(_BACKFILL_SPEC)
sys.modules[_BACKFILL_SPEC.name] = _BACKFILL
_BACKFILL_SPEC.loader.exec_module(_BACKFILL)
_compute_refreshed_snapshot = _BACKFILL._compute_refreshed_snapshot


def _dependencies():
    config = build_app_config(enable_ai=False)
    interpretation_repo = InterpretationRepository(
        db_path=config.paths.interpretation_db,
        index_file=config.paths.gua_index_file,
        guaci_dir=config.paths.guaci_dir,
        takashima_dir=config.paths.takashima_dir,
        symbolic_dir=config.paths.symbolic_dir,
        english_structured_dir=config.paths.english_structured_dir,
    )
    return config, interpretation_repo, NajiaRepository(config.paths.najia_db)


def _historical_snapshot():
    saved_lines = [8, "7", 8, "9", 6, "8"]
    return {
        "hex_text": "legacy outer hex text",
        "hex_sections": [{"legacy": True}],
        "hex_overview": {"legacy": True},
        "najia_table": {"rows": [{"god": "legacy outer god"}]},
        "najia_text": "legacy outer Najia text",
        "ai_text": "preserve outer AI text byte-for-byte",
        "ai_analysis": "preserve outer AI analysis",
        "ai_response_id": "resp_outer_123",
        "ai_usage": {"input_tokens": 11, "output_tokens": 22},
        "reading_brief": {"headline": "preserve outer brief"},
        "full_text": "preserve rendered full text",
        "context": {"locale": "zh", "note": "preserve context"},
        "chats": [{"role": "user", "content": "preserve chat"}],
        "unrelated": {"nested": [1, 2, 3]},
        "session_dict": {
            "topic": "事业",
            "user_question": "会怎样？",
            "user_context": "preserve user context",
            "current_time_str": "2026.07.02 12:00",
            "method": "蓍草法",
            "lines": saved_lines,
            "hex_text": "legacy inner hex text",
            "hex_sections": [{"legacy": True}],
            "hex_overview": {"legacy": True},
            "najia_table": {"rows": [{"god": "legacy inner god"}]},
            "najia_text": "legacy inner Najia text",
            "najia_data": {"main": {"lines": [{"god": "fixed source god"}]}},
            "ai_analysis": "preserve inner AI prose byte-for-byte",
            "ai_response_id": "resp_inner_456",
            "ai_usage": {"total_tokens": 33},
            "reading_brief": {"headline": "preserve inner brief"},
            "unrelated_inner": {"keep": True},
        },
    }


def _refresh(snapshot):
    config, interpretation_repo, najia_repo = _dependencies()
    return _compute_refreshed_snapshot(
        snapshot=snapshot,
        definitions={},
        interpretation_repo=interpretation_repo,
        najia_repo=najia_repo,
        config=config,
    )


def test_repairs_modern_snapshot_exactly_without_rerolling_or_rewriting_prose():
    snapshot = _historical_snapshot()
    original = copy.deepcopy(snapshot)
    config, interpretation_repo, najia_repo = _dependencies()
    from iching.core.hexagram import load_hexagram_definitions

    definitions = load_hexagram_definitions(config.paths.gua_index_file)
    patched = _compute_refreshed_snapshot(
        snapshot=snapshot,
        definitions=definitions,
        interpretation_repo=interpretation_repo,
        najia_repo=najia_repo,
        config=config,
    )

    assert patched is not None
    expected_relations = [
        "父母戊子水",
        "妻财戊戌土",
        "官鬼戊申金",
        "子孙戊午火",
        "妻财戊辰土",
        "兄弟戊寅木",
    ]
    expected_gods = ["青龙", "玄武", "白虎", "腾蛇", "勾陈", "朱雀"]
    inner = patched["session_dict"]

    assert patched["najia_table"] == inner["najia_table"]
    assert patched["najia_text"] == inner["najia_text"]
    assert inner["najia_data"]["block_text"] == inner["najia_text"]
    assert [row["changed_relation"] for row in inner["najia_table"]["rows"]] == expected_relations
    assert [row["god"] for row in inner["najia_table"]["rows"]] == expected_gods
    assert [line["relation"] for line in inner["najia_data"]["changed"]["lines"]] == expected_relations
    assert [line["god"] for line in inner["najia_data"]["changed"]["lines"]] == expected_gods

    preserved_paths = [
        ("ai_text",),
        ("ai_analysis",),
        ("ai_response_id",),
        ("ai_usage",),
        ("reading_brief",),
        ("full_text",),
        ("context",),
        ("chats",),
        ("unrelated",),
        ("session_dict", "lines"),
        ("session_dict", "user_context"),
        ("session_dict", "ai_analysis"),
        ("session_dict", "ai_response_id"),
        ("session_dict", "ai_usage"),
        ("session_dict", "reading_brief"),
        ("session_dict", "unrelated_inner"),
    ]
    for path in preserved_paths:
        before = original
        after = patched
        for key in path:
            before = before[key]
            after = after[key]
        assert after == before, path

    assert snapshot == original
    assert _compute_refreshed_snapshot(
        snapshot=patched,
        definitions=definitions,
        interpretation_repo=interpretation_repo,
        najia_repo=najia_repo,
        config=config,
    ) == patched


def test_invalid_saved_cast_time_skips_the_whole_snapshot():
    snapshot = _historical_snapshot()
    snapshot["session_dict"]["current_time_str"] = "not-a-cast-time"
    original = copy.deepcopy(snapshot)

    assert _refresh(snapshot) is None
    assert snapshot == original


def test_guarded_update_request_is_owner_scoped_and_preserves_updated_at():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["request"] = request
        return httpx.Response(200, json=[{"session_id": "session-1"}])

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = SupabaseRestClient(
        project_url="https://example.supabase.co",
        service_key="service-key",
        client=http_client,
    )

    updated = client.update_session_if_unchanged(
        session_id="session-1",
        user_id="user-1",
        expected_updated_at="2026-07-12T08:30:00+00:00",
        payload={"payload_snapshot": {"repaired": True}},
    )

    assert updated is True
    request = captured["request"]
    assert request.method == "PATCH"
    assert parse_qs(request.url.query.decode()) == {
        "session_id": ["eq.session-1"],
        "user_id": ["eq.user-1"],
        "updated_at": ["eq.2026-07-12T08:30:00+00:00"],
    }
    assert request.headers["prefer"] == "return=representation"
    assert request.read() == b'{"payload_snapshot":{"repaired":true}}'
