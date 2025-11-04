"""
Top-level package for the refactored I Ching application.

This module exposes the public surface that other scripts should import
instead of reaching into individual implementation files.
"""

from .config import PATHS, AppConfig, build_app_config
from .services.session import SessionService, SessionResult

__all__ = ["AppConfig", "PATHS", "SessionResult", "SessionService", "build_app_config"]
