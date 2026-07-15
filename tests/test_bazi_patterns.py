from __future__ import annotations

import importlib
import json
from typing import Any

import pytest

from iching.core.bazi_structure import (
    BRANCH_ELEMENTS,
    HIDDEN_STEMS,
    STEM_ELEMENTS,
    _ten_god,
    build_structure_profile,
)


def _chart(*texts: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    labels = ("年", "月", "日", "时")
    day_stem = texts[2][0]
    pillars = []
    for label, text in zip(labels, texts):
        stem, branch = text
        pillars.append({
            "label": label,
            "stem": stem,
            "branch": branch,
            "text": text,
            "stem_element": STEM_ELEMENTS[stem],
            "branch_element": BRANCH_ELEMENTS[branch],
            "ten_god": "日主" if label == "日" else _ten_god(day_stem, stem),
            "hidden_stems": [
                {
                    "stem": hidden,
                    "element": STEM_ELEMENTS[hidden],
                    "ten_god": _ten_god(day_stem, hidden),
                }
                for hidden in HIDDEN_STEMS[branch]
            ],
        })
    structure = build_structure_profile(
        pillars,
        gender=None,
        shensha_hits=[],
        seasonal_status={"木": "囚", "火": "死", "土": "休", "金": "旺", "水": "相"},
    )
    return pillars, structure


def test_ordinary_pattern_tracks_break_and_rescue_from_month_command() -> None:
    module = importlib.import_module("iching.core.bazi_patterns")
    pillars, structure = _chart("丁卯", "癸酉", "甲午", "辛未")

    result = module.assess_patterns(pillars, structure)
    officer = next(item for item in result["ordinary"] if item["name"] == "正官")

    assert officer["status"] == "rescued"
    assert any(item["kind"] == "month_command" for item in officer["evidence"])
    assert any(item["kind"] == "transparent" for item in officer["evidence"])
    assert "伤官见官" in officer["constraints"]
    assert "印星制伤" in officer["rescues"]
    assert result["primary"]["name"] == "正官"
    assert {item["id"] for item in result["evidence"]} >= set(result["primary"]["evidence_ids"])
    assert json.loads(json.dumps(result, ensure_ascii=False)) == result


@pytest.mark.parametrize(("month_branch", "expected"), [
    ("酉", "正官"),
    ("申", "七杀"),
    ("未", "正财"),
    ("辰", "偏财"),
    ("巳", "食神"),
    ("午", "伤官"),
    ("子", "正印"),
    ("亥", "偏印"),
    ("寅", "建禄"),
    ("卯", "阳刃"),
])
def test_all_ordinary_month_command_patterns_are_executable(
    month_branch: str,
    expected: str,
) -> None:
    module = importlib.import_module("iching.core.bazi_patterns")
    pillars, structure = _chart("乙丑", f"乙{month_branch}", "甲午", "丙戌")

    result = module.assess_patterns(pillars, structure)
    item = next(pattern for pattern in result["ordinary"] if pattern["name"] == expected)

    assert item["status"] != "not_candidate"
    assert any(evidence["kind"] == "month_command" for evidence in item["evidence"])


def test_month_hidden_candidate_can_form_through_a_complete_meeting() -> None:
    module = importlib.import_module("iching.core.bazi_patterns")
    pillars, structure = _chart("乙申", "乙辰", "甲子", "丁午")

    result = module.assess_patterns(pillars, structure)
    resource = next(item for item in result["ordinary"] if item["name"] == "正印")

    assert resource["status"] == "formed"
    assert any(item["kind"] == "meeting" for item in resource["evidence"])


def test_officer_pattern_without_rescue_breaks_and_mixed_officers_stay_distinct() -> None:
    module = importlib.import_module("iching.core.bazi_patterns")
    broken_pillars, broken_structure = _chart("丁卯", "乙酉", "甲午", "辛未")
    mixed_pillars, mixed_structure = _chart("庚寅", "乙酉", "甲午", "辛未")

    broken = next(
        item for item in module.assess_patterns(broken_pillars, broken_structure)["ordinary"]
        if item["name"] == "正官"
    )
    mixed = next(
        item for item in module.assess_patterns(mixed_pillars, mixed_structure)["ordinary"]
        if item["name"] == "正官"
    )

    assert broken["status"] == "broken"
    assert mixed["status"] == "mixed"


@pytest.mark.parametrize(("name", "texts"), [
    ("从财", ("戊戌", "己戌", "甲戌", "戊戌")),
    ("从杀", ("庚酉", "辛酉", "甲酉", "庚酉")),
    ("从儿", ("丙午", "丁巳", "甲午", "丙巳")),
    ("从旺", ("甲寅", "乙卯", "甲寅", "乙卯")),
    ("从强", ("壬子", "癸亥", "甲寅", "甲子")),
    ("曲直", ("甲亥", "乙卯", "甲未", "乙卯")),
    ("炎上", ("丙寅", "丁午", "丙戌", "丁午")),
    ("稼穑", ("戊辰", "己未", "戊戌", "己丑")),
    ("从革", ("庚巳", "辛酉", "庚丑", "辛酉")),
    ("润下", ("壬申", "癸子", "壬辰", "癸子")),
])
def test_strict_special_patterns_have_positive_gate_examples(
    name: str,
    texts: tuple[str, str, str, str],
) -> None:
    module = importlib.import_module("iching.core.bazi_patterns")
    pillars, structure = _chart(*texts)

    item = next(
        pattern for pattern in module.assess_patterns(pillars, structure)["special"]
        if pattern["name"] == name
    )

    assert item["status"] == "formed", (name, item)
    assert item["score"] >= 80
    assert item["evidence"]


def test_following_and_exclusive_patterns_reject_near_misses() -> None:
    module = importlib.import_module("iching.core.bazi_patterns")
    rooted_pillars, rooted_structure = _chart("戊戌", "己戌", "甲戌", "甲寅")
    controlled_pillars, controlled_structure = _chart("庚酉", "乙卯", "甲未", "乙亥")

    rooted_follow = next(
        item for item in module.assess_patterns(rooted_pillars, rooted_structure)["special"]
        if item["name"] == "从财"
    )
    controlled_exclusive = next(
        item for item in module.assess_patterns(controlled_pillars, controlled_structure)["special"]
        if item["name"] == "曲直"
    )

    assert rooted_follow["status"] == "rejected"
    assert any("日主有根" in reason for reason in rooted_follow["constraints"])
    assert controlled_exclusive["status"] == "rejected"
    assert any("克制五行" in reason for reason in controlled_exclusive["constraints"])


def test_incomplete_month_command_returns_an_explicit_empty_assessment() -> None:
    module = importlib.import_module("iching.core.bazi_patterns")
    pillars = [
        {"label": "年", "stem": "甲", "branch": "子", "text": "甲子"},
        {"label": "月", "stem": "乙", "branch": "待定", "text": "待定"},
        {"label": "日", "stem": "甲", "branch": "午", "text": "甲午"},
        {"label": "时", "stem": "丙", "branch": "戌", "text": "丙戌"},
    ]

    result = module.assess_patterns(pillars, {})

    assert result["primary"] is None
    assert result["ordinary"] == []
    assert result["special"] == []
    assert result["evidence"] == []
