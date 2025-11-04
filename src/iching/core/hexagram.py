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

    def to_text(self, *, guaci_path: Optional[Path] = None) -> str:
        """Build the textual representation with focused guaci content."""
        chunks: List[str] = ["\n您的卦象:"]
        chunks.extend(self.render_lines())
        chunks.append(f"\n本卦: {self.name} - 解释: {self.explanation}")

        main_text, main_line_text, changed_header, changed_text = self._build_interpretation(
            guaci_path=guaci_path
        )
        if main_text:
            chunks.append(main_text)
        if main_line_text:
            chunks.append(main_line_text)

        if changed_header:
            chunks.append(changed_header)
        if changed_text:
            chunks.append(changed_text)

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
        self, *, guaci_path: Optional[Path]
    ) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
        if not guaci_path:
            return None, None, None, None

        try:
            main_guaci = load_guaci_by_name(self.name, guaci_path)
        except FileNotFoundError:
            return None, None, None, None

        selection = self._select_line_strategy()
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
