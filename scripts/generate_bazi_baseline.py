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
BASELINE_VERSION = "calendar-1924-2044-g4"
BASELINE_GENERATION_VERSION = 4
PROMOTION_SOURCE_VERSION = "calendar-1924-2044-g3"
REFRESH_SOURCE_CONSUMER_RULES_VERSION = "metaphysics-consumer-2026.07-v5"
REFRESH_SOURCE_PATTERN_BUNDLE_DIGEST = (
    "27a01e7fd9c87896259718252f107ad3b4ca95762bfb94d6580eb4e62483516d"
)
REFRESH_SOURCE_RULES_REGISTRY_HASH = (
    "sha256:f4c327d3ac5405abee1da87e587b8054062df05eb70e80593b5a8d5b3aa1db91"
)

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


def _validate_promotion_source(source: Mapping[str, Any], day_boundary: str) -> None:
    expected_id = f"bazi-{PROMOTION_SOURCE_VERSION}-{day_boundary}"
    if source.get("id") != expected_id:
        raise ValueError(
            f"Expected promotion source {expected_id}, got {source.get('id')!r}"
        )
    if source.get("chart_type") != "bazi":
        raise ValueError("Only bazi baselines can be promoted")
    if int(source.get("schema_version", 0)) != 5:
        raise ValueError("Only schema v5 baselines can be promoted to g4")
    if int(source.get("baseline_generation_version", 0)) != 3:
        raise ValueError("Only generation g3 baselines can be promoted to g4")
    if source.get("day_boundary") != day_boundary:
        raise ValueError(
            "Promotion source day-boundary metadata does not match its filename"
        )
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
    if (
        source.get("rules_version") != RULES_VERSION
        or source.get("rules_registry_hash") != bazi_rules_registry_hash()
    ):
        raise ValueError(
            "Rule formulas changed; a full baseline regeneration is required"
        )

    source_features = source.get("feature_catalog")
    if not isinstance(source_features, list):
        raise ValueError("Promotion source feature catalog is missing")
    if source.get("feature_catalog_hash") != feature_catalog_hash(source_features):
        raise ValueError("Promotion source feature catalog hash is invalid")
    if source_features != _feature_catalog():
        raise ValueError(
            "Feature formulas changed; a full baseline regeneration is required"
        )

    source_metrics = source.get("metric_catalog")
    if not isinstance(source_metrics, list):
        raise ValueError("Promotion source metric catalog is missing")
    if source.get("metric_catalog_hash") != metric_catalog_hash(source_metrics):
        raise ValueError("Promotion source metric catalog hash is invalid")
    current_metric_catalog = [
        METRIC_DEFINITIONS[key] for key in sorted(METRIC_DEFINITIONS)
    ]
    if source_metrics != current_metric_catalog:
        raise ValueError(
            "Metric formulas changed; a full baseline regeneration is required"
        )

    consumer_features = source.get("consumer_features")
    if not isinstance(consumer_features, Mapping):
        raise ValueError("Promotion source consumer feature frequencies are missing")
    catalog = consumer_features.get("catalog")
    weights = consumer_features.get("hit_weights")
    if not isinstance(catalog, list) or not isinstance(weights, Mapping):
        raise ValueError("Promotion source consumer feature frequencies are invalid")
    if consumer_features.get("rules_version") != CONSUMER_RULES_VERSION:
        raise ValueError(
            "Consumer feature formulas changed; a full baseline regeneration is required"
        )
    if (
        consumer_features.get("method") != BAZI_CONSUMER_FEATURE_METHOD
        or consumer_features.get("pattern_authority") != _canonical_pattern_authority()
    ):
        raise ValueError(
            "Consumer pattern authority changed; a full baseline regeneration is required"
        )
    catalog_ids = {
        str(item.get("id", ""))
        for item in catalog
        if isinstance(item, Mapping) and item.get("id")
    }
    if catalog_ids != set(weights):
        raise ValueError("Promotion source consumer feature catalog and weights differ")
    pattern_ids = {
        str(item.get("id", ""))
        for item in catalog
        if isinstance(item, Mapping) and item.get("kind") == "pattern"
    }
    if any(
        not identifier.startswith("bazi.pattern.canonical.")
        for identifier in pattern_ids
    ):
        raise ValueError(
            "Consumer pattern catalog predates canonical lifecycle features; "
            "a full baseline regeneration is required"
        )


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
    promoted.update(
        {
            "schema_version": BASELINE_SCHEMA_VERSION,
            "baseline_generation_version": BASELINE_GENERATION_VERSION,
            "id": f"bazi-{BASELINE_VERSION}-{day_boundary}",
            "rules_version": RULES_VERSION,
            "rules_registry_hash": bazi_rules_registry_hash(),
            "metric_catalog": metric_catalog,
            "metric_catalog_hash": metric_catalog_hash(metric_catalog),
            **_pattern_bundle_identity(),
        }
    )
    consumer_features = dict(promoted["consumer_features"])
    consumer_features.update(_canonical_consumer_feature_metadata())
    promoted["consumer_features"] = consumer_features

    for key in _RETAINED_DISTRIBUTION_KEYS:
        if promoted[key] != source[key]:
            raise AssertionError(
                f"Promotion unexpectedly changed retained distribution: {key}"
            )
    for key in ("catalog", "hit_weights"):
        if promoted["consumer_features"][key] != source["consumer_features"][key]:
            raise AssertionError(
                f"Promotion unexpectedly changed consumer feature {key}"
            )
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
    """Return the exact 120-year four-pillar states and duration weights."""

    zone = ZoneInfo("Asia/Shanghai")
    start = _lichun(1924, zone)
    end = _lichun(2044, zone)
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


def _canonical_pattern_records_for_state(
    item: tuple[tuple[str, ...], float],
) -> tuple[float, tuple[tuple[str, str], ...]]:
    state_key, seconds = item
    pillars = _pillars_from_state_key(state_key)
    pattern_set = evaluate_pattern_set(
        build_rule_evaluation_context(build_bazi_fact_graph(pillars)),
        load_packaged_shen_registry(),
    ).as_dict()
    records = consumer_feature_records(
        {
            "source_backed_authority": {
                "authoritative": True,
                "pattern_set": pattern_set,
            }
        },
        {},
    )
    return seconds, tuple(
        (record["id"], record["title"])
        for record in records
        if record.get("kind") == "pattern"
    )


def _replace_canonical_pattern_features(
    source: Mapping[str, Any],
    *,
    pattern_weights: Mapping[str, float],
    pattern_titles: Mapping[str, str],
) -> dict[str, Any]:
    """Replace only pattern incidence; preserve unrelated generated summaries."""

    payload = deepcopy(dict(source))
    package = payload.get("consumer_features")
    if not isinstance(package, Mapping):
        raise ValueError("Baseline consumer feature package is missing")
    old_catalog = package.get("catalog")
    old_weights = package.get("hit_weights")
    if not isinstance(old_catalog, list) or not isinstance(old_weights, Mapping):
        raise ValueError("Baseline consumer feature package is invalid")
    retained_catalog = [
        dict(record)
        for record in old_catalog
        if isinstance(record, Mapping) and record.get("kind") != "pattern"
    ]
    retained_ids = {str(record["id"]) for record in retained_catalog}
    retained_weights = {
        str(identifier): weight
        for identifier, weight in old_weights.items()
        if str(identifier) in retained_ids
    }
    pattern_catalog = [
        {"id": identifier, "kind": "pattern", "title": pattern_titles[identifier]}
        for identifier in sorted(pattern_weights)
    ]
    combined_catalog = sorted(
        [*retained_catalog, *pattern_catalog],
        key=lambda record: str(record["id"]),
    )
    combined_weights = {
        **retained_weights,
        **{
            identifier: round(float(pattern_weights[identifier]) / 60, 6)
            for identifier in sorted(pattern_weights)
        },
    }
    payload["consumer_features"] = {
        **dict(package),
        **_canonical_consumer_feature_metadata(),
        "catalog": combined_catalog,
        "hit_weights": combined_weights,
    }
    payload.update(
        {
            "rules_registry_hash": bazi_rules_registry_hash(),
            **_pattern_bundle_identity(),
        }
    )
    payload["hash"] = payload_hash(payload)
    return payload


def _validate_pattern_refresh_source(
    source: Mapping[str, Any],
    day_boundary: str,
) -> None:
    """Accept only the exact G4/v5 producer whose pattern slice is migrated."""

    expected_id = f"bazi-{BASELINE_VERSION}-{day_boundary}"
    if source.get("id") != expected_id or source.get("day_boundary") != day_boundary:
        raise ValueError(f"Expected baseline {expected_id}")
    if source.get("hash") != payload_hash(source):
        raise ValueError("Baseline payload hash is invalid")
    if source.get("chart_type") != "bazi" or source.get("config_id") != _config_id(
        day_boundary
    ):
        raise ValueError("Baseline calendar configuration is incompatible")
    if int(source.get("schema_version", 0)) != BASELINE_SCHEMA_VERSION:
        raise ValueError("Baseline schema version is incompatible")
    if int(source.get("baseline_generation_version", 0)) != BASELINE_GENERATION_VERSION:
        raise ValueError("Baseline generation version is incompatible")
    if source.get("rules_version") != RULES_VERSION:
        raise ValueError("ShenSha formulas changed; full regeneration is required")
    if (
        source.get("pattern_bundle_id")
        != _pattern_bundle_identity()["pattern_bundle_id"]
    ):
        raise ValueError("Baseline pattern bundle identity is incompatible")
    if source.get("pattern_bundle_digest") != REFRESH_SOURCE_PATTERN_BUNDLE_DIGEST:
        raise ValueError("Baseline is not the approved pre-refresh pattern bundle")
    if source.get("rules_registry_hash") != REFRESH_SOURCE_RULES_REGISTRY_HASH:
        raise ValueError("Baseline is not the approved pre-refresh rule registry")

    source_features = source.get("feature_catalog")
    if not isinstance(source_features, list):
        raise ValueError("Baseline feature catalog is missing")
    if source.get("feature_catalog_hash") != feature_catalog_hash(source_features):
        raise ValueError("Baseline feature catalog hash is invalid")
    if source_features != _feature_catalog():
        raise ValueError("Feature formulas changed; full regeneration is required")

    source_metrics = source.get("metric_catalog")
    if not isinstance(source_metrics, list):
        raise ValueError("Baseline metric catalog is missing")
    if source.get("metric_catalog_hash") != metric_catalog_hash(source_metrics):
        raise ValueError("Baseline metric catalog hash is invalid")
    current_metrics = [METRIC_DEFINITIONS[key] for key in sorted(METRIC_DEFINITIONS)]
    if source_metrics != current_metrics:
        raise ValueError("Metric formulas changed; full regeneration is required")

    consumer_features = source.get("consumer_features")
    if not isinstance(consumer_features, Mapping):
        raise ValueError("Baseline consumer feature package is missing")
    if consumer_features.get("rules_version") != REFRESH_SOURCE_CONSUMER_RULES_VERSION:
        raise ValueError("Baseline is not the approved v5 consumer producer")
    if consumer_features.get("method") != "weighted_empirical_feature_incidence":
        raise ValueError("Baseline consumer feature method is incompatible")
    if "pattern_authority" in consumer_features:
        raise ValueError("Baseline pattern slice has already been refreshed")
    catalog = consumer_features.get("catalog")
    weights = consumer_features.get("hit_weights")
    if not isinstance(catalog, list) or not isinstance(weights, Mapping):
        raise ValueError("Baseline consumer feature package is invalid")
    catalog_ids = {
        str(item.get("id", ""))
        for item in catalog
        if isinstance(item, Mapping) and item.get("id")
    }
    if catalog_ids != set(weights):
        raise ValueError("Baseline consumer feature catalog and weights differ")
    pattern_ids = {
        str(item.get("id", ""))
        for item in catalog
        if isinstance(item, Mapping) and item.get("kind") == "pattern"
    }
    if not pattern_ids or any(
        not identifier.startswith(("bazi.pattern.ordinary.", "bazi.pattern.special."))
        for identifier in pattern_ids
    ):
        raise ValueError("Baseline does not contain the approved legacy pattern slice")


def refresh_canonical_pattern_features(
    source: Mapping[str, Any],
    day_boundary: str,
    *,
    workers: int = 1,
) -> dict[str, Any]:
    """Recompute canonical pattern incidence without relabeling legacy values."""

    _validate_pattern_refresh_source(source, day_boundary)
    start, end, state_weights = _calendar_state_weights(day_boundary)
    if source.get("start") != start.isoformat() or source.get("end") != end.isoformat():
        raise ValueError("Baseline time interval is incompatible")
    if int(source.get("unique_state_count", 0)) != len(state_weights):
        raise ValueError("Baseline state count is incompatible")
    sample_weight = round(sum(state_weights.values()) / 60, 6)
    if abs(float(source.get("sample_weight", 0)) - sample_weight) > 1e-6:
        raise ValueError("Baseline sample weight is incompatible")

    pattern_weights: Counter[str] = Counter()
    pattern_titles: dict[str, str] = {}
    items = list(state_weights.items())

    def collect(results: Iterable[tuple[float, tuple[tuple[str, str], ...]]]) -> None:
        for seconds, records in results:
            for identifier, title in records:
                pattern_weights[identifier] += seconds
                pattern_titles.setdefault(identifier, title)

    if workers <= 1:
        collect(map(_canonical_pattern_records_for_state, items))
    else:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            collect(
                executor.map(
                    _canonical_pattern_records_for_state,
                    items,
                    chunksize=512,
                )
            )
    return _replace_canonical_pattern_features(
        source,
        pattern_weights=pattern_weights,
        pattern_titles=pattern_titles,
    )


def generate(day_boundary: str) -> dict:
    start, end, state_weights = _calendar_state_weights(day_boundary)
    feature_weights: Counter[str] = Counter()
    profile_genders = {"male": "male", "female": "female", "neutral": None}
    theme_metric_weights_by_gender = {
        gender: {theme: {} for theme in THEME_ORDER} for gender in profile_genders
    }
    consumer_feature_weights: Counter[str] = Counter()
    consumer_feature_catalog: dict[str, dict[str, str]] = {}
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
        effects = evaluate_shensha_effects(
            evaluated_hits, pillars, structures["neutral"]
        )
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
                    histogram = theme_metric_weights_by_gender[gender][
                        theme
                    ].setdefault(metric["metric_id"], Counter())
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
            feature_id: {
                "hit_weight": round(feature_weights.get(feature_id, 0.0) / 60, 6)
            }
            for feature_id in catalog
        },
        "theme_comparison_method": "transparent_metric_distributions",
        "theme_metric_weights_by_gender": {
            gender: {
                theme: {
                    metric_id: {
                        value: round(seconds / 60, 6)
                        for value, seconds in sorted(
                            histogram.items(), key=lambda item: int(item[0])
                        )
                    }
                    for metric_id, histogram in metrics.items()
                }
                for theme, metrics in themes.items()
            }
            for gender, themes in theme_metric_weights_by_gender.items()
        },
        "consumer_features": {
            **_canonical_consumer_feature_metadata(),
            "catalog": [
                consumer_feature_catalog[key]
                for key in sorted(consumer_feature_catalog)
            ],
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
    parser.add_argument(
        "--refresh-canonical-pattern-features-from",
        type=Path,
        help="Directory containing g4 baselines whose canonical pattern incidence must be rebuilt",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=max(1, min(8, os.cpu_count() or 1)),
        help="Worker processes for canonical pattern feature refresh",
    )
    args = parser.parse_args()
    if args.metadata:
        print(json.dumps(generator_metadata(), ensure_ascii=False, sort_keys=True))
        return
    args.output.mkdir(parents=True, exist_ok=True)
    modes = ("forward", "current") if args.mode == "all" else (args.mode,)
    if args.promote_from and args.refresh_canonical_pattern_features_from:
        parser.error("choose only one baseline source mode")
    if args.promote_from:
        payloads = []
        for mode in modes:
            source_path = (
                args.promote_from / f"bazi-{PROMOTION_SOURCE_VERSION}-{mode}.json"
            )
            source = json.loads(source_path.read_text())
            payloads.append(promote_g3_payload(source, mode))
    elif args.refresh_canonical_pattern_features_from:
        payloads = []
        for mode in modes:
            source_path = (
                args.refresh_canonical_pattern_features_from
                / f"bazi-{BASELINE_VERSION}-{mode}.json"
            )
            source = json.loads(source_path.read_text())
            payloads.append(
                refresh_canonical_pattern_features(
                    source,
                    mode,
                    workers=max(1, args.workers),
                )
            )
    else:
        payloads = [generate(mode) for mode in modes]
    for payload in payloads:
        path = args.output / f"{payload['id']}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        print(
            f"{path}: {payload['sample_weight']:.0f} minute weight, {payload['hash']}"
        )


if __name__ == "__main__":
    main()
