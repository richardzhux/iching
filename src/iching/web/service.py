from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Dict, Optional, Tuple

from iching.config import AppConfig, build_app_config
from iching.integrations.ai import DEFAULT_MODEL, MODEL_CAPABILITIES
from iching.integrations.supabase_client import SupabaseRestClient, SupabaseUser
from iching.services.session import SessionService
from iching.web.models import (
    ConfigResponse,
    MethodInfo,
    ModelInfo,
    SessionCreateRequest,
    SessionPayload,
    TopicInfo,
)


MAX_QUESTION_LENGTH = 2000
MAX_DAILY_ATTEMPTS = 1000
MAX_DAILY_AI_SUCCESSES = 50


class AccessDeniedError(RuntimeError):
    """Raised when an AI-enabled request lacks the proper password."""


class RateLimitError(RuntimeError):
    """Raised when a client exceeds allowed request quotas."""


@dataclass
class RateCounter:
    date: str
    attempts: int = 0
    ai_successes: int = 0


class RateLimiter:
    def __init__(self, max_attempts: int, max_ai_successes: int) -> None:
        self.max_attempts = max_attempts
        self.max_ai_successes = max_ai_successes
        self._lock = Lock()
        self._counters: Dict[str, RateCounter] = {}

    def record_attempt(self, ip: str) -> None:
        normalized = self._normalize_ip(ip)
        with self._lock:
            counter = self._get_counter(normalized)
            counter.attempts += 1
            if counter.attempts > self.max_attempts:
                raise RateLimitError("请求过于频繁，请明天再试。")

    def ensure_ai_quota(self, ip: str) -> None:
        normalized = self._normalize_ip(ip)
        with self._lock:
            counter = self._get_counter(normalized)
            if counter.ai_successes >= self.max_ai_successes:
                raise RateLimitError("AI 请求达到每日上限，请明天再试。")

    def record_ai_success(self, ip: str) -> None:
        normalized = self._normalize_ip(ip)
        with self._lock:
            counter = self._get_counter(normalized)
            counter.ai_successes += 1

    def _get_counter(self, ip: str) -> RateCounter:
        today = datetime.utcnow().date().isoformat()
        counter = self._counters.get(ip)
        if counter is None or counter.date != today:
            counter = RateCounter(date=today)
            self._counters[ip] = counter
        return counter

    @staticmethod
    def _normalize_ip(ip: str) -> str:
        return ip or "unknown"


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


from iching.web.chat_state import SessionStateStore
from iching.web.chat_service import ChatService


@dataclass(slots=True)
class SessionRunner:
    service: SessionService
    config: AppConfig
    rate_limiter: RateLimiter
    session_state_store: SessionStateStore
    chat_service: ChatService

    def run(
        self,
        request: SessionCreateRequest,
        client_ip: str | None = None,
        user: Optional[SupabaseUser] = None,
    ) -> SessionPayload:
        ip = client_ip or "unknown"
        self.rate_limiter.record_attempt(ip)
        user_authenticated = user is not None

        if request.user_question and len(request.user_question) > MAX_QUESTION_LENGTH:
            raise ValueError("question too verbose!")

        allowed_topics = {
            label for key, label in self.service.TOPIC_MAP.items() if key != "q"
        }
        if request.topic not in allowed_topics:
            raise ValueError(f"未知的占卜主题: {request.topic}")

        allowed_methods = set(self.service.methods.keys())
        if request.method_key not in allowed_methods:
            raise ValueError(f"未知的占卜方法: {request.method_key}")

        timestamp = request.timestamp if not request.use_current_time else None

        ai_allowed = False
        if request.enable_ai:
            if not user_authenticated:
                raise AccessDeniedError("登录后才能启用 AI 分析。")
            self.rate_limiter.ensure_ai_quota(ip)
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
            f"八字: {result.bazi_output}",
            f"五行: {result.elements_output}",
            f"六爻: {result.lines}",
        ]

        raw_session = result.to_dict()
        safe_session = json.loads(json.dumps(raw_session, default=str))

        payload = SessionPayload(
            summary_text="\n".join(summary),
            hex_text=result.hex_text,
            hex_sections=result.hex_sections,
            hex_overview=result.hex_overview,
            bazi_detail=result.bazi_detail,
            najia_text=result.najia_text,
            najia_table=result.najia_table,
            ai_text=result.ai_analysis or "",
            session_dict=safe_session,
            archive_path=str(archive_path),
            full_text=result.full_text,
            session_id=result.session_id,
            ai_enabled=bool(result.ai_analysis),
            ai_model=result.ai_model,
            ai_reasoning=result.ai_reasoning,
            ai_verbosity=result.ai_verbosity,
            ai_tone=result.ai_tone,
            ai_response_id=result.ai_response_id,
            ai_usage=result.ai_usage or {},
            user_authenticated=user_authenticated,
        )
        if result.ai_analysis:
            initial_tokens = 0
            if isinstance(result.ai_usage, dict):
                initial_tokens = int(result.ai_usage.get("total_tokens") or 0)
            self.session_state_store.register(
                session_id=result.session_id,
                summary_text=payload.summary_text,
                ai_text=result.ai_analysis or "",
                ai_enabled=True,
                ai_model=result.ai_model,
                ai_reasoning=result.ai_reasoning,
                ai_verbosity=result.ai_verbosity,
                ai_tone=result.ai_tone,
                last_response_id=result.ai_response_id,
                initial_tokens=initial_tokens,
                session_payload=safe_session,
            )
            if request.enable_ai and ai_allowed:
                self.rate_limiter.record_ai_success(ip)

        should_snapshot = bool(user_authenticated) or bool(result.ai_response_id)
        if should_snapshot:
            self.chat_service.record_session_snapshot(
                result=result,
                summary_text=payload.summary_text,
                user=user,
                session_payload=payload.model_dump(),
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
_RATE_LIMITER = RateLimiter(
    max_attempts=MAX_DAILY_ATTEMPTS,
    max_ai_successes=MAX_DAILY_AI_SUCCESSES,
)
_SESSION_STATE_STORE = SessionStateStore()
_SUPABASE_CLIENT = SupabaseRestClient()
_CHAT_SERVICE = ChatService(store=_SESSION_STATE_STORE, client=_SUPABASE_CLIENT)
_SESSION_RUNNER = SessionRunner(
    service=_SESSION_SERVICE,
    config=_APP_CONFIG,
    rate_limiter=_RATE_LIMITER,
    session_state_store=_SESSION_STATE_STORE,
    chat_service=_CHAT_SERVICE,
)


def get_session_runner() -> SessionRunner:
    return _SESSION_RUNNER


def get_session_state_store() -> SessionStateStore:
    return _SESSION_STATE_STORE


def get_chat_service() -> ChatService:
    return _CHAT_SERVICE
