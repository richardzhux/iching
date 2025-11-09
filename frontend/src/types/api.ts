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

export type SessionPayload = {
  summary_text: string
  hex_text: string
  hex_sections: HexSection[]
  hex_overview: HexOverview
  najia_text: string
  najia_table: NajiaTable
  ai_text: string
  session_dict: Record<string, unknown>
  archive_path: string
  full_text: string
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
