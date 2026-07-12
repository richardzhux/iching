#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from iching.config import build_app_config
from iching.core.bazi import BaZiCalculator
from iching.core.hexagram import Hexagram, load_hexagram_definitions
from iching.integrations.interpretation_repository import InterpretationRepository
from iching.integrations.najia_repository import NajiaRepository
from iching.integrations.supabase_client import SupabaseRestClient
from iching.services.session import build_session_najia_payload


@dataclass
class BackfillStats:
    scanned: int = 0
    changed: int = 0
    updated: int = 0
    skipped: int = 0
    failed: int = 0


def _coerce_lines(value: object) -> Optional[List[int]]:
    if not isinstance(value, list) or len(value) != 6:
        return None
    lines: List[int] = []
    for item in value:
        if isinstance(item, bool):
            return None
        if isinstance(item, int):
            parsed = item
        elif isinstance(item, str) and item.strip().isdigit():
            parsed = int(item.strip())
        else:
            return None
        if parsed not in {6, 7, 8, 9}:
            return None
        lines.append(parsed)
    return lines


def _extract_context(snapshot: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    session_dict = snapshot.get("session_dict")
    if isinstance(session_dict, dict):
        return session_dict
    keys = {
        "topic",
        "user_question",
        "current_time_str",
        "method",
        "lines",
        "hex_text",
        "bazi_output",
        "elements_output",
        "najia_data",
    }
    if any(key in snapshot for key in keys):
        return snapshot
    return None


def _parse_cast_time(value: object) -> Optional[datetime]:
    if not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value, "%Y.%m.%d %H:%M")
    except ValueError:
        return None


def _patch_snapshot(
    *,
    snapshot: Dict[str, Any],
    hex_text: str,
    hex_sections: List[Dict[str, object]],
    hex_overview: Dict[str, object],
    najia_table: Dict[str, object],
    najia_data: Dict[str, object],
    najia_text: str,
) -> Dict[str, Any]:
    patched = copy.deepcopy(snapshot)
    patched["hex_text"] = hex_text
    patched["hex_sections"] = hex_sections
    patched["hex_overview"] = hex_overview
    patched["najia_table"] = najia_table
    patched["najia_text"] = najia_text
    session_dict = patched.get("session_dict")
    if isinstance(session_dict, dict):
        session_dict["hex_text"] = hex_text
        session_dict["hex_sections"] = hex_sections
        session_dict["hex_overview"] = hex_overview
        session_dict["najia_table"] = najia_table
        session_dict["najia_data"] = najia_data
        session_dict["najia_text"] = najia_text
    return patched


def _compute_refreshed_snapshot(
    *,
    snapshot: Dict[str, Any],
    definitions: Dict[str, tuple[str, str]],
    interpretation_repo: InterpretationRepository,
    najia_repo: NajiaRepository,
    config,
) -> Optional[Dict[str, Any]]:
    context = _extract_context(snapshot)
    if not context:
        return None
    lines = _coerce_lines(context.get("lines"))
    if not lines:
        return None
    cast_time = _parse_cast_time(context.get("current_time_str"))
    if cast_time is None:
        return None

    try:
        bazi_calculator = BaZiCalculator(cast_time)
        bazi_calculator.calculate()
        day_stem = (bazi_calculator.last_components or {}).get("day_stem")
    except Exception:
        return None

    hexagram = Hexagram(lines=lines, definitions=definitions)
    hex_text, hex_sections, hex_overview = hexagram.to_text_package(
        guaci_path=config.paths.guaci_dir,
        takashima_path=config.paths.takashima_dir,
        interpretation_repo=interpretation_repo,
    )
    main_entry = najia_repo.get_by_bottom(hexagram.binary)
    changed_entry = (
        najia_repo.get_by_bottom(hexagram.changed_hexagram.binary)
        if hexagram.changed_hexagram
        else None
    )
    najia_table, najia_data, najia_text = build_session_najia_payload(
        main_entry,
        changed_entry,
        hex_overview.get("lines", []),
        day_stem,
    )
    return _patch_snapshot(
        snapshot=snapshot,
        hex_text=hex_text,
        hex_sections=hex_sections,
        hex_overview=hex_overview,
        najia_table=najia_table,
        najia_data=najia_data,
        najia_text=najia_text,
    )


def _snapshot_skip_reason(snapshot: Dict[str, Any]) -> str:
    context = _extract_context(snapshot)
    if not context:
        return "missing_context"
    if _coerce_lines(context.get("lines")) is None:
        return "invalid_lines"
    if _parse_cast_time(context.get("current_time_str")) is None:
        return "invalid_cast_time"
    return "invalid_saved_snapshot"


def _report_row(session_id: str, status: str, reason: str) -> None:
    print(
        json.dumps(
            {"session_id": session_id or None, "status": status, "reason": reason},
            ensure_ascii=False,
        ),
        file=sys.stderr,
    )


def _iter_sessions(
    client: SupabaseRestClient,
    *,
    page_size: int,
    limit: Optional[int],
) -> Iterable[Dict[str, Any]]:
    offset = 0
    yielded = 0
    while True:
        remaining = None if limit is None else max(0, limit - yielded)
        if remaining == 0:
            return
        batch_size = page_size if remaining is None else min(page_size, remaining)
        page = client.list_sessions_page(limit=batch_size, offset=offset)
        if not page:
            return
        for row in page:
            yield row
            yielded += 1
        offset += len(page)


def _session_id_list(value: str) -> List[str]:
    items = [item.strip() for item in value.split(",")]
    return [item for item in items if item]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backfill Supabase session payload snapshots with refreshed hex sections."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write updates to Supabase. Without this flag the script is dry-run only.",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=200,
        help="Number of rows fetched per page (default: 200).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of sessions to scan.",
    )
    parser.add_argument(
        "--session-ids",
        type=str,
        default="",
        help="Comma-separated session_id list for targeted backfill.",
    )
    parser.add_argument(
        "--supabase-url",
        type=str,
        default="",
        help="Override SUPABASE_URL for this run.",
    )
    parser.add_argument(
        "--supabase-service-key",
        type=str,
        default="",
        help="Override SUPABASE_SERVICE_KEY for this run.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = build_app_config(enable_ai=False)
    definitions = load_hexagram_definitions(config.paths.gua_index_file)
    interpretation_repo = InterpretationRepository(
        db_path=config.paths.interpretation_db,
        index_file=config.paths.gua_index_file,
        guaci_dir=config.paths.guaci_dir,
        takashima_dir=config.paths.takashima_dir,
        symbolic_dir=config.paths.symbolic_dir,
        english_structured_dir=config.paths.english_structured_dir,
    )
    najia_repo = NajiaRepository(config.paths.najia_db)
    client = SupabaseRestClient(
        project_url=args.supabase_url or None,
        service_key=args.supabase_service_key or None,
    )
    if not client.enabled:
        raise RuntimeError("Supabase is not configured. Set SUPABASE_URL and SUPABASE_SERVICE_KEY.")

    target_ids = _session_id_list(args.session_ids)
    try:
        if target_ids:
            rows: List[Dict[str, Any]] = []
            for session_id in target_ids:
                record = client.fetch_session_any(session_id=session_id)
                if record:
                    rows.append(record)
        else:
            rows = list(
                _iter_sessions(client, page_size=max(1, args.page_size), limit=args.limit)
            )
    except Exception as exc:
        raise RuntimeError(
            "Failed to query Supabase sessions. Check SUPABASE_URL, SUPABASE_SERVICE_KEY, and network access."
        ) from exc

    stats = BackfillStats()
    started_at = datetime.now(timezone.utc)
    dry_run = not args.apply

    for row in rows:
        stats.scanned += 1
        session_id = str(row.get("session_id") or "")
        user_id = str(row.get("user_id") or "")
        original_updated_at = str(row.get("updated_at") or "")
        snapshot = row.get("payload_snapshot")
        if not session_id or not user_id or not original_updated_at or not isinstance(snapshot, dict):
            stats.skipped += 1
            _report_row(session_id, "skipped", "missing_row_identity_or_snapshot")
            continue

        try:
            patched = _compute_refreshed_snapshot(
                snapshot=snapshot,
                definitions=definitions,
                interpretation_repo=interpretation_repo,
                najia_repo=najia_repo,
                config=config,
            )
        except Exception as exc:
            stats.failed += 1
            _report_row(session_id, "failed", f"{type(exc).__name__}: {exc}"[:180])
            continue

        if patched is None:
            stats.skipped += 1
            _report_row(session_id, "skipped", _snapshot_skip_reason(snapshot))
            continue

        if patched == snapshot:
            continue

        stats.changed += 1
        if dry_run:
            continue

        try:
            updated = client.update_session_if_unchanged(
                session_id=session_id,
                user_id=user_id,
                expected_updated_at=original_updated_at,
                payload={
                    "payload_snapshot": patched,
                },
            )
            if updated:
                stats.updated += 1
            else:
                stats.skipped += 1
                _report_row(session_id, "skipped", "concurrent_update")
        except Exception as exc:
            stats.failed += 1
            _report_row(session_id, "failed", f"{type(exc).__name__}: {exc}"[:180])

    ended_at = datetime.now(timezone.utc)
    report = {
        "mode": "apply" if args.apply else "dry-run",
        "started_at": started_at.isoformat(),
        "ended_at": ended_at.isoformat(),
        "duration_seconds": round((ended_at - started_at).total_seconds(), 3),
        "scanned": stats.scanned,
        "changed": stats.changed,
        "updated": stats.updated,
        "skipped": stats.skipped,
        "failed": stats.failed,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(
            json.dumps(
                {
                    "mode": "error",
                    "error": str(exc),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        sys.exit(1)
