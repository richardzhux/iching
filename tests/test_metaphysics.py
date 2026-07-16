from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest
import sxtwl

from iching.core.metaphysics import (
    JIE_QI_NAMES,
    _branch_relations,
    _jieqi_datetime,
    _stem_relations,
    build_metaphysics_chart,
)
from iching.core.calendar_engine import normalize_local_datetime


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


def test_year_and_month_pillars_change_at_exact_lichun_instant() -> None:
    before = build_metaphysics_chart(
        datetime(2024, 2, 4, 10, 0),
        timezone_name="Asia/Shanghai",
    )
    after = build_metaphysics_chart(
        datetime(2024, 2, 4, 17, 0),
        timezone_name="Asia/Shanghai",
    )

    assert before["bazi"].startswith("癸卯 乙丑")
    assert after["bazi"].startswith("甲辰 丙寅")


def test_solar_term_is_one_instant_across_timezones() -> None:
    lichun = next(
        item for item in sxtwl.getJieQiByYear(2024)
        if JIE_QI_NAMES[int(item.jqIndex)] == "立春"
    )

    shanghai = _jieqi_datetime(lichun, ZoneInfo("Asia/Shanghai"))
    new_york = _jieqi_datetime(lichun, ZoneInfo("America/New_York"))

    assert shanghai.astimezone(timezone.utc) == new_york.astimezone(timezone.utc)
    assert (shanghai.hour, shanghai.minute) == (16, 26)
    assert (new_york.hour, new_york.minute) == (3, 26)


def test_dst_gap_is_rejected_and_repeated_time_requires_a_choice() -> None:
    with pytest.raises(ValueError, match="并不存在"):
        normalize_local_datetime(
            datetime(2024, 3, 10, 2, 30),
            "America/New_York",
        )
    with pytest.raises(ValueError, match="出现了两次"):
        normalize_local_datetime(
            datetime(2024, 11, 3, 1, 30),
            "America/New_York",
        )

    first = normalize_local_datetime(
        datetime(2024, 11, 3, 1, 30),
        "America/New_York",
        fold_choice="first",
    )
    second = normalize_local_datetime(
        datetime(2024, 11, 3, 1, 30),
        "America/New_York",
        fold_choice="second",
    )

    assert (second.civil_instant_utc - first.civil_instant_utc).total_seconds() == 3600


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


def test_each_theme_counts_all_matching_shensha_as_one_evidence_family() -> None:
    chart = build_metaphysics_chart(
        datetime(2004, 6, 26, 4),
        timezone_name="Asia/Shanghai",
        gender="male",
    )

    for profile in chart["theme_profiles"]:
        shensha_evidence = [item for item in profile["evidence"] if item["family"] == "神煞"]
        assert len(shensha_evidence) == 1
        assert "、" in shensha_evidence[0]["detail"]


def test_consumer_synthesis_is_traceable_and_uses_consumer_theme_names() -> None:
    chart = build_metaphysics_chart(
        datetime(2004, 6, 26, 4),
        timezone_name="Asia/Shanghai",
        gender="male",
    )

    assert [item["theme"] for item in chart["theme_profiles"]] == [
        "事业", "财富", "感情", "五行与承压结构",
    ]
    evidence_ids = {
        item["id"]
        for profile in chart["theme_profiles"]
        for item in profile["evidence"]
    }
    conclusions = chart["synthesis"]["conclusions"]
    assert 4 <= len(conclusions) <= 7
    assert all(item["headline"] and item["body"] for item in conclusions)
    assert all(set(item["supporting_evidence_ids"]) <= evidence_ids for item in conclusions)


def test_heavenly_stem_combinations_take_precedence_over_element_control() -> None:
    assert _stem_relations([{"stem": "甲"}, {"stem": "己"}]) == ["甲己合土"]
    assert _stem_relations([{"stem": "己"}, {"stem": "甲"}]) == ["甲己合土"]
    assert _stem_relations([{"stem": "丙"}, {"stem": "辛"}]) == ["丙辛合水"]


def test_branch_relations_include_six_combinations_and_bully_punishment() -> None:
    relations = _branch_relations([{"branch": branch} for branch in ("子", "丑", "未", "戌")])

    assert "子丑六合土" in relations
    assert "丑未相刑" in relations
    assert "丑戌相刑" in relations
    assert "未戌相刑" in relations


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
    assert len(chart["birth_profile"]["dayun"]["cycles"]) == 13


def test_current_dayun_changes_at_the_exact_start_instant() -> None:
    before = build_metaphysics_chart(
        datetime(2004, 6, 26, 4),
        timezone_name="Asia/Shanghai",
        gender="male",
        reference_timestamp=datetime(2018, 2, 17, 17, 59),
    )
    after = build_metaphysics_chart(
        datetime(2004, 6, 26, 4),
        timezone_name="Asia/Shanghai",
        gender="male",
        reference_timestamp=datetime(2018, 2, 17, 18, 1),
    )

    before_current = next(item for item in before["period_layers"]["dayun"] if item["is_current"])
    after_current = next(item for item in after["period_layers"]["dayun"] if item["is_current"])
    assert before_current["index"] == 1
    assert after_current["index"] == 2


def test_compact_periods_cover_an_older_users_current_and_next_dayun() -> None:
    chart = build_metaphysics_chart(
        datetime(1905, 1, 1, 4),
        timezone_name="Asia/Shanghai",
        gender="male",
        reference_timestamp=datetime(2026, 7, 16, 12),
        include_period_details=False,
    )

    visible_cycles = chart["period_layers"]["dayun"]
    assert len(chart["birth_profile"]["dayun"]["cycles"]) >= 15
    assert len(visible_cycles) >= 15
    current_cycle = next(item for item in visible_cycles if item["is_current"])
    assert current_cycle["index"] >= 12
    assert any(item["index"] == current_cycle["index"] + 1 for item in visible_cycles)

    life_kline = chart["consumer"]["life_kline"]
    assert all(len(series["points"]) == 20 for series in life_kline["series"])
    assert len(life_kline["stages"]) == 3


def test_current_flow_year_changes_at_lichun_not_midnight() -> None:
    before = build_metaphysics_chart(
        datetime(1990, 8, 4, 1),
        timezone_name="Asia/Shanghai",
        gender="male",
        reference_timestamp=datetime(2024, 2, 4, 10),
    )
    after = build_metaphysics_chart(
        datetime(1990, 8, 4, 1),
        timezone_name="Asia/Shanghai",
        gender="male",
        reference_timestamp=datetime(2024, 2, 4, 17),
    )

    assert before["period_layers"]["current"]["year"]["year"] == 2023
    assert after["period_layers"]["current"]["year"]["year"] == 2024


def test_unknown_hour_returns_only_stable_results() -> None:
    chart = build_metaphysics_chart(
        datetime(1990, 1, 1, 12, 0),
        gender="female",
        hour_uncertain=True,
    )

    assert chart["calculation_quality"]["status"] == "uncertain"
    assert chart["birth_profile"]["hour_uncertain"] is True
    assert chart["birth_profile"]["stability"]["candidate_count"] == 13
    assert chart["birth_profile"]["dayun"]["status"] == "requires_hour"
    assert chart["period_layers"]["dayun"] == []


def test_invalid_lunar_input_is_rejected() -> None:
    with pytest.raises(ValueError, match="无效的农历日期"):
        build_metaphysics_chart(
            datetime(2024, 1, 1),
            calendar_type="lunar",
            lunar_year=2024,
            lunar_month=13,
            lunar_day=1,
        )
