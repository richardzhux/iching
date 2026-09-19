from __future__ import annotations

from collections import Counter
from itertools import combinations
from typing import Any, Iterable, Mapping, Optional


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

THEME_ORDER = ("事业", "财富", "感情", "五行与承压结构")
TOPIC_TO_THEME = {"career": "事业", "wealth": "财富", "relationship": "感情", "health": "五行与承压结构"}
METRIC_REGISTRY_VERSION = "bazi-core-metrics-2026.07-v2"
_THEME_METRICS = {
    "事业": (
        ("officer_count", "官杀出现", "ordinal", "日主中心十神"),
        ("resource_count", "印星出现", "ordinal", "日主中心十神"),
        ("output_count", "食伤出现", "ordinal", "日主中心十神"),
        ("relation_count", "事业相关关系", "ordinal", "结构化干支关系"),
        ("mobility_count", "迁动信号", "ordinal", "驿马与地支冲"),
        ("shensha_count", "事业辅助神煞", "binary", "版本化神煞注册表"),
    ),
    "财富": (
        ("visible_wealth_count", "财星明透", "ordinal", "日主中心十神"),
        ("hidden_wealth_count", "财星藏见", "ordinal", "日主中心十神"),
        ("output_count", "食伤出现", "ordinal", "日主中心十神"),
        ("peer_count", "比劫出现", "ordinal", "日主中心十神"),
        ("relation_count", "财富相关关系", "ordinal", "结构化干支关系"),
        ("shensha_count", "财富辅助神煞", "binary", "版本化神煞注册表"),
    ),
    "感情": (
        ("visible_spouse_count", "配偶星明透", "ordinal", "传统配偶星取法"),
        ("hidden_spouse_count", "配偶星藏见", "ordinal", "传统配偶星取法"),
        ("spouse_palace_relation_count", "夫妻宫关系", "ordinal", "日支夫妻宫与干支关系"),
        ("day_stem_combine_count", "日干合", "ordinal", "天干五合"),
        ("relation_count", "感情相关关系", "ordinal", "结构化干支关系"),
        ("shensha_count", "感情辅助神煞", "binary", "版本化神煞注册表"),
    ),
    "五行与承压结构": (
        ("missing_element_count", "未见五行", "ordinal", "明干、主气、藏干分层"),
        ("concentrated_element_count", "集中五行", "ordinal", "明干、主气、藏干分层"),
        ("root_pillar_count", "通根柱位", "ordinal", "藏干同五行检查"),
        ("pressure_relation_count", "冲刑害破克", "ordinal", "结构化干支关系"),
        ("repeated_branch_count", "重复地支", "ordinal", "四支重复检查"),
        ("shensha_count", "承压辅助神煞", "binary", "版本化神煞注册表"),
    ),
}
_METRIC_SEMANTIC_POLES = {
    "事业.officer_count": {"low": "规则压力较轻", "typical": "责任结构适中", "high": "责任结构更集中"},
    "事业.resource_count": {"low": "支持路径较精简", "typical": "支持结构适中", "high": "支持与学习结构更集中"},
    "事业.output_count": {"low": "表达方式偏内敛", "typical": "表达结构适中", "high": "表达与产出更活跃"},
    "事业.relation_count": {"low": "事业关系较聚焦", "typical": "事业互动适中", "high": "事业互动更密集"},
    "事业.mobility_count": {"low": "发展路径较定向", "typical": "迁动信号适中", "high": "迁动与变化更活跃"},
    "财富.visible_wealth_count": {"low": "财富表达偏潜藏", "typical": "财富显隐适中", "high": "财富表达更外显"},
    "财富.hidden_wealth_count": {"low": "资源路径更直接", "typical": "藏见资源适中", "high": "资源更偏内藏积累"},
    "财富.output_count": {"low": "价值输出偏收敛", "typical": "价值转化适中", "high": "价值转化更活跃"},
    "财富.peer_count": {"low": "资源边界较独立", "typical": "协作结构适中", "high": "共同体与协作更活跃"},
    "财富.relation_count": {"low": "财富关系较聚焦", "typical": "财富互动适中", "high": "财富互动更密集"},
    "感情.visible_spouse_count": {"low": "配偶星表达偏潜藏", "typical": "配偶星显隐适中", "high": "配偶星表达更外显"},
    "感情.hidden_spouse_count": {"low": "配偶星路径较直接", "typical": "配偶星藏见适中", "high": "配偶星更偏内藏显现"},
    "感情.spouse_palace_relation_count": {"low": "夫妻宫关系较聚焦", "typical": "夫妻宫互动适中", "high": "夫妻宫互动更密集"},
    "感情.day_stem_combine_count": {"low": "日干互动较独立", "typical": "日干互动适中", "high": "日干合意象更突出"},
    "感情.relation_count": {"low": "感情关系较聚焦", "typical": "感情互动适中", "high": "感情互动更密集"},
    "五行与承压结构.missing_element_count": {"low": "五行覆盖更完整", "typical": "五行覆盖适中", "high": "五行呈现更偏科"},
    "五行与承压结构.concentrated_element_count": {"low": "五行分布较分散", "typical": "五行集中度适中", "high": "五行集中度更高"},
    "五行与承压结构.root_pillar_count": {"low": "通根范围较窄", "typical": "通根范围适中", "high": "通根范围较广"},
    "五行与承压结构.pressure_relation_count": {"low": "结构张力较低", "typical": "结构张力适中", "high": "结构张力更集中"},
    "五行与承压结构.repeated_branch_count": {"low": "地支重复较少", "typical": "地支重复适中", "high": "地支重复更明显"},
}
METRIC_DEFINITIONS = {
    f"{theme}.{metric_id}": {
        "id": f"{theme}.{metric_id}",
        "theme": theme,
        "metric_id": metric_id,
        "label": label,
        "metric_type": metric_type,
        "source": source,
        "version": METRIC_REGISTRY_VERSION,
        **(
            {"semantic_poles": _METRIC_SEMANTIC_POLES[f"{theme}.{metric_id}"]}
            if metric_type == "ordinal"
            else {}
        ),
    }
    for theme, metrics in _THEME_METRICS.items()
    for metric_id, label, metric_type, source in metrics
}


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
        topics.append("五行与承压结构")
    return [topic for topic in THEME_ORDER if topic in topics]


def build_structure_profile(
    pillars: list[Mapping[str, Any]],
    *,
    gender: str | None,
    shensha_hits: Iterable[Mapping[str, Any]],
    seasonal_status: Mapping[str, str],
    fact_graph: Any | None = None,
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
    strength = day_master_strength(
        pillars, seasonal_status=seasonal_status, roots=roots
    )
    synthesis = build_consumer_synthesis(theme_profiles, strength=strength)
    return {
        "day_master": {
            "stem": day_stem,
            "element": day_element,
            "rooted": bool(roots),
            "root_pillars": roots,
            "month_status": seasonal_status.get(day_element, "—"),
            "strength": strength,
        },
        "day_master_relations": _day_master_relations(pillars, day_stem),
        "layered_distribution": distributions,
        "structural_relations": relations,
        "theme_profiles": theme_profiles,
        "synthesis": synthesis,
    }


#: 月令 weighting for the day master's element. A house scale, not canon: it is
#: reported alongside every conclusion so a reader can disagree with it.
_SEASON_WEIGHT = {"旺": 3.0, "相": 2.0, "休": -1.0, "囚": -2.0, "死": -3.0}
_SUPPORT_GODS = {"比肩", "劫财", "正印", "偏印"}
_DRAIN_GODS = {"食神", "伤官", "正财", "偏财", "正官", "七杀"}

STRENGTH_BANDS = ("偏弱", "中和", "偏强")
#: Tercile cutoffs of the score distribution over the reference sample.
STRENGTH_LOWER_TERCILE = 0.24
STRENGTH_UPPER_TERCILE = 4.18


def day_master_strength(
    pillars: list[Mapping[str, Any]],
    *,
    seasonal_status: Mapping[str, str],
    roots: list[str],
) -> dict[str, Any]:
    """Score the day master 身强 / 身弱 and show the arithmetic.

    The synthesis used to ask only whether a ten-god *appeared* anywhere across
    eight stems and eight hidden stems. With sixteen slots in play almost every
    family appears in almost every chart, so the conclusions were fixed text.
    Strength is the discriminator 子平 actually turns on, so it is computed here
    and drives the wording.
    """
    day_stem = str(pillars[2]["stem"])
    day_element = STEM_ELEMENTS[day_stem]
    season = str(seasonal_status.get(day_element, "—"))

    support = drain = 0
    for index, pillar in enumerate(pillars):
        stem = str(pillar.get("stem", ""))
        if index != 2 and stem in STEM_ELEMENTS:
            god = _ten_god(day_stem, stem)
            if god in _SUPPORT_GODS:
                support += 1
            elif god in _DRAIN_GODS:
                drain += 1
        for hidden in pillar.get("hidden_stems", ()) or ():
            if not isinstance(hidden, Mapping):
                continue
            hidden_stem = str(hidden.get("stem", ""))
            if hidden_stem not in STEM_ELEMENTS:
                continue
            god = _ten_god(day_stem, hidden_stem)
            if god in _SUPPORT_GODS:
                support += 1
            elif god in _DRAIN_GODS:
                drain += 1

    score = _SEASON_WEIGHT.get(season, 0.0)
    score += 1.4 * len(roots)
    score += 0.5 * support
    score -= 0.34 * drain

    # Calibrated to the terciles of 3,000 charts sampled across 1950-2012
    # (tools/measure_metric_scales.py). At the first-guess cutoff of +/-1.6 the
    # band read 偏强 for 53% of charts, which tells a reader almost nothing. A
    # band is only worth printing if it separates.
    if score >= STRENGTH_UPPER_TERCILE:
        band = "偏强"
    elif score <= STRENGTH_LOWER_TERCILE:
        band = "偏弱"
    else:
        band = "中和"

    return {
        "day_stem": day_stem,
        "element": day_element,
        "month_status": season,
        "rooted_pillars": list(roots),
        "support_count": support,
        "drain_count": drain,
        "score": round(score, 2),
        "band": band,
        "method": "house-weighted-月令-通根-同异类",
        "inputs": {
            "season_weight": _SEASON_WEIGHT.get(season, 0.0),
            "root_weight": round(1.4 * len(roots), 2),
            "support_weight": round(0.5 * support, 2),
            "drain_weight": round(-0.34 * drain, 2),
        },
    }


def _metric_values(profile: Mapping[str, Any]) -> dict[str, int]:
    values: dict[str, int] = {}
    for metric in profile.get("structure_metrics", ()) or ():
        if isinstance(metric, Mapping):
            try:
                values[str(metric.get("metric_id"))] = int(metric.get("value") or 0)
            except (TypeError, ValueError):
                continue
    return values


def _metric_labels(profile: Mapping[str, Any]) -> dict[str, str]:
    labels: dict[str, str] = {}
    for metric in profile.get("structure_metrics", ()) or ():
        if isinstance(metric, Mapping):
            labels[str(metric.get("metric_id"))] = str(metric.get("label") or "")
    return labels


#: Which metric each theme's conclusion is allowed to lead on, and how to word
#: it. `binary` metrics (神煞) are excluded: they fire on nearly every chart, so
#: they carry no information about this chart in particular.
_THEME_LEADS: dict[str, tuple[tuple[str, str, str], ...]] = {
    "事业": (
        ("officer_count", "责任与规则", "官杀{n}见，事业更容易长在明确的责任、标准与组织位置上"),
        ("resource_count", "专业与背书", "印星{n}见，资历、学习与他人背书是主要的推进方式"),
        ("output_count", "表达与产出", "食伤{n}见，把想法做成可见成果是主要的推进方式"),
        ("mobility_count", "迁动与变化", "迁动信号{n}处，位置、城市或赛道的变化本身就是事业线索"),
        ("relation_count", "协作与牵动", "事业相关干支关系{n}组，进展多由外部互动触发"),
    ),
    "财富": (
        ("visible_wealth_count", "外显的资源", "财星明透{n}位，金钱与资源配置会直接进入日常判断"),
        ("hidden_wealth_count", "内藏的积累", "财星藏于地支{n}处，财多靠时间、场景与经营慢慢显形"),
        ("output_count", "以能力换取", "食伤{n}见，收入更依赖把能力持续转成产出"),
        ("peer_count", "共享与分摊", "比劫{n}见，资源常在合作与分配中流动"),
        ("relation_count", "互动中的财", "财富相关干支关系{n}组，财随关系起落"),
    ),
    "感情": (
        ("visible_spouse_count", "明确的关系信号", "配偶星明透{n}位，对象与承诺方式通常感受得比较清楚"),
        ("spouse_palace_relation_count", "夫妻宫被牵动", "夫妻宫参与{n}组关系，亲密关系会实际改变阶段选择"),
        ("day_stem_combine_count", "日干有合", "日干{n}处成合，关系对本人的牵引明显"),
        ("hidden_spouse_count", "藏而后显", "配偶星藏见{n}处，关系多在真实相处中逐步确认"),
        ("relation_count", "互动密度", "感情相关干支关系{n}组"),
    ),
    "五行与承压结构": (
        ("pressure_relation_count", "张力集中", "冲刑害破克{n}组，结构里的推拉比较集中"),
        ("missing_element_count", "五行有缺", "{n}种五行未见，结构明显偏科"),
        ("concentrated_element_count", "五行集中", "{n}种五行高度集中，力量偏向一处"),
        ("repeated_branch_count", "地支重复", "{n}组地支重复，同一类场景反复出现"),
        ("root_pillar_count", "根气可用", "日主通根{n}柱，遇变时有可依靠的基础"),
    ),
}

_STRENGTH_CLAUSE = {
    "事业": {
        "偏强": "日主偏强，适合主动承担与对外争取。",
        "中和": "日主中和，进退都有余地，看具体条件决定节奏。",
        "偏弱": "日主偏弱，借力、协作与阶段性积累比硬扛更有效。",
    },
    "财富": {
        "偏强": "日主偏强，能担财，扩张与经营的容量较大。",
        "中和": "日主中和，量入为出，扩张与守成都不勉强。",
        "偏弱": "日主偏弱，财重则身轻，控制规模比追求速度重要。",
    },
    "感情": {
        "偏强": "日主偏强，关系中较主动，也需留出对方的空间。",
        "中和": "日主中和，关系里的给予与接受较容易平衡。",
        "偏弱": "日主偏弱，容易被关系牵动，先照顾自己的节奏。",
    },
    "五行与承压结构": {
        "偏强": "日主偏强，抗压有余，注意不要把张力转成硬碰。",
        "中和": "日主中和，压力来时调整空间较大。",
        "偏弱": "日主偏弱，遇到集中压力时更需要外部支持与休整。",
    },
}


#: Population mean and standard deviation for each ordinal metric,
#: measured over 2,500 charts sampled uniformly across 1950-2012 by
#: tools/measure_metric_scales.py. Raw counts are not comparable across
#: metrics: 关系 counts average 5.3 while 日干合 averages 0.31, so ranking
#: by raw value made 关系 the lead on ~70-90% of charts. Ranking by
#: deviation from the population asks the question that matters — what is
#: unusual about THIS chart.
METRIC_SCALES: dict[str, dict[str, tuple[float, float]]] = {
    "事业": {
        "mobility_count": (0.885, 0.891),
        "officer_count": (2.434, 1.227),
        "output_count": (2.436, 1.233),
        "relation_count": (5.258, 2.196),
        "resource_count": (2.48, 1.236),
    },
    "五行与承压结构": {
        "concentrated_element_count": (2.347, 0.716),
        "missing_element_count": (0.188, 0.412),
        "pressure_relation_count": (4.27, 1.884),
        "repeated_branch_count": (0.432, 0.529),
        "root_pillar_count": (1.873, 1.07),
    },
    "感情": {
        "day_stem_combine_count": (0.313, 0.533),
        "hidden_spouse_count": (1.86, 1.06),
        "relation_count": (5.844, 2.17),
        "spouse_palace_relation_count": (2.3, 1.152),
        "visible_spouse_count": (0.61, 0.692),
    },
    "财富": {
        "hidden_wealth_count": (1.875, 1.065),
        "output_count": (2.436, 1.233),
        "peer_count": (2.486, 1.276),
        "relation_count": (5.43, 2.17),
        "visible_wealth_count": (0.614, 0.705),
    },
}

def metric_deviation(theme: str, metric_id: str, value: int) -> float:
    """How far this chart sits from the population on one metric, in sd."""
    mean, sd = METRIC_SCALES.get(theme, {}).get(metric_id, (0.0, 1.0))
    return (float(value) - mean) / (sd or 1.0)


def _lead_for(
    theme: str, values: Mapping[str, int]
) -> tuple[str, str, str, int, float] | None:
    """The metric this chart is most unusual on, high or low.

    Ranking by raw count let whichever metric happens to have the largest
    natural scale win almost every time. Ranking by deviation surfaces what is
    actually distinctive; a strongly *absent* signal is as informative as a
    strongly present one, so the comparison is on magnitude.
    """
    candidates = _THEME_LEADS.get(theme, ())
    best: tuple[str, str, str, int, float] | None = None
    for metric_id, short, template in candidates:
        # A metric the profile never reported is missing data, not a measured
        # zero; scoring it as zero makes a partial payload look extreme.
        if metric_id not in values:
            continue
        count = int(values[metric_id])
        deviation = metric_deviation(theme, metric_id, count)
        if best is None or abs(deviation) > abs(best[4]):
            best = (metric_id, short, template, count, deviation)
    # A chart sitting at the population average on everything has no lead.
    if best is None or abs(best[4]) < 0.75:
        return None
    return best


def build_consumer_synthesis(
    profiles: Iterable[Mapping[str, Any]],
    *,
    strength: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """Conclusions driven by what this chart measures, not by what it contains.

    The previous version branched on set membership — `{"官杀", "印星"} <=
    families` — across all eight stems and their hidden stems. Sixteen slots
    make almost every family present in almost every chart, so measured over
    2,000 generated charts five of six conclusions were fixed text: 事业 read
    the same for 90.1%, 感情 for 98.1%, 五行 for 99.4%, and both 整体
    conclusions for 100%. Ordering made it worse: 通根 is present in 89.8% of
    charts but its headline reached 0.6% of readers, because the 冲刑害破 branch
    above it was true 99.4% of the time.

    Now each theme leads on whichever of its ordinal metrics this chart is
    actually highest on, and every conclusion is qualified by day-master
    strength, which is the axis 子平 turns on.
    """
    profile_list = list(profiles)
    band = str((strength or {}).get("band") or "中和")
    conclusions: list[dict[str, Any]] = []

    for priority, profile in enumerate(profile_list, start=1):
        theme = str(profile.get("theme", ""))
        evidence = list(profile.get("evidence", ()))
        values = _metric_values(profile)
        lead = _lead_for(theme, values)
        strength_clause = _STRENGTH_CLAUSE.get(theme, {}).get(band, "")

        if lead is None:
            headline = f"{theme}：本盘各项都接近常见水平"
            body = (
                "这一主题的每项结构指标都落在常见区间，没有哪一条特别突出。"
                f"{strength_clause}"
            )
        else:
            metric_id, short, template, count, deviation = lead
            high = deviation > 0
            headline = f"{theme}：{short}{'偏多' if high else '偏少'}，是本盘最偏离常见值的一条"
            mean = METRIC_SCALES.get(theme, {}).get(metric_id, (0.0, 1.0))[0]
            if high:
                body = template.format(n=count)
            else:
                body = f"{short}只计到 {count}，明显低于常见水平"
            body += f"（常见约 {mean:g}，本盘 {count}，偏离 {deviation:+.1f} 个标准差）。"
            if strength_clause:
                body += strength_clause
            # Name the next two by deviation, so the lead is visibly a ranking.
            others = sorted(
                (
                    (
                        abs(metric_deviation(theme, other_id, int(values.get(other_id, 0)))),
                        other_short,
                        int(values.get(other_id, 0)),
                    )
                    for other_id, other_short, *_ in _THEME_LEADS.get(theme, ())
                    if other_id != metric_id
                ),
                reverse=True,
            )[:2]
            if others:
                joined = "、".join(f"{label} {value}" for _, label, value in others)
                body += f"其次偏离较大的是{joined}。"

        supporting = [
            str(item.get("id", "")) for item in evidence if item.get("evidence_type") != "制约"
        ][:4]
        counter = [
            str(item.get("id", "")) for item in evidence if item.get("evidence_type") == "制约"
        ][:2]
        conclusions.append(
            {
                "id": f"bazi.conclusion.{priority}",
                "theme": theme,
                "headline": headline,
                "body": body,
                "lead_metric": lead[0] if lead else None,
                "lead_value": lead[3] if lead else 0,
                "strength_band": band,
                "supporting_evidence_ids": [item for item in supporting if item],
                "counter_evidence_ids": [item for item in counter if item],
                "school_scope": "现代子平通行分析",
                "priority": priority,
            }
        )

    # One overall conclusion, written from the strength reading rather than
    # fired on every chart regardless of content.
    if strength:
        month = str(strength.get("month_status") or "—")
        roots = list(strength.get("rooted_pillars") or [])
        root_text = "、".join(roots) + "柱" if roots else "四柱皆无"
        conclusions.append(
            {
                "id": "bazi.conclusion.overall.strength",
                "theme": "整体",
                "headline": f"日主{strength.get('day_stem', '')}{strength.get('element', '')}，{band}",
                "body": (
                    f"日主五行在月令为{month}，通根见于{root_text}；"
                    f"同类{strength.get('support_count', 0)}、异类{strength.get('drain_count', 0)}，"
                    f"计得{strength.get('score', 0)}，归为{band}。"
                    "此判断用于决定以上各主题该偏向主动还是借力，算法与权重一并给出，可自行复核。"
                ),
                "lead_metric": "day_master_strength",
                "lead_value": strength.get("score", 0),
                "strength_band": band,
                "supporting_evidence_ids": [],
                "counter_evidence_ids": [],
                "school_scope": "房规加权（月令 / 通根 / 同异类）",
                "priority": len(conclusions) + 1,
            }
        )

    return {
        "method": "modern-ziping-metric-led-v2",
        "strength": dict(strength) if strength else None,
        "conclusions": conclusions,
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
            evidence.append({
                "id": f"bazi.evidence.{THEME_ORDER.index(theme) + 1}.{len(evidence) + 1}",
                "family": family,
                "evidence_type": evidence_type,
                "title": title,
                "detail": detail,
                "source": source,
            })

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
                add("财星藏见", "背景", "财星见于藏干", "、".join(hidden_wealth), "日主中心十神关系")
            if any(god in all_gods for god in ("食神", "伤官")) and any(god in all_gods for god in ("正财", "偏财")):
                add("食伤财星", "支持", "食伤与财星同见", "原局食伤与财星同见，价值创造与资源兑现相互衔接。", "十神生克关系")
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

        topic_hits = [
            hit for hit in shensha_hits
            if theme in {TOPIC_TO_THEME.get(str(topic), str(topic)) for topic in hit.get("topic_tags", hit.get("theme_tags", ()))}
        ]
        def god_count(names: set[str]) -> int:
            return sum(1 for god in all_gods if god in names)

        def visible_count(names: set[str]) -> int:
            return sum(1 for god in visible_gods if god in names)

        def hidden_count(names: set[str]) -> int:
            return sum(1 for god in hidden_gods if god in names)
        if theme == "事业":
            metrics = [
                ("officer_count", "官杀出现", god_count({"正官", "七杀"})),
                ("resource_count", "印星出现", god_count({"正印", "偏印"})),
                ("output_count", "食伤出现", god_count({"食神", "伤官"})),
                ("relation_count", "事业相关关系", relation_topics[theme]),
                ("mobility_count", "迁动信号", int(any(hit.get("rule_id") == "yima" for hit in shensha_hits)) + sum(1 for relation in relations if relation.get("relation_type") == "地支冲")),
                ("shensha_count", "事业神煞", len(topic_hits)),
            ]
        elif theme == "财富":
            metrics = [
                ("visible_wealth_count", "财星明透", visible_count({"正财", "偏财"})),
                ("hidden_wealth_count", "财星藏见", hidden_count({"正财", "偏财"})),
                ("output_count", "食伤出现", god_count({"食神", "伤官"})),
                ("peer_count", "比劫出现", god_count({"比肩", "劫财"})),
                ("relation_count", "财富相关关系", relation_topics[theme]),
                ("shensha_count", "财富神煞", len(topic_hits)),
            ]
        elif theme == "感情":
            spouse_gods = {"正财", "偏财"} if gender == "male" else {"正官", "七杀"} if gender == "female" else {"正财", "偏财", "正官", "七杀"}
            spouse_relations = [relation for relation in relations if any(item.get("pillar") == "日" and item.get("layer") == "branch" for item in relation.get("participants", ()))]
            stem_combines = [relation for relation in relations if relation.get("relation_type") == "天干合" and any(item.get("pillar") == "日" for item in relation.get("participants", ()))]
            metrics = [
                ("visible_spouse_count", "配偶星明透", visible_count(spouse_gods)),
                ("hidden_spouse_count", "配偶星藏见", hidden_count(spouse_gods)),
                ("spouse_palace_relation_count", "夫妻宫关系", len(spouse_relations)),
                ("day_stem_combine_count", "日干合", len(stem_combines)),
                ("relation_count", "感情相关关系", relation_topics[theme]),
                ("shensha_count", "感情神煞", len(topic_hits)),
            ]
        else:
            totals = {element: sum(layer[element] for layer in element_layers.values()) for element in ELEMENTS}
            metrics = [
                ("missing_element_count", "未见五行", sum(1 for value in totals.values() if value == 0)),
                ("concentrated_element_count", "集中五行", sum(1 for value in totals.values() if value >= 4)),
                ("root_pillar_count", "通根柱位", len(roots)),
                ("pressure_relation_count", "冲刑害破克", sum(1 for relation in relations if relation.get("relation_type") in {"天干克", "天干冲", "地支冲", "地支害", "地支破", "地支刑", "地支自刑"})),
                ("repeated_branch_count", "重复地支", sum(1 for count in branch_counts.values() if count > 1)),
                ("shensha_count", "承压主题神煞", len(topic_hits)),
            ]
        metric_payloads = []
        for metric_id, label, value in metrics:
            definition = METRIC_DEFINITIONS[f"{theme}.{metric_id}"]
            metric_value = int(bool(value)) if definition["metric_type"] == "binary" else int(value)
            metric_payloads.append({
                "definition_id": definition["id"],
                "metric_id": metric_id,
                "label": label,
                "value": metric_value,
                "unit": "是否命中" if definition["metric_type"] == "binary" else "项",
                "metric_type": definition["metric_type"],
                "source": definition["source"],
                **(
                    {"semantic_poles": dict(definition["semantic_poles"])}
                    if "semantic_poles" in definition
                    else {}
                ),
            })
        profiles.append({
            "theme": theme,
            "evidence": evidence,
            "active_families": sorted(families),
            "structure_metrics": metric_payloads,
            "comparisons": [],
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
