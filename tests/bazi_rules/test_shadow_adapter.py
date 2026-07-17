from __future__ import annotations

import hashlib
import inspect
import json
from datetime import datetime
from typing import Any

import pytest

import iching.core.bazi_patterns as patterns_module
import iching.core.metaphysics as metaphysics_module
from iching.core.bazi_patterns import _assess_patterns_legacy, assess_patterns
from iching.core.bazi_rules.adapter import (
    SHADOW_DIFF_REASONS,
    build_source_backed_shadow,
)
from iching.core.bazi_rules.fact_graph import (
    build_bazi_fact_envelope,
    build_bazi_fact_graph,
)
from iching.core.bazi_structure import (
    BRANCH_ELEMENTS,
    HIDDEN_STEMS,
    STEM_ELEMENTS,
    _ten_god,
    build_structure_profile,
)


FIXTURES = {
    "xue": ("甲申", "壬申", "乙巳", "戊寅"),
    "anonymous": ("壬戌", "丁未", "戊申", "乙卯"),
    "jin": ("乙卯", "丁亥", "丁未", "庚戌"),
    "xuan": ("己卯", "辛未", "壬寅", "辛亥"),
    "li": ("庚寅", "乙酉", "甲子", "戊辰"),
    "fan": ("丁丑", "壬寅", "己巳", "丙寅"),
}

TASK4_SHADOW_PROJECTION_HASHES = {
    "xue": (9571, "e64239d630044d1e35a608ac4a0feca478861cda6c4b954bb03adb9175d1ab90"),
    "anonymous": (
        10003,
        "87ea1d32abcafba1f342b2b5f89f670a2015d4554bd515d82f3d6f8810800c0b",
    ),
    "jin": (9485, "11dafa97bbf34ea57a0880b1a9332034b913c3ee3030a7d359f307341ff70bca"),
    "xuan": (9908, "cfbaed588f4c975eb9a9074db0bca1453e5c32c24780667598d814ed75f231dd"),
    "li": (9182, "5bccaa767fd19fc0e90f1c3439cd97a33f4e2bc07402e7bc7d54b2ffb132c153"),
    "fan": (9787, "3c1bbcdc57d73867d06288a36962613b31f1d9bd9b0d47d036bcadf86c15349c"),
}

TASK4_SHADOW_KEYS = (
    "mode",
    "authoritative",
    "bundle_id",
    "bundle_digest",
    "generic_result",
    "example_attestations",
    "legacy_status",
    "diff",
)


def _chart(*texts: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    day_stem = texts[2][0]
    pillars = []
    for label, text in zip(("年", "月", "日", "时"), texts):
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
    graph = build_bazi_fact_graph(pillars)
    structure = build_structure_profile(
        pillars,
        gender=None,
        shensha_hits=(),
        seasonal_status={
            "木": "囚",
            "火": "死",
            "土": "休",
            "金": "旺",
            "水": "相",
        },
        fact_graph=graph,
    )
    return pillars, structure


def test_public_pattern_signature_keeps_two_positional_arguments() -> None:
    parameters = tuple(inspect.signature(assess_patterns).parameters.values())

    assert [item.name for item in parameters[:2]] == ["pillars", "structure"]
    assert all(item.kind is inspect.Parameter.KEYWORD_ONLY for item in parameters[2:])


def test_canonical_authority_is_added_without_mutating_legacy_values() -> None:
    pillars, structure = _chart(*FIXTURES["li"])
    legacy = _assess_patterns_legacy(pillars, structure)

    result = assess_patterns(
        pillars,
        structure,
        fact_graph=build_bazi_fact_graph(pillars),
    )

    assert set(result) == {
        *legacy,
        "source_backed_shadow",
        "source_backed_authority",
    }
    assert {
        key: value
        for key, value in result.items()
        if key not in {"source_backed_shadow", "source_backed_authority"}
    } == legacy
    assert result["source_backed_shadow"]["authoritative"] is False
    assert result["source_backed_authority"]["authoritative"] is True
    assert (
        result["source_backed_authority"]["bundle_digest"]
        == result["source_backed_shadow"]["pattern_set"]["bundle_digest"]
    )


def test_supplied_graph_is_reused_and_incomplete_input_is_guarded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pillars, structure = _chart(*FIXTURES["xue"])
    graph = build_bazi_fact_graph(pillars)

    def forbidden(_pillars: Any) -> Any:
        raise AssertionError("pattern adapter rebuilt the fact graph")

    monkeypatch.setattr(patterns_module, "build_bazi_fact_graph", forbidden)
    result = assess_patterns(pillars, structure, fact_graph=graph)
    incomplete = assess_patterns(pillars[:2], structure)

    assert (
        result["source_backed_shadow"]["generic_result"]["world_digest"] == graph.digest
    )
    assert "source_backed_shadow" not in incomplete


def test_legacy_tolerated_graph_unsafe_inputs_return_legacy_payload() -> None:
    pillars, structure = _chart(*FIXTURES["xue"])
    duplicate_labels = [dict(item) for item in pillars]
    duplicate_labels[-1]["label"] = "年"
    invalid_position = [dict(item) for item in pillars]
    invalid_position[0]["position"] = "not-a-pillar-position"

    for malformed in (duplicate_labels, invalid_position):
        legacy = _assess_patterns_legacy(malformed, structure)
        result = assess_patterns(malformed, structure)

        assert result == legacy
        assert "source_backed_shadow" not in result


def test_supplied_fact_graph_must_describe_the_same_pillars() -> None:
    fan_pillars, fan_structure = _chart(*FIXTURES["fan"])
    li_pillars, _ = _chart(*FIXTURES["li"])
    legacy = _assess_patterns_legacy(fan_pillars, fan_structure)

    result = assess_patterns(
        fan_pillars,
        fan_structure,
        fact_graph=build_bazi_fact_graph(li_pillars),
    )

    assert result == legacy
    assert "source_backed_shadow" not in result


def test_complete_pillars_reject_multi_world_envelope_in_direct_adapter() -> None:
    fan_pillars, fan_structure = _chart(*FIXTURES["fan"])
    li_pillars, _ = _chart(*FIXTURES["li"])
    envelope = build_bazi_fact_envelope((fan_pillars, li_pillars))

    with pytest.raises(ValueError, match="single BaziFactGraph"):
        build_source_backed_shadow(
            fan_pillars,
            fan_structure,
            envelope,
        )


def test_assess_patterns_returns_legacy_for_complete_pillars_and_envelope() -> None:
    fan_pillars, fan_structure = _chart(*FIXTURES["fan"])
    li_pillars, _ = _chart(*FIXTURES["li"])
    envelope = build_bazi_fact_envelope((fan_pillars, li_pillars))
    legacy = _assess_patterns_legacy(fan_pillars, fan_structure)

    result = assess_patterns(
        fan_pillars,
        fan_structure,
        fact_graph=envelope,
    )

    assert result == legacy
    assert "source_backed_shadow" not in result


def test_nonempty_pillars_never_accept_supplied_envelope() -> None:
    fan_pillars, fan_structure = _chart(*FIXTURES["fan"])
    xue_pillars, _ = _chart(*FIXTURES["xue"])
    li_pillars, _ = _chart(*FIXTURES["li"])
    envelope = build_bazi_fact_envelope((xue_pillars, li_pillars))

    with pytest.raises(ValueError, match="single BaziFactGraph"):
        build_source_backed_shadow(fan_pillars, fan_structure, envelope)


@pytest.mark.parametrize(
    ("fixture", "required_reasons"),
    [
        ("anonymous", {"candidate_scope", "attestation_only"}),
        ("xuan", {"activation_semantics", "attestation_only"}),
        ("li", {"damage_binding", "rescue_binding"}),
        ("fan", {"attestation_only"}),
    ],
)
def test_focused_shadow_diffs_use_closed_reasons(
    fixture: str,
    required_reasons: set[str],
) -> None:
    pillars, structure = _chart(*FIXTURES[fixture])

    shadow = assess_patterns(pillars, structure)["source_backed_shadow"]
    diff = shadow["diff"]
    reasons = set(diff["reasons"])
    comparisons = diff["pattern_comparisons"]

    assert required_reasons <= reasons
    assert reasons <= set(SHADOW_DIFF_REASONS)
    assert "unclassified" not in reasons
    assert diff["compared_pattern_count"] == len(shadow["pattern_set"]["patterns"])
    assert [item["pattern_id"] for item in comparisons] == [
        item["pattern_id"] for item in shadow["pattern_set"]["patterns"]
    ]
    assert all(set(item["reasons"]) <= set(SHADOW_DIFF_REASONS) for item in comparisons)
    assert all(item["reasons"] for item in comparisons if item["is_difference"])
    assert all(not item["reasons"] for item in comparisons if not item["is_difference"])
    assert diff["unclassified_count"] == 0


def test_pattern_shadow_matching_uses_ids_not_legacy_list_order() -> None:
    pillars, structure = _chart(*FIXTURES["anonymous"])
    graph = build_bazi_fact_graph(pillars)
    legacy = _assess_patterns_legacy(pillars, structure)
    reordered = {
        **legacy,
        "ordinary": list(reversed(legacy["ordinary"])),
        "special": list(reversed(legacy["special"])),
    }

    original = build_source_backed_shadow(pillars, legacy, graph)
    changed = build_source_backed_shadow(pillars, reordered, graph)

    assert changed["diff"] == original["diff"]
    assert "legacy_list_order" not in changed["diff"]["reasons"]


def test_missing_legacy_pattern_is_an_explicit_classified_defect() -> None:
    pillars, structure = _chart(*FIXTURES["li"])
    graph = build_bazi_fact_graph(pillars)
    legacy = _assess_patterns_legacy(pillars, structure)
    missing = {
        **legacy,
        "ordinary": [
            item
            for item in legacy["ordinary"]
            if item["id"] != "bazi.pattern.ordinary.direct_officer"
        ],
    }

    shadow = build_source_backed_shadow(pillars, missing, graph)
    comparison = next(
        item
        for item in shadow["diff"]["pattern_comparisons"]
        if item["pattern_id"] == "direct_officer"
    )

    assert comparison["legacy_status"] == "missing"
    assert comparison["is_difference"] is True
    assert "defect" in comparison["reasons"]
    assert shadow["diff"]["unclassified_count"] == 0


def test_threshold_fallback_is_used_only_when_no_structural_reason_applies() -> None:
    pillars, structure = _chart(*FIXTURES["anonymous"])

    shadow = assess_patterns(pillars, structure)["source_backed_shadow"]
    comparison = next(
        item
        for item in shadow["diff"]["pattern_comparisons"]
        if item["pattern_id"] == "month_robbery"
    )

    assert comparison == {
        "pattern_id": "month_robbery",
        "canonical_status": "rejected",
        "legacy_status": "formed",
        "is_difference": True,
        "reasons": ["legacy_thresholds_shares"],
    }


def test_attestations_never_change_generic_canonical_result() -> None:
    pillars, structure = _chart(*FIXTURES["fan"])

    enabled = assess_patterns(pillars, structure, include_attestations=True)
    disabled = assess_patterns(pillars, structure, include_attestations=False)
    enabled_shadow = enabled["source_backed_shadow"]
    disabled_shadow = disabled["source_backed_shadow"]

    assert enabled_shadow["generic_result"] == disabled_shadow["generic_result"]
    assert enabled_shadow["example_attestations"]
    assert disabled_shadow["example_attestations"] == []


@pytest.mark.parametrize("fixture", tuple(FIXTURES))
def test_task4_shadow_projection_remains_byte_compatible(fixture: str) -> None:
    pillars, structure = _chart(*FIXTURES[fixture])

    shadow = assess_patterns(pillars, structure)["source_backed_shadow"]
    assert set(shadow) == {*TASK4_SHADOW_KEYS, "pattern_set", "overlay_results"}
    assert tuple(shadow) == (*TASK4_SHADOW_KEYS, "pattern_set", "overlay_results")
    projection = {key: shadow[key] for key in TASK4_SHADOW_KEYS}
    payload = json.dumps(
        projection,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")

    assert (len(payload), hashlib.sha256(payload).hexdigest()) == (
        TASK4_SHADOW_PROJECTION_HASHES[fixture]
    )


def test_metaphysics_passes_one_graph_by_identity_to_both_consumers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    built = []
    structure_seen = []
    patterns_seen = []
    real_build = metaphysics_module.build_bazi_fact_graph
    real_structure = metaphysics_module.build_structure_profile
    real_patterns = metaphysics_module.assess_patterns

    def build(pillars: Any) -> Any:
        graph = real_build(pillars)
        built.append(graph)
        return graph

    def structure(pillars: Any, **kwargs: Any) -> dict[str, Any]:
        structure_seen.append(kwargs.get("fact_graph"))
        return real_structure(pillars, **kwargs)

    def patterns(pillars: Any, profile: Any, **kwargs: Any) -> dict[str, Any]:
        patterns_seen.append(kwargs.get("fact_graph"))
        return real_patterns(pillars, profile, **kwargs)

    monkeypatch.setattr(metaphysics_module, "build_bazi_fact_graph", build)
    monkeypatch.setattr(metaphysics_module, "build_structure_profile", structure)
    monkeypatch.setattr(metaphysics_module, "assess_patterns", patterns)

    metaphysics_module.build_metaphysics_chart(
        datetime(2004, 6, 26, 4),
        timezone_name="Asia/Shanghai",
    )

    assert len(built) == 1
    assert structure_seen == [built[0]]
    assert patterns_seen == [built[0]]


def test_unknown_hour_shadow_uses_candidate_world_envelope_not_noon() -> None:
    chart = metaphysics_module.build_metaphysics_chart(
        datetime(2004, 6, 26, 4),
        timezone_name="Asia/Shanghai",
        hour_uncertain=True,
    )

    shadow = chart["structure"]["patterns"]["source_backed_shadow"]
    generic = shadow["generic_result"]
    assert shadow["legacy_status"] == "hour_uncertain"
    assert shadow["example_attestations"] == []
    assert generic["world_results"]
    assert generic["world_digest"] is None
    assert shadow["diff"]["compared_pattern_count"] == len(
        shadow["pattern_set"]["patterns"]
    )
    assert all(
        item["is_difference"] and "scope_gap" in item["reasons"]
        for item in shadow["diff"]["pattern_comparisons"]
    )
    assert shadow["diff"]["unclassified_count"] == 0
