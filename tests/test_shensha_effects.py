from __future__ import annotations

import importlib
import json

from iching.core.bazi_structure import HIDDEN_STEMS, STEM_ELEMENTS, _ten_god


def test_effect_state_preserves_hit_and_uses_chart_constraints() -> None:
    module = importlib.import_module("iching.core.shensha_effects")
    hits = [{
        "rule_id": "wenchang",
        "name": "文昌贵人",
        "axis": "才学",
        "pillar_labels": ["时"],
        "formula": {"candidate_field": "branch"},
        "topic_tags": ["career"],
        "custom_source_field": "keep-me",
    }]
    pillars = [
        {"label": "年", "stem": "甲", "branch": "子", "text": "甲子"},
        {"label": "月", "stem": "丁", "branch": "卯", "text": "丁卯"},
        {"label": "日", "stem": "甲", "branch": "午", "text": "甲午", "xunkong": "辰巳"},
        {"label": "时", "stem": "己", "branch": "巳", "text": "己巳"},
    ]
    structure = {
        "day_master": {"stem": "甲", "element": "木", "root_pillars": ["年", "月"]},
        "structural_relations": [{
            "relation_type": "地支冲",
            "participants": [{"pillar": "时"}, {"pillar": "日"}],
        }],
    }

    result = module.evaluate_shensha_effects(hits, pillars, structure)
    evaluated = result["hits"][0]

    assert evaluated["custom_source_field"] == "keep-me"
    assert evaluated["state"] == "受制"
    assert evaluated["effect_flags"]["void"] is True
    assert evaluated["effect_flags"]["clashed"] is True
    assert evaluated["state_reason"]
    assert json.loads(json.dumps(result, ensure_ascii=False)) == result


def test_rule_specific_support_can_make_a_hit_effective() -> None:
    module = importlib.import_module("iching.core.shensha_effects")
    hits = [{
        "rule_id": "lushen",
        "name": "禄神",
        "axis": "执行",
        "pillar_labels": ["月"],
        "formula": {"candidate_field": "branch", "mapping": {"甲": ["寅"]}},
        "topic_tags": ["career", "wealth"],
    }]
    pillars = [
        {"label": "年", "stem": "壬", "branch": "子", "text": "壬子"},
        {"label": "月", "stem": "甲", "branch": "寅", "text": "甲寅"},
        {"label": "日", "stem": "甲", "branch": "午", "text": "甲午", "xunkong": "辰巳"},
        {"label": "时", "stem": "乙", "branch": "卯", "text": "乙卯"},
    ]
    structure = {
        "day_master": {"stem": "甲", "element": "木", "root_pillars": ["月", "时"]},
        "day_master_relations": [{"ten_god": "比肩"}, {"ten_god": "劫财"}],
        "structural_relations": [],
    }

    evaluated = module.evaluate_shensha_effects(hits, pillars, structure)["hits"][0]

    assert evaluated["state"] == "发力"
    assert evaluated["effect_flags"]["rooted"] is True
    assert evaluated["effect_flags"]["season_supported"] is True
    assert evaluated["effect_flags"]["structure_echo"] is True


def test_void_is_derived_from_day_pillar_when_not_precomputed() -> None:
    module = importlib.import_module("iching.core.shensha_effects")
    hit = {
        "rule_id": "huagai",
        "name": "华盖",
        "axis": "执行",
        "pillar_labels": ["时"],
        "formula": {"candidate_field": "branch"},
        "topic_tags": ["career"],
    }
    pillars = [
        {"label": "年", "stem": "甲", "branch": "子", "text": "甲子"},
        {"label": "月", "stem": "丙", "branch": "寅", "text": "丙寅"},
        {"label": "日", "stem": "甲", "branch": "子", "text": "甲子"},
        {"label": "时", "stem": "乙", "branch": "亥", "text": "乙亥"},
    ]

    evaluated = module.evaluate_shensha_effects([hit], pillars, {})["hits"][0]

    assert evaluated["effect_flags"]["void"] is True
    assert evaluated["state"] == "受制"


def test_incomplete_day_master_is_handled_without_inventing_support() -> None:
    module = importlib.import_module("iching.core.shensha_effects")
    hit = {
        "rule_id": "tianyi",
        "name": "天乙贵人",
        "axis": "助力",
        "pillar_labels": ["年"],
        "topic_tags": ["career"],
    }
    pillars = [
        {"label": "年", "stem": "甲", "branch": "卯", "text": "甲卯"},
        {"label": "日", "stem": "", "branch": "", "text": ""},
    ]

    evaluated = module.evaluate_shensha_effects([hit], pillars, {})["hits"][0]

    assert evaluated["effect_flags"]["rooted"] is False
    assert evaluated["effect_flags"]["structure_echo"] is False
    assert evaluated["effect_flags"]["season_supported"] is False


def test_documented_combinations_have_explicit_provenance() -> None:
    module = importlib.import_module("iching.core.shensha_effects")
    hit_specs = [
        ("lushen", "禄神", ["年"], ["career", "wealth"]),
        ("yima", "驿马", ["年"], ["career", "wealth"]),
        ("xuetang", "学堂", ["月"], ["career"]),
        ("tianyi", "天乙贵人", ["日"], ["career"]),
        ("tiande", "天德贵人", ["年"], ["career"]),
        ("yuede", "月德贵人", ["月"], ["career"]),
        ("jiangxing", "将星", ["时"], ["career"]),
        ("yangren", "羊刃", ["日"], ["career", "health"]),
        ("dexiu", "德秀贵人", ["时"], ["career"]),
        ("wenchang", "文昌贵人", ["年"], ["career"]),
        ("guoyin", "国印贵人", ["月"], ["career"]),
    ]
    hits = [
        {
            "rule_id": rule_id,
            "name": name,
            "axis": "助力",
            "pillar_labels": labels,
            "formula": {"candidate_field": "branch"},
            "topic_tags": tags,
        }
        for rule_id, name, labels, tags in hit_specs
    ]
    day_stem = "甲"
    pillars = []
    for label, text in zip(("年", "月", "日", "时"), ("戊辰", "辛酉", "甲子", "癸亥")):
        stem, branch = text
        pillars.append({
            "label": label,
            "stem": stem,
            "branch": branch,
            "text": text,
            "ten_god": "日主" if label == "日" else _ten_god(day_stem, stem),
            "hidden_stems": [
                {"stem": hidden, "element": STEM_ELEMENTS[hidden], "ten_god": _ten_god(day_stem, hidden)}
                for hidden in HIDDEN_STEMS[branch]
            ],
        })
    structure = {
        "day_master": {"stem": "甲", "element": "木", "root_pillars": ["年"]},
        "structural_relations": [],
    }

    combinations = module.evaluate_shensha_effects(hits, pillars, structure)["combinations"]
    titles = {item["title"] for item in combinations}

    assert {
        "禄马同乡",
        "学堂会禄",
        "学堂会贵",
        "学堂朝驿马",
        "二德扶持",
        "将星扶德天乙加临",
        "羊刃带禄官印相资",
        "德秀学堂财官",
        "有文有印",
    } <= titles
    assert all(item["tier"] in {
        "classical_named", "classical_interaction", "product_cluster"
    } for item in combinations)
    assert all({
        "id", "title", "tier", "rarity_tier", "member_rule_ids",
        "status", "summary", "topic_tags",
    } <= item.keys() for item in combinations)


def test_luma_distinguishes_crossed_positions_and_modern_clusters_are_labeled() -> None:
    module = importlib.import_module("iching.core.shensha_effects")
    hits = [
        {"rule_id": "lushen", "name": "禄神", "axis": "执行", "pillar_labels": ["年"], "topic_tags": ["wealth"]},
        {"rule_id": "yima", "name": "驿马", "axis": "迁动", "pillar_labels": ["时"], "topic_tags": ["career"]},
        {"rule_id": "wenchang", "name": "文昌贵人", "axis": "才学", "pillar_labels": ["月"], "topic_tags": ["career"]},
        {"rule_id": "huagai", "name": "华盖", "axis": "执行", "pillar_labels": ["日"], "topic_tags": ["career"]},
        {"rule_id": "dexiu", "name": "德秀贵人", "axis": "助力", "pillar_labels": ["月"], "topic_tags": ["career"]},
    ]
    pillars = [
        {"label": "年", "stem": "甲", "branch": "寅", "text": "甲寅"},
        {"label": "月", "stem": "丙", "branch": "午", "text": "丙午"},
        {"label": "日", "stem": "甲", "branch": "辰", "text": "甲辰", "xunkong": "寅卯"},
        {"label": "时", "stem": "庚", "branch": "申", "text": "庚申"},
    ]

    combinations = module.evaluate_shensha_effects(hits, pillars, {})["combinations"]

    assert "禄马交驰" in {item["title"] for item in combinations}
    products = [item for item in combinations if item["tier"] == "product_cluster"]
    assert products
    assert all(not item["title"].startswith("现代组合·") for item in products)
    assert all("不作古法格局名" not in item["summary"] for item in products)
    assert all(item["member_names"] for item in products)
