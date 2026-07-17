"""Rebuild the packaged canonical BaZi registry from reviewed research sources."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from iching.core.bazi_rules.registry import (
    compile_research_direct_officer_registry,
    registry_to_data,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.project_root.resolve()
    registry = compile_research_direct_officer_registry(root)
    target = root / "src/iching/core/bazi_rules/bundles/zzq-shen-canonical-v1.json"
    payload = (
        json.dumps(
            registry_to_data(registry),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    temporary = target.with_suffix(".json.tmp")
    temporary.write_text(payload, encoding="utf-8")
    temporary.replace(target)


if __name__ == "__main__":
    main()
