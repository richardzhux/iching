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
    hour_candidates: Array<{ label: string; time_range: string; pillar: string }>
    dayun: {
      status: "not_requested" | "requires_hour" | "available"
      algorithm?: "sect1" | "sect2"
      algorithm_note?: string
      note?: string
      direction?: "forward" | "reverse"
      start?: { years: number; months: number; days: number; hours: number; solar_date: string }
      engine_bazi?: string
      crosscheck_matches?: boolean
      cycles: Array<{ index: number; label: string; ganzhi: string; start_year: number; end_year: number; start_age: number; end_age: number }>
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
  confidence: number
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
  user_email?: string | null
  user_display_name?: string | null
  user_avatar_url?: string | null
  topic_label?: string | null
  method_label?: string | null
}

export type SessionHistoryResponse = {
  sessions: SessionSummary[]
}
