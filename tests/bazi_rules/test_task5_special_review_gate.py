from __future__ import annotations

import copy
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from iching.core.bazi_rules.engine import evaluate_pattern_set
from iching.core.bazi_rules.fact_graph import (
    build_bazi_fact_envelope,
    build_bazi_fact_graph,
    build_rule_evaluation_context,
)
from iching.core.bazi_rules.registry import (
    compile_research_registry,
    registry_from_data,
    registry_to_data,
)
from iching.core.bazi_rules.schema import TruthValue


ROOT = Path(__file__).resolve().parents[2]


def _chart(*pillars: str) -> list[dict[str, Any]]:
    return [
        {"label": label, "stem": text[0], "branch": text[1], "text": text}
        for label, text in zip(("年", "月", "日", "时"), pillars)
    ]


@pytest.fixture(scope="module")
def registry():
    return compile_research_registry(
        ROOT,
        bundle_id="zzq-shen-canonical-v1",
        authority_layer="shen_core",
    )


def _evaluate(registry, *pillars: str):
    context = build_rule_evaluation_context(build_bazi_fact_graph(_chart(*pillars)))
    return evaluate_pattern_set(context, registry)


def test_special_gate_provenance_is_fail_closed(registry) -> None:
    policy = registry.special_review_gate
    assert policy is not None
    missing = policy.ordinary_use_source_id

    with pytest.raises(ValueError, match="verified production provenance"):
        replace(
            registry,
            source_provenance=tuple(
                item
                for item in registry.source_provenance
                if item.proposition_id != missing
            ),
            source_provenance_digest="",
        )


def test_special_gate_packaged_schema_rejects_unknown_fields(registry) -> None:
    payload = copy.deepcopy(registry_to_data(registry))
    payload["special_review_gate"]["surprise"] = True

    with pytest.raises(ValueError, match="unknown fields"):
        registry_from_data(payload)


@pytest.mark.parametrize(
    ("officer_pillar", "ordinary_use"),
    (
        ("庚子", TruthValue.UNKNOWN),
        ("辛酉", TruthValue.TRUE),
    ),
)
def test_exposed_officer_or_killing_blocks_regardless_of_ordinary_lifecycle(
    registry,
    officer_pillar: str,
    ordinary_use: TruthValue,
) -> None:
    result = _evaluate(registry, officer_pillar, "甲子", "甲子", "丙子")
    gate = result.special_review_gate

    assert gate is not None
    assert gate.status == "blocked"
    assert gate.review_allowed is TruthValue.FALSE
    assert gate.checks["officer_killing_exposed"] is TruthValue.TRUE
    assert gate.checks["ordinary_use"] is ordinary_use
    assert "officer_killing_exposed" in gate.blocking_reasons


def test_two_exposed_wealth_positions_block_special_review(registry) -> None:
    result = _evaluate(registry, "戊子", "甲子", "甲子", "戊子")
    gate = result.special_review_gate

    assert gate is not None
    assert gate.status == "blocked"
    assert gate.checks["double_wealth_exposed"] is TruthValue.TRUE
    assert gate.checks["rooted_wealth"] is TruthValue.FALSE
    assert gate.blocking_reasons == ("double_wealth_exposed",)


def test_one_exposed_wealth_does_not_block_but_open_world_use_is_unknown(
    registry,
) -> None:
    result = _evaluate(registry, "戊子", "甲子", "甲子", "丙子")
    gate = result.special_review_gate

    assert gate is not None
    assert gate.status == "undetermined"
    assert gate.review_allowed is TruthValue.UNKNOWN
    assert gate.checks == {
        "ordinary_use": TruthValue.UNKNOWN,
        "officer_killing_exposed": TruthValue.FALSE,
        "rooted_wealth": TruthValue.FALSE,
        "double_wealth_exposed": TruthValue.FALSE,
    }
    assert gate.uncertain_reasons == ("ordinary_use",)


def test_hidden_wealth_without_exposed_wealth_is_not_a_rooted_wealth_blocker(
    registry,
) -> None:
    result = _evaluate(registry, "甲子", "甲子", "甲子", "丙辰")
    gate = result.special_review_gate

    assert gate is not None
    assert gate.checks["rooted_wealth"] is TruthValue.FALSE
    assert gate.check_details["rooted_wealth"]["hidden_wealth"]["truth"] == "true"
    assert "rooted_wealth" not in gate.blocking_reasons
    assert "rooted_wealth" not in gate.uncertain_reasons


def test_exposed_and_hidden_wealth_keeps_root_depth_unresolved(registry) -> None:
    result = _evaluate(registry, "戊子", "甲子", "甲子", "丙辰")
    gate = result.special_review_gate

    assert gate is not None
    assert gate.checks["rooted_wealth"] is TruthValue.UNKNOWN
    assert gate.status == "undetermined"
    assert "rooted_wealth" in gate.uncertain_reasons
    assert (
        gate.check_details["rooted_wealth"]["binding_status"]
        == "root_depth_predicate_unresolved"
    )


def test_formed_ordinary_path_blocks_even_when_later_broken(registry) -> None:
    result = _evaluate(registry, "戊辰", "丁酉", "甲子", "庚辰")
    direct_officer = result.by_id("direct_officer")
    wealth_path = next(
        path for path in direct_officer.paths if path.path_id == "wealth_support"
    )
    gate = result.special_review_gate

    assert direct_officer.candidate is TruthValue.TRUE
    assert direct_officer.status == "broken"
    assert wealth_path.formation_truth is TruthValue.TRUE
    assert wealth_path.status == "broken"
    assert gate is not None
    assert gate.checks["ordinary_use"] is TruthValue.TRUE
    assert gate.status == "blocked"
    assert "ordinary_use" in gate.blocking_reasons


def test_uncertain_hour_gate_is_reduced_per_world_without_losing_correlation(
    registry,
) -> None:
    envelope = build_bazi_fact_envelope(
        (
            _chart("甲子", "甲子", "甲子", "庚子"),
            _chart("甲子", "甲子", "甲子", "丙子"),
        )
    )
    result = evaluate_pattern_set(
        build_rule_evaluation_context(envelope),
        registry,
    )
    gate = result.special_review_gate

    assert gate is not None
    assert gate.status == "undetermined"
    assert gate.review_allowed is TruthValue.UNKNOWN
    assert len(gate.world_results) == len(envelope.worlds) == 2
    gate_by_digest = {item.world_digest: item for item in gate.world_results}
    for world in envelope.worlds:
        world_gate = gate_by_digest[world.digest]
        if world.pillar("hour").stem == "庚":
            assert world_gate.status == "blocked"
            assert world_gate.checks["officer_killing_exposed"] is TruthValue.TRUE
        else:
            assert world.pillar("hour").stem == "丙"
            assert world_gate.status == "undetermined"
            assert world_gate.checks["officer_killing_exposed"] is TruthValue.FALSE
    assert "candidate_world_gate_disagreement" in gate.uncertain_reasons


def test_every_candidate_world_blocked_remains_blocked_when_reasons_differ(
    registry,
) -> None:
    envelope = build_bazi_fact_envelope(
        (
            _chart("戊子", "甲子", "甲子", "庚子"),
            _chart("戊子", "甲子", "甲子", "戊子"),
        )
    )
    result = evaluate_pattern_set(
        build_rule_evaluation_context(envelope),
        registry,
    )
    gate = result.special_review_gate

    assert gate is not None
    assert gate.status == "blocked"
    assert gate.review_allowed is TruthValue.FALSE
    assert {item.blocking_reasons for item in gate.world_results} == {
        ("officer_killing_exposed",),
        ("double_wealth_exposed",),
    }
    assert gate.checks["officer_killing_exposed"] is TruthValue.UNKNOWN
    assert gate.checks["double_wealth_exposed"] is TruthValue.UNKNOWN
    assert gate.blocking_reasons == (
        "double_wealth_exposed",
        "officer_killing_exposed",
    )


@pytest.mark.parametrize(
    "pillars",
    (
        ("庚子", "甲子", "甲子", "丙子"),
        ("戊子", "甲子", "甲子", "戊子"),
        ("戊辰", "丁酉", "甲子", "庚辰"),
    ),
)
def test_special_gate_never_claims_that_a_special_pattern_formed(
    registry,
    pillars: tuple[str, str, str, str],
) -> None:
    result = _evaluate(registry, *pillars)

    assert result.special_review_gate is not None
    assert result.special_review_gate.status in {
        "blocked",
        "eligible",
        "undetermined",
    }
    assert all("special" not in pattern.pattern_id for pattern in result.patterns)
    assert all("special" not in pattern_id for pattern_id in result.active_pattern_ids)
