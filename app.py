"""Vercel entrypoint for the existing FastAPI application."""

from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from iching.web.api.main import app  # noqa: E402


__all__ = ["app"]
