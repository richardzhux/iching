from __future__ import annotations

import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Mapping

from iching.core.shensha import AXES, REGISTRY_DIGEST, RULE_BY_ID


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
BASELINE_SCHEMA_VERSION = 3
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
    if int(baseline.get("schema_version", 1)) < BASELINE_SCHEMA_VERSION:
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
    for histograms in baseline.get("theme_histograms_by_gender", {}).values():
        if not isinstance(histograms, dict):
            raise BaselineCompatibilityError("统计基线主题直方图无效，请重新生成基线。")
        for histogram in histograms.values():
            if not isinstance(histogram, dict):
                raise BaselineCompatibilityError("统计基线主题直方图无效，请重新生成基线。")
            total = sum(float(weight) for weight in histogram.values())
            if abs(total - float(sample_weight)) > tolerance:
                raise BaselineCompatibilityError("统计基线主题直方图分母与样本权重不一致。")


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


def _legacy_theme_families(baseline: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if baseline.get("chart_type") != "bazi" or not baseline.get("axis_histograms"):
        return {}
    return {
        axis: {
            "label": axis,
            "feature_ids": sorted(
                f"bazi.shensha.{rule.rule_id}"
                for rule in RULE_BY_ID.values()
                if rule.level == "core" and rule.axis == axis
            ),
        }
        for axis in AXES
    }


def theme_profile(feature_ids: Iterable[str], baseline: dict[str, Any]) -> list[dict[str, Any]]:
    families = baseline.get("theme_families") or _legacy_theme_families(baseline)
    histograms = baseline.get("theme_histograms") or baseline.get("axis_histograms", {})
    selected = set(feature_ids)
    result = []
    for theme_id, definition in families.items():
        if not definition.get("feature_ids"):
            continue
        family_ids = set(definition.get("feature_ids", []))
        contributors = sorted(selected & family_ids)
        histogram = histograms.get(theme_id, {})
        reference_weight = float(sum(histogram.values()))
        result.append({
            "theme_id": theme_id,
            "label": definition.get("label", theme_id),
            "raw_count": len(contributors),
            "percentile": _percentile(histogram, len(contributors)),
            "contribution_feature_ids": contributors,
            "reference_weight": reference_weight,
            "percentile_method": "weighted_midrank",
            "baseline_id": baseline["id"],
        })
    return result


def apply_theme_percentiles(
    profiles: Iterable[Mapping[str, Any]],
    baseline: Mapping[str, Any],
    *,
    gender: str | None,
) -> list[dict[str, Any]]:
    """Attach a density percentile to already-derived structural evidence profiles."""
    histograms_by_gender = baseline.get("theme_histograms_by_gender", {})
    histogram_group = histograms_by_gender.get(gender) or histograms_by_gender.get("neutral") or {}
    result: list[dict[str, Any]] = []
    for profile in profiles:
        item = dict(profile)
        theme = str(item.get("theme", ""))
        histogram = histogram_group.get(theme, {})
        if histogram:
            percentile = _percentile(histogram, int(item.get("raw_family_count", 0)))
            item["activity_percentile"] = percentile
            item["percentile_label"] = f"第 {percentile:.0f} 百分位"
            item["baseline_id"] = baseline.get("id")
            item["percentile_method"] = "weighted_midrank_of_evidence_family_count"
        else:
            item["activity_percentile"] = None
            item["percentile_label"] = "暂无结构基线"
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
        "rule_indices": [],
        "rule_indices_deprecated": True,
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
    supported_feature_ids = [feature_id for feature_id in normalized if feature_id in catalog]
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
    legacy_indices = (
        rule_indices(supported_feature_ids, baseline)
        if chart_type == "bazi" and int(baseline.get("schema_version", 1)) < BASELINE_SCHEMA_VERSION
        else []
    )
    return {
        "status": "available",
        "unavailable_reason": None,
        "baseline": _baseline_public(baseline),
        "rarity_metrics": metrics,
        "theme_profile": theme_profile(supported_feature_ids, baseline),
        "rule_indices": legacy_indices,
        "rule_indices_deprecated": True,
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
        result["theme_profiles"] = apply_theme_percentiles(theme_profiles, baseline, gender=gender)
    except RuntimeError:
        result["theme_profiles"] = [
            {**dict(profile), "activity_percentile": None, "percentile_label": "统计暂时不可用"}
            for profile in theme_profiles
        ]
    return result
