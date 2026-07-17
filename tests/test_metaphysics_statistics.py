from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

import iching.core.metaphysics_statistics as statistics
from iching.core.bazi_rules.registry import load_packaged_shen_registry
from iching.core.bazi_patterns import assess_patterns
from iching.core.bazi_structure import METRIC_DEFINITIONS, build_structure_profile
from iching.core.metaphysics import _seasonal_status
from iching.core.metaphysics_consumer import (
    CONSUMER_RULES_VERSION,
    consumer_feature_records,
)
from iching.core.metaphysics_statistics import (
    BASELINE_ID,
    frequency_label,
    lookup_statistics,
)
from iching.core.shensha import RULES_VERSION
from iching.web.api.main import app


client = TestClient(app)
ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from generate_bazi_baseline import (  # noqa: E402
    _canonical_consumer_feature_metadata,
    _config_id,
    _feature_catalog,
    _pattern_bundle_identity,
    _pillars as baseline_pillars,
    _pillars_from_state_key,
    _replace_canonical_pattern_features,
    REFRESH_SOURCE_CONSUMER_RULES_VERSION,
    REFRESH_SOURCE_PATTERN_BUNDLE_DIGEST,
    REFRESH_SOURCE_RULES_REGISTRY_HASH,
    _validate_pattern_refresh_source,
    _validate_promotion_source,
    promote_g3_payload,
)


@pytest.fixture(autouse=True)
def clear_baseline_cache():
    statistics.load_baseline.cache_clear()
    yield
    statistics.load_baseline.cache_clear()


def test_frequency_labels_do_not_render_false_zeroes() -> None:
    assert frequency_label(0.0) == "0%"
    assert frequency_label(0.009) == "<0.01%"
    assert frequency_label(0.5) == "0.50%"
    assert frequency_label(12.345) == "12.35%"


def test_baseline_generator_uses_the_live_exact_lichun_boundary() -> None:
    zone = ZoneInfo("Asia/Shanghai")
    before = baseline_pillars(datetime(2024, 2, 4, 10, tzinfo=zone), "forward")
    after = baseline_pillars(datetime(2024, 2, 4, 17, tzinfo=zone), "forward")

    assert [item["text"] for item in before[:2]] == ["癸卯", "乙丑"]
    assert [item["text"] for item in after[:2]] == ["甲辰", "丙寅"]


def test_baseline_lookup_returns_denominator_and_version() -> None:
    result = lookup_statistics(
        chart_type="bazi",
        baseline_id=BASELINE_ID,
        feature_ids=["bazi.shensha.wenchang", "bazi.shensha.yima"],
    )

    assert result["baseline"]["id"] == BASELINE_ID
    assert result["baseline"]["sample_weight"] > 0
    assert result["baseline"]["hash"]
    assert result["status"] == "available"
    assert len(result["rarity_metrics"]) == 2
    assert all(
        metric["total_weight"] == result["baseline"]["sample_weight"]
        for metric in result["rarity_metrics"]
    )
    assert all(metric["status"] == "observed" for metric in result["rarity_metrics"])
    assert all(
        metric["level"] in {"common", "less_common", "rare", "very_rare"}
        for metric in result["rarity_metrics"]
    )


def _write_v6_baseline(tmp_path, *, registry_hash: str | None = None) -> None:
    catalog = ["bazi.shensha.wenchang", "bazi.shensha.yima"]
    pattern_registry = load_packaged_shen_registry()
    payload = {
        "schema_version": 6,
        "id": BASELINE_ID,
        "chart_type": "bazi",
        "kind": "calendar_sample_frequency",
        "label": "test baseline",
        "start": "2000-01-01T00:00:00+08:00",
        "end": "2000-01-01T00:10:00+08:00",
        "timezone": "Asia/Shanghai",
        "day_boundary": "forward",
        "config_id": "bazi-canonical-calendar-1-asia-shanghai-forward",
        "engine": "canonical-calendar-1",
        "baseline_generation_version": 4,
        "pattern_bundle_id": pattern_registry.bundle_id,
        "pattern_bundle_digest": pattern_registry.bundle_digest,
        "rules_version": "shensha-2026.07-v2",
        "rules_registry_hash": registry_hash or statistics.bazi_rules_registry_hash(),
        "feature_catalog": catalog,
        "feature_catalog_hash": statistics.feature_catalog_hash(catalog),
        "metric_catalog": [
            statistics.METRIC_DEFINITIONS[key]
            for key in sorted(statistics.METRIC_DEFINITIONS)
        ],
        "metric_catalog_hash": statistics.metric_catalog_hash(
            [
                statistics.METRIC_DEFINITIONS[key]
                for key in sorted(statistics.METRIC_DEFINITIONS)
            ]
        ),
        "unique_state_count": 2,
        "sample_unit": "minute",
        "weighted_unit": "minute",
        "sample_weight": 10,
        "method": "test",
        "features": {"bazi.shensha.wenchang": {"hit_weight": 5}},
        "theme_metric_weights_by_gender": {
            gender: {
                theme: {"metric": {"0": 4, "1": 6}} for theme in statistics.THEME_IDS
            }
            for gender in ("male", "female", "neutral")
        },
    }
    payload["hash"] = statistics.payload_hash(payload)
    (tmp_path / f"{BASELINE_ID}.json").write_text(
        json.dumps(payload, ensure_ascii=False)
    )


def test_catalog_statuses_distinguish_zero_and_unsupported(
    tmp_path, monkeypatch
) -> None:
    _write_v6_baseline(tmp_path)
    monkeypatch.setattr(statistics, "DATA_DIR", tmp_path)
    statistics.load_baseline.cache_clear()

    result = lookup_statistics(
        chart_type="bazi",
        baseline_id=BASELINE_ID,
        feature_ids=[
            "bazi.shensha.wenchang",
            "bazi.shensha.yima",
            "bazi.shensha.not_in_catalog",
        ],
    )

    observed, zero, unsupported = result["rarity_metrics"]
    assert observed["status"] == "observed"
    assert {
        key: zero[key]
        for key in ("status", "display_percentage", "percentage", "hit_weight")
    } == {
        "status": "zero",
        "display_percentage": "0%",
        "percentage": 0.0,
        "hit_weight": 0.0,
    }
    assert unsupported["status"] == "unsupported"
    assert unsupported["display_percentage"] == "—"
    assert unsupported["level"] == "unavailable"


def test_metric_distribution_replaces_family_count_percentile(
    tmp_path, monkeypatch
) -> None:
    _write_v6_baseline(tmp_path)
    monkeypatch.setattr(statistics, "DATA_DIR", tmp_path)
    statistics.load_baseline.cache_clear()

    result = lookup_statistics(
        chart_type="bazi",
        baseline_id=BASELINE_ID,
        feature_ids=["bazi.shensha.yima"],
    )

    assert "rule_indices" not in result
    assert result["theme_profile"] == []
    comparison = statistics.apply_theme_comparisons(
        [
            {
                "theme": "事业",
                "structure_metrics": [
                    {"metric_id": "metric", "label": "指标", "value": 1, "unit": "项"}
                ],
            }
        ],
        statistics.load_baseline(BASELINE_ID),
        gender="male",
    )[0]["comparisons"][0]
    assert comparison["same_percentage"] == 60
    assert comparison["lower_percentage"] == 40
    assert comparison["higher_percentage"] == 0
    assert "percentile" not in comparison
    assert comparison["rank_interval"] == {"lower": 40.0, "upper": 100.0}
    assert comparison["same_mass"] == 60.0
    assert comparison["support_size"] == 2
    assert comparison["histogram"] == [
        {"value": 0, "weight": 4.0, "percentage": 40.0},
        {"value": 1, "weight": 6.0, "percentage": 60.0},
    ]
    assert comparison["resolution"] == "low"
    assert comparison["display_mode"] == "common_value"
    assert "%" not in comparison["display_label"]

    binary = statistics.apply_theme_comparisons(
        [
            {
                "theme": "事业",
                "structure_metrics": [
                    {
                        "metric_id": "metric",
                        "label": "是否命中",
                        "value": 1,
                        "unit": "是否命中",
                        "metric_type": "binary",
                    }
                ],
            }
        ],
        statistics.load_baseline(BASELINE_ID),
        gender="male",
    )[0]["comparisons"][0]
    assert binary["comparison_mode"] == "incidence"
    assert binary["display_mode"] == "incidence"
    assert binary["display_label"] == "出现率 60.00%"
    assert binary["hit_percentage"] == 60.0
    assert "rank_interval" not in binary
    assert "lower_percentage" not in binary


def _theme_comparison(
    *,
    theme: str,
    metric_id: str,
    value: int,
    histogram: dict[str, float],
    metric_type: str = "ordinal",
) -> dict:
    definition = statistics.METRIC_DEFINITIONS[f"{theme}.{metric_id}"]
    baseline = {
        "id": "test-semantic-baseline",
        "sample_weight": sum(histogram.values()),
        "theme_metric_weights_by_gender": {
            "neutral": {theme: {metric_id: histogram}},
        },
    }
    profile = {
        "theme": theme,
        "structure_metrics": [
            {
                "definition_id": definition["id"],
                "metric_id": metric_id,
                "label": definition["label"],
                "value": value,
                "unit": "是否命中" if metric_type == "binary" else "项",
                "metric_type": metric_type,
            }
        ],
    }
    return statistics.apply_theme_comparisons(
        [profile],
        baseline,
        gender="neutral",
    )[0]["comparisons"][0]


def test_ordered_metrics_expose_inclusive_tail_only_at_high_resolution() -> None:
    histogram = {
        "0": 15,
        "1": 15,
        "2": 15,
        "3": 15,
        "4": 15,
        "5": 10,
        "6": 5,
        "7": 10,
    }

    high = _theme_comparison(
        theme="财富",
        metric_id="visible_wealth_count",
        value=6,
        histogram=histogram,
    )
    assert high["resolution"] == "high"
    assert high["display_mode"] == "exact_tail"
    assert high["display_direction"] == "high"
    assert high["semantic_pole"] == "财富表达更外显"
    assert high["tail_side"] == "upper"
    assert high["tail_percentage"] == 15.0
    assert high["upper_tail_percentage"] == 15.0
    assert high["display_label"] == "财富表达更外显 · 前约 15.00%"

    low = _theme_comparison(
        theme="财富",
        metric_id="visible_wealth_count",
        value=0,
        histogram={
            "0": 5,
            "1": 15,
            "2": 15,
            "3": 15,
            "4": 15,
            "5": 15,
            "6": 10,
            "7": 10,
        },
    )
    assert low["resolution"] == "high"
    assert low["display_mode"] == "exact_tail"
    assert low["display_direction"] == "low"
    assert low["semantic_pole"] == "财富表达偏潜藏"
    assert low["tail_side"] == "lower"
    assert low["tail_percentage"] == 5.0
    assert low["lower_tail_percentage"] == 5.0
    assert low["display_label"] == "财富表达偏潜藏 · 低位约 5.00%"


def test_ordered_metrics_suppress_precision_at_medium_and_low_resolution() -> None:
    threshold = _theme_comparison(
        theme="事业",
        metric_id="relation_count",
        value=9,
        histogram={str(value): 10 for value in range(10)},
    )
    assert threshold["resolution"] == "medium"
    assert threshold["display_mode"] == "directional"
    assert "tail_percentage" not in threshold
    assert "%" not in threshold["display_label"]

    directional = _theme_comparison(
        theme="事业",
        metric_id="relation_count",
        value=4,
        histogram={str(value): 20 for value in range(5)},
    )
    assert directional["resolution"] == "medium"
    assert directional["display_mode"] == "directional"
    assert directional["display_direction"] == "high"
    assert directional["display_label"] == "事业互动更密集 · 相对偏高"
    assert "tail_percentage" not in directional
    assert "%" not in directional["display_label"]
    # The exact distribution remains available to the professional view.
    assert directional["upper_tail_percentage"] == 20.0
    assert directional["rank_interval"] == {"lower": 80.0, "upper": 100.0}

    common = _theme_comparison(
        theme="五行与承压结构",
        metric_id="pressure_relation_count",
        value=0,
        histogram={"0": 35, "1": 30, "2": 35},
    )
    assert common["resolution"] == "low"
    assert common["display_mode"] == "common_value"
    assert common["display_direction"] == "low"
    assert common["semantic_pole"] == "结构张力较低"
    assert common["display_label"] == "结构张力较低 · 常见区间"
    assert "tail_percentage" not in common
    assert "%" not in common["display_label"]


def test_every_ordered_metric_has_three_neutral_semantic_poles() -> None:
    ordered = [
        definition
        for definition in statistics.METRIC_DEFINITIONS.values()
        if definition["metric_type"] == "ordinal"
    ]

    assert ordered
    assert all(
        set(definition["semantic_poles"]) == {"low", "typical", "high"}
        for definition in ordered
    )
    assert all(
        all(definition["semantic_poles"][pole] for pole in ("low", "typical", "high"))
        for definition in ordered
    )


def test_v6_baseline_integrity_and_registry_errors_are_caller_friendly(
    tmp_path, monkeypatch
) -> None:
    _write_v6_baseline(tmp_path)
    path = tmp_path / f"{BASELINE_ID}.json"
    payload = json.loads(path.read_text())
    payload["sample_weight"] = 11
    path.write_text(json.dumps(payload, ensure_ascii=False))
    monkeypatch.setattr(statistics, "DATA_DIR", tmp_path)
    statistics.load_baseline.cache_clear()

    with pytest.raises(statistics.BaselineCompatibilityError, match="完整性校验失败"):
        statistics.load_baseline(BASELINE_ID)
    unavailable = lookup_statistics(
        chart_type="bazi",
        baseline_id=BASELINE_ID,
        feature_ids=["bazi.shensha.wenchang"],
    )
    assert unavailable["status"] == "unavailable"
    assert unavailable["rarity_metrics"][0]["status"] == "unsupported"
    assert unavailable["baseline"] == {
        "schema_version": statistics.BASELINE_SCHEMA_VERSION,
        "id": BASELINE_ID,
        "chart_type": "bazi",
        "kind": "calendar_sample_frequency",
        "label": "统计基线不可用",
        "start": "",
        "end": "",
        "timezone": "unavailable",
        "day_boundary": "unavailable",
        "engine": "unavailable",
        "rules_version": "unavailable",
        "sample_unit": "unavailable",
        "weighted_unit": "unavailable",
        "sample_weight": 0.0,
        "unique_state_count": 0,
        "method": "",
        "hash": "",
    }
    assert "完整性校验失败" in unavailable["unavailable_reason"]
    assert "完整性校验失败" in unavailable["disclaimer"]

    _write_v6_baseline(tmp_path, registry_hash="sha256:" + "0" * 64)
    statistics.load_baseline.cache_clear()
    with pytest.raises(statistics.BaselineCompatibilityError, match="规则注册表不兼容"):
        statistics.load_baseline(BASELINE_ID)
    mismatch = lookup_statistics(
        chart_type="bazi",
        baseline_id=BASELINE_ID,
        feature_ids=["bazi.shensha.wenchang"],
    )
    assert mismatch["status"] == "version_mismatch"


def test_generator_metadata_declares_current_grain_without_full_regeneration() -> None:
    bazi = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "generate_bazi_baseline.py"),
            "--metadata",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
        text=True,
    )
    bazi_metadata = json.loads(bazi.stdout)
    assert bazi_metadata["schema_version"] == 6
    assert bazi_metadata["baseline_generation_version"] == 4
    assert bazi_metadata["weighted_unit"] == "minute"
    assert bazi_metadata["config_ids"] == {
        "current": "bazi-canonical-calendar-1-asia-shanghai-current",
        "forward": "bazi-canonical-calendar-1-asia-shanghai-forward",
    }
    assert bazi_metadata["feature_catalog_hash"]
    assert bazi_metadata["rules_registry_hash"] == statistics.bazi_rules_registry_hash()
    pattern_registry = load_packaged_shen_registry()
    assert bazi_metadata["pattern_bundle_id"] == pattern_registry.bundle_id
    assert bazi_metadata["pattern_bundle_digest"] == pattern_registry.bundle_digest
    assert (
        bazi_metadata["theme_comparison_method"] == "transparent_metric_distributions"
    )
    assert (
        bazi_metadata["consumer_feature_method"]
        == statistics.BAZI_CONSUMER_FEATURE_METHOD
    )
    assert bazi_metadata["pattern_authority"] == {
        "pattern_bundle_id": pattern_registry.bundle_id,
        "pattern_bundle_digest": pattern_registry.bundle_digest,
        "feature_semantics": statistics.BAZI_PATTERN_FEATURE_SEMANTICS,
    }

    ziwei = subprocess.run(
        ["node", str(ROOT / "scripts" / "generate_ziwei_baseline.mjs"), "--metadata"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    ziwei_metadata = json.loads(ziwei.stdout)
    assert ziwei_metadata["schema_version"] == 3
    assert ziwei_metadata["config_id"] == statistics.ZIWEI_STANDARD_CONFIG_ID
    assert ziwei_metadata["time_index_weights"] == [
        1,
        2,
        2,
        2,
        2,
        2,
        2,
        2,
        2,
        2,
        2,
        2,
        1,
    ]
    assert (
        ziwei_metadata["gender_scope"] == "male_only_natal_structure_gender_invariant"
    )
    assert ziwei_metadata["unique_state_count"] == 43829 * 13
    assert ziwei_metadata["sample_weight"] == 43829 * 24
    assert ziwei_metadata["weighted_unit"] == "civil_hour"
    assert (
        ziwei_metadata["rules_registry_hash"] == statistics.ziwei_rules_registry_hash()
    )


def test_legacy_baseline_without_current_pattern_bundle_cannot_be_promoted() -> None:
    source = {
        "id": "bazi-calendar-1924-2044-g3-forward",
        "chart_type": "bazi",
        "schema_version": 5,
        "baseline_generation_version": 3,
        "day_boundary": "forward",
        "config_id": "bazi-canonical-calendar-1-asia-shanghai-forward",
    }
    source["hash"] = statistics.payload_hash(source)

    with pytest.raises(ValueError, match="full baseline regeneration"):
        promote_g3_payload(source, "forward")


def _current_rule_promotion_source() -> dict:
    feature_catalog = _feature_catalog()
    metric_catalog = [METRIC_DEFINITIONS[key] for key in sorted(METRIC_DEFINITIONS)]
    source = {
        "id": "bazi-calendar-1924-2044-g3-forward",
        "chart_type": "bazi",
        "schema_version": 5,
        "baseline_generation_version": 3,
        "day_boundary": "forward",
        "config_id": _config_id("forward"),
        "rules_version": RULES_VERSION,
        "rules_registry_hash": statistics.bazi_rules_registry_hash(),
        **_pattern_bundle_identity(),
        "feature_catalog": feature_catalog,
        "feature_catalog_hash": statistics.feature_catalog_hash(feature_catalog),
        "metric_catalog": metric_catalog,
        "metric_catalog_hash": statistics.metric_catalog_hash(metric_catalog),
        "consumer_features": {
            **_canonical_consumer_feature_metadata(),
            "catalog": [],
            "hit_weights": {},
        },
    }
    source["hash"] = statistics.payload_hash(source)
    return source


@pytest.mark.parametrize(
    ("mutation", "message"),
    (
        ("registry", "Rule formulas changed"),
        ("metric", "Metric formulas changed"),
        ("consumer", "Consumer feature formulas changed"),
        ("consumer_method", "Consumer pattern authority changed"),
        ("consumer_authority", "Consumer pattern authority changed"),
        ("consumer_catalog", "predates canonical lifecycle features"),
    ),
)
def test_promotion_requires_exact_rule_formulas(mutation: str, message: str) -> None:
    source = _current_rule_promotion_source()
    if mutation == "registry":
        source["rules_registry_hash"] = "sha256:" + "0" * 64
    elif mutation == "metric":
        source["metric_catalog"][0] = {**source["metric_catalog"][0], "label": "旧公式"}
        source["metric_catalog_hash"] = statistics.metric_catalog_hash(
            source["metric_catalog"]
        )
    elif mutation == "consumer":
        source["consumer_features"]["rules_version"] = "legacy-consumer-rules"
    elif mutation == "consumer_method":
        source["consumer_features"]["method"] = "weighted_empirical_feature_incidence"
    elif mutation == "consumer_authority":
        source["consumer_features"]["pattern_authority"]["feature_semantics"] = (
            "legacy_candidates"
        )
    else:
        source["consumer_features"]["catalog"] = [
            {
                "id": "bazi.pattern.ordinary.direct_officer",
                "kind": "pattern",
                "title": "正官格",
            }
        ]
        source["consumer_features"]["hit_weights"] = {
            "bazi.pattern.ordinary.direct_officer": 1
        }
    source["hash"] = statistics.payload_hash(source)

    with pytest.raises(ValueError, match=message):
        _validate_promotion_source(source, "forward")


def test_pattern_refresh_replaces_only_legacy_pattern_incidence() -> None:
    source = _current_rule_promotion_source()
    source["consumer_features"] = {
        "rules_version": "metaphysics-consumer-2026.07-v5",
        "weighted_unit": "minute",
        "method": "legacy",
        "catalog": [
            {
                "id": "bazi.pattern.special.follow_strong",
                "kind": "pattern",
                "title": "从强格",
            },
            {
                "id": "bazi.shensha.combination.two_virtues",
                "kind": "combination",
                "title": "二德扶持",
            },
        ],
        "hit_weights": {
            "bazi.pattern.special.follow_strong": 12.5,
            "bazi.shensha.combination.two_virtues": 7,
        },
    }
    source["hash"] = statistics.payload_hash(source)

    refreshed = _replace_canonical_pattern_features(
        source,
        pattern_weights={
            "bazi.pattern.canonical.indirect_resource.status.formed": 180,
        },
        pattern_titles={
            "bazi.pattern.canonical.indirect_resource.status.formed": "偏印·成格",
        },
    )

    assert refreshed["consumer_features"]["catalog"] == [
        {
            "id": "bazi.pattern.canonical.indirect_resource.status.formed",
            "kind": "pattern",
            "title": "偏印·成格",
        },
        {
            "id": "bazi.shensha.combination.two_virtues",
            "kind": "combination",
            "title": "二德扶持",
        },
    ]
    assert refreshed["consumer_features"]["hit_weights"] == {
        "bazi.pattern.canonical.indirect_resource.status.formed": 3.0,
        "bazi.shensha.combination.two_virtues": 7,
    }
    assert refreshed["consumer_features"]["rules_version"] == CONSUMER_RULES_VERSION
    assert (
        refreshed["consumer_features"]["method"]
        == statistics.BAZI_CONSUMER_FEATURE_METHOD
    )
    assert refreshed["consumer_features"]["pattern_authority"] == {
        **_pattern_bundle_identity(),
        "feature_semantics": "canonical_active_lifecycle_status",
    }
    assert refreshed["rules_registry_hash"] == statistics.bazi_rules_registry_hash()
    assert refreshed["hash"] == statistics.payload_hash(refreshed)


def test_full_generator_path_emits_canonical_pattern_incidence() -> None:
    pillars = _pillars_from_state_key(("甲子", "丙寅", "丙寅", "戊子"))
    structure = build_structure_profile(
        pillars,
        gender=None,
        shensha_hits=[],
        seasonal_status=_seasonal_status(pillars[1]["branch"]),
    )
    patterns = assess_patterns(pillars, structure, include_attestations=False)

    pattern_records = [
        record
        for record in consumer_feature_records(patterns, {})
        if record["kind"] == "pattern"
    ]

    assert pattern_records == [
        {
            "id": "bazi.pattern.canonical.indirect_resource.status.candidate",
            "kind": "pattern",
            "title": "偏印·候选",
        }
    ]


@pytest.mark.parametrize("mode", ("forward", "current"))
def test_checked_in_g4_pattern_incidence_is_canonical(mode: str) -> None:
    path = (
        ROOT
        / "src"
        / "iching"
        / "core"
        / "data"
        / f"bazi-calendar-1924-2044-g4-{mode}.json"
    )
    baseline = json.loads(path.read_text())
    package = baseline["consumer_features"]
    pattern_ids = {
        item["id"] for item in package["catalog"] if item["kind"] == "pattern"
    }

    assert pattern_ids
    assert pattern_ids == {
        identifier
        for identifier in package["hit_weights"]
        if identifier.startswith("bazi.pattern.")
    }
    assert all(
        identifier.startswith("bazi.pattern.canonical.") for identifier in pattern_ids
    )
    assert not any(
        ".ordinary." in identifier or ".special." in identifier
        for identifier in pattern_ids
    )
    assert package["rules_version"] == CONSUMER_RULES_VERSION
    assert package["method"] == statistics.BAZI_CONSUMER_FEATURE_METHOD
    assert package["pattern_authority"] == {
        **_pattern_bundle_identity(),
        "feature_semantics": statistics.BAZI_PATTERN_FEATURE_SEMANTICS,
    }
    assert baseline["rules_registry_hash"] == statistics.bazi_rules_registry_hash()
    assert baseline["hash"] == statistics.payload_hash(baseline)


@pytest.mark.parametrize("mutation", ("method", "bundle", "semantics"))
def test_g4_loader_rejects_noncanonical_consumer_pattern_producer(
    mutation: str,
) -> None:
    path = (
        ROOT
        / "src"
        / "iching"
        / "core"
        / "data"
        / "bazi-calendar-1924-2044-g4-forward.json"
    )
    baseline = json.loads(path.read_text())
    package = baseline["consumer_features"]
    if mutation == "method":
        package["method"] = "weighted_empirical_feature_incidence"
    elif mutation == "bundle":
        package["pattern_authority"]["pattern_bundle_digest"] = "stale"
    else:
        package["pattern_authority"]["feature_semantics"] = "legacy_candidates"
    baseline["hash"] = statistics.payload_hash(baseline)

    with pytest.raises(statistics.BaselineVersionMismatchError):
        statistics._validate_v3_baseline(baseline)


def _approved_pattern_refresh_source() -> dict:
    source_path = (
        ROOT
        / "src"
        / "iching"
        / "core"
        / "data"
        / "bazi-calendar-1924-2044-g4-forward.json"
    )
    source = json.loads(source_path.read_text())
    package = source["consumer_features"]
    non_patterns = [item for item in package["catalog"] if item["kind"] != "pattern"]
    non_pattern_ids = {item["id"] for item in non_patterns}
    source["pattern_bundle_digest"] = REFRESH_SOURCE_PATTERN_BUNDLE_DIGEST
    source["rules_registry_hash"] = REFRESH_SOURCE_RULES_REGISTRY_HASH
    source["consumer_features"] = {
        "rules_version": REFRESH_SOURCE_CONSUMER_RULES_VERSION,
        "weighted_unit": "minute",
        "method": "weighted_empirical_feature_incidence",
        "catalog": [
            *non_patterns,
            {
                "id": "bazi.pattern.ordinary.direct_officer",
                "kind": "pattern",
                "title": "正官格",
            },
        ],
        "hit_weights": {
            **{
                key: value
                for key, value in package["hit_weights"].items()
                if key in non_pattern_ids
            },
            "bazi.pattern.ordinary.direct_officer": 1,
        },
    }
    source["hash"] = statistics.payload_hash(source)
    return source


@pytest.mark.parametrize(
    ("mutation", "message"),
    (
        ("schema", "schema version"),
        ("generation", "generation version"),
        ("registry", "pre-refresh rule registry"),
        ("feature", "Feature formulas changed"),
        ("metric", "Metric formulas changed"),
        ("consumer", "approved v5 consumer producer"),
        ("consumer_weights", "catalog and weights differ"),
    ),
)
def test_pattern_refresh_rejects_mismatched_preserved_producers(
    mutation: str,
    message: str,
) -> None:
    source = _approved_pattern_refresh_source()
    if mutation == "schema":
        source["schema_version"] -= 1
    elif mutation == "generation":
        source["baseline_generation_version"] -= 1
    elif mutation == "registry":
        source["rules_registry_hash"] = "sha256:" + "0" * 64
    elif mutation == "feature":
        source["feature_catalog"] = source["feature_catalog"][:-1]
        source["feature_catalog_hash"] = statistics.feature_catalog_hash(
            source["feature_catalog"]
        )
    elif mutation == "metric":
        source["metric_catalog"][0] = {
            **source["metric_catalog"][0],
            "label": "stale",
        }
        source["metric_catalog_hash"] = statistics.metric_catalog_hash(
            source["metric_catalog"]
        )
    elif mutation == "consumer":
        source["consumer_features"]["rules_version"] = "unknown-producer"
    else:
        source["consumer_features"]["hit_weights"].pop(
            next(iter(source["consumer_features"]["hit_weights"]))
        )
    source["hash"] = statistics.payload_hash(source)

    with pytest.raises(ValueError, match=message):
        _validate_pattern_refresh_source(source, "forward")


def test_statistics_endpoint_accepts_only_normalized_features() -> None:
    response = client.post(
        "/api/tools/metaphysics/statistics",
        json={
            "chart_type": "bazi",
            "baseline_id": BASELINE_ID,
            "feature_ids": ["bazi.shensha.wenchang"],
        },
    )

    assert response.status_code == 200
    assert response.json()["rarity_metrics"][0]["feature_id"] == "bazi.shensha.wenchang"

    rejected = client.post(
        "/api/tools/metaphysics/statistics",
        json={
            "chart_type": "bazi",
            "baseline_id": BASELINE_ID,
            "feature_ids": ["name=Alice&birthday=2000-01-01"],
        },
    )
    assert rejected.status_code == 422
