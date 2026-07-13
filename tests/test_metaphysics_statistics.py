from __future__ import annotations

from fastapi.testclient import TestClient

from iching.core.metaphysics_statistics import BASELINE_ID, frequency_label, lookup_statistics
from iching.web.api.main import app


client = TestClient(app)


def test_frequency_labels_do_not_render_false_zeroes() -> None:
    assert frequency_label(0.0) == "<0.01%"
    assert frequency_label(0.009) == "<0.01%"
    assert frequency_label(0.5) == "0.50%"
    assert frequency_label(12.345) == "12.35%"


def test_baseline_lookup_returns_denominator_and_version() -> None:
    result = lookup_statistics(
        chart_type="bazi",
        baseline_id=BASELINE_ID,
        feature_ids=["bazi.shensha.wenchang", "bazi.shensha.yima"],
    )

    assert result["baseline"]["id"] == BASELINE_ID
    assert result["baseline"]["sample_weight"] > 0
    assert result["baseline"]["hash"]
    assert len(result["rarity_metrics"]) == 2
    assert all(metric["total_weight"] == result["baseline"]["sample_weight"] for metric in result["rarity_metrics"])
    assert all(metric["level"] in {"common", "less_common", "rare", "very_rare"} for metric in result["rarity_metrics"])


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
