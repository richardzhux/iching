from __future__ import annotations

from datetime import datetime

import pytest

from iching.core.metaphysics import build_metaphysics_chart


def test_known_lunar_new_year_chart() -> None:
    chart = build_metaphysics_chart(datetime(2024, 2, 10, 12), timezone_name="Asia/Shanghai")

    assert chart["bazi"] == "甲辰 丙寅 甲辰 庚午"
    assert chart["lunar_date"] == "2024年正月初一"
    assert chart["xunkong"] == "寅卯"
    assert chart["previous_solar_term"]["name"] == "立春"
    assert chart["next_solar_term"]["name"] == "雨水"
    assert chart["calendar_facts"] == {
        "gregorian": "2024-02-10T12:00:00+08:00",
        "month_command": "寅",
        "day_pillar": "甲辰",
        "day_branch": "辰",
        "month_clash": "申",
        "month_combine": "亥",
        "day_clash": "戌",
        "day_combine": "酉",
        "six_spirit_start": "青龙",
        "six_spirits": ["青龙", "朱雀", "勾陈", "腾蛇", "白虎", "玄武"],
    }


def test_professional_pillar_facts_and_relationships_match_known_chart() -> None:
    chart = build_metaphysics_chart(datetime(2004, 6, 26, 4), timezone_name="Asia/Shanghai")

    assert chart["bazi"] == "甲申 庚午 丙子 庚寅"
    assert [pillar["xunkong"] for pillar in chart["pillars"]] == ["午未", "戌亥", "申酉", "午未"]
    assert [pillar["di_shi"] for pillar in chart["pillars"]] == ["病", "帝旺", "胎", "长生"]
    assert [pillar["self_seat"] for pillar in chart["pillars"]] == ["绝", "沐浴", "胎", "绝"]
    assert chart["stem_relations"] == ["甲庚冲", "丙庚克"]
    assert "申子半合水" in chart["branch_relations"]
    assert "寅午半合火" in chart["branch_relations"]
    assert "子午相冲" in chart["branch_relations"]
    assert "寅申相冲" in chart["branch_relations"]
    assert chart["element_season_status"] == {"火": "旺", "土": "相", "木": "休", "水": "囚", "金": "死"}


def test_late_zi_hour_day_boundary_is_explicit() -> None:
    timestamp = datetime(2024, 1, 1, 23, 30)

    current_day = build_metaphysics_chart(timestamp, day_boundary="current")
    forward_day = build_metaphysics_chart(timestamp, day_boundary="forward")

    assert current_day["pillars"][2]["text"] == "甲子"
    assert forward_day["pillars"][2]["text"] == "乙丑"
    assert current_day["pillars"][3]["branch"] == "子"
    assert forward_day["pillars"][3]["branch"] == "子"


def test_true_solar_time_and_invalid_timezone() -> None:
    standard = build_metaphysics_chart(datetime(2026, 7, 12, 10, 30), longitude=121.4737)
    solar = build_metaphysics_chart(
        datetime(2026, 7, 12, 10, 30),
        longitude=121.4737,
        use_true_solar_time=True,
    )

    assert standard["calculation_mode"] == "standard_time"
    assert standard["true_solar_correction_minutes"] == 0
    assert solar["calculation_mode"] == "true_solar"
    assert solar["true_solar_correction_minutes"] != 0
    with pytest.raises(ValueError, match="未知时区"):
        build_metaphysics_chart(datetime(2026, 7, 12, 10, 30), timezone_name="Mars/Olympus")


def test_lunar_input_converts_with_historical_timezone_and_crosschecks_engines() -> None:
    chart = build_metaphysics_chart(
        datetime(1986, 4, 21, 0, 0),
        timezone_name="Asia/Shanghai",
        calendar_type="lunar",
        lunar_year=1986,
        lunar_month=4,
        lunar_day=21,
        lunar_hour=0,
        lunar_minute=0,
        gender="male",
    )

    assert chart["birth_profile"]["converted_solar_date"] == "1986-05-29T00:00:00+09:00"
    assert chart["bazi"] == "丙寅 癸巳 癸酉 壬子"
    assert chart["birth_profile"]["dayun"]["status"] == "available"
    assert chart["birth_profile"]["dayun"]["crosscheck_matches"] is True
    assert len(chart["birth_profile"]["dayun"]["cycles"]) == 9


def test_unknown_hour_exposes_candidates_and_withholds_dayun_precision() -> None:
    chart = build_metaphysics_chart(
        datetime(1990, 1, 1, 12, 0),
        gender="female",
        hour_uncertain=True,
    )

    assert chart["pillars"][3]["text"] == "待定"
    assert len(chart["birth_profile"]["hour_candidates"]) == 13
    assert chart["birth_profile"]["dayun"]["status"] == "requires_hour"
    assert chart["birth_profile"]["dayun"]["cycles"] == []
    assert sum(chart["element_counts"].values()) == 6


def test_invalid_lunar_input_is_rejected() -> None:
    with pytest.raises(ValueError, match="无效的农历日期"):
        build_metaphysics_chart(
            datetime(2024, 1, 1),
            calendar_type="lunar",
            lunar_year=2024,
            lunar_month=13,
            lunar_day=1,
        )
