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

export type SessionPayload = {
  summary_text: string
  hex_text: string
  najia_text: string
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
}
