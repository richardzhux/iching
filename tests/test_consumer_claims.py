from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from iching.core.bazi_patterns import assess_patterns
from iching.core.bazi_structure import (
    BRANCH_ELEMENTS,
    HIDDEN_STEMS,
    STEM_ELEMENTS,
    _ten_god,
    build_structure_profile,
)
from iching.core.consumer_claims import (
    CLAIM_THEME_ORDER,
    CONSUMER_CLAIMS_VERSION,
    compile_consumer_claims,
    project_consumer_claims,
)


def _chart(*texts: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    labels = ("年", "月", "日", "时")
    day_stem = texts[2][0]
    pillars = []
    for label, text in zip(labels, texts):
        stem, branch = text
        pillars.append(
            {
                "label": label,
                "stem": stem,
                "branch": branch,
                "text": text,
                "stem_element": STEM_ELEMENTS[stem],
                "branch_element": BRANCH_ELEMENTS[branch],
                "ten_god": "日主" if label == "日" else _ten_god(day_stem, stem),
                "hidden_stems": [
                    {
                        "stem": hidden,
                        "element": STEM_ELEMENTS[hidden],
                        "ten_god": _ten_god(day_stem, hidden),
                    }
                    for hidden in HIDDEN_STEMS[branch]
                ],
            }
        )
    structure = build_structure_profile(
        pillars,
        gender="male",
        shensha_hits=[],
        seasonal_status={"木": "囚", "火": "死", "土": "休", "金": "旺", "水": "相"},
    )
    return pillars, structure


def _cycles() -> list[dict[str, Any]]:
    result = []
    for index, start in enumerate((2026, 2036, 2046, 2056), start=1):
        result.append(
            {
                "index": index,
                "label": f"第{index}运",
                "ganzhi": ("甲子", "乙丑", "丙寅", "丁卯")[index - 1],
                "start_year": start,
                "end_year": start + 9,
                "start_timestamp": f"{start}-02-04T00:00:00+08:00",
                "end_timestamp": f"{start + 10}-02-04T00:00:00+08:00",
                "is_current": index == 1,
                "theme_activations": {
                    "事业": [
                        {
                            "kind": "新增",
                            "label": f"第{index}运十神",
                            "detail": "",
                            "source": "日主中心十神",
                        },
                        {
                            "kind": "联动",
                            "label": f"第{index}运关系",
                            "detail": "",
                            "source": "结构化干支关系",
                        },
                    ],
                    "财富": [],
                    "感情": [],
                    "五行与承压结构": [],
                },
                "years": [],
            }
        )
    return result


def _effects() -> dict[str, Any]:
    return {
        "hits": [
            {"rule_id": "wenchang", "name": "文昌贵人", "state": "发力"},
        ],
        "combinations": [
            {
                "id": "bazi.shensha.combination.single",
                "title": "单项神煞",
                "tier": "product_cluster",
                "summary": "不应成为组合 claim。",
                "member_rule_ids": ["wenchang"],
            },
            {
                "id": "bazi.shensha.combination.learning_mobility",
                "title": "才学迁动",
                "tier": "classical_interaction",
                "summary": "才学与迁动结构共同出现。",
                "member_rule_ids": ["wenchang", "yima"],
            },
        ],
    }


def _compiled() -> tuple[list[dict[str, Any]], Mapping[str, Any]]:
    pillars, structure = _chart("丁卯", "癸酉", "甲午", "辛未")
    patterns = assess_patterns(pillars, structure)
    claims = compile_consumer_claims(
        patterns=patterns,
        theme_profiles=structure["theme_profiles"],
        shensha_effects=_effects(),
        cycles=_cycles(),
        feature_metrics=[
            {
                "feature_id": "bazi.shensha.combination.learning_mobility",
                "status": "observed",
                "percentage": 8.25,
                "baseline_id": "bazi-test-baseline",
            }
        ],
    )
    return claims, patterns


def _forbidden_keys(value: Any) -> set[str]:
    forbidden = {"score", "raw_score", "percentile", "rank", "top_percentage"}
    found: set[str] = set()
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key) in forbidden:
                found.add(str(key))
            found.update(_forbidden_keys(child))
    elif isinstance(value, list):
        for child in value:
            found.update(_forbidden_keys(child))
    return found


def test_complete_chart_compiles_fixed_claim_slots_in_classical_order() -> None:
    claims, _ = _compiled()
    slots = [claim["slot"] for claim in claims]

    assert slots.count("hero") == 1
    assert slots.count("theme") == 4
    assert 3 <= slots.count("signature") <= 5
    assert 0 <= slots.count("combination") <= 4
    assert slots.count("timeline") == 3
    assert slots == sorted(
        slots,
        key=("hero", "theme", "signature", "combination", "timeline").index,
    )
    assert [claim["theme"] for claim in claims if claim["slot"] == "theme"] == list(
        CLAIM_THEME_ORDER
    )
    assert not _forbidden_keys(claims)


def test_claims_are_deterministic_and_every_trace_array_is_present() -> None:
    first, patterns = _compiled()
    reordered_cycles = list(reversed(_cycles()))
    for cycle in reordered_cycles:
        cycle["theme_activations"]["事业"].reverse()
    second = compile_consumer_claims(
        patterns=patterns,
        theme_profiles=_chart("丁卯", "癸酉", "甲午", "辛未")[1]["theme_profiles"],
        shensha_effects=_effects(),
        cycles=reordered_cycles,
        feature_metrics=[
            {
                "feature_id": "bazi.shensha.combination.learning_mobility",
                "status": "observed",
                "percentage": 8.25,
                "baseline_id": "bazi-test-baseline",
            }
        ],
    )

    assert first == second
    assert all(
        isinstance(claim[key], list)
        for claim in first
        for key in ("evidenceIds", "ruleIds", "sourceIds")
    )
    assert all(
        claim["activation"]["drivers"] for claim in first if claim["slot"] == "timeline"
    )


def test_shadow_adds_ids_but_cannot_override_legacy_hero() -> None:
    claims, patterns = _compiled()
    changed = deepcopy(patterns)
    canonical = next(
        item
        for item in changed["source_backed_shadow"]["pattern_set"]["patterns"]
        if item["pattern_id"] == "direct_officer"
    )
    canonical["status"] = "broken"
    rebuilt = compile_consumer_claims(
        patterns=changed,
        theme_profiles=_chart("丁卯", "癸酉", "甲午", "辛未")[1]["theme_profiles"],
        shensha_effects=_effects(),
        cycles=_cycles(),
    )
    original_hero = next(claim for claim in claims if claim["slot"] == "hero")
    rebuilt_hero = next(claim for claim in rebuilt if claim["slot"] == "hero")

    assert original_hero["title"] == rebuilt_hero["title"] == "正官格 · 救成"
    # Equal status is insufficient: the legacy `officer_wealth` formation path
    # differs from the canonical `seal_support` path.
    assert original_hero["ruleIds"] == []
    assert original_hero["sourceIds"] == []
    assert rebuilt_hero["patternId"] == "direct_officer"
    assert rebuilt_hero["ruleIds"] == []
    assert rebuilt_hero["sourceIds"] == []
    assert not [
        claim for claim in rebuilt if claim["classicalRole"] in {"damage", "rescue"}
    ]


def test_exact_formation_path_binds_hero_damage_and_rescue_provenance() -> None:
    claims = compile_consumer_claims(
        patterns={
            "primary": {
                "id": "bazi.pattern.ordinary.direct_officer",
                "name": "正官",
                "title": "正官格",
                "status": "rescued",
                "summary": "正官格破而有救，成格路径为财星生官。",
                "formation_path": {"id": "wealth_support", "title": "财星生官"},
                "constraints": ["伤官见官"],
                "rescues": ["印星制伤"],
                "evidence_ids": [
                    "legacy.officer.formation",
                    "legacy.officer.constraint",
                    "legacy.officer.rescue",
                ],
            },
            "evidence": [
                {"id": "legacy.officer.formation", "kind": "formation_path"},
                {"id": "legacy.officer.constraint", "kind": "constraint"},
                {"id": "legacy.officer.rescue", "kind": "rescue"},
            ],
            "source_backed_shadow": {
                "authoritative": False,
                "pattern_set": {
                    "patterns": [
                        {
                            "pattern_id": "direct_officer",
                            "candidate": "true",
                            "status": "rescued",
                            "paths": [
                                {
                                    "path_id": "wealth_support",
                                    "status": "rescued",
                                    "actual_damage_ids": ["zzq.rule.officer.damage"],
                                    "active_rescue_ids": ["zzq.rule.officer.rescue"],
                                }
                            ],
                            "stages": [
                                {
                                    "stage": "candidate",
                                    "rules": [
                                        {
                                            "rule_id": "zzq.rule.officer.candidate",
                                            "truth": "true",
                                            "path_id": None,
                                            "source_ids": ["zzq.prop.officer.route"],
                                        }
                                    ],
                                },
                                {
                                    "stage": "formation",
                                    "rules": [
                                        {
                                            "rule_id": "zzq.rule.officer.form-wealth",
                                            "truth": "true",
                                            "path_id": "wealth_support",
                                            "source_ids": [
                                                "zzq.prop.officer.form-wealth"
                                            ],
                                        }
                                    ],
                                },
                                {
                                    "stage": "damage",
                                    "rules": [
                                        {
                                            "rule_id": "zzq.rule.officer.damage",
                                            "truth": "true",
                                            "path_id": "wealth_support",
                                            "source_ids": ["zzq.prop.officer.damage"],
                                        }
                                    ],
                                },
                                {
                                    "stage": "rescue",
                                    "rules": [
                                        {
                                            "rule_id": "zzq.rule.officer.rescue",
                                            "truth": "true",
                                            "path_id": "wealth_support",
                                            "source_ids": ["zzq.prop.officer.rescue"],
                                        }
                                    ],
                                },
                            ],
                        }
                    ],
                },
            },
        },
        theme_profiles=[],
        shensha_effects={},
        cycles=[],
    )
    hero = claims[0]

    assert hero["ruleIds"] == [
        "zzq.rule.officer.candidate",
        "zzq.rule.officer.form-wealth",
        "zzq.rule.officer.damage",
        "zzq.rule.officer.rescue",
    ]
    assert hero["sourceIds"] == [
        "zzq.prop.officer.route",
        "zzq.prop.officer.form-wealth",
        "zzq.prop.officer.damage",
        "zzq.prop.officer.rescue",
    ]
    damage = next(claim for claim in claims if claim["classicalRole"] == "damage")
    rescue = next(claim for claim in claims if claim["classicalRole"] == "rescue")
    assert damage["ruleIds"] == ["zzq.rule.officer.damage"]
    assert damage["sourceIds"] == ["zzq.prop.officer.damage"]
    assert rescue["ruleIds"] == ["zzq.rule.officer.rescue"]
    assert rescue["sourceIds"] == ["zzq.prop.officer.rescue"]


def test_legacy_and_canonical_path_ids_are_never_guessed_across() -> None:
    claims, _ = _compiled()
    formation = next(
        claim
        for claim in claims
        if claim["slot"] == "signature" and claim["classicalRole"] == "formation_path"
    )

    assert formation["title"] == "官逢财生"
    assert "pathId" not in formation
    assert formation["ruleIds"] == []
    assert formation["sourceIds"] == []
    assert all(
        "pathId" not in claim and claim["expressionPathId"].startswith("bazi.path.")
        for claim in claims
        if claim["slot"] == "theme"
    )


def test_mismatched_formation_path_suppresses_damage_and_rescue_provenance() -> None:
    claims, _ = _compiled()

    assert not [
        claim for claim in claims if claim["classicalRole"] in {"damage", "rescue"}
    ]


def test_special_pattern_without_canonical_match_does_not_fabricate_ids() -> None:
    claims = compile_consumer_claims(
        patterns={
            "primary": {
                "id": "bazi.pattern.special.follow_wealth",
                "name": "从财",
                "title": "从财格",
                "status": "formed",
                "summary": "从财格成立。",
                "evidence_ids": ["bazi.pattern.follow_wealth.gate.1"],
            },
            "source_backed_shadow": {
                "authoritative": False,
                "pattern_set": {"patterns": []},
            },
        },
        theme_profiles=[],
        shensha_effects={},
        cycles=[],
    )
    hero = claims[0]

    assert hero["title"] == "从财格 · 成格"
    assert "patternId" not in hero
    assert "pathId" not in hero
    assert hero["ruleIds"] == []
    assert hero["sourceIds"] == []


def test_single_shensha_is_never_promoted_and_combinations_require_two_rules() -> None:
    claims, _ = _compiled()
    combinations = [claim for claim in claims if claim["slot"] == "combination"]

    assert [claim["title"] for claim in combinations] == ["才学迁动"]
    assert all(len(claim["ruleIds"]) >= 2 for claim in combinations)
    assert all("文昌贵人" not in claim["title"] for claim in claims)
    assert combinations[0]["comparison"] == {
        "kind": "incidence",
        "featureId": "bazi.shensha.combination.learning_mobility",
        "status": "observed",
        "percentage": 8.25,
        "display": "历法样本出现率 8.25%",
        "baselineId": "bazi-test-baseline",
    }
    assert combinations[0]["sourceIds"] == []


def test_missing_feature_metric_never_creates_fallback_rarity() -> None:
    pillars, structure = _chart("丁卯", "癸酉", "甲午", "辛未")
    claims = compile_consumer_claims(
        patterns=assess_patterns(pillars, structure),
        theme_profiles=structure["theme_profiles"],
        shensha_effects=_effects(),
        cycles=[],
    )
    combination = next(claim for claim in claims if claim["slot"] == "combination")

    assert "comparison" not in combination
    assert not [claim for claim in claims if claim["slot"] == "timeline"]


def test_timeline_requires_an_explicit_current_cycle() -> None:
    cycles = _cycles()
    for cycle in cycles:
        cycle["is_current"] = False
    claims, patterns = _compiled()
    rebuilt = compile_consumer_claims(
        patterns=patterns,
        theme_profiles=_chart("丁卯", "癸酉", "甲午", "辛未")[1]["theme_profiles"],
        shensha_effects=_effects(),
        cycles=cycles,
    )

    assert not [claim for claim in rebuilt if claim["slot"] == "timeline"]


def test_compatibility_projection_comes_only_from_claims() -> None:
    claims, _ = _compiled()
    projected = project_consumer_claims(claims)

    assert projected["identity"]["archetype_title"] == claims[0]["title"]
    assert (
        projected["identity"]["archetype_title"]
        not in projected["identity"]["archetype_subtitle"]
    )
    assert [subject["key"] for subject in projected["subjects"]] == [
        "career",
        "wealth",
        "relationship",
        "health",
    ]
    assert len(projected["fingerprints"]) == len(
        [claim for claim in claims if claim["slot"] == "signature"]
    )
    assert all("top_percentage" not in item for item in projected["fingerprints"])
    assert projected["achievements"][0]["rarity_percentage"] == 8.25
    assert all(
        subject["headline"] != subject["path_label"]
        for subject in projected["subjects"]
    )
    assert CONSUMER_CLAIMS_VERSION == "consumer-claims-2026.07-v1"
