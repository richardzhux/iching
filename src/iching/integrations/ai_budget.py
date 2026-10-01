from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from time import monotonic
from typing import Iterator

AI_MAX_INPUT_BYTES = 65_536
AI_MAX_OUTPUT_TOKENS = 8_192
AI_TOKEN_OVERHEAD = 2_048
AI_PROVIDER_TOTAL_SECONDS = 135.0


class AIDeadlineExceeded(TimeoutError):
    """The request's shared provider deadline expired without a safe retry."""


@dataclass
class AICallBudget:
    max_input_bytes: int = AI_MAX_INPUT_BYTES
    max_output_tokens: int = AI_MAX_OUTPUT_TOKENS
    dispatched: bool = False
    usage: dict[str, int] | None = None
    response_id: str | None = None
    provider_total_seconds: float = AI_PROVIDER_TOTAL_SECONDS
    provider_deadline: float | None = None

    def remaining_seconds(self) -> float:
        """Start once at dispatch; compatibility retries share the same deadline."""
        now = monotonic()
        if self.provider_deadline is None:
            self.provider_deadline = now + self.provider_total_seconds
        remaining = self.provider_deadline - now
        if remaining <= 0:
            raise AIDeadlineExceeded("AI 响应超时，请查询本次请求状态后再继续。")
        return remaining


_ACTIVE_BUDGET: ContextVar[AICallBudget | None] = ContextVar("iching_ai_budget", default=None)


def get_ai_budget() -> AICallBudget:
    return _ACTIVE_BUDGET.get() or AICallBudget()


@contextmanager
def use_ai_budget(budget: AICallBudget) -> Iterator[AICallBudget]:
    token = _ACTIVE_BUDGET.set(budget)
    try:
        yield budget
    finally:
        _ACTIVE_BUDGET.reset(token)
