from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock
from typing import Dict, List, Optional

from iching.integrations.ai import (
    MODEL_CAPABILITIES,
    continue_analysis,
    continue_analysis_from_session,
    normalize_model_name,
)
from iching.integrations.supabase_client import (
    SupabaseAuthError,
    SupabaseRestClient,
    SupabaseUser,
)
from iching.services.session import SessionResult
from iching.web.chat_state import SessionState, SessionStateStore


CHAT_TURN_LIMIT = int(os.getenv("ICHING_CHAT_TURN_LIMIT", "10"))
CHAT_TOKEN_LIMIT = int(os.getenv("ICHING_CHAT_TOKEN_LIMIT", "150000"))
CHAT_FOLLOWUP_MODEL = os.getenv("ICHING_CHAT_MODEL", "gpt-5-mini")
CHAT_MESSAGE_CHAR_LIMIT = int(os.getenv("ICHING_CHAT_MESSAGE_LIMIT", "10000"))
ANONYMOUS_USER_ID = os.getenv("ICHING_ANON_USER_ID", "00000000-0000-0000-0000-000000000000")
USER_DAILY_TOKEN_LIMIT = int(os.getenv("ICHING_USER_DAILY_TOKEN_LIMIT", "300000"))
USER_SESSION_LIMIT = int(os.getenv("ICHING_USER_SESSION_LIMIT", "50"))


class ChatRateLimitError(RuntimeError):
    """Raised when per-session chat quotas are exceeded."""


@dataclass(slots=True)
class ChatMessageRecord:
    role: str
    content: str
    tokens_in: int = 0
    tokens_out: int = 0


@dataclass(slots=True)
class UserTokenCounter:
    date: str
    tokens: int = 0


class UserTokenLimiter:
    def __init__(self, daily_limit: int) -> None:
        self.daily_limit = max(0, daily_limit)
        self._lock = Lock()
        self._counters: Dict[str, UserTokenCounter] = {}

    def ensure_allowance(self, user_id: str) -> None:
        if self.daily_limit <= 0:
            return
        with self._lock:
            counter = self._get_counter(user_id)
            if counter.tokens >= self.daily_limit:
                raise ChatRateLimitError("今日 AI 追问用量已达 300k tokens 上限，请明日再试。")

    def record_usage(self, user_id: str, tokens: int) -> None:
        if self.daily_limit <= 0 or tokens <= 0:
            return
        with self._lock:
            counter = self._get_counter(user_id)
            counter.tokens += tokens

    def _get_counter(self, user_id: str) -> UserTokenCounter:
        today = datetime.now(timezone.utc).date().isoformat()
        counter = self._counters.get(user_id)
        if counter is None or counter.date != today:
            counter = UserTokenCounter(date=today)
            self._counters[user_id] = counter
        return counter


class ChatService:
    """Coordinates Supabase persistence and OpenAI follow-up calls."""

    def __init__(
        self,
        store: SessionStateStore,
        client: SupabaseRestClient,
        token_limiter: Optional[UserTokenLimiter] = None,
    ) -> None:
        self.store = store
        self.client = client
        self.token_limiter = token_limiter or UserTokenLimiter(USER_DAILY_TOKEN_LIMIT)

    def authenticate(self, access_token: str) -> SupabaseUser:
        if not self.client.enabled:
            raise RuntimeError("Supabase is not configured on the server.")
        return self.client.verify_access_token(access_token)

    def record_session_snapshot(
        self,
        result: SessionResult,
        summary_text: str,
        user: Optional[SupabaseUser] = None,
        session_payload: Optional[Dict[str, object]] = None,
    ) -> None:
        """Persist the initial response so future follow-ups can resume."""
        if not self.client.enabled:
            return
        snapshot = session_payload or result.to_dict()
        tokens_used = 0
        if isinstance(result.ai_usage, dict):
            tokens_used = int(result.ai_usage.get("total_tokens") or 0)
        user_id = user.id if user else ANONYMOUS_USER_ID
        if user and user.id:
            self._enforce_session_limit(user.id)
        payload = {
            "session_id": result.session_id,
            "user_id": user_id,
            "last_response_id": result.ai_response_id,
            "ai_model": result.ai_model or CHAT_FOLLOWUP_MODEL,
            "followup_model": result.ai_model or CHAT_FOLLOWUP_MODEL,
            "ai_reasoning": result.ai_reasoning,
            "ai_verbosity": result.ai_verbosity,
            "ai_tone": result.ai_tone,
            "chat_turns": 0,
            "tokens_used": tokens_used,
            "summary_text": summary_text,
            "initial_ai_text": result.ai_analysis or "",
            "payload_snapshot": snapshot,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        payload.update(_user_profile_payload(user))
        self.client.upsert_session(payload)

    def ensure_session_row(self, session_id: str, user: SupabaseUser) -> Dict[str, object]:
        if not self.client.enabled:
            raise RuntimeError("Supabase is not configured on the server.")
        record = self.client.fetch_session(session_id=session_id, user_id=user.id)
        if record:
            return self._sync_followup_model(record, user.id)
        record = self._claim_anonymous_session(session_id, user)
        if record:
            return self._sync_followup_model(record, user.id)
        state = self.store.get(session_id)
        if not state or not state.last_response_id:
            raise ValueError("无法找到该会话，请重新生成占卜结果后再试。")
        payload = {
            "session_id": session_id,
            "user_id": user.id,
            "last_response_id": state.last_response_id,
            "ai_model": state.ai_model,
            "followup_model": CHAT_FOLLOWUP_MODEL,
            "ai_reasoning": state.ai_reasoning,
            "ai_verbosity": state.ai_verbosity,
            "ai_tone": state.ai_tone,
            "chat_turns": state.chat_turns,
            "tokens_used": state.initial_tokens,
            "summary_text": state.summary_text,
            "initial_ai_text": state.ai_text,
            "payload_snapshot": state.session_payload,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        payload.update(_user_profile_payload(user))
        record = self.client.upsert_session(payload) or payload
        self._persist_initial_message(state=state, user=user)
        return record

    def _claim_anonymous_session(self, session_id: str, user: SupabaseUser) -> Optional[Dict[str, object]]:
        if not self.client.enabled:
            return None
        record = self.client.fetch_session(session_id=session_id, user_id=ANONYMOUS_USER_ID)
        if not record:
            return None
        payload = {
            "user_id": user.id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            **_user_profile_payload(user),
        }
        self.client.update_session(session_id=session_id, user_id=ANONYMOUS_USER_ID, payload=payload)
        record["user_id"] = user.id
        record.update(_user_profile_payload(user))
        return record

    def _sync_followup_model(self, record: Dict[str, object], user_id: str) -> Dict[str, object]:
        current_model = record.get("followup_model")
        if current_model == CHAT_FOLLOWUP_MODEL:
            return record
        payload = {"followup_model": CHAT_FOLLOWUP_MODEL}
        self.client.update_session(session_id=record["session_id"], user_id=user_id, payload=payload)
        record["followup_model"] = CHAT_FOLLOWUP_MODEL
        return record

    def _persist_initial_message(self, state: SessionState, user: SupabaseUser) -> None:
        if not self.client.enabled or not state.ai_text:
            return
        usage = state.session_payload.get("ai_usage")
        prompt_tokens = 0
        completion_tokens = 0
        if isinstance(usage, dict):
            prompt_tokens = int(usage.get("input_tokens") or 0)
            completion_tokens = int(usage.get("output_tokens") or 0)
        records = [
            {
                "session_id": state.session_id,
                "user_id": user.id,
                "role": "assistant",
                "content": state.ai_text,
                "tokens_in": prompt_tokens,
                "tokens_out": completion_tokens,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "model": state.ai_model,
                "reasoning": state.ai_reasoning,
                "verbosity": state.ai_verbosity,
                "tone": state.ai_tone,
                **_user_profile_payload(user),
            }
        ]
        self.client.insert_chat_messages(records)

    def fetch_transcript(self, *, session_id: str, user: SupabaseUser) -> Dict[str, object]:
        record = self.ensure_session_row(session_id, user)
        messages = self.client.fetch_chat_messages(session_id=session_id, user_id=user.id)
        return {
            "session": record,
            "messages": messages,
        }

    def list_sessions(self, user: SupabaseUser) -> List[Dict[str, object]]:
        if not self.client.enabled:
            raise RuntimeError("Supabase is not configured on the server.")
        params = {
            "user_id": f"eq.{user.id}",
            "order": "updated_at.desc",
            "select": (
                "session_id,summary_text,created_at,updated_at,initial_ai_text,"
                "user_email,user_display_name,user_avatar_url,payload_snapshot"
            ),
        }
        headers = self.client._service_headers()
        response = self.client._client.get(f"{self.client.rest_base}/sessions", params=params, headers=headers)
        response.raise_for_status()
        records = response.json()
        return [
            {
                "session_id": record.get("session_id"),
                "summary_text": record.get("summary_text"),
                "created_at": record.get("created_at") or record.get("updated_at"),
                "ai_enabled": bool(record.get("initial_ai_text")),
                "followup_available": _is_followup_available(record),
                "user_email": record.get("user_email"),
                "user_display_name": record.get("user_display_name"),
                "user_avatar_url": record.get("user_avatar_url"),
                "topic_label": _extract_snapshot_field(record, "topic")
                or _infer_label_from_summary(record.get("summary_text"), prefix="主题")
                or record.get("topic_label"),
                "method_label": _extract_snapshot_field(record, "method")
                or _infer_label_from_summary(record.get("summary_text"), prefix="方法")
                or record.get("method_label"),
            }
            for record in records or []
        ]

    def delete_session(self, session_id: str, user: SupabaseUser) -> None:
        if not self.client.enabled:
            raise RuntimeError("Supabase is not configured on the server.")
        if not user.id:
            raise ValueError("用户无效。")
        self.client.delete_session(session_id=session_id, user_id=user.id)
        self.store.remove(session_id)

    def send_followup(
        self,
        *,
        session_id: str,
        user: SupabaseUser,
        message: str,
        reasoning: Optional[str],
        verbosity: Optional[str],
        tone: Optional[str],
        model_override: Optional[str],
    ) -> Dict[str, object]:
        stripped = message.strip()
        if not stripped:
            raise ValueError("问题内容不能为空。")
        if len(stripped) > CHAT_MESSAGE_CHAR_LIMIT:
            raise ValueError(f"单次追问最多 {CHAT_MESSAGE_CHAR_LIMIT} 字符。")
        record = self.ensure_session_row(session_id, user)
        configured_raw = record.get("followup_model")
        configured_model = (
            normalize_model_name(str(configured_raw)) if configured_raw else CHAT_FOLLOWUP_MODEL
        )
        chosen_model = normalize_model_name(model_override) or configured_model
        if chosen_model not in MODEL_CAPABILITIES:
            chosen_model = CHAT_FOLLOWUP_MODEL
        if chosen_model != configured_raw:
            self.client.update_session(
                session_id=session_id,
                user_id=user.id,
                payload={"followup_model": chosen_model},
            )
            record["followup_model"] = chosen_model
        turns_used = int(record.get("chat_turns") or 0)
        if turns_used >= CHAT_TURN_LIMIT:
            raise ChatRateLimitError("本次占卜的追问次数已达上限。")
        tokens_used = int(record.get("tokens_used") or 0)
        if tokens_used >= CHAT_TOKEN_LIMIT:
            raise ChatRateLimitError("本次占卜的追问字数已达上限。")

        self._ensure_user_allowance(user)

        applied_reasoning = reasoning if reasoning is not None else record.get("ai_reasoning")
        applied_verbosity = verbosity if verbosity is not None else record.get("ai_verbosity")
        applied_tone = tone or record.get("ai_tone")

        last_response_id = record.get("last_response_id")
        if last_response_id:
            ai_result = continue_analysis(
                previous_response_id=last_response_id,
                message=stripped,
                model_name=record.get("followup_model") or CHAT_FOLLOWUP_MODEL,
                reasoning_effort=reasoning,
                verbosity=verbosity,
                tone=tone or record.get("ai_tone"),
            )
        else:
            session_context = _extract_session_context(record)
            if not session_context:
                raise ValueError("当前会话缺少完整快照，暂时无法开启 AI 追问。")
            ai_result = continue_analysis_from_session(
                session_data=session_context,
                message=stripped,
                model_name=record.get("followup_model") or CHAT_FOLLOWUP_MODEL,
                reasoning_effort=reasoning,
                verbosity=verbosity,
                tone=tone or record.get("ai_tone"),
            )

        usage_dict = ai_result.usage or {}
        prompt_tokens = int(usage_dict.get("input_tokens") or 0)
        completion_tokens = int(usage_dict.get("output_tokens") or 0)
        total_tokens = int(usage_dict.get("total_tokens") or (prompt_tokens + completion_tokens))
        tokens_used += total_tokens
        if tokens_used > CHAT_TOKEN_LIMIT:
            raise ChatRateLimitError("本次占卜的追问字数已达上限。")
        turns_used += 1

        timestamp = datetime.now(timezone.utc).isoformat()
        update_payload = {
            "last_response_id": ai_result.response_id,
            "chat_turns": turns_used,
            "tokens_used": tokens_used,
            "updated_at": timestamp,
        }
        self.client.update_session(session_id=session_id, user_id=user.id, payload=update_payload)

        user_record = {
            "session_id": session_id,
            "user_id": user.id,
            "role": "user",
            "content": message,
            "tokens_in": prompt_tokens,
            "tokens_out": 0,
            "created_at": timestamp,
            "model": chosen_model,
            "reasoning": applied_reasoning,
            "verbosity": applied_verbosity,
            "tone": applied_tone,
            **_user_profile_payload(user),
        }
        assistant_record = {
            "session_id": session_id,
            "user_id": user.id,
            "role": "assistant",
            "content": ai_result.text,
            "tokens_in": 0,
            "tokens_out": completion_tokens,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "model": chosen_model,
            "reasoning": applied_reasoning,
            "verbosity": applied_verbosity,
            "tone": applied_tone,
            **_user_profile_payload(user),
        }
        self.client.insert_chat_messages([user_record, assistant_record])

        self.store.update_response(session_id, ai_result.response_id or "", increment_turn=True)
        self.store.add_tokens(session_id, total_tokens)
        self._record_user_usage(user, total_tokens)

        return {
            "assistant": assistant_record,
            "usage": usage_dict,
        }

    def _ensure_user_allowance(self, user: SupabaseUser) -> None:
        if not user or not user.id:
            return
        self.token_limiter.ensure_allowance(user.id)

    def _record_user_usage(self, user: SupabaseUser, tokens: int) -> None:
        if not user or not user.id:
            return
        self.token_limiter.record_usage(user.id, tokens)

    def _enforce_session_limit(self, user_id: str) -> None:
        if USER_SESSION_LIMIT <= 0:
            return
        records = self.client.list_session_ids(user_id=user_id, limit=1, offset=USER_SESSION_LIMIT - 1)
        surplus_ids = [record.get("session_id") for record in records if record and record.get("session_id")]
        for session_id in surplus_ids:
            try:
                self.client.delete_session(session_id=session_id, user_id=user_id)
                self.store.remove(session_id)
            except Exception:
                continue


def _user_profile_payload(user: Optional[SupabaseUser]) -> Dict[str, Optional[str]]:
    if not user:
        return {"user_email": None, "user_display_name": None, "user_avatar_url": None}
    metadata = user.metadata or {}
    display_name = (
        metadata.get("full_name")
        or metadata.get("name")
        or metadata.get("user_name")
        or (user.email.split("@")[0] if user.email else None)
    )
    avatar_url = metadata.get("avatar_url") or metadata.get("picture") or metadata.get("profile_image_url")
    return {
        "user_email": user.email,
        "user_display_name": display_name,
        "user_avatar_url": avatar_url,
    }


def _extract_snapshot_field(record: Dict[str, object], key: str) -> Optional[str]:
    session_context = _extract_session_context(record)
    if isinstance(session_context, dict):
        value = session_context.get(key)
        if isinstance(value, str):
            return value
    return None


def _infer_label_from_summary(summary: Optional[str], prefix: str) -> Optional[str]:
    if not summary or not prefix:
        return None
    for line in summary.splitlines():
        stripped = line.strip()
        if stripped.startswith(f"{prefix}:"):
            value = stripped[len(prefix) + 1 :].strip()
            if value and not value.startswith("（"):
                return value
    return None


def _is_followup_available(record: Dict[str, object]) -> bool:
    return _extract_session_context(record) is not None


def _extract_session_context(record: Dict[str, object]) -> Optional[Dict[str, object]]:
    snapshot = record.get("payload_snapshot")
    if not isinstance(snapshot, dict):
        return None
    session_dict = snapshot.get("session_dict")
    if isinstance(session_dict, dict):
        return session_dict
    # Legacy rows may have stored raw SessionResult dict at top-level.
    has_context = any(
        key in snapshot
        for key in (
            "topic",
            "user_question",
            "current_time_str",
            "method",
            "lines",
            "hex_text",
            "bazi_output",
            "elements_output",
            "najia_data",
        )
    )
    if has_context:
        return snapshot
    return None
