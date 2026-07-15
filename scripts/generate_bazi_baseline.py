from __future__ import annotations

import argparse
import json
from bisect import bisect_right
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import sxtwl

from iching.core.bazi_structure import METRIC_DEFINITIONS, THEME_ORDER, build_structure_profile
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
    BASELINE_SCHEMA_VERSION,
    bazi_rules_registry_hash,
    feature_catalog_hash,
    metric_catalog_hash,
    payload_hash,
)
from iching.core.metaphysics_consumer import (
    CONSUMER_RULES_VERSION,
    THEME_ORDER as CONSUMER_THEME_ORDER,
    consumer_feature_records,
    score_bazi_consumer_themes,
)
from iching.core.shensha import RULE_BY_ID, RULES_VERSION, evaluate_shensha
from iching.core.shensha_effects import evaluate_shensha_effects


DEFAULT_OUTPUT = Path(__file__).parents[1] / "src" / "iching" / "core" / "data"
BASELINE_VERSION = "calendar-1924-2044-g3"
BASELINE_GENERATION_VERSION = 3


def _config_id(day_boundary: str) -> str:
    return f"bazi-canonical-calendar-1-asia-shanghai-{day_boundary}"


def _feature_catalog() -> list[str]:
    return sorted(
        f"bazi.shensha.{rule.rule_id}"
        for rule in RULE_BY_ID.values()
        if rule.method != "fixed_none"
    )


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
        "weighted_unit": "minute",
        "theme_comparison_method": "transparent_metric_distributions",
        "consumer_rules_version": CONSUMER_RULES_VERSION,
        "consumer_score_dimensions": ["overall", *CONSUMER_THEME_ORDER],
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
    month_gz = GanZhiIndex((yin_month_stem + month_offset) % 10, BRANCHES.index(month_branch))
    pillar_date = value + timedelta(days=1) if day_boundary == "forward" and value.hour >= 23 else value
    solar_day = sxtwl.fromSolar(pillar_date.year, pillar_date.month, pillar_date.day)
    raw_day = solar_day.getDayGZ()
    hour = 0 if day_boundary == "forward" and value.hour >= 23 else value.hour
    raw_hour = solar_day.getHourGZ(hour)
    day_gz = GanZhiIndex(int(raw_day.tg), int(raw_day.dz))
    hour_gz = GanZhiIndex(int(raw_hour.tg), int(raw_hour.dz))
    gz_values = (year_gz, month_gz, day_gz, hour_gz)
    day_stem = STEMS[day_gz.tg]
    return [_pillar(label, gz, day_stem) for label, gz in zip(("年", "月", "日", "时"), gz_values)]


def _pillars_from_state_key(state_key: tuple[str, ...]) -> list[dict[str, Any]]:
    day_stem = state_key[2][0]
    values = [GanZhiIndex(STEMS.index(text[0]), BRANCHES.index(text[1])) for text in state_key]
    return [_pillar(label, value, day_stem) for label, value in zip(("年", "月", "日", "时"), values)]


def compact_score_histogram(histogram: Counter[str]) -> str:
    """Encode a small integer-score histogram without tens of thousands of JSON rows."""
    entries = []
    for score, seconds in sorted(histogram.items(), key=lambda item: int(item[0])):
        weight = f"{seconds / 60:.6f}".rstrip("0").rstrip(".")
        entries.append(f"{score}:{weight}")
    return ",".join(entries)


def generate(day_boundary: str) -> dict:
    zone = ZoneInfo("Asia/Shanghai")
    start = _lichun(1924, zone)
    end = _lichun(2044, zone)
    events = _events(start, end, zone, day_boundary)
    all_terms = solar_terms_for_years(range(start.year - 2, end.year + 2), zone)
    jie_terms = [item for item in all_terms if item.index in JIE_MONTH_BRANCH]
    jie_timestamps = [item.instant_utc.timestamp() for item in jie_terms]
    lichun_terms = [item for item in all_terms if item.index == 3]
    lichun_timestamps = [item.instant_utc.timestamp() for item in lichun_terms]
    feature_weights: Counter[str] = Counter()
    profile_genders = {"male": "male", "female": "female", "neutral": None}
    theme_metric_weights_by_gender = {
        gender: {theme: {} for theme in THEME_ORDER}
        for gender in profile_genders
    }
    score_dimensions = ("overall", *CONSUMER_THEME_ORDER)
    consumer_global = {
        gender: {dimension: Counter() for dimension in score_dimensions}
        for gender in profile_genders
    }
    consumer_cohorts: dict[str, dict[str, dict[str, Counter[str]]]] = {}
    consumer_feature_weights: Counter[str] = Counter()
    consumer_feature_catalog: dict[str, dict[str, str]] = {}
    # Aggregate identical four-pillar states before running the expensive
    # structure engines. This keeps the exhaustive 120-year semantics while
    # retaining only a compact tuple->duration map in memory.
    state_weights: Counter[tuple[str, ...]] = Counter()
    for left, right in zip(events, events[1:]):
        seconds = right.timestamp() - left.timestamp()
        if seconds <= 0:
            continue
        midpoint = datetime.fromtimestamp((left.timestamp() + right.timestamp()) / 2, zone)
        pillars = _baseline_pillars(
            midpoint,
            day_boundary,
            jie_terms=jie_terms,
            jie_timestamps=jie_timestamps,
            lichun_terms=lichun_terms,
            lichun_timestamps=lichun_timestamps,
        )
        state_key = tuple(pillar["text"] for pillar in pillars)
        state_weights[state_key] += seconds

    total_seconds = sum(state_weights.values())
    for state_key, seconds in state_weights.items():
        pillars = _pillars_from_state_key(state_key)
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
        structures = {
            gender: build_structure_profile(
                pillars,
                gender=calculation_gender,
                shensha_hits=hits,
                seasonal_status=seasonal_status,
            )
            for gender, calculation_gender in profile_genders.items()
        }
        patterns = assess_patterns(pillars, structures["neutral"])
        structures["neutral"]["patterns"] = patterns
        effects = evaluate_shensha_effects(evaluated_hits, pillars, structures["neutral"])
        profile_metrics = {
            gender: {
                item["theme"]: item["structure_metrics"]
                for item in structures[gender]["theme_profiles"]
            }
            for gender in profile_genders
        }
        consumer_scores = {
            gender: score_bazi_consumer_themes(
                structure=structures[gender],
                patterns=patterns,
                shensha_effects=effects,
            )
            for gender in profile_genders
        }
        for record in consumer_feature_records(patterns, effects):
            consumer_feature_weights[record["id"]] += seconds
            consumer_feature_catalog.setdefault(record["id"], record)
        for hit in hits:
            feature_weights[hit["feature_id"]] += seconds
        for gender in profile_genders:
            for theme, metrics in profile_metrics[gender].items():
                for metric in metrics:
                    histogram = theme_metric_weights_by_gender[gender][theme].setdefault(metric["metric_id"], Counter())
                    histogram[str(metric["value"])] += seconds
            cohort_key = f"{pillars[2]['stem']}-{pillars[1]['branch']}"
            cohort = consumer_cohorts.setdefault(
                cohort_key,
                {
                    cohort_gender: {dimension: Counter() for dimension in score_dimensions}
                    for cohort_gender in profile_genders
                },
            )
            for dimension in score_dimensions:
                score = str(int(consumer_scores[gender][dimension]["score"]))
                consumer_global[gender][dimension][score] += seconds
                cohort[gender][dimension][score] += seconds

    sample_weight = round(total_seconds / 60, 6)
    catalog = _feature_catalog()
    metric_catalog = [METRIC_DEFINITIONS[key] for key in sorted(METRIC_DEFINITIONS)]
    payload = {
        "schema_version": BASELINE_SCHEMA_VERSION,
        "baseline_generation_version": BASELINE_GENERATION_VERSION,
        "id": f"bazi-{BASELINE_VERSION}-{day_boundary}",
        "chart_type": "bazi",
        "kind": "calendar_sample_frequency",
        "label": "1924立春—2044立春历法样本",
        "start": start.isoformat(),
        "end": end.isoformat(),
        "timezone": "Asia/Shanghai",
        "day_boundary": day_boundary,
        "config_id": _config_id(day_boundary),
        "engine": "canonical-calendar-1 (sxtwl 2.0.7 ephemeris)",
        "rules_version": RULES_VERSION,
        "rules_registry_hash": bazi_rules_registry_hash(),
        "feature_catalog": catalog,
        "feature_catalog_hash": feature_catalog_hash(catalog),
        "metric_catalog": metric_catalog,
        "metric_catalog_hash": metric_catalog_hash(metric_catalog),
        "unique_state_count": len(state_weights),
        "sample_unit": "minute",
        "weighted_unit": "minute",
        "sample_weight": sample_weight,
        "method": "按四柱变化边界分段穷举，并按每段实际持续分钟数加权。",
        "features": {
            feature_id: {"hit_weight": round(feature_weights.get(feature_id, 0.0) / 60, 6)}
            for feature_id in catalog
        },
        "theme_comparison_method": "transparent_metric_distributions",
        "theme_metric_weights_by_gender": {
            gender: {
                theme: {
                    metric_id: {value: round(seconds / 60, 6) for value, seconds in sorted(histogram.items(), key=lambda item: int(item[0]))}
                    for metric_id, histogram in metrics.items()
                }
                for theme, metrics in themes.items()
            }
            for gender, themes in theme_metric_weights_by_gender.items()
        },
        "consumer_score_distributions": {
            "rules_version": CONSUMER_RULES_VERSION,
            "weighted_unit": "minute",
            "dimensions": list(score_dimensions),
            "method": "weighted_empirical_integer_score_histograms",
            "encoding": "comma_separated_score:minute_weight",
            "global": {
                gender: {
                    dimension: compact_score_histogram(histogram)
                    for dimension, histogram in dimensions.items()
                }
                for gender, dimensions in consumer_global.items()
            },
            "cohorts": {
                cohort_key: {
                    gender: {
                        dimension: compact_score_histogram(histogram)
                        for dimension, histogram in dimensions.items()
                    }
                    for gender, dimensions in genders.items()
                }
                for cohort_key, genders in sorted(consumer_cohorts.items())
            },
        },
        "consumer_features": {
            "rules_version": CONSUMER_RULES_VERSION,
            "weighted_unit": "minute",
            "method": "weighted_empirical_feature_incidence",
            "catalog": [consumer_feature_catalog[key] for key in sorted(consumer_feature_catalog)],
            "hit_weights": {
                key: round(consumer_feature_weights[key] / 60, 6)
                for key in sorted(consumer_feature_catalog)
            },
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
