from __future__ import annotations

import os
from datetime import datetime, timezone
from uuid import uuid4
from typing import Dict, List, Optional

from iching.integrations.ai import (
    MODEL_CAPABILITIES,
    continue_analysis_from_session,
    normalize_model_name,
    stream_continue_analysis_from_session,
)
from iching.integrations.supabase_client import (
    SupabaseAuthError,
    SupabaseRestClient,
    SupabaseUser,
)
from iching.services.session import SessionResult
from iching.web.chat_state import SessionState, SessionStateStore


from iching.integrations.ai_budget import use_ai_budget
from iching.integrations.ai import _build_followup_session_context, CHAT_CONTINUATION_PROMPT, TONE_PROFILES
from iching.web.ai_operations import (AIOperations, AIOperationLimitError, validate_ai_access,
    operation_id, new_budget, reservation_for, usage_tokens)


def followup_prompt(context, message):
    return ("以下是同一会话的固定占卜上下文，请据此回答用户追问，不要重起卦：\n\n"
            + _build_followup_session_context(context) + "\n\n用户追问：" + message)


CHAT_FOLLOWUP_MODEL = normalize_model_name(os.getenv("ICHING_CHAT_MODEL", "gpt-5.6-terra")) or "gpt-5.6-terra"
CHAT_MESSAGE_CHAR_LIMIT = int(os.getenv("ICHING_CHAT_MESSAGE_LIMIT", "10000"))
ANONYMOUS_USER_ID = os.getenv("ICHING_ANON_USER_ID", "00000000-0000-0000-0000-000000000000")
USER_SESSION_LIMIT = int(os.getenv("ICHING_USER_SESSION_LIMIT", "500"))


ChatRateLimitError = AIOperationLimitError


class ChatService:
    """Coordinates Supabase persistence and OpenAI follow-up calls."""

    def __init__(
        self,
        store: SessionStateStore,
        client: SupabaseRestClient,
    ) -> None:
        self.store = store
        self.client = client
        self.operations = AIOperations(client)

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
        self.client.upsert_session(payload)

    def ensure_session_row(self, session_id: str, user: SupabaseUser) -> Dict[str, object]:
        if not self.client.enabled:
            raise RuntimeError("Supabase is not configured on the server.")
        record = self.client.fetch_session(session_id=session_id, user_id=user.id)
        if record:
            return self._sync_followup_model(record, user.id)
        state = self.store.get(session_id, owner_id=user.id)
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
        record = self.client.upsert_session(payload) or payload
        self._persist_initial_message(state=state, user=user)
        return record

    def _sync_followup_model(self, record: Dict[str, object], user_id: str) -> Dict[str, object]:
        current_model = record.get("followup_model")
        normalized = normalize_model_name(str(current_model)) if current_model else None
        if normalized in MODEL_CAPABILITIES and normalized == current_model:
            return record
        next_model = normalized if normalized in MODEL_CAPABILITIES else CHAT_FOLLOWUP_MODEL
        payload = {"followup_model": next_model}
        self.client.update_session(session_id=record["session_id"], user_id=user_id, payload=payload)
        record["followup_model"] = next_model
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
        if not user.id:
            raise ValueError("用户无效。")
        result = self.client.rpc("list_session_summaries", {"p_user_id": user.id})
        records = result.get("sessions")
        if not isinstance(records, list):
            raise RuntimeError("Session summaries returned an invalid response.")
        return [
            {
                "session_id": record.get("session_id"),
                "summary_text": record.get("summary_text"),
                "created_at": record.get("created_at") or record.get("updated_at"),
                "ai_enabled": bool(record.get("ai_enabled")),
                "followup_available": bool(record.get("followup_available")),
                "topic_label": record.get("topic_label")
                or _infer_label_from_summary(record.get("summary_text"), prefix="主题"),
                "method_label": record.get("method_label")
                or _infer_label_from_summary(record.get("summary_text"), prefix="方法"),
            }
            for record in records or []
        ]

    def delete_session(self, session_id: str, user: SupabaseUser) -> None:
        if not self.client.enabled:
            raise RuntimeError("Supabase is not configured on the server.")
        if not user.id:
            raise ValueError("用户无效。")
        if not self.client.fetch_session(session_id=session_id, user_id=user.id):
            raise ValueError("会话不存在或不属于当前账户。")
        self.client.delete_session(session_id=session_id, user_id=user.id)
        self.store.remove(session_id)

    def execute_initial(self, *, request, user, callback):
        from iching.web.models import SessionPayload
        validate_ai_access(request.access_password)
        request_id = operation_id(request.request_id)
        if normalize_model_name(request.ai_model) not in MODEL_CAPABILITIES:
            raise ValueError("不支持的 AI 模型。")
        budget = new_budget()
        admitted = self.operations.admit(
            user_id=user.id, request_id=request_id, session_id=None, kind="initial",
            semantics=request.model_dump(mode="json", exclude={"request_id", "access_password"}),
            reserve=reservation_for(budget),
        )
        if admitted["status"] == "completed":
            return SessionPayload.model_validate(admitted["result"])
        try:
            with use_ai_budget(budget):
                result = callback()
            tokens = usage_tokens(budget.usage)
            if budget.dispatched and not isinstance(budget.usage, dict):
                raise RuntimeError("AI 用量尚未确认，已阻止重复扣费。")
            self.operations.finish(user_id=user.id, request_id=request_id,
                                   status="completed", tokens=tokens,
                                   result=result.model_dump(mode="json"))
            return result
        except BaseException:
            self.operations.fail(user_id=user.id, request_id=request_id, budget=budget)
            raise

    def _prepare_followup(self, *, session_id, user, message, reasoning, verbosity,
                          tone, model_override, restart, request_id, access_password):
        validate_ai_access(access_password)
        request_id = operation_id(request_id)
        stripped = message.strip()
        if not stripped or len(stripped) > CHAT_MESSAGE_CHAR_LIMIT:
            raise ValueError(f"追问内容需为 1–{CHAT_MESSAGE_CHAR_LIMIT} 字符。")
        record = self.ensure_session_row(session_id, user)
        chosen_model = normalize_model_name(model_override or str(record.get("followup_model") or CHAT_FOLLOWUP_MODEL))
        if chosen_model not in MODEL_CAPABILITIES:
            raise ValueError("不支持的 AI 模型。")
        context = _extract_session_context(record)
        if not context:
            raise ValueError("当前会话缺少完整快照，无法开启 AI 追问。")
        context = dict(context)
        history = self.client.fetch_chat_messages(session_id=session_id, user_id=user.id)
        replacement_ids = _regeneration_message_ids(history, stripped) if restart else {}
        if restart:
            history = _history_before_regeneration(history, stripped)
        # Explicit context makes the provider's entire paid input measurable and bounded.
        # No hidden previous_response_id chain can silently expand the input budget.
        context["conversation_history"] = history[-20:]
        applied = {
            "model_name": chosen_model,
            "reasoning_effort": reasoning if reasoning is not None else record.get("ai_reasoning"),
            "verbosity": verbosity if verbosity is not None else record.get("ai_verbosity"),
            "tone": tone if tone is not None else record.get("ai_tone"),
        }
        budget = new_budget()
        prompt = followup_prompt(context, stripped)
        instructions = CHAT_CONTINUATION_PROMPT
        if applied["tone"]:
            instructions += f"\n\n语气设定: {applied['tone']} —— {TONE_PROFILES.get(applied['tone'], '用户自定义语气')}"
        while len((prompt + instructions).encode()) > budget.max_input_bytes and context["conversation_history"]:
            context["conversation_history"] = context["conversation_history"][2:]
            prompt = followup_prompt(context, stripped)
        input_bytes = len((prompt + instructions).encode())
        if input_bytes > budget.max_input_bytes:
            raise ValueError("本次占卜上下文过长，请缩短背景后重新起卦。")
        # Reserve the conservative bound for this exact explicit prompt, not a stale counter.
        budget.max_input_bytes = input_bytes
        admitted = self.operations.admit(
            user_id=user.id, request_id=request_id, session_id=session_id, kind="chat",
            semantics={"message":message,"reasoning":reasoning,"verbosity":verbosity,
                       "tone":tone,"model":model_override,"restart":restart},
            reserve=reservation_for(budget),
        )
        return {"request_id":request_id,"budget":budget,"admitted":admitted,
                "context":context,"message":stripped,"applied":applied,
                "replacement_ids":replacement_ids}

    def _complete_followup(self, *, session_id, user, prepared, result):
        budget = prepared["budget"]
        usage = budget.usage if isinstance(budget.usage, dict) else result.usage
        if not isinstance(usage, dict):
            raise RuntimeError("AI 用量尚未确认，已阻止重复扣费。")
        # Keep usage even if later transcript persistence fails.
        budget.usage = usage
        budget.response_id = result.response_id
        applied = prepared["applied"]
        common = {"session_id":session_id,"user_id":user.id,"model":applied["model_name"],
                  "reasoning":applied["reasoning_effort"],"verbosity":applied["verbosity"],"tone":applied["tone"]}
        user_record = {**common,"id":prepared["replacement_ids"].get("user") or str(uuid4()),
                       "role":"user","content":prepared["message"],
                       "tokens_in":int(usage.get("input_tokens") or 0),"tokens_out":0,
                       "created_at":datetime.now(timezone.utc).isoformat()}
        assistant = {**common,"id":prepared["replacement_ids"].get("assistant") or str(uuid4()),
                     "role":"assistant","content":result.text,"tokens_in":0,
                     "tokens_out":int(usage.get("output_tokens") or 0),
                     "created_at":datetime.now(timezone.utc).isoformat()}
        stored = {"assistant":assistant,"usage":usage,"_messages":[user_record,assistant],
                  "_session_patch":{"last_response_id":result.response_id,"followup_model":applied["model_name"],
                                    "ai_reasoning":applied["reasoning_effort"],"ai_verbosity":applied["verbosity"],"ai_tone":applied["tone"]}}
        self.operations.finish(user_id=user.id,request_id=prepared["request_id"],
                               status="completed",tokens=usage_tokens(usage),result=stored)
        self.store.update_response(session_id,result.response_id or "",increment_turn=True)
        self.store.add_tokens(session_id,usage_tokens(usage))
        return {"assistant":assistant,"usage":usage}

    def send_followup(self, *, session_id, user, message, reasoning=None, verbosity=None,
                      tone=None, model_override=None, restart=False, request_id=None, access_password=None):
        prepared = self._prepare_followup(session_id=session_id,user=user,message=message,
            reasoning=reasoning,verbosity=verbosity,tone=tone,model_override=model_override,
            restart=restart,request_id=request_id,access_password=access_password)
        if prepared["admitted"]["status"] == "completed":
            cached = prepared["admitted"]["result"]
            return {"assistant":cached["assistant"],"usage":cached["usage"]}
        try:
            with use_ai_budget(prepared["budget"]):
                result = continue_analysis_from_session(session_data=prepared["context"],
                    message=prepared["message"],**prepared["applied"])
            return self._complete_followup(session_id=session_id,user=user,prepared=prepared,result=result)
        except BaseException:
            self.operations.fail(user_id=user.id,request_id=prepared["request_id"],budget=prepared["budget"])
            raise

    def stream_followup(self, *, session_id, user, message, reasoning=None, verbosity=None,
                        tone=None, model_override=None, restart=False, request_id=None, access_password=None):
        prepared = self._prepare_followup(session_id=session_id,user=user,message=message,
            reasoning=reasoning,verbosity=verbosity,tone=tone,model_override=model_override,
            restart=restart,request_id=request_id,access_password=access_password)
        if prepared["admitted"]["status"] == "completed":
            cached = prepared["admitted"]["result"]
            return iter([{"type":"completed","assistant":cached["assistant"],"usage":cached["usage"]}])
        def generate():
            try:
                result = None
                stream = iter(stream_continue_analysis_from_session(
                    session_data=prepared["context"], message=prepared["message"],
                    **prepared["applied"]))
                try:
                    while True:
                        # Starlette may advance each chunk in a different Context.
                        # Never keep a ContextVar token alive across a yield.
                        with use_ai_budget(prepared["budget"]):
                            try:
                                event = next(stream)
                            except StopIteration:
                                break
                        if event.get("type") == "delta":
                            yield {"type":"delta","delta":str(event.get("delta") or "")}
                        elif event.get("type") == "result":
                            result = event.get("result")
                finally:
                    close = getattr(stream, "close", None)
                    if close:
                        with use_ai_budget(prepared["budget"]):
                            close()
                if result is None:
                    raise RuntimeError("AI 未确认完成，已阻止重复扣费。")
                completed = self._complete_followup(session_id=session_id,user=user,prepared=prepared,result=result)
                yield {"type":"completed",**completed}
            except BaseException:
                self.operations.fail(user_id=user.id,request_id=prepared["request_id"],budget=prepared["budget"])
                raise
        return generate()

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


def _history_before_regeneration(records: List[Dict[str, object]], message: str) -> List[Dict[str, object]]:
    history = list(records)
    if history and history[-1].get("role") == "assistant":
        history.pop()
    if history and history[-1].get("role") == "user" and str(history[-1].get("content") or "").strip() == message:
        history.pop()
    return history[-20:]


def _regeneration_message_ids(records: List[Dict[str, object]], message: str) -> Dict[str, str]:
    """Reuse the last turn's row ids so regeneration replaces it instead of duplicating it."""
    history = list(records)
    result: Dict[str, str] = {}
    if history and history[-1].get("role") == "assistant":
        assistant_id = history[-1].get("id")
        if assistant_id:
            result["assistant"] = str(assistant_id)
        history.pop()
    if history and history[-1].get("role") == "user" and str(history[-1].get("content") or "").strip() == message:
        user_id = history[-1].get("id")
        if user_id:
            result["user"] = str(user_id)
    return result


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
