from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

from iching.core.shensha import AXES, RULE_BY_ID


DATA_DIR = Path(__file__).with_name("data")
BASELINE_ID = "bazi-calendar-1924-2044-v1-forward"
BASELINE_IDS = {
    "bazi": {
        "forward": BASELINE_ID,
        "current": "bazi-calendar-1924-2044-v1-current",
    },
    "ziwei": {"default": "ziwei-calendar-1924-2044-v1"},
}
FEATURE_ID_RE = re.compile(r"^(bazi|ziwei)\.[a-z0-9_.-]{1,96}$")


@lru_cache(maxsize=8)
def load_baseline(baseline_id: str) -> dict[str, Any]:
    if baseline_id not in {item for values in BASELINE_IDS.values() for item in values.values()}:
        raise ValueError(f"未知统计基线: {baseline_id}")
    path = DATA_DIR / f"{baseline_id}.json"
    if not path.exists():
        raise RuntimeError(f"统计基线尚未生成: {baseline_id}")
    return json.loads(path.read_text())


def frequency_level(percentage: float) -> str:
    if percentage >= 20:
        return "common"
    if percentage >= 5:
        return "less_common"
    if percentage >= 1:
        return "rare"
    return "very_rare"


def frequency_label(percentage: float) -> str:
    if percentage < 0.01:
        return "<0.01%"
    return f"{percentage:.2f}%"


def _baseline_public(baseline: dict[str, Any]) -> dict[str, Any]:
    return {key: baseline[key] for key in (
        "id", "chart_type", "kind", "label", "start", "end", "timezone", "day_boundary",
        "engine", "rules_version", "sample_unit", "sample_weight", "method", "hash",
    ) if key in baseline}


def _percentile(histogram: dict[str, float], raw_count: int) -> float:
    total = sum(histogram.values())
    if total <= 0:
        return 0.0
    below = sum(weight for count, weight in histogram.items() if int(count) < raw_count)
    equal = histogram.get(str(raw_count), 0.0)
    return round((below + equal / 2) / total * 100, 2)


def rule_indices(feature_ids: Iterable[str], baseline: dict[str, Any]) -> list[dict[str, Any]]:
    rule_ids = {feature_id.rsplit(".", 1)[-1] for feature_id in feature_ids}
    result = []
    for axis in AXES:
        contributors = [rule_id for rule_id in rule_ids if rule_id in RULE_BY_ID and RULE_BY_ID[rule_id].level == "core" and RULE_BY_ID[rule_id].axis == axis]
        count = len(contributors)
        histogram = baseline.get("axis_histograms", {}).get(axis, {})
        result.append({
            "dimension": axis,
            "raw_count": count,
            "percentile": _percentile(histogram, count),
            "contribution_rule_ids": sorted(contributors),
            "contribution_rules": [RULE_BY_ID[rule_id].name for rule_id in sorted(contributors)],
            "denominator": "命中的不同核心规则数量",
            "baseline_id": baseline["id"],
        })
    return result


def lookup_statistics(*, chart_type: str, baseline_id: str, feature_ids: Iterable[str]) -> dict[str, Any]:
    if chart_type not in BASELINE_IDS:
        raise ValueError(f"尚不支持的命盘统计类型: {chart_type}")
    baseline = load_baseline(baseline_id)
    if baseline["chart_type"] != chart_type:
        raise ValueError("命盘类型与统计基线不匹配。")
    normalized = list(dict.fromkeys(feature_ids))
    if any(not FEATURE_ID_RE.fullmatch(item) or not item.startswith(f"{chart_type}.") for item in normalized):
        raise ValueError("feature_ids 只能包含规范化统计特征 ID。")
    total = float(baseline["sample_weight"])
    metrics = []
    for feature_id in normalized:
        hit_weight = float(baseline.get("features", {}).get(feature_id, {}).get("hit_weight", 0))
        percentage = 0.0 if total <= 0 else hit_weight / total * 100
        metrics.append({
            "feature_id": feature_id,
            "hit_weight": hit_weight,
            "total_weight": total,
            "percentage": round(percentage, 6),
            "display_percentage": frequency_label(percentage),
            "level": frequency_level(percentage),
            "baseline_id": baseline["id"],
        })
    return {
        "baseline": _baseline_public(baseline),
        "rarity_metrics": metrics,
        "rule_indices": rule_indices(normalized, baseline) if chart_type == "bazi" else [],
        "disclaimer": "此处为指定规则与历法范围内的样本出现频率，并非真实人口比例，也不代表吉凶或命运确定性。",
    }


def statistics_for_shensha(hits: Iterable[dict[str, Any]], day_boundary: str) -> dict[str, Any]:
    baseline_id = BASELINE_IDS["bazi"].get(day_boundary, BASELINE_ID)
    return lookup_statistics(
        chart_type="bazi",
        baseline_id=baseline_id,
        feature_ids=[hit["feature_id"] for hit in hits],
    )
