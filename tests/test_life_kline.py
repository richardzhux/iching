from __future__ import annotations

from copy import deepcopy

from iching.core.metaphysics_consumer import THEME_ORDER, build_life_kline


PROFILE_LABELS = {
    "career": "事业",
    "wealth": "财富",
    "relationship": "感情",
    "rhythm": "五行与承压结构",
}


def _event(
    *,
    label: str,
    role: str = "neutral",
    delta: float = 0,
    layer: str = "liuyue",
    feature: str = "",
) -> dict:
    return {
        "id": f"event.{layer}.{label}",
        "layer": layer,
        "role": role,
        "delta": delta,
        "feature": feature,
        "label": label,
        "evidenceIds": [],
        "ruleIds": [],
    }


def _year(value: int, *, current: bool = False, signed: bool = True) -> dict:
    months = []
    for index in range(12):
        activations = {label: [] for label in PROFILE_LABELS.values()}
        if signed and index == 2:
            activations["事业"] = [_event(label=f"{value}事业联动", role="support", delta=4.5)]
        elif signed and index == 8:
            activations["事业"] = [_event(label=f"{value}事业冲突", role="conflict", delta=-6)]
        months.append({
            "index": index,
            "label": f"{index + 1}月",
            "ganzhi": "甲子",
            "theme_activations": activations,
        })
    return {
        "year": value,
        "is_current": current,
        "theme_activations": {label: [] for label in PROFILE_LABELS.values()},
        "months": months,
    }


def _cycles(*, signed: bool = True) -> list[dict]:
    return [
        {
            "label": "乙丑",
            "start_year": 2024,
            "end_year": 2033,
            "is_current": True,
            "theme_activations": {label: [] for label in PROFILE_LABELS.values()},
            "years": [_year(value, current=value == 2026, signed=signed) for value in range(2024, 2034)],
        },
        {
            "label": "丙寅",
            "start_year": 2034,
            "end_year": 2043,
            "is_current": False,
            "theme_activations": {label: [] for label in PROFILE_LABELS.values()},
            "years": [_year(value, signed=signed) for value in range(2034, 2044)],
        },
    ]


def test_kline_has_four_relative_series_real_ohlc_and_future_windows() -> None:
    result = build_life_kline(_cycles())

    assert [item["key"] for item in result["series"]] == list(THEME_ORDER)
    assert result["baseline"]["normalized_value"] == 100
    assert result["default_window"] == {"start_year": 2026, "end_year": 2035}
    assert len(result["stages"]) == 3
    assert all(item["year"] >= 2026 for item in result["stages"])
    assert all("score" not in item and "relative_index" in item for item in result["stages"])

    career = result["series"][0]
    point = career["points"][0]
    monthly = [month["value"] for month in point["months"]]
    assert len(monthly) == 12
    assert point["open"] == monthly[0]
    assert point["close"] == monthly[-1]
    assert point["high"] == max(monthly)
    assert point["low"] == min(monthly)
    assert point["high"] > 105
    assert point["low"] < 95


def test_neutral_ten_god_or_shensha_changes_volume_not_direction() -> None:
    cycles = _cycles(signed=False)
    neutral = _event(label="流月神煞·驿马", feature="yima")
    cycles[0]["years"][0]["months"][0]["theme_activations"]["事业"] = [neutral]

    result = build_life_kline(cycles)
    career = result["series"][0]

    assert {month["value"] for point in career["points"] for month in point["months"]} == {100.0}
    assert career["points"][0]["volume"] > 0


def test_period_match_uses_named_formation_driver_and_is_deterministic() -> None:
    cycles = _cycles(signed=False)
    event = _event(label="流月十神·正官", feature="正官")
    event.update({
        "role": "formation",
        "lifecycle": {
            "before": "inactive",
            "after": "formed",
            "patternId": "direct_officer",
            "pathId": "seal_support",
            "ruleIds": ["zzq.rule.officer.formation"],
            "sourceIds": ["zzq.prop.officer.formation"],
        },
    })
    cycles[0]["years"][2]["months"][1]["theme_activations"]["事业"] = [event]
    claims = [{
        "id": "bazi.claim.signature.officer.formation",
        "classicalRole": "formation_path",
        "title": "官印相生",
        "summary": "正官与正印形成主导路径。",
        "patternId": "direct_officer",
        "pathId": "seal_support",
        "evidenceIds": ["evidence.officer"],
        "ruleIds": ["zzq.rule.officer.formation"],
        "sourceIds": ["zzq.prop.officer.formation"],
        "lifecycleProvenance": [
            {
                "pathId": "seal_support",
                "ruleId": "zzq.rule.officer.formation",
                "sourceIds": ["zzq.prop.officer.formation"],
            }
        ],
    }]

    first = build_life_kline(cycles, claims=claims)
    reordered = deepcopy(cycles)
    reordered.reverse()
    for cycle in reordered:
        cycle["years"].reverse()
        for year in cycle["years"]:
            year["months"].reverse()
            for month in year["months"]:
                for events in month["theme_activations"].values():
                    events.reverse()
    second = build_life_kline(reordered, claims=claims)

    assert first == second
    month = first["series"][0]["points"][2]["months"][1]
    formation = next(driver for driver in month["drivers"] if driver["role"] == "formation")
    assert "呼应官印相生" in formation["label"]
    assert formation["ruleIds"] == ["zzq.rule.officer.formation"]
    assert month["value"] > 100


def test_legacy_or_unmatched_pattern_claims_are_display_only_in_kline() -> None:
    cycles = _cycles(signed=False)
    plain_ten_god = _event(label="流月十神·正官", feature="正官")
    mismatched_lifecycle = _event(label="流月格局变化·正官", feature="正官")
    mismatched_lifecycle.update({
        "role": "formation",
        "lifecycle": {
            "before": "inactive",
            "after": "formed",
            "patternId": "direct_officer",
            "pathId": "wealth_support",
            "ruleIds": ["zzq.rule.officer.other-formation"],
            "sourceIds": ["zzq.prop.officer.other-formation"],
        },
    })
    cycles[0]["years"][2]["months"][1]["theme_activations"]["事业"] = [
        plain_ten_god,
        mismatched_lifecycle,
    ]
    claims = [
        {
            "id": "bazi.claim.signature.officer.legacy-formation",
            "classicalRole": "formation_path",
            "title": "官逢财生",
            "summary": "正官与财星形成旧版路径。",
            "evidenceIds": ["legacy.officer.formation"],
            "ruleIds": [],
            "sourceIds": [],
        },
        {
            "id": "bazi.claim.signature.officer.source-backed-formation",
            "classicalRole": "formation_path",
            "title": "官印相生",
            "summary": "正官与正印形成主导路径。",
            "patternId": "direct_officer",
            "pathId": "seal_support",
            "evidenceIds": ["evidence.officer"],
            "ruleIds": ["zzq.rule.officer.formation"],
            "sourceIds": ["zzq.prop.officer.formation"],
        },
    ]

    result = build_life_kline(cycles, claims=claims)
    month = result["series"][0]["points"][2]["months"][1]

    assert month["value"] == 100.0
    assert all(float(driver.get("delta", 0)) == 0 for driver in month["drivers"])
    assert all(driver.get("layer") != "natal" for driver in month["drivers"])
    assert all(driver.get("label") != "官印相生" for driver in month["drivers"])


def test_lifecycle_driver_rejects_cross_path_provenance_and_wrong_transition() -> None:
    cycles = _cycles(signed=False)
    cross_path = _event(label="流月格局变化·正官", feature="正官")
    cross_path.update({
        "role": "formation",
        "lifecycle": {
            "before": "inactive",
            "after": "formed",
            "patternId": "direct_officer",
            "pathId": "seal_support",
            "ruleIds": ["zzq.rule.officer.wealth-formation"],
            "sourceIds": ["zzq.prop.officer.wealth-formation"],
        },
    })
    wrong_transition = _event(label="流月格局受制·正官", feature="正官")
    wrong_transition.update({
        "role": "formation",
        "lifecycle": {
            "before": "formed",
            "after": "broken",
            "patternId": "direct_officer",
            "pathId": "seal_support",
            "ruleIds": ["zzq.rule.officer.seal-formation"],
            "sourceIds": ["zzq.prop.officer.seal-formation"],
        },
    })
    cycles[0]["years"][2]["months"][1]["theme_activations"]["事业"] = [
        cross_path,
        wrong_transition,
    ]
    claims = [{
        "id": "bazi.claim.signature.officer.formation",
        "classicalRole": "formation_path",
        "title": "官格成格路径",
        "summary": "两条路径分别有来源依据。",
        "patternId": "direct_officer",
        "pathIds": ["seal_support", "wealth_support"],
        "ruleIds": [
            "zzq.rule.officer.seal-formation",
            "zzq.rule.officer.wealth-formation",
        ],
        "sourceIds": [
            "zzq.prop.officer.seal-formation",
            "zzq.prop.officer.wealth-formation",
        ],
        "lifecycleProvenance": [
            {
                "pathId": "seal_support",
                "ruleId": "zzq.rule.officer.seal-formation",
                "sourceIds": ["zzq.prop.officer.seal-formation"],
            },
            {
                "pathId": "wealth_support",
                "ruleId": "zzq.rule.officer.wealth-formation",
                "sourceIds": ["zzq.prop.officer.wealth-formation"],
            },
        ],
    }]

    result = build_life_kline(cycles, claims=claims)
    month = result["series"][0]["points"][2]["months"][1]

    assert month["value"] == 100.0
    assert all(float(driver.get("delta", 0)) == 0 for driver in month["drivers"])


def test_source_backed_damage_and_rescue_use_role_specific_transitions() -> None:
    cases = (
        ("damage", "damage", "formed", "broken", -1),
        ("rescue", "rescue", "broken", "rescued", 1),
    )
    for role, classical_role, before, after, direction in cases:
        cycles = _cycles(signed=False)
        event = _event(label=f"流月格局·{role}", feature="正官")
        event.update({
            "role": role,
            "lifecycle": {
                "before": before,
                "after": after,
                "patternId": "direct_officer",
                "pathId": "seal_support",
                "ruleIds": [f"zzq.rule.officer.{role}"],
                "sourceIds": [f"zzq.prop.officer.{role}"],
            },
        })
        cycles[0]["years"][2]["months"][1]["theme_activations"]["事业"] = [event]
        claims = [{
            "id": f"bazi.claim.signature.officer.{role}",
            "classicalRole": classical_role,
            "title": f"正官格{role}",
            "summary": "经来源规则确认的生命周期变化。",
            "patternId": "direct_officer",
            "pathIds": ["seal_support"],
            "ruleIds": [f"zzq.rule.officer.{role}"],
            "sourceIds": [f"zzq.prop.officer.{role}"],
            "lifecycleProvenance": [
                {
                    "pathId": "seal_support",
                    "ruleId": f"zzq.rule.officer.{role}",
                    "sourceIds": [f"zzq.prop.officer.{role}"],
                }
            ],
        }]

        result = build_life_kline(cycles, claims=claims)
        month = result["series"][0]["points"][2]["months"][1]

        assert (month["value"] - 100) * direction > 0
        assert any(driver.get("role") == role for driver in month["drivers"])


def test_compact_and_full_views_share_one_full_horizon_baseline() -> None:
    cycles = _cycles()
    visible_years = set(range(2024, 2034))

    full = build_life_kline(cycles)
    compact = build_life_kline(cycles, visible_years=visible_years)

    assert compact["baseline"] == full["baseline"]
    assert compact["baseline"]["scope"] == "full_horizon"
    assert all(len(series["points"]) == 10 for series in compact["series"])
    for compact_series, full_series in zip(compact["series"], full["series"], strict=True):
        expected = [point for point in full_series["points"] if point["year"] in visible_years]
        assert compact_series["points"] == expected
