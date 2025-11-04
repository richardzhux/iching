from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


HexagramDefinition = Tuple[str, str]


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
        """
        Build the textual representation including guaci references.

        The guaci directory is optional; if provided, the matching files
        will be included inline when available.
        """
        chunks: List[str] = ["\n您的卦象:"]
        chunks.extend(self.render_lines())
        chunks.append(f"\n本卦: {self.name} - 解释: {self.explanation}")

        if self.changed_hexagram:
            chunks.append(
                f"变卦: {self.changed_hexagram.name} - 解释: {self.changed_hexagram.explanation}"
            )
            chunks.append(
                self._load_guaci_text(self.name, "本卦", guaci_path=guaci_path)
            )
            chunks.append(
                self.changed_hexagram._load_guaci_text(
                    self.changed_hexagram.name, "变卦", guaci_path=guaci_path
                )
            )
        else:
            chunks.append("变卦：没有动爻，故无变卦 - 404 Not Found。")
            chunks.append(
                self._load_guaci_text(self.name, "本卦", guaci_path=guaci_path)
            )

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

    def _load_guaci_text(
        self, name: str, label: str, *, guaci_path: Optional[Path]
    ) -> str:
        if not guaci_path or not guaci_path.exists():
            return f"未找到 {label} 对应的文件目录: {guaci_path}"
        for candidate in guaci_path.iterdir():
            if candidate.is_file() and name in candidate.stem:
                content = candidate.read_text(encoding="utf-8")
                return f"\n{label}: {name} 对应的文件: {candidate}\n内容:\n{content}\n"
        return f"未找到 {label} 对应的文件: {name}"
