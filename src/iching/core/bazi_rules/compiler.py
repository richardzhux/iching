"""Source hydration and deterministic compilation for BaZi rules."""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

from iching.core.bazi_rules.predicates import (
    parse_predicate,
    predicate_to_canonical_data,
)
from iching.core.bazi_rules.primitives import PRIMITIVES_VERSION
from iching.core.bazi_rules.schema import (
    CompiledRule,
    CompiledRuleBundle,
    Proposition,
    RuleDefinition,
    SCHEMA_VERSION,
    SourceLocator,
    SourceSegment,
    SourceWitness,
)


COMPILER_VERSION = "bazi-rule-compiler-v1"

PRODUCTION_PROPOSITION_LAYERS = frozenset(("shen_core",))
PRODUCTION_PROPOSITION_TYPES = frozenset(("formation", "failure", "damage", "rescue"))
PRODUCTION_SEGMENT_LAYERS = frozenset(("shen_core",))
PRODUCTION_SEGMENT_TYPES = frozenset(
    (
        "formation_rule",
        "formation_rules",
        "failure_rules",
        "damage_rule",
        "damage_rules",
        "rescue_rule",
        "rescue_rules",
        "comparative_rule",
        "transformation_rule",
        "doctrine_with_analogy",
    )
)
PRODUCTION_RIGHTS_STATUSES = frozenset(
    (
        "public_domain",
        "open_license",
        "licensed",
        "permission_granted",
        "owned",
    )
)
PRODUCTION_AUTHORITY_ROLES = frozenset(
    ("canonical_textual_authority", "operational_locator", "independent_collation")
)
PROPOSITION_RECORD_FIELDS = frozenset(
    (
        "id",
        "atomic_claim",
        "layer",
        "text_type",
        "explicit_conditions",
        "inferred_conditions",
        "exceptions",
        "segment_ids",
        "locator_ids",
        "production_eligible",
        "review_state",
        "chapter_id",
    )
)


def _canonicalize(value: Any, *, path: str = "$") -> Any:
    if value is None or type(value) in {bool, int}:
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError(f"non-finite float at {path}")
        return value
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        original_keys: dict[str, str] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(f"non-string mapping key at {path}: {key!r}")
            normalized_key = unicodedata.normalize("NFC", key)
            if normalized_key in result:
                raise ValueError(
                    f"normalized key collision at {path}: {original_keys[normalized_key]!r}, {key!r}"
                )
            original_keys[normalized_key] = key
            result[normalized_key] = _canonicalize(
                item, path=f"{path}.{normalized_key}"
            )
        return result
    if isinstance(value, (list, tuple)):
        return [
            _canonicalize(item, path=f"{path}[{index}]")
            for index, item in enumerate(value)
        ]
    if isinstance(value, (set, frozenset)):
        raise ValueError(f"sets are not canonical JSON at {path}")
    if hasattr(value, "value") and isinstance(getattr(value, "value"), str):
        return unicodedata.normalize("NFC", value.value)
    raise ValueError(f"non-JSON value at {path}: {type(value).__name__}")


def canonical_json_bytes(value: Any) -> bytes:
    text = json.dumps(
        _canonicalize(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return text.encode("utf-8")


def canonical_digest(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _exact_quote_digest(quote: str) -> str:
    return hashlib.sha256(quote.encode("utf-8")).hexdigest()


def _require_digest(value: str, field: str) -> None:
    if len(value) != 64 or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise ValueError(f"{field} must be a lowercase SHA-256 digest")


def _require_bool(value: Any, field: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{field} must be a boolean")
    return value


def _require_string(
    value: Any,
    field: str,
    *,
    allow_empty: bool = False,
    identifier: bool = False,
) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    result = unicodedata.normalize("NFC", value) if identifier else value
    if not allow_empty and not result.strip():
        raise ValueError(f"{field} cannot be blank")
    return result


def _require_string_sequence(
    value: Any,
    field: str,
    *,
    identifier: bool = False,
) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ValueError(f"{field} must be a sequence of strings")
    return tuple(
        _require_string(item, f"{field}[{index}]", identifier=identifier)
        for index, item in enumerate(value)
    )


def _optional_positive_int(value: Any, field: str) -> int | None:
    if value is None:
        return None
    if type(value) is not int or value <= 0:
        raise ValueError(f"{field} must be a positive integer")
    return value


def _id_addressed_records(value: Any, field: str) -> tuple[Mapping[str, Any], ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ValueError(f"{field} must be an array of ID-addressed objects")
    by_id: dict[str, Mapping[str, Any]] = {}
    for index, record in enumerate(value):
        if not isinstance(record, Mapping):
            raise ValueError(f"{field}[{index}] must be an object")
        record_id = _require_string(
            record.get("id"), f"{field}[{index}] id", identifier=True
        )
        if record_id in by_id:
            raise ValueError(f"duplicate {field} id: {record_id}")
        by_id[record_id] = record
    return tuple(by_id[record_id] for record_id in sorted(by_id))


def _semantic_manifest_digest(
    manifest: Mapping[str, Any], *, id_addressed_fields: tuple[str, ...]
) -> str:
    """Digest a manifest while canonicalizing only explicitly ID-addressed arrays."""

    payload = dict(manifest)
    for field in id_addressed_fields:
        if field in payload:
            payload[field] = list(_id_addressed_records(payload[field], field))
    return canonical_digest(payload)


def _source_manifest_digest_payload(
    source_manifest: Mapping[str, Any],
) -> Mapping[str, Any]:
    payload = dict(source_manifest)
    if "witnesses" not in payload:
        return payload
    witnesses: list[Mapping[str, Any]] = []
    for index, raw in enumerate(payload["witnesses"]):
        if not isinstance(raw, Mapping):
            raise ValueError(f"witnesses[{index}] must be an object")
        witness = dict(raw)
        if "authority_roles" in witness:
            witness["authority_roles"] = sorted(
                set(
                    _require_string_sequence(
                        witness["authority_roles"],
                        f"witnesses[{index}] authority_roles",
                        identifier=True,
                    )
                )
            )
        witnesses.append(witness)
    payload["witnesses"] = witnesses
    return payload


def _unique_records(records: Sequence[Any], *, kind: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for record in records:
        raw_id = record.id if hasattr(record, "id") else record.get("id", "")
        record_id = _require_string(raw_id, f"{kind} id", identifier=True)
        if record_id in result:
            raise ValueError(f"duplicate {kind} id: {record_id}")
        result[record_id] = record
    return result


def _reject_duplicate_object_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate object key: {key!r}")
        result[key] = value
    return result


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle, object_pairs_hook=_reject_duplicate_object_keys)


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.endswith("\n"):
                raise ValueError(
                    f"JSONL record lacks terminal newline: {path}:{line_number}"
                )
            if not line.strip():
                raise ValueError(f"blank JSONL line: {path}:{line_number}")
            value = json.loads(
                line,
                object_pairs_hook=_reject_duplicate_object_keys,
            )
            if not isinstance(value, dict):
                raise ValueError(
                    f"JSONL record must be an object: {path}:{line_number}"
                )
            records.append(value)
    return records


def _source_witnesses(source_manifest: Mapping[str, Any]) -> tuple[SourceWitness, ...]:
    records: list[SourceWitness] = []
    for raw in source_manifest.get("witnesses", ()):
        rights = raw.get("rights", {})
        if not isinstance(rights, Mapping):
            raise ValueError(f"witness {raw.get('id')} rights must be an object")
        raw_roles = raw.get("authority_roles")
        if raw_roles is None:
            authority_role = raw.get("authority_role")
            raw_roles = (authority_role,) if authority_role is not None else ()
        authority_roles = _require_string_sequence(
            raw_roles,
            f"witness {raw.get('id')} authority_roles",
            identifier=True,
        )
        records.append(
            SourceWitness(
                id=_require_string(raw.get("id"), "witness id", identifier=True),
                sha256=_require_string(
                    raw.get("sha256"), f"witness {raw.get('id')} sha256"
                ),
                production_use_allowed=_require_bool(
                    rights.get("production_use_allowed", False),
                    f"witness {raw.get('id')} rights.production_use_allowed",
                ),
                rights_status=_require_string(
                    rights.get("status"),
                    f"witness {raw.get('id')} rights.status",
                    identifier=True,
                ),
                rights=dict(rights),
                authority_roles=authority_roles,
                relation=_require_string(
                    raw.get("relation", ""),
                    f"witness {raw.get('id')} relation",
                    allow_empty=True,
                    identifier=True,
                ),
            )
        )
    _unique_records(records, kind="witness")
    return tuple(records)


def _source_locators(corpus_manifest: Mapping[str, Any]) -> tuple[SourceLocator, ...]:
    def bbox(raw: Any, locator_id: Any) -> tuple[float, ...] | None:
        if raw is None:
            return None
        if (
            isinstance(raw, (str, bytes))
            or not isinstance(raw, Sequence)
            or len(raw) != 4
        ):
            raise ValueError(f"locator {locator_id} bbox must contain four numbers")
        if any(
            type(item) not in {int, float} or isinstance(item, bool) for item in raw
        ):
            raise ValueError(f"locator {locator_id} bbox must contain four numbers")
        result = tuple(float(item) for item in raw)
        if any(not math.isfinite(item) for item in result):
            raise ValueError(f"locator {locator_id} bbox must contain finite numbers")
        return result

    records = tuple(
        SourceLocator(
            id=_require_string(raw.get("id"), "locator id", identifier=True),
            witness_id=_require_string(
                raw.get("witness_id"),
                f"locator {raw.get('id')} witness_id",
                identifier=True,
            ),
            quote=_require_string(raw.get("quote"), f"locator {raw.get('id')} quote"),
            quote_sha256=_require_string(
                raw.get("quote_sha256"),
                f"locator {raw.get('id')} quote_sha256",
            ),
            visually_verified=_require_bool(
                raw.get("visually_verified", False),
                f"locator {raw.get('id')} visually_verified",
            ),
            review_state=_require_string(
                raw.get("review_state"),
                f"locator {raw.get('id')} review_state",
                identifier=True,
            ),
            pdf_page=_optional_positive_int(
                raw.get("pdf_page"),
                f"locator {raw.get('id')} pdf_page",
            ),
            printed_page=_require_string(
                raw["printed_page"],
                f"locator {raw.get('id')} printed_page",
            )
            if raw.get("printed_page") is not None
            else None,
            column_line=_require_string(
                raw["column_line"],
                f"locator {raw.get('id')} column_line",
            )
            if raw.get("column_line") is not None
            else None,
            url=_require_string(raw["url"], f"locator {raw.get('id')} url")
            if raw.get("url") is not None
            else None,
            bbox=bbox(raw.get("bbox"), raw.get("id")),
        )
        for raw in corpus_manifest.get("locators", ())
    )
    _unique_records(records, kind="locator")
    return records


def _source_segments(records: Sequence[Mapping[str, Any]]) -> tuple[SourceSegment, ...]:
    result = tuple(
        SourceSegment(
            id=_require_string(raw.get("id"), "segment id", identifier=True),
            diplomatic_text=_require_string(
                raw.get("diplomatic_text"),
                f"segment {raw.get('id')} diplomatic_text",
            ),
            locator_ids=_require_string_sequence(
                raw.get("locator_ids", ()),
                f"segment {raw.get('id')} locator_ids",
                identifier=True,
            ),
            layer=_require_string(
                raw.get("layer"), f"segment {raw.get('id')} layer", identifier=True
            ),
            text_type=_require_string(
                raw.get("text_type"),
                f"segment {raw.get('id')} text_type",
                identifier=True,
            ),
            review_state=_require_string(
                raw.get("review_state"),
                f"segment {raw.get('id')} review_state",
                identifier=True,
            ),
        )
        for raw in records
    )
    _unique_records(result, kind="segment")
    return result


def _validated_locator_witness(
    locator: SourceLocator,
    witness_map: Mapping[str, SourceWitness],
) -> SourceWitness:
    if not isinstance(locator.quote, str) or not locator.quote.strip():
        raise ValueError(f"locator {locator.id} quote cannot be blank")
    _require_digest(locator.quote_sha256, f"locator {locator.id} quote_sha256")
    if _exact_quote_digest(locator.quote) != locator.quote_sha256:
        raise ValueError(f"locator {locator.id} quote hash mismatch")
    witness = witness_map.get(locator.witness_id)
    if witness is None:
        raise ValueError(
            f"locator {locator.id} references unknown witness {locator.witness_id}"
        )
    _require_digest(witness.sha256, f"witness {witness.id} sha256")
    return witness


def _witness_snapshot_for_locators(
    locators: Sequence[SourceLocator],
    validated_witnesses: Mapping[str, SourceWitness],
) -> tuple[SourceWitness, ...]:
    by_id: dict[str, SourceWitness] = {}
    for locator in locators:
        witness = validated_witnesses[locator.id]
        by_id.setdefault(witness.id, witness)
    return tuple(by_id.values())


def hydrate_propositions(
    records: Sequence[Mapping[str, Any]],
    *,
    witnesses: Sequence[SourceWitness],
    locators: Sequence[SourceLocator],
    segments: Sequence[SourceSegment],
    source_manifest_digest: str,
    corpus_manifest_digest: str,
    corpus_artifact_digest: str,
) -> tuple[Proposition, ...]:
    """Resolve every proposition reference before it can reach compilation."""

    record_snapshot = tuple(records)
    witness_snapshot = tuple(witnesses)
    locator_snapshot = tuple(locators)
    segment_snapshot = tuple(segments)
    _require_digest(source_manifest_digest, "source_manifest_digest")
    _require_digest(corpus_manifest_digest, "corpus_manifest_digest")
    _require_digest(corpus_artifact_digest, "corpus_artifact_digest")
    witness_map = _unique_records(witness_snapshot, kind="witness")
    locator_map = _unique_records(locator_snapshot, kind="locator")
    segment_map = _unique_records(segment_snapshot, kind="segment")
    for index, raw in enumerate(record_snapshot):
        if not isinstance(raw, Mapping):
            raise ValueError(f"proposition record {index} must be an object")
        if any(not isinstance(key, str) for key in raw):
            raise ValueError(f"proposition record {index} fields must use string keys")
        extras = set(raw) - PROPOSITION_RECORD_FIELDS
        if extras:
            raise ValueError(
                f"proposition {raw.get('id', '<unknown>')} has unknown fields: {sorted(extras)}"
            )
    _unique_records(record_snapshot, kind="proposition")
    validated_witnesses: dict[str, SourceWitness] = {}
    for segment in segment_snapshot:
        for locator_id in segment.locator_ids:
            locator = locator_map.get(locator_id)
            if locator is None:
                raise ValueError(
                    f"segment {segment.id} references unknown locator {locator_id}"
                )
            validated_witnesses[locator.id] = _validated_locator_witness(
                locator, witness_map
            )
    hydrated: list[Proposition] = []
    for raw in record_snapshot:
        proposition_id = _require_string(
            raw.get("id"), "proposition id", identifier=True
        )
        segment_ids = _require_string_sequence(
            raw.get("segment_ids", ()),
            f"proposition {proposition_id} segment_ids",
            identifier=True,
        )
        locator_ids = _require_string_sequence(
            raw.get("locator_ids", ()),
            f"proposition {proposition_id} locator_ids",
            identifier=True,
        )
        if len(segment_ids) != len(set(segment_ids)):
            raise ValueError(f"proposition {proposition_id} has duplicate segment_ids")
        if len(locator_ids) != len(set(locator_ids)):
            raise ValueError(f"proposition {proposition_id} has duplicate locator_ids")
        if not segment_ids or not locator_ids:
            raise ValueError(
                f"proposition {proposition_id} has no source segments/locators"
            )
        try:
            resolved_segments = tuple(segment_map[item] for item in segment_ids)
        except KeyError as exc:
            raise ValueError(
                f"proposition {proposition_id} references unknown segment {exc.args[0]}"
            ) from exc
        try:
            resolved_locators = tuple(locator_map[item] for item in locator_ids)
        except KeyError as exc:
            raise ValueError(
                f"proposition {proposition_id} references unknown locator {exc.args[0]}"
            ) from exc
        segment_locator_ids = {
            item for segment in resolved_segments for item in segment.locator_ids
        }
        outside = set(locator_ids) - segment_locator_ids
        if outside:
            raise ValueError(
                f"proposition {proposition_id} locators are not contained in referenced segments: {sorted(outside)}"
            )
        ordered_segment_locator_ids = tuple(
            dict.fromkeys(
                locator_id
                for segment in resolved_segments
                for locator_id in segment.locator_ids
            )
        )
        context_locator_ids = tuple(
            locator_id
            for locator_id in ordered_segment_locator_ids
            if locator_id not in set(locator_ids)
        )
        context_locators = tuple(locator_map[item] for item in context_locator_ids)
        support_witnesses = _witness_snapshot_for_locators(
            resolved_locators, validated_witnesses
        )
        context_witnesses = _witness_snapshot_for_locators(
            context_locators, validated_witnesses
        )
        hydrated.append(
            Proposition(
                id=proposition_id,
                atomic_claim=_require_string(
                    raw.get("atomic_claim"),
                    f"proposition {proposition_id} atomic_claim",
                ),
                layer=_require_string(
                    raw.get("layer"),
                    f"proposition {proposition_id} layer",
                    identifier=True,
                ),
                text_type=_require_string(
                    raw.get("text_type"),
                    f"proposition {proposition_id} text_type",
                    identifier=True,
                ),
                explicit_conditions=_require_string_sequence(
                    raw.get("explicit_conditions", ()),
                    f"proposition {proposition_id} explicit_conditions",
                ),
                inferred_conditions=_require_string_sequence(
                    raw.get("inferred_conditions", ()),
                    f"proposition {proposition_id} inferred_conditions",
                ),
                exceptions=_require_string_sequence(
                    raw.get("exceptions", ()),
                    f"proposition {proposition_id} exceptions",
                ),
                segment_ids=segment_ids,
                locator_ids=locator_ids,
                locators=resolved_locators,
                segments=resolved_segments,
                witnesses=support_witnesses,
                source_manifest_digest=source_manifest_digest,
                corpus_manifest_digest=corpus_manifest_digest,
                corpus_artifact_digest=corpus_artifact_digest,
                production_eligible=_require_bool(
                    raw.get("production_eligible", False),
                    f"proposition {proposition_id} production_eligible",
                ),
                review_state=_require_string(
                    raw.get("review_state"),
                    f"proposition {proposition_id} review_state",
                    identifier=True,
                ),
                chapter_id=_require_string(
                    raw.get("chapter_id", ""),
                    f"proposition {proposition_id} chapter_id",
                    allow_empty=True,
                    identifier=True,
                ),
                context_locators=context_locators,
                context_witnesses=context_witnesses,
            )
        )
    return tuple(hydrated)


def load_hydrated_propositions(
    source_manifest_path: str | Path,
    corpus_manifest_path: str | Path,
) -> tuple[Proposition, ...]:
    """Load, digest, and hydrate all proposition shards in one corpus manifest."""

    source_path = Path(source_manifest_path)
    corpus_path = Path(corpus_manifest_path)
    source_manifest = _load_json(source_path)
    corpus_manifest = _load_json(corpus_path)
    if not isinstance(source_manifest, Mapping):
        raise ValueError("source manifest must be an object")
    if not isinstance(corpus_manifest, Mapping):
        raise ValueError("corpus manifest must be an object")
    source_digest = _semantic_manifest_digest(
        _source_manifest_digest_payload(source_manifest),
        id_addressed_fields=("witnesses", "search_aids"),
    )
    corpus_digest = _semantic_manifest_digest(
        corpus_manifest,
        id_addressed_fields=("locators", "chapters", "witness_variants"),
    )
    root = (
        corpus_path.parents[3]
        if corpus_path.parts[-3:] == ("classics", "ziping_zhenquan", "manifest.json")
        else Path.cwd()
    )
    # Paths in the checked-in manifest are repository-relative. Locate the
    # repository root by walking upward when a caller supplies an absolute path.
    for candidate in (corpus_path.parent, *corpus_path.parents):
        if (candidate / "research" / "classics").is_dir():
            root = candidate
            break
    artifact_records: list[dict[str, Any]] = []
    segment_records: list[dict[str, Any]] = []
    proposition_records: list[dict[str, Any]] = []
    raw_chapters = corpus_manifest.get("chapters", ())
    _id_addressed_records(raw_chapters, "chapters")
    chapters = tuple(raw_chapters)
    for chapter in chapters:
        files = chapter.get("files", {})
        if not isinstance(files, Mapping):
            raise ValueError(f"chapter {chapter.get('id')} files must be an object")
        for role, relative in sorted(files.items()):
            path = root / str(relative)
            records = _load_jsonl(path)
            artifact_records.append(
                {"path": str(relative), "role": role, "records": records}
            )
            if role == "segments":
                segment_records.extend(records)
            elif role == "propositions":
                proposition_records.extend(records)
    artifact_digest = canonical_digest(
        sorted(artifact_records, key=lambda item: (item["path"], item["role"]))
    )
    return hydrate_propositions(
        proposition_records,
        witnesses=_source_witnesses(source_manifest),
        locators=_source_locators(corpus_manifest),
        segments=_source_segments(segment_records),
        source_manifest_digest=source_digest,
        corpus_manifest_digest=corpus_digest,
        corpus_artifact_digest=artifact_digest,
    )


def _coerce_rule(value: RuleDefinition | Mapping[str, Any]) -> RuleDefinition:
    if isinstance(value, RuleDefinition):
        return value
    if not isinstance(value, Mapping):
        raise TypeError("rule ingestion requires objects or RuleDefinition instances")
    if any(not isinstance(key, str) for key in value):
        raise ValueError("rule fields must use string keys")
    allowed = {
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
    }
    required = {
        "id",
        "proposition_id",
        "predicate",
        "effect",
        "resolution_slot",
        "precedence",
        "execution_ready",
        "production_eligible",
        "semantic_status",
    }
    extras = set(value) - allowed
    if extras:
        raise ValueError(
            f"rule {value.get('id', '<unknown>')} has unknown fields: {sorted(extras)}"
        )
    missing = required - set(value)
    if missing:
        raise ValueError(f"rule is missing required fields: {sorted(missing)}")
    predicate = value["predicate"]
    if not isinstance(predicate, Mapping):
        raise ValueError(f"rule {value.get('id')} predicate must be an object")
    metadata = value.get("metadata", {})
    if not isinstance(metadata, Mapping):
        raise ValueError(f"rule {value.get('id')} metadata must be an object")
    canonical_json_bytes(metadata)
    precedence = value["precedence"]
    if precedence is not None and type(precedence) is not int:
        raise ValueError(
            f"rule {value.get('id')} precedence must be an integer or null"
        )
    after = _require_string_sequence(
        value.get("after", ()),
        f"rule {value.get('id')} after",
        identifier=True,
    )
    before = _require_string_sequence(
        value.get("before", ()),
        f"rule {value.get('id')} before",
        identifier=True,
    )
    if len(set(after)) != len(after) or len(set(before)) != len(before):
        raise ValueError(f"rule {value.get('id')} has duplicate precedence references")
    return RuleDefinition(
        id=_require_string(value.get("id"), "rule id", identifier=True),
        proposition_id=_require_string(
            value.get("proposition_id"),
            f"rule {value.get('id')} proposition_id",
            identifier=True,
        ),
        predicate=predicate,
        effect=_require_string(
            value.get("effect"), f"rule {value.get('id')} effect", identifier=True
        ),
        resolution_slot=_require_string(
            value.get("resolution_slot"),
            f"rule {value.get('id')} resolution_slot",
            identifier=True,
        ),
        precedence=precedence,
        after=after,
        before=before,
        execution_ready=_require_bool(
            value.get("execution_ready", False),
            f"rule {value.get('id')} execution_ready",
        ),
        production_eligible=_require_bool(
            value.get("production_eligible", False),
            f"rule {value.get('id')} production_eligible",
        ),
        semantic_status=_require_string(
            value.get("semantic_status"),
            f"rule {value.get('id')} semantic_status",
            identifier=True,
        ),
        metadata=metadata,
    )


def _validate_proposition(proposition: Proposition) -> None:
    _require_bool(
        proposition.production_eligible,
        f"proposition {proposition.id} production_eligible",
    )
    if (
        not proposition.production_eligible
        or proposition.review_state != "scan_verified"
    ):
        raise ValueError(
            f"proposition {proposition.id} is not production eligible and scan verified"
        )
    if (
        not isinstance(proposition.atomic_claim, str)
        or not proposition.atomic_claim.strip()
    ):
        raise ValueError(f"proposition {proposition.id} atomic_claim cannot be blank")
    if proposition.layer not in PRODUCTION_PROPOSITION_LAYERS:
        raise ValueError(
            f"proposition {proposition.id} has unsupported production layer"
        )
    if proposition.text_type not in PRODUCTION_PROPOSITION_TYPES:
        raise ValueError(
            f"proposition {proposition.id} has unsupported production text_type"
        )
    for field, digest in (
        ("source_manifest_digest", proposition.source_manifest_digest),
        ("corpus_manifest_digest", proposition.corpus_manifest_digest),
        ("corpus_artifact_digest", proposition.corpus_artifact_digest),
    ):
        _require_digest(digest, field)
    if (
        not proposition.locators
        or not proposition.segments
        or not proposition.witnesses
    ):
        raise ValueError(f"proposition {proposition.id} is not hydrated")
    if tuple(item.id for item in proposition.locators) != proposition.locator_ids:
        raise ValueError(
            f"proposition {proposition.id} locator_ids do not match hydrated locators"
        )
    if tuple(item.id for item in proposition.segments) != proposition.segment_ids:
        raise ValueError(
            f"proposition {proposition.id} segment_ids do not match hydrated segments"
        )
    if len(set(proposition.locator_ids)) != len(proposition.locator_ids):
        raise ValueError(f"proposition {proposition.id} has duplicate locator_ids")
    if len(set(proposition.segment_ids)) != len(proposition.segment_ids):
        raise ValueError(f"proposition {proposition.id} has duplicate segment_ids")
    if proposition.text_type in {"example_claim", "commentary"}:
        raise ValueError(f"proposition {proposition.id} is commentary/example-only")
    forbidden_segment_types = {
        "chapter_heading",
        "classical_example",
        "cross_reference_closing",
        "methodological_closing",
    }
    if any(
        segment.text_type in forbidden_segment_types
        or segment.layer in {"example", "editorial", "commentary"}
        for segment in proposition.segments
    ):
        raise ValueError(
            f"proposition {proposition.id} references commentary/example-only source segments"
        )
    if any(
        not isinstance(segment.diplomatic_text, str)
        or not segment.diplomatic_text.strip()
        or segment.layer not in PRODUCTION_SEGMENT_LAYERS
        or segment.text_type not in PRODUCTION_SEGMENT_TYPES
        for segment in proposition.segments
    ):
        raise ValueError(
            f"proposition {proposition.id} has incomplete or unsupported production segments"
        )
    support_locator_map = _unique_records(proposition.locators, kind="support locator")
    locator_ids = set(support_locator_map)
    segment_locator_ids = {
        item for segment in proposition.segments for item in segment.locator_ids
    }
    if not locator_ids <= segment_locator_ids:
        raise ValueError(
            f"proposition {proposition.id} has locator outside its source segments"
        )
    context_locator_map = _unique_records(
        proposition.context_locators, kind="context locator"
    )
    expected_context_locator_ids = segment_locator_ids - locator_ids
    if set(context_locator_map) != expected_context_locator_ids:
        raise ValueError(
            f"proposition {proposition.id} context locators do not match its source segments"
        )
    witness_map = _unique_records(proposition.witnesses, kind="witness")
    expected_witness_ids = {locator.witness_id for locator in proposition.locators}
    if set(witness_map) != expected_witness_ids:
        raise ValueError(
            f"proposition {proposition.id} hydrated witnesses do not match locator witnesses"
        )
    context_witness_map = _unique_records(
        proposition.context_witnesses, kind="context witness"
    )
    expected_context_witness_ids = {
        locator.witness_id for locator in proposition.context_locators
    }
    if set(context_witness_map) != expected_context_witness_ids:
        raise ValueError(
            f"proposition {proposition.id} context witnesses do not match context locators"
        )
    for locator in proposition.context_locators:
        _validated_locator_witness(locator, context_witness_map)
    eligible_support_locator_ids: set[str] = set()
    for locator in proposition.locators:
        witness = _validated_locator_witness(locator, witness_map)
        _require_bool(
            locator.visually_verified, f"locator {locator.id} visually_verified"
        )
        if not locator.visually_verified or locator.review_state != "scan_verified":
            raise ValueError(f"locator {locator.id} is not visually scan verified")
        has_page = type(locator.pdf_page) is int and locator.pdf_page > 0
        has_bbox = locator.bbox is not None and len(locator.bbox) == 4
        has_printed_page = isinstance(locator.printed_page, str) and bool(
            locator.printed_page.strip()
        )
        has_column_line = isinstance(locator.column_line, str) and bool(
            locator.column_line.strip()
        )
        has_url = isinstance(locator.url, str) and bool(locator.url.strip())
        if not (has_page or has_bbox or has_printed_page or has_column_line or has_url):
            raise ValueError(
                f"locator {locator.id} has no meaningful source coordinate"
            )
        _require_bool(
            witness.production_use_allowed,
            f"witness {witness.id} production_use_allowed",
        )
        canonical_json_bytes(witness.rights)
        if (
            not witness.rights
            or witness.rights_status not in PRODUCTION_RIGHTS_STATUSES
        ):
            raise ValueError(
                f"witness {witness.id} has no resolved production rights status"
            )
        if not set(witness.authority_roles) & PRODUCTION_AUTHORITY_ROLES:
            raise ValueError(
                f"witness {witness.id} is not a production textual/locator authority"
            )
        declared_status = witness.rights.get("status")
        if declared_status != witness.rights_status:
            raise ValueError(f"witness {witness.id} rights status is inconsistent")
        declared = witness.rights.get("production_use_allowed")
        _require_bool(declared, f"witness {witness.id} rights.production_use_allowed")
        if declared is not witness.production_use_allowed:
            raise ValueError(f"witness {witness.id} rights eligibility is inconsistent")
        basis = witness.rights.get("basis")
        if (
            isinstance(basis, (str, bytes))
            or not isinstance(basis, (tuple, list))
            or not basis
        ):
            raise ValueError(f"witness {witness.id} rights basis is unresolved")
        if any(not isinstance(item, str) or not item.strip() for item in basis):
            raise ValueError(f"witness {witness.id} rights basis is unresolved")
        if not witness.production_use_allowed:
            raise ValueError(f"locator {locator.id} uses a rights-ineligible witness")
        eligible_support_locator_ids.add(locator.id)
    for segment in proposition.segments:
        if not eligible_support_locator_ids.intersection(segment.locator_ids):
            raise ValueError(f"segment {segment.id} has no production support locator")
    if any(segment.review_state != "scan_verified" for segment in proposition.segments):
        raise ValueError(
            f"proposition {proposition.id} has an unverified source segment"
        )


def _precedence_order(
    rules: Sequence[RuleDefinition],
) -> tuple[
    tuple[RuleDefinition, ...],
    Mapping[str, tuple[str, ...]],
    Mapping[str, tuple[str, ...]],
]:
    by_id = _unique_records(list(rules), kind="rule")
    outgoing: dict[str, set[str]] = {rule_id: set() for rule_id in by_id}
    incoming: dict[str, set[str]] = {rule_id: set() for rule_id in by_id}
    for rule in rules:
        if not rule.resolution_slot:
            raise ValueError(f"rule {rule.id} has no resolution_slot")
        if isinstance(rule.precedence, bool) or not isinstance(rule.precedence, int):
            raise ValueError(f"rule {rule.id} has unresolved precedence")
        for predecessor in rule.after:
            if predecessor == rule.id:
                raise ValueError(f"rule {rule.id} has self precedence")
            if predecessor not in by_id:
                raise ValueError(
                    f"rule {rule.id} references missing predecessor {predecessor}"
                )
            outgoing[predecessor].add(rule.id)
            incoming[rule.id].add(predecessor)
        for successor in rule.before:
            if successor == rule.id:
                raise ValueError(f"rule {rule.id} has self precedence")
            if successor not in by_id:
                raise ValueError(
                    f"rule {rule.id} references missing successor {successor}"
                )
            outgoing[rule.id].add(successor)
            incoming[successor].add(rule.id)
    for left_id, successors in outgoing.items():
        for right_id in successors:
            left = by_id[left_id]
            right = by_id[right_id]
            if left.resolution_slot == right.resolution_slot and int(
                left.precedence
            ) > int(right.precedence):
                raise ValueError(
                    f"precedence number contradicts edge {left_id} -> {right_id}"
                )

    ready = sorted(
        (rule_id for rule_id, dependencies in incoming.items() if not dependencies),
        key=lambda rule_id: (
            by_id[rule_id].resolution_slot,
            int(by_id[rule_id].precedence),
            rule_id,
        ),
    )
    incoming_work = {
        rule_id: set(dependencies) for rule_id, dependencies in incoming.items()
    }
    ordered_ids: list[str] = []
    while ready:
        rule_id = ready.pop(0)
        ordered_ids.append(rule_id)
        for successor in sorted(outgoing[rule_id]):
            incoming_work[successor].discard(rule_id)
            if (
                not incoming_work[successor]
                and successor not in ordered_ids
                and successor not in ready
            ):
                ready.append(successor)
        ready.sort(
            key=lambda item: (
                by_id[item].resolution_slot,
                int(by_id[item].precedence),
                item,
            )
        )
    if len(ordered_ids) != len(rules):
        cycle_ids = sorted(
            rule_id for rule_id, dependencies in incoming_work.items() if dependencies
        )
        raise ValueError(f"rule precedence cycle: {cycle_ids}")

    # Same-slot/same-number rules are a real conflict unless one is transitively
    # ordered before the other. Unrelated slots need no artificial total order.
    reachability: dict[str, set[str]] = {rule_id: set() for rule_id in by_id}
    for rule_id in reversed(ordered_ids):
        for successor in outgoing[rule_id]:
            reachability[rule_id].add(successor)
            reachability[rule_id].update(reachability[successor])
    for left_id, successors in reachability.items():
        left = by_id[left_id]
        for right_id in successors:
            right = by_id[right_id]
            if left.resolution_slot == right.resolution_slot and int(
                left.precedence
            ) > int(right.precedence):
                raise ValueError(
                    f"precedence number contradicts transitive edge {left_id} -> {right_id}"
                )
    grouped: dict[tuple[str, int], list[str]] = defaultdict(list)
    for rule in rules:
        grouped[(rule.resolution_slot, int(rule.precedence))].append(rule.id)
    for (slot, precedence), ids in grouped.items():
        for left, right in itertools.combinations(sorted(ids), 2):
            if right not in reachability[left] and left not in reachability[right]:
                raise ValueError(
                    f"unresolved same-slot conflict at {slot}/{precedence}: {left}, {right}"
                )
    # Persist graph semantics rather than declaration syntax.  Reachability
    # closure makes ``a.before=b``, ``b.after=a``, duplicate declarations, and
    # redundant transitive edges canonicalize to the same compiled bundle.
    canonical_before = {
        rule_id: tuple(sorted(reachability[rule_id])) for rule_id in by_id
    }
    canonical_after = {
        rule_id: tuple(
            sorted(
                predecessor
                for predecessor, successors in reachability.items()
                if rule_id in successors
            )
        )
        for rule_id in by_id
    }
    return (
        tuple(by_id[rule_id] for rule_id in ordered_ids),
        canonical_after,
        canonical_before,
    )


def _witness_digest_payload(witness: SourceWitness) -> dict[str, Any]:
    return {
        "id": witness.id,
        "sha256": witness.sha256,
        "production_use_allowed": witness.production_use_allowed,
        "rights_status": witness.rights_status,
        "rights": dict(witness.rights),
        "authority_roles": list(witness.authority_roles),
        "relation": witness.relation,
    }


def _locator_digest_payload(locator: SourceLocator) -> dict[str, Any]:
    return {
        "id": locator.id,
        "witness_id": locator.witness_id,
        "quote": locator.quote,
        "quote_sha256": locator.quote_sha256,
        "review_state": locator.review_state,
        "visually_verified": locator.visually_verified,
        "pdf_page": locator.pdf_page,
        "printed_page": locator.printed_page,
        "column_line": locator.column_line,
        "url": locator.url,
        "bbox": list(locator.bbox) if locator.bbox is not None else None,
    }


def _proposition_digest_payload(proposition: Proposition) -> dict[str, Any]:
    return {
        "id": proposition.id,
        "atomic_claim": proposition.atomic_claim,
        "layer": proposition.layer,
        "text_type": proposition.text_type,
        "explicit_conditions": sorted(
            unicodedata.normalize("NFC", item)
            for item in proposition.explicit_conditions
        ),
        "inferred_conditions": sorted(
            unicodedata.normalize("NFC", item)
            for item in proposition.inferred_conditions
        ),
        "exceptions": sorted(
            unicodedata.normalize("NFC", item) for item in proposition.exceptions
        ),
        "chapter_id": proposition.chapter_id,
        "segment_ids": sorted(proposition.segment_ids),
        "locator_ids": sorted(proposition.locator_ids),
        "production_eligible": proposition.production_eligible,
        "review_state": proposition.review_state,
        "witnesses": [
            _witness_digest_payload(witness)
            for witness in sorted(proposition.witnesses, key=lambda item: item.id)
        ],
        "context_witnesses": [
            _witness_digest_payload(witness)
            for witness in sorted(
                proposition.context_witnesses, key=lambda item: item.id
            )
        ],
        "segments": [
            {
                "id": segment.id,
                "diplomatic_text": segment.diplomatic_text,
                "locator_ids": sorted(segment.locator_ids),
                "layer": segment.layer,
                "text_type": segment.text_type,
                "review_state": segment.review_state,
            }
            for segment in sorted(proposition.segments, key=lambda item: item.id)
        ],
        "locators": [
            _locator_digest_payload(locator)
            for locator in sorted(proposition.locators, key=lambda item: item.id)
        ],
        "context_locators": [
            _locator_digest_payload(locator)
            for locator in sorted(
                proposition.context_locators, key=lambda item: item.id
            )
        ],
        "source_manifest_digest": proposition.source_manifest_digest,
        "corpus_manifest_digest": proposition.corpus_manifest_digest,
        "corpus_artifact_digest": proposition.corpus_artifact_digest,
    }


def ingest_rule_definitions(
    records: Sequence[RuleDefinition | Mapping[str, Any]],
) -> tuple[RuleDefinition, ...]:
    """Strictly ingest sequence records before any ID can be overwritten."""

    record_snapshot = tuple(records)
    rules = tuple(_coerce_rule(item) for item in record_snapshot)
    _unique_records(rules, kind="rule")
    return rules


def index_hydrated_propositions(
    records: Sequence[Proposition],
) -> dict[str, Proposition]:
    """Index a hydrated sequence only after duplicate-ID validation."""

    record_snapshot = tuple(records)
    if any(not isinstance(item, Proposition) for item in record_snapshot):
        raise TypeError("proposition ingestion requires hydrated Proposition records")
    return _unique_records(record_snapshot, kind="proposition")


def compile_rule_records(
    definitions: Sequence[RuleDefinition | Mapping[str, Any]],
    propositions: Sequence[Proposition],
) -> CompiledRuleBundle:
    """Ingestion boundary for raw rule records and proposition sequences."""

    return compile_rule_bundle(
        ingest_rule_definitions(definitions),
        index_hydrated_propositions(propositions),
    )


def compile_rule_bundle(
    definitions: Sequence[RuleDefinition],
    propositions: Mapping[str, Proposition],
) -> CompiledRuleBundle:
    """Compile source-backed definitions into a deterministic immutable bundle."""

    rules = tuple(definitions)
    if any(not isinstance(item, RuleDefinition) for item in rules):
        raise TypeError(
            "compile_rule_bundle requires RuleDefinition objects; use compile_rule_records for ingestion"
        )
    if not isinstance(propositions, Mapping):
        raise TypeError("compile_rule_bundle requires a proposition mapping")
    _unique_records(rules, kind="rule")
    normalized_propositions: dict[str, Proposition] = {}
    for key, value in propositions.items():
        if not isinstance(value, Proposition):
            raise TypeError("compile_rule_bundle requires hydrated Proposition values")
        normalized_key = _require_string(
            key, "proposition mapping key", identifier=True
        )
        if normalized_key in normalized_propositions:
            raise ValueError(
                f"duplicate proposition mapping key after NFC normalization: {normalized_key}"
            )
        if normalized_key != value.id:
            raise ValueError(
                f"proposition mapping key {key!r} does not match id {value.id!r}"
            )
        normalized_propositions[normalized_key] = value
    proposition_map = _unique_records(
        list(normalized_propositions.values()), kind="proposition"
    )
    ordered, canonical_after, canonical_before = _precedence_order(rules)
    compiled: list[CompiledRule] = []
    for rule in ordered:
        _require_bool(rule.execution_ready, f"rule {rule.id} execution_ready")
        _require_bool(rule.production_eligible, f"rule {rule.id} production_eligible")
        if (
            not rule.execution_ready
            or not rule.production_eligible
            or rule.semantic_status != "resolved"
        ):
            raise ValueError(f"rule {rule.id} is unresolved or non-executable")
        if not rule.id or not rule.proposition_id or not rule.effect:
            raise ValueError("rule id, proposition_id, and effect are required")
        proposition = proposition_map.get(rule.proposition_id)
        if proposition is None:
            raise ValueError(
                f"rule {rule.id} references missing proposition {rule.proposition_id}"
            )
        _validate_proposition(proposition)
        predicate = parse_predicate(rule.predicate)
        compiled.append(
            CompiledRule(
                id=rule.id,
                proposition_id=rule.proposition_id,
                predicate=predicate,
                effect=rule.effect,
                resolution_slot=rule.resolution_slot,
                precedence=int(rule.precedence),
                after=canonical_after[rule.id],
                before=canonical_before[rule.id],
                proposition=proposition,
                metadata=dict(rule.metadata),
            )
        )
    digest_payload = {
        "compiler_version": COMPILER_VERSION,
        "schema_version": SCHEMA_VERSION,
        "primitives_version": PRIMITIVES_VERSION,
        "rules": [
            {
                "id": rule.id,
                "proposition_id": rule.proposition_id,
                "predicate": predicate_to_canonical_data(rule.predicate),
                "effect": rule.effect,
                "resolution_slot": rule.resolution_slot,
                "precedence": rule.precedence,
                "after": list(rule.after),
                "before": list(rule.before),
                "metadata": dict(rule.metadata),
                "proposition": _proposition_digest_payload(rule.proposition),
            }
            for rule in sorted(compiled, key=lambda item: item.id)
        ],
    }
    digest = canonical_digest(digest_payload)
    return CompiledRuleBundle(
        compiler_version=COMPILER_VERSION,
        schema_version=SCHEMA_VERSION,
        primitives_version=PRIMITIVES_VERSION,
        digest=digest,
        rules=tuple(compiled),
        source_manifest_digests=tuple(
            sorted({item.proposition.source_manifest_digest for item in compiled})
        ),
        corpus_manifest_digests=tuple(
            sorted({item.proposition.corpus_manifest_digest for item in compiled})
        ),
        corpus_artifact_digests=tuple(
            sorted({item.proposition.corpus_artifact_digest for item in compiled})
        ),
    )
