from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import iching.core.metaphysics_statistics as statistics
from iching.core.metaphysics_statistics import BASELINE_ID, frequency_label, lookup_statistics
from iching.web.api.main import app


client = TestClient(app)
ROOT = Path(__file__).parents[1]


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
    assert all(metric["total_weight"] == result["baseline"]["sample_weight"] for metric in result["rarity_metrics"])
    assert all(metric["status"] == "observed" for metric in result["rarity_metrics"])
    assert all(metric["level"] in {"common", "less_common", "rare", "very_rare"} for metric in result["rarity_metrics"])


def _write_v3_baseline(tmp_path, *, registry_hash: str | None = None) -> None:
    catalog = ["bazi.shensha.wenchang", "bazi.shensha.yima"]
    payload = {
        "schema_version": 3,
        "id": BASELINE_ID,
        "chart_type": "bazi",
        "kind": "calendar_sample_frequency",
        "label": "test baseline",
        "start": "2000-01-01T00:00:00+08:00",
        "end": "2000-01-01T00:10:00+08:00",
        "timezone": "Asia/Shanghai",
        "day_boundary": "forward",
        "config_id": "bazi-sxtwl-2.0.7-asia-shanghai-forward-v1",
        "engine": "sxtwl 2.0.7",
        "rules_version": "shensha-2026.07-v2",
        "rules_registry_hash": registry_hash or statistics.bazi_rules_registry_hash(),
        "feature_catalog": catalog,
        "feature_catalog_hash": statistics.feature_catalog_hash(catalog),
        "unique_state_count": 2,
        "sample_unit": "minute",
        "weighted_unit": "minute",
        "sample_weight": 10,
        "method": "test",
        "features": {"bazi.shensha.wenchang": {"hit_weight": 5}},
        "theme_families": {
            "mobility": {
                "label": "迁动",
                "feature_ids": ["bazi.shensha.yima"],
            }
        },
        "theme_histograms": {"mobility": {"0": 4, "1": 6}},
    }
    payload["hash"] = statistics.payload_hash(payload)
    (tmp_path / f"{BASELINE_ID}.json").write_text(json.dumps(payload, ensure_ascii=False))


def test_catalog_statuses_distinguish_zero_and_unsupported(tmp_path, monkeypatch) -> None:
    _write_v3_baseline(tmp_path)
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
    assert {key: zero[key] for key in ("status", "display_percentage", "percentage", "hit_weight")} == {
        "status": "zero",
        "display_percentage": "0%",
        "percentage": 0.0,
        "hit_weight": 0.0,
    }
    assert unsupported["status"] == "unsupported"
    assert unsupported["display_percentage"] == "—"
    assert unsupported["level"] == "unavailable"


def test_v3_theme_profile_replaces_rule_indices(tmp_path, monkeypatch) -> None:
    _write_v3_baseline(tmp_path)
    monkeypatch.setattr(statistics, "DATA_DIR", tmp_path)
    statistics.load_baseline.cache_clear()

    result = lookup_statistics(
        chart_type="bazi",
        baseline_id=BASELINE_ID,
        feature_ids=["bazi.shensha.yima"],
    )

    assert result["rule_indices"] == []
    assert result["rule_indices_deprecated"] is True
    assert result["theme_profile"] == [{
        "theme_id": "mobility",
        "label": "迁动",
        "raw_count": 1,
        "percentile": 70.0,
        "contribution_feature_ids": ["bazi.shensha.yima"],
        "reference_weight": 10.0,
        "percentile_method": "weighted_midrank",
        "baseline_id": BASELINE_ID,
    }]


def test_v3_baseline_integrity_and_registry_errors_are_caller_friendly(tmp_path, monkeypatch) -> None:
    _write_v3_baseline(tmp_path)
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
    assert "完整性校验失败" in unavailable["unavailable_reason"]
    assert "完整性校验失败" in unavailable["disclaimer"]

    _write_v3_baseline(tmp_path, registry_hash="sha256:" + "0" * 64)
    statistics.load_baseline.cache_clear()
    with pytest.raises(statistics.BaselineCompatibilityError, match="规则注册表不兼容"):
        statistics.load_baseline(BASELINE_ID)
    mismatch = lookup_statistics(
        chart_type="bazi",
        baseline_id=BASELINE_ID,
        feature_ids=["bazi.shensha.wenchang"],
    )
    assert mismatch["status"] == "version_mismatch"


def test_generator_metadata_declares_v3_grain_without_full_regeneration() -> None:
    bazi = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "generate_bazi_baseline.py"), "--metadata"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
        text=True,
    )
    bazi_metadata = json.loads(bazi.stdout)
    assert bazi_metadata["schema_version"] == 3
    assert bazi_metadata["weighted_unit"] == "minute"
    assert bazi_metadata["config_ids"] == {
        "current": "bazi-sxtwl-2.0.7-asia-shanghai-current-v1",
        "forward": "bazi-sxtwl-2.0.7-asia-shanghai-forward-v1",
    }
    assert bazi_metadata["feature_catalog_hash"]
    assert bazi_metadata["rules_registry_hash"] == statistics.bazi_rules_registry_hash()
    assert set(bazi_metadata["theme_families"]) == set(statistics.THEME_IDS)

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
    assert ziwei_metadata["time_index_weights"] == [1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1]
    assert ziwei_metadata["gender_scope"] == "male_only_natal_structure_gender_invariant"
    assert ziwei_metadata["unique_state_count"] == 43829 * 13
    assert ziwei_metadata["sample_weight"] == 43829 * 24
    assert ziwei_metadata["weighted_unit"] == "civil_hour"
    assert ziwei_metadata["rules_registry_hash"] == statistics.ziwei_rules_registry_hash()


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
