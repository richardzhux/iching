from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


@dataclass(frozen=True)
class NajiaLine:
    position_top: int
    position_bottom: int
    god: str
    hidden: str
    relation: str
    marker: str
    glyph: str
    line_type: str

    def to_payload(self) -> Dict[str, str]:
        return {
            "position_top": self.position_top,
            "position_bottom": self.position_bottom,
            "god": self.god,
            "hidden": self.hidden,
            "relation": self.relation,
            "marker": self.marker,
            "glyph": self.glyph,
            "line_type": self.line_type,
        }


@dataclass(frozen=True)
class NajiaEntry:
    name: str
    palace: str
    descriptor: str
    binary_top_to_bottom: str
    binary_bottom_to_top: str
    header: str
    block_text: str
    lines: List[NajiaLine]

    def get_line_by_top(self, position_top: int) -> Optional[NajiaLine]:
        for line in self.lines:
            if line.position_top == position_top:
                return line
        return None

    def to_payload(self) -> Dict[str, object]:
        return {
            "name": self.name,
            "palace": self.palace,
            "descriptor": self.descriptor,
            "binary_top_to_bottom": self.binary_top_to_bottom,
            "binary_bottom_to_top": self.binary_bottom_to_top,
            "header": self.header,
            "lines": [line.to_payload() for line in self.lines],
        }


class NajiaRepository:
    """Lazy loader for the compiled Najia SQLite database."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        self._by_bottom: Optional[Dict[str, NajiaEntry]] = None
        self._by_top: Optional[Dict[str, NajiaEntry]] = None

    def get_by_bottom(self, binary: str) -> Optional[NajiaEntry]:
        self._ensure_loaded()
        assert self._by_bottom is not None
        return self._by_bottom.get(binary)

    def get_by_top(self, binary: str) -> Optional[NajiaEntry]:
        self._ensure_loaded()
        assert self._by_top is not None
        return self._by_top.get(binary)

    def _ensure_loaded(self) -> None:
        if self._by_bottom is not None and self._by_top is not None:
            return
        if not self.db_path.exists():
            raise FileNotFoundError(
                f"Najia database not found at {self.db_path}. "
                "Please run tools/najia/build_db.py to generate it."
            )

        by_bottom: Dict[str, NajiaEntry] = {}
        by_top: Dict[str, NajiaEntry] = {}

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            hex_rows = conn.execute(
                "SELECT id, name, palace, descriptor, binary_top_to_bottom, "
                "binary_bottom_to_top, header, block_text FROM hexagrams"
            ).fetchall()

            line_rows = conn.execute(
                "SELECT hexagram_id, line_position_top, line_position_bottom, "
                "god, hidden, relation, marker, glyph, line_type "
                "FROM hexagram_lines ORDER BY hexagram_id, line_position_top DESC"
            ).fetchall()

        lines_by_hex: Dict[int, List[NajiaLine]] = {}
        for row in line_rows:
            line = NajiaLine(
                position_top=row["line_position_top"],
                position_bottom=row["line_position_bottom"],
                god=row["god"] or "",
                hidden=row["hidden"] or "",
                relation=row["relation"] or "",
                marker=row["marker"] or "",
                glyph=row["glyph"] or "",
                line_type=row["line_type"] or "yang",
            )
            lines_by_hex.setdefault(row["hexagram_id"], []).append(line)

        for row in hex_rows:
            lines = lines_by_hex.get(row["id"], [])
            # Ensure ordering from top (6) to bottom (1)
            lines.sort(key=lambda item: -item.position_top)
            entry = NajiaEntry(
                name=row["name"],
                palace=row["palace"] or "",
                descriptor=row["descriptor"] or "",
                binary_top_to_bottom=row["binary_top_to_bottom"],
                binary_bottom_to_top=row["binary_bottom_to_top"],
                header=row["header"] or "",
                block_text=row["block_text"] or "",
                lines=lines,
            )
            by_bottom[entry.binary_bottom_to_top] = entry
            by_top[entry.binary_top_to_bottom] = entry

        self._by_bottom = by_bottom
        self._by_top = by_top
