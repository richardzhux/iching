"""Typed, closed registry contracts for pattern lifecycle rules."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from functools import lru_cache
from importlib import resources
from pathlib import Path
from types import MappingProxyType
from typing import Any

from iching.core.bazi_rules.compiler import (
    PRODUCTION_PROPOSITION_TYPES,
    PRODUCTION_RIGHTS_STATUSES,
    PRODUCTION_SEGMENT_TYPES,
    canonical_digest,
    compile_rule_records,
    load_hydrated_propositions,
)
from iching.core.bazi_rules.predicates import (
    parse_predicate,
    predicate_to_canonical_data,
)
from iching.core.bazi_rules.primitives import BRANCHES, STEMS
from iching.core.bazi_rules.schema import PredicateNode, Proposition


REGISTRY_VERSION = "bazi-rule-registry-v1"
ATTESTATION_BUNDLE_VERSION = "bazi-example-attestations-v1"
LIFECYCLE_STAGES = (
    "candidate",
    "formation",
    "damage",
    "rescue",
    "purity",
    "transformation",
    "special_gate",
    "resolution",
)
_STAGE_INDEX = {stage: index for index, stage in enumerate(LIFECYCLE_STAGES)}
_EXECUTABLE_STAGE_EFFECTS: Mapping[str, frozenset[str]] = MappingProxyType(
    {
        "formation": frozenset(("formation",)),
        "damage": frozenset(
            ("damage", "officer_killing_mixture", "rescue_invalidation")
        ),
        "rescue": frozenset(("rescue",)),
        "transformation": frozenset(("transformation",)),
        "special_gate": frozenset(("require", "reject")),
        "resolution": frozenset(("source_precedence",)),
    }
)
_AUTHORITY_LAYERS = frozenset(("shen_core", "xu_commentary", "yuanhai", "synthetic"))
_METADATA_KEYS = frozenset(
    (
        "stage",
        "pattern_id",
        "path_id",
        "targets_path_ids",
        "resolves_damage_ids",
        "invalidates_rescue_ids",
        "supersedes_path_ids",
        "authority_layer",
        "source_ids",
    )
)
_RULE_DEFINITION_KEYS = frozenset(
    (
        "id",
        "proposition_id",
        "predicate",
        "effect",
        "resolution_slot",
        "precedence",
        "after",
        "before",
        "execution_ready",
        "production_eligible",
        "semantic_status",
        "metadata",
    )
)


def _identifier(value: Any, field_name: str, *, optional: bool = False) -> str | None:
    if value is None and optional:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-blank string")
    return value


def _identifiers(value: Any, field_name: str) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ValueError(f"{field_name} must be a list of strings")
    result = tuple(_identifier(item, field_name) for item in value)
    if len(set(result)) != len(result):
        raise ValueError(f"{field_name} contains duplicates")
    return tuple(sorted(str(item) for item in result))


def _ordered_strings(value: Any, field_name: str) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ValueError(f"{field_name} must be a list of strings")
    return tuple(str(_identifier(item, field_name)) for item in value)


def _looks_like_attestation(source_id: str) -> bool:
    return (
        source_id.startswith("attestation.")
        or ".attestation." in source_id
        or ".example." in source_id
        or ".example-" in source_id
    )


def _valid_pillar_text(value: str) -> bool:
    return (
        len(value) == 2
        and value[0] in STEMS
        and value[1] in BRANCHES
        and STEMS.index(value[0]) % 2 == BRANCHES.index(value[1]) % 2
    )


def _valid_digest(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _closed_object(
    value: Any,
    *,
    field_name: str,
    allowed: frozenset[str],
    required: frozenset[str] | None = None,
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field_name} must be an object")
    extras = set(value) - set(allowed)
    if extras:
        raise ValueError(f"{field_name} has unknown fields: {sorted(extras)}")
    missing = set(required or allowed) - set(value)
    if missing:
        raise ValueError(f"{field_name} is missing fields: {sorted(missing)}")
    return value


def _records(value: Any, field_name: str) -> tuple[Mapping[str, Any], ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ValueError(f"{field_name} must be an array of objects")
    result = tuple(value)
    if any(not isinstance(item, Mapping) for item in result):
        raise ValueError(f"{field_name} must be an array of objects")
    return result


def _load_json_resource(name: str) -> Mapping[str, Any]:
    package = resources.files("iching.core.bazi_rules")
    payload = json.loads(package.joinpath("bundles", name).read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"packaged bundle {name} must contain an object")
    return payload


def _load_jsonl(path: Path) -> tuple[Mapping[str, Any], ...]:
    records: list[Mapping[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                raise ValueError(f"blank JSONL line: {path}:{line_number}")
            value = json.loads(line)
            if not isinstance(value, Mapping):
                raise ValueError(
                    f"JSONL record must be an object: {path}:{line_number}"
                )
            records.append(value)
    return tuple(records)


@dataclass(frozen=True)
class RegistrySourceSegment:
    id: str
    layer: str
    text_type: str
    review_state: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _identifier(self.id, "source segment id"))
        if self.layer != "shen_core":
            raise ValueError("production provenance requires shen_core segments")
        if self.text_type not in PRODUCTION_SEGMENT_TYPES:
            raise ValueError("production provenance has unsupported segment type")
        if self.review_state != "scan_verified":
            raise ValueError("production provenance has unverified segment")

    def canonical_data(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "layer": self.layer,
            "text_type": self.text_type,
            "review_state": self.review_state,
        }


@dataclass(frozen=True)
class RegistrySupportLocator:
    id: str
    review_state: str
    visually_verified: bool
    witness_id: str
    witness_rights_status: str
    witness_production_allowed: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _identifier(self.id, "support locator id"))
        object.__setattr__(
            self,
            "witness_id",
            _identifier(self.witness_id, "support witness id"),
        )
        if self.review_state != "scan_verified" or self.visually_verified is not True:
            raise ValueError("production provenance has unverified support locator")
        if (
            self.witness_rights_status not in PRODUCTION_RIGHTS_STATUSES
            or self.witness_production_allowed is not True
        ):
            raise ValueError("production provenance has rights-ineligible witness")

    def canonical_data(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "review_state": self.review_state,
            "visually_verified": True,
            "witness_id": self.witness_id,
            "witness_rights_status": self.witness_rights_status,
            "witness_production_allowed": True,
        }


@dataclass(frozen=True)
class RegistrySourceProvenance:
    proposition_id: str
    layer: str
    text_type: str
    production_eligible: bool
    review_state: str
    source_manifest_digest: str
    corpus_manifest_digest: str
    corpus_artifact_digest: str
    segments: tuple[RegistrySourceSegment, ...]
    support_locators: tuple[RegistrySupportLocator, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "proposition_id",
            _identifier(self.proposition_id, "provenance proposition_id"),
        )
        if (
            self.layer != "shen_core"
            or self.text_type not in PRODUCTION_PROPOSITION_TYPES
            or self.production_eligible is not True
            or self.review_state != "scan_verified"
        ):
            raise ValueError("source is not verified production provenance")
        for field_name in (
            "source_manifest_digest",
            "corpus_manifest_digest",
            "corpus_artifact_digest",
        ):
            if not _valid_digest(getattr(self, field_name)):
                raise ValueError(f"{field_name} must be a lowercase SHA-256 digest")
        segments = tuple(self.segments)
        support_locators = tuple(self.support_locators)
        if not segments or any(
            not isinstance(item, RegistrySourceSegment) for item in segments
        ):
            raise ValueError("production provenance requires source segments")
        if not support_locators or any(
            not isinstance(item, RegistrySupportLocator) for item in support_locators
        ):
            raise ValueError("production provenance requires support locators")
        if len({item.id for item in segments}) != len(segments):
            raise ValueError("production provenance has duplicate source segments")
        if len({item.id for item in support_locators}) != len(support_locators):
            raise ValueError("production provenance has duplicate support locators")
        object.__setattr__(
            self,
            "segments",
            tuple(sorted(segments, key=lambda item: item.id)),
        )
        object.__setattr__(
            self,
            "support_locators",
            tuple(sorted(support_locators, key=lambda item: item.id)),
        )

    def canonical_data(self) -> dict[str, Any]:
        return {
            "proposition_id": self.proposition_id,
            "layer": self.layer,
            "text_type": self.text_type,
            "production_eligible": True,
            "review_state": self.review_state,
            "source_manifest_digest": self.source_manifest_digest,
            "corpus_manifest_digest": self.corpus_manifest_digest,
            "corpus_artifact_digest": self.corpus_artifact_digest,
            "segments": [item.canonical_data() for item in self.segments],
            "support_locators": [
                item.canonical_data() for item in self.support_locators
            ],
        }


def _source_provenance(proposition: Proposition) -> RegistrySourceProvenance:
    witnesses = {item.id: item for item in proposition.witnesses}
    return RegistrySourceProvenance(
        proposition_id=proposition.id,
        layer=proposition.layer,
        text_type=proposition.text_type,
        production_eligible=proposition.production_eligible,
        review_state=proposition.review_state,
        source_manifest_digest=proposition.source_manifest_digest,
        corpus_manifest_digest=proposition.corpus_manifest_digest,
        corpus_artifact_digest=proposition.corpus_artifact_digest,
        segments=tuple(
            RegistrySourceSegment(
                id=item.id,
                layer=item.layer,
                text_type=item.text_type,
                review_state=item.review_state,
            )
            for item in proposition.segments
        ),
        support_locators=tuple(
            RegistrySupportLocator(
                id=item.id,
                review_state=item.review_state,
                visually_verified=item.visually_verified,
                witness_id=item.witness_id,
                witness_rights_status=witnesses[item.witness_id].rights_status,
                witness_production_allowed=witnesses[
                    item.witness_id
                ].production_use_allowed,
            )
            for item in proposition.locators
        ),
    )


@dataclass(frozen=True)
class RegistryExclusion:
    candidate_id: str
    reason: str
    source_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "candidate_id", _identifier(self.candidate_id, "candidate_id")
        )
        object.__setattr__(self, "reason", _identifier(self.reason, "exclusion reason"))
        source_ids = _identifiers(self.source_ids, "source_ids")
        if not source_ids:
            raise ValueError("registry exclusion requires source_ids")
        object.__setattr__(self, "source_ids", source_ids)

    def canonical_data(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "reason": self.reason,
            "source_ids": list(self.source_ids),
        }


@dataclass(frozen=True)
class ExampleAttestation:
    id: str
    pillars: tuple[str, ...]
    mechanisms: tuple[str, ...]
    explanation: str
    source_ids: tuple[str, ...]
    affects_canonical_status: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _identifier(self.id, "attestation id"))
        pillars = _ordered_strings(self.pillars, "attestation pillars")
        if len(pillars) != 4 or any(not _valid_pillar_text(item) for item in pillars):
            raise ValueError(
                "attestation pillars must be an exact four-pillar signature"
            )
        object.__setattr__(self, "pillars", pillars)
        mechanisms = _ordered_strings(self.mechanisms, "attestation mechanisms")
        if not mechanisms:
            raise ValueError("attestation mechanisms cannot be empty")
        object.__setattr__(self, "mechanisms", mechanisms)
        object.__setattr__(
            self,
            "explanation",
            _identifier(self.explanation, "attestation explanation"),
        )
        source_ids = _identifiers(self.source_ids, "attestation source_ids")
        if not source_ids:
            raise ValueError("attestation requires source_ids")
        object.__setattr__(self, "source_ids", source_ids)
        if (
            type(self.affects_canonical_status) is not bool
            or self.affects_canonical_status
        ):
            raise ValueError("affects_canonical_status must be literal false")

    def canonical_data(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "pillars": list(self.pillars),
            "mechanisms": list(self.mechanisms),
            "explanation": self.explanation,
            "source_ids": list(self.source_ids),
            "affects_canonical_status": False,
        }


@dataclass(frozen=True)
class ExampleAttestationBundle:
    bundle_id: str
    generic_bundle_id: str
    attestations: tuple[ExampleAttestation, ...]
    bundle_digest: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.bundle_digest, str):
            raise ValueError("attestation bundle_digest must be a string")
        object.__setattr__(self, "bundle_id", _identifier(self.bundle_id, "bundle_id"))
        object.__setattr__(
            self,
            "generic_bundle_id",
            _identifier(self.generic_bundle_id, "generic_bundle_id"),
        )
        attestations = tuple(self.attestations)
        if any(not isinstance(item, ExampleAttestation) for item in attestations):
            raise TypeError("attestations must be ExampleAttestation records")
        by_id = {item.id: item for item in attestations}
        if len(by_id) != len(attestations):
            raise ValueError("attestation bundle contains duplicate IDs")
        object.__setattr__(
            self,
            "attestations",
            tuple(by_id[item_id] for item_id in sorted(by_id)),
        )
        expected = canonical_digest(
            {
                "attestation_bundle_version": ATTESTATION_BUNDLE_VERSION,
                "bundle_id": self.bundle_id,
                "generic_bundle_id": self.generic_bundle_id,
                "attestations": [item.canonical_data() for item in self.attestations],
            }
        )
        if self.bundle_digest and self.bundle_digest != expected:
            raise ValueError(
                "attestation bundle_digest does not match semantic content"
            )
        object.__setattr__(self, "bundle_digest", expected)


@dataclass(frozen=True)
class RegistryRule:
    id: str
    stage: str
    pattern_id: str
    predicate: PredicateNode | Mapping[str, Any]
    effect: str
    path_id: str | None = None
    targets_path_ids: tuple[str, ...] = ()
    resolves_damage_ids: tuple[str, ...] = ()
    invalidates_rescue_ids: tuple[str, ...] = ()
    supersedes_path_ids: tuple[str, ...] = ()
    authority_layer: str = "shen_core"
    source_ids: tuple[str, ...] = ()
    precedence: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _identifier(self.id, "rule id"))
        if self.stage not in _STAGE_INDEX:
            raise ValueError(f"unresolved lifecycle stage: {self.stage!r}")
        if self.stage not in _EXECUTABLE_STAGE_EFFECTS:
            raise ValueError(
                f"unsupported executable stage: {self.stage}; "
                "the registry has no closed reducer contract for this stage"
            )
        object.__setattr__(
            self, "pattern_id", _identifier(self.pattern_id, "pattern_id")
        )
        object.__setattr__(self, "effect", _identifier(self.effect, "rule effect"))
        if self.effect not in _EXECUTABLE_STAGE_EFFECTS[self.stage]:
            raise ValueError(
                f"unsupported stage/effect combination: {self.stage}/{self.effect}"
            )
        object.__setattr__(
            self, "path_id", _identifier(self.path_id, "path_id", optional=True)
        )
        for field_name in (
            "targets_path_ids",
            "resolves_damage_ids",
            "invalidates_rescue_ids",
            "supersedes_path_ids",
            "source_ids",
        ):
            object.__setattr__(
                self,
                field_name,
                _identifiers(getattr(self, field_name), field_name),
            )
        if self.stage in {"transformation", "special_gate"}:
            binding_count = int(self.path_id is not None) + int(
                bool(self.targets_path_ids)
            )
            if binding_count != 1:
                raise ValueError(
                    f"terminal rule {self.id} requires exactly one formation path binding"
                )
            if (
                self.resolves_damage_ids
                or self.invalidates_rescue_ids
                or self.supersedes_path_ids
            ):
                raise ValueError(
                    f"terminal rule {self.id} cannot declare lifecycle side effects"
                )
        if self.stage == "formation" and self.path_id is None:
            raise ValueError(f"formation rule {self.id} requires path_id")
        if self.stage == "rescue" and not self.resolves_damage_ids:
            raise ValueError(f"rescue rule {self.id} requires declared damage")
        if self.effect == "rescue_invalidation" and not self.invalidates_rescue_ids:
            raise ValueError(
                f"rescue invalidation rule {self.id} requires invalidates_rescue_ids"
            )
        if self.stage == "resolution":
            if self.path_id is None:
                raise ValueError(f"source precedence rule {self.id} requires path_id")
            if not self.supersedes_path_ids:
                raise ValueError(
                    f"source precedence rule {self.id} requires supersedes_path_ids"
                )
        if self.resolves_damage_ids and self.stage != "rescue":
            raise ValueError("only rescue rules may declare resolved damage")
        if self.authority_layer not in _AUTHORITY_LAYERS:
            raise ValueError(f"unknown authority layer: {self.authority_layer!r}")
        if not self.source_ids:
            raise ValueError(f"rule {self.id} requires source_ids")
        if any(_looks_like_attestation(source_id) for source_id in self.source_ids):
            raise ValueError(f"generic rule {self.id} depends on an attestation")
        if type(self.precedence) is not int:
            raise ValueError("registry precedence must be an integer")
        object.__setattr__(self, "predicate", parse_predicate(self.predicate))

    def canonical_data(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "stage": self.stage,
            "pattern_id": self.pattern_id,
            "predicate": predicate_to_canonical_data(self.predicate),
            "effect": self.effect,
            "path_id": self.path_id,
            "targets_path_ids": list(self.targets_path_ids),
            "resolves_damage_ids": list(self.resolves_damage_ids),
            "invalidates_rescue_ids": list(self.invalidates_rescue_ids),
            "supersedes_path_ids": list(self.supersedes_path_ids),
            "authority_layer": self.authority_layer,
            "source_ids": list(self.source_ids),
            "precedence": self.precedence,
        }


@dataclass(frozen=True)
class RuleRegistry:
    bundle_id: str
    rules: tuple[RegistryRule, ...]
    bundle_digest: str = ""
    source_bundle_digest: str = ""
    exclusions: tuple[RegistryExclusion, ...] = ()
    source_provenance: tuple[RegistrySourceProvenance, ...] = ()
    source_provenance_digest: str = ""
    rules_by_id: Mapping[str, RegistryRule] = field(
        init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        if not isinstance(self.bundle_digest, str):
            raise ValueError("registry bundle_digest must be a string")
        if not isinstance(self.source_bundle_digest, str):
            raise ValueError("source_bundle_digest must be a string")
        if not isinstance(self.source_provenance_digest, str):
            raise ValueError("source_provenance_digest must be a string")
        object.__setattr__(self, "bundle_id", _identifier(self.bundle_id, "bundle_id"))
        rules = tuple(self.rules)
        if any(not isinstance(item, RegistryRule) for item in rules):
            raise TypeError("registry rules must be RegistryRule records")
        by_id = {item.id: item for item in rules}
        if len(by_id) != len(rules):
            raise ValueError("registry contains duplicate rule IDs")
        exclusions = tuple(self.exclusions)
        if any(not isinstance(item, RegistryExclusion) for item in exclusions):
            raise TypeError("registry exclusions must be RegistryExclusion records")
        if len({item.candidate_id for item in exclusions}) != len(exclusions):
            raise ValueError("registry contains duplicate exclusion candidate IDs")
        if self.source_bundle_digest and not _valid_digest(self.source_bundle_digest):
            raise ValueError("source_bundle_digest must be a lowercase SHA-256 digest")
        source_provenance = tuple(self.source_provenance)
        if any(
            not isinstance(item, RegistrySourceProvenance) for item in source_provenance
        ):
            raise TypeError(
                "source_provenance must contain RegistrySourceProvenance records"
            )
        if len({item.proposition_id for item in source_provenance}) != len(
            source_provenance
        ):
            raise ValueError("source_provenance contains duplicate proposition IDs")
        object.__setattr__(
            self,
            "source_provenance",
            tuple(sorted(source_provenance, key=lambda item: item.proposition_id)),
        )
        object.__setattr__(
            self,
            "rules",
            tuple(
                sorted(
                    rules,
                    key=lambda item: (
                        _STAGE_INDEX[item.stage],
                        item.precedence,
                        item.id,
                    ),
                )
            ),
        )
        object.__setattr__(
            self,
            "exclusions",
            tuple(sorted(exclusions, key=lambda item: item.candidate_id)),
        )
        canonical_by_id = {item.id: item for item in self.rules}
        object.__setattr__(self, "rules_by_id", MappingProxyType(canonical_by_id))
        production_rules = tuple(
            rule for rule in self.rules if rule.authority_layer != "synthetic"
        )
        synthetic_rules = tuple(
            rule for rule in self.rules if rule.authority_layer == "synthetic"
        )
        if production_rules and synthetic_rules:
            raise ValueError("production and synthetic fixture rules cannot be mixed")
        if production_rules:
            required_sources = {
                source_id for rule in production_rules for source_id in rule.source_ids
            }
            provided_sources = {item.proposition_id for item in self.source_provenance}
            if not self.source_bundle_digest or required_sources != provided_sources:
                raise ValueError(
                    "production rules require verified production provenance; "
                    f"required={sorted(required_sources)}, "
                    f"provided={sorted(provided_sources)}"
                )
            expected_provenance_digest = canonical_digest(
                {
                    "source_bundle_digest": self.source_bundle_digest,
                    "source_provenance": [
                        item.canonical_data() for item in self.source_provenance
                    ],
                }
            )
            if (
                self.source_provenance_digest
                and self.source_provenance_digest != expected_provenance_digest
            ):
                raise ValueError(
                    "source_provenance_digest does not bind source eligibility facts"
                )
            object.__setattr__(
                self,
                "source_provenance_digest",
                expected_provenance_digest,
            )
        elif (
            self.source_bundle_digest
            or self.source_provenance
            or self.source_provenance_digest
        ):
            raise ValueError(
                "synthetic fixture registries cannot declare production provenance"
            )
        self._validate_references(canonical_by_id)
        expected = self._semantic_digest()
        if self.bundle_digest and self.bundle_digest != expected:
            raise ValueError("registry bundle_digest does not match semantic content")
        object.__setattr__(self, "bundle_digest", expected)

    def _semantic_digest(self) -> str:
        return canonical_digest(
            {
                "registry_version": REGISTRY_VERSION,
                "bundle_id": self.bundle_id,
                "source_bundle_digest": self.source_bundle_digest,
                "source_provenance_digest": self.source_provenance_digest,
                "source_provenance": [
                    item.canonical_data() for item in self.source_provenance
                ],
                "rules": [
                    item.canonical_data()
                    for item in sorted(self.rules, key=lambda rule: rule.id)
                ],
                "exclusions": [item.canonical_data() for item in self.exclusions],
            }
        )

    def _validate_references(self, by_id: Mapping[str, RegistryRule]) -> None:
        paths = {
            (rule.pattern_id, str(rule.path_id))
            for rule in self.rules
            if rule.stage == "formation" and rule.path_id is not None
        }
        path_patterns: dict[str, set[str]] = {}
        for pattern_id, path_id in paths:
            path_patterns.setdefault(path_id, set()).add(pattern_id)
        damages = {rule.id: rule for rule in self.rules if rule.stage == "damage"}
        rescues = {rule.id: rule for rule in self.rules if rule.stage == "rescue"}

        for rule in self.rules:
            bound_path_ids = (
                *rule.targets_path_ids,
                *rule.supersedes_path_ids,
                *((rule.path_id,) if rule.path_id is not None else ()),
            )
            for path_id in bound_path_ids:
                if (rule.pattern_id, path_id) in paths:
                    continue
                if path_id in path_patterns:
                    raise ValueError(
                        f"cross-pattern target path {path_id} from rule {rule.id}"
                    )
                raise ValueError(f"unknown target path {path_id} from rule {rule.id}")
            for damage_id in rule.resolves_damage_ids:
                damage = damages.get(damage_id)
                if damage is None:
                    raise ValueError(
                        f"rescue rule {rule.id} references unknown declared damage {damage_id}"
                    )
                if damage.pattern_id != rule.pattern_id:
                    raise ValueError(
                        f"cross-pattern damage reference {damage_id} from rule {rule.id}"
                    )
            for rescue_id in rule.invalidates_rescue_ids:
                rescue = rescues.get(rescue_id)
                if rescue is None:
                    raise ValueError(
                        f"rule {rule.id} invalidates unknown rescue {rescue_id}"
                    )
                if rescue.pattern_id != rule.pattern_id:
                    raise ValueError(
                        f"cross-pattern rescue reference {rescue_id} from rule {rule.id}"
                    )

        invalidation_graph = {
            rule.id: set(rule.invalidates_rescue_ids)
            for rule in self.rules
            if rule.id in rescues
        }
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(rule_id: str) -> None:
            if rule_id in visiting:
                raise ValueError("rescue invalidation cycle")
            if rule_id in visited:
                return
            visiting.add(rule_id)
            for target in invalidation_graph.get(rule_id, set()):
                visit(target)
            visiting.remove(rule_id)
            visited.add(rule_id)

        for rule_id in invalidation_graph:
            visit(rule_id)

        supersession_graph: dict[tuple[str, str], set[tuple[str, str]]] = {}
        for rule in self.rules:
            if rule.path_id is None:
                continue
            source = (rule.pattern_id, rule.path_id)
            supersession_graph.setdefault(source, set()).update(
                (rule.pattern_id, target) for target in rule.supersedes_path_ids
            )
        path_visiting: set[tuple[str, str]] = set()
        path_visited: set[tuple[str, str]] = set()

        def visit_path(path: tuple[str, str]) -> None:
            if path in path_visiting:
                raise ValueError("path supersession cycle")
            if path in path_visited:
                return
            path_visiting.add(path)
            for target in supersession_graph.get(path, set()):
                visit_path(target)
            path_visiting.remove(path)
            path_visited.add(path)

        for path in supersession_graph:
            visit_path(path)

    def rules_for(self, pattern_id: str, stage: str) -> tuple[RegistryRule, ...]:
        if stage not in _STAGE_INDEX:
            raise ValueError(f"unresolved lifecycle stage: {stage!r}")
        return tuple(
            item
            for item in self.rules
            if item.pattern_id == pattern_id and item.stage == stage
        )


def registry_from_records(
    bundle_id: str,
    records: Sequence[Mapping[str, Any]],
    *,
    source_bundle_digest: str = "",
    exclusions: Sequence[RegistryExclusion] = (),
    source_provenance: Sequence[RegistrySourceProvenance] = (),
    source_provenance_digest: str = "",
    bundle_digest: str = "",
) -> RuleRegistry:
    """Parse Task 3 compiled-like records through a closed metadata contract."""

    rules: list[RegistryRule] = []
    allowed_record_keys = frozenset(
        (
            "id",
            "predicate",
            "effect",
            "precedence",
            "metadata",
            "proposition_id",
            "resolution_slot",
            "after",
            "before",
        )
    )
    for raw in records:
        if not isinstance(raw, Mapping):
            raise ValueError("registry records must be objects")
        extras = set(raw) - set(allowed_record_keys)
        if extras:
            raise ValueError(f"registry record has unknown fields: {sorted(extras)}")
        metadata = raw.get("metadata")
        if not isinstance(metadata, Mapping):
            raise ValueError("registry rule metadata must be an object")
        metadata_extras = set(metadata) - set(_METADATA_KEYS)
        if metadata_extras:
            raise ValueError(
                f"registry rule has unknown metadata: {sorted(metadata_extras)}"
            )
        missing = _METADATA_KEYS - set(metadata)
        if missing:
            raise ValueError(f"registry rule is missing metadata: {sorted(missing)}")
        source_ids = _identifiers(metadata["source_ids"], "source_ids")
        if "proposition_id" in raw:
            proposition_id = _identifier(
                raw["proposition_id"],
                "registry proposition_id",
            )
            assert proposition_id is not None
            if source_ids != (proposition_id,):
                raise ValueError(
                    "compiled registry source_ids must exactly cite proposition_id"
                )
        rules.append(
            RegistryRule(
                id=raw.get("id", ""),
                stage=metadata["stage"],
                pattern_id=metadata["pattern_id"],
                predicate=raw.get("predicate", {}),
                effect=raw.get("effect", ""),
                path_id=metadata["path_id"],
                targets_path_ids=_identifiers(
                    metadata["targets_path_ids"], "targets_path_ids"
                ),
                resolves_damage_ids=_identifiers(
                    metadata["resolves_damage_ids"], "resolves_damage_ids"
                ),
                invalidates_rescue_ids=_identifiers(
                    metadata["invalidates_rescue_ids"], "invalidates_rescue_ids"
                ),
                supersedes_path_ids=_identifiers(
                    metadata["supersedes_path_ids"], "supersedes_path_ids"
                ),
                authority_layer=metadata["authority_layer"],
                source_ids=source_ids,
                precedence=raw.get("precedence", 0),
            )
        )
    return RuleRegistry(
        bundle_id=bundle_id,
        rules=tuple(rules),
        bundle_digest=bundle_digest,
        source_bundle_digest=source_bundle_digest,
        exclusions=tuple(exclusions),
        source_provenance=tuple(source_provenance),
        source_provenance_digest=source_provenance_digest,
    )


def _source_provenance_from_data(
    value: Mapping[str, Any],
    *,
    index: int,
) -> RegistrySourceProvenance:
    fields = frozenset(
        (
            "proposition_id",
            "layer",
            "text_type",
            "production_eligible",
            "review_state",
            "source_manifest_digest",
            "corpus_manifest_digest",
            "corpus_artifact_digest",
            "segments",
            "support_locators",
        )
    )
    raw = _closed_object(
        value,
        field_name=f"source_provenance[{index}]",
        allowed=fields,
    )
    segment_fields = frozenset(("id", "layer", "text_type", "review_state"))
    segments = tuple(
        RegistrySourceSegment(
            **dict(
                _closed_object(
                    item,
                    field_name=f"source_provenance[{index}].segments[{item_index}]",
                    allowed=segment_fields,
                )
            )
        )
        for item_index, item in enumerate(
            _records(raw["segments"], f"source_provenance[{index}].segments")
        )
    )
    locator_fields = frozenset(
        (
            "id",
            "review_state",
            "visually_verified",
            "witness_id",
            "witness_rights_status",
            "witness_production_allowed",
        )
    )
    support_locators = tuple(
        RegistrySupportLocator(
            **dict(
                _closed_object(
                    item,
                    field_name=(
                        f"source_provenance[{index}].support_locators[{item_index}]"
                    ),
                    allowed=locator_fields,
                )
            )
        )
        for item_index, item in enumerate(
            _records(
                raw["support_locators"],
                f"source_provenance[{index}].support_locators",
            )
        )
    )
    return RegistrySourceProvenance(
        proposition_id=raw["proposition_id"],
        layer=raw["layer"],
        text_type=raw["text_type"],
        production_eligible=raw["production_eligible"],
        review_state=raw["review_state"],
        source_manifest_digest=raw["source_manifest_digest"],
        corpus_manifest_digest=raw["corpus_manifest_digest"],
        corpus_artifact_digest=raw["corpus_artifact_digest"],
        segments=segments,
        support_locators=support_locators,
    )


def registry_from_data(payload: Mapping[str, Any]) -> RuleRegistry:
    """Parse the self-contained packaged registry through a closed schema."""

    raw = _closed_object(
        payload,
        field_name="registry bundle",
        allowed=frozenset(
            (
                "registry_version",
                "bundle_id",
                "bundle_digest",
                "source_bundle_digest",
                "source_provenance",
                "source_provenance_digest",
                "rules",
                "exclusions",
            )
        ),
    )
    if raw["registry_version"] != REGISTRY_VERSION:
        raise ValueError("unsupported registry_version")
    rule_fields = frozenset(
        (
            "id",
            "stage",
            "pattern_id",
            "predicate",
            "effect",
            "path_id",
            "targets_path_ids",
            "resolves_damage_ids",
            "invalidates_rescue_ids",
            "supersedes_path_ids",
            "authority_layer",
            "source_ids",
            "precedence",
        )
    )
    rules = []
    for index, item in enumerate(_records(raw["rules"], "registry rules")):
        rule = _closed_object(
            item,
            field_name=f"registry rules[{index}]",
            allowed=rule_fields,
        )
        rules.append(RegistryRule(**dict(rule)))
    exclusion_fields = frozenset(("candidate_id", "reason", "source_ids"))
    exclusions = []
    for index, item in enumerate(_records(raw["exclusions"], "registry exclusions")):
        exclusion = _closed_object(
            item,
            field_name=f"registry exclusions[{index}]",
            allowed=exclusion_fields,
        )
        exclusions.append(RegistryExclusion(**dict(exclusion)))
    source_provenance = tuple(
        _source_provenance_from_data(item, index=index)
        for index, item in enumerate(
            _records(raw["source_provenance"], "source_provenance")
        )
    )
    registry = RuleRegistry(
        bundle_id=raw["bundle_id"],
        rules=tuple(rules),
        bundle_digest=raw["bundle_digest"],
        source_bundle_digest=raw["source_bundle_digest"],
        exclusions=tuple(exclusions),
        source_provenance=source_provenance,
        source_provenance_digest=raw["source_provenance_digest"],
    )
    if any(rule.authority_layer == "synthetic" for rule in registry.rules):
        raise ValueError("packaged production registry cannot contain synthetic rules")
    return registry


def attestation_bundle_from_data(
    payload: Mapping[str, Any],
) -> ExampleAttestationBundle:
    """Parse exact-signature evidence that cannot mutate canonical results."""

    raw = _closed_object(
        payload,
        field_name="attestation bundle",
        allowed=frozenset(
            (
                "attestation_bundle_version",
                "bundle_id",
                "generic_bundle_id",
                "bundle_digest",
                "attestations",
            )
        ),
    )
    if raw["attestation_bundle_version"] != ATTESTATION_BUNDLE_VERSION:
        raise ValueError("unsupported attestation_bundle_version")
    fields = frozenset(
        (
            "id",
            "pillars",
            "mechanisms",
            "explanation",
            "source_ids",
            "affects_canonical_status",
        )
    )
    attestations = []
    for index, item in enumerate(_records(raw["attestations"], "attestations")):
        record = _closed_object(
            item,
            field_name=f"attestations[{index}]",
            allowed=fields,
        )
        attestations.append(ExampleAttestation(**dict(record)))
    return ExampleAttestationBundle(
        bundle_id=raw["bundle_id"],
        generic_bundle_id=raw["generic_bundle_id"],
        attestations=tuple(attestations),
        bundle_digest=raw["bundle_digest"],
    )


@lru_cache(maxsize=1)
def load_packaged_registry() -> RuleRegistry:
    """Load the generic registry from package resources, never research paths."""

    return registry_from_data(_load_json_resource("zzq-shen-canonical-v1.json"))


@lru_cache(maxsize=1)
def load_packaged_attestation_bundle() -> ExampleAttestationBundle:
    """Load exact classical examples from their non-authoritative resource."""

    return attestation_bundle_from_data(
        _load_json_resource("zzq-direct-officer-example-attestations-v1.json")
    )


def compile_research_direct_officer_registry(project_root: str | Path) -> RuleRegistry:
    """Regenerate the canonical direct-officer slice from reviewed research."""

    root = Path(project_root)
    source_manifest = root / "research" / "classics" / "sources" / "manifest.json"
    corpus_manifest = (
        root / "research" / "classics" / "ziping_zhenquan" / "manifest.json"
    )
    propositions = load_hydrated_propositions(source_manifest, corpus_manifest)
    manifest = json.loads(corpus_manifest.read_text(encoding="utf-8"))
    if not isinstance(manifest, Mapping):
        raise ValueError("corpus manifest must be an object")
    selected: list[Mapping[str, Any]] = []
    for chapter in _records(manifest.get("chapters"), "corpus chapters"):
        files = chapter.get("files")
        if not isinstance(files, Mapping):
            raise ValueError("corpus chapter files must be an object")
        rule_path = root / str(files.get("rule_candidates", ""))
        for record in _load_jsonl(rule_path):
            if record.get("execution_ready") is True:
                selected.append(
                    {key: record[key] for key in _RULE_DEFINITION_KEYS if key in record}
                )
    compiled = compile_rule_records(selected, propositions)
    compiled_records = [
        {
            "id": item.id,
            "proposition_id": item.proposition_id,
            "predicate": predicate_to_canonical_data(item.predicate),
            "effect": item.effect,
            "resolution_slot": item.resolution_slot,
            "precedence": item.precedence,
            "after": list(item.after),
            "before": list(item.before),
            "metadata": dict(item.metadata),
        }
        for item in compiled.rules
    ]
    exclusion_records = _records(
        manifest.get("lifecycle_exclusions", ()),
        "lifecycle_exclusions",
    )
    exclusion_fields = frozenset(("candidate_id", "reason", "source_ids"))
    exclusions = tuple(
        RegistryExclusion(
            **dict(
                _closed_object(
                    item,
                    field_name=f"lifecycle_exclusions[{index}]",
                    allowed=exclusion_fields,
                )
            )
        )
        for index, item in enumerate(exclusion_records)
    )
    return registry_from_records(
        "zzq-shen-canonical-v1",
        compiled_records,
        source_bundle_digest=compiled.digest,
        exclusions=exclusions,
        source_provenance=tuple(
            _source_provenance(proposition)
            for _, proposition in sorted(
                {
                    item.proposition_id: item.proposition for item in compiled.rules
                }.items()
            )
        ),
    )


__all__ = [
    "ATTESTATION_BUNDLE_VERSION",
    "ExampleAttestation",
    "ExampleAttestationBundle",
    "LIFECYCLE_STAGES",
    "REGISTRY_VERSION",
    "RegistryExclusion",
    "RegistryRule",
    "RegistrySourceProvenance",
    "RegistrySourceSegment",
    "RegistrySupportLocator",
    "RuleRegistry",
    "attestation_bundle_from_data",
    "compile_research_direct_officer_registry",
    "load_packaged_attestation_bundle",
    "load_packaged_registry",
    "registry_from_data",
    "registry_from_records",
]
