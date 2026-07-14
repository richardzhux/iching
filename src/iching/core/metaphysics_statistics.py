from __future__ import annotations

import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Mapping

from iching.core.shensha import REGISTRY_DIGEST


DATA_DIR = Path(__file__).with_name("data")
BASELINE_ID = "bazi-calendar-1924-2044-v2-forward"
BASELINE_IDS = {
    "bazi": {
        "forward": BASELINE_ID,
        "current": "bazi-calendar-1924-2044-v2-current",
    },
    "ziwei": {"default": "ziwei-calendar-1924-2044-v1"},
}
FEATURE_ID_RE = re.compile(r"^(bazi|ziwei)\.[a-z0-9_.-]{1,96}$")
BASELINE_SCHEMA_VERSION = 4
ZIWEI_RULES_VERSION = "ziwei-structural-2026.07-v2.1"
ZIWEI_STANDARD_CONFIG_ID = "ziwei-standard-v1"
THEME_IDS = ("事业", "财富", "感情", "健康")
ZIWEI_REGISTRY_DESCRIPTOR = {
    "rules_version": ZIWEI_RULES_VERSION,
    "encoding_version": 1,
    "feature_families": [
        "life_combo",
        "body_branch",
        "five_elements",
        "empty_palaces",
        "brightness",
        "mutagen_palace_index",
        "auspicious_palaces",
        "auspicious_max_density",
        "challenging_palaces",
        "challenging_max_density",
    ],
}


class BaselineCompatibilityError(RuntimeError):
    """Raised when a baseline is present but unsafe to use with this runtime."""

    status = "unavailable"


class BaselineVersionMismatchError(BaselineCompatibilityError):
    """Raised when baseline provenance does not match the current registry/config."""

    status = "version_mismatch"


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_json(value: Any) -> str:
    return f"sha256:{hashlib.sha256(_canonical_json(value).encode()).hexdigest()}"


def payload_hash(payload: Mapping[str, Any]) -> str:
    canonical_payload = {key: value for key, value in payload.items() if key != "hash"}
    return _sha256_json(canonical_payload)


def feature_catalog_hash(feature_ids: Iterable[str]) -> str:
    return _sha256_json(sorted(set(feature_ids)))


def bazi_rules_registry_hash() -> str:
    return REGISTRY_DIGEST


def ziwei_rules_registry_hash() -> str:
    return _sha256_json(ZIWEI_REGISTRY_DESCRIPTOR)


def _expected_config_id(baseline: Mapping[str, Any]) -> str:
    if baseline.get("chart_type") == "bazi":
        boundary = baseline.get("day_boundary")
        return f"bazi-sxtwl-2.0.7-asia-shanghai-{boundary}-v1"
    return ZIWEI_STANDARD_CONFIG_ID


def _validate_v3_baseline(baseline: dict[str, Any]) -> None:
    required_schema = BASELINE_SCHEMA_VERSION if baseline.get("chart_type") == "bazi" else 3
    if int(baseline.get("schema_version", 1)) < required_schema:
        raise BaselineVersionMismatchError("统计基线为旧版 schema，请重新生成后再启用统计。")
    required = {
        "config_id",
        "feature_catalog",
        "feature_catalog_hash",
        "rules_registry_hash",
        "unique_state_count",
        "sample_weight",
        "weighted_unit",
        "hash",
    }
    missing = sorted(required - baseline.keys())
    if missing:
        raise BaselineCompatibilityError(f"统计基线缺少 schema v3 字段: {', '.join(missing)}")
    if baseline["hash"] != payload_hash(baseline):
        raise BaselineCompatibilityError("统计基线完整性校验失败，请重新生成基线。")
    catalog = baseline.get("feature_catalog")
    if not isinstance(catalog, list) or any(not isinstance(item, str) for item in catalog):
        raise BaselineCompatibilityError("统计基线特征目录无效，请重新生成基线。")
    if baseline["feature_catalog_hash"] != feature_catalog_hash(catalog):
        raise BaselineCompatibilityError("统计基线特征目录完整性校验失败，请重新生成基线。")
    expected_registry = (
        bazi_rules_registry_hash()
        if baseline.get("chart_type") == "bazi"
        else ziwei_rules_registry_hash()
    )
    if baseline["rules_registry_hash"] != expected_registry:
        raise BaselineVersionMismatchError("统计基线规则注册表不兼容，请重新生成基线。")
    if baseline["config_id"] != _expected_config_id(baseline):
        raise BaselineVersionMismatchError("统计基线配置与当前运行时不兼容，请选择匹配的基线。")
    if not isinstance(baseline["unique_state_count"], int) or baseline["unique_state_count"] <= 0:
        raise BaselineCompatibilityError("统计基线 unique_state_count 无效，请重新生成基线。")
    if not isinstance(baseline["weighted_unit"], str) or not baseline["weighted_unit"]:
        raise BaselineCompatibilityError("统计基线 weighted_unit 无效，请重新生成基线。")
    sample_weight = baseline["sample_weight"]
    if not isinstance(sample_weight, (int, float)) or isinstance(sample_weight, bool) or sample_weight <= 0:
        raise BaselineCompatibilityError("统计基线 sample_weight 无效，请重新生成基线。")
    features = baseline.get("features")
    if not isinstance(features, dict):
        raise BaselineCompatibilityError("统计基线 features 无效，请重新生成基线。")
    for feature_id in catalog:
        feature = features.get(feature_id, {"hit_weight": 0})
        hit_weight = feature.get("hit_weight") if isinstance(feature, dict) else None
        if (
            not isinstance(hit_weight, (int, float))
            or isinstance(hit_weight, bool)
            or hit_weight < 0
            or hit_weight > sample_weight
        ):
            raise BaselineCompatibilityError(f"统计基线特征权重无效: {feature_id}")
    tolerance = max(0.001, float(sample_weight) * 1e-9)
    metric_groups = baseline.get("theme_metric_weights_by_gender", {})
    if baseline.get("chart_type") == "bazi" and not metric_groups:
        raise BaselineCompatibilityError("统计基线缺少主题结构指标分布，请重新生成基线。")
    for themes in metric_groups.values():
        if not isinstance(themes, dict):
            raise BaselineCompatibilityError("统计基线主题结构分布无效，请重新生成基线。")
        for metrics in themes.values():
            if not isinstance(metrics, dict):
                raise BaselineCompatibilityError("统计基线主题结构分布无效，请重新生成基线。")
            for histogram in metrics.values():
                if not isinstance(histogram, dict):
                    raise BaselineCompatibilityError("统计基线主题结构分布无效，请重新生成基线。")
                total = sum(float(weight) for weight in histogram.values())
                if abs(total - float(sample_weight)) > tolerance:
                    raise BaselineCompatibilityError("统计基线主题结构分布分母与样本权重不一致。")


@lru_cache(maxsize=8)
def load_baseline(baseline_id: str) -> dict[str, Any]:
    if baseline_id not in {item for values in BASELINE_IDS.values() for item in values.values()}:
        raise ValueError(f"未知统计基线: {baseline_id}")
    path = DATA_DIR / f"{baseline_id}.json"
    if not path.exists():
        raise RuntimeError(f"统计基线尚未生成: {baseline_id}")
    try:
        baseline = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise BaselineCompatibilityError(f"统计基线无法读取: {baseline_id}") from exc
    if baseline.get("id") != baseline_id:
        raise BaselineCompatibilityError("统计基线 ID 与文件名不匹配，请重新生成基线。")
    _validate_v3_baseline(baseline)
    return baseline


def frequency_level(percentage: float) -> str:
    if percentage >= 20:
        return "common"
    if percentage >= 5:
        return "less_common"
    if percentage >= 1:
        return "rare"
    return "very_rare"


def frequency_label(percentage: float) -> str:
    if percentage == 0:
        return "0%"
    if percentage < 0.01:
        return "<0.01%"
    return f"{percentage:.2f}%"


def _baseline_public(baseline: dict[str, Any]) -> dict[str, Any]:
    public = {key: baseline[key] for key in (
        "schema_version", "config_id", "feature_catalog_hash", "rules_registry_hash",
        "unique_state_count", "weighted_unit", "time_index_weights", "gender_scope", "interval_semantics",
        "id", "chart_type", "kind", "label", "start", "end", "timezone", "day_boundary",
        "engine", "rules_version", "sample_unit", "sample_weight", "method", "hash",
    ) if key in baseline}
    public.setdefault("schema_version", 1)
    public.setdefault("weighted_unit", baseline.get("sample_unit", "sample"))
    if "rules_registry_hash" in baseline:
        public.setdefault("registry_hash", baseline["rules_registry_hash"])
    return public


def apply_theme_comparisons(
    profiles: Iterable[Mapping[str, Any]],
    baseline: Mapping[str, Any],
    *,
    gender: str | None,
) -> list[dict[str, Any]]:
    """Compare each transparent structural metric; never collapse them into one score."""
    metrics_by_gender = baseline.get("theme_metric_weights_by_gender", {})
    metric_group = metrics_by_gender.get(gender) or metrics_by_gender.get("neutral") or {}
    total = float(baseline.get("sample_weight", 0))
    result: list[dict[str, Any]] = []
    for profile in profiles:
        item = dict(profile)
        theme = str(item.get("theme", ""))
        theme_histograms = metric_group.get(theme, {})
        comparisons = []
        for metric in item.get("structure_metrics", ()):
            metric_id = str(metric.get("metric_id", ""))
            value = int(metric.get("value", 0))
            histogram = theme_histograms.get(metric_id, {}) if isinstance(theme_histograms, Mapping) else {}
            exact_weight = float(histogram.get(str(value), 0)) if isinstance(histogram, Mapping) else 0.0
            if histogram and total > 0:
                lower = sum(float(weight) for key, weight in histogram.items() if int(key) < value)
                higher = sum(float(weight) for key, weight in histogram.items() if int(key) > value)
                exact_percentage = exact_weight / total * 100
                comparisons.append({
                    **dict(metric),
                    "status": "observed" if exact_weight > 0 else "zero",
                    "exact_weight": round(exact_weight, 6),
                    "total_weight": total,
                    "exact_percentage": round(exact_percentage, 6),
                    "display_percentage": frequency_label(exact_percentage),
                    "lower_percentage": round(lower / total * 100, 4),
                    "same_percentage": round(exact_percentage, 4),
                    "higher_percentage": round(higher / total * 100, 4),
                    "baseline_id": baseline.get("id"),
                    "method": "weighted_empirical_metric_distribution",
                })
            else:
                comparisons.append({**dict(metric), "status": "unsupported", "display_percentage": "—", "lower_percentage": 0.0, "same_percentage": 0.0, "higher_percentage": 0.0, "baseline_id": baseline.get("id"), "method": "weighted_empirical_metric_distribution"})
        item["comparisons"] = comparisons
        result.append(item)
    return result


def _unavailable_statistics(
    *,
    chart_type: str,
    baseline_id: str,
    feature_ids: Iterable[str],
    reason: str,
    status: str,
) -> dict[str, Any]:
    metrics = [{
        "feature_id": feature_id,
        "hit_weight": 0.0,
        "total_weight": 0.0,
        "percentage": 0.0,
        "display_percentage": "—",
        "level": "unavailable",
        "status": "unsupported",
        "baseline_id": baseline_id,
    } for feature_id in feature_ids]
    return {
        "status": status,
        "unavailable_reason": reason,
        "baseline": {
            "schema_version": BASELINE_SCHEMA_VERSION,
            "id": baseline_id,
            "chart_type": chart_type,
            "kind": "calendar_sample_frequency",
            "label": "统计基线不可用",
            "sample_unit": "unavailable",
            "weighted_unit": "unavailable",
            "sample_weight": 0.0,
            "method": "",
            "hash": "",
        },
        "rarity_metrics": metrics,
        "theme_profile": [],
        "disclaimer": f"统计基线当前不可用：{reason} 未返回任何频率、百分位或吉凶结论。",
    }


def lookup_statistics(*, chart_type: str, baseline_id: str, feature_ids: Iterable[str]) -> dict[str, Any]:
    if chart_type not in BASELINE_IDS:
        raise ValueError(f"尚不支持的命盘统计类型: {chart_type}")
    normalized = list(dict.fromkeys(feature_ids))
    if any(not FEATURE_ID_RE.fullmatch(item) or not item.startswith(f"{chart_type}.") for item in normalized):
        raise ValueError("feature_ids 只能包含规范化统计特征 ID。")
    try:
        baseline = load_baseline(baseline_id)
    except RuntimeError as exc:
        return _unavailable_statistics(
            chart_type=chart_type,
            baseline_id=baseline_id,
            feature_ids=normalized,
            reason=str(exc),
            status=getattr(exc, "status", "unavailable"),
        )
    if baseline["chart_type"] != chart_type:
        raise ValueError("命盘类型与统计基线不匹配。")
    total = float(baseline["sample_weight"])
    catalog = set(baseline.get("feature_catalog", baseline.get("features", {}).keys()))
    metrics = []
    for feature_id in normalized:
        supported = feature_id in catalog
        hit_weight = float(baseline.get("features", {}).get(feature_id, {}).get("hit_weight", 0)) if supported else 0.0
        percentage = 0.0 if total <= 0 else hit_weight / total * 100
        status = "unsupported" if not supported else ("observed" if hit_weight > 0 else "zero")
        metrics.append({
            "feature_id": feature_id,
            "hit_weight": hit_weight,
            "total_weight": total,
            "percentage": round(percentage, 6),
            "display_percentage": "—" if status == "unsupported" else frequency_label(percentage),
            "level": frequency_level(percentage) if status == "observed" else "unavailable",
            "status": status,
            "baseline_id": baseline["id"],
        })
    return {
        "status": "available",
        "unavailable_reason": None,
        "baseline": _baseline_public(baseline),
        "rarity_metrics": metrics,
        "theme_profile": [],
        "disclaimer": "此处为指定规则、配置与历法范围内的边际出现频率，并非真实人口比例、联合命盘概率，也不代表吉凶或命运确定性。",
    }


def statistics_for_shensha(
    hits: Iterable[dict[str, Any]],
    day_boundary: str,
    *,
    theme_profiles: Iterable[Mapping[str, Any]] = (),
    gender: str | None = None,
) -> dict[str, Any]:
    baseline_id = BASELINE_IDS["bazi"].get(day_boundary, BASELINE_ID)
    result = lookup_statistics(
        chart_type="bazi",
        baseline_id=baseline_id,
        feature_ids=[hit["feature_id"] for hit in hits],
    )
    try:
        baseline = load_baseline(baseline_id)
        result["theme_profiles"] = apply_theme_comparisons(theme_profiles, baseline, gender=gender)
    except RuntimeError:
        result["theme_profiles"] = [
            {**dict(profile), "comparisons": []}
            for profile in theme_profiles
        ]
    return result
