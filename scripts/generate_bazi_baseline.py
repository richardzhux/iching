from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import sxtwl

from iching.core.bazi_structure import THEME_POSSIBLE_FAMILIES, build_structure_profile
from iching.core.metaphysics import JIE_QI_NAMES, STEMS, _pillar, _seasonal_status
from iching.core.metaphysics_statistics import (
    BASELINE_SCHEMA_VERSION,
    bazi_rules_registry_hash,
    feature_catalog_hash,
    payload_hash,
)
from iching.core.shensha import RULE_BY_ID, RULES_VERSION, evaluate_shensha


DEFAULT_OUTPUT = Path(__file__).parents[1] / "src" / "iching" / "core" / "data"
BASELINE_VERSION = "calendar-1924-2044-v1"


def _config_id(day_boundary: str) -> str:
    return f"bazi-sxtwl-2.0.7-asia-shanghai-{day_boundary}-v1"


def _feature_catalog() -> list[str]:
    return sorted(
        f"bazi.shensha.{rule.rule_id}"
        for rule in RULE_BY_ID.values()
        if rule.method != "fixed_none"
    )


def _theme_families() -> dict[str, dict[str, object]]:
    return {
        theme: {
            "label": theme,
            "possible_family_count": possible_count,
            "measure": "distinct_active_evidence_families",
        }
        for theme, possible_count in THEME_POSSIBLE_FAMILIES.items()
    }


def generator_metadata() -> dict[str, object]:
    catalog = _feature_catalog()
    return {
        "schema_version": BASELINE_SCHEMA_VERSION,
        "config_ids": {mode: _config_id(mode) for mode in ("current", "forward")},
        "feature_catalog_hash": feature_catalog_hash(catalog),
        "rules_registry_hash": bazi_rules_registry_hash(),
        "weighted_unit": "minute",
        "theme_families": _theme_families(),
    }


def _jieqi_datetime(item, zone: ZoneInfo) -> datetime:
    value = sxtwl.JD2DD(item.jd)
    return datetime(int(value.Y), int(value.M), int(value.D), int(value.h), int(value.m), int(value.s), tzinfo=zone)


def _lichun(year: int, zone: ZoneInfo) -> datetime:
    for item in sxtwl.getJieQiByYear(year):
        if JIE_QI_NAMES[int(item.jqIndex)] == "立春":
            value = _jieqi_datetime(item, zone)
            if value.year == year:
                return value
    raise RuntimeError(f"Missing Li Chun for {year}")


def _events(start: datetime, end: datetime, zone: ZoneInfo, day_boundary: str) -> list[datetime]:
    values = {start, end}
    day = start.replace(hour=0, minute=0, second=0, microsecond=0)
    boundary_hours = (0, 1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23) if day_boundary == "current" else (1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23)
    while day <= end:
        for hour in boundary_hours:
            value = day.replace(hour=hour)
            if start < value < end:
                values.add(value)
        day += timedelta(days=1)
    for year in range(start.year - 1, end.year + 2):
        for item in sxtwl.getJieQiByYear(year):
            value = _jieqi_datetime(item, zone)
            if start < value < end:
                values.add(value)
    return sorted(values)


def _pillars(value: datetime, day_boundary: str) -> list[dict[str, Any]]:
    pillar_date = value + timedelta(days=1) if day_boundary == "forward" and value.hour >= 23 else value
    day = sxtwl.fromSolar(pillar_date.year, pillar_date.month, pillar_date.day)
    hour = 0 if day_boundary == "forward" and value.hour >= 23 else value.hour
    gz_values = (day.getYearGZ(), day.getMonthGZ(), day.getDayGZ(), day.getHourGZ(hour))
    labels = ("年", "月", "日", "时")
    day_stem = STEMS[gz_values[2].tg]
    return [_pillar(label, gz, day_stem) for label, gz in zip(labels, gz_values)]


def generate(day_boundary: str) -> dict:
    zone = ZoneInfo("Asia/Shanghai")
    start = _lichun(1924, zone)
    end = _lichun(2044, zone)
    events = _events(start, end, zone, day_boundary)
    feature_weights: Counter[str] = Counter()
    profile_genders = {"male": "male", "female": "female", "neutral": None}
    theme_histograms_by_gender = {
        gender: {theme: Counter() for theme in THEME_POSSIBLE_FAMILIES}
        for gender in profile_genders
    }
    unique_states: set[tuple[str, ...]] = set()
    state_cache: dict[tuple[str, ...], tuple[list[dict[str, Any]], dict[str, dict[str, int]]]] = {}
    total_seconds = 0.0
    for left, right in zip(events, events[1:]):
        seconds = right.timestamp() - left.timestamp()
        if seconds <= 0:
            continue
        midpoint = datetime.fromtimestamp((left.timestamp() + right.timestamp()) / 2, zone)
        pillars = _pillars(midpoint, day_boundary)
        state_key = tuple(pillar["text"] for pillar in pillars)
        unique_states.add(state_key)
        cached = state_cache.get(state_key)
        if cached is None:
            evaluated_hits = evaluate_shensha(pillars, include_extended=True)
            hits = [
                {
                    "rule_id": hit["rule_id"],
                    "feature_id": hit["feature_id"],
                    "name": hit["name"],
                    "axis": hit["axis"],
                    "level": hit["level"],
                    "topic_tags": hit["topic_tags"],
                }
                for hit in evaluated_hits
            ]
            seasonal_status = _seasonal_status(pillars[1]["branch"])
            profile_counts = {
                gender: {
                    item["theme"]: item["raw_family_count"]
                    for item in build_structure_profile(
                        pillars,
                        gender=calculation_gender,
                        shensha_hits=hits,
                        seasonal_status=seasonal_status,
                    )["theme_profiles"]
                }
                for gender, calculation_gender in profile_genders.items()
            }
            state_cache[state_key] = (hits, profile_counts)
        else:
            hits, profile_counts = cached
        total_seconds += seconds
        for hit in hits:
            feature_weights[hit["feature_id"]] += seconds
        for gender in profile_genders:
            for theme, count in profile_counts[gender].items():
                theme_histograms_by_gender[gender][theme][count] += seconds

    sample_weight = round(total_seconds / 60, 6)
    catalog = _feature_catalog()
    theme_families = _theme_families()
    payload = {
        "schema_version": BASELINE_SCHEMA_VERSION,
        "id": f"bazi-{BASELINE_VERSION}-{day_boundary}",
        "chart_type": "bazi",
        "kind": "calendar_sample_frequency",
        "label": "1924立春—2044立春历法样本",
        "start": start.isoformat(),
        "end": end.isoformat(),
        "timezone": "Asia/Shanghai",
        "day_boundary": day_boundary,
        "config_id": _config_id(day_boundary),
        "engine": "sxtwl 2.0.7",
        "rules_version": RULES_VERSION,
        "rules_registry_hash": bazi_rules_registry_hash(),
        "feature_catalog": catalog,
        "feature_catalog_hash": feature_catalog_hash(catalog),
        "unique_state_count": len(unique_states),
        "sample_unit": "minute",
        "weighted_unit": "minute",
        "sample_weight": sample_weight,
        "method": "按四柱变化边界分段穷举，并按每段实际持续分钟数加权。",
        "features": {
            feature_id: {"hit_weight": round(feature_weights.get(feature_id, 0.0) / 60, 6)}
            for feature_id in catalog
        },
        "theme_families": theme_families,
        "theme_histograms_by_gender": {
            gender: {
                theme: {str(count): round(seconds / 60, 6) for count, seconds in sorted(histogram.items())}
                for theme, histogram in histograms.items()
            }
            for gender, histograms in theme_histograms_by_gender.items()
        },
    }
    payload["hash"] = payload_hash(payload)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--metadata", action="store_true")
    parser.add_argument("--mode", choices=("forward", "current", "all"), default="all")
    args = parser.parse_args()
    if args.metadata:
        print(json.dumps(generator_metadata(), ensure_ascii=False, sort_keys=True))
        return
    args.output.mkdir(parents=True, exist_ok=True)
    modes = ("forward", "current") if args.mode == "all" else (args.mode,)
    payloads = [generate(mode) for mode in modes]
    for payload in payloads:
        path = args.output / f"{payload['id']}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        print(f"{path}: {payload['sample_weight']:.0f} minute weight, {payload['hash']}")


if __name__ == "__main__":
    main()
