from __future__ import annotations

from math import sqrt
from typing import Any, Iterable, Mapping

from iching.core.consumer_claims import (
    CONSUMER_CLAIMS_VERSION,
    compile_consumer_claims,
    project_consumer_claims,
)


CONSUMER_RULES_VERSION = "metaphysics-consumer-2026.07-v3"

THEME_ORDER = ("career", "wealth", "relationship", "health")
THEME_LABELS = {
    "career": "事业",
    "wealth": "财富",
    "relationship": "感情",
    "health": "身心节奏",
}
THEME_COLORS = {
    "overall": "#7c3aed",
    "career": "#dc2626",
    "wealth": "#d97706",
    "relationship": "#db2777",
    "health": "#059669",
}


_PERIOD_EVENT_WEIGHTS = {"新增": 3.2, "联动": 4.4, "变化": 1.2, "冲突": -4.8}
_SHENSHA_STATE_IDS = {"发力": "activated", "有力": "supported", "可见": "visible", "受制": "constrained"}


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


def _event_delta(events: Iterable[Mapping[str, Any]]) -> tuple[float, list[str], float]:
    positive = 0.0
    negative = 0.0
    drivers: list[str] = []
    seen: set[tuple[str, str]] = set()
    for event in events:
        kind = str(event.get("kind", "变化"))
        label = str(event.get("label", "阶段变化"))
        identity = (kind, label)
        if identity in seen:
            continue
        seen.add(identity)
        weight = _PERIOD_EVENT_WEIGHTS.get(kind, 1.0)
        if weight >= 0:
            positive += weight
        else:
            negative += abs(weight)
        if len(drivers) < 4:
            drivers.append(label)

    # Activation signals compound with diminishing returns. This keeps a year
    # with many related rules visibly active without allowing repeated labels
    # to pin an entire K-line at 99 or 1.
    delta = sqrt(positive) * 1.35 - sqrt(negative) * 1.55
    intensity = len(seen) * 4 + sqrt(positive + negative) * 2
    return round(delta, 2), drivers, round(intensity, 2)


def build_life_kline(
    cycles: Iterable[Mapping[str, Any]],
    natal_scores: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    """Build period activity without treating natal structure as quality.

    ``natal_scores`` remains accepted so older callers keep working,
    but intentionally has no effect. The client rebases each series to the
    user's own long-term average of 100.
    """
    del natal_scores
    expanded_cycles = [cycle for cycle in cycles if cycle.get("years")]
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
    for key in ("overall", *THEME_ORDER):
        label = "综合" if key == "overall" else THEME_LABELS[key]
        natal = 50.0
        points: list[dict[str, Any]] = []
        for cycle in expanded_cycles:
            cycle_theme = []
            activations = cycle.get("theme_activations", {})
            if key == "overall":
                cycle_theme = [event for values in activations.values() for event in values]
            else:
                profile_label = "五行与承压结构" if key == "health" else THEME_LABELS[key]
                cycle_theme = list(activations.get(profile_label, ()))
            cycle_delta, _, _ = _event_delta(cycle_theme)
            for year in cycle.get("years", ()):
                year_events_by_theme = year.get("theme_activations", {})
                if key == "overall":
                    year_events = [event for values in year_events_by_theme.values() for event in values]
                else:
                    profile_label = "五行与承压结构" if key == "health" else THEME_LABELS[key]
                    year_events = list(year_events_by_theme.get(profile_label, ()))
                year_delta, year_drivers, year_intensity = _event_delta(year_events)
                months = []
                month_values = []
                for month in year.get("months", ()):
                    month_by_theme = month.get("theme_activations", {})
                    if key == "overall":
                        month_events = [event for values in month_by_theme.values() for event in values]
                    else:
                        profile_label = "五行与承压结构" if key == "health" else THEME_LABELS[key]
                        month_events = list(month_by_theme.get(profile_label, ()))
                    month_delta, month_drivers, month_intensity = _event_delta(month_events)
                    value = round(_clamp(natal + cycle_delta * 0.45 + year_delta * 0.9 + month_delta * 1.25, 12, 98), 1)
                    month_values.append(value)
                    months.append({
                        "index": int(month.get("index", len(months))),
                        "label": str(month.get("label", f"{len(months) + 1}月")),
                        "ganzhi": str(month.get("ganzhi", "")),
                        "value": value,
                        "delta": round(cycle_delta * 0.45 + year_delta * 0.9 + month_delta * 1.25, 1),
                        "drivers": list(dict.fromkeys([*year_drivers, *month_drivers]))[:4],
                        "intensity": round(month_intensity, 1),
                    })
                if not month_values:
                    continue
                year_number = int(year.get("year", 0) or 0)
                all_years.add(year_number)
                points.append({
                    "year": year_number,
                    "open": month_values[0],
                    "close": month_values[-1],
                    "high": max(month_values),
                    "low": min(month_values),
                    "volume": round(year_intensity + sum(float(item["intensity"]) for item in months), 1),
                    "ma3": None,
                    "ma5": None,
                    "ma10": None,
                    "months": months,
                })
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
    default_years = sorted(
        int(year.get("year", 0) or 0)
        for year in (default_cycle or {}).get("years", ())
        if int(year.get("year", 0) or 0)
    )
    default_year_set = set(default_years)
    stages = []
    for item in series:
        candidates = [point for point in item["points"] if not default_year_set or point["year"] in default_year_set]
        sorted_points = sorted(candidates, key=lambda point: (point["high"], point["volume"]), reverse=True)
        stages.extend({
            "key": item["key"],
            "label": ("突破窗口" if index == 0 else "扩张窗口" if index == 1 else "重要转折"),
            "year": point["year"],
            "score": point["high"],
            "theme": item["label"],
            "summary": f"全年峰值 {point['high']:.0f}，结构活跃度 {point['volume']:.0f}。",
        } for index, point in enumerate(sorted_points[:3]))
    return {
        "default_window": {
            "start_year": default_years[0] if default_years else years[0] if years else 0,
            "end_year": default_years[-1] if default_years else years[-1] if years else 0,
        },
        "series": series,
        "period_bands": bands,
        "stages": stages,
        "method": "deterministic-period-activation-ohlcv-v1",
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
) -> dict[str, Any]:
    # Claims intentionally compile from already-derived chart facts, not raw
    # pillars. The legacy arguments remain in the public signature.
    del pillars, consumer_distributions
    profiles = list(structure.get("theme_profiles", ()))
    cycle_list = list(cycles)
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
        "life_kline": build_life_kline(cycle_list),
        "capability_key": None,
    }
