from __future__ import annotations

import importlib
import inspect
from itertools import product
from typing import Any

import pytest

from iching.core.bazi_rules.fact_graph import (
    build_bazi_fact_envelope,
    build_bazi_fact_envelope_from_graphs,
    build_bazi_fact_graph,
    build_rule_evaluation_context,
)
from iching.core.bazi_rules.predicates import (
    COLLECTION_GLOBAL_MAXIMA,
    FACT_PATH_REGISTRY,
    evaluate_predicate,
    parse_predicate,
)
from iching.core.bazi_rules.primitives import (
    BRANCHES,
    BRANCH_ELEMENTS,
    BRANCH_SIX_COMBINATIONS,
    ELEMENT_CONTROLS,
    ELEMENT_GENERATES,
    HIDDEN_STEMS,
    LABEL_POSITIONS,
    POSITION_LABELS,
    STEMS,
    STEM_COMBINATIONS,
    STEM_ELEMENTS,
    assert_legacy_primitive_parity,
    ten_god,
)
from iching.core.bazi_rules.schema import TruthValue


def _chart(*texts: str) -> list[dict[str, Any]]:
    return [
        {"label": label, "stem": text[0], "branch": text[1], "text": text}
        for label, text in zip(("年", "月", "日", "时"), texts)
    ]


OFFICER_CHART = _chart("甲申", "壬申", "乙巳", "戊寅")


def test_canonical_primitives_preserve_every_legacy_public_semantic() -> None:
    structure = importlib.import_module("iching.core.bazi_structure")
    metaphysics = importlib.import_module("iching.core.metaphysics")
    calendar = importlib.import_module("iching.core.calendar_engine")

    assert_legacy_primitive_parity(
        structure_module=structure,
        metaphysics_module=metaphysics,
        calendar_module=calendar,
    )
    assert isinstance(structure.HIDDEN_STEMS["申"], tuple)
    assert isinstance(metaphysics.HIDDEN_STEMS["申"], list)
    for day_stem, other_stem in product(STEMS, repeat=2):
        assert ten_god(day_stem, other_stem) == structure._ten_god(day_stem, other_stem)


def test_fact_graph_records_positions_qi_occurrences_roots_relations_and_complete_combinations() -> (
    None
):
    graph = build_bazi_fact_graph(OFFICER_CHART)

    assert [item.position for item in graph.pillars] == ["year", "month", "day", "hour"]
    assert graph.day_master.stem == "乙"
    assert graph.day_master.element == "木"
    assert graph.month_command.branch == "申"
    assert [(item.level, item.stem) for item in graph.month_command.qi] == [
        ("main", "庚"),
        ("secondary", "壬"),
        ("residual", "戊"),
    ]
    assert any(
        item.exposed and item.position == "month" and item.ten_god == "正印"
        for item in graph.occurrences
    )
    assert any(
        item.mode == "same_element" and item.position == "hour" and item.stem == "甲"
        for item in graph.roots
    )
    assert any(item.relation_type == "branch_punishment" for item in graph.relations)
    assert any(
        item.kind == "branch_six_combine" and set(item.required_values) == {"巳", "申"}
        for item in graph.combinations
    )
    assert all(item.complete for item in graph.combinations)
    assert all(not hasattr(item, "transformed") for item in graph.combinations)
    payload = repr(graph)
    for forbidden in ("weight", "strength", "theme", "pattern"):
        assert forbidden not in payload.lower()


def test_graph_digest_is_stable_for_explicit_positions_and_input_order() -> None:
    first = build_bazi_fact_graph(OFFICER_CHART)
    reordered = [
        {**OFFICER_CHART[2], "position": "day"},
        {**OFFICER_CHART[0], "position": "year"},
        {**OFFICER_CHART[3], "position": "hour"},
        {**OFFICER_CHART[1], "position": "month"},
    ]
    second = build_bazi_fact_graph(reordered)

    assert first == second
    assert first.digest == second.digest


def test_envelope_can_reuse_prebuilt_world_objects_by_identity() -> None:
    first = build_bazi_fact_graph(OFFICER_CHART)
    second = build_bazi_fact_graph(_chart("甲申", "壬申", "乙巳", "己卯"))

    envelope = build_bazi_fact_envelope_from_graphs((first, second))

    assert {id(item) for item in envelope.worlds} == {id(first), id(second)}
    assert (
        envelope.digest
        == build_bazi_fact_envelope(
            (OFFICER_CHART, _chart("甲申", "壬申", "乙巳", "己卯"))
        ).digest
    )


def test_public_fact_graph_signature_and_boolean_are_strict() -> None:
    assert list(inspect.signature(build_bazi_fact_graph).parameters) == [
        "pillars",
        "hour_uncertain",
    ]
    with pytest.raises(ValueError, match="boolean"):
        build_bazi_fact_graph(OFFICER_CHART, hour_uncertain="false")  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "pillars",
    [
        [
            {**item, "position": "century"} if index == 0 else item
            for index, item in enumerate(OFFICER_CHART)
        ],
        _chart("戊卯", "壬申", "乙巳", "戊寅"),
    ],
)
def test_invalid_explicit_position_or_sexagenary_polarity_is_rejected(
    pillars: list[dict[str, Any]],
) -> None:
    with pytest.raises(ValueError):
        build_bazi_fact_graph(pillars)


@pytest.mark.parametrize(
    ("predicate", "expected"),
    [
        (
            {"op": "fact_equals", "path": "day_master.stem", "value": "乙"},
            TruthValue.TRUE,
        ),
        (
            {
                "op": "fact_in",
                "path": "month_command.main_god",
                "values": ["正官", "七杀"],
            },
            TruthValue.TRUE,
        ),
        (
            {"op": "exists_occurrence", "gods": ["正官"], "layers": ["hidden"]},
            TruthValue.TRUE,
        ),
        (
            {
                "op": "count_compare",
                "path": "occurrences",
                "where": {"gods": ["正财"]},
                "comparator": ">=",
                "value": 1,
            },
            TruthValue.TRUE,
        ),
        (
            {"op": "relation_exists", "relation_types": ["branch_punishment"]},
            TruthValue.TRUE,
        ),
        ({"op": "root_exists", "mode": "same_element"}, TruthValue.TRUE),
        (
            {"op": "month_command_equals", "level": "main", "god": "正官"},
            TruthValue.TRUE,
        ),
        ({"op": "god_exposed", "gods": ["正财"]}, TruthValue.TRUE),
        (
            {
                "op": "combination_complete",
                "kinds": ["branch_six_combine"],
                "members": ["巳", "申"],
            },
            TruthValue.TRUE,
        ),
        (
            {
                "op": "not",
                "child": {
                    "op": "fact_equals",
                    "path": "day_master.stem",
                    "value": "甲",
                },
            },
            TruthValue.TRUE,
        ),
        (
            {
                "op": "all",
                "children": [
                    {"op": "fact_equals", "path": "day_master.stem", "value": "乙"},
                    {"op": "month_command_equals", "level": "main", "god": "正官"},
                ],
            },
            TruthValue.TRUE,
        ),
        (
            {
                "op": "any",
                "children": [
                    {"op": "fact_equals", "path": "day_master.stem", "value": "甲"},
                    {"op": "month_command_equals", "level": "main", "god": "正官"},
                ],
            },
            TruthValue.TRUE,
        ),
    ],
)
def test_every_closed_operator_evaluates_with_a_stable_trace(
    predicate: dict[str, Any], expected: TruthValue
) -> None:
    result = evaluate_predicate(predicate, build_bazi_fact_graph(OFFICER_CHART))

    assert result.truth is expected
    assert result.trace.as_dict()["truth"] == expected.value
    assert result.trace.as_dict() == result.trace.as_dict()


def test_day_master_is_excluded_from_god_exposed_unless_explicitly_requested() -> None:
    graph = build_bazi_fact_graph(_chart("丙子", "丁丑", "甲寅", "己卯"))
    predicate = {"op": "god_exposed", "gods": ["比肩"], "positions": ["day"]}

    assert evaluate_predicate(predicate, graph).truth is TruthValue.FALSE
    assert (
        evaluate_predicate({**predicate, "include_day_master": True}, graph).truth
        is TruthValue.TRUE
    )


def test_same_element_root_is_inclusive_while_exact_stem_is_narrower() -> None:
    graph = build_bazi_fact_graph(_chart("甲子", "丙寅", "甲午", "甲寅"))

    exact = [item for item in graph.roots if item.mode == "exact_stem"]
    inclusive = [item for item in graph.roots if item.mode == "same_element"]
    assert exact
    assert {item.id.replace(".exact_stem", ".same_element") for item in exact} <= {
        item.id for item in inclusive
    }
    assert (
        evaluate_predicate({"op": "root_exists", "mode": "exact_stem"}, graph).truth
        is TruthValue.TRUE
    )
    assert (
        evaluate_predicate({"op": "root_exists", "mode": "same_element"}, graph).truth
        is TruthValue.TRUE
    )


def test_stem_control_preserves_controller_and_controlled_direction() -> None:
    graph = build_bazi_fact_graph(_chart("甲子", "戊辰", "丙午", "庚寅"))
    forward = {
        "op": "relation_exists",
        "relation_types": ["stem_control"],
        "controller_positions": ["year"],
        "controller_values": ["甲"],
        "controlled_positions": ["month"],
        "controlled_values": ["戊"],
    }
    reverse = {
        **forward,
        "controller_positions": ["month"],
        "controller_values": ["戊"],
        "controlled_positions": ["year"],
        "controlled_values": ["甲"],
    }

    assert evaluate_predicate(forward, graph).truth is TruthValue.TRUE
    assert evaluate_predicate(reverse, graph).truth is TruthValue.FALSE
    relation = next(
        item for item in graph.relations if item.id == "rel.stem_control.year.month"
    )
    assert [(item.position, item.role) for item in relation.members] == [
        ("year", "controller"),
        ("month", "controlled"),
    ]


@pytest.mark.parametrize(
    "predicate",
    [
        {"op": "fact_equals", "path": "pillars.hour.stem", "value": "戊"},
        {"op": "exists_occurrence", "gods": ["比肩"]},
        {
            "op": "count_compare",
            "path": "occurrences",
            "where": {"gods": ["比肩"]},
            "comparator": "==",
            "value": 1,
        },
        {"op": "relation_exists", "relation_types": ["branch_clash"]},
        {"op": "root_exists", "mode": "exact_stem"},
        {"op": "god_exposed", "gods": ["正财"]},
    ],
)
def test_unknown_hour_propagates_unknown_for_every_hour_sensitive_leaf(
    predicate: dict[str, Any],
) -> None:
    graph = build_bazi_fact_graph(OFFICER_CHART, hour_uncertain=True)
    result = evaluate_predicate(predicate, graph)

    assert result.truth is TruthValue.UNKNOWN
    assert "reason" in result.trace.details
    assert graph.pillar("hour").stem is None
    assert graph.completeness.uncertain_positions == frozenset(("hour",))


def test_fixed_month_fact_remains_known_when_only_hour_is_uncertain() -> None:
    graph = build_bazi_fact_graph(OFFICER_CHART, hour_uncertain=True)
    result = evaluate_predicate(
        {"op": "month_command_equals", "level": "main", "god": "正官"},
        graph,
    )

    assert result.truth is TruthValue.TRUE


def test_unknown_hour_only_marks_a_combination_unknown_when_it_can_complete_it() -> (
    None
):
    impossible = build_bazi_fact_graph(OFFICER_CHART, hour_uncertain=True)
    one_missing = build_bazi_fact_graph(
        _chart("甲申", "丙子", "甲午", "戊辰"),
        hour_uncertain=True,
    )
    predicate = {"op": "combination_complete", "kinds": ["trine"]}

    assert evaluate_predicate(predicate, impossible).truth is TruthValue.FALSE
    assert evaluate_predicate(predicate, one_missing).truth is TruthValue.UNKNOWN
    explicit_impossible = {
        "op": "combination_complete",
        "kinds": ["trine"],
        "members": ["申", "子", "辰"],
    }
    assert evaluate_predicate(explicit_impossible, impossible).truth is TruthValue.FALSE


def test_absent_relation_with_filtered_known_position_stays_unknown_until_worlds_resolve_it() -> (
    None
):
    base = _chart("甲申", "丙子", "甲午", "庚寅")
    partial = build_bazi_fact_graph(base, hour_uncertain=True)
    predicate = {
        "op": "relation_exists",
        "relation_types": ["branch_clash"],
        "positions": ["year"],
    }
    worlds = build_bazi_fact_envelope((base, _chart("甲申", "丙子", "甲午", "辛卯")))

    assert evaluate_predicate(predicate, partial).truth is TruthValue.UNKNOWN
    assert evaluate_predicate(predicate, worlds).truth is TruthValue.UNKNOWN


def test_partial_count_uses_exact_legal_world_support() -> None:
    base = ("甲申", "丙子", "甲午")
    first_world = _chart(*base, "庚寅")
    partial = build_bazi_fact_graph(first_world, hour_uncertain=True)
    predicate = {
        "op": "count_compare",
        "path": "relations",
        "where": {},
        "comparator": "<=",
        "value": 20,
    }
    partial_result = evaluate_predicate(predicate, partial)
    complete_results = tuple(
        evaluate_predicate(predicate, world) for world in _legal_hour_world_graphs(base)
    )
    support = {int(item.trace.details["interval"][0]) for item in complete_results}
    worlds = build_bazi_fact_envelope((first_world, _chart(*base, "辛卯")))

    assert {item.truth for item in complete_results} == {TruthValue.TRUE}
    assert partial_result.truth is TruthValue.TRUE
    assert partial_result.trace.details["support"] == tuple(sorted(support))
    assert partial_result.trace.details["interval"] == (min(support), max(support))
    assert evaluate_predicate(predicate, worlds).truth is TruthValue.TRUE


def _legal_hour_world_graphs(base: tuple[str, str, str]) -> tuple[Any, ...]:
    return tuple(
        build_bazi_fact_graph(_chart(*base, stem + branch))
        for stem, branch in product(STEMS, BRANCHES)
        if STEMS.index(stem) % 2 == BRANCHES.index(branch) % 2
    )


def test_unknown_hour_occurrence_count_equality_uses_exact_world_support() -> None:
    base = ("甲申", "壬申", "乙巳")
    partial = build_bazi_fact_graph(_chart(*base, "戊寅"), hour_uncertain=True)
    predicate = {
        "op": "count_compare",
        "path": "occurrences",
        "where": {},
        "comparator": "==",
        "value": 11,
    }
    complete_results = [
        evaluate_predicate(predicate, world) for world in _legal_hour_world_graphs(base)
    ]

    assert {item.truth for item in complete_results} == {TruthValue.FALSE}
    assert evaluate_predicate(predicate, partial).truth is TruthValue.FALSE


@pytest.mark.parametrize(
    "predicate",
    [
        {
            "op": "count_compare",
            "path": "occurrences",
            "where": {"gods": ["比肩"], "positions": ["hour"]},
            "comparator": "!=",
            "value": 0,
        },
        {
            "op": "count_compare",
            "path": "roots",
            "where": {"mode": "exact_stem", "positions": ["hour"]},
            "comparator": ">",
            "value": 0,
        },
        {
            "op": "count_compare",
            "path": "relations",
            "where": {
                "relation_types": ["stem_combine"],
                "member_filters": [{"values": ["甲"]}],
            },
            "comparator": ">=",
            "value": 1,
        },
        {
            "op": "count_compare",
            "path": "relations",
            "where": {
                "relation_types": ["branch_clash"],
                "positions": ["hour"],
            },
            "comparator": "<",
            "value": 1,
        },
        {
            "op": "count_compare",
            "path": "combinations",
            "where": {"kinds": ["trine"], "result_elements": ["水"]},
            "comparator": "<=",
            "value": 2,
        },
    ],
)
def test_unknown_hour_count_support_matches_all_legal_worlds(
    predicate: dict[str, Any],
) -> None:
    base = ("甲申", "壬申", "乙巳")
    partial = build_bazi_fact_graph(_chart(*base, "戊寅"), hour_uncertain=True)
    complete_results = tuple(
        evaluate_predicate(predicate, world) for world in _legal_hour_world_graphs(base)
    )
    complete_truths = {item.truth for item in complete_results}
    support = {int(item.trace.details["interval"][0]) for item in complete_results}
    expected = (
        next(iter(complete_truths)) if len(complete_truths) == 1 else TruthValue.UNKNOWN
    )

    result = evaluate_predicate(predicate, partial)

    assert result.truth is expected
    assert result.trace.details["support"] == tuple(sorted(support))
    assert result.trace.details["interval"] == (min(support), max(support))


def test_three_pillar_input_automatically_marks_hour_unknown() -> None:
    graph = build_bazi_fact_graph(OFFICER_CHART[:3])

    assert graph.completeness.hour_known is False
    assert graph.completeness.uncertain_positions == frozenset(("hour",))
    assert (
        evaluate_predicate(
            {"op": "fact_equals", "path": "pillars.hour.branch", "value": "子"}, graph
        ).truth
        is TruthValue.UNKNOWN
    )


def test_count_interval_can_still_prove_a_monotone_result() -> None:
    graph = build_bazi_fact_graph(OFFICER_CHART, hour_uncertain=True)
    result = evaluate_predicate(
        {
            "op": "count_compare",
            "path": "occurrences",
            "where": {},
            "comparator": ">=",
            "value": 1,
        },
        graph,
    )

    assert result.truth is TruthValue.TRUE
    assert result.trace.details["interval"][0] > 1


def test_possible_world_envelope_returns_consensus_or_unknown() -> None:
    one = _chart("甲申", "壬申", "乙巳", "戊寅")
    two = _chart("甲申", "壬申", "乙巳", "己卯")
    envelope = build_bazi_fact_envelope((one, two))

    stable = evaluate_predicate(
        {"op": "fact_equals", "path": "day_master.stem", "value": "乙"}, envelope
    )
    variable = evaluate_predicate(
        {"op": "god_exposed", "gods": ["正财"], "positions": ["hour"]}, envelope
    )

    assert stable.truth is TruthValue.TRUE
    assert variable.truth is TruthValue.UNKNOWN
    assert variable.trace.details["reason"] == "candidate_worlds_disagree"


def test_fact_envelope_requires_complete_worlds_and_caps_trace_growth() -> None:
    with pytest.raises(ValueError, match="complete"):
        build_bazi_fact_envelope((OFFICER_CHART[:3],))
    with pytest.raises(ValueError, match="64"):
        build_bazi_fact_envelope([OFFICER_CHART for _ in range(65)])


def test_relation_members_bind_identity_god_and_canonical_pillar_geometry() -> None:
    graph = build_bazi_fact_graph(_chart("甲申", "壬申", "乙巳", "戊寅"))

    month_hour = next(
        item for item in graph.relations if item.id == "rel.stem_control.month.hour"
    )
    assert month_hour.position_distance == 2
    assert month_hour.intervening_positions == ("day",)
    assert month_hour.adjacent is False
    assert [
        (
            member.position,
            member.occurrence_id,
            member.element,
            member.ten_god,
        )
        for member in month_hour.members
    ] == [
        ("month", "occ.month.stem.壬", "水", "正印"),
        ("hour", "occ.hour.stem.戊", "土", "正财"),
    ]

    adjacent = next(
        item
        for item in graph.relations
        if item.id == "rel.branch_six_combine.month.day"
    )
    assert adjacent.position_distance == 1
    assert adjacent.intervening_positions == ()
    assert adjacent.adjacent is True


def test_relation_member_filters_use_injective_non_greedy_same_relation_binding() -> (
    None
):
    graph = build_bazi_fact_graph(_chart("甲子", "己巳", "丙午", "庚寅"))
    flexible_then_specific = {
        "op": "relation_exists",
        "relation_types": ["stem_combine"],
        "member_filters": [
            {"values": ["甲", "己"]},
            {"values": ["甲"]},
        ],
    }
    duplicate_specific = {
        **flexible_then_specific,
        "member_filters": [
            {"values": ["甲"]},
            {"values": ["甲"]},
        ],
    }

    assert evaluate_predicate(flexible_then_specific, graph).truth is TruthValue.TRUE
    assert evaluate_predicate(duplicate_specific, graph).truth is TruthValue.FALSE
    parsed = parse_predicate(
        {
            **flexible_then_specific,
            "member_filters": list(reversed(flexible_then_specific["member_filters"])),
        }
    )
    assert parsed == parse_predicate(flexible_then_specific)


def test_relation_adjacency_and_member_filters_preserve_unknown_positions() -> None:
    graph = build_bazi_fact_graph(_chart("甲申", "壬申", "乙巳", "戊寅"))
    nonadjacent = {
        "op": "relation_exists",
        "relation_types": ["stem_control"],
        "member_filters": [
            {"positions": ["month"], "gods": ["正印"]},
            {"positions": ["hour"], "gods": ["正财"]},
        ],
        "adjacent": True,
    }
    unknown_hour = {
        "op": "relation_exists",
        "relation_types": ["stem_combine"],
        "member_filters": [{"positions": ["hour"]}],
        "adjacent": True,
    }
    unknown_directional_alternatives = {
        "op": "relation_exists",
        "relation_types": ["stem_control"],
        "layers": ["stem"],
        "controller_gods": ["偏财", "正财"],
        "controlled_gods": ["偏印", "正印"],
    }

    assert evaluate_predicate(nonadjacent, graph).truth is TruthValue.FALSE
    assert (
        evaluate_predicate(
            unknown_hour,
            build_bazi_fact_graph(OFFICER_CHART, hour_uncertain=True),
        ).truth
        is TruthValue.UNKNOWN
    )
    assert (
        evaluate_predicate(
            unknown_directional_alternatives,
            build_bazi_fact_graph(OFFICER_CHART, hour_uncertain=True),
        ).truth
        is TruthValue.UNKNOWN
    )
    with pytest.raises(ValueError, match="adjacent"):
        parse_predicate({**nonadjacent, "adjacent": 1})


@pytest.mark.parametrize(
    "predicate",
    [
        {
            "op": "exists_occurrence",
            "stems": ["甲"],
            "elements": ["金"],
            "gods": [],
            "positions": ["hour"],
            "layers": ["stem"],
            "qi_levels": [],
            "exposed": True,
            "include_day_master": False,
        },
        {
            "op": "relation_exists",
            "relation_types": ["stem_control"],
            "layers": ["stem"],
            "controller_values": ["甲"],
            "controlled_values": ["乙"],
        },
        {
            "op": "relation_exists",
            "relation_types": ["stem_combine"],
            "layers": ["stem"],
            "values": ["甲", "丙"],
        },
        {
            "op": "relation_exists",
            "relation_types": ["stem_combine"],
            "layers": ["branch"],
        },
        {
            "op": "relation_exists",
            "relation_types": ["stem_control"],
            "member_filters": [{"roles": ["participant"]}],
        },
        {
            "op": "relation_exists",
            "relation_types": ["stem_combine"],
            "member_filters": [{"values": ["甲"], "gods": ["正官"]}],
        },
        {
            "op": "relation_exists",
            "relation_types": ["stem_combine"],
            "values": ["甲", "己"],
            "excluded_member_gods": ["劫财"],
        },
        {
            "op": "relation_exists",
            "relation_types": ["stem_combine"],
            "member_filters": [
                {
                    "values": ["己"],
                    "occurrence_ids": ["occ.hour.stem.甲"],
                }
            ],
        },
    ],
)
def test_incomplete_filter_feasibility_agrees_with_all_legal_hour_worlds(
    predicate: dict[str, Any],
) -> None:
    base = ("甲申", "壬申", "乙巳")
    incomplete = build_bazi_fact_graph(
        _chart(*base, "戊寅"),
        hour_uncertain=True,
    )
    complete_truths = {
        evaluate_predicate(
            predicate, build_bazi_fact_graph(_chart(*base, stem + branch))
        ).truth
        for stem, branch in product(STEMS, BRANCHES)
        if STEMS.index(stem) % 2 == BRANCHES.index(branch) % 2
    }

    assert complete_truths == {TruthValue.FALSE}
    assert evaluate_predicate(predicate, incomplete).truth is TruthValue.FALSE


def test_directional_relation_god_lists_are_allowed_value_alternatives() -> None:
    graph = build_bazi_fact_graph(_chart("癸卯", "己酉", "甲子", "丁卯"))
    predicate = {
        "op": "relation_exists",
        "relation_types": ["stem_control"],
        "layers": ["stem"],
        "adjacent": True,
        "controller_gods": ["偏财", "正财"],
        "controlled_gods": ["偏印", "正印"],
    }

    assert evaluate_predicate(predicate, graph).truth is TruthValue.TRUE


@pytest.mark.parametrize(
    ("texts", "predicate", "expected"),
    [
        (
            ("乙卯", "丁亥", "丁未", "庚戌"),
            {
                "op": "activation_exists",
                "gods": ["伤官"],
                "families": ["output"],
                "positions": [],
                "origins": [],
                "scope": "generic",
            },
            TruthValue.FALSE,
        ),
        (
            ("己卯", "辛未", "壬寅", "辛亥"),
            {
                "op": "activation_exists",
                "gods": ["伤官"],
                "families": ["output"],
                "positions": [],
                "origins": [],
                "scope": "generic",
            },
            TruthValue.UNKNOWN,
        ),
        (
            ("丁丑", "壬寅", "己巳", "丙寅"),
            {
                "op": "activation_exists",
                "gods": ["伤官"],
                "families": ["output"],
                "positions": [],
                "origins": [],
                "scope": "generic",
            },
            TruthValue.FALSE,
        ),
        (
            ("丁卯", "癸酉", "甲午", "辛未"),
            {
                "op": "activation_exists",
                "gods": ["伤官"],
                "families": ["output"],
                "positions": ["year"],
                "origins": ["exposed_stem"],
                "scope": "generic",
            },
            TruthValue.TRUE,
        ),
    ],
)
def test_activation_exists_distinguishes_exposed_hidden_and_pending_groups(
    texts: tuple[str, str, str, str],
    predicate: dict[str, Any],
    expected: TruthValue,
) -> None:
    context = build_rule_evaluation_context(build_bazi_fact_graph(_chart(*texts)))

    result = evaluate_predicate(predicate, context)

    assert result.truth is expected


def test_relation_member_god_binding_cannot_be_faked_by_independent_facts() -> None:
    predicate = {
        "op": "relation_exists",
        "relation_types": ["stem_combine"],
        "adjacent": True,
        "member_filters": [{"gods": ["七杀"]}],
        "excluded_member_gods": ["正官"],
    }
    li = build_bazi_fact_graph(_chart("庚寅", "乙酉", "甲子", "戊辰"))
    independent = build_bazi_fact_graph(_chart("庚寅", "丁亥", "甲子", "壬申"))

    assert evaluate_predicate(predicate, li).truth is TruthValue.TRUE
    assert evaluate_predicate(predicate, independent).truth is TruthValue.FALSE
    counted = evaluate_predicate(
        {
            "op": "count_compare",
            "path": "relations",
            "where": {key: value for key, value in predicate.items() if key != "op"},
            "comparator": ">=",
            "value": 1,
        },
        li,
    )
    assert counted.truth is TruthValue.TRUE


def test_activation_context_for_envelope_derives_each_world_before_consensus() -> None:
    xuan = _chart("己卯", "辛未", "壬寅", "辛亥")
    context = build_rule_evaluation_context(build_bazi_fact_envelope((xuan,)))
    predicate = {
        "op": "activation_exists",
        "gods": ["伤官"],
        "families": ["output"],
        "positions": [],
        "origins": [],
        "scope": "generic",
    }

    assert evaluate_predicate(predicate, context).truth is TruthValue.UNKNOWN


def test_public_closed_registries_cannot_be_mutated_or_extended() -> None:
    registries = (
        FACT_PATH_REGISTRY,
        COLLECTION_GLOBAL_MAXIMA,
        POSITION_LABELS,
        LABEL_POSITIONS,
        STEM_ELEMENTS,
        BRANCH_ELEMENTS,
        HIDDEN_STEMS,
        ELEMENT_GENERATES,
        ELEMENT_CONTROLS,
        STEM_COMBINATIONS,
        BRANCH_SIX_COMBINATIONS,
    )
    for registry in registries:
        key = next(iter(registry))
        with pytest.raises(TypeError):
            registry[key] = registry[key]  # type: ignore[index]

    with pytest.raises(TypeError):
        FACT_PATH_REGISTRY["runtime.injected"] = FACT_PATH_REGISTRY[  # type: ignore[index]
            "day_master.stem"
        ]
    with pytest.raises(ValueError, match="unknown fact path"):
        parse_predicate({"op": "fact_equals", "path": "runtime.injected", "value": "x"})


def test_unknown_hour_combination_count_uses_feasible_positional_bound() -> None:
    partial = build_bazi_fact_graph(OFFICER_CHART, hour_uncertain=True)
    hour_pillars = (
        "丙子",
        "丁丑",
        "戊寅",
        "己卯",
        "庚辰",
        "辛巳",
        "壬午",
        "癸未",
        "甲申",
        "乙酉",
        "丙戌",
        "丁亥",
    )
    worlds = tuple(_chart("甲申", "壬申", "乙巳", hour) for hour in hour_pillars)
    envelope = build_bazi_fact_envelope(worlds)
    base = {
        "op": "count_compare",
        "path": "combinations",
        "where": {"result_elements": ["水"]},
    }

    equal_two = {**base, "comparator": "==", "value": 2}
    at_most_four = {**base, "comparator": "<=", "value": 4}
    above_four = {**base, "comparator": ">", "value": 4}
    partial_equal = evaluate_predicate(equal_two, partial)

    assert partial_equal.truth is TruthValue.UNKNOWN
    assert partial_equal.trace.details["interval"] == (2, 4)
    assert evaluate_predicate(at_most_four, partial).truth is TruthValue.TRUE
    assert evaluate_predicate(above_four, partial).truth is TruthValue.FALSE
    support = {
        sum(1 for item in world.combinations if item.result_element == "水")
        for world in envelope.worlds
    }
    assert support == {2, 3, 4}
    assert evaluate_predicate(equal_two, envelope).truth is TruthValue.UNKNOWN
    assert evaluate_predicate(at_most_four, envelope).truth is TruthValue.TRUE
    assert evaluate_predicate(above_four, envelope).truth is TruthValue.FALSE


@pytest.mark.parametrize(
    ("predicate", "expected"),
    [
        (
            {
                "op": "all",
                "children": [
                    {"op": "fact_equals", "path": "day_master.stem", "value": "甲"},
                    {"op": "fact_equals", "path": "pillars.hour.stem", "value": "戊"},
                ],
            },
            TruthValue.FALSE,
        ),
        (
            {
                "op": "all",
                "children": [
                    {"op": "fact_equals", "path": "day_master.stem", "value": "乙"},
                    {"op": "fact_equals", "path": "pillars.hour.stem", "value": "戊"},
                ],
            },
            TruthValue.UNKNOWN,
        ),
        (
            {
                "op": "any",
                "children": [
                    {"op": "fact_equals", "path": "day_master.stem", "value": "乙"},
                    {"op": "fact_equals", "path": "pillars.hour.stem", "value": "戊"},
                ],
            },
            TruthValue.TRUE,
        ),
        (
            {
                "op": "any",
                "children": [
                    {"op": "fact_equals", "path": "day_master.stem", "value": "甲"},
                    {"op": "fact_equals", "path": "pillars.hour.stem", "value": "戊"},
                ],
            },
            TruthValue.UNKNOWN,
        ),
        (
            {
                "op": "not",
                "child": {
                    "op": "fact_equals",
                    "path": "pillars.hour.stem",
                    "value": "戊",
                },
            },
            TruthValue.UNKNOWN,
        ),
    ],
)
def test_kleene_truth_tables_preserve_unknown(
    predicate: dict[str, Any], expected: TruthValue
) -> None:
    graph = build_bazi_fact_graph(OFFICER_CHART, hour_uncertain=True)

    assert evaluate_predicate(predicate, graph).truth is expected


@pytest.mark.parametrize(
    "bad",
    [
        {"op": "all", "children": []},
        {"op": "mystery"},
        {"op": "fact_equals", "path": "__class__.__mro__", "value": "x"},
        {"op": "fact_equals", "path": "day_master.stem", "value": 1},
        {"op": "fact_in", "path": "day_master.stem", "values": []},
        {
            "op": "count_compare",
            "path": "occurrences",
            "where": {},
            "comparator": ">=",
            "value": True,
        },
        {"op": "root_exists"},
        {"op": "month_command_equals", "god": "正官"},
        {"op": "god_exposed", "gods": ["正官"], "surprise": True},
    ],
)
def test_predicate_contract_rejects_ambiguous_or_open_input(
    bad: dict[str, Any],
) -> None:
    with pytest.raises(ValueError):
        parse_predicate(bad)


def test_predicate_ast_depth_is_bounded() -> None:
    value: dict[str, Any] = {
        "op": "fact_equals",
        "path": "day_master.stem",
        "value": "乙",
    }
    for _ in range(33):
        value = {"op": "not", "child": value}

    with pytest.raises(ValueError, match="depth"):
        parse_predicate(value)


def test_predicate_ast_node_count_is_bounded() -> None:
    leaf = {"op": "fact_equals", "path": "day_master.stem", "value": "乙"}
    value = {"op": "all", "children": [leaf for _ in range(1024)]}

    with pytest.raises(ValueError, match="nodes"):
        parse_predicate(value)


def test_parsed_predicates_and_traces_are_deeply_immutable_and_idempotent() -> None:
    raw = {
        "op": "all",
        "children": [
            {"op": "fact_equals", "path": "day_master.stem", "value": "乙"},
            {
                "op": "count_compare",
                "path": "occurrences",
                "where": {"gods": ["正官", "七杀"]},
                "comparator": ">=",
                "value": 1,
            },
        ],
    }
    parsed = parse_predicate(raw)
    raw["children"].clear()

    assert parse_predicate(parsed) is parsed
    assert parsed.children
    with pytest.raises(TypeError):
        parsed.children[0].arguments["path"] = "day_master.element"  # type: ignore[index]
    result = evaluate_predicate(parsed, build_bazi_fact_graph(OFFICER_CHART))
    copied = result.trace.as_dict()
    copied["details"]["external"] = True
    assert "external" not in result.trace.details


def test_commutative_predicate_parse_has_stable_child_and_trace_order() -> None:
    children = [
        {"op": "fact_equals", "path": "day_master.stem", "value": "乙"},
        {"op": "month_command_equals", "level": "main", "god": "正官"},
    ]
    first = parse_predicate({"op": "all", "children": children})
    second = parse_predicate({"op": "all", "children": list(reversed(children))})
    graph = build_bazi_fact_graph(OFFICER_CHART)

    assert first == second
    assert (
        evaluate_predicate(first, graph).trace.as_dict()
        == evaluate_predicate(second, graph).trace.as_dict()
    )
