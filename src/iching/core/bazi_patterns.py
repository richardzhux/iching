from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from iching.core.bazi_rules.adapter import (
    build_source_backed_shadow,
    fact_graph_matches_pillars,
)
from iching.core.bazi_rules.fact_graph import build_bazi_fact_graph
from iching.core.bazi_rules.schema import BaziFactGraph
from iching.core.bazi_structure import (
    BRANCH_CLASHES,
    ELEMENT_CONTROLS,
    HIDDEN_STEMS,
    MEETINGS,
    STEM_ELEMENTS,
    TRINES,
    _ten_god,
)


PATTERN_RULES_VERSION = "bazi-patterns-2026.07-v2"

ORDINARY_PATTERN_NAMES = (
    "正官", "七杀", "正财", "偏财", "食神", "伤官", "正印", "偏印", "建禄", "月劫", "阳刃",
)
SPECIAL_PATTERN_NAMES = (
    "从财", "从杀", "从儿", "从旺", "从强", "曲直", "炎上", "稼穑", "从革", "润下",
)

_STEMS = "甲乙丙丁戊己庚辛壬癸"
_BRANCHES = "子丑寅卯辰巳午未申酉戌亥"

_LU_BRANCH = dict(zip(_STEMS, ("寅", "卯", "巳", "午", "巳", "午", "申", "酉", "亥", "子")))
_YANG_STEMS = frozenset("甲丙戊庚壬")
_YANGREN_BRANCH = {"甲": "卯", "丙": "午", "戊": "午", "庚": "酉", "壬": "子"}

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
    "月劫": "month_robbery",
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

_HIDDEN_TENSION_LABELS = {
    "伤官见官": "伤官藏见，与官星形成局部牵动",
    "财星生杀而无制": "财星藏见，对七杀形成潜在生助",
    "比劫夺财": "比劫藏见，与财星形成资源竞争",
    "枭印夺食": "偏印藏见，对食神形成局部牵制",
    "财星坏印": "财星藏见，对印星形成局部牵制",
}

_COUNTERPART = {
    "正官": "七杀", "七杀": "正官",
    "正财": "偏财", "偏财": "正财",
    "正印": "偏印", "偏印": "正印",
    "食神": "伤官", "伤官": "食神",
}

_FORMATION_PATH_SPECS: dict[str, tuple[tuple[str, str, tuple[frozenset[str], ...]], ...]] = {
    "正官": (
        ("officer_wealth", "官逢财生", (frozenset({"正财", "偏财"}),)),
        ("officer_resource", "官星佩印", (frozenset({"正印", "偏印"}),)),
        ("officer_wealth_resource", "财印相辅", (frozenset({"正财", "偏财"}), frozenset({"正印", "偏印"}))),
    ),
    "七杀": (
        ("killing_food", "食神制杀", (frozenset({"食神"}),)),
        ("killing_resource", "杀印相生", (frozenset({"正印", "偏印"}),)),
        ("killing_output", "伤官制杀", (frozenset({"伤官"}),)),
    ),
    "正财": (
        ("wealth_output", "食伤生财", (frozenset({"食神", "伤官"}),)),
        ("wealth_officer", "财旺生官", (frozenset({"正官", "七杀"}),)),
        ("wealth_resource", "财格佩印", (frozenset({"正印", "偏印"}),)),
    ),
    "偏财": (
        ("wealth_output", "食伤生财", (frozenset({"食神", "伤官"}),)),
        ("wealth_officer", "财旺生官", (frozenset({"正官", "七杀"}),)),
        ("wealth_resource", "财格佩印", (frozenset({"正印", "偏印"}),)),
    ),
    "正印": (
        ("resource_output", "印用食伤", (frozenset({"食神", "伤官"}),)),
        ("resource_officer", "官印相生", (frozenset({"正官"}),)),
        ("resource_killing", "杀印相生", (frozenset({"七杀"}),)),
        ("resource_peer", "印绶护身", (frozenset({"比肩", "劫财"}),)),
    ),
    "偏印": (
        ("resource_output", "印用食伤", (frozenset({"食神", "伤官"}),)),
        ("resource_killing", "偏印化杀", (frozenset({"七杀"}),)),
        ("resource_officer", "官印相生", (frozenset({"正官"}),)),
        ("resource_peer", "印绶护身", (frozenset({"比肩", "劫财"}),)),
    ),
    "食神": (
        ("food_wealth", "食神生财", (frozenset({"正财", "偏财"}),)),
        ("food_killing", "食神制杀", (frozenset({"七杀"}),)),
        ("food_peer", "食神吐秀", (frozenset({"比肩", "劫财", "正印", "偏印"}),)),
    ),
    "伤官": (
        ("output_wealth", "伤官生财", (frozenset({"正财", "偏财"}),)),
        ("output_resource", "伤官配印", (frozenset({"正印", "偏印"}),)),
        ("output_killing", "伤官制杀", (frozenset({"七杀"}),)),
    ),
    "建禄": (
        ("prosperity_officer", "建禄用官", (frozenset({"正官"}),)),
        ("prosperity_killing", "建禄用杀", (frozenset({"七杀"}),)),
        ("prosperity_wealth", "建禄用财", (frozenset({"正财", "偏财"}),)),
        ("prosperity_output", "建禄用食伤", (frozenset({"食神", "伤官"}),)),
    ),
    "月劫": (
        ("robbery_officer", "月劫用官", (frozenset({"正官"}),)),
        ("robbery_killing", "月劫用杀", (frozenset({"七杀"}),)),
        ("robbery_wealth", "月劫用财", (frozenset({"正财", "偏财"}),)),
        ("robbery_output", "月劫用食伤", (frozenset({"食神", "伤官"}),)),
    ),
    "阳刃": (
        ("blade_officer", "阳刃用官", (frozenset({"正官"}),)),
        ("blade_killing", "阳刃驾杀", (frozenset({"七杀"}),)),
        ("blade_resource", "刃印相资", (frozenset({"正印", "偏印"}),)),
        ("blade_output", "阳刃泄秀", (frozenset({"食神", "伤官"}),)),
        ("blade_wealth_officer", "财官制刃", (frozenset({"正财", "偏财"}), frozenset({"正官", "七杀"}))),
    ),
}

_STATUS_LABELS = {
    "formed": "成格",
    "broken": "破格",
    "rescued": "破而有救",
    "mixed": "混杂",
    "candidate": "候选",
    "rejected": "未通过严格门槛",
    "not_candidate": "未取格",
}


def _display_pattern_title(pattern: Mapping[str, Any]) -> str:
    name = str(pattern.get("name", ""))
    return f"{name}格"


def _value(pillar: Mapping[str, Any], key: str) -> str:
    value = pillar.get(key, "")
    if isinstance(value, Mapping):
        value = value.get("value", "")
    return str(value)


def _pillar_by_label(pillars: list[Mapping[str, Any]], label: str, fallback: int) -> Mapping[str, Any]:
    return next((pillar for pillar in pillars if str(pillar.get("label", "")) == label), pillars[fallback])


@dataclass(frozen=True)
class _GodOccurrence:
    god: str
    pillar: str
    stem: str
    branch: str
    exposed: bool
    qi_level: str
    clashed: bool
    weight: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "god": self.god,
            "pillar": self.pillar,
            "stem": self.stem,
            "branch": self.branch,
            "exposed": self.exposed,
            "qi_level": self.qi_level,
            "clashed": self.clashed,
            "weight": round(self.weight, 2),
        }


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
    god_occurrences: Mapping[str, tuple[_GodOccurrence, ...]]

    def god_share(self, names: set[str]) -> float:
        total = sum(self.god_weights.values())
        return sum(self.god_weights[name] for name in names) / total if total else 0.0

    def element_share(self, element: str) -> float:
        total = sum(self.element_weights.values())
        return self.element_weights[element] / total if total else 0.0

    def occurrences(self, names: Iterable[str]) -> tuple[_GodOccurrence, ...]:
        return tuple(
            occurrence
            for name in names
            for occurrence in self.god_occurrences.get(name, ())
        )

    def effective_weight(self, names: Iterable[str]) -> float:
        return sum(occurrence.weight for occurrence in self.occurrences(names))

    def has_effective(self, names: Iterable[str]) -> bool:
        return self.effective_weight(names) >= 0.75

    def has_exposed(self, names: Iterable[str]) -> bool:
        return any(occurrence.exposed for occurrence in self.occurrences(names))

    def presence_detail(self, names: Iterable[str]) -> str:
        occurrences = sorted(
            self.occurrences(names),
            key=lambda item: (-item.weight, not item.exposed, item.pillar),
        )
        details: list[str] = []
        for occurrence in occurrences[:4]:
            if occurrence.exposed:
                details.append(f"{occurrence.pillar}干{occurrence.stem}{occurrence.god}透出")
            else:
                qi = {"main": "本气", "secondary": "中气", "residual": "余气"}.get(occurrence.qi_level, "藏气")
                clash = "、受冲而仍参与" if occurrence.clashed else ""
                details.append(f"{occurrence.pillar}支{occurrence.branch}藏{occurrence.stem}{occurrence.god}（{qi}{clash}）")
        return "；".join(details)

    def effective_god_summary(self) -> dict[str, Any]:
        return {
            god: {
                "present": self.has_effective({god}),
                "exposed": self.has_exposed({god}),
                "effective_weight": round(self.effective_weight({god}), 2),
                "locations": [occurrence.as_dict() for occurrence in occurrences],
            }
            for god, occurrences in sorted(self.god_occurrences.items())
        }


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
    god_occurrences: dict[str, list[_GodOccurrence]] = {}
    roots: set[str] = set()
    branches: list[str] = []
    branch_by_label = {
        str(pillar.get("label", "")): _value(pillar, "branch")
        for pillar in pillars
        if _value(pillar, "branch") in HIDDEN_STEMS
    }
    clashed_labels = {
        label
        for label, branch in branch_by_label.items()
        if any(
            other_label != label and frozenset((branch, other_branch)) in BRANCH_CLASHES
            for other_label, other_branch in branch_by_label.items()
        )
    }
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
                god_occurrences.setdefault(god, []).append(_GodOccurrence(
                    god=god,
                    pillar=label,
                    stem=stem,
                    branch=branch,
                    exposed=True,
                    qi_level="visible",
                    clashed=False,
                    weight=3.0,
                ))
        if branch not in HIDDEN_STEMS:
            continue
        branches.append(branch)
        for index, hidden_stem in enumerate(HIDDEN_STEMS[branch]):
            base_weight = 2.0 if index == 0 else 1.2 if index == 1 else 0.8
            month_bonus = 1.5 if label == "月" and index == 0 else 0.0
            clash_factor = 0.68 if label in clashed_labels else 1.0
            effective_weight = (base_weight + month_bonus) * clash_factor
            god = _ten_god(day_stem, hidden_stem)
            god_weights[god] += base_weight
            element_weights[STEM_ELEMENTS[hidden_stem]] += base_weight
            god_occurrences.setdefault(god, []).append(_GodOccurrence(
                god=god,
                pillar=label,
                stem=hidden_stem,
                branch=branch,
                exposed=False,
                qi_level="main" if index == 0 else "secondary" if index == 1 else "residual",
                clashed=label in clashed_labels,
                weight=effective_weight,
            ))
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
        god_occurrences={god: tuple(occurrences) for god, occurrences in god_occurrences.items()},
    )


def _evidence(pattern_id: str, kind: str, detail: str, index: int) -> dict[str, str]:
    return {
        "id": f"bazi.pattern.{pattern_id}.{kind}.{index}",
        "kind": kind,
        "detail": detail,
    }


def _god_element(day_stem: str, god: str) -> str:
    if god in {"建禄", "月劫", "阳刃"}:
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


def _selection_for_candidate(position: int, transparent: bool, meeting: str) -> str:
    if position == 0:
        return "month_main_qi"
    if transparent:
        return "month_hidden_exposed"
    if meeting:
        return "month_meeting"
    return "month_hidden_only"


def _formation_paths(name: str, facts: _ChartFacts) -> list[dict[str, Any]]:
    paths: list[dict[str, Any]] = []
    for path_id, title, requirement_groups in _FORMATION_PATH_SPECS.get(name, ()):
        if not all(facts.has_effective(group) for group in requirement_groups):
            continue
        evidence_weight = sum(facts.effective_weight(group) for group in requirement_groups)
        exposure_bonus = sum(1.5 for group in requirement_groups if facts.has_exposed(group))
        details = [facts.presence_detail(group) for group in requirement_groups]
        paths.append({
            "id": path_id,
            "title": title,
            "evidence_weight": round(evidence_weight + exposure_bonus, 2),
            "details": [detail for detail in details if detail],
        })
    # Registry order expresses the classical formation-path priority. Keep
    # composite paths as additional evidence rather than letting a larger
    # count mechanically outrank the simpler controlling path.
    return paths


def _trigger_is_direct(facts: _ChartFacts, gods: set[str]) -> bool:
    if facts.has_exposed(gods):
        return True
    return any(
        _complete_meeting(facts.branches, _god_element(facts.day_stem, god))
        for god in gods
    )


def _damage_rescue_and_tension(
    name: str,
    facts: _ChartFacts,
) -> tuple[list[str], list[str], list[str]]:
    constraints: list[str] = []
    rescues: list[str] = []
    tensions: list[str] = []
    for gods, label in _BREAK_RULES.get(name, ()):
        if _trigger_is_direct(facts, gods):
            constraints.append(label)
        elif facts.has_effective(gods):
            tensions.append(_HIDDEN_TENSION_LABELS.get(label, f"{label.replace('而无制', '')}藏见，形成局部牵制"))
    if constraints:
        for gods, label in _RESCUE_RULES.get(name, ()):
            if facts.has_effective(gods):
                rescues.append(label)
    officer_gods = {"正官", "七杀"}
    if name == "建禄" and facts.has_effective({"正财", "偏财"}) and not facts.has_effective(officer_gods):
        tensions.append("比劫与财星同见，资源取得更依赖经营与边界")
    if name == "月劫" and facts.has_effective({"正财", "偏财"}) and not facts.has_effective(officer_gods):
        tensions.append("月劫见财而官杀不显，财务结构更强调竞争与协作边界")
    if name == "阳刃" and not facts.has_effective(officer_gods):
        constraints.append("阳刃未见有效官杀制化")
    elif name == "阳刃" and not facts.has_exposed(officer_gods):
        officer_clashed = any(occurrence.clashed for occurrence in facts.occurrences(officer_gods))
        tensions.append(
            "官杀藏支参与制刃，虽未透干仍属有效；制刃支受冲，结构伴随冲战"
            if officer_clashed
            else "官杀藏支参与制刃，虽未透干仍属有效"
        )
    return list(dict.fromkeys(constraints)), list(dict.fromkeys(rescues)), list(dict.fromkeys(tensions))


def _purity(name: str, facts: _ChartFacts) -> tuple[str, bool]:
    counterpart = _COUNTERPART.get(name)
    if not counterpart or not facts.has_effective({counterpart}):
        return "clear", False
    if name in {"正官", "七杀"} and facts.has_exposed({name}) and facts.has_exposed({counterpart}):
        return "mixed", True
    return "combined", False


def _pattern_strength(name: str, facts: _ChartFacts, position: int, transparent: bool) -> str:
    target_god = "比肩" if name == "建禄" else "劫财" if name in {"月劫", "阳刃"} else name
    weight = facts.effective_weight({target_god})
    if position == 0 and (transparent or weight >= 4.0):
        return "effective"
    if position == 0 or transparent or weight >= 2.0:
        return "ordinary"
    return "weak"


def _ordinary_patterns(facts: _ChartFacts) -> list[dict[str, Any]]:
    day_stem = facts.day_stem
    month_branch = facts.month_branch
    month_hidden = HIDDEN_STEMS.get(month_branch, ())
    month_gods = [_ten_god(day_stem, stem) for stem in month_hidden]
    results: list[dict[str, Any]] = []
    for name in ORDINARY_PATTERN_NAMES:
        pattern_id = _PATTERN_IDS[name]
        if name == "建禄":
            is_candidate = month_branch == _LU_BRANCH[day_stem]
            position = 0
            transparent_god = "比肩"
        elif name == "月劫":
            is_candidate = facts.month_main_god == "劫财" and not (
                day_stem in _YANG_STEMS and month_branch == _YANGREN_BRANCH.get(day_stem)
            )
            position = 0
            transparent_god = "劫财"
        elif name == "阳刃":
            is_candidate = day_stem in _YANG_STEMS and month_branch == _YANGREN_BRANCH.get(day_stem)
            position = 0
            transparent_god = "劫财"
        else:
            raw_candidate = name in month_gods
            position = month_gods.index(name) if raw_candidate else -1
            transparent_god = name
            hidden_exposed = raw_candidate and facts.has_exposed({name})
            hidden_meeting = _complete_meeting(facts.branches, _god_element(day_stem, name)) if raw_candidate else ""
            is_candidate = raw_candidate and (position == 0 or hidden_exposed or bool(hidden_meeting))
        evidence: list[dict[str, str]] = []
        if is_candidate:
            evidence.append(_evidence(
                pattern_id,
                "month_command",
                f"月支{month_branch}{'本气' if position == 0 else '藏气'}为{name}。",
                len(evidence) + 1,
            ))
        transparent = is_candidate and facts.has_exposed({transparent_god})
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
        selection = _selection_for_candidate(position, transparent, meeting) if is_candidate else "not_selected"
        paths = _formation_paths(name, facts) if is_candidate else []
        formation_path = paths[0] if paths else None
        formed = is_candidate and formation_path is not None
        constraints, rescues, tensions = _damage_rescue_and_tension(name, facts) if is_candidate else ([], [], [])
        purity, mixed = _purity(name, facts) if is_candidate else ("clear", False)
        for path in paths:
            details = "；".join(path["details"])
            evidence.append(_evidence(
                pattern_id,
                "formation_path",
                f"{path['title']}：{details}" if details else str(path["title"]),
                len(evidence) + 1,
            ))
        for tension in tensions:
            evidence.append(_evidence(pattern_id, "tension", tension, len(evidence) + 1))
        if mixed:
            status = "mixed"
        elif formed and constraints and rescues:
            status = "rescued"
        elif formed and constraints:
            status = "broken"
        elif formed:
            status = "formed"
        elif is_candidate:
            status = "candidate"
        else:
            status = "not_candidate"
        integrity = "broken" if constraints and not rescues else "rescued" if constraints else "minor_damage" if tensions else "complete"
        rescue_state = "effective" if constraints and rescues else "none"
        results.append({
            "id": f"bazi.pattern.ordinary.{pattern_id}",
            "name": name,
            "status": status,
            "selection": selection,
            "formation": "formed" if formed else "candidate" if is_candidate else "not_selected",
            "formation_path": formation_path,
            "formation_paths": paths,
            "integrity": integrity,
            "rescue": rescue_state,
            "purity": purity,
            "strength": _pattern_strength(name, facts, position, transparent) if is_candidate else "none",
            "authenticity": "regular",
            "role": "candidate" if is_candidate else "none",
            "evidence": evidence,
            "constraints": constraints,
            "rescues": rescues,
            "tensions": tensions,
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
    return {
        "id": f"bazi.pattern.special.{pattern_id}",
        "name": name,
        "status": "formed" if formed else "rejected",
        "selection": "strict_special_gates" if formed else "rejected",
        "formation": "formed" if formed else "rejected",
        "formation_path": None,
        "formation_paths": [],
        "integrity": "complete" if formed else "not_applicable",
        "rescue": "none",
        "purity": "clear" if formed else "not_applicable",
        "strength": "effective" if formed else "none",
        "authenticity": "strict" if formed else "rejected",
        "role": "special_candidate" if formed else "none",
        "evidence": evidence,
        "constraints": constraints,
        "rescues": [],
        "tensions": [],
        "hard_gates": [
            {"id": gate, "passed": passed, "success": success, "failure": failure}
            for gate, passed, success, failure in gates
        ],
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


def _assess_patterns_legacy(
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
            "method": "effective-structure-month-patterns-v2",
            "primary": None,
            "ordinary": [],
            "special": [],
            "formed": [],
            "evidence": [],
            "effective_structure": {},
        }
    facts = _chart_facts(valid, structure)
    ordinary = _ordinary_patterns(facts)
    special = _special_patterns(facts)
    ordinary_active = [item for item in ordinary if item["status"] in {"formed", "broken", "rescued", "mixed", "candidate"}]
    special_active = [item for item in special if item["status"] == "formed"]
    selection_order = {
        "month_main_qi": 0,
        "month_hidden_exposed": 1,
        "month_meeting": 2,
        "month_hidden_only": 3,
    }
    status_order = {"formed": 0, "rescued": 1, "mixed": 2, "broken": 3, "candidate": 4}
    ordinary_primary = min(
        ordinary_active,
        key=lambda item: (
            selection_order.get(str(item.get("selection", "")), 9),
            status_order.get(str(item.get("status", "")), 9),
            ORDINARY_PATTERN_NAMES.index(str(item["name"])),
        ),
        default=None,
    )
    # Strict special structures supersede the ordinary month pattern only
    # after every hard gate has passed. Otherwise the month-command pattern
    # remains primary and the special structure stays diagnostic only.
    best = special_active[0] if special_active else ordinary_primary
    primary = None
    if best:
        best["role"] = "primary"
        title = _display_pattern_title(best)
        status_label = _STATUS_LABELS.get(best["status"], best["status"])
        formation_path = best.get("formation_path")
        path_title = str(formation_path.get("title", "")) if isinstance(formation_path, Mapping) else ""
        selection_label = {
            "month_main_qi": "月令本气取格",
            "month_hidden_exposed": "月令藏气透干取格",
            "month_meeting": "月令藏气因合会取格",
            "strict_special_gates": "特殊格严格门槛成立",
        }.get(str(best.get("selection", "")), "月令候选")
        summary_parts = [selection_label]
        if path_title:
            summary_parts.append(f"成格路径为{path_title}")
        if best.get("tensions"):
            summary_parts.append("存在局部牵制")
        primary = {
            "id": best["id"],
            "name": best["name"],
            "title": title,
            "status": best["status"],
            "summary": f"{title} · {status_label}。{'；'.join(summary_parts)}。",
            "selection": best.get("selection"),
            "formation": best.get("formation"),
            "formation_path": formation_path,
            "integrity": best.get("integrity"),
            "rescue": best.get("rescue"),
            "purity": best.get("purity"),
            "strength": best.get("strength"),
            "authenticity": best.get("authenticity"),
            "role": "primary",
            "evidence_ids": [item["id"] for item in best["evidence"]],
            "constraints": list(best["constraints"]),
            "rescues": list(best["rescues"]),
            "tensions": list(best.get("tensions", ())),
        }
    all_evidence = [
        evidence
        for pattern in (*ordinary, *special)
        for evidence in pattern["evidence"]
    ]
    return {
        "rules_version": PATTERN_RULES_VERSION,
        "method": "effective-structure-month-patterns-v2",
        "primary": primary,
        "ordinary": ordinary,
        "special": special,
        "formed": [item["id"] for item in (*ordinary, *special) if item["status"] in {"formed", "rescued"}],
        "evidence": all_evidence,
        "effective_structure": facts.effective_god_summary(),
        "source_refs": [
            "三命通会·卷六·论阳刃/论建禄/论杂气",
            "渊海子平·神趣八法及月令取用",
        ],
    }


def assess_patterns(
    pillars: Iterable[Mapping[str, Any]],
    structure: Mapping[str, Any] | None,
    *,
    fact_graph: BaziFactGraph | None = None,
    include_attestations: bool = True,
) -> dict[str, Any]:
    """Preserve legacy pattern output and attach a non-authoritative shadow."""

    pillar_list = list(pillars)
    legacy = _assess_patterns_legacy(pillar_list, structure)
    complete = len(pillar_list) == 4 and all(
        _value(pillar, "stem") in STEM_ELEMENTS
        and _value(pillar, "branch") in HIDDEN_STEMS
        and _STEMS.index(_value(pillar, "stem")) % 2
        == _BRANCHES.index(_value(pillar, "branch")) % 2
        for pillar in pillar_list
    )
    if not complete:
        return legacy
    if fact_graph is None:
        try:
            graph = build_bazi_fact_graph(pillar_list)
        except (TypeError, ValueError):
            return legacy
    else:
        graph = fact_graph
        if not fact_graph_matches_pillars(pillar_list, graph):
            return legacy
    legacy["source_backed_shadow"] = build_source_backed_shadow(
        pillar_list,
        legacy,
        graph,
        include_attestations=include_attestations,
    )
    return legacy
