from __future__ import annotations

import os
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple
from uuid import uuid4

from iching.config import AppConfig, PATHS, build_app_config
from iching.core.bazi import BaZiCalculator
from iching.core.divination import AVAILABLE_METHODS, DivinationMethod
from iching.core.hexagram import Hexagram, load_hexagram_definitions
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
from iching.integrations.najia_repository import NajiaEntry, NajiaRepository


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
    if not ai_text:
        return None
    lines = [line.strip() for line in ai_text.splitlines() if line.strip()]
    for index, line in enumerate(lines):
        normalized = line.lstrip("#").strip()
        if normalized in {"一句话结论", "最终判断"}:
            for candidate in lines[index + 1 :]:
                cleaned = candidate.lstrip("-•0123456789. ").strip()
                if cleaned and not cleaned.startswith("#"):
                    return _compact_text(cleaned, limit=96)
    for line in lines:
        if line.startswith("#"):
            continue
        cleaned = line.lstrip("-•0123456789. ").strip()
        if cleaned:
            return _compact_text(cleaned, limit=96)
    return None


def _extract_ai_plain_language(ai_text: Optional[str]) -> Optional[str]:
    if not ai_text:
        return None
    lines = [line.strip() for line in ai_text.splitlines()]
    capture = False
    collected: List[str] = []
    for line in lines:
        heading = line.lstrip("#").strip()
        if heading == "给普通人的解释":
            capture = True
            continue
        if capture and line.startswith("#"):
            break
        if capture and line:
            collected.append(line.lstrip("-• ").strip())
    if collected:
        return _compact_text(" ".join(collected), limit=260)
    return None


def _extract_ai_section_lines(ai_text: Optional[str], headings: set[str]) -> List[str]:
    if not ai_text:
        return []
    capture = False
    collected: List[str] = []
    for raw_line in ai_text.splitlines():
        line = raw_line.strip()
        heading = line.lstrip("#").strip()
        if heading in headings:
            capture = True
            continue
        if capture and line.startswith("#"):
            break
        if not capture or not line:
            continue
        cleaned = line.lstrip("-• ").strip()
        if cleaned:
            collected.append(cleaned)
    return collected


def _field_value(parts: List[str], labels: set[str]) -> str:
    for part in parts:
        for label in labels:
            prefix = f"{label}："
            if part.startswith(prefix):
                return part[len(prefix) :].strip()
            prefix = f"{label}:"
            if part.startswith(prefix):
                return part[len(prefix) :].strip()
    return ""


def _parse_confidence(value: str, default: int) -> int:
    match = re.search(r"(\d{1,3})", value or "")
    if not match:
        return default
    return max(0, min(100, int(match.group(1))))


def _extract_ai_timing(ai_text: Optional[str]) -> List[Dict[str, object]]:
    items: List[Dict[str, object]] = []
    for line in _extract_ai_section_lines(ai_text, {"应期与条件", "Timing and conditions"}):
        parts = [part.strip() for part in line.split("｜") if part.strip()]
        window = _field_value(parts, {"主应期", "次应期", "窗口", "Window"}) or (parts[0] if parts else "")
        condition = _field_value(parts, {"条件", "Condition"})
        confidence = _parse_confidence(_field_value(parts, {"置信度", "Confidence"}), 55)
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
    for line in _extract_ai_section_lines(ai_text, {"行动建议", "Actions"}):
        parts = [part.strip() for part in line.split("｜") if part.strip()]
        action = _field_value(parts, {"动作", "Action"}) or (parts[0] if parts else "")
        cadence = _field_value(parts, {"节奏", "Cadence"})
        signal = _field_value(parts, {"观察指标", "指标", "Signal"})
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
    lines = _extract_ai_section_lines(ai_text, {"风险与转折信号", "Risk signals"})
    return [_compact_text(line, limit=150) for line in lines if line][:4]


def _extract_ai_followups(ai_text: Optional[str]) -> List[str]:
    lines = _extract_ai_section_lines(ai_text, {"继续追问", "后续追问", "Continue with"})
    prompts = []
    for line in lines:
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


def _basis_for_lines(lines: List[int], main_name: str, changed_name: Optional[str]) -> str:
    moving = _moving_positions(lines)
    if not moving:
        return "无动爻，取本卦卦辞为主"
    if len(moving) == 6:
        if all(value == 9 for value in lines) and "乾" in main_name:
            return "六爻全动，乾卦取用九"
        if all(value == 6 for value in lines) and "坤" in main_name:
            return "六爻全动，坤卦取用六"
        return f"六爻全动，取变卦卦辞为主（{changed_name or '变卦'}）"
    if len(moving) == 1:
        return f"第{moving[0]}爻动，取动爻为主"
    joined = "、".join(str(position) for position in moving)
    return f"第{joined}爻动，按动爻组合取主断"


def _build_evidence_items(
    *,
    lines: List[int],
    hex_sections: List[Dict[str, object]],
    main_name: str,
    changed_name: Optional[str],
    najia_table: Dict[str, object],
    bazi_output: str,
) -> List[Dict[str, object]]:
    primary_sections = [
        section
        for section in hex_sections
        if section.get("visible_by_default") and section.get("content")
    ]
    primary_source_ids = [_source_id_for_section(section) for section in primary_sections[:3]]
    items: List[Dict[str, object]] = [
        {
            "conclusion": "主断依据",
            "basis": _basis_for_lines(lines, main_name, changed_name),
            "plain": "先确定本次阅读该看卦辞、动爻、用九/用六，还是变卦，再把文本和纳甲作为校验。",
            "source_ids": primary_source_ids,
        }
    ]

    for section in primary_sections[:3]:
        title = str(section.get("title") or section.get("hexagram_name") or "经典文本")
        source_label = str(section.get("source_label") or section.get("source") or "经典文本")
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
                "conclusion": "纳甲参照",
                "basis": f"纳甲六亲/六神｜{relation}",
                "plain": "用纳甲表观察主客、阻力与触发点，作为经典文本之外的结构化参照。",
                "source_ids": [],
            }
        )

    if bazi_output:
        items.append(
            {
                "conclusion": "时间气象",
                "basis": "起卦时间八字",
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


def _key_passage_plain(section: Dict[str, object]) -> str:
    hex_type = str(section.get("hexagram_type") or "")
    section_kind = str(section.get("section_kind") or "")
    line_key = section.get("line_key")
    if hex_type == "changed":
        return "这段只作为变化后的场景参照，帮助确认趋势落点，不替代本卦主断。"
    if line_key == "all":
        return "全爻动时不把六爻平均展开，而是用这一段统摄整卦的变化方式。"
    if section_kind == "line":
        return "这段对应本次被选中的爻位，描述事情正在变化的位置、触发点与应对姿态。"
    return "这段描述本卦的总体格局，用来判断当前局面的底色、边界和主方向。"


def _key_passage_reason(
    *,
    section: Dict[str, object],
    lines: List[int],
    main_name: str,
    changed_name: Optional[str],
) -> str:
    moving = _moving_positions(lines)
    hex_type = str(section.get("hexagram_type") or "")
    section_kind = str(section.get("section_kind") or "")
    line_key = section.get("line_key")

    if hex_type == "changed":
        return f"变卦{changed_name or ''}只放在第二层，说明变化后的背景，不抢主证据位置。"
    if not moving and section_kind == "top":
        return "本卦无动爻，卦辞就是本次判断的核心依据。"
    if line_key == "all":
        if all(value == 9 for value in lines) and "乾" in main_name:
            return "乾卦六爻全动，传统以用九为总断，不逐爻平均分散判断。"
        if all(value == 6 for value in lines) and "坤" in main_name:
            return "坤卦六爻全动，传统以用六为总断，不逐爻平均分散判断。"
        return "六爻全动时需要用统摄性的全动规则，而不是把所有爻辞同时堆给用户。"
    if section_kind == "line":
        return "这是本次取用的动爻，代表问题真正发生变化的关键位置。"
    return "这段保留为本卦背景，用来校准动爻判断的语境。"


def _build_key_passages(
    *,
    hex_sections: List[Dict[str, object]],
    lines: List[int],
    main_name: str,
    changed_name: Optional[str],
) -> List[Dict[str, object]]:
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
        title = str(section.get("title") or section.get("hexagram_name") or "关键段落")
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
                "plain_language": _key_passage_plain(section),
                "why_it_matters": _key_passage_reason(
                    section=section,
                    lines=lines,
                    main_name=main_name,
                    changed_name=changed_name,
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
) -> Dict[str, object]:
    main = hex_overview.get("main_hexagram") if isinstance(hex_overview, dict) else {}
    changed = hex_overview.get("changed_hexagram") if isinstance(hex_overview, dict) else {}
    main_name = str((main or {}).get("name") or "本卦")
    changed_name = str((changed or {}).get("name") or "") if changed else None
    moving = _moving_positions(lines)
    ai_headline = _extract_ai_headline(ai_analysis_text)
    headline = ai_headline or f"{topic}｜{main_name}" + (f"之{changed_name}" if changed_name else "")
    plain = _extract_ai_plain_language(ai_analysis_text)
    if not plain:
        question_part = f"围绕“{user_question}”，" if user_question else ""
        context_part = f"已知背景是：{_compact_text(user_context, limit=120)}。" if user_context else ""
        moving_part = (
            "本卦无动爻，重点看当前局势本身。"
            if not moving
            else f"本次有{len(moving)}个动爻，重点看变化中的触发点。"
        )
        plain = (
            f"{question_part}本次用{method_name}起得{main_name}"
            f"{('，变为' + changed_name) if changed_name else ''}。{context_part}{moving_part}"
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
    )
    source_passages = _build_source_passages(hex_sections)
    key_passages = _build_key_passages(
        hex_sections=hex_sections,
        lines=lines,
        main_name=main_name,
        changed_name=changed_name,
    )
    archive_sources = _build_archive_sources(source_passages)

    fallback_timing: List[Dict[str, object]] = []
    fallback_actions = [
        {
            "action": "先做一个低成本验证，不要一次性押上全部资源。",
            "cadence": "下一步",
            "signal": "记录实际反馈、资源是否到位，以及前提条件是否成立。",
        },
        {
            "action": "把关键风险写成可观察条件，再决定是否推进。",
            "cadence": "每次重大动作前",
            "signal": "条件满足则进，不满足则缓。",
        },
        {
            "action": "保留复盘记录，后续追问不要重新起卦。",
            "cadence": "出现新事实时",
            "signal": "同一问题的判断链保持连续。",
        },
    ]
    fallback_risks = [
        "只看结论而忽略动爻和文本依据，容易把复杂局势看得过于简单。",
        "如果问题本身过宽，判断会更偏趋势而不是具体执行方案。",
        "外部条件发生实质变化时，需要基于同一会话继续追问，而不是混用多个卦。",
    ]
    fallback_followups = [
        "这卦最关键的风险信号是什么？",
        "如果我要推进，第一步应该做什么？",
        "请把经典原文和现代建议逐条对照。",
    ]

    return {
        "headline": headline,
        "stance": stance,
        "plain_language": plain,
        "evidence": evidence,
        "key_passages": key_passages,
        "source_passages": source_passages[:12],
        "archive_sources": archive_sources,
        "personal_context": {
            "status": "reserved",
            "current_scope": "casting_time_bazi_only",
            "note": "本阶段只使用起卦时间八字；用户出生信息、大运/流年/流月将作为后续独立个人画像层接入。",
            "future_profile_fields": ["birth_datetime", "birth_place", "timezone", "gender_optional"],
        },
        "timing": _extract_ai_timing(ai_analysis_text) or fallback_timing,
        "actions": _extract_ai_actions(ai_analysis_text) or fallback_actions,
        "risks": _extract_ai_risks(ai_analysis_text) or fallback_risks,
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

    def __init__(self, config: Optional[AppConfig] = None) -> None:
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
        self._history: List[SessionResult] = []

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

        bazi_calculator = BaZiCalculator(timestamp)
        bazi_output, elements_output = bazi_calculator.calculate()
        bazi_components = bazi_calculator.last_components or {}
        bazi_detail = bazi_calculator.last_detail or []
        day_stem = bazi_components.get("day_stem")

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

        session_id = str(uuid4())
        session_payload = {
            "session_id": session_id,
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
