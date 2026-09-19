import type { Page, Route } from "@playwright/test"

/** Config the workspace blocks on. Every test that renders the desk needs it. */
export const CONFIG = {
  topics: [
    { key: "1", label: "事业" },
    { key: "2", label: "感情" },
    { key: "3", label: "财运" },
    { key: "4", label: "身体健康" },
    { key: "5", label: "整体运势" },
    { key: "6", label: "其他/跳过" },
  ],
  methods: [
    { key: "c", label: "三枚铜钱法" },
    { key: "s", label: "五十蓍草法" },
    { key: "m", label: "梅花易数法" },
    { key: "x", label: "手动输入" },
  ],
  ai_models: [],
  default_model: "",
  model_aliases: {},
}

const SESSION_ID = "00000000-0000-0000-0000-000000000001"

type SessionOptions = {
  lines?: number[]
  sessionId?: string
  provenance?: Record<string, unknown>
}

/** A reading payload shaped like SessionPayload, trimmed to what the UI reads. */
export function sessionPayload({
  lines = [7, 7, 8, 8, 9, 9],
  sessionId = SESSION_ID,
  provenance = {
    method_key: "x",
    method_label: "手动输入",
    line_source: "manual",
    description: "Lines were entered by hand.",
    verified: false,
  },
}: SessionOptions = {}) {
  const ordered = [...lines].reverse().map((value, index) => ({
    position: 6 - index,
    value,
    line_type: value === 7 || value === 9 ? "yang" : "yin",
    is_moving: value === 6 || value === 9,
    moving_symbol: value === 9 ? "O" : value === 6 ? "X" : "",
    changed_value: value === 9 ? 8 : value === 6 ? 7 : value,
    changed_type: value === 9 ? "yin" : value === 6 ? "yang" : value === 7 ? "yang" : "yin",
    changed_line_type: value === 9 ? "yin" : value === 6 ? "yang" : value === 7 ? "yang" : "yin",
  }))

  return {
    summary_text: "Test summary",
    casting_provenance: provenance,
    hex_text: "Test hex text",
    hex_sections: [
      {
        id: "main-guaci-top",
        hexagram_type: "main",
        hexagram_name: "Test Hexagram",
        source: "guaci",
        source_label: "卦辞库",
        slot_key: "test:gua",
        section_kind: "top",
        line_key: null,
        title: "本卦 · 卦辞总览",
        content: "Hexagram statement under test.",
        importance: "primary",
        visible_by_default: true,
        line_role: "background",
      },
      {
        id: "main-guaci-line-5",
        hexagram_type: "main",
        hexagram_name: "Test Hexagram",
        source: "guaci",
        source_label: "卦辞库",
        slot_key: "test:5",
        section_kind: "line",
        line_key: "5",
        title: "本卦 · 第5爻",
        content: "Primary line text under test.",
        importance: "primary",
        visible_by_default: true,
        line_role: "primary",
      },
    ],
    hex_overview: {
      lines: ordered,
      main_hexagram: { name: "Test Hexagram", explanation: "Present situation." },
      changed_hexagram: { name: "Changed Hexagram", explanation: "Where it is going." },
      line_selection: {
        rule: "two-moving",
        rule_name: "二爻动",
        rule_detail: "一阴一阳取阴爻，同阴同阳取上动爻为主，另一动爻并参",
        rule_name_en: "Two moving lines",
        rule_detail_en: "one yin and one yang takes the yin line",
        primary_line: 6,
        secondary_lines: [5],
        primary_is_moving: true,
        line_role: "动爻",
      },
    },
    bazi_detail: [],
    reading_brief: {
      headline: "Proceed once the budget is signed off.",
      stance: "changing",
      direction: { kind: "advance", summary: "The direction holds." },
      plain_language: "Plain language summary under test.",
      evidence: [],
      key_passages: [],
      source_passages: [],
      archive_sources: { total_passages: 0, sources: {}, slot_keys: [], primary_slot_keys: [] },
      timing: [],
      actions: [],
      risks: [],
      followup_prompts: [],
      generated_at: "2026.09.18 12:00",
    },
    najia_text: "",
    najia_table: { meta: { main: null, changed: null }, rows: [] },
    ai_text: "",
    session_dict: {
      topic: "事业",
      user_question: "Test question",
      method: "手动输入",
      lines,
      current_time_str: "2026.09.18 12:00",
      bazi_output: "",
      elements_output: "",
      bazi_detail: [],
      locale: "en",
    },
    archive_path: "",
    full_text: "",
    session_id: sessionId,
    ai_enabled: false,
    ai_model: null,
    ai_reasoning: null,
    ai_verbosity: null,
    ai_tone: "normal",
    ai_response_id: null,
    ai_usage: {},
    user_authenticated: false,
  }
}

export async function mockConfig(page: Page) {
  await page.route("**/api/config", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(CONFIG) }),
  )
}

/** Captures every POST body so a test can assert what the client actually sent. */
export async function mockCreateSession(page: Page, sent: Record<string, unknown>[]) {
  await page.route("**/api/sessions", async (route) => {
    if (route.request().method() !== "POST") return route.fallback()
    sent.push(route.request().postDataJSON())
    await route.fulfill({
      status: 201,
      contentType: "application/json",
      body: JSON.stringify(sessionPayload()),
    })
  })
}

export async function mockCastingPreview(page: Page, token = "a".repeat(32)) {
  await page.route("**/api/casting/preview", (route) => {
    const body = route.request().postDataJSON() as { method_key: string; timestamp: string }
    const lines = [8, 8, 6, 8, 8, 9]
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        method_key: body.method_key,
        timestamp: body.timestamp,
        lines,
        yarrow_steps: lines.map((value) => [44, 40, value * 4]),
        yarrow_trace: lines.map((value) => [
          { before: 49, left: 20, right: 29, hanging: 1, left_remainder: 4, right_remainder: 1, removed: 5, after: 44 },
          { before: 44, left: 20, right: 24, hanging: 1, left_remainder: 4, right_remainder: 3, removed: 4, after: 40 },
          { before: 40, left: 20, right: 20, hanging: 1, left_remainder: 4, right_remainder: 3, removed: 40 - value * 4, after: value * 4 },
        ]),
        meihua_mode: body.method_key === "m" ? "traditional" : null,
        calculation_inputs: {},
        upper_trigram: null,
        lower_trigram: null,
        changing_line: null,
        casting_token: token,
      }),
    })
  })
}

/** Every backend call fails, to check the app degrades instead of going blank. */
export async function mockBackendDown(page: Page) {
  await page.route("**/api/**", (route: Route) => route.abort("connectionrefused"))
}
