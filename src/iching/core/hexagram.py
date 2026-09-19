from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Iterable, List, Optional, Tuple

from iching.core.guaci_repository import load_guaci_by_name

if TYPE_CHECKING:
    from iching.integrations.interpretation_repository import (
        InterpretationEntry,
        InterpretationRepository,
    )


HexagramDefinition = Tuple[str, str]

QIAN_NAMES = {"乾为天", "乾卦"}
KUN_NAMES = {"坤为地", "坤卦"}
# 用九 / 用六 belong to 乾 and 坤 by structure, not by whatever the index file
# happens to call them. Matching on the name silently lost the rule whenever a
# definition file used a variant spelling.
USE_LINE_BINARIES = {"111111", "000000"}

#: How many lines each rule draws on, and whether the primary line is a moving
#: one. Four and five moving lines resolve to a *static* line.
LINE_RULE_LABELS = {
    "none": ("无动爻", "取本卦卦辞为主"),
    "one-moving": ("一爻动", "取该动爻爻辞为主"),
    "two-moving": ("二爻动", "一阴一阳取阴爻，同阴同阳取上动爻为主，另一动爻并参"),
    "three-moving": ("三爻动", "取中间动爻为主，其余二动爻并参"),
    "four-moving": ("四爻动", "取二静爻，以下静爻为主"),
    "five-moving": ("五爻动", "取唯一静爻"),
    "all-use": ("六爻全动", "乾坤取用九、用六"),
    "all-changed": ("六爻全动", "取变卦卦辞为主"),
}

LINE_RULE_LABELS_EN = {
    "none": ("No moving lines", "read the hexagram statement of the present hexagram"),
    "one-moving": ("One moving line", "read that line's text"),
    "two-moving": (
        "Two moving lines",
        "one yin and one yang takes the yin line; two alike takes the upper, "
        "with the other read alongside",
    ),
    "three-moving": (
        "Three moving lines",
        "take the middle moving line, with the other two read alongside",
    ),
    "four-moving": (
        "Four moving lines",
        "take the two unchanged lines, the lower one primary",
    ),
    "five-moving": ("Five moving lines", "take the single unchanged line"),
    "all-use": ("All six lines moving", "乾/坤 take 用九 / 用六"),
    "all-changed": (
        "All six lines moving",
        "read the hexagram statement of the changed hexagram",
    ),
}


@dataclass(frozen=True, slots=True)
class LineSelection:
    """Which line carries the reading, and what kind of line it is.

    ``strategy`` is the legacy value the text builders consume: ``None`` for no
    moving lines, ``"all"`` for 用九/用六, ``"all-move-other"`` for a full change
    in any other hexagram, otherwise a zero-based line index.
    """

    rule: str
    strategy: Optional[object]
    primary: Optional[int] = None
    secondary: Tuple[int, ...] = ()
    primary_is_moving: bool = False

    @property
    def primary_line_no(self) -> Optional[int]:
        """The primary line as a 1-based position, or ``None``."""
        return None if self.primary is None else self.primary + 1

    @property
    def secondary_line_nos(self) -> Tuple[int, ...]:
        return tuple(index + 1 for index in self.secondary)

    @property
    def rule_name(self) -> str:
        return LINE_RULE_LABELS.get(self.rule, ("", ""))[0]

    @property
    def rule_detail(self) -> str:
        return LINE_RULE_LABELS.get(self.rule, ("", ""))[1]

    @property
    def rule_name_en(self) -> str:
        return LINE_RULE_LABELS_EN.get(self.rule, ("", ""))[0]

    @property
    def rule_detail_en(self) -> str:
        return LINE_RULE_LABELS_EN.get(self.rule, ("", ""))[1]

    @property
    def line_role(self) -> str:
        """``动爻`` or ``静爻`` — what the selected line actually is."""
        if self.primary is None:
            return ""
        return "动爻" if self.primary_is_moving else "静爻"

    def describes_line(self, line_no: int) -> bool:
        return line_no == self.primary_line_no or line_no in self.secondary_line_nos


#: The corpus attaches a per-line note of the form
#: ``六四爻动变得周易第43卦：泽天夬。…`` to every line slot. It describes the
#: hexagram you reach when *that one line* moves, so it is only true for a
#: single-moving-line reading of that line. In every other configuration the
#: page ends up asserting one 变卦 in its header and a different one in the
#: body, and the model is fed the contradiction too.
_CHANGE_NOTE = re.compile(
    r"(?:^|\n)[^\n]{0,12}爻动变得周易第\d+卦[：:]\s*([^\s。，、；]+)[^\n]*(?:\n(?!\n)[^\n]*)*"
)


def drop_conflicting_change_note(content: Optional[str], changed_name: Optional[str]) -> Optional[str]:
    """Remove single-line 变卦 notes that disagree with this reading's 变卦.

    A note naming the hexagram this reading actually changes into is accurate
    and stays. Flipping a different set of lines always yields a different
    hexagram, so a name match is sufficient to prove the note consistent.
    """
    if not content or "爻动变得周易第" not in content:
        return content

    def replace(match: "re.Match[str]") -> str:
        named = match.group(1)
        if changed_name and named == changed_name:
            return match.group(0)
        return "\n" if match.group(0).startswith("\n") else ""

    cleaned = _CHANGE_NOTE.sub(replace, content)
    return re.sub(r"\n{3,}", "\n\n", cleaned).strip() or None


def _section_line_role(entry: object, info: "LineSelection") -> str:
    """Classify a section against the 取用 rule: primary, secondary, background."""
    slot_kind = getattr(entry, "slot_kind", "")
    line_key = getattr(entry, "line_key", None)
    if slot_kind == "gua":
        return "background"
    if slot_kind == "use":
        return "primary" if info.rule == "all-use" else "background"
    try:
        line_no = int(line_key)
    except (TypeError, ValueError):
        return "background"
    if line_no == info.primary_line_no:
        return "primary"
    if line_no in info.secondary_line_nos:
        return "secondary"
    return "background"


def load_hexagram_definitions(index_file: Path) -> Dict[str, HexagramDefinition]:
    """
    Load hexagram metadata from the CSV-like index file.

    The file is expected to contain lines formatted as:
        名称, binary_code, explanation
    """
    hexagrams: Dict[str, HexagramDefinition] = {}
    if not index_file.exists():
        raise FileNotFoundError(f"Hexagram index not found: {index_file}")

    with index_file.open("r", encoding="utf-8") as handle:
        for line in handle.readlines()[1:]:
            parts = [p.strip() for p in line.strip().split(",")]
            if len(parts) >= 3:
                name = parts[0]
                binary = parts[1]
                explanation = ",".join(parts[2:]).strip()
                hexagrams[binary] = (name, explanation)
    return hexagrams


@dataclass(slots=True)
class Hexagram:
    """Represents a hexagram and its related derived forms."""

    lines: List[int]
    definitions: Dict[str, HexagramDefinition]
    binary: str = field(init=False)
    name: str = field(init=False)
    explanation: str = field(init=False)
    changed_hexagram: Optional["Hexagram"] = field(init=False, default=None)
    inverse_hexagram: Tuple[str, str] = field(init=False, default=("未知卦", "未找到解释"))
    reverse_hexagram: Tuple[str, str] = field(init=False, default=("未知卦", "未找到解释"))
    mutual_hexagram: Tuple[str, str] = field(init=False, default=("未知卦", "未找到解释"))

    def __post_init__(self) -> None:
        self.binary = "".join("1" if value in (7, 9) else "0" for value in self.lines)
        name, explanation = self.definitions.get(self.binary, ("未知卦", "未找到解释"))
        self.name = name
        self.explanation = explanation

        self.changed_hexagram = self._calculate_changed_hexagram()
        self.inverse_hexagram = self._lookup_hexagram(self._inverse_binary(self.binary))
        self.reverse_hexagram = self._lookup_hexagram(self.binary[::-1])
        self.mutual_hexagram = self._lookup_hexagram(self._mutual_binary(self.binary))

    @property
    def reversed_lines(self) -> Iterable[Tuple[int, int]]:
        for position, line in enumerate(reversed(self.lines), start=1):
            yield 7 - position, line

    def _calculate_changed_hexagram(self) -> Optional["Hexagram"]:
        changed_lines: List[int] = []
        has_moving_line = False
        for value in self.lines:
            if value == 9:
                changed_lines.append(8)
                has_moving_line = True
            elif value == 6:
                changed_lines.append(7)
                has_moving_line = True
            else:
                changed_lines.append(value)
        if has_moving_line:
            return Hexagram(changed_lines, self.definitions)
        return None

    def _lookup_hexagram(self, binary: Optional[str]) -> Tuple[str, str]:
        if not binary:
            return "未知卦", "未找到解释"
        return self.definitions.get(binary, ("未知卦", "未找到解释"))

    @staticmethod
    def _inverse_binary(binary: str) -> str:
        return "".join("1" if bit == "0" else "0" for bit in binary)

    @staticmethod
    def _mutual_binary(binary: str) -> Optional[str]:
        if len(binary) == 6:
            return binary[1:4] + binary[2:5]
        return None

    def render_lines(self) -> List[str]:
        rendered: List[str] = []
        for index, value in enumerate(reversed(self.lines), start=1):
            symbol = "---" if value in (7, 9) else "- -"
            moving = " O" if value == 9 else " X" if value == 6 else ""
            rendered.append(f"第 {7 - index} 爻: {symbol}{moving}")
        return rendered

    def to_text(
        self,
        *,
        guaci_path: Optional[Path] = None,
        takashima_path: Optional[Path] = None,
        interpretation_repo: Optional["InterpretationRepository"] = None,
    ) -> str:
        """Build the legacy textual representation used by downstream consumers."""
        summary, _, _ = self.to_text_package(
            guaci_path=guaci_path,
            takashima_path=takashima_path,
            interpretation_repo=interpretation_repo,
        )
        return summary

    def to_text_package(
        self,
        *,
        guaci_path: Optional[Path] = None,
        takashima_path: Optional[Path] = None,
        interpretation_repo: Optional["InterpretationRepository"] = None,
    ) -> Tuple[str, List[Dict[str, object]], Dict[str, object]]:
        """Return the focused summary text, structured sections, and overview metadata."""
        info = self.line_selection()
        selection = info.strategy
        main_text, main_line_text, changed_header, changed_text = self._build_interpretation(
            guaci_path=guaci_path,
            selection=selection,
            interpretation_repo=interpretation_repo,
        )
        summary = self._compose_summary(
            info, main_text, main_line_text, changed_header, changed_text
        )
        sections = self._collect_sections(
            selection,
            guaci_path,
            takashima_path,
            interpretation_repo=interpretation_repo,
            info=info,
        )
        overview = self._build_overview()
        overview["line_selection"] = {
            "rule": info.rule,
            "rule_name": info.rule_name,
            "rule_detail": info.rule_detail,
            "rule_name_en": info.rule_name_en,
            "rule_detail_en": info.rule_detail_en,
            "primary_line": info.primary_line_no,
            "secondary_lines": list(info.secondary_line_nos),
            "primary_is_moving": info.primary_is_moving,
            "line_role": info.line_role,
        }
        return summary, sections, overview

    def _compose_summary(
        self,
        info: "LineSelection",
        main_text: Optional[str],
        main_line_text: Optional[str],
        changed_header: Optional[str],
        changed_text: Optional[str],
    ) -> str:
        chunks: List[str] = ["\n您的卦象:"]
        chunks.extend(self.render_lines())
        chunks.append("")
        chunks.append(f"本卦: {self.name} - 解释: {self.explanation}")

        top_changed_line: Optional[str] = None
        if self.changed_hexagram:
            top_changed_line = (
                f"变卦: {self.changed_hexagram.name} - 解释: {self.changed_hexagram.explanation}"
            )
        elif changed_header and "没有动爻" in changed_header:
            top_changed_line = changed_header.strip()
            changed_header = None

        if top_changed_line:
            chunks.append(top_changed_line)

        # State the 取用 rule explicitly: which line the reading rests on and
        # whether that line moved. Readers and the model both used to have to
        # infer this, and the old labels inferred it wrongly.
        basis = f"取用: {info.rule_name} · {info.rule_detail}"
        if info.primary_line_no is not None:
            basis += f"；主爻为第{info.primary_line_no}爻（{info.line_role}）"
            if info.secondary_line_nos:
                joined = "、".join(str(no) for no in info.secondary_line_nos)
                basis += f"，并参第{joined}爻"
        chunks.append(basis)

        chunks.append("────────────────────────")

        if main_text:
            chunks.append(main_text)
        if main_line_text:
            chunks.append(main_line_text)

        if changed_text:
            if self.changed_hexagram:
                # Four and five moving lines select a STATIC line, so the old
                # unconditional "变卦动爻" named it as the very thing it is not.
                if info.rule == "all-changed":
                    label = "变卦详解"
                elif info.primary_line_no is None:
                    label = "变卦对读"
                else:
                    label = f"变卦第{info.primary_line_no}爻（本卦{info.line_role}）"
                chunks.append(f"\n【{label}】\n{changed_text}")
            else:
                if changed_header:
                    chunks.append(changed_header)
                chunks.append(changed_text)
        elif changed_header and not self.changed_hexagram:
            chunks.append(changed_header)

        inverse_name, inverse_explanation = self.inverse_hexagram
        chunks.append(f"错卦: {inverse_name} - 解释: {inverse_explanation}")

        reverse_name, reverse_explanation = self.reverse_hexagram
        chunks.append(f"综卦: {reverse_name} - 解释: {reverse_explanation}")

        mutual_name, mutual_explanation = self.mutual_hexagram
        if mutual_name != "未知卦":
            chunks.append(f"互卦: {mutual_name} - 解释: {mutual_explanation}")
        else:
            chunks.append("互卦未找到。")

        return "\n".join(filter(None, chunks))

    # ------------------------------------------------------------------ #
    # Interpretation helpers
    # ------------------------------------------------------------------ #

    def _build_interpretation(
        self,
        *,
        guaci_path: Optional[Path],
        selection: Optional[object],
        interpretation_repo: Optional["InterpretationRepository"] = None,
    ) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
        if interpretation_repo is not None:
            return self._build_interpretation_from_repository(
                interpretation_repo=interpretation_repo,
                selection=selection,
            )

        if not guaci_path:
            return None, None, None, None

        try:
            main_guaci = load_guaci_by_name(self.name, guaci_path)
        except FileNotFoundError:
            return None, None, None, None

        main_top_text = main_guaci.combine_top() or None
        main_line_text: Optional[str] = None
        changed_header: Optional[str] = None
        changed_text: Optional[str] = None

        if selection is None:
            changed_header = None
            if self.changed_hexagram is None:
                changed_header = "变卦：没有动爻，故无变卦。"
            return main_top_text, None, changed_header, None

        if selection == "all-move-other":
            # Use only the transformed hexagram's guaci text.
            if self.changed_hexagram:
                try:
                    changed_data = load_guaci_by_name(
                        self.changed_hexagram.name, guaci_path
                    )
                except FileNotFoundError:
                    changed_data = None
                if changed_data:
                    combined = changed_data.combine_top() or None
                    if combined:
                        changed_header = (
                            f"\n变卦: {self.changed_hexagram.name} - 解释: {self.changed_hexagram.explanation}"
                        )
                        changed_text = combined
            return None, None, changed_header, changed_text

        if selection == "all":
            main_line_text = main_guaci.combine_line("all")
        elif isinstance(selection, int):
            line_key = str(selection + 1)
            main_line_text = main_guaci.combine_line(line_key)

            if self.changed_hexagram:
                try:
                    changed_data = load_guaci_by_name(
                        self.changed_hexagram.name, guaci_path
                    )
                except FileNotFoundError:
                    changed_data = None
                if changed_data:
                    changed_line = changed_data.combine_line(line_key)
                    if changed_line:
                        changed_header = (
                            f"\n变卦: {self.changed_hexagram.name} - 解释: {self.changed_hexagram.explanation}"
                        )
                        changed_text = changed_line
        return main_top_text, main_line_text, changed_header, changed_text

    def _build_interpretation_from_repository(
        self,
        *,
        interpretation_repo: "InterpretationRepository",
        selection: Optional[object],
    ) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
        main_top_text = interpretation_repo.get_slot_content(
            hexagram_name=self.name,
            source_key="guaci",
            slot_kind="gua",
        )
        main_line_text: Optional[str] = None
        changed_header: Optional[str] = None
        changed_text: Optional[str] = None

        if selection is None:
            if self.changed_hexagram is None:
                changed_header = "变卦：没有动爻，故无变卦。"
            return main_top_text, None, changed_header, None

        if selection == "all-move-other":
            if self.changed_hexagram:
                changed_top = interpretation_repo.get_slot_content(
                    hexagram_name=self.changed_hexagram.name,
                    source_key="guaci",
                    slot_kind="gua",
                )
                if changed_top:
                    changed_header = (
                        f"\n变卦: {self.changed_hexagram.name} - 解释: {self.changed_hexagram.explanation}"
                    )
                    changed_text = changed_top
            return None, None, changed_header, changed_text

        if selection == "all":
            main_line_text = interpretation_repo.get_slot_content(
                hexagram_name=self.name,
                source_key="guaci",
                slot_kind="use",
            )
            return main_top_text, main_line_text, changed_header, changed_text

        if isinstance(selection, int):
            line_no = selection + 1
            changed_name = self.changed_hexagram.name if self.changed_hexagram else None
            main_line_text = drop_conflicting_change_note(
                interpretation_repo.get_slot_content(
                    hexagram_name=self.name,
                    source_key="guaci",
                    slot_kind="line",
                    line_no=line_no,
                ),
                changed_name,
            )
            if self.changed_hexagram:
                # The 变卦's own per-line note points somewhere else again.
                changed_line = drop_conflicting_change_note(
                    interpretation_repo.get_slot_content(
                        hexagram_name=self.changed_hexagram.name,
                        source_key="guaci",
                        slot_kind="line",
                        line_no=line_no,
                    ),
                    None,
                )
                if changed_line:
                    changed_header = (
                        f"\n变卦: {self.changed_hexagram.name} - 解释: {self.changed_hexagram.explanation}"
                    )
                    changed_text = changed_line

        return main_top_text, main_line_text, changed_header, changed_text

    def _collect_sections(
        self,
        selection: Optional[object],
        guaci_path: Optional[Path],
        takashima_path: Optional[Path],
        interpretation_repo: Optional["InterpretationRepository"] = None,
        info: Optional["LineSelection"] = None,
    ) -> List[Dict[str, object]]:
        if interpretation_repo is not None:
            repo_sections = self._collect_sections_from_repository(
                selection=selection,
                interpretation_repo=interpretation_repo,
                info=info or self.line_selection(),
            )
            if repo_sections:
                return repo_sections

        if not guaci_path and not takashima_path:
            return []

        sections: List[Dict[str, object]] = []

        if guaci_path:
            try:
                main_guaci = load_guaci_by_name(self.name, guaci_path)
            except FileNotFoundError:
                main_guaci = None
        else:
            main_guaci = None

        changed_data = None
        if self.changed_hexagram and guaci_path:
            try:
                changed_data = load_guaci_by_name(self.changed_hexagram.name, guaci_path)
            except FileNotFoundError:
                changed_data = None

        if takashima_path:
            try:
                main_takashima = load_guaci_by_name(self.name, takashima_path)
            except FileNotFoundError:
                main_takashima = None
        else:
            main_takashima = None

        changed_takashima = None
        if self.changed_hexagram and takashima_path:
            try:
                changed_takashima = load_guaci_by_name(
                    self.changed_hexagram.name, takashima_path
                )
            except FileNotFoundError:
                changed_takashima = None

        def add_section(
            hex_type: str,
            name: str,
            section_kind: str,
            line_key: Optional[str],
            content: Optional[str],
            visible: bool,
            source: str = "guaci",
        ) -> None:
            if not content:
                return
            prefix = "本卦" if hex_type == "main" else "变卦"
            if source == "takashima":
                if section_kind == "top":
                    title = f"{prefix} · 高岛易断总览"
                elif line_key == "all":
                    title = f"{prefix} · 高岛易断 · 全动爻"
                else:
                    title = f"{prefix} · 高岛易断 · 第{line_key}爻"
            else:
                if section_kind == "top":
                    title = f"{prefix} · 卦辞总览"
                elif line_key == "all":
                    title = f"{prefix} · 全爻总览"
                else:
                    title = f"{prefix} · 第{line_key}爻"
            sections.append(
                {
                    "id": f"{hex_type}-{source}-{section_kind}-{line_key or 'top'}",
                    "hexagram_type": hex_type,
                    "hexagram_name": name,
                    "source": source,
                    "source_label": "高岛易断" if source == "takashima" else "卦辞库",
                    "slot_key": f"{name}.{line_key or 'gua'}",
                    "section_kind": section_kind,
                    "line_key": line_key,
                    "title": title,
                    "content": content,
                    "importance": "primary" if visible else "secondary",
                    "visible_by_default": visible,
                }
            )

        def sorted_keys(entries: Dict[str, object]) -> List[str]:
            def sort_key(value: str) -> Tuple[int, str]:
                if value == "all":
                    return (99, value)
                try:
                    return (int(value), value)
                except ValueError:
                    return (100, value)

            return sorted(entries.keys(), key=sort_key)

        def takashima_top(data: Optional[object]) -> Optional[str]:
            if data is None:
                return None
            top_sections = getattr(data, "top_sections", {})
            value = top_sections.get("takashima")
            return value if value else None

        def takashima_line(data: Optional[object], key: str) -> Optional[str]:
            if data is None:
                return None
            line_sections = getattr(data, "line_sections", {})
            line = line_sections.get(key)
            if not line:
                return None
            value = line.sections.get("takashima")
            return value if value else None

        selected_main_line: Optional[str] = None
        if selection == "all":
            selected_main_line = "all"
        elif isinstance(selection, int):
            selected_main_line = str(selection + 1)

        selected_changed_line: Optional[str] = None
        if selection == "all":
            selected_changed_line = "all"
        elif isinstance(selection, int):
            selected_changed_line = str(selection + 1)

        # Main hexagram sections
        if main_guaci:
            main_top = main_guaci.combine_top()
            show_main_top = selection != "all-move-other"
            add_section("main", self.name, "top", None, main_top, show_main_top)

            for key in sorted_keys(main_guaci.line_sections):
                content = main_guaci.combine_line(key)
                add_section(
                    "main",
                    self.name,
                    "line",
                    key,
                    content,
                    visible=(key == selected_main_line),
                )

        if main_takashima:
            add_section(
                "main",
                self.name,
                "top",
                None,
                takashima_top(main_takashima),
                selection != "all-move-other",
                source="takashima",
            )
            for key in sorted_keys(main_takashima.line_sections):
                add_section(
                    "main",
                    self.name,
                    "line",
                    key,
                    takashima_line(main_takashima, key),
                    visible=(key == selected_main_line),
                    source="takashima",
                )

        # Changed hexagram sections
        if self.changed_hexagram and changed_data:
            changed_top = changed_data.combine_top()
            show_changed_top = selection == "all-move-other"
            add_section(
                "changed",
                self.changed_hexagram.name,
                "top",
                None,
                changed_top,
                show_changed_top,
            )

            for key in sorted_keys(changed_data.line_sections):
                content = changed_data.combine_line(key)
                add_section(
                    "changed",
                    self.changed_hexagram.name,
                    "line",
                    key,
                    content,
                    visible=(key == selected_changed_line and selection != "all-move-other"),
                )

        if self.changed_hexagram and changed_takashima:
            add_section(
                "changed",
                self.changed_hexagram.name,
                "top",
                None,
                takashima_top(changed_takashima),
                selection == "all-move-other",
                source="takashima",
            )
            for key in sorted_keys(changed_takashima.line_sections):
                add_section(
                    "changed",
                    self.changed_hexagram.name,
                    "line",
                    key,
                    takashima_line(changed_takashima, key),
                    visible=(key == selected_changed_line and selection != "all-move-other"),
                    source="takashima",
                )

        return sections

    def _collect_sections_from_repository(
        self,
        *,
        selection: Optional[object],
        interpretation_repo: "InterpretationRepository",
        info: Optional["LineSelection"] = None,
    ) -> List[Dict[str, object]]:
        info = info or self.line_selection()
        main_entries = interpretation_repo.list_entries(
            hexagram_name=self.name,
            locale="zh-CN",
            source_keys=("guaci", "takashima", "symbolic"),
        )
        main_english_entries = interpretation_repo.list_entries(
            hexagram_name=self.name,
            locale="en-US",
            source_keys=("english_commentary",),
        )
        changed_entries: List["InterpretationEntry"] = []
        changed_english_entries: List["InterpretationEntry"] = []
        if self.changed_hexagram:
            changed_entries = interpretation_repo.list_entries(
                hexagram_name=self.changed_hexagram.name,
                locale="zh-CN",
                source_keys=("guaci", "takashima", "symbolic"),
            )
            changed_english_entries = interpretation_repo.list_entries(
                hexagram_name=self.changed_hexagram.name,
                locale="en-US",
                source_keys=("english_commentary",),
            )

        # Lines the classical rule names: the primary one plus the secondaries
        # that used to be computed and then dropped on the floor.
        relevant_lines: set[str] = set()
        if selection == "all":
            relevant_lines.add("all")
        elif isinstance(selection, int):
            relevant_lines.add(str(selection + 1))
            relevant_lines.update(str(no) for no in info.secondary_line_nos)

        def line_is_relevant(entry: "InterpretationEntry") -> bool:
            return entry.line_key in relevant_lines

        def is_visible(entry: "InterpretationEntry", *, changed: bool) -> bool:
            # english_commentary is the entire body of text an English reader
            # gets. Hiding it by source left the English reading with zero
            # visible passages while the Chinese one showed six.
            if selection == "all-move-other":
                return entry.slot_kind == "gua" if changed else False
            if entry.slot_kind == "gua":
                return not changed
            return line_is_relevant(entry)

        changed_name = self.changed_hexagram.name if self.changed_hexagram else None

        def is_visible_main(entry: "InterpretationEntry") -> bool:
            return is_visible(entry, changed=False)

        def is_visible_changed(entry: "InterpretationEntry") -> bool:
            return is_visible(entry, changed=True)

        def title_for(entry: "InterpretationEntry", hex_type: str) -> str:
            prefix = "本卦" if hex_type == "main" else "变卦"
            if entry.source_key == "takashima":
                if entry.slot_kind == "gua":
                    return f"{prefix} · 高岛易断总览"
                if entry.slot_kind == "use":
                    return f"{prefix} · 高岛易断 · 全动爻"
                return f"{prefix} · 高岛易断 · 第{entry.line_key}爻"
            if entry.source_key == "symbolic":
                if entry.slot_kind == "gua":
                    return f"{prefix} · 八卦象意总览"
                if entry.slot_kind == "use":
                    return f"{prefix} · 八卦象意 · 全动爻"
                return f"{prefix} · 八卦象意 · 第{entry.line_key}爻"
            if entry.source_key == "english_commentary":
                # An English reader saw "本卦 · English Commentary · Line 1".
                english_prefix = "Present" if hex_type == "main" else "Becoming"
                if entry.slot_kind == "gua":
                    return f"{english_prefix} · English Commentary"
                if entry.slot_kind == "use":
                    return f"{english_prefix} · English Commentary · All Moving Lines"
                return f"{english_prefix} · English Commentary · Line {entry.line_key}"
            if entry.slot_kind == "gua":
                return f"{prefix} · 卦辞总览"
            if entry.slot_kind == "use":
                return f"{prefix} · 全爻总览"
            return f"{prefix} · 第{entry.line_key}爻"

        sections: List[Dict[str, object]] = []

        def add_entries(
            *,
            entries: Iterable["InterpretationEntry"],
            hex_type: str,
            hex_name: str,
            visible_check,
        ) -> None:
            for entry in entries:
                visible = bool(visible_check(entry))
                section_kind = "top" if entry.slot_kind == "gua" else "line"
                sections.append(
                    {
                        "id": f"{hex_type}-{entry.source_key}-{entry.slot_key}",
                        "hexagram_type": hex_type,
                        "hexagram_name": hex_name,
                        "source": entry.source_key,
                        "source_label": entry.source_label,
                        "slot_key": entry.slot_key,
                        "section_kind": section_kind,
                        "line_key": entry.line_key,
                        "title": title_for(entry, hex_type),
                        "content": drop_conflicting_change_note(
                            entry.content,
                            changed_name if hex_type == "main" else None,
                        ),
                        "importance": "primary" if visible else "secondary",
                        "visible_by_default": visible,
                        # "primary" | "secondary" | "background": lets callers
                        # label a section without re-deriving the 取用 rule.
                        "line_role": _section_line_role(entry, info),
                    }
                )

        add_entries(
            entries=main_entries,
            hex_type="main",
            hex_name=self.name,
            visible_check=is_visible_main,
        )
        add_entries(
            entries=main_english_entries,
            hex_type="main",
            hex_name=self.name,
            visible_check=is_visible_main,
        )

        if self.changed_hexagram:
            add_entries(
                entries=changed_entries,
                hex_type="changed",
                hex_name=self.changed_hexagram.name,
                visible_check=is_visible_changed,
            )
            add_entries(
                entries=changed_english_entries,
                hex_type="changed",
                hex_name=self.changed_hexagram.name,
                visible_check=is_visible_changed,
            )

        return sections

    def _build_overview(self) -> Dict[str, object]:
        lines_info: List[Dict[str, object]] = []
        ordered_lines = list(reversed(self.lines))
        changed_lines = (
            list(reversed(self.changed_hexagram.lines)) if self.changed_hexagram else None
        )

        for idx, value in enumerate(ordered_lines, start=1):
            position = 7 - idx
            line_type = "yang" if value in (7, 9) else "yin"
            is_moving = value in (6, 9)
            moving_symbol = "O" if value == 9 else "X" if value == 6 else ""
            changed_value = (
                changed_lines[idx - 1] if changed_lines and len(changed_lines) >= idx else value
            )
            changed_type = "yang" if changed_value in (7, 9) else "yin"
            lines_info.append(
                {
                    "position": position,
                    "value": value,
                    "line_type": line_type,
                    "is_moving": is_moving,
                    "moving_symbol": moving_symbol,
                    "changed_value": changed_value,
                    "changed_type": changed_type,
                    "changed_line_type": changed_type,
                }
            )

        overview = {
            "lines": lines_info,
            "main_hexagram": {"name": self.name, "explanation": self.explanation},
            "changed_hexagram": None,
        }
        if self.changed_hexagram:
            overview["changed_hexagram"] = {
                "name": self.changed_hexagram.name,
                "explanation": self.changed_hexagram.explanation,
            }
        return overview

    def line_selection(self) -> "LineSelection":
        """Resolve which line (if any) carries this reading, and why.

        Returns the full selection rather than a bare index so callers can tell
        a moving line from a static one. Four and five moving lines select a
        *static* line; labelling that line "动爻" was wrong in three places
        downstream. ``secondary_indices`` carries the lines the classical rule
        names alongside the primary one, which used to be discarded.
        """
        lines = self.lines
        moving = [idx for idx, value in enumerate(lines) if value in (6, 9)]
        static = [idx for idx, value in enumerate(lines) if value not in (6, 9)]
        count = len(moving)

        if count == 0:
            return LineSelection(rule="none", strategy=None)

        if count == 6:
            if self.binary in USE_LINE_BINARIES:
                return LineSelection(rule="all-use", strategy="all")
            return LineSelection(rule="all-changed", strategy="all-move-other")

        if count == 1:
            return LineSelection(
                rule="one-moving", strategy=moving[0], primary=moving[0], primary_is_moving=True
            )

        if count == 2:
            first, second = moving
            if {lines[first], lines[second]} == {6, 9}:
                primary = first if lines[first] == 6 else second
            else:
                primary = max(moving)
            secondary = tuple(idx for idx in moving if idx != primary)
            return LineSelection(
                rule="two-moving",
                strategy=primary,
                primary=primary,
                secondary=secondary,
                primary_is_moving=True,
            )

        if count == 3:
            primary = sorted(moving)[1]
            secondary = tuple(idx for idx in sorted(moving) if idx != primary)
            return LineSelection(
                rule="three-moving",
                strategy=primary,
                primary=primary,
                secondary=secondary,
                primary_is_moving=True,
            )

        if count == 4:
            # 朱熹: 以之卦二不变爻占，仍以下爻为主 — both unchanged lines, lower
            # primary. Four moving lines always leave exactly two static, so no
            # emptiness guard is needed here or in the five-moving branch.
            primary = sorted(static)[0]
            secondary = tuple(idx for idx in sorted(static) if idx != primary)
            return LineSelection(
                rule="four-moving",
                strategy=primary,
                primary=primary,
                secondary=secondary,
                primary_is_moving=False,
            )

        if count == 5:
            primary = sorted(static)[0]
            return LineSelection(
                rule="five-moving",
                strategy=primary,
                primary=primary,
                primary_is_moving=False,
            )

        return LineSelection(rule="none", strategy=None)

    def _select_line_strategy(self) -> Optional[object]:
        """Legacy accessor: the bare strategy value used by the text builders."""
        return self.line_selection().strategy
