from __future__ import annotations

from dataclasses import replace
from typing import Any

import pytest

from iching.core.bazi_rules.engine import evaluate_pattern_set
from iching.core.bazi_rules.fact_graph import (
    build_bazi_fact_graph,
    build_rule_evaluation_context,
)
from iching.core.bazi_rules.adapter import build_source_backed_shadow
from iching.core.bazi_rules.registry import (
    RegistryExclusion,
    RegistryRule,
    RuleRegistry,
    load_packaged_registry,
    load_packaged_shen_registry,
    registry_from_data,
    registry_to_data,
)
from iching.core.bazi_rules.predicates import predicate_to_canonical_data


TRUE = {
    "op": "fact_equals",
    "path": "completeness.chart_complete",
    "value": True,
}
FALSE = {
    "op": "fact_equals",
    "path": "completeness.chart_complete",
    "value": False,
}


def _chart(*texts: str) -> list[dict[str, Any]]:
    return [
        {"label": label, "stem": text[0], "branch": text[1], "text": text}
        for label, text in zip(("年", "月", "日", "时"), texts)
    ]


def _candidate(
    pattern_id: str,
    effect: str,
    predicate: dict[str, Any],
) -> RegistryRule:
    return RegistryRule(
        id=f"fixture.{pattern_id}.{effect}",
        stage="candidate",
        pattern_id=pattern_id,
        predicate=predicate,
        effect=effect,
        authority_layer="synthetic",
        source_ids=(f"prop.{pattern_id}.{effect}",),
    )


def _formation(pattern_id: str) -> RegistryRule:
    return RegistryRule(
        id=f"fixture.{pattern_id}.formation",
        stage="formation",
        pattern_id=pattern_id,
        predicate=TRUE,
        effect="formation",
        path_id="primary",
        authority_layer="synthetic",
        source_ids=(f"prop.{pattern_id}.formation",),
    )


def _registry(*rules: RegistryRule) -> RuleRegistry:
    return RuleRegistry("fixture-task5", tuple(rules), authority_layer="synthetic")


def _context():
    graph = build_bazi_fact_graph(_chart("甲子", "乙酉", "甲午", "戊辰"))
    return build_rule_evaluation_context(graph)


def _xu_overlay(kind: str):
    from iching.core.bazi_rules.authority import OverlayDescriptor, OverlayRelation

    canonical = load_packaged_registry()
    canonical_rule = next(
        rule
        for rule in canonical.rules
        if rule.pattern_id == "direct_officer" and rule.stage == "formation"
    )
    predicate = predicate_to_canonical_data(canonical_rule.predicate)
    if kind == "adds_condition":
        predicate = {"op": "all", "children": [predicate, TRUE]}
    elif kind == "disagrees":
        predicate = {"op": "not", "child": predicate}
    overlay_rule = replace(
        canonical_rule,
        id=f"xu.fixture.{kind}",
        predicate=predicate,
        authority_layer="xu_commentary",
    )
    canonical_provenance = next(
        item
        for item in canonical.source_provenance
        if item.proposition_id in canonical_rule.source_ids
    )
    overlay_provenance = replace(
        canonical_provenance,
        layer="xu_commentary",
        segments=tuple(
            replace(segment, layer="xu_commentary")
            for segment in canonical_provenance.segments
        ),
    )
    registry = RuleRegistry(
        f"xu-fixture-{kind}",
        (overlay_rule,),
        source_bundle_digest=canonical.source_bundle_digest,
        source_provenance=(overlay_provenance,),
        authority_layer="xu_commentary",
    )
    relation = OverlayRelation(
        id=f"fixture.{kind}",
        kind=kind,
        pattern_id=canonical_rule.pattern_id,
        overlay_rule_ids=(overlay_rule.id,),
        canonical_rule_ids=(canonical_rule.id,),
        canonical_term="正官" if kind == "different_terminology" else None,
        overlay_term="官格" if kind == "different_terminology" else None,
        semantic_delta=(
            "Xu witness rejects this canonical condition in the fixture."
            if kind == "disagrees"
            else None
        ),
    )
    return canonical, OverlayDescriptor(
        authority_layer="xu_commentary",
        availability="partial",
        base_bundle_id=canonical.bundle_id,
        base_bundle_digest=canonical.bundle_digest,
        registry=registry,
        relations=(relation,),
    )


def test_candidate_confirm_and_possible_drive_two_pattern_results() -> None:
    registry = _registry(
        _candidate("direct_officer", "candidate_confirm", TRUE),
        _candidate("direct_officer", "candidate_possible", TRUE),
        _formation("direct_officer"),
        _candidate("seven_killings", "candidate_confirm", FALSE),
        _candidate("seven_killings", "candidate_possible", TRUE),
        _formation("seven_killings"),
    )

    result = evaluate_pattern_set(_context(), registry)

    assert [item.pattern_id for item in result.patterns] == [
        "direct_officer",
        "seven_killings",
    ]
    assert result.by_id("direct_officer").status == "formed"
    assert result.by_id("seven_killings").status == "undetermined"
    assert result.active_pattern_ids == ("direct_officer",)
    assert result.ambiguous_pattern_ids == ("seven_killings",)
    assert result.authority_layer == "synthetic"


def test_pattern_set_is_independent_of_registry_input_order() -> None:
    rules = (
        _candidate("direct_officer", "candidate_confirm", TRUE),
        _candidate("direct_officer", "candidate_possible", TRUE),
        _formation("direct_officer"),
        _candidate("seven_killings", "candidate_confirm", FALSE),
        _candidate("seven_killings", "candidate_possible", FALSE),
        _formation("seven_killings"),
    )

    first = evaluate_pattern_set(_context(), _registry(*rules)).as_dict()
    second = evaluate_pattern_set(_context(), _registry(*reversed(rules))).as_dict()

    assert first == second


def _two_active_pattern_set():
    registry = _registry(
        _candidate("direct_officer", "candidate_confirm", TRUE),
        _candidate("direct_officer", "candidate_possible", TRUE),
        _formation("direct_officer"),
        _candidate("seven_killings", "candidate_confirm", TRUE),
        _candidate("seven_killings", "candidate_possible", TRUE),
        _formation("seven_killings"),
    )
    return evaluate_pattern_set(_context(), registry)


@pytest.mark.parametrize(
    "active_pattern_ids",
    [
        ("seven_killings", "direct_officer"),
        ("direct_officer", "direct_officer"),
        ("not_declared",),
    ],
)
def test_pattern_set_rejects_unsorted_duplicate_or_unknown_result_ids(
    active_pattern_ids: tuple[str, ...],
) -> None:
    with pytest.raises(ValueError, match="pattern"):
        replace(_two_active_pattern_set(), active_pattern_ids=active_pattern_ids)


def test_pattern_set_result_id_groups_must_be_disjoint() -> None:
    result = _two_active_pattern_set()

    with pytest.raises(ValueError, match="disjoint"):
        replace(
            result,
            ambiguous_pattern_ids=("direct_officer",),
        )


def test_pattern_set_and_member_bundle_identity_must_match() -> None:
    result = _two_active_pattern_set()
    mismatched = replace(result.patterns[0], bundle_digest="0" * 64)

    with pytest.raises(ValueError, match="bundle identity"):
        replace(result, patterns=(mismatched, *result.patterns[1:]))


def test_pattern_set_exclusions_are_reported_only_on_their_bound_pattern() -> None:
    rules = (
        _candidate("direct_officer", "candidate_confirm", TRUE),
        _candidate("direct_officer", "candidate_possible", TRUE),
        _formation("direct_officer"),
        _candidate("seven_killings", "candidate_confirm", TRUE),
        _candidate("seven_killings", "candidate_possible", TRUE),
        _formation("seven_killings"),
    )
    registry = RuleRegistry(
        "pattern-exclusion-fixture",
        rules,
        authority_layer="synthetic",
        exclusions=(
            RegistryExclusion(
                "candidate.excluded",
                "fixture exclusion",
                ("prop.excluded",),
                pattern_id="direct_officer",
            ),
        ),
    )
    result = evaluate_pattern_set(_context(), registry)
    direct_resolution = next(
        stage
        for stage in result.by_id("direct_officer").stages
        if stage.stage == "resolution"
    )
    killing_resolution = next(
        stage
        for stage in result.by_id("seven_killings").stages
        if stage.stage == "resolution"
    )

    assert len(direct_resolution.details["excluded_candidates"]) == 1
    assert killing_resolution.details["excluded_candidates"] == []


def test_registry_rejects_exclusion_bound_to_an_undeclared_pattern() -> None:
    with pytest.raises(ValueError, match="undeclared pattern"):
        RuleRegistry(
            "bad-pattern-exclusion",
            (_formation("direct_officer"),),
            authority_layer="synthetic",
            exclusions=(
                RegistryExclusion(
                    "candidate.excluded",
                    "fixture exclusion",
                    ("prop.excluded",),
                    pattern_id="seven_killings",
                ),
            ),
        )


def test_registry_rejects_bundle_and_rule_authority_layer_mixing() -> None:
    with pytest.raises(ValueError, match="authority layer"):
        RuleRegistry(
            "mixed",
            (_candidate("direct_officer", "candidate_confirm", TRUE),),
            authority_layer="shen_core",
        )


def test_registry_digest_binds_the_authority_layer_even_when_empty() -> None:
    source_digest = "a" * 64
    yuanhai = RuleRegistry(
        "empty-overlay",
        (),
        source_bundle_digest=source_digest,
        authority_layer="yuanhai",
    )
    xu = RuleRegistry(
        "empty-overlay",
        (),
        source_bundle_digest=source_digest,
        authority_layer="xu_commentary",
    )

    assert yuanhai.bundle_digest != xu.bundle_digest
    payload = registry_to_data(yuanhai)
    payload["authority_layer"] = "xu_commentary"
    with pytest.raises(ValueError, match="bundle_digest"):
        registry_from_data(payload)


def test_registry_rejects_half_declared_candidate_route() -> None:
    with pytest.raises(ValueError, match="candidate_confirm and candidate_possible"):
        _registry(
            _candidate("direct_officer", "candidate_confirm", TRUE),
            _formation("direct_officer"),
        )


def test_registry_keeps_primary_and_supporting_runtime_provenance_separate() -> None:
    canonical = load_packaged_shen_registry()
    primary = next(rule for rule in canonical.rules if rule.stage == "formation")
    primary_provenance = next(
        item
        for item in canonical.source_provenance
        if item.proposition_id == primary.source_ids[0]
    )
    supporting_provenance = next(
        item
        for item in canonical.source_provenance
        if item.proposition_id != primary.source_ids[0]
    )
    cited = replace(
        primary,
        supporting_source_ids=(supporting_provenance.proposition_id,),
    )

    with pytest.raises(ValueError, match="verified production provenance"):
        RuleRegistry(
            "supporting-missing",
            (cited,),
            source_bundle_digest=canonical.source_bundle_digest,
            source_provenance=(primary_provenance,),
            authority_layer="shen_core",
        )
    registry = RuleRegistry(
        "supporting-complete",
        (cited,),
        source_bundle_digest=canonical.source_bundle_digest,
        source_provenance=(primary_provenance, supporting_provenance),
        authority_layer="shen_core",
    )

    assert registry.rules[0].source_ids == primary.source_ids
    assert registry.rules[0].supporting_source_ids == (
        supporting_provenance.proposition_id,
    )
    assert registry_from_data(registry_to_data(registry)) == registry


@pytest.mark.parametrize(
    "kind",
    ["agrees", "adds_condition", "disagrees", "different_terminology"],
)
def test_overlay_relation_kind_is_closed(kind: str) -> None:
    from iching.core.bazi_rules.authority import OverlayRelation

    relation = OverlayRelation(
        id=f"fixture.{kind}",
        kind=kind,
        pattern_id="direct_officer",
        overlay_rule_ids=("overlay.rule",),
        canonical_rule_ids=("canonical.rule",),
        canonical_term="正官" if kind == "different_terminology" else None,
        overlay_term="官格" if kind == "different_terminology" else None,
        semantic_delta="fixture disagreement" if kind == "disagrees" else None,
    )

    assert relation.kind == kind


@pytest.mark.parametrize(
    "kind",
    ["agrees", "adds_condition", "disagrees", "different_terminology"],
)
def test_overlay_relation_contracts_validate_without_mutating_canonical(
    kind: str,
) -> None:
    canonical, overlay = _xu_overlay(kind)
    before = canonical.bundle_digest

    overlay.validate_against(canonical)

    assert canonical.bundle_digest == before


def test_available_overlay_requires_every_rule_to_be_related_once() -> None:
    canonical, overlay = _xu_overlay("agrees")
    unreferenced = replace(overlay, relations=())
    duplicated = replace(
        overlay,
        relations=(
            overlay.relations[0],
            replace(overlay.relations[0], id="fixture.agrees.duplicate"),
        ),
    )

    with pytest.raises(ValueError, match="every executable overlay rule"):
        unreferenced.validate_against(canonical)
    with pytest.raises(ValueError, match="exactly once"):
        duplicated.validate_against(canonical)


def test_adds_condition_rejects_an_identical_predicate() -> None:
    canonical, agrees = _xu_overlay("agrees")
    relation = replace(agrees.relations[0], kind="adds_condition")
    invalid = replace(agrees, relations=(relation,))

    with pytest.raises(ValueError, match="explicit condition"):
        invalid.validate_against(canonical)


def test_disagrees_rejects_an_identical_rule_even_with_a_labelled_delta() -> None:
    canonical, agrees = _xu_overlay("agrees")
    relation = replace(
        agrees.relations[0],
        kind="disagrees",
        semantic_delta="claimed but not present",
    )
    invalid = replace(agrees, relations=(relation,))

    with pytest.raises(ValueError, match="real semantic delta"):
        invalid.validate_against(canonical)


def test_overlay_descriptor_fails_closed_on_base_digest_mismatch() -> None:
    from iching.core.bazi_rules.authority import OverlayDescriptor

    canonical = load_packaged_registry()
    descriptor = OverlayDescriptor(
        authority_layer="xu_commentary",
        availability="unavailable",
        base_bundle_id=canonical.bundle_id,
        base_bundle_digest="0" * 64,
        registry=None,
        relations=(),
        unavailable_reason="fixture",
    )

    with pytest.raises(ValueError, match="base bundle digest"):
        descriptor.validate_against(canonical)


def test_public_packaged_overlay_loader_validates_its_canonical_pin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import iching.core.bazi_rules.authority as authority_module

    valid = authority_module.load_packaged_overlay("xu_commentary")
    invalid = replace(valid, base_bundle_digest="0" * 64)
    authority_module.load_packaged_overlay.cache_clear()
    monkeypatch.setattr(
        authority_module,
        "overlay_descriptor_from_data",
        lambda _payload: invalid,
    )

    with pytest.raises(ValueError, match="base bundle digest"):
        authority_module.load_packaged_overlay("xu_commentary")
    authority_module.load_packaged_overlay.cache_clear()


def test_packaged_xu_is_honestly_unavailable_and_shen_alias_is_stable() -> None:
    from iching.core.bazi_rules.authority import (
        load_packaged_classical_authorities,
        load_packaged_overlay,
    )

    canonical = load_packaged_shen_registry()
    authorities = load_packaged_classical_authorities()
    xu = load_packaged_overlay("xu_commentary")
    yuanhai = load_packaged_overlay("yuanhai")

    assert load_packaged_registry() is canonical
    assert authorities.canonical is canonical
    assert authorities.overlays == (xu, yuanhai)
    assert xu.availability == "unavailable"
    assert xu.registry is None
    assert xu.relations == ()
    assert xu.unavailable_reason
    assert yuanhai.availability == "partial"
    assert yuanhai.registry is not None
    assert yuanhai.registry.authority_layer == "yuanhai"
    assert yuanhai.registry.rules == ()
    assert yuanhai.relations == ()


def test_unknown_overlay_layer_is_rejected_without_fallback() -> None:
    from iching.core.bazi_rules.authority import load_packaged_overlay

    with pytest.raises(ValueError, match="unsupported overlay layer"):
        load_packaged_overlay("not-a-layer")


def test_shadow_keeps_frozen_task4_generic_and_adds_canonical_pattern_set() -> None:
    pillars = _chart("甲子", "乙酉", "甲午", "戊辰")
    graph = build_bazi_fact_graph(pillars)

    shadow = build_source_backed_shadow(pillars, {"ordinary": []}, graph)

    canonical_officer = next(
        item
        for item in shadow["pattern_set"]["patterns"]
        if item["pattern_id"] == "direct_officer"
    )
    assert shadow["generic_result"] != canonical_officer
    assert shadow["generic_result"]["bundle_digest"] == shadow["bundle_digest"]
    assert canonical_officer["bundle_digest"] == shadow["pattern_set"]["bundle_digest"]
    assert shadow["overlay_results"] == []
    assert {"generic_result", "example_attestations", "legacy_status", "diff"} <= set(
        shadow
    )


def test_package_exports_task5_runtime_contracts() -> None:
    from iching.core import bazi_rules

    assert bazi_rules.evaluate_pattern_set is evaluate_pattern_set
    assert bazi_rules.load_packaged_shen_registry is load_packaged_shen_registry
    assert bazi_rules.OverlayDescriptor.__name__ == "OverlayDescriptor"
