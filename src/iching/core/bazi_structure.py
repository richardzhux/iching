from __future__ import annotations

from collections import Counter
from itertools import combinations
from typing import Any, Iterable, Mapping


ELEMENTS = ("木", "火", "土", "金", "水")
ELEMENT_GENERATES = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
ELEMENT_CONTROLS = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}
STEM_ELEMENTS = dict(zip("甲乙丙丁戊己庚辛壬癸", ("木", "木", "火", "火", "土", "土", "金", "金", "水", "水")))
BRANCH_ELEMENTS = dict(zip("子丑寅卯辰巳午未申酉戌亥", ("水", "土", "木", "木", "土", "火", "火", "土", "金", "金", "土", "水")))
HIDDEN_STEMS = {
    "子": ("癸",), "丑": ("己", "癸", "辛"), "寅": ("甲", "丙", "戊"), "卯": ("乙",),
    "辰": ("戊", "乙", "癸"), "巳": ("丙", "戊", "庚"), "午": ("丁", "己"),
    "未": ("己", "丁", "乙"), "申": ("庚", "壬", "戊"), "酉": ("辛",),
    "戌": ("戊", "辛", "丁"), "亥": ("壬", "甲"),
}

STEM_COMBINATIONS = {
    frozenset(("甲", "己")): "土", frozenset(("乙", "庚")): "金",
    frozenset(("丙", "辛")): "水", frozenset(("丁", "壬")): "木",
    frozenset(("戊", "癸")): "火",
}
STEM_CLASHES = {frozenset(pair) for pair in (("甲", "庚"), ("乙", "辛"), ("丙", "壬"), ("丁", "癸"))}
BRANCH_COMBINATIONS = {
    frozenset(("子", "丑")): "土", frozenset(("寅", "亥")): "木",
    frozenset(("卯", "戌")): "火", frozenset(("辰", "酉")): "金",
    frozenset(("巳", "申")): "水", frozenset(("午", "未")): None,
}
BRANCH_CLASHES = {frozenset(pair) for pair in (("子", "午"), ("丑", "未"), ("寅", "申"), ("卯", "酉"), ("辰", "戌"), ("巳", "亥"))}
BRANCH_HARMS = {frozenset(pair) for pair in (("子", "未"), ("丑", "午"), ("寅", "巳"), ("卯", "辰"), ("申", "亥"), ("酉", "戌"))}
BRANCH_BREAKS = {frozenset(pair) for pair in (("子", "酉"), ("丑", "辰"), ("寅", "亥"), ("卯", "午"), ("巳", "申"), ("未", "戌"))}
TRINES = (("申子辰", "水"), ("亥卯未", "木"), ("寅午戌", "火"), ("巳酉丑", "金"))
MEETINGS = (("亥子丑", "水"), ("寅卯辰", "木"), ("巳午未", "火"), ("申酉戌", "金"))

THEME_ORDER = ("事业", "财富", "感情", "健康")
THEME_POSSIBLE_FAMILIES = {"事业": 7, "财富": 6, "感情": 6, "健康": 6}
TOPIC_TO_THEME = {"career": "事业", "wealth": "财富", "relationship": "感情", "health": "健康"}


def element_relation(day_element: str, other_element: str) -> str:
    if day_element == other_element:
        return "同我"
    if ELEMENT_GENERATES[other_element] == day_element:
        return "生我"
    if ELEMENT_GENERATES[day_element] == other_element:
        return "我生"
    if ELEMENT_CONTROLS[day_element] == other_element:
        return "我克"
    return "克我"


def _ten_god(day_stem: str, other_stem: str) -> str:
    stems = "甲乙丙丁戊己庚辛壬癸"
    day_element = ELEMENTS.index(STEM_ELEMENTS[day_stem])
    other_element = ELEMENTS.index(STEM_ELEMENTS[other_stem])
    same_polarity = stems.index(day_stem) % 2 == stems.index(other_stem) % 2
    relation = (other_element - day_element) % 5
    if relation == 0:
        return "比肩" if same_polarity else "劫财"
    if relation == 1:
        return "食神" if same_polarity else "伤官"
    if relation == 2:
        return "偏财" if same_polarity else "正财"
    if relation == 3:
        return "七杀" if same_polarity else "正官"
    return "偏印" if same_polarity else "正印"


def _participant(pillar: Mapping[str, Any], *, layer: str, value: str, day_stem: str) -> dict[str, str]:
    element = STEM_ELEMENTS[value] if layer != "branch" else BRANCH_ELEMENTS[value]
    stem_for_ten_god = value if value in STEM_ELEMENTS else HIDDEN_STEMS[value][0]
    return {
        "pillar": str(pillar.get("label", "")),
        "layer": layer,
        "value": value,
        "element": element,
        "day_master_relation": element_relation(STEM_ELEMENTS[day_stem], element),
        "ten_god": "日主" if pillar.get("label") == "日" and layer == "stem" else _ten_god(day_stem, stem_for_ten_god),
    }


def layered_distribution(pillars: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, int]]:
    visible: Counter[str] = Counter()
    main_qi: Counter[str] = Counter()
    hidden: Counter[str] = Counter()
    visible_ten_gods: Counter[str] = Counter()
    hidden_ten_gods: Counter[str] = Counter()
    for pillar in pillars:
        stem = str(pillar.get("stem", ""))
        branch = str(pillar.get("branch", ""))
        if stem in STEM_ELEMENTS:
            visible[STEM_ELEMENTS[stem]] += 1
            visible_ten_gods[str(pillar.get("ten_god") or "—")] += 1
        if branch in BRANCH_ELEMENTS:
            main_qi[BRANCH_ELEMENTS[branch]] += 1
            for hidden_stem in pillar.get("hidden_stems", ()):
                value = str(hidden_stem.get("stem", "")) if isinstance(hidden_stem, Mapping) else str(hidden_stem)
                if value in STEM_ELEMENTS:
                    hidden[STEM_ELEMENTS[value]] += 1
                    ten_god = str(hidden_stem.get("ten_god", "—")) if isinstance(hidden_stem, Mapping) else "—"
                    hidden_ten_gods[ten_god] += 1
    element_layers = {
        "visible_stems": {element: visible[element] for element in ELEMENTS},
        "branch_main_qi": {element: main_qi[element] for element in ELEMENTS},
        "hidden_stems": {element: hidden[element] for element in ELEMENTS},
    }
    return {
        "elements": element_layers,
        "ten_gods": {
            "visible_stems": dict(sorted(visible_ten_gods.items())),
            "hidden_stems": dict(sorted(hidden_ten_gods.items())),
        },
    }


def structured_relations(pillars: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    if len(pillars) < 3:
        return []
    day_stem = str(pillars[2]["stem"])
    relations: list[dict[str, Any]] = []
    valid_stems = [(pillar, str(pillar.get("stem", ""))) for pillar in pillars if str(pillar.get("stem", "")) in STEM_ELEMENTS]
    for (left_pillar, left), (right_pillar, right) in combinations(valid_stems, 2):
        pair = frozenset((left, right))
        relation_type = ""
        result_element: str | None = None
        if pair in STEM_COMBINATIONS:
            relation_type = "天干合"
            result_element = STEM_COMBINATIONS[pair]
        elif pair in STEM_CLASHES:
            relation_type = "天干冲"
        elif ELEMENT_CONTROLS[STEM_ELEMENTS[left]] == STEM_ELEMENTS[right] or ELEMENT_CONTROLS[STEM_ELEMENTS[right]] == STEM_ELEMENTS[left]:
            relation_type = "天干克"
        if relation_type:
            relations.append(_relation_payload(relation_type, [
                _participant(left_pillar, layer="stem", value=left, day_stem=day_stem),
                _participant(right_pillar, layer="stem", value=right, day_stem=day_stem),
            ], result_element))

    valid_branches = [(pillar, str(pillar.get("branch", ""))) for pillar in pillars if str(pillar.get("branch", "")) in BRANCH_ELEMENTS]
    for group, result_element in (*TRINES, *MEETINGS):
        found = [(pillar, branch) for pillar, branch in valid_branches if branch in group]
        distinct = list(dict.fromkeys(branch for _, branch in found))
        if len(distinct) >= 2:
            complete = len(distinct) == 3
            relation_type = ("三合" if (group, result_element) in TRINES else "三会") if complete else ("半合" if (group, result_element) in TRINES else "半会")
            relations.append(_relation_payload(relation_type, [
                _participant(pillar, layer="branch", value=branch, day_stem=day_stem)
                for pillar, branch in found
            ], result_element))
    for (left_pillar, left), (right_pillar, right) in combinations(valid_branches, 2):
        pair = frozenset((left, right))
        candidates: list[tuple[str, str | None]] = []
        if pair in BRANCH_COMBINATIONS:
            candidates.append(("地支六合", BRANCH_COMBINATIONS[pair]))
        if pair in BRANCH_CLASHES:
            candidates.append(("地支冲", None))
        if pair in BRANCH_HARMS:
            candidates.append(("地支害", None))
        if pair in BRANCH_BREAKS:
            candidates.append(("地支破", None))
        if pair <= frozenset(("寅", "巳", "申")) or pair <= frozenset(("丑", "未", "戌")) or pair == frozenset(("子", "卯")):
            candidates.append(("地支刑", None))
        if left == right and left in {"辰", "午", "酉", "亥"}:
            candidates.append(("地支自刑", None))
        participants = [
            _participant(left_pillar, layer="branch", value=left, day_stem=day_stem),
            _participant(right_pillar, layer="branch", value=right, day_stem=day_stem),
        ]
        for relation_type, result_element in candidates:
            relations.append(_relation_payload(relation_type, participants, result_element))
    return relations


def _relation_payload(relation_type: str, participants: list[dict[str, str]], result_element: str | None) -> dict[str, Any]:
    topics = _relation_topics(participants)
    return {
        "relation_type": relation_type,
        "participants": participants,
        "result_element": result_element,
        "theme_tags": topics,
        "source_rule": "子平干支关系通行表",
        "label": f"{'·'.join(item['pillar'] + item['value'] for item in participants)} {relation_type}{result_element or ''}",
    }


def _relation_topics(participants: Iterable[Mapping[str, str]]) -> list[str]:
    gods = {item.get("ten_god", "") for item in participants}
    pillars = {item.get("pillar", "") for item in participants}
    topics: list[str] = []
    if gods & {"正官", "七杀", "正印", "偏印", "食神", "伤官"}:
        topics.append("事业")
    if gods & {"正财", "偏财", "比肩", "劫财", "食神", "伤官"}:
        topics.append("财富")
    if "日" in pillars or gods & {"正财", "偏财", "正官", "七杀"}:
        topics.append("感情")
    if any(item.get("day_master_relation") in {"生我", "克我", "同我"} for item in participants):
        topics.append("健康")
    return [topic for topic in THEME_ORDER if topic in topics]


def build_structure_profile(
    pillars: list[Mapping[str, Any]],
    *,
    gender: str | None,
    shensha_hits: Iterable[Mapping[str, Any]],
    seasonal_status: Mapping[str, str],
) -> dict[str, Any]:
    if len(pillars) < 4 or any(str(pillar.get("stem", "")) not in STEM_ELEMENTS for pillar in pillars):
        raise ValueError("完整四柱结构分析需要准确出生时辰。")
    day_stem = str(pillars[2]["stem"])
    day_element = STEM_ELEMENTS[day_stem]
    distributions = layered_distribution(pillars)
    relations = structured_relations(pillars)
    roots = [
        str(pillar.get("label", ""))
        for pillar in pillars
        if any(
            STEM_ELEMENTS.get(str(hidden.get("stem", ""))) == day_element
            for hidden in pillar.get("hidden_stems", ())
            if isinstance(hidden, Mapping)
        )
    ]
    theme_profiles = _theme_profiles(
        pillars,
        gender=gender,
        shensha_hits=list(shensha_hits),
        seasonal_status=seasonal_status,
        relations=relations,
        roots=roots,
        element_layers=distributions["elements"],
    )
    return {
        "day_master": {
            "stem": day_stem,
            "element": day_element,
            "rooted": bool(roots),
            "root_pillars": roots,
            "month_status": seasonal_status.get(day_element, "—"),
        },
        "day_master_relations": _day_master_relations(pillars, day_stem),
        "layered_distribution": distributions,
        "structural_relations": relations,
        "theme_profiles": theme_profiles,
    }


def _day_master_relations(pillars: list[Mapping[str, Any]], day_stem: str) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for pillar in pillars:
        stem = str(pillar.get("stem", ""))
        branch = str(pillar.get("branch", ""))
        if stem in STEM_ELEMENTS:
            result.append(_participant(pillar, layer="stem", value=stem, day_stem=day_stem))
        if branch in BRANCH_ELEMENTS:
            result.append(_participant(pillar, layer="branch", value=branch, day_stem=day_stem))
            for hidden in pillar.get("hidden_stems", ()):
                if not isinstance(hidden, Mapping):
                    continue
                hidden_stem = str(hidden.get("stem", ""))
                if hidden_stem in STEM_ELEMENTS:
                    result.append(_participant(pillar, layer="hidden_stem", value=hidden_stem, day_stem=day_stem))
    return result


def _theme_profiles(
    pillars: list[Mapping[str, Any]],
    *,
    gender: str | None,
    shensha_hits: list[Mapping[str, Any]],
    seasonal_status: Mapping[str, str],
    relations: list[Mapping[str, Any]],
    roots: list[str],
    element_layers: Mapping[str, Mapping[str, int]],
) -> list[dict[str, Any]]:
    visible_gods = [str(pillar.get("ten_god", "")) for pillar in pillars if pillar.get("label") != "日"]
    hidden_gods = [str(hidden.get("ten_god", "")) for pillar in pillars for hidden in pillar.get("hidden_stems", ()) if isinstance(hidden, Mapping)]
    all_gods = visible_gods + hidden_gods
    relation_topics = Counter(topic for relation in relations for topic in relation.get("theme_tags", ()))
    shensha_topics = {
        TOPIC_TO_THEME.get(str(topic), str(topic))
        for hit in shensha_hits
        for topic in hit.get("topic_tags", hit.get("theme_tags", ()))
    }
    branch_counts = Counter(str(pillar.get("branch", "")) for pillar in pillars)
    profiles: list[dict[str, Any]] = []
    for theme in THEME_ORDER:
        evidence: list[dict[str, str]] = []
        families: set[str] = set()

        def add(family: str, evidence_type: str, title: str, detail: str, source: str) -> None:
            families.add(family)
            evidence.append({"family": family, "evidence_type": evidence_type, "title": title, "detail": detail, "source": source})

        if theme == "事业":
            _add_god_evidence(add, all_gods, visible_gods, {"正官", "七杀"}, "官杀", "事业")
            _add_god_evidence(add, all_gods, visible_gods, {"正印", "偏印"}, "印星", "事业")
            _add_god_evidence(add, all_gods, visible_gods, {"食神", "伤官"}, "食伤", "事业")
            add("月令", "背景", "月令关系", f"日主五行在月令为{seasonal_status.get(STEM_ELEMENTS[str(pillars[2]['stem'])], '—')}。", "旺相休囚死通行表")
            if relation_topics[theme]:
                add("干支关系", "活动", "事业相关关系", f"{relation_topics[theme]} 条关系涉及官杀、印星或食伤。", "结构化干支关系")
            if any(hit.get("rule_id") == "yima" for hit in shensha_hits) or any(relation.get("relation_type") == "地支冲" for relation in relations):
                add("迁动", "活动", "迁动信号", "原局出现驿马或地支冲；只表示迁动结构活跃。", "驿马与地支冲")
        elif theme == "财富":
            visible_wealth = [god for god in visible_gods if god in {"正财", "偏财"}]
            hidden_wealth = [god for god in hidden_gods if god in {"正财", "偏财"}]
            if visible_wealth:
                add("财星明透", "背景", "财星见于明干", "、".join(visible_wealth), "日主中心十神关系")
            if hidden_wealth:
                add("财星藏根", "背景", "财星见于藏干", "、".join(hidden_wealth), "日主中心十神关系")
            if any(god in all_gods for god in ("食神", "伤官")) and any(god in all_gods for god in ("正财", "偏财")):
                add("食伤财星", "支持", "食伤与财星同见", "原局同时出现食伤与财星；这是结构共现，不代表财富多少。", "十神生克关系")
            _add_god_evidence(add, all_gods, visible_gods, {"比肩", "劫财"}, "比劫", "财富")
            if relation_topics[theme]:
                add("干支关系", "活动", "财富相关关系", f"{relation_topics[theme]} 条关系涉及财星、比劫或食伤。", "结构化干支关系")
        elif theme == "感情":
            spouse_gods = {"正财", "偏财"} if gender == "male" else {"正官", "七杀"} if gender == "female" else {"正财", "偏财", "正官", "七杀"}
            visible_spouse = [god for god in visible_gods if god in spouse_gods]
            hidden_spouse = [god for god in hidden_gods if god in spouse_gods]
            if visible_spouse:
                add("配偶星明透", "背景", "传统配偶星见于明干", "、".join(visible_spouse), "男命财星、女命官杀的通行取法")
            if hidden_spouse:
                add("配偶星藏见", "背景", "传统配偶星见于藏干", "、".join(hidden_spouse), "男命财星、女命官杀的通行取法")
            day_branch = str(pillars[2].get("branch", ""))
            add("夫妻宫", "背景", "日支夫妻宫", f"日支为{day_branch}，主气十神为{_ten_god(str(pillars[2]['stem']), HIDDEN_STEMS[day_branch][0])}。", "子平日支夫妻宫")
            spouse_relations = [relation for relation in relations if any(item.get("pillar") == "日" and item.get("layer") == "branch" for item in relation.get("participants", ()))]
            if spouse_relations:
                add("夫妻宫关系", "活动", "夫妻宫参与关系", "；".join(str(item.get("label", "")) for item in spouse_relations), "结构化干支关系")
            stem_combine = [relation for relation in relations if relation.get("relation_type") == "天干合" and any(item.get("pillar") == "日" for item in relation.get("participants", ()))]
            if stem_combine:
                add("日干合", "活动", "日干参与天干合", "；".join(str(item.get("label", "")) for item in stem_combine), "天干五合")
        else:
            missing = [element for element in ELEMENTS if sum(layer[element] for layer in element_layers.values()) == 0]
            concentrated = [element for element in ELEMENTS if sum(layer[element] for layer in element_layers.values()) >= 4]
            if missing or concentrated:
                add("五行分布", "背景", "五行分布特征", f"未见：{'、'.join(missing) or '无'}；集中：{'、'.join(concentrated) or '无'}。", "明干、主气、藏干分层计数")
            add("月令", "背景", "日主月令状态", f"日主五行在月令为{seasonal_status.get(STEM_ELEMENTS[str(pillars[2]['stem'])], '—')}。", "旺相休囚死通行表")
            if roots:
                add("通根", "支持", "日主通根", f"同类根气见于{'、'.join(roots)}柱。", "藏干同五行检查")
            pressure = [relation for relation in relations if relation.get("relation_type") in {"天干克", "天干冲", "地支冲", "地支害", "地支破", "地支刑", "地支自刑"}]
            if pressure:
                add("冲刑害破", "制约", "结构关系活跃", f"原局记录 {len(pressure)} 条冲、刑、害、破或克关系。", "结构化干支关系")
            repeated = [branch for branch, count in branch_counts.items() if count > 1]
            if repeated:
                add("重复地支", "活动", "重复地支", "、".join(repeated), "四支重复检查")

        if theme in shensha_topics:
            matched = [
                str(hit.get("name", ""))
                for hit in shensha_hits
                if theme in {
                    TOPIC_TO_THEME.get(str(topic), str(topic))
                    for topic in hit.get("topic_tags", hit.get("theme_tags", ()))
                }
            ]
            add("神煞", "背景", "辅助神煞", "、".join(matched), "神煞注册表；同主题仅计一个证据家族")

        profiles.append({
            "theme": theme,
            "evidence": evidence,
            "raw_family_count": len(families),
            "possible_family_count": THEME_POSSIBLE_FAMILIES[theme],
            "activity_percentile": None,
            "percentile_label": "待统计基线",
        })
    return profiles


def _add_god_evidence(add: Any, all_gods: list[str], visible_gods: list[str], gods: set[str], family: str, theme: str) -> None:
    matches = [god for god in all_gods if god in gods]
    if not matches:
        return
    visible = [god for god in visible_gods if god in gods]
    add(
        family,
        "背景",
        f"{family}分布",
        f"共见 {len(matches)} 项，其中明干 {len(visible)} 项：{'、'.join(matches)}。",
        f"日主中心十神关系 · {theme}",
    )
