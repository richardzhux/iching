"""Generate the public hexagram archive data used by the Next.js library pages."""

from __future__ import annotations

import json
import re
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "interpretations.db"
LIBRARY_PATH = ROOT / "frontend" / "src" / "lib" / "hexagram-library.ts"
OUTPUT_PATH = ROOT / "frontend" / "src" / "lib" / "hexagram-archive.ts"
DATA_DIR = ROOT / "frontend" / "src" / "lib" / "hexagram-archive-data"

SOURCE_ORDER = {
    "guaci": 0,
    "takashima": 1,
    "english_commentary": 2,
    "symbolic": 3,
}


def _read_library_entries() -> dict[int, dict[str, Any]]:
    source = LIBRARY_PATH.read_text(encoding="utf-8")
    entries: dict[int, dict[str, Any]] = {}
    pattern = re.compile(
        r'\{\s*number:\s*(?P<number>\d+),\s*slug:\s*"(?P<slug>[^"]+)",\s*'
        r'nameZh:\s*"(?P<name_zh>[^"]+)",\s*shortNameZh:\s*"(?P<short_name_zh>[^"]+)",\s*'
        r'titleEn:\s*"(?P<title_en>[^"]+)",\s*meaningEn:\s*"(?P<meaning_en>[^"]+)"',
    )
    for match in pattern.finditer(source):
        number = int(match.group("number"))
        entries[number] = {
            "slug": match.group("slug"),
            "nameZh": match.group("name_zh"),
            "shortNameZh": match.group("short_name_zh"),
            "titleEn": match.group("title_en"),
            "meaningEn": match.group("meaning_en"),
        }
    if len(entries) != 64:
        raise RuntimeError(f"Expected 64 frontend hexagram entries, found {len(entries)}")
    return entries


def _source_count_literal(counts: dict[str, int]) -> str:
    return (
        "{ "
        f"guaci: {counts.get('guaci', 0)}, "
        f"takashima: {counts.get('takashima', 0)}, "
        f"english_commentary: {counts.get('english_commentary', 0)}, "
        f"symbolic: {counts.get('symbolic', 0)}"
        " }"
    )


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=4)


def main() -> None:
    library_entries = _read_library_entries()
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row

    slot_counts = {
        row["hexagram_id"]: row["slot_count"]
        for row in connection.execute(
            """
            SELECT hexagram_id, COUNT(*) AS slot_count
            FROM interpretation_slot
            GROUP BY hexagram_id
            """
        )
    }
    global_slot_count = sum(slot_counts.values())

    rows = connection.execute(
        """
        SELECT
            h.id AS hexagram_number,
            sl.canonical_key AS slot_key,
            sl.slot_kind AS slot_kind,
            sl.line_no AS line_no,
            sl.use_kind AS use_kind,
            src.source_key AS source_key,
            src.display_name AS source_label,
            ent.locale AS locale,
            ent.content AS content
        FROM interpretation_entry ent
        JOIN interpretation_slot sl ON sl.id = ent.slot_id
        JOIN interpretation_hexagram h ON h.id = sl.hexagram_id
        JOIN interpretation_source src ON src.id = ent.source_id
        WHERE ent.is_current = 1 AND ent.status = 'published'
        ORDER BY
            h.id ASC,
            sl.sort_index ASC,
            CASE src.source_key
                WHEN 'guaci' THEN 0
                WHEN 'takashima' THEN 1
                WHEN 'english_commentary' THEN 2
                WHEN 'symbolic' THEN 3
                ELSE 9
            END ASC
        """
    ).fetchall()

    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    source_counts: dict[str, int] = defaultdict(int)
    per_hex_source_counts: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for row in rows:
        number = row["hexagram_number"]
        source_key = row["source_key"]
        source_counts[source_key] += 1
        per_hex_source_counts[number][source_key] += 1
        grouped[number].append(
            {
                "slotKey": row["slot_key"],
                "slotKind": row["slot_kind"],
                "lineNo": row["line_no"],
                "useKind": row["use_kind"],
                "sourceKey": source_key,
                "sourceLabel": row["source_label"],
                "locale": row["locale"],
                "content": row["content"].strip(),
            }
        )

    total_entries = sum(source_counts.values())
    if total_entries != 1356:
        raise RuntimeError(f"Expected 1,356 current entries, found {total_entries}")
    if global_slot_count != 450:
        raise RuntimeError(f"Expected 450 canonical slots, found {global_slot_count}")

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for old_file in DATA_DIR.glob("*.ts"):
        old_file.unlink()

    archive_index_blocks: list[str] = []
    loader_blocks: list[str] = []
    for number in range(1, 65):
        metadata = library_entries[number]
        counts = dict(per_hex_source_counts[number])
        entries = grouped[number]
        archive_index_blocks.append(
            "\n".join(
                [
                    "  {",
                    f"    number: {number},",
                    f"    slug: {_json(metadata['slug'])},",
                    f"    nameZh: {_json(metadata['nameZh'])},",
                    f"    shortNameZh: {_json(metadata['shortNameZh'])},",
                    f"    titleEn: {_json(metadata['titleEn'])},",
                    f"    meaningEn: {_json(metadata['meaningEn'])},",
                    f"    totalEntries: {len(entries)},",
                    f"    canonicalSlotCount: {slot_counts.get(number, 0)},",
                    f"    sourceCounts: {_source_count_literal(counts)},",
                    "  },",
                ]
            )
        )
        slug = metadata["slug"]
        loader_blocks.append(f'  "{slug}": () => import("./hexagram-archive-data/{slug}"),')
        data_output = f"""// Generated by tools/build_frontend_hexagram_archive.py. Do not edit by hand.

import type {{ HexagramArchive }} from "../hexagram-archive"

const archive = {{
  number: {number},
  slug: {_json(slug)},
  nameZh: {_json(metadata['nameZh'])},
  shortNameZh: {_json(metadata['shortNameZh'])},
  titleEn: {_json(metadata['titleEn'])},
  meaningEn: {_json(metadata['meaningEn'])},
  totalEntries: {len(entries)},
  canonicalSlotCount: {slot_counts.get(number, 0)},
  sourceCounts: {_source_count_literal(counts)},
  entries: {_json(entries)},
}} as const satisfies HexagramArchive

export default archive
"""
        (DATA_DIR / f"{slug}.ts").write_text(data_output, encoding="utf-8")

    output = f"""// Generated by tools/build_frontend_hexagram_archive.py. Do not edit by hand.

export type HexagramArchiveSourceKey = "guaci" | "takashima" | "english_commentary" | "symbolic"

export type HexagramArchiveEntry = {{
  slotKey: string
  slotKind: "gua" | "line" | "use"
  lineNo: number | null
  useKind: string | null
  sourceKey: HexagramArchiveSourceKey
  sourceLabel: string
  locale: "zh-CN" | "en-US"
  content: string
}}

export type HexagramArchive = {{
  number: number
  slug: string
  nameZh: string
  shortNameZh: string
  titleEn: string
  meaningEn: string
  totalEntries: number
  canonicalSlotCount: number
  sourceCounts: Record<HexagramArchiveSourceKey, number>
  entries: readonly HexagramArchiveEntry[]
}}

export type HexagramArchiveIndexEntry = Omit<HexagramArchive, "entries">

export const HEXAGRAM_ARCHIVE_SUMMARY = {{
  totalEntries: {total_entries},
  canonicalSlotCount: {global_slot_count},
  sourceCounts: {_source_count_literal(dict(source_counts))},
}} as const

export const HEXAGRAM_ARCHIVE_INDEX = [
{chr(10).join(archive_index_blocks)}] as const satisfies readonly HexagramArchiveIndexEntry[]

export const HEXAGRAM_ARCHIVE_LOADERS: Record<string, () => Promise<{{ default: HexagramArchive }}>> = {{
{chr(10).join(loader_blocks)}
}}

export function getHexagramArchiveSummary(slug: string) {{
  return HEXAGRAM_ARCHIVE_INDEX.find((entry) => entry.slug === slug)
}}

export async function getHexagramArchive(slug: string) {{
  const loader = HEXAGRAM_ARCHIVE_LOADERS[slug]
  if (!loader) {{
    return undefined
  }}
  return (await loader()).default
}}

export function getHexagramArchiveSummaryByNumber(number: number) {{
  return HEXAGRAM_ARCHIVE_INDEX.find((entry) => entry.number === number)
}}
"""
    OUTPUT_PATH.write_text(output, encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH.relative_to(ROOT)} and {len(library_entries)} archive data files with {total_entries} source entries.")


if __name__ == "__main__":
    main()
