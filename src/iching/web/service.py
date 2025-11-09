from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Tuple

from iching.config import AppConfig, build_app_config
from iching.integrations.ai import DEFAULT_MODEL, MODEL_CAPABILITIES
from iching.services.session import SessionService
from iching.web.models import (
    ConfigResponse,
    MethodInfo,
    ModelInfo,
    SessionCreateRequest,
    SessionPayload,
    TopicInfo,
)


class AccessDeniedError(RuntimeError):
    """Raised when an AI-enabled request lacks the proper password."""


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _save_archive(directory: Path, prefix: str, content: str) -> Path:
    target_dir = _ensure_dir(directory)
    timestamp = datetime.now().strftime("%Y.%m.%d.%H%M%S")
    filepath = target_dir / f"{prefix}_{timestamp}.txt"
    try:
        filepath.write_text(content, encoding="utf-8")
        return filepath
    except OSError:
        fallback_dir = Path(tempfile.gettempdir()) / "iching-archives"
        fallback_dir.mkdir(parents=True, exist_ok=True)
        fallback_path = fallback_dir / filepath.name
        fallback_path.write_text(content, encoding="utf-8")
        return fallback_path


def _validate_ai_password(password: str | None) -> Tuple[bool, str]:
    expected = os.getenv("OPENAI_PW", "")
    if not expected:
        return False, "OPENAI_PW environment variable is not set on the server."
    if not password:
        return False, "Access password is required when AI analysis is enabled."
    if password != expected:
        return False, "Access password is invalid."
    return True, ""


@dataclass(slots=True)
class SessionRunner:
    service: SessionService
    config: AppConfig

    def run(self, request: SessionCreateRequest) -> SessionPayload:
        timestamp = request.timestamp if not request.use_current_time else None

        ai_allowed = False
        if request.enable_ai:
            ok, message = _validate_ai_password(request.access_password)
            if not ok:
                raise AccessDeniedError(message)
            ai_allowed = True

        result = self.service.create_session(
            topic=request.topic,
            user_question=request.user_question,
            method_key=request.method_key,
            use_current_time=request.use_current_time,
            timestamp=timestamp,
            manual_lines=request.manual_lines,
            enable_ai=ai_allowed,
            ai_model=request.ai_model or DEFAULT_MODEL,
            ai_reasoning=request.ai_reasoning,
            ai_verbosity=request.ai_verbosity,
            ai_tone=request.ai_tone,
            interactive=False,
        )

        archive_path = _save_archive(
            self.config.paths.archive_complete_dir,
            prefix="session",
            content=result.full_text,
        )

        summary = [
            f"主题: {result.topic or '（未填）'}",
            f"问题: {result.user_question or '（无）'}",
            f"方法: {result.method}",
            f"时间: {result.current_time_str}",
            f"六爻: {result.lines}",
            f"已保存: {archive_path}",
        ]

        raw_session = result.to_dict()
        safe_session = json.loads(json.dumps(raw_session, default=str))

        payload = SessionPayload(
            summary_text="\n".join(summary),
            hex_text=result.hex_text,
            hex_sections=result.hex_sections,
            hex_overview=result.hex_overview,
            najia_text=result.najia_text,
            najia_table=result.najia_table,
            ai_text=result.ai_analysis or "",
            session_dict=safe_session,
            archive_path=str(archive_path),
            full_text=result.full_text,
        )
        return payload

    def config_response(self) -> ConfigResponse:
        topics = [
            TopicInfo(key=key, label=value)
            for key, value in self.service.TOPIC_MAP.items()
            if key != "q"
        ]
        methods = [
            MethodInfo(key=method.key, label=method.name)
            for method in self.service.methods.values()
        ]
        ai_models = [
            ModelInfo(
                name=name,
                reasoning=meta.get("reasoning", []),
                default_reasoning=meta.get("default_reasoning"),
                verbosity=bool(meta.get("verbosity")),
                default_verbosity=meta.get("default_verbosity"),
            )
            for name, meta in MODEL_CAPABILITIES.items()
        ]
        return ConfigResponse(topics=topics, methods=methods, ai_models=ai_models)


_APP_CONFIG = build_app_config()
_SESSION_SERVICE = SessionService(config=_APP_CONFIG)
_SESSION_RUNNER = SessionRunner(service=_SESSION_SERVICE, config=_APP_CONFIG)


def get_session_runner() -> SessionRunner:
    return _SESSION_RUNNER
