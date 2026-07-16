from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import pytest

from iching.core.bazi_rules.engine import (
    evaluate_pattern_lifecycle,
    evaluate_pattern_set,
)
from iching.core.bazi_rules.fact_graph import (
    build_bazi_fact_graph,
    build_rule_evaluation_context,
)
from iching.core.bazi_rules.predicates import evaluate_predicate
from iching.core.bazi_rules.registry import (
    RegistryRule,
    RuleRegistry,
    compile_research_registry,
    load_packaged_shen_registry,
    registry_from_data,
    registry_to_data,
)
from iching.core.bazi_rules.schema import TruthValue


ROOT = Path(__file__).resolve().parents[2]


def _chart(day: str, month: str) -> list[dict[str, Any]]:
    return [
        {"label": label, "stem": text[0], "branch": text[1], "text": text}
        for label, text in zip(
            ("年", "月", "日", "时"),
            ("甲子", month, day, "丙寅"),
        )
    ]


def _context(day: str, month: str):
    return build_rule_evaluation_context(build_bazi_fact_graph(_chart(day, month)))


def test_generalized_compiler_round_trips_the_packaged_shen_registry() -> None:
    regenerated = compile_research_registry(
        ROOT,
        bundle_id="zzq-shen-canonical-v1",
        authority_layer="shen_core",
    )
    packaged = load_packaged_shen_registry()

    assert registry_to_data(regenerated) == registry_to_data(packaged)
    assert registry_from_data(registry_to_data(regenerated)) == regenerated
    assert len(packaged.rules) == 46
    assert len(packaged.source_provenance) == 33
    assert packaged.authority_layer == "shen_core"


def test_all_eleven_source_backed_candidate_routes_are_complete() -> None:
    registry = load_packaged_shen_registry()
    effects_by_pattern: dict[str, set[str]] = {}
    for rule in registry.rules:
        if rule.stage == "candidate":
            effects_by_pattern.setdefault(rule.pattern_id, set()).add(rule.effect)

    assert effects_by_pattern == {
        pattern_id: {"candidate_confirm", "candidate_possible"}
        for pattern_id in (
            "direct_officer",
            "direct_resource",
            "direct_wealth",
            "eating_god",
            "hurting_officer",
            "indirect_resource",
            "indirect_wealth",
            "month_prosperity",
            "month_robbery",
            "seven_killings",
            "yang_blade",
        )
    }


@pytest.mark.parametrize(
    ("pattern_id", "day", "month"),
    (
        ("direct_officer", "甲子", "癸酉"),
        ("direct_resource", "甲子", "甲子"),
        ("direct_wealth", "甲子", "乙丑"),
        ("eating_god", "甲子", "己巳"),
        ("hurting_officer", "甲子", "庚午"),
        ("indirect_resource", "甲子", "乙亥"),
        ("indirect_wealth", "甲子", "戊辰"),
        ("month_prosperity", "甲子", "丙寅"),
        ("month_robbery", "乙丑", "丙寅"),
        ("seven_killings", "甲子", "壬申"),
        ("yang_blade", "甲子", "丁卯"),
    ),
)
def test_candidate_route_positive_wheel(
    pattern_id: str,
    day: str,
    month: str,
) -> None:
    result = evaluate_pattern_set(
        _context(day, month),
        load_packaged_shen_registry(),
    ).by_id(pattern_id)
    candidate_stage = next(item for item in result.stages if item.stage == "candidate")

    assert result.candidate is TruthValue.TRUE
    assert candidate_stage.details == {
        "routing_truth": "true",
        "routing_policy": "source_backed_candidate_rules",
    }
    assert {item.truth for item in candidate_stage.rules} == {TruthValue.TRUE}


@pytest.mark.parametrize(
    ("pattern_id", "day", "month"),
    (
        ("direct_officer", "甲子", "乙丑"),
        ("seven_killings", "甲子", "己巳"),
        ("direct_wealth", "甲子", "庚午"),
        ("indirect_wealth", "甲子", "丙寅"),
        ("eating_god", "甲子", "丙寅"),
        ("hurting_officer", "甲子", "辛未"),
        ("direct_resource", "甲子", "乙丑"),
        ("indirect_resource", "甲子", "壬申"),
    ),
)
def test_secondary_or_residual_month_qi_is_possible_but_not_confirmed(
    pattern_id: str,
    day: str,
    month: str,
) -> None:
    result = evaluate_pattern_set(
        _context(day, month),
        load_packaged_shen_registry(),
    ).by_id(pattern_id)
    candidate_stage = next(item for item in result.stages if item.stage == "candidate")
    truth_by_effect = {
        load_packaged_shen_registry().rules_by_id[item.rule_id].effect: item.truth
        for item in candidate_stage.rules
    }

    assert result.candidate is TruthValue.UNKNOWN
    assert truth_by_effect == {
        "candidate_confirm": TruthValue.FALSE,
        "candidate_possible": TruthValue.TRUE,
    }


def test_prosperity_robbery_and_yang_blade_use_disjoint_closed_tables() -> None:
    registry = load_packaged_shen_registry()
    days = (
        "甲子",
        "乙丑",
        "丙寅",
        "丁卯",
        "戊辰",
        "己巳",
        "庚午",
        "辛未",
        "壬申",
        "癸酉",
    )
    months = (
        "甲子",
        "乙丑",
        "丙寅",
        "丁卯",
        "戊辰",
        "己巳",
        "庚午",
        "辛未",
        "壬申",
        "癸酉",
        "甲戌",
        "乙亥",
    )
    expected = {
        "month_prosperity": {
            ("甲子", "丙寅"),
            ("乙丑", "丁卯"),
            ("丙寅", "己巳"),
            ("丁卯", "庚午"),
            ("戊辰", "己巳"),
            ("己巳", "庚午"),
            ("庚午", "壬申"),
            ("辛未", "癸酉"),
            ("壬申", "乙亥"),
            ("癸酉", "甲子"),
        },
        "month_robbery": {
            ("乙丑", "丙寅"),
            ("丁卯", "己巳"),
            ("己巳", "己巳"),
            ("辛未", "壬申"),
            ("癸酉", "乙亥"),
        },
        "yang_blade": {
            ("甲子", "丁卯"),
            ("丙寅", "庚午"),
            ("戊辰", "庚午"),
            ("庚午", "癸酉"),
            ("壬申", "甲子"),
        },
    }
    observed = {pattern_id: set() for pattern_id in expected}
    for day in days:
        for month in months:
            result = evaluate_pattern_set(_context(day, month), registry)
            for pattern_id in observed:
                if result.by_id(pattern_id).candidate is TruthValue.TRUE:
                    observed[pattern_id].add((day, month))

    assert observed == expected
    assert not (observed["month_prosperity"] & observed["month_robbery"])
    assert not (observed["month_prosperity"] & observed["yang_blade"])
    assert not (observed["month_robbery"] & observed["yang_blade"])


def test_every_lifecycle_reference_is_path_local_to_its_pattern() -> None:
    registry = load_packaged_shen_registry()
    paths = {
        (rule.pattern_id, rule.path_id)
        for rule in registry.rules
        if rule.stage == "formation"
    }
    by_id = registry.rules_by_id

    for rule in registry.rules:
        for path_id in (*rule.targets_path_ids, *rule.supersedes_path_ids):
            assert (rule.pattern_id, path_id) in paths
        if rule.stage != "formation" and rule.path_id is not None:
            assert (rule.pattern_id, rule.path_id) in paths
        for damage_id in rule.resolves_damage_ids:
            assert by_id[damage_id].pattern_id == rule.pattern_id
            assert by_id[damage_id].stage == "damage"
        for rescue_id in rule.invalidates_rescue_ids:
            assert by_id[rescue_id].pattern_id == rule.pattern_id
            assert by_id[rescue_id].stage == "rescue"


def test_task4_direct_officer_registry_is_only_extended_by_candidate_pair() -> None:
    registry = load_packaged_shen_registry()
    direct_officer_ids = {
        rule.id for rule in registry.rules if rule.pattern_id == "direct_officer"
    }
    assert direct_officer_ids == {
        "zzq.rule.direct-officer.candidate-confirm",
        "zzq.rule.direct-officer.candidate-possible",
        "zzq.rule.officer.form-wealth-support-001",
        "zzq.rule.officer.form-seal-support-001",
        "zzq.rule.officer.form-dual-support-001",
        "zzq.rule.officer.damage-mixed-killing-001",
        "zzq.rule.officer.damage-hurting-officer-001",
        "zzq.rule.officer.damage-wealth-breaks-seal-001",
        "zzq.rule.officer.rescue-hurting-seal-001",
        "zzq.rule.useful.rescue-officer-002",
        "zzq.rule.officer.form-single-support-001",
    }


def test_packaged_pattern_set_is_independent_of_registry_input_order() -> None:
    registry = load_packaged_shen_registry()
    reordered = RuleRegistry(
        bundle_id=registry.bundle_id,
        rules=tuple(reversed(registry.rules)),
        source_bundle_digest=registry.source_bundle_digest,
        exclusions=registry.exclusions,
        special_review_gate=registry.special_review_gate,
        source_provenance=registry.source_provenance,
        authority_layer=registry.authority_layer,
    )
    context = _context("甲子", "癸酉")

    assert reordered.bundle_digest == registry.bundle_digest
    assert (
        evaluate_pattern_set(context, reordered).as_dict()
        == evaluate_pattern_set(context, registry).as_dict()
    )


def test_legacy_candidate_fallback_keeps_the_task4_trace_label() -> None:
    registry = RuleRegistry(
        bundle_id="legacy-direct-officer-fixture",
        authority_layer="synthetic",
        rules=(
            RegistryRule(
                id="fixture.direct-officer.formation",
                stage="formation",
                pattern_id="direct_officer",
                predicate={
                    "op": "fact_equals",
                    "path": "completeness.chart_complete",
                    "value": True,
                },
                effect="formation",
                path_id="primary",
                authority_layer="synthetic",
                source_ids=("fixture.direct-officer.proposition",),
            ),
        ),
    )
    result = evaluate_pattern_lifecycle(
        _context("甲子", "癸酉"),
        registry,
    )
    candidate_stage = next(item for item in result.stages if item.stage == "candidate")

    assert result.candidate is TruthValue.TRUE
    assert candidate_stage.details["routing_policy"] == "month_command_qi_level"


def test_page_86_special_gate_is_a_typed_source_bound_set_policy() -> None:
    base = ROOT / "research/classics/ziping_zhenquan"
    propositions = [
        json.loads(line)
        for line in (base / "propositions/zzq.pattern.special-gate.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    candidates = [
        json.loads(line)
        for line in (base / "rules/zzq.pattern.special-gate.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]

    assert len(propositions) == len(candidates) == 4
    assert all(item["layer"] == "shen_core" for item in propositions)
    assert all(item["locator_ids"] == ["loc.gc.special.86"] for item in propositions)
    assert all(item["review_state"] == "scan_verified" for item in propositions)
    assert all(item["execution_ready"] is False for item in candidates)
    assert all(
        item["candidate_status"] == "source_verified_not_compiled"
        for item in candidates
    )
    registry = compile_research_registry(
        ROOT,
        bundle_id="zzq-shen-canonical-v1",
        authority_layer="shen_core",
    )
    policy = registry.special_review_gate
    assert policy is not None
    proposition_ids = {item["id"] for item in propositions}
    assert set(policy.source_ids) == proposition_ids

    provenance_by_id = {
        item.proposition_id: item for item in registry.source_provenance
    }
    for proposition_id in proposition_ids:
        provenance = provenance_by_id[proposition_id]
        assert provenance.layer == "shen_core"
        assert provenance.production_eligible is True
        assert provenance.review_state == "scan_verified"
        assert {locator.id for locator in provenance.support_locators} == {
            "loc.gc.special.86"
        }

    payload = registry_to_data(registry)
    assert payload["special_review_gate"] == policy.canonical_data()
    round_tripped = registry_from_data(payload)
    assert round_tripped == registry
    assert round_tripped.special_review_gate == policy

    compiled_sources = {
        source_id for rule in registry.rules for source_id in rule.source_ids
    }
    assert not (proposition_ids & compiled_sources)


def test_all_production_rules_receive_definitive_predicate_and_lifecycle_coverage() -> (
    None
):
    registry = load_packaged_shen_registry()
    charts: list[tuple[str, str, str, str]] = []
    example_root = ROOT / "research/classics/ziping_zhenquan/examples"
    for path in sorted(example_root.glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            record = json.loads(line)
            if "pillars" in record:
                charts.append(tuple(record["pillars"]))
    days = (
        "甲子",
        "乙丑",
        "丙寅",
        "丁卯",
        "戊辰",
        "己巳",
        "庚午",
        "辛未",
        "壬申",
        "癸酉",
    )
    months = (
        "甲子",
        "乙丑",
        "丙寅",
        "丁卯",
        "戊辰",
        "己巳",
        "庚午",
        "辛未",
        "壬申",
        "癸酉",
        "甲戌",
        "乙亥",
    )
    charts.extend(("甲子", month, day, "丙寅") for day in days for month in months)
    charts.append(("乙卯", "乙卯", "乙卯", "辛卯"))
    predicate_truths: dict[str, set[TruthValue]] = defaultdict(set)
    lifecycle_truths: dict[str, set[TruthValue]] = defaultdict(set)

    for pillars in charts:
        context = build_rule_evaluation_context(
            build_bazi_fact_graph(
                [
                    {
                        "label": label,
                        "stem": text[0],
                        "branch": text[1],
                        "text": text,
                    }
                    for label, text in zip(("年", "月", "日", "时"), pillars)
                ]
            )
        )
        for rule in registry.rules:
            predicate_truths[rule.id].add(
                evaluate_predicate(rule.predicate, context).truth
            )
        for pattern in evaluate_pattern_set(context, registry).patterns:
            for stage in pattern.stages:
                for trace in stage.rules:
                    lifecycle_truths[trace.rule_id].add(trace.truth)

    expected_truths = {TruthValue.TRUE, TruthValue.FALSE}
    assert set(predicate_truths) == set(registry.rules_by_id)
    assert set(lifecycle_truths) == set(registry.rules_by_id)
    assert all(expected_truths <= truths for truths in predicate_truths.values())
    assert all(expected_truths <= truths for truths in lifecycle_truths.values())
    for stage in ("candidate", "formation", "damage", "rescue", "resolution"):
        family_truths = set().union(
            *(
                lifecycle_truths[rule.id]
                for rule in registry.rules
                if rule.stage == stage
            )
        )
        assert expected_truths <= family_truths
