from __future__ import annotations

from hashlib import sha256
from math import sqrt
from typing import Any, Iterable, Mapping


CONSUMER_RULES_VERSION = "metaphysics-consumer-2026.07-v3"

THEME_ORDER = ("career", "wealth", "relationship", "health")
THEME_LABELS = {
    "career": "事业",
    "wealth": "财富",
    "relationship": "感情",
    "health": "身心节奏",
}
PROFILE_THEME_KEYS = {
    "事业": "career",
    "财富": "wealth",
    "感情": "relationship",
    "五行与承压结构": "health",
    "健康": "health",
}
THEME_COLORS = {
    "overall": "#7c3aed",
    "career": "#dc2626",
    "wealth": "#d97706",
    "relationship": "#db2777",
    "health": "#059669",
}


_ARCHETYPES = (
    ("breaker", "破局型表达者", "把复杂局面说清楚，再把新路走出来", {"食神", "伤官"}),
    ("strategist", "谋略型操盘手", "擅长在资源、节奏与关系之间找到最优解", {"偏印", "七杀"}),
    ("builder", "长期主义建造者", "靠稳定积累把能力变成可持续成果", {"正印", "正财"}),
    ("commander", "高压型领导者", "越是复杂和有约束的局面，越能显出掌控力", {"正官", "七杀"}),
    ("creator", "天赋型创造者", "表达、审美与原创能力是最醒目的个人资产", {"食神", "伤官", "偏印"}),
    ("connector", "资源型连接者", "能看见人与资源之间尚未被利用的连接", {"偏财", "正财"}),
    ("scholar", "体系型研究者", "把知识变成判断框架，是你最稳定的优势", {"正印", "偏印"}),
    ("challenger", "逆风型挑战者", "压力不会让你停下，反而会逼出行动速度", {"七杀", "劫财"}),
    ("operator", "结果型经营者", "目标感强，善于把抽象机会落成现实结果", {"正财", "偏财", "正官"}),
    ("independent", "独立型开拓者", "更适合凭判断与个人能力开出自己的路径", {"比肩", "劫财"}),
    ("mentor", "影响型引导者", "善于把经验、知识与秩序传递给别人", {"正印", "食神"}),
    ("diplomat", "关系型协调者", "能够同时理解不同立场并推动局面前进", {"正官", "正财", "正印"}),
    ("visionary", "前瞻型策划者", "比多数人更早看见趋势、风险与第二条路", {"偏印", "伤官"}),
    ("finisher", "执行型终结者", "不只提出想法，更擅长把事情推到完成", {"七杀", "正财"}),
    ("guardian", "稳定型守成者", "在变化中维持秩序与长期价值", {"正官", "正印", "正财"}),
    ("catalyst", "变化型催化者", "你的出现往往会加速环境、人和选择的变化", {"驿马", "伤官"}),
    ("magnet", "魅力型影响者", "个人表达与关系感知很容易形成记忆点", {"桃花", "红鸾", "天喜"}),
    ("integrator", "全局型整合者", "擅长把分散的信息、人和资源重新组织", set()),
)

_PERIOD_EVENT_WEIGHTS = {"新增": 3.2, "联动": 4.4, "变化": 1.2, "冲突": -4.8}
_PATTERN_STATUS_LABELS = {
    "formed": "成格",
    "effective": "得用",
    "broken": "受制",
    "rescued": "救成",
    "mixed": "混杂",
    "transformed": "转化",
    "candidate": "主导",
}
_SHENSHA_STATE_IDS = {"发力": "activated", "有力": "supported", "可见": "visible", "受制": "constrained"}

_PATTERN_ARCHETYPES = {
    "正官": "guardian",
    "七杀": "commander",
    "正财": "builder",
    "偏财": "connector",
    "食神": "creator",
    "伤官": "breaker",
    "正印": "scholar",
    "偏印": "scholar",
    "建禄": "independent",
    "阳刃": "challenger",
    "从财": "operator",
    "从杀": "commander",
    "从儿": "creator",
    "从旺": "independent",
    "从强": "guardian",
}


def _clamp(value: float, minimum: float = 0, maximum: float = 100) -> float:
    return max(minimum, min(maximum, value))


def _stable_fraction(value: str) -> float:
    return int(sha256(value.encode("utf-8")).hexdigest()[:8], 16) / 0xFFFFFFFF


def _profile_by_key(profiles: Iterable[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    return {
        PROFILE_THEME_KEYS[str(profile.get("theme", ""))]: profile
        for profile in profiles
        if str(profile.get("theme", "")) in PROFILE_THEME_KEYS
    }


def _theme_path(
    key: str,
    profile: Mapping[str, Any],
    pattern: Mapping[str, Any],
) -> tuple[str, str]:
    values = {
        str(metric.get("metric_id", "")): int(metric.get("value", 0) or 0)
        for metric in profile.get("structure_metrics", ())
    }
    primary = pattern.get("primary") if isinstance(pattern, Mapping) else None
    pattern_name = str(primary.get("name", "")) if isinstance(primary, Mapping) else ""
    if key == "career":
        if "印" in pattern_name:
            return "专业积累型", "更适合通过学习、研究、资质与长期能力建设形成位置。"
        if any(token in pattern_name for token in ("官", "杀")):
            return "责任推动型", "更容易在明确目标、责任与组织协作中建立影响力。"
        if any(token in pattern_name for token in ("食神", "伤官")):
            return "创造表达型", "更适合用作品、表达、解决问题与新方法打开局面。"
        return "自主开拓型", "事业路径更依赖个人判断、持续行动与阶段机会。"
    if key == "wealth":
        visible = values.get("visible_wealth_count", 0)
        hidden = values.get("hidden_wealth_count", 0)
        if visible:
            return "外显经营型", "资源与现实结果更容易直接进入选择和行动。"
        if hidden:
            return "潜藏兑现型", "财星主要藏于地支，资源更偏长期积累与阶段兑现；这不等于贫穷或没有财富。"
        return "能力转化型", "财富更依赖专业能力、关系网络与运限机会转化，并非由单一财星数量决定。"
    if key == "relationship":
        if values.get("spouse_palace_relation_count", 0) >= 4:
            return "高互动型", "关系与生活选择联动较多，重要关系更容易推动阶段变化。"
        if values.get("day_stem_combine_count", 0):
            return "关系牵引型", "亲密关系在选择、合作与人生节奏中具有较强牵引力。"
        return "渐进建立型", "关系更适合通过理解、信任与共同经历逐步深化。"
    pressure = values.get("pressure_relation_count", 0)
    concentration = values.get("concentrated_element_count", 0)
    if pressure >= 5:
        return "敏感调节型", "结构变化较密集，需要在输出、休整与环境切换之间找到自己的节奏。"
    if concentration >= 2:
        return "内稳外紧型", "内在力量较集中，外部变化来临时更需要主动安排恢复与缓冲。"
    return "均衡恢复型", "整体节奏更适合稳定推进，并为阶段变化保留恢复空间。"


def consumer_feature_records(
    patterns: Mapping[str, Any] | None,
    shensha_effects: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    """Feature IDs shared by baseline generation and live-chart lookup."""
    records: list[dict[str, str]] = []
    pattern = patterns or {}
    primary = pattern.get("primary") if isinstance(pattern, Mapping) else None
    if isinstance(primary, Mapping) and primary.get("id"):
        records.append({
            "id": str(primary["id"]),
            "kind": "pattern",
            "title": str(primary.get("title", primary.get("name", "主导格局"))),
        })
    effects = shensha_effects or {}
    for hit in effects.get("hits", ()):
        state = str(hit.get("state", "可见"))
        state_id = _SHENSHA_STATE_IDS.get(state, "visible")
        records.append({
            "id": f"bazi.consumer.shensha.{hit.get('rule_id', 'unknown')}.state.{state_id}",
            "kind": "shensha_state",
            "title": f"{hit.get('name', '神煞')}·{state}",
        })
    for combination in effects.get("combinations", ()):
        if combination.get("id"):
            records.append({
                "id": str(combination["id"]),
                "kind": "combination",
                "title": str(combination.get("title", "结构组合")),
            })
    unique: dict[str, dict[str, str]] = {}
    for record in records:
        unique.setdefault(record["id"], record)
    return list(unique.values())


def _feature_percentage_map(metrics: Iterable[Mapping[str, Any]]) -> dict[str, float]:
    return {
        str(metric.get("feature_id", "")): float(metric.get("percentage", 0) or 0)
        for metric in metrics
        if metric.get("status") in {"observed", "zero"}
    }


def _choose_archetype(
    pillars: Iterable[Mapping[str, Any]],
    shensha: Iterable[Mapping[str, Any]],
    pattern: Mapping[str, Any],
) -> tuple[str, str, str]:
    primary = pattern.get("primary") if isinstance(pattern, Mapping) else None
    pattern_name = str(primary.get("name", "")) if isinstance(primary, Mapping) else ""
    preferred_id = next((archetype_id for token, archetype_id in _PATTERN_ARCHETYPES.items() if token in pattern_name), "")
    if preferred_id:
        preferred = next(item for item in _ARCHETYPES if item[0] == preferred_id)
        return preferred[0], preferred[1], preferred[2]

    pillar_list = list(pillars)
    tokens = {str(pillar.get("ten_god", "")) for pillar in pillar_list}
    tokens.update(
        str(hidden.get("ten_god", ""))
        for pillar in pillar_list
        for hidden in pillar.get("hidden_stems", ())
    )
    tokens.update(str(hit.get("name", "")) for hit in shensha)
    best = max(
        _ARCHETYPES,
        key=lambda item: (len(item[3] & tokens), _stable_fraction("|".join(sorted(tokens)) + item[0])),
    )
    return best[0], best[1], best[2]


def _fingerprints(
    profiles: Iterable[Mapping[str, Any]],
    pattern: Mapping[str, Any],
    shensha: Iterable[Mapping[str, Any]],
    feature_percentages: Mapping[str, float],
) -> list[dict[str, Any]]:
    candidates: list[tuple[int, float, dict[str, Any]]] = []
    primary = pattern.get("primary") if isinstance(pattern, Mapping) else None
    if isinstance(primary, Mapping) and primary.get("name"):
        pattern_incidence = feature_percentages.get(str(primary.get("id", "")))
        sort_incidence = pattern_incidence if pattern_incidence is not None else 100.0
        candidates.append((0, sort_incidence, {
            "id": f"pattern.{primary.get('id', 'primary')}",
            "title": f"{primary.get('title', primary['name'])} · {_PATTERN_STATUS_LABELS.get(str(primary.get('status', '')), str(primary.get('status', '主导')))}",
            "detail": str(primary.get("summary", "这是命盘最醒目的格局结构。")),
            "rarity_label": "主格结构" if pattern_incidence is None else "罕见" if pattern_incidence < 1 else "稀有" if pattern_incidence < 5 else "少见" if pattern_incidence < 20 else "核心格局",
            "top_percentage": max(1, min(99, int(round(pattern_incidence)))) if pattern_incidence is not None else 100,
            "incidence_percentage": round(pattern_incidence, 2) if pattern_incidence is not None else None,
        }))
    metric_priority = {
        "root_pillar_count": 1,
        "visible_wealth_count": 1,
        "hidden_wealth_count": 1,
        "visible_spouse_count": 1,
        "hidden_spouse_count": 1,
        "spouse_palace_relation_count": 1,
        "day_stem_combine_count": 1,
        "relation_count": 2,
        "mobility_count": 2,
    }
    for profile in profiles:
        for comparison in profile.get("comparisons", ()):
            if comparison.get("status") not in {"observed", "zero"}:
                continue
            same = float(comparison.get("same_mass", comparison.get("exact_percentage", 100)) or 100)
            value = comparison.get("value", 0)
            title = str(comparison.get("label", comparison.get("metric_id", "结构特征")))
            metric_id = str(comparison.get("metric_id", title))
            candidates.append((metric_priority.get(metric_id, 3), same, {
                "id": f"metric.{comparison.get('metric_id', title)}",
                "title": title,
                "detail": f"当前为 {value}{comparison.get('unit', '项')}；约 {same:.1f}% 的历法样本与此同值。",
                "rarity_label": "罕见" if same < 1 else "稀有" if same < 5 else "少见" if same < 20 else "常见结构",
                "top_percentage": max(1, min(99, int(round(same)))),
                "incidence_percentage": round(same, 2),
            }))
    for hit in shensha:
        state = str(hit.get("state", "可见"))
        if state not in {"发力", "有力"}:
            continue
        state_feature_id = f"bazi.consumer.shensha.{hit.get('rule_id', 'unknown')}.state.{_SHENSHA_STATE_IDS.get(state, 'visible')}"
        rarity = feature_percentages.get(
            state_feature_id,
            float(hit.get("rarity_percentage", 100) or 100),
        )
        if rarity >= 20:
            continue
        candidates.append((4, rarity + 0.1, {
            "id": f"shensha.{hit.get('rule_id', hit.get('name', 'hit'))}",
            "title": f"{hit.get('name', '神煞')} · {hit.get('state', '可见')}",
            "detail": str(hit.get("state_reason", hit.get("trigger", "原局命中这一辅助结构。"))),
            "rarity_label": "罕见" if rarity < 1 else "稀有" if rarity < 5 else "少见",
            "top_percentage": max(1, int(round(rarity))),
            "incidence_percentage": round(rarity, 2),
        }))
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for _, _, item in sorted(candidates, key=lambda pair: (pair[0], pair[1], pair[2]["id"])):
        if item["id"] in seen:
            continue
        seen.add(item["id"])
        unique.append(item)
        if len(unique) == 5:
            break
    return unique


def _achievements(
    combinations: Iterable[Mapping[str, Any]],
    shensha: Iterable[Mapping[str, Any]],
    feature_percentages: Mapping[str, float],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    member_names = {str(hit.get("rule_id", "")): str(hit.get("name", "")) for hit in shensha}
    for combo in combinations:
        member_count = len(combo.get("member_rule_ids", ()))
        tier = str(combo.get("tier", "product_cluster"))
        fallback_rarity = max(0.2, 14 / max(1, member_count) * {"classical_named": 0.45, "classical_interaction": 0.7, "product_cluster": 1.0}.get(tier, 1))
        rarity = feature_percentages.get(str(combo.get("id", "")), fallback_rarity)
        results.append({
            "id": str(combo.get("id", "combination")),
            "title": str(combo.get("title", "结构共振")),
            "tier": "SSR" if tier == "classical_named" else "SR" if tier == "classical_interaction" else "R",
            "state": "发力" if tier == "classical_named" else "有力" if tier == "classical_interaction" else "可见",
            "rarity_percentage": round(rarity, 2),
            "position": " · ".join(
                str(item)
                for item in (
                    combo.get("member_names")
                    or [member_names.get(str(rule_id), str(rule_id)) for rule_id in combo.get("member_rule_ids", ())]
                )
            ),
            "summary": str(combo.get("summary", "多个结构在同一命盘中形成共振。")),
            "member_ids": list(combo.get("member_rule_ids", ())),
        })
    for hit in shensha:
        if str(hit.get("state", "可见")) not in {"发力", "有力"}:
            continue
        state = str(hit.get("state", "有力"))
        state_feature_id = f"bazi.consumer.shensha.{hit.get('rule_id', 'unknown')}.state.{_SHENSHA_STATE_IDS.get(state, 'visible')}"
        rarity = feature_percentages.get(
            state_feature_id,
            float(hit.get("rarity_percentage", 12.0) or 12.0),
        )
        if rarity >= 20:
            continue
        results.append({
            "id": f"shensha.{hit.get('rule_id', hit.get('name', 'hit'))}",
            "title": str(hit.get("name", "神煞")),
            "tier": "SR" if hit.get("state") == "发力" else "R",
            "state": str(hit.get("state", "有力")),
            "rarity_percentage": rarity,
            "position": " · ".join(str(item) for item in hit.get("pillar_labels", ())),
            "summary": str(hit.get("state_reason", hit.get("trigger", "这一结构在原局得到呼应。"))),
            "member_ids": [str(hit.get("rule_id", ""))],
        })
    return sorted(results, key=lambda item: (float(item["rarity_percentage"]), item["title"]))[:8]


def _event_delta(events: Iterable[Mapping[str, Any]]) -> tuple[float, list[str], float]:
    positive = 0.0
    negative = 0.0
    drivers: list[str] = []
    seen: set[tuple[str, str]] = set()
    for event in events:
        kind = str(event.get("kind", "变化"))
        label = str(event.get("label", "阶段变化"))
        identity = (kind, label)
        if identity in seen:
            continue
        seen.add(identity)
        weight = _PERIOD_EVENT_WEIGHTS.get(kind, 1.0)
        if weight >= 0:
            positive += weight
        else:
            negative += abs(weight)
        if len(drivers) < 4:
            drivers.append(label)

    # Activation signals compound with diminishing returns. This keeps a year
    # with many related rules visibly active without allowing repeated labels
    # to pin an entire K-line at 99 or 1.
    delta = sqrt(positive) * 1.35 - sqrt(negative) * 1.55
    intensity = len(seen) * 4 + sqrt(positive + negative) * 2
    return round(delta, 2), drivers, round(intensity, 2)


def build_life_kline(
    cycles: Iterable[Mapping[str, Any]],
    natal_scores: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    """Build period activity without treating natal structure as quality.

    ``natal_scores`` remains accepted so older callers keep working,
    but intentionally has no effect. The client rebases each series to the
    user's own long-term average of 100.
    """
    del natal_scores
    expanded_cycles = [cycle for cycle in cycles if cycle.get("years")]
    bands = [
        {
            "label": str(cycle.get("label", "大运")),
            "start_year": int(cycle.get("start_year", 0) or 0),
            "end_year": int(cycle.get("end_year", 0) or 0),
        }
        for cycle in expanded_cycles
    ]
    series: list[dict[str, Any]] = []
    all_years: set[int] = set()
    for key in ("overall", *THEME_ORDER):
        label = "综合" if key == "overall" else THEME_LABELS[key]
        natal = 50.0
        points: list[dict[str, Any]] = []
        for cycle in expanded_cycles:
            cycle_theme = []
            activations = cycle.get("theme_activations", {})
            if key == "overall":
                cycle_theme = [event for values in activations.values() for event in values]
            else:
                profile_label = "五行与承压结构" if key == "health" else THEME_LABELS[key]
                cycle_theme = list(activations.get(profile_label, ()))
            cycle_delta, _, _ = _event_delta(cycle_theme)
            for year in cycle.get("years", ()):
                year_events_by_theme = year.get("theme_activations", {})
                if key == "overall":
                    year_events = [event for values in year_events_by_theme.values() for event in values]
                else:
                    profile_label = "五行与承压结构" if key == "health" else THEME_LABELS[key]
                    year_events = list(year_events_by_theme.get(profile_label, ()))
                year_delta, year_drivers, year_intensity = _event_delta(year_events)
                months = []
                month_values = []
                for month in year.get("months", ()):
                    month_by_theme = month.get("theme_activations", {})
                    if key == "overall":
                        month_events = [event for values in month_by_theme.values() for event in values]
                    else:
                        profile_label = "五行与承压结构" if key == "health" else THEME_LABELS[key]
                        month_events = list(month_by_theme.get(profile_label, ()))
                    month_delta, month_drivers, month_intensity = _event_delta(month_events)
                    value = round(_clamp(natal + cycle_delta * 0.45 + year_delta * 0.9 + month_delta * 1.25, 12, 98), 1)
                    month_values.append(value)
                    months.append({
                        "index": int(month.get("index", len(months))),
                        "label": str(month.get("label", f"{len(months) + 1}月")),
                        "ganzhi": str(month.get("ganzhi", "")),
                        "value": value,
                        "delta": round(cycle_delta * 0.45 + year_delta * 0.9 + month_delta * 1.25, 1),
                        "drivers": list(dict.fromkeys([*year_drivers, *month_drivers]))[:4],
                        "intensity": round(month_intensity, 1),
                    })
                if not month_values:
                    continue
                year_number = int(year.get("year", 0) or 0)
                all_years.add(year_number)
                points.append({
                    "year": year_number,
                    "open": month_values[0],
                    "close": month_values[-1],
                    "high": max(month_values),
                    "low": min(month_values),
                    "volume": round(year_intensity + sum(float(item["intensity"]) for item in months), 1),
                    "ma3": None,
                    "ma5": None,
                    "ma10": None,
                    "months": months,
                })
        closes: list[float] = []
        for point in points:
            closes.append(float(point["close"]))
            for window in (3, 5, 10):
                point[f"ma{window}"] = round(sum(closes[-window:]) / window, 1) if len(closes) >= window else None
        series.append({"key": key, "label": label, "color": THEME_COLORS[key], "points": points})

    years = sorted(year for year in all_years if year)
    default_cycle = next((cycle for cycle in expanded_cycles if cycle.get("is_current")), None)
    if default_cycle is None and expanded_cycles:
        default_cycle = expanded_cycles[0]
    default_years = sorted(
        int(year.get("year", 0) or 0)
        for year in (default_cycle or {}).get("years", ())
        if int(year.get("year", 0) or 0)
    )
    default_year_set = set(default_years)
    stages = []
    for item in series:
        candidates = [point for point in item["points"] if not default_year_set or point["year"] in default_year_set]
        sorted_points = sorted(candidates, key=lambda point: (point["high"], point["volume"]), reverse=True)
        stages.extend({
            "key": item["key"],
            "label": ("突破窗口" if index == 0 else "扩张窗口" if index == 1 else "重要转折"),
            "year": point["year"],
            "score": point["high"],
            "theme": item["label"],
            "summary": f"全年峰值 {point['high']:.0f}，结构活跃度 {point['volume']:.0f}。",
        } for index, point in enumerate(sorted_points[:3]))
    return {
        "default_window": {
            "start_year": default_years[0] if default_years else years[0] if years else 0,
            "end_year": default_years[-1] if default_years else years[-1] if years else 0,
        },
        "series": series,
        "period_bands": bands,
        "stages": stages,
        "method": "deterministic-period-activation-ohlcv-v1",
    }


def build_bazi_consumer_profile(
    *,
    pillars: Iterable[Mapping[str, Any]],
    structure: Mapping[str, Any],
    patterns: Mapping[str, Any] | None,
    shensha_effects: Mapping[str, Any] | None,
    cycles: Iterable[Mapping[str, Any]],
    consumer_distributions: Mapping[str, Any] | None = None,
    consumer_feature_metrics: Iterable[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    pillar_list = list(pillars)
    profiles = list(structure.get("theme_profiles", ()))
    effects = shensha_effects or {}
    hits = list(effects.get("hits", ()))
    combinations = list(effects.get("combinations", ()))
    pattern = patterns or {}
    feature_percentages = _feature_percentage_map(consumer_feature_metrics)
    profiles_by_key = _profile_by_key(profiles)
    subjects: list[dict[str, Any]] = []
    for key in THEME_ORDER:
        profile = profiles_by_key.get(key, {})
        path_label, path_summary = _theme_path(key, profile, pattern)
        evidence = list(profile.get("evidence", ()))
        drivers = [
            str(item.get("title", ""))
            for item in evidence
            if item.get("evidence_type") in {"支持", "活动", "背景"} and item.get("title")
        ][:4]
        primary = pattern.get("primary") if isinstance(pattern, Mapping) else None
        if isinstance(primary, Mapping) and primary.get("name"):
            status = _PATTERN_STATUS_LABELS.get(str(primary.get("status", "")), str(primary.get("status", "主导")))
            drivers.insert(0, f"{primary['name']}·{status}")
        drivers = list(dict.fromkeys(drivers))[:4]
        subjects.append({
            "key": key,
            "label": THEME_LABELS[key],
            "headline": " · ".join(drivers[:2]) or "结构节奏鲜明",
            "drivers": drivers,
            "path_label": path_label,
            "path_summary": path_summary,
        })

    archetype_id, archetype_title, archetype_subtitle = _choose_archetype(pillar_list, hits, pattern)
    primary = pattern.get("primary") if isinstance(pattern, Mapping) else None
    pattern_title = str(primary.get("title", primary.get("name", "主导结构"))) if isinstance(primary, Mapping) else "主导结构"
    identity = {
        "system_title": "八字命格",
        "archetype_id": archetype_id,
        "archetype_title": f"{pattern_title} · {archetype_title}",
        "archetype_subtitle": archetype_subtitle,
        "fusion_title": None,
        "primary_arena": subjects[0]["path_label"] if subjects else "个人成长",
        "signature": next((item["path_label"] for item in subjects if item["key"] == "relationship"), "关系节奏鲜明"),
        "life_rhythm": next((item["path_label"] for item in subjects if item["key"] == "health"), "稳定推进型"),
    }
    return {
        "version": CONSUMER_RULES_VERSION,
        "system": "bazi",
        "identity": identity,
        "subjects": subjects,
        "achievements": _achievements(combinations, hits, feature_percentages),
        "fingerprints": _fingerprints(profiles, pattern, hits, feature_percentages),
        # A day-master/month-command cohort is not a true structural twin.
        "twin": None,
        "life_kline": build_life_kline(cycles),
        "capability_key": None,
    }
