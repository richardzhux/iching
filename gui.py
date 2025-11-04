"""Thin wrapper to launch the refactored Gradio interface."""

import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent / "src"
if SRC_DIR.exists():
    sys.path.insert(0, str(SRC_DIR))

from iching.gui.app import launch


if __name__ == "__main__":
    launch()
