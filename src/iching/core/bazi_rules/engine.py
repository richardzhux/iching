"""Deterministic, path-local lifecycle reduction for source-backed patterns."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from iching.core.bazi_rules.fact_graph import build_rule_evaluation_context
from iching.core.bazi_rules.predicates import evaluate_predicate
from iching.core.bazi_rules.registry import (
    LIFECYCLE_STAGES,
    RegistryRule,
    RuleRegistry,
)
from iching.core.bazi_rules.schema import (
    BaziFactEnvelope,
    BaziFactGraph,
    EvaluationTrace,
    RuleEvaluationContext,
    TruthValue,
)


LIFECYCLE_ENGINE_VERSION = "bazi-pattern-lifecycle-v1"
LIFECYCLE_STATUSES = frozenset(
    (
        "formed",
        "broken",
        "rescued",
        "mixed",
        "transformed",
        "candidate",
        "rejected",
        "undetermined",
        "ambiguous",
    )
)


def _truth_value(values: Sequence[TruthValue]) -> TruthValue:
    if TruthValue.TRUE in values:
        return TruthValue.TRUE
    if TruthValue.UNKNOWN in values:
        return TruthValue.UNKNOWN
    return TruthValue.FALSE


@dataclass(frozen=True)
class LifecycleRuleTrace:
    rule_id: str
    stage: str
    truth: TruthValue
    path_id: str | None
    targets_path_ids: tuple[str, ...]
    source_ids: tuple[str, ...]
    predicate_trace: EvaluationTrace

    def as_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "stage": self.stage,
            "truth": self.truth.value,
            "path_id": self.path_id,
            "targets_path_ids": list(self.targets_path_ids),
            "source_ids": list(self.source_ids),
            "predicate_trace": self.predicate_trace.as_dict(),
        }


@dataclass(frozen=True)
class LifecycleStageTrace:
    stage: str
    rules: tuple[LifecycleRuleTrace, ...] = ()
    details: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "rules", tuple(self.rules))
        object.__setattr__(self, "details", MappingProxyType(dict(self.details)))

    def as_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "rules": [item.as_dict() for item in self.rules],
            "details": dict(self.details),
        }


@dataclass(frozen=True)
class PathLifecycleResult:
    path_id: str
    formation_truth: TruthValue
    status: str
    actual_damage_ids: tuple[str, ...] = ()
    unknown_damage_ids: tuple[str, ...] = ()
    resolved_damage_ids: tuple[str, ...] = ()
    unresolved_damage_ids: tuple[str, ...] = ()
    active_rescue_ids: tuple[str, ...] = ()
    invalidated_rescue_ids: tuple[str, ...] = ()
    superseded_by_rule_ids: tuple[str, ...] = ()
    reasons: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "path_id": self.path_id,
            "formation_truth": self.formation_truth.value,
            "status": self.status,
            "actual_damage_ids": list(self.actual_damage_ids),
            "unknown_damage_ids": list(self.unknown_damage_ids),
            "resolved_damage_ids": list(self.resolved_damage_ids),
            "unresolved_damage_ids": list(self.unresolved_damage_ids),
            "active_rescue_ids": list(self.active_rescue_ids),
            "invalidated_rescue_ids": list(self.invalidated_rescue_ids),
            "superseded_by_rule_ids": list(self.superseded_by_rule_ids),
            "reasons": list(self.reasons),
        }


@dataclass(frozen=True)
class PatternLifecycleResult:
    pattern_id: str
    status: str
    candidate: TruthValue
    bundle_id: str
    bundle_digest: str
    paths: tuple[PathLifecycleResult, ...]
    stages: tuple[LifecycleStageTrace, ...]
    reasons: tuple[str, ...] = ()
    world_digest: str | None = None
    world_results: tuple["PatternLifecycleResult", ...] = ()

    @property
    def candidate_truth(self) -> TruthValue:
        return self.candidate

    def as_dict(self) -> dict[str, Any]:
        return {
            "engine_version": LIFECYCLE_ENGINE_VERSION,
            "pattern_id": self.pattern_id,
            "status": self.status,
            "candidate": self.candidate.value,
            "bundle_id": self.bundle_id,
            "bundle_digest": self.bundle_digest,
            "paths": [item.as_dict() for item in self.paths],
            "stages": [item.as_dict() for item in self.stages],
            "reasons": list(self.reasons),
            "world_digest": self.world_digest,
            "world_results": [item.as_dict() for item in self.world_results],
        }


def _candidate_truth(graph: BaziFactGraph, pattern_id: str) -> TruthValue:
    if pattern_id != "direct_officer":
        return TruthValue.FALSE
    main = graph.month_command.at("main")
    if any(item.ten_god == "正官" for item in main):
        return TruthValue.TRUE
    if any(
        item.ten_god == "正官"
        for level in ("secondary", "residual")
        for item in graph.month_command.at(level)
    ):
        return TruthValue.UNKNOWN
    return TruthValue.FALSE


def _targets(rule: RegistryRule, path_id: str) -> bool:
    if rule.targets_path_ids:
        return path_id in rule.targets_path_ids
    if rule.path_id is not None:
        return rule.path_id == path_id
    return True


def _evaluate_world(
    context: RuleEvaluationContext,
    registry: RuleRegistry,
    pattern_id: str,
) -> PatternLifecycleResult:
    graph = context.graph
    if not isinstance(graph, BaziFactGraph):
        raise TypeError("one-world lifecycle evaluation requires BaziFactGraph")
    candidate = _candidate_truth(graph, pattern_id)
    rules = tuple(item for item in registry.rules if item.pattern_id == pattern_id)
    evaluations = {
        rule.id: evaluate_predicate(rule.predicate, context) for rule in rules
    }
    stage_traces: list[LifecycleStageTrace] = []
    for stage in LIFECYCLE_STAGES:
        stage_rules = tuple(item for item in rules if item.stage == stage)
        details: dict[str, Any] = {}
        if stage == "candidate":
            details = {
                "routing_truth": candidate.value,
                "routing_policy": "month_command_qi_level",
            }
        if stage in {"transformation", "special_gate"} and not stage_rules:
            details = {"executed": True, "rule_count": 0}
        if stage == "resolution" and registry.exclusions:
            details = {
                "excluded_candidates": [
                    {
                        "candidate_id": item.candidate_id,
                        "reason": item.reason,
                        "source_ids": list(item.source_ids),
                    }
                    for item in registry.exclusions
                ]
            }
        stage_traces.append(
            LifecycleStageTrace(
                stage=stage,
                rules=tuple(
                    LifecycleRuleTrace(
                        rule_id=rule.id,
                        stage=stage,
                        truth=evaluations[rule.id].truth,
                        path_id=rule.path_id,
                        targets_path_ids=rule.targets_path_ids,
                        source_ids=rule.source_ids,
                        predicate_trace=evaluations[rule.id].trace,
                    )
                    for rule in stage_rules
                ),
                details=details,
            )
        )

    formation_rules = tuple(rule for rule in rules if rule.stage == "formation")
    path_rules: dict[str, list[RegistryRule]] = {}
    for rule in formation_rules:
        assert rule.path_id is not None
        path_rules.setdefault(rule.path_id, []).append(rule)
    formation_truths = {
        path_id: _truth_value([evaluations[rule.id].truth for rule in definitions])
        for path_id, definitions in path_rules.items()
    }

    superseded_true: dict[str, set[str]] = {path_id: set() for path_id in path_rules}
    superseded_unknown: dict[str, set[str]] = {path_id: set() for path_id in path_rules}
    for rule in rules:
        if not rule.supersedes_path_ids:
            continue
        truth = evaluations[rule.id].truth
        if rule.path_id is not None:
            controller_truth = formation_truths.get(rule.path_id, TruthValue.FALSE)
            if controller_truth is TruthValue.FALSE:
                continue
            if controller_truth is TruthValue.UNKNOWN and truth is TruthValue.TRUE:
                truth = TruthValue.UNKNOWN
        target_map = (
            superseded_true
            if truth is TruthValue.TRUE
            else superseded_unknown
            if truth is TruthValue.UNKNOWN
            else None
        )
        if target_map is None:
            continue
        for target in rule.supersedes_path_ids:
            target_map[target].add(rule.id)

    damage_rules = tuple(
        rule
        for rule in rules
        if rule.stage == "damage" and rule.effect != "rescue_invalidation"
    )
    rescue_rules = tuple(rule for rule in rules if rule.stage == "rescue")
    transformation_rules = tuple(
        rule for rule in rules if rule.stage == "transformation"
    )
    gate_rules = tuple(rule for rule in rules if rule.stage == "special_gate")
    path_results: list[PathLifecycleResult] = []

    for path_id in sorted(path_rules):
        formation_truth = formation_truths[path_id]
        if superseded_true[path_id]:
            path_results.append(
                PathLifecycleResult(
                    path_id=path_id,
                    formation_truth=formation_truth,
                    status="superseded",
                    superseded_by_rule_ids=tuple(sorted(superseded_true[path_id])),
                    reasons=("source_backed_path_supersession",),
                )
            )
            continue
        if formation_truth is TruthValue.FALSE:
            path_results.append(
                PathLifecycleResult(path_id, formation_truth, "inactive")
            )
            continue
        if formation_truth is TruthValue.UNKNOWN or superseded_unknown[path_id]:
            path_results.append(
                PathLifecycleResult(
                    path_id=path_id,
                    formation_truth=formation_truth,
                    status="undetermined",
                    reasons=("unknown_formation_or_precedence",),
                )
            )
            continue

        applicable_damage = tuple(
            rule for rule in damage_rules if _targets(rule, path_id)
        )
        actual_damage = tuple(
            sorted(
                rule.id
                for rule in applicable_damage
                if evaluations[rule.id].truth is TruthValue.TRUE
            )
        )
        unknown_damage = tuple(
            sorted(
                rule.id
                for rule in applicable_damage
                if evaluations[rule.id].truth is TruthValue.UNKNOWN
            )
        )
        if unknown_damage:
            path_results.append(
                PathLifecycleResult(
                    path_id=path_id,
                    formation_truth=formation_truth,
                    status="undetermined",
                    actual_damage_ids=actual_damage,
                    unknown_damage_ids=unknown_damage,
                    reasons=("relevant_unknown_damage",),
                )
            )
            continue

        resolved: set[str] = set()
        unresolved: set[str] = set()
        active_rescues: set[str] = set()
        invalidated_rescues: set[str] = set()
        rescue_uncertain = False
        for damage_id in actual_damage:
            candidates = tuple(
                rescue
                for rescue in rescue_rules
                if damage_id in rescue.resolves_damage_ids and _targets(rescue, path_id)
            )
            definitive_rescue = False
            pending_rescue = False
            for rescue in candidates:
                rescue_truth = evaluations[rescue.id].truth
                if rescue_truth is TruthValue.FALSE:
                    continue
                invalidators = tuple(
                    rule
                    for rule in rules
                    if rescue.id in rule.invalidates_rescue_ids
                    and _targets(rule, path_id)
                )
                invalidator_truths = tuple(
                    evaluations[rule.id].truth for rule in invalidators
                )
                if TruthValue.TRUE in invalidator_truths:
                    if rescue_truth is TruthValue.TRUE:
                        invalidated_rescues.add(rescue.id)
                    continue
                if (
                    rescue_truth is TruthValue.UNKNOWN
                    or TruthValue.UNKNOWN in invalidator_truths
                ):
                    pending_rescue = True
                    continue
                definitive_rescue = True
                active_rescues.add(rescue.id)
            if definitive_rescue:
                resolved.add(damage_id)
            elif pending_rescue:
                rescue_uncertain = True
            else:
                unresolved.add(damage_id)

        applicable_transformations = tuple(
            rule for rule in transformation_rules if _targets(rule, path_id)
        )
        transformation_truth = (
            _truth_value(
                [evaluations[rule.id].truth for rule in applicable_transformations]
            )
            if applicable_transformations
            else TruthValue.FALSE
        )
        applicable_gates = tuple(rule for rule in gate_rules if _targets(rule, path_id))
        gate_unknown = any(
            evaluations[rule.id].truth is TruthValue.UNKNOWN
            for rule in applicable_gates
        )
        gate_failed = any(
            (
                rule.effect == "require"
                and evaluations[rule.id].truth is TruthValue.FALSE
            )
            or (
                rule.effect == "reject"
                and evaluations[rule.id].truth is TruthValue.TRUE
            )
            for rule in applicable_gates
        )

        if (
            transformation_truth is TruthValue.UNKNOWN
            or gate_unknown
            or rescue_uncertain
        ):
            status = "undetermined"
            reasons = ("relevant_unknown_rescue_transformation_or_gate",)
        elif gate_failed:
            status = "broken"
            reasons = ("special_gate_failed",)
        elif transformation_truth is TruthValue.TRUE:
            status = "transformed"
            reasons = ("source_backed_transformation",)
        elif not actual_damage:
            status = "formed"
            reasons = ()
        elif not unresolved:
            status = "rescued"
            reasons = ("every_actual_damage_resolved",)
        elif all(
            registry.rules_by_id[damage_id].effect == "officer_killing_mixture"
            for damage_id in unresolved
        ):
            status = "mixed"
            reasons = ("unresolved_officer_killing_mixture",)
        else:
            status = "broken"
            reasons = ("unresolved_damage",)
        path_results.append(
            PathLifecycleResult(
                path_id=path_id,
                formation_truth=formation_truth,
                status=status,
                actual_damage_ids=actual_damage,
                resolved_damage_ids=tuple(sorted(resolved)),
                unresolved_damage_ids=tuple(sorted(unresolved)),
                active_rescue_ids=tuple(sorted(active_rescues)),
                invalidated_rescue_ids=tuple(sorted(invalidated_rescues)),
                reasons=reasons,
            )
        )

    if candidate is TruthValue.FALSE:
        status = "rejected"
        reasons = ("candidate_false",)
    elif candidate is TruthValue.UNKNOWN:
        status = "undetermined"
        reasons = ("candidate_unknown",)
    else:
        relevant_paths = tuple(
            item
            for item in path_results
            if item.status not in {"inactive", "superseded"}
        )
        if not relevant_paths:
            status = "candidate"
            reasons = ("no_true_or_unknown_formation",)
        elif any(item.status == "undetermined" for item in relevant_paths):
            status = "undetermined"
            reasons = ("relevant_path_unknown",)
        else:
            path_statuses = {item.status for item in relevant_paths}
            if len(path_statuses) == 1:
                status = next(iter(path_statuses))
                reasons = ()
            else:
                status = "ambiguous"
                reasons = ("incompatible_definitive_path_resolutions",)
    assert status in LIFECYCLE_STATUSES
    return PatternLifecycleResult(
        pattern_id=pattern_id,
        status=status,
        candidate=candidate,
        bundle_id=registry.bundle_id,
        bundle_digest=registry.bundle_digest,
        paths=tuple(path_results),
        stages=tuple(stage_traces),
        reasons=reasons,
        world_digest=graph.digest,
    )


def evaluate_pattern_lifecycle(
    context: RuleEvaluationContext,
    registry: RuleRegistry,
    *,
    pattern_id: str = "direct_officer",
) -> PatternLifecycleResult:
    """Evaluate every lifecycle stage without first-match or list-order fallbacks."""

    if not isinstance(context, RuleEvaluationContext):
        raise TypeError("context must be RuleEvaluationContext")
    if not isinstance(registry, RuleRegistry):
        raise TypeError("registry must be RuleRegistry")
    if isinstance(context.graph, BaziFactGraph):
        return _evaluate_world(context, registry, pattern_id)

    envelope: BaziFactEnvelope = context.graph
    source_activations = tuple(
        item for item in context.activations if item.origin == "source_rule"
    )
    world_results = tuple(
        _evaluate_world(
            build_rule_evaluation_context(
                world,
                source_activations=source_activations,
            ),
            registry,
            pattern_id,
        )
        for world in envelope.worlds
    )
    statuses = {item.status for item in world_results}
    if len(statuses) == 1:
        status = next(iter(statuses))
        reasons = ("candidate_worlds_agree",)
    elif "undetermined" in statuses:
        status = "undetermined"
        reasons = ("candidate_world_contains_uncertainty",)
    else:
        status = "ambiguous"
        reasons = ("candidate_worlds_have_differing_definitive_outcomes",)
    candidates = {item.candidate for item in world_results}
    candidate = next(iter(candidates)) if len(candidates) == 1 else TruthValue.UNKNOWN
    stages = tuple(
        LifecycleStageTrace(
            stage=stage,
            details={
                "world_statuses": [item.status for item in world_results],
                "world_digests": [item.world_digest for item in world_results],
            },
        )
        for stage in LIFECYCLE_STAGES
    )
    return PatternLifecycleResult(
        pattern_id=pattern_id,
        status=status,
        candidate=candidate,
        bundle_id=registry.bundle_id,
        bundle_digest=registry.bundle_digest,
        paths=(),
        stages=stages,
        reasons=reasons,
        world_results=world_results,
    )


__all__ = [
    "LIFECYCLE_ENGINE_VERSION",
    "LIFECYCLE_STATUSES",
    "LifecycleRuleTrace",
    "LifecycleStageTrace",
    "PathLifecycleResult",
    "PatternLifecycleResult",
    "evaluate_pattern_lifecycle",
]
