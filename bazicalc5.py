"""
Backward-compatible wrapper for the refactored I Ching application.

Prefer importing from `iching` directly:

    from iching.cli.runner import run_console
    run_console()
"""

from __future__ import annotations

import sys
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent / "src"
if SRC_DIR.exists():
    sys.path.insert(0, str(SRC_DIR))

from iching.config import build_app_config
from iching.services.session import SessionResult, SessionService


def run_iching_console(*, enable_ai: bool = True) -> None:
    """Launch the interactive console application."""
    config = build_app_config(enable_ai=enable_ai)
    SessionService(config=config).run_console(enable_ai=enable_ai)


def compute_session_for_gui(
    *,
    topic: str,
    user_question: Optional[str],
    method_key: str,
    use_current_time: bool = True,
    custom_time: Optional[datetime] = None,
    manual_lines: Optional[List[int]] = None,
    enable_ai: bool = False,
    api_key: Optional[str] = None,
) -> Tuple[Dict[str, object], str]:
    """
    Non-interactive helper retained for compatibility with existing GUI code.
    Returns (session_dict, full_text).
    """
    config = build_app_config(enable_ai=enable_ai)
    service = SessionService(config=config)
    result = service.create_session(
        topic=topic,
        user_question=user_question,
        method_key=method_key,
        use_current_time=use_current_time,
        timestamp=custom_time,
        manual_lines=manual_lines,
        enable_ai=enable_ai,
        interactive=False,
    )
    session_dict = result.to_dict()
    session_dict["ai_analysis"] = result.ai_analysis
    return session_dict, result.full_text


__all__ = ["compute_session_for_gui", "run_iching_console"]
