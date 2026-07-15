"""Build immutable, judgment-free BaZi fact graphs."""

from __future__ import annotations

import hashlib
import json
import unicodedata
from itertools import combinations
from typing import Any, Iterable, Mapping, Sequence

from iching.core.bazi_rules.primitives import (
    BRANCHES,
    BRANCH_BREAKS,
    BRANCH_CLASHES,
    BRANCH_HARMS,
    BRANCH_PUNISHMENT_PAIRS,
    BRANCH_SIX_COMBINATIONS,
    ELEMENT_CONTROLS,
    HIDDEN_STEMS,
    LABEL_POSITIONS,
    MEETINGS,
    PILLAR_POSITIONS,
    POSITION_LABELS,
    PRIMITIVES_VERSION,
    QI_LEVELS,
    SELF_PUNISHMENT_BRANCHES,
    STEMS,
    STEM_CLASHES,
    STEM_COMBINATIONS,
    STEM_ELEMENTS,
    TRINES,
    ten_god,
)
from iching.core.bazi_rules.schema import (
    BaziFactEnvelope,
    BaziFactGraph,
    CombinationFact,
    CompletenessFact,
    DayMasterFact,
    MonthCommandFact,
    MonthQiFact,
    OccurrenceFact,
    PillarFact,
    RelationFact,
    RelationMember,
    RootFact,
    SCHEMA_VERSION,
)


FACT_GRAPH_VERSION = "bazi-fact-graph-v1"
MAX_ENVELOPE_WORLDS = 64


def _value(pillar: Mapping[str, Any], key: str) -> str:
    value = pillar.get(key, "")
    if isinstance(value, Mapping):
        value = value.get("value", "")
    return str(value)


def _canonical_bytes(value: Any) -> bytes:
    text = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return unicodedata.normalize("NFC", text).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _position_for(pillar: Mapping[str, Any], fallback: str) -> str:
    if "position" in pillar:
        explicit = pillar["position"]
        if not isinstance(explicit, str) or explicit not in PILLAR_POSITIONS:
            raise ValueError(f"invalid explicit pillar position: {explicit!r}")
        return explicit
    label = str(pillar.get("label", ""))
    return LABEL_POSITIONS.get(label, fallback)


def _normalize_pillars(
    pillars: Sequence[Mapping[str, Any]],
    uncertain_positions: frozenset[str],
) -> tuple[PillarFact, ...]:
    if len(pillars) not in {3, 4}:
        raise ValueError("fact graph requires three or four ordered pillars")
    by_position: dict[str, PillarFact] = {}
    for index, raw in enumerate(pillars):
        fallback = PILLAR_POSITIONS[index]
        position = _position_for(raw, fallback)
        if position in by_position:
            raise ValueError(f"duplicate pillar position: {position}")
        stem = _value(raw, "stem")
        branch = _value(raw, "branch")
        if stem not in STEMS:
            raise ValueError(f"invalid stem at {position}: {stem!r}")
        if branch not in BRANCHES:
            raise ValueError(f"invalid branch at {position}: {branch!r}")
        if STEMS.index(stem) % 2 != BRANCHES.index(branch) % 2:
            raise ValueError(
                f"invalid sexagenary stem/branch polarity at {position}: {stem}{branch}"
            )
        known = position not in uncertain_positions
        by_position[position] = PillarFact(
            position=position,  # type: ignore[arg-type]
            label=POSITION_LABELS[position],
            stem=stem if known else None,
            branch=branch if known else None,
            known=known,
        )
    for required in ("year", "month", "day"):
        if required not in by_position:
            raise ValueError(f"missing required pillar position: {required}")
    if "day" in uncertain_positions or "month" in uncertain_positions:
        raise ValueError(
            "uncertain day/month requires build_bazi_fact_envelope candidate worlds"
        )
    if "hour" not in by_position:
        by_position["hour"] = PillarFact(
            "hour", POSITION_LABELS["hour"], None, None, False
        )
    return tuple(by_position[position] for position in PILLAR_POSITIONS)


def _occurrences(
    pillars: tuple[PillarFact, ...],
    day_stem: str,
) -> tuple[OccurrenceFact, ...]:
    result: list[OccurrenceFact] = []
    for pillar in pillars:
        if not pillar.known or pillar.stem is None or pillar.branch is None:
            continue
        result.append(
            OccurrenceFact(
                id=f"occ.{pillar.position}.stem.{pillar.stem}",
                position=pillar.position,
                layer="stem",
                stem=pillar.stem,
                element=STEM_ELEMENTS[pillar.stem],
                ten_god=ten_god(day_stem, pillar.stem),
                exposed=True,
                qi_level=None,
                is_day_master=pillar.position == "day",
            )
        )
        for index, hidden_stem in enumerate(HIDDEN_STEMS[pillar.branch]):
            qi_level = QI_LEVELS[index]
            result.append(
                OccurrenceFact(
                    id=f"occ.{pillar.position}.hidden.{index}.{hidden_stem}",
                    position=pillar.position,
                    layer="hidden",
                    stem=hidden_stem,
                    element=STEM_ELEMENTS[hidden_stem],
                    ten_god=ten_god(day_stem, hidden_stem),
                    exposed=False,
                    qi_level=qi_level,  # type: ignore[arg-type]
                    is_day_master=False,
                )
            )
    return tuple(result)


def _roots(
    occurrences: tuple[OccurrenceFact, ...], day_stem: str
) -> tuple[RootFact, ...]:
    """Record same-element roots; exact-stem roots also receive the narrower marker."""

    day_element = STEM_ELEMENTS[day_stem]
    result: list[RootFact] = []
    for item in occurrences:
        if (
            item.layer != "hidden"
            or item.element != day_element
            or item.qi_level is None
        ):
            continue
        result.append(
            RootFact(
                id=f"root.{item.position}.{item.qi_level}.{item.stem}.same_element",
                position=item.position,
                stem=item.stem,
                element=item.element,
                mode="same_element",
                qi_level=item.qi_level,
            )
        )
        if item.stem == day_stem:
            result.append(
                RootFact(
                    id=f"root.{item.position}.{item.qi_level}.{item.stem}.exact_stem",
                    position=item.position,
                    stem=item.stem,
                    element=item.element,
                    mode="exact_stem",
                    qi_level=item.qi_level,
                )
            )
    return tuple(result)


def _member(
    pillar: PillarFact, layer: str, role: str = "participant"
) -> RelationMember:
    value = pillar.stem if layer == "stem" else pillar.branch
    if value is None:
        raise ValueError("unknown pillar cannot become a relation member")
    return RelationMember(pillar.position, layer, value, role)  # type: ignore[arg-type]


def _pair_relations(pillars: tuple[PillarFact, ...]) -> tuple[RelationFact, ...]:
    known = tuple(item for item in pillars if item.known)
    result: list[RelationFact] = []
    for left, right in combinations(known, 2):
        assert left.stem is not None and right.stem is not None
        stem_pair = frozenset((left.stem, right.stem))
        stem_types: list[tuple[str, str | None]] = []
        if stem_pair in STEM_COMBINATIONS:
            stem_types.append(("stem_combine", STEM_COMBINATIONS[stem_pair]))
        if stem_pair in STEM_CLASHES:
            stem_types.append(("stem_clash", None))
        if (
            ELEMENT_CONTROLS[STEM_ELEMENTS[left.stem]] == STEM_ELEMENTS[right.stem]
            or ELEMENT_CONTROLS[STEM_ELEMENTS[right.stem]] == STEM_ELEMENTS[left.stem]
        ):
            stem_types.append(("stem_control", None))
        for relation_type, result_element in stem_types:
            if relation_type == "stem_control":
                left_controls = (
                    ELEMENT_CONTROLS[STEM_ELEMENTS[left.stem]]
                    == STEM_ELEMENTS[right.stem]
                )
                members = (
                    _member(
                        left, "stem", "controller" if left_controls else "controlled"
                    ),
                    _member(
                        right, "stem", "controlled" if left_controls else "controller"
                    ),
                )
            else:
                members = (_member(left, "stem"), _member(right, "stem"))
            result.append(
                RelationFact(
                    id=f"rel.{relation_type}.{left.position}.{right.position}",
                    relation_type=relation_type,
                    layer="stem",
                    members=members,
                    result_element=result_element,
                )
            )

        assert left.branch is not None and right.branch is not None
        branch_pair = frozenset((left.branch, right.branch))
        branch_types: list[tuple[str, str | None]] = []
        if branch_pair in BRANCH_SIX_COMBINATIONS:
            branch_types.append(
                ("branch_six_combine", BRANCH_SIX_COMBINATIONS[branch_pair])
            )
        if branch_pair in BRANCH_CLASHES:
            branch_types.append(("branch_clash", None))
        if branch_pair in BRANCH_HARMS:
            branch_types.append(("branch_harm", None))
        if branch_pair in BRANCH_BREAKS:
            branch_types.append(("branch_break", None))
        if branch_pair in BRANCH_PUNISHMENT_PAIRS:
            branch_types.append(("branch_punishment", None))
        if left.branch == right.branch and left.branch in SELF_PUNISHMENT_BRANCHES:
            branch_types.append(("branch_self_punishment", None))
        for relation_type, result_element in branch_types:
            members = (_member(left, "branch"), _member(right, "branch"))
            result.append(
                RelationFact(
                    id=f"rel.{relation_type}.{left.position}.{right.position}",
                    relation_type=relation_type,
                    layer="branch",
                    members=members,
                    result_element=result_element,
                )
            )
    return tuple(sorted(result, key=lambda item: item.id))


def _complete_group_members(
    known: tuple[PillarFact, ...],
    required: tuple[str, ...],
) -> tuple[RelationMember, ...] | None:
    members: list[RelationMember] = []
    for value in required:
        pillar = next((item for item in known if item.branch == value), None)
        if pillar is None:
            return None
        members.append(_member(pillar, "branch"))
    return tuple(members)


def _combinations(pillars: tuple[PillarFact, ...]) -> tuple[CombinationFact, ...]:
    known = tuple(item for item in pillars if item.known)
    result: list[CombinationFact] = []
    for left, right in combinations(known, 2):
        assert left.stem is not None and right.stem is not None
        stem_pair = frozenset((left.stem, right.stem))
        if stem_pair in STEM_COMBINATIONS:
            values = tuple(sorted(stem_pair, key=STEMS.index))
            result.append(
                CombinationFact(
                    id=f"comb.stem.{'.'.join(values)}.{left.position}.{right.position}",
                    kind="stem_combine",
                    members=(_member(left, "stem"), _member(right, "stem")),
                    required_values=values,
                    result_element=STEM_COMBINATIONS[stem_pair],
                )
            )
        assert left.branch is not None and right.branch is not None
        branch_pair = frozenset((left.branch, right.branch))
        if branch_pair in BRANCH_SIX_COMBINATIONS:
            values = tuple(sorted(branch_pair, key=BRANCHES.index))
            result.append(
                CombinationFact(
                    id=f"comb.six.{'.'.join(values)}.{left.position}.{right.position}",
                    kind="branch_six_combine",
                    members=(_member(left, "branch"), _member(right, "branch")),
                    required_values=values,
                    result_element=BRANCH_SIX_COMBINATIONS[branch_pair],
                )
            )
    for kind, groups in (("trine", TRINES), ("meeting", MEETINGS)):
        for required, element in groups:
            members = _complete_group_members(known, required)
            if members is None:
                continue
            result.append(
                CombinationFact(
                    id=f"comb.{kind}.{'.'.join(required)}",
                    kind=kind,  # type: ignore[arg-type]
                    members=members,
                    required_values=required,
                    result_element=element,
                )
            )
    return tuple(sorted(result, key=lambda item: item.id))


def _graph_payload(
    pillars: tuple[PillarFact, ...],
    day_master: DayMasterFact,
    month_command: MonthCommandFact,
    occurrences: tuple[OccurrenceFact, ...],
    roots: tuple[RootFact, ...],
    relations: tuple[RelationFact, ...],
    combinations_: tuple[CombinationFact, ...],
    completeness: CompletenessFact,
) -> dict[str, Any]:
    def member_payload(item: RelationMember) -> dict[str, Any]:
        return {
            "position": item.position,
            "layer": item.layer,
            "value": item.value,
            "role": item.role,
        }

    return {
        "fact_graph_version": FACT_GRAPH_VERSION,
        "schema_version": SCHEMA_VERSION,
        "primitives_version": PRIMITIVES_VERSION,
        "pillars": [item.__dict__ for item in pillars],
        "day_master": day_master.__dict__,
        "month_command": {
            "branch": month_command.branch,
            "qi": [item.__dict__ for item in month_command.qi],
        },
        "occurrences": [item.__dict__ for item in occurrences],
        "roots": [item.__dict__ for item in roots],
        "relations": [
            {
                "id": item.id,
                "relation_type": item.relation_type,
                "layer": item.layer,
                "members": [member_payload(member) for member in item.members],
                "result_element": item.result_element,
            }
            for item in relations
        ],
        "combinations": [
            {
                "id": item.id,
                "kind": item.kind,
                "members": [member_payload(member) for member in item.members],
                "required_values": list(item.required_values),
                "result_element": item.result_element,
                "complete": item.complete,
            }
            for item in combinations_
        ],
        "completeness": {
            "chart_complete": completeness.chart_complete,
            "hour_known": completeness.hour_known,
            "uncertain_positions": sorted(completeness.uncertain_positions),
            "uncertainty_reason": completeness.uncertainty_reason,
        },
    }


def _build_bazi_fact_graph(
    pillars: Iterable[Mapping[str, Any]],
    *,
    hour_uncertain: bool,
    uncertain_positions: Iterable[str],
) -> BaziFactGraph:
    """Build one fact graph.

    ``hour_uncertain`` masks any supplied hour rather than treating it as a
    candidate answer.  When uncertainty can change day/month pillars, callers
    must supply complete candidate worlds to :func:`build_bazi_fact_envelope`.
    """

    if type(hour_uncertain) is not bool:
        raise ValueError("hour_uncertain must be a boolean")
    raw = list(pillars)
    uncertain = set(uncertain_positions)
    if len(raw) == 3:
        uncertain.add("hour")
    if hour_uncertain:
        uncertain.add("hour")
    invalid_uncertain = uncertain - set(PILLAR_POSITIONS)
    if invalid_uncertain:
        raise ValueError(f"unknown uncertain positions: {sorted(invalid_uncertain)}")
    normalized = _normalize_pillars(raw, frozenset(uncertain))
    day = next(item for item in normalized if item.position == "day")
    month = next(item for item in normalized if item.position == "month")
    assert day.stem is not None and month.branch is not None
    day_master = DayMasterFact(day.stem, STEM_ELEMENTS[day.stem])
    month_qi = tuple(
        MonthQiFact(
            level=QI_LEVELS[index],  # type: ignore[arg-type]
            stem=stem,
            element=STEM_ELEMENTS[stem],
            ten_god=ten_god(day.stem, stem),
        )
        for index, stem in enumerate(HIDDEN_STEMS[month.branch])
    )
    month_command = MonthCommandFact(month.branch, month_qi)
    occurrences = _occurrences(normalized, day.stem)
    roots = _roots(occurrences, day.stem)
    relations = _pair_relations(normalized)
    combinations_ = _combinations(normalized)
    completeness = CompletenessFact(
        chart_complete=not uncertain and all(item.known for item in normalized),
        hour_known=next(item for item in normalized if item.position == "hour").known,
        uncertain_positions=frozenset(uncertain),  # type: ignore[arg-type]
        uncertainty_reason="birth_time_uncertain" if uncertain else None,
    )
    payload = _graph_payload(
        normalized,
        day_master,
        month_command,
        occurrences,
        roots,
        relations,
        combinations_,
        completeness,
    )
    return BaziFactGraph(
        schema_version=SCHEMA_VERSION,
        primitives_version=PRIMITIVES_VERSION,
        pillars=normalized,
        day_master=day_master,
        month_command=month_command,
        occurrences=occurrences,
        roots=roots,
        relations=relations,
        combinations=combinations_,
        completeness=completeness,
        digest=_digest(payload),
    )


def build_bazi_fact_graph(
    pillars: Iterable[Mapping[str, Any]],
    *,
    hour_uncertain: bool = False,
) -> BaziFactGraph:
    return _build_bazi_fact_graph(
        pillars,
        hour_uncertain=hour_uncertain,
        uncertain_positions=(),
    )


def build_bazi_fact_envelope(
    candidate_pillar_sets: Iterable[Iterable[Mapping[str, Any]]],
) -> BaziFactEnvelope:
    """Build a deterministic possible-world envelope for uncertain input."""

    candidates: list[Iterable[Mapping[str, Any]]] = []
    for index, candidate in enumerate(candidate_pillar_sets):
        if index >= MAX_ENVELOPE_WORLDS:
            raise ValueError(
                f"fact envelope cannot exceed {MAX_ENVELOPE_WORLDS} candidate worlds"
            )
        candidates.append(candidate)
    if not candidates:
        raise ValueError("fact envelope requires at least one complete candidate world")
    worlds_by_digest: dict[str, BaziFactGraph] = {}
    for candidate in candidates:
        graph = build_bazi_fact_graph(candidate)
        if not graph.completeness.chart_complete:
            raise ValueError("fact envelope candidate worlds must be complete")
        worlds_by_digest[graph.digest] = graph
    worlds = tuple(worlds_by_digest[key] for key in sorted(worlds_by_digest))
    return BaziFactEnvelope(
        worlds=worlds,
        digest=_digest(
            {
                "fact_graph_version": FACT_GRAPH_VERSION,
                "worlds": [item.digest for item in worlds],
            }
        ),
    )
