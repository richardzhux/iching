from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from iching.integrations.ai import DEFAULT_MODEL

ALLOWED_LINE_VALUES = {6, 7, 8, 9}


class TopicInfo(BaseModel):
    key: str
    label: str


class MethodInfo(BaseModel):
    key: str
    label: str


class ModelInfo(BaseModel):
    name: str
    reasoning: List[str] = Field(default_factory=list)
    default_reasoning: Optional[str] = None
    verbosity: bool = False
    default_verbosity: Optional[str] = None


class SessionCreateRequest(BaseModel):
    topic: str
    user_question: Optional[str] = None
    method_key: str
    manual_lines: Optional[List[int]] = None
    use_current_time: bool = True
    timestamp: Optional[datetime] = None
    enable_ai: bool = False
    access_password: Optional[str] = None
    ai_model: str = DEFAULT_MODEL
    ai_reasoning: Optional[str] = None
    ai_verbosity: Optional[str] = None
    ai_tone: Optional[str] = "normal"

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def _validate_time(self) -> "SessionCreateRequest":
        if not self.use_current_time and self.timestamp is None:
            raise ValueError("timestamp must be provided when use_current_time is false")
        return self

    @model_validator(mode="after")
    def _validate_manual_lines(self) -> "SessionCreateRequest":
        if self.manual_lines is None:
            return self
        if len(self.manual_lines) != 6:
            raise ValueError("manual_lines must contain exactly 6 values")
        invalid = [value for value in self.manual_lines if value not in ALLOWED_LINE_VALUES]
        if invalid:
            raise ValueError("manual_lines can only contain 6, 7, 8, or 9")
        return self


class SessionPayload(BaseModel):
    summary_text: str
    hex_text: str
    hex_sections: List[Dict[str, object]]
    hex_overview: Dict[str, object]
    najia_text: str
    najia_table: Dict[str, object]
    ai_text: str
    session_dict: Dict[str, object]
    archive_path: str
    full_text: str


class ConfigResponse(BaseModel):
    topics: List[TopicInfo]
    methods: List[MethodInfo]
    ai_models: List[ModelInfo]
