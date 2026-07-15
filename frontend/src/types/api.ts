export type TopicInfo = {
  key: string
  label: string
}

export type MethodInfo = {
  key: string
  label: string
}

export type ModelInfo = {
  name: string
  label: string
  tier: "standard" | "deep" | "more" | "expert" | "fast" | string
  description: string
  reasoning: string[]
  default_reasoning?: string | null
  verbosity?: boolean
  default_verbosity?: string | null
}

export type ConfigResponse = {
  topics: TopicInfo[]
  methods: MethodInfo[]
  ai_models: ModelInfo[]
  default_model: string
  model_aliases: Record<string, string>
}

export type MetaphysicsPillar = {
  label: string
  stem: string
  branch: string
  text: string
  stem_element: string
  branch_element: string
  polarity: string
  ten_god: string
  hidden_stems: Array<{ stem: string; element: string; ten_god: string }>
  nayin: string
  xunkong: string
  di_shi: string
  self_seat: string
}

export type ShenShaHit = {
  rule_id: string
  feature_id: string
  name: string
  category: string
  axis: "助力" | "才学" | "情缘" | "执行" | "迁动" | "考验"
  level: "core" | "extended"
  pillar_labels: string[]
  trigger: string
  source: { title: string; note: string }
  school_note?: string
  topic_tags: Array<"career" | "wealth" | "relationship" | "health">
  formula_digest?: string
  anchors?: Array<{ reference: string; label: string; field: string; value: string; targets: string[]; target_roles?: Record<string, string[]> }>
  formula?: { method: string; anchor: string; anchor_selector: string; candidate_field: string; candidate_scope: string; mapping: Record<string, unknown> }
  registry_version?: string
  registry_digest?: string
  rules_version: string
  state?: "发力" | "有力" | "可见" | "受制"
  state_reason?: string
  effect_score?: number
  rarity_percentage?: number
}

export type PatternCandidate = {
  id: string
  name: string
  title?: string
  status: "成格" | "得用" | "受制" | "救成" | "混杂" | "转化" | string
  score?: number
  strength?: number | "effective" | "ordinary" | "weak" | "none" | string
  summary?: string
  evidence?: Array<string | Record<string, unknown>>
  evidence_ids?: string[]
  constraints?: string[]
  rescues?: string[]
  tensions?: string[]
  selection?: string
  formation?: string
  formation_path?: {
    id: string
    title: string
    evidence_weight?: number
    details?: string[]
  } | null
  formation_paths?: Array<{
    id: string
    title: string
    evidence_weight?: number
    details?: string[]
  }>
  integrity?: string
  rescue?: string
  purity?: string
  authenticity?: string
  role?: string
}

export type PatternAssessment = {
  rules_version: string
  primary: PatternCandidate | null
  ordinary: PatternCandidate[]
  special: PatternCandidate[]
  evidence?: Array<Record<string, unknown>>
  effective_structure?: Record<string, unknown>
  source_refs?: string[]
}

export type ConsumerSubjectPath = {
  key: "career" | "wealth" | "relationship" | "health"
  label: string
  /** @deprecated Legacy snapshot only; new profile builders never populate this. */
  score?: number
  /** @deprecated Legacy snapshot only; new profile builders never populate this. */
  raw_score?: number
  /** @deprecated Legacy snapshot only; new profile builders never populate this. */
  global_percentile?: number
  /** @deprecated Legacy snapshot only; new profile builders never populate this. */
  global_top_percentage?: number
  /** @deprecated Legacy snapshot only; new profile builders never populate this. */
  cohort_percentile?: number
  /** @deprecated Legacy snapshot only; new profile builders never populate this. */
  cohort_top_percentage?: number
  headline: string
  drivers?: string[]
  path_label?: string
  path_summary?: string
}

/** @deprecated Compatibility alias for components that still use the old type name. */
export type ConsumerSubjectScore = ConsumerSubjectPath

export type ConsumerAchievement = {
  id: string
  title: string
  tier: "SSR" | "SR" | "R" | string
  state: string
  rarity_percentage: number
  position: string
  summary: string
  member_ids: string[]
}

export type ConsumerFingerprint = {
  id: string
  title: string
  detail: string
  rarity_label: string
  top_percentage: number
  incidence_percentage?: number | null
}

export type LifeKlineMonth = {
  index: number
  label: string
  ganzhi: string
  value: number
  delta: number
  drivers: string[]
  intensity?: number
}

export type LifeKlinePoint = {
  year: number
  open: number
  close: number
  high: number
  low: number
  volume: number
  ma3: number | null
  ma5: number | null
  ma10: number | null
  months: LifeKlineMonth[]
}

export type LifeKlineSeries = {
  default_window: { start_year: number; end_year: number }
  series: Array<{
    key: "overall" | "career" | "wealth" | "relationship" | "health" | string
    label: string
    color: string
    points: LifeKlinePoint[]
  }>
  period_bands: Array<{ label: string; start_year: number; end_year: number }>
  stages: Array<{ key: string; label: string; year: number; score: number; theme: string; summary: string }>
  method: string
}

export type ConsumerProfile = {
  version: string
  system: "bazi" | "ziwei"
  identity: {
    system_title: string
    archetype_id?: string
    archetype_title: string
    archetype_subtitle: string
    fusion_title?: string | null
    /** Legacy score-era fields may exist on old snapshots. */
    main_score?: number
    global_percentile?: number
    global_top_percentage?: number
    cohort_percentile?: number
    cohort_top_percentage?: number
    cohort_label?: string
  }
  subjects: ConsumerSubjectPath[]
  achievements: ConsumerAchievement[]
  fingerprints: ConsumerFingerprint[]
  twin: {
    family_id: string
    title: string
    share_percentage: number
    summary: string
    representatives: string[]
  } | null
  life_kline: LifeKlineSeries
  capability_key: string | null
}

export type RarityMetric = {
  status: "observed" | "zero" | "unsupported"
  feature_id: string
  hit_weight: number
  total_weight: number
  percentage: number
  display_percentage: string
  level: "common" | "less_common" | "rare" | "very_rare" | "unavailable"
  baseline_id: string
}

export type ThemeEvidence = {
  id: string
  family: string
  evidence_type: "支持" | "制约" | "活动" | "背景"
  title: string
  detail: string
  source: string
}

export type ThemeStructureMetric = {
  definition_id?: string
  metric_id: string
  label: string
  value: number
  unit: string
  metric_type?: "ordinal" | "binary" | "categorical"
  source?: string
}

export type ThemeComparison = ThemeStructureMetric & {
  status: "observed" | "zero" | "unsupported"
  exact_weight?: number
  total_weight?: number
  exact_percentage?: number
  display_percentage: string
  comparison_mode?: "rank_interval" | "incidence" | "category_share"
  lower_percentage?: number
  same_percentage?: number
  higher_percentage?: number
  hit_percentage?: number
  rank_interval?: { lower: number; upper: number }
  same_mass?: number
  support_size?: number
  normalized_entropy?: number
  effective_support?: number
  resolution?: "high" | "medium" | "low"
  histogram?: Array<{ value: number | string; weight: number; percentage: number }>
  baseline_id: string
  method: "weighted_empirical_metric_distribution"
}

export type ThemeProfile = {
  theme: "事业" | "财富" | "感情" | "五行与承压结构"
  evidence: ThemeEvidence[]
  active_families?: string[]
  structure_metrics?: ThemeStructureMetric[]
  comparisons?: ThemeComparison[]
}

export type StructuralParticipant = {
  pillar: string
  layer: "stem" | "branch" | "hidden_stem"
  value: string
  element: string
  day_master_relation: "同我" | "我生" | "我克" | "克我" | "生我"
  ten_god: string
}

export type StructuralRelation = {
  relation_type: string
  participants: StructuralParticipant[]
  result_element?: string | null
  theme_tags: Array<"事业" | "财富" | "感情" | "五行与承压结构">
  source_rule: string
  label: string
}

export type MetaphysicsStatistics = {
  baseline: {
    id: string
    chart_type: "bazi" | "ziwei"
    kind: "calendar_sample_frequency"
    label: string
    start: string
    end: string
    timezone: string
    day_boundary: string
    engine: string
    rules_version: string
    sample_unit: string
    sample_weight: number
    unique_state_count?: number
    config_id?: string
    schema_version?: number
    feature_catalog_hash?: string
    registry_hash?: string
    weighting?: Record<string, number>
    time_index_weights?: number[]
    gender_scope?: string
    interval_semantics?: string
    method: string
    hash: string
  }
  rarity_metrics: RarityMetric[]
  consumer_baseline?: unknown
  disclaimer: string
  status?: "available" | "unavailable" | "version_mismatch"
  unavailable_reason?: string
}

export type PeriodMonth = {
  layer: "liuyue"
  index: number
  label: string
  ganzhi: string
  ten_god: string
  xunkong: string
  shen_sha: string[]
  relations: string[]
  theme_activations: PeriodThemeActivations
  start_timestamp?: string
  end_timestamp?: string
  is_current?: boolean
}

export type PeriodThemeActivation = {
  kind: "新增" | "联动" | "冲突" | "变化"
  label: string
  detail: string
  source: string
}

export type PeriodThemeActivations = Record<"事业" | "财富" | "感情" | "五行与承压结构", PeriodThemeActivation[]>

export type PeriodYear = {
  layer: "liunian"
  index: number
  year: number
  age: number
  label: string
  ganzhi: string
  ten_god: string
  xunkong: string
  shen_sha: string[]
  relations: string[]
  theme_activations: PeriodThemeActivations
  months: PeriodMonth[]
  start_timestamp?: string
  end_timestamp?: string
  is_current?: boolean
}

export type DayunCycle = {
  index: number
  label: string
  ganzhi: string
  start_year: number
  end_year: number
  start_age: number
  end_age: number
  ten_god?: string
  shen_sha: string[]
  relations: string[]
  theme_activations: PeriodThemeActivations
  years: PeriodYear[]
  start_timestamp?: string
  end_timestamp?: string
  is_current?: boolean
}

export type MetaphysicsChart = {
  timezone: string
  input_timestamp: string
  calculation_timestamp: string
  calculation_mode: string
  true_solar_correction_minutes: number
  day_boundary: string
  lunar_date: string
  pillars: MetaphysicsPillar[]
  bazi: string
  day_master: string
  xunkong: string
  stem_relations: string[]
  branch_relations: string[]
  element_season_status: Record<string, string>
  calendar_facts: {
    gregorian: string
    month_command: string
    day_pillar: string
    day_branch: string
    month_clash: string
    month_combine: string
    day_clash: string
    day_combine: string
    six_spirit_start: string
    six_spirits: string[]
  }
  element_counts: Record<string, number>
  calculation_quality: { status: "verified" | "verified_canonical" | "conflict" | "uncertain"; label: string; crosscheck?: string }
  boundary_flags: { near_solar_term?: boolean; nearest_solar_term_seconds?: number }
  derived_schema_version: number
  rules_version: string
  shen_sha: ShenShaHit[]
  structure: {
    day_master: { stem: string; element: string; rooted: boolean; root_pillars: string[]; month_status: string }
    day_master_relations: StructuralParticipant[]
    layered_distribution: {
      elements: Record<"visible_stems" | "branch_main_qi" | "hidden_stems", Record<string, number>>
      ten_gods: Record<"visible_stems" | "hidden_stems", Record<string, number>>
    }
    structural_relations: StructuralRelation[]
    theme_profiles: ThemeProfile[]
    synthesis?: BaziSynthesis
    patterns?: PatternAssessment
  }
  theme_profiles: ThemeProfile[]
  synthesis: BaziSynthesis
  statistics: MetaphysicsStatistics
  period_layers: {
    dayun: DayunCycle[]
    current: {
      as_of: string
      year: Omit<PeriodYear, "months"> | null
      month: PeriodMonth | null
    }
    engine: string
  }
  consumer?: ConsumerProfile
  previous_solar_term?: { name: string; timestamp: string; days_away: number; seconds_away: number } | null
  next_solar_term?: { name: string; timestamp: string; days_away: number; seconds_away: number } | null
  birth_profile: {
    calendar_type: "solar" | "lunar"
    input_date: string
    is_leap_month: boolean
    converted_solar_date?: string
    birth_place: string
    gender?: "male" | "female" | null
    hour_uncertain: boolean
    hour_candidates: Array<{ label: string; time_range: string; pillar: string; day_master?: string; pillars?: string[] }>
    stability?: {
      stable_pillars: Array<{ label: string; text: string; pillar: MetaphysicsPillar }>
      stable_shensha: string[]
      sensitive_items: Array<{ label: string; detail: string }>
      candidate_count: number
    }
    period_query?: MetaphysicsChartRequest
    dayun: {
      status: "not_requested" | "requires_hour" | "available"
      algorithm?: "sect1" | "sect2"
      algorithm_note?: string
      note?: string
      direction?: "forward" | "reverse"
      start?: { years: number; months: number; days: number; hours: number; solar_date: string }
      engine_bazi?: string
      crosscheck_matches?: boolean
      cycles: DayunCycle[]
      current?: {
        as_of: string
        year: Omit<PeriodYear, "months"> | null
        month: PeriodMonth | null
      }
    }
    engines: Record<string, string>
  }
}

export type MetaphysicsChartRequest = {
  timestamp: string
  timezone: string
  longitude?: number | null
  use_true_solar_time?: boolean
  day_boundary?: "current" | "forward"
  calendar_type?: "solar" | "lunar"
  is_leap_month?: boolean
  gender?: "male" | "female" | null
  birth_place?: string | null
  hour_uncertain?: boolean
  dayun_algorithm?: "sect1" | "sect2"
  lunar_year?: number | null
  lunar_month?: number | null
  lunar_day?: number | null
  lunar_hour?: number | null
  lunar_minute?: number | null
  fold_choice?: "first" | "second" | null
  reference_timestamp?: string | null
  include_period_details?: boolean
  period_cycle_index?: number | null
}

export type BaziConclusion = {
  id: string
  theme: string
  headline: string
  body: string
  supporting_evidence_ids: string[]
  counter_evidence_ids: string[]
  school_scope: string
  priority: number
  distribution_context?: string
}

export type BaziSynthesis = {
  method: string
  conclusions: BaziConclusion[]
}

export type ChartSubjectPayload = {
  id?: string | null
  display_name?: string | null
  birth_local_timestamp: string
  timezone: string
  calendar_type: "solar" | "lunar"
  gender?: "male" | "female" | null
  birth_place?: string | null
  location_id?: string | null
  latitude?: number | null
  longitude?: number | null
}

export type MetaphysicsChartSavePayload = {
  id?: string | null
  chart_type: "bazi" | "ziwei"
  subject: ChartSubjectPayload
  title?: string | null
  birth_date: string
  day_pillar?: string | null
  input_snapshot: Record<string, unknown>
  result_snapshot: Record<string, unknown>
  engine_name: string
  engine_version: string
  rules_version: string
  schema_version: number
}

export type ChartSubjectRecord = ChartSubjectPayload & {
  id: string
  utc_offset_minutes: number
}

export type MetaphysicsChartRecord = {
  id: string
  subject_id: string
  chart_type: "bazi" | "ziwei"
  title?: string | null
  birth_date: string
  day_pillar?: string | null
  input_snapshot: Record<string, unknown>
  result_snapshot: Record<string, unknown>
  engine_name: string
  engine_version: string
  rules_version: string
  schema_version: number
  pinned: boolean
  created_at: string
  updated_at: string
  last_opened_at: string
  subject: ChartSubjectRecord
}

export type MetaphysicsChartSummary = {
  id: string
  subject_id: string
  chart_type: "bazi" | "ziwei"
  title?: string | null
  display_name?: string | null
  birth_date: string
  day_pillar?: string | null
  birth_place?: string | null
  engine_name: string
  engine_version: string
  pinned: boolean
  created_at: string
  updated_at: string
}

export type MetaphysicsChartListResponse = {
  charts: MetaphysicsChartSummary[]
}

export type HexSection = {
  id: string
  hexagram_type: "main" | "changed"
  hexagram_name: string
  source_id?: string
  source?: "guaci" | "takashima" | string
  source_label?: string
  slot_key?: string
  section_kind: "top" | "line"
  line_key?: string | null
  title: string
  content: string
  importance: "primary" | "secondary"
  visible_by_default: boolean
}

export type HexLineInfo = {
  position: number
  value: number
  line_type: "yang" | "yin"
  is_moving: boolean
  moving_symbol: string
  changed_value: number
  changed_type: "yang" | "yin"
  changed_line_type?: "yang" | "yin"
}

export type HexOverview = {
  lines: HexLineInfo[]
  main_hexagram: {
    name: string
    explanation: string
  }
  changed_hexagram?: {
    name: string
    explanation: string
  } | null
}

export type NajiaMeta = {
  name?: string | null
  gong?: string | null
  type?: string | null
}

export type NajiaRow = {
  position: number
  line_type: "yang" | "yin"
  changed_line_type: "yang" | "yin"
  is_moving: boolean
  moving_symbol: string
  god: string
  hidden: string
  main_relation: string
  main_mark: string
  marker: string
  movement_tag: string
  changed_relation: string
  changed_mark: string
}

export type NajiaTable = {
  meta: {
    main: NajiaMeta | null
    changed: NajiaMeta | null
  }
  rows: NajiaRow[]
}

export type ReadingBriefEvidence = {
  conclusion: string
  basis: string
  plain: string
  source_id?: string
  source_ids?: string[]
}

export type ReadingBriefTiming = {
  window: string
  condition: string
  confidence?: number | null
}

export type ReadingBriefAction = {
  action: string
  cadence: string
  signal: string
}

export type ReadingBriefSourcePassage = {
  source_id?: string
  slot_key: string
  source: string
  source_label: string
  hexagram_name?: string
  section_kind?: string | null
  line_key?: string | null
  title: string
  content: string
  citation: string
  visible_by_default?: boolean
  importance?: string
}

export type ReadingBriefKeyPassage = ReadingBriefSourcePassage & {
  role?: "primary" | "secondary_context" | string
  quote?: string
  excerpt: string
  plain_language: string
  why_it_matters: string
}

export type ReadingBrief = {
  headline: string
  stance: "stable" | "changing" | "transforming" | string
  plain_language: string
  evidence: ReadingBriefEvidence[]
  key_passages?: ReadingBriefKeyPassage[]
  source_passages?: ReadingBriefSourcePassage[]
  archive_sources?: {
    total_passages: number
    sources: Record<string, number>
    slot_keys: string[]
    primary_slot_keys: string[]
  }
  personal_context?: {
    status: "reserved" | string
    current_scope?: string
    note?: string
    future_profile_fields?: string[]
  }
  timing: ReadingBriefTiming[]
  actions: ReadingBriefAction[]
  risks: string[]
  followup_prompts: string[]
  generated_at?: string | null
}

export type BaziElement = {
  value: string
  element: string
  polarity: "阳" | "阴" | ""
}

export type BaziPillar = {
  label: string
  stem: BaziElement
  branch: BaziElement
}

export type SessionPayload = {
  summary_text: string
  hex_text: string
  hex_sections: HexSection[]
  hex_overview: HexOverview
  bazi_detail?: BaziPillar[]
  reading_brief?: ReadingBrief
  najia_text: string
  najia_table: NajiaTable
  ai_text: string
  session_dict: Record<string, unknown>
  archive_path: string
  full_text: string
  session_id: string
  ai_enabled: boolean
  ai_model?: string | null
  ai_reasoning?: string | null
  ai_verbosity?: string | null
  ai_tone?: string | null
  ai_response_id?: string | null
  ai_usage: Record<string, number>
  user_authenticated?: boolean
}

export type SessionRequest = {
  topic: string
  user_question?: string
  user_context?: string
  method_key: string
  manual_lines?: number[]
  use_current_time: boolean
  timestamp?: string | null
  enable_ai: boolean
  access_password?: string | null
  ai_model: string
  ai_reasoning?: string | null
  ai_verbosity?: string | null
  ai_tone?: string | null
}

export type ChatMessage = {
  id?: string
  localId?: string
  role: "user" | "assistant"
  content: string
  tokens_in?: number | null
  tokens_out?: number | null
  created_at?: string | null
  model?: string | null
  reasoning?: string | null
  verbosity?: string | null
  tone?: string | null
}

export type ChatTurnResponse = {
  session_id: string
  assistant: ChatMessage
  usage: Record<string, number>
}

export type ChatTurnPayload = {
  message: string
  reasoning?: string | null
  verbosity?: string | null
  tone?: string | null
  model?: string | null
  restart?: boolean
}

export type ChatTranscriptResponse = {
  session_id: string
  summary_text?: string | null
  initial_ai_text?: string | null
  messages: ChatMessage[]
  payload_snapshot?: SessionPayload
  followup_model?: string | null
  ai_reasoning?: string | null
  ai_verbosity?: string | null
  ai_tone?: string | null
}

export type SessionSummary = {
  session_id: string
  summary_text?: string | null
  created_at?: string | null
  ai_enabled: boolean
  followup_available: boolean
  topic_label?: string | null
  method_label?: string | null
}

export type SessionHistoryResponse = {
  sessions: SessionSummary[]
}
