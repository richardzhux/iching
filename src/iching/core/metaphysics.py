from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
import logging
from math import cos, pi, sin
from typing import Any, Dict, Iterable, Optional
from zoneinfo import ZoneInfo

import sxtwl
from lunar_python import Lunar as LunarCalendar
from lunar_python import Solar as SolarCalendar

from iching.core.bazi_patterns import assess_patterns
from iching.core.bazi_rules.adapter import (
    build_source_backed_shadow,
    canonical_authority_from_shadow,
)
from iching.core.bazi_rules.registry import load_packaged_shen_registry
from iching.core.bazi_rules.fact_graph import (
    build_bazi_fact_envelope_from_graphs,
    build_bazi_fact_graph,
)
from iching.core.bazi_structure import build_structure_profile, structured_relations
from iching.core.calendar_engine import (
    ENGINE_VERSION as CALENDAR_ENGINE_VERSION,
    JIE_MONTH_BRANCH,
    calculate_calendar_facts,
    normalize_local_datetime,
    serialize_solar_term,
    solar_terms_for_years,
    solar_term_datetime,
    timezone_for,
)
from iching.core.najia import derive_six_gods
from iching.core.metaphysics_statistics import (
    BASELINE_ID,
    BASELINE_IDS,
    statistics_for_shensha,
    unavailable_bazi_statistics,
)
from iching.core.metaphysics_consumer import (
    CONSUMER_RULES_VERSION,
    build_bazi_consumer_profile,
    consumer_feature_records,
)
from iching.core.shensha import RULES_VERSION, evaluate_shensha
from iching.core.shensha_effects import evaluate_shensha_effects

logger = logging.getLogger(__name__)

STEMS = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
BRANCHES = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
ELEMENTS = ["木", "火", "土", "金", "水"]
STEM_ELEMENTS = {stem: ELEMENTS[index // 2] for index, stem in enumerate(STEMS)}
BRANCH_ELEMENTS = dict(
    zip(
        BRANCHES,
        ["水", "土", "木", "木", "土", "火", "火", "土", "金", "金", "土", "水"],
    )
)
HIDDEN_STEMS = {
    "子": ["癸"],
    "丑": ["己", "癸", "辛"],
    "寅": ["甲", "丙", "戊"],
    "卯": ["乙"],
    "辰": ["戊", "乙", "癸"],
    "巳": ["丙", "戊", "庚"],
    "午": ["丁", "己"],
    "未": ["己", "丁", "乙"],
    "申": ["庚", "壬", "戊"],
    "酉": ["辛"],
    "戌": ["戊", "辛", "丁"],
    "亥": ["壬", "甲"],
}
NAYIN = [
    "海中金",
    "炉中火",
    "大林木",
    "路旁土",
    "剑锋金",
    "山头火",
    "涧下水",
    "城头土",
    "白蜡金",
    "杨柳木",
    "泉中水",
    "屋上土",
    "霹雳火",
    "松柏木",
    "长流水",
    "沙中金",
    "山下火",
    "平地木",
    "壁上土",
    "金箔金",
    "覆灯火",
    "天河水",
    "大驿土",
    "钗钏金",
    "桑柘木",
    "大溪水",
    "沙中土",
    "天上火",
    "石榴木",
    "大海水",
]
JIE_QI_NAMES = [
    "冬至",
    "小寒",
    "大寒",
    "立春",
    "雨水",
    "惊蛰",
    "春分",
    "清明",
    "谷雨",
    "立夏",
    "小满",
    "芒种",
    "夏至",
    "小暑",
    "大暑",
    "立秋",
    "处暑",
    "白露",
    "秋分",
    "寒露",
    "霜降",
    "立冬",
    "小雪",
    "大雪",
]
LUNAR_MONTHS = [
    "",
    "正",
    "二",
    "三",
    "四",
    "五",
    "六",
    "七",
    "八",
    "九",
    "十",
    "冬",
    "腊",
]
LUNAR_DAYS = [
    "",
    "初一",
    "初二",
    "初三",
    "初四",
    "初五",
    "初六",
    "初七",
    "初八",
    "初九",
    "初十",
    "十一",
    "十二",
    "十三",
    "十四",
    "十五",
    "十六",
    "十七",
    "十八",
    "十九",
    "二十",
    "廿一",
    "廿二",
    "廿三",
    "廿四",
    "廿五",
    "廿六",
    "廿七",
    "廿八",
    "廿九",
    "三十",
]
BRANCH_CLASH = dict(
    zip(
        BRANCHES,
        ["午", "未", "申", "酉", "戌", "亥", "子", "丑", "寅", "卯", "辰", "巳"],
    )
)
BRANCH_COMBINE = dict(
    zip(
        BRANCHES,
        ["丑", "子", "亥", "戌", "酉", "申", "未", "午", "巳", "辰", "卯", "寅"],
    )
)
CHANG_SHENG = [
    "长生",
    "沐浴",
    "冠带",
    "临官",
    "帝旺",
    "衰",
    "病",
    "死",
    "墓",
    "绝",
    "胎",
    "养",
]
CHANG_SHENG_OFFSET = {
    "甲": 1,
    "丙": 10,
    "戊": 10,
    "庚": 7,
    "壬": 4,
    "乙": 6,
    "丁": 9,
    "己": 9,
    "辛": 0,
    "癸": 3,
}
STEM_CLASHES = {
    frozenset(pair) for pair in (("甲", "庚"), ("乙", "辛"), ("丙", "壬"), ("丁", "癸"))
}
STEM_COMBINATIONS = {
    frozenset(("甲", "己")): "甲己合土",
    frozenset(("乙", "庚")): "乙庚合金",
    frozenset(("丙", "辛")): "丙辛合水",
    frozenset(("丁", "壬")): "丁壬合木",
    frozenset(("戊", "癸")): "戊癸合火",
}
ELEMENT_CONTROLS = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}
BRANCH_CLASHES = {
    frozenset(pair)
    for pair in (
        ("子", "午"),
        ("丑", "未"),
        ("寅", "申"),
        ("卯", "酉"),
        ("辰", "戌"),
        ("巳", "亥"),
    )
}
BRANCH_SIX_COMBINATIONS = {
    frozenset(("子", "丑")): "子丑六合土",
    frozenset(("寅", "亥")): "寅亥六合木",
    frozenset(("卯", "戌")): "卯戌六合火",
    frozenset(("辰", "酉")): "辰酉六合金",
    frozenset(("巳", "申")): "巳申六合水",
    frozenset(("午", "未")): "午未六合",
}
BRANCH_HARMS = {
    frozenset(pair)
    for pair in (
        ("子", "未"),
        ("丑", "午"),
        ("寅", "巳"),
        ("卯", "辰"),
        ("申", "亥"),
        ("酉", "戌"),
    )
}
BRANCH_BREAKS = {
    frozenset(pair)
    for pair in (
        ("子", "酉"),
        ("丑", "辰"),
        ("寅", "亥"),
        ("卯", "午"),
        ("巳", "申"),
        ("未", "戌"),
    )
}
BRANCH_HARMONIES = (
    ("申子辰", "水"),
    ("亥卯未", "木"),
    ("寅午戌", "火"),
    ("巳酉丑", "金"),
)
BRANCH_MEETINGS = (
    ("亥子丑", "水"),
    ("寅卯辰", "木"),
    ("巳午未", "火"),
    ("申酉戌", "金"),
)
SEASONAL_ELEMENT_STATUS = {
    "spring": {"木": "旺", "火": "相", "水": "休", "金": "囚", "土": "死"},
    "summer": {"火": "旺", "土": "相", "木": "休", "水": "囚", "金": "死"},
    "autumn": {"金": "旺", "水": "相", "土": "休", "火": "囚", "木": "死"},
    "winter": {"水": "旺", "木": "相", "金": "休", "土": "囚", "火": "死"},
    "earth": {"土": "旺", "金": "相", "火": "休", "木": "囚", "水": "死"},
}


def bazi_rule_versions() -> Dict[str, str]:
    """Return the exact rule tuple bound to live BaZi schema-v7 results."""
    registry = load_packaged_shen_registry()
    return {
        "calendar": CALENDAR_ENGINE_VERSION,
        "pattern_bundle": registry.bundle_id,
        "pattern_digest": registry.bundle_digest,
        "shensha": RULES_VERSION,
        "consumer": CONSUMER_RULES_VERSION,
    }


def _statistics_or_unavailable(
    hits: Iterable[Dict[str, Any]],
    day_boundary: str,
    *,
    theme_profiles: Iterable[Dict[str, Any]],
    gender: Optional[str] = None,
    day_master: str = "",
    month_command: str = "",
    consumer_feature_ids: Iterable[str] = (),
) -> Dict[str, Any]:
    """Isolate optional baseline failures from deterministic chart output."""
    hit_list = list(hits)
    profile_list = list(theme_profiles)
    feature_ids = [
        str(hit.get("feature_id", "")) for hit in hit_list if hit.get("feature_id")
    ]
    try:
        return statistics_for_shensha(
            hit_list,
            day_boundary,
            theme_profiles=profile_list,
            gender=gender,
            day_master=day_master,
            month_command=month_command,
            consumer_feature_ids=consumer_feature_ids,
        )
    except (RuntimeError, OSError, ValueError) as exc:
        logger.warning(
            "BaZi statistics unavailable; returning chart without comparisons: %s", exc
        )
        baseline_id = BASELINE_IDS["bazi"].get(day_boundary, BASELINE_ID)
        return unavailable_bazi_statistics(
            baseline_id=baseline_id,
            feature_ids=feature_ids,
            theme_profiles=profile_list,
            reason=str(exc),
            status=getattr(exc, "status", "unavailable"),
        )


def _timezone(name: str) -> ZoneInfo:
    return timezone_for(name)


def _localize(value: datetime, timezone_name: str) -> datetime:
    return normalize_local_datetime(value, timezone_name).local_datetime


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
    fold_choice: Optional[str] = None,
) -> tuple[datetime, Dict[str, Any]]:
    local_input = normalize_local_datetime(
        value,
        timezone_name,
        fold_choice=fold_choice if fold_choice in {"first", "second"} else None,
    ).local_datetime
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
    solar_naive = datetime(
        solar.getYear(),
        solar.getMonth(),
        solar.getDay(),
        solar.getHour(),
        solar.getMinute(),
        solar.getSecond(),
    )
    solar_value = normalize_local_datetime(
        solar_naive,
        timezone_name,
        fold_choice=fold_choice if fold_choice in {"first", "second"} else None,
    ).local_datetime
    return solar_value, {
        "calendar_type": "lunar",
        "input_date": f"{lunar_year:04d}-{abs(signed_lunar_month):02d}-{lunar_day:02d} {input_hour:02d}:{input_minute:02d}:00",
        "is_leap_month": is_leap_month,
        "converted_solar_date": solar_value.isoformat(),
    }


def _true_solar_time(
    value: datetime, longitude: Optional[float]
) -> tuple[datetime, float]:
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


def _growth_stage(stem: str, branch: str) -> str:
    branch_index = BRANCHES.index(branch)
    index = CHANG_SHENG_OFFSET[stem] + (
        branch_index if STEMS.index(stem) % 2 == 0 else -branch_index
    )
    return CHANG_SHENG[index % 12]


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
            {
                "stem": hidden,
                "element": STEM_ELEMENTS[hidden],
                "ten_god": _ten_god(day_stem, hidden),
            }
            for hidden in HIDDEN_STEMS[branch]
        ],
        "nayin": _nayin(stem, branch),
        "xunkong": _xunkong(stem, branch),
        "di_shi": _growth_stage(day_stem, branch),
        "self_seat": _growth_stage(stem, branch),
    }


def _xunkong(day_stem: str, day_branch: str) -> str:
    start_branch = (BRANCHES.index(day_branch) - STEMS.index(day_stem)) % 12
    return f"{BRANCHES[(start_branch - 2) % 12]}{BRANCHES[(start_branch - 1) % 12]}"


def _stem_relations(pillars: list[Dict[str, Any]]) -> list[str]:
    stems = [pillar["stem"] for pillar in pillars if pillar["stem"] in STEMS]
    relations: list[str] = []
    for left_index, left in enumerate(stems):
        for right in stems[left_index + 1 :]:
            pair = frozenset((left, right))
            if pair in STEM_CLASHES:
                relation = f"{left}{right}冲"
            elif pair in STEM_COMBINATIONS:
                relation = STEM_COMBINATIONS[pair]
            elif ELEMENT_CONTROLS[STEM_ELEMENTS[left]] == STEM_ELEMENTS[right]:
                relation = f"{left}{right}克"
            elif ELEMENT_CONTROLS[STEM_ELEMENTS[right]] == STEM_ELEMENTS[left]:
                relation = f"{right}{left}克"
            else:
                continue
            if relation not in relations:
                relations.append(relation)
    return relations


def _branch_relations(pillars: list[Dict[str, Any]]) -> list[str]:
    branches = [pillar["branch"] for pillar in pillars if pillar["branch"] in BRANCHES]
    relations: list[str] = []
    for group, element in BRANCH_HARMONIES:
        unique = [branch for branch in group if branch in branches]
        if len(unique) == 3:
            relations.append(f"{''.join(unique)}三合{element}")
        elif len(unique) == 2:
            relations.append(f"{''.join(unique)}半合{element}")
    for group, element in BRANCH_MEETINGS:
        unique = [branch for branch in group if branch in branches]
        if len(unique) == 3:
            relations.append(f"{''.join(unique)}三会{element}")
        elif len(unique) == 2:
            relations.append(f"{''.join(unique)}半会{element}")
    for left_index, left in enumerate(branches):
        for right in branches[left_index + 1 :]:
            pair = frozenset((left, right))
            labels: list[str] = []
            if pair in BRANCH_SIX_COMBINATIONS:
                labels.append(BRANCH_SIX_COMBINATIONS[pair])
            if pair in BRANCH_CLASHES:
                labels.append("相冲")
            if pair in BRANCH_HARMS:
                labels.append("相害")
            if pair in BRANCH_BREAKS:
                labels.append("相破")
            if (
                pair <= frozenset(("寅", "巳", "申"))
                or pair <= frozenset(("丑", "未", "戌"))
                or pair == frozenset(("子", "卯"))
            ):
                labels.append("相刑")
            if left == right and left in {"辰", "午", "酉", "亥"}:
                labels.append("自刑")
            for label in labels:
                if label.endswith("六合") or "六合" in label:
                    relation = label
                    if relation not in relations:
                        relations.append(relation)
                    continue
                ordered_pair = "".join(sorted((left, right), key=BRANCHES.index))
                relation = f"{ordered_pair}{label}"
                if relation not in relations:
                    relations.append(relation)
    return relations


def _seasonal_status(month_branch: str) -> Dict[str, str]:
    season = "earth"
    if month_branch in {"寅", "卯"}:
        season = "spring"
    elif month_branch in {"巳", "午"}:
        season = "summer"
    elif month_branch in {"申", "酉"}:
        season = "autumn"
    elif month_branch in {"亥", "子"}:
        season = "winter"
    return SEASONAL_ELEMENT_STATUS[season]


def _jieqi_datetime(item: Any, zone: ZoneInfo) -> datetime:
    return solar_term_datetime(item, zone)


def _nearby_jieqi(
    value: datetime,
) -> tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
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
    labels = [
        "早子",
        "丑",
        "寅",
        "卯",
        "辰",
        "巳",
        "午",
        "未",
        "申",
        "酉",
        "戌",
        "亥",
        "晚子",
    ]
    hours = [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 23]
    candidates: list[Dict[str, str]] = []
    for label, hour in zip(labels, hours):
        candidate = value.replace(hour=hour, minute=0, second=0, microsecond=0)
        pillar_date = (
            candidate + timedelta(days=1)
            if day_boundary == "forward" and hour == 23
            else candidate
        )
        solar_day = sxtwl.fromSolar(
            pillar_date.year, pillar_date.month, pillar_date.day
        )
        hour_gz = solar_day.getHourGZ(
            0 if day_boundary == "forward" and hour == 23 else hour
        )
        candidates.append(
            {
                "label": label,
                "time_range": f"{hour:02d}:00",
                "pillar": _gz_text(hour_gz),
            }
        )
    return candidates


def _build_uncertain_metaphysics_chart(
    local: datetime,
    *,
    calendar_input: Dict[str, Any],
    timezone_name: str,
    longitude: Optional[float],
    use_true_solar_time: bool,
    day_boundary: str,
    gender: Optional[str],
    birth_place: Optional[str],
    dayun_algorithm: str,
) -> Dict[str, Any]:
    """Build useful, explicitly stable results when the birth hour is unknown."""
    representative = local.replace(hour=12, minute=0, second=0, microsecond=0)
    base = build_metaphysics_chart(
        representative,
        timezone_name=timezone_name,
        longitude=longitude,
        use_true_solar_time=use_true_solar_time,
        day_boundary=day_boundary,
        calendar_type="solar",
        gender=gender,
        birth_place=birth_place,
        hour_uncertain=False,
        dayun_algorithm=dayun_algorithm,
        include_period_details=False,
    )
    labels = [
        "早子",
        "丑",
        "寅",
        "卯",
        "辰",
        "巳",
        "午",
        "未",
        "申",
        "酉",
        "戌",
        "亥",
        "晚子",
    ]
    hours = [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 23]
    candidates: list[Dict[str, Any]] = []
    candidate_profiles: list[Dict[str, Any]] = []
    candidate_hits: list[list[Dict[str, Any]]] = []
    candidate_graphs = []

    for label, hour in zip(labels, hours):
        civil = local.replace(hour=hour, minute=0, second=0, microsecond=0)
        calculation_time, _ = (
            _true_solar_time(civil, longitude) if use_true_solar_time else (civil, 0.0)
        )
        facts = calculate_calendar_facts(
            calculation_time,
            timezone_name=timezone_name,
            day_boundary=day_boundary,
        )
        day_stem = STEMS[facts.day_gz.tg]
        pillars = [
            _pillar("年", facts.year_gz, day_stem),
            _pillar("月", facts.month_gz, day_stem),
            _pillar("日", facts.day_gz, day_stem),
            _pillar("时", facts.hour_gz, day_stem),
        ]
        hits = evaluate_shensha(pillars)
        fact_graph = build_bazi_fact_graph(pillars)
        profile = build_structure_profile(
            pillars,
            gender=gender,
            shensha_hits=hits,
            seasonal_status=_seasonal_status(pillars[1]["branch"]),
            fact_graph=fact_graph,
        )
        candidates.append(
            {
                "label": label,
                "time_range": f"{hour:02d}:00",
                "pillar": pillars[3]["text"],
                "day_master": day_stem,
                "pillars": [pillar["text"] for pillar in pillars],
            }
        )
        candidate_profiles.append(profile)
        candidate_hits.append(hits)
        candidate_graphs.append(fact_graph)

    stable_pillars: list[Dict[str, Any]] = []
    for index, pillar_label in enumerate(("年", "月", "日", "时")):
        values = {candidate["pillars"][index] for candidate in candidates}
        if len(values) == 1:
            stable_pillars.append(
                {
                    "label": pillar_label,
                    "text": values.pop(),
                    "pillar": base["pillars"][index],
                }
            )

    stable_rule_ids = set.intersection(
        *({str(hit["rule_id"]) for hit in hits} for hits in candidate_hits)
    )
    hit_by_id = {str(hit["rule_id"]): hit for hit in candidate_hits[0]}
    stable_hits = [
        hit_by_id[rule_id]
        for rule_id in sorted(stable_rule_ids)
        if rule_id in hit_by_id
    ]

    def evidence_key(item: Dict[str, Any]) -> tuple[str, ...]:
        return (
            str(item.get("family", "")),
            str(item.get("evidence_type", "")),
            str(item.get("title", "")),
            str(item.get("detail", "")),
            str(item.get("source", "")),
        )

    evidence_sets = [
        {
            evidence_key(item): (str(theme.get("theme", "")), item)
            for theme in profile.get("theme_profiles", [])
            for item in theme.get("evidence", [])
        }
        for profile in candidate_profiles
    ]
    common_evidence_keys = set.intersection(*(set(items) for items in evidence_sets))
    stable_theme_profiles: list[Dict[str, Any]] = []
    conclusions: list[Dict[str, Any]] = []
    for theme in PERIOD_THEMES:
        evidence: list[Dict[str, Any]] = []
        for key in sorted(common_evidence_keys):
            item_theme, original = evidence_sets[0][key]
            if item_theme != theme:
                continue
            item = dict(original)
            item["id"] = f"stable.{theme}.{len(evidence) + 1}"
            evidence.append(item)
        stable_theme_profiles.append(
            {
                "theme": theme,
                "evidence": evidence,
                "active_families": sorted(
                    {
                        str(item.get("family", ""))
                        for item in evidence
                        if item.get("family")
                    }
                ),
                "structure_metrics": [],
                "comparisons": [],
            }
        )
        if evidence:
            support = [
                item
                for item in evidence
                if item.get("evidence_type") in {"支持", "活动", "背景"}
            ]
            constraints = [
                item for item in evidence if item.get("evidence_type") == "制约"
            ]
            lead = (support or evidence)[0]
            conclusions.append(
                {
                    "id": f"stable.{theme}",
                    "theme": theme,
                    "headline": f"{theme}有不受出生时辰影响的结构主线",
                    "body": f"{lead['title']}。这项判断在全部可能时辰中都成立，可以先作为理解命盘的稳定起点。",
                    "supporting_evidence_ids": [item["id"] for item in support[:3]],
                    "counter_evidence_ids": [item["id"] for item in constraints[:2]],
                    "school_scope": "现代子平通行分析",
                    "school_agreement": "stable_across_hours",
                    "distribution_context": None,
                    "input_sensitivity": "stable",
                    "priority": len(PERIOD_THEMES) - PERIOD_THEMES.index(theme),
                }
            )

    sensitivity: list[Dict[str, str]] = []
    varying_pillars = [
        label
        for index, label in enumerate(("年柱", "月柱", "日柱", "时柱"))
        if len({candidate["pillars"][index] for candidate in candidates}) > 1
    ]
    if varying_pillars:
        sensitivity.append(
            {"label": "可能变化的四柱", "detail": "、".join(varying_pillars)}
        )
    day_masters = sorted({str(candidate["day_master"]) for candidate in candidates})
    if len(day_masters) > 1:
        sensitivity.append({"label": "日主可能变化", "detail": " / ".join(day_masters)})
    all_rule_ids = set.union(
        *({str(hit["rule_id"]) for hit in hits} for hits in candidate_hits)
    )
    variable_rules = all_rule_ids - stable_rule_ids
    if variable_rules:
        sensitivity.append(
            {
                "label": "随时辰变化的神煞",
                "detail": f"{len(variable_rules)} 项会随候选时柱变化",
            }
        )
    sensitivity.append(
        {"label": "运限起点", "detail": "补充时辰后可精确定位大运、流年与流月交接"}
    )

    statistics = _statistics_or_unavailable(
        stable_hits,
        day_boundary,
        theme_profiles=stable_theme_profiles,
        gender=gender,
    )
    base.update(
        {
            "input_timestamp": local.isoformat(),
            "day_master": day_masters[0] if len(day_masters) == 1 else "待定",
            "calculation_quality": {
                "status": "uncertain",
                "label": "已分析稳定部分",
                "crosscheck": "hour_range",
            },
            "shen_sha": stable_hits,
            "theme_profiles": stable_theme_profiles,
            "synthesis": {
                "method": "modern-ziping-common-v1",
                "conclusions": conclusions,
            },
            "statistics": statistics,
            "period_layers": {
                "dayun": [],
                "current": {
                    "as_of": datetime.now(local.tzinfo).isoformat(),
                    "year": None,
                    "month": None,
                },
                "engine": "pending_exact_hour",
            },
            "consumer": {},
        }
    )
    base["structure"]["theme_profiles"] = stable_theme_profiles
    base["structure"]["synthesis"] = base["synthesis"]
    base["birth_profile"].update(
        {
            **calendar_input,
            "birth_place": birth_place or "",
            "gender": gender,
            "hour_uncertain": True,
            "hour_candidates": candidates,
            "stability": {
                "stable_pillars": stable_pillars,
                "stable_shensha": [hit["name"] for hit in stable_hits],
                "sensitive_items": sensitivity[:4],
                "candidate_count": len(candidates),
            },
            "dayun": {
                "status": "requires_hour",
                "algorithm": dayun_algorithm,
                "note": "补充出生时辰后即可精确展开运限。",
                "cycles": [],
            },
        }
    )
    base["birth_profile"].pop("period_query", None)
    envelope = build_bazi_fact_envelope_from_graphs(candidate_graphs)
    uncertain_shadow = build_source_backed_shadow(
        (),
        base["structure"]["patterns"],
        envelope,
        include_attestations=False,
    )
    base["structure"]["patterns"]["source_backed_shadow"] = uncertain_shadow
    base["structure"]["patterns"]["source_backed_authority"] = (
        canonical_authority_from_shadow(uncertain_shadow)
    )
    return base


PERIOD_THEMES = ("事业", "财富", "感情", "五行与承压结构")
PERIOD_TOPIC_THEMES = {
    "career": "事业",
    "wealth": "财富",
    "relationship": "感情",
    "health": "五行与承压结构",
}


def _period_theme_activations(
    *,
    period_label: str,
    ten_god: str,
    gender: Optional[str],
    shensha_hits: list[Dict[str, Any]],
    relations: list[Dict[str, Any]],
) -> Dict[str, list[Dict[str, Any]]]:
    activations: Dict[str, list[Dict[str, Any]]] = {
        theme: [] for theme in PERIOD_THEMES
    }
    seen: set[tuple[str, str, str]] = set()
    layer = {"大运": "dayun", "流年": "liunian", "流月": "liuyue"}.get(
        period_label, "period"
    )

    def add(
        theme: str,
        kind: str,
        label: str,
        detail: str,
        source: str,
        *,
        feature: str = "",
        role: str = "activity",
    ) -> None:
        key = (theme, kind, label)
        if theme not in activations or key in seen:
            return
        seen.add(key)
        activations[theme].append(
            {
                "id": f"bazi.period.{layer}.{theme}.{len(activations[theme]) + 1}",
                "layer": layer,
                "kind": kind,
                # Role explains how the event participates in the structure.
                # K-line magnitude remains unsigned activity density, so a
                # conflict is not silently converted into a bad-life score.
                "role": role,
                "delta": 0.0,
                "activity": 1.0,
                "feature": feature,
                "label": label,
                "detail": detail,
                "source": source,
            }
        )

    if ten_god in {"正官", "七杀", "正印", "偏印", "食神", "伤官"}:
        add(
            "事业",
            "新增",
            f"{period_label}十神·{ten_god}",
            "该运限天干与日主形成此十神关系。",
            "日主中心十神",
            feature=ten_god,
        )
    if ten_god in {"正财", "偏财", "食神", "伤官", "比肩", "劫财"}:
        add(
            "财富",
            "新增",
            f"{period_label}十神·{ten_god}",
            "该运限天干与日主形成此十神关系。",
            "日主中心十神",
            feature=ten_god,
        )
    spouse_gods = {"正财", "偏财"} if gender == "male" else {"正官", "七杀"}
    if ten_god in spouse_gods:
        add(
            "感情",
            "新增",
            f"{period_label}配偶星·{ten_god}",
            "按男命财星、女命官杀的通行取法记录。",
            "子平配偶星取法",
            feature=ten_god,
        )
    if ten_god in {"正印", "偏印", "比肩", "劫财", "正官", "七杀", "食神", "伤官"}:
        add(
            "五行与承压结构",
            "变化",
            f"{period_label}日主关系·{ten_god}",
            "传统五行的支持与制约关系在这一阶段发生变化。",
            "日主中心十神",
            feature=ten_god,
        )

    for hit in shensha_hits:
        for topic in hit.get("topic_tags", ()):
            theme = PERIOD_TOPIC_THEMES.get(str(topic))
            if theme:
                # A ShenSha occurrence is context, not an automatic rise or fall.
                add(
                    theme,
                    "新增",
                    f"{period_label}神煞·{hit['name']}",
                    str(hit.get("trigger", "")),
                    "版本化神煞注册表",
                    feature=str(hit.get("rule_id", hit["name"])),
                    role="neutral",
                )

    for relation in relations:
        relation_type = str(relation.get("relation_type", ""))
        conflict = any(
            token in relation_type for token in ("冲", "刑", "害", "破", "克")
        )
        kind = "冲突" if conflict else "联动"
        for theme in relation.get("theme_tags", ()):
            add(
                str(theme),
                kind,
                f"{period_label}关系·{relation_type}",
                str(relation.get("label", "")),
                "结构化干支关系",
                feature=relation_type,
                role="conflict" if conflict else "support",
            )
    return activations


def _dayun_payload(
    value: datetime,
    *,
    gender: Optional[str],
    hour_uncertain: bool,
    day_boundary: str,
    algorithm: str,
    expected_bazi: str,
    natal_pillars: list[Dict[str, Any]],
    timezone_name: str,
    reference_timestamp: Optional[datetime] = None,
    include_period_details: bool = True,
    period_cycle_index: Optional[int] = None,
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
    solar = SolarCalendar.fromYmdHms(
        value.year, value.month, value.day, value.hour, value.minute, value.second
    )
    eight_char = solar.getLunar().getEightChar()
    eight_char.setSect(1 if day_boundary == "forward" else 2)
    crosscheck_bazi = eight_char.toString()
    sect = 2 if algorithm == "sect2" else 1
    yun = eight_char.getYun(1 if gender == "male" else 0, sect)
    reference = (
        normalize_local_datetime(reference_timestamp, timezone_name).local_datetime
        if reference_timestamp is not None
        else datetime.now(value.tzinfo)
    )
    reference_facts = calculate_calendar_facts(
        reference,
        timezone_name=timezone_name,
        day_boundary=day_boundary,
    )
    reference_year = reference_facts.lichun_boundary.local_datetime.year
    reference_month_ganzhi = reference_facts.month_gz.text
    start_solar = yun.getStartSolar()
    first_dayun_start = normalize_local_datetime(
        datetime(
            start_solar.getYear(),
            start_solar.getMonth(),
            start_solar.getDay(),
            start_solar.getHour(),
            start_solar.getMinute(),
            start_solar.getSecond(),
        ),
        timezone_name,
    ).local_datetime

    def add_years(source: datetime, years: int) -> datetime:
        try:
            return source.replace(year=source.year + years)
        except ValueError:
            return source.replace(year=source.year + years, day=28)

    def flow_boundaries(year: int) -> tuple[datetime, datetime, list[datetime]]:
        terms = solar_terms_for_years(range(year - 1, year + 3), value.tzinfo)
        lichun = next(
            item.local_datetime
            for item in terms
            if item.index == 3 and item.local_datetime.year == year
        )
        next_lichun = next(
            item.local_datetime
            for item in terms
            if item.index == 3 and item.local_datetime.year == year + 1
        )
        month_starts = [
            item.local_datetime
            for item in terms
            if item.index in JIE_MONTH_BRANCH
            and lichun <= item.local_datetime < next_lichun
        ]
        month_starts.sort()
        return lichun, next_lichun, [*month_starts, next_lichun]

    natal_relations = set(
        _stem_relations(natal_pillars) + _branch_relations(natal_pillars)
    )
    cycles = []
    kline_cycles = []
    expand_next_cycle = False
    current_year_payload: Optional[Dict[str, Any]] = None
    current_month_payload: Optional[Dict[str, Any]] = None
    # Keep a stable contemporary minimum, then extend only as far as needed for
    # the reference age plus the following cycle. The cap covers living users
    # without allowing an extreme historical input to create an unbounded API
    # payload.
    reference_age_years = max(0, reference.year - value.year)
    cycle_count = max(13, min(20, reference_age_years // 10 + 3))
    for cycle in yun.getDaYun(cycle_count):
        cycle_index = cycle.getIndex()
        cycle_start = (
            value
            if cycle_index == 0
            else add_years(first_dayun_start, (cycle_index - 1) * 10)
        )
        cycle_end = (
            first_dayun_start
            if cycle_index == 0
            else add_years(first_dayun_start, cycle_index * 10)
        )
        cycle_is_current = cycle_start <= reference < cycle_end
        cycle_ganzhi = cycle.getGanZhi()
        cycle_pillar = (
            {
                "label": "大运",
                "stem": cycle_ganzhi[0],
                "branch": cycle_ganzhi[1],
                "text": cycle_ganzhi,
            }
            if cycle_ganzhi
            else None
        )
        cycle_context = [*natal_pillars, *([cycle_pillar] if cycle_pillar else [])]
        cycle_ten_god = (
            _ten_god(natal_pillars[2]["stem"], cycle_ganzhi[0]) if cycle_ganzhi else "—"
        )
        cycle_hits = (
            [
                hit
                for hit in evaluate_shensha(cycle_context)
                if "大运" in hit["pillar_labels"]
            ]
            if cycle_pillar
            else []
        )
        cycle_relations = _stem_relations(cycle_context) + _branch_relations(
            cycle_context
        )
        cycle_structured_relations = [
            relation
            for relation in structured_relations(cycle_context)
            if any(
                item.get("pillar") == "大运"
                for item in relation.get("participants", ())
            )
        ]
        years = []
        is_default_next_cycle = expand_next_cycle
        should_expand_cycle = (
            include_period_details
            or cycle_is_current
            or is_default_next_cycle
            or cycle_index == period_cycle_index
        )
        expand_next_cycle = cycle_is_current
        for liu_nian in cycle.getLiuNian():
            year_start, year_end, month_boundaries = flow_boundaries(liu_nian.getYear())
            year_is_current = cycle_is_current and year_start <= reference < year_end
            year_ganzhi = liu_nian.getGanZhi()
            year_pillar = {
                "label": "流年",
                "stem": year_ganzhi[0],
                "branch": year_ganzhi[1],
                "text": year_ganzhi,
            }
            year_context = [*cycle_context, year_pillar]
            year_hits = [
                hit
                for hit in evaluate_shensha(year_context)
                if "流年" in hit["pillar_labels"]
            ]
            year_relations = _stem_relations(year_context) + _branch_relations(
                year_context
            )
            year_structured_relations = [
                relation
                for relation in structured_relations(year_context)
                if any(
                    item.get("pillar") == "流年"
                    for item in relation.get("participants", ())
                )
            ]
            year_ten_god = _ten_god(natal_pillars[2]["stem"], year_ganzhi[0])
            months = []
            for liu_yue in liu_nian.getLiuYue():
                month_index = liu_yue.getIndex()
                month_start = month_boundaries[month_index]
                month_end = month_boundaries[month_index + 1]
                month_is_current = (
                    year_is_current and month_start <= reference < month_end
                )
                month_ganzhi = liu_yue.getGanZhi()
                month_pillar = {
                    "label": "流月",
                    "stem": month_ganzhi[0],
                    "branch": month_ganzhi[1],
                    "text": month_ganzhi,
                }
                month_context = [*year_context, month_pillar]
                month_hits = [
                    hit
                    for hit in evaluate_shensha(month_context)
                    if "流月" in hit["pillar_labels"]
                ]
                month_relations = _stem_relations(month_context) + _branch_relations(
                    month_context
                )
                month_structured_relations = [
                    relation
                    for relation in structured_relations(month_context)
                    if any(
                        item.get("pillar") == "流月"
                        for item in relation.get("participants", ())
                    )
                ]
                month_ten_god = _ten_god(natal_pillars[2]["stem"], month_ganzhi[0])
                month_payload = {
                    "layer": "liuyue",
                    "index": liu_yue.getIndex(),
                    "label": f"{str(liu_yue.getMonthInChinese()).lstrip('0123456789')}月",
                    "ganzhi": month_ganzhi,
                    "ten_god": month_ten_god,
                    "xunkong": liu_yue.getXunKong(),
                    "start_timestamp": month_start.isoformat(),
                    "end_timestamp": month_end.isoformat(),
                    "is_current": month_is_current,
                    "shen_sha": [hit["name"] for hit in month_hits],
                    "relations": [
                        relation
                        for relation in month_relations
                        if relation not in set(year_relations)
                    ],
                    "theme_activations": _period_theme_activations(
                        period_label="流月",
                        ten_god=month_ten_god,
                        gender=gender,
                        shensha_hits=month_hits,
                        relations=month_structured_relations,
                    ),
                }
                months.append(month_payload)
                if month_is_current and month_ganzhi == reference_month_ganzhi:
                    current_month_payload = month_payload
            year_payload = {
                "layer": "liunian",
                "index": liu_nian.getIndex(),
                "year": liu_nian.getYear(),
                "age": liu_nian.getAge(),
                "label": str(liu_nian.getYear()),
                "ganzhi": year_ganzhi,
                "ten_god": year_ten_god,
                "xunkong": liu_nian.getXunKong(),
                "start_timestamp": year_start.isoformat(),
                "end_timestamp": year_end.isoformat(),
                "is_current": year_is_current,
                "shen_sha": [hit["name"] for hit in year_hits],
                "relations": [
                    relation
                    for relation in year_relations
                    if relation not in set(cycle_relations)
                ],
                "theme_activations": _period_theme_activations(
                    period_label="流年",
                    ten_god=year_ten_god,
                    gender=gender,
                    shensha_hits=year_hits,
                    relations=year_structured_relations,
                ),
                "months": months,
            }
            years.append(year_payload)
            if year_is_current and liu_nian.getYear() == reference_year:
                current_year_payload = {
                    key: value for key, value in year_payload.items() if key != "months"
                }
        cycle_payload = {
            "index": cycle_index,
            "label": "童限" if cycle_index == 0 else cycle_ganzhi,
            "ganzhi": cycle_ganzhi,
            "start_year": cycle.getStartYear(),
            "end_year": cycle.getEndYear(),
            "start_age": cycle.getStartAge(),
            "end_age": cycle.getEndAge(),
            "start_timestamp": cycle_start.isoformat(),
            "end_timestamp": cycle_end.isoformat(),
            "is_current": cycle_is_current,
            "ten_god": cycle_ten_god,
            "shen_sha": [hit["name"] for hit in cycle_hits],
            "relations": [
                relation
                for relation in cycle_relations
                if relation not in natal_relations
            ],
            "theme_activations": _period_theme_activations(
                period_label="大运",
                ten_god=cycle_ten_god,
                gender=gender,
                shensha_hits=cycle_hits,
                relations=cycle_structured_relations,
            ),
            "years": years,
        }
        kline_cycles.append(cycle_payload)
        cycles.append(
            cycle_payload if should_expand_cycle else {**cycle_payload, "years": []}
        )
    return {
        "status": "available",
        "algorithm": algorithm,
        "algorithm_note": "sect2 按分钟精算；sect1 按日数与时辰折算。"
        if algorithm == "sect2"
        else "sect1 按日数与时辰折算。",
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
        # Consumed and removed before API serialization. It keeps the personal
        # baseline fixed across the compact and full-life views.
        "_kline_cycles": kline_cycles,
        "current": {
            "as_of": reference.isoformat(),
            "year": current_year_payload,
            "month": current_month_payload,
        },
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
    fold_choice: Optional[str] = None,
    reference_timestamp: Optional[datetime] = None,
    include_period_details: bool = True,
    period_cycle_index: Optional[int] = None,
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
        fold_choice=fold_choice,
    )
    if hour_uncertain:
        return _build_uncertain_metaphysics_chart(
            local,
            calendar_input=calendar_input,
            timezone_name=timezone_name,
            longitude=longitude,
            use_true_solar_time=use_true_solar_time,
            day_boundary=day_boundary,
            gender=gender,
            birth_place=birth_place,
            dayun_algorithm=dayun_algorithm,
        )
    effective_local = local
    calculation_time, correction_minutes = (
        _true_solar_time(effective_local, longitude)
        if use_true_solar_time
        else (effective_local, 0.0)
    )
    pillar_date = calculation_time
    if day_boundary == "forward" and calculation_time.hour >= 23:
        pillar_date = calculation_time + timedelta(days=1)

    calendar_facts = calculate_calendar_facts(
        calculation_time,
        timezone_name=timezone_name,
        day_boundary=day_boundary,
    )
    if calendar_facts.quality["status"] == "conflict":
        raise ValueError("这个出生时间正处于换柱敏感区，请确认出生时间后继续。")
    solar_day = sxtwl.fromSolar(pillar_date.year, pillar_date.month, pillar_date.day)
    year_gz = calendar_facts.year_gz
    month_gz = calendar_facts.month_gz
    day_gz = calendar_facts.day_gz
    hour_gz = calendar_facts.hour_gz
    day_stem = STEMS[day_gz.tg]
    pillars = [
        _pillar("年", year_gz, day_stem),
        _pillar("月", month_gz, day_stem),
        _pillar("日", day_gz, day_stem),
        _pillar("时", hour_gz, day_stem),
    ]
    hour_candidates: list[Dict[str, str]] = []
    direct_elements: Iterable[str] = (
        value
        for pillar in pillars
        for value in (pillar["stem_element"], pillar["branch_element"])
        if value in ELEMENTS
    )
    counts = Counter(direct_elements)
    previous_term = serialize_solar_term(calendar_facts.previous_jie, calculation_time)
    next_term = serialize_solar_term(calendar_facts.next_jie, calculation_time)
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
        natal_pillars=pillars,
        timezone_name=timezone_name,
        reference_timestamp=reference_timestamp,
        include_period_details=include_period_details,
        period_cycle_index=period_cycle_index,
    )
    kline_cycles = dayun.pop("_kline_cycles", dayun.get("cycles", []))
    raw_shen_sha = evaluate_shensha(pillars)
    fact_graph = build_bazi_fact_graph(pillars)
    structure = build_structure_profile(
        pillars,
        gender=gender,
        shensha_hits=raw_shen_sha,
        seasonal_status=_seasonal_status(month_branch),
        fact_graph=fact_graph,
    )
    patterns = assess_patterns(pillars, structure, fact_graph=fact_graph)
    structure["patterns"] = patterns
    shensha_effects = evaluate_shensha_effects(raw_shen_sha, pillars, structure)
    shen_sha = shensha_effects["hits"]
    consumer_features = consumer_feature_records(patterns, shensha_effects)
    statistics = _statistics_or_unavailable(
        shen_sha,
        day_boundary,
        theme_profiles=structure["theme_profiles"],
        gender=gender,
        day_master=day_stem,
        month_command=month_branch,
        consumer_feature_ids=[item["id"] for item in consumer_features],
    )
    theme_profiles = statistics.get("theme_profiles") or structure["theme_profiles"]
    structure["theme_profiles"] = theme_profiles
    rarity_by_feature = {
        str(item.get("feature_id", "")): float(item.get("percentage", 0) or 0)
        for item in statistics.get("rarity_metrics", ())
        if item.get("status") in {"observed", "zero"}
    }
    for hit in shen_sha:
        feature_id = str(hit.get("feature_id", ""))
        if feature_id in rarity_by_feature:
            hit["rarity_percentage"] = rarity_by_feature[feature_id]
    structure["shensha_combinations"] = shensha_effects["combinations"]
    synthesis = structure.get(
        "synthesis", {"method": "modern-ziping-common-v1", "conclusions": []}
    )
    profiles_by_theme = {
        str(profile.get("theme", "")): profile for profile in theme_profiles
    }
    for conclusion in synthesis.get("conclusions", []):
        comparisons = profiles_by_theme.get(str(conclusion.get("theme", "")), {}).get(
            "comparisons", []
        )
        supported = [
            item
            for item in comparisons
            if item.get("status") in {"observed", "zero"} and item.get("display_label")
        ]
        if not supported:
            continue
        display_priority = {
            "exact_tail": 0,
            "directional": 1,
            "reference_zero": 2,
            "common_value": 3,
            "incidence": 4,
        }
        most_distinctive = min(
            supported,
            key=lambda item: (
                display_priority.get(str(item.get("display_mode", "")), 5),
                float(item.get("tail_percentage", 101) or 101),
                str(item.get("metric_id", "")),
            ),
        )
        conclusion["distribution_context"] = str(most_distinctive["display_label"])
    consumer = build_bazi_consumer_profile(
        pillars=pillars,
        structure=structure,
        patterns=patterns,
        shensha_effects=shensha_effects,
        cycles=dayun.get("cycles", []),
        consumer_distributions=statistics.get("consumer_distributions"),
        consumer_feature_metrics=statistics.get("consumer_feature_metrics", ()),
        kline_cycles=kline_cycles,
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
        "stem_relations": _stem_relations(pillars),
        "branch_relations": _branch_relations(pillars),
        "element_season_status": _seasonal_status(month_branch),
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
        "derived_schema_version": 7,
        "calculation_quality": calendar_facts.quality,
        "boundary_flags": calendar_facts.boundary_flags,
        "rules_version": RULES_VERSION,
        "rule_versions": bazi_rule_versions(),
        "shen_sha": shen_sha,
        "structure": structure,
        "theme_profiles": theme_profiles,
        "synthesis": synthesis,
        "statistics": statistics,
        "period_layers": {
            "dayun": dayun.get("cycles", []),
            "current": dayun.get(
                "current",
                {
                    "as_of": datetime.now(calculation_time.tzinfo).isoformat(),
                    "year": None,
                    "month": None,
                },
            ),
            "engine": "lunar_python 1.4.8",
        },
        "consumer": consumer,
        "previous_solar_term": previous_term,
        "next_solar_term": next_term,
        "birth_profile": {
            **calendar_input,
            "birth_place": birth_place or "",
            "gender": gender,
            "hour_uncertain": hour_uncertain,
            "hour_candidates": hour_candidates,
            "dayun": dayun,
            "period_query": {
                "timestamp": local.isoformat(),
                "timezone": timezone_name,
                "longitude": longitude,
                "use_true_solar_time": use_true_solar_time,
                "day_boundary": day_boundary,
                "calendar_type": "solar",
                "is_leap_month": False,
                "gender": gender,
                "birth_place": birth_place,
                "hour_uncertain": False,
                "dayun_algorithm": dayun_algorithm,
                "reference_timestamp": reference_timestamp.isoformat()
                if reference_timestamp
                else None,
                "include_period_details": False,
            },
            "engines": {
                "calendar": "sxtwl 2.0.7",
                "birth_calendar_and_dayun": "lunar_python 1.4.8",
            },
        },
    }
