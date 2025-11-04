from __future__ import annotations

import io
import os
import sys
from pathlib import Path


class TeeLogger(io.StringIO):
    """Mirror stdout to an in-memory buffer and persist to disk when requested."""

    def __init__(self, output_dir: Path):
        super().__init__()
        self._output_dir = output_dir.expanduser().resolve()
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._original_stdout = sys.stdout

    @property
    def output_dir(self) -> Path:
        return self._output_dir

    @output_dir.setter
    def output_dir(self, value: Path) -> None:
        resolved = value.expanduser().resolve()
        resolved.mkdir(parents=True, exist_ok=True)
        self._output_dir = resolved

    def write(self, string: str) -> int:
        count = super().write(string)
        self._original_stdout.write(string)
        self._original_stdout.flush()
        return count

    def __enter__(self) -> "TeeLogger":
        sys.stdout = self
        return self

    def __exit__(self, exc_type, exc_value, tb) -> None:
        sys.stdout = self._original_stdout

    def save(self) -> Path:
        files = sorted(
            [
                f
                for f in self._output_dir.iterdir()
                if f.is_file() and f.suffix == ".txt" and f.stem.isdigit()
            ]
        )
        next_index = f"{len(files) + 1:04d}"
        file_path = self._output_dir / f"{next_index}.txt"
        file_path.write_text(self.getvalue(), encoding="utf-8")
        print(f"【本次占卜已自动保存到文件】: {file_path}\n")
        return file_path
