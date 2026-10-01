#!/usr/bin/env python3
"""Compile and check immutable reference assets before Vercel packages FastAPI."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from iching.config import build_path_config  # noqa: E402
from iching.integrations.interpretation_repository import InterpretationRepository  # noqa: E402
from iching.integrations.najia_repository import NajiaRepository  # noqa: E402


def main() -> None:
    paths = build_path_config()
    if not paths.interpretation_db.is_relative_to(PROJECT_ROOT):
        raise RuntimeError("The Vercel reference database must be generated inside the project to be packaged.")
    source_counts = {}
    for source, directory, suffix, required in (
        ("guaci", paths.guaci_dir, "*.txt", 64),
        ("takashima", paths.takashima_dir, "*.txt", 64),
        ("symbolic", paths.symbolic_dir, "*.txt", 8),
        ("english_commentary", paths.english_structured_dir, "*.json", 64),
    ):
        count = len(list(directory.glob(suffix)))
        if count != required:
            raise RuntimeError(f"{source} requires {required} source files, found {count} in {directory}")
        source_counts[source] = count

    package_data = PROJECT_ROOT / "src" / "iching" / "core" / "data"
    for name in (
        "bazi-calendar-1950-2030-g5-current.json",
        "bazi-calendar-1950-2030-g5-forward.json",
        "bazi-pattern-coverage.json",
        "pattern-product-catalog-v1.json",
        "ziwei-calendar-1950-2030-life-v2.json",
    ):
        json.loads((package_data / name).read_text(encoding="utf-8"))
    bundles = sorted((PROJECT_ROOT / "src" / "iching" / "core" / "bazi_rules" / "bundles").glob("*.json"))
    if not bundles:
        raise RuntimeError("Packaged BaZi rule bundles are missing")
    for bundle in bundles:
        json.loads(bundle.read_text(encoding="utf-8"))

    # Importing the native extension in the build catches an incompatible
    # Python/Linux wheel before a deployment can become production.
    import sxtwl

    if sxtwl.fromSolar(2024, 2, 10).getLunarYear() != 2024:
        raise RuntimeError("sxtwl native calendar check failed")
    for name in ("Asia/Shanghai", "America/Los_Angeles"):
        ZoneInfo(name)
    NajiaRepository(paths.najia_db).validate()

    paths.interpretation_db.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".interpretations-build-", dir=paths.interpretation_db.parent) as staging:
        staged_db = Path(staging) / "interpretations.db"
        repo = InterpretationRepository(
            db_path=staged_db,
            index_file=paths.gua_index_file,
            guaci_dir=paths.guaci_dir,
            takashima_dir=paths.takashima_dir,
            symbolic_dir=paths.symbolic_dir,
            english_structured_dir=paths.english_structured_dir,
        )
        entries = repo.validate_reference_data()
        slots = repo.count_slots()
        os.replace(staged_db, paths.interpretation_db)

    # Reopen exactly the generated output using the deployed connection mode.
    InterpretationRepository(
        db_path=paths.interpretation_db,
        index_file=paths.gua_index_file,
        guaci_dir=paths.guaci_dir,
        takashima_dir=paths.takashima_dir,
        symbolic_dir=paths.symbolic_dir,
        english_structured_dir=paths.english_structured_dir,
        read_only=True,
    )
    print(json.dumps({
        "reference_database": str(paths.interpretation_db.relative_to(PROJECT_ROOT)),
        "database_bytes": paths.interpretation_db.stat().st_size,
        "database_sha256": hashlib.sha256(paths.interpretation_db.read_bytes()).hexdigest(),
        "hexagrams": 64,
        "slots": slots,
        "source_files": source_counts,
        "entries": entries,
        "rule_bundles": len(bundles),
        "native_calendar": "ok",
        "timezones": "ok",
        "python": sys.version.split()[0],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
