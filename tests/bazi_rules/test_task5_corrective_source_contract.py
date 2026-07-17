from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "research" / "classics" / "ziping_zhenquan"
FOUR_PILLAR_RE = re.compile(
    r"([甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥])"
    r"([甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥])"
    r"([甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥])"
    r"([甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥])"
)


def _manifest() -> dict[str, Any]:
    return json.loads((CORPUS / "manifest.json").read_text(encoding="utf-8"))


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _rule(rule_id: str) -> dict[str, Any]:
    for path in sorted((CORPUS / "rules").glob("*.jsonl")):
        for record in _jsonl(path):
            if record["id"] == rule_id:
                return record
    raise AssertionError(f"missing rule candidate {rule_id}")


def _walk_predicates(predicate: dict[str, Any]) -> list[dict[str, Any]]:
    records = [predicate]
    for child in predicate.get("children", []):
        records.extend(_walk_predicates(child))
    nested = predicate.get("child")
    if nested is not None:
        records.extend(_walk_predicates(nested))
    return records


def test_page_map_and_complete_witness_status_are_scan_honest() -> None:
    manifest = _manifest()
    expected = {
        "zzq.useful-god.success-failure-rescue": (18, 20),
        "zzq.pattern.direct-officer": (57, 60),
        "zzq.pattern.wealth": (60, 64),
        "zzq.pattern.resource": (64, 68),
        "zzq.pattern.eating-god": (68, 71),
        "zzq.pattern.seven-killings": (71, 75),
        "zzq.pattern.hurting-officer": (75, 79),
        "zzq.pattern.yang-blade": (79, 81),
        "zzq.pattern.prosperity-robbery": (82, 86),
        "zzq.pattern.special-gate": (86, 90),
        "zzq.appendix.pattern-plates": (91, 102),
    }
    actual = {
        row["chapter_id"]: (row["start_pdf_page"], row["end_pdf_page"])
        for row in manifest["chapter_page_map"]
    }
    assert actual == expected

    chapters = {row["id"]: row for row in manifest["chapters"]}
    for chapter_id in expected:
        assert chapters[chapter_id]["completeness"] == "complete"
    food_note = chapters["zzq.pattern.eating-god"]["completeness_note"]
    assert "homoeoteleuton" in food_note
    assert "do not import absent wording" in food_note


def test_full_witness_visual_review_and_appendix_boundary_are_explicit() -> None:
    manifest = _manifest()
    scope = manifest["witness_review_scope"]
    assert scope["canonical_witness_id"] == "gengcun-ji-ncl-06599"
    assert scope["corpus_coverage"] == "selected_chapters_only"
    assert scope["visual_review"] == {
        "end_pdf_page": 103,
        "start_pdf_page": 1,
        "status": "complete",
    }
    assert scope["not_transcribed_scope"]["pdf_pages"] == [1, 56]
    assert scope["terminal_page"]["classification"] == "blank_content_page"
    assert scope["terminal_page"]["pdf_page"] == 103
    assert scope["known_witness_lacunae"] == [
        {
            "chapter": "論時說拘泥格局",
            "note": (
                "The opening text is absent across the PDF page 54 to 55 transition "
                "in this witness; no missing wording was imported from another edition."
            ),
            "pdf_pages": [54, 55],
        }
    ]

    appendix = next(
        row
        for row in manifest["chapters"]
        if row["id"] == "zzq.appendix.pattern-plates"
    )
    assert appendix["record_counts"] == {
        "examples": 93,
        "non_rules": 12,
        "propositions": 0,
        "rule_candidates": 0,
        "segments": 93,
    }
    assert "no generic rule is inferred" in appendix["completeness_note"]
    assert "Working interpretations" in appendix["completeness_note"]

    appendix_examples = _jsonl(
        CORPUS / "examples" / "zzq.appendix.pattern-plates.jsonl"
    )
    appendix_segments = {
        row["id"]: row
        for row in _jsonl(CORPUS / "segments" / "zzq.appendix.pattern-plates.jsonl")
    }
    assert len(appendix_examples) == 93
    assert all("plate_note" not in row for row in appendix_examples)
    for example in appendix_examples:
        identity = (
            example["pattern_label"]
            if example["name"] == example["pattern_label"]
            else example["pattern_label"] + example["name"]
        )
        expected_diplomatic = "".join((identity, *example["pillars"]))
        assert appendix_segments[example["segment_ids"][0]]["diplomatic_text"] == (
            expected_diplomatic
        )


def test_current_locator_quotes_use_their_actual_scan_pages() -> None:
    locators = {row["id"]: row for row in _manifest()["locators"]}
    expected = {
        "loc.gc.officer.audit-ou1": 59,
        "loc.gc.officer.audit-ou2": 60,
        "loc.gc.wealth.61-officer-path": 61,
        "loc.gc.wealth.62-killing-paths": 62,
        "loc.gc.wealth.63-period": 63,
        "loc.gc.resource.64-opening": 64,
        "loc.gc.resource.65-wealth-path": 65,
        "loc.gc.resource.67-period": 67,
        "loc.gc.food.68": 68,
        "loc.gc.food.69": 69,
        "loc.gc.food.70": 70,
        "loc.gc.kill.71": 71,
        "loc.gc.kill.73-blade-path": 73,
        "loc.gc.kill.74-period": 74,
        "loc.gc.hurting.76-wealth-path": 76,
        "loc.gc.hurting.76-resource-path": 76,
        "loc.gc.hurting.77-officer-path": 77,
        "loc.gc.hurting.78-period": 78,
        "loc.gc.blade.79-opening": 79,
        "loc.gc.blade.80-output-alternatives": 80,
        "loc.gc.blade.81-period": 81,
        "loc.gc.blade.81-heading": 81,
        "loc.gc.lu-robbery.82-heading": 82,
        "loc.gc.lu-robbery.84-mixture": 84,
        "loc.gc.lu-robbery.85-period": 85,
        "loc.gc.special.86": 86,
    }
    assert {
        locator_id: locators[locator_id]["pdf_page"] for locator_id in expected
    } == expected


def test_conflated_source_alternatives_are_split_and_misreading_is_removed() -> None:
    segments = {
        record["id"]: record
        for path in sorted((CORPUS / "segments").glob("zzq.pattern.*.jsonl"))
        for record in _jsonl(path)
    }
    assert "zzq.seg.wealth.officer-path" in segments
    assert "zzq.seg.wealth.output-path" in segments
    assert "zzq.seg.food.killing-resource-alternative" in segments
    assert "zzq.seg.food.single-killing-alternative" in segments
    assert "zzq.seg.blade.output-resource-alternative" in segments
    assert "zzq.seg.blade.heavy-killing-reduction-alternative" in segments
    assert "zzq.seg.blade.clearance-alternative" in segments
    assert "zzq.seg.lu-robbery.officer-resource-support" in segments
    assert "zzq.seg.lu-robbery.officer-wealth-support" in segments
    assert "zzq.seg.kill.blade-path" in segments
    assert "用刃當者" in segments["zzq.seg.kill.blade-path"]["diplomatic_text"]
    assert all("用印當者" not in row["diplomatic_text"] for row in segments.values())

    prosperity_segments = {
        row["id"]
        for row in _jsonl(CORPUS / "segments" / "zzq.pattern.prosperity-robbery.jsonl")
    }
    assert "zzq.seg.lu-robbery.page-81-boundary" not in prosperity_segments


def test_qin_end_matter_erratum_prevents_false_production_mapping() -> None:
    manifest = _manifest()
    erratum = next(row for row in manifest["errata"] if row["id"] == "err.qin.160-164")
    assert erratum["pdf_pages"] == [160, 161, 162, 163, 164]
    assert erratum["classification"] == "publisher_end_matter"
    assert erratum["production_mapping"] is False

    for locator in manifest["locators"]:
        assert not (
            locator["witness_id"] == "qin-shenan-1926-ziping-zhenquan-v2"
            and locator["pdf_page"] in erratum["pdf_pages"]
        )


def test_ordinary_examples_separate_author_claim_from_engine_expectation() -> None:
    for path in sorted((CORPUS / "examples").glob("zzq.pattern.*.jsonl")):
        for record in _jsonl(path):
            assert "author_claim" in record, (path, record["id"])
            assert "engine_expectation" in record, (path, record["id"])
            assert "source_claim" not in record, (path, record["id"])


def test_every_parseable_source_chart_has_a_distinct_structured_example() -> None:
    source_charts = {
        match
        for path in sorted((CORPUS / "segments").glob("*.jsonl"))
        for record in _jsonl(path)
        for match in FOUR_PILLAR_RE.findall(record["normalized_search_text"])
    }
    examples = {
        tuple(record["pillars"]): record
        for path in sorted((CORPUS / "examples").glob("*.jsonl"))
        for record in _jsonl(path)
    }

    assert source_charts <= set(examples)
    assert examples[("戊戌", "乙卯", "丙午", "乙亥")]["id"] == (
        "zzq.example.resource.li-zhuangyuan-r3"
    )
    assert examples[("己巳", "癸亥", "壬午", "丙午")]["id"] == (
        "zzq.example.lu-robbery.yuan-l7"
    )
    assert examples[("戊戌", "乙卯", "丙午", "乙亥")]["engine_expectation"] is None
    assert examples[("己巳", "癸亥", "壬午", "丙午")]["engine_expectation"] is None


def test_candidate_routing_is_declared_engine_policy_not_scan_explicit_doctrine() -> (
    None
):
    manifest = _manifest()
    policy = manifest["engine_policies"]["month_command_candidate_routing"]
    assert policy["authority"] == "canonical_engine_ontology"
    assert policy["scan_explicit"] is False
    assert policy["source_framework_ids"]


def test_all_119_ordinary_and_officer_period_paragraphs_have_explicit_source_dispositions() -> (
    None
):
    manifest = _manifest()
    dispositions = manifest["paragraph_dispositions"]
    locator_ids = {row["id"] for row in manifest["locators"]}
    segment_ids = {
        row["id"]
        for path in sorted((CORPUS / "segments").glob("zzq.pattern.*.jsonl"))
        for row in _jsonl(path)
    }
    non_rule_ids = {
        row["id"]
        for path in sorted((CORPUS / "non_rules").glob("zzq.pattern.*.jsonl"))
        for row in _jsonl(path)
    }
    assert len(dispositions) == 119
    assert len({row["audit_id"] for row in dispositions}) == 119
    assert {
        chapter_id: sum(row["chapter_id"] == chapter_id for row in dispositions)
        for chapter_id in {row["chapter_id"] for row in dispositions}
    } == {
        "zzq.pattern.direct-officer": 6,
        "zzq.pattern.wealth": 18,
        "zzq.pattern.resource": 18,
        "zzq.pattern.eating-god": 14,
        "zzq.pattern.seven-killings": 17,
        "zzq.pattern.hurting-officer": 17,
        "zzq.pattern.yang-blade": 9,
        "zzq.pattern.prosperity-robbery": 20,
    }
    for row in dispositions:
        assert row["pdf_pages"]
        assert row["start_anchor"]
        assert row["required_coverage"]
        assert row["adjudication"]
        assert set(row["locator_ids"]) <= locator_ids
        assert set(row["segment_ids"]) <= segment_ids
        assert set(row["non_rule_ids"]) <= non_rule_ids
        if row["provenance"] == "period":
            assert row["disposition"] == "excluded_period_doctrine"
            assert row["runtime_ids"] == []
            assert row["non_rule_ids"]
        if row["audit_id"] in {"F7", "F8"}:
            assert row["paragraph_text_status"] == "witness_lacuna_partial_paragraph"
            assert "Gengcun ji PDF page 69" in row["paragraph_text_note"]
            assert "does not" in row["paragraph_text_note"]
        else:
            assert row["paragraph_text_status"] == "full_paragraph"


def test_known_semantic_overclaims_are_not_executable() -> None:
    unresolved = {
        "zzq.rule.food.form-abandon-follow-killing",
        "zzq.rule.food.damage-owl",
        "zzq.rule.food.rescue-owl-wealth",
        "zzq.rule.hurting.form-killing-resource-no-wealth",
        "zzq.rule.direct-wealth.form-position-safe-resource",
        "zzq.rule.indirect-wealth.form-position-safe-resource",
    }
    for rule_id in unresolved:
        record = _rule(rule_id)
        assert record["execution_ready"] is False, rule_id
        assert record["candidate_status"] == "source_verified_not_compiled", rule_id
        assert "predicate" not in record, rule_id


def test_resource_officer_path_requires_exposed_officer() -> None:
    for prefix in ("direct", "indirect"):
        record = _rule(f"zzq.rule.{prefix}-resource.form-officer-resource")
        officer_predicates = [
            predicate
            for predicate in _walk_predicates(record["predicate"])
            if predicate.get("gods") == ["正官"]
        ]
        assert officer_predicates
        assert officer_predicates[0]["origins"] == ["exposed_stem"]


def test_generic_killing_control_does_not_narrow_control_to_eating_god() -> None:
    for pattern in ("month-prosperity", "month-robbery"):
        record = _rule(f"zzq.rule.{pattern}.form-killing-control")
        control_predicates = [
            predicate
            for predicate in _walk_predicates(record["predicate"])
            if predicate.get("op") == "relation_exists"
        ]
        assert control_predicates
        assert control_predicates[0]["controller_gods"] == ["伤官", "食神"]
        assert control_predicates[0]["controlled_gods"] == ["七杀"]


def test_blade_no_hurting_condition_has_declared_cross_doctrine_support() -> None:
    record = _rule("zzq.rule.blade.form-officer-killing-support")
    assert record["metadata"]["supporting_source_ids"] == [
        "zzq.prop.useful.form-blade-001"
    ]
