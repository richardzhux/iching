from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Literal, Mapping, Sequence


RULES_VERSION = "shensha-2026.07-v2"

Level = Literal["core", "extended"]
Axis = Literal["助力", "才学", "情缘", "执行", "迁动", "考验"]


@dataclass(frozen=True)
class ShenShaRule:
    rule_id: str
    name: str
    category: str
    axis: Axis
    level: Level
    method: str
    mapping: Mapping[str, Sequence[str]]
    anchor: str
    source_title: str
    source_note: str
    school_note: str = ""


DAY_STEM_BRANCH_RULES: dict[str, dict[str, tuple[str, ...]]] = {
    "tianyi": {
        "甲": ("丑", "未"), "乙": ("子", "申"), "丙": ("亥", "酉"), "丁": ("亥", "酉"),
        "戊": ("丑", "未"), "己": ("子", "申"), "庚": ("丑", "未"), "辛": ("寅", "午"),
        "壬": ("卯", "巳"), "癸": ("卯", "巳"),
    },
    "taiji": {
        "甲": ("子", "午"), "乙": ("子", "午"), "丙": ("卯", "酉"), "丁": ("卯", "酉"),
        "戊": ("辰", "戌", "丑", "未"), "己": ("辰", "戌", "丑", "未"),
        "庚": ("寅", "亥"), "辛": ("寅", "亥"), "壬": ("巳", "申"), "癸": ("巳", "申"),
    },
    "wenchang": {
        "甲": ("巳",), "乙": ("午",), "丙": ("申",), "丁": ("酉",), "戊": ("申",),
        "己": ("酉",), "庚": ("亥",), "辛": ("子",), "壬": ("寅",), "癸": ("卯",),
    },
    "guoyin": {
        "甲": ("戌",), "乙": ("亥",), "丙": ("丑",), "丁": ("寅",), "戊": ("丑",),
        "己": ("寅",), "庚": ("辰",), "辛": ("巳",), "壬": ("未",), "癸": ("申",),
    },
    "fuxing": {
        "甲": ("寅", "子"), "乙": ("卯", "丑"), "丙": ("寅", "子"), "丁": ("亥",),
        "戊": ("申",), "己": ("未",), "庚": ("午",), "辛": ("巳",), "壬": ("辰",), "癸": ("卯", "丑"),
    },
    "lushen": {
        "甲": ("寅",), "乙": ("卯",), "丙": ("巳",), "丁": ("午",), "戊": ("巳",),
        "己": ("午",), "庚": ("申",), "辛": ("酉",), "壬": ("亥",), "癸": ("子",),
    },
    "yangren": {
        "甲": ("卯",), "乙": ("辰",), "丙": ("午",), "丁": ("未",), "戊": ("午",),
        "己": ("未",), "庚": ("酉",), "辛": ("戌",), "壬": ("子",), "癸": ("丑",),
    },
    "hongyan": {
        "甲": ("午",), "乙": ("午",), "丙": ("寅",), "丁": ("未",), "戊": ("辰",),
        "己": ("辰",), "庚": ("戌",), "辛": ("酉",), "壬": ("子",), "癸": ("申",),
    },
    "jinyu": {
        "甲": ("辰",), "乙": ("巳",), "丙": ("未",), "丁": ("申",), "戊": ("未",),
        "己": ("申",), "庚": ("戌",), "辛": ("亥",), "壬": ("丑",), "癸": ("寅",),
    },
    "xuetang": {
        "甲": ("亥",), "乙": ("亥",), "丙": ("寅",), "丁": ("寅",), "戊": ("申",),
        "己": ("申",), "庚": ("巳",), "辛": ("巳",), "壬": ("申",), "癸": ("申",),
    },
    "ciguan": {
        "甲": ("申",), "乙": ("申",), "丙": ("亥",), "丁": ("亥",), "戊": ("寅",),
        "己": ("寅",), "庚": ("巳",), "辛": ("巳",), "壬": ("亥",), "癸": ("亥",),
    },
}

DAY_STEM_PILLAR_RULES: dict[str, dict[str, tuple[str, ...]]] = {
    "xuetang": {
        "甲": ("己亥",), "乙": ("壬午",), "丙": ("丙寅",), "丁": ("丁酉",), "戊": ("戊寅",),
        "己": ("己酉",), "庚": ("辛巳",), "辛": ("甲子",), "壬": ("甲申",), "癸": ("乙卯",),
    },
    "ciguan": {
        "甲": ("庚寅",), "乙": ("辛卯",), "丙": ("乙巳",), "丁": ("戊午",), "戊": ("丁巳",),
        "己": ("庚午",), "庚": ("壬申",), "辛": ("癸酉",), "壬": ("癸亥",), "癸": ("壬戌",),
    },
}

TRINE_TARGETS: dict[str, dict[str, str]] = {
    "yima": {"申子辰": "寅", "寅午戌": "申", "巳酉丑": "亥", "亥卯未": "巳"},
    "taohua": {"申子辰": "酉", "寅午戌": "卯", "巳酉丑": "午", "亥卯未": "子"},
    "huagai": {"申子辰": "辰", "寅午戌": "戌", "巳酉丑": "丑", "亥卯未": "未"},
    "jiangxing": {"申子辰": "子", "寅午戌": "午", "巳酉丑": "酉", "亥卯未": "卯"},
    "jiesha": {"申子辰": "巳", "寅午戌": "亥", "巳酉丑": "寅", "亥卯未": "申"},
    "wangshen": {"申子辰": "亥", "寅午戌": "巳", "巳酉丑": "申", "亥卯未": "寅"},
    "zaisha": {"申子辰": "午", "寅午戌": "子", "巳酉丑": "卯", "亥卯未": "酉"},
}

MONTH_BRANCH_TARGETS: dict[str, dict[str, tuple[str, ...]]] = {
    "tiande": {
        "寅": ("丁",), "卯": ("申",), "辰": ("壬",), "巳": ("辛",), "午": ("亥",), "未": ("甲",),
        "申": ("癸",), "酉": ("寅",), "戌": ("丙",), "亥": ("乙",), "子": ("巳",), "丑": ("庚",),
    },
    "yuede": {
        "寅": ("丙",), "午": ("丙",), "戌": ("丙",), "申": ("壬",), "子": ("壬",), "辰": ("壬",),
        "亥": ("甲",), "卯": ("甲",), "未": ("甲",), "巳": ("庚",), "酉": ("庚",), "丑": ("庚",),
    },
    "tianyi_doctor": {
        "寅": ("丑",), "卯": ("寅",), "辰": ("卯",), "巳": ("辰",), "午": ("巳",), "未": ("午",),
        "申": ("未",), "酉": ("申",), "戌": ("酉",), "亥": ("戌",), "子": ("亥",), "丑": ("子",),
    },
}

YEAR_BRANCH_TARGETS: dict[str, dict[str, tuple[str, ...]]] = {
    "guchen": {
        "亥": ("寅",), "子": ("寅",), "丑": ("寅",), "寅": ("巳",), "卯": ("巳",), "辰": ("巳",),
        "巳": ("申",), "午": ("申",), "未": ("申",), "申": ("亥",), "酉": ("亥",), "戌": ("亥",),
    },
    "guasuo": {
        "亥": ("戌",), "子": ("戌",), "丑": ("戌",), "寅": ("丑",), "卯": ("丑",), "辰": ("丑",),
        "巳": ("辰",), "午": ("辰",), "未": ("辰",), "申": ("未",), "酉": ("未",), "戌": ("未",),
    },
    "hongluan": {
        "子": ("卯",), "丑": ("寅",), "寅": ("丑",), "卯": ("子",), "辰": ("亥",), "巳": ("戌",),
        "午": ("酉",), "未": ("申",), "申": ("未",), "酉": ("午",), "戌": ("巳",), "亥": ("辰",),
    },
    "tianxi": {
        "子": ("酉",), "丑": ("申",), "寅": ("未",), "卯": ("午",), "辰": ("巳",), "巳": ("辰",),
        "午": ("卯",), "未": ("寅",), "申": ("丑",), "酉": ("子",), "戌": ("亥",), "亥": ("戌",),
    },
}


def _rule(
    rule_id: str,
    name: str,
    category: str,
    axis: Axis,
    level: Level,
    method: str,
    mapping: Mapping[str, Sequence[str]],
    anchor: str,
    source_title: str,
    source_note: str,
    school_note: str = "",
) -> ShenShaRule:
    return ShenShaRule(rule_id, name, category, axis, level, method, mapping, anchor, source_title, source_note, school_note)


RULES: tuple[ShenShaRule, ...] = (
    _rule("tianyi", "天乙贵人", "助力", "助力", "core", "day_stem_branch", DAY_STEM_BRANCH_RULES["tianyi"], "日干", "《三命通会》", "以日干查四支。"),
    _rule("taiji", "太极贵人", "助力", "助力", "core", "day_stem_branch", DAY_STEM_BRANCH_RULES["taiji"], "日干", "《三命通会》", "以日干查四支。"),
    _rule("tiande", "天德贵人", "助力", "助力", "core", "month_mixed", MONTH_BRANCH_TARGETS["tiande"], "月支", "《三命通会》", "以月支查命局天干或地支。"),
    _rule("yuede", "月德贵人", "助力", "助力", "core", "month_mixed", MONTH_BRANCH_TARGETS["yuede"], "月支", "《三命通会》", "以月支三合局查命局天干。"),
    _rule("wenchang", "文昌贵人", "才学", "才学", "core", "day_stem_branch", DAY_STEM_BRANCH_RULES["wenchang"], "日干", "《渊海子平》", "以日干查四支。"),
    _rule("guoyin", "国印贵人", "助力", "助力", "core", "day_stem_branch", DAY_STEM_BRANCH_RULES["guoyin"], "日干", "《三命通会》", "以日干查四支。"),
    _rule("fuxing", "福星贵人", "助力", "助力", "core", "day_stem_branch", DAY_STEM_BRANCH_RULES["fuxing"], "日干", "《三命通会》", "以日干查四支。"),
    _rule("xuetang", "学堂", "才学", "才学", "core", "day_stem_branch", DAY_STEM_BRANCH_RULES["xuetang"], "日干五行", "《渊海子平·论十干学堂》", "按日干五行查四支；正位干支仅作进一步等级，不改变本项命中。", "另有纳音与官贵学堂法，本版固定采用《渊海子平》五行支位法。"),
    _rule("ciguan", "词馆", "才学", "才学", "core", "day_stem_branch", DAY_STEM_BRANCH_RULES["ciguan"], "日干官星", "《三命通会·论学堂词馆》", "按官贵临官之位查四支。", "学堂词馆另有纳音、食神与会禄等法，本版固定采用官贵临官法。"),
    _rule("lushen", "禄神", "执行", "执行", "core", "day_stem_branch", DAY_STEM_BRANCH_RULES["lushen"], "日干", "《渊海子平》", "以日干查临官地支。"),
    _rule("yima", "驿马", "迁动", "迁动", "core", "year_day_trine", TRINE_TARGETS["yima"], "年支、日支", "《三命通会》", "分别以年支、日支所属三合局查四支。"),
    _rule("taohua", "桃花", "情缘", "情缘", "core", "year_day_trine", TRINE_TARGETS["taohua"], "年支、日支", "《三命通会》", "分别以年支、日支所属三合局查四支。"),
    _rule("huagai", "华盖", "执行", "执行", "core", "year_day_trine", TRINE_TARGETS["huagai"], "年支、日支", "《三命通会》", "分别以年支、日支所属三合局查四支。"),
    _rule("jiangxing", "将星", "执行", "执行", "core", "year_day_trine", TRINE_TARGETS["jiangxing"], "年支、日支", "《三命通会》", "分别以年支、日支所属三合局查四支。"),
    _rule("yangren", "羊刃", "考验", "考验", "core", "day_stem_branch", DAY_STEM_BRANCH_RULES["yangren"], "日干", "《渊海子平》", "以日干查四支。", "阴干羊刃定位存在流派差异，本版按十干表。"),
    _rule("jiesha", "劫煞", "考验", "考验", "core", "year_day_trine", TRINE_TARGETS["jiesha"], "年支、日支", "《三命通会》", "分别以年支、日支所属三合局查四支。"),
    _rule("wangshen", "亡神", "考验", "考验", "core", "year_day_trine", TRINE_TARGETS["wangshen"], "年支、日支", "《三命通会》", "分别以年支、日支所属三合局查四支。"),
    _rule("zaisha", "灾煞", "考验", "考验", "core", "year_day_trine", TRINE_TARGETS["zaisha"], "年支、日支", "《三命通会》", "分别以年支、日支所属三合局查四支。"),
    _rule("guchen", "孤辰", "考验", "考验", "core", "year_branch", YEAR_BRANCH_TARGETS["guchen"], "年支", "《三命通会》", "以年支所属季方查四支。"),
    _rule("guasuo", "寡宿", "考验", "考验", "core", "year_branch", YEAR_BRANCH_TARGETS["guasuo"], "年支", "《三命通会》", "以年支所属季方查四支。"),
    _rule("hongluan", "红鸾", "情缘", "情缘", "extended", "year_branch", YEAR_BRANCH_TARGETS["hongluan"], "年支", "传统星命表", "以年支查四支。", "不同术数体系的用法不一。"),
    _rule("tianxi", "天喜", "情缘", "情缘", "extended", "year_branch", YEAR_BRANCH_TARGETS["tianxi"], "年支", "传统星命表", "以年支查四支。", "不同术数体系的用法不一。"),
    _rule("hongyan", "红艳", "情缘", "情缘", "extended", "day_stem_branch", DAY_STEM_BRANCH_RULES["hongyan"], "日干", "传统神煞表", "以日干查四支。", "各家表格有异，本版固定版本化表。"),
    _rule("jinyu", "金舆", "助力", "助力", "extended", "day_stem_branch", DAY_STEM_BRANCH_RULES["jinyu"], "日干", "《三命通会》", "以日干查四支。"),
    _rule("tianyi_doctor", "天医", "助力", "助力", "extended", "month_branch", MONTH_BRANCH_TARGETS["tianyi_doctor"], "月支", "传统神煞表", "以月支查四支。"),
    _rule("tianku", "天厨", "才学", "才学", "extended", "fixed_none", {}, "日干", "《渊海子平·论天厨贵人》", "十二宫星次换算需单独规则层，本版注册但不自动命中。", "避免把天厨误作禄神；完成星次换算审校前不参与结果与指数。"),
    _rule("dexiu", "德秀贵人", "助力", "助力", "extended", "fixed_none", {}, "月令", "《三命通会》", "需结合月令与透干，暂不作自动命中。", "组合条件异说较多，注册但不自动命中。"),
    _rule("kuigang", "魁罡", "执行", "执行", "extended", "fixed_day", {"day": ("庚辰", "庚戌", "壬辰", "戊戌")}, "日柱", "《三命通会》", "以日柱查固定干支。"),
    _rule("yinyang_error", "阴差阳错", "考验", "考验", "extended", "fixed_day", {"day": ("丙子", "丁丑", "戊寅", "辛卯", "壬辰", "癸巳", "丙午", "丁未", "戊申", "辛酉", "壬戌", "癸亥")}, "日柱", "《三命通会》", "以日柱查固定干支。"),
    _rule("ten_bad_defeats", "十恶大败", "考验", "考验", "extended", "fixed_day", {"day": ("甲辰", "乙巳", "乙丑", "丙申", "丁亥", "戊戌", "庚辰", "辛巳", "壬申", "癸亥")}, "日柱", "《渊海子平·论十恶大败》", "以日柱查禄入空亡的十个固定干支。", "只在日柱命中，不从其他柱推断。"),
)

RULE_BY_ID = {rule.rule_id: rule for rule in RULES}
CORE_RULE_IDS = tuple(rule.rule_id for rule in RULES if rule.level == "core")
EXTENDED_RULE_IDS = tuple(rule.rule_id for rule in RULES if rule.level == "extended")
AXES: tuple[Axis, ...] = ("助力", "才学", "情缘", "执行", "迁动", "考验")


def _valid_pillars(pillars: Iterable[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return [pillar for pillar in pillars if len(str(pillar.get("text", ""))) == 2 and pillar.get("stem") != "待定"]


def _trine_target(branch: str, mapping: Mapping[str, Sequence[str]]) -> set[str]:
    return {str(target) for group, target in mapping.items() if branch in group}


def _matched_labels(rule: ShenShaRule, pillars: list[Mapping[str, Any]]) -> tuple[list[str], list[str]]:
    if len(pillars) < 3:
        return [], []
    year = next((pillar for pillar in pillars if pillar.get("label") == "年"), pillars[0])
    month = next((pillar for pillar in pillars if pillar.get("label") == "月"), pillars[1])
    day = next((pillar for pillar in pillars if pillar.get("label") == "日"), pillars[2])
    targets: set[str] = set()
    values: list[str] = []
    if rule.method == "day_stem_branch":
        targets = set(rule.mapping.get(str(day["stem"]), ()))
        values = [str(pillar["branch"]) for pillar in pillars]
    elif rule.method == "day_stem_pillar":
        targets = set(rule.mapping.get(str(day["stem"]), ()))
        values = [str(pillar["text"]) for pillar in pillars]
    elif rule.method == "month_mixed":
        targets = set(rule.mapping.get(str(month["branch"]), ()))
        values = [str(pillar["stem"]) if str(pillar["stem"]) in targets else str(pillar["branch"]) for pillar in pillars]
    elif rule.method == "month_branch":
        targets = set(rule.mapping.get(str(month["branch"]), ()))
        values = [str(pillar["branch"]) for pillar in pillars]
    elif rule.method == "year_branch":
        targets = set(rule.mapping.get(str(year["branch"]), ()))
        values = [str(pillar["branch"]) for pillar in pillars]
    elif rule.method == "year_day_trine":
        targets = _trine_target(str(year["branch"]), rule.mapping) | _trine_target(str(day["branch"]), rule.mapping)
        values = [str(pillar["branch"]) for pillar in pillars]
    elif rule.method == "fixed_day":
        targets = set(rule.mapping.get("day", ()))
        values = [str(pillar["text"]) if pillar.get("label") == "日" else "" for pillar in pillars]
    else:
        return [], []
    labels = [str(pillar.get("label", "")) for pillar, value in zip(pillars, values) if value in targets]
    return list(dict.fromkeys(labels)), sorted(targets)


def evaluate_shensha(
    pillars: Iterable[Mapping[str, Any]],
    *,
    include_extended: bool = True,
) -> list[dict[str, Any]]:
    valid = _valid_pillars(pillars)
    hits: list[dict[str, Any]] = []
    for rule in RULES:
        if rule.level == "extended" and not include_extended:
            continue
        labels, targets = _matched_labels(rule, valid)
        if not labels:
            continue
        hits.append({
            "rule_id": rule.rule_id,
            "feature_id": f"bazi.shensha.{rule.rule_id}",
            "name": rule.name,
            "category": rule.category,
            "axis": rule.axis,
            "level": rule.level,
            "pillar_labels": labels,
            "trigger": f"{rule.anchor}取 {'、'.join(targets)}，命中{'、'.join(labels)}柱。",
            "source": {"title": rule.source_title, "note": rule.source_note},
            "school_note": rule.school_note,
            "rules_version": RULES_VERSION,
        })
    return hits


def registry_payload() -> list[dict[str, Any]]:
    return [
        {
            "rule_id": rule.rule_id,
            "feature_id": f"bazi.shensha.{rule.rule_id}",
            "name": rule.name,
            "category": rule.category,
            "axis": rule.axis,
            "level": rule.level,
            "anchor": rule.anchor,
            "source": {"title": rule.source_title, "note": rule.source_note},
            "school_note": rule.school_note,
            "rules_version": RULES_VERSION,
        }
        for rule in RULES
    ]
