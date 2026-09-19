from __future__ import annotations

import os
import re
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple
from uuid import uuid4

from iching.config import AppConfig, PATHS, build_app_config
from iching.core.ganzhi import DEFAULT_DAY_BOUNDARY, four_pillars, zi_hour_notice
from iching.core.divination import AVAILABLE_METHODS, DivinationMethod
from iching.core.hexagram import Hexagram, load_hexagram_definitions
from iching.core.hexagram_essence import essence_for
from iching.core.najia import derive_six_gods, rebase_relation
from iching.core.time_utils import get_current_time
from iching.integrations.ai import (
    DEFAULT_MODEL,
    MODEL_CAPABILITIES,
    AIResponseData,
    normalize_model_name,
    start_analysis,
)
from iching.integrations.interpretation_repository import InterpretationRepository
from iching.integrations.reading_format import (
    field_value,
    first_body_line,
    is_heading,
    normalize_locale,
    parse_sections,
    split_fields,
)
from iching.integrations.najia_repository import NajiaEntry, NajiaRepository


#: The 换日 rule a cast is recorded under. `current` (晚子时不换日) is what the
#: product has always produced, so no existing reading changes meaning. It is
#: named here rather than inherited from whichever library call came first, and
#: it is written into every session so a stored reading states its own school.
#: Inside 23:00–23:59 the reading also carries the other school's pillars, since
#: that is a live disagreement and not ours to settle silently.
READING_DAY_BOUNDARY = DEFAULT_DAY_BOUNDARY


def _default_input(prompt: str) -> str:
    return input(prompt)


def _build_najia_table(
    main_entry: Optional[NajiaEntry],
    changed_entry: Optional[NajiaEntry],
    line_overview: List[Dict[str, object]],
    day_stem: Optional[str],
) -> Dict[str, object]:
    meta: Dict[str, Optional[Dict[str, Optional[str]]]] = {"main": None, "changed": None}
    if main_entry:
        meta["main"] = {
            "name": main_entry.name,
            "gong": main_entry.palace,
            "type": main_entry.descriptor,
        }
    if changed_entry:
        meta["changed"] = {
            "name": changed_entry.name,
            "gong": changed_entry.palace,
            "type": changed_entry.descriptor,
        }
    if not main_entry:
        return {"meta": meta, "rows": []}

    overview = list(line_overview or [])
    if len(overview) < 6:
        overview.extend({} for _ in range(6 - len(overview)))

    six_gods = derive_six_gods(day_stem)
    god_map = {index + 1: god for index, god in enumerate(six_gods)}

    rows: List[Dict[str, object]] = []
    for idx in range(6):
        line_info = overview[idx] if idx < len(overview) else {}
        position = line_info.get("position", 6 - idx)
        line_type = line_info.get("line_type", "yang")
        changed_line_type = line_info.get("changed_line_type", line_type)
        is_moving = bool(line_info.get("is_moving"))
        moving_symbol = line_info.get("moving_symbol", "")
        value = line_info.get("value")

        main_line = main_entry.get_line_by_position(position)
        changed_line = (
            changed_entry.get_line_by_position(position) if changed_entry else None
        )
        changed_relation = changed_line.relation if changed_line else ""
        if changed_relation:
            changed_relation = rebase_relation(changed_relation, main_entry.palace)

        rows.append(
            {
                "position": position,
                "line_type": line_type,
                "changed_line_type": changed_line_type,
                "is_moving": is_moving,
                "moving_symbol": moving_symbol,
                "god": god_map.get(position, ""),
                "hidden": main_line.hidden if main_line else "",
                "main_relation": main_line.relation if main_line else "",
                "main_mark": main_line.glyph if main_line else "",
                "marker": main_line.marker if main_line else "",
                "movement_tag": _movement_tag_from_value(value),
                "changed_relation": changed_relation,
                "changed_mark": changed_line.glyph if changed_line else "",
            }
        )

    return {"meta": meta, "rows": rows}


def _normalized_entry_payload(
    entry: Optional[NajiaEntry],
    rows: List[Dict[str, object]],
    *,
    changed: bool,
) -> Optional[Dict[str, object]]:
    if entry is None:
        return None
    payload = entry.to_payload()
    rows_by_position = {row["position"]: row for row in rows}
    line_payloads = payload.get("lines")
    if not isinstance(line_payloads, list):
        return payload
    for line in line_payloads:
        if not isinstance(line, dict):
            continue
        row = rows_by_position.get(line.get("position"))
        if not row:
            continue
        line["god"] = row.get("god", "")
        if changed:
            line["relation"] = row.get("changed_relation", "")
            line["hidden"] = ""
    return payload


def _render_najia_text(najia_table: Dict[str, object]) -> str:
    meta = najia_table.get("meta")
    rows = najia_table.get("rows")
    if not isinstance(meta, dict) or not isinstance(rows, list):
        return ""
    main_meta = meta.get("main")
    changed_meta = meta.get("changed")
    if not isinstance(main_meta, dict):
        return ""

    header = f"六神　伏神　{main_meta.get('gong', '')}：{main_meta.get('name', '')}"
    if isinstance(changed_meta, dict):
        header += f"　之　{changed_meta.get('gong', '')}：{changed_meta.get('name', '')}"
    rendered = [header]
    for row in rows:
        if not isinstance(row, dict):
            continue
        main = "　".join(
            filter(
                None,
                [
                    str(row.get("god", "")),
                    str(row.get("hidden", "")),
                    str(row.get("main_mark", "")),
                    str(row.get("main_relation", "")),
                    str(row.get("marker", "")),
                ],
            )
        )
        changed_relation = str(row.get("changed_relation", ""))
        if changed_relation:
            main += "　→　" + "　".join(
                filter(
                    None,
                    [str(row.get("changed_mark", "")), changed_relation],
                )
            )
        rendered.append(main)
    return "\n".join(rendered)


def build_session_najia_payload(
    main_entry: Optional[NajiaEntry],
    changed_entry: Optional[NajiaEntry],
    line_overview: List[Dict[str, object]],
    day_stem: Optional[str],
) -> Tuple[Dict[str, object], Dict[str, object], str]:
    najia_table = _build_najia_table(
        main_entry, changed_entry, line_overview, day_stem
    )
    rows = najia_table.get("rows")
    normalized_rows = rows if isinstance(rows, list) else []
    najia_text = _render_najia_text(najia_table)
    najia_data = {
        "main": _normalized_entry_payload(
            main_entry, normalized_rows, changed=False
        ),
        "changed": _normalized_entry_payload(
            changed_entry, normalized_rows, changed=True
        ),
        "block_text": najia_text,
        "day_stem": day_stem,
    }
    return najia_table, najia_data, najia_text


def _movement_tag_from_value(value: Optional[int]) -> str:
    if value == 6:
        return "×→"
    if value == 9:
        return "○→"
    return ""


@dataclass(slots=True)
class SessionResult:
    session_id: str
    timestamp: str
    topic: str
    user_question: Optional[str]
    user_context: Optional[str]
    method: str
    lines: List[int]
    current_time_str: str
    bazi_output: str
    elements_output: str
    hex_text: str
    hex_sections: List[Dict[str, object]]
    hex_overview: Dict[str, object]
    najia_text: str
    najia_data: Dict[str, object]
    najia_table: Dict[str, object]
    bazi_detail: List[Dict[str, object]]
    reading_brief: Dict[str, object]
    ai_model: Optional[str]
    ai_reasoning: Optional[str]
    ai_verbosity: Optional[str]
    ai_tone: Optional[str]
    ai_analysis: Optional[str]
    ai_response_id: Optional[str]
    ai_usage: Optional[Dict[str, int]]
    full_text: str = field(repr=False)
    #: Carried on the record so a follow-up answers in the reading's language.
    locale: str = "zh"
    #: The 换日 school this reading was cast under, stated rather than implied.
    day_boundary: str = READING_DAY_BOUNDARY
    #: Present only when the cast fell inside 子时; carries both schools'
    #: pillars when they disagree (23:00–23:59).
    zi_hour: Optional[Dict[str, object]] = None

    def to_dict(self) -> Dict[str, object]:
        payload = asdict(self)
        payload.pop("full_text", None)
        return payload


def _compact_text(value: object, *, limit: int = 180) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _extract_ai_headline(ai_text: Optional[str]) -> Optional[str]:
    """First line of the conclusion section, in whichever locale it came back."""
    headline = first_body_line(ai_text, "headline") or first_body_line(ai_text, "final")
    if headline:
        return _compact_text(headline, limit=96)
    for line in (ai_text or "").splitlines():
        stripped = line.strip()
        if not stripped or is_heading(stripped):
            continue
        cleaned = stripped.lstrip("-•0123456789. ").strip()
        if cleaned:
            return _compact_text(cleaned, limit=96)
    return None


#: Direction keywords in both locales. The Chinese-only matcher meant an
#: English reading always fell through to "observe".
#: A direction stem. On its own it is generic, so it is never rendered alone:
#: `_compose_direction` fastens it to this hexagram's own image or counsel.
_DIRECTION_STEMS = {
    "zh": {
        "stop": "此时不宜继续加码",
        "wait": "条件未到，先等关键触发",
        "adjust": "先改变推进方式，再谈加速",
        "advance": "方向可行，可以按条件推进",
        "transforming": "旧局正在整体转换",
        "changing": "变化已经开始",
        "observe": "先守住当前条件",
    },
    "en": {
        "stop": "not the moment to commit further",
        "wait": "the conditions are not in place yet",
        "adjust": "change how you are pushing before accelerating",
        "advance": "the direction holds",
        "transforming": "the whole situation is turning over",
        "changing": "the change has already started",
        "observe": "hold the position you have",
    },
}


def _compose_direction(
    kind: str,
    locale: str,
    *,
    main_name: str,
    changed_name: Optional[str],
    essence: Optional[object] = None,
    moving: Optional[List[int]] = None,
) -> str:
    """A direction line that could only have been written for this hexagram.

    The old version returned one fixed sentence per kind, so every reading of
    every hexagram with the same stance read identically. Name the hexagram,
    quote its own 大象, and say which lines moved.
    """
    stem = _DIRECTION_STEMS[locale].get(kind, _DIRECTION_STEMS[locale]["observe"])
    image = str(getattr(essence, "image", "") or "")
    moving = moving or []

    if locale == "en":
        parts = [f"{main_name}: {stem}"]
        if moving:
            joined = ", ".join(str(item) for item in moving)
            parts.append(f"line {joined} is moving" if len(moving) == 1 else f"lines {joined} are moving")
        if changed_name:
            parts.append(f"turning toward {changed_name}")
        return "; ".join(parts) + "."

    parts = [f"{main_name}：{stem}"]
    if image:
        parts.append(f"其象为{image}")
    if moving:
        joined = "、".join(str(item) for item in moving)
        parts.append(f"第{joined}爻动")
    if changed_name:
        parts.append(f"趋向{changed_name}")
    return "；".join(parts) + "。"


_DIRECTION_TOKENS: Tuple[Tuple[str, Tuple[str, ...], str], ...] = (
    ("stop", ("不利", "停止", "止步", "不要推进", "do not", "don't", "avoid", "hold off", "unfavourable", "unfavorable"),
     "当前条件不支持继续加码。"),
    ("wait", ("延迟", "等待", "暂缓", "待时", "wait", "delay", "postpone", "not yet"),
     "条件尚未成熟，先等关键触发出现。"),
    ("adjust", ("调整", "转向", "改变", "修正", "adjust", "pivot", "change course", "rework"),
     "先改变推进方式，再决定是否加速。"),
    ("advance", ("利成", "推进", "可行", "有利", "proceed", "advance", "go ahead", "favourable", "favorable"),
     "方向可行，按关键条件向前推进。"),
)


def _reading_direction(
    headline: str,
    stance: str,
    locale: str = "zh",
    *,
    main_name: str = "",
    changed_name: Optional[str] = None,
    essence: Optional[object] = None,
    moving: Optional[List[int]] = None,
) -> Dict[str, str]:
    locale = normalize_locale(locale)
    normalized = str(headline or "").casefold()

    def compose(kind: str, stem_key: str) -> Dict[str, str]:
        return {
            "kind": kind,
            "summary": _compose_direction(
                stem_key,
                locale,
                main_name=main_name or ("this hexagram" if locale == "en" else "本卦"),
                changed_name=changed_name,
                essence=essence,
                moving=moving,
            ),
        }

    for kind, tokens, _ in _DIRECTION_TOKENS:
        if any(token.casefold() in normalized for token in tokens):
            return compose(kind, kind)
    if stance == "transforming":
        return compose("adjust", "transforming")
    if stance == "changing":
        return compose("adjust", "changing")
    return compose("observe", "observe")


def _extract_ai_plain_language(ai_text: Optional[str]) -> Optional[str]:
    lines = parse_sections(ai_text).get("plain_language") or []
    if lines:
        return _compact_text(" ".join(lines), limit=260)
    return None


def _parse_confidence(value: str, default: int) -> int:
    match = re.search(r"(\d{1,3})", value or "")
    if not match:
        return default
    return max(0, min(100, int(match.group(1))))


def _extract_ai_timing(ai_text: Optional[str]) -> List[Dict[str, object]]:
    items: List[Dict[str, object]] = []
    for line in parse_sections(ai_text).get("timing") or []:
        parts = split_fields(line)
        window = field_value(parts, ("主应期", "次应期", "窗口", "Window", "Timing")) or (
            parts[0] if parts else ""
        )
        condition = field_value(parts, ("条件", "Condition", "Trigger"))
        confidence = _parse_confidence(
            field_value(parts, ("置信度", "Confidence")), 55
        )
        if window and condition:
            items.append(
                {
                    "window": _compact_text(window, limit=40),
                    "condition": _compact_text(condition, limit=140),
                    "confidence": confidence,
                }
            )
    return items[:3]


def _extract_ai_actions(ai_text: Optional[str]) -> List[Dict[str, object]]:
    items: List[Dict[str, object]] = []
    for line in parse_sections(ai_text).get("actions") or []:
        parts = split_fields(line)
        action = field_value(parts, ("动作", "Action", "Step")) or (parts[0] if parts else "")
        cadence = field_value(parts, ("节奏", "Cadence", "When"))
        signal = field_value(parts, ("观察指标", "指标", "Signal", "Watch"))
        if action:
            items.append(
                {
                    "action": _compact_text(action, limit=120),
                    "cadence": _compact_text(cadence or "下一步", limit=60),
                    "signal": _compact_text(signal or "观察阻力是否下降。", limit=100),
                }
            )
    return items[:4]


def _extract_ai_risks(ai_text: Optional[str]) -> List[str]:
    lines = parse_sections(ai_text).get("risks") or []
    return [_compact_text(line, limit=150) for line in lines if line][:4]


def _extract_ai_followups(ai_text: Optional[str]) -> List[str]:
    prompts = []
    for line in parse_sections(ai_text).get("followups") or []:
        cleaned = line.strip().strip("。")
        if cleaned:
            prompts.append(_compact_text(cleaned, limit=60))
    return prompts[:3]


def _moving_positions(lines: List[int]) -> List[int]:
    return [index + 1 for index, value in enumerate(lines) if value in {6, 9}]


def _source_id_for_section(section: Dict[str, object]) -> str:
    hexagram_name = str(section.get("hexagram_name") or "")
    slot_key = str(section.get("slot_key") or f"{hexagram_name}:{section.get('section_kind') or 'slot'}")
    source = str(section.get("source") or "unknown")
    return f"{slot_key}::{source}"


_BRIEF_COPY = {
    "zh": {
        "rule_basis": "主断依据",
        "rule_plain": "先确定本次阅读该看卦辞、动爻、用九/用六，还是变卦，再把文本和纳甲作为校验。",
        "najia": "纳甲参照",
        "najia_plain": "用纳甲表观察主客、阻力与触发点，作为经典文本之外的结构化参照。",
        "najia_basis": "纳甲六亲/六神",
        "time": "时间气象",
        "time_basis": "起卦时间八字",
        "classic": "经典文本",
        "changed_context": "这段只作为变化后的场景参照，帮助确认趋势落点，不替代本卦主断。",
        "all_moving": "全爻动时不把六爻平均展开，而是用这一段统摄整卦的变化方式。",
        "gua_context": "这段描述本卦的总体格局，用来判断当前局面的底色、边界和主方向。",
        "static_primary": "这段对应本次取用的静爻，描述变化之中没有被牵动、可以立足的位置。",
        "moving_primary": "这段对应本次取用的动爻，描述事情正在变化的位置、触发点与应对姿态。",
        "background_reason": "这段保留为本卦背景，用来校准取用判断的语境。",
        "no_moving_reason": "本卦无动爻，卦辞就是本次判断的核心依据。",
        "all_moving_reason": "六爻全动时需要用统摄性的全动规则，而不是把所有爻辞同时堆给用户。",
    },
    "en": {
        "rule_basis": "Basis of the judgement",
        "rule_plain": (
            "First settle whether this reading rests on the hexagram statement, a "
            "moving line, 用九/用六, or the changed hexagram; then use the text and "
            "Najia as a cross-check."
        ),
        "najia": "Najia cross-reference",
        "najia_plain": (
            "The Najia table shows subject and object, resistance and trigger points, "
            "as a structured check beside the classical text."
        ),
        "najia_basis": "Najia six relatives / six spirits",
        "time": "Time and season",
        "time_basis": "BaZi of the casting moment",
        "classic": "Classical text",
        "changed_context": (
            "This passage is context for the situation after the change. It confirms "
            "where the trend lands; it does not replace the main judgement."
        ),
        "all_moving": (
            "With every line moving, the six lines are not read one by one; this "
            "passage governs the change as a whole."
        ),
        "gua_context": (
            "This passage describes the overall shape of the present hexagram: the "
            "tone, the boundaries and the main direction."
        ),
        "static_primary": (
            "This is the static line the rule selects: the ground that is not being "
            "moved, and can be stood on."
        ),
        "moving_primary": (
            "This is the moving line the rule selects: where the situation is "
            "changing, what triggers it, and how to meet it."
        ),
        "background_reason": (
            "Kept as background for the present hexagram, to calibrate the selected line."
        ),
        "no_moving_reason": (
            "No lines are moving, so the hexagram statement is the core evidence."
        ),
        "all_moving_reason": (
            "With every line moving the reading needs one governing rule, not all six "
            "line texts at once."
        ),
    },
}


def _line_selection(hex_overview: Dict[str, object]) -> Dict[str, object]:
    """The 取用 rule as resolved by :class:`Hexagram`, never re-derived here.

    This used to be recomputed from ``lines`` in three places, each with its own
    idea of the rule, which is how a static line ended up described as 动爻.
    """
    selection = hex_overview.get("line_selection") if isinstance(hex_overview, dict) else None
    return selection if isinstance(selection, dict) else {}


def _basis_for_lines(
    lines: List[int],
    main_name: str,
    changed_name: Optional[str],
    selection: Optional[Dict[str, object]] = None,
    locale: str = "zh",
) -> str:
    selection = selection or {}
    locale = normalize_locale(locale)
    rule = str(selection.get("rule") or "")
    if locale == "en":
        rule_name = str(selection.get("rule_name_en") or selection.get("rule_name") or "")
        detail = str(selection.get("rule_detail_en") or selection.get("rule_detail") or "")
    else:
        rule_name = str(selection.get("rule_name") or "")
        detail = str(selection.get("rule_detail") or "")
    primary = selection.get("primary_line")
    role = str(selection.get("line_role") or "")
    secondary = [str(item) for item in (selection.get("secondary_lines") or [])]

    if not rule:  # Overview predates the structured selection.
        moving = _moving_positions(lines)
        if not moving:
            return "无动爻，取本卦卦辞为主"
        joined = "、".join(str(position) for position in moving)
        return f"第{joined}爻动，按动爻组合取主断"

    if locale == "en":
        role_en = "moving line" if selection.get("primary_is_moving") else "static line"
        if rule == "all-changed":
            return f"{rule_name} — {detail} ({changed_name or 'changed hexagram'})"
        if primary is None:
            return f"{rule_name} — {detail}"
        text = f"{rule_name} — {detail}; primary line {primary} ({role_en})"
        if secondary:
            text += f", read alongside line {', '.join(secondary)}"
        return text

    if rule == "all-changed":
        return f"{rule_name}，{detail}（{changed_name or '变卦'}）"
    if primary is None:
        return f"{rule_name}，{detail}"

    text = f"{rule_name}，{detail}；主爻为第{primary}爻（{role}）"
    if secondary:
        text += f"，并参第{'、'.join(secondary)}爻"
    return text


def _build_evidence_items(
    *,
    lines: List[int],
    hex_sections: List[Dict[str, object]],
    main_name: str,
    changed_name: Optional[str],
    najia_table: Dict[str, object],
    bazi_output: str,
    selection: Optional[Dict[str, object]] = None,
    locale: str = "zh",
) -> List[Dict[str, object]]:
    locale = normalize_locale(locale)
    copy = _BRIEF_COPY[locale]
    primary_sections = [
        section
        for section in hex_sections
        if section.get("visible_by_default") and section.get("content")
    ]
    primary_source_ids = [_source_id_for_section(section) for section in primary_sections[:3]]
    items: List[Dict[str, object]] = [
        {
            "conclusion": copy["rule_basis"],
            "basis": _basis_for_lines(lines, main_name, changed_name, selection, locale),
            "plain": copy["rule_plain"],
            "source_ids": primary_source_ids,
        }
    ]

    for section in primary_sections[:3]:
        title = str(section.get("title") or section.get("hexagram_name") or copy["classic"])
        source_label = str(section.get("source_label") or section.get("source") or copy["classic"])
        source_id = _source_id_for_section(section)
        if section.get("line_key") == "all":
            if "乾" in str(section.get("hexagram_name") or main_name):
                title = f"{title} · 用九"
            elif "坤" in str(section.get("hexagram_name") or main_name):
                title = f"{title} · 用六"
        items.append(
            {
                "conclusion": title,
                "basis": f"{source_label}｜{title}",
                "plain": _compact_text(section.get("content"), limit=180),
                "source_id": source_id,
                "source_ids": [source_id],
            }
        )

    rows = najia_table.get("rows") if isinstance(najia_table, dict) else None
    if isinstance(rows, list) and rows:
        moving_rows = [row for row in rows if isinstance(row, dict) and row.get("is_moving")]
        sample = moving_rows[0] if moving_rows else rows[0]
        relation = sample.get("main_relation") or sample.get("god") or "六亲六神"
        items.append(
            {
                "conclusion": copy["najia"],
                "basis": f"{copy['najia_basis']}｜{relation}",
                "plain": copy["najia_plain"],
                "source_ids": [],
            }
        )

    if bazi_output:
        items.append(
            {
                "conclusion": copy["time"],
                "basis": copy["time_basis"],
                "plain": _compact_text(bazi_output, limit=120),
                "source_ids": [],
            }
        )

    return items[:6]


def _build_source_passages(hex_sections: List[Dict[str, object]]) -> List[Dict[str, object]]:
    passages: List[Dict[str, object]] = []
    sorted_sections = sorted(
        [section for section in hex_sections if section.get("content")],
        key=lambda section: (
            not bool(section.get("visible_by_default")),
            str(section.get("slot_key") or ""),
            str(section.get("source") or ""),
            str(section.get("id") or ""),
        ),
    )
    for section in sorted_sections:
        source = str(section.get("source") or "unknown")
        source_label = str(section.get("source_label") or source)
        title = str(section.get("title") or section.get("hexagram_name") or "经典段落")
        hexagram_name = str(section.get("hexagram_name") or "")
        slot_key = str(section.get("slot_key") or f"{hexagram_name}:{section.get('section_kind') or 'slot'}")
        source_id = _source_id_for_section(section)
        passages.append(
            {
                "source_id": source_id,
                "slot_key": slot_key,
                "source": source,
                "source_label": source_label,
                "hexagram_name": hexagram_name,
                "section_kind": section.get("section_kind"),
                "line_key": section.get("line_key"),
                "title": title,
                "content": _compact_text(section.get("content"), limit=520),
                "citation": "｜".join(part for part in [source_label, hexagram_name, title] if part),
                "visible_by_default": bool(section.get("visible_by_default")),
                "importance": section.get("importance") or "secondary",
            }
        )
    return passages


def _key_source_order(section: Dict[str, object]) -> Tuple[int, str]:
    source_order = {
        "guaci": 0,
        "takashima": 1,
        "symbolic": 2,
        "english_commentary": 3,
    }
    source = str(section.get("source") or "")
    return (source_order.get(source, 9), source)


def _sort_key_sections(sections: List[Dict[str, object]]) -> List[Dict[str, object]]:
    return sorted(
        sections,
        key=lambda section: (
            str(section.get("slot_key") or ""),
            *_key_source_order(section),
            str(section.get("id") or ""),
        ),
    )


def _key_passage_plain(
    section: Dict[str, object],
    selection: Optional[Dict[str, object]] = None,
    locale: str = "zh",
) -> str:
    selection = selection or {}
    locale = normalize_locale(locale)
    copy = _BRIEF_COPY[locale]
    hex_type = str(section.get("hexagram_type") or "")
    section_kind = str(section.get("section_kind") or "")
    line_key = section.get("line_key")
    line_role = str(section.get("line_role") or "")
    is_moving = bool(selection.get("primary_is_moving", True))

    if hex_type == "changed":
        return copy["changed_context"]
    if line_key == "all":
        return copy["all_moving"]
    if section_kind == "line":
        if line_role == "secondary":
            if locale == "en":
                return (
                    "A line the rule reads alongside the primary one, filling in what a "
                    "single line cannot show."
                )
            role = str(selection.get("line_role") or "动爻")
            return f"这段是本次并参的爻位，与主{role}一起看，用来补足单爻看不全的部分。"
        # A four- or five-moving reading selects a STATIC line; calling it a
        # moving line told the reader the opposite of what the rule did.
        return copy["moving_primary"] if is_moving else copy["static_primary"]
    return copy["gua_context"]


def _key_passage_reason(
    *,
    section: Dict[str, object],
    lines: List[int],
    main_name: str,
    changed_name: Optional[str],
    selection: Optional[Dict[str, object]] = None,
    locale: str = "zh",
) -> str:
    selection = selection or {}
    locale = normalize_locale(locale)
    copy = _BRIEF_COPY[locale]
    rule = str(selection.get("rule") or "")
    if locale == "en":
        rule_name = str(selection.get("rule_name_en") or selection.get("rule_name") or "")
        detail = str(selection.get("rule_detail_en") or selection.get("rule_detail") or "")
    else:
        rule_name = str(selection.get("rule_name") or "")
        detail = str(selection.get("rule_detail") or "")
    role = str(selection.get("line_role") or "动爻")
    hex_type = str(section.get("hexagram_type") or "")
    section_kind = str(section.get("section_kind") or "")
    line_key = section.get("line_key")
    line_role = str(section.get("line_role") or "")

    if locale == "en":
        role_en = "moving line" if selection.get("primary_is_moving", True) else "static line"
        if hex_type == "changed":
            return (
                f"The changed hexagram {changed_name or ''} sits in the second layer as "
                "background; it does not take the primary evidence slot."
            ).strip()
        if rule == "none" and section_kind == "top":
            return copy["no_moving_reason"]
        if line_key == "all":
            if rule == "all-use":
                return (
                    "Every line is moving in 乾/坤, so tradition reads 用九/用六 as the "
                    "single governing judgement."
                )
            return copy["all_moving_reason"]
        if section_kind == "line":
            if line_role == "secondary":
                return f"{rule_name} — {detail}. This line is read alongside, to calibrate the primary one."
            if rule:
                return f"{rule_name} — {detail}. This is the {role_en} the rule selects."
            return f"This is the {role_en} the rule selects."
        return copy["background_reason"]

    if hex_type == "changed":
        return f"变卦{changed_name or ''}只放在第二层，说明变化后的背景，不抢主证据位置。"
    if rule == "none" and section_kind == "top":
        return copy["no_moving_reason"]
    if line_key == "all":
        if rule == "all-use":
            head = "乾卦" if "乾" in main_name else "坤卦" if "坤" in main_name else "本卦"
            return f"{head}六爻全动，传统以用九、用六为总断，不逐爻平均分散判断。"
        return copy["all_moving_reason"]
    if section_kind == "line":
        if line_role == "secondary":
            return f"{rule_name}的规则是{detail}，这一爻并参，用来校准主爻的判断。"
        if rule:
            return f"{rule_name}，{detail}；这是本次取用的{role}。"
        return f"这是本次取用的{role}。"
    return copy["background_reason"]


def _build_key_passages(
    *,
    hex_sections: List[Dict[str, object]],
    lines: List[int],
    main_name: str,
    changed_name: Optional[str],
    selection: Optional[Dict[str, object]] = None,
    locale: str = "zh",
) -> List[Dict[str, object]]:
    locale = normalize_locale(locale)
    sections = [section for section in hex_sections if section.get("content")]
    moving = _moving_positions(lines)

    if not moving:
        candidates = [
            section
            for section in sections
            if section.get("hexagram_type") == "main"
            and section.get("section_kind") == "top"
            and section.get("visible_by_default")
        ]
    elif len(moving) == 6 and (
        (all(value == 9 for value in lines) and "乾" in main_name)
        or (all(value == 6 for value in lines) and "坤" in main_name)
    ):
        candidates = [
            section
            for section in sections
            if section.get("hexagram_type") == "main"
            and section.get("section_kind") == "line"
            and section.get("line_key") == "all"
            and section.get("visible_by_default")
        ]
    elif len(moving) == 6:
        candidates = [
            section
            for section in sections
            if section.get("hexagram_type") == "changed"
            and section.get("section_kind") == "top"
            and section.get("visible_by_default")
        ]
    else:
        candidates = [
            section
            for section in sections
            if section.get("hexagram_type") == "main"
            and section.get("section_kind") == "line"
            and section.get("visible_by_default")
        ]

    if not candidates:
        candidates = [
            section for section in sections if section.get("visible_by_default")
        ]
    if not candidates:
        candidates = sections[:1]

    passages: List[Dict[str, object]] = []
    for section in _sort_key_sections(candidates)[:4]:
        source = str(section.get("source") or "unknown")
        source_label = str(section.get("source_label") or source)
        default_title = "Key passage" if locale == "en" else "关键段落"
        title = str(section.get("title") or section.get("hexagram_name") or default_title)
        hexagram_name = str(section.get("hexagram_name") or "")
        slot_key = str(section.get("slot_key") or f"{hexagram_name}:{section.get('section_kind') or 'slot'}")
        excerpt = _compact_text(section.get("content"), limit=360)
        source_id = _source_id_for_section(section)
        passages.append(
            {
                "source_id": source_id,
                "slot_key": slot_key,
                "role": "secondary_context"
                if section.get("hexagram_type") == "changed"
                else "primary",
                "source": source,
                "source_label": source_label,
                "hexagram_name": hexagram_name,
                "section_kind": section.get("section_kind"),
                "line_key": section.get("line_key"),
                "title": title,
                "content": excerpt,
                "quote": excerpt,
                "excerpt": excerpt,
                "plain_language": _key_passage_plain(section, selection, locale),
                "why_it_matters": _key_passage_reason(
                    section=section,
                    lines=lines,
                    main_name=main_name,
                    changed_name=changed_name,
                    selection=selection,
                    locale=locale,
                ),
                "citation": "｜".join(part for part in [source_label, hexagram_name, title] if part),
                "visible_by_default": bool(section.get("visible_by_default")),
                "importance": section.get("importance") or "primary",
            }
        )
    return passages


def _build_archive_sources(source_passages: List[Dict[str, object]]) -> Dict[str, object]:
    source_counts: Dict[str, int] = {}
    slot_keys: List[str] = []
    primary_slot_keys: List[str] = []
    for passage in source_passages:
        source = str(passage.get("source") or "unknown")
        source_counts[source] = source_counts.get(source, 0) + 1
        slot_key = str(passage.get("slot_key") or "")
        if slot_key and slot_key not in slot_keys:
            slot_keys.append(slot_key)
        if passage.get("visible_by_default") and slot_key and slot_key not in primary_slot_keys:
            primary_slot_keys.append(slot_key)
    return {
        "total_passages": len(source_passages),
        "sources": source_counts,
        "slot_keys": slot_keys,
        "primary_slot_keys": primary_slot_keys,
    }


def _fallback_action(
    locale: str,
    *,
    main_name: str,
    changed_name: Optional[str],
    essence: Optional[object],
    selection: Dict[str, object],
) -> Dict[str, str]:
    """A next step taken from this hexagram's own counsel.

    The constant it replaces — "先验证一个决定成败的条件，再决定是否加码。" —
    was true of any reading, so it told the reader nothing about theirs.
    """
    counsel = str(getattr(essence, "counsel", "") or "")
    trend = str(getattr(essence, "trend", "") or "")
    primary = selection.get("primary_line")
    role = str(selection.get("line_role") or "")

    if locale == "en":
        if counsel:
            action = f"Take {main_name}'s counsel 「{counsel}」 and turn it into one concrete move this week."
        elif trend:
            action = f"{main_name} reads: {trend}. Pick the one step that tests it."
        else:
            action = f"Test the single condition {main_name} turns on before committing further."
        cadence = f"At line {primary}" if primary else "Next step"
        signal = (
            f"Whether the situation starts moving toward {changed_name}."
            if changed_name
            else f"Whether {main_name}'s own condition holds."
        )
        return {"action": action, "cadence": cadence, "signal": signal}

    if counsel:
        action = f"取{main_name}之教「{counsel}」，先把它落成本周一件具体的事。"
    elif trend:
        action = f"{main_name}的运势是「{trend}」，先做一件能验证它的事。"
    else:
        action = f"先验证{main_name}最吃紧的那一个条件，再决定是否加码。"
    cadence = f"第{primary}爻（{role}）" if primary else "下一步"
    signal = (
        f"局面是否开始向{changed_name}移动。"
        if changed_name
        else f"{main_name}的本有条件是否仍然成立。"
    )
    return {"action": action, "cadence": cadence, "signal": signal}


def _fallback_followups(
    locale: str, *, main_name: str, changed_name: Optional[str], selection: Dict[str, object]
) -> List[str]:
    """Follow-up prompts that name this reading's own parts."""
    primary = selection.get("primary_line")
    if locale == "en":
        prompts = [f"What is the main risk {main_name} points to?"]
        if primary:
            prompts.append(f"What does line {primary} ask me to do first?")
        if changed_name:
            prompts.append(f"What changes once this becomes {changed_name}?")
        prompts.append(f"Read {main_name}'s classical text against the modern advice.")
        return prompts[:3]
    prompts = [f"{main_name}最吃紧的风险在哪里？"]
    if primary:
        prompts.append(f"第{primary}爻具体要我先做什么？")
    if changed_name:
        prompts.append(f"变为{changed_name}之后，哪一点会不一样？")
    prompts.append(f"请把{main_name}的原文与现代建议逐条对照。")
    return prompts[:3]


_PERSONAL_CONTEXT_NOTE = {
    "zh": "本阶段只使用起卦时间八字；用户出生信息、大运/流年/流月将作为后续独立个人画像层接入。",
    "en": (
        "This stage uses only the BaZi of the casting moment. Birth details and "
        "the Da Yun / annual / monthly layers arrive later as a separate profile."
    ),
}


def _fallback_plain_language(
    *,
    locale: str,
    user_question: Optional[str],
    user_context: Optional[str],
    method_name: str,
    main_name: str,
    changed_name: Optional[str],
    moving: List[int],
) -> str:
    """Plain-language summary when the model did not supply one."""
    if locale == "en":
        question_part = f"On \u201c{user_question}\u201d: " if user_question else ""
        context_part = (
            f" Background given: {_compact_text(user_context, limit=120)}."
            if user_context
            else ""
        )
        moving_part = (
            " No lines are moving, so read the situation as it stands."
            if not moving
            else f" {len(moving)} line(s) are moving, so the trigger points matter most."
        )
        becoming = f", becoming {changed_name}" if changed_name else ""
        return (
            f"{question_part}This reading used {method_name} and produced "
            f"{main_name}{becoming}.{context_part}{moving_part}"
        )
    question_part = f"\u56f4\u7ed5\u201c{user_question}\u201d\uff0c" if user_question else ""
    context_part = (
        f"\u5df2\u77e5\u80cc\u666f\u662f\uff1a{_compact_text(user_context, limit=120)}\u3002"
        if user_context
        else ""
    )
    moving_part = (
        "\u672c\u5366\u65e0\u52a8\u723b\uff0c\u91cd\u70b9\u770b\u5f53\u524d\u5c40\u52bf\u672c\u8eab\u3002"
        if not moving
        else f"\u672c\u6b21\u6709{len(moving)}\u4e2a\u52a8\u723b\uff0c\u91cd\u70b9\u770b\u53d8\u5316\u4e2d\u7684\u89e6\u53d1\u70b9\u3002"
    )
    becoming = f"\uff0c\u53d8\u4e3a{changed_name}" if changed_name else ""
    return (
        f"{question_part}\u672c\u6b21\u7528{method_name}\u8d77\u5f97{main_name}"
        f"{becoming}\u3002{context_part}{moving_part}"
    )


def _build_reading_brief(
    *,
    topic: str,
    user_question: Optional[str],
    user_context: Optional[str],
    method_name: str,
    lines: List[int],
    current_time_str: str,
    bazi_output: str,
    hex_sections: List[Dict[str, object]],
    hex_overview: Dict[str, object],
    najia_table: Dict[str, object],
    ai_analysis_text: Optional[str],
    locale: Optional[str] = None,
    essence: Optional[object] = None,
) -> Dict[str, object]:
    locale = normalize_locale(locale)
    main = hex_overview.get("main_hexagram") if isinstance(hex_overview, dict) else {}
    changed = hex_overview.get("changed_hexagram") if isinstance(hex_overview, dict) else {}
    main_name = str((main or {}).get("name") or "本卦")
    changed_name = str((changed or {}).get("name") or "") if changed else None
    selection = _line_selection(hex_overview)
    moving = _moving_positions(lines)
    ai_headline = _extract_ai_headline(ai_analysis_text)
    headline = ai_headline or f"{topic}｜{main_name}" + (f"之{changed_name}" if changed_name else "")
    plain = _extract_ai_plain_language(ai_analysis_text)
    if not plain:
        plain = _fallback_plain_language(
            locale=locale,
            user_question=user_question,
            user_context=user_context,
            method_name=method_name,
            main_name=main_name,
            changed_name=changed_name,
            moving=moving,
        )

    if not moving:
        stance = "stable"
    elif len(moving) == 6:
        stance = "transforming"
    else:
        stance = "changing"

    evidence = _build_evidence_items(
        lines=lines,
        hex_sections=hex_sections,
        main_name=main_name,
        changed_name=changed_name,
        najia_table=najia_table,
        bazi_output=bazi_output,
        selection=selection,
        locale=locale,
    )
    source_passages = _build_source_passages(hex_sections)
    key_passages = _build_key_passages(
        hex_sections=hex_sections,
        lines=lines,
        main_name=main_name,
        changed_name=changed_name,
        selection=selection,
        locale=locale,
    )
    archive_sources = _build_archive_sources(source_passages)

    fallback_timing: List[Dict[str, object]] = []
    fallback_actions = [
        _fallback_action(
            locale,
            main_name=main_name,
            changed_name=changed_name,
            essence=essence,
            selection=selection,
        )
    ]
    fallback_followups = _fallback_followups(
        locale, main_name=main_name, changed_name=changed_name, selection=selection
    )

    return {
        "headline": headline,
        "stance": stance,
        "direction": _reading_direction(
            headline,
            stance,
            locale,
            main_name=main_name,
            changed_name=changed_name,
            essence=essence,
            moving=moving,
        ),
        "plain_language": plain,
        "evidence": evidence,
        "key_passages": key_passages,
        "source_passages": source_passages[:12],
        "archive_sources": archive_sources,
        "personal_context": {
            "status": "reserved",
            "current_scope": "casting_time_bazi_only",
            "note": _PERSONAL_CONTEXT_NOTE[locale],
            "future_profile_fields": ["birth_datetime", "birth_place", "timezone", "gender_optional"],
        },
        "timing": _extract_ai_timing(ai_analysis_text) or fallback_timing,
        "actions": _extract_ai_actions(ai_analysis_text) or fallback_actions,
        "risks": _extract_ai_risks(ai_analysis_text),
        "followup_prompts": _extract_ai_followups(ai_analysis_text) or fallback_followups,
        "generated_at": current_time_str,
    }


class SessionService:
    """Central orchestrator for running I Ching sessions."""

    TOPIC_MAP = {
        "1": "事业",
        "2": "感情",
        "3": "财运",
        "4": "身体健康",
        "5": "整体运势",
        "6": "其他/跳过",
        "q": "就地退出",
    }

    def __init__(self, config: Optional[AppConfig] = None, *, history_limit: int = 100) -> None:
        self.config = config or build_app_config()
        self.definitions = load_hexagram_definitions(self.config.paths.gua_index_file)
        self.najia_repo = NajiaRepository(self.config.paths.najia_db)
        self.interpretation_repo = InterpretationRepository(
            db_path=self.config.paths.interpretation_db,
            index_file=self.config.paths.gua_index_file,
            guaci_dir=self.config.paths.guaci_dir,
            takashima_dir=self.config.paths.takashima_dir,
            symbolic_dir=self.config.paths.symbolic_dir,
            english_structured_dir=self.config.paths.english_structured_dir,
        )
        self._history: deque[SessionResult] = deque(maxlen=max(0, history_limit))

    @property
    def history(self) -> List[SessionResult]:
        return list(self._history)

    @property
    def methods(self) -> Dict[str, DivinationMethod]:
        return AVAILABLE_METHODS

    def run_console(
        self,
        *,
        input_func: Callable[[str], str] = _default_input,
        print_func: Callable[[str], None] = print,
        enable_ai: Optional[bool] = None,
    ) -> None:
        """Interactive CLI loop used by `iching5.py`."""
        from iching.core.system import display_system_usage
        from iching.services.logging import TeeLogger

        paths = self.config.paths
        enable_ai = self.config.enable_ai if enable_ai is None else enable_ai

        while True:
            output_dir = paths.archive_complete_dir
            with TeeLogger(output_dir) as logger:
                try:
                    print_func("\n欢迎使用理查德猪的易经占卜应用！")
                    print_func("\n请选择本次占卜主题：")
                    for key, label in self.TOPIC_MAP.items():
                        print_func(f"{key}. {label}")
                    topic_choice = self._get_valid_choice(
                        "\n请输入主题编号 (1-6): ",
                        choices=set(self.TOPIC_MAP.keys()),
                        input_func=input_func,
                        logger=logger,
                    )
                    topic = self.TOPIC_MAP[topic_choice]

                    specify_question = self._get_valid_choice(
                        "\n是否要输入一个具体问题？(y/n): ",
                        choices={"y", "n"},
                        input_func=input_func,
                        logger=logger,
                    )
                    user_question = None
                    if specify_question == "y":
                        user_question = input_func(
                            "\n请输入您的具体问题（按回车结束，或输入 'q' 退出）："
                        ).strip()
                        if user_question.lower() == "q":
                            print_func("\n感谢您使用易经占卜应用，再见！\n")
                            logger.output_dir = paths.archive_acquittal_dir
                            logger.save()
                            raise SystemExit(0)
                        if not user_question:
                            user_question = None

                    print_func(
                        "\n请选择占卜方法：\n"
                        "1. 五十蓍草法占卜 (输入 's')\n"
                        "2. 三枚铜钱法占卜 (输入 'c')\n"
                        "3. 梅花易数法占卜 (输入 'm')\n"
                        "4. 输入您自己的卦 (输入 'x')\n"
                        "r. 查看系统资源 (输入 'r')\n"
                        "q. 退出 (输入 'q')"
                    )
                    method_choice = self._get_valid_choice(
                        "\n您的选择: ",
                        choices=set(self.methods.keys()) | {"r"},
                        input_func=input_func,
                        logger=logger,
                    )
                    if method_choice == "r":
                        print_func(display_system_usage())
                        logger.output_dir = paths.archive_acquittal_dir
                        logger.save()
                        print_func("\n感谢您使用易经占卜应用，再见！\n")
                        raise SystemExit(0)

                    method = self.methods[method_choice]
                    current_time = None
                    if method.key == "m":
                        time_choice = self._get_valid_choice(
                            "\n使用当前时间进行计算请输入 '1'，输入您自己的时间请输入 '2': ",
                            choices={"1", "2"},
                            input_func=input_func,
                            logger=logger,
                        )
                        if time_choice == "1":
                            current_time = get_current_time()
                        else:
                            from iching.core.time_utils import get_user_time_input

                            current_time = get_user_time_input(input_func=input_func)
                    manual_lines = None
                    if method.key == "x":
                        manual_lines = method.generate_lines(
                            interactive=True, input_func=input_func
                        )
                    if manual_lines is not None:
                        lines = manual_lines
                    elif method.key == "m":
                        lines = method.generate_lines(
                            interactive=True,
                            input_func=input_func,
                            now_func=lambda: current_time,
                        )
                    else:
                        lines = method.generate_lines(
                            interactive=True, input_func=input_func
                        )

                    if method.key == "x":
                        time_choice = self._get_valid_choice(
                            "\n使用当前时间进行计算请输入 '1'，输入您自己的时间请输入 '2': ",
                            choices={"1", "2"},
                            input_func=input_func,
                            logger=logger,
                        )
                        if time_choice == "1":
                            current_time = get_current_time()
                        else:
                            from iching.core.time_utils import get_user_time_input

                            current_time = get_user_time_input(input_func=input_func)
                    elif current_time is None:
                        current_time = get_current_time()

                    result = self.create_session(
                        topic=topic,
                        user_question=user_question,
                        method_key=method.key,
                        lines_override=lines,
                        timestamp=current_time,
                        use_current_time=False,
                        enable_ai=enable_ai,
                        interactive=True,
                        input_func=input_func,
                    )

                    print_func("\n起卦时间:")
                    print_func(result.current_time_str)
                    print_func(result.bazi_output)
                    print_func(result.elements_output)
                    print_func(result.hex_text)
                    print_func("\n【纳甲六亲、六神、动爻等详细信息】")
                    print_func(result.najia_text or "(无数据)")
                    if result.ai_analysis:
                        print_func("\nAI 分析结果:\n" + result.ai_analysis)

                    again = input_func(
                        "\n请问您是否要再次卜卦？(如继续，请输入'y'，任何其他视为退出): "
                    ).strip()
                    logger.save()
                    if again.lower() != "y":
                        print_func("\n感谢您使用易经占卜应用，再见！\n")
                        break
                except SystemExit:
                    raise
                except Exception as exc:
                    print_func(f"发生异常: {exc}")
                    logger.output_dir = paths.archive_acquittal_dir
                    logger.save()
                    break

    def create_session(
        self,
        *,
        topic: str,
        user_question: Optional[str],
        method_key: str,
        user_context: Optional[str] = None,
        use_current_time: bool = True,
        timestamp: Optional[datetime] = None,
        manual_lines: Optional[List[int]] = None,
        lines_override: Optional[List[int]] = None,
        enable_ai: Optional[bool] = None,
        ai_model: Optional[str] = None,
        ai_reasoning: Optional[str] = None,
        ai_verbosity: Optional[str] = None,
        ai_tone: Optional[str] = "normal",
        locale: Optional[str] = None,
        api_key: Optional[str] = None,
        interactive: bool = False,
        input_func: Callable[[str], str] = _default_input,
    ) -> SessionResult:
        method = self.methods.get(method_key)
        if method is None:
            raise ValueError(f"未知的占卜方法: {method_key}")

        if use_current_time or timestamp is None:
            timestamp = get_current_time()

        if lines_override is not None:
            lines = lines_override
        else:
            lines = method.generate_lines(
                interactive=interactive,
                input_func=input_func,
                now_func=lambda: timestamp,
                manual_lines=manual_lines,
            )

        current_time_str = timestamp.strftime("%Y.%m.%d %H:%M")

        # A cast time is an instant, not testimony: no timezone to infer, no
        # DST fold to resolve. It still has to be an explicit instant, so a
        # naive timestamp is anchored to the server zone rather than silently
        # read as whatever clock this process runs on.
        pillar_time = timestamp if timestamp.tzinfo else timestamp.astimezone()
        pillars = four_pillars(pillar_time, day_boundary=READING_DAY_BOUNDARY)
        bazi_output = pillars.labelled_text
        elements_output = pillars.elements_text
        bazi_components = pillars.components
        bazi_detail = pillars.detail
        day_stem = pillars.day_stem
        zi_hour = zi_hour_notice(pillar_time)

        hexagram = Hexagram(lines, self.definitions)
        hex_text, hex_sections, hex_overview = hexagram.to_text_package(
            guaci_path=self.config.paths.guaci_dir,
            takashima_path=self.config.paths.takashima_dir,
            interpretation_repo=self.interpretation_repo,
        )

        main_najia_entry = self.najia_repo.get_by_bottom(hexagram.binary)
        changed_najia_entry = (
            self.najia_repo.get_by_bottom(hexagram.changed_hexagram.binary)
            if hexagram.changed_hexagram
            else None
        )
        najia_table, najia_data, najia_text = build_session_najia_payload(
            main_najia_entry, changed_najia_entry, hex_overview.get("lines", []), day_stem
        )

        ai_analysis_text = None
        ai_response_id: Optional[str] = None
        ai_usage: Optional[Dict[str, int]] = None
        tone_profile = ai_tone or "normal"
        should_use_ai = self.config.enable_ai if enable_ai is None else enable_ai
        model_hint = normalize_model_name(ai_model or self.config.preferred_ai_model or DEFAULT_MODEL)
        capabilities = MODEL_CAPABILITIES.get(model_hint, MODEL_CAPABILITIES[DEFAULT_MODEL])

        allowed_reasoning = capabilities.get("reasoning", [])
        default_reasoning = capabilities.get("default_reasoning")
        if allowed_reasoning:
            if ai_reasoning in allowed_reasoning:
                reasoning_effort = ai_reasoning
            else:
                reasoning_effort = default_reasoning or allowed_reasoning[0]
        else:
            reasoning_effort = None

        supports_verbosity = bool(capabilities.get("verbosity"))
        if supports_verbosity:
            default_verbosity = capabilities.get("default_verbosity", "medium")
            if ai_verbosity in {"low", "medium", "high"}:
                verbosity_level = ai_verbosity
            else:
                verbosity_level = default_verbosity
        else:
            verbosity_level = None

        resolved_locale = normalize_locale(locale)
        session_id = str(uuid4())
        session_payload = {
            "session_id": session_id,
            "locale": resolved_locale,
            "day_boundary": READING_DAY_BOUNDARY,
            "zi_hour": zi_hour,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "topic": topic,
            "user_question": user_question,
            "user_context": user_context,
            "method": method.name,
            "lines": lines,
            "current_time_str": current_time_str,
            "bazi_output": bazi_output,
            "elements_output": elements_output,
            "hex_text": hex_text,
            "hex_sections": hex_sections,
            "hex_overview": hex_overview,
            "bazi_detail": bazi_detail,
            "najia_data": najia_data,
            "najia_text": najia_text,
            "najia_table": najia_table,
            "ai_analysis": None,
            "ai_model": model_hint,
            "ai_reasoning": reasoning_effort,
            "ai_verbosity": verbosity_level,
            "ai_tone": tone_profile,
            "ai_response_id": None,
            "ai_usage": None,
        }

        if should_use_ai:
            ai_result = start_analysis(
                session_payload,
                api_key=api_key,
                model_hint=model_hint,
                interactive=interactive,
                reasoning_effort=reasoning_effort,
                verbosity=verbosity_level,
                tone=tone_profile,
                locale=resolved_locale,
            )
            if ai_result:
                ai_analysis_text = ai_result.text
                ai_response_id = ai_result.response_id
                ai_usage = ai_result.usage
                session_payload["ai_analysis"] = ai_analysis_text
                session_payload["ai_response_id"] = ai_response_id
                session_payload["ai_usage"] = ai_usage

        reading_brief = _build_reading_brief(
            topic=topic,
            user_question=user_question,
            user_context=user_context,
            method_name=method.name,
            lines=lines,
            current_time_str=current_time_str,
            bazi_output=bazi_output,
            hex_sections=hex_sections,
            hex_overview=hex_overview,
            najia_table=najia_table,
            ai_analysis_text=ai_analysis_text,
            locale=resolved_locale,
            essence=essence_for(hexagram.name, self.interpretation_repo),
        )
        session_payload["reading_brief"] = reading_brief

        chunks = [
            "起卦时间: " + current_time_str,
            ("背景补充: " + user_context) if user_context else "",
            bazi_output,
            elements_output,
            hex_text,
            "\n【纳甲六亲、六神、动爻等详细信息】",
            najia_text or "(无纳甲数据)",
        ]
        if ai_analysis_text:
            chunks.append("\n【AI 分析】\n" + ai_analysis_text)
        full_text = "\n".join(chunks)

        result = SessionResult(
            session_id=session_id,
            timestamp=session_payload["timestamp"],
            topic=topic,
            user_question=user_question,
            user_context=user_context,
            method=method.name,
            lines=lines,
            current_time_str=current_time_str,
            bazi_output=bazi_output,
            elements_output=elements_output,
            hex_text=hex_text,
            hex_sections=hex_sections,
            hex_overview=hex_overview,
            najia_text=najia_text,
            najia_data=session_payload["najia_data"],
            najia_table=najia_table,
            bazi_detail=bazi_detail,
            reading_brief=reading_brief,
            ai_model=session_payload.get("ai_model"),
            ai_reasoning=session_payload.get("ai_reasoning"),
            ai_verbosity=session_payload.get("ai_verbosity"),
            ai_tone=session_payload.get("ai_tone"),
            ai_analysis=ai_analysis_text,
            ai_response_id=session_payload.get("ai_response_id"),
            ai_usage=session_payload.get("ai_usage"),
            full_text=full_text,
            locale=resolved_locale,
            day_boundary=READING_DAY_BOUNDARY,
            zi_hour=zi_hour,
        )
        self._history.append(result)
        return result

    def _get_valid_choice(
        self,
        prompt: str,
        *,
        choices: set[str],
        input_func: Callable[[str], str],
        logger=None,
    ) -> str:
        quit_char = "q"
        valid_choices = {choice.lower() for choice in choices} | {quit_char}
        while True:
            answer = input_func(prompt).strip().lower()
            if answer == quit_char:
                print("\n感谢您使用易经占卜应用，再见！\n")
                if logger:
                    from iching.services.logging import TeeLogger

                    if isinstance(logger, TeeLogger):
                        logger.output_dir = self.config.paths.archive_acquittal_dir
                        logger.save()
                raise SystemExit(0)
            if answer in valid_choices:
                return answer
            print("输入无效，请重新输入。")
