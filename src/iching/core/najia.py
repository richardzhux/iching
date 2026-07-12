from __future__ import annotations


PALACE_ELEMENTS = {
    "乾": "金",
    "兑": "金",
    "离": "火",
    "震": "木",
    "巽": "木",
    "坎": "水",
    "艮": "土",
    "坤": "土",
}
GENERATES = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
CONTROLS = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}
SIX_RELATIVES = ("父母", "兄弟", "子孙", "妻财", "官鬼")
SIX_GOD_SEQUENCE = ("青龙", "朱雀", "勾陈", "腾蛇", "白虎", "玄武")
SIX_GOD_START_INDEX = {
    "甲": 0,
    "乙": 0,
    "丙": 1,
    "丁": 1,
    "戊": 2,
    "己": 3,
    "庚": 4,
    "辛": 4,
    "壬": 5,
    "癸": 5,
}


def palace_element(palace: str) -> str:
    for trigram, element in PALACE_ELEMENTS.items():
        if trigram in palace:
            return element
    raise ValueError(f"unknown palace: {palace}")


def six_relative_label(reference_element: str, line_element: str) -> str:
    if reference_element == line_element:
        return "兄弟"
    if GENERATES.get(reference_element) == line_element:
        return "子孙"
    if GENERATES.get(line_element) == reference_element:
        return "父母"
    if CONTROLS.get(reference_element) == line_element:
        return "妻财"
    if CONTROLS.get(line_element) == reference_element:
        return "官鬼"
    raise ValueError(
        f"unknown five-element relation: {reference_element} -> {line_element}"
    )


def rebase_relation(relation: str, palace: str) -> str:
    if not relation or relation[-1] not in GENERATES:
        return relation
    prefix = next((label for label in SIX_RELATIVES if relation.startswith(label)), None)
    if prefix is None:
        return relation
    label = six_relative_label(palace_element(palace), relation[-1])
    return label + relation[len(prefix) :]


def derive_six_gods(day_stem: str | None) -> list[str]:
    start = SIX_GOD_START_INDEX.get(day_stem or "")
    if start is None:
        return [""] * 6
    return [
        SIX_GOD_SEQUENCE[(start + offset) % len(SIX_GOD_SEQUENCE)]
        for offset in range(6)
    ]
