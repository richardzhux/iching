from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional


TOP_SECTION_ORDER = ["guaci", "xiangci", "duanyi", "zhaoyong", "fupeirong", "zongjie", "philos"]
LINE_SECTION_ORDER = ["yaoci", "zhaoyong", "fupeirong", "var", "philos"]

FILENAME_PATTERN = re.compile(r"^第(?P<number>\d+)卦_.*\((?P<name>.+)\)\.txt$")


@dataclass(frozen=True)
class LineText:
    sections: Dict[str, str]


@dataclass(frozen=True)
class GuaciText:
    number: int
    name: str
    top_sections: Dict[str, str]
    line_sections: Dict[str, LineText]

    def combine_top(self) -> str:
        pieces: List[str] = []
        for key in TOP_SECTION_ORDER:
            text = self.top_sections.get(key)
            if text:
                pieces.append(text)
        return "\n\n".join(pieces).strip()

    def combine_line(self, line_key: str) -> Optional[str]:
        line = self.line_sections.get(line_key)
        if not line:
            return None
        pieces: List[str] = []
        for key in LINE_SECTION_ORDER:
            text = line.sections.get(key)
            if text:
                pieces.append(text)
        return "\n\n".join(pieces).strip()


@lru_cache(maxsize=None)
def _scan_directory(directory: str) -> Tuple[Dict[int, Path], Dict[str, Path]]:
    number_map: Dict[int, Path] = {}
    name_map: Dict[str, Path] = {}
    path = Path(directory)
    for file in path.glob("第*卦*.txt"):
        match = FILENAME_PATTERN.match(file.name)
        if not match:
            continue
        number = int(match.group("number"))
        name = match.group("name")
        number_map[number] = file
        name_map[name] = file
    return number_map, name_map


def _resolve_path_by_number(hex_number: int, directory: Path) -> Path:
    number_map, _ = _scan_directory(str(directory))
    try:
        return number_map[hex_number]
    except KeyError as exc:
        raise FileNotFoundError(f"未找到第{hex_number}卦的卦辞文件") from exc


def _resolve_path_by_name(name: str, directory: Path) -> Path:
    _, name_map = _scan_directory(str(directory))
    try:
        return name_map[name]
    except KeyError as exc:
        raise FileNotFoundError(f"未找到名称为 {name} 的卦辞文件") from exc


def load_guaci_by_number(hex_number: int, directory: Path) -> GuaciText:
    path = _resolve_path_by_number(hex_number, directory)
    return _load_guaci_file(path)


def load_guaci_by_name(name: str, directory: Path) -> GuaciText:
    path = _resolve_path_by_name(name, directory)
    return _load_guaci_file(path)


@lru_cache(maxsize=None)
def _load_guaci_file(path: Path) -> GuaciText:
    match = FILENAME_PATTERN.match(path.name)
    if not match:
        raise ValueError(f"无法解析卦辞文件名: {path.name}")
    number = int(match.group("number"))
    name = match.group("name")

    lines = path.read_text(encoding="utf-8").splitlines()
    top_sections: Dict[str, str] = {}
    line_sections: Dict[str, Dict[str, List[str]]] = {}

    current_key: Optional[Tuple[str, ...]] = None
    buffer: List[str] = []

    def commit() -> None:
        nonlocal current_key, buffer
        if current_key is None:
            return
        content = "\n".join(buffer).strip()
        buffer = []
        if not content:
            current_key = None
            return
        if current_key[0] == "top":
            top_sections[current_key[1]] = content
        elif current_key[0] == "line":
            line_key, section_key = current_key[1], current_key[2]
            store = line_sections.setdefault(line_key, {})
            store.setdefault(section_key, []).append(content)
        current_key = None

    expected_prefix = str(number)
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if buffer is not None:
                buffer.append("")
            continue
        if stripped.endswith("."):
            tokens = [token for token in stripped.split(".") if token]
            if tokens and tokens[0] == expected_prefix:
                commit()
                if len(tokens) == 2:
                    key = tokens[1]
                    if key == "all":
                        current_key = ("line", "all", "yaoci")
                    else:
                        current_key = ("top", key)
                elif len(tokens) >= 3:
                    line_key = tokens[1]
                    section_key = tokens[2]
                    current_key = ("line", line_key, section_key)
                else:
                    current_key = None
                continue
        if current_key is None:
            # ignore text preceding recognised marker
            continue
        buffer.append(line)

    commit()

    normalised_line_sections: Dict[str, LineText] = {}
    for line_key, sections in line_sections.items():
        normalised_line_sections[line_key] = LineText(
            sections={key: "\n".join(value).strip() for key, value in sections.items()}
        )

    return GuaciText(
        number=number,
        name=name,
        top_sections={key: value for key, value in top_sections.items() if value.strip()},
        line_sections=normalised_line_sections,
    )
