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

test("paid follow-up retries preserve operation identity without persisting its password", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 })
  await page.route("**/api/config", (route) => route.fulfill({ json: {
    ...config,
    ai_models: ["model-a", "model-b"].map((name) => ({ name, label: name, reasoning: ["low", "medium", "high"], default_reasoning: "medium", verbosity: true, default_verbosity: "medium" })),
    default_model: "model-a",
  } }))
  const result = sessionPayload()
  const requests: Record<string, unknown>[] = []
  const transcript = [
    { id: "prior-user", role: "user", content: "An earlier question" },
    { id: "prior-answer", role: "assistant", content: "An earlier answer" },
  ]
  const headers = {
    "access-control-allow-origin": "*",
    "access-control-allow-methods": "GET, POST, OPTIONS",
    "access-control-allow-headers": "apikey, authorization, content-type, x-client-info, x-supabase-api-version",
  }
  await page.route("**/auth/v1/token**", (route) => {
    if (route.request().method() === "OPTIONS") return route.fulfill({ status: 204, headers })
    return route.fulfill({ status: 200, headers, json: {
      access_token: "mock-access-token", token_type: "bearer", expires_in: 3600,
      expires_at: Math.floor(Date.now() / 1000) + 3600, refresh_token: "mock-refresh-token",
      user: { id: "00000000-0000-4000-8000-000000000001", aud: "authenticated", role: "authenticated", email: "reader@example.com", app_metadata: {}, user_metadata: {}, identities: [] },
    } })
  })
  await page.route(`**/api/sessions/${result.session_id}/chat`, (route) => {
    if (route.request().method() === "OPTIONS") return route.fulfill({ status: 204, headers })
    return route.fulfill({ headers, json: { session_id: result.session_id, messages: transcript, payload_snapshot: result } })
  })
  await page.route(`**/api/sessions/${result.session_id}/chat/stream`, (route) => {
    if (route.request().method() === "OPTIONS") return route.fulfill({ status: 204, headers })
    requests.push(route.request().postDataJSON())
    if (requests.length === 1) return route.fulfill({ status: 409, headers, json: { detail: "The request may still be running; retry the same request." } })
    const assistant = { id: `answer-${requests.length}`, role: "assistant", content: "Completed answer", model: "model-a" }
    transcript.push({ id: `user-${requests.length}`, role: "user", content: String(requests.at(-1)?.message) }, assistant)
    return route.fulfill({ status: 200, headers, contentType: "text/event-stream", body: `event: completed\ndata: ${JSON.stringify({ assistant, usage: { total_tokens: 10 } })}\n\n` })
  })
  await page.addInitScript((payload) => {
    if (localStorage.getItem("iching-workspace")) return
    localStorage.setItem("iching-workspace", JSON.stringify({ version: 1, state: {
      result: payload, history: [payload], journal: {}, view: "results", resultsTab: "summary",
      form: { topic: "事业", userQuestion: "", userContext: "", methodKey: "c", manualLines: "", useCurrentTime: true, customTimestamp: "2026-07-13T12:00", enableAi: false, accessPassword: "", aiModel: "", aiTone: "normal" },
    } }))
  }, result)
  await page.goto("/en/reading")
  const chat = page.locator("#ai-followup")
  await chat.locator('input[type="email"]').fill("reader@example.com")
  await chat.locator('input[type="password"]').fill("account-password")
  await chat.getByRole("button", { name: "Sign in", exact: true }).click()
  await chat.getByLabel("AI access password").fill("test-ai-secret")
  await chat.locator("textarea").fill("What is the next step?")
  await chat.locator('button[type="submit"]').click()
  await expect(chat.getByRole("button", { name: "Retry request", exact: true })).toBeVisible()
  await expect(chat.getByText("An earlier answer", { exact: true })).toBeVisible()
  await page.reload()
  await expect(chat.getByText("An earlier answer", { exact: true })).toBeVisible()
  await expect(chat.getByRole("button", { name: "Retry request", exact: true })).toBeVisible()
  await chat.getByLabel("AI access password").fill("test-ai-secret")
  await chat.getByText("Model and output settings", { exact: true }).click()
  await chat.getByRole("combobox").nth(0).click()
  await page.getByRole("option", { name: "model-b", exact: true }).click()
  await chat.getByRole("combobox").nth(1).click()
  await page.getByRole("option", { name: "High", exact: true }).click()
  await chat.getByRole("button", { name: "Retry request", exact: true }).click()
  await expect(chat.getByText("Completed answer", { exact: true })).toBeVisible()
  expect(requests).toHaveLength(2)
  expect(requests[1]).toEqual(requests[0])
  expect(requests[0].request_id).toMatch(/^[0-9a-f]{8}-[0-9a-f-]{27}$/)
  expect(requests[0].access_password).toBe("test-ai-secret")
  expect(await page.evaluate(() => JSON.stringify(Object.values(localStorage)))).not.toContain("test-ai-secret")
  await chat.getByRole("button", { name: "Regenerate (new request)", exact: true }).click()
  await expect.poll(() => requests.length).toBe(3)
  expect(requests[2].request_id).not.toBe(requests[0].request_id)
  expect(requests[2].restart).toBe(true)
  expect(requests[2].model).toBe("model-b")
  expect(requests[2].reasoning).toBe("high")
  await expect(chat.getByRole("button", { name: "Retry request", exact: true })).toHaveCount(0)
  const storedChat = await page.evaluate((sessionId) => localStorage.getItem(`iching-chat-v2-${sessionId}`), result.session_id)
  expect(storedChat).not.toContain(String(requests[0].request_id))

  const casts: Record<string, unknown>[] = []
  await page.route("**/api/sessions", (route) => {
    if (route.request().method() === "OPTIONS") return route.fulfill({ status: 204, headers })
    casts.push(route.request().postDataJSON())
    return casts.length === 1
      ? route.fulfill({ status: 409, headers, json: { detail: "Retry the same request." } })
      : route.fulfill({ status: 201, headers, json: result })
  })
  await page.getByRole("link", { name: "Cast", exact: true }).click()
  await page.getByRole("button", { name: "Reading settings", exact: true }).click()
  await page.getByRole("button", { name: "Standard", exact: true }).click()
  await page.keyboard.press("Escape")
  await page.getByRole("button", { name: "Complete the remaining steps", exact: true }).click()
  const readButton = page.getByRole("button", { name: "Read this hexagram", exact: true })
  await readButton.click()
  await expect.poll(() => casts.length).toBe(1)
  await expect(readButton).toBeEnabled()
  const savedWorkspace = await page.evaluate(() => new Promise<string>((resolve, reject) => {
    const open = indexedDB.open("iching-workspace", 1)
    open.onerror = () => reject(open.error)
    open.onsuccess = () => {
      const read = open.result.transaction("workspace", "readonly").objectStore("workspace").get("iching-workspace")
      read.onsuccess = () => { resolve(read.result); open.result.close() }
      read.onerror = () => reject(read.error)
    }
  }))
  expect(savedWorkspace).not.toContain("test-ai-secret")
  expect(JSON.parse(savedWorkspace).state.pendingAiRequest.payload.request_id).toBe(casts[0].request_id)
  await page.reload()
  await page.getByRole("button", { name: "Reading settings", exact: true }).click()
  await page.getByRole("dialog").locator('input[type="password"]').fill("test-ai-secret")
  await page.keyboard.press("Escape")
  await readButton.click()
  await expect.poll(() => casts.length).toBe(2)
  expect(casts[1]).toEqual(casts[0])
  expect(casts[0].request_id).toMatch(/^[0-9a-f]{8}-[0-9a-f-]{27}$/)
  expect(casts[0].access_password).toBe("test-ai-secret")
})

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
