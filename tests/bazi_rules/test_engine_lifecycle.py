from __future__ import annotations

from dataclasses import replace
from typing import Any

import pytest

from iching.core.bazi_rules.engine import evaluate_pattern_lifecycle
from iching.core.bazi_rules.fact_graph import (
    build_bazi_fact_envelope,
    build_bazi_fact_graph,
    build_rule_evaluation_context,
)
from iching.core.bazi_rules.registry import (
    LIFECYCLE_STAGES,
    RegistryExclusion,
    RegistryRule,
    RuleRegistry,
    load_packaged_registry,
    registry_from_records,
)


def _chart(*texts: str) -> list[dict[str, Any]]:
    return [
        {"label": label, "stem": text[0], "branch": text[1], "text": text}
        for label, text in zip(("年", "月", "日", "时"), texts)
    ]


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
UNKNOWN = {
    "op": "fact_equals",
    "path": "pillars.hour.stem",
    "value": "戊",
}
STABLE_TRUE = {
    "op": "fact_equals",
    "path": "day_master.stem",
    "value": "甲",
}


def _rule(
    rule_id: str,
    stage: str,
    *,
    predicate: dict[str, Any] | None = None,
    effect: str | None = None,
    path_id: str | None = None,
    targets: tuple[str, ...] = (),
    resolves: tuple[str, ...] = (),
    invalidates: tuple[str, ...] = (),
    supersedes: tuple[str, ...] = (),
    precedence: int = 10,
) -> RegistryRule:
    return RegistryRule(
        id=rule_id,
        stage=stage,
        pattern_id="direct_officer",
        predicate=predicate or TRUE,
        effect=effect or stage,
        path_id=path_id,
        targets_path_ids=targets,
        resolves_damage_ids=resolves,
        invalidates_rescue_ids=invalidates,
        supersedes_path_ids=supersedes,
        authority_layer="synthetic",
        source_ids=(f"prop.{rule_id}",),
        precedence=precedence,
    )


def _registry(*rules: RegistryRule) -> RuleRegistry:
    return RuleRegistry("fixture-direct-officer", tuple(rules))


def _context(*texts: str):
    return build_rule_evaluation_context(build_bazi_fact_graph(_chart(*texts)))


def _unknown_hour_context(*texts: str):
    return build_rule_evaluation_context(
        build_bazi_fact_graph(_chart(*texts), hour_uncertain=True)
    )


DIRECT_OFFICER = ("甲子", "乙酉", "甲午", "戊辰")
NOT_DIRECT_OFFICER = ("甲子", "丙寅", "甲午", "戊辰")


def test_lifecycle_emits_all_fixed_stages_and_basic_candidate_terminals() -> None:
    formed_registry = _registry(
        _rule("form", "formation", path_id="wealth"),
    )

    formed = evaluate_pattern_lifecycle(_context(*DIRECT_OFFICER), formed_registry)
    candidate = evaluate_pattern_lifecycle(
        _context(*DIRECT_OFFICER),
        _registry(_rule("form", "formation", predicate=FALSE, path_id="wealth")),
    )
    rejected = evaluate_pattern_lifecycle(
        _context(*NOT_DIRECT_OFFICER), formed_registry
    )

    assert formed.status == "formed"
    assert candidate.status == "candidate"
    assert rejected.status == "rejected"
    assert tuple(stage.stage for stage in formed.stages) == LIFECYCLE_STAGES
    assert len(formed.as_dict()["stages"]) == 8


def test_damage_rescue_is_path_local_and_rescue_requires_actual_damage() -> None:
    formation = _rule("form.wealth", "formation", path_id="wealth")
    damage = _rule(
        "damage.output",
        "damage",
        targets=("wealth",),
    )
    rescue = _rule(
        "rescue.seal",
        "rescue",
        targets=("wealth",),
        resolves=("damage.output",),
    )

    broken = evaluate_pattern_lifecycle(
        _context(*DIRECT_OFFICER), _registry(formation, damage)
    )
    rescued = evaluate_pattern_lifecycle(
        _context(*DIRECT_OFFICER), _registry(formation, damage, rescue)
    )
    rescue_without_damage = evaluate_pattern_lifecycle(
        _context(*DIRECT_OFFICER),
        _registry(formation, replace(damage, predicate=FALSE), rescue),
    )

    assert broken.status == "broken"
    assert rescued.status == "rescued"
    assert rescued.paths[0].resolved_damage_ids == ("damage.output",)
    assert rescue_without_damage.status == "formed"
    assert rescue_without_damage.paths[0].resolved_damage_ids == ()


def test_rescue_invalidation_rule_is_not_itself_counted_as_damage() -> None:
    formation = _rule("form.wealth", "formation", path_id="wealth")
    damage = _rule("damage.output", "damage", targets=("wealth",))
    rescue = _rule(
        "rescue.seal",
        "rescue",
        targets=("wealth",),
        resolves=("damage.output",),
    )
    invalidator = _rule(
        "damage.breaks-seal",
        "damage",
        effect="rescue_invalidation",
        targets=("wealth",),
        invalidates=("rescue.seal",),
    )

    result = evaluate_pattern_lifecycle(
        _context(*DIRECT_OFFICER),
        _registry(formation, damage, rescue, invalidator),
    )

    assert result.status == "broken"
    assert result.paths[0].actual_damage_ids == ("damage.output",)
    assert result.paths[0].invalidated_rescue_ids == ("rescue.seal",)


def test_only_unresolved_officer_killing_mixture_returns_mixed() -> None:
    result = evaluate_pattern_lifecycle(
        _context(*DIRECT_OFFICER),
        _registry(
            _rule("form", "formation", path_id="wealth"),
            _rule(
                "damage.mixed",
                "damage",
                effect="officer_killing_mixture",
                targets=("wealth",),
            ),
        ),
    )

    assert result.status == "mixed"


def test_relevant_unknowns_poison_but_inactive_damage_rescue_unknowns_do_not() -> None:
    xuan = _context("己卯", "辛未", "壬寅", "辛亥")
    pending_output = {
        "op": "activation_exists",
        "gods": ["伤官"],
        "families": ["output"],
        "positions": [],
        "origins": [],
        "scope": "generic",
    }
    formation = _rule("form", "formation", path_id="seal")
    unknown_damage = _rule(
        "damage.output",
        "damage",
        predicate=pending_output,
        targets=("seal",),
    )
    inactive_damage = replace(unknown_damage, id="damage.inactive", predicate=FALSE)
    irrelevant_unknown_rescue = _rule(
        "rescue.inactive",
        "rescue",
        predicate=pending_output,
        targets=("seal",),
        resolves=("damage.inactive",),
    )

    relevant = evaluate_pattern_lifecycle(xuan, _registry(formation, unknown_damage))
    irrelevant = evaluate_pattern_lifecycle(
        xuan, _registry(formation, inactive_damage, irrelevant_unknown_rescue)
    )

    assert relevant.status == "undetermined"
    assert irrelevant.status == "formed"


def test_known_path_conflict_is_not_a_list_order_fallback() -> None:
    wealth = _rule("form.wealth", "formation", path_id="wealth")
    seal = _rule("form.seal", "formation", path_id="seal")
    seal_damage = _rule("damage.seal", "damage", targets=("seal",))

    ambiguous = evaluate_pattern_lifecycle(
        _context(*DIRECT_OFFICER), _registry(wealth, seal, seal_damage)
    )

    assert ambiguous.status == "ambiguous"


@pytest.mark.parametrize(
    ("predicate", "hour_uncertain", "expected", "expected_reasons"),
    [
        (TRUE, False, "transformed", ("source_backed_transformation",)),
        (FALSE, False, "formed", ()),
        (
            UNKNOWN,
            True,
            "undetermined",
            ("relevant_unknown_rescue_transformation_or_gate",),
        ),
    ],
)
def test_transformation_terminal_truth_semantics(
    predicate: dict[str, Any],
    hour_uncertain: bool,
    expected: str,
    expected_reasons: tuple[str, ...],
) -> None:
    context = (
        _unknown_hour_context(*DIRECT_OFFICER)
        if hour_uncertain
        else _context(*DIRECT_OFFICER)
    )
    registry = _registry(
        _rule(
            "form.wealth",
            "formation",
            predicate=STABLE_TRUE,
            path_id="wealth",
        ),
        _rule(
            "transform.wealth",
            "transformation",
            predicate=predicate,
            effect="transformation",
            targets=("wealth",),
        ),
    )

    result = evaluate_pattern_lifecycle(context, registry)

    assert result.status == expected
    assert result.paths[0].status == expected
    assert result.paths[0].reasons == expected_reasons


@pytest.mark.parametrize(
    ("effect", "predicate", "hour_uncertain", "expected", "expected_reasons"),
    [
        ("require", FALSE, False, "broken", ("special_gate_failed",)),
        ("require", TRUE, False, "formed", ()),
        (
            "require",
            UNKNOWN,
            True,
            "undetermined",
            ("relevant_unknown_rescue_transformation_or_gate",),
        ),
        ("reject", TRUE, False, "broken", ("special_gate_failed",)),
        ("reject", FALSE, False, "formed", ()),
        (
            "reject",
            UNKNOWN,
            True,
            "undetermined",
            ("relevant_unknown_rescue_transformation_or_gate",),
        ),
    ],
)
def test_special_gate_terminal_truth_semantics(
    effect: str,
    predicate: dict[str, Any],
    hour_uncertain: bool,
    expected: str,
    expected_reasons: tuple[str, ...],
) -> None:
    context = (
        _unknown_hour_context(*DIRECT_OFFICER)
        if hour_uncertain
        else _context(*DIRECT_OFFICER)
    )
    registry = _registry(
        _rule(
            "form.wealth",
            "formation",
            predicate=STABLE_TRUE,
            path_id="wealth",
        ),
        _rule(
            f"gate.{effect}.wealth",
            "special_gate",
            predicate=predicate,
            effect=effect,
            targets=("wealth",),
        ),
    )

    result = evaluate_pattern_lifecycle(context, registry)

    assert result.status == expected
    assert result.paths[0].status == expected
    assert result.paths[0].reasons == expected_reasons


def test_source_supersession_resolves_dual_and_single_support_without_rule_order() -> (
    None
):
    wealth = _rule("form.wealth", "formation", path_id="wealth")
    seal = _rule("form.seal", "formation", path_id="seal")
    dual = _rule(
        "form.dual",
        "formation",
        path_id="dual",
        supersedes=("wealth", "seal"),
    )
    first = _registry(wealth, seal, dual)
    second = _registry(*reversed(first.rules))

    one = evaluate_pattern_lifecycle(_context(*DIRECT_OFFICER), first)
    two = evaluate_pattern_lifecycle(_context(*DIRECT_OFFICER), second)

    assert one.status == two.status == "formed"
    assert [item.path_id for item in one.paths if not item.superseded_by_rule_ids] == [
        "dual"
    ]
    assert first.bundle_digest == second.bundle_digest
    assert one.as_dict() == two.as_dict()


def test_registry_rejects_self_and_mutual_path_supersession_cycles() -> None:
    wealth = _rule("form.wealth", "formation", path_id="wealth")
    seal = _rule("form.seal", "formation", path_id="seal")
    self_cycle = replace(wealth, supersedes_path_ids=("wealth",))
    wealth_over_seal = _rule(
        "resolution.wealth",
        "resolution",
        effect="source_precedence",
        path_id="wealth",
        supersedes=("seal",),
    )
    seal_over_wealth = _rule(
        "resolution.seal",
        "resolution",
        effect="source_precedence",
        path_id="seal",
        supersedes=("wealth",),
    )

    with pytest.raises(ValueError, match="path supersession cycle"):
        _registry(self_cycle)
    with pytest.raises(ValueError, match="path supersession cycle"):
        _registry(wealth, seal, wealth_over_seal, seal_over_wealth)


@pytest.mark.parametrize(
    ("stage", "predicate"),
    [
        ("candidate", TRUE),
        ("candidate", FALSE),
        ("purity", FALSE),
    ],
)
def test_registry_rejects_executable_stages_without_reduction_semantics(
    stage: str,
    predicate: dict[str, Any],
) -> None:
    with pytest.raises(ValueError, match="unsupported executable stage"):
        _registry(_rule(f"unsupported.{stage}", stage, predicate=predicate))


@pytest.mark.parametrize(
    ("stage", "effect"),
    [
        ("formation", "rescue"),
        ("damage", "formation"),
        ("rescue", "damage"),
        ("transformation", "transform"),
        ("transformation", "gate"),
        ("special_gate", "gate"),
        ("special_gate", "special_gate"),
        ("special_gate", "transform"),
        ("special_gate", "no_op"),
        ("resolution", "resolution"),
        ("resolution", "transform"),
    ],
)
def test_registry_rule_rejects_unsupported_stage_effect_pairs(
    stage: str,
    effect: str,
) -> None:
    with pytest.raises(ValueError, match="unsupported"):
        _rule(
            f"bad.{stage}.{effect}",
            stage,
            effect=effect,
            path_id="wealth" if stage in {"formation", "resolution"} else None,
            targets=("wealth",) if stage in {"transformation", "special_gate"} else (),
            resolves=("damage.any",) if stage == "rescue" else (),
            supersedes=("seal",) if stage == "resolution" else (),
        )


def test_effect_contract_rejects_no_op_invalidation_and_resolution_rules() -> None:
    with pytest.raises(ValueError, match="requires invalidates_rescue_ids"):
        _rule(
            "damage.no-op-invalidation",
            "damage",
            effect="rescue_invalidation",
        )
    with pytest.raises(ValueError, match="requires supersedes_path_ids"):
        _rule(
            "resolution.no-op",
            "resolution",
            effect="source_precedence",
            path_id="wealth",
        )
    with pytest.raises(ValueError, match="requires path_id"):
        _rule(
            "resolution.unbound",
            "resolution",
            effect="source_precedence",
            supersedes=("wealth",),
        )


@pytest.mark.parametrize(
    ("stage", "kwargs"),
    [
        ("formation", {"path_id": "wealth", "targets": ("wealth",)}),
        (
            "formation",
            {"path_id": "wealth", "invalidates": ("rescue.any",)},
        ),
        ("damage", {"supersedes": ("wealth",)}),
        ("damage", {"invalidates": ("rescue.any",)}),
        (
            "rescue",
            {
                "resolves": ("damage.any",),
                "invalidates": ("rescue.any",),
            },
        ),
        (
            "resolution",
            {
                "effect": "source_precedence",
                "path_id": "wealth",
                "supersedes": ("seal",),
                "invalidates": ("rescue.any",),
            },
        ),
    ],
)
def test_lifecycle_stages_reject_foreign_side_effect_fields(
    stage: str,
    kwargs: dict[str, Any],
) -> None:
    with pytest.raises(ValueError, match="side effect|invalidate"):
        _rule(f"foreign-side-effect.{stage}", stage, **kwargs)


@pytest.mark.parametrize("stage", ["damage", "rescue"])
def test_damage_and_rescue_use_only_one_path_binding_form(stage: str) -> None:
    with pytest.raises(ValueError, match="only one path binding"):
        _rule(
            f"double-bound.{stage}",
            stage,
            path_id="wealth",
            targets=("wealth",),
            resolves=("damage.any",) if stage == "rescue" else (),
        )


def test_rescue_must_reference_an_actual_damage_on_a_shared_path() -> None:
    wealth = _rule("form.wealth", "formation", path_id="wealth")
    seal = _rule("form.seal", "formation", path_id="seal")
    invalidator = _rule(
        "damage.invalidate-rescue",
        "damage",
        effect="rescue_invalidation",
        targets=("wealth",),
        invalidates=("rescue.invalid",),
    )
    invalid_rescue = _rule(
        "rescue.invalid",
        "rescue",
        targets=("wealth",),
        resolves=(invalidator.id,),
    )
    with pytest.raises(ValueError, match="actual damage"):
        _registry(wealth, invalidator, invalid_rescue)

    damage = _rule("damage.wealth", "damage", targets=("wealth",))
    wrong_path_rescue = _rule(
        "rescue.seal",
        "rescue",
        targets=("seal",),
        resolves=(damage.id,),
    )
    with pytest.raises(ValueError, match="share a formation path"):
        _registry(wealth, seal, damage, wrong_path_rescue)


@pytest.mark.parametrize(
    ("stage", "effect"),
    [
        ("transformation", "transformation"),
        ("special_gate", "require"),
        ("special_gate", "reject"),
    ],
)
def test_terminal_rules_require_explicit_path_binding(stage: str, effect: str) -> None:
    with pytest.raises(ValueError, match="formation path binding"):
        _rule(f"unbound.{stage}.{effect}", stage, effect=effect)


def test_terminal_rules_reject_ambiguous_or_double_duty_bindings() -> None:
    with pytest.raises(ValueError, match="exactly one formation path binding"):
        _rule(
            "transform.ambiguous",
            "transformation",
            effect="transformation",
            path_id="wealth",
            targets=("wealth",),
        )
    with pytest.raises(ValueError, match="cannot declare lifecycle side effects"):
        _rule(
            "transform.precedence",
            "transformation",
            effect="transformation",
            targets=("wealth",),
            supersedes=("seal",),
        )
    with pytest.raises(ValueError, match="cannot declare lifecycle side effects"):
        _rule(
            "gate.invalidation",
            "special_gate",
            effect="require",
            targets=("wealth",),
            invalidates=("rescue.any",),
        )


@pytest.mark.parametrize(
    ("stage", "effect"),
    [
        ("transformation", "transformation"),
        ("special_gate", "require"),
        ("special_gate", "reject"),
    ],
)
def test_terminal_rule_binding_must_name_a_declared_formation_path(
    stage: str,
    effect: str,
) -> None:
    formation = _rule("form.wealth", "formation", path_id="wealth")
    terminal = _rule(
        f"missing.{stage}.{effect}",
        stage,
        effect=effect,
        targets=("missing",),
    )

    with pytest.raises(ValueError, match="unknown target path missing"):
        _registry(formation, terminal)


def test_terminal_rules_accept_path_id_or_targets_path_ids_binding() -> None:
    formation = _rule("form.wealth", "formation", path_id="wealth")

    by_path_id = _registry(
        formation,
        _rule(
            "transform.by-path",
            "transformation",
            effect="transformation",
            path_id="wealth",
        ),
    )
    by_targets = _registry(
        formation,
        _rule(
            "require.by-targets",
            "special_gate",
            effect="require",
            targets=("wealth",),
        ),
    )

    assert by_path_id.rules_for("direct_officer", "transformation")
    assert by_targets.rules_for("direct_officer", "special_gate")


def test_packaged_registry_uses_only_closed_stage_effect_pairs() -> None:
    registry = load_packaged_registry()

    assert {(rule.stage, rule.effect) for rule in registry.rules} == {
        ("candidate", "candidate_confirm"),
        ("candidate", "candidate_possible"),
        ("formation", "formation"),
        ("damage", "damage"),
        ("damage", "officer_killing_mixture"),
        ("damage", "rescue_invalidation"),
        ("rescue", "rescue"),
        ("resolution", "source_precedence"),
    }


def test_rules_by_id_iteration_uses_canonical_rule_order() -> None:
    late = _rule("form.late", "formation", path_id="late", precedence=30)
    early = _rule("form.early", "formation", path_id="early", precedence=10)
    registry = _registry(late, early)

    assert tuple(registry.rules_by_id) == tuple(rule.id for rule in registry.rules)


@pytest.mark.parametrize(
    "unsafe_source_id",
    [
        "zzq.prop.officer.damage-dual-support-001",
        "zzq.prop.officer.rescue-fan-allocation-001",
    ],
)
def test_packaged_registry_rejects_actual_example_only_proposition_sources(
    unsafe_source_id: str,
) -> None:
    registry = load_packaged_registry()
    first = replace(registry.rules[0], source_ids=(unsafe_source_id,))

    with pytest.raises(ValueError, match="verified production provenance"):
        replace(
            registry,
            rules=(first, *registry.rules[1:]),
            bundle_digest="",
        )


@pytest.mark.parametrize(
    ("field_name", "replacement"),
    [
        ("corpus_artifact_digest", "0" * 64),
        ("source_manifest_digest", "1" * 64),
    ],
)
def test_source_provenance_digest_binds_eligibility_facts(
    field_name: str,
    replacement: str,
) -> None:
    registry = load_packaged_registry()
    changed = replace(
        registry.source_provenance[0],
        **{field_name: replacement},
    )

    with pytest.raises(ValueError, match="does not bind source eligibility facts"):
        replace(
            registry,
            source_provenance=(changed, *registry.source_provenance[1:]),
            bundle_digest="",
        )

    with pytest.raises(ValueError, match="does not bind source eligibility facts"):
        replace(
            registry,
            source_bundle_digest="2" * 64,
            bundle_digest="",
        )


def test_envelope_reduces_each_world_then_returns_consensus_or_ambiguity() -> None:
    formation = _rule(
        "form.wealth",
        "formation",
        path_id="wealth",
        predicate={
            "op": "activation_exists",
            "gods": ["正财", "偏财"],
            "families": ["wealth"],
            "positions": ["hour"],
            "origins": ["exposed_stem"],
            "scope": "generic",
        },
    )
    one = _chart("甲子", "乙酉", "甲午", "戊辰")
    two = _chart("甲子", "乙酉", "甲午", "己卯")
    three = _chart("甲子", "乙酉", "甲午", "丙寅")

    consensus = evaluate_pattern_lifecycle(
        build_rule_evaluation_context(build_bazi_fact_envelope((one, two))),
        _registry(formation),
    )
    disagreement = evaluate_pattern_lifecycle(
        build_rule_evaluation_context(build_bazi_fact_envelope((one, three))),
        _registry(formation),
    )

    assert consensus.status == "formed"
    assert disagreement.status == "ambiguous"
    assert {item.status for item in disagreement.world_results} == {
        "formed",
        "candidate",
    }


def test_registry_rejects_unknown_targets_rescue_without_damage_and_metadata() -> None:
    formation = _rule("form", "formation", path_id="wealth")
    with pytest.raises(ValueError, match="unknown target path"):
        _registry(formation, _rule("damage", "damage", targets=("missing",)))
    with pytest.raises(ValueError, match="declared damage"):
        _registry(
            formation,
            _rule("rescue", "rescue", targets=("wealth",), resolves=()),
        )

    with pytest.raises(ValueError, match="unsupported lifecycle side effects"):
        _rule(
            "rescue.invalidates-another-rescue",
            "rescue",
            targets=("wealth",),
            resolves=("damage",),
            invalidates=("rescue.other",),
        )

    record = {
        "id": "form",
        "predicate": TRUE,
        "effect": "formation",
        "precedence": 1,
        "metadata": {
            "stage": "formation",
            "pattern_id": "direct_officer",
            "path_id": "wealth",
            "targets_path_ids": [],
            "resolves_damage_ids": [],
            "invalidates_rescue_ids": [],
            "supersedes_path_ids": [],
            "authority_layer": "shen_core",
            "source_ids": ["prop.form"],
            "arbitrary_binding": "forbidden",
        },
    }
    with pytest.raises(ValueError, match="unknown metadata"):
        registry_from_records("fixture", [record])


def test_registry_rejects_cross_pattern_and_attestation_dependencies() -> None:
    other = replace(
        _rule("other.form", "formation", path_id="other"),
        pattern_id="other_pattern",
    )
    direct = _rule("direct.form", "formation", path_id="wealth")
    cross = _rule("direct.damage", "damage", targets=("other",))
    with pytest.raises(ValueError, match="cross-pattern"):
        _registry(other, direct, cross)

    with pytest.raises(ValueError, match="attestation"):
        replace(direct, source_ids=("zzq.attestation.anonymous",))


def test_registry_rejects_nonformation_path_binding_to_unknown_path() -> None:
    formation = _rule("direct.form", "formation", path_id="wealth")
    mistyped_binding = _rule("direct.damage", "damage", path_id="weatlh")

    with pytest.raises(ValueError, match="unknown target path weatlh"):
        _registry(formation, mistyped_binding)


def test_registry_rejects_duplicate_exclusions_and_invalid_source_digest() -> None:
    exclusion = RegistryExclusion("candidate.one", "not executable", ("prop.one",))
    with pytest.raises(ValueError, match="duplicate exclusion"):
        RuleRegistry(
            "fixture",
            (_rule("form", "formation", path_id="wealth"),),
            exclusions=(exclusion, exclusion),
        )
    with pytest.raises(ValueError, match="source_bundle_digest"):
        RuleRegistry(
            "fixture",
            (_rule("form", "formation", path_id="wealth"),),
            source_bundle_digest="not-a-digest",
        )

    invalid_record = {
        "id": 17,
        "predicate": TRUE,
        "effect": "formation",
        "precedence": 1,
        "metadata": {
            "stage": "formation",
            "pattern_id": "direct_officer",
            "path_id": "wealth",
            "targets_path_ids": [],
            "resolves_damage_ids": [],
            "invalidates_rescue_ids": [],
            "supersedes_path_ids": [],
            "authority_layer": "shen_core",
            "source_ids": ["prop.form"],
        },
    }
    with pytest.raises(ValueError, match="rule id"):
        registry_from_records("fixture", [invalid_record])


def test_compiled_registry_sources_must_exactly_cite_the_compiled_proposition() -> None:
    record = {
        "id": "form",
        "proposition_id": "prop.shen-core",
        "predicate": TRUE,
        "effect": "formation",
        "precedence": 1,
        "metadata": {
            "stage": "formation",
            "pattern_id": "direct_officer",
            "path_id": "wealth",
            "targets_path_ids": [],
            "resolves_damage_ids": [],
            "invalidates_rescue_ids": [],
            "supersedes_path_ids": [],
            "authority_layer": "shen_core",
            "source_ids": [
                "prop.shen-core",
                "zzq.prop.officer.damage-dual-support-001",
            ],
        },
    }

    with pytest.raises(ValueError, match="exactly cite proposition_id"):
        registry_from_records("fixture", [record])
