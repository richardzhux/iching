from __future__ import annotations

import argparse
import json
from bisect import bisect_right
from collections import Counter
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Mapping
from zoneinfo import ZoneInfo

import sxtwl

from iching.core.bazi_rules.registry import load_packaged_shen_registry
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
    consumer_feature_records,
)
from iching.core.shensha import RULE_BY_ID, RULES_VERSION, evaluate_shensha
from iching.core.shensha_effects import evaluate_shensha_effects


DEFAULT_OUTPUT = Path(__file__).parents[1] / "src" / "iching" / "core" / "data"
BASELINE_VERSION = "calendar-1924-2044-g4"
BASELINE_GENERATION_VERSION = 4
PROMOTION_SOURCE_VERSION = "calendar-1924-2044-g3"

_RETAINED_DISTRIBUTION_KEYS = (
    "features",
    "feature_catalog",
    "theme_metric_weights_by_gender",
)


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
    }


def _validate_promotion_source(source: Mapping[str, Any], day_boundary: str) -> None:
    expected_id = f"bazi-{PROMOTION_SOURCE_VERSION}-{day_boundary}"
    if source.get("id") != expected_id:
        raise ValueError(f"Expected promotion source {expected_id}, got {source.get('id')!r}")
    if source.get("chart_type") != "bazi":
        raise ValueError("Only bazi baselines can be promoted")
    if int(source.get("schema_version", 0)) != 5:
        raise ValueError("Only schema v5 baselines can be promoted to g4")
    if int(source.get("baseline_generation_version", 0)) != 3:
        raise ValueError("Only generation g3 baselines can be promoted to g4")
    if source.get("day_boundary") != day_boundary:
        raise ValueError("Promotion source day-boundary metadata does not match its filename")
    if source.get("config_id") != _config_id(day_boundary):
        raise ValueError("Promotion source config is not the canonical calendar config")
    if source.get("hash") != payload_hash(source):
        raise ValueError("Promotion source payload hash is invalid")

    current_pattern_bundle = _pattern_bundle_identity()
    if any(source.get(key) != value for key, value in current_pattern_bundle.items()):
        raise ValueError(
            "Promotion source predates the current pattern bundle; "
            "a full baseline regeneration is required"
        )
    if source.get("rules_version") != RULES_VERSION or source.get("rules_registry_hash") != bazi_rules_registry_hash():
        raise ValueError("Rule formulas changed; a full baseline regeneration is required")

    source_features = source.get("feature_catalog")
    if not isinstance(source_features, list):
        raise ValueError("Promotion source feature catalog is missing")
    if source.get("feature_catalog_hash") != feature_catalog_hash(source_features):
        raise ValueError("Promotion source feature catalog hash is invalid")
    if source_features != _feature_catalog():
        raise ValueError("Feature formulas changed; a full baseline regeneration is required")

    source_metrics = source.get("metric_catalog")
    if not isinstance(source_metrics, list):
        raise ValueError("Promotion source metric catalog is missing")
    if source.get("metric_catalog_hash") != metric_catalog_hash(source_metrics):
        raise ValueError("Promotion source metric catalog hash is invalid")
    current_metric_catalog = [METRIC_DEFINITIONS[key] for key in sorted(METRIC_DEFINITIONS)]
    if source_metrics != current_metric_catalog:
        raise ValueError("Metric formulas changed; a full baseline regeneration is required")

    consumer_features = source.get("consumer_features")
    if not isinstance(consumer_features, Mapping):
        raise ValueError("Promotion source consumer feature frequencies are missing")
    catalog = consumer_features.get("catalog")
    weights = consumer_features.get("hit_weights")
    if not isinstance(catalog, list) or not isinstance(weights, Mapping):
        raise ValueError("Promotion source consumer feature frequencies are invalid")
    if consumer_features.get("rules_version") != CONSUMER_RULES_VERSION:
        raise ValueError("Consumer feature formulas changed; a full baseline regeneration is required")
    catalog_ids = {
        str(item.get("id", ""))
        for item in catalog
        if isinstance(item, Mapping) and item.get("id")
    }
    if catalog_ids != set(weights):
        raise ValueError("Promotion source consumer feature catalog and weights differ")


def promote_g3_payload(source: Mapping[str, Any], day_boundary: str) -> dict[str, Any]:
    """Promote only distributions already generated by the exact rule bundle.

    A legacy baseline without the same pattern bundle ID and digest is rejected
    because its pattern incidence cannot be relabeled as current-rule data.
    """

    _validate_promotion_source(source, day_boundary)
    promoted = {
        key: deepcopy(value)
        for key, value in source.items()
        if key not in {"consumer_score_distributions", "hash"}
    }
    metric_catalog = [METRIC_DEFINITIONS[key] for key in sorted(METRIC_DEFINITIONS)]
    promoted.update({
        "schema_version": BASELINE_SCHEMA_VERSION,
        "baseline_generation_version": BASELINE_GENERATION_VERSION,
        "id": f"bazi-{BASELINE_VERSION}-{day_boundary}",
        "rules_version": RULES_VERSION,
        "rules_registry_hash": bazi_rules_registry_hash(),
        "metric_catalog": metric_catalog,
        "metric_catalog_hash": metric_catalog_hash(metric_catalog),
        **_pattern_bundle_identity(),
    })
    consumer_features = dict(promoted["consumer_features"])
    consumer_features["rules_version"] = CONSUMER_RULES_VERSION
    promoted["consumer_features"] = consumer_features

    for key in _RETAINED_DISTRIBUTION_KEYS:
        if promoted[key] != source[key]:
            raise AssertionError(f"Promotion unexpectedly changed retained distribution: {key}")
    for key in ("catalog", "hit_weights"):
        if promoted["consumer_features"][key] != source["consumer_features"][key]:
            raise AssertionError(f"Promotion unexpectedly changed consumer feature {key}")
    promoted["hash"] = payload_hash(promoted)
    return promoted


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
        **_pattern_bundle_identity(),
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
    parser.add_argument(
        "--promote-from",
        type=Path,
        help="Directory containing g3 baselines generated by the exact current pattern bundle",
    )
    args = parser.parse_args()
    if args.metadata:
        print(json.dumps(generator_metadata(), ensure_ascii=False, sort_keys=True))
        return
    args.output.mkdir(parents=True, exist_ok=True)
    modes = ("forward", "current") if args.mode == "all" else (args.mode,)
    if args.promote_from:
        payloads = []
        for mode in modes:
            source_path = args.promote_from / f"bazi-{PROMOTION_SOURCE_VERSION}-{mode}.json"
            source = json.loads(source_path.read_text())
            payloads.append(promote_g3_payload(source, mode))
    else:
        payloads = [generate(mode) for mode in modes]
    for payload in payloads:
        path = args.output / f"{payload['id']}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        print(f"{path}: {payload['sample_weight']:.0f} minute weight, {payload['hash']}")


if __name__ == "__main__":
    main()
