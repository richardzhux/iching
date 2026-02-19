from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from iching.core.guaci_repository import load_guaci_by_name


HexagramDefinition = Tuple[str, str]

QIAN_NAMES = {"乾为天", "乾卦"}
KUN_NAMES = {"坤为地", "坤卦"}


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
    ) -> str:
        """Build the legacy textual representation used by downstream consumers."""
        summary, _, _ = self.to_text_package(
            guaci_path=guaci_path, takashima_path=takashima_path
        )
        return summary

    def to_text_package(
        self,
        *,
        guaci_path: Optional[Path] = None,
        takashima_path: Optional[Path] = None,
    ) -> Tuple[str, List[Dict[str, object]], Dict[str, object]]:
        """Return the focused summary text, structured sections, and overview metadata."""
        selection = self._select_line_strategy()
        main_text, main_line_text, changed_header, changed_text = self._build_interpretation(
            guaci_path=guaci_path, selection=selection
        )
        summary = self._compose_summary(
            selection, main_text, main_line_text, changed_header, changed_text
        )
        sections = self._collect_sections(selection, guaci_path, takashima_path)
        overview = self._build_overview()
        return summary, sections, overview

    def _compose_summary(
        self,
        selection: Optional[object],
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

        chunks.append("────────────────────────")

        if main_text:
            chunks.append(main_text)
        if main_line_text:
            chunks.append(main_line_text)

        if changed_text:
            if self.changed_hexagram:
                label = "变卦详解" if selection == "all-move-other" else "变卦动爻"
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
        self, *, guaci_path: Optional[Path], selection: Optional[object]
    ) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
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

    def _collect_sections(
        self,
        selection: Optional[object],
        guaci_path: Optional[Path],
        takashima_path: Optional[Path],
    ) -> List[Dict[str, object]]:
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

        # Main hexagram sections
        if main_guaci:
            main_top = main_guaci.combine_top()
            show_main_top = selection != "all-move-other"
            add_section("main", self.name, "top", None, main_top, show_main_top)

            selected_main_line: Optional[str] = None
            if selection == "all":
                selected_main_line = "all"
            elif isinstance(selection, int):
                selected_main_line = str(selection + 1)

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
                False,
                source="takashima",
            )
            for key in sorted_keys(main_takashima.line_sections):
                add_section(
                    "main",
                    self.name,
                    "line",
                    key,
                    takashima_line(main_takashima, key),
                    False,
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

            selected_changed_line: Optional[str] = None
            if selection == "all":
                selected_changed_line = "all"
            elif isinstance(selection, int):
                selected_changed_line = str(selection + 1)

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
                False,
                source="takashima",
            )
            for key in sorted_keys(changed_takashima.line_sections):
                add_section(
                    "changed",
                    self.changed_hexagram.name,
                    "line",
                    key,
                    takashima_line(changed_takashima, key),
                    False,
                    source="takashima",
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

    def _select_line_strategy(self) -> Optional[object]:
        moving_indices = [idx for idx, value in enumerate(self.lines) if value in (6, 9)]
        count = len(moving_indices)

        if count == 0:
            return None
        if count == 6:
            if self.name in QIAN_NAMES or self.name in KUN_NAMES:
                return "all"
            return "all-move-other"

        if count == 1:
            return moving_indices[0]

        if count == 2:
            first, second = moving_indices
            values = [self.lines[first], self.lines[second]]
            if set(values) == {6, 9}:
                return first if self.lines[first] == 6 else second
            return max(moving_indices)

        if count == 3:
            return sorted(moving_indices)[1]

        if count == 4:
            static_indices = [idx for idx, value in enumerate(self.lines) if value not in (6, 9)]
            if static_indices:
                return sorted(static_indices)[0]
            return None

        if count == 5:
            static_indices = [idx for idx, value in enumerate(self.lines) if value not in (6, 9)]
            return static_indices[0] if static_indices else None

        return None
