from __future__ import annotations

from iching.core.metaphysics_consumer import THEME_ORDER, build_bazi_consumer_profile, build_life_kline
from iching.core.metaphysics_statistics import select_consumer_distributions, select_consumer_feature_metrics


def test_consumer_profile_uses_empirical_global_and_cohort_midrank() -> None:
    dimensions = ("overall", *THEME_ORDER)
    baseline = {
        "id": "test-bazi-baseline",
        "weighted_unit": "minute",
        "consumer_score_distributions": {
            "rules_version": "metaphysics-consumer-2026.07-v3",
            "weighted_unit": "minute",
            "global": {
                "male": {dimension: {"42": 20, "43": 60, "44": 20} for dimension in dimensions},
            },
            "cohorts": {
                "丙-午": {
                    "male": {dimension: {"43": 10, "44": 90} for dimension in dimensions},
                },
            },
        },
    }
    selected = select_consumer_distributions(baseline, gender="male", cohort_key="丙-午")
    structure = {
        "theme_profiles": [
            {"theme": label, "evidence": [], "structure_metrics": [], "comparisons": []}
            for label in ("事业", "财富", "感情", "五行与承压结构")
        ],
    }
    profile = build_bazi_consumer_profile(
        pillars=[
            {"label": "年", "stem": "甲", "branch": "申", "ten_god": "偏印"},
            {"label": "月", "stem": "庚", "branch": "午", "ten_god": "偏财"},
            {"label": "日", "stem": "丙", "branch": "子", "ten_god": "日主"},
            {"label": "时", "stem": "庚", "branch": "寅", "ten_god": "偏财"},
        ],
        structure=structure,
        patterns={},
        shensha_effects={"hits": [], "combinations": []},
        cycles=[],
        consumer_distributions=selected,
    )

    assert profile["identity"]["main_score"] == 50
    assert profile["identity"]["raw_score"] == 43
    assert profile["identity"]["global_percentile"] == 50.0
    assert profile["identity"]["cohort_percentile"] == 5.0
    assert profile["identity"]["ranking_basis"] == "weighted_empirical_calendar_baseline"
    assert all(subject["score"] == 50 for subject in profile["subjects"])
    assert all(subject["raw_score"] == 43 for subject in profile["subjects"])
    assert all(subject["global_percentile"] == 50.0 for subject in profile["subjects"])
    assert all(subject["cohort_percentile"] == 5.0 for subject in profile["subjects"])


def test_full_life_kline_opens_on_current_cycle() -> None:
    def year(value: int) -> dict:
        return {
            "year": value,
            "theme_activations": {},
            "months": [
                {"index": index, "label": f"{index + 1}月", "ganzhi": "甲子", "theme_activations": {}}
                for index in range(12)
            ],
        }

    kline = build_life_kline(
        [
            {"label": "甲子", "start_year": 2016, "end_year": 2025, "is_current": False, "theme_activations": {}, "years": [year(value) for value in range(2016, 2026)]},
            {"label": "乙丑", "start_year": 2026, "end_year": 2035, "is_current": True, "theme_activations": {}, "years": [year(value) for value in range(2026, 2036)]},
            {"label": "丙寅", "start_year": 2036, "end_year": 2045, "is_current": False, "theme_activations": {}, "years": [year(value) for value in range(2036, 2046)]},
        ],
        {theme: 60 for theme in THEME_ORDER},
    )

    assert kline["default_window"] == {"start_year": 2026, "end_year": 2035}
    assert len(kline["series"][0]["points"]) == 30
    assert len(kline["stages"]) == 15
    assert {stage["key"] for stage in kline["stages"]} == {"overall", *THEME_ORDER}
    assert all(2026 <= stage["year"] <= 2035 for stage in kline["stages"])


def test_consumer_feature_lookup_returns_compact_incidence() -> None:
    baseline = {
        "id": "test-bazi-baseline",
        "sample_weight": 100,
        "consumer_features": {
            "rules_version": "metaphysics-consumer-2026.07-v3",
            "catalog": [{"id": "bazi.shensha.combination.two_virtues", "kind": "combination", "title": "二德扶持"}],
            "hit_weights": {"bazi.shensha.combination.two_virtues": 4.25},
        },
    }

    observed, unsupported = select_consumer_feature_metrics(
        baseline,
        ["bazi.shensha.combination.two_virtues", "bazi.shensha.combination.unknown"],
    )

    assert observed["percentage"] == 4.25
    assert observed["status"] == "observed"
    assert unsupported["status"] == "unsupported"
