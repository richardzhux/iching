from __future__ import annotations

from math import sqrt, tanh
from typing import Any, Iterable, Mapping

from iching.core.consumer_claims import (
    CONSUMER_CLAIMS_VERSION,
    compile_consumer_claims,
    project_consumer_claims,
)


CONSUMER_RULES_VERSION = "metaphysics-consumer-2026.07-v4"

THEME_ORDER = ("career", "wealth", "relationship", "rhythm")
THEME_LABELS = {
    "career": "事业",
    "wealth": "财富",
    "relationship": "感情",
    "rhythm": "身心节奏",
}
THEME_PROFILE_LABELS = {
    "career": "事业",
    "wealth": "财富",
    "relationship": "感情",
    "rhythm": "五行与承压结构",
}
THEME_COLORS = {
    "career": "#dc2626",
    "wealth": "#d97706",
    "relationship": "#db2777",
    "rhythm": "#059669",
}

_PERIOD_ROLE_WEIGHTS = {
    "formation": 8.0,
    "rescue": 7.0,
    "support": 4.5,
    "damage": -8.0,
    "conflict": -6.0,
    "neutral": 0.0,
}
_SHENSHA_STATE_IDS = {"发力": "activated", "有力": "supported", "可见": "visible", "受制": "constrained"}
_LIFECYCLE_TRANSITIONS = {
    "formation": (
        frozenset(("inactive", "superseded", "undetermined")),
        frozenset(("formed", "rescued", "mixed", "transformed")),
    ),
    "damage": (
        frozenset(("formed", "rescued", "transformed")),
        frozenset(("broken", "mixed")),
    ),
    "rescue": (
        frozenset(("broken", "mixed")),
        frozenset(("rescued",)),
    ),
}


def _clamp(value: float, minimum: float = 0, maximum: float = 100) -> float:
    return max(minimum, min(maximum, value))


def consumer_feature_records(
    patterns: Mapping[str, Any] | None,
    shensha_effects: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    """Feature IDs shared by baseline generation and live-chart lookup."""
    records: list[dict[str, str]] = []
    pattern = patterns or {}
    primary = pattern.get("primary") if isinstance(pattern, Mapping) else None
    if isinstance(primary, Mapping) and primary.get("id"):
        records.append({
            "id": str(primary["id"]),
            "kind": "pattern",
            "title": str(primary.get("title", primary.get("name", "主导格局"))),
        })
    effects = shensha_effects or {}
    for hit in effects.get("hits", ()):
        state = str(hit.get("state", "可见"))
        state_id = _SHENSHA_STATE_IDS.get(state, "visible")
        records.append({
            "id": f"bazi.consumer.shensha.{hit.get('rule_id', 'unknown')}.state.{state_id}",
            "kind": "shensha_state",
            "title": f"{hit.get('name', '神煞')}·{state}",
        })
    for combination in effects.get("combinations", ()):
        if combination.get("id"):
            records.append({
                "id": str(combination["id"]),
                "kind": "combination",
                "title": str(combination.get("title", "结构组合")),
            })
    unique: dict[str, dict[str, str]] = {}
    for record in records:
        unique.setdefault(record["id"], record)
    return list(unique.values())


def _driver_from_event(event: Mapping[str, Any]) -> dict[str, Any] | None:
    role = str(event.get("role", "neutral"))
    # Formation, damage, and rescue are lifecycle verdicts, not generic period
    # labels. They are admitted only through the exact provenance matcher below.
    if role in {"formation", "damage", "rescue"}:
        return None
    raw_delta = event.get("delta", _PERIOD_ROLE_WEIGHTS.get(role, 0.0))
    try:
        delta = float(raw_delta)
    except (TypeError, ValueError):
        delta = float(_PERIOD_ROLE_WEIGHTS.get(role, 0.0))
    driver = {
        "id": str(event.get("id", f"bazi.period.{role}.{event.get('label', 'change')}")),
        "layer": str(event.get("layer", "period")),
        "role": role,
        "label": str(event.get("label", "阶段变化")),
        "delta": round(delta, 2),
    }
    evidence_ids = [str(item) for item in event.get("evidenceIds", ()) if item]
    rule_ids = [str(item) for item in event.get("ruleIds", ()) if item]
    if evidence_ids:
        driver["evidenceIds"] = evidence_ids
    if rule_ids:
        driver["ruleIds"] = rule_ids
    return driver


def _pattern_driver_context(
    claims: Iterable[Mapping[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    result = {key: [] for key in THEME_ORDER}
    role_weights = {"formation_path": "formation", "damage": "damage", "rescue": "rescue"}
    for claim in sorted(claims, key=lambda item: str(item.get("id", ""))):
        classical_role = str(claim.get("classicalRole", ""))
        role = role_weights.get(classical_role)
        if not role:
            continue
        path_ids = _unique_driver_strings(
            (
                claim.get("pathId", ""),
                *_unique_driver_strings(claim.get("pathIds", ())),
            )
        )
        rule_ids = _unique_driver_strings(claim.get("ruleIds", ()))
        source_ids = _unique_driver_strings(claim.get("sourceIds", ()))
        pattern_id = str(claim.get("patternId", ""))
        provenance: list[dict[str, Any]] = []
        for value in claim.get("lifecycleProvenance", ()):
            if not isinstance(value, Mapping):
                continue
            binding_path_id = str(value.get("pathId", ""))
            binding_rule_id = str(value.get("ruleId", ""))
            binding_source_ids = _unique_driver_strings(value.get("sourceIds", ()))
            if (
                not binding_path_id
                or not binding_rule_id
                or not binding_source_ids
                or binding_path_id not in path_ids
                or binding_rule_id not in rule_ids
                or not set(binding_source_ids).issubset(source_ids)
            ):
                continue
            provenance.append({
                "pathId": binding_path_id,
                "ruleId": binding_rule_id,
                "sourceIds": binding_source_ids,
            })
        source_backed = bool(pattern_id and provenance)
        explicit_theme = str(claim.get("theme", ""))
        themes = [explicit_theme] if explicit_theme in result else list(THEME_ORDER)
        for theme in themes:
            result[theme].append({
                "id": str(claim.get("id", f"bazi.claim.{role}")),
                "layer": "natal",
                "role": role,
                "label": str(claim.get("title", "主导结构")),
                # Natal facts define the personal baseline. Only an actual
                # period match receives a signed delta below.
                "delta": 0.0,
                "evidenceIds": [str(item) for item in claim.get("evidenceIds", ()) if item],
                "ruleIds": rule_ids,
                "sourceIds": source_ids,
                "patternId": pattern_id,
                "pathIds": path_ids,
                "lifecycleProvenance": provenance,
                "_sourceBackedLifecycle": source_backed,
            })
    return result


def _unique_driver_strings(values: Any) -> list[str]:
    if values is None:
        return []
    if isinstance(values, (str, bytes)):
        values = (values,)
    try:
        return list(dict.fromkeys(str(value) for value in values if str(value)))
    except TypeError:
        return []


def _matched_pattern_drivers(
    events: Iterable[Mapping[str, Any]],
    pattern_drivers: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for event in events:
        lifecycle = event.get("lifecycle")
        if not isinstance(lifecycle, Mapping):
            continue
        before = str(lifecycle.get("before", ""))
        after = str(lifecycle.get("after", ""))
        event_pattern_id = str(lifecycle.get("patternId", ""))
        event_path_id = str(lifecycle.get("pathId", ""))
        event_rule_ids = set(_unique_driver_strings(lifecycle.get("ruleIds", ())))
        event_source_ids = set(_unique_driver_strings(lifecycle.get("sourceIds", ())))
        for driver in pattern_drivers:
            if not driver.get("_sourceBackedLifecycle"):
                continue
            role = str(driver.get("role", "neutral"))
            if str(event.get("role", "neutral")) != role:
                continue
            transition = _LIFECYCLE_TRANSITIONS.get(role)
            if (
                transition is None
                or before not in transition[0]
                or after not in transition[1]
            ):
                continue
            if event_pattern_id != str(driver.get("patternId", "")):
                continue
            matching_bindings = [
                binding
                for binding in driver.get("lifecycleProvenance", ())
                if isinstance(binding, Mapping)
                and str(binding.get("pathId", "")) == event_path_id
                and str(binding.get("ruleId", "")) in event_rule_ids
            ]
            matched_rule_ids = {
                str(binding.get("ruleId", "")) for binding in matching_bindings
            }
            matched_source_ids = {
                source_id
                for binding in matching_bindings
                for source_id in _unique_driver_strings(binding.get("sourceIds", ()))
            }
            if (
                not event_rule_ids
                or not event_source_ids
                or matched_rule_ids != event_rule_ids
                or matched_source_ids != event_source_ids
            ):
                continue
            matches.append({
                **dict(driver),
                "id": f"{driver.get('id', 'bazi.claim')}.{event.get('id', event.get('layer', 'period'))}",
                "layer": str(event.get("layer", "period")),
                "label": f"{event.get('label', '运限变化')}呼应{driver.get('label', '原局结构')}",
                "delta": _PERIOD_ROLE_WEIGHTS.get(role, 0.0),
                "lifecycle": {
                    "before": before,
                    "after": after,
                    "patternId": event_pattern_id,
                    "pathId": event_path_id,
                    "ruleIds": sorted(event_rule_ids),
                    "sourceIds": sorted(event_source_ids),
                },
            })
    return matches


def _event_delta(
    events: Iterable[Mapping[str, Any]],
    pattern_drivers: Iterable[Mapping[str, Any]] = (),
) -> tuple[float, list[dict[str, Any]], float]:
    event_list = [dict(event) for event in events]
    drivers = [
        *(
            driver
            for event in event_list
            if (driver := _driver_from_event(event)) is not None
        ),
        *_matched_pattern_drivers(event_list, pattern_drivers),
    ]
    positive = 0.0
    negative = 0.0
    unique: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for driver in drivers:
        identity = (str(driver.get("layer", "period")), str(driver.get("role", "neutral")), str(driver.get("label", "阶段变化")))
        if identity in seen:
            continue
        seen.add(identity)
        unique.append(driver)
        weight = float(driver.get("delta", 0) or 0)
        if weight >= 0:
            positive += weight
        else:
            negative += abs(weight)

    # Signed lifecycle signals use diminishing returns. Neutral Ten-God and
    # ShenSha events contribute to volume only; they never become hidden points.
    delta = sqrt(positive) * 2.8 - sqrt(negative) * 3.0
    intensity = len(seen) * 4 + sqrt(positive + negative) * 3
    ordered = sorted(
        unique,
        key=lambda item: (-abs(float(item.get("delta", 0) or 0)), str(item.get("layer", "")), str(item.get("label", ""))),
    )
    return round(delta, 2), ordered[:5], round(intensity, 2)


def build_life_kline(
    cycles: Iterable[Mapping[str, Any]],
    natal_scores: Mapping[str, int] | None = None,
    *,
    claims: Iterable[Mapping[str, Any]] = (),
    visible_years: set[int] | None = None,
) -> dict[str, Any]:
    """Build period activity without treating natal structure as quality.

    ``natal_scores`` remains accepted so older callers keep working,
    but intentionally has no effect. The client rebases each series to the
    user's own available long-horizon average of 100.
    """
    del natal_scores
    expanded_cycles = sorted(
        (cycle for cycle in cycles if cycle.get("years")),
        key=lambda cycle: (
            int(cycle.get("start_year", 0) or 0),
            int(cycle.get("index", 0) or 0),
            str(cycle.get("label", "")),
        ),
    )
    pattern_context = _pattern_driver_context(claims)
    bands = [
        {
            "label": str(cycle.get("label", "大运")),
            "start_year": int(cycle.get("start_year", 0) or 0),
            "end_year": int(cycle.get("end_year", 0) or 0),
        }
        for cycle in expanded_cycles
    ]
    series: list[dict[str, Any]] = []
    all_years: set[int] = set()
    baseline_series: dict[str, dict[str, float]] = {}
    for key in THEME_ORDER:
        label = THEME_LABELS[key]
        natal = 50.0
        points: list[dict[str, Any]] = []
        all_raw_months: list[float] = []
        for cycle in expanded_cycles:
            activations = cycle.get("theme_activations", {})
            profile_label = THEME_PROFILE_LABELS[key]
            cycle_theme = list(activations.get(profile_label, ()))
            cycle_delta, cycle_drivers, cycle_intensity = _event_delta(cycle_theme, pattern_context[key])
            for year in sorted(cycle.get("years", ()), key=lambda item: int(item.get("year", 0) or 0)):
                year_events_by_theme = year.get("theme_activations", {})
                year_events = list(year_events_by_theme.get(profile_label, ()))
                year_delta, year_drivers, year_intensity = _event_delta(year_events, pattern_context[key])
                months = []
                raw_month_values = []
                for month in sorted(year.get("months", ()), key=lambda item: int(item.get("index", 0) or 0)):
                    month_by_theme = month.get("theme_activations", {})
                    month_events = list(month_by_theme.get(profile_label, ()))
                    month_delta, month_drivers, month_intensity = _event_delta(month_events, pattern_context[key])
                    raw_value = round(_clamp(natal + cycle_delta * 0.55 + year_delta + month_delta * 1.4, 8, 92), 3)
                    raw_month_values.append(raw_value)
                    all_raw_months.append(raw_value)
                    named_drivers = []
                    for driver in [*cycle_drivers, *year_drivers, *month_drivers]:
                        identity = (driver.get("id"), driver.get("layer"), driver.get("label"))
                        if any((item.get("id"), item.get("layer"), item.get("label")) == identity for item in named_drivers):
                            continue
                        named_drivers.append({
                            key: value
                            for key, value in driver.items()
                            if not key.startswith("_")
                            and value not in ([], (), None, "")
                        })
                    named_drivers.sort(
                        key=lambda driver: (
                            -abs(float(driver.get("delta", 0) or 0)),
                            str(driver.get("layer", "")),
                            str(driver.get("label", "")),
                        )
                    )
                    months.append({
                        "index": int(month.get("index", len(months))),
                        "label": str(month.get("label", f"{len(months) + 1}月")),
                        "ganzhi": str(month.get("ganzhi", "")),
                        "raw_value": raw_value,
                        "drivers": named_drivers[:6],
                        "intensity": round(cycle_intensity + year_intensity + month_intensity, 1),
                    })
                if not raw_month_values:
                    continue
                year_number = int(year.get("year", 0) or 0)
                all_years.add(year_number)
                strongest_month_drivers = sorted(
                    (
                        driver
                        for month in months
                        for driver in month.get("drivers", ())
                    ),
                    key=lambda item: -abs(float(item.get("delta", 0) or 0)),
                )
                point_drivers: list[dict[str, Any]] = []
                for driver in [*cycle_drivers, *year_drivers, *strongest_month_drivers]:
                    identity = (driver.get("id"), driver.get("layer"), driver.get("label"))
                    if any((item.get("id"), item.get("layer"), item.get("label")) == identity for item in point_drivers):
                        continue
                    point_drivers.append({
                        key: value
                        for key, value in driver.items()
                        if not key.startswith("_")
                        and value not in ([], (), None, "")
                    })
                points.append({
                    "year": year_number,
                    "is_current": bool(year.get("is_current")),
                    "raw_open": raw_month_values[0],
                    "raw_close": raw_month_values[-1],
                    "raw_high": max(raw_month_values),
                    "raw_low": min(raw_month_values),
                    "volume": round(year_intensity + sum(float(item["intensity"]) for item in months), 1),
                    "ma3": None,
                    "ma5": None,
                    "ma10": None,
                    "drivers": point_drivers[:5],
                    "months": months,
                })
        baseline_raw = sum(all_raw_months) / len(all_raw_months) if all_raw_months else natal
        baseline_series[key] = {"raw_value": round(baseline_raw, 6)}
        def normalize(value: float) -> float:
            raw_distance = (value / baseline_raw - 1) * 100
            return round(100 + 35 * tanh(raw_distance / 35), 1)
        for point in points:
            point["open"] = normalize(float(point.pop("raw_open")))
            point["close"] = normalize(float(point.pop("raw_close")))
            point["high"] = normalize(float(point.pop("raw_high")))
            point["low"] = normalize(float(point.pop("raw_low")))
            for month in point["months"]:
                month["value"] = normalize(float(month.pop("raw_value")))
                month["delta"] = round(float(month["value"]) - 100, 1)
        if visible_years is not None:
            points = [point for point in points if int(point["year"]) in visible_years]
        closes: list[float] = []
        for point in points:
            closes.append(float(point["close"]))
            for window in (3, 5, 10):
                point[f"ma{window}"] = round(sum(closes[-window:]) / window, 1) if len(closes) >= window else None
        series.append({"key": key, "label": label, "color": THEME_COLORS[key], "points": points})

    years = sorted(year for year in all_years if year)
    default_cycle = next((cycle for cycle in expanded_cycles if cycle.get("is_current")), None)
    if default_cycle is None and expanded_cycles:
        default_cycle = expanded_cycles[0]
    current_year = next(
        (
            int(year.get("year", 0) or 0)
            for cycle in expanded_cycles
            for year in cycle.get("years", ())
            if year.get("is_current") and int(year.get("year", 0) or 0)
        ),
        0,
    )
    default_years = sorted(
        int(year.get("year", 0) or 0)
        for year in (default_cycle or {}).get("years", ())
        if int(year.get("year", 0) or 0)
    )
    if not current_year:
        current_year = default_years[0] if default_years else years[0] if years else 0
    candidates: list[dict[str, Any]] = []
    for item in series:
        for point in item["points"]:
            if point["year"] < current_year or point["year"] > current_year + 9:
                continue
            high_distance = abs(float(point["high"]) - 100)
            low_distance = abs(float(point["low"]) - 100)
            relative_index = float(point["high"]) if high_distance >= low_distance else float(point["low"])
            target_month = (
                max(point["months"], key=lambda month: float(month["value"]))
                if high_distance >= low_distance
                else min(point["months"], key=lambda month: float(month["value"]))
            )
            direction = 1 if relative_index >= 100 else -1
            ordered_drivers = sorted(
                target_month.get("drivers", ()),
                key=lambda driver: (
                    0
                    if float(driver.get("delta", 0) or 0) * direction > 0
                    else 1
                    if float(driver.get("delta", 0) or 0) == 0
                    else 2,
                    -abs(float(driver.get("delta", 0) or 0)),
                    str(driver.get("label", "")),
                ),
            )
            aligned_drivers = [
                driver
                for driver in ordered_drivers
                if float(driver.get("delta", 0) or 0) * direction > 0
            ]
            neutral_drivers = [
                driver
                for driver in ordered_drivers
                if float(driver.get("delta", 0) or 0) == 0
            ]
            stage_drivers = [*aligned_drivers, *neutral_drivers][:4]
            candidates.append({
                "key": item["key"],
                "year": point["year"],
                "theme": item["label"],
                "relative_index": relative_index,
                "volume": float(point["volume"]),
                "drivers": stage_drivers,
                "distance": max(high_distance, low_distance),
            })
    candidates.sort(key=lambda item: (item["distance"], item["volume"], -item["year"]), reverse=True)
    selected: list[dict[str, Any]] = []
    used_years: set[int] = set()
    used_themes: set[str] = set()
    for candidate in candidates:
        if candidate["year"] in used_years or candidate["key"] in used_themes:
            continue
        selected.append(candidate)
        used_years.add(candidate["year"])
        used_themes.add(candidate["key"])
        if len(selected) == 3:
            break
    if len(selected) < 3:
        for candidate in candidates:
            if candidate["year"] in used_years:
                continue
            selected.append(candidate)
            used_years.add(candidate["year"])
            if len(selected) == 3:
                break
    stages = []
    for candidate in sorted(selected, key=lambda item: item["year"]):
        relative_index = float(candidate["relative_index"])
        label = "上行窗口" if relative_index >= 105 else "调整窗口" if relative_index <= 95 else "活跃窗口"
        stages.append({
            "key": candidate["key"],
            "label": label,
            "year": candidate["year"],
            "relative_index": round(relative_index, 1),
            "theme": candidate["theme"],
            "drivers": candidate["drivers"][:4],
            "summary": f"{candidate['theme']}相对个人常态来到 {relative_index:.0f}，由当年与月份的结构变化共同形成。",
        })
    horizon_start = years[0] if years else 0
    horizon_end = years[-1] if years else 0
    return {
        "default_window": {
            "start_year": current_year,
            "end_year": min(current_year + 9, horizon_end) if current_year and horizon_end else horizon_end,
        },
        "baseline": {
            "normalized_value": 100,
            "scope": "full_horizon",
            "start_year": horizon_start,
            "end_year": horizon_end,
            "method": "mean_monthly_activation_v1",
            "series": baseline_series,
        },
        "series": series,
        "period_bands": bands,
        "stages": stages,
        "method": "deterministic-period-activation-ohlcv-v2",
    }


def build_bazi_consumer_profile(
    *,
    pillars: Iterable[Mapping[str, Any]],
    structure: Mapping[str, Any],
    patterns: Mapping[str, Any] | None,
    shensha_effects: Mapping[str, Any] | None,
    cycles: Iterable[Mapping[str, Any]],
    consumer_distributions: Mapping[str, Any] | None = None,
    consumer_feature_metrics: Iterable[Mapping[str, Any]] = (),
    kline_cycles: Iterable[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    # Claims intentionally compile from already-derived chart facts, not raw
    # pillars. The legacy arguments remain in the public signature.
    del pillars, consumer_distributions
    profiles = list(structure.get("theme_profiles", ()))
    cycle_list = list(cycles)
    full_kline_cycles = list(kline_cycles) if kline_cycles is not None else cycle_list
    visible_years = {
        int(year.get("year", 0) or 0)
        for cycle in cycle_list
        for year in cycle.get("years", ())
        if int(year.get("year", 0) or 0)
    }
    effects = shensha_effects or {}
    pattern = patterns or {}
    claims = compile_consumer_claims(
        patterns=pattern,
        theme_profiles=profiles,
        shensha_effects=effects,
        cycles=cycle_list,
        feature_metrics=consumer_feature_metrics,
    )
    compatibility = project_consumer_claims(claims)
    return {
        "version": CONSUMER_RULES_VERSION,
        "claims_version": CONSUMER_CLAIMS_VERSION,
        "system": "bazi",
        "claims": claims,
        "identity": compatibility["identity"],
        "subjects": compatibility["subjects"],
        "achievements": compatibility["achievements"],
        "fingerprints": compatibility["fingerprints"],
        # A day-master/month-command cohort is not a true structural twin.
        "twin": None,
        "life_kline": build_life_kline(
            full_kline_cycles,
            claims=claims,
            visible_years=visible_years if kline_cycles is not None else None,
        ),
        "capability_key": None,
    }
