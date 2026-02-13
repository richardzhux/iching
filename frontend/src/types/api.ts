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
  reasoning: string[]
  default_reasoning?: string | null
  verbosity?: boolean
  default_verbosity?: string | null
}

export type ConfigResponse = {
  topics: TopicInfo[]
  methods: MethodInfo[]
  ai_models: ModelInfo[]
}

export type HexSection = {
  id: string
  hexagram_type: "main" | "changed"
  hexagram_name: string
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
}

export type ChatTranscriptResponse = {
  session_id: string
  summary_text?: string | null
  initial_ai_text?: string | null
  messages: ChatMessage[]
  payload_snapshot?: SessionPayload
  followup_model?: string | null
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
