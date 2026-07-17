"""Independent classical authority layers that never merge their results."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
from typing import Any, Literal, Mapping, Sequence

from iching.core.bazi_rules.predicates import predicate_to_canonical_data
from iching.core.bazi_rules.registry import (
    RuleRegistry,
    load_packaged_shen_registry,
    registry_from_data,
)


OVERLAY_DESCRIPTOR_VERSION = "bazi-overlay-descriptor-v1"
OverlayRelationKind = Literal[
    "agrees",
    "adds_condition",
    "disagrees",
    "different_terminology",
]
_RELATION_KINDS = frozenset(
    ("agrees", "adds_condition", "disagrees", "different_terminology")
)
_OVERLAY_RESOURCES = {
    "xu_commentary": "zzq-xu-commentary-v1.json",
    "yuanhai": "yuanhai-ziping-v1.json",
}


def _identifier(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-blank string")
    return value


def _identifiers(value: Any, field_name: str) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ValueError(f"{field_name} must be a list of strings")
    result = tuple(_identifier(item, field_name) for item in value)
    if not result or len(set(result)) != len(result):
        raise ValueError(f"{field_name} must be a non-empty unique list")
    return tuple(sorted(result))


@dataclass(frozen=True)
class OverlayRelation:
    id: str
    kind: OverlayRelationKind | str
    pattern_id: str
    overlay_rule_ids: tuple[str, ...]
    canonical_rule_ids: tuple[str, ...]
    canonical_term: str | None = None
    overlay_term: str | None = None
    semantic_delta: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _identifier(self.id, "relation id"))
        if self.kind not in _RELATION_KINDS:
            raise ValueError(f"unsupported overlay relation kind: {self.kind!r}")
        object.__setattr__(
            self,
            "pattern_id",
            _identifier(self.pattern_id, "relation pattern_id"),
        )
        object.__setattr__(
            self,
            "overlay_rule_ids",
            _identifiers(self.overlay_rule_ids, "overlay_rule_ids"),
        )
        object.__setattr__(
            self,
            "canonical_rule_ids",
            _identifiers(self.canonical_rule_ids, "canonical_rule_ids"),
        )
        terminology = self.kind == "different_terminology"
        if terminology:
            object.__setattr__(
                self,
                "canonical_term",
                _identifier(self.canonical_term, "canonical_term"),
            )
            object.__setattr__(
                self,
                "overlay_term",
                _identifier(self.overlay_term, "overlay_term"),
            )
        elif self.canonical_term is not None or self.overlay_term is not None:
            raise ValueError("terminology fields require different_terminology")
        if self.kind == "disagrees":
            object.__setattr__(
                self,
                "semantic_delta",
                _identifier(self.semantic_delta, "semantic_delta"),
            )
        elif self.semantic_delta is not None:
            raise ValueError("semantic_delta requires disagrees")

    def canonical_data(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "pattern_id": self.pattern_id,
            "overlay_rule_ids": list(self.overlay_rule_ids),
            "canonical_rule_ids": list(self.canonical_rule_ids),
            "canonical_term": self.canonical_term,
            "overlay_term": self.overlay_term,
            "semantic_delta": self.semantic_delta,
        }


def _binding(rule: Any) -> tuple[Any, ...]:
    return (
        rule.pattern_id,
        rule.stage,
        rule.effect,
        rule.path_id,
        rule.targets_path_ids,
        rule.resolves_damage_ids,
        rule.invalidates_rescue_ids,
        rule.supersedes_path_ids,
    )


def _is_narrower_predicate(overlay_rule: Any, canonical_rule: Any) -> bool:
    overlay = predicate_to_canonical_data(overlay_rule.predicate)
    canonical = predicate_to_canonical_data(canonical_rule.predicate)
    if overlay == canonical or overlay.get("op") != "all":
        return False
    children = overlay.get("children")
    return isinstance(children, list) and canonical in children and len(children) > 1


@dataclass(frozen=True)
class OverlayDescriptor:
    authority_layer: Literal["xu_commentary", "yuanhai"] | str
    availability: Literal["available", "partial", "unavailable"] | str
    base_bundle_id: str
    base_bundle_digest: str
    registry: RuleRegistry | None
    relations: tuple[OverlayRelation, ...]
    unavailable_reason: str | None = None

    def __post_init__(self) -> None:
        if self.authority_layer not in _OVERLAY_RESOURCES:
            raise ValueError(f"unsupported overlay layer: {self.authority_layer!r}")
        if self.availability not in {"available", "partial", "unavailable"}:
            raise ValueError(f"unsupported overlay availability: {self.availability!r}")
        object.__setattr__(
            self,
            "base_bundle_id",
            _identifier(self.base_bundle_id, "base_bundle_id"),
        )
        digest = self.base_bundle_digest
        if (
            not isinstance(digest, str)
            or len(digest) != 64
            or any(char not in "0123456789abcdef" for char in digest)
        ):
            raise ValueError("base_bundle_digest must be a lowercase SHA-256 digest")
        relations = tuple(sorted(self.relations, key=lambda item: item.id))
        if any(not isinstance(item, OverlayRelation) for item in relations):
            raise TypeError("relations must contain OverlayRelation records")
        if len({item.id for item in relations}) != len(relations):
            raise ValueError("overlay contains duplicate relation IDs")
        object.__setattr__(self, "relations", relations)
        if self.availability == "unavailable":
            if self.registry is not None or relations:
                raise ValueError("unavailable overlay cannot contain executable rules")
            object.__setattr__(
                self,
                "unavailable_reason",
                _identifier(self.unavailable_reason, "unavailable_reason"),
            )
        else:
            if not isinstance(self.registry, RuleRegistry):
                raise ValueError("available overlay requires an independent registry")
            if self.unavailable_reason is not None:
                raise ValueError("available overlay cannot declare unavailable_reason")
            if self.registry.authority_layer != self.authority_layer:
                raise ValueError("overlay registry authority layer mismatch")

    def validate_against(self, canonical: RuleRegistry) -> None:
        if canonical.authority_layer != "shen_core":
            raise ValueError("canonical registry must use shen_core authority")
        if self.base_bundle_id != canonical.bundle_id:
            raise ValueError("overlay base bundle ID does not match canonical bundle")
        if self.base_bundle_digest != canonical.bundle_digest:
            raise ValueError(
                "overlay base bundle digest does not match canonical bundle"
            )
        if self.availability == "unavailable":
            return
        assert self.registry is not None
        canonical_rules = canonical.rules_by_id
        overlay_rules = self.registry.rules_by_id
        referenced: list[str] = []
        for relation in self.relations:
            for rule_id in relation.overlay_rule_ids:
                if rule_id not in overlay_rules:
                    raise ValueError(
                        f"overlay relation references unknown rule {rule_id}"
                    )
                referenced.append(rule_id)
            for rule_id in relation.canonical_rule_ids:
                if rule_id not in canonical_rules:
                    raise ValueError(
                        f"overlay relation references unknown canonical rule {rule_id}"
                    )
            for overlay_id in relation.overlay_rule_ids:
                overlay_rule = overlay_rules[overlay_id]
                if overlay_rule.pattern_id != relation.pattern_id:
                    raise ValueError("overlay relation pattern binding mismatch")
                for canonical_id in relation.canonical_rule_ids:
                    canonical_rule = canonical_rules[canonical_id]
                    if canonical_rule.pattern_id != relation.pattern_id:
                        raise ValueError("canonical relation pattern binding mismatch")
                    if relation.kind in {"agrees", "different_terminology"}:
                        if _binding(overlay_rule) != _binding(canonical_rule):
                            raise ValueError(
                                f"{relation.kind} requires matching lifecycle binding"
                            )
                        if predicate_to_canonical_data(
                            overlay_rule.predicate
                        ) != predicate_to_canonical_data(canonical_rule.predicate):
                            raise ValueError(
                                f"{relation.kind} requires matching predicate"
                            )
                    elif relation.kind == "adds_condition":
                        if _binding(overlay_rule) != _binding(canonical_rule):
                            raise ValueError(
                                "adds_condition requires matching lifecycle binding"
                            )
                        if not _is_narrower_predicate(overlay_rule, canonical_rule):
                            raise ValueError(
                                "adds_condition predicate must include the canonical "
                                "predicate plus an explicit condition"
                            )
                    elif relation.kind == "disagrees":
                        same_binding = _binding(overlay_rule) == _binding(
                            canonical_rule
                        )
                        same_predicate = predicate_to_canonical_data(
                            overlay_rule.predicate
                        ) == predicate_to_canonical_data(canonical_rule.predicate)
                        if same_binding and same_predicate:
                            raise ValueError(
                                "disagrees requires a real semantic delta"
                            )
        if set(referenced) != set(overlay_rules) or len(referenced) != len(
            set(referenced)
        ):
            raise ValueError(
                "every executable overlay rule must be referenced exactly once"
            )


@dataclass(frozen=True)
class ClassicalAuthoritySet:
    canonical: RuleRegistry
    overlays: tuple[OverlayDescriptor, ...]

    def __post_init__(self) -> None:
        if self.canonical.authority_layer != "shen_core":
            raise ValueError("default classical authority must be shen_core")
        overlays = tuple(sorted(self.overlays, key=lambda item: item.authority_layer))
        if len({item.authority_layer for item in overlays}) != len(overlays):
            raise ValueError("classical authority set contains duplicate overlays")
        for overlay in overlays:
            overlay.validate_against(self.canonical)
        object.__setattr__(self, "overlays", overlays)


def _strict_object(
    value: Any,
    *,
    fields: frozenset[str],
    required: frozenset[str] | None = None,
    field_name: str,
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field_name} must be an object")
    extras = set(value) - set(fields)
    missing = set(required if required is not None else fields) - set(value)
    if extras or missing:
        raise ValueError(
            f"{field_name} fields mismatch: allowed={sorted(fields)}, "
            f"required={sorted(required if required is not None else fields)}, "
            f"actual={sorted(value)}"
        )
    return value


def overlay_descriptor_from_data(payload: Mapping[str, Any]) -> OverlayDescriptor:
    fields = frozenset(
        (
            "overlay_descriptor_version",
            "authority_layer",
            "availability",
            "base_bundle_id",
            "base_bundle_digest",
            "registry",
            "relations",
            "unavailable_reason",
        )
    )
    raw = _strict_object(payload, fields=fields, field_name="overlay descriptor")
    if raw["overlay_descriptor_version"] != OVERLAY_DESCRIPTOR_VERSION:
        raise ValueError("unsupported overlay_descriptor_version")
    relation_fields = frozenset(
        (
            "id",
            "kind",
            "pattern_id",
            "overlay_rule_ids",
            "canonical_rule_ids",
            "canonical_term",
            "overlay_term",
            "semantic_delta",
        )
    )
    relations_raw = raw["relations"]
    if isinstance(relations_raw, (str, bytes)) or not isinstance(
        relations_raw, Sequence
    ):
        raise ValueError("relations must be an array")
    relations = tuple(
        OverlayRelation(
            **dict(
                _strict_object(
                    item,
                    fields=relation_fields,
                    required=relation_fields - {"semantic_delta"},
                    field_name=f"relations[{index}]",
                )
            )
        )
        for index, item in enumerate(relations_raw)
    )
    registry_raw = raw["registry"]
    registry = None if registry_raw is None else registry_from_data(registry_raw)
    return OverlayDescriptor(
        authority_layer=raw["authority_layer"],
        availability=raw["availability"],
        base_bundle_id=raw["base_bundle_id"],
        base_bundle_digest=raw["base_bundle_digest"],
        registry=registry,
        relations=relations,
        unavailable_reason=raw["unavailable_reason"],
    )


@lru_cache(maxsize=2)
def load_packaged_overlay(layer: str) -> OverlayDescriptor:
    if layer not in _OVERLAY_RESOURCES:
        raise ValueError(f"unsupported overlay layer: {layer!r}")
    resource = resources.files("iching.core.bazi_rules").joinpath(
        "bundles", _OVERLAY_RESOURCES[layer]
    )
    if not resource.is_file():
        raise ValueError(f"packaged overlay resource is unavailable for {layer}")
    payload = json.loads(resource.read_text(encoding="utf-8"))
    descriptor = overlay_descriptor_from_data(payload)
    if descriptor.authority_layer != layer:
        raise ValueError("packaged overlay resource authority layer mismatch")
    descriptor.validate_against(load_packaged_shen_registry())
    return descriptor


@lru_cache(maxsize=1)
def load_packaged_classical_authorities() -> ClassicalAuthoritySet:
    canonical = load_packaged_shen_registry()
    return ClassicalAuthoritySet(
        canonical=canonical,
        overlays=(
            load_packaged_overlay("xu_commentary"),
            load_packaged_overlay("yuanhai"),
        ),
    )


__all__ = [
    "ClassicalAuthoritySet",
    "OVERLAY_DESCRIPTOR_VERSION",
    "OverlayDescriptor",
    "OverlayRelation",
    "OverlayRelationKind",
    "load_packaged_classical_authorities",
    "load_packaged_overlay",
    "overlay_descriptor_from_data",
]
