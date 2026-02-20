#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence


PDF_NAME_RE = re.compile(r"^Hexagram (?P<number>\d{2})\.pdf$")
LINE_HEADER_RE = re.compile(r"^\s*Line[- ]?([1-6])\s*$", re.IGNORECASE)
GUA_START_RE = re.compile(
    r"^\s*(Judgment|The Image|COMMENTARY|CONFUCIAN COMMENTARY|NOTES AND PARAPHRASES)\s*:?\s*$",
    re.IGNORECASE,
)
PAGE_HEADER_RE = re.compile(r"^\s*\d+\s*--.*--\s*\d+\s*$")


@dataclass
class HexagramDocument:
    number: int
    gua: str
    lines: Dict[str, str]


def _extract_pdf_text(pdf: Path) -> str:
    try:
        result = subprocess.run(
            ["pdftotext", str(pdf), "-"],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("pdftotext not found; install poppler first.") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"failed to extract text from {pdf.name}") from exc
    return result.stdout


def _normalize_lines(raw_text: str) -> List[str]:
    normalized = (
        raw_text.replace("\r\n", "\n")
        .replace("\f", "\n")
        .replace("\ufeff", "")
        .replace("\ufffc", "")
    )
    lines: List[str] = []
    for raw_line in normalized.split("\n"):
        line = raw_line.strip()
        if PAGE_HEADER_RE.match(line):
            continue
        lines.append(line)
    return lines


def _clean_block(lines: Sequence[str]) -> str:
    content = list(lines)
    while content and not content[0]:
        content.pop(0)
    while content and not content[-1]:
        content.pop()

    squashed: List[str] = []
    previous_blank = False
    for line in content:
        blank = not line
        if blank and previous_blank:
            continue
        squashed.append(line)
        previous_blank = blank
    return "\n".join(squashed).strip()


def _parse_hexagram(raw_text: str, number: int) -> HexagramDocument:
    lines = _normalize_lines(raw_text)

    line_positions: Dict[int, int] = {}
    for idx, line in enumerate(lines):
        match = LINE_HEADER_RE.match(line)
        if not match:
            continue
        line_no = int(match.group(1))
        if line_no not in line_positions:
            line_positions[line_no] = idx

    missing = [line_no for line_no in range(1, 7) if line_no not in line_positions]
    if missing:
        raise ValueError(
            f"hexagram {number:02d} missing line headings: {','.join(map(str, missing))}"
        )

    line1 = line_positions[1]
    gua_start_candidates = [
        idx for idx, line in enumerate(lines[:line1]) if GUA_START_RE.match(line)
    ]
    gua_start = gua_start_candidates[0] if gua_start_candidates else 0

    gua = _clean_block(lines[gua_start:line1])
    if not gua:
        raise ValueError(f"hexagram {number:02d} has empty gua section")

    parsed_lines: Dict[str, str] = {}
    for line_no in range(1, 7):
        start = line_positions[line_no]
        end = line_positions[line_no + 1] if line_no < 6 else len(lines)
        block = _clean_block(lines[start:end])
        if not block:
            raise ValueError(f"hexagram {number:02d} has empty line-{line_no} section")
        parsed_lines[str(line_no)] = block

    return HexagramDocument(number=number, gua=gua, lines=parsed_lines)


def _iter_hexagram_pdfs(source_dir: Path) -> List[Path]:
    files: List[Path] = []
    for path in sorted(source_dir.glob("Hexagram *.pdf")):
        match = PDF_NAME_RE.match(path.name)
        if match is None:
            continue
        files.append(path)
    return files


def build_dataset(source_dir: Path, output_dir: Path) -> None:
    files = _iter_hexagram_pdfs(source_dir)
    if len(files) != 64:
        raise RuntimeError(f"expected 64 hexagram pdf files, got {len(files)}")

    output_dir.mkdir(parents=True, exist_ok=True)
    written = 0
    for file in files:
        match = PDF_NAME_RE.match(file.name)
        if match is None:
            continue
        number = int(match.group("number"))
        raw_text = _extract_pdf_text(file)
        parsed = _parse_hexagram(raw_text, number=number)
        target = output_dir / f"Hexagram {number:02d}.json"
        payload = {
            "hexagram_number": parsed.number,
            "gua": parsed.gua,
            "lines": parsed.lines,
        }
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        written += 1

    if written != 64:
        raise RuntimeError(f"expected to write 64 files, wrote {written}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract English hexagram PDFs into structured JSON sections."
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=Path("data/eng"),
        help="English PDF folder (default: data/eng)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/eng_structured"),
        help="Structured output folder (default: data/eng_structured)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    build_dataset(args.source_dir, args.output_dir)
    print(f"Structured English dataset generated at: {args.output_dir}")


if __name__ == "__main__":
    main()
