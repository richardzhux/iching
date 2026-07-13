import { expect, test, type Page } from "@playwright/test"

const config = {
  topics: [{ key: "1", label: "事业" }],
  methods: [
    { key: "c", label: "三枚铜钱法" },
    { key: "x", label: "手动输入" },
  ],
  ai_models: [],
  default_model: "",
  model_aliases: {},
}

function sessionPayload(lines: number[] = [7, 8, 7, 8, 7, 8]) {
  const unknownPassage = {
    source_id: "unknown-source",
    slot_key: "test:top",
    source: "unknown",
    source_label: "卦辞库",
    hexagram_name: "Test Hexagram",
    section_kind: "top",
    line_key: null,
    title: "Legacy source label",
    content: "Unverified source content.",
    citation: "卦辞库｜legacy citation",
    visible_by_default: true,
    importance: "primary",
  }
  return {
    summary_text: "Test summary",
    hex_text: "Test hex text",
    hex_sections: [
      {
        id: "unknown-section",
        hexagram_type: "main",
        hexagram_name: "Test Hexagram",
        source_id: "unknown-source",
        source: "unknown",
        source_label: "卦辞库",
        slot_key: "test:top",
        section_kind: "top",
        line_key: null,
        title: "Legacy source label",
        content: "Unverified source content.",
        importance: "primary",
        visible_by_default: true,
      },
    ],
    hex_overview: {
      lines: lines.map((value, index) => ({
        position: index + 1,
        value,
        line_type: value === 7 || value === 9 ? "yang" : "yin",
        is_moving: value === 6 || value === 9,
        moving_symbol: value === 9 ? "○" : value === 6 ? "×" : "",
        changed_value: value,
        changed_type: value === 7 || value === 9 ? "yang" : "yin",
      })),
      main_hexagram: { name: "Test Hexagram", explanation: "Test" },
      changed_hexagram: null,
    },
    bazi_detail: [],
    reading_brief: {
      headline: "A test conclusion",
      stance: "stable",
      plain_language: "A plain-language orientation.",
      evidence: [
        {
          conclusion: "Missing-source evidence",
          basis: "Test basis",
          plain: "Open a source ID that is absent.",
          source_id: "missing-source",
        },
      ],
      key_passages: [
        {
          ...unknownPassage,
          excerpt: "Unverified source content.",
          plain_language: "Plain meaning.",
          why_it_matters: "Test role.",
        },
      ],
      source_passages: [unknownPassage],
      archive_sources: {
        total_passages: 1,
        sources: { unknown: 1 },
        slot_keys: ["test:top"],
        primary_slot_keys: ["test:top"],
      },
      timing: [],
      actions: [],
      risks: ["Test risk"],
      followup_prompts: [],
    },
    najia_text: "",
    najia_table: { meta: { main: null, changed: null }, rows: [] },
    ai_text: "",
    session_dict: {
      topic: "事业",
      method: "三枚铜钱法",
      lines,
      current_time_str: "2026.07.13 12:00",
      bazi_output: "",
      elements_output: "",
      bazi_detail: [],
    },
    archive_path: "",
    full_text: "",
    session_id: "00000000-0000-0000-0000-000000000001",
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

async function mockConfig(page: Page) {
  await page.route("**/api/config", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(config) }),
  )
}

test("migrates stale source-tab state into the unified reading and labels unknown sources honestly", async ({ page }) => {
  await mockConfig(page)
  const result = sessionPayload()
  await page.addInitScript((payload) => {
    window.localStorage.setItem(
      "iching-workspace",
      JSON.stringify({
        state: {
          form: {
            topic: "事业",
            userQuestion: "",
            userContext: "",
            methodKey: "c",
            manualLines: "",
            useCurrentTime: true,
            customTimestamp: "2026-07-13T12:00",
            enableAi: false,
            accessPassword: "",
            aiModel: "",
            aiReasoning: null,
            aiVerbosity: null,
            aiTone: "normal",
          },
          result: payload,
          history: [payload],
          journal: {},
          view: "results",
          resultsTab: "sources",
          lastSessionId: payload.session_id,
        },
        version: 1,
      }),
    )
  }, result)

  await page.goto("/en/reading")

  await expect(page).toHaveURL(/\/en\/reading/)
  await expect(page.getByText("Hexagram mechanics, Najia, source evidence, and AI follow-up stay on this page.")).toBeVisible()
  await expect(page.getByText("Source unverified").first()).toBeVisible()
  await expect(page.getByText("卦辞库")).toHaveCount(0)

  await page.getByRole("button", { name: "Review source notebook" }).click()
  await expect(page.getByRole("dialog")).toContainText("Source unverified")
  await page.keyboard.press("Escape")
})

test("coin builder submits and stores the exact six lines as the coin method", async ({ page }) => {
  await mockConfig(page)
  let submitted: Record<string, unknown> | undefined
  await page.route("**/api/sessions", async (route) => {
    if (route.request().method() !== "POST") return route.continue()
    submitted = route.request().postDataJSON() as Record<string, unknown>
    const lines = submitted.manual_lines as number[]
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(sessionPayload(lines)),
    })
  })

  await page.goto("/en/app")

  await expect(page.getByRole("combobox", { name: "Casting Method" })).toHaveText(/三枚铜钱法/)
  const toss = page.getByRole("button", { name: "Toss one coin line" })
  for (let index = 0; index < 6; index += 1) await toss.click()
  await expect(page.getByRole("status")).toContainText("Built 6/6")

  const displayed = (await page.getByRole("list", { name: "Manual six lines (bottom to top)" }).getByRole("listitem").allTextContents())
    .map((value) => Number(value.trim()))
  await page.getByRole("button", { name: "Cast", exact: true }).click()
  await expect(page).toHaveURL(/\/en\/reading/)
  await expect(page.getByText("Hexagram mechanics, Najia, source evidence, and AI follow-up stay on this page.")).toBeVisible()

  expect(submitted?.method_key).toBe("c")
  expect(submitted?.manual_lines).toEqual(displayed)
  const persisted = await page.evaluate(() => JSON.parse(window.localStorage.getItem("iching-workspace") || "{}"))
  expect(persisted.state.result.session_dict.method).toBe("三枚铜钱法")
  expect(persisted.state.result.session_dict.lines).toEqual(displayed)
})
