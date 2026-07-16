"""Typed contracts for source-backed BaZi facts and rules."""

from __future__ import annotations

import math
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass, field, fields, is_dataclass
from enum import Enum
from numbers import Real
from types import MappingProxyType
from typing import Any, Literal, Mapping
from urllib.parse import urlparse


SCHEMA_VERSION = "bazi-rule-schema-v2"


class TruthValue(str, Enum):
    TRUE = "true"
    FALSE = "false"
    UNKNOWN = "unknown"


PillarPosition = Literal["year", "month", "day", "hour"]
QiLevel = Literal["main", "secondary", "residual"]


@dataclass(frozen=True)
class PillarFact:
    position: PillarPosition
    label: str
    stem: str | None
    branch: str | None
    known: bool = True


@dataclass(frozen=True)
class DayMasterFact:
    stem: str
    element: str


@dataclass(frozen=True)
class MonthQiFact:
    level: QiLevel
    stem: str
    element: str
    ten_god: str


@dataclass(frozen=True)
class MonthCommandFact:
    branch: str
    qi: tuple[MonthQiFact, ...]

    def at(self, level: str) -> tuple[MonthQiFact, ...]:
        if level == "any":
            return self.qi
        return tuple(item for item in self.qi if item.level == level)


@dataclass(frozen=True)
class OccurrenceFact:
    id: str
    position: PillarPosition
    layer: Literal["stem", "hidden"]
    stem: str
    element: str
    ten_god: str
    exposed: bool
    qi_level: QiLevel | None
    is_day_master: bool = False


@dataclass(frozen=True)
class RootFact:
    id: str
    position: PillarPosition
    stem: str
    element: str
    mode: Literal["exact_stem", "same_element"]
    qi_level: QiLevel


@dataclass(frozen=True)
class RelationMember:
    position: PillarPosition
    layer: Literal["stem", "branch"]
    value: str
    role: Literal["participant", "controller", "controlled"] = "participant"
    occurrence_id: str | None = None
    element: str | None = None
    ten_god: str | None = None


@dataclass(frozen=True)
class RelationFact:
    id: str
    relation_type: str
    layer: Literal["stem", "branch"]
    members: tuple[RelationMember, ...]
    result_element: str | None = None
    position_distance: int = 0
    intervening_positions: tuple[PillarPosition, ...] = ()
    adjacent: bool = False


@dataclass(frozen=True)
class CombinationFact:
    id: str
    kind: Literal["stem_combine", "branch_six_combine", "trine", "meeting"]
    members: tuple[RelationMember, ...]
    required_values: tuple[str, ...]
    result_element: str | None
    complete: bool = True


@dataclass(frozen=True)
class CompletenessFact:
    chart_complete: bool
    hour_known: bool
    uncertain_positions: frozenset[PillarPosition] = frozenset()
    uncertainty_reason: str | None = None


@dataclass(frozen=True)
class BaziFactGraph:
    schema_version: str
    primitives_version: str
    pillars: tuple[PillarFact, ...]
    day_master: DayMasterFact
    month_command: MonthCommandFact
    occurrences: tuple[OccurrenceFact, ...]
    roots: tuple[RootFact, ...]
    relations: tuple[RelationFact, ...]
    combinations: tuple[CombinationFact, ...]
    completeness: CompletenessFact
    digest: str

    def pillar(self, position: PillarPosition) -> PillarFact:
        return next(item for item in self.pillars if item.position == position)


@dataclass(frozen=True)
class BaziFactEnvelope:
    """A finite set of complete candidate worlds for uncertain input."""

    worlds: tuple[BaziFactGraph, ...]
    digest: str


@dataclass(frozen=True)
class ActivationFact:
    """A derived activation claim kept outside the judgment-free fact graph."""

    subject_id: str
    god: str | None
    god_family: Literal["peer", "output", "wealth", "officer", "seal"]
    origin: Literal[
        "month_command_main",
        "exposed_stem",
        "source_rule",
        "complete_combination_pending",
    ]
    truth: TruthValue


@dataclass(frozen=True)
class RuleEvaluationContext:
    graph: BaziFactGraph | BaziFactEnvelope
    activations: tuple[ActivationFact, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "activations", tuple(self.activations))


@dataclass(frozen=True)
class SourceWitness:
    id: str
    sha256: str
    production_use_allowed: bool
    rights_status: str
    rights: Mapping[str, Any] = field(default_factory=dict)
    authority_roles: tuple[str, ...] = ()
    relation: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _identifier(self.id, "witness id"))
        object.__setattr__(
            self,
            "rights_status",
            _identifier(self.rights_status, "witness rights_status"),
        )
        rights = dict(self.rights)
        if "status" in rights:
            rights["status"] = _identifier(rights["status"], "witness rights.status")
        object.__setattr__(self, "rights", _deep_freeze(rights))
        object.__setattr__(
            self,
            "authority_roles",
            tuple(
                sorted(
                    {
                        _identifier(item, "witness authority_role")
                        for item in self.authority_roles
                    }
                )
            ),
        )
        object.__setattr__(
            self,
            "relation",
            _identifier(self.relation, "witness relation", allow_empty=True),
        )


@dataclass(frozen=True)
class SourceLocator:
    id: str
    witness_id: str
    quote: str
    quote_sha256: str
    visually_verified: bool
    review_state: str
    pdf_page: int | None = None
    printed_page: str | None = None
    column_line: str | None = None
    url: str | None = None
    bbox: tuple[float, ...] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _identifier(self.id, "locator id"))
        object.__setattr__(
            self, "witness_id", _identifier(self.witness_id, "locator witness_id")
        )
        object.__setattr__(
            self,
            "review_state",
            _identifier(self.review_state, "locator review_state"),
        )
        if self.pdf_page is not None and (
            type(self.pdf_page) is not int or self.pdf_page <= 0
        ):
            raise ValueError("locator pdf_page must be a positive integer")
        for name in ("printed_page", "column_line"):
            value = getattr(self, name)
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ValueError(f"locator {name} must be a non-blank string")
        if self.bbox is not None:
            try:
                values = tuple(self.bbox)
            except TypeError as exc:
                raise TypeError("locator bbox must contain four numbers") from exc
            if len(values) != 4 or any(
                isinstance(item, bool) or not isinstance(item, Real) for item in values
            ):
                raise ValueError(
                    "locator bbox must contain four finite real non-boolean numbers"
                )
            try:
                normalized_bbox = tuple(float(item) for item in values)
            except (OverflowError, TypeError, ValueError) as exc:
                raise ValueError(
                    "locator bbox must contain four finite real non-boolean numbers"
                ) from exc
            if any(not math.isfinite(item) for item in normalized_bbox):
                raise ValueError("locator bbox must contain four finite numbers")
            object.__setattr__(self, "bbox", normalized_bbox)
        if self.url is not None:
            if not isinstance(self.url, str) or not self.url.strip():
                raise ValueError("locator URL must be a non-blank string")
            if any(
                character.isspace() or ord(character) <= 0x20 or ord(character) == 0x7F
                for character in self.url
            ):
                raise ValueError("locator URL cannot contain whitespace or controls")
            try:
                parsed_url = urlparse(self.url)
                host = parsed_url.hostname
                parsed_url.port
            except ValueError as exc:
                raise ValueError(
                    "locator URL must be absolute HTTP(S) with a host"
                ) from exc
            if parsed_url.scheme.lower() not in {"http", "https"} or not host:
                raise ValueError("locator URL must be absolute HTTP(S) with a host")
        if not any(
            (
                self.pdf_page is not None,
                self.printed_page is not None,
                self.column_line is not None,
                self.bbox is not None,
                self.url is not None,
            )
        ):
            raise ValueError("locator has no meaningful source coordinate")


@dataclass(frozen=True)
class SourceSegment:
    id: str
    diplomatic_text: str
    locator_ids: tuple[str, ...]
    layer: str
    text_type: str
    review_state: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _identifier(self.id, "segment id"))
        object.__setattr__(self, "layer", _identifier(self.layer, "segment layer"))
        object.__setattr__(
            self,
            "text_type",
            _identifier(self.text_type, "segment text_type"),
        )
        object.__setattr__(
            self,
            "review_state",
            _identifier(self.review_state, "segment review_state"),
        )
        object.__setattr__(
            self,
            "locator_ids",
            tuple(_identifier(item, "segment locator_id") for item in self.locator_ids),
        )
        if len(set(self.locator_ids)) != len(self.locator_ids):
            raise ValueError(f"segment {self.id} has duplicate locator_ids")


@dataclass(frozen=True)
class Proposition:
    id: str
    atomic_claim: str
    layer: str
    text_type: str
    explicit_conditions: tuple[str, ...]
    inferred_conditions: tuple[str, ...]
    exceptions: tuple[str, ...]
    segment_ids: tuple[str, ...]
    locator_ids: tuple[str, ...]
    locators: tuple[SourceLocator, ...]
    segments: tuple[SourceSegment, ...]
    witnesses: tuple[SourceWitness, ...]
    source_manifest_digest: str
    corpus_manifest_digest: str
    corpus_artifact_digest: str
    production_eligible: bool
    review_state: str
    chapter_id: str = ""
    context_locators: tuple[SourceLocator, ...] = ()
    context_witnesses: tuple[SourceWitness, ...] = ()

    def __post_init__(self) -> None:
        # A proposition is the complete hydrated provenance snapshot carried by
        # a compiled rule.  Copy every caller-owned collection at the boundary
        # so later mutation cannot silently diverge the evidence from the
        # bundle digest.
        object.__setattr__(self, "id", _identifier(self.id, "proposition id"))
        object.__setattr__(self, "layer", _identifier(self.layer, "proposition layer"))
        object.__setattr__(
            self,
            "text_type",
            _identifier(self.text_type, "proposition text_type"),
        )
        object.__setattr__(
            self,
            "review_state",
            _identifier(self.review_state, "proposition review_state"),
        )
        for name in (
            "explicit_conditions",
            "inferred_conditions",
            "exceptions",
        ):
            raw_conditions = getattr(self, name)
            if isinstance(raw_conditions, (str, bytes)) or not isinstance(
                raw_conditions, Sequence
            ):
                raise TypeError(f"proposition {name} must be a sequence of strings")
            normalized_conditions: list[str] = []
            for index, item in enumerate(tuple(raw_conditions)):
                if not isinstance(item, str):
                    raise TypeError(f"proposition {name}[{index}] must be a string")
                if not item.strip():
                    raise ValueError(f"proposition {name}[{index}] cannot be blank")
                normalized_conditions.append(unicodedata.normalize("NFC", item))
            object.__setattr__(self, name, tuple(normalized_conditions))
        for name in (
            "locators",
            "segments",
            "witnesses",
            "context_locators",
            "context_witnesses",
        ):
            object.__setattr__(self, name, tuple(getattr(self, name)))
        for name in ("witnesses", "context_witnesses"):
            seen_witness_ids: set[str] = set()
            for witness in getattr(self, name):
                if not isinstance(witness, SourceWitness):
                    raise TypeError(
                        f"proposition {name} must contain SourceWitness records"
                    )
                if witness.id in seen_witness_ids:
                    raise ValueError(
                        f"proposition {self.id} has duplicate witness id: {witness.id}"
                    )
                seen_witness_ids.add(witness.id)
        object.__setattr__(
            self,
            "segment_ids",
            tuple(
                _identifier(item, "proposition segment_id") for item in self.segment_ids
            ),
        )
        object.__setattr__(
            self,
            "locator_ids",
            tuple(
                _identifier(item, "proposition locator_id") for item in self.locator_ids
            ),
        )
        object.__setattr__(
            self,
            "chapter_id",
            _identifier(self.chapter_id, "proposition chapter_id", allow_empty=True),
        )


@dataclass(frozen=True)
class PredicateNode:
    operator: str
    arguments: Mapping[str, Any] = field(default_factory=dict)
    children: tuple["PredicateNode", ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "arguments", _deep_freeze(dict(self.arguments)))
        object.__setattr__(self, "children", tuple(self.children))


@dataclass(frozen=True)
class RuleDefinition:
    id: str
    proposition_id: str
    predicate: PredicateNode | Mapping[str, Any]
    effect: str
    resolution_slot: str
    precedence: int | None
    after: tuple[str, ...] = ()
    before: tuple[str, ...] = ()
    execution_ready: bool = True
    production_eligible: bool = True
    semantic_status: str = "resolved"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Parse at the construction boundary.  Besides validating the closed
        # DSL, this copies and canonicalizes caller-owned dict/list input into
        # an immutable PredicateNode before compilation retains it.
        from iching.core.bazi_rules.predicates import parse_predicate

        object.__setattr__(
            self,
            "id",
            _identifier(self.id, "rule id"),
        )
        object.__setattr__(
            self,
            "proposition_id",
            _identifier(self.proposition_id, "rule proposition id"),
        )
        object.__setattr__(
            self,
            "resolution_slot",
            _identifier(self.resolution_slot, "rule resolution slot"),
        )
        object.__setattr__(self, "effect", _identifier(self.effect, "rule effect"))
        object.__setattr__(
            self,
            "semantic_status",
            _identifier(self.semantic_status, "rule semantic_status", allow_empty=True),
        )
        object.__setattr__(self, "predicate", parse_predicate(self.predicate))
        object.__setattr__(
            self,
            "after",
            tuple(_identifier(item, "rule after id") for item in self.after),
        )
        object.__setattr__(
            self,
            "before",
            tuple(_identifier(item, "rule before id") for item in self.before),
        )
        object.__setattr__(self, "metadata", _deep_freeze(dict(self.metadata)))


@dataclass(frozen=True)
class CompiledRule:
    id: str
    proposition_id: str
    predicate: PredicateNode
    effect: str
    resolution_slot: str
    precedence: int
    after: tuple[str, ...]
    before: tuple[str, ...]
    proposition: Proposition
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _identifier(self.id, "compiled rule id"))
        object.__setattr__(
            self,
            "proposition_id",
            _identifier(self.proposition_id, "compiled proposition_id"),
        )
        object.__setattr__(self, "effect", _identifier(self.effect, "compiled effect"))
        object.__setattr__(
            self,
            "resolution_slot",
            _identifier(self.resolution_slot, "compiled resolution_slot"),
        )
        object.__setattr__(
            self,
            "after",
            tuple(_identifier(item, "compiled after id") for item in self.after),
        )
        object.__setattr__(
            self,
            "before",
            tuple(_identifier(item, "compiled before id") for item in self.before),
        )
        object.__setattr__(self, "metadata", _deep_freeze(dict(self.metadata)))


@dataclass(frozen=True)
class EvaluationTrace:
    operator: str
    truth: TruthValue
    details: Mapping[str, Any]
    children: tuple["EvaluationTrace", ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "details", _deep_freeze(dict(self.details)))
        object.__setattr__(self, "children", tuple(self.children))

    def as_dict(self) -> dict[str, Any]:
        return {
            "operator": self.operator,
            "truth": self.truth.value,
            "details": _plain(self.details),
            "children": [child.as_dict() for child in self.children],
        }


@dataclass(frozen=True)
class EvaluationResult:
    truth: TruthValue
    trace: EvaluationTrace


@dataclass(frozen=True)
class RuleEvaluation:
    rule_id: str
    proposition_id: str
    effect: str
    truth: TruthValue
    trace: EvaluationTrace


@dataclass(frozen=True)
class CompiledRuleBundle:
    compiler_version: str
    schema_version: str
    primitives_version: str
    digest: str
    rules: tuple[CompiledRule, ...]
    source_manifest_digests: tuple[str, ...]
    corpus_manifest_digests: tuple[str, ...]
    corpus_artifact_digests: tuple[str, ...]

    def evaluate(
        self, graph: BaziFactGraph | BaziFactEnvelope | RuleEvaluationContext
    ) -> tuple[RuleEvaluation, ...]:
        from iching.core.bazi_rules.predicates import evaluate_predicate

        return tuple(
            RuleEvaluation(
                rule_id=rule.id,
                proposition_id=rule.proposition_id,
                effect=rule.effect,
                truth=(result := evaluate_predicate(rule.predicate, graph)).truth,
                trace=result.trace,
            )
            for rule in self.rules
        )


def _plain(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {item.name: _plain(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list, set, frozenset)):
        return [_plain(item) for item in value]
    return value


def _deep_freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {key: _deep_freeze(item) for key, item in value.items()}
        )
    if isinstance(value, (tuple, list)):
        return tuple(_deep_freeze(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_deep_freeze(item) for item in value)
    return value


def _identifier(value: Any, field: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field} must be a string")
    normalized = unicodedata.normalize("NFC", value)
    if not allow_empty and not normalized.strip():
        raise ValueError(f"{field} cannot be blank")
    return normalized
