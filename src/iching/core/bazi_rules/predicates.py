"""Closed, three-valued predicate language for :mod:`bazi_rules`."""

from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from itertools import combinations as position_pairs
from types import MappingProxyType
from typing import Any, Callable, Iterable, Mapping, Sequence

from iching.core.bazi_rules.primitives import (
    BRANCH_SIX_COMBINATIONS,
    BRANCHES,
    ELEMENTS,
    MEETINGS,
    PILLAR_POSITIONS,
    QI_LEVELS,
    STEM_COMBINATIONS,
    STEMS,
    TEN_GODS,
    TRINES,
)
from iching.core.bazi_rules.schema import (
    BaziFactEnvelope,
    BaziFactGraph,
    CombinationFact,
    EvaluationResult,
    EvaluationTrace,
    OccurrenceFact,
    PredicateNode,
    RelationFact,
    RelationMember,
    RootFact,
    RuleEvaluationContext,
    TruthValue,
)


PREDICATE_VERSION = "bazi-predicates-v2"
MAX_AST_DEPTH = 32
MAX_AST_NODES = 1024

OPERATORS = frozenset(
    (
        "all",
        "any",
        "not",
        "fact_equals",
        "fact_in",
        "exists_occurrence",
        "count_compare",
        "relation_exists",
        "root_exists",
        "month_command_equals",
        "god_exposed",
        "combination_complete",
        "activation_exists",
    )
)

RELATION_TYPES = frozenset(
    (
        "stem_combine",
        "stem_clash",
        "stem_control",
        "branch_six_combine",
        "branch_clash",
        "branch_harm",
        "branch_break",
        "branch_punishment",
        "branch_self_punishment",
    )
)
COMBINATION_KINDS = frozenset(
    ("stem_combine", "branch_six_combine", "trine", "meeting")
)
COLLECTION_PATHS = frozenset(("occurrences", "roots", "relations", "combinations"))
COLLECTION_GLOBAL_MAXIMA: Mapping[str, int] = MappingProxyType(
    {
        "occurrences": 16,
        "roots": 24,  # exact roots also appear in the inclusive same-element set
        "relations": 30,  # six pillar pairs × at most five simultaneous relation facts
        "combinations": 20,  # six stem + six branch pairs + four trines + four meetings
    }
)


@dataclass(frozen=True)
class FactPathSpec:
    value_type: type | tuple[type, ...]
    dependencies: frozenset[str]


FACT_PATH_REGISTRY: Mapping[str, FactPathSpec] = MappingProxyType(
    {
        **{
            f"pillars.{position}.{field}": FactPathSpec(str, frozenset((position,)))
            for position in PILLAR_POSITIONS
            for field in ("stem", "branch")
        },
        "day_master.stem": FactPathSpec(str, frozenset(("day",))),
        "day_master.element": FactPathSpec(str, frozenset(("day",))),
        "month_command.branch": FactPathSpec(str, frozenset(("month",))),
        "month_command.main_stem": FactPathSpec(str, frozenset(("month", "day"))),
        "month_command.main_element": FactPathSpec(str, frozenset(("month",))),
        "month_command.main_god": FactPathSpec(str, frozenset(("month", "day"))),
        "completeness.chart_complete": FactPathSpec(bool, frozenset()),
        "completeness.hour_known": FactPathSpec(bool, frozenset()),
    }
)


_LEAF_KEYS: dict[str, frozenset[str]] = {
    "fact_equals": frozenset(("op", "path", "value")),
    "fact_in": frozenset(("op", "path", "values")),
    "exists_occurrence": frozenset(
        (
            "op",
            "stems",
            "elements",
            "gods",
            "positions",
            "layers",
            "qi_levels",
            "exposed",
            "include_day_master",
        )
    ),
    "count_compare": frozenset(("op", "path", "where", "comparator", "value")),
    "relation_exists": frozenset(
        (
            "op",
            "relation_types",
            "positions",
            "values",
            "layers",
            "result_elements",
            "controller_positions",
            "controller_values",
            "controlled_positions",
            "controlled_values",
            "adjacent",
            "member_filters",
            "excluded_member_gods",
            "excluded_occurrence_ids",
            "controller_gods",
            "controlled_gods",
        )
    ),
    "root_exists": frozenset(("op", "mode", "positions", "qi_levels")),
    "month_command_equals": frozenset(("op", "level", "stem", "element", "god")),
    "god_exposed": frozenset(("op", "gods", "positions", "include_day_master")),
    "combination_complete": frozenset(("op", "kinds", "members", "result_elements")),
    "activation_exists": frozenset(
        ("op", "gods", "families", "positions", "origins", "scope")
    ),
}

_MEMBER_FILTER_KEYS = frozenset(
    ("positions", "layers", "values", "roles", "gods", "elements", "occurrence_ids")
)
_ACTIVATION_FAMILIES = frozenset(("peer", "output", "wealth", "officer", "seal"))
_ACTIVATION_ORIGINS = frozenset(
    (
        "month_command_main",
        "exposed_stem",
        "source_rule",
        "complete_combination_pending",
    )
)
_GOD_FAMILIES = {
    "比肩": "peer",
    "劫财": "peer",
    "食神": "output",
    "伤官": "output",
    "偏财": "wealth",
    "正财": "wealth",
    "七杀": "officer",
    "正官": "officer",
    "偏印": "seal",
    "正印": "seal",
}


def _strict_keys(
    value: Mapping[str, Any], allowed: frozenset[str], operator: str
) -> None:
    extras = set(value) - set(allowed)
    if extras:
        raise ValueError(f"{operator} has unknown fields: {sorted(extras)}")


def _strings(
    value: Any,
    *,
    field: str,
    allowed: Iterable[str] | None = None,
    required: bool = False,
) -> tuple[str, ...]:
    if value is None:
        if required:
            raise ValueError(f"{field} is required")
        return ()
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ValueError(f"{field} must be a list of strings")
    result = tuple(str(item) for item in value)
    if required and not result:
        raise ValueError(f"{field} cannot be empty")
    if any(not isinstance(item, str) for item in value):
        raise ValueError(f"{field} must contain only strings")
    if allowed is not None:
        invalid = set(result) - set(allowed)
        if invalid:
            raise ValueError(f"{field} has invalid values: {sorted(invalid)}")
    return tuple(sorted(set(result)))


def _bool(value: Any, *, field: str, default: bool = False) -> bool:
    if value is None:
        return default
    if not isinstance(value, bool):
        raise ValueError(f"{field} must be boolean")
    return value


def _optional_bool(value: Any, *, field: str) -> bool | None:
    if value is None:
        return None
    if type(value) is not bool:
        raise ValueError(f"{field} must be boolean or null")
    return value


def _identifiers(value: Any, *, field: str) -> tuple[str, ...]:
    result = _strings(value, field=field)
    if any(not item.strip() for item in result):
        raise ValueError(f"{field} cannot contain blank values")
    return result


def _json_scalar(value: Any, *, field: str) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise ValueError(f"{field} must be a JSON scalar")


def parse_predicate(value: PredicateNode | Mapping[str, Any]) -> PredicateNode:
    """Parse and validate the closed predicate AST."""

    if isinstance(value, PredicateNode):
        _validate_parsed_predicate(value)
        return value
    state = {"nodes": 0}

    def parse(raw: Mapping[str, Any], depth: int) -> PredicateNode:
        if not isinstance(raw, Mapping):
            raise ValueError("predicate nodes must be objects")
        if depth > MAX_AST_DEPTH:
            raise ValueError(f"predicate AST exceeds depth {MAX_AST_DEPTH}")
        state["nodes"] += 1
        if state["nodes"] > MAX_AST_NODES:
            raise ValueError(f"predicate AST exceeds {MAX_AST_NODES} nodes")
        operator = raw.get("op")
        if not isinstance(operator, str) or operator not in OPERATORS:
            raise ValueError(f"unknown predicate operator: {operator!r}")
        if operator in {"all", "any"}:
            _strict_keys(raw, frozenset(("op", "children")), operator)
            children_raw = raw.get("children")
            if (
                isinstance(children_raw, (str, bytes))
                or not isinstance(children_raw, Sequence)
                or not children_raw
            ):
                raise ValueError(f"{operator}.children must be a non-empty list")
            children = tuple(parse(child, depth + 1) for child in children_raw)
            children = tuple(
                sorted(
                    children,
                    key=lambda item: _canonical_text(predicate_to_canonical_data(item)),
                )
            )
            return PredicateNode(operator, children=children)
        if operator == "not":
            _strict_keys(raw, frozenset(("op", "child")), operator)
            child = raw.get("child")
            if not isinstance(child, Mapping):
                raise ValueError("not.child must be an object")
            return PredicateNode(operator, children=(parse(child, depth + 1),))

        _strict_keys(raw, _LEAF_KEYS[operator], operator)
        arguments = _validate_leaf(operator, raw)
        return PredicateNode(operator, arguments=arguments)

    if not isinstance(value, Mapping):
        raise ValueError("predicate must be an object")
    return parse(value, 1)


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


def _validate_parsed_predicate(node: PredicateNode) -> None:
    """Validate a typed node in place without reconstructing/reparsing it."""

    state = {"nodes": 0}

    def visit(item: PredicateNode, depth: int) -> None:
        if depth > MAX_AST_DEPTH:
            raise ValueError(f"predicate AST exceeds depth {MAX_AST_DEPTH}")
        state["nodes"] += 1
        if state["nodes"] > MAX_AST_NODES:
            raise ValueError(f"predicate AST exceeds {MAX_AST_NODES} nodes")
        if item.operator not in OPERATORS:
            raise ValueError(f"unknown predicate operator: {item.operator!r}")
        if item.operator in {"all", "any"}:
            if item.arguments or not item.children:
                raise ValueError(f"invalid parsed {item.operator} node")
            canonical_order = tuple(
                sorted(
                    item.children,
                    key=lambda child: _canonical_text(
                        predicate_to_canonical_data(child)
                    ),
                )
            )
            if item.children != canonical_order:
                raise ValueError(f"parsed {item.operator} children are not canonical")
        elif item.operator == "not":
            if item.arguments or len(item.children) != 1:
                raise ValueError("invalid parsed not node")
        else:
            if item.children:
                raise ValueError(f"leaf {item.operator} cannot have children")
            raw = {"op": item.operator, **_thaw(item.arguments)}
            _strict_keys(raw, _LEAF_KEYS[item.operator], item.operator)
            normalized = _validate_leaf(item.operator, raw)
            if _canonical_text(_thaw(item.arguments)) != _canonical_text(
                _thaw(normalized)
            ):
                raise ValueError(f"parsed {item.operator} arguments are not canonical")
        for child in item.children:
            visit(child, depth + 1)

    visit(node, 1)


def _validate_leaf(operator: str, raw: Mapping[str, Any]) -> dict[str, Any]:
    if operator == "fact_equals":
        path = raw.get("path")
        if path not in FACT_PATH_REGISTRY:
            raise ValueError(f"unknown fact path: {path!r}")
        value = _json_scalar(raw.get("value"), field="value")
        if not isinstance(value, FACT_PATH_REGISTRY[str(path)].value_type):
            raise ValueError(f"fact_equals.value has wrong type for {path}")
        return {"path": path, "value": value}
    if operator == "fact_in":
        path = raw.get("path")
        if path not in FACT_PATH_REGISTRY:
            raise ValueError(f"unknown fact path: {path!r}")
        values = raw.get("values")
        if (
            isinstance(values, (str, bytes))
            or not isinstance(values, Sequence)
            or not values
        ):
            raise ValueError("fact_in.values must be a non-empty list")
        normalized = tuple(_json_scalar(item, field="values") for item in values)
        expected_type = FACT_PATH_REGISTRY[str(path)].value_type
        if any(not isinstance(item, expected_type) for item in normalized):
            raise ValueError(f"fact_in.values have wrong type for {path}")
        return {
            "path": path,
            "values": tuple(sorted(set(normalized), key=_canonical_text)),
        }
    if operator == "exists_occurrence":
        arguments = {
            "stems": _strings(raw.get("stems"), field="stems", allowed=STEMS),
            "elements": _strings(
                raw.get("elements"), field="elements", allowed=ELEMENTS
            ),
            "gods": _strings(raw.get("gods"), field="gods", allowed=TEN_GODS),
            "positions": _strings(
                raw.get("positions"), field="positions", allowed=PILLAR_POSITIONS
            ),
            "layers": _strings(
                raw.get("layers"), field="layers", allowed=("stem", "hidden")
            ),
            "qi_levels": _strings(
                raw.get("qi_levels"), field="qi_levels", allowed=QI_LEVELS
            ),
            "exposed": raw.get("exposed"),
            "include_day_master": _bool(
                raw.get("include_day_master"), field="include_day_master"
            ),
        }
        if arguments["exposed"] is not None and not isinstance(
            arguments["exposed"], bool
        ):
            raise ValueError("exposed must be boolean")
        return arguments
    if operator == "count_compare":
        path = raw.get("path")
        if path not in COLLECTION_PATHS:
            raise ValueError(f"unknown count path: {path!r}")
        comparator = raw.get("comparator")
        if comparator not in {"==", "!=", ">", ">=", "<", "<="}:
            raise ValueError(f"invalid count comparator: {comparator!r}")
        target = raw.get("value")
        if isinstance(target, bool) or not isinstance(target, int):
            raise ValueError("count_compare.value must be an integer, not bool")
        if target < 0:
            raise ValueError("count_compare.value cannot be negative")
        where = raw.get("where", {})
        if not isinstance(where, Mapping):
            raise ValueError("count_compare.where must be an object")
        normalized_where = _validate_count_where(str(path), where)
        return {
            "path": path,
            "where": normalized_where,
            "comparator": comparator,
            "value": target,
        }
    if operator == "relation_exists":
        return _validate_relation_filter(raw, include_op=True)
    if operator == "root_exists":
        mode = raw.get("mode")
        if mode not in {"exact_stem", "same_element"}:
            raise ValueError("root_exists.mode must be exact_stem or same_element")
        return {
            "mode": mode,
            "positions": _strings(
                raw.get("positions"), field="positions", allowed=PILLAR_POSITIONS
            ),
            "qi_levels": _strings(
                raw.get("qi_levels"), field="qi_levels", allowed=QI_LEVELS
            ),
        }
    if operator == "month_command_equals":
        level = raw.get("level")
        if level not in {"main", "secondary", "residual", "any"}:
            raise ValueError("month_command_equals.level must be explicit")
        result = {
            "level": level,
            "stem": raw.get("stem"),
            "element": raw.get("element"),
            "god": raw.get("god"),
        }
        if result["stem"] is not None and result["stem"] not in STEMS:
            raise ValueError("invalid month-command stem")
        if result["element"] is not None and result["element"] not in ELEMENTS:
            raise ValueError("invalid month-command element")
        if result["god"] is not None and result["god"] not in TEN_GODS:
            raise ValueError("invalid month-command god")
        if all(result[field] is None for field in ("stem", "element", "god")):
            raise ValueError("month_command_equals needs stem, element, or god")
        return result
    if operator == "god_exposed":
        return {
            "gods": _strings(
                raw.get("gods"), field="gods", allowed=TEN_GODS, required=True
            ),
            "positions": _strings(
                raw.get("positions"), field="positions", allowed=PILLAR_POSITIONS
            ),
            "include_day_master": _bool(
                raw.get("include_day_master"), field="include_day_master"
            ),
        }
    if operator == "combination_complete":
        return {
            "kinds": _strings(
                raw.get("kinds"), field="kinds", allowed=COMBINATION_KINDS
            ),
            "members": _strings(
                raw.get("members"), field="members", allowed=(*STEMS, *BRANCHES)
            ),
            "result_elements": _strings(
                raw.get("result_elements"), field="result_elements", allowed=ELEMENTS
            ),
        }
    if operator == "activation_exists":
        scope = raw.get("scope")
        if scope != "generic":
            raise ValueError("activation_exists.scope must be generic")
        gods = _strings(raw.get("gods"), field="gods", allowed=TEN_GODS)
        families = _strings(
            raw.get("families"),
            field="families",
            allowed=_ACTIVATION_FAMILIES,
        )
        if not gods and not families:
            raise ValueError("activation_exists needs gods or families")
        return {
            "gods": gods,
            "families": families,
            "positions": _strings(
                raw.get("positions"), field="positions", allowed=PILLAR_POSITIONS
            ),
            "origins": _strings(
                raw.get("origins"), field="origins", allowed=_ACTIVATION_ORIGINS
            ),
            "scope": scope,
        }
    raise AssertionError(operator)


def _validate_member_filter(raw: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise ValueError("relation member_filters must contain objects")
    _strict_keys(raw, _MEMBER_FILTER_KEYS, "relation member filter")
    result = {
        "positions": _strings(
            raw.get("positions"), field="member.positions", allowed=PILLAR_POSITIONS
        ),
        "layers": _strings(
            raw.get("layers"), field="member.layers", allowed=("stem", "branch")
        ),
        "values": _strings(
            raw.get("values"), field="member.values", allowed=(*STEMS, *BRANCHES)
        ),
        "roles": _strings(
            raw.get("roles"),
            field="member.roles",
            allowed=("participant", "controller", "controlled"),
        ),
        "gods": _strings(raw.get("gods"), field="member.gods", allowed=TEN_GODS),
        "elements": _strings(
            raw.get("elements"), field="member.elements", allowed=ELEMENTS
        ),
        "occurrence_ids": _identifiers(
            raw.get("occurrence_ids"), field="member.occurrence_ids"
        ),
    }
    if not any(result.values()):
        raise ValueError("relation member filter cannot be empty")
    return result


def _validate_relation_filter(
    raw: Mapping[str, Any], *, include_op: bool
) -> dict[str, Any]:
    if not include_op:
        _strict_keys(
            raw,
            frozenset(
                (
                    "relation_types",
                    "positions",
                    "values",
                    "layers",
                    "result_elements",
                    "controller_positions",
                    "controller_values",
                    "controlled_positions",
                    "controlled_values",
                    "adjacent",
                    "member_filters",
                    "excluded_member_gods",
                    "excluded_occurrence_ids",
                    "controller_gods",
                    "controlled_gods",
                )
            ),
            "relation filter",
        )
    raw_member_filters = raw.get("member_filters", ())
    if isinstance(raw_member_filters, (str, bytes)) or not isinstance(
        raw_member_filters, Sequence
    ):
        raise ValueError("member_filters must be a list of objects")
    member_filters = tuple(_validate_member_filter(item) for item in raw_member_filters)
    if len(member_filters) > 2:
        raise ValueError("member_filters cannot require more than two relation members")
    member_filters = tuple(sorted(member_filters, key=_canonical_text))
    return {
        "relation_types": _strings(
            raw.get("relation_types"), field="relation_types", allowed=RELATION_TYPES
        ),
        "positions": _strings(
            raw.get("positions"), field="positions", allowed=PILLAR_POSITIONS
        ),
        "values": _strings(
            raw.get("values"), field="values", allowed=(*STEMS, *BRANCHES)
        ),
        "layers": _strings(
            raw.get("layers"), field="layers", allowed=("stem", "branch")
        ),
        "result_elements": _strings(
            raw.get("result_elements"), field="result_elements", allowed=ELEMENTS
        ),
        "controller_positions": _strings(
            raw.get("controller_positions"),
            field="controller_positions",
            allowed=PILLAR_POSITIONS,
        ),
        "controller_values": _strings(
            raw.get("controller_values"), field="controller_values", allowed=STEMS
        ),
        "controlled_positions": _strings(
            raw.get("controlled_positions"),
            field="controlled_positions",
            allowed=PILLAR_POSITIONS,
        ),
        "controlled_values": _strings(
            raw.get("controlled_values"), field="controlled_values", allowed=STEMS
        ),
        "adjacent": _optional_bool(raw.get("adjacent"), field="adjacent"),
        "member_filters": member_filters,
        "excluded_member_gods": _strings(
            raw.get("excluded_member_gods"),
            field="excluded_member_gods",
            allowed=TEN_GODS,
        ),
        "excluded_occurrence_ids": _identifiers(
            raw.get("excluded_occurrence_ids"), field="excluded_occurrence_ids"
        ),
        "controller_gods": _strings(
            raw.get("controller_gods"), field="controller_gods", allowed=TEN_GODS
        ),
        "controlled_gods": _strings(
            raw.get("controlled_gods"), field="controlled_gods", allowed=TEN_GODS
        ),
    }


def _validate_count_where(path: str, where: Mapping[str, Any]) -> dict[str, Any]:
    if path == "occurrences":
        synthetic = {"op": "exists_occurrence", **where}
        _strict_keys(synthetic, _LEAF_KEYS["exists_occurrence"], "occurrence filter")
        return _validate_leaf("exists_occurrence", synthetic)
    if path == "roots":
        synthetic = {"op": "root_exists", **where}
        _strict_keys(synthetic, _LEAF_KEYS["root_exists"], "root filter")
        return _validate_leaf("root_exists", synthetic)
    if path == "relations":
        return _validate_relation_filter(where, include_op=False)
    _strict_keys(
        where, frozenset(("kinds", "members", "result_elements")), "combination filter"
    )
    synthetic = {"op": "combination_complete", **where}
    return _validate_leaf("combination_complete", synthetic)


def _canonical_text(value: Any) -> str:
    return unicodedata.normalize(
        "NFC",
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ),
    )


def predicate_to_canonical_data(node: PredicateNode) -> dict[str, Any]:
    """Return canonical JSON data, sorting only semantically commutative parts."""

    if node.operator in {"all", "any"}:
        children = [predicate_to_canonical_data(child) for child in node.children]
        children.sort(key=_canonical_text)
        return {"op": node.operator, "children": children}
    if node.operator == "not":
        return {"op": "not", "child": predicate_to_canonical_data(node.children[0])}
    arguments: dict[str, Any] = {}
    for key, value in node.arguments.items():
        if key == "member_filters":
            arguments[key] = [
                {
                    nested_key: list(nested_value)
                    if isinstance(nested_value, tuple)
                    else nested_value
                    for nested_key, nested_value in item.items()
                }
                for item in value
            ]
            continue
        if isinstance(value, tuple):
            values = list(value)
            if key in {
                "values",
                "stems",
                "elements",
                "gods",
                "positions",
                "layers",
                "qi_levels",
                "relation_types",
                "result_elements",
                "kinds",
                "members",
                "controller_positions",
                "controller_values",
                "controlled_positions",
                "controlled_values",
                "excluded_member_gods",
                "excluded_occurrence_ids",
                "controller_gods",
                "controlled_gods",
                "families",
                "origins",
            }:
                values.sort(key=_canonical_text)
            arguments[key] = values
        elif isinstance(value, Mapping):
            arguments[key] = {
                nested_key: sorted(list(nested_value), key=_canonical_text)
                if isinstance(nested_value, tuple)
                else nested_value
                for nested_key, nested_value in value.items()
            }
        else:
            arguments[key] = value
    return {"op": node.operator, **arguments}


def _trace(
    operator: str,
    truth: TruthValue,
    *,
    children: tuple[EvaluationTrace, ...] = (),
    **details: Any,
) -> EvaluationResult:
    return EvaluationResult(truth, EvaluationTrace(operator, truth, details, children))


def _kleene_not(value: TruthValue) -> TruthValue:
    if value is TruthValue.TRUE:
        return TruthValue.FALSE
    if value is TruthValue.FALSE:
        return TruthValue.TRUE
    return TruthValue.UNKNOWN


def _fact_path(graph: BaziFactGraph, path: str) -> Any:
    if path.startswith("pillars."):
        _, position, field = path.split(".")
        return getattr(graph.pillar(position), field)
    if path.startswith("day_master."):
        return getattr(graph.day_master, path.rsplit(".", 1)[1])
    if path == "month_command.branch":
        return graph.month_command.branch
    if path.startswith("month_command.main_"):
        main = graph.month_command.at("main")[0]
        field = path.removeprefix("month_command.main_")
        return main.ten_god if field == "god" else getattr(main, field)
    if path == "completeness.chart_complete":
        return graph.completeness.chart_complete
    if path == "completeness.hour_known":
        return graph.completeness.hour_known
    raise AssertionError(path)


def _path_unknown(graph: BaziFactGraph, path: str) -> bool:
    dependencies = FACT_PATH_REGISTRY[path].dependencies
    return bool(dependencies & graph.completeness.uncertain_positions)


def _filter_positions_may_include_unknown(
    graph: BaziFactGraph, positions: Sequence[str]
) -> bool:
    uncertain = graph.completeness.uncertain_positions
    return bool(uncertain & (set(positions) if positions else set(PILLAR_POSITIONS)))


def _matches_occurrence(item: OccurrenceFact, where: Mapping[str, Any]) -> bool:
    if where.get("stems") and item.stem not in where["stems"]:
        return False
    if where.get("elements") and item.element not in where["elements"]:
        return False
    if where.get("gods") and item.ten_god not in where["gods"]:
        return False
    if where.get("positions") and item.position not in where["positions"]:
        return False
    if where.get("layers") and item.layer not in where["layers"]:
        return False
    if where.get("qi_levels") and item.qi_level not in where["qi_levels"]:
        return False
    if where.get("exposed") is not None and item.exposed is not where["exposed"]:
        return False
    if item.is_day_master and not where.get("include_day_master", False):
        return False
    return True


def _matches_root(item: RootFact, where: Mapping[str, Any]) -> bool:
    if item.mode != where.get("mode"):
        return False
    if where.get("positions") and item.position not in where["positions"]:
        return False
    if where.get("qi_levels") and item.qi_level not in where["qi_levels"]:
        return False
    return True


def _matches_relation_member(member: RelationMember, where: Mapping[str, Any]) -> bool:
    return not (
        (where.get("positions") and member.position not in where["positions"])
        or (where.get("layers") and member.layer not in where["layers"])
        or (where.get("values") and member.value not in where["values"])
        or (where.get("roles") and member.role not in where["roles"])
        or (where.get("gods") and member.ten_god not in where["gods"])
        or (where.get("elements") and member.element not in where["elements"])
        or (
            where.get("occurrence_ids")
            and member.occurrence_id not in where["occurrence_ids"]
        )
    )


def _member_filters_match(
    members: Sequence[RelationMember], filters: Sequence[Mapping[str, Any]]
) -> bool:
    """Find an injective filter-to-member assignment without greedy bias."""

    if len(filters) > len(members):
        return False

    def assign(index: int, used: frozenset[int]) -> bool:
        if index == len(filters):
            return True
        return any(
            assign(index + 1, used | {member_index})
            for member_index, member in enumerate(members)
            if member_index not in used
            and _matches_relation_member(member, filters[index])
        )

    return assign(0, frozenset())


def _matches_relation(item: RelationFact, where: Mapping[str, Any]) -> bool:
    if (
        where.get("relation_types")
        and item.relation_type not in where["relation_types"]
    ):
        return False
    positions = {member.position for member in item.members}
    if where.get("positions") and not set(where["positions"]) <= positions:
        return False
    values = {member.value for member in item.members}
    if where.get("values") and not set(where["values"]) <= values:
        return False
    if where.get("layers") and item.layer not in where["layers"]:
        return False
    if (
        where.get("result_elements")
        and item.result_element not in where["result_elements"]
    ):
        return False
    if where.get("adjacent") is not None and item.adjacent is not where["adjacent"]:
        return False
    if where.get("member_filters") and not _member_filters_match(
        item.members, where["member_filters"]
    ):
        return False
    if where.get("excluded_member_gods") and any(
        member.ten_god in where["excluded_member_gods"] for member in item.members
    ):
        return False
    if where.get("excluded_occurrence_ids") and any(
        member.occurrence_id in where["excluded_occurrence_ids"]
        for member in item.members
    ):
        return False
    controllers = {
        member.position for member in item.members if member.role == "controller"
    }
    controller_values = {
        member.value for member in item.members if member.role == "controller"
    }
    controlled = {
        member.position for member in item.members if member.role == "controlled"
    }
    controlled_values = {
        member.value for member in item.members if member.role == "controlled"
    }
    controller_gods = {
        member.ten_god for member in item.members if member.role == "controller"
    }
    controlled_gods = {
        member.ten_god for member in item.members if member.role == "controlled"
    }
    if (
        where.get("controller_positions")
        and not set(where["controller_positions"]) <= controllers
    ):
        return False
    if (
        where.get("controller_values")
        and not set(where["controller_values"]) <= controller_values
    ):
        return False
    if (
        where.get("controlled_positions")
        and not set(where["controlled_positions"]) <= controlled
    ):
        return False
    if (
        where.get("controlled_values")
        and not set(where["controlled_values"]) <= controlled_values
    ):
        return False
    if where.get("controller_gods") and not (
        set(where["controller_gods"]) & controller_gods
    ):
        return False
    if where.get("controlled_gods") and not (
        set(where["controlled_gods"]) & controlled_gods
    ):
        return False
    return True


def _matches_combination(item: CombinationFact, where: Mapping[str, Any]) -> bool:
    if not item.complete:
        return False
    if where.get("kinds") and item.kind not in where["kinds"]:
        return False
    if where.get("members") and not set(where["members"]) <= set(item.required_values):
        return False
    if (
        where.get("result_elements")
        and item.result_element not in where["result_elements"]
    ):
        return False
    return True


def _collection(graph: BaziFactGraph, path: str) -> Sequence[Any]:
    return getattr(graph, path)


def _matcher(path: str) -> Callable[[Any, Mapping[str, Any]], bool]:
    return {
        "occurrences": _matches_occurrence,
        "roots": _matches_root,
        "relations": _matches_relation,
        "combinations": _matches_combination,
    }[path]


@lru_cache(maxsize=16)
def _legal_hour_worlds(
    signature: tuple[tuple[str, str | None, str | None], ...],
) -> tuple[BaziFactGraph, ...]:
    """Materialize every sexagenary-valid completion for one unknown hour."""

    from iching.core.bazi_rules.fact_graph import build_bazi_fact_graph

    worlds: list[BaziFactGraph] = []
    for stem in STEMS:
        for branch in BRANCHES:
            if STEMS.index(stem) % 2 != BRANCHES.index(branch) % 2:
                continue
            pillars = []
            for position, known_stem, known_branch in signature:
                candidate_stem = stem if position == "hour" else known_stem
                candidate_branch = branch if position == "hour" else known_branch
                assert candidate_stem is not None and candidate_branch is not None
                pillars.append(
                    {
                        "position": position,
                        "stem": candidate_stem,
                        "branch": candidate_branch,
                    }
                )
            worlds.append(build_bazi_fact_graph(pillars))
    return tuple(worlds)


def _exact_hour_worlds(graph: BaziFactGraph) -> tuple[BaziFactGraph, ...] | None:
    if graph.completeness.uncertain_positions != frozenset(("hour",)):
        return None
    signature = tuple((item.position, item.stem, item.branch) for item in graph.pillars)
    return _legal_hour_worlds(signature)


def _uncertain_match_possible(
    graph: BaziFactGraph,
    path: str,
    where: Mapping[str, Any],
) -> bool | None:
    worlds = _exact_hour_worlds(graph)
    if worlds is None:
        return None
    match = _matcher(path)
    return any(
        any(match(item, where) for item in _collection(world, path)) for world in worlds
    )


def _uncertain_match_count_changes(
    graph: BaziFactGraph,
    path: str,
    where: Mapping[str, Any],
) -> bool | None:
    support = _exact_hour_count_support(graph, path, where)
    if support is None:
        return None
    match = _matcher(path)
    current = sum(1 for item in _collection(graph, path) if match(item, where))
    return support != (current,)


def _exact_hour_count_support(
    graph: BaziFactGraph,
    path: str,
    where: Mapping[str, Any],
) -> tuple[int, ...] | None:
    worlds = _exact_hour_worlds(graph)
    if worlds is None:
        return None
    match = _matcher(path)
    return tuple(
        sorted(
            {
                sum(1 for item in _collection(world, path) if match(item, where))
                for world in worlds
            }
        )
    )


def _relation_may_be_added(graph: BaziFactGraph, where: Mapping[str, Any]) -> bool:
    uncertain = graph.completeness.uncertain_positions
    if not uncertain:
        return False
    exact = _uncertain_match_possible(graph, "relations", where)
    if exact is not None:
        return exact
    if (
        len(where.get("controller_positions", ())) > 1
        or len(where.get("controlled_positions", ())) > 1
    ):
        return False
    if (
        len(where.get("controller_values", ())) > 1
        or len(where.get("controlled_values", ())) > 1
    ):
        return False
    directional = any(
        where.get(key)
        for key in (
            "controller_positions",
            "controller_values",
            "controlled_positions",
            "controlled_values",
            "controller_gods",
            "controlled_gods",
        )
    )
    if (
        directional
        and where.get("relation_types")
        and "stem_control" not in where["relation_types"]
    ):
        return False
    if directional and where.get("layers") and "stem" not in where["layers"]:
        return False
    relation_types = set(where.get("relation_types", ()))
    layers = set(where.get("layers", ()))
    stem_types = {"stem_combine", "stem_clash", "stem_control"}
    branch_types = RELATION_TYPES - stem_types
    if layers == {"stem"} and relation_types and not relation_types & stem_types:
        return False
    if layers == {"branch"} and relation_types and not relation_types & branch_types:
        return False
    if (
        where.get("result_elements")
        and relation_types
        and not relation_types
        & {
            "stem_combine",
            "branch_six_combine",
        }
    ):
        return False
    values = set(where.get("values", ()))
    if layers == {"stem"} and values - set(STEMS):
        return False
    if layers == {"branch"} and values - set(BRANCHES):
        return False
    if len(values) > 2 or len(where.get("member_filters", ())) > 2:
        return False

    def filter_positions(filter_: Mapping[str, Any]) -> set[str]:
        positions = set(filter_.get("positions", ()))
        occurrence_positions = {
            occurrence_id.split(".")[1]
            for occurrence_id in filter_.get("occurrence_ids", ())
            if occurrence_id.startswith("occ.")
            and len(occurrence_id.split(".")) > 2
            and occurrence_id.split(".")[1] in PILLAR_POSITIONS
        }
        if positions and occurrence_positions:
            return positions & occurrence_positions
        return positions or occurrence_positions

    member_filters = tuple(where.get("member_filters", ()))

    def filters_fit_pair(pair: tuple[str, str]) -> bool:
        candidates = []
        for filter_ in member_filters:
            allowed = filter_positions(filter_)
            candidates.append(
                tuple(
                    index
                    for index, position in enumerate(pair)
                    if not allowed or position in allowed
                )
            )

        def assign(index: int, used: frozenset[int]) -> bool:
            if index == len(candidates):
                return True
            return any(
                assign(index + 1, used | {candidate})
                for candidate in candidates[index]
                if candidate not in used
            )

        return assign(0, frozenset())

    top_positions = set(where.get("positions", ()))
    top_positions.update(where.get("controller_positions", ()))
    top_positions.update(where.get("controlled_positions", ()))
    for raw_pair in position_pairs(PILLAR_POSITIONS, 2):
        pair = (str(raw_pair[0]), str(raw_pair[1]))
        pair_set = set(pair)
        if not pair_set & uncertain or not top_positions <= pair_set:
            continue
        distance = abs(
            PILLAR_POSITIONS.index(pair[0]) - PILLAR_POSITIONS.index(pair[1])
        )
        adjacent = distance == 1
        if where.get("adjacent") is not None and adjacent is not where["adjacent"]:
            continue
        if filters_fit_pair(pair):
            return True
    return False


def _combination_templates(
    where: Mapping[str, Any],
) -> tuple[tuple[str, frozenset[str], str | None], ...]:
    templates: list[tuple[str, frozenset[str], str | None]] = []
    for pair, element in STEM_COMBINATIONS.items():
        templates.append(("stem_combine", pair, element))
    for pair, element in BRANCH_SIX_COMBINATIONS.items():
        templates.append(("branch_six_combine", pair, element))
    templates.extend(
        ("trine", frozenset(values), element) for values, element in TRINES
    )
    templates.extend(
        ("meeting", frozenset(values), element) for values, element in MEETINGS
    )
    kinds = set(where.get("kinds", ()))
    members = set(where.get("members", ()))
    result_elements = set(where.get("result_elements", ()))
    return tuple(
        item
        for item in templates
        if (not kinds or item[0] in kinds)
        and (not members or members <= item[1])
        and (not result_elements or item[2] in result_elements)
    )


def _combination_may_be_added(graph: BaziFactGraph, where: Mapping[str, Any]) -> bool:
    """Return whether an uncertain pillar can add another matching fact.

    Pair combinations are positional facts: when a known chart already has a
    matching pair, an unknown pillar can still repeat either member and form a
    second pair with the known counterpart.  Three-member groups are unique by
    template in the graph and can only be added when the unknown positions fill
    currently missing values.
    """

    unknown_count = len(graph.completeness.uncertain_positions)
    if unknown_count == 0:
        return False
    known_stems = {
        item.stem for item in graph.pillars if item.known and item.stem is not None
    }
    known_branches = {
        item.branch for item in graph.pillars if item.known and item.branch is not None
    }
    for kind, required, _element in _combination_templates(where):
        known = known_stems if kind == "stem_combine" else known_branches
        if kind in {"stem_combine", "branch_six_combine"}:
            known_members = required & known
            if known_members and unknown_count >= 1:
                return True
            if not known_members and unknown_count >= 2:
                return True
            continue
        missing = required - known
        if 0 < len(missing) <= unknown_count:
            return True
    return False


def _combination_count_upper_bound(
    graph: BaziFactGraph,
    where: Mapping[str, Any],
    lower: int,
) -> int:
    """Bound matching positional combination facts across unknown pillars."""

    unknown_count = len(graph.completeness.uncertain_positions)
    if unknown_count == 0:
        return lower
    known_stems = tuple(
        item.stem for item in graph.pillars if item.known and item.stem is not None
    )
    known_branches = tuple(
        item.branch for item in graph.pillars if item.known and item.branch is not None
    )
    added = 0
    for kind, required, _element in _combination_templates(where):
        known = known_stems if kind == "stem_combine" else known_branches
        if kind in {"stem_combine", "branch_six_combine"}:
            left, right = tuple(required)
            left_count = known.count(left)
            right_count = known.count(right)
            template_max = 0
            for unknown_left in range(unknown_count + 1):
                for unknown_right in range(unknown_count - unknown_left + 1):
                    template_max = max(
                        template_max,
                        unknown_left * right_count
                        + unknown_right * left_count
                        + unknown_left * unknown_right,
                    )
            added += template_max
            continue
        missing = required - set(known)
        if missing and len(missing) <= unknown_count:
            added += 1
    return lower + added


def _collection_may_change(
    graph: BaziFactGraph, path: str, where: Mapping[str, Any]
) -> bool:
    if not graph.completeness.uncertain_positions:
        return False
    exact = _uncertain_match_count_changes(graph, path, where)
    if exact is not None:
        return exact
    if path in {"occurrences", "roots"}:
        return _filter_positions_may_include_unknown(
            graph, tuple(where.get("positions", ()))
        )
    if path == "relations":
        return _relation_may_be_added(graph, where)
    return _combination_may_be_added(graph, where)


def _compare(left: int, comparator: str, right: int) -> bool:
    return {
        "==": left == right,
        "!=": left != right,
        ">": left > right,
        ">=": left >= right,
        "<": left < right,
        "<=": left <= right,
    }[comparator]


def _activation_positions(
    context: RuleEvaluationContext, subject_id: str, origin: str
) -> frozenset[str]:
    graph = context.graph
    if not isinstance(graph, BaziFactGraph):
        return frozenset()
    if origin == "month_command_main":
        return frozenset(("month",))
    occurrence = next(
        (item for item in graph.occurrences if item.id == subject_id), None
    )
    if occurrence is not None:
        return frozenset((occurrence.position,))
    combination = next(
        (item for item in graph.combinations if item.id == subject_id), None
    )
    if combination is not None:
        return frozenset(member.position for member in combination.members)
    return frozenset()


def _evaluate_activation(
    args: Mapping[str, Any], context: RuleEvaluationContext
) -> EvaluationResult:
    graph = context.graph
    if not isinstance(graph, BaziFactGraph):
        raise TypeError("activation evaluation requires one fact-graph world")
    requested_gods = set(args.get("gods", ()))
    requested_families = set(args.get("families", ()))
    requested_positions = set(args.get("positions", ()))
    requested_origins = set(args.get("origins", ()))
    matches: list[str] = []
    pending: list[str] = []
    for item in context.activations:
        if requested_origins and item.origin not in requested_origins:
            continue
        positions = _activation_positions(context, item.subject_id, item.origin)
        if requested_positions and not requested_positions & positions:
            continue
        if requested_families and item.god_family not in requested_families:
            continue
        if requested_gods:
            if item.god is not None and item.god not in requested_gods:
                continue
            if item.god is None and not any(
                _GOD_FAMILIES[god] == item.god_family for god in requested_gods
            ):
                continue
        if item.truth is TruthValue.TRUE:
            matches.append(item.subject_id)
        elif item.truth is TruthValue.UNKNOWN:
            pending.append(item.subject_id)
    if matches:
        return _trace(
            "activation_exists",
            TruthValue.TRUE,
            matches=sorted(matches),
            pending=sorted(pending),
        )
    if pending:
        return _trace(
            "activation_exists",
            TruthValue.UNKNOWN,
            matches=[],
            pending=sorted(pending),
            reason="matching_activation_pending_source_rule",
        )
    uncertain = set(graph.completeness.uncertain_positions)
    if uncertain and (not requested_positions or uncertain & requested_positions):
        return _trace(
            "activation_exists",
            TruthValue.UNKNOWN,
            matches=[],
            pending=[],
            reason="uncertain_position_may_add_activation",
        )
    return _trace("activation_exists", TruthValue.FALSE, matches=[], pending=[])


def _evaluate_graph(
    node: PredicateNode,
    graph: BaziFactGraph,
    context: RuleEvaluationContext | None = None,
) -> EvaluationResult:
    operator = node.operator
    if operator in {"all", "any"}:
        results = tuple(
            _evaluate_graph(child, graph, context) for child in node.children
        )
        truths = tuple(item.truth for item in results)
        if operator == "all":
            truth = (
                TruthValue.FALSE
                if TruthValue.FALSE in truths
                else TruthValue.UNKNOWN
                if TruthValue.UNKNOWN in truths
                else TruthValue.TRUE
            )
        else:
            truth = (
                TruthValue.TRUE
                if TruthValue.TRUE in truths
                else TruthValue.UNKNOWN
                if TruthValue.UNKNOWN in truths
                else TruthValue.FALSE
            )
        return _trace(operator, truth, children=tuple(item.trace for item in results))
    if operator == "not":
        result = _evaluate_graph(node.children[0], graph, context)
        return _trace("not", _kleene_not(result.truth), children=(result.trace,))

    args = node.arguments
    if operator == "activation_exists":
        if context is None:
            from iching.core.bazi_rules.fact_graph import (
                build_rule_evaluation_context,
            )

            context = build_rule_evaluation_context(graph)
        return _evaluate_activation(args, context)
    if operator in {"fact_equals", "fact_in"}:
        path = str(args["path"])
        if _path_unknown(graph, path):
            return _trace(
                operator,
                TruthValue.UNKNOWN,
                path=path,
                reason="uncertain_fact_dependency",
            )
        actual = _fact_path(graph, path)
        matched = (
            actual == args["value"]
            if operator == "fact_equals"
            else actual in args["values"]
        )
        return _trace(
            operator,
            TruthValue.TRUE if matched else TruthValue.FALSE,
            path=path,
            actual=actual,
        )
    if operator == "exists_occurrence":
        matches = [
            item.id for item in graph.occurrences if _matches_occurrence(item, args)
        ]
        if matches:
            return _trace(operator, TruthValue.TRUE, matches=matches)
        exact = _uncertain_match_possible(graph, "occurrences", args)
        may_add = (
            exact
            if exact is not None
            else _filter_positions_may_include_unknown(graph, args.get("positions", ()))
        )
        if may_add:
            return _trace(
                operator,
                TruthValue.UNKNOWN,
                matches=[],
                reason="uncertain_position_may_add_occurrence",
            )
        return _trace(operator, TruthValue.FALSE, matches=[])
    if operator == "count_compare":
        path = str(args["path"])
        where = args["where"]
        match = _matcher(path)
        exact_support = _exact_hour_count_support(graph, path, where)
        if exact_support is not None:
            support = exact_support
            lower, upper = support[0], support[-1]
        else:
            lower = sum(1 for item in _collection(graph, path) if match(item, where))
            if path == "combinations":
                upper = _combination_count_upper_bound(graph, where, lower)
            else:
                upper = (
                    COLLECTION_GLOBAL_MAXIMA[path]
                    if _collection_may_change(graph, path, where)
                    else lower
                )
            upper = max(lower, upper)
            support = tuple(range(lower, upper + 1))
        outcomes = {
            _compare(value, str(args["comparator"]), int(args["value"]))
            for value in support
        }
        details: dict[str, Any] = {"path": path, "interval": [lower, upper]}
        if exact_support is not None:
            details["support"] = list(support)
        if len(outcomes) == 1:
            truth = TruthValue.TRUE if outcomes.pop() else TruthValue.FALSE
            return _trace(operator, truth, **details)
        return _trace(
            operator,
            TruthValue.UNKNOWN,
            **details,
            reason=(
                "exact_count_support_crosses_threshold"
                if exact_support is not None
                else "count_interval_crosses_threshold"
            ),
        )
    if operator == "relation_exists":
        matches = [item.id for item in graph.relations if _matches_relation(item, args)]
        if matches:
            return _trace(operator, TruthValue.TRUE, matches=matches)
        if _relation_may_be_added(graph, args):
            return _trace(
                operator,
                TruthValue.UNKNOWN,
                matches=[],
                reason="uncertain_position_may_add_relation",
            )
        return _trace(operator, TruthValue.FALSE, matches=[])
    if operator == "root_exists":
        matches = [item.id for item in graph.roots if _matches_root(item, args)]
        if matches:
            return _trace(operator, TruthValue.TRUE, matches=matches)
        exact = _uncertain_match_possible(graph, "roots", args)
        may_add = (
            exact
            if exact is not None
            else _filter_positions_may_include_unknown(graph, args.get("positions", ()))
        )
        if may_add:
            return _trace(
                operator,
                TruthValue.UNKNOWN,
                matches=[],
                reason="uncertain_position_may_add_root",
            )
        return _trace(operator, TruthValue.FALSE, matches=[])
    if operator == "month_command_equals":
        candidates = graph.month_command.at(str(args["level"]))
        matched = any(
            (args.get("stem") is None or item.stem == args["stem"])
            and (args.get("element") is None or item.element == args["element"])
            and (args.get("god") is None or item.ten_god == args["god"])
            for item in candidates
        )
        return _trace(
            operator,
            TruthValue.TRUE if matched else TruthValue.FALSE,
            level=args["level"],
            candidate_stems=[item.stem for item in candidates],
        )
    if operator == "god_exposed":
        where = {
            "gods": args["gods"],
            "positions": args.get("positions", ()),
            "layers": ("stem",),
            "exposed": True,
            "include_day_master": args.get("include_day_master", False),
        }
        matches = [
            item.id for item in graph.occurrences if _matches_occurrence(item, where)
        ]
        if matches:
            return _trace(operator, TruthValue.TRUE, matches=matches)
        exact = _uncertain_match_possible(graph, "occurrences", where)
        may_add = (
            exact
            if exact is not None
            else _filter_positions_may_include_unknown(graph, args.get("positions", ()))
        )
        if may_add:
            return _trace(
                operator,
                TruthValue.UNKNOWN,
                matches=[],
                reason="uncertain_position_may_expose_god",
            )
        return _trace(operator, TruthValue.FALSE, matches=[])
    if operator == "combination_complete":
        matches = [
            item.id for item in graph.combinations if _matches_combination(item, args)
        ]
        if matches:
            return _trace(
                operator,
                TruthValue.TRUE,
                matches=matches,
                transformation_inferred=False,
            )
        if _combination_may_be_added(graph, args):
            return _trace(
                operator,
                TruthValue.UNKNOWN,
                matches=[],
                reason="uncertain_position_may_complete_combination",
                transformation_inferred=False,
            )
        return _trace(
            operator, TruthValue.FALSE, matches=[], transformation_inferred=False
        )
    raise AssertionError(operator)


def evaluate_predicate(
    predicate: PredicateNode | Mapping[str, Any],
    graph: BaziFactGraph | BaziFactEnvelope | RuleEvaluationContext,
) -> EvaluationResult:
    """Evaluate a predicate with Kleene truth and a stable evidence trace."""

    node = parse_predicate(predicate)
    if isinstance(graph, RuleEvaluationContext):
        context = graph
        if isinstance(context.graph, BaziFactGraph):
            return _evaluate_graph(node, context.graph, context)
        from iching.core.bazi_rules.fact_graph import build_rule_evaluation_context

        source_activations = tuple(
            item for item in context.activations if item.origin == "source_rule"
        )
        world_results = tuple(
            _evaluate_graph(
                node,
                world,
                build_rule_evaluation_context(
                    world,
                    source_activations=source_activations,
                ),
            )
            for world in context.graph.worlds
        )
        truths = {item.truth for item in world_results}
        truth = next(iter(truths)) if len(truths) == 1 else TruthValue.UNKNOWN
        return _trace(
            "possible_worlds",
            truth,
            children=tuple(item.trace for item in world_results),
            world_digests=[world.digest for world in context.graph.worlds],
            reason="candidate_worlds_disagree"
            if len(truths) > 1
            else "candidate_worlds_agree",
        )
    if isinstance(graph, BaziFactGraph):
        return _evaluate_graph(node, graph)
    world_results = tuple(_evaluate_graph(node, world) for world in graph.worlds)
    truths = {item.truth for item in world_results}
    truth = next(iter(truths)) if len(truths) == 1 else TruthValue.UNKNOWN
    return _trace(
        "possible_worlds",
        truth,
        children=tuple(item.trace for item in world_results),
        world_digests=[world.digest for world in graph.worlds],
        reason="candidate_worlds_disagree"
        if len(truths) > 1
        else "candidate_worlds_agree",
    )
