"""Shadow-only adapter between source-backed lifecycle data and legacy consumers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from iching.core.bazi_rules.engine import (
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
    result = {
        "mode": "shadow",
        "authoritative": False,
        "bundle_id": compatibility_registry.bundle_id,
        "bundle_digest": compatibility_registry.bundle_digest,
        "generic_result": generic.as_dict(),
        "example_attestations": attestations,
        "legacy_status": legacy_status,
        "diff": {
            "reasons": _classified_diffs(
                generic_result=generic,
                legacy_status=legacy_status,
                attestation_count=len(attestations),
                uncertain_envelope=uncertain,
            )
        },
    }
    result["pattern_set"] = pattern_set.as_dict()
    result["overlay_results"] = []
    return result


__all__ = [
    "SHADOW_DIFF_REASONS",
    "build_source_backed_shadow",
    "evaluate_example_attestations",
    "fact_graph_matches_pillars",
]
