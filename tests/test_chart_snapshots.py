from __future__ import annotations

import base64
from copy import deepcopy
from datetime import datetime
import gzip
import json
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from iching.core.metaphysics import build_metaphysics_chart
from iching.integrations.supabase_client import SupabaseUser
from iching.web.chart_service import ChartArchiveService
from iching.web.chart_snapshots import (
    CHART_SNAPSHOT_DECODED_BYTES,
    CHART_SNAPSHOT_ENCODING,
    CHART_SNAPSHOT_STORAGE_BYTES,
    decode_chart_snapshot,
)
from iching.web.models import MetaphysicsChartSaveRequest


USER_ID = "00000000-0000-0000-0000-000000000001"
SUBJECT_ID = "00000000-0000-0000-0000-000000000002"
CHART_ID = "00000000-0000-0000-0000-000000000003"
RULE_VERSIONS = {
    "calendar": "canonical-calendar-1",
    "pattern_bundle": "zzq-shen-canonical-v1",
    "pattern_digest": "8c41b4f22b8461526651b364d95144a74036c9e9a8606f1088eb53c4d356a523",
    "shensha": "shensha-2026.07-v2.1",
    "consumer": "metaphysics-consumer-2026.07-v4",
}


def _envelope(compressed: bytes) -> dict:
    return {"_encoding": CHART_SNAPSHOT_ENCODING, "data": base64.b64encode(compressed).decode("ascii")}


def _encode(value: object) -> dict:
    raw = json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()
    return _envelope(gzip.compress(raw, compresslevel=6, mtime=0))


def _save_payload(snapshot: dict, *, schema_version: int = 7) -> dict:
    return {
        "chart_type": "bazi",
        "subject": {"birth_local_timestamp": "2024-02-10T12:00", "timezone": "Asia/Shanghai", "gender": "female"},
        "birth_date": "2024-02-10",
        "input_snapshot": {"form": {}},
        "result_snapshot": snapshot,
        "engine_name": "canonical-calendar",
        "engine_version": "1+sxtwl-2.0.7+lunar-python-1.4.8",
        "rules_version": "shensha-2026.07-v2.1",
        "schema_version": schema_version,
    }


@pytest.fixture(scope="module")
def full_life_snapshot() -> dict:
    return {"chart": build_metaphysics_chart(
        datetime.fromisoformat("2024-02-10T12:00:00+08:00"),
        timezone_name="Asia/Shanghai", gender="female",
        reference_timestamp=datetime.fromisoformat("2026-10-01T12:00:00+08:00"),
        include_period_details=True,
    ), "generated_at": "2026-10-01T04:00:00Z", "subject_name": "合成测试命主"}


def test_real_full_life_snapshot_roundtrips_exactly_under_existing_storage_cap(full_life_snapshot: dict) -> None:
    raw = json.dumps(full_life_snapshot, ensure_ascii=False, separators=(",", ":")).encode()
    assert len(raw) > 20_000_000
    assert len(raw) < CHART_SNAPSHOT_DECODED_BYTES
    envelope = _encode(full_life_snapshot)
    assert len(json.dumps(envelope).encode()) < CHART_SNAPSHOT_STORAGE_BYTES
    before = deepcopy(envelope)
    request = MetaphysicsChartSaveRequest.model_validate(_save_payload(envelope))

    decoded = decode_chart_snapshot(request.result_snapshot)
    assert decoded == full_life_snapshot
    assert decoded["chart"]["rule_versions"] == full_life_snapshot["chart"]["rule_versions"]
    assert decoded["chart"]["structure"]["patterns"] == full_life_snapshot["chart"]["structure"]["patterns"]
    assert request.result_snapshot == before


def test_archive_stores_envelope_and_returns_original_chart(full_life_snapshot: dict) -> None:
    envelope = _encode(full_life_snapshot)
    request = MetaphysicsChartSaveRequest.model_validate(_save_payload(envelope))
    client = Mock()
    client.insert_row.side_effect = lambda table, payload: {
        "id": SUBJECT_ID if table == "chart_subjects" else CHART_ID, **deepcopy(payload)
    }
    service = ChartArchiveService(client)

    saved = service.save_chart(request=request, user=SupabaseUser(id=USER_ID))
    stored = client.insert_row.call_args_list[-1].args[1]["result_snapshot"]
    assert stored == envelope
    assert saved["result_snapshot"] == full_life_snapshot
    assert request.result_snapshot == envelope

    row = {"id": CHART_ID, "schema_version": 7, "result_snapshot": deepcopy(stored), "subject": {"id": SUBJECT_ID}}
    client.select_rows.return_value = [row]
    fetched = service.fetch_chart(chart_id=CHART_ID, user=SupabaseUser(id=USER_ID))
    assert fetched["result_snapshot"] == full_life_snapshot
    assert row["result_snapshot"] == envelope
    assert client.select_rows.call_args.kwargs["params"]["user_id"] == f"eq.{USER_ID}"


def test_compressed_schema_seven_validates_its_original_rule_metadata() -> None:
    snapshot = {"chart": {"derived_schema_version": 7, "rule_versions": RULE_VERSIONS}}
    request = MetaphysicsChartSaveRequest.model_validate(_save_payload(_encode(snapshot)))
    assert decode_chart_snapshot(request.result_snapshot) == snapshot
    del snapshot["chart"]["rule_versions"]
    for outer_version in (6, 7):
        with pytest.raises(ValidationError, match="schema 7"):
            MetaphysicsChartSaveRequest.model_validate(_save_payload(_encode(snapshot), schema_version=outer_version))


def test_legacy_plain_snapshots_keep_their_representation_and_two_megabyte_limit() -> None:
    legacy = {"chart": {"derived_schema_version": 6, "bazi": "甲辰 丙寅 甲辰 庚午"}}
    request = MetaphysicsChartSaveRequest.model_validate(_save_payload(legacy, schema_version=6))
    assert request.result_snapshot == legacy
    assert decode_chart_snapshot(legacy) is legacy
    with pytest.raises(ValidationError, match="2 MB"):
        MetaphysicsChartSaveRequest.model_validate(_save_payload({"data": "x" * CHART_SNAPSHOT_STORAGE_BYTES}, schema_version=6))


@pytest.mark.parametrize("snapshot", [
    {"_encoding": "iching.chart-snapshot.gzip.v2", "data": ""},
    {"_encoding": CHART_SNAPSHOT_ENCODING, "data": 123},
    {"_encoding": CHART_SNAPSHOT_ENCODING, "data": "", "extra": True},
    {"_encoding": CHART_SNAPSHOT_ENCODING, "data": "!not-base64!"},
    {"_encoding": CHART_SNAPSHOT_ENCODING, "data": "AB=="},
    {"_encoding": CHART_SNAPSHOT_ENCODING, "data": "AAAA"},
])
def test_invalid_envelopes_are_rejected(snapshot: dict) -> None:
    with pytest.raises(ValueError):
        decode_chart_snapshot(snapshot)


@pytest.mark.parametrize("damage", ["crc", "header", "truncated", "trailing", "concatenated"])
def test_gzip_integrity_and_exactly_one_member_are_required(damage: str) -> None:
    compressed = gzip.compress(b'{"chart":{"rule":"original"}}', mtime=0)
    if damage == "crc":
        corrupted = bytearray(compressed)
        corrupted[-8] ^= 1
        compressed = bytes(corrupted)
    elif damage == "header":
        compressed = compressed[:4]
    elif damage == "truncated":
        compressed = compressed[:-1]
    elif damage == "trailing":
        compressed += b"trailing"
    else:
        compressed += gzip.compress(b"{}", mtime=0)
    with pytest.raises(ValueError):
        decode_chart_snapshot(_envelope(compressed))


@pytest.mark.parametrize("raw", [b"[]", b"null", b"42", b'"text"', b"{broken}", b'{"name":"\xff"}', b'{"a":1,"a":2}', b'{"a":NaN}'])
def test_decoded_snapshot_must_be_an_unambiguous_json_object(raw: bytes) -> None:
    with pytest.raises(ValueError):
        decode_chart_snapshot(_envelope(gzip.compress(raw, mtime=0)))


def test_compressed_storage_bound_is_checked_before_decoding() -> None:
    envelope = {"_encoding": CHART_SNAPSHOT_ENCODING, "data": "A" * CHART_SNAPSHOT_STORAGE_BYTES}
    with pytest.raises(ValueError, match="2 MB"):
        decode_chart_snapshot(envelope)


def test_gzip_expansion_stops_at_thirty_two_mebibytes() -> None:
    assert CHART_SNAPSHOT_DECODED_BYTES == 32 * 1024 * 1024
    oversized = b'{"value":"' + b"x" * CHART_SNAPSHOT_DECODED_BYTES + b'"}'
    compressed = gzip.compress(oversized, compresslevel=6, mtime=0)
    assert len(compressed) < CHART_SNAPSHOT_STORAGE_BYTES
    with pytest.raises(ValueError, match="32 MiB"):
        decode_chart_snapshot(_envelope(compressed))
