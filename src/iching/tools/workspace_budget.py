from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


SOFT_LIMIT_BYTES = 1_850_000_000
HARD_LIMIT_BYTES = 2_000_000_000


@dataclass(frozen=True)
class WorkspaceBudgetResult:
    root: str
    total_bytes: int
    soft_limit_bytes: int
    hard_limit_bytes: int
    status: str


def _directory_size(path: Path) -> int:
    if not path.exists():
        raise FileNotFoundError(f"workspace root does not exist: {path}")
    if not path.is_dir():
        raise NotADirectoryError(f"workspace root is not a directory: {path}")
    total = 0
    pending = [path]
    while pending:
        current = pending.pop()
        try:
            entries = os.scandir(current)
        except FileNotFoundError as exc:
            raise FileNotFoundError(f"workspace directory disappeared during scan: {current}") from exc
        except PermissionError as exc:
            raise PermissionError(f"cannot read workspace directory: {current}") from exc
        with entries:
            for entry in entries:
                try:
                    if entry.is_symlink():
                        total += entry.stat(follow_symlinks=False).st_size
                    elif entry.is_dir(follow_symlinks=False):
                        pending.append(Path(entry.path))
                    elif entry.is_file(follow_symlinks=False):
                        total += entry.stat(follow_symlinks=False).st_size
                except FileNotFoundError as exc:
                    raise FileNotFoundError(f"workspace entry disappeared during scan: {entry.path}") from exc
                except PermissionError as exc:
                    raise PermissionError(f"cannot inspect workspace entry: {entry.path}") from exc
    return total


def check_workspace_budget(
    root: str | Path,
    soft_bytes: int = SOFT_LIMIT_BYTES,
    hard_bytes: int = HARD_LIMIT_BYTES,
) -> WorkspaceBudgetResult:
    resolved = Path(root).resolve()
    if soft_bytes <= 0 or hard_bytes <= 0 or soft_bytes >= hard_bytes:
        raise ValueError("workspace budget requires 0 < soft_bytes < hard_bytes")
    total = _directory_size(resolved)
    status = "hard_limit_exceeded" if total >= hard_bytes else "soft_limit_exceeded" if total >= soft_bytes else "ok"
    return WorkspaceBudgetResult(
        root=str(resolved),
        total_bytes=total,
        soft_limit_bytes=soft_bytes,
        hard_limit_bytes=hard_bytes,
        status=status,
    )
