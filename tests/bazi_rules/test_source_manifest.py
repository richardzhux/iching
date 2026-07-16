from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_MANIFEST = PROJECT_ROOT / "research/classics/sources/manifest.json"
CORPUS_MANIFEST = PROJECT_ROOT / "research/classics/ziping_zhenquan/manifest.json"

EXPECTED_CHAPTERS = {
    "zzq.useful-god.success-failure-rescue": "論用神成敗救應",
    "zzq.pattern.direct-officer": "論正官",
}

DIRECT_OFFICER_SEGMENT_ORDER = [
    "zzq.seg.officer.heading",
    "zzq.seg.officer.principle.doctrine",
    "zzq.seg.officer.principle.analogy",
    "zzq.seg.officer.formation.likes-dislikes",
    "zzq.seg.officer.formation.evaluation",
    "zzq.seg.officer.formation.dual-support",
    "zzq.seg.officer.formation.outcome",
    "zzq.seg.officer.example.xue.structure",
    "zzq.seg.officer.example.xue.outcome",
    "zzq.seg.officer.example.lesser-rank.structure",
    "zzq.seg.officer.example.lesser-rank.evaluation",
    "zzq.seg.officer.example.lesser-rank.support-conflict",
    "zzq.seg.officer.example.lesser-rank.outcome",
    "zzq.seg.officer.single-support",
    "zzq.seg.officer.transformation.rule",
    "zzq.seg.officer.transformation.evaluation",
    "zzq.seg.officer.example.jin",
    "zzq.seg.officer.rescue-overview.introduction",
    "zzq.seg.officer.rescue-overview.evaluation",
    "zzq.seg.officer.rescue-overview.doctrine",
    "zzq.seg.officer.example.xuan",
    "zzq.seg.officer.example.li",
    "zzq.seg.officer.damage",
    "zzq.seg.officer.example.fan.outcome-introduction",
    "zzq.seg.officer.example.fan.mechanism",
    "zzq.seg.officer.example.fan.evaluation",
    "zzq.seg.officer.example.fan.outcome",
    "zzq.seg.officer.closing.doctrine",
    "zzq.seg.officer.closing.cross-reference",
]

DIRECT_OFFICER_DIPLOMATIC_CONTENT_SHA256 = (
    "2715723f5948aa2964d8acbdfed7262d262915e9e32add1b2fd998c3f28e0b47"
)
DIRECT_OFFICER_NORMALIZED_CONTENT_SHA256 = (
    "c50b54803248803a01de5c1c77fe450073faeb8dc518b36290b458ae88a45cd7"
)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(relative_path: str) -> list[dict[str, Any]]:
    path = PROJECT_ROOT / relative_path
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    assert text == "" or all(lines), f"{relative_path} must not contain blank lines"
    records = [json.loads(line) for line in lines]
    assert lines == [
        json.dumps(record, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        for record in records
    ], f"{relative_path} must use deterministic stable-key JSONL"
    return records


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_source_witnesses_freeze_identity_rights_and_raw_provenance() -> None:
    manifest = _load_json(SOURCE_MANIFEST)
    assert manifest["schema"] == "iching.classics.source-manifest.v1"

    witnesses = {item["id"]: item for item in manifest["witnesses"]}
    assert set(witnesses) == {
        "gengcun-ji-ncl-06599",
        "qin-shenan-1926-ziping-zhenquan-v2",
        "world-library-ziping-zhenquan-nlc",
    }
    gengcun = witnesses["gengcun-ji-ncl-06599"]
    qin = witnesses["qin-shenan-1926-ziping-zhenquan-v2"]
    world = witnesses["world-library-ziping-zhenquan-nlc"]
    assert gengcun["authority_role"] == "canonical_textual_authority"
    assert gengcun["authority_roles"] == ["canonical_textual_authority"]
    assert qin["authority_role"] == "operational_locator"
    assert qin["authority_roles"] == ["operational_locator", "independent_collation"]
    assert world["authority_role"] == "search_aid"
    assert world["authority_roles"] == ["search_aid", "comparison_only"]
    assert "independent_collation" not in world["authority_roles"]

    for witness in witnesses.values():
        assert witness["bytes"] > 0
        assert witness["pages"] > 0
        assert re.fullmatch(r"[0-9a-f]{64}", witness["sha256"])
        assert witness["completeness"] == "complete"
        assert witness["provenance_url"].startswith("https://upload.wikimedia.org/")
        assert witness["local_path"].startswith("references/classics/raw/")
        assert witness["rights"]["status"] != "unknown"
        raw_path = PROJECT_ROOT / witness["local_path"]
        if raw_path.exists():
            assert raw_path.stat().st_size == witness["bytes"]
            assert _file_sha256(raw_path) == witness["sha256"]

    assert gengcun["rights"]["production_use_allowed"] is True
    assert qin["rights"]["production_use_allowed"] is True
    assert world["rights"]["production_use_allowed"] is False
    assert world["rights"]["caveat"]
    eligible_independent_collators = {
        witness["id"]
        for witness in witnesses.values()
        if "independent_collation" in witness["authority_roles"]
        and witness["rights"]["production_use_allowed"]
    }
    assert eligible_independent_collators == {"qin-shenan-1926-ziping-zhenquan-v2"}
    assert all(aid["authority_role"] == "search_aid" for aid in manifest["search_aids"])
    assert all(
        aid["production_use_allowed"] is False for aid in manifest["search_aids"]
    )


def test_vertical_slice_is_complete_deterministic_and_scan_traceable() -> None:
    sources = _load_json(SOURCE_MANIFEST)
    manifest = _load_json(CORPUS_MANIFEST)
    witnesses = {item["id"]: item for item in sources["witnesses"]}
    locators = {item["id"]: item for item in manifest["locators"]}

    assert manifest["schema"] == "iching.classics.corpus-manifest.v1"
    assert manifest["commentary_boundary"]["later_commentary_imported"] is False
    assert manifest["commentary_boundary"]["canonical_layer"] == "shen_core"
    assert {
        chapter["id"]: chapter["title_diplomatic"] for chapter in manifest["chapters"]
    } == EXPECTED_CHAPTERS
    assert len(locators) == len(manifest["locators"])

    variants = manifest["witness_variants"]
    assert len({item["id"] for item in variants}) == len(variants) == 23
    assert sum(item["id"].startswith("var.useful.") for item in variants) == 12
    assert sum(item["id"].startswith("var.officer.") for item in variants) == 11
    assert all(item["kind"] in {"lexical", "orthographic"} for item in variants)
    assert all(item["base_reading"] != item["witness_reading"] for item in variants)
    assert all(
        set(item["base_locator_ids"] + item["witness_locator_ids"]) <= set(locators)
        for item in variants
    )
    assert all(item["witness_id"] in witnesses for item in variants)
    material_pairs = {
        (item["base_reading"], item["witness_reading"]) for item in variants
    }
    assert ("位置安適", "位置妥帖") in material_pairs
    assert ("印能護官亦能減官", "印能護官亦能洩官") in material_pairs
    assert ("逢伏〔旁改制〕煞；遇伏制", "逢制煞；遇制伏") in material_pairs

    for locator in locators.values():
        assert locator["witness_id"] in witnesses
        assert locator["pdf_page"] > 0
        assert locator["quote"]
        assert locator["quote_sha256"] == _sha256(locator["quote"])
        assert locator["url"].startswith("https://")

    all_segment_ids: set[str] = set()
    all_proposition_ids: set[str] = set()

    for chapter in manifest["chapters"]:
        segments = _load_jsonl(chapter["files"]["segments"])
        propositions = _load_jsonl(chapter["files"]["propositions"])
        rules = _load_jsonl(chapter["files"]["rule_candidates"])
        examples = _load_jsonl(chapter["files"]["examples"])
        non_rules = _load_jsonl(chapter["files"]["non_rules"])

        assert chapter["completeness"] == "complete"
        assert chapter["review_state"] == "scan_verified"
        assert {
            kind: len(records)
            for kind, records in {
                "segments": segments,
                "propositions": propositions,
                "rule_candidates": rules,
                "examples": examples,
                "non_rules": non_rules,
            }.items()
        } == chapter["record_counts"]

        segments_by_id = {item["id"]: item for item in segments}
        segment_ids = set(segments_by_id)
        proposition_ids = {item["id"] for item in propositions}
        assert len(segment_ids) == len(segments)
        assert len(proposition_ids) == len(propositions)
        assert all(item["chapter_id"] == chapter["id"] for item in segments)
        assert all(item["chapter_id"] == chapter["id"] for item in propositions)
        assert all(
            item["diplomatic_text"] and item["normalized_search_text"]
            for item in segments
        )
        assert any(
            item["diplomatic_text"] != item["normalized_search_text"]
            for item in segments
        )
        assert all(
            item["layer"] in {"shen_core", "editorial", "commentary", "example"}
            for item in segments
        )
        assert all(set(item["locator_ids"]) <= set(locators) for item in segments)

        transcript = "\n".join(item["diplomatic_text"] for item in segments)
        assert chapter["diplomatic_sha256"] == _sha256(transcript)
        if chapter["id"] == "zzq.useful-god.success-failure-rescue":
            formation = next(
                item for item in segments if item["id"] == "zzq.seg.useful.formation"
            )
            assert "身強七煞逢伏〔旁改制〕煞格成也" in formation["diplomatic_text"]
            assert "身強七煞逢制煞格成也" in formation["normalized_search_text"]

        for proposition in propositions:
            assert set(proposition["segment_ids"]) <= segment_ids
            assert set(proposition["locator_ids"]) <= set(locators)
            assert (
                proposition["explicit_conditions"] or proposition["inferred_conditions"]
            )
            if proposition["production_eligible"]:
                assert proposition["layer"] != "commentary"
                assert all(
                    segments_by_id[segment_id]["layer"] != "commentary"
                    for segment_id in proposition["segment_ids"]
                )
                assert proposition["review_state"] == "scan_verified"
                assert proposition["locator_ids"]
                for locator_id in proposition["locator_ids"]:
                    locator = locators[locator_id]
                    assert locator["visually_verified"] is True
                    assert (
                        witnesses[locator["witness_id"]]["rights"][
                            "production_use_allowed"
                        ]
                        is True
                    )

        propositions_by_id = {item["id"]: item for item in propositions}
        assert all(item["proposition_id"] in proposition_ids for item in rules)
        assert all(item["production_eligible"] is True for item in rules)
        assert all(
            propositions_by_id[item["proposition_id"]]["production_eligible"] is True
            for item in rules
        )
        unresolved = [
            item for item in rules if item["semantic_status"].startswith("requires_")
        ]
        assert unresolved
        assert all(item["execution_ready"] is False for item in unresolved)
        assert all(
            item["candidate_status"] == "source_verified_not_compiled"
            for item in unresolved
        )
        assert all(set(item["segment_ids"]) <= segment_ids for item in examples)
        assert all(set(item["segment_ids"]) <= segment_ids for item in non_rules)

        all_segment_ids.update(segment_ids)
        all_proposition_ids.update(proposition_ids)

    assert len(all_segment_ids) == sum(
        chapter["record_counts"]["segments"] for chapter in manifest["chapters"]
    )
    assert len(all_proposition_ids) == sum(
        chapter["record_counts"]["propositions"] for chapter in manifest["chapters"]
    )


def test_direct_officer_rule_segments_exclude_analogy_evaluation_and_outcome_text() -> (
    None
):
    segments = _load_jsonl(
        "research/classics/ziping_zhenquan/segments/zzq.pattern.direct-officer.jsonl"
    )
    propositions = _load_jsonl(
        "research/classics/ziping_zhenquan/propositions/zzq.pattern.direct-officer.jsonl"
    )
    examples = _load_jsonl(
        "research/classics/ziping_zhenquan/examples/zzq.pattern.direct-officer.jsonl"
    )
    non_rules = _load_jsonl(
        "research/classics/ziping_zhenquan/non_rules/zzq.pattern.direct-officer.jsonl"
    )

    assert [segment["id"] for segment in segments] == DIRECT_OFFICER_SEGMENT_ORDER
    assert _sha256("".join(segment["diplomatic_text"] for segment in segments)) == (
        DIRECT_OFFICER_DIPLOMATIC_CONTENT_SHA256
    )
    assert _sha256(
        "".join(segment["normalized_search_text"] for segment in segments)
    ) == (DIRECT_OFFICER_NORMALIZED_CONTENT_SHA256)

    segments_by_id = {segment["id"]: segment for segment in segments}
    production_segment_ids = {
        segment_id
        for proposition in propositions
        if proposition["production_eligible"]
        for segment_id in proposition["segment_ids"]
    }
    referenced_segment_ids = {
        segment_id
        for record in (*propositions, *examples, *non_rules)
        for segment_id in record["segment_ids"]
    }
    assert set(segments_by_id) - {"zzq.seg.officer.heading"} <= referenced_segment_ids
    forbidden_text_types = {
        "historical_evaluation",
        "historical_outcome",
        "social_analogy",
    }
    forbidden_outcome_fragments = {
        "大貴",
        "七品",
        "其貴也大",
        "最為貴格",
        "貴極天子",
        "焉得不貴",
    }
    for segment_id in production_segment_ids:
        segment = segments_by_id[segment_id]
        assert segment["layer"] == "shen_core"
        assert segment["text_type"] not in forbidden_text_types
        assert not any(
            fragment in segment["diplomatic_text"]
            for fragment in forbidden_outcome_fragments
        )
