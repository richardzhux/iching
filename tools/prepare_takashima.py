#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Dict, List, Tuple


FILENAME_PATTERN = re.compile(r"^第(?P<number>\d+)卦_.*\((?P<name>.+)\)\.txt$")
ARTICLE_HEADING_RE = re.compile(r"^\s*0?\d{1,2}\s*[.．]?\s*.*高岛易断")
LINE_HEADING_RE = re.compile(r"^\s*(初[九六]|[九六][二三四五]|上[九六]|用[九六])：")

FOOTER_MARKER_RE = re.compile(
    r"(?:"
    r"未经允许不得转载|"
    r"加师傅微信咨询|"
    r"WhatsApp咨询|"
    r"QQ交流群|"
    r"电报交流群|"
    r"微信咨询：|"
    r"上一篇|"
    r"下一篇|"
    r"相关推荐|"
    r"订阅评论|"
    r"连接与|"
    r"你的称呼\*|"
    r"你的邮箱\*|"
    r"你的网站\(选填\)|"
    r"评论\(\d+\)|"
    r"^\s*\d+\s*评论\s*$|"
    r"^\s*回复\s*$|"
    r"赞\(\d+\)\s*打赏"
    r")"
)

POSITION_KEYS = ["1", "2", "3", "4", "5", "6"]
NEXT_KEY = {"1": "2", "2": "3", "3": "4", "4": "5", "5": "6", "6": None}


def _section_key(token: str) -> str:
    if token.startswith("用"):
        return "all"
    if token.startswith("初"):
        return "1"
    if token.startswith("上"):
        return "6"
    number_char = token[-1]
    return {
        "二": "2",
        "三": "3",
        "四": "4",
        "五": "5",
    }[number_char]


def _trim_empty_edges(lines: List[str]) -> List[str]:
    start = 0
    end = len(lines)
    while start < end and not lines[start].strip():
        start += 1
    while end > start and not lines[end - 1].strip():
        end -= 1
    return lines[start:end]


def _build_filename_map(guaci_dir: Path) -> Dict[int, str]:
    mapping: Dict[int, str] = {}
    for file in guaci_dir.glob("第*卦*.txt"):
        match = FILENAME_PATTERN.match(file.name)
        if not match:
            continue
        number = int(match.group("number"))
        mapping[number] = file.name
    missing = [number for number in range(1, 65) if number not in mapping]
    if missing:
        raise ValueError(f"缺少卦辞文件映射: {missing}")
    return mapping


def _find_occurrences(lines: List[str]) -> List[Tuple[int, str]]:
    occurrences: List[Tuple[int, str]] = []
    for index, line in enumerate(lines):
        match = LINE_HEADING_RE.match(line)
        if not match:
            continue
        token = match.group(1)
        occurrences.append((index, _section_key(token)))
    return occurrences


def _latest_complete_chain(occurrences: List[Tuple[int, str]]) -> Dict[str, int]:
    by_key: Dict[str, List[int]] = {key: [] for key in POSITION_KEYS}
    for index, key in occurrences:
        if key in by_key:
            by_key[key].append(index)

    for key in POSITION_KEYS:
        if not by_key[key]:
            raise ValueError(f"缺少爻段标题: {key}")

    best_chain: Dict[str, int] | None = None
    for first in by_key["1"]:
        chain: Dict[str, int] = {"1": first}
        current = first
        ok = True
        for key in POSITION_KEYS[1:]:
            candidate = next((value for value in by_key[key] if value > current), None)
            if candidate is None:
                ok = False
                break
            chain[key] = candidate
            current = candidate
        if not ok:
            continue
        if best_chain is None or chain["1"] > best_chain["1"]:
            best_chain = chain

    if best_chain is None:
        raise ValueError("未找到完整的六爻顺序链")
    return best_chain


def _trim_scrape_wrapper(lines: List[str], line_start_hint: int) -> List[str]:
    heading_candidates = [
        index
        for index, line in enumerate(lines[: line_start_hint + 1])
        if ARTICLE_HEADING_RE.search(line)
        and "全解：" not in line
        and "未经允许不得转载" not in line
    ]
    start_index = heading_candidates[-1] if heading_candidates else 0
    segment = lines[start_index:]

    footer_start: int | None = None
    for index, line in enumerate(segment):
        stripped = line.strip()
        if index < 12:
            continue
        if FOOTER_MARKER_RE.search(stripped):
            footer_start = index
            break
        if "mingtianji.com/" in stripped and "http" in stripped:
            footer_start = index
            break

    if footer_start is not None:
        segment = segment[:footer_start]

    return _trim_empty_edges(segment)


def _extract_sections(lines: List[str]) -> Dict[str, str]:
    occurrences = _find_occurrences(lines)
    chain = _latest_complete_chain(occurrences)

    all_occurrences = [index for index, key in occurrences if key == "all"]
    all_index = next((index for index in all_occurrences if index > chain["6"]), None)

    sections: Dict[str, str] = {}

    top_text = "\n".join(lines[: chain["1"]]).strip()
    if not top_text:
        raise ValueError("本卦总段为空")
    sections["top"] = top_text

    for key in POSITION_KEYS:
        start = chain[key]
        next_key = NEXT_KEY[key]
        if next_key is not None:
            end = chain[next_key]
        elif all_index is not None:
            end = all_index
        else:
            end = len(lines)
        content = "\n".join(lines[start:end]).strip()
        if not content:
            raise ValueError(f"爻段 {key} 为空")
        sections[key] = content

    if all_index is not None:
        content = "\n".join(lines[all_index:]).strip()
        if content:
            sections["all"] = content

    return sections


def _write_structured_file(path: Path, number: int, sections: Dict[str, str]) -> None:
    blocks: List[str] = [f"{number}.takashima.\n{sections['top']}"]
    for key in POSITION_KEYS:
        blocks.append(f"{number}.{key}.takashima.\n{sections[key]}")
    if "all" in sections:
        blocks.append(f"{number}.all.takashima.\n{sections['all']}")
    content = "\n\n".join(blocks).rstrip() + "\n"
    path.write_text(content, encoding="utf-8")


def build_dataset(source_dir: Path, guaci_dir: Path, output_dir: Path) -> None:
    filename_map = _build_filename_map(guaci_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for number in range(1, 65):
        source_file = source_dir / f"{number}.txt"
        if not source_file.exists():
            raise FileNotFoundError(f"缺失源文件: {source_file}")

        raw_lines = source_file.read_text(encoding="utf-8").replace("\r\n", "\n").split("\n")
        raw_occurrences = _find_occurrences(raw_lines)
        raw_chain = _latest_complete_chain(raw_occurrences)

        cleaned_lines = _trim_scrape_wrapper(raw_lines, raw_chain["1"])
        sections = _extract_sections(cleaned_lines)

        output_file = output_dir / filename_map[number]
        _write_structured_file(output_file, number, sections)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Clean and structure Takashima raw text files.")
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=Path("data/takashima"),
        help="Raw Takashima txt folder (default: data/takashima)",
    )
    parser.add_argument(
        "--guaci-dir",
        type=Path,
        default=Path("data/guaci"),
        help="Guaci folder used for filename mapping (default: data/guaci)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/takashima_structured"),
        help="Structured output folder (default: data/takashima_structured)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    build_dataset(args.source_dir, args.guaci_dir, args.output_dir)
    print(f"Structured Takashima dataset generated at: {args.output_dir}")


if __name__ == "__main__":
    main()
