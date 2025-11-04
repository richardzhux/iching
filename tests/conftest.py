import sys
from pathlib import Path


def pytest_configure(config):
    root = Path(__file__).resolve().parents[1]
    src_dir = root / "src"
    if src_dir.exists():
        sys.path.insert(0, str(src_dir))
