from __future__ import annotations

import hashlib
import hmac
import json
import os
from uuid import UUID

from iching.integrations.ai_budget import AICallBudget, AI_MAX_INPUT_BYTES, AI_MAX_OUTPUT_TOKENS, AI_TOKEN_OVERHEAD
from iching.web.errors import AccessDeniedError


class AIOperationLimitError(RuntimeError):
    pass


def validate_ai_access(password: str | None) -> None:
    expected = os.getenv("OPENAI_PW", "")
    if not expected or not password or not hmac.compare_digest(password.encode(), expected.encode()):
        raise AccessDeniedError("请输入有效的 AI 使用密码后再继续。")


def operation_id(value: str | None) -> str:
    try:
        return str(UUID(str(value)))
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError("AI 请求需要有效的请求编号，请刷新页面后重试。") from exc


class AIOperations:
    def __init__(self, client):
        self.client = client

    def admit(self, *, user_id, request_id, session_id, kind, semantics, reserve):
        fingerprint = hashlib.sha256(json.dumps(semantics, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()
        result = self.client.rpc("admit_ai_operation", {
            "p_user_id": user_id, "p_request_id": request_id, "p_session_id": session_id,
            "p_kind": kind, "p_fingerprint": fingerprint, "p_reserve": reserve,
            "p_daily_limit": max(1, int(os.getenv("ICHING_USER_DAILY_TOKEN_LIMIT", "300000"))),
            "p_session_limit": max(1, int(os.getenv("ICHING_CHAT_TOKEN_LIMIT", "150000"))),
            "p_turn_limit": max(1, int(os.getenv("ICHING_CHAT_TURN_LIMIT", "10"))),
            "p_initial_limit": 50,
            "p_global_limit": max(0, int(os.getenv("ICHING_GLOBAL_DAILY_TOKEN_LIMIT", "0"))),
        })
        state = result.get("status")
        if state in {"admitted", "completed"}:
            return result
        if state == "conflict":
            raise ValueError("请求编号对应的内容已改变，请为新问题创建新请求。")
        if state in {"pending", "busy"}:
            raise AIOperationLimitError("AI 请求仍在处理中，请稍后重试同一请求，不要重复提交。")
        if state in {"uncertain", "failed"}:
            raise AIOperationLimitError("该请求未能确认完成，已阻止再次扣费。请先检查记录；如需重新生成，请明确发起新请求。")
        if state == "missing":
            raise ValueError("会话不存在或不属于当前账户。")
        raise AIOperationLimitError("剩余 AI 额度不足以安全完成本次请求，请稍后或明日再试。")

    def finish(self, *, user_id, request_id, status, tokens, result=None):
        # This RPC is idempotent. A transport retry can never dispatch an AI call.
        payload = {"p_user_id": user_id, "p_request_id": request_id,
                   "p_status": status, "p_tokens": max(0, tokens), "p_result": result}
        try:
            return self.client.rpc("finish_ai_operation", payload)
        except Exception:
            return self.client.rpc("finish_ai_operation", payload)

    def fail(self, *, user_id, request_id, budget):
        usage = budget.usage
        known = isinstance(usage, dict)
        tokens = usage_tokens(usage) if known else 0
        # Ambiguous provider errors remain reserved, even after worker restart.
        status = "failed" if known or not budget.dispatched else "uncertain"
        self.finish(user_id=user_id, request_id=request_id, status=status, tokens=tokens,
                    result={"response_id": budget.response_id} if budget.response_id else None)


def usage_tokens(usage):
    return int((usage or {}).get("total_tokens") or (
        int((usage or {}).get("input_tokens") or 0) + int((usage or {}).get("output_tokens") or 0)))


def new_budget():
    return AICallBudget(max_input_bytes=AI_MAX_INPUT_BYTES, max_output_tokens=AI_MAX_OUTPUT_TOKENS)


def reservation_for(budget):
    # UTF-8 bytes conservatively bound text tokens; framing gets its own allowance.
    return budget.max_input_bytes + budget.max_output_tokens + AI_TOKEN_OVERHEAD
