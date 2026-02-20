#!/usr/bin/env python3
from __future__ import annotations

from iching.config import PATHS
from iching.integrations.interpretation_repository import InterpretationRepository


def main() -> None:
    repo = InterpretationRepository(
        db_path=PATHS.interpretation_db,
        index_file=PATHS.gua_index_file,
        guaci_dir=PATHS.guaci_dir,
        takashima_dir=PATHS.takashima_dir,
    )
    print(f"Synced interpretation DB: {PATHS.interpretation_db}")
    print(f"Slots: {repo.count_slots()}")
    print(f"Entries (guaci): {repo.count_entries('guaci')}")
    print(f"Entries (takashima): {repo.count_entries('takashima')}")


if __name__ == "__main__":
    main()
