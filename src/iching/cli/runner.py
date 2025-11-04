from __future__ import annotations

from typing import Optional

from iching.config import build_app_config
from iching.services.session import SessionService


def run_console(*, enable_ai: Optional[bool] = None) -> None:
    """
    Launch the interactive console application.

    Example:
        from iching.cli.runner import run_console
        run_console()
    """
    config = build_app_config(enable_ai=enable_ai)
    service = SessionService(config=config)
    service.run_console(enable_ai=enable_ai)


__all__ = ["run_console"]
