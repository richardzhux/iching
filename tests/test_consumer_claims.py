from __future__ import annotations

from copy import deepcopy
from datetime import datetime
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
from iching.core.metaphysics import build_metaphysics_chart


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


def test_theme_and_signature_claims_keep_existing_provenance_and_comparison() -> None:
    pillars, structure = _chart("丁卯", "癸酉", "甲午", "辛未")
    profiles = deepcopy(structure["theme_profiles"])
    wealth = next(profile for profile in profiles if profile["theme"] == "财富")
    hidden_wealth = next(
        evidence for evidence in wealth["evidence"] if evidence["family"] == "财星藏根"
    )
    hidden_wealth["rule_ids"] = ["bazi.rule.hidden-wealth"]
    hidden_wealth["source_ids"] = ["bazi.source.hidden-wealth"]
    wealth["comparisons"] = [
        {
            "metric_id": "hidden_wealth_count",
            "status": "observed",
            "comparison_mode": "rank_interval",
            "display_label": "资源更偏内藏积累 · 相对偏高",
            "display_mode": "directional",
            "display_direction": "high",
            "display_percentage": "8.40%",
            "same_percentage": 8.4,
            "lower_percentage": 86.0,
            "higher_percentage": 5.6,
            "value": 3,
            "baseline_id": "bazi-test-baseline",
        }
    ]

    claims = compile_consumer_claims(
        patterns=assess_patterns(pillars, structure),
        theme_profiles=profiles,
        shensha_effects={},
        cycles=[],
    )
    career = next(
        claim
        for claim in claims
        if claim["slot"] == "theme" and claim["theme"] == "career"
    )
    wealth_claim = next(
        claim
        for claim in claims
        if claim["slot"] == "theme" and claim["theme"] == "wealth"
    )
    signature = next(
        claim
        for claim in claims
        if claim["slot"] == "signature" and hidden_wealth["id"] in claim["evidenceIds"]
    )

    assert career["ruleIds"] and career["sourceIds"]
    assert wealth_claim["ruleIds"] == ["bazi.rule.hidden-wealth"]
    assert wealth_claim["sourceIds"] == ["bazi.source.hidden-wealth"]
    assert signature["ruleIds"] == ["bazi.rule.hidden-wealth"]
    assert signature["sourceIds"] == ["bazi.source.hidden-wealth"]
    assert signature["comparison"] == {
        "kind": "rank_interval",
        "metricId": "hidden_wealth_count",
        "status": "observed",
        "value": 3,
        "display": "资源更偏内藏积累 · 相对偏高",
        "displayMode": "directional",
        "displayDirection": "high",
        "displayPercentage": "8.40%",
        "samePercentage": 8.4,
        "lowerPercentage": 86.0,
        "higherPercentage": 5.6,
        "baselineId": "bazi-test-baseline",
    }
    projected = project_consumer_claims(claims)
    fingerprint = next(
        item for item in projected["fingerprints"] if item["id"] == signature["id"]
    )
    assert fingerprint["comparison_kind"] == "rank_interval"
    assert fingerprint["comparison_label"] == "资源更偏内藏积累 · 相对偏高"
    assert fingerprint["incidence_percentage"] is None


def test_timeline_claims_trace_events_without_inventing_source_ids() -> None:
    cycles = _cycles()
    cycles[0]["theme_activations"]["事业"] = [
        {
            "id": "bazi.period.dayun.career.shensha.1",
            "kind": "新增",
            "label": "大运神煞·驿马",
            "detail": "日支命中驿马规则。",
            "feature": "yima",
            "source": "版本化神煞注册表",
            "source_ids": ["bazi.source.yima"],
        },
        {
            "id": "bazi.period.dayun.career.relation.2",
            "kind": "联动",
            "label": "大运关系·地支冲",
            "detail": "大运支与原局形成地支冲。",
            "feature": "地支冲",
            "source": "结构化干支关系",
        },
    ]
    claims = compile_consumer_claims(
        patterns={},
        theme_profiles=[],
        shensha_effects={},
        cycles=cycles,
    )
    window = next(claim for claim in claims if claim["slot"] == "timeline")

    assert window["evidenceIds"] == [
        "bazi.period.dayun.career.shensha.1",
        "bazi.period.dayun.career.relation.2",
    ]
    assert window["ruleIds"] == ["yima"]
    assert window["sourceIds"] == ["bazi.source.yima"]
    assert "结构化干支关系" not in window["sourceIds"]
    assert window["activation"]["drivers"][0]["evidenceIds"] == [
        "bazi.period.dayun.career.shensha.1"
    ]
    assert window["activation"]["drivers"][0]["ruleIds"] == ["yima"]


def test_common_ten_god_signature_uses_its_matching_distribution_metric() -> None:
    claims = compile_consumer_claims(
        patterns={},
        theme_profiles=[
            {
                "theme": "事业",
                "evidence": [
                    {
                        "id": "bazi.evidence.career.officer",
                        "family": "官杀",
                        "title": "官杀分布",
                        "detail": "官杀共见三项。",
                    }
                ],
                "structure_metrics": [],
                "comparisons": [
                    {
                        "metric_id": "officer_count",
                        "status": "observed",
                        "comparison_mode": "rank_interval",
                        "display_label": "责任结构更集中 · 相对偏高",
                        "same_percentage": 12.5,
                        "baseline_id": "bazi-test-baseline",
                    }
                ],
            }
        ],
        shensha_effects={},
        cycles=[],
    )
    signature = next(claim for claim in claims if claim["slot"] == "signature")

    assert signature["comparison"]["metricId"] == "officer_count"
    assert signature["comparison"]["display"] == "责任结构更集中 · 相对偏高"


def test_canonical_authority_controls_the_consumer_hero() -> None:
    claims, patterns = _compiled()
    changed = deepcopy(patterns)
    canonical = next(
        item
        for item in changed["source_backed_authority"]["pattern_set"]["patterns"]
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

    assert original_hero["title"] == "正官格 · 救成"
    assert rebuilt_hero["title"] == "正官格 · 受制"
    assert original_hero["ruleIds"]
    assert original_hero["sourceIds"]
    assert rebuilt_hero["patternId"] == "direct_officer"
    assert rebuilt_hero["ruleIds"]
    assert rebuilt_hero["sourceIds"]


def test_ambiguous_canonical_result_never_falls_back_to_legacy_verdict() -> None:
    _, patterns = _compiled()
    changed = deepcopy(patterns)
    authority = changed["source_backed_authority"]["pattern_set"]
    authority["active_pattern_ids"] = []
    authority["ambiguous_pattern_ids"] = ["direct_officer"]
    canonical = next(
        item for item in authority["patterns"] if item["pattern_id"] == "direct_officer"
    )
    canonical["candidate"] = "unknown"
    canonical["status"] = "undetermined"
    changed["primary"]["status"] = "rescued"
    changed["primary"]["title"] = "不应显示的旧格局结论"

    claims = compile_consumer_claims(
        patterns=changed,
        theme_profiles=_chart("丁卯", "癸酉", "甲午", "辛未")[1]["theme_profiles"],
        shensha_effects=_effects(),
        cycles=_cycles(),
    )
    hero = next(claim for claim in claims if claim["slot"] == "hero")

    assert hero["title"] == "正官格 · 待定"
    assert "旧格局" not in hero["title"]
    assert hero["ruleIds"] == []
    assert hero["sourceIds"] == []
    assert "patternId" not in hero
    assert not [
        claim
        for claim in claims
        if claim["classicalRole"] in {"formation_path", "damage", "rescue"}
    ]


def test_multiple_active_canonical_patterns_are_not_reduced_by_sort_order() -> None:
    _, patterns = _compiled()
    changed = deepcopy(patterns)
    authority = changed["source_backed_authority"]["pattern_set"]
    second = next(
        item for item in authority["patterns"] if item["pattern_id"] == "seven_killings"
    )
    second["candidate"] = "true"
    second["status"] = "candidate"
    authority["active_pattern_ids"] = ["direct_officer", "seven_killings"]
    authority["ambiguous_pattern_ids"] = []

    claims = compile_consumer_claims(
        patterns=changed,
        theme_profiles=_chart("丁卯", "癸酉", "甲午", "辛未")[1]["theme_profiles"],
        shensha_effects=_effects(),
        cycles=_cycles(),
    )
    hero = next(claim for claim in claims if claim["slot"] == "hero")

    assert hero["title"] == "多重主导结构 · 并见"
    assert "正官格" in hero["summary"]
    assert "七杀格" in hero["summary"]
    assert "patternId" not in hero
    assert hero["ruleIds"] == []
    assert hero["sourceIds"] == []


def test_empty_canonical_result_uses_neutral_undetermined_hero() -> None:
    _, patterns = _compiled()
    changed = deepcopy(patterns)
    authority = changed["source_backed_authority"]["pattern_set"]
    authority["active_pattern_ids"] = []
    authority["ambiguous_pattern_ids"] = []
    changed["primary"]["title"] = "不应显示的旧格局结论"

    claims = compile_consumer_claims(
        patterns=changed,
        theme_profiles=_chart("丁卯", "癸酉", "甲午", "辛未")[1]["theme_profiles"],
        shensha_effects=_effects(),
        cycles=_cycles(),
    )
    hero = next(claim for claim in claims if claim["slot"] == "hero")

    assert hero["title"] == "主导结构 · 待定"
    assert hero["ruleIds"] == []
    assert hero["sourceIds"] == []


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
            "source_backed_authority": {
                "authoritative": True,
                "pattern_set": {
                    "active_pattern_ids": ["direct_officer"],
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
    formation = next(
        claim for claim in claims if claim["classicalRole"] == "formation_path"
    )
    assert formation["lifecycleProvenance"] == [
        {
            "pathId": "wealth_support",
            "ruleId": "zzq.rule.officer.form-wealth",
            "sourceIds": ["zzq.prop.officer.form-wealth"],
        }
    ]
    damage = next(claim for claim in claims if claim["classicalRole"] == "damage")
    rescue = next(claim for claim in claims if claim["classicalRole"] == "rescue")
    assert damage["ruleIds"] == ["zzq.rule.officer.damage"]
    assert damage["sourceIds"] == ["zzq.prop.officer.damage"]
    assert damage["pathIds"] == ["wealth_support"]
    assert damage["lifecycleProvenance"] == [
        {
            "pathId": "wealth_support",
            "ruleId": "zzq.rule.officer.damage",
            "sourceIds": ["zzq.prop.officer.damage"],
        }
    ]
    assert rescue["ruleIds"] == ["zzq.rule.officer.rescue"]
    assert rescue["sourceIds"] == ["zzq.prop.officer.rescue"]
    assert rescue["pathIds"] == ["wealth_support"]
    assert rescue["lifecycleProvenance"] == [
        {
            "pathId": "wealth_support",
            "ruleId": "zzq.rule.officer.rescue",
            "sourceIds": ["zzq.prop.officer.rescue"],
        }
    ]


def test_canonical_damage_and_rescue_do_not_depend_on_legacy_copy_arrays() -> None:
    claims, patterns = _compiled()
    baseline_roles = {
        claim["classicalRole"]
        for claim in claims
        if claim["classicalRole"] in {"damage", "rescue"}
    }
    changed = deepcopy(patterns)
    changed["primary"]["constraints"] = []
    changed["primary"]["rescues"] = []

    rebuilt = compile_consumer_claims(
        patterns=changed,
        theme_profiles=_chart("丁卯", "癸酉", "甲午", "辛未")[1]["theme_profiles"],
        shensha_effects=_effects(),
        cycles=_cycles(),
    )
    rebuilt_roles = {
        claim["classicalRole"]
        for claim in rebuilt
        if claim["classicalRole"] in {"damage", "rescue"}
    }

    assert rebuilt_roles == baseline_roles
    assert all(
        claim["ruleIds"] and claim["sourceIds"]
        for claim in rebuilt
        if claim["classicalRole"] in {"damage", "rescue"}
    )


def test_consumer_formation_path_comes_from_canonical_authority() -> None:
    claims, _ = _compiled()
    formation = next(
        claim
        for claim in claims
        if claim["slot"] == "signature" and claim["classicalRole"] == "formation_path"
    )

    assert formation["title"] == "官印相生"
    assert formation["pathId"] == "seal_support"
    assert formation["ruleIds"]
    assert formation["sourceIds"]
    assert all(
        "pathId" not in claim and claim["expressionPathId"].startswith("bazi.path.")
        for claim in claims
        if claim["slot"] == "theme"
    )


def test_canonical_damage_and_rescue_keep_exact_provenance() -> None:
    claims, _ = _compiled()

    lifecycle_claims = [
        claim for claim in claims if claim["classicalRole"] in {"damage", "rescue"}
    ]
    assert {claim["classicalRole"] for claim in lifecycle_claims} == {
        "damage",
        "rescue",
    }
    assert all(claim["ruleIds"] and claim["sourceIds"] for claim in lifecycle_claims)


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


def test_hero_provenance_binds_true_chart_facts_to_rules_and_sources() -> None:
    chart = build_metaphysics_chart(
        datetime(2004, 6, 26, 4, 33),
        timezone_name="Asia/Shanghai",
        gender="male",
    )
    hero = next(
        claim for claim in chart["consumer"]["claims"] if claim["slot"] == "hero"
    )

    assert hero["provenanceBindings"]
    assert {binding["ruleId"] for binding in hero["provenanceBindings"]} == set(
        hero["ruleIds"]
    )
    for binding in hero["provenanceBindings"]:
        assert binding["sourceIds"]
        assert binding["factRefs"]
        assert all(
            fact.get("path") or fact.get("matchIds") for fact in binding["factRefs"]
        )
