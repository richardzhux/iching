"""The shared derivation core, and the 子时 school question it refuses to settle."""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from iching.core.calendar_engine import calculate_calendar_facts
from iching.core.ganzhi import (
    DAY_BOUNDARIES,
    both_schools,
    four_pillars,
    in_zi_hour,
    schools_disagree,
    zi_hour_notice,
)

SHANGHAI = ZoneInfo("Asia/Shanghai")


# --------------------------------------------------------------------------- #
# One derivation, shared
# --------------------------------------------------------------------------- #


def test_core_agrees_with_calendar_engine_across_both_schools():
    """calendar_engine delegates here; the two must never drift apart again."""
    random.seed(4)
    compared = 0
    for _ in range(1500):
        moment = datetime(
            random.randint(1950, 2030), random.randint(1, 12), random.randint(1, 28),
            random.randint(0, 23), random.randint(0, 59), tzinfo=SHANGHAI,
        )
        for boundary in DAY_BOUNDARIES:
            expected = calculate_calendar_facts(
                moment, timezone_name="Asia/Shanghai", day_boundary=boundary, crosscheck=False
            ).bazi
            assert four_pillars(moment, day_boundary=boundary).text == expected
            compared += 1
    assert compared == 3000


def test_naive_input_is_refused():
    """A naive datetime silently means 'whatever clock this process runs on'."""
    with pytest.raises(ValueError):
        four_pillars(datetime(2024, 6, 10, 14, 30))


def test_unknown_boundary_is_refused():
    with pytest.raises(ValueError):
        four_pillars(datetime(2024, 6, 10, 14, 30, tzinfo=SHANGHAI), day_boundary="whatever")


def test_offset_only_timezones_work():
    """A cast carries an offset, not an IANA name; that is enough to derive."""
    moment = datetime(2024, 6, 10, 14, 30, tzinfo=timezone(timedelta(hours=8)))
    assert four_pillars(moment).text == "甲辰 庚午 乙巳 癸未"


# --------------------------------------------------------------------------- #
# Solar terms resolve to the instant, not the day
# --------------------------------------------------------------------------- #


def test_month_follows_the_exact_solar_term_instant():
    """立春 1999 fell at 14:57:02; sxtwl's per-day getMonthGZ could not see that.

    The retired core/bazi.py answered 丙寅 for the whole of 1999-02-04, so a
    morning birth was filed under the wrong month and the wrong year.
    """
    before = four_pillars(datetime(1999, 2, 4, 7, 25, tzinfo=SHANGHAI))
    after = four_pillars(datetime(1999, 2, 4, 20, 25, tzinfo=SHANGHAI))

    assert before.month.text == "乙丑" and before.year.text == "戊寅"
    assert after.month.text == "丙寅" and after.year.text == "己卯"


def test_reference_instant_separates_labelling_from_term_placement():
    """True-solar correction moves the clock, not which side of a term you fall."""
    civil = datetime(1999, 2, 4, 15, 30, tzinfo=SHANGHAI)
    solar = datetime(1999, 2, 4, 14, 30, tzinfo=SHANGHAI)
    # Labelled by the solar clock, placed by the civil instant (after 立春).
    pillars = four_pillars(solar, reference_instant=civil)
    assert pillars.month.text == "丙寅"


# --------------------------------------------------------------------------- #
# 早子时 / 晚子时 — the product states the dispute, it does not settle it
# --------------------------------------------------------------------------- #


def test_the_schools_differ_only_across_the_late_zi_hour():
    for hour in (21, 22):
        assert not schools_disagree(datetime(2024, 6, 10, hour, 30, tzinfo=SHANGHAI))
    assert schools_disagree(datetime(2024, 6, 10, 23, 30, tzinfo=SHANGHAI))
    for hour in (0, 1, 2):
        assert not schools_disagree(datetime(2024, 6, 11, hour, 30, tzinfo=SHANGHAI))


def test_zi_hour_spans_both_halves_but_only_one_is_disputed():
    late = datetime(2024, 6, 10, 23, 30, tzinfo=SHANGHAI)
    early = datetime(2024, 6, 11, 0, 30, tzinfo=SHANGHAI)
    assert in_zi_hour(late) and in_zi_hour(early)
    assert schools_disagree(late)
    assert not schools_disagree(early)


def test_late_zi_pillars_match_each_named_school():
    """2024-06-10 is 乙巳日, 2024-06-11 is 丙午日."""
    charts = both_schools(datetime(2024, 6, 10, 23, 30, tzinfo=SHANGHAI))
    # 流派二: the day pillar stays, while the hour stem already follows the
    # incoming day's 五鼠遁 — 乙巳 paired with 戊子, which 五鼠遁 never produces.
    assert charts["current"].day.text == "乙巳"
    assert charts["current"].hour.text == "戊子"
    # 流派一 resolves that by advancing the day too.
    assert charts["forward"].day.text == "丙午"
    assert charts["forward"].hour.text == "戊子"


def test_notice_offers_a_choice_only_when_there_is_one():
    disputed = zi_hour_notice(datetime(2024, 6, 10, 23, 30, tzinfo=SHANGHAI))
    assert disputed is not None
    assert disputed["schools_disagree"] is True
    assert disputed["half"] == "晚子时"
    assert {option["day_pillar"] for option in disputed["options"]} == {"乙巳", "丙午"}

    agreed = zi_hour_notice(datetime(2024, 6, 11, 0, 30, tzinfo=SHANGHAI))
    assert agreed is not None
    assert agreed["schools_disagree"] is False
    assert len({option["bazi"] for option in agreed["options"]}) == 1

    assert zi_hour_notice(datetime(2024, 6, 10, 14, 30, tzinfo=SHANGHAI)) is None


def test_notice_uses_the_calibrated_clock_not_the_civil_one():
    """A civil 23:50 that corrects to 22:59 is not in the disputed window."""
    civil = datetime(1990, 5, 12, 23, 50, tzinfo=SHANGHAI)
    solar = datetime(1990, 5, 12, 22, 59, tzinfo=SHANGHAI)
    assert zi_hour_notice(civil) is not None
    assert zi_hour_notice(solar, reference_instant=civil) is None


# --------------------------------------------------------------------------- #
# The retired engine stays retired
# --------------------------------------------------------------------------- #


def test_the_second_bazi_engine_is_gone():
    """core/bazi.py answered the same question with day-granularity terms."""
    import importlib

    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("iching.core.bazi")


def test_nothing_imports_the_retired_engine():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    needle = "from iching.core." + "bazi import"
    offenders = [
        path.relative_to(root).as_posix()
        for folder in ("src", "tools", "tests")
        for path in (root / folder).rglob("*.py")
        if path != Path(__file__) and needle in path.read_text(encoding="utf-8")
    ]
    assert not offenders, offenders
