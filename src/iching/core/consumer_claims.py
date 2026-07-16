from __future__ import annotations

from typing import Any, Iterable, Mapping


CONSUMER_CLAIMS_VERSION = "consumer-claims-2026.07-v1"

CLAIM_THEME_ORDER = ("career", "wealth", "relationship", "rhythm")
CLAIM_THEME_LABELS = {
    "career": "事业",
    "wealth": "财富",
    "relationship": "感情",
    "rhythm": "身心节奏",
}
_PROFILE_THEME_KEYS = {
    "事业": "career",
    "财富": "wealth",
    "感情": "relationship",
    "五行与承压结构": "rhythm",
    "健康": "rhythm",
}
_PATTERN_STATUS_LABELS = {
    "formed": "成格",
    "effective": "得用",
    "broken": "受制",
    "rescued": "救成",
    "mixed": "混杂",
    "transformed": "转化",
    "candidate": "主导",
}
_CAREER_PATHS = {
    "direct_resource": (
        "expertise_builder",
        "专业积累型",
        "更适合通过学习、研究、资质与长期能力建设形成位置。",
    ),
    "indirect_resource": (
        "expertise_builder",
        "专业积累型",
        "更适合通过学习、研究、资质与长期能力建设形成位置。",
    ),
    "direct_officer": (
        "responsibility_builder",
        "责任推动型",
        "更容易在明确目标、责任与组织协作中建立影响力。",
    ),
    "seven_killings": (
        "responsibility_builder",
        "责任推动型",
        "更容易在明确目标、责任与复杂任务中建立影响力。",
    ),
    "follow_officer": (
        "responsibility_builder",
        "责任推动型",
        "更容易在明确目标、责任与复杂任务中建立影响力。",
    ),
    "eating_god": (
        "creative_expression",
        "创造表达型",
        "更适合用作品、表达、解决问题与新方法打开局面。",
    ),
    "hurting_officer": (
        "creative_expression",
        "创造表达型",
        "更适合用作品、表达、解决问题与新方法打开局面。",
    ),
    "follow_output": (
        "creative_expression",
        "创造表达型",
        "更适合用作品、表达、解决问题与新方法打开局面。",
    ),
    "direct_wealth": (
        "result_operator",
        "成果经营型",
        "更适合把资源、协作与现实目标组织成可持续成果。",
    ),
    "indirect_wealth": (
        "result_operator",
        "成果经营型",
        "更适合把资源、协作与现实目标组织成可持续成果。",
    ),
    "follow_wealth": (
        "result_operator",
        "成果经营型",
        "更适合把资源、协作与现实目标组织成可持续成果。",
    ),
    "month_prosperity": (
        "independent_builder",
        "自主建造型",
        "事业路径更依赖个人判断、持续行动与可积累的专长。",
    ),
    "month_robbery": (
        "independent_builder",
        "自主建造型",
        "事业路径更依赖个人判断、持续行动与可积累的专长。",
    ),
    "yang_blade": (
        "independent_builder",
        "自主建造型",
        "事业路径更依赖个人判断、持续行动与可积累的专长。",
    ),
    "follow_prosperous": (
        "independent_builder",
        "自主建造型",
        "事业路径更依赖个人判断、持续行动与可积累的专长。",
    ),
    "follow_strong": (
        "independent_builder",
        "自主建造型",
        "事业路径更依赖个人判断、持续行动与可积累的专长。",
    ),
}
_SIGNATURE_FAMILY_PRIORITY = {
    "月令": 0,
    "通根": 1,
    "夫妻宫": 1,
    "夫妻宫关系": 1,
    "财星明透": 1,
    "财星藏根": 1,
    "官杀": 2,
    "印星": 2,
    "食伤": 2,
    "食伤财星": 2,
    "五行分布": 3,
    "冲刑害破": 3,
    "干支关系": 4,
    "迁动": 4,
    "比劫": 4,
}
_FAMILY_METRICS = {
    "通根": "root_pillar_count",
    "夫妻宫关系": "spouse_palace_relation_count",
    "财星明透": "visible_wealth_count",
    "财星藏根": "hidden_wealth_count",
    "干支关系": "relation_count",
    "迁动": "mobility_count",
    "冲刑害破": "pressure_relation_count",
    "五行分布": "concentrated_element_count",
}


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _unique_strings(values: Iterable[Any]) -> list[str]:
    return list(dict.fromkeys(str(value) for value in values if str(value)))


def _primary_pattern(patterns: Mapping[str, Any]) -> Mapping[str, Any]:
    return _mapping(patterns.get("primary"))


def _pattern_key(primary: Mapping[str, Any]) -> str:
    identifier = str(primary.get("id", ""))
    return identifier.rsplit(".", 1)[-1] if identifier else ""


def _source_backed_pattern(
    patterns: Mapping[str, Any],
    pattern_key: str,
) -> Mapping[str, Any]:
    """Return the matching non-authoritative trace, never a replacement verdict."""

    shadow = _mapping(patterns.get("source_backed_shadow"))
    if shadow.get("authoritative") is not False:
        return {}
    pattern_set = _mapping(shadow.get("pattern_set"))
    for item in pattern_set.get("patterns", ()):
        candidate = _mapping(item)
        if (
            str(candidate.get("pattern_id", "")) == pattern_key
            and str(candidate.get("candidate", "")) == "true"
            and str(candidate.get("status", "")) != "rejected"
        ):
            return candidate
    return {}


def _true_stage_traces(
    pattern: Mapping[str, Any],
    stages: Iterable[str],
    *,
    path_id: str | None = None,
) -> list[Mapping[str, Any]]:
    requested = set(stages)
    traces: list[Mapping[str, Any]] = []
    for stage_value in pattern.get("stages", ()):
        stage = _mapping(stage_value)
        if str(stage.get("stage", "")) not in requested:
            continue
        for rule_value in stage.get("rules", ()):
            rule = _mapping(rule_value)
            if str(rule.get("truth", "")) != "true":
                continue
            if path_id is not None and str(rule.get("path_id", "")) != path_id:
                continue
            traces.append(rule)
    return traces


def _trace_ids(traces: Iterable[Mapping[str, Any]]) -> tuple[list[str], list[str]]:
    trace_list = list(traces)
    return (
        _unique_strings(trace.get("rule_id", "") for trace in trace_list),
        _unique_strings(
            source_id
            for trace in trace_list
            for source_id in (
                *trace.get("source_ids", ()),
                *trace.get("supporting_source_ids", ()),
            )
        ),
    )


def _canonical_verdict_traces(pattern: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    active_paths = [
        path
        for path in pattern.get("paths", ())
        if isinstance(path, Mapping)
        and str(path.get("status", ""))
        not in {"inactive", "superseded", "undetermined"}
    ]
    active_path_ids = {str(path.get("path_id", "")) for path in active_paths}
    damage_ids = {
        str(rule_id)
        for path in active_paths
        for rule_id in path.get("actual_damage_ids", ())
    }
    rescue_ids = {
        str(rule_id)
        for path in active_paths
        for rule_id in path.get("active_rescue_ids", ())
    }
    result = _true_stage_traces(pattern, ("candidate",))
    result.extend(
        trace
        for trace in _true_stage_traces(pattern, ("formation", "resolution"))
        if not trace.get("path_id") or str(trace.get("path_id", "")) in active_path_ids
    )
    result.extend(
        trace
        for trace in _true_stage_traces(pattern, ("damage",))
        if str(trace.get("rule_id", "")) in damage_ids
    )
    result.extend(
        trace
        for trace in _true_stage_traces(pattern, ("rescue",))
        if str(trace.get("rule_id", "")) in rescue_ids
    )
    return result


def _verdict_provenance_matches(
    primary: Mapping[str, Any],
    source_backed: Mapping[str, Any],
) -> bool:
    if not source_backed or str(source_backed.get("status", "")) != str(
        primary.get("status", "")
    ):
        return False
    legacy_path = _mapping(primary.get("formation_path"))
    legacy_path_id = str(legacy_path.get("id", ""))
    active_path_ids = {
        str(path.get("path_id", ""))
        for path in source_backed.get("paths", ())
        if isinstance(path, Mapping)
        and str(path.get("status", ""))
        not in {"inactive", "superseded", "undetermined"}
    }
    if legacy_path_id:
        return legacy_path_id in active_path_ids
    return not active_path_ids


def _hero_summary(primary: Mapping[str, Any]) -> str:
    selection = {
        "month_main_qi": "月令本气形成主导结构",
        "month_hidden_exposed": "月令藏气透出，形成主导结构",
        "month_meeting": "月令藏气因合会进入主线",
        "month_hidden_only": "月令藏气构成命盘底色",
        "strict_special_gates": "原局条件集中，特殊结构成立",
    }.get(str(primary.get("selection", "")), "原局形成清晰的主导结构")
    parts = [selection]
    formation_path = _mapping(primary.get("formation_path"))
    if formation_path.get("title"):
        parts.append(f"主要通过{formation_path['title']}展开")
    return "；".join(parts) + "。"


def _hero_claim(patterns: Mapping[str, Any]) -> dict[str, Any]:
    primary = _primary_pattern(patterns)
    pattern_key = _pattern_key(primary)
    source_backed = _source_backed_pattern(patterns, pattern_key)
    verdict_matches = _verdict_provenance_matches(primary, source_backed)
    traces = _canonical_verdict_traces(source_backed) if verdict_matches else []
    rule_ids, source_ids = _trace_ids(traces)
    status = str(primary.get("status", "candidate"))
    title = str(primary.get("title", primary.get("name", "主导结构")))
    status_label = _PATTERN_STATUS_LABELS.get(status, status or "主导")
    return {
        "id": f"bazi.claim.hero.{pattern_key or 'undetermined'}",
        "slot": "hero",
        "title": f"{title} · {status_label}",
        "summary": _hero_summary(primary),
        "importance": "foundation",
        "classicalRole": "pattern",
        **({"patternId": pattern_key} if source_backed else {}),
        "evidenceIds": _unique_strings(primary.get("evidence_ids", ())),
        "ruleIds": rule_ids,
        "sourceIds": source_ids,
    }


def _profiles_by_theme(
    profiles: Iterable[Mapping[str, Any]],
) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    for profile in profiles:
        theme = _PROFILE_THEME_KEYS.get(str(profile.get("theme", "")))
        if theme:
            result[theme] = profile
    return result


def _metric_values(profile: Mapping[str, Any]) -> dict[str, int]:
    return {
        str(metric.get("metric_id", "")): int(metric.get("value", 0) or 0)
        for metric in profile.get("structure_metrics", ())
        if isinstance(metric, Mapping)
    }


def _theme_path(
    theme: str,
    profile: Mapping[str, Any],
    primary: Mapping[str, Any],
) -> tuple[str, str, str]:
    values = _metric_values(profile)
    if theme == "career":
        return _CAREER_PATHS.get(
            _pattern_key(primary),
            (
                "self_directed",
                "自主开拓型",
                "事业路径更依赖个人判断、持续行动与阶段机会。",
            ),
        )
    if theme == "wealth":
        if values.get("visible_wealth_count", 0) > 0:
            return (
                "visible_operation",
                "外显经营型",
                "资源与现实结果更容易直接进入选择、协作与行动。",
            )
        if values.get("hidden_wealth_count", 0) > 0:
            return (
                "hidden_accumulation",
                "潜藏兑现型",
                "财星主要藏于地支，资源更偏长期积累与阶段兑现；这不等于贫穷或没有财富。",
            )
        return (
            "capability_conversion",
            "能力转化型",
            "财富更依赖专业能力、关系网络与运限机会转化，并非由单一财星数量决定。",
        )
    if theme == "relationship":
        if values.get("spouse_palace_relation_count", 0) >= 4:
            return (
                "high_interaction",
                "高互动型",
                "关系与生活选择联动较多，重要关系更容易推动阶段变化。",
            )
        if values.get("day_stem_combine_count", 0) > 0:
            return (
                "relational_pull",
                "关系牵引型",
                "亲密关系在选择、合作与人生节奏中具有较强牵引力。",
            )
        return (
            "progressive_bond",
            "渐进建立型",
            "关系更适合通过理解、信任与共同经历逐步深化。",
        )
    if values.get("pressure_relation_count", 0) >= 5:
        return (
            "adaptive_regulation",
            "敏感调节型",
            "结构变化较密集，需要在输出、休整与环境切换之间找到自己的节奏。",
        )
    if values.get("concentrated_element_count", 0) >= 2:
        return (
            "concentrated_rhythm",
            "内稳外紧型",
            "内在力量较集中，外部变化来临时更需要主动安排恢复与缓冲。",
        )
    return (
        "steady_recovery",
        "均衡恢复型",
        "整体节奏更适合稳定推进，并为阶段变化保留恢复空间。",
    )


def _theme_claims(
    profiles: Iterable[Mapping[str, Any]],
    patterns: Mapping[str, Any],
) -> list[dict[str, Any]]:
    by_theme = _profiles_by_theme(profiles)
    primary = _primary_pattern(patterns)
    canonical_pattern = _source_backed_pattern(patterns, _pattern_key(primary))
    claims: list[dict[str, Any]] = []
    for theme in CLAIM_THEME_ORDER:
        profile = by_theme.get(theme, {})
        path_key, title, summary = _theme_path(theme, profile, primary)
        evidence = [
            item
            for item in profile.get("evidence", ())
            if isinstance(item, Mapping) and str(item.get("family", "")) != "神煞"
        ]
        evidence.sort(
            key=lambda item: (
                {"支持": 0, "活动": 1, "背景": 2, "制约": 3}.get(
                    str(item.get("evidence_type", "")),
                    4,
                ),
                str(item.get("id", "")),
            )
        )
        highlights = _unique_strings(item.get("title", "") for item in evidence)[:2]
        claims.append(
            {
                "id": f"bazi.claim.theme.{theme}.{path_key}",
                "slot": "theme",
                "theme": theme,
                "title": title,
                "summary": summary,
                "importance": "primary",
                "classicalRole": "expression",
                "expressionPathId": f"bazi.path.{theme}.{path_key}",
                "evidenceHighlights": highlights,
                **(
                    {"patternId": _pattern_key(primary)}
                    if theme == "career" and canonical_pattern
                    else {}
                ),
                "evidenceIds": _unique_strings(
                    evidence.get("id", "")
                    for evidence in profile.get("evidence", ())
                    if isinstance(evidence, Mapping)
                ),
                "ruleIds": [],
                "sourceIds": [],
            }
        )
    return claims


def _pattern_evidence_ids(
    patterns: Mapping[str, Any],
    primary: Mapping[str, Any],
    kind: str,
) -> list[str]:
    primary_ids = set(_unique_strings(primary.get("evidence_ids", ())))
    return _unique_strings(
        evidence.get("id", "")
        for evidence in patterns.get("evidence", ())
        if isinstance(evidence, Mapping)
        and str(evidence.get("id", "")) in primary_ids
        and str(evidence.get("kind", "")) == kind
    )


def _comparison_same_mass(profile: Mapping[str, Any], family: str) -> float:
    metric_id = _FAMILY_METRICS.get(family)
    if not metric_id:
        return 101.0
    for comparison in profile.get("comparisons", ()):
        if not isinstance(comparison, Mapping):
            continue
        if str(comparison.get("metric_id", "")) != metric_id:
            continue
        if str(comparison.get("status", "")) not in {"observed", "zero"}:
            return 101.0
        return float(comparison.get("same_mass", 101) or 101)
    return 101.0


def _signature_claims(
    profiles: Iterable[Mapping[str, Any]],
    patterns: Mapping[str, Any],
) -> list[dict[str, Any]]:
    primary = _primary_pattern(patterns)
    pattern_key = _pattern_key(primary)
    source_backed = _source_backed_pattern(patterns, pattern_key)
    verdict_matches = _verdict_provenance_matches(primary, source_backed)
    candidates: list[tuple[tuple[int, float, str], dict[str, Any]]] = []
    formation_path = _mapping(primary.get("formation_path"))
    if formation_path.get("id"):
        path_id = str(formation_path["id"])
        # Legacy and source-backed path namespaces are intentionally not guessed
        # across. Canonical provenance is attached only if the exact path ID is
        # active in the source-backed result.
        active_canonical_paths = {
            str(path.get("path_id", ""))
            for path in source_backed.get("paths", ())
            if isinstance(path, Mapping)
            and str(path.get("status", ""))
            not in {"inactive", "superseded", "undetermined"}
        }
        canonical_path_matches = verdict_matches and path_id in active_canonical_paths
        traces = (
            _true_stage_traces(source_backed, ("formation",), path_id=path_id)
            if canonical_path_matches
            else []
        )
        rule_ids, source_ids = _trace_ids(traces)
        details = _unique_strings(formation_path.get("details", ()))
        claim = {
            "id": f"bazi.claim.signature.{pattern_key}.formation.{path_id}",
            "slot": "signature",
            "title": str(formation_path.get("title", "成格路径")),
            "summary": "；".join(details) or "这条路径说明主导格局怎样在原局中形成。",
            "importance": "primary",
            "classicalRole": "formation_path",
            **({"patternId": pattern_key} if source_backed else {}),
            **({"pathId": path_id} if canonical_path_matches else {}),
            "evidenceIds": _pattern_evidence_ids(patterns, primary, "formation_path"),
            "ruleIds": rule_ids,
            "sourceIds": source_ids,
        }
        candidates.append(((0, 0.0, claim["id"]), claim))

    constraints = _unique_strings(primary.get("constraints", ()))
    if constraints:
        active_damage_ids = {
            str(rule_id)
            for path in source_backed.get("paths", ())
            if isinstance(path, Mapping)
            and str(path.get("status", ""))
            not in {"inactive", "superseded", "undetermined"}
            for rule_id in path.get("actual_damage_ids", ())
        }
        traces = (
            [
                trace
                for trace in _true_stage_traces(source_backed, ("damage",))
                if str(trace.get("rule_id", "")) in active_damage_ids
            ]
            if verdict_matches
            else []
        )
        rule_ids, source_ids = _trace_ids(traces)
        evidence_ids = _pattern_evidence_ids(patterns, primary, "constraint")
        if evidence_ids or rule_ids or source_ids:
            claim = {
                "id": f"bazi.claim.signature.{pattern_key}.damage",
                "slot": "signature",
                "title": "格局中的制约",
                "summary": f"{'、'.join(constraints)}会牵制主导结构的直接发挥。",
                "importance": "major",
                "classicalRole": "damage",
                **({"patternId": pattern_key} if source_backed else {}),
                "evidenceIds": evidence_ids,
                "ruleIds": rule_ids,
                "sourceIds": source_ids,
            }
            candidates.append(((1, 0.0, claim["id"]), claim))

    rescues = _unique_strings(primary.get("rescues", ()))
    if rescues:
        active_rescue_ids = {
            str(rule_id)
            for path in source_backed.get("paths", ())
            if isinstance(path, Mapping)
            and str(path.get("status", ""))
            not in {"inactive", "superseded", "undetermined"}
            for rule_id in path.get("active_rescue_ids", ())
        }
        traces = (
            [
                trace
                for trace in _true_stage_traces(source_backed, ("rescue",))
                if str(trace.get("rule_id", "")) in active_rescue_ids
            ]
            if verdict_matches
            else []
        )
        rule_ids, source_ids = _trace_ids(traces)
        evidence_ids = _pattern_evidence_ids(patterns, primary, "rescue")
        if evidence_ids or rule_ids or source_ids:
            claim = {
                "id": f"bazi.claim.signature.{pattern_key}.rescue",
                "slot": "signature",
                "title": "制约得到回应",
                "summary": f"{'、'.join(rescues)}让原局中的制约得到具体回应。",
                "importance": "major",
                "classicalRole": "rescue",
                **({"patternId": pattern_key} if source_backed else {}),
                "evidenceIds": evidence_ids,
                "ruleIds": rule_ids,
                "sourceIds": source_ids,
            }
            candidates.append(((2, 0.0, claim["id"]), claim))

    for profile in profiles:
        theme = _PROFILE_THEME_KEYS.get(str(profile.get("theme", "")))
        if not theme:
            continue
        for evidence_value in profile.get("evidence", ()):
            evidence = _mapping(evidence_value)
            family = str(evidence.get("family", ""))
            if family == "神煞" or not evidence.get("id") or not evidence.get("title"):
                continue
            importance_rank = _SIGNATURE_FAMILY_PRIORITY.get(family, 5)
            importance = "major" if importance_rank <= 2 else "supporting"
            claim = {
                "id": f"bazi.claim.signature.{evidence['id']}",
                "slot": "signature",
                "theme": theme,
                "title": str(evidence["title"]),
                "summary": str(evidence.get("detail", "这是命盘中可核对的结构事实。")),
                "importance": importance,
                "classicalRole": "expression"
                if importance_rank <= 2
                else "supporting_marker",
                "evidenceIds": [str(evidence["id"])],
                "ruleIds": [],
                "sourceIds": [],
                "_family": family,
            }
            candidates.append(
                (
                    (
                        3 + importance_rank,
                        _comparison_same_mass(profile, family),
                        claim["id"],
                    ),
                    claim,
                )
            )

    results: list[dict[str, Any]] = []
    seen_content: set[tuple[str, str]] = set()
    seen_families: set[str] = set()
    for _, claim in sorted(candidates, key=lambda item: item[0]):
        content_key = (claim["title"], claim["summary"])
        family = str(claim.get("_family", ""))
        if content_key in seen_content or (family and family in seen_families):
            continue
        seen_content.add(content_key)
        if family:
            seen_families.add(family)
        claim.pop("_family", None)
        results.append(claim)
        if len(results) == 5:
            break
    return results


def _feature_metrics_by_id(
    metrics: Iterable[Mapping[str, Any]],
) -> dict[str, Mapping[str, Any]]:
    return {
        str(metric.get("feature_id", "")): metric
        for metric in metrics
        if metric.get("feature_id")
    }


def _incidence_comparison(metric: Mapping[str, Any]) -> dict[str, Any] | None:
    if str(metric.get("status", "")) not in {"observed", "zero"}:
        return None
    percentage = float(metric.get("percentage", 0) or 0)
    status = str(metric.get("status", "observed"))
    display = (
        "0% · 本参考周期未出现"
        if status == "zero"
        else "<0.01%"
        if 0 < percentage < 0.01
        else f"{percentage:.2f}%"
    )
    return {
        "kind": "incidence",
        "featureId": str(metric.get("feature_id", "")),
        "status": status,
        "percentage": round(percentage, 6),
        "display": f"历法样本出现率 {display}",
        "baselineId": metric.get("baseline_id"),
    }


def _combination_claims(
    shensha_effects: Mapping[str, Any],
    feature_metrics: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    metrics_by_id = _feature_metrics_by_id(feature_metrics)
    candidates: list[tuple[int, float, str, dict[str, Any]]] = []
    for value in shensha_effects.get("combinations", ()):
        combination = _mapping(value)
        member_ids = _unique_strings(combination.get("member_rule_ids", ()))
        if len(member_ids) < 2:
            continue
        identifier = str(combination.get("id", ""))
        if not identifier:
            continue
        tier = str(combination.get("tier", "product_cluster"))
        comparison = _incidence_comparison(metrics_by_id.get(identifier, {}))
        incidence = float(comparison.get("percentage", 101)) if comparison else 101.0
        claim = {
            "id": f"bazi.claim.combination.{identifier}",
            "slot": "combination",
            "title": str(combination.get("title", "结构组合")),
            "summary": str(
                combination.get("summary", "多个结构在同一命盘中形成共振。")
            ),
            "importance": "major" if tier == "classical_named" else "supporting",
            "classicalRole": "supporting_marker",
            **({"comparison": comparison} if comparison else {}),
            "evidenceIds": _unique_strings(combination.get("evidence_ids", ())),
            "ruleIds": member_ids,
            # Combination registries currently carry rule IDs but no classical
            # proposition IDs. An empty list is more honest than a fabricated link.
            "sourceIds": _unique_strings(combination.get("source_ids", ())),
        }
        tier_rank = {
            "classical_named": 0,
            "classical_interaction": 1,
            "product_cluster": 2,
        }.get(tier, 3)
        candidates.append((tier_rank, incidence, identifier, claim))
    return [item[3] for item in sorted(candidates, key=lambda item: item[:3])[:4]]


def _timeline_claims(cycles: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    event_kind_order = {"新增": 0, "联动": 1, "变化": 2, "冲突": 3}
    usable = sorted(
        [
            cycle
            for cycle in cycles
            if int(cycle.get("start_year", 0) or 0)
            and int(cycle.get("end_year", 0) or 0)
        ],
        key=lambda cycle: (
            str(cycle.get("start_timestamp", "")),
            int(cycle.get("start_year", 0) or 0),
            int(cycle.get("index", 0) or 0),
        ),
    )
    if not usable:
        return []
    current_index = next(
        (index for index, cycle in enumerate(usable) if cycle.get("is_current")),
        None,
    )
    if current_index is None:
        return []
    selected = usable[current_index : current_index + 3]
    claims: list[dict[str, Any]] = []
    theme_lookup = {
        "事业": "career",
        "财富": "wealth",
        "感情": "relationship",
        "五行与承压结构": "rhythm",
        "健康": "rhythm",
    }
    for cycle in selected:
        start_year = int(cycle.get("start_year", 0) or 0)
        end_year = int(cycle.get("end_year", 0) or 0)
        activations = _mapping(cycle.get("theme_activations"))
        ranked: list[tuple[int, int, str, list[Mapping[str, Any]]]] = []
        for order, theme_name in enumerate(("事业", "财富", "感情", "五行与承压结构")):
            events = sorted(
                [
                    _mapping(event)
                    for event in activations.get(theme_name, ())
                    if isinstance(event, Mapping)
                ],
                key=lambda event: (
                    event_kind_order.get(str(event.get("kind", "")), 9),
                    str(event.get("label", "")),
                    str(event.get("detail", "")),
                    str(event.get("source", "")),
                ),
            )
            unique = {
                (str(event.get("kind", "")), str(event.get("label", "")))
                for event in events
                if event.get("label")
            }
            ranked.append((-len(unique), order, theme_name, events))
        negative_count, _, theme_name, events = min(ranked)
        theme = theme_lookup[theme_name] if negative_count < 0 else None
        cycle_label = str(cycle.get("label", cycle.get("ganzhi", "大运")))
        grouped: dict[str, list[str]] = {}
        for event in events:
            label = str(event.get("label", ""))
            if not label:
                continue
            kind = str(event.get("kind", "变化"))
            grouped.setdefault(kind, [])
            if label not in grouped[kind]:
                grouped[kind].append(label)
        group_labels = {
            "联动": "联动",
            "冲突": "调整",
            "变化": "变化",
            "新增": "新增",
        }
        summary_parts = [
            f"{group_labels.get(kind, kind)}：{'、'.join(labels[:2])}"
            for kind, labels in grouped.items()
            if labels
        ]
        if summary_parts and theme:
            title = f"{start_year}–{end_year} · {CLAIM_THEME_LABELS[theme]}信号最集中"
            summary = "；".join(summary_parts[:3]) + "。"
        else:
            title = f"{start_year}–{end_year} · {cycle_label}"
            summary = "这一阶段的具体激活点由大运、流年与流月共同展开。"
        claims.append(
            {
                "id": f"bazi.claim.timeline.{cycle.get('index', start_year)}",
                "slot": "timeline",
                **({"theme": theme} if theme else {}),
                "title": title,
                "summary": summary,
                "importance": "major",
                "classicalRole": "expression",
                "activation": {
                    "layer": "dayun",
                    "ganzhi": str(cycle.get("ganzhi", cycle_label)),
                    "startTimestamp": str(cycle.get("start_timestamp", "")),
                    "endTimestamp": str(cycle.get("end_timestamp", "")),
                    "startYear": start_year,
                    "endYear": end_year,
                    "isCurrent": bool(cycle.get("is_current")),
                    "drivers": [
                        {
                            "kind": str(event.get("kind", "")),
                            "label": str(event.get("label", "")),
                            "detail": str(event.get("detail", "")),
                            "source": str(event.get("source", "")),
                        }
                        for event in events
                        if event.get("label")
                    ],
                },
                "evidenceIds": [],
                "ruleIds": [],
                "sourceIds": [],
            }
        )
    return claims


def compile_consumer_claims(
    *,
    patterns: Mapping[str, Any] | None,
    theme_profiles: Iterable[Mapping[str, Any]],
    shensha_effects: Mapping[str, Any] | None,
    cycles: Iterable[Mapping[str, Any]],
    feature_metrics: Iterable[Mapping[str, Any]] = (),
) -> list[dict[str, Any]]:
    """Compile chart facts into concise, source-traceable consumer claims.

    Claims describe structure, expression and activation. They never expose a
    life-quality score, fortune percentile or an unsupported classical source.
    """

    pattern_data = patterns or {}
    profile_list = list(theme_profiles)
    effects = shensha_effects or {}
    claims = [
        _hero_claim(pattern_data),
        *_theme_claims(profile_list, pattern_data),
        *_signature_claims(profile_list, pattern_data),
        *_combination_claims(effects, feature_metrics),
        *_timeline_claims(cycles),
    ]
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for claim in claims:
        identifier = str(claim.get("id", ""))
        if not identifier or identifier in seen:
            continue
        seen.add(identifier)
        unique.append(claim)
    return unique


def project_consumer_claims(claims: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Project canonical claims into the temporary V3 consumer UI contract."""

    claim_list = list(claims)
    hero = next((claim for claim in claim_list if claim.get("slot") == "hero"), {})
    themes = [claim for claim in claim_list if claim.get("slot") == "theme"]
    signatures = [claim for claim in claim_list if claim.get("slot") == "signature"]
    combinations = [claim for claim in claim_list if claim.get("slot") == "combination"]
    theme_by_key = {str(claim.get("theme", "")): claim for claim in themes}
    identity = {
        "system_title": "八字命格",
        "archetype_id": str(hero.get("patternId", hero.get("id", "bazi.claim.hero"))),
        "archetype_title": str(hero.get("title", "主导结构")),
        "archetype_subtitle": str(hero.get("summary", "命盘的主导结构已形成。")),
        "fusion_title": None,
        "primary_arena": str(theme_by_key.get("career", {}).get("title", "个人成长")),
        "signature": str(
            theme_by_key.get("relationship", {}).get("title", "关系节奏鲜明")
        ),
        "life_rhythm": str(theme_by_key.get("rhythm", {}).get("title", "稳定推进型")),
    }
    subjects = []
    for theme in CLAIM_THEME_ORDER:
        claim = theme_by_key.get(theme)
        if not claim:
            continue
        subjects.append(
            {
                "key": "health" if theme == "rhythm" else theme,
                "label": CLAIM_THEME_LABELS[theme],
                "headline": " · ".join(
                    _unique_strings(claim.get("evidenceHighlights", ()))
                )
                or "查看关键结构依据",
                "drivers": [],
                "path_label": str(claim.get("title", "结构路径")),
                "path_summary": str(claim.get("summary", "")),
            }
        )
    importance_labels = {
        "foundation": "命盘根基",
        "primary": "主线结构",
        "major": "重要结构",
        "supporting": "结构亮点",
        "auxiliary": "辅助结构",
    }
    fingerprints = []
    for claim in signatures:
        comparison = _mapping(claim.get("comparison"))
        fingerprints.append(
            {
                "id": str(claim.get("id", "signature")),
                "title": str(claim.get("title", "结构特征")),
                "detail": str(claim.get("summary", "")),
                "rarity_label": importance_labels.get(
                    str(claim.get("importance", "supporting")), "结构亮点"
                ),
                "incidence_percentage": comparison.get("percentage"),
            }
        )
    achievements = []
    for claim in combinations:
        comparison = _mapping(claim.get("comparison"))
        achievements.append(
            {
                "id": str(claim.get("id", "combination")),
                "title": str(claim.get("title", "结构组合")),
                "tier": "组合",
                "state": "可见",
                "rarity_percentage": comparison.get("percentage"),
                "position": f"{len(claim.get('ruleIds', ()))} 项结构共振",
                "summary": str(claim.get("summary", "")),
                "member_ids": list(claim.get("ruleIds", ())),
            }
        )
    return {
        "identity": identity,
        "subjects": subjects,
        "fingerprints": fingerprints,
        "achievements": achievements,
    }


__all__ = [
    "CLAIM_THEME_LABELS",
    "CLAIM_THEME_ORDER",
    "CONSUMER_CLAIMS_VERSION",
    "compile_consumer_claims",
    "project_consumer_claims",
]
