from __future__ import annotations

import json
from datetime import datetime

from iching.core import shensha
from iching.core.metaphysics import build_metaphysics_chart
from iching.core.shensha import CORE_RULE_IDS, RULES_VERSION, evaluate_shensha


def test_core_registry_has_the_approved_twenty_rules() -> None:
    assert RULES_VERSION == "shensha-2026.07-v2.1"
    assert len(CORE_RULE_IDS) == 20
    assert len(set(CORE_RULE_IDS)) == 20


def test_v21_registry_has_thirty_executable_serializable_rules() -> None:
    assert shensha.REGISTRY_VERSION == "shensha-registry-2026.07-v2.1"
    assert len(shensha.RULES) == 30
    assert len(shensha.EXTENDED_RULE_IDS) == 10
    assert all(rule.method != "fixed_none" for rule in shensha.RULES)

    payload = shensha.registry_payload()
    assert len(payload) == 30
    assert json.loads(json.dumps(payload, ensure_ascii=False)) == payload
    assert all(item["formula"]["mapping"] for item in payload)
    assert all(item["formula_digest"].startswith("sha256:") for item in payload)
    assert all(item["registry_digest"] == shensha.REGISTRY_DIGEST for item in payload)
    assert {tag for item in payload for tag in item["topic_tags"]} == {
        "career", "wealth", "relationship", "health"
    }


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
    pillars = [
        {"label": "年", "stem": "甲", "branch": "申", "text": "甲申"},
        {"label": "月", "stem": "庚", "branch": "午", "text": "庚午"},
        {"label": "日", "stem": "丙", "branch": "子", "text": "丙子"},
        {"label": "时", "stem": "待定", "branch": "待定", "text": "待定"},
    ]

    assert all("时" not in hit["pillar_labels"] for hit in evaluate_shensha(pillars))


def test_chart_exposes_versioned_derived_metaphysics_payload() -> None:
    chart = build_metaphysics_chart(datetime(2004, 6, 26, 4), timezone_name="Asia/Shanghai", gender="male")

    assert chart["derived_schema_version"] == 7
    assert chart["rules_version"] == RULES_VERSION
    assert chart["rule_versions"]["shensha"] == RULES_VERSION
    assert chart["rule_versions"]["pattern_bundle"] == "zzq-shen-canonical-v1"
    assert len(chart["rule_versions"]["pattern_digest"]) == 64
    assert chart["statistics"]["baseline"]["kind"] == "calendar_sample_frequency"
    assert chart["statistics"]["disclaimer"]
    assert "rule_indices" not in chart["statistics"]
    assert {item["theme"] for item in chart["theme_profiles"]} == {
        "事业", "财富", "感情", "五行与承压结构"
    }
    assert all(len(item["structure_metrics"]) == 6 for item in chart["theme_profiles"])
    assert all(len(item["comparisons"]) == 6 for item in chart["theme_profiles"])
    assert chart["period_layers"]["dayun"]
    assert chart["period_layers"]["current"]["year"]


def test_xuetang_and_ciguan_share_the_exact_pillar_convention() -> None:
    pillars = [
        {"label": "年", "stem": "己", "branch": "亥", "text": "己亥"},
        {"label": "月", "stem": "丙", "branch": "辰", "text": "丙辰"},
        {"label": "日", "stem": "甲", "branch": "子", "text": "甲子"},
        {"label": "时", "stem": "庚", "branch": "寅", "text": "庚寅"},
    ]
    hits = {hit["name"]: hit for hit in evaluate_shensha(pillars)}

    assert hits["学堂"]["pillar_labels"] == ["年"]
    assert hits["词馆"]["pillar_labels"] == ["时"]
    assert hits["学堂"]["formula"]["method"] == "day_stem_pillar"
    assert hits["词馆"]["formula"]["method"] == "day_stem_pillar"

    pillars[0] = {"label": "年", "stem": "乙", "branch": "亥", "text": "乙亥"}
    pillars[3] = {"label": "时", "stem": "甲", "branch": "寅", "text": "甲寅"}
    names = {hit["name"] for hit in evaluate_shensha(pillars)}
    assert "学堂" not in names
    assert "词馆" not in names


def test_tianchu_and_dexiu_use_executable_modern_ziping_conventions() -> None:
    pillars = [
        {"label": "年", "stem": "丙", "branch": "巳", "text": "丙巳"},
        {"label": "月", "stem": "戊", "branch": "寅", "text": "戊寅"},
        {"label": "日", "stem": "甲", "branch": "子", "text": "甲子"},
        {"label": "时", "stem": "庚", "branch": "辰", "text": "庚辰"},
    ]
    hits = {hit["name"]: hit for hit in evaluate_shensha(pillars)}

    assert hits["天厨"]["pillar_labels"] == ["年"]
    assert hits["德秀贵人"]["pillar_labels"] == ["年", "月"]
    assert hits["德秀贵人"]["anchors"][0]["target_roles"] == {
        "德": ["丙", "丁"], "秀": ["戊", "癸"]
    }


def test_ten_bad_defeats_uses_jichou_and_records_yichou_variant() -> None:
    pillars = [
        {"label": "年", "stem": "甲", "branch": "亥", "text": "甲亥"},
        {"label": "月", "stem": "丙", "branch": "寅", "text": "丙寅"},
        {"label": "日", "stem": "己", "branch": "丑", "text": "己丑"},
        {"label": "时", "stem": "辛", "branch": "申", "text": "辛申"},
    ]
    hits = {hit["name"]: hit for hit in evaluate_shensha(pillars)}

    assert hits["十恶大败"]["pillar_labels"] == ["日"]
    assert "乙丑" in hits["十恶大败"]["school_note"]

    pillars[2] = {"label": "日", "stem": "乙", "branch": "丑", "text": "乙丑"}
    assert "十恶大败" not in {hit["name"] for hit in evaluate_shensha(pillars)}


def test_hits_trace_tianyi_and_year_day_trine_anchors() -> None:
    pillars = [
        {"label": "年", "stem": "庚", "branch": "子", "text": "庚子"},
        {"label": "月", "stem": "乙", "branch": "寅", "text": "乙寅"},
        {"label": "日", "stem": "甲", "branch": "午", "text": "甲午"},
        {"label": "时", "stem": "丙", "branch": "申", "text": "丙申"},
        {"label": "流年", "stem": "丁", "branch": "丑", "text": "丁丑"},
    ]
    hits = {hit["name"]: hit for hit in evaluate_shensha(pillars)}

    assert hits["天乙贵人"]["anchors"] == [{
        "reference": "日干", "label": "日", "field": "stem", "value": "甲",
        "targets": ["丑", "未"],
    }]
    assert "双支并查" in hits["天乙贵人"]["school_note"]
    assert hits["驿马"]["pillar_labels"] == ["月", "时"]
    assert hits["驿马"]["anchors"] == [
        {"reference": "年支", "label": "年", "field": "branch", "value": "子", "targets": ["寅"]},
        {"reference": "日支", "label": "日", "field": "branch", "value": "午", "targets": ["申"]},
    ]
    assert "年支、日支分别起例" in hits["驿马"]["school_note"]
