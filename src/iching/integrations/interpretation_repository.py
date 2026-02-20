from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from iching.core.guaci_repository import load_guaci_by_number


TRIGRAM_SEED: List[Tuple[int, str, str, str]] = [
    (1, "111", "乾", "Heaven"),
    (2, "000", "坤", "Earth"),
    (3, "100", "震", "Thunder"),
    (4, "011", "巽", "Wind"),
    (5, "010", "坎", "Water"),
    (6, "101", "离", "Fire"),
    (7, "001", "艮", "Mountain"),
    (8, "110", "兑", "Lake"),
]
TRIGRAM_ID_BY_CODE: Dict[str, int] = {code: trigram_id for trigram_id, code, _, _ in TRIGRAM_SEED}

SOURCE_SEED: List[Tuple[str, str]] = [
    ("guaci", "卦辞库"),
    ("takashima", "高岛易断"),
    ("symbolic", "八卦象意"),
    ("english_commentary", "English Commentary"),
]

SYMBOLIC_HEXAGRAM_ID_BY_STEM: Dict[str, int] = {
    "qian": 1,
    "kun": 2,
    "kan": 29,
    "li": 30,
    "zhen": 51,
    "gen": 52,
    "xun": 57,
    "dui": 58,
}

SYMBOLIC_NOISE_MARKERS = ("周易六十四卦象意，建议收藏",)


@dataclass(frozen=True)
class InterpretationEntry:
    hexagram_number: int
    hexagram_name: str
    slot_key: str
    slot_kind: str
    line_no: Optional[int]
    use_kind: Optional[str]
    source_key: str
    source_label: str
    content: str

    @property
    def line_key(self) -> Optional[str]:
        if self.slot_kind == "line" and self.line_no is not None:
            return str(self.line_no)
        if self.slot_kind == "use":
            return "all"
        return None


def _canonical_slot_key(
    hexagram_id: int,
    slot_kind: str,
    *,
    line_no: Optional[int] = None,
    use_kind: Optional[str] = None,
) -> str:
    if slot_kind == "gua":
        return f"{hexagram_id}.gua"
    if slot_kind == "line" and line_no is not None:
        return f"{hexagram_id}.line.{line_no}"
    if slot_kind == "use" and use_kind:
        return f"{hexagram_id}.use.{use_kind}"
    raise ValueError("invalid slot coordinates")


def _read_hexagram_index(index_file: Path) -> List[Tuple[int, str, str, str]]:
    if not index_file.exists():
        raise FileNotFoundError(f"Hexagram index not found: {index_file}")
    rows: List[Tuple[int, str, str, str]] = []
    lines = index_file.read_text(encoding="utf-8").splitlines()
    for raw in lines[1:]:
        line = raw.strip()
        if not line:
            continue
        parts = [part.strip() for part in line.split(",")]
        if len(parts) < 3:
            continue
        name = parts[0]
        binary = parts[1]
        meaning = ",".join(parts[2:]).strip()
        rows.append((len(rows) + 1, name, binary, meaning))
    if len(rows) != 64:
        raise ValueError(f"expected 64 hexagrams in index, got {len(rows)}")
    return rows


def _take_takashima_top(data: object) -> Optional[str]:
    top_sections = getattr(data, "top_sections", {})
    value = top_sections.get("takashima")
    return value.strip() if isinstance(value, str) and value.strip() else None


def _take_takashima_line(data: object, line_key: str) -> Optional[str]:
    line_sections = getattr(data, "line_sections", {})
    line = line_sections.get(line_key)
    if not line:
        return None
    value = line.sections.get("takashima")
    return value.strip() if isinstance(value, str) and value.strip() else None


def _resolve_symbolic_hexagram_id(path: Path) -> Optional[int]:
    stem = "".join(char for char in path.stem.lower() if char.isalpha())
    if not stem:
        return None
    return SYMBOLIC_HEXAGRAM_ID_BY_STEM.get(stem)


def _clean_symbolic_text(raw: str) -> Optional[str]:
    normalized = (
        raw.replace("\r\n", "\n")
        .replace("\ufeff", "")
        .replace("\ufffc", "")
    )

    lines: List[str] = []
    pending_blank = False
    for raw_line in normalized.split("\n"):
        line = raw_line.strip()
        if not line:
            pending_blank = True
            continue
        if any(marker in line for marker in SYMBOLIC_NOISE_MARKERS):
            continue
        if pending_blank and lines:
            lines.append("")
        lines.append(line)
        pending_blank = False

    text = "\n".join(lines).strip()
    return text or None


def _clean_english_structured_text(raw: object) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    normalized = (
        raw.replace("\r\n", "\n")
        .replace("\ufeff", "")
        .replace("\ufffc", "")
    )
    lines = [line.rstrip() for line in normalized.split("\n")]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        return None

    squashed: List[str] = []
    previous_blank = False
    for line in lines:
        blank = not line.strip()
        if blank and previous_blank:
            continue
        squashed.append(line)
        previous_blank = blank

    text = "\n".join(squashed).strip()
    return text or None


class InterpretationRepository:
    """SQL-backed storage for slot-based hexagram interpretations."""

    def __init__(
        self,
        *,
        db_path: Path,
        index_file: Path,
        guaci_dir: Path,
        takashima_dir: Path,
        symbolic_dir: Path,
        english_structured_dir: Path,
    ) -> None:
        self.db_path = db_path
        self.index_file = index_file
        self.guaci_dir = guaci_dir
        self.takashima_dir = takashima_dir
        self.symbolic_dir = symbolic_dir
        self.english_structured_dir = english_structured_dir
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()
        self._seed_reference_data()
        self.sync_from_files()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def count_slots(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS count FROM interpretation_slot").fetchone()
            return int(row["count"]) if row else 0

    def count_entries(self, source_key: Optional[str] = None) -> int:
        with self._connect() as conn:
            if source_key:
                row = conn.execute(
                    """
                    SELECT COUNT(*) AS count
                    FROM interpretation_entry e
                    JOIN interpretation_source s ON s.id = e.source_id
                    WHERE s.source_key = ? AND e.is_current = 1
                    """,
                    (source_key,),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT COUNT(*) AS count FROM interpretation_entry WHERE is_current = 1"
                ).fetchone()
            return int(row["count"]) if row else 0

    def list_entries(
        self,
        *,
        hexagram_name: str,
        locale: str = "zh-CN",
        source_keys: Optional[Sequence[str]] = None,
    ) -> List[InterpretationEntry]:
        params: List[object] = [hexagram_name, locale]
        source_filter = ""
        if source_keys:
            placeholders = ", ".join("?" for _ in source_keys)
            source_filter = f"AND src.source_key IN ({placeholders})"
            params.extend(source_keys)

        sql = f"""
            SELECT
                h.id AS hexagram_number,
                h.name_zh AS hexagram_name,
                slt.canonical_key AS slot_key,
                slt.slot_kind AS slot_kind,
                slt.line_no AS line_no,
                slt.use_kind AS use_kind,
                src.source_key AS source_key,
                src.display_name AS source_label,
                ent.content AS content
            FROM interpretation_entry ent
            JOIN interpretation_slot slt ON slt.id = ent.slot_id
            JOIN interpretation_hexagram h ON h.id = slt.hexagram_id
            JOIN interpretation_source src ON src.id = ent.source_id
            WHERE h.name_zh = ?
              AND ent.locale = ?
              AND ent.is_current = 1
              AND ent.status = 'published'
              {source_filter}
            ORDER BY
              CASE slt.slot_kind
                WHEN 'gua' THEN 0
                WHEN 'line' THEN 1
                WHEN 'use' THEN 2
                ELSE 9
              END,
              COALESCE(slt.line_no, 99) ASC,
              CASE src.source_key
                WHEN 'guaci' THEN 0
                WHEN 'takashima' THEN 1
                WHEN 'symbolic' THEN 2
                WHEN 'english_commentary' THEN 3
                ELSE 9
              END,
              src.source_key ASC
        """

        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()

        return [
            InterpretationEntry(
                hexagram_number=int(row["hexagram_number"]),
                hexagram_name=str(row["hexagram_name"]),
                slot_key=str(row["slot_key"]),
                slot_kind=str(row["slot_kind"]),
                line_no=int(row["line_no"]) if row["line_no"] is not None else None,
                use_kind=str(row["use_kind"]) if row["use_kind"] is not None else None,
                source_key=str(row["source_key"]),
                source_label=str(row["source_label"]),
                content=str(row["content"]),
            )
            for row in rows
        ]

    def get_slot_content(
        self,
        *,
        hexagram_name: str,
        source_key: str,
        slot_kind: str,
        line_no: Optional[int] = None,
        use_kind: Optional[str] = None,
        locale: str = "zh-CN",
    ) -> Optional[str]:
        where = ["h.name_zh = ?", "src.source_key = ?", "ent.locale = ?", "ent.is_current = 1"]
        params: List[object] = [hexagram_name, source_key, locale]

        if slot_kind == "gua":
            where.append("slt.slot_kind = 'gua'")
        elif slot_kind == "line":
            if line_no is None:
                raise ValueError("line_no is required for slot_kind=line")
            where.append("slt.slot_kind = 'line'")
            where.append("slt.line_no = ?")
            params.append(line_no)
        elif slot_kind == "use":
            where.append("slt.slot_kind = 'use'")
            if use_kind:
                where.append("slt.use_kind = ?")
                params.append(use_kind)
        else:
            raise ValueError(f"unknown slot_kind: {slot_kind}")

        sql = f"""
            SELECT ent.content
            FROM interpretation_entry ent
            JOIN interpretation_slot slt ON slt.id = ent.slot_id
            JOIN interpretation_hexagram h ON h.id = slt.hexagram_id
            JOIN interpretation_source src ON src.id = ent.source_id
            WHERE {" AND ".join(where)}
            ORDER BY ent.version DESC
            LIMIT 1
        """

        with self._connect() as conn:
            row = conn.execute(sql, params).fetchone()
        if not row:
            return None
        content = str(row["content"]).strip()
        return content or None

    def sync_from_files(self) -> None:
        self._sync_source_from_directory(source_key="guaci", directory=self.guaci_dir)
        self._sync_source_from_directory(source_key="takashima", directory=self.takashima_dir)
        self._sync_symbolic_source(source_key="symbolic", directory=self.symbolic_dir)
        self._sync_english_source(
            source_key="english_commentary", directory=self.english_structured_dir
        )

    # ------------------------------------------------------------------ #
    # Internal: schema + seed
    # ------------------------------------------------------------------ #

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS interpretation_trigram (
                  id INTEGER PRIMARY KEY,
                  binary_code TEXT NOT NULL UNIQUE CHECK (length(binary_code) = 3),
                  name_zh TEXT NOT NULL UNIQUE,
                  name_en TEXT
                );

                CREATE TABLE IF NOT EXISTS interpretation_hexagram (
                  id INTEGER PRIMARY KEY CHECK (id BETWEEN 1 AND 64),
                  name_zh TEXT NOT NULL UNIQUE,
                  binary_code TEXT NOT NULL UNIQUE
                    CHECK (length(binary_code) = 6 AND binary_code GLOB '[01][01][01][01][01][01]'),
                  meaning TEXT,
                  upper_trigram_id INTEGER NOT NULL
                    REFERENCES interpretation_trigram(id) ON DELETE RESTRICT,
                  lower_trigram_id INTEGER NOT NULL
                    REFERENCES interpretation_trigram(id) ON DELETE RESTRICT
                );

                CREATE TABLE IF NOT EXISTS interpretation_slot (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  hexagram_id INTEGER NOT NULL
                    REFERENCES interpretation_hexagram(id) ON DELETE CASCADE,
                  slot_kind TEXT NOT NULL CHECK (slot_kind IN ('gua', 'line', 'use')),
                  line_no INTEGER,
                  use_kind TEXT CHECK (use_kind IN ('yong_jiu', 'yong_liu')),
                  sort_index INTEGER NOT NULL,
                  canonical_key TEXT NOT NULL UNIQUE,
                  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                  CHECK (
                    (slot_kind = 'gua' AND line_no IS NULL AND use_kind IS NULL)
                    OR (slot_kind = 'line' AND line_no BETWEEN 1 AND 6 AND use_kind IS NULL)
                    OR (slot_kind = 'use' AND line_no IS NULL AND use_kind IN ('yong_jiu', 'yong_liu'))
                  ),
                  CHECK (
                    slot_kind != 'use'
                    OR (hexagram_id = 1 AND use_kind = 'yong_jiu')
                    OR (hexagram_id = 2 AND use_kind = 'yong_liu')
                  )
                );

                CREATE UNIQUE INDEX IF NOT EXISTS idx_interpretation_slot_coords
                  ON interpretation_slot(hexagram_id, slot_kind, line_no, use_kind);

                CREATE TABLE IF NOT EXISTS interpretation_source (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  source_key TEXT NOT NULL UNIQUE,
                  display_name TEXT NOT NULL,
                  is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
                );

                CREATE TABLE IF NOT EXISTS interpretation_entry (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  slot_id INTEGER NOT NULL
                    REFERENCES interpretation_slot(id) ON DELETE CASCADE,
                  source_id INTEGER NOT NULL
                    REFERENCES interpretation_source(id) ON DELETE CASCADE,
                  locale TEXT NOT NULL,
                  content TEXT NOT NULL,
                  version INTEGER NOT NULL DEFAULT 1 CHECK (version >= 1),
                  status TEXT NOT NULL DEFAULT 'published'
                    CHECK (status IN ('draft', 'reviewed', 'published')),
                  is_current INTEGER NOT NULL DEFAULT 1 CHECK (is_current IN (0, 1)),
                  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE UNIQUE INDEX IF NOT EXISTS idx_interpretation_entry_version
                  ON interpretation_entry(slot_id, source_id, locale, version);

                CREATE UNIQUE INDEX IF NOT EXISTS idx_interpretation_entry_current
                  ON interpretation_entry(slot_id, source_id, locale)
                  WHERE is_current = 1;
                """
            )

    def _seed_reference_data(self) -> None:
        index_rows = _read_hexagram_index(self.index_file)
        with self._connect() as conn:
            self._seed_trigrams(conn)
            self._seed_hexagrams(conn, index_rows)
            self._seed_sources(conn)
            self._seed_slots(conn)

    def _seed_trigrams(self, conn: sqlite3.Connection) -> None:
        conn.executemany(
            """
            INSERT INTO interpretation_trigram(id, binary_code, name_zh, name_en)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              binary_code = excluded.binary_code,
              name_zh = excluded.name_zh,
              name_en = excluded.name_en
            """,
            TRIGRAM_SEED,
        )

    def _seed_hexagrams(
        self,
        conn: sqlite3.Connection,
        rows: Sequence[Tuple[int, str, str, str]],
    ) -> None:
        payload: List[Tuple[int, str, str, str, int, int]] = []
        for hexagram_id, name_zh, binary_code, meaning in rows:
            if len(binary_code) != 6:
                raise ValueError(f"invalid hexagram binary: {binary_code}")
            lower = binary_code[:3]
            upper = binary_code[3:]
            lower_id = TRIGRAM_ID_BY_CODE.get(lower)
            upper_id = TRIGRAM_ID_BY_CODE.get(upper)
            if lower_id is None or upper_id is None:
                raise ValueError(f"unknown trigram code in {name_zh}: {binary_code}")
            payload.append(
                (
                    hexagram_id,
                    name_zh,
                    binary_code,
                    meaning,
                    upper_id,
                    lower_id,
                )
            )

        conn.executemany(
            """
            INSERT INTO interpretation_hexagram(
              id, name_zh, binary_code, meaning, upper_trigram_id, lower_trigram_id
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              name_zh = excluded.name_zh,
              binary_code = excluded.binary_code,
              meaning = excluded.meaning,
              upper_trigram_id = excluded.upper_trigram_id,
              lower_trigram_id = excluded.lower_trigram_id
            """,
            payload,
        )

    def _seed_sources(self, conn: sqlite3.Connection) -> None:
        conn.executemany(
            """
            INSERT INTO interpretation_source(source_key, display_name, is_active)
            VALUES (?, ?, 1)
            ON CONFLICT(source_key) DO UPDATE SET
              display_name = excluded.display_name,
              is_active = 1
            """,
            SOURCE_SEED,
        )

    def _seed_slots(self, conn: sqlite3.Connection) -> None:
        slots: List[Tuple[int, str, Optional[int], Optional[str], int, str]] = []
        for hexagram_id in range(1, 65):
            slots.append(
                (
                    hexagram_id,
                    "gua",
                    None,
                    None,
                    0,
                    _canonical_slot_key(hexagram_id, "gua"),
                )
            )
            for line_no in range(1, 7):
                slots.append(
                    (
                        hexagram_id,
                        "line",
                        line_no,
                        None,
                        line_no,
                        _canonical_slot_key(hexagram_id, "line", line_no=line_no),
                    )
                )

            if hexagram_id == 1:
                slots.append(
                    (
                        1,
                        "use",
                        None,
                        "yong_jiu",
                        7,
                        _canonical_slot_key(1, "use", use_kind="yong_jiu"),
                    )
                )
            if hexagram_id == 2:
                slots.append(
                    (
                        2,
                        "use",
                        None,
                        "yong_liu",
                        7,
                        _canonical_slot_key(2, "use", use_kind="yong_liu"),
                    )
                )

        conn.executemany(
            """
            INSERT INTO interpretation_slot(
              hexagram_id, slot_kind, line_no, use_kind, sort_index, canonical_key
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(canonical_key) DO UPDATE SET
              hexagram_id = excluded.hexagram_id,
              slot_kind = excluded.slot_kind,
              line_no = excluded.line_no,
              use_kind = excluded.use_kind,
              sort_index = excluded.sort_index
            """,
            slots,
        )

    # ------------------------------------------------------------------ #
    # Internal: content import
    # ------------------------------------------------------------------ #

    def _sync_source_from_directory(self, *, source_key: str, directory: Path) -> None:
        if not directory.exists():
            return

        with self._connect() as conn:
            source_row = conn.execute(
                "SELECT id FROM interpretation_source WHERE source_key = ?",
                (source_key,),
            ).fetchone()
            if not source_row:
                raise ValueError(f"source not found: {source_key}")
            source_id = int(source_row["id"])

            slot_rows = conn.execute(
                "SELECT id, canonical_key FROM interpretation_slot"
            ).fetchall()
            slot_id_by_key = {str(row["canonical_key"]): int(row["id"]) for row in slot_rows}

            conn.execute(
                "DELETE FROM interpretation_entry WHERE source_id = ? AND locale = ?",
                (source_id, "zh-CN"),
            )

            payload: List[Tuple[int, int, str, str, int, str, int]] = []

            for hexagram_id in range(1, 65):
                try:
                    data = load_guaci_by_number(hexagram_id, directory)
                except FileNotFoundError:
                    continue

                if source_key == "guaci":
                    top_content = data.combine_top()
                    line_values = {
                        str(index): data.combine_line(str(index))
                        for index in range(1, 7)
                    }
                    use_content = data.combine_line("all")
                elif source_key == "takashima":
                    top_content = _take_takashima_top(data)
                    line_values = {
                        str(index): _take_takashima_line(data, str(index))
                        for index in range(1, 7)
                    }
                    use_content = _take_takashima_line(data, "all")
                else:
                    raise ValueError(f"unsupported source for structured sync: {source_key}")

                def append_entry(slot_key: str, text: Optional[str]) -> None:
                    if not text:
                        return
                    cleaned = text.strip()
                    if not cleaned:
                        return
                    slot_id = slot_id_by_key.get(slot_key)
                    if slot_id is None:
                        return
                    payload.append(
                        (
                            slot_id,
                            source_id,
                            "zh-CN",
                            cleaned,
                            1,
                            "published",
                            1,
                        )
                    )

                append_entry(
                    _canonical_slot_key(hexagram_id, "gua"),
                    top_content,
                )
                for line_no in range(1, 7):
                    append_entry(
                        _canonical_slot_key(hexagram_id, "line", line_no=line_no),
                        line_values.get(str(line_no)),
                    )

                if hexagram_id == 1:
                    append_entry(
                        _canonical_slot_key(1, "use", use_kind="yong_jiu"),
                        use_content,
                    )
                elif hexagram_id == 2:
                    append_entry(
                        _canonical_slot_key(2, "use", use_kind="yong_liu"),
                        use_content,
                    )

            if payload:
                conn.executemany(
                    """
                    INSERT INTO interpretation_entry(
                      slot_id, source_id, locale, content, version, status, is_current
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    payload,
                )

    def _sync_symbolic_source(self, *, source_key: str, directory: Path) -> None:
        if not directory.exists():
            return

        with self._connect() as conn:
            source_row = conn.execute(
                "SELECT id FROM interpretation_source WHERE source_key = ?",
                (source_key,),
            ).fetchone()
            if not source_row:
                raise ValueError(f"source not found: {source_key}")
            source_id = int(source_row["id"])

            slot_rows = conn.execute(
                "SELECT id, canonical_key FROM interpretation_slot"
            ).fetchall()
            slot_id_by_key = {str(row["canonical_key"]): int(row["id"]) for row in slot_rows}

            conn.execute(
                "DELETE FROM interpretation_entry WHERE source_id = ? AND locale = ?",
                (source_id, "zh-CN"),
            )

            content_by_hexagram: Dict[int, str] = {}
            for file in sorted(directory.glob("*.txt")):
                hexagram_id = _resolve_symbolic_hexagram_id(file)
                if hexagram_id is None:
                    continue
                text = _clean_symbolic_text(file.read_text(encoding="utf-8"))
                if not text:
                    continue
                content_by_hexagram[hexagram_id] = text

            payload: List[Tuple[int, int, str, str, int, str, int]] = []
            for hexagram_id, content in sorted(content_by_hexagram.items()):
                slot_key = _canonical_slot_key(hexagram_id, "gua")
                slot_id = slot_id_by_key.get(slot_key)
                if slot_id is None:
                    continue
                payload.append(
                    (
                        slot_id,
                        source_id,
                        "zh-CN",
                        content,
                        1,
                        "published",
                        1,
                    )
                )

            if payload:
                conn.executemany(
                    """
                    INSERT INTO interpretation_entry(
                      slot_id, source_id, locale, content, version, status, is_current
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    payload,
                )

    def _sync_english_source(self, *, source_key: str, directory: Path) -> None:
        if not directory.exists():
            return

        with self._connect() as conn:
            source_row = conn.execute(
                "SELECT id FROM interpretation_source WHERE source_key = ?",
                (source_key,),
            ).fetchone()
            if not source_row:
                raise ValueError(f"source not found: {source_key}")
            source_id = int(source_row["id"])

            slot_rows = conn.execute(
                "SELECT id, canonical_key FROM interpretation_slot"
            ).fetchall()
            slot_id_by_key = {str(row["canonical_key"]): int(row["id"]) for row in slot_rows}

            conn.execute(
                "DELETE FROM interpretation_entry WHERE source_id = ? AND locale = ?",
                (source_id, "en-US"),
            )

            payload: List[Tuple[int, int, str, str, int, str, int]] = []
            for hexagram_id in range(1, 65):
                canonical = f"Hexagram {hexagram_id:02d}.json"
                fallback = f"{hexagram_id:02d}.json"
                path = directory / canonical
                if not path.exists():
                    path = directory / fallback
                if not path.exists():
                    continue

                raw = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(raw, dict):
                    continue

                gua_text = _clean_english_structured_text(raw.get("gua"))
                lines_payload = raw.get("lines")
                lines = lines_payload if isinstance(lines_payload, dict) else {}

                def append_entry(slot_key: str, text: Optional[str]) -> None:
                    if not text:
                        return
                    slot_id = slot_id_by_key.get(slot_key)
                    if slot_id is None:
                        return
                    payload.append(
                        (
                            slot_id,
                            source_id,
                            "en-US",
                            text,
                            1,
                            "published",
                            1,
                        )
                    )

                append_entry(_canonical_slot_key(hexagram_id, "gua"), gua_text)
                for line_no in range(1, 7):
                    line_text = _clean_english_structured_text(
                        lines.get(str(line_no)) or lines.get(f"line_{line_no}")
                    )
                    append_entry(
                        _canonical_slot_key(hexagram_id, "line", line_no=line_no),
                        line_text,
                    )

            if payload:
                conn.executemany(
                    """
                    INSERT INTO interpretation_entry(
                      slot_id, source_id, locale, content, version, status, is_current
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    payload,
                )
