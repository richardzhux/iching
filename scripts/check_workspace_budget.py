from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from iching.tools.workspace_budget import HARD_LIMIT_BYTES, SOFT_LIMIT_BYTES, check_workspace_budget


def main() -> int:
    parser = argparse.ArgumentParser(description="Check the complete repository against its storage budget.")
    parser.add_argument("root", nargs="?", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--soft-bytes", type=int, default=SOFT_LIMIT_BYTES)
    parser.add_argument("--hard-bytes", type=int, default=HARD_LIMIT_BYTES)
    args = parser.parse_args()
    result = check_workspace_budget(args.root, args.soft_bytes, args.hard_bytes)
    print(json.dumps(asdict(result), ensure_ascii=False, sort_keys=True))
    return 2 if result.status == "hard_limit_exceeded" else 1 if result.status == "soft_limit_exceeded" else 0


if __name__ == "__main__":
    raise SystemExit(main())
