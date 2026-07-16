from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from iching.core.bazi_rules.authority import load_packaged_overlay
from iching.core.bazi_rules.compiler import research_corpus_digest
from iching.core.bazi_rules.engine import evaluate_pattern_lifecycle
from iching.core.bazi_rules.fact_graph import (
    build_bazi_fact_graph,
    build_rule_evaluation_context,
)
from iching.core.bazi_rules.registry import (
    compile_research_registry,
    registry_from_data,
    registry_to_data,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_MANIFEST = PROJECT_ROOT / "research/classics/sources/manifest.json"
CORPUS_MANIFEST = PROJECT_ROOT / "research/classics/yuanhai_ziping/manifest.json"
EXPECTED_WITNESSES = {
    "yuanhai-ziping-nlc-wanli-v1": (48, 14_387_365),
    "yuanhai-ziping-nlc-wanli-v2": (30, 8_982_462),
    "yuanhai-ziping-nlc-wanli-v3": (46, 13_845_843),
    "yuanhai-ziping-nlc-wanli-v4": (41, 12_376_070),
}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_stable_jsonl(relative_path: str) -> list[dict[str, Any]]:
    path = PROJECT_ROOT / relative_path
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    assert all(lines)
    records = [json.loads(line) for line in lines]
    assert lines == [
        json.dumps(record, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        for record in records
    ]
    return records


def test_wanli_witness_parts_are_frozen_and_public_domain() -> None:
    source_manifest = _load_json(SOURCE_MANIFEST)
    witnesses = {item["id"]: item for item in source_manifest["witnesses"]}
    assert EXPECTED_WITNESSES.keys() <= witnesses.keys()

    for witness_id, (pages, size) in EXPECTED_WITNESSES.items():
        witness = witnesses[witness_id]
        assert witness["authority_role"] == "canonical_textual_authority"
        assert witness["pages"] == pages
        assert witness["bytes"] == size
        assert witness["rights"]["status"] == "public_domain"
        assert witness["rights"]["production_use_allowed"] is True
        assert witness["provenance_url"].startswith(
            "https://upload.wikimedia.org/wikipedia/commons/"
        )
        raw_path = PROJECT_ROOT / witness["local_path"]
        if raw_path.exists():
            assert raw_path.stat().st_size == size
            assert _file_sha256(raw_path) == witness["sha256"]


def test_first_yuanhai_tranche_is_scan_traceable_and_honestly_non_executable() -> None:
    manifest = _load_json(CORPUS_MANIFEST)
    assert manifest["schema"] == "iching.classics.yuanhai-corpus.v1"
    boundary = manifest["authority_boundary"]
    assert boundary["runtime_bundle_created"] is True
    assert boundary["runtime_bundle_status"] == "bound_zero_executable_partial_registry"
    assert "zero-executable" in boundary["note"]
    assert "no executable doctrine" in boundary["note"]
    assert set(manifest["witness_ids"]) == set(EXPECTED_WITNESSES)
    assert len(manifest["chapters"]) == 1

    locators = {item["id"]: item for item in manifest["locators"]}
    assert len(locators) == 6
    for locator in locators.values():
        assert locator["witness_id"] == "yuanhai-ziping-nlc-wanli-v1"
        assert 37 <= locator["pdf_page"] <= 42
        assert locator["visually_verified"] is True
        assert locator["review_state"] == "scan_verified"
        assert (
            locator["quote_sha256"]
            == hashlib.sha256(locator["quote"].encode("utf-8")).hexdigest()
        )

    chapter = manifest["chapters"][0]
    record_sets = {
        kind: _load_stable_jsonl(chapter["files"][kind])
        for kind in ("segments", "propositions", "rule_candidates", "non_rules")
    }
    assert chapter["files"]["examples"] is None
    assert chapter["record_counts"] == {
        "examples": 0,
        **{kind: len(records) for kind, records in record_sets.items()},
    }
    for kind, records in record_sets.items():
        path = PROJECT_ROOT / chapter["files"][kind]
        assert chapter["file_sha256"][kind] == _file_sha256(path)
        assert all(record["chapter_id"] == chapter["id"] for record in records)

    segment_ids = {item["id"] for item in record_sets["segments"]}
    proposition_ids = {item["id"] for item in record_sets["propositions"]}
    assert all(
        set(item["locator_ids"]) <= set(locators)
        for item in record_sets["segments"] + record_sets["propositions"]
    )
    assert all(
        set(item["segment_ids"]) <= segment_ids
        for item in record_sets["propositions"] + record_sets["non_rules"]
    )
    assert all(
        item["proposition_id"] in proposition_ids
        and item["execution_ready"] is False
        and item["candidate_status"] == "source_verified_not_compiled"
        and item["semantic_status"].startswith("requires_")
        for item in record_sets["rule_candidates"]
    )
    assert manifest["coverage"]["known_gaps"]
    assert "non-executable" in manifest["coverage"]["production_interpretation"]


def test_zero_executable_yuanhai_corpus_compiles_to_a_bound_empty_overlay() -> None:
    manifest = _load_json(CORPUS_MANIFEST)
    compiled = compile_research_registry(
        PROJECT_ROOT,
        bundle_id="yuanhai-ziping-v1",
        authority_layer="yuanhai",
        corpus_manifest=CORPUS_MANIFEST,
    )
    expected_corpus_digest = research_corpus_digest(
        SOURCE_MANIFEST,
        CORPUS_MANIFEST,
    )
    packaged = load_packaged_overlay("yuanhai")

    assert manifest["authority_boundary"]["layer"] == compiled.authority_layer
    assert compiled.rules == ()
    assert compiled.source_provenance == ()
    assert compiled.source_bundle_digest == expected_corpus_digest
    assert compiled.source_bundle_digest
    assert registry_from_data(registry_to_data(compiled)) == compiled
    assert packaged.availability == "partial"
    assert packaged.registry is not None
    assert registry_to_data(packaged.registry) == registry_to_data(compiled)


def test_zero_rule_overlay_cannot_leak_the_legacy_direct_officer_fallback() -> None:
    descriptor = load_packaged_overlay("yuanhai")
    assert descriptor.registry is not None
    context = build_rule_evaluation_context(
        build_bazi_fact_graph(
            [
                {
                    "label": label,
                    "stem": text[0],
                    "branch": text[1],
                    "text": text,
                }
                for label, text in zip(
                    ("年", "月", "日", "时"),
                    ("甲子", "癸酉", "甲午", "戊辰"),
                )
            ]
        )
    )

    with pytest.raises(ValueError, match="not declared"):
        evaluate_pattern_lifecycle(context, descriptor.registry)
