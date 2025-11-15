from __future__ import annotations

import os
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from threading import Lock
from typing import Dict, Optional

MAX_SESSION_CACHE = int(os.getenv("ICHING_SESSION_CACHE_LIMIT", "100"))
SESSION_CACHE_TTL_SECONDS = int(os.getenv("ICHING_SESSION_CACHE_TTL_SECONDS", str(6 * 3600)))


@dataclass(slots=True)
class SessionState:
    session_id: str
    summary_text: str
    ai_text: Optional[str]
    ai_enabled: bool
    ai_model: Optional[str]
    ai_reasoning: Optional[str]
    ai_verbosity: Optional[str]
    ai_tone: Optional[str]
    last_response_id: Optional[str]
    initial_tokens: int = 0
    chat_turns: int = 0
    session_payload: Dict[str, object] = field(default_factory=dict)
    last_access: float = field(default_factory=lambda: time.time())

    def to_dict(self) -> Dict[str, object]:
        return {
            "session_id": self.session_id,
            "summary_text": self.summary_text,
            "ai_text": self.ai_text,
            "ai_enabled": self.ai_enabled,
            "ai_model": self.ai_model,
            "ai_reasoning": self.ai_reasoning,
            "ai_verbosity": self.ai_verbosity,
            "ai_tone": self.ai_tone,
            "last_response_id": self.last_response_id,
            "initial_tokens": self.initial_tokens,
            "chat_turns": self.chat_turns,
        }


class SessionStateStore:
    """In-memory registry so chat endpoints can look up recent sessions quickly."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._sessions: Dict[str, SessionState] = {}
        self._order: "OrderedDict[str, None]" = OrderedDict()
        self._max_sessions = max(1, MAX_SESSION_CACHE)
        self._ttl_seconds = max(0, SESSION_CACHE_TTL_SECONDS)

    def register(
        self,
        *,
        session_id: str,
        summary_text: str,
        ai_text: Optional[str],
        ai_enabled: bool,
        ai_model: Optional[str],
        ai_reasoning: Optional[str],
        ai_verbosity: Optional[str],
        ai_tone: Optional[str],
        last_response_id: Optional[str],
        initial_tokens: int,
        session_payload: Dict[str, object],
    ) -> SessionState:
        state = SessionState(
            session_id=session_id,
            summary_text=summary_text,
            ai_text=ai_text,
            ai_enabled=ai_enabled,
            ai_model=ai_model,
            ai_reasoning=ai_reasoning,
            ai_verbosity=ai_verbosity,
            ai_tone=ai_tone,
            last_response_id=last_response_id,
            initial_tokens=initial_tokens,
            session_payload=session_payload,
        )
        with self._lock:
            self._sessions[session_id] = state
            self._order[session_id] = None
            self._touch_locked(session_id)
            self._evict_locked()
        return state

    def get(self, session_id: str) -> Optional[SessionState]:
        with self._lock:
            state = self._sessions.get(session_id)
            if state:
                self._touch_locked(session_id)
            return state

    def update_response(self, session_id: str, response_id: str, *, increment_turn: bool = False) -> None:
        with self._lock:
            state = self._sessions.get(session_id)
            if not state:
                return
            state.last_response_id = response_id
            if increment_turn:
                state.chat_turns += 1
            self._touch_locked(session_id)
            self._evict_locked()

    def add_tokens(self, session_id: str, delta: int) -> None:
        if delta <= 0:
            return
        with self._lock:
            state = self._sessions.get(session_id)
            if not state:
                return
            state.initial_tokens += delta
            self._touch_locked(session_id)
            self._evict_locked()

    def remove(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)
            self._order.pop(session_id, None)

    def _touch_locked(self, session_id: str) -> None:
        state = self._sessions.get(session_id)
        if not state:
            return
        state.last_access = time.time()
        if session_id in self._order:
            self._order.move_to_end(session_id)

    def _evict_locked(self) -> None:
        now = time.time()
        if self._ttl_seconds > 0:
            expired = [
                session_id
                for session_id, state in list(self._sessions.items())
                if now - state.last_access > self._ttl_seconds
            ]
            for session_id in expired:
                self._sessions.pop(session_id, None)
                self._order.pop(session_id, None)
        while len(self._sessions) > self._max_sessions:
            oldest, _ = self._order.popitem(last=False)
            self._sessions.pop(oldest, None)
