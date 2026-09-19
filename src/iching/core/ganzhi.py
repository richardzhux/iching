"""Instant → four pillars. The one derivation the whole product shares.

There used to be two implementations of this. `core/bazi.py` (Nov 2025)
answered "what is the BaZi of now?" and took a bare datetime; `calendar_engine`
(Jul 2026) answered "what is the BaZi of a birth someone reports to me?" and
grew timezone normalisation, DST-fold resolution, true-solar correction, lunar
input and an uncertain-hour mode.

Only one of those jobs differs between the two callers. Turning testimony into
an instant is birth-chart work. Turning an instant into four pillars is the
same arithmetic either way. Fusing the two layers meant the reading path could
not reuse the careful engine, so it kept its own copy — and that copy called
``sxtwl.getMonthGZ()``, which takes no hour argument and therefore cannot
represent a solar term that falls mid-day. Every month and year disagreement
between the two engines traced back to that.

So: resolution lives above this module, derivation lives here, and the 换日
rule is always an explicit argument. Nothing infers a school from whichever
library function happened to be at hand.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Literal, Tuple

import sxtwl

from iching.core.calendar_engine import (
    JIE_MONTH_BRANCH,
    UTC,
    GanZhiIndex,
    SolarTermInstant,
    solar_terms_for_years,
)

STEMS = ("甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸")
BRANCHES = ("子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥")

DayBoundary = Literal["current", "forward"]
DAY_BOUNDARIES: Tuple[str, ...] = ("current", "forward")

#: The two schools disagree only across 23:00–23:59. 子時 runs 23:00–01:00, and
#: both agree that 00:00–01:00 (早子時) belongs to the new day; the dispute is
#: whether 23:00–24:00 (晚子時) does too. `forward` advances the day pillar,
#: `current` leaves it on the calendar day while the hour stem still comes from
#: the incoming day's 五鼠遁 — which is why `current` can pair 乙巳日 with 戊子時,
#: a combination 五鼠遁 does not produce. That inconsistency is precisely what
#: the schools argue about, so this module refuses to pick one for the caller.
ZI_HOUR_START = 23
ZI_HOUR_END = 1

#: The product's single 换日 default, named here so no surface inherits one
#: from whichever library call it happened to reach for. `current` keeps every
#: existing reading byte-identical, and outside 23:00–23:59 the two schools
#: agree anyway — so this only picks which option is pre-selected inside the
#: disputed window, where both are shown regardless.
DEFAULT_DAY_BOUNDARY: DayBoundary = "current"

FIVE_ELEMENTS: Dict[str, str] = {
    "甲": "阳木", "乙": "阴木", "丙": "阳火", "丁": "阴火", "戊": "阳土",
    "己": "阴土", "庚": "阳金", "辛": "阴金", "壬": "阳水", "癸": "阴水",
    "子": "阳水", "丑": "阴土", "寅": "阳木", "卯": "阴木", "辰": "阳土",
    "巳": "阴火", "午": "阳火", "未": "阴土", "申": "阳金", "酉": "阴金",
    "戌": "阳土", "亥": "阴水",
}

PILLAR_LABELS = ("年", "月", "日", "时")


@dataclass(frozen=True, slots=True)
class FourPillars:
    """The four pillars of one instant under one 换日 rule."""

    year: GanZhiIndex
    month: GanZhiIndex
    day: GanZhiIndex
    hour: GanZhiIndex
    day_boundary: str
    #: The solar terms bracketing this instant, for callers that show context.
    previous_term: SolarTermInstant
    next_term: SolarTermInstant
    lichun_boundary: SolarTermInstant

    @property
    def pillars(self) -> Tuple[GanZhiIndex, GanZhiIndex, GanZhiIndex, GanZhiIndex]:
        return (self.year, self.month, self.day, self.hour)

    @property
    def text(self) -> str:
        """Space separated, as the chart tool prints it: 甲辰 庚午 乙巳 丁亥."""
        return " ".join(item.text for item in self.pillars)

    @property
    def labelled_text(self) -> str:
        """Labelled, as the reading prints it: 甲辰年 庚午月 乙巳日 丁亥时."""
        return " ".join(
            f"{item.text}{label}" for item, label in zip(self.pillars, PILLAR_LABELS)
        )

    @property
    def day_stem(self) -> str:
        return STEMS[self.day.tg]

    @property
    def components(self) -> Dict[str, str]:
        """Flat stem/branch map, the shape the Najia layer reads."""
        keys = ("year", "month", "day", "hour")
        result: Dict[str, str] = {}
        for key, item in zip(keys, self.pillars):
            result[f"{key}_stem"] = STEMS[item.tg]
            result[f"{key}_branch"] = BRANCHES[item.dz]
        return result

    @property
    def detail(self) -> List[Dict[str, Any]]:
        """Per-pillar polarity and element, the shape the UI's BaziPillar reads."""
        detail: List[Dict[str, Any]] = []
        for label, item in zip(PILLAR_LABELS, self.pillars):
            stem = STEMS[item.tg]
            branch = BRANCHES[item.dz]
            detail.append(
                {
                    "label": label,
                    "stem": _describe(stem),
                    "branch": _describe(branch),
                }
            )
        return detail

    @property
    def elements_text(self) -> str:
        return " ".join(
            f"{pillar['stem']['element'] or pillar['stem']['value']}"
            f"{pillar['branch']['element'] or pillar['branch']['value']}"
            f"{pillar['label']}"
            for pillar in self.detail
        )


def _describe(symbol: str) -> Dict[str, str]:
    descriptor = FIVE_ELEMENTS.get(symbol, "")
    return {
        "value": symbol,
        "polarity": descriptor[0] if descriptor else "",
        "element": descriptor[1:] if len(descriptor) > 1 else "",
    }


def _year_ganzhi(year: int) -> GanZhiIndex:
    return GanZhiIndex((year - 4) % 10, (year - 4) % 12)


def _month_ganzhi(year_stem_index: int, month_branch: str) -> GanZhiIndex:
    month_offset = (BRANCHES.index(month_branch) - BRANCHES.index("寅")) % 12
    yin_month_stem = ((year_stem_index % 5) * 2 + 2) % 10
    return GanZhiIndex((yin_month_stem + month_offset) % 10, BRANCHES.index(month_branch))


def _sxtwl_gz(value: Any) -> GanZhiIndex:
    return GanZhiIndex(int(value.tg), int(value.dz))


def in_zi_hour(value: datetime) -> bool:
    """Is this instant inside 子時 (23:00–01:00)?"""
    return value.hour >= ZI_HOUR_START or value.hour < ZI_HOUR_END


def schools_disagree(value: datetime) -> bool:
    """Do 早子/晚子 actually produce different pillars for this instant?

    True only across 23:00–23:59. Both schools place 00:00–01:00 on the new
    day, so a reader whose time lands there should be told the question does
    not arise rather than be asked to choose.
    """
    return value.hour == ZI_HOUR_START


def four_pillars(
    value: datetime,
    *,
    day_boundary: DayBoundary = "current",
    reference_instant: datetime | None = None,
) -> FourPillars:
    """Derive the four pillars of a resolved instant.

    ``value`` must be timezone aware: resolving what instant a person meant is
    the caller's job, and a naive datetime silently means "whatever clock this
    process happens to run on".

    ``reference_instant`` lets a true-solar-corrected clock label the pillars
    while the physical instant still decides which side of a solar term the
    birth falls on.
    """
    if value.tzinfo is None:
        raise ValueError("干支推导只接受带时区的时间；先在上层解析出确定的时刻。")
    if day_boundary not in DAY_BOUNDARIES:
        raise ValueError(f"未知换日规则: {day_boundary}")

    terms = solar_terms_for_years(range(value.year - 2, value.year + 3), value.tzinfo)
    instant = (reference_instant or value).astimezone(UTC)

    previous = next(item for item in reversed(terms) if item.instant_utc <= instant)
    following = next(item for item in terms if item.instant_utc > instant)
    previous_lichun = next(
        item for item in reversed(terms) if item.index == 3 and item.instant_utc <= instant
    )
    previous_jie = next(
        item
        for item in reversed(terms)
        if item.index in JIE_MONTH_BRANCH and item.instant_utc <= instant
    )

    # Year and month come from the exact solar-term instant, never from a
    # whole-day lookup: 立春 1999 fell at 14:57:02, so a birth that morning
    # belongs to the previous year and month.
    year_gz = _year_ganzhi(previous_lichun.local_datetime.year)
    month_gz = _month_ganzhi(year_gz.tg, JIE_MONTH_BRANCH[previous_jie.index])

    advance = day_boundary == "forward" and value.hour >= ZI_HOUR_START
    pillar_date = value + timedelta(days=1) if advance else value
    solar_day = sxtwl.fromSolar(pillar_date.year, pillar_date.month, pillar_date.day)
    day_gz = _sxtwl_gz(solar_day.getDayGZ())
    hour_gz = _sxtwl_gz(solar_day.getHourGZ(0 if advance else value.hour))

    return FourPillars(
        year=year_gz,
        month=month_gz,
        day=day_gz,
        hour=hour_gz,
        day_boundary=day_boundary,
        previous_term=previous,
        next_term=following,
        lichun_boundary=previous_lichun,
    )


def both_schools(
    value: datetime, *, reference_instant: datetime | None = None
) -> Dict[str, FourPillars]:
    """Both readings of an instant, for a time inside the disputed window."""
    return {
        boundary: four_pillars(
            value, day_boundary=boundary, reference_instant=reference_instant
        )
        for boundary in DAY_BOUNDARIES
    }


def zi_hour_notice(
    value: datetime, *, reference_instant: datetime | None = None
) -> Dict[str, Any] | None:
    """Describe the 子時 situation, or None when the instant is not in it.

    The product does not pick a school here. Inside 23:00–23:59 it reports both
    readings and leaves the choice with the reader; inside 00:00–01:00 it says
    the schools agree, which is a real answer rather than a deferral.
    """
    if not in_zi_hour(value):
        return None
    charts = both_schools(value, reference_instant=reference_instant)
    disputed = schools_disagree(value)
    return {
        "in_zi_hour": True,
        "half": "晚子时" if value.hour >= ZI_HOUR_START else "早子时",
        "schools_disagree": disputed,
        "options": [
            {
                "day_boundary": boundary,
                "label": "晚子时换日（流派一）" if boundary == "forward" else "晚子时不换日（流派二）",
                "bazi": chart.text,
                "day_pillar": chart.day.text,
                "hour_pillar": chart.hour.text,
                "day_stem": chart.day_stem,
            }
            for boundary, chart in charts.items()
        ],
        "note": (
            "出生时间落在晚子时（23:00–24:00），两派对日柱是否进位有分歧，"
            "两种排法都列在下面，请自行选择。"
            if disputed
            else "出生时间落在早子时（00:00–01:00），两派在此一致，日柱不受换日之争影响。"
        ),
    }
