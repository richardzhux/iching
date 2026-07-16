"""Typed, closed registry contracts for pattern lifecycle rules."""

from __future__ import annotations

import hashlib
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
    research_corpus_digest,
)
from iching.core.bazi_rules.predicates import (
    parse_predicate,
    predicate_to_canonical_data,
)
from iching.core.bazi_rules.primitives import BRANCHES, STEMS
from iching.core.bazi_rules.schema import PredicateNode, Proposition


REGISTRY_VERSION = "bazi-rule-registry-v1"
ATTESTATION_BUNDLE_VERSION = "bazi-example-attestations-v1"
TASK4_SHADOW_BUNDLE_ID = "zzq-shen-canonical-v1"
TASK4_SHADOW_BUNDLE_DIGEST = (
    "b95f8d7e5e94fbd179f12b1704bf169ead94f14fd2d3fdd4a9410b474471ad3e"
)
TASK4_SHADOW_RESOURCE_SHA256 = (
    "7d5e2e42040c259c13b25749c4fc61b986bbcd8bd12be8f14f4ee2049cbce303"
)
TASK4_SHADOW_RESOURCE = "zzq-task4-direct-officer-shadow-v1.json"
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
        "candidate": frozenset(("candidate_confirm", "candidate_possible")),
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
_PRODUCTION_AUTHORITY_LAYERS = _AUTHORITY_LAYERS - {"synthetic"}
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
_OPTIONAL_METADATA_KEYS = frozenset(("supporting_source_ids",))
_ALLOWED_METADATA_KEYS = _METADATA_KEYS | _OPTIONAL_METADATA_KEYS
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
        if self.layer not in _PRODUCTION_AUTHORITY_LAYERS:
            raise ValueError("production provenance has unsupported authority layer")
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
    quote: str | None = None
    pdf_page: int | None = None
    printed_page: str | None = None
    column_line: str | None = None
    url: str | None = None

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
        if self.quote is not None and (
            not isinstance(self.quote, str) or not self.quote.strip()
        ):
            raise ValueError("support locator quote must be a non-blank string")
        if self.pdf_page is not None and (
            type(self.pdf_page) is not int or self.pdf_page <= 0
        ):
            raise ValueError("support locator pdf_page must be a positive integer")
        for field_name in ("printed_page", "column_line", "url"):
            value = getattr(self, field_name)
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ValueError(f"support locator {field_name} must be non-blank")
        if self.url is not None and not self.url.startswith(("https://", "http://")):
            raise ValueError("support locator url must use HTTP or HTTPS")

    def canonical_data(self) -> dict[str, Any]:
        result = {
            "id": self.id,
            "review_state": self.review_state,
            "visually_verified": True,
            "witness_id": self.witness_id,
            "witness_rights_status": self.witness_rights_status,
            "witness_production_allowed": True,
        }
        for field_name in ("quote", "pdf_page", "printed_page", "column_line", "url"):
            value = getattr(self, field_name)
            if value is not None:
                result[field_name] = value
        return result

    def packaged_data(self) -> dict[str, Any]:
        """Serialize the digest-bound source locator for the packaged bundle."""

        return self.canonical_data()


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
            self.layer not in _PRODUCTION_AUTHORITY_LAYERS
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
        if {item.layer for item in segments} != {self.layer}:
            raise ValueError(
                "production provenance segment layer does not match proposition layer"
            )
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

    def packaged_data(self) -> dict[str, Any]:
        result = self.canonical_data()
        result["support_locators"] = [
            item.packaged_data() for item in self.support_locators
        ]
        return result


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
                quote=item.quote,
                pdf_page=item.pdf_page,
                printed_page=item.printed_page,
                column_line=item.column_line,
                url=item.url,
            )
            for item in proposition.locators
        ),
    )


@dataclass(frozen=True)
class RegistryExclusion:
    candidate_id: str
    reason: str
    source_ids: tuple[str, ...] = ()
    pattern_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "candidate_id", _identifier(self.candidate_id, "candidate_id")
        )
        object.__setattr__(self, "reason", _identifier(self.reason, "exclusion reason"))
        source_ids = _identifiers(self.source_ids, "source_ids")
        if not source_ids:
            raise ValueError("registry exclusion requires source_ids")
        object.__setattr__(self, "source_ids", source_ids)
        object.__setattr__(
            self,
            "pattern_id",
            _identifier(self.pattern_id, "exclusion pattern_id", optional=True),
        )

    def canonical_data(self) -> dict[str, Any]:
        result = {
            "candidate_id": self.candidate_id,
            "reason": self.reason,
            "source_ids": list(self.source_ids),
        }
        if self.pattern_id is not None:
            result["pattern_id"] = self.pattern_id
        return result


@dataclass(frozen=True)
class SpecialReviewGatePolicy:
    """Source bindings for the set-level ordinary-before-special review gate."""

    id: str
    ordinary_use_source_id: str
    officer_killing_source_id: str
    rooted_wealth_source_id: str
    double_wealth_source_id: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _identifier(self.id, "special gate policy id"))
        for field_name in (
            "ordinary_use_source_id",
            "officer_killing_source_id",
            "rooted_wealth_source_id",
            "double_wealth_source_id",
        ):
            object.__setattr__(
                self,
                field_name,
                _identifier(getattr(self, field_name), field_name),
            )
        if len(set(self.source_ids)) != len(self.source_ids):
            raise ValueError("special review gate source IDs must be unique")

    @property
    def source_ids(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                (
                    self.ordinary_use_source_id,
                    self.officer_killing_source_id,
                    self.rooted_wealth_source_id,
                    self.double_wealth_source_id,
                )
            )
        )

    def canonical_data(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "ordinary_use_source_id": self.ordinary_use_source_id,
            "officer_killing_source_id": self.officer_killing_source_id,
            "rooted_wealth_source_id": self.rooted_wealth_source_id,
            "double_wealth_source_id": self.double_wealth_source_id,
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
    supporting_source_ids: tuple[str, ...] = ()
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
                "unsupported executable stage/effect combination: "
                f"{self.stage}/{self.effect}"
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
            "supporting_source_ids",
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
        if self.stage == "candidate" and (
            self.path_id is not None
            or self.targets_path_ids
            or self.resolves_damage_ids
            or self.invalidates_rescue_ids
            or self.supersedes_path_ids
        ):
            raise ValueError(
                f"candidate rule {self.id} cannot declare lifecycle bindings"
            )
        if self.stage == "formation" and self.path_id is None:
            raise ValueError(f"formation rule {self.id} requires path_id")
        if self.stage == "formation" and (
            self.targets_path_ids
            or self.resolves_damage_ids
            or self.invalidates_rescue_ids
        ):
            raise ValueError(
                f"formation rule {self.id} has unsupported lifecycle side effects"
            )
        if (
            self.stage in {"damage", "rescue"}
            and self.path_id is not None
            and self.targets_path_ids
        ):
            raise ValueError(
                f"{self.stage} rule {self.id} must use only one path binding form"
            )
        if self.stage == "damage":
            if self.resolves_damage_ids or self.supersedes_path_ids:
                raise ValueError(
                    f"damage rule {self.id} has unsupported lifecycle side effects"
                )
            if self.effect == "rescue_invalidation":
                if not self.invalidates_rescue_ids:
                    raise ValueError(
                        f"rescue invalidation rule {self.id} requires "
                        "invalidates_rescue_ids"
                    )
            elif self.invalidates_rescue_ids:
                raise ValueError(f"damage rule {self.id} cannot invalidate a rescue")
        if self.stage == "rescue":
            if not self.resolves_damage_ids:
                raise ValueError(f"rescue rule {self.id} requires declared damage")
            if self.invalidates_rescue_ids or self.supersedes_path_ids:
                raise ValueError(
                    f"rescue rule {self.id} has unsupported lifecycle side effects"
                )
        if self.stage == "resolution":
            if self.path_id is None:
                raise ValueError(f"source precedence rule {self.id} requires path_id")
            if not self.supersedes_path_ids:
                raise ValueError(
                    f"source precedence rule {self.id} requires supersedes_path_ids"
                )
            if self.resolves_damage_ids or self.invalidates_rescue_ids:
                raise ValueError(
                    f"resolution rule {self.id} has unsupported lifecycle side effects"
                )
        if self.resolves_damage_ids and self.stage != "rescue":
            raise ValueError("only rescue rules may declare resolved damage")
        if self.authority_layer not in _AUTHORITY_LAYERS:
            raise ValueError(f"unknown authority layer: {self.authority_layer!r}")
        if not self.source_ids:
            raise ValueError(f"rule {self.id} requires source_ids")
        if set(self.source_ids) & set(self.supporting_source_ids):
            raise ValueError("supporting_source_ids must be disjoint from source_ids")
        if any(
            _looks_like_attestation(source_id)
            for source_id in (*self.source_ids, *self.supporting_source_ids)
        ):
            raise ValueError(f"generic rule {self.id} depends on an attestation")
        if type(self.precedence) is not int:
            raise ValueError("registry precedence must be an integer")
        object.__setattr__(self, "predicate", parse_predicate(self.predicate))

    def canonical_data(self) -> dict[str, Any]:
        result = {
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
        if self.supporting_source_ids:
            result["supporting_source_ids"] = list(self.supporting_source_ids)
        return result


@dataclass(frozen=True)
class RuleRegistry:
    bundle_id: str
    rules: tuple[RegistryRule, ...]
    bundle_digest: str = ""
    source_bundle_digest: str = ""
    exclusions: tuple[RegistryExclusion, ...] = ()
    special_review_gate: SpecialReviewGatePolicy | None = None
    source_provenance: tuple[RegistrySourceProvenance, ...] = ()
    source_provenance_digest: str = ""
    authority_layer: str | None = None
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
        rule_layers = {item.authority_layer for item in rules}
        selected_layer = self.authority_layer
        if selected_layer is None:
            selected_layer = (
                next(iter(rule_layers)) if len(rule_layers) == 1 else "synthetic"
            )
        if selected_layer not in _AUTHORITY_LAYERS:
            raise ValueError(f"unknown registry authority layer: {selected_layer!r}")
        if rule_layers and rule_layers != {selected_layer}:
            raise ValueError(
                "registry authority layer does not match every rule authority layer"
            )
        object.__setattr__(self, "authority_layer", selected_layer)
        exclusions = tuple(self.exclusions)
        if any(not isinstance(item, RegistryExclusion) for item in exclusions):
            raise TypeError("registry exclusions must be RegistryExclusion records")
        if len({item.candidate_id for item in exclusions}) != len(exclusions):
            raise ValueError("registry contains duplicate exclusion candidate IDs")
        declared_pattern_ids = {item.pattern_id for item in rules}
        if any(
            item.pattern_id is not None and item.pattern_id not in declared_pattern_ids
            for item in exclusions
        ):
            raise ValueError("registry exclusion references an undeclared pattern")
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
        if source_provenance and {item.layer for item in source_provenance} != {
            selected_layer
        }:
            raise ValueError(
                "registry authority layer does not match source provenance layer"
            )
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
        if self.special_review_gate is not None and not isinstance(
            self.special_review_gate, SpecialReviewGatePolicy
        ):
            raise TypeError("special_review_gate must be a SpecialReviewGatePolicy")
        if self.special_review_gate is not None and selected_layer != "shen_core":
            raise ValueError("special review gate belongs only to canonical Shen core")
        canonical_by_id = {item.id: item for item in self.rules}
        object.__setattr__(self, "rules_by_id", MappingProxyType(canonical_by_id))
        candidate_effects: dict[str, set[str]] = {}
        for rule in self.rules:
            if rule.stage == "candidate":
                candidate_effects.setdefault(rule.pattern_id, set()).add(rule.effect)
        required_candidate_effects = {"candidate_confirm", "candidate_possible"}
        for pattern_id, effects in candidate_effects.items():
            if effects != required_candidate_effects:
                raise ValueError(
                    f"pattern {pattern_id} requires candidate_confirm and "
                    "candidate_possible"
                )
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
                source_id
                for rule in production_rules
                for source_id in (*rule.source_ids, *rule.supporting_source_ids)
            }
            if self.special_review_gate is not None:
                required_sources.update(self.special_review_gate.source_ids)
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
        elif selected_layer != "synthetic":
            if not self.source_bundle_digest:
                raise ValueError(
                    "empty production registry requires a bound research corpus digest"
                )
            if self.source_provenance or self.source_provenance_digest:
                raise ValueError(
                    "empty production registry cannot declare executable provenance"
                )
            if self.special_review_gate is not None:
                raise ValueError(
                    "empty production registry cannot declare a special gate"
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
        payload = {
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
        if self.special_review_gate is not None:
            payload["special_review_gate"] = self.special_review_gate.canonical_data()
        # A non-empty registry already binds its authority through every rule and
        # provenance record. Keeping the redundant bundle field out preserves the
        # immutable Task 4 semantic digest. Empty production overlays have neither,
        # so their authority must be bound explicitly.
        if not self.rules:
            payload["authority_layer"] = self.authority_layer
        return canonical_digest(payload)

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

        def bound_paths(rule: RegistryRule) -> set[str]:
            declared = {
                path_id
                for pattern_id, path_id in paths
                if pattern_id == rule.pattern_id
            }
            if rule.targets_path_ids:
                return set(rule.targets_path_ids)
            if rule.path_id is not None:
                return {rule.path_id}
            return declared

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
                if damage.effect == "rescue_invalidation":
                    raise ValueError(
                        f"rescue rule {rule.id} must reference an actual damage, "
                        f"not rescue invalidator {damage_id}"
                    )
                if not (bound_paths(rule) & bound_paths(damage)):
                    raise ValueError(
                        f"rescue rule {rule.id} does not share a formation path "
                        f"with damage {damage_id}"
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
                if not (bound_paths(rule) & bound_paths(rescue)):
                    raise ValueError(
                        f"rule {rule.id} does not share a formation path with "
                        f"rescue {rescue_id}"
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
    authority_layer: str | None = None,
    source_bundle_digest: str = "",
    exclusions: Sequence[RegistryExclusion] = (),
    special_review_gate: SpecialReviewGatePolicy | None = None,
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
        metadata_extras = set(metadata) - set(_ALLOWED_METADATA_KEYS)
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
                supporting_source_ids=_identifiers(
                    metadata.get("supporting_source_ids", ()),
                    "supporting_source_ids",
                ),
                precedence=raw.get("precedence", 0),
            )
        )
    return RuleRegistry(
        bundle_id=bundle_id,
        rules=tuple(rules),
        authority_layer=authority_layer,
        bundle_digest=bundle_digest,
        source_bundle_digest=source_bundle_digest,
        exclusions=tuple(exclusions),
        special_review_gate=special_review_gate,
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
            "quote",
            "pdf_page",
            "printed_page",
            "column_line",
            "url",
        )
    )
    required_locator_fields = frozenset(
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
                    required=required_locator_fields,
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

    bundle_fields = frozenset(
        (
            "registry_version",
            "bundle_id",
            "bundle_digest",
            "source_bundle_digest",
            "source_provenance",
            "source_provenance_digest",
            "rules",
            "exclusions",
            "special_review_gate",
            "authority_layer",
        )
    )
    required_bundle_fields = bundle_fields - {"authority_layer", "special_review_gate"}
    raw = _closed_object(
        payload,
        field_name="registry bundle",
        allowed=bundle_fields,
        required=required_bundle_fields,
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
            "supporting_source_ids",
            "precedence",
        )
    )
    required_rule_fields = rule_fields - {"supporting_source_ids"}
    rules = []
    for index, item in enumerate(_records(raw["rules"], "registry rules")):
        rule = _closed_object(
            item,
            field_name=f"registry rules[{index}]",
            allowed=rule_fields,
            required=required_rule_fields,
        )
        rules.append(RegistryRule(**dict(rule)))
    if any(rule.authority_layer == "synthetic" for rule in rules):
        raise ValueError("packaged production registry cannot contain synthetic rules")
    exclusion_fields = frozenset(("candidate_id", "reason", "source_ids", "pattern_id"))
    required_exclusion_fields = exclusion_fields - {"pattern_id"}
    exclusions = []
    for index, item in enumerate(_records(raw["exclusions"], "registry exclusions")):
        exclusion = _closed_object(
            item,
            field_name=f"registry exclusions[{index}]",
            allowed=exclusion_fields,
            required=required_exclusion_fields,
        )
        exclusions.append(RegistryExclusion(**dict(exclusion)))
    special_review_gate = None
    if "special_review_gate" in raw:
        gate_fields = frozenset(
            (
                "id",
                "ordinary_use_source_id",
                "officer_killing_source_id",
                "rooted_wealth_source_id",
                "double_wealth_source_id",
            )
        )
        gate = _closed_object(
            raw["special_review_gate"],
            field_name="special_review_gate",
            allowed=gate_fields,
            required=gate_fields,
        )
        special_review_gate = SpecialReviewGatePolicy(**dict(gate))
    source_provenance = tuple(
        _source_provenance_from_data(item, index=index)
        for index, item in enumerate(
            _records(raw["source_provenance"], "source_provenance")
        )
    )
    registry = RuleRegistry(
        bundle_id=raw["bundle_id"],
        rules=tuple(rules),
        authority_layer=raw.get("authority_layer"),
        bundle_digest=raw["bundle_digest"],
        source_bundle_digest=raw["source_bundle_digest"],
        exclusions=tuple(exclusions),
        special_review_gate=special_review_gate,
        source_provenance=source_provenance,
        source_provenance_digest=raw["source_provenance_digest"],
    )
    if rules and not _valid_digest(raw["source_provenance_digest"]):
        raise ValueError(
            "packaged registry source_provenance_digest must be a non-blank "
            "lowercase SHA-256 digest"
        )
    if not _valid_digest(raw["bundle_digest"]):
        raise ValueError(
            "packaged registry bundle_digest must be a non-blank lowercase SHA-256 digest"
        )
    return registry


def registry_to_data(registry: RuleRegistry) -> dict[str, Any]:
    """Serialize a registry through the same closed packaged-bundle schema."""

    if not isinstance(registry, RuleRegistry):
        raise TypeError("registry must be a RuleRegistry")
    result = {
        "registry_version": REGISTRY_VERSION,
        "bundle_id": registry.bundle_id,
        "bundle_digest": registry.bundle_digest,
        "source_bundle_digest": registry.source_bundle_digest,
        "source_provenance": [
            item.packaged_data() for item in registry.source_provenance
        ],
        "source_provenance_digest": registry.source_provenance_digest,
        "rules": [item.canonical_data() for item in registry.rules],
        "exclusions": [item.canonical_data() for item in registry.exclusions],
        "authority_layer": registry.authority_layer,
    }
    if registry.special_review_gate is not None:
        result["special_review_gate"] = registry.special_review_gate.canonical_data()
    return result


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
def load_packaged_shen_registry() -> RuleRegistry:
    """Load the canonical Shen registry from package resources."""

    registry = registry_from_data(_load_json_resource("zzq-shen-canonical-v1.json"))
    if registry.authority_layer != "shen_core":
        raise ValueError("packaged canonical registry must use shen_core authority")
    return registry


@lru_cache(maxsize=1)
def load_packaged_task4_shadow_registry() -> RuleRegistry:
    """Load the immutable Task 4 direct-officer compatibility projection."""

    resource = resources.files("iching.core.bazi_rules").joinpath(
        "bundles", TASK4_SHADOW_RESOURCE
    )
    payload = resource.read_bytes()
    if hashlib.sha256(payload).hexdigest() != TASK4_SHADOW_RESOURCE_SHA256:
        raise ValueError("Task 4 shadow resource byte digest mismatch")
    raw = json.loads(payload)
    if not isinstance(raw, Mapping):
        raise ValueError("Task 4 shadow resource must contain an object")
    registry = registry_from_data(raw)
    if (
        registry.bundle_id != TASK4_SHADOW_BUNDLE_ID
        or registry.bundle_digest != TASK4_SHADOW_BUNDLE_DIGEST
        or registry.authority_layer != "shen_core"
    ):
        raise ValueError("Task 4 shadow registry identity mismatch")
    return registry


def load_packaged_registry() -> RuleRegistry:
    """Compatibility alias for the canonical Shen registry."""

    return load_packaged_shen_registry()


@lru_cache(maxsize=1)
def load_packaged_attestation_bundle() -> ExampleAttestationBundle:
    """Load exact classical examples from their non-authoritative resource."""

    return attestation_bundle_from_data(
        _load_json_resource("zzq-direct-officer-example-attestations-v1.json")
    )


def compile_research_registry(
    project_root: str | Path,
    *,
    bundle_id: str,
    authority_layer: str,
    corpus_manifest: str | Path = "research/classics/ziping_zhenquan/manifest.json",
) -> RuleRegistry:
    """Compile one reviewed corpus into one isolated authority registry."""

    if authority_layer not in _PRODUCTION_AUTHORITY_LAYERS:
        raise ValueError("research registry requires a production authority layer")
    root = Path(project_root)
    source_manifest = root / "research" / "classics" / "sources" / "manifest.json"
    corpus_path = Path(corpus_manifest)
    if not corpus_path.is_absolute():
        corpus_path = root / corpus_path
    manifest = json.loads(corpus_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, Mapping):
        raise ValueError("corpus manifest must be an object")
    authority_boundary = manifest.get("authority_boundary")
    if authority_boundary is not None:
        if not isinstance(authority_boundary, Mapping):
            raise ValueError("corpus authority_boundary must be an object")
        if authority_boundary.get("layer") != authority_layer:
            raise ValueError("corpus authority layer does not match registry layer")
    special_review_gate = None
    gate_payload = manifest.get("special_review_gate")
    if gate_payload is not None:
        gate_fields = frozenset(
            (
                "id",
                "ordinary_use_source_id",
                "officer_killing_source_id",
                "rooted_wealth_source_id",
                "double_wealth_source_id",
            )
        )
        gate = _closed_object(
            gate_payload,
            field_name="special_review_gate",
            allowed=gate_fields,
            required=gate_fields,
        )
        special_review_gate = SpecialReviewGatePolicy(**dict(gate))
    selected: list[Mapping[str, Any]] = []
    for chapter in _records(manifest.get("chapters"), "corpus chapters"):
        files = chapter.get("files")
        if not isinstance(files, Mapping):
            raise ValueError("corpus chapter files must be an object")
        relative_rule_path = files.get("rule_candidates")
        if relative_rule_path is None:
            continue
        rule_path = root / str(relative_rule_path)
        for record in _load_jsonl(rule_path):
            if record.get("execution_ready") is True:
                selected.append(
                    {key: record[key] for key in _RULE_DEFINITION_KEYS if key in record}
                )
    if selected:
        propositions = load_hydrated_propositions(source_manifest, corpus_path)
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
        source_bundle_digest = compiled.digest
        proposition_by_id = {item.id: item for item in propositions}
        cited_source_ids = {
            source_id
            for item in compiled.rules
            for source_id in (
                item.proposition_id,
                *item.metadata.get("supporting_source_ids", ()),
            )
        }
        if special_review_gate is not None:
            cited_source_ids.update(special_review_gate.source_ids)
        missing_gate_sources = cited_source_ids - set(proposition_by_id)
        if missing_gate_sources:
            raise ValueError(
                "registry source policy references missing propositions: "
                f"{sorted(missing_gate_sources)}"
            )
        source_provenance = tuple(
            _source_provenance(proposition_by_id[source_id])
            for source_id in sorted(cited_source_ids)
        )
    else:
        if special_review_gate is not None:
            raise ValueError("special review gate requires executable canonical rules")
        compiled_records = []
        source_bundle_digest = research_corpus_digest(source_manifest, corpus_path)
        source_provenance = ()
    exclusion_records = _records(
        manifest.get("lifecycle_exclusions", ()),
        "lifecycle_exclusions",
    )
    exclusion_fields = frozenset(("candidate_id", "reason", "source_ids", "pattern_id"))
    required_exclusion_fields = exclusion_fields - {"pattern_id"}
    exclusions = tuple(
        RegistryExclusion(
            **dict(
                _closed_object(
                    item,
                    field_name=f"lifecycle_exclusions[{index}]",
                    allowed=exclusion_fields,
                    required=required_exclusion_fields,
                )
            )
        )
        for index, item in enumerate(exclusion_records)
    )
    return registry_from_records(
        bundle_id,
        compiled_records,
        authority_layer=authority_layer,
        source_bundle_digest=source_bundle_digest,
        exclusions=exclusions,
        special_review_gate=special_review_gate,
        source_provenance=source_provenance,
    )


def compile_research_direct_officer_registry(project_root: str | Path) -> RuleRegistry:
    """Compatibility wrapper for the reviewed canonical Shen corpus."""

    return compile_research_registry(
        project_root,
        bundle_id="zzq-shen-canonical-v1",
        authority_layer="shen_core",
    )


__all__ = [
    "ATTESTATION_BUNDLE_VERSION",
    "ExampleAttestation",
    "ExampleAttestationBundle",
    "LIFECYCLE_STAGES",
    "REGISTRY_VERSION",
    "TASK4_SHADOW_BUNDLE_DIGEST",
    "TASK4_SHADOW_BUNDLE_ID",
    "TASK4_SHADOW_RESOURCE",
    "TASK4_SHADOW_RESOURCE_SHA256",
    "RegistryExclusion",
    "RegistryRule",
    "RegistrySourceProvenance",
    "RegistrySourceSegment",
    "RegistrySupportLocator",
    "RuleRegistry",
    "SpecialReviewGatePolicy",
    "attestation_bundle_from_data",
    "compile_research_registry",
    "compile_research_direct_officer_registry",
    "load_packaged_attestation_bundle",
    "load_packaged_registry",
    "load_packaged_shen_registry",
    "load_packaged_task4_shadow_registry",
    "registry_from_data",
    "registry_from_records",
    "registry_to_data",
]
