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
    SpecialReviewGatePolicy,
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
SPECIAL_REVIEW_GATE_STATUSES = frozenset(("blocked", "eligible", "undetermined"))


def _truth_value(values: Sequence[TruthValue]) -> TruthValue:
    if TruthValue.TRUE in values:
        return TruthValue.TRUE
    if TruthValue.UNKNOWN in values:
        return TruthValue.UNKNOWN
    return TruthValue.FALSE


def _consensus_truth(values: Sequence[TruthValue]) -> TruthValue:
    distinct = set(values)
    if len(distinct) == 1:
        return next(iter(distinct))
    return TruthValue.UNKNOWN


@dataclass(frozen=True)
class LifecycleRuleTrace:
    rule_id: str
    stage: str
    truth: TruthValue
    path_id: str | None
    targets_path_ids: tuple[str, ...]
    source_ids: tuple[str, ...]
    predicate_trace: EvaluationTrace
    supporting_source_ids: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        result = {
            "rule_id": self.rule_id,
            "stage": self.stage,
            "truth": self.truth.value,
            "path_id": self.path_id,
            "targets_path_ids": list(self.targets_path_ids),
            "source_ids": list(self.source_ids),
            "predicate_trace": self.predicate_trace.as_dict(),
        }
        if self.supporting_source_ids:
            result["supporting_source_ids"] = list(self.supporting_source_ids)
        return result


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


@dataclass(frozen=True)
class SpecialReviewGateResult:
    policy_id: str
    status: str
    review_allowed: TruthValue
    checks: Mapping[str, TruthValue]
    source_bindings: Mapping[str, str]
    check_details: Mapping[str, Mapping[str, Any]]
    blocking_reasons: tuple[str, ...] = ()
    uncertain_reasons: tuple[str, ...] = ()
    world_digest: str | None = None
    world_results: tuple["SpecialReviewGateResult", ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.policy_id, str) or not self.policy_id.strip():
            raise ValueError("special review gate policy_id must be non-blank")
        if self.status not in SPECIAL_REVIEW_GATE_STATUSES:
            raise ValueError(f"unknown special review gate status: {self.status!r}")
        expected_status = {
            TruthValue.TRUE: "eligible",
            TruthValue.FALSE: "blocked",
            TruthValue.UNKNOWN: "undetermined",
        }[self.review_allowed]
        if self.status != expected_status:
            raise ValueError("special review gate status contradicts review_allowed")
        checks = dict(self.checks)
        expected_checks = {
            "ordinary_use",
            "officer_killing_exposed",
            "rooted_wealth",
            "double_wealth_exposed",
        }
        if set(checks) != expected_checks or any(
            not isinstance(value, TruthValue) for value in checks.values()
        ):
            raise ValueError("special review gate checks are incomplete")
        source_bindings = dict(self.source_bindings)
        if set(source_bindings) != expected_checks or any(
            not isinstance(value, str) or not value
            for value in source_bindings.values()
        ):
            raise ValueError("special review gate source bindings are incomplete")
        if len(set(source_bindings.values())) != len(source_bindings):
            raise ValueError("special review gate source bindings must be unique")
        object.__setattr__(self, "checks", MappingProxyType(checks))
        object.__setattr__(
            self, "source_bindings", MappingProxyType(source_bindings)
        )
        check_details = dict(self.check_details)
        if set(check_details) != expected_checks or any(
            not isinstance(value, Mapping) for value in check_details.values()
        ):
            raise ValueError("special review gate check details are incomplete")
        object.__setattr__(
            self,
            "check_details",
            MappingProxyType(
                {
                    key: MappingProxyType(dict(value))
                    for key, value in check_details.items()
                }
            ),
        )
        for field_name in ("blocking_reasons", "uncertain_reasons"):
            values = tuple(getattr(self, field_name))
            if values != tuple(sorted(set(values))):
                raise ValueError(f"{field_name} must be unique and sorted")
            object.__setattr__(self, field_name, values)
        object.__setattr__(self, "world_results", tuple(self.world_results))
        if self.status == "blocked" and not self.blocking_reasons:
            raise ValueError("blocked special review gate requires a blocking reason")
        if self.status == "eligible" and (
            self.blocking_reasons or self.uncertain_reasons
        ):
            raise ValueError("eligible special review gate cannot retain blockers")
        if self.status == "undetermined" and not self.uncertain_reasons:
            raise ValueError("undetermined special review gate requires uncertainty")
        if any(
            item.policy_id != self.policy_id
            or dict(item.source_bindings) != source_bindings
            for item in self.world_results
        ):
            raise ValueError("special review gate worlds must share one source policy")

    def as_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "status": self.status,
            "review_allowed": self.review_allowed.value,
            "checks": {
                key: value.value for key, value in sorted(self.checks.items())
            },
            "source_bindings": dict(sorted(self.source_bindings.items())),
            "check_details": {
                key: dict(value)
                for key, value in sorted(self.check_details.items())
            },
            "blocking_reasons": list(self.blocking_reasons),
            "uncertain_reasons": list(self.uncertain_reasons),
            "world_digest": self.world_digest,
            "world_results": [item.as_dict() for item in self.world_results],
        }


@dataclass(frozen=True)
class PatternSetResult:
    bundle_id: str
    bundle_digest: str
    authority_layer: str
    patterns: tuple[PatternLifecycleResult, ...]
    active_pattern_ids: tuple[str, ...]
    ambiguous_pattern_ids: tuple[str, ...]
    suppressed_pattern_ids: tuple[str, ...] = ()
    special_review_gate: SpecialReviewGateResult | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "patterns", tuple(self.patterns))
        for field_name in (
            "active_pattern_ids",
            "ambiguous_pattern_ids",
            "suppressed_pattern_ids",
        ):
            values = tuple(getattr(self, field_name))
            if values != tuple(sorted(values)) or len(values) != len(set(values)):
                raise ValueError(f"{field_name} must contain unique sorted pattern IDs")
            object.__setattr__(self, field_name, values)
        ids = [item.pattern_id for item in self.patterns]
        if ids != sorted(ids) or len(ids) != len(set(ids)):
            raise ValueError("pattern set results must have unique sorted pattern IDs")
        pattern_ids = set(ids)
        result_sets = {
            "active_pattern_ids": set(self.active_pattern_ids),
            "ambiguous_pattern_ids": set(self.ambiguous_pattern_ids),
            "suppressed_pattern_ids": set(self.suppressed_pattern_ids),
        }
        for field_name, values in result_sets.items():
            if not values <= pattern_ids:
                raise ValueError(f"{field_name} contains an undeclared pattern ID")
        field_names = tuple(result_sets)
        for index, left_name in enumerate(field_names):
            for right_name in field_names[index + 1 :]:
                if result_sets[left_name] & result_sets[right_name]:
                    raise ValueError("pattern result ID sets must be disjoint")
        if any(
            item.bundle_id != self.bundle_id or item.bundle_digest != self.bundle_digest
            for item in self.patterns
        ):
            raise ValueError("pattern result bundle identity does not match its set")
        if self.special_review_gate is not None and not isinstance(
            self.special_review_gate, SpecialReviewGateResult
        ):
            raise TypeError("special_review_gate must be a SpecialReviewGateResult")

    def by_id(self, pattern_id: str) -> PatternLifecycleResult:
        try:
            return next(item for item in self.patterns if item.pattern_id == pattern_id)
        except StopIteration as exc:
            raise KeyError(pattern_id) from exc

    def as_dict(self) -> dict[str, Any]:
        result = {
            "engine_version": LIFECYCLE_ENGINE_VERSION,
            "bundle_id": self.bundle_id,
            "bundle_digest": self.bundle_digest,
            "authority_layer": self.authority_layer,
            "patterns": [item.as_dict() for item in self.patterns],
            "active_pattern_ids": list(self.active_pattern_ids),
            "ambiguous_pattern_ids": list(self.ambiguous_pattern_ids),
            "suppressed_pattern_ids": list(self.suppressed_pattern_ids),
        }
        if self.special_review_gate is not None:
            result["special_review_gate"] = self.special_review_gate.as_dict()
        return result


def _legacy_candidate_truth(graph: BaziFactGraph, pattern_id: str) -> TruthValue:
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


def _candidate_truth(
    graph: BaziFactGraph,
    pattern_id: str,
    rules: Sequence[RegistryRule],
    evaluations: Mapping[str, Any],
) -> tuple[TruthValue, str]:
    confirmed_rules = tuple(
        item for item in rules if item.effect == "candidate_confirm"
    )
    possible_rules = tuple(
        item for item in rules if item.effect == "candidate_possible"
    )
    if not confirmed_rules and not possible_rules:
        return _legacy_candidate_truth(graph, pattern_id), "month_command_qi_level"
    if not confirmed_rules or not possible_rules:
        raise ValueError(
            f"pattern {pattern_id} requires candidate_confirm and candidate_possible"
        )
    confirmed = _truth_value([evaluations[item.id].truth for item in confirmed_rules])
    possible = _truth_value([evaluations[item.id].truth for item in possible_rules])
    if confirmed is TruthValue.TRUE:
        return TruthValue.TRUE, "source_backed_candidate_rules"
    if confirmed is TruthValue.UNKNOWN:
        return TruthValue.UNKNOWN, "source_backed_candidate_rules"
    if possible is TruthValue.FALSE:
        return TruthValue.FALSE, "source_backed_candidate_rules"
    return TruthValue.UNKNOWN, "source_backed_candidate_rules"


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
    rules = tuple(item for item in registry.rules if item.pattern_id == pattern_id)
    evaluations = {
        rule.id: evaluate_predicate(rule.predicate, context) for rule in rules
    }
    candidate, routing_policy = _candidate_truth(
        graph,
        pattern_id,
        rules,
        evaluations,
    )
    stage_traces: list[LifecycleStageTrace] = []
    for stage in LIFECYCLE_STAGES:
        stage_rules = tuple(item for item in rules if item.stage == stage)
        details: dict[str, Any] = {}
        if stage == "candidate":
            details = {
                "routing_truth": candidate.value,
                "routing_policy": routing_policy,
            }
        if stage in {"transformation", "special_gate"} and not stage_rules:
            details = {"executed": True, "rule_count": 0}
        if stage == "resolution" and registry.exclusions:
            relevant_exclusions = tuple(
                item
                for item in registry.exclusions
                if item.pattern_id in {None, pattern_id}
            )
            details = {
                "excluded_candidates": [
                    {
                        "candidate_id": item.candidate_id,
                        "reason": item.reason,
                        "source_ids": list(item.source_ids),
                    }
                    for item in relevant_exclusions
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
                        supporting_source_ids=rule.supporting_source_ids,
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
    declared_pattern_ids = {rule.pattern_id for rule in registry.rules}
    if pattern_id not in declared_pattern_ids:
        raise ValueError(
            f"pattern {pattern_id!r} is not declared by registry {registry.bundle_id!r}"
        )
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


def _special_gate_source_bindings(
    policy: SpecialReviewGatePolicy,
) -> dict[str, str]:
    return {
        "ordinary_use": policy.ordinary_use_source_id,
        "officer_killing_exposed": policy.officer_killing_source_id,
        "rooted_wealth": policy.rooted_wealth_source_id,
        "double_wealth_exposed": policy.double_wealth_source_id,
    }


def _ordinary_use_truth(
    patterns: Sequence[PatternLifecycleResult],
) -> TruthValue:
    for pattern in patterns:
        if pattern.candidate is not TruthValue.TRUE:
            continue
        if any(path.formation_truth is TruthValue.TRUE for path in pattern.paths):
            return TruthValue.TRUE
    # The current canonical registry does not claim closed-world coverage of
    # every way a month-command use can form. No compiled match therefore
    # cannot prove 月令無用; it remains UNKNOWN until a completeness contract
    # exists for every ordinary pattern.
    return TruthValue.UNKNOWN


def _evaluate_special_review_gate_world(
    context: RuleEvaluationContext,
    policy: SpecialReviewGatePolicy,
    patterns: Sequence[PatternLifecycleResult],
) -> SpecialReviewGateResult:
    graph = context.graph
    if not isinstance(graph, BaziFactGraph):
        raise TypeError("one-world special review gate requires BaziFactGraph")
    officer_killing_evaluation = evaluate_predicate(
        {"op": "god_exposed", "gods": ["正官", "七杀"]},
        context,
    )
    officer_killing = officer_killing_evaluation.truth
    exposed_wealth_evaluation = evaluate_predicate(
        {"op": "god_exposed", "gods": ["正财", "偏财"]},
        context,
    )
    hidden_wealth_evaluation = evaluate_predicate(
        {
            "op": "exists_occurrence",
            "gods": ["正财", "偏财"],
            "layers": ["hidden"],
        },
        context,
    )
    # The source says 財根深, not merely "wealth appears in a branch". Until
    # that depth predicate is separately source-bound, a hidden occurrence is
    # evidence of an unresolved blocker rather than a fabricated TRUE result.
    if exposed_wealth_evaluation.truth is TruthValue.FALSE:
        rooted_wealth = TruthValue.FALSE
    elif (
        exposed_wealth_evaluation.truth is TruthValue.TRUE
        and hidden_wealth_evaluation.truth is TruthValue.FALSE
    ):
        rooted_wealth = TruthValue.FALSE
    else:
        rooted_wealth = TruthValue.UNKNOWN
    double_wealth_evaluation = evaluate_predicate(
        {
            "op": "count_compare",
            "path": "occurrences",
            "where": {
                "gods": ["正财", "偏财"],
                "layers": ["stem"],
                "exposed": True,
            },
            "comparator": ">=",
            "value": 2,
        },
        context,
    )
    double_wealth = double_wealth_evaluation.truth
    checks = {
        "ordinary_use": _ordinary_use_truth(patterns),
        "officer_killing_exposed": officer_killing,
        "rooted_wealth": rooted_wealth,
        "double_wealth_exposed": double_wealth,
    }
    ordinary_details = {
        "candidate_pattern_ids": sorted(
            pattern.pattern_id
            for pattern in patterns
            if pattern.candidate is TruthValue.TRUE
        ),
        "formed_paths": sorted(
            f"{pattern.pattern_id}:{path.path_id}"
            for pattern in patterns
            if pattern.candidate is TruthValue.TRUE
            for path in pattern.paths
            if path.formation_truth is TruthValue.TRUE
        ),
        "coverage": "open_world",
    }
    check_details = {
        "ordinary_use": ordinary_details,
        "officer_killing_exposed": officer_killing_evaluation.trace.as_dict(),
        "rooted_wealth": {
            "exposed_wealth": exposed_wealth_evaluation.trace.as_dict(),
            "hidden_wealth": hidden_wealth_evaluation.trace.as_dict(),
            "binding_status": "root_depth_predicate_unresolved",
        },
        "double_wealth_exposed": double_wealth_evaluation.trace.as_dict(),
    }
    definitive_blockers = tuple(
        sorted(
            key
            for key in (
                "ordinary_use",
                "officer_killing_exposed",
                "double_wealth_exposed",
            )
            if checks[key] is TruthValue.TRUE
        )
    )
    uncertainties = tuple(
        sorted(key for key, truth in checks.items() if truth is TruthValue.UNKNOWN)
    )
    if definitive_blockers:
        review_allowed = TruthValue.FALSE
        status = "blocked"
    elif uncertainties:
        review_allowed = TruthValue.UNKNOWN
        status = "undetermined"
    else:
        review_allowed = TruthValue.TRUE
        status = "eligible"
    return SpecialReviewGateResult(
        policy_id=policy.id,
        status=status,
        review_allowed=review_allowed,
        checks=checks,
        source_bindings=_special_gate_source_bindings(policy),
        check_details=check_details,
        blocking_reasons=definitive_blockers,
        uncertain_reasons=uncertainties,
        world_digest=graph.digest,
    )


def _evaluate_special_review_gate(
    context: RuleEvaluationContext,
    policy: SpecialReviewGatePolicy,
    patterns: Sequence[PatternLifecycleResult],
) -> SpecialReviewGateResult:
    if isinstance(context.graph, BaziFactGraph):
        return _evaluate_special_review_gate_world(context, policy, patterns)

    envelope = context.graph
    source_activations = tuple(
        item for item in context.activations if item.origin == "source_rule"
    )
    if any(len(pattern.world_results) != len(envelope.worlds) for pattern in patterns):
        raise ValueError("pattern world results do not align with fact envelope")
    world_results = tuple(
        _evaluate_special_review_gate_world(
            build_rule_evaluation_context(
                world,
                source_activations=source_activations,
            ),
            policy,
            tuple(pattern.world_results[index] for pattern in patterns),
        )
        for index, world in enumerate(envelope.worlds)
    )
    review_allowed = _consensus_truth(
        [item.review_allowed for item in world_results]
    )
    status = {
        TruthValue.TRUE: "eligible",
        TruthValue.FALSE: "blocked",
        TruthValue.UNKNOWN: "undetermined",
    }[review_allowed]
    check_names = tuple(world_results[0].checks) if world_results else ()
    checks = {
        key: _consensus_truth([item.checks[key] for item in world_results])
        for key in check_names
    }
    check_details = {
        key: {
            "world_digests": [item.world_digest for item in world_results],
            "world_values": [item.checks[key].value for item in world_results],
        }
        for key in check_names
    }
    blocking_reasons = (
        tuple(
            sorted(
                {
                    reason
                    for item in world_results
                    for reason in item.blocking_reasons
                }
            )
        )
        if review_allowed is TruthValue.FALSE
        else ()
    )
    uncertain_reasons = set(
        reason for item in world_results for reason in item.uncertain_reasons
    )
    if review_allowed is TruthValue.UNKNOWN:
        uncertain_reasons.add("candidate_world_gate_disagreement")
    return SpecialReviewGateResult(
        policy_id=policy.id,
        status=status,
        review_allowed=review_allowed,
        checks=checks,
        source_bindings=_special_gate_source_bindings(policy),
        check_details=check_details,
        blocking_reasons=blocking_reasons,
        uncertain_reasons=tuple(sorted(uncertain_reasons)),
        world_digest=envelope.digest,
        world_results=world_results,
    )


def evaluate_pattern_set(
    context: RuleEvaluationContext,
    registry: RuleRegistry,
) -> PatternSetResult:
    """Evaluate every declared pattern without selecting a list-order winner."""

    if not isinstance(context, RuleEvaluationContext):
        raise TypeError("context must be RuleEvaluationContext")
    if not isinstance(registry, RuleRegistry):
        raise TypeError("registry must be RuleRegistry")
    pattern_ids = tuple(sorted({item.pattern_id for item in registry.rules}))
    patterns = tuple(
        evaluate_pattern_lifecycle(
            context,
            registry,
            pattern_id=pattern_id,
        )
        for pattern_id in pattern_ids
    )
    active_statuses = {
        "formed",
        "broken",
        "rescued",
        "mixed",
        "transformed",
        "candidate",
    }
    ambiguous_statuses = {"ambiguous", "undetermined"}
    special_review_gate = (
        _evaluate_special_review_gate(
            context,
            registry.special_review_gate,
            patterns,
        )
        if registry.special_review_gate is not None
        else None
    )
    return PatternSetResult(
        bundle_id=registry.bundle_id,
        bundle_digest=registry.bundle_digest,
        authority_layer=str(registry.authority_layer),
        patterns=patterns,
        active_pattern_ids=tuple(
            item.pattern_id for item in patterns if item.status in active_statuses
        ),
        ambiguous_pattern_ids=tuple(
            item.pattern_id for item in patterns if item.status in ambiguous_statuses
        ),
        suppressed_pattern_ids=(),
        special_review_gate=special_review_gate,
    )


__all__ = [
    "LIFECYCLE_ENGINE_VERSION",
    "LIFECYCLE_STATUSES",
    "SPECIAL_REVIEW_GATE_STATUSES",
    "LifecycleRuleTrace",
    "LifecycleStageTrace",
    "PathLifecycleResult",
    "PatternLifecycleResult",
    "PatternSetResult",
    "SpecialReviewGateResult",
    "evaluate_pattern_lifecycle",
    "evaluate_pattern_set",
]
