from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Iterator

AI_MAX_INPUT_BYTES = 65_536
AI_MAX_OUTPUT_TOKENS = 8_192
AI_TOKEN_OVERHEAD = 2_048


@dataclass
class AICallBudget:
    max_input_bytes: int = AI_MAX_INPUT_BYTES
    max_output_tokens: int = AI_MAX_OUTPUT_TOKENS
    dispatched: bool = False
    usage: dict[str, int] | None = None
    response_id: str | None = None


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
