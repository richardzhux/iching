from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
from math import cos, pi, sin
from typing import Any, Dict, Iterable, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import sxtwl
from lunar_python import Lunar as LunarCalendar
from lunar_python import Solar as SolarCalendar

from iching.core.najia import derive_six_gods

STEMS = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
BRANCHES = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
ELEMENTS = ["木", "火", "土", "金", "水"]
STEM_ELEMENTS = {stem: ELEMENTS[index // 2] for index, stem in enumerate(STEMS)}
BRANCH_ELEMENTS = dict(zip(BRANCHES, ["水", "土", "木", "木", "土", "火", "火", "土", "金", "金", "土", "水"]))
HIDDEN_STEMS = {
    "子": ["癸"], "丑": ["己", "癸", "辛"], "寅": ["甲", "丙", "戊"], "卯": ["乙"],
    "辰": ["戊", "乙", "癸"], "巳": ["丙", "戊", "庚"], "午": ["丁", "己"], "未": ["己", "丁", "乙"],
    "申": ["庚", "壬", "戊"], "酉": ["辛"], "戌": ["戊", "辛", "丁"], "亥": ["壬", "甲"],
}
NAYIN = [
    "海中金", "炉中火", "大林木", "路旁土", "剑锋金", "山头火", "涧下水", "城头土", "白蜡金", "杨柳木",
    "泉中水", "屋上土", "霹雳火", "松柏木", "长流水", "沙中金", "山下火", "平地木", "壁上土", "金箔金",
    "覆灯火", "天河水", "大驿土", "钗钏金", "桑柘木", "大溪水", "沙中土", "天上火", "石榴木", "大海水",
]
JIE_QI_NAMES = [
    "冬至", "小寒", "大寒", "立春", "雨水", "惊蛰", "春分", "清明", "谷雨", "立夏", "小满", "芒种",
    "夏至", "小暑", "大暑", "立秋", "处暑", "白露", "秋分", "寒露", "霜降", "立冬", "小雪", "大雪",
]
LUNAR_MONTHS = ["", "正", "二", "三", "四", "五", "六", "七", "八", "九", "十", "冬", "腊"]
LUNAR_DAYS = [
    "", "初一", "初二", "初三", "初四", "初五", "初六", "初七", "初八", "初九", "初十",
    "十一", "十二", "十三", "十四", "十五", "十六", "十七", "十八", "十九", "二十",
    "廿一", "廿二", "廿三", "廿四", "廿五", "廿六", "廿七", "廿八", "廿九", "三十",
]
BRANCH_CLASH = dict(zip(BRANCHES, ["午", "未", "申", "酉", "戌", "亥", "子", "丑", "寅", "卯", "辰", "巳"]))
BRANCH_COMBINE = dict(zip(BRANCHES, ["丑", "子", "亥", "戌", "酉", "申", "未", "午", "巳", "辰", "卯", "寅"]))


def _timezone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"未知时区: {name}") from exc


def _localize(value: datetime, timezone_name: str) -> datetime:
    zone = _timezone(timezone_name)
    if value.tzinfo is None:
        return value.replace(tzinfo=zone)
    return value.astimezone(zone)


def _calendar_input_to_solar(
    value: datetime,
    *,
    timezone_name: str,
    calendar_type: str,
    is_leap_month: bool,
    lunar_year: Optional[int] = None,
    lunar_month: Optional[int] = None,
    lunar_day: Optional[int] = None,
    lunar_hour: Optional[int] = None,
    lunar_minute: Optional[int] = None,
) -> tuple[datetime, Dict[str, Any]]:
    local_input = _localize(value, timezone_name)
    if calendar_type == "solar":
        return local_input, {
            "calendar_type": "solar",
            "input_date": local_input.isoformat(),
            "is_leap_month": False,
        }
    if calendar_type != "lunar":
        raise ValueError(f"未知历法类型: {calendar_type}")
    if lunar_year is None or lunar_month is None or lunar_day is None:
        raise ValueError("农历排盘必须提供农历年、月、日。")
    input_hour = 0 if lunar_hour is None else lunar_hour
    input_minute = 0 if lunar_minute is None else lunar_minute
    signed_lunar_month = -abs(lunar_month) if is_leap_month else lunar_month
    try:
        lunar = LunarCalendar.fromYmdHms(
            lunar_year,
            signed_lunar_month,
            lunar_day,
            input_hour,
            input_minute,
            0,
        )
        solar = lunar.getSolar()
    except Exception as exc:
        raise ValueError("无效的农历日期或闰月设置。") from exc
    zone = _timezone(timezone_name)
    solar_value = datetime(
        solar.getYear(),
        solar.getMonth(),
        solar.getDay(),
        solar.getHour(),
        solar.getMinute(),
        solar.getSecond(),
        tzinfo=zone,
    )
    return solar_value, {
        "calendar_type": "lunar",
        "input_date": f"{lunar_year:04d}-{abs(signed_lunar_month):02d}-{lunar_day:02d} {input_hour:02d}:{input_minute:02d}:00",
        "is_leap_month": is_leap_month,
        "converted_solar_date": solar_value.isoformat(),
    }


def _true_solar_time(value: datetime, longitude: Optional[float]) -> tuple[datetime, float]:
    if longitude is None:
        return value, 0.0
    standard_offset = (value.utcoffset() or timedelta()) - (value.dst() or timedelta())
    standard_meridian = standard_offset.total_seconds() / 3600 * 15
    day_number = value.timetuple().tm_yday
    b = 2 * pi * (day_number - 81) / 364
    equation = 9.87 * sin(2 * b) - 7.53 * cos(b) - 1.5 * sin(b)
    correction_minutes = 4 * (longitude - standard_meridian) + equation
    return value + timedelta(minutes=correction_minutes), correction_minutes


def _gz_text(gz: Any) -> str:
    return f"{STEMS[gz.tg]}{BRANCHES[gz.dz]}"


def _sexagenary_index(stem: str, branch: str) -> int:
    for index in range(60):
        if STEMS[index % 10] == stem and BRANCHES[index % 12] == branch:
            return index
    raise ValueError(f"无效干支组合: {stem}{branch}")


def _nayin(stem: str, branch: str) -> str:
    return NAYIN[_sexagenary_index(stem, branch) // 2]


def _ten_god(day_stem: str, other_stem: str) -> str:
    self_element = ELEMENTS.index(STEM_ELEMENTS[day_stem])
    other_element = ELEMENTS.index(STEM_ELEMENTS[other_stem])
    same_polarity = STEMS.index(day_stem) % 2 == STEMS.index(other_stem) % 2
    relation = (other_element - self_element) % 5
    if relation == 0:
        return "比肩" if same_polarity else "劫财"
    if relation == 1:
        return "食神" if same_polarity else "伤官"
    if relation == 2:
        return "偏财" if same_polarity else "正财"
    if relation == 3:
        return "七杀" if same_polarity else "正官"
    return "偏印" if same_polarity else "正印"


def _pillar(label: str, gz: Any, day_stem: str) -> Dict[str, Any]:
    stem = STEMS[gz.tg]
    branch = BRANCHES[gz.dz]
    return {
        "label": label,
        "stem": stem,
        "branch": branch,
        "text": f"{stem}{branch}",
        "stem_element": STEM_ELEMENTS[stem],
        "branch_element": BRANCH_ELEMENTS[branch],
        "polarity": "阳" if gz.tg % 2 == 0 else "阴",
        "ten_god": "日主" if label == "日" else _ten_god(day_stem, stem),
        "hidden_stems": [
            {"stem": hidden, "element": STEM_ELEMENTS[hidden], "ten_god": _ten_god(day_stem, hidden)}
            for hidden in HIDDEN_STEMS[branch]
        ],
        "nayin": _nayin(stem, branch),
    }


def _xunkong(day_stem: str, day_branch: str) -> str:
    start_branch = (BRANCHES.index(day_branch) - STEMS.index(day_stem)) % 12
    return f"{BRANCHES[(start_branch - 2) % 12]}{BRANCHES[(start_branch - 1) % 12]}"


def _jieqi_datetime(item: Any, zone: ZoneInfo) -> datetime:
    value = sxtwl.JD2DD(item.jd)
    return datetime(
        int(value.Y),
        int(value.M),
        int(value.D),
        int(value.h),
        int(value.m),
        int(value.s),
        tzinfo=zone,
    )


def _nearby_jieqi(value: datetime) -> tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    items: list[tuple[datetime, int]] = []
    for year in (value.year - 1, value.year, value.year + 1):
        for item in sxtwl.getJieQiByYear(year):
            items.append((_jieqi_datetime(item, value.tzinfo), int(item.jqIndex)))
    items.sort(key=lambda pair: pair[0])
    previous = next(((dt, idx) for dt, idx in reversed(items) if dt <= value), None)
    following = next(((dt, idx) for dt, idx in items if dt > value), None)

    def serialize(pair: Optional[tuple[datetime, int]]) -> Optional[Dict[str, Any]]:
        if not pair:
            return None
        dt, index = pair
        seconds_away = round((dt - value).total_seconds())
        return {
            "name": JIE_QI_NAMES[index],
            "timestamp": dt.isoformat(),
            "days_away": round(seconds_away / 86400, 2),
            "seconds_away": seconds_away,
        }

    return serialize(previous), serialize(following)


def _hour_candidates(value: datetime, day_boundary: str) -> list[Dict[str, str]]:
    labels = ["早子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥", "晚子"]
    hours = [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 23]
    candidates: list[Dict[str, str]] = []
    for label, hour in zip(labels, hours):
        candidate = value.replace(hour=hour, minute=0, second=0, microsecond=0)
        pillar_date = candidate + timedelta(days=1) if day_boundary == "forward" and hour == 23 else candidate
        solar_day = sxtwl.fromSolar(pillar_date.year, pillar_date.month, pillar_date.day)
        hour_gz = solar_day.getHourGZ(0 if day_boundary == "forward" and hour == 23 else hour)
        candidates.append({"label": label, "time_range": f"{hour:02d}:00", "pillar": _gz_text(hour_gz)})
    return candidates


def _dayun_payload(
    value: datetime,
    *,
    gender: Optional[str],
    hour_uncertain: bool,
    day_boundary: str,
    algorithm: str,
    expected_bazi: str,
) -> Dict[str, Any]:
    if gender not in {"male", "female"}:
        return {"status": "not_requested", "cycles": []}
    if hour_uncertain:
        return {
            "status": "requires_hour",
            "algorithm": algorithm,
            "note": "时辰不确定时，起运时刻与大运交接可能变化，暂不输出伪精确大运。",
            "cycles": [],
        }
    solar = SolarCalendar.fromYmdHms(value.year, value.month, value.day, value.hour, value.minute, value.second)
    eight_char = solar.getLunar().getEightChar()
    eight_char.setSect(1 if day_boundary == "forward" else 2)
    crosscheck_bazi = eight_char.toString()
    sect = 2 if algorithm == "sect2" else 1
    yun = eight_char.getYun(1 if gender == "male" else 0, sect)
    cycles = []
    for cycle in yun.getDaYun(9):
        cycles.append({
            "index": cycle.getIndex(),
            "label": "童限" if cycle.getIndex() == 0 else cycle.getGanZhi(),
            "ganzhi": cycle.getGanZhi(),
            "start_year": cycle.getStartYear(),
            "end_year": cycle.getEndYear(),
            "start_age": cycle.getStartAge(),
            "end_age": cycle.getEndAge(),
        })
    return {
        "status": "available",
        "algorithm": algorithm,
        "algorithm_note": "sect2 按分钟精算；sect1 按日数与时辰折算。" if algorithm == "sect2" else "sect1 按日数与时辰折算。",
        "direction": "forward" if yun.isForward() else "reverse",
        "start": {
            "years": yun.getStartYear(),
            "months": yun.getStartMonth(),
            "days": yun.getStartDay(),
            "hours": yun.getStartHour(),
            "solar_date": yun.getStartSolar().toYmdHms(),
        },
        "engine_bazi": crosscheck_bazi,
        "crosscheck_matches": crosscheck_bazi == expected_bazi,
        "cycles": cycles,
    }


def build_metaphysics_chart(
    timestamp: datetime,
    *,
    timezone_name: str = "Asia/Shanghai",
    longitude: Optional[float] = None,
    use_true_solar_time: bool = False,
    day_boundary: str = "forward",
    calendar_type: str = "solar",
    is_leap_month: bool = False,
    gender: Optional[str] = None,
    birth_place: Optional[str] = None,
    hour_uncertain: bool = False,
    dayun_algorithm: str = "sect2",
    lunar_year: Optional[int] = None,
    lunar_month: Optional[int] = None,
    lunar_day: Optional[int] = None,
    lunar_hour: Optional[int] = None,
    lunar_minute: Optional[int] = None,
) -> Dict[str, Any]:
    if dayun_algorithm not in {"sect1", "sect2"}:
        raise ValueError(f"未知大运算法: {dayun_algorithm}")
    local, calendar_input = _calendar_input_to_solar(
        timestamp,
        timezone_name=timezone_name,
        calendar_type=calendar_type,
        is_leap_month=is_leap_month,
        lunar_year=lunar_year,
        lunar_month=lunar_month,
        lunar_day=lunar_day,
        lunar_hour=lunar_hour,
        lunar_minute=lunar_minute,
    )
    effective_local = local.replace(hour=12, minute=0, second=0, microsecond=0) if hour_uncertain else local
    calculation_time, correction_minutes = _true_solar_time(effective_local, longitude) if use_true_solar_time else (effective_local, 0.0)
    pillar_date = calculation_time
    if day_boundary == "forward" and calculation_time.hour >= 23:
        pillar_date = calculation_time + timedelta(days=1)

    solar_day = sxtwl.fromSolar(pillar_date.year, pillar_date.month, pillar_date.day)
    year_gz = solar_day.getYearGZ()
    month_gz = solar_day.getMonthGZ()
    day_gz = solar_day.getDayGZ()
    hour_for_gz = 0 if day_boundary == "forward" and calculation_time.hour >= 23 else calculation_time.hour
    hour_gz = solar_day.getHourGZ(hour_for_gz)
    day_stem = STEMS[day_gz.tg]
    pillars = [
        _pillar("年", year_gz, day_stem),
        _pillar("月", month_gz, day_stem),
        _pillar("日", day_gz, day_stem),
        _pillar("时", hour_gz, day_stem),
    ]
    hour_candidates = _hour_candidates(calculation_time, day_boundary) if hour_uncertain else []
    if hour_uncertain:
        pillars[-1] = {
            "label": "时",
            "stem": "待定",
            "branch": "待定",
            "text": "待定",
            "stem_element": "—",
            "branch_element": "—",
            "polarity": "—",
            "ten_god": "待定",
            "hidden_stems": [],
            "nayin": "—",
        }
    direct_elements: Iterable[str] = (
        value
        for pillar in pillars
        for value in (pillar["stem_element"], pillar["branch_element"])
        if value in ELEMENTS
    )
    counts = Counter(direct_elements)
    previous_term, next_term = _nearby_jieqi(calculation_time)
    lunar_month = abs(solar_day.getLunarMonth())
    lunar_day = solar_day.getLunarDay()
    lunar_text = f"{solar_day.getLunarYear()}年{'闰' if solar_day.isLunarLeap() else ''}{LUNAR_MONTHS[lunar_month]}月{LUNAR_DAYS[lunar_day]}"
    month_branch = pillars[1]["branch"]
    day_branch = pillars[2]["branch"]
    six_gods = derive_six_gods(day_stem)
    bazi_text = " ".join(pillar["text"] for pillar in pillars)
    dayun = _dayun_payload(
        calculation_time,
        gender=gender,
        hour_uncertain=hour_uncertain,
        day_boundary=day_boundary,
        algorithm=dayun_algorithm,
        expected_bazi=bazi_text,
    )
    return {
        "timezone": timezone_name,
        "input_timestamp": local.isoformat(),
        "calculation_timestamp": calculation_time.isoformat(),
        "calculation_mode": "true_solar" if use_true_solar_time else "standard_time",
        "true_solar_correction_minutes": round(correction_minutes, 2),
        "day_boundary": day_boundary,
        "lunar_date": lunar_text,
        "pillars": pillars,
        "bazi": bazi_text,
        "day_master": day_stem,
        "xunkong": _xunkong(pillars[2]["stem"], pillars[2]["branch"]),
        "calendar_facts": {
            "gregorian": calculation_time.isoformat(),
            "month_command": month_branch,
            "day_pillar": pillars[2]["text"],
            "day_branch": day_branch,
            "month_clash": BRANCH_CLASH[month_branch],
            "month_combine": BRANCH_COMBINE[month_branch],
            "day_clash": BRANCH_CLASH[day_branch],
            "day_combine": BRANCH_COMBINE[day_branch],
            "six_spirit_start": six_gods[0],
            "six_spirits": six_gods,
        },
        "element_counts": {element: counts.get(element, 0) for element in ELEMENTS},
        "previous_solar_term": previous_term,
        "next_solar_term": next_term,
        "birth_profile": {
            **calendar_input,
            "birth_place": birth_place or "",
            "gender": gender,
            "hour_uncertain": hour_uncertain,
            "hour_candidates": hour_candidates,
            "dayun": dayun,
            "engines": {
                "calendar": "sxtwl 2.0.7",
                "birth_calendar_and_dayun": "lunar_python 1.4.8",
            },
        },
    }
