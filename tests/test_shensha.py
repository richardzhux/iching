from __future__ import annotations

from datetime import datetime

from iching.core.metaphysics import build_metaphysics_chart
from iching.core.shensha import CORE_RULE_IDS, RULES_VERSION, evaluate_shensha


def test_core_registry_has_the_approved_twenty_rules() -> None:
    assert RULES_VERSION.startswith("shensha-")
    assert len(CORE_RULE_IDS) == 20
    assert len(set(CORE_RULE_IDS)) == 20


def test_known_chart_returns_traceable_hits_and_pillar_positions() -> None:
    chart = build_metaphysics_chart(datetime(2004, 6, 26, 4), timezone_name="Asia/Shanghai")
    hits = evaluate_shensha(chart["pillars"])
    by_name = {hit["name"]: hit for hit in hits}

    assert by_name["文昌贵人"]["pillar_labels"] == ["年"]
    assert by_name["月德贵人"]["pillar_labels"] == ["日"]
    assert by_name["驿马"]["pillar_labels"] == ["时"]
    assert by_name["将星"]["pillar_labels"] == ["日"]
    assert by_name["羊刃"]["pillar_labels"] == ["月"]
    assert by_name["灾煞"]["pillar_labels"] == ["月"]
    assert all(hit["rule_id"] and hit["source"]["title"] for hit in hits)
    assert all(hit["trigger"] and hit["level"] in {"core", "extended"} for hit in hits)


def test_unknown_hour_never_claims_an_hour_pillar_hit() -> None:
    chart = build_metaphysics_chart(
        datetime(2004, 6, 26, 12),
        timezone_name="Asia/Shanghai",
        hour_uncertain=True,
    )

    assert all("时" not in hit["pillar_labels"] for hit in chart["shen_sha"])


def test_chart_exposes_versioned_derived_metaphysics_payload() -> None:
    chart = build_metaphysics_chart(datetime(2004, 6, 26, 4), timezone_name="Asia/Shanghai", gender="male")

    assert chart["derived_schema_version"] == 2
    assert chart["rules_version"] == RULES_VERSION
    assert chart["statistics"]["baseline"]["kind"] == "calendar_sample_frequency"
    assert chart["statistics"]["disclaimer"]
    assert {item["dimension"] for item in chart["statistics"]["rule_indices"]} == {
        "助力", "才学", "情缘", "执行", "迁动", "考验"
    }
    assert chart["period_layers"]["dayun"]
    assert chart["period_layers"]["current"]["year"]


def test_source_checked_school_and_ten_bad_defeat_tables() -> None:
    pillars = [
        {"label": "年", "stem": "甲", "branch": "亥", "text": "甲亥"},
        {"label": "月", "stem": "丙", "branch": "寅", "text": "丙寅"},
        {"label": "日", "stem": "乙", "branch": "丑", "text": "乙丑"},
        {"label": "时", "stem": "辛", "branch": "申", "text": "辛申"},
    ]
    hits = {hit["name"]: hit for hit in evaluate_shensha(pillars)}

    assert hits["学堂"]["pillar_labels"] == ["年"]
    assert hits["词馆"]["pillar_labels"] == ["时"]
    assert hits["十恶大败"]["pillar_labels"] == ["日"]

    pillars[2] = {"label": "日", "stem": "己", "branch": "丑", "text": "己丑"}
    assert "十恶大败" not in {hit["name"] for hit in evaluate_shensha(pillars)}
