"""Shadow-only adapter between source-backed lifecycle data and legacy consumers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from iching.core.bazi_rules.engine import (
    PatternLifecycleResult,
    PatternSetResult,
    evaluate_pattern_lifecycle,
    evaluate_pattern_set,
)
from iching.core.bazi_rules.fact_graph import build_rule_evaluation_context
from iching.core.bazi_rules.registry import (
    ExampleAttestationBundle,
    load_packaged_attestation_bundle,
    load_packaged_shen_registry,
    load_packaged_task4_shadow_registry,
)
from iching.core.bazi_rules.primitives import LABEL_POSITIONS, PILLAR_POSITIONS
from iching.core.bazi_rules.schema import BaziFactEnvelope, BaziFactGraph, TruthValue


SHADOW_DIFF_REASONS = (
    "candidate_scope",
    "activation_semantics",
    "damage_binding",
    "rescue_binding",
    "source_precedence",
    "legacy_thresholds_shares",
    "legacy_list_order",
    "attestation_only",
    "scope_gap",
    "defect",
    "unclassified",
)


def _pillar_signature(pillars: Sequence[Mapping[str, Any]]) -> tuple[str, ...] | None:
    if isinstance(pillars, (str, bytes)) or len(pillars) != 4:
        return None
    ordered: dict[str, str] = {}
    for index, pillar in enumerate(pillars):
        if not isinstance(pillar, Mapping):
            return None
        text = pillar.get("text")
        stem = pillar.get("stem")
        branch = pillar.get("branch")
        if isinstance(stem, str) and isinstance(branch, str):
            derived = f"{stem}{branch}"
            if isinstance(text, str) and len(text) == 2 and text != derived:
                return None
            text = derived
        if not isinstance(text, str) or len(text) != 2:
            return None
        label = pillar.get("label")
        label_position = LABEL_POSITIONS.get(label) if isinstance(label, str) else None
        explicit_position = pillar.get("position") if "position" in pillar else None
        if explicit_position is not None and (
            not isinstance(explicit_position, str)
            or explicit_position not in PILLAR_POSITIONS
        ):
            return None
        if (
            explicit_position is not None
            and label_position is not None
            and explicit_position != label_position
        ):
            return None
        position = explicit_position or label_position or PILLAR_POSITIONS[index]
        if position in ordered:
            return None
        ordered[position] = text
    if set(ordered) != set(PILLAR_POSITIONS):
        return None
    return tuple(ordered[position] for position in PILLAR_POSITIONS)


def fact_graph_matches_pillars(
    pillars: Sequence[Mapping[str, Any]],
    graph: BaziFactGraph | BaziFactEnvelope,
) -> bool:
    """Verify that an externally supplied fact object belongs to the input."""

    signature = _pillar_signature(pillars)
    if signature is None or not isinstance(graph, BaziFactGraph):
        return False
    graph_signature = tuple(f"{pillar.stem}{pillar.branch}" for pillar in graph.pillars)
    return signature == graph_signature


def evaluate_example_attestations(
    pillars: Sequence[Mapping[str, Any]],
    *,
    bundle: ExampleAttestationBundle | None = None,
) -> list[dict[str, Any]]:
    """Return exact evidence matches without evaluating or mutating generic status."""

    signature = _pillar_signature(pillars)
    if signature is None:
        return []
    selected = bundle if bundle is not None else load_packaged_attestation_bundle()
    if not isinstance(selected, ExampleAttestationBundle):
        raise TypeError("bundle must be an ExampleAttestationBundle")
    return [
        item.canonical_data()
        for item in selected.attestations
        if item.pillars == signature
    ]


def _legacy_direct_officer_status(legacy_result: Mapping[str, Any]) -> str:
    ordinary = legacy_result.get("ordinary", ())
    if isinstance(ordinary, Sequence) and not isinstance(ordinary, (str, bytes)):
        for item in ordinary:
            if not isinstance(item, Mapping):
                continue
            if item.get("id") == "direct_officer" or item.get("name") == "正官":
                status = item.get("status")
                if isinstance(status, str) and status:
                    return status
    return "not_candidate"


def _legacy_patterns_by_id(
    legacy_result: Mapping[str, Any],
) -> tuple[dict[str, Mapping[str, Any]], frozenset[str]]:
    """Index live legacy patterns by their explicit stable IDs.

    The adapter deliberately does not fall back to array position or display
    name. A duplicate stable ID is retained as a defect so the comparison
    cannot silently choose whichever record happened to appear first.
    """

    indexed: dict[str, Mapping[str, Any]] = {}
    duplicates: set[str] = set()
    for collection_name in ("ordinary", "special"):
        values = legacy_result.get(collection_name, ())
        if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
            continue
        prefix = f"bazi.pattern.{collection_name}."
        for value in values:
            if not isinstance(value, Mapping):
                continue
            identifier = value.get("id")
            if not isinstance(identifier, str) or not identifier.startswith(prefix):
                continue
            pattern_id = identifier.removeprefix(prefix)
            if not pattern_id:
                continue
            if pattern_id in indexed:
                duplicates.add(pattern_id)
                continue
            indexed[pattern_id] = value
    return indexed, frozenset(duplicates)


def _normalized_pattern_status(status: str) -> str:
    """Normalize the one intentional inactive-status vocabulary difference."""

    return "rejected" if status in {"not_candidate", "rejected"} else status


def _canonical_structural_diff_reasons(
    pattern: PatternLifecycleResult,
    pattern_set: PatternSetResult,
) -> set[str]:
    """Classify source-engine mechanics that can explain a status mismatch."""

    reasons: set[str] = set()
    if pattern.candidate is TruthValue.UNKNOWN:
        reasons.add("candidate_scope")
    if pattern.status in {"candidate", "undetermined", "ambiguous"}:
        reasons.add("activation_semantics")
    if any(
        path.actual_damage_ids or path.unknown_damage_ids or path.unresolved_damage_ids
        for path in pattern.paths
    ):
        reasons.add("damage_binding")
    if any(
        path.resolved_damage_ids
        or path.active_rescue_ids
        or path.invalidated_rescue_ids
        for path in pattern.paths
    ):
        reasons.add("rescue_binding")
    if pattern.pattern_id in pattern_set.suppressed_pattern_ids or any(
        path.superseded_by_rule_ids for path in pattern.paths
    ):
        reasons.add("source_precedence")
    return reasons


def _canonical_pattern_comparisons(
    *,
    pattern_set: PatternSetResult,
    legacy_result: Mapping[str, Any],
    uncertain_envelope: bool,
) -> list[dict[str, Any]]:
    """Compare every canonical result with the matching live legacy status."""

    legacy_by_id, duplicate_ids = _legacy_patterns_by_id(legacy_result)
    comparisons: list[dict[str, Any]] = []
    for pattern in pattern_set.patterns:
        legacy = legacy_by_id.get(pattern.pattern_id)
        if pattern.pattern_id in duplicate_ids:
            legacy_status = "duplicate"
        elif legacy is None:
            legacy_status = "missing"
        else:
            value = legacy.get("status")
            legacy_status = value if isinstance(value, str) and value else "invalid"

        is_difference = (
            uncertain_envelope
            or legacy_status in {"duplicate", "missing", "invalid"}
            or _normalized_pattern_status(legacy_status)
            != _normalized_pattern_status(pattern.status)
        )
        reasons: set[str] = set()
        if is_difference:
            if uncertain_envelope:
                # The canonical result is a reduction across candidate worlds,
                # while the legacy payload is a single representative chart.
                reasons.add("scope_gap")
            if legacy_status in {"duplicate", "missing", "invalid"}:
                reasons.add("defect")
            reasons.update(_canonical_structural_diff_reasons(pattern, pattern_set))
            if not reasons:
                # Only after candidate/path/precedence mechanics have been
                # exhausted may the old heuristic thresholds explain the gap.
                reasons.add("legacy_thresholds_shares")

        comparisons.append(
            {
                "pattern_id": pattern.pattern_id,
                "canonical_status": pattern.status,
                "legacy_status": legacy_status,
                "is_difference": is_difference,
                "reasons": [
                    reason for reason in SHADOW_DIFF_REASONS if reason in reasons
                ],
            }
        )
    return comparisons


def _classified_diffs(
    *,
    generic_result: Any,
    legacy_status: str,
    attestation_count: int,
    uncertain_envelope: bool,
) -> list[str]:
    reasons: set[str] = set()
    if uncertain_envelope:
        reasons.add("scope_gap")
    if generic_result.candidate is TruthValue.UNKNOWN:
        reasons.add("candidate_scope")
    elif generic_result.status == "undetermined":
        reasons.add("activation_semantics")
    paths = tuple(generic_result.paths)
    if any(item.actual_damage_ids for item in paths):
        reasons.add("damage_binding")
    if any(item.resolved_damage_ids or item.active_rescue_ids for item in paths):
        reasons.add("rescue_binding")
    if any(item.superseded_by_rule_ids for item in paths):
        reasons.add("source_precedence")
    if attestation_count:
        reasons.add("attestation_only")
    if (
        not uncertain_envelope
        and legacy_status != generic_result.status
        and not reasons
    ):
        reasons.add("legacy_thresholds_shares")
    return [item for item in SHADOW_DIFF_REASONS if item in reasons]


def build_source_backed_shadow(
    pillars: Sequence[Mapping[str, Any]],
    legacy_result: Mapping[str, Any],
    graph: BaziFactGraph | BaziFactEnvelope,
    *,
    include_attestations: bool = True,
) -> dict[str, Any]:
    """Evaluate the source-backed registry without changing legacy authority."""

    if not isinstance(graph, (BaziFactGraph, BaziFactEnvelope)):
        raise TypeError("graph must be BaziFactGraph or BaziFactEnvelope")
    if pillars and isinstance(graph, BaziFactEnvelope):
        raise ValueError("nonempty pillars require a single BaziFactGraph")
    if pillars and not fact_graph_matches_pillars(pillars, graph):
        raise ValueError("fact graph does not describe supplied pillars")
    context = build_rule_evaluation_context(graph)
    compatibility_registry = load_packaged_task4_shadow_registry()
    canonical_registry = load_packaged_shen_registry()
    generic = evaluate_pattern_lifecycle(context, compatibility_registry)
    pattern_set = evaluate_pattern_set(
        context,
        canonical_registry,
    )
    uncertain = isinstance(graph, BaziFactEnvelope)
    attestations = (
        evaluate_example_attestations(pillars)
        if include_attestations and not uncertain
        else []
    )
    legacy_status = (
        "hour_uncertain" if uncertain else _legacy_direct_officer_status(legacy_result)
    )
    pattern_comparisons = _canonical_pattern_comparisons(
        pattern_set=pattern_set,
        legacy_result=legacy_result,
        uncertain_envelope=uncertain,
    )
    compatibility_reasons = _classified_diffs(
        generic_result=generic,
        legacy_status=legacy_status,
        attestation_count=len(attestations),
        uncertain_envelope=uncertain,
    )
    canonical_reasons = {
        reason
        for comparison in pattern_comparisons
        if comparison["is_difference"]
        for reason in comparison["reasons"]
    }
    aggregate_reasons = [
        reason
        for reason in SHADOW_DIFF_REASONS
        if reason in set(compatibility_reasons) | canonical_reasons
    ]
    result = {
        "mode": "shadow",
        "authoritative": False,
        "bundle_id": compatibility_registry.bundle_id,
        "bundle_digest": compatibility_registry.bundle_digest,
        "generic_result": generic.as_dict(),
        "example_attestations": attestations,
        "legacy_status": legacy_status,
        "diff": {
            "reasons": aggregate_reasons,
            "compared_pattern_count": len(pattern_comparisons),
            "pattern_comparisons": pattern_comparisons,
            "unclassified_count": sum(
                not comparison["reasons"] or "unclassified" in comparison["reasons"]
                for comparison in pattern_comparisons
                if comparison["is_difference"]
            ),
        },
    }
    result["pattern_set"] = pattern_set.as_dict()
    result["overlay_results"] = []
    return result


def canonical_authority_from_shadow(shadow: Mapping[str, Any]) -> dict[str, Any]:
    """Promote the reviewed pattern set while retaining legacy diagnostics.

    ``generic_result`` remains a compatibility probe, but the independently
    compiled Shen pattern set is the only production authority exposed here.
    """

    pattern_set = shadow.get("pattern_set")
    if not isinstance(pattern_set, Mapping):
        raise ValueError("source-backed shadow is missing its canonical pattern set")
    return {
        "mode": "canonical",
        "authoritative": True,
        "bundle_id": str(pattern_set.get("bundle_id", "")),
        "bundle_digest": str(pattern_set.get("bundle_digest", "")),
        "authority_layer": str(pattern_set.get("authority_layer", "")),
        "pattern_set": dict(pattern_set),
    }


__all__ = [
    "SHADOW_DIFF_REASONS",
    "build_source_backed_shadow",
    "canonical_authority_from_shadow",
    "evaluate_example_attestations",
    "fact_graph_matches_pillars",
]
