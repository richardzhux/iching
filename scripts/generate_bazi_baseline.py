from __future__ import annotations

import argparse
import json
import os
from bisect import bisect_right
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable, Mapping
from zoneinfo import ZoneInfo

import sxtwl

from iching.core.bazi_rules.registry import load_packaged_shen_registry
from iching.core.bazi_rules.engine import evaluate_pattern_set
from iching.core.bazi_rules.fact_graph import (
    build_bazi_fact_graph,
    build_rule_evaluation_context,
)
from iching.core.bazi_structure import (
    METRIC_DEFINITIONS,
    THEME_ORDER,
    build_structure_profile,
)
from iching.core.bazi_patterns import assess_patterns
from iching.core.calendar_engine import (
    BRANCHES,
    JIE_MONTH_BRANCH,
    GanZhiIndex,
    calculate_calendar_facts,
    solar_term_datetime,
    solar_terms_for_years,
)
from iching.core.metaphysics import JIE_QI_NAMES, STEMS, _pillar, _seasonal_status
from iching.core.metaphysics_statistics import (
    BAZI_CONSUMER_FEATURE_METHOD,
    BAZI_PATTERN_FEATURE_SEMANTICS,
    BASELINE_SCHEMA_VERSION,
    bazi_rules_registry_hash,
    feature_catalog_hash,
    metric_catalog_hash,
    payload_hash,
)
from iching.core.metaphysics_consumer import (
    CONSUMER_RULES_VERSION,
    consumer_feature_records,
)
from iching.core.shensha import RULE_BY_ID, RULES_VERSION, evaluate_shensha
from iching.core.shensha_effects import evaluate_shensha_effects


DEFAULT_OUTPUT = Path(__file__).parents[1] / "src" / "iching" / "core" / "data"
BASELINE_VERSION = "calendar-1950-2030-g5"
BASELINE_GENERATION_VERSION = 5


def _config_id(day_boundary: str) -> str:
    return f"bazi-canonical-calendar-1-asia-shanghai-{day_boundary}"


def _feature_catalog() -> list[str]:
    return sorted(
        f"bazi.shensha.{rule.rule_id}"
        for rule in RULE_BY_ID.values()
        if rule.method != "fixed_none"
    )


def _pattern_bundle_identity() -> dict[str, str]:
    registry = load_packaged_shen_registry()
    return {
        "pattern_bundle_id": registry.bundle_id,
        "pattern_bundle_digest": registry.bundle_digest,
    }


def _canonical_pattern_authority() -> dict[str, str]:
    return {
        **_pattern_bundle_identity(),
        "feature_semantics": BAZI_PATTERN_FEATURE_SEMANTICS,
    }


def _canonical_consumer_feature_metadata() -> dict[str, object]:
    return {
        "rules_version": CONSUMER_RULES_VERSION,
        "weighted_unit": "minute",
        "method": BAZI_CONSUMER_FEATURE_METHOD,
        "pattern_authority": _canonical_pattern_authority(),
    }


def generator_metadata() -> dict[str, object]:
    catalog = _feature_catalog()
    metric_catalog = [METRIC_DEFINITIONS[key] for key in sorted(METRIC_DEFINITIONS)]
    return {
        "schema_version": BASELINE_SCHEMA_VERSION,
        "baseline_generation_version": BASELINE_GENERATION_VERSION,
        "config_ids": {mode: _config_id(mode) for mode in ("current", "forward")},
        "feature_catalog_hash": feature_catalog_hash(catalog),
        "metric_catalog_hash": metric_catalog_hash(metric_catalog),
        "rules_registry_hash": bazi_rules_registry_hash(),
        **_pattern_bundle_identity(),
        "weighted_unit": "minute",
        "theme_comparison_method": "transparent_metric_distributions",
        "consumer_rules_version": CONSUMER_RULES_VERSION,
        "consumer_feature_method": BAZI_CONSUMER_FEATURE_METHOD,
        "pattern_authority": _canonical_pattern_authority(),
    }


def _jieqi_datetime(item, zone: ZoneInfo) -> datetime:
    return solar_term_datetime(item, zone)


def _lichun(year: int, zone: ZoneInfo) -> datetime:
    for item in sxtwl.getJieQiByYear(year):
        if JIE_QI_NAMES[int(item.jqIndex)] == "立春":
            value = _jieqi_datetime(item, zone)
            if value.year == year:
                return value
    raise RuntimeError(f"Missing Li Chun for {year}")


def _events(
    start: datetime, end: datetime, zone: ZoneInfo, day_boundary: str
) -> list[datetime]:
    values = {start, end}
    day = start.replace(hour=0, minute=0, second=0, microsecond=0)
    boundary_hours = (
        (0, 1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23)
        if day_boundary == "current"
        else (1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23)
    )
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
    facts = calculate_calendar_facts(
        value,
        timezone_name="Asia/Shanghai",
        day_boundary=day_boundary,
        crosscheck=False,
    )
    gz_values = (facts.year_gz, facts.month_gz, facts.day_gz, facts.hour_gz)
    labels = ("年", "月", "日", "时")
    day_stem = STEMS[gz_values[2].tg]
    return [_pillar(label, gz, day_stem) for label, gz in zip(labels, gz_values)]


def _baseline_pillars(
    value: datetime,
    day_boundary: str,
    *,
    jie_terms: list[Any],
    jie_timestamps: list[float],
    lichun_terms: list[Any],
    lichun_timestamps: list[float],
) -> list[dict[str, Any]]:
    """Fast canonical path for the already segmented baseline loop."""
    stamp = value.timestamp()
    previous_jie = jie_terms[bisect_right(jie_timestamps, stamp) - 1]
    previous_lichun = lichun_terms[bisect_right(lichun_timestamps, stamp) - 1]
    year_number = previous_lichun.local_datetime.year
    year_gz = GanZhiIndex((year_number - 4) % 10, (year_number - 4) % 12)
    month_branch = JIE_MONTH_BRANCH[previous_jie.index]
    month_offset = (BRANCHES.index(month_branch) - BRANCHES.index("寅")) % 12
    yin_month_stem = ((year_gz.tg % 5) * 2 + 2) % 10
    month_gz = GanZhiIndex(
        (yin_month_stem + month_offset) % 10, BRANCHES.index(month_branch)
    )
    pillar_date = (
        value + timedelta(days=1)
        if day_boundary == "forward" and value.hour >= 23
        else value
    )
    solar_day = sxtwl.fromSolar(pillar_date.year, pillar_date.month, pillar_date.day)
    raw_day = solar_day.getDayGZ()
    hour = 0 if day_boundary == "forward" and value.hour >= 23 else value.hour
    raw_hour = solar_day.getHourGZ(hour)
    day_gz = GanZhiIndex(int(raw_day.tg), int(raw_day.dz))
    hour_gz = GanZhiIndex(int(raw_hour.tg), int(raw_hour.dz))
    gz_values = (year_gz, month_gz, day_gz, hour_gz)
    day_stem = STEMS[day_gz.tg]
    return [
        _pillar(label, gz, day_stem)
        for label, gz in zip(("年", "月", "日", "时"), gz_values)
    ]


def _pillars_from_state_key(state_key: tuple[str, ...]) -> list[dict[str, Any]]:
    day_stem = state_key[2][0]
    values = [
        GanZhiIndex(STEMS.index(text[0]), BRANCHES.index(text[1])) for text in state_key
    ]
    return [
        _pillar(label, value, day_stem)
        for label, value in zip(("年", "月", "日", "时"), values)
    ]


def _calendar_state_weights(
    day_boundary: str,
) -> tuple[datetime, datetime, Counter[tuple[str, ...]]]:
    """Return the fixed 80-year four-pillar states and duration weights."""

    zone = ZoneInfo("Asia/Shanghai")
    start = datetime(1950, 1, 1, tzinfo=zone)
    end = datetime(2030, 1, 1, tzinfo=zone)
    events = _events(start, end, zone, day_boundary)
    all_terms = solar_terms_for_years(range(start.year - 2, end.year + 2), zone)
    jie_terms = [item for item in all_terms if item.index in JIE_MONTH_BRANCH]
    jie_timestamps = [item.instant_utc.timestamp() for item in jie_terms]
    lichun_terms = [item for item in all_terms if item.index == 3]
    lichun_timestamps = [item.instant_utc.timestamp() for item in lichun_terms]
    state_weights: Counter[tuple[str, ...]] = Counter()
    for left, right in zip(events, events[1:]):
        seconds = right.timestamp() - left.timestamp()
        if seconds <= 0:
            continue
        midpoint = datetime.fromtimestamp(
            (left.timestamp() + right.timestamp()) / 2,
            zone,
        )
        pillars = _baseline_pillars(
            midpoint,
            day_boundary,
            jie_terms=jie_terms,
            jie_timestamps=jie_timestamps,
            lichun_terms=lichun_terms,
            lichun_timestamps=lichun_timestamps,
        )
        state_weights[tuple(pillar["text"] for pillar in pillars)] += seconds
    return start, end, state_weights



def _empty_totals():
    return {"features": Counter(), "consumer_weights": Counter(), "catalog": {},
            "metrics": {gender: {theme: {} for theme in THEME_ORDER}
                        for gender in ("male", "female", "neutral")}}


def _evaluate_batch(items):
    totals = {mode: _empty_totals() for mode in ("forward", "current")}
    registry = load_packaged_shen_registry()
    for state_key, weights in items:
        pillars = _pillars_from_state_key(state_key)
        hits = evaluate_shensha(pillars, include_extended=True)
        profiles = {gender: build_structure_profile(
            pillars, gender=None if gender == "neutral" else gender,
            shensha_hits=hits, seasonal_status=_seasonal_status(pillars[1]["branch"]),
        ) for gender in ("male", "female", "neutral")}
        graph = build_bazi_fact_graph(pillars)
        pattern_set = evaluate_pattern_set(build_rule_evaluation_context(graph), registry).as_dict()
        patterns = {"source_backed_authority": {"authoritative": True, "pattern_set": pattern_set}}
        # The effects function reads structural facts, never legacy pattern grades.
        effects = evaluate_shensha_effects(hits, pillars, profiles["neutral"])
        records = consumer_feature_records(patterns, effects)
        for mode, seconds in weights.items():
            target = totals[mode]
            for feature_id in {hit["feature_id"] for hit in hits}:
                target["features"][feature_id] += seconds
            for record in records:
                target["consumer_weights"][record["id"]] += seconds
                target["catalog"][record["id"]] = record
            for gender, profile in profiles.items():
                for theme in profile["theme_profiles"]:
                    for metric in theme["structure_metrics"]:
                        histogram = target["metrics"][gender][theme["theme"]].setdefault(metric["metric_id"], Counter())
                        histogram[str(metric["value"])] += seconds
    return totals


def _merge(target, incoming):
    target["features"].update(incoming["features"])
    target["consumer_weights"].update(incoming["consumer_weights"])
    target["catalog"].update(incoming["catalog"])
    for gender, themes in incoming["metrics"].items():
        for theme, metrics in themes.items():
            for key, histogram in metrics.items():
                target["metrics"][gender][theme].setdefault(key, Counter()).update(histogram)


def _payload(mode, start, end, states, totals):
    catalog = _feature_catalog()
    metric_catalog = [METRIC_DEFINITIONS[key] for key in sorted(METRIC_DEFINITIONS)]
    result = {
        "schema_version": BASELINE_SCHEMA_VERSION,
        "baseline_generation_version": BASELINE_GENERATION_VERSION,
        "id": f"bazi-{BASELINE_VERSION}-{mode}", "chart_type": "bazi",
        "kind": "calendar_sample_frequency", "label": "1950—2029 年固定历法参考（80 年）",
        "start": start.isoformat(), "end": end.isoformat(), "interval_semantics": "[start, end)",
        "timezone": "Asia/Shanghai", "day_boundary": mode, "config_id": _config_id(mode),
        "engine": "canonical-calendar-1 (sxtwl 2.0.7 ephemeris)",
        "rules_version": RULES_VERSION, "rules_registry_hash": bazi_rules_registry_hash(),
        **_pattern_bundle_identity(), "feature_catalog": catalog,
        "feature_catalog_hash": feature_catalog_hash(catalog),
        "metric_catalog": metric_catalog, "metric_catalog_hash": metric_catalog_hash(metric_catalog),
        "unique_state_count": len(states), "sample_unit": "minute", "weighted_unit": "minute",
        "sample_weight": round(sum(states.values()) / 60, 6),
        "method": "1950-01-01 至 2030-01-01，不含终点；四柱变化边界分段穷举，按实际持续分钟加权。非人口出生分布。",
        "features": {key: {"hit_weight": round(totals["features"].get(key, 0) / 60, 6)} for key in catalog},
        "theme_comparison_method": "transparent_metric_distributions",
        "theme_metric_weights_by_gender": {gender: {theme: {key: {value: round(weight/60, 6) for value, weight in sorted(hist.items(), key=lambda x: int(x[0]))} for key, hist in metrics.items()} for theme, metrics in themes.items()} for gender, themes in totals["metrics"].items()},
        "consumer_features": {**_canonical_consumer_feature_metadata(),
            "catalog": [totals["catalog"][key] for key in sorted(totals["catalog"])],
            "hit_weights": {key: round(weight / 60, 6) for key, weight in sorted(totals["consumer_weights"].items())}},
    }
    result["hash"] = payload_hash(result)
    return result


def main():
    parser = argparse.ArgumentParser(description="Generate both fixed 80-year BaZi references using identical live rules.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--workers", type=int, default=min(6, os.cpu_count() or 1))
    parser.add_argument("--metadata", action="store_true")
    args = parser.parse_args()
    if args.metadata:
        print(json.dumps(generator_metadata(), ensure_ascii=False)); return
    calendars = {mode: _calendar_state_weights(mode) for mode in ("forward", "current")}
    joint = {}
    for mode, (_, _, states) in calendars.items():
        for key, seconds in states.items():
            joint.setdefault(key, {})[mode] = seconds
    items = list(joint.items())
    totals = {mode: _empty_totals() for mode in calendars}
    batches = [items[index:index+500] for index in range(0, len(items), 500)]
    print(f"Evaluating {len(items)} shared four-pillar states with {args.workers} workers", flush=True)
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for result in pool.map(_evaluate_batch, batches):
            for mode in calendars:
                _merge(totals[mode], result[mode])
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for mode, (start, end, states) in calendars.items():
        payload = _payload(mode, start, end, states, totals[mode])
        target = args.output_dir / f"{payload['id']}.json"
        temporary = target.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")
        temporary.replace(target)
        print(f"{target}: {len(states)} states; {payload['sample_weight']} minutes", flush=True)


if __name__ == "__main__":
    main()
