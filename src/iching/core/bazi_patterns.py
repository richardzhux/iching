from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from iching.core.bazi_structure import (
    ELEMENT_CONTROLS,
    HIDDEN_STEMS,
    MEETINGS,
    STEM_ELEMENTS,
    TRINES,
    _ten_god,
)


PATTERN_RULES_VERSION = "bazi-patterns-2026.07-v1"

ORDINARY_PATTERN_NAMES = (
    "正官", "七杀", "正财", "偏财", "食神", "伤官", "正印", "偏印", "建禄", "阳刃",
)
SPECIAL_PATTERN_NAMES = (
    "从财", "从杀", "从儿", "从旺", "从强", "曲直", "炎上", "稼穑", "从革", "润下",
)

_STEMS = "甲乙丙丁戊己庚辛壬癸"

_LU_BRANCH = dict(zip(_STEMS, ("寅", "卯", "巳", "午", "巳", "午", "申", "酉", "亥", "子")))
_YANGREN_BRANCH = dict(zip(_STEMS, ("卯", "辰", "午", "未", "午", "未", "酉", "戌", "子", "丑")))

_PATTERN_IDS = {
    "正官": "direct_officer",
    "七杀": "seven_killings",
    "正财": "direct_wealth",
    "偏财": "indirect_wealth",
    "食神": "eating_god",
    "伤官": "hurting_officer",
    "正印": "direct_resource",
    "偏印": "indirect_resource",
    "建禄": "month_prosperity",
    "阳刃": "yang_blade",
    "从财": "follow_wealth",
    "从杀": "follow_officer",
    "从儿": "follow_output",
    "从旺": "follow_prosperous",
    "从强": "follow_strong",
    "曲直": "exclusive_wood",
    "炎上": "exclusive_fire",
    "稼穑": "exclusive_earth",
    "从革": "exclusive_metal",
    "润下": "exclusive_water",
}

_BREAK_RULES: dict[str, tuple[tuple[set[str], str], ...]] = {
    "正官": (({"伤官"}, "伤官见官"),),
    "七杀": (({"正财", "偏财"}, "财星生杀而无制"),),
    "正财": (({"比肩", "劫财"}, "比劫夺财"),),
    "偏财": (({"比肩", "劫财"}, "比劫夺财"),),
    "食神": (({"偏印"}, "枭印夺食"),),
    "伤官": (({"正官"}, "伤官见官"),),
    "正印": (({"正财", "偏财"}, "财星坏印"),),
    "偏印": (({"正财", "偏财"}, "财星坏印"),),
}

_RESCUE_RULES: dict[str, tuple[tuple[set[str], str], ...]] = {
    "正官": (({"正印", "偏印"}, "印星制伤"),),
    "七杀": (({"食神"}, "食神制杀"), ({"正印", "偏印"}, "印星化杀")),
    "正财": (({"食神", "伤官"}, "食伤生财"), ({"正官", "七杀"}, "官杀制劫")),
    "偏财": (({"食神", "伤官"}, "食伤生财"), ({"正官", "七杀"}, "官杀制劫")),
    "食神": (({"正财", "偏财"}, "财星护食"),),
    "伤官": (({"正印", "偏印"}, "印星制伤"), ({"正财", "偏财"}, "伤官生财")),
    "正印": (({"正官", "七杀"}, "官杀生印"),),
    "偏印": (({"正官", "七杀"}, "官杀生印"),),
}

_MIXED_PAIR = {
    "正官": "七杀", "七杀": "正官",
    "正财": "偏财", "偏财": "正财",
    "正印": "偏印", "偏印": "正印",
    "食神": "伤官", "伤官": "食神",
}

_STATUS_LABELS = {
    "formed": "成格",
    "broken": "破格",
    "rescued": "破而有救",
    "mixed": "混杂",
    "candidate": "候选",
    "rejected": "未通过严格门槛",
}


def _display_pattern_title(pattern: Mapping[str, Any]) -> str:
    name = str(pattern.get("name", ""))
    rescues = set(str(item) for item in pattern.get("rescues", ()))
    status = str(pattern.get("status", ""))
    if name == "伤官" and "印星制伤" in rescues:
        return "伤官配印"
    if name == "伤官" and "伤官生财" in rescues:
        return "伤官生财"
    if name == "七杀" and "食神制杀" in rescues:
        return "食神制杀"
    if name == "七杀" and "印星化杀" in rescues:
        return "杀印相生"
    if name in {"正财", "偏财"} and "食伤生财" in rescues:
        return "食伤生财"
    if name == "食神" and "财星护食" in rescues:
        return "食神生财"
    if name == "正印" and "官杀生印" in rescues:
        return "官印相生"
    if name == "偏印" and "官杀生印" in rescues:
        return "杀印相生"
    if name == "阳刃" and "官杀制比劫" in rescues:
        return "阳刃驾杀"
    if status == "mixed":
        if name in {"正官", "七杀"}:
            return "官杀混杂"
        if name in {"正财", "偏财"}:
            return "财星并透"
        if name in {"正印", "偏印"}:
            return "印星并见"
        if name in {"食神", "伤官"}:
            return "食伤并见"
    return f"{name}格"


def _value(pillar: Mapping[str, Any], key: str) -> str:
    value = pillar.get(key, "")
    if isinstance(value, Mapping):
        value = value.get("value", "")
    return str(value)


def _pillar_by_label(pillars: list[Mapping[str, Any]], label: str, fallback: int) -> Mapping[str, Any]:
    return next((pillar for pillar in pillars if str(pillar.get("label", "")) == label), pillars[fallback])


@dataclass(frozen=True)
class _ChartFacts:
    pillars: tuple[Mapping[str, Any], ...]
    day_stem: str
    day_element: str
    month_branch: str
    month_main_god: str
    branches: tuple[str, ...]
    roots: tuple[str, ...]
    visible_gods: Counter[str]
    god_weights: Counter[str]
    visible_elements: Counter[str]
    element_weights: Counter[str]

    def god_share(self, names: set[str]) -> float:
        total = sum(self.god_weights.values())
        return sum(self.god_weights[name] for name in names) / total if total else 0.0

    def element_share(self, element: str) -> float:
        total = sum(self.element_weights.values())
        return self.element_weights[element] / total if total else 0.0


def _chart_facts(
    pillars: list[Mapping[str, Any]],
    structure: Mapping[str, Any] | None,
) -> _ChartFacts:
    day = _pillar_by_label(pillars, "日", 2)
    month = _pillar_by_label(pillars, "月", 1)
    day_stem = _value(day, "stem")
    day_element = STEM_ELEMENTS[day_stem]
    month_branch = _value(month, "branch")
    visible_gods: Counter[str] = Counter()
    god_weights: Counter[str] = Counter()
    visible_elements: Counter[str] = Counter()
    element_weights: Counter[str] = Counter()
    roots: set[str] = set()
    branches: list[str] = []
    for pillar in pillars:
        label = str(pillar.get("label", ""))
        stem = _value(pillar, "stem")
        branch = _value(pillar, "branch")
        if stem in STEM_ELEMENTS:
            visible_elements[STEM_ELEMENTS[stem]] += 1
            element_weights[STEM_ELEMENTS[stem]] += 3
            if label != "日":
                god = _ten_god(day_stem, stem)
                visible_gods[god] += 1
                god_weights[god] += 3
        if branch not in HIDDEN_STEMS:
            continue
        branches.append(branch)
        for index, hidden_stem in enumerate(HIDDEN_STEMS[branch]):
            weight = 2 if index == 0 else 1
            god_weights[_ten_god(day_stem, hidden_stem)] += weight
            element_weights[STEM_ELEMENTS[hidden_stem]] += weight
            if STEM_ELEMENTS[hidden_stem] == day_element:
                roots.add(label)
    day_master = (structure or {}).get("day_master", {})
    if isinstance(day_master, Mapping):
        roots.update(str(label) for label in day_master.get("root_pillars", ()) if label)
    month_main = HIDDEN_STEMS.get(month_branch, ("",))[0]
    return _ChartFacts(
        pillars=tuple(pillars),
        day_stem=day_stem,
        day_element=day_element,
        month_branch=month_branch,
        month_main_god=_ten_god(day_stem, month_main),
        branches=tuple(branches),
        roots=tuple(sorted(roots)),
        visible_gods=visible_gods,
        god_weights=god_weights,
        visible_elements=visible_elements,
        element_weights=element_weights,
    )


def _evidence(pattern_id: str, kind: str, detail: str, index: int) -> dict[str, str]:
    return {
        "id": f"bazi.pattern.{pattern_id}.{kind}.{index}",
        "kind": kind,
        "detail": detail,
    }


def _god_element(day_stem: str, god: str) -> str:
    if god in {"建禄", "阳刃"}:
        return STEM_ELEMENTS[day_stem]
    return next(
        STEM_ELEMENTS[stem]
        for stem in _STEMS
        if _ten_god(day_stem, stem) == god
    )


def _complete_meeting(branches: Iterable[str], element: str) -> str:
    branch_set = set(branches)
    for group, result_element in (*TRINES, *MEETINGS):
        if result_element == element and set(group) <= branch_set:
            return group
    return ""


def _ordinary_patterns(facts: _ChartFacts) -> list[dict[str, Any]]:
    day_stem = facts.day_stem
    month_branch = facts.month_branch
    month_hidden = HIDDEN_STEMS.get(month_branch, ())
    month_gods = [_ten_god(day_stem, stem) for stem in month_hidden]
    visible = facts.visible_gods
    results: list[dict[str, Any]] = []
    for name in ORDINARY_PATTERN_NAMES:
        pattern_id = _PATTERN_IDS[name]
        if name == "建禄":
            is_candidate = month_branch == _LU_BRANCH[day_stem]
            position = 0
            transparent_god = "比肩"
        elif name == "阳刃":
            is_candidate = month_branch == _YANGREN_BRANCH[day_stem]
            position = 0
            transparent_god = "劫财"
        else:
            is_candidate = name in month_gods
            position = month_gods.index(name) if is_candidate else -1
            transparent_god = name
        evidence: list[dict[str, str]] = []
        if is_candidate:
            evidence.append(_evidence(
                pattern_id,
                "month_command",
                f"月支{month_branch}{'本气' if position == 0 else '藏气'}为{name}。",
                len(evidence) + 1,
            ))
        transparent = is_candidate and visible[transparent_god] > 0
        if transparent:
            evidence.append(_evidence(
                pattern_id,
                "transparent",
                f"{name}在年、月或时干透出。",
                len(evidence) + 1,
            ))
        meeting = _complete_meeting(facts.branches, _god_element(day_stem, name)) if is_candidate else ""
        if meeting:
            evidence.append(_evidence(
                pattern_id,
                "meeting",
                f"地支{meeting}完整合会至{name}五行。",
                len(evidence) + 1,
            ))
        formed = is_candidate and (position == 0 or transparent or bool(meeting))
        constraints = [
            label
            for gods, label in _BREAK_RULES.get(name, ())
            if any(visible[god] for god in gods)
        ] if formed else []
        rescues = [
            label
            for gods, label in _RESCUE_RULES.get(name, ())
            if constraints and any(visible[god] for god in gods)
        ] if formed else []
        if name == "建禄" and formed and any(visible[god] for god in {"正财", "偏财"}) and not any(visible[god] for god in {"正官", "七杀"}):
            constraints.append("比劫见财而无官杀制")
        if name == "阳刃" and formed and not any(visible[god] for god in {"正官", "七杀"}):
            constraints.append("阳刃无制")
        if name in {"建禄", "阳刃"} and constraints and any(visible[god] for god in {"正官", "七杀"}):
            rescues.append("官杀制比劫")
        mixed = formed and visible[_MIXED_PAIR.get(name, "")] > 0
        if mixed:
            status = "mixed"
        elif constraints and rescues:
            status = "rescued"
        elif constraints:
            status = "broken"
        elif formed:
            status = "formed"
        elif is_candidate:
            status = "candidate"
        else:
            status = "not_candidate"
        score = 0
        if is_candidate:
            score = 35 + (20 if position == 0 else 0) + (15 if transparent else 0) + (10 if meeting else 0)
            score -= 20 * bool(constraints)
            score += 12 * bool(rescues)
            score -= 10 * bool(mixed)
        results.append({
            "id": f"bazi.pattern.ordinary.{pattern_id}",
            "name": name,
            "status": status,
            "score": max(0, min(100, score)),
            "evidence": evidence,
            "constraints": constraints,
            "rescues": rescues,
        })
    return results


def _gate_pattern(
    name: str,
    gates: list[tuple[str, bool, str, str]],
) -> dict[str, Any]:
    pattern_id = _PATTERN_IDS[name]
    evidence = [
        {
            **_evidence(pattern_id, "gate", success, index),
            "gate": gate,
        }
        for index, (gate, passed, success, _) in enumerate(gates, start=1)
        if passed
    ]
    constraints = [failure for _, passed, _, failure in gates if not passed]
    formed = not constraints
    passed_count = len(gates) - len(constraints)
    score = min(100, 80 + 2 * len(gates)) if formed else round(70 * passed_count / len(gates))
    return {
        "id": f"bazi.pattern.special.{pattern_id}",
        "name": name,
        "status": "formed" if formed else "rejected",
        "score": score,
        "evidence": evidence,
        "constraints": constraints,
        "rescues": [],
    }


def _follow_pattern(
    facts: _ChartFacts,
    *,
    name: str,
    target_gods: set[str],
    minimum_share: float,
) -> dict[str, Any]:
    support_gods = {"比肩", "劫财", "正印", "偏印"}
    target_share = facts.god_share(target_gods)
    target_visible = sum(facts.visible_gods[god] for god in target_gods)
    support_weight = sum(facts.god_weights[god] for god in support_gods)
    gates = [
        (
            "month_command",
            facts.month_main_god in target_gods,
            f"月令本气落在{'/'.join(sorted(target_gods))}。",
            "月令本气不在目标十神组。",
        ),
        (
            "dominance",
            target_share >= minimum_share,
            f"目标十神加权占比为{target_share:.3f}。",
            f"目标十神占比{target_share:.3f}未达严格门槛{minimum_share:.2f}。",
        ),
        (
            "visible_target",
            target_visible > 0,
            "目标十神至少一位明透。",
            "目标十神未见明透。",
        ),
        (
            "no_root",
            not facts.roots,
            "日主在四支不见同类根气。",
            f"日主有根（{'、'.join(facts.roots)}柱），不作{name}。",
        ),
        (
            "no_support",
            support_weight == 0,
            "原局不见比劫印星回扶日主。",
            "原局仍见比劫或印星回扶日主。",
        ),
    ]
    return _gate_pattern(name, gates)


def _prosperous_pattern(facts: _ChartFacts, *, strong: bool) -> dict[str, Any]:
    name = "从强" if strong else "从旺"
    peer_gods = {"比肩", "劫财"}
    resource_gods = {"正印", "偏印"}
    opposing_gods = {"食神", "伤官", "正财", "偏财", "正官", "七杀"}
    support_share = facts.god_share(peer_gods | resource_gods)
    resource_visible = sum(facts.visible_gods[god] for god in resource_gods)
    peer_visible = sum(facts.visible_gods[god] for god in peer_gods)
    opposing_visible = sum(facts.visible_gods[god] for god in opposing_gods)
    if strong:
        gates = [
            ("month_command", facts.month_main_god in peer_gods | resource_gods, "月令本气为比劫或印星。", "月令不在比劫印星支持组。"),
            ("support_dominance", support_share >= 0.80, f"比劫印星加权占比为{support_share:.3f}。", f"比劫印星占比{support_share:.3f}未达0.80。"),
            ("resource_visible", resource_visible > 0, "印星明透，按从强分型。", "印星未明透，不满足从强分型。"),
            ("rooted", len(facts.roots) >= 1, f"日主在{'、'.join(facts.roots)}柱有根。", "日主无根，不能作从强。"),
            ("no_opposition", opposing_visible == 0, "食伤财官未见明透逆势。", "食伤财官仍有明透，不作从强。"),
        ]
    else:
        gates = [
            ("month_command", facts.month_main_god in peer_gods, "月令本气为比劫。", "月令本气不是比劫。"),
            ("same_element_dominance", facts.element_share(facts.day_element) >= 0.70, f"日主同类五行占比为{facts.element_share(facts.day_element):.3f}。", "日主同类五行未达0.70。"),
            ("peer_visible", peer_visible >= 2, "比劫至少两位明透。", "比劫明透不足两位。"),
            ("rooted", len(facts.roots) >= 2, f"日主在{'、'.join(facts.roots)}柱多重通根。", "日主根气不足两柱。"),
            ("pure_peer", resource_visible == 0 and opposing_visible == 0, "印星与异党均未明透，按从旺分型。", "仍有印星或异党明透，不作纯从旺。"),
        ]
    return _gate_pattern(name, gates)


_EXCLUSIVE_SPECS: dict[str, tuple[str, str, tuple[str, ...]]] = {
    "曲直": ("木", "寅卯辰", ("亥卯未", "寅卯辰")),
    "炎上": ("火", "巳午未", ("寅午戌", "巳午未")),
    "稼穑": ("土", "辰戌丑未", ()),
    "从革": ("金", "申酉戌", ("巳酉丑", "申酉戌")),
    "润下": ("水", "亥子丑", ("申子辰", "亥子丑")),
}


def _controller_of(element: str) -> str:
    return next(controller for controller, target in ELEMENT_CONTROLS.items() if target == element)


def _exclusive_pattern(facts: _ChartFacts, name: str) -> dict[str, Any]:
    element, seasonal_branches, complete_groups = _EXCLUSIVE_SPECS[name]
    branch_set = set(facts.branches)
    if element == "土":
        group_complete = len(branch_set & set("辰戌丑未")) >= 3
        group_detail = "四季土支至少见三类"
    else:
        matched_group = next((group for group in complete_groups if set(group) <= branch_set), "")
        group_complete = bool(matched_group)
        group_detail = f"地支成{matched_group}" if matched_group else ""
    controller = _controller_of(element)
    controller_share = facts.element_share(controller)
    controller_quiet = facts.visible_elements[controller] == 0 and controller_share <= 0.15
    dominance = facts.element_share(element)
    gates = [
        ("day_element", facts.day_element == element, f"日主五行为{element}。", f"日主不是{element}，不入{name}。"),
        ("season", facts.month_branch in seasonal_branches, f"月支{facts.month_branch}在{element}旺令门槛内。", f"月支{facts.month_branch}不在{element}旺令门槛内。"),
        ("complete_group", group_complete, group_detail, "地支未成严格三合/三会或专土门槛。"),
        ("dominance", dominance >= 0.68, f"{element}加权占比为{dominance:.3f}。", f"{element}占比{dominance:.3f}未达0.68。"),
        ("no_controller", controller_quiet, f"克制五行{controller}未明透且占比低。", f"克制五行{controller}明透或占比过高。"),
    ]
    return _gate_pattern(name, gates)


def _special_patterns(facts: _ChartFacts) -> list[dict[str, Any]]:
    return [
        _follow_pattern(facts, name="从财", target_gods={"正财", "偏财"}, minimum_share=0.60),
        _follow_pattern(facts, name="从杀", target_gods={"正官", "七杀"}, minimum_share=0.70),
        _follow_pattern(facts, name="从儿", target_gods={"食神", "伤官"}, minimum_share=0.70),
        _prosperous_pattern(facts, strong=False),
        _prosperous_pattern(facts, strong=True),
        *(_exclusive_pattern(facts, name) for name in ("曲直", "炎上", "稼穑", "从革", "润下")),
    ]


def assess_patterns(
    pillars: Iterable[Mapping[str, Any]],
    structure: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Assess deterministic month-command patterns without making fortune claims."""

    pillar_list = list(pillars)
    day = next((pillar for pillar in pillar_list if str(pillar.get("label", "")) == "日"), None)
    month = next((pillar for pillar in pillar_list if str(pillar.get("label", "")) == "月"), None)
    essential_valid = all(
        pillar is not None
        and _value(pillar, "stem") in STEM_ELEMENTS
        and _value(pillar, "branch") in HIDDEN_STEMS
        for pillar in (month, day)
    )
    valid = [
        pillar for pillar in pillar_list
        if _value(pillar, "stem") in STEM_ELEMENTS and _value(pillar, "branch") in HIDDEN_STEMS
    ]
    if not essential_valid or len(valid) < 3:
        return {
            "rules_version": PATTERN_RULES_VERSION,
            "method": "month-command-strict-gates-v1",
            "primary": None,
            "ordinary": [],
            "special": [],
            "formed": [],
            "evidence": [],
        }
    facts = _chart_facts(valid, structure)
    ordinary = _ordinary_patterns(facts)
    special = _special_patterns(facts)
    ordinary_active = [item for item in ordinary if item["status"] in {"formed", "broken", "rescued", "mixed"}]
    special_active = [item for item in special if item["status"] == "formed"]
    active = ordinary_active + special_active
    pattern_order = (*ORDINARY_PATTERN_NAMES, *SPECIAL_PATTERN_NAMES)
    best = max(active, key=lambda item: (item["score"], -pattern_order.index(item["name"])), default=None)
    primary = None
    if best:
        title = _display_pattern_title(best)
        status_label = _STATUS_LABELS.get(best["status"], best["status"])
        primary = {
            "id": best["id"],
            "name": best["name"],
            "title": title,
            "status": best["status"],
            "summary": f"{title} · {status_label}。月令、透干与救应关系共同形成这张命盘的主导结构。",
            "strength": best["score"],
            "evidence_ids": [item["id"] for item in best["evidence"]],
            "constraints": list(best["constraints"]),
            "rescues": list(best["rescues"]),
        }
    all_evidence = [
        evidence
        for pattern in (*ordinary, *special)
        for evidence in pattern["evidence"]
    ]
    return {
        "rules_version": PATTERN_RULES_VERSION,
        "method": "month-command-strict-gates-v1",
        "primary": primary,
        "ordinary": ordinary,
        "special": special,
        "formed": [item["id"] for item in active if item["status"] in {"formed", "rescued"}],
        "evidence": all_evidence,
    }
