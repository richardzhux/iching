from __future__ import annotations

import json
from datetime import date, datetime
from typing import Dict, List, Literal, Optional

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
    label: str
    tier: str
    description: str
    reasoning: List[str] = Field(default_factory=list)
    default_reasoning: Optional[str] = None
    verbosity: bool = False
    default_verbosity: Optional[str] = None


class SessionCreateRequest(BaseModel):
    topic: str
    user_question: Optional[str] = None
    user_context: Optional[str] = None
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
            raise ValueError(
                "timestamp must be provided when use_current_time is false"
            )
        return self

    @model_validator(mode="after")
    def _validate_manual_lines(self) -> "SessionCreateRequest":
        if self.manual_lines is None:
            return self
        if len(self.manual_lines) != 6:
            raise ValueError("manual_lines must contain exactly 6 values")
        invalid = [
            value for value in self.manual_lines if value not in ALLOWED_LINE_VALUES
        ]
        if invalid:
            raise ValueError("manual_lines can only contain 6, 7, 8, or 9")
        return self


class SessionPayload(BaseModel):
    summary_text: str
    hex_text: str
    hex_sections: List[Dict[str, object]]
    hex_overview: Dict[str, object]
    bazi_detail: List[Dict[str, object]]
    reading_brief: Dict[str, object]
    najia_text: str
    najia_table: Dict[str, object]
    ai_text: str
    session_dict: Dict[str, object]
    archive_path: str
    full_text: str
    session_id: str
    ai_enabled: bool
    ai_model: Optional[str] = None
    ai_reasoning: Optional[str] = None
    ai_verbosity: Optional[str] = None
    ai_tone: Optional[str] = None
    ai_response_id: Optional[str] = None
    ai_usage: Dict[str, int] = Field(default_factory=dict)
    user_authenticated: bool = False


class ConfigResponse(BaseModel):
    topics: List[TopicInfo]
    methods: List[MethodInfo]
    ai_models: List[ModelInfo]
    default_model: str
    model_aliases: Dict[str, str] = Field(default_factory=dict)


class MetaphysicsChartRequest(BaseModel):
    timestamp: datetime
    timezone: str = "Asia/Shanghai"
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    use_true_solar_time: bool = False
    day_boundary: Literal["current", "forward"] = "forward"
    calendar_type: Literal["solar", "lunar"] = "solar"
    is_leap_month: bool = False
    gender: Optional[Literal["male", "female"]] = None
    birth_place: Optional[str] = Field(default=None, max_length=120)
    hour_uncertain: bool = False
    dayun_algorithm: Literal["sect1", "sect2"] = "sect2"
    lunar_year: Optional[int] = Field(default=None, ge=1, le=9999)
    lunar_month: Optional[int] = Field(default=None, ge=1, le=12)
    lunar_day: Optional[int] = Field(default=None, ge=1, le=30)
    lunar_hour: Optional[int] = Field(default=None, ge=0, le=23)
    lunar_minute: Optional[int] = Field(default=None, ge=0, le=59)
    fold_choice: Optional[Literal["first", "second"]] = None
    reference_timestamp: Optional[datetime] = None
    include_period_details: bool = False
    period_cycle_index: Optional[int] = Field(default=None, ge=0, le=19)

    @model_validator(mode="after")
    def _validate_lunar_input(self) -> "MetaphysicsChartRequest":
        if self.calendar_type == "lunar" and None in (
            self.lunar_year,
            self.lunar_month,
            self.lunar_day,
        ):
            raise ValueError(
                "lunar_year, lunar_month, and lunar_day are required for lunar input"
            )
        return self


class MetaphysicsPeriodRequest(MetaphysicsChartRequest):
    cycle_index: int = Field(ge=0, le=19)


class PatternLifecycleTransitionResponse(BaseModel):
    before: str
    after: str
    pattern_id: str = Field(alias="patternId")
    path_id: str = Field(alias="pathId")
    rule_ids: List[str] = Field(default_factory=list, alias="ruleIds")
    source_ids: List[str] = Field(default_factory=list, alias="sourceIds")

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class PeriodThemeActivationResponse(BaseModel):
    id: str
    layer: Literal["dayun", "liunian", "liuyue", "period"]
    kind: Literal["新增", "联动", "冲突", "变化"]
    role: Literal[
        "activity", "formation", "rescue", "support", "damage", "conflict", "neutral"
    ]
    delta: float
    activity: float = Field(ge=0)
    feature: str
    label: str
    detail: str
    source: str
    evidence_ids: List[str] = Field(default_factory=list, alias="evidenceIds")
    rule_ids: List[str] = Field(default_factory=list, alias="ruleIds")
    source_ids: List[str] = Field(default_factory=list, alias="sourceIds")
    lifecycle: Optional[PatternLifecycleTransitionResponse] = None

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class PeriodMonthResponse(BaseModel):
    layer: Literal["liuyue"]
    index: int
    label: str
    ganzhi: str
    ten_god: str
    xunkong: str
    start_timestamp: datetime
    end_timestamp: datetime
    is_current: bool
    shen_sha: List[str] = Field(default_factory=list)
    relations: List[str] = Field(default_factory=list)
    theme_activations: Dict[str, List[PeriodThemeActivationResponse]] = Field(
        default_factory=dict
    )

    model_config = ConfigDict(extra="forbid")


class PeriodYearResponse(BaseModel):
    layer: Literal["liunian"]
    index: int
    year: int
    age: int
    label: str
    ganzhi: str
    ten_god: str
    xunkong: str
    start_timestamp: datetime
    end_timestamp: datetime
    is_current: bool
    shen_sha: List[str] = Field(default_factory=list)
    relations: List[str] = Field(default_factory=list)
    theme_activations: Dict[str, List[PeriodThemeActivationResponse]] = Field(
        default_factory=dict
    )
    months: List[PeriodMonthResponse] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class DayunCycleResponse(BaseModel):
    index: int
    label: str
    ganzhi: str
    start_year: int
    end_year: int
    start_age: int
    end_age: int
    start_timestamp: datetime
    end_timestamp: datetime
    is_current: bool
    ten_god: str
    shen_sha: List[str] = Field(default_factory=list)
    relations: List[str] = Field(default_factory=list)
    theme_activations: Dict[str, List[PeriodThemeActivationResponse]] = Field(
        default_factory=dict
    )
    years: List[PeriodYearResponse] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class MetaphysicsPeriodResponse(BaseModel):
    cycle: DayunCycleResponse

    model_config = ConfigDict(extra="forbid")


class RuleVersions(BaseModel):
    """Version tuple required to reproduce a generated BaZi result."""

    calendar: str = Field(min_length=1, max_length=80)
    pattern_bundle: str = Field(min_length=1, max_length=120)
    pattern_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    shensha: str = Field(min_length=1, max_length=80)
    consumer: str = Field(min_length=1, max_length=80)

    model_config = ConfigDict(extra="forbid")


class MetaphysicsChartResponse(BaseModel):
    timezone: str
    input_timestamp: str
    calculation_timestamp: str
    calculation_mode: str
    true_solar_correction_minutes: float
    day_boundary: str
    lunar_date: str
    pillars: List[Dict[str, object]]
    bazi: str
    day_master: str
    xunkong: str
    stem_relations: List[str] = Field(default_factory=list)
    branch_relations: List[str] = Field(default_factory=list)
    element_season_status: Dict[str, str] = Field(default_factory=dict)
    calendar_facts: Dict[str, object]
    element_counts: Dict[str, int]
    calculation_quality: Dict[str, object] = Field(default_factory=dict)
    boundary_flags: Dict[str, object] = Field(default_factory=dict)
    previous_solar_term: Optional[Dict[str, object]] = None
    next_solar_term: Optional[Dict[str, object]] = None
    birth_profile: Dict[str, object]
    derived_schema_version: int = 7
    rules_version: str
    rule_versions: RuleVersions
    shen_sha: List[Dict[str, object]] = Field(default_factory=list)
    structure: Dict[str, object] = Field(default_factory=dict)
    theme_profiles: List[Dict[str, object]] = Field(default_factory=list)
    synthesis: Dict[str, object] = Field(default_factory=dict)
    statistics: Dict[str, object]
    period_layers: Dict[str, object]
    consumer: Dict[str, object] = Field(default_factory=dict)


class PatternRuleSourceSegmentSummary(BaseModel):
    id: str
    text_type: str
    review_state: Literal["scan_verified"]

    model_config = ConfigDict(extra="forbid")


class PatternRuleSourceLocatorSummary(BaseModel):
    id: str
    witness_id: str
    rights_status: Literal[
        "public_domain",
        "open_license",
        "licensed",
        "permission_granted",
        "owned",
    ]
    review_state: Literal["scan_verified"]
    visually_verified: Literal[True]
    quote: Optional[str] = None
    pdf_page: Optional[int] = Field(default=None, ge=1)
    printed_page: Optional[str] = None
    column_line: Optional[str] = None
    url: Optional[str] = Field(default=None, pattern=r"^https?://")

    model_config = ConfigDict(extra="forbid")


class PatternRuleSourceSummary(BaseModel):
    proposition_id: str
    authority_layer: str
    text_type: str
    review_state: Literal["scan_verified"]
    segments: List[PatternRuleSourceSegmentSummary] = Field(default_factory=list)
    locators: List[PatternRuleSourceLocatorSummary] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class PatternRuleSummaryResponse(BaseModel):
    bundle_id: str
    bundle_digest: str
    rule_id: str
    pattern_id: str
    title: str
    summary: str
    stage: str
    effect: str
    path_id: Optional[str] = None
    authority_layer: str
    sources: List[PatternRuleSourceSummary] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class PatternExampleSummary(BaseModel):
    id: str
    chapter_id: str
    pattern_id: str
    name: str
    pillars: List[str] = Field(default_factory=list)
    author_claim: str = ""
    classification: str = ""
    review_state: str = ""
    locator_ids: List[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class PatternLibraryResponse(BaseModel):
    version: str
    digest: str
    pattern_id: str
    label: str
    candidate_count: int = Field(ge=0)
    executable_count: int = Field(ge=0)
    status_counts: Dict[str, int] = Field(default_factory=dict)
    examples: List[PatternExampleSummary] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class MetaphysicsStatisticsRequest(BaseModel):
    chart_type: Literal["bazi", "ziwei"]
    baseline_id: str = Field(min_length=1, max_length=120)
    feature_ids: List[str] = Field(default_factory=list, max_length=128)

    @model_validator(mode="after")
    def validate_feature_ids(self):
        import re

        pattern = re.compile(r"^(bazi|ziwei)\.[a-z0-9_.-]{1,96}$")
        if any(
            not pattern.fullmatch(item) or not item.startswith(f"{self.chart_type}.")
            for item in self.feature_ids
        ):
            raise ValueError("feature_ids must be normalized and match chart_type")
        return self


class MetaphysicsStatisticsResponse(BaseModel):
    baseline: Dict[str, object]
    rarity_metrics: List[Dict[str, object]] = Field(default_factory=list)
    theme_profile: List[Dict[str, object]] = Field(default_factory=list)
    theme_profiles: List[Dict[str, object]] = Field(default_factory=list)
    consumer_baseline: Dict[str, object] = Field(default_factory=dict)
    status: Literal["available", "unavailable", "version_mismatch"] = "available"
    unavailable_reason: Optional[str] = None
    disclaimer: str


class ChartSubjectInput(BaseModel):
    id: Optional[str] = None
    display_name: Optional[str] = Field(default=None, max_length=80)
    birth_local_timestamp: datetime
    timezone: str = Field(min_length=1, max_length=80)
    calendar_type: Literal["solar", "lunar"] = "solar"
    gender: Optional[Literal["male", "female"]] = None
    birth_place: Optional[str] = Field(default=None, max_length=160)
    location_id: Optional[str] = Field(default=None, max_length=240)
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)


class MetaphysicsChartSaveRequest(BaseModel):
    id: Optional[str] = None
    chart_type: Literal["bazi", "ziwei"]
    subject: ChartSubjectInput
    title: Optional[str] = Field(default=None, max_length=120)
    birth_date: date
    day_pillar: Optional[str] = Field(default=None, max_length=16)
    input_snapshot: Dict[str, object]
    result_snapshot: Dict[str, object]
    engine_name: str = Field(min_length=1, max_length=80)
    engine_version: str = Field(min_length=1, max_length=40)
    rules_version: str = Field(min_length=1, max_length=80)
    schema_version: int = Field(default=1, ge=1, le=32767)

    @model_validator(mode="after")
    def validate_snapshot_sizes(self):
        input_bytes = len(
            json.dumps(
                self.input_snapshot, ensure_ascii=False, separators=(",", ":")
            ).encode()
        )
        result_bytes = len(
            json.dumps(
                self.result_snapshot, ensure_ascii=False, separators=(",", ":")
            ).encode()
        )
        if input_bytes > 262_144:
            raise ValueError("命盘输入快照不能超过 256 KB。")
        if result_bytes > 2_097_152:
            raise ValueError("命盘结果快照不能超过 2 MB。")
        if self.chart_type == "bazi":
            chart = self.result_snapshot.get("chart")
            derived_schema_version = (
                chart.get("derived_schema_version") if isinstance(chart, dict) else None
            )
            if derived_schema_version is not None and (
                not isinstance(derived_schema_version, int)
                or isinstance(derived_schema_version, bool)
            ):
                raise ValueError("八字命盘快照的 derived_schema_version 无效。")
            requires_rule_versions = (
                self.schema_version >= 7 or (derived_schema_version or 0) >= 7
            )
            if not requires_rule_versions:
                return self
            if not isinstance(chart, dict):
                raise ValueError("schema 7 命盘快照缺少 chart。")
            try:
                RuleVersions.model_validate(chart.get("rule_versions"))
            except (TypeError, ValueError) as exc:
                raise ValueError("schema 7 命盘快照缺少完整的规则版本。") from exc
        return self


class ChartSubjectResponse(BaseModel):
    id: str
    display_name: Optional[str] = None
    birth_local_timestamp: datetime
    timezone: str
    utc_offset_minutes: int
    calendar_type: Literal["solar", "lunar"]
    gender: Optional[Literal["male", "female"]] = None
    birth_place: Optional[str] = None
    location_id: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class MetaphysicsChartRecord(BaseModel):
    id: str
    subject_id: str
    chart_type: Literal["bazi", "ziwei"]
    title: Optional[str] = None
    birth_date: date
    day_pillar: Optional[str] = None
    input_snapshot: Dict[str, object]
    result_snapshot: Dict[str, object]
    engine_name: str
    engine_version: str
    rules_version: str
    schema_version: int
    pinned: bool = False
    created_at: datetime
    updated_at: datetime
    last_opened_at: datetime
    subject: ChartSubjectResponse


class MetaphysicsChartSummary(BaseModel):
    id: str
    subject_id: str
    chart_type: Literal["bazi", "ziwei"]
    title: Optional[str] = None
    display_name: Optional[str] = None
    birth_date: date
    day_pillar: Optional[str] = None
    birth_place: Optional[str] = None
    engine_name: str
    engine_version: str
    pinned: bool = False
    created_at: datetime
    updated_at: datetime


class MetaphysicsChartListResponse(BaseModel):
    charts: List[MetaphysicsChartSummary]


class ChatTurnRequest(BaseModel):
    message: str
    reasoning: Optional[str] = None
    verbosity: Optional[str] = None
    tone: Optional[str] = None
    model: Optional[str] = None
    restart: bool = False


class ChatMessage(BaseModel):
    id: Optional[str] = None
    role: Literal["user", "assistant"]
    content: str
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None
    created_at: Optional[datetime] = None
    model: Optional[str] = None
    reasoning: Optional[str] = None
    verbosity: Optional[str] = None
    tone: Optional[str] = None


class ChatTurnResponse(BaseModel):
    session_id: str
    assistant: ChatMessage
    usage: Dict[str, int]


class ChatTranscriptResponse(BaseModel):
    session_id: str
    summary_text: Optional[str] = None
    initial_ai_text: Optional[str] = None
    messages: List[ChatMessage]
    followup_model: Optional[str] = None
    ai_reasoning: Optional[str] = None
    ai_verbosity: Optional[str] = None
    ai_tone: Optional[str] = None
    payload_snapshot: Optional[Dict[str, object]] = None


class SessionSummary(BaseModel):
    session_id: str
    summary_text: Optional[str] = None
    created_at: Optional[datetime] = None
    ai_enabled: bool = False
    followup_available: bool = False
    topic_label: Optional[str] = None
    method_label: Optional[str] = None


class SessionHistoryResponse(BaseModel):
    sessions: List[SessionSummary]
