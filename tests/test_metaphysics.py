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
    comparison_labels_by_theme = {
        profile["theme"]: {
            comparison.get("display_label")
            for comparison in profile.get("comparisons", [])
            if comparison.get("display_label")
        }
        for profile in chart["theme_profiles"]
    }
    assert all(
        item.get("distribution_context")
        in comparison_labels_by_theme.get(item["theme"], set())
        for item in conclusions
        if item.get("distribution_context")
    )
    assert all(
        "同值样本" not in item.get("distribution_context", "")
        for item in conclusions
    )


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
    assert current_day["lunar_date"] == forward_day["lunar_date"] == "2023年冬月二十"


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
    for chart, current_cycle in ((before, before_current), (after, after_current)):
        assert chart["period_layers"]["current"]["year"]["year"] == 2018
        assert chart["period_layers"]["current"]["month"]["ganzhi"] == "甲寅"
        assert next(year for year in current_cycle["years"] if year["is_current"])["year"] == 2018
        for series in chart["consumer"]["life_kline"]["series"]:
            years = [point["year"] for point in series["points"]]
            assert len(years) == len(set(years))


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


def test_true_solar_clock_removes_dst_but_keeps_physical_term_boundary() -> None:
    from zoneinfo import ZoneInfo
    from datetime import timedelta, timezone
    from iching.core.metaphysics import _true_solar_time
    from iching.core.calendar_engine import calculate_calendar_facts, solar_terms_for_years

    civil = datetime(2026, 7, 1, 13, 30, tzinfo=ZoneInfo("America/Los_Angeles"))
    solar, correction = _true_solar_time(civil, -118.24)
    standard = civil.astimezone(timezone(timedelta(hours=-8)))
    solar_standard, _ = _true_solar_time(standard, -118.24)
    assert solar.replace(tzinfo=None) == solar_standard.replace(tzinfo=None)
    assert -65 < correction < -50
    zone = ZoneInfo("Asia/Shanghai")
    term = next(t for t in solar_terms_for_years([2024], zone) if t.index == 3 and t.local_datetime.year == 2024)
    instant = term.local_datetime + timedelta(seconds=1)
    shifted, _ = _true_solar_time(instant, 75)
    factual = calculate_calendar_facts(instant, timezone_name="Asia/Shanghai", day_boundary="forward", crosscheck=False)
    corrected = calculate_calendar_facts(shifted, timezone_name="Asia/Shanghai", day_boundary="forward", reference_instant=instant)
    assert (corrected.year_gz, corrected.month_gz) == (factual.year_gz, factual.month_gz)
    assert shifted < term.local_datetime


def test_selected_period_reuses_facts_but_refreshes_current_month(monkeypatch) -> None:
    import iching.core.metaphysics as metaphysics
    from collections import OrderedDict

    monkeypatch.setattr(metaphysics, "_period_cache", OrderedDict())
    monkeypatch.setattr(metaphysics, "_period_cache_bytes", 0)
    compute = metaphysics._compute_dayun_cycle
    computed_cycles = []

    def track_cycle(cycle, **kwargs):
        computed_cycles.append(cycle.getIndex())
        return compute(cycle, **kwargs)

    def unexpected_analysis(*args, **kwargs):
        pytest.fail(
            "A selected period must not rebuild natal analysis or the lifetime K-line"
        )

    monkeypatch.setattr(metaphysics, "_compute_dayun_cycle", track_cycle)
    monkeypatch.setattr(metaphysics, "build_bazi_consumer_profile", unexpected_analysis)
    monkeypatch.setattr(metaphysics, "_statistics_or_unavailable", unexpected_analysis)
    options = {"gender": "male", "cycle_index": 2}
    first = metaphysics.build_metaphysics_period(
        datetime(2004, 6, 26, 4),
        reference_timestamp=datetime(2026, 2, 10, 12),
        **options,
    )["cycle"]
    first_month = next(
        month["ganzhi"]
        for year in first["years"]
        for month in year["months"]
        if month["is_current"]
    )
    # A response consumer can mutate any level without corrupting cached facts.
    first["years"][0]["months"].clear()
    second = metaphysics.build_metaphysics_period(
        datetime(2004, 6, 26, 4),
        reference_timestamp=datetime(2026, 3, 10, 12),
        **options,
    )["cycle"]
    second_month = next(
        month["ganzhi"]
        for year in second["years"]
        for month in year["months"]
        if month["is_current"]
    )
    assert computed_cycles == [2]
    assert second["years"][0]["months"]
    assert first_month != second_month
    versions = metaphysics.bazi_rule_versions()
    monkeypatch.setattr(
        metaphysics, "bazi_rule_versions", lambda: {**versions, "consumer": "changed"}
    )
    metaphysics.build_metaphysics_period(
        datetime(2004, 6, 26, 4),
        reference_timestamp=datetime(2026, 3, 10, 12),
        **options,
    )
    assert computed_cycles == [2, 2]


def test_unknown_hour_does_not_calculate_discarded_periods_or_consumer(
    monkeypatch,
) -> None:
    import iching.core.metaphysics as metaphysics

    def unexpected_work(*args, **kwargs):
        pytest.fail(
            "Unknown-hour analysis must not compute discarded exact periods or consumer data"
        )

    monkeypatch.setattr(metaphysics, "_dayun_payload", unexpected_work)
    monkeypatch.setattr(metaphysics, "build_bazi_consumer_profile", unexpected_work)
    chart = metaphysics.build_metaphysics_chart(
        datetime(1990, 1, 1, 12),
        gender="female",
        hour_uncertain=True,
    )
    assert chart["birth_profile"]["stability"]["candidate_count"] == 13
    assert chart["birth_profile"]["dayun"]["status"] == "requires_hour"


def test_solar_term_cache_reuses_years_across_windows_and_timezones(
    monkeypatch,
) -> None:
    import iching.core.calendar_engine as calendar

    calendar._solar_terms_cached.cache_clear()
    original = calendar.sxtwl.getJieQiByYear
    computed_years = []

    def track_year(year):
        computed_years.append(year)
        return original(year)

    monkeypatch.setattr(calendar.sxtwl, "getJieQiByYear", track_year)
    first = calendar.solar_terms_for_years(range(2023, 2027), ZoneInfo("Asia/Shanghai"))
    calendar.solar_terms_for_years(range(2024, 2028), ZoneInfo("America/Los_Angeles"))
    utc = calendar.solar_terms_for_years(range(2023, 2027), timezone.utc)
    assert computed_years == [2023, 2024, 2025, 2026, 2027]
    assert [(term.index, term.instant_utc) for term in first] == [
        (term.index, term.instant_utc) for term in utc
    ]
    assert all(term.local_datetime.utcoffset().total_seconds() == 0 for term in utc)


# --------------------------------------------------------------------------- #
# Period expansion: arithmetic instead of re-deriving the calendar per month
# --------------------------------------------------------------------------- #


def test_xun_kong_matches_the_library_for_every_ganzhi():
    """旬空 is fixed by position in the sexagenary cycle, so compute it."""
    from lunar_python.util import LunarUtil

    from iching.core.metaphysics import BRANCHES, STEMS, _xun_kong

    for index in range(60):
        ganzhi = STEMS[index % 10] + BRANCHES[index % 12]
        assert _xun_kong(ganzhi) == LunarUtil.getXunKong(ganzhi), ganzhi


def test_xun_kong_is_safe_on_junk_input():
    from iching.core.metaphysics import _xun_kong

    assert _xun_kong("") == ""
    assert _xun_kong("x") == ""
    assert _xun_kong("??") == ""


def test_liu_yue_ganzhi_follows_wu_hu_dun():
    """流月 stem comes from the 流年 stem by 五虎遁; index 0 is 寅月."""
    from iching.core.metaphysics import _liu_yue_ganzhi

    # 甲/己 year starts at 丙寅.
    assert _liu_yue_ganzhi("甲子", 0) == "丙寅"
    assert _liu_yue_ganzhi("己巳", 0) == "丙寅"
    # 乙/庚 starts at 戊寅, 丙/辛 at 庚寅, 丁/壬 at 壬寅, 戊/癸 at 甲寅.
    assert _liu_yue_ganzhi("乙丑", 0) == "戊寅"
    assert _liu_yue_ganzhi("丙寅", 0) == "庚寅"
    assert _liu_yue_ganzhi("丁卯", 0) == "壬寅"
    assert _liu_yue_ganzhi("戊辰", 0) == "甲寅"
    # The branch advances with the index and wraps at 子.
    assert _liu_yue_ganzhi("甲子", 11) == "丁丑"
    assert _liu_yue_ganzhi("", 0) == ""


def test_month_expansion_matches_the_library_across_a_full_chart():
    """The arithmetic path must reproduce lunar_python exactly, not approximately."""
    from datetime import datetime
    from zoneinfo import ZoneInfo

    import iching.core.metaphysics as metaphysics

    zone = ZoneInfo("Asia/Shanghai")
    moment = datetime(1990, 5, 12, 14, 30, tzinfo=zone)

    def cycles(chart):
        dayun = chart["period_layers"]["dayun"]
        return dayun["cycles"] if isinstance(dayun, dict) else dayun

    def build():
        metaphysics._period_cache.clear()
        metaphysics._period_cache_bytes = 0
        return metaphysics.build_metaphysics_chart(
            moment, timezone_name="Asia/Shanghai", gender="male"
        )

    fast = build()
    original = metaphysics._liu_yue_ganzhi
    try:
        # Empty string makes the caller fall back to liu_yue.getGanZhi().
        metaphysics._liu_yue_ganzhi = lambda year_ganzhi, index: ""
        library = build()
    finally:
        metaphysics._liu_yue_ganzhi = original

    compared = 0
    for fast_cycle, library_cycle in zip(cycles(fast), cycles(library)):
        for fast_year, library_year in zip(
            fast_cycle.get("years", []), library_cycle.get("years", [])
        ):
            for fast_month, library_month in zip(
                fast_year.get("months", []), library_year.get("months", [])
            ):
                assert fast_month["ganzhi"] == library_month["ganzhi"]
                compared += 1

    assert compared > 500, f"only compared {compared} months"


# --------------------------------------------------------------------------- #
# Synthesis: conclusions must vary with the chart
# --------------------------------------------------------------------------- #


def _sample_profiles(count: int = 300):
    import random
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from iching.core.bazi_structure import build_structure_profile
    from iching.core.calendar_engine import STEMS as CAL_STEMS
    from iching.core.calendar_engine import calculate_calendar_facts
    from iching.core.metaphysics import _pillar, _seasonal_status
    from iching.core.shensha import evaluate_shensha

    random.seed(17)
    zone = ZoneInfo("Asia/Shanghai")
    profiles = []
    for _ in range(count):
        moment = datetime(
            random.randint(1955, 2012),
            random.randint(1, 12),
            random.randint(1, 28),
            random.randint(0, 23),
            random.randint(0, 59),
            tzinfo=zone,
        )
        try:
            facts = calculate_calendar_facts(
                moment, timezone_name="Asia/Shanghai", day_boundary="forward", crosscheck=False
            )
        except Exception:
            continue
        day_stem = CAL_STEMS[facts.day_gz.tg]
        pillars = [
            _pillar("年", facts.year_gz, day_stem),
            _pillar("月", facts.month_gz, day_stem),
            _pillar("日", facts.day_gz, day_stem),
            _pillar("时", facts.hour_gz, day_stem),
        ]
        profiles.append(
            build_structure_profile(
                pillars,
                gender=random.choice(["male", "female"]),
                shensha_hits=evaluate_shensha(pillars),
                seasonal_status=_seasonal_status(pillars[1]["branch"]),
            )
        )
    return profiles


def test_no_single_conclusion_dominates_the_population():
    """Measured over 2,000 charts the old synthesis gave five of six themes the
    same headline for 90-100% of readers, because it branched on whether a
    ten-god appeared anywhere across sixteen slots. A conclusion that fits
    nearly everyone describes nobody."""
    from collections import Counter, defaultdict

    profiles = _sample_profiles()
    assert len(profiles) > 250

    per_theme = defaultdict(Counter)
    for profile in profiles:
        for conclusion in profile["synthesis"]["conclusions"]:
            per_theme[conclusion["theme"]][conclusion["headline"]] += 1

    total = len(profiles)
    for theme, counter in per_theme.items():
        top_share = counter.most_common(1)[0][1] / total
        assert top_share < 0.45, (
            f"{theme}: one headline covers {top_share:.0%} of charts "
            f"({counter.most_common(1)[0][0]})"
        )
        assert len(counter) >= 3, f"{theme} only ever produces {len(counter)} headlines"


def test_day_master_bands_actually_separate():
    """At the first-guess cutoffs 53% of charts read 偏强, which is not a band."""
    from collections import Counter

    profiles = _sample_profiles()
    bands = Counter(p["synthesis"]["strength"]["band"] for p in profiles)
    total = sum(bands.values())
    for band in ("偏强", "中和", "偏弱"):
        share = bands[band] / total
        assert 0.2 < share < 0.5, f"{band} covers {share:.0%} of charts"


def test_conclusions_quote_the_numbers_they_rest_on():
    profiles = _sample_profiles(40)
    for profile in profiles:
        for conclusion in profile["synthesis"]["conclusions"]:
            if conclusion["id"].endswith("overall.strength"):
                continue
            body = conclusion["body"]
            if conclusion["lead_metric"]:
                assert "标准差" in body, body
                assert "常见约" in body, body
