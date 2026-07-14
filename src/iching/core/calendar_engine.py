from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone, tzinfo
from functools import lru_cache
from typing import Any, Iterable, Literal, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import sxtwl
from lunar_python import Solar as SolarCalendar


STEMS = ("甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸")
BRANCHES = ("子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥")
JIE_QI_NAMES = (
    "冬至", "小寒", "大寒", "立春", "雨水", "惊蛰", "春分", "清明", "谷雨", "立夏", "小满", "芒种",
    "夏至", "小暑", "大暑", "立秋", "处暑", "白露", "秋分", "寒露", "霜降", "立冬", "小雪", "大雪",
)
JIE_MONTH_BRANCH = {
    1: "丑",
    3: "寅",
    5: "卯",
    7: "辰",
    9: "巳",
    11: "午",
    13: "未",
    15: "申",
    17: "酉",
    19: "戌",
    21: "亥",
    23: "子",
}

# sxtwl 2.0.7's JD2DD values are China Standard Time clock values. They are
# not UTC and must not be relabelled as the destination timezone. A fixed +08
# source is intentional here: historical Asia/Shanghai DST must not be applied
# to the library's source clock representation.
SXTWL_SOURCE_TZ = timezone(timedelta(hours=8), name="sxtwl-cst")
UTC = timezone.utc
ENGINE_VERSION = "canonical-calendar-1"


class AmbiguousLocalTimeError(ValueError):
    pass


class NonexistentLocalTimeError(ValueError):
    pass


@dataclass(frozen=True)
class GanZhiIndex:
    tg: int
    dz: int

    @property
    def text(self) -> str:
        return f"{STEMS[self.tg]}{BRANCHES[self.dz]}"


@dataclass(frozen=True)
class NormalizedBirthTime:
    local_datetime: datetime
    timezone: str
    civil_instant_utc: datetime
    fold: int


@dataclass(frozen=True)
class SolarTermInstant:
    name: str
    index: int
    instant_utc: datetime
    local_datetime: datetime


@dataclass(frozen=True)
class CalendarFactSet:
    year_gz: GanZhiIndex
    month_gz: GanZhiIndex
    day_gz: GanZhiIndex
    hour_gz: GanZhiIndex
    previous_jie: SolarTermInstant
    next_jie: SolarTermInstant
    lichun_boundary: SolarTermInstant
    boundary_flags: dict[str, Any]
    quality: dict[str, Any]

    @property
    def bazi(self) -> str:
        return " ".join(item.text for item in (self.year_gz, self.month_gz, self.day_gz, self.hour_gz))


def timezone_for(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"未知时区: {name}") from exc


def _roundtrip_valid(naive: datetime, zone: ZoneInfo, fold: int) -> Optional[datetime]:
    aware = naive.replace(tzinfo=zone, fold=fold)
    roundtrip = aware.astimezone(UTC).astimezone(zone)
    if roundtrip.replace(tzinfo=None) != naive:
        return None
    return aware


def normalize_local_datetime(
    value: datetime,
    timezone_name: str,
    *,
    fold_choice: Optional[Literal["first", "second"]] = None,
) -> NormalizedBirthTime:
    zone = timezone_for(timezone_name)
    if value.tzinfo is not None:
        local = value.astimezone(zone)
        return NormalizedBirthTime(local, timezone_name, local.astimezone(UTC), int(local.fold))

    first = _roundtrip_valid(value, zone, 0)
    second = _roundtrip_valid(value, zone, 1)
    candidates = [item for item in (first, second) if item is not None]
    if not candidates:
        raise NonexistentLocalTimeError("这个当地时间因夏令时跳转并不存在，请选择前后相邻的有效时间。")

    unique_offsets = {item.utcoffset() for item in candidates}
    if len(unique_offsets) > 1:
        if fold_choice is None:
            raise AmbiguousLocalTimeError("这个当地时间出现了两次，请选择第一次或第二次出现的时间。")
        local = candidates[0] if fold_choice == "first" else candidates[-1]
    else:
        local = candidates[0]
    return NormalizedBirthTime(local, timezone_name, local.astimezone(UTC), int(local.fold))


def _dd_to_source_datetime(value: Any) -> datetime:
    base = datetime(int(value.Y), int(value.M), int(value.D), int(value.h), int(value.m), tzinfo=SXTWL_SOURCE_TZ)
    return base + timedelta(seconds=float(value.s))


def solar_term_datetime(item: Any, zone: tzinfo) -> datetime:
    source = _dd_to_source_datetime(sxtwl.JD2DD(item.jd))
    return source.astimezone(zone)


@lru_cache(maxsize=96)
def _solar_terms_cached(years: tuple[int, ...], timezone_name: str) -> tuple[SolarTermInstant, ...]:
    zone = timezone_for(timezone_name)
    result: list[SolarTermInstant] = []
    seen: set[tuple[int, datetime]] = set()
    for year in years:
        for item in sxtwl.getJieQiByYear(year):
            index = int(item.jqIndex)
            local = solar_term_datetime(item, zone)
            key = (index, local.astimezone(UTC))
            if key in seen:
                continue
            seen.add(key)
            result.append(SolarTermInstant(JIE_QI_NAMES[index], index, local.astimezone(UTC), local))
    return tuple(sorted(result, key=lambda item: item.instant_utc))


def solar_terms_for_years(years: Iterable[int], zone: tzinfo) -> list[SolarTermInstant]:
    timezone_name = getattr(zone, "key", None)
    if timezone_name:
        return list(_solar_terms_cached(tuple(years), str(timezone_name)))
    result: list[SolarTermInstant] = []
    seen: set[tuple[int, datetime]] = set()
    for year in years:
        for item in sxtwl.getJieQiByYear(year):
            index = int(item.jqIndex)
            local = solar_term_datetime(item, zone)
            key = (index, local.astimezone(UTC))
            if key in seen:
                continue
            seen.add(key)
            result.append(SolarTermInstant(JIE_QI_NAMES[index], index, local.astimezone(UTC), local))
    return sorted(result, key=lambda item: item.instant_utc)


def _year_ganzhi(year: int) -> GanZhiIndex:
    return GanZhiIndex((year - 4) % 10, (year - 4) % 12)


def _month_ganzhi(year_stem_index: int, month_branch: str) -> GanZhiIndex:
    month_offset = (BRANCHES.index(month_branch) - BRANCHES.index("寅")) % 12
    yin_month_stem = ((year_stem_index % 5) * 2 + 2) % 10
    return GanZhiIndex((yin_month_stem + month_offset) % 10, BRANCHES.index(month_branch))


def _sxtwl_gz(value: Any) -> GanZhiIndex:
    return GanZhiIndex(int(value.tg), int(value.dz))


def _crosscheck(
    value: datetime,
    *,
    timezone_name: str,
    day_boundary: str,
    expected: str,
) -> dict[str, Any]:
    # lunar-python uses a China civil clock and exposes no timezone contract.
    # Only compare when its inputs are semantically equivalent to the canonical
    # engine; all other cases remain valid canonical calculations.
    comparable = (
        timezone_name == "Asia/Shanghai"
        and value.utcoffset() == timedelta(hours=8)
        and day_boundary in {"current", "forward"}
    )
    if not comparable:
        return {
            "status": "verified_canonical",
            "label": "已校准",
            "crosscheck": "not_comparable",
        }
    solar = SolarCalendar.fromYmdHms(value.year, value.month, value.day, value.hour, value.minute, value.second)
    eight_char = solar.getLunar().getEightChar()
    eight_char.setSect(1 if day_boundary == "forward" else 2)
    actual = eight_char.toString()
    if actual == expected:
        return {
            "status": "verified",
            "label": "已校准",
            "crosscheck": "matched",
        }
    return {
        "status": "conflict",
        "label": "需要确认出生时间",
        "crosscheck": "mismatch",
        "canonical_bazi": expected,
        "secondary_bazi": actual,
    }


def calculate_calendar_facts(
    value: datetime,
    *,
    timezone_name: str,
    day_boundary: str,
    crosscheck: bool = True,
) -> CalendarFactSet:
    if value.tzinfo is None:
        raise ValueError("历法计算只接受已规范化的时区时间。")
    if day_boundary not in {"current", "forward"}:
        raise ValueError(f"未知换日规则: {day_boundary}")

    terms = solar_terms_for_years(range(value.year - 2, value.year + 3), value.tzinfo)
    instant = value.astimezone(UTC)
    previous = next(item for item in reversed(terms) if item.instant_utc <= instant)
    following = next(item for item in terms if item.instant_utc > instant)
    previous_lichun = next(
        item for item in reversed(terms)
        if item.index == 3 and item.instant_utc <= instant
    )
    previous_jie = next(
        item for item in reversed(terms)
        if item.index in JIE_MONTH_BRANCH and item.instant_utc <= instant
    )

    year_number = previous_lichun.local_datetime.year
    year_gz = _year_ganzhi(year_number)
    month_gz = _month_ganzhi(year_gz.tg, JIE_MONTH_BRANCH[previous_jie.index])

    pillar_date = value
    if day_boundary == "forward" and value.hour >= 23:
        pillar_date = value + timedelta(days=1)
    solar_day = sxtwl.fromSolar(pillar_date.year, pillar_date.month, pillar_date.day)
    day_gz = _sxtwl_gz(solar_day.getDayGZ())
    hour = 0 if day_boundary == "forward" and value.hour >= 23 else value.hour
    hour_gz = _sxtwl_gz(solar_day.getHourGZ(hour))

    expected = " ".join(item.text for item in (year_gz, month_gz, day_gz, hour_gz))
    nearest_seconds = min(
        abs((instant - previous.instant_utc).total_seconds()),
        abs((following.instant_utc - instant).total_seconds()),
    )
    quality = (
        _crosscheck(
            value,
            timezone_name=timezone_name,
            day_boundary=day_boundary,
            expected=expected,
        )
        if crosscheck
        else {"status": "verified_canonical", "label": "已校准", "crosscheck": "skipped"}
    )
    return CalendarFactSet(
        year_gz=year_gz,
        month_gz=month_gz,
        day_gz=day_gz,
        hour_gz=hour_gz,
        previous_jie=previous,
        next_jie=following,
        lichun_boundary=previous_lichun,
        boundary_flags={
            "near_solar_term": nearest_seconds <= 6 * 3600,
            "nearest_solar_term_seconds": round(nearest_seconds),
        },
        quality=quality,
    )


def serialize_solar_term(term: SolarTermInstant, reference: datetime) -> dict[str, Any]:
    seconds_away = round((term.instant_utc - reference.astimezone(UTC)).total_seconds())
    return {
        "name": term.name,
        "timestamp": term.local_datetime.isoformat(),
        "instant_utc": term.instant_utc.isoformat(),
        "days_away": round(seconds_away / 86400, 2),
        "seconds_away": seconds_away,
    }
