from __future__ import annotations

import hashlib
import json
import re
from functools import lru_cache
from math import exp, log
from pathlib import Path
from typing import Any, Iterable, Mapping

from iching.core.bazi_structure import METRIC_DEFINITIONS, METRIC_REGISTRY_VERSION
from iching.core.metaphysics_consumer import CONSUMER_RULES_VERSION
from iching.core.shensha import REGISTRY_DIGEST


DATA_DIR = Path(__file__).with_name("data")
BASELINE_ID = "bazi-calendar-1924-2044-g3-forward"
BASELINE_IDS = {
    "bazi": {
        "forward": BASELINE_ID,
        "current": "bazi-calendar-1924-2044-g3-current",
    },
    "ziwei": {"default": "ziwei-calendar-1924-2044-v1"},
}
FEATURE_ID_RE = re.compile(r"^(bazi|ziwei)\.[a-z0-9_.-]{1,96}$")
BASELINE_SCHEMA_VERSION = 5
ZIWEI_RULES_VERSION = "ziwei-structural-2026.07-v2.1"
ZIWEI_CONSUMER_RULES_VERSION = "ziwei-consumer-c1"
ZIWEI_STANDARD_CONFIG_ID = "ziwei-standard-v1"
THEME_IDS = ("事业", "财富", "感情", "五行与承压结构")
ZIWEI_REGISTRY_DESCRIPTOR = {
    "rules_version": ZIWEI_RULES_VERSION,
    "consumer_rules_version": ZIWEI_CONSUMER_RULES_VERSION,
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
        "achievement",
        "archetype",
        "consumer_score_histogram",
        "structural_family",
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
    return _sha256_json({
        "shensha_registry_digest": REGISTRY_DIGEST,
        "metric_registry_version": METRIC_REGISTRY_VERSION,
        "metric_definitions": METRIC_DEFINITIONS,
    })


def metric_catalog_hash(catalog: Iterable[Mapping[str, Any]]) -> str:
    return _sha256_json(sorted((dict(item) for item in catalog), key=lambda item: str(item.get("id", ""))))


def ziwei_rules_registry_hash() -> str:
    return _sha256_json(ZIWEI_REGISTRY_DESCRIPTOR)


def _decode_consumer_histogram(value: Any) -> dict[str, float]:
    if isinstance(value, Mapping):
        try:
            return {str(score): float(weight) for score, weight in value.items()}
        except (TypeError, ValueError):
            return {}
    if not isinstance(value, str) or not value:
        return {}
    result: dict[str, float] = {}
    try:
        for entry in value.split(","):
            score, separator, weight = entry.partition(":")
            if not separator:
                return {}
            result[score] = float(weight)
    except (TypeError, ValueError):
        return {}
    return result


def _expected_config_id(baseline: Mapping[str, Any]) -> str:
    if baseline.get("chart_type") == "bazi":
        boundary = baseline.get("day_boundary")
        return f"bazi-canonical-calendar-1-asia-shanghai-{boundary}"
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
    if baseline.get("chart_type") == "bazi":
        required.update({"baseline_generation_version", "metric_catalog", "metric_catalog_hash"})
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
    if baseline.get("chart_type") == "bazi":
        metric_catalog = baseline.get("metric_catalog")
        if not isinstance(metric_catalog, list) or any(not isinstance(item, dict) for item in metric_catalog):
            raise BaselineCompatibilityError("统计基线指标目录无效，请重新生成基线。")
        if baseline.get("metric_catalog_hash") != metric_catalog_hash(metric_catalog):
            raise BaselineCompatibilityError("统计基线指标目录完整性校验失败，请重新生成基线。")
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
    consumer_scores = baseline.get("consumer_score_distributions")
    if baseline.get("chart_type") == "bazi" and isinstance(consumer_scores, dict) and consumer_scores.get("rules_version") == CONSUMER_RULES_VERSION:
        dimensions = {"overall", "career", "wealth", "relationship", "health"}
        global_scores = consumer_scores.get("global")
        cohorts = consumer_scores.get("cohorts")
        if not isinstance(global_scores, dict) or not isinstance(cohorts, dict):
            raise BaselineCompatibilityError("八字消费排名分布无效，请重新生成基线。")
        for gender in ("male", "female", "neutral"):
            histograms = global_scores.get(gender)
            if not isinstance(histograms, dict) or set(histograms) != dimensions:
                raise BaselineCompatibilityError("八字消费排名指标目录无效，请重新生成基线。")
            for encoded_histogram in histograms.values():
                histogram = _decode_consumer_histogram(encoded_histogram)
                if not histogram or abs(sum(histogram.values()) - float(sample_weight)) > tolerance:
                    raise BaselineCompatibilityError("八字消费排名全样本分母不一致，请重新生成基线。")
        cohort_total = 0.0
        for cohort in cohorts.values():
            if not isinstance(cohort, dict):
                raise BaselineCompatibilityError("八字消费排名同类样本无效，请重新生成基线。")
            cohort_weight: float | None = None
            for gender in ("male", "female", "neutral"):
                histograms = cohort.get(gender)
                if not isinstance(histograms, dict) or set(histograms) != dimensions:
                    raise BaselineCompatibilityError("八字消费排名同类指标目录无效，请重新生成基线。")
                for encoded_histogram in histograms.values():
                    histogram = _decode_consumer_histogram(encoded_histogram)
                    if not histogram:
                        raise BaselineCompatibilityError("八字消费排名同类直方图无效，请重新生成基线。")
                    total = sum(float(weight) for weight in histogram.values())
                    if cohort_weight is None:
                        cohort_weight = total
                    elif abs(total - cohort_weight) > tolerance:
                        raise BaselineCompatibilityError("八字消费排名同类分母不一致，请重新生成基线。")
            cohort_total += cohort_weight or 0.0
        if abs(cohort_total - float(sample_weight)) > tolerance:
            raise BaselineCompatibilityError("八字消费排名同类样本总量不一致，请重新生成基线。")
    consumer_features = baseline.get("consumer_features")
    if baseline.get("chart_type") == "bazi" and isinstance(consumer_features, dict) and consumer_features.get("rules_version") == CONSUMER_RULES_VERSION:
        feature_catalog = consumer_features.get("catalog")
        hit_weights = consumer_features.get("hit_weights")
        if not isinstance(feature_catalog, list) or not isinstance(hit_weights, dict):
            raise BaselineCompatibilityError("八字消费特征频率无效，请重新生成基线。")
        catalog_ids = {
            str(item.get("id", ""))
            for item in feature_catalog
            if isinstance(item, Mapping) and item.get("id")
        }
        if catalog_ids != set(hit_weights):
            raise BaselineCompatibilityError("八字消费特征目录与频率不一致，请重新生成基线。")
        if any(not isinstance(weight, (int, float)) or isinstance(weight, bool) or weight < 0 or weight > sample_weight for weight in hit_weights.values()):
            raise BaselineCompatibilityError("八字消费特征频率权重无效，请重新生成基线。")
    if baseline.get("chart_type") == "ziwei" and baseline.get("consumer_baseline") is not None:
        consumer = baseline["consumer_baseline"]
        if not isinstance(consumer, dict):
            raise BaselineCompatibilityError("紫微消费统计分布无效，请重新生成基线。")
        if consumer.get("rules_version") != ZIWEI_CONSUMER_RULES_VERSION:
            raise BaselineVersionMismatchError("紫微消费统计规则版本不兼容，请重新生成基线。")
        if consumer.get("hash") != payload_hash(consumer):
            raise BaselineCompatibilityError("紫微消费统计分布完整性校验失败，请重新生成基线。")
        score_keys = consumer.get("score_keys")
        expected_score_keys = {"overall", "career", "wealth", "relationship", "health"}
        if not isinstance(score_keys, list) or set(score_keys) != expected_score_keys:
            raise BaselineCompatibilityError("紫微消费统计指标目录无效，请重新生成基线。")
        histograms = consumer.get("histograms")
        cohort_histograms = consumer.get("cohort_histograms")
        cohort_weights = consumer.get("cohort_weights")
        if not isinstance(histograms, dict) or not isinstance(cohort_histograms, dict) or not isinstance(cohort_weights, dict):
            raise BaselineCompatibilityError("紫微消费统计直方图无效，请重新生成基线。")
        for score_key in expected_score_keys:
            histogram = histograms.get(score_key)
            if not isinstance(histogram, dict) or abs(sum(float(weight) for weight in histogram.values()) - float(sample_weight)) > tolerance:
                raise BaselineCompatibilityError("紫微消费统计全样本分母不一致，请重新生成基线。")
        if abs(sum(float(weight) for weight in cohort_weights.values()) - float(sample_weight)) > tolerance:
            raise BaselineCompatibilityError("紫微消费统计同类样本分母不一致，请重新生成基线。")
        for cohort_id, cohort_weight in cohort_weights.items():
            cohort = cohort_histograms.get(cohort_id)
            if not isinstance(cohort, dict):
                raise BaselineCompatibilityError("紫微消费统计同类样本缺失，请重新生成基线。")
            for score_key in expected_score_keys:
                histogram = cohort.get(score_key)
                if not isinstance(histogram, dict) or abs(sum(float(weight) for weight in histogram.values()) - float(cohort_weight)) > tolerance:
                    raise BaselineCompatibilityError("紫微消费统计同类直方图分母不一致，请重新生成基线。")


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
        "schema_version", "baseline_generation_version", "config_id", "feature_catalog_hash", "metric_catalog_hash", "rules_registry_hash",
        "unique_state_count", "weighted_unit", "time_index_weights", "gender_scope", "interval_semantics",
        "id", "chart_type", "kind", "label", "start", "end", "timezone", "day_boundary",
        "engine", "rules_version", "sample_unit", "sample_weight", "method", "hash",
    ) if key in baseline}
    public.setdefault("schema_version", 1)
    public.setdefault("weighted_unit", baseline.get("sample_unit", "sample"))
    if "rules_registry_hash" in baseline:
        public.setdefault("registry_hash", baseline["rules_registry_hash"])
    return public


def _ziwei_consumer_public(baseline: Mapping[str, Any], feature_ids: Iterable[str]) -> dict[str, Any] | None:
    """Return global histograms plus only the requested life-star cohort."""
    consumer = baseline.get("consumer_baseline")
    if not isinstance(consumer, Mapping):
        return None
    life_feature = next((item for item in feature_ids if item.startswith("ziwei.life_combo.")), None)
    cohort_id = life_feature.removeprefix("ziwei.") if life_feature else ""
    archetype_feature = next((item for item in feature_ids if item.startswith("ziwei.archetype.")), None)
    archetype_id = archetype_feature.removeprefix("ziwei.archetype.") if archetype_feature else ""
    cohort_histograms = consumer.get("cohort_histograms", {})
    cohort_weights = consumer.get("cohort_weights", {})
    selected_histogram = cohort_histograms.get(cohort_id) if isinstance(cohort_histograms, Mapping) else None
    selected_weight = cohort_weights.get(cohort_id) if isinstance(cohort_weights, Mapping) else None
    family_features = {
        f"life:{cohort_id.removeprefix('life_combo.')}" if cohort_id else "",
        f"archetype:{archetype_id}" if archetype_id else "",
    } - {""}
    structural_families = []
    for family in consumer.get("structural_families", []):
        if not isinstance(family, Mapping):
            continue
        features = {str(item) for item in family.get("features", [])}
        if str(family.get("id", "")).startswith("joint."):
            selected = bool(family_features) and family_features.issubset(features)
        else:
            selected = bool(archetype_id) and f"archetype:{archetype_id}" in features
        if selected:
            structural_families.append(dict(family))
    return {
        "schema_version": consumer.get("schema_version", 1),
        "id": consumer.get("id"),
        "rules_version": consumer.get("rules_version"),
        "score_keys": consumer.get("score_keys", []),
        "sample_weight": consumer.get("sample_weight"),
        "weighted_unit": consumer.get("weighted_unit"),
        "histograms": consumer.get("histograms", {}),
        "cohort_key": consumer.get("cohort_key"),
        "cohort_weights": {cohort_id: selected_weight} if cohort_id and selected_weight is not None else {},
        "cohort_histograms": {cohort_id: selected_histogram} if cohort_id and isinstance(selected_histogram, Mapping) else {},
        "structural_families": structural_families,
        "method": consumer.get("method"),
        "hash": consumer.get("hash"),
    }


def select_consumer_distributions(
    baseline: Mapping[str, Any],
    *,
    gender: str | None,
    cohort_key: str,
) -> dict[str, Any]:
    """Select only the live chart's compact global/cohort score histograms.

    The full baseline remains server-side; a chart snapshot receives at most
    ten small integer-score histograms instead of every cohort distribution.
    """
    package = baseline.get("consumer_score_distributions", {})
    if not isinstance(package, Mapping) or package.get("rules_version") != CONSUMER_RULES_VERSION:
        return {
            "status": "unavailable",
            "baseline_id": baseline.get("id"),
            "rules_version": package.get("rules_version") if isinstance(package, Mapping) else None,
            "global": {},
            "cohort": {},
        }
    requested_gender = gender if gender in {"male", "female", "neutral"} else "neutral"
    global_by_gender = package.get("global", {})
    cohorts = package.get("cohorts", {})
    if not isinstance(global_by_gender, Mapping) or not isinstance(cohorts, Mapping):
        return {"status": "unavailable", "baseline_id": baseline.get("id"), "global": {}, "cohort": {}}
    global_histograms = global_by_gender.get(requested_gender) or global_by_gender.get("neutral") or {}
    cohort_entry = cohorts.get(cohort_key, {}) if isinstance(cohorts.get(cohort_key, {}), Mapping) else {}
    cohort_histograms = cohort_entry.get(requested_gender) or cohort_entry.get("neutral") or {}
    status = "available" if isinstance(global_histograms, Mapping) and global_histograms else "unavailable"
    return {
        "status": status,
        "baseline_id": baseline.get("id"),
        "rules_version": package.get("rules_version"),
        "weighted_unit": package.get("weighted_unit", baseline.get("weighted_unit")),
        "cohort_key": cohort_key,
        "global": {
            str(key): _decode_consumer_histogram(histogram)
            for key, histogram in global_histograms.items()
        } if isinstance(global_histograms, Mapping) else {},
        "cohort": {
            str(key): _decode_consumer_histogram(histogram)
            for key, histogram in cohort_histograms.items()
        } if isinstance(cohort_histograms, Mapping) else {},
    }


def select_consumer_feature_metrics(
    baseline: Mapping[str, Any],
    feature_ids: Iterable[str],
) -> list[dict[str, Any]]:
    package = baseline.get("consumer_features", {})
    if not isinstance(package, Mapping) or package.get("rules_version") != CONSUMER_RULES_VERSION:
        return []
    catalog = {
        str(item.get("id", "")): item
        for item in package.get("catalog", ())
        if isinstance(item, Mapping) and item.get("id")
    }
    weights = package.get("hit_weights", {})
    total = float(baseline.get("sample_weight", 0) or 0)
    if not isinstance(weights, Mapping) or total <= 0:
        return []
    result = []
    for feature_id in dict.fromkeys(str(item) for item in feature_ids if item):
        supported = feature_id in catalog
        hit_weight = float(weights.get(feature_id, 0) or 0) if supported else 0.0
        percentage = hit_weight / total * 100 if supported else 0.0
        result.append({
            "feature_id": feature_id,
            "kind": str(catalog.get(feature_id, {}).get("kind", "")),
            "title": str(catalog.get(feature_id, {}).get("title", "")),
            "status": "observed" if hit_weight > 0 else "zero" if supported else "unsupported",
            "hit_weight": hit_weight,
            "total_weight": total,
            "percentage": round(percentage, 6),
            "display_percentage": frequency_label(percentage) if supported else "—",
            "baseline_id": baseline.get("id"),
        })
    return result


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
                ordered_histogram = [
                    {
                        "value": int(key),
                        "weight": float(weight),
                        "percentage": round(float(weight) / total * 100, 4),
                    }
                    for key, weight in sorted(histogram.items(), key=lambda pair: int(pair[0]))
                    if float(weight) > 0
                ]
                probabilities = [entry["weight"] / total for entry in ordered_histogram]
                entropy = -sum(probability * log(probability) for probability in probabilities if probability > 0)
                support_size = len(probabilities)
                normalized_entropy = entropy / log(support_size) if support_size > 1 else 0.0
                effective_support = exp(entropy) if probabilities else 0.0
                if exact_percentage <= 10 and normalized_entropy >= 0.70 and effective_support >= 6:
                    resolution = "high"
                elif exact_percentage <= 25 and normalized_entropy >= 0.45 and effective_support >= 3:
                    resolution = "medium"
                else:
                    resolution = "low"
                lower_percentage = lower / total * 100
                higher_percentage = higher / total * 100
                metric_type = str(metric.get("metric_type", "ordinal"))
                common_distribution = {
                    **dict(metric),
                    "metric_type": metric_type,
                    "status": "observed" if exact_weight > 0 else "zero",
                    "exact_weight": round(exact_weight, 6),
                    "total_weight": total,
                    "exact_percentage": round(exact_percentage, 6),
                    "display_percentage": frequency_label(exact_percentage),
                    "same_mass": round(exact_percentage, 4),
                    "support_size": support_size,
                    "normalized_entropy": round(normalized_entropy, 6),
                    "effective_support": round(effective_support, 6),
                    "resolution": resolution,
                    "histogram": ordered_histogram,
                    "baseline_id": baseline.get("id"),
                    "method": "weighted_empirical_metric_distribution",
                }
                if metric_type == "binary":
                    hit_weight = float(histogram.get("1", 0))
                    comparisons.append({
                        **common_distribution,
                        "comparison_mode": "incidence",
                        "hit_percentage": round(hit_weight / total * 100, 4),
                    })
                    continue
                comparisons.append({
                    **common_distribution,
                    "comparison_mode": "rank_interval",
                    "lower_percentage": round(lower_percentage, 4),
                    "same_percentage": round(exact_percentage, 4),
                    "higher_percentage": round(higher_percentage, 4),
                    "rank_interval": {
                        "lower": round(lower_percentage, 4),
                        "upper": round(lower_percentage + exact_percentage, 4),
                    },
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
    result = {
        "status": "available",
        "unavailable_reason": None,
        "baseline": _baseline_public(baseline),
        "rarity_metrics": metrics,
        "theme_profile": [],
        "disclaimer": "此处为指定规则、配置与历法范围内的边际出现频率，并非真实人口比例、联合命盘概率，也不代表吉凶或命运确定性。",
    }
    if chart_type == "ziwei" and isinstance(baseline.get("consumer_baseline"), dict):
        # Compact histograms only: no birth dates, raw charts, names, or sample
        # rows are returned to the client.
        result["consumer_baseline"] = _ziwei_consumer_public(baseline, normalized)
    return result


def statistics_for_shensha(
    hits: Iterable[dict[str, Any]],
    day_boundary: str,
    *,
    theme_profiles: Iterable[Mapping[str, Any]] = (),
    gender: str | None = None,
    day_master: str = "",
    month_command: str = "",
    consumer_feature_ids: Iterable[str] = (),
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
        result["consumer_distributions"] = select_consumer_distributions(
            baseline,
            gender=gender,
            cohort_key=f"{day_master}-{month_command}" if day_master and month_command else "",
        )
        result["consumer_feature_metrics"] = select_consumer_feature_metrics(
            baseline,
            consumer_feature_ids,
        )
    except RuntimeError:
        result["theme_profiles"] = [
            {**dict(profile), "comparisons": []}
            for profile in theme_profiles
        ]
        result["consumer_distributions"] = {"status": "unavailable", "global": {}, "cohort": {}}
        result["consumer_feature_metrics"] = []
    return result
