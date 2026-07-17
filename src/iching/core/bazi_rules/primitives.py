"""Canonical, judgment-free Zi Ping primitives.

This module is deliberately a leaf: it imports no legacy BaZi module.  Legacy
modules keep their public containers and display strings until a later adapter
milestone; :func:`assert_legacy_primitive_parity` proves semantic parity without
changing those runtime contracts.
"""

from __future__ import annotations

from itertools import product
from types import MappingProxyType
from typing import Any, Mapping


PRIMITIVES_VERSION = "bazi-primitives-v1"

STEMS = ("甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸")
BRANCHES = ("子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥")
ELEMENTS = ("木", "火", "土", "金", "水")
PILLAR_POSITIONS = ("year", "month", "day", "hour")
POSITION_LABELS = MappingProxyType(
    {"year": "年", "month": "月", "day": "日", "hour": "时"}
)
LABEL_POSITIONS = MappingProxyType(
    {**{value: key for key, value in POSITION_LABELS.items()}, "時": "hour"}
)

STEM_ELEMENTS = MappingProxyType(
    dict(zip(STEMS, ("木", "木", "火", "火", "土", "土", "金", "金", "水", "水")))
)
BRANCH_ELEMENTS = MappingProxyType(
    dict(
        zip(
            BRANCHES,
            ("水", "土", "木", "木", "土", "火", "火", "土", "金", "金", "土", "水"),
        )
    )
)
HIDDEN_STEMS = MappingProxyType(
    {
        "子": ("癸",),
        "丑": ("己", "癸", "辛"),
        "寅": ("甲", "丙", "戊"),
        "卯": ("乙",),
        "辰": ("戊", "乙", "癸"),
        "巳": ("丙", "戊", "庚"),
        "午": ("丁", "己"),
        "未": ("己", "丁", "乙"),
        "申": ("庚", "壬", "戊"),
        "酉": ("辛",),
        "戌": ("戊", "辛", "丁"),
        "亥": ("壬", "甲"),
    }
)
QI_LEVELS = ("main", "secondary", "residual")

ELEMENT_GENERATES = MappingProxyType(
    {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
)
ELEMENT_CONTROLS = MappingProxyType(
    {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}
)

TEN_GODS = (
    "比肩",
    "劫财",
    "食神",
    "伤官",
    "偏财",
    "正财",
    "七杀",
    "正官",
    "偏印",
    "正印",
)

STEM_COMBINATIONS = MappingProxyType(
    {
        frozenset(("甲", "己")): "土",
        frozenset(("乙", "庚")): "金",
        frozenset(("丙", "辛")): "水",
        frozenset(("丁", "壬")): "木",
        frozenset(("戊", "癸")): "火",
    }
)
STEM_CLASHES = frozenset(
    frozenset(pair) for pair in (("甲", "庚"), ("乙", "辛"), ("丙", "壬"), ("丁", "癸"))
)
BRANCH_SIX_COMBINATIONS = MappingProxyType(
    {
        frozenset(("子", "丑")): "土",
        frozenset(("寅", "亥")): "木",
        frozenset(("卯", "戌")): "火",
        frozenset(("辰", "酉")): "金",
        frozenset(("巳", "申")): "水",
        frozenset(("午", "未")): None,
    }
)
BRANCH_CLASHES = frozenset(
    frozenset(pair)
    for pair in (
        ("子", "午"),
        ("丑", "未"),
        ("寅", "申"),
        ("卯", "酉"),
        ("辰", "戌"),
        ("巳", "亥"),
    )
)
BRANCH_HARMS = frozenset(
    frozenset(pair)
    for pair in (
        ("子", "未"),
        ("丑", "午"),
        ("寅", "巳"),
        ("卯", "辰"),
        ("申", "亥"),
        ("酉", "戌"),
    )
)
BRANCH_BREAKS = frozenset(
    frozenset(pair)
    for pair in (
        ("子", "酉"),
        ("丑", "辰"),
        ("寅", "亥"),
        ("卯", "午"),
        ("巳", "申"),
        ("未", "戌"),
    )
)
BRANCH_PUNISHMENT_PAIRS = frozenset(
    frozenset(pair)
    for pair in (
        ("寅", "巳"),
        ("巳", "申"),
        ("申", "寅"),
        ("丑", "未"),
        ("未", "戌"),
        ("戌", "丑"),
        ("子", "卯"),
    )
)
SELF_PUNISHMENT_BRANCHES = frozenset(("辰", "午", "酉", "亥"))
TRINES = (
    (("申", "子", "辰"), "水"),
    (("亥", "卯", "未"), "木"),
    (("寅", "午", "戌"), "火"),
    (("巳", "酉", "丑"), "金"),
)
MEETINGS = (
    (("亥", "子", "丑"), "水"),
    (("寅", "卯", "辰"), "木"),
    (("巳", "午", "未"), "火"),
    (("申", "酉", "戌"), "金"),
)


def ten_god(day_stem: str, other_stem: str) -> str:
    """Return the conventional ten-god relation for two valid stems."""

    if day_stem not in STEM_ELEMENTS or other_stem not in STEM_ELEMENTS:
        raise ValueError(f"invalid stem pair: {day_stem!r}, {other_stem!r}")
    day_element = ELEMENTS.index(STEM_ELEMENTS[day_stem])
    other_element = ELEMENTS.index(STEM_ELEMENTS[other_stem])
    same_polarity = STEMS.index(day_stem) % 2 == STEMS.index(other_stem) % 2
    relation = (other_element - day_element) % 5
    if relation == 0:
        return "比肩" if same_polarity else "劫财"
    if relation == 1:
        return "食神" if same_polarity else "伤官"
    if relation == 2:
        return "偏财" if same_polarity else "正财"
    if relation == 3:
        return "七杀" if same_polarity else "正官"
    return "偏印" if same_polarity else "正印"


def element_relation(day_element: str, other_element: str) -> str:
    if day_element not in ELEMENTS or other_element not in ELEMENTS:
        raise ValueError(f"invalid element pair: {day_element!r}, {other_element!r}")
    if day_element == other_element:
        return "同我"
    if ELEMENT_GENERATES[other_element] == day_element:
        return "生我"
    if ELEMENT_GENERATES[day_element] == other_element:
        return "我生"
    if ELEMENT_CONTROLS[day_element] == other_element:
        return "我克"
    return "克我"


def _semantic_stem_combinations(
    value: Mapping[frozenset[str], Any],
) -> dict[frozenset[str], str | None]:
    result: dict[frozenset[str], str | None] = {}
    for pair, display_or_element in value.items():
        if display_or_element in ELEMENTS or display_or_element is None:
            result[pair] = display_or_element
        else:
            text = str(display_or_element)
            result[pair] = next(
                (element for element in ELEMENTS if text.endswith(element)), None
            )
    return result


def _semantic_branch_combinations(
    value: Mapping[frozenset[str], Any],
) -> dict[frozenset[str], str | None]:
    result: dict[frozenset[str], str | None] = {}
    for pair, display_or_element in value.items():
        if display_or_element in ELEMENTS or display_or_element is None:
            result[pair] = display_or_element
        else:
            text = str(display_or_element)
            result[pair] = next(
                (element for element in ELEMENTS if text.endswith(element)), None
            )
    return result


def _semantic_groups(value: Any) -> tuple[tuple[tuple[str, ...], str], ...]:
    return tuple((tuple(group), str(element)) for group, element in value)


def assert_legacy_primitive_parity(
    *,
    structure_module: Any,
    metaphysics_module: Any,
    calendar_module: Any,
) -> None:
    """Raise when legacy public primitives have drifted semantically.

    Container types are intentionally *not* required to match.  For example,
    ``metaphysics.HIDDEN_STEMS`` remains list-valued while this canonical leaf is
    tuple-valued; display maps are normalized before comparison.
    """

    assert tuple(calendar_module.STEMS) == STEMS
    assert tuple(calendar_module.BRANCHES) == BRANCHES
    assert tuple(metaphysics_module.STEMS) == STEMS
    assert tuple(metaphysics_module.BRANCHES) == BRANCHES
    assert dict(structure_module.STEM_ELEMENTS) == STEM_ELEMENTS
    assert dict(structure_module.BRANCH_ELEMENTS) == BRANCH_ELEMENTS
    assert dict(metaphysics_module.STEM_ELEMENTS) == STEM_ELEMENTS
    assert dict(metaphysics_module.BRANCH_ELEMENTS) == BRANCH_ELEMENTS
    assert {
        key: tuple(value) for key, value in structure_module.HIDDEN_STEMS.items()
    } == HIDDEN_STEMS
    assert {
        key: tuple(value) for key, value in metaphysics_module.HIDDEN_STEMS.items()
    } == HIDDEN_STEMS
    assert (
        _semantic_stem_combinations(structure_module.STEM_COMBINATIONS)
        == STEM_COMBINATIONS
    )
    assert (
        _semantic_stem_combinations(metaphysics_module.STEM_COMBINATIONS)
        == STEM_COMBINATIONS
    )
    assert frozenset(structure_module.STEM_CLASHES) == STEM_CLASHES
    assert frozenset(metaphysics_module.STEM_CLASHES) == STEM_CLASHES
    assert (
        _semantic_branch_combinations(structure_module.BRANCH_COMBINATIONS)
        == BRANCH_SIX_COMBINATIONS
    )
    assert (
        _semantic_branch_combinations(metaphysics_module.BRANCH_SIX_COMBINATIONS)
        == BRANCH_SIX_COMBINATIONS
    )
    assert frozenset(structure_module.BRANCH_CLASHES) == BRANCH_CLASHES
    assert frozenset(metaphysics_module.BRANCH_CLASHES) == BRANCH_CLASHES
    assert frozenset(structure_module.BRANCH_HARMS) == BRANCH_HARMS
    assert frozenset(metaphysics_module.BRANCH_HARMS) == BRANCH_HARMS
    assert frozenset(structure_module.BRANCH_BREAKS) == BRANCH_BREAKS
    assert frozenset(metaphysics_module.BRANCH_BREAKS) == BRANCH_BREAKS
    assert _semantic_groups(structure_module.TRINES) == TRINES
    assert _semantic_groups(metaphysics_module.BRANCH_HARMONIES) == TRINES
    assert _semantic_groups(structure_module.MEETINGS) == MEETINGS
    assert _semantic_groups(metaphysics_module.BRANCH_MEETINGS) == MEETINGS
    for day_stem, other_stem in product(STEMS, repeat=2):
        expected = ten_god(day_stem, other_stem)
        assert structure_module._ten_god(day_stem, other_stem) == expected
        assert metaphysics_module._ten_god(day_stem, other_stem) == expected
