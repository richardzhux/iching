from __future__ import annotations

from collections import Counter
from typing import Any, Iterable, Mapping

from iching.core.bazi_structure import (
    HIDDEN_STEMS,
    STEM_ELEMENTS,
    _ten_god,
    structured_relations,
)


SHENSHA_EFFECTS_RULES_VERSION = "shensha-effects-2026.09-v2"

_STEMS = "甲乙丙丁戊己庚辛壬癸"
_BRANCHES = "子丑寅卯辰巳午未申酉戌亥"
_STEM_SET = frozenset(_STEMS)
_BRANCH_SET = frozenset(_BRANCHES)
_SEASONAL_STATUS = {
    "spring": {"木": "旺", "火": "相", "水": "休", "金": "囚", "土": "死"},
    "summer": {"火": "旺", "土": "相", "木": "休", "水": "囚", "金": "死"},
    "autumn": {"金": "旺", "水": "相", "土": "休", "火": "囚", "木": "死"},
    "winter": {"水": "旺", "木": "相", "金": "休", "土": "囚", "火": "死"},
    "earth": {"土": "旺", "金": "相", "火": "休", "木": "囚", "水": "死"},
}

_AXIS_GODS: dict[str, set[str]] = {
    "助力": {"正官", "七杀", "正印", "偏印"},
    "才学": {"食神", "伤官", "正印", "偏印"},
    "情缘": {"正财", "偏财", "正官", "七杀"},
    "执行": {"比肩", "劫财", "正官", "七杀"},
    "迁动": {"食神", "伤官", "正财", "偏财"},
    "考验": {"比肩", "劫财", "正官", "七杀"},
}

_RULE_GODS: dict[str, set[str]] = {
    "wenchang": {"食神", "伤官", "正印", "偏印"},
    "xuetang": {"食神", "伤官", "正印", "偏印"},
    "ciguan": {"食神", "伤官", "正印", "偏印"},
    "tianku": {"食神", "伤官"},
    "dexiu": {"食神", "伤官", "正印", "偏印"},
    "lushen": {"比肩", "劫财"},
    "yangren": {"比肩", "劫财"},
    "jiangxing": {"比肩", "劫财", "正官", "七杀"},
    "kuigang": {"比肩", "劫财", "正官", "七杀"},
    "huagai": {"食神", "伤官", "正印", "偏印"},
    "taohua": {"正财", "偏财", "正官", "七杀"},
    "hongluan": {"正财", "偏财", "正官", "七杀"},
    "tianxi": {"正财", "偏财", "正官", "七杀"},
    "hongyan": {"正财", "偏财", "正官", "七杀"},
    "jinyu": {"正财", "偏财", "正官", "七杀"},
}

_TOPIC_ORDER = ("career", "wealth", "relationship", "health")


def _pillar_by_label(pillars: list[Mapping[str, Any]], label: str) -> Mapping[str, Any] | None:
    return next((pillar for pillar in pillars if str(pillar.get("label", "")) == label), None)


def _value(pillar: Mapping[str, Any], key: str) -> str:
    value = pillar.get(key, "")
    if isinstance(value, Mapping):
        value = value.get("value", "")
    return str(value)


def _day_void(pillars: list[Mapping[str, Any]]) -> set[str]:
    day = _pillar_by_label(pillars, "日")
    if not day:
        return set()
    recorded = str(day.get("xunkong", ""))
    if len(recorded) == 2:
        return set(recorded)
    stem = _value(day, "stem")
    branch = _value(day, "branch")
    if stem not in _STEM_SET or branch not in _BRANCH_SET:
        return set()
    start_branch = (_BRANCHES.index(branch) - _STEMS.index(stem)) % 12
    return {_BRANCHES[(start_branch - 2) % 12], _BRANCHES[(start_branch - 1) % 12]}


def _seasonal_status(month_branch: str) -> Mapping[str, str]:
    if month_branch not in _BRANCH_SET:
        return {}
    if month_branch in {"寅", "卯"}:
        season = "spring"
    elif month_branch in {"巳", "午"}:
        season = "summer"
    elif month_branch in {"申", "酉"}:
        season = "autumn"
    elif month_branch in {"亥", "子"}:
        season = "winter"
    else:
        season = "earth"
    return _SEASONAL_STATUS[season]


def _day_stem(pillars: list[Mapping[str, Any]], structure: Mapping[str, Any]) -> str:
    day_master = structure.get("day_master", {})
    recorded = str(day_master.get("stem", "")) if isinstance(day_master, Mapping) else ""
    if recorded in _STEM_SET:
        return recorded
    day = _pillar_by_label(pillars, "日")
    return _value(day, "stem") if day else ""


def _pillar_gods(pillar: Mapping[str, Any], day_stem: str) -> set[str]:
    gods: set[str] = set()
    label = str(pillar.get("label", ""))
    stem = _value(pillar, "stem")
    branch = _value(pillar, "branch")
    if label != "日" and stem in _STEM_SET:
        gods.add(_ten_god(day_stem, stem))
    hidden_values = HIDDEN_STEMS.get(branch, ())
    for hidden in hidden_values:
        gods.add(_ten_god(day_stem, hidden))
    return gods


def _chart_gods(
    pillars: list[Mapping[str, Any]],
    structure: Mapping[str, Any],
    day_stem: str,
) -> set[str]:
    gods = {god for pillar in pillars for god in _pillar_gods(pillar, day_stem)}
    for relation in structure.get("day_master_relations", ()):
        if isinstance(relation, Mapping):
            god = str(relation.get("ten_god", ""))
            if god:
                gods.add(god)
    return gods


def _visible_gods(pillars: list[Mapping[str, Any]], day_stem: str) -> Counter[str]:
    gods: Counter[str] = Counter()
    for pillar in pillars:
        if str(pillar.get("label", "")) == "日":
            continue
        stem = _value(pillar, "stem")
        if stem in _STEM_SET:
            gods[_ten_god(day_stem, stem)] += 1
    return gods


def _matched_elements(
    hit: Mapping[str, Any],
    labels: set[str],
    pillars: list[Mapping[str, Any]],
) -> set[str]:
    formula = hit.get("formula", {})
    candidate_field = str(formula.get("candidate_field", "branch")) if isinstance(formula, Mapping) else "branch"
    targets = {
        str(target)
        for anchor in hit.get("anchors", ())
        if isinstance(anchor, Mapping)
        for target in anchor.get("targets", ())
    }
    elements: set[str] = set()
    for label in labels:
        pillar = _pillar_by_label(pillars, label)
        if not pillar:
            continue
        stem = _value(pillar, "stem")
        branch = _value(pillar, "branch")
        symbols: list[str]
        if candidate_field == "stem":
            symbols = [stem]
        elif candidate_field == "stem_or_branch":
            symbols = [symbol for symbol in (stem, branch) if not targets or symbol in targets]
        elif candidate_field == "text":
            symbols = [stem, branch]
        else:
            symbols = [branch]
        for symbol in symbols:
            if symbol in STEM_ELEMENTS:
                elements.add(STEM_ELEMENTS[symbol])
            elif symbol in HIDDEN_STEMS:
                elements.add(STEM_ELEMENTS[HIDDEN_STEMS[symbol][0]])
    return elements


def _rooted(
    hit: Mapping[str, Any],
    labels: set[str],
    pillars: list[Mapping[str, Any]],
    structure: Mapping[str, Any],
    day_stem: str,
) -> bool:
    relevant = _RULE_GODS.get(str(hit.get("rule_id", "")), _AXIS_GODS.get(str(hit.get("axis", "")), set()))
    root_labels = set()
    day_master = structure.get("day_master", {})
    if isinstance(day_master, Mapping):
        root_labels = {str(label) for label in day_master.get("root_pillars", ())}
    if str(hit.get("rule_id", "")) in {"lushen", "yangren"} and labels & root_labels:
        return True
    return any(
        bool(_pillar_gods(pillar, day_stem) & relevant)
        for label in labels
        if (pillar := _pillar_by_label(pillars, label)) is not None
    )


def _structure_echo(
    hit: Mapping[str, Any],
    chart_gods: set[str],
    relations: Iterable[Mapping[str, Any]],
    structure: Mapping[str, Any],
) -> bool:
    rule_id = str(hit.get("rule_id", ""))
    relevant = _RULE_GODS.get(rule_id, _AXIS_GODS.get(str(hit.get("axis", "")), set()))
    if chart_gods & relevant:
        return True
    relation_types = {str(relation.get("relation_type", "")) for relation in relations}
    if rule_id == "yima" and "地支冲" in relation_types:
        return True
    if str(hit.get("axis", "")) == "考验" and relation_types & {"地支冲", "地支刑", "地支害", "地支破", "天干冲", "天干克"}:
        return True
    pattern = structure.get("pattern_assessment", structure.get("patterns", {}))
    if isinstance(pattern, Mapping):
        primary = pattern.get("primary")
        if isinstance(primary, Mapping) and str(primary.get("name", "")) in relevant:
            return True
    return False


def _relation_flags(
    labels: set[str],
    relations: Iterable[Mapping[str, Any]],
) -> dict[str, bool]:
    flags = {"clashed": False, "punished": False, "harmed": False, "broken": False}
    names = {
        "地支冲": "clashed",
        "地支刑": "punished",
        "地支自刑": "punished",
        "地支害": "harmed",
        "地支破": "broken",
    }
    for relation in relations:
        relation_type = str(relation.get("relation_type", ""))
        flag = names.get(relation_type)
        if not flag:
            continue
        participants = {
            str(item.get("pillar", ""))
            for item in relation.get("participants", ())
            if isinstance(item, Mapping)
        }
        if labels & participants:
            flags[flag] = True
    return flags


def _combination(
    by_id: Mapping[str, Mapping[str, Any]],
    *,
    combo_id: str,
    title: str,
    tier: str,
    rarity_tier: str,
    members: Iterable[str],
    summary: str,
    fallback_topics: Iterable[str] = (),
) -> dict[str, Any]:
    member_ids = list(dict.fromkeys(str(member) for member in members if member in by_id))
    topics = {
        str(topic)
        for rule_id in member_ids
        for topic in by_id[rule_id].get("topic_tags", ())
    }
    topics.update(str(topic) for topic in fallback_topics)
    constrained = any(by_id[rule_id].get("state") == "受制" for rule_id in member_ids)
    return {
        "id": f"bazi.shensha.combination.{combo_id}",
        "title": title,
        "tier": tier,
        "rarity_tier": rarity_tier,
        "member_rule_ids": member_ids,
        "member_names": [str(by_id[rule_id].get("name") or rule_id) for rule_id in member_ids],
        "status": "constrained" if constrained else "active",
        "summary": summary,
        "topic_tags": [topic for topic in _TOPIC_ORDER if topic in topics],
    }


# Fixed, declared topic universes. Each feature describes the exact membership
# within its universe, including absent markers; no search for a rare subset.
THEME_MARKER_GROUPS = (
    ("learning", "才学组合", ("wenchang", "xuetang", "ciguan", "huagai", "dexiu"), "career"),
    ("relationship", "关系组合", ("taohua", "hongyan", "hongluan", "tianxi"), "relationship"),
    ("support", "助力组合", ("tianyi", "tiande", "yuede", "fuxing", "guoyin"), "career"),
    ("movement", "行动组合", ("lushen", "yima", "jiangxing", "yangren"), "career"),
)


def _theme_combinations(evaluated: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    by_id = {str(hit.get("rule_id", "")): hit for hit in evaluated}
    results = []
    for topic_id, title, universe, theme in THEME_MARKER_GROUPS:
        members = [key for key in universe if key in by_id]
        if len(members) < 2:
            continue
        mask = "".join("1" if key in by_id else "0" for key in universe)
        names = [str(by_id[key].get("name", key)) for key in members]
        missing = [key for key in universe if key not in by_id]
        result = _combination(
            by_id, combo_id=f"theme.{topic_id}.{mask}", title=title,
            tier="theme_profile", rarity_tier="frequency_only", members=members,
            summary="、".join(names) + "共同命中；出现率统计这套固定主题指标中完全相同的有无配置，不据此判定聪明、感情好坏或现实结果。",
            fallback_topics=(theme,),
        )
        result.update({"universe_rule_ids": list(universe), "absent_rule_ids": missing,
                       "incidence_semantics": "exact_membership_within_fixed_theme",
                       "state": "受制" if any(by_id[key].get("state") == "受制" for key in members) else "条件齐备" if all(by_id[key].get("state") == "条件齐备" for key in members) else "命中",
                       "member_positions": {key: list(by_id[key].get("pillar_labels", ())) for key in members}})
        results.append(result)
    return results


def evaluate_shensha_effects(
    hits: Iterable[Mapping[str, Any]],
    pillars: Iterable[Mapping[str, Any]],
    structure: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Add evidence-based effect states while preserving every registry hit field."""

    pillar_list = list(pillars)
    structure = structure or {}
    raw_relations = structure.get("structural_relations")
    if isinstance(raw_relations, (list, tuple)):
        relations = list(raw_relations)
    else:
        relations = structured_relations(pillar_list)
    void_branches = _day_void(pillar_list)
    day_stem = _day_stem(pillar_list, structure)
    chart_gods = _chart_gods(pillar_list, structure, day_stem) if day_stem in _STEM_SET else set()
    month = _pillar_by_label(pillar_list, "月")
    season = _seasonal_status(_value(month, "branch") if month else "")
    evaluated: list[dict[str, Any]] = []
    for source_hit in hits:
        hit = dict(source_hit)
        labels = {str(label) for label in hit.get("pillar_labels", ())}
        matched_branches = {
            _value(pillar, "branch")
            for label in labels
            if (pillar := _pillar_by_label(pillar_list, label)) is not None
        }
        matched_elements = _matched_elements(hit, labels, pillar_list)
        flags: dict[str, bool] = {
            "rooted": _rooted(hit, labels, pillar_list, structure, day_stem) if day_stem in _STEM_SET else False,
            "season_supported": any(season.get(element) in {"旺", "相"} for element in matched_elements),
            "void": bool(matched_branches & void_branches),
            **_relation_flags(labels, relations),
            "structure_echo": _structure_echo(hit, chart_gods, relations, structure),
            "central_position": bool(labels & {"月", "日"}),
            "multiple_positions": len(labels) > 1,
        }
        if not labels or day_stem not in _STEM_SET:
            state = "待核"
        elif any(flags[key] for key in ("void", "clashed", "punished", "harmed", "broken")):
            state = "受制"
        elif flags["rooted"] and flags["season_supported"] and flags["structure_echo"]:
            state = "条件齐备"
        else:
            state = "命中"
        positive_labels = {
            "rooted": "得根",
            "season_supported": "得令",
            "structure_echo": "结构呼应",
            "central_position": "月日近身",
            "multiple_positions": "多柱同见",
        }
        negative_labels = {
            "void": "落空亡",
            "clashed": "逢冲",
            "punished": "逢刑",
            "harmed": "逢害",
            "broken": "逢破",
        }
        positive = [label for name, label in positive_labels.items() if flags[name]]
        negative = [label for name, label in negative_labels.items() if flags[name]]
        hit.update({
            "state": state,
            "state_reason": f"支持：{'、'.join(positive) or '仅规则命中'}；制约：{'、'.join(negative) or '未见冲刑害破空'}。",
            "condition_method": "位置明确；通根、月令支持与主题呼应齐备且未见冲刑害破空时，记条件齐备。此为辅助条件检查，不是吉凶或作用强度评分。",
            "effect_flags": flags,
        })
        evaluated.append(hit)
    visible_gods = _visible_gods(pillar_list, day_stem) if day_stem in _STEM_SET else Counter()
    combinations = _theme_combinations(evaluated)
    return {
        "rules_version": SHENSHA_EFFECTS_RULES_VERSION,
        "hits": evaluated,
        "combinations": combinations,
    }
