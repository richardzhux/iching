from __future__ import annotations

import argparse
import json
import re
import sqlite3
from pathlib import Path
from typing import Iterable, List, Tuple

GLYPH_SOLID = "▅▅▅▅▅"
GLYPH_BROKEN = "▅▅　▅▅"
WHITESPACE_RE = re.compile(r"[ \u3000]+")


def load_guaxiang_map(path: Path) -> dict[str, str]:
    if not path.exists():
        raise FileNotFoundError(f"guaxiang index not found: {path}")

    mapping: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("Hexagram"):
            continue
        parts = [segment.strip() for segment in line.split(",", 2)]
        if len(parts) < 2:
            continue
        name, binary = parts[0], parts[1].replace(" ", "")
        if name:
            mapping[name] = binary
    if not mapping:
        raise RuntimeError(f"guaxiang index at {path} produced no entries")
    return mapping


def normalize_text(text: str) -> str:
    return text.replace("\xa0", " ").rstrip()


def parse_data_lines(block: str) -> List[dict[str, str]]:
    rows: List[dict[str, str]] = []
    for raw_line in block.splitlines():
        line = normalize_text(raw_line)
        if not line.strip():
            continue
        glyph, line_type = detect_glyph(line)
        if not glyph:
            continue
        idx = line.index(glyph)
        prefix = line[:idx].strip()
        suffix = line[idx + len(glyph) :].strip()

        prefix_tokens = tokenize(prefix)
        suffix_tokens = tokenize(suffix)
        god = prefix_tokens[0] if prefix_tokens else ""
        hidden = prefix_tokens[1] if len(prefix_tokens) > 1 else ""
        relation = suffix_tokens[0] if suffix_tokens else ""
        marker = suffix_tokens[1] if len(suffix_tokens) > 1 else ""

        rows.append(
            {
                "god": god,
                "hidden": hidden,
                "relation": relation,
                "marker": marker,
                "glyph": glyph,
                "line_type": line_type,
            }
        )
    if len(rows) != 6:
        raise ValueError(f"expected 6 rows in block; got {len(rows)}\n{block}")
    return rows


def detect_glyph(line: str) -> Tuple[str, str]:
    if GLYPH_SOLID in line:
        return GLYPH_SOLID, "yang"
    if GLYPH_BROKEN in line:
        return GLYPH_BROKEN, "yin"
    return "", ""


def tokenize(value: str) -> List[str]:
    if not value:
        return []
    return [token for token in WHITESPACE_RE.split(value) if token]


def parse_block(block: str) -> Tuple[str, str, str, List[dict[str, str]]]:
    lines = [normalize_text(line) for line in block.splitlines() if line.strip()]
    if not lines:
        raise ValueError("empty 六神區塊")

    header = lines[0]
    palace = extract_palace(header)
    descriptor = header.split("：", 1)[1].strip() if "：" in header else ""
    rows = parse_data_lines(block)
    return header, palace, descriptor, rows


def extract_palace(header: str) -> str:
    match = re.search(r"([\u4e00-\u9fff]+宫)", header)
    if match:
        return match.group(1)
    return ""


def iter_index_entries(index_path: Path) -> Iterable[dict]:
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    for item in payload:
        yield item


def build_database(source_dir: Path, guaxiang_path: Path, output_path: Path) -> None:
    index_path = source_dir / "index.json"
    if not index_path.exists():
        raise FileNotFoundError(f"missing index.json in {source_dir}")

    gua_map = load_guaxiang_map(guaxiang_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(output_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(
            """
            DROP TABLE IF EXISTS hexagram_lines;
            DROP TABLE IF EXISTS hexagrams;
            CREATE TABLE hexagrams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                palace TEXT,
                descriptor TEXT,
                binary_top_to_bottom TEXT NOT NULL,
                binary_bottom_to_top TEXT NOT NULL,
                header TEXT,
                block_text TEXT NOT NULL
            );
            CREATE TABLE hexagram_lines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hexagram_id INTEGER NOT NULL REFERENCES hexagrams(id) ON DELETE CASCADE,
                line_position_top INTEGER NOT NULL,
                line_position_bottom INTEGER NOT NULL,
                god TEXT,
                hidden TEXT,
                relation TEXT,
                marker TEXT,
                glyph TEXT,
                line_type TEXT,
                UNIQUE(hexagram_id, line_position_top)
            );
        """
        )

        for entry in iter_index_entries(index_path):
            folder = entry["folder"]
            hex_title = entry["hexagram_title"]
            binary_top = entry["bits_top_to_bottom"]
            binary_bottom = binary_top[::-1]
            expected_binary = gua_map.get(hex_title)
            if expected_binary and expected_binary != binary_bottom:
                raise ValueError(
                    f"binary mismatch for {hex_title}: index has {binary_top}, "
                    f"expected {expected_binary} (bottom-to-top)"
                )

            folder_path = source_dir / folder
            json_file = next((folder_path / name for name in entry["files"] if name.endswith(".json")), None)
            if not json_file or not json_file.exists():
                raise FileNotFoundError(f"missing JSON file for {hex_title} in {folder_path}")

            payload = json.loads(json_file.read_text(encoding="utf-8"))
            block = payload.get("六神區塊", "").strip()
            if not block:
                raise ValueError(f"六神區塊 missing for {hex_title}")

            header, palace, descriptor, rows = parse_block(block)
            cursor = conn.execute(
                """
                INSERT INTO hexagrams (name, palace, descriptor, binary_top_to_bottom,
                                       binary_bottom_to_top, header, block_text)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (hex_title, palace, descriptor, binary_top, binary_bottom, header, block),
            )
            hex_id = cursor.lastrowid
            for idx, row in enumerate(rows):
                position_top = 6 - idx
                position_bottom = idx + 1
                conn.execute(
                    """
                    INSERT INTO hexagram_lines (
                        hexagram_id, line_position_top, line_position_bottom,
                        god, hidden, relation, marker, glyph, line_type
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        hex_id,
                        position_top,
                        position_bottom,
                        row["god"],
                        row["hidden"],
                        row["relation"],
                        row["marker"],
                        row["glyph"],
                        row["line_type"],
                    ),
                )

    print(f"Najia database written to {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Najia SQLite database from JSON artifacts.")
    parser.add_argument("--source", type=Path, default=Path("data/najia"), help="Folder containing the raw Najia files.")
    parser.add_argument("--guaxiang", type=Path, default=Path("data/guaxiang.txt"), help="Guaxiang index file.")
    parser.add_argument("--output", type=Path, default=Path("data/najia.db"), help="Destination SQLite path.")
    args = parser.parse_args()
    build_database(args.source, args.guaxiang, args.output)


if __name__ == "__main__":
    main()
