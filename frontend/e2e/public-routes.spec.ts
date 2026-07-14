import { expect, test, type Page } from "@playwright/test"
import { readFile } from "node:fs/promises"

const oldHomepagePhrases = [
  "From yarrow stalks to AI",
  "Tired of ChatGPT-style vagueness",
  "AI WORKBENCH",
  "Coming Soon",
]

const intentConfig = {
  topics: [
    { key: "1", label: "事业" },
    { key: "2", label: "感情" },
    { key: "3", label: "财运" },
    { key: "4", label: "身体健康" },
    { key: "5", label: "整体运势" },
    { key: "6", label: "其他/跳过" },
  ],
  methods: [{ key: "c", label: "三枚铜钱法" }],
  ai_models: [],
  default_model: "",
  model_aliases: {},
}

const mockedMetaphysicsChart = {
  timezone: "Asia/Shanghai",
  input_timestamp: "1990-01-01T12:00:00+08:00",
  calculation_timestamp: "2026-07-13T08:00:00Z",
  calculation_mode: "standard",
  true_solar_correction_minutes: 0,
  day_boundary: "forward",
  lunar_date: "己巳年 腊月初五 午时",
  pillars: [
    { label: "年", stem: "己", branch: "巳", text: "己巳", stem_element: "土", branch_element: "火", polarity: "阴", ten_god: "伤官", hidden_stems: [{ stem: "丙", element: "火", ten_god: "偏印" }], nayin: "大林木", xunkong: "戌亥", di_shi: "临官", self_seat: "帝旺" },
    { label: "月", stem: "丙", branch: "子", text: "丙子", stem_element: "火", branch_element: "水", polarity: "阳", ten_god: "偏印", hidden_stems: [{ stem: "癸", element: "水", ten_god: "正财" }], nayin: "涧下水", xunkong: "申酉", di_shi: "胎", self_seat: "胎" },
    { label: "日", stem: "戊", branch: "辰", text: "戊辰", stem_element: "土", branch_element: "土", polarity: "阳", ten_god: "日主", hidden_stems: [{ stem: "戊", element: "土", ten_god: "比肩" }], nayin: "大林木", xunkong: "戌亥", di_shi: "冠带", self_seat: "冠带" },
    { label: "时", stem: "戊", branch: "午", text: "戊午", stem_element: "土", branch_element: "火", polarity: "阳", ten_god: "比肩", hidden_stems: [{ stem: "丁", element: "火", ten_god: "正印" }], nayin: "天上火", xunkong: "子丑", di_shi: "帝旺", self_seat: "帝旺" },
  ],
  bazi: "己巳 丙子 戊辰 戊午",
  day_master: "戊土",
  xunkong: "戌亥",
  calendar_facts: {
    gregorian: "1990-01-01T12:00:00+08:00",
    month_command: "子",
    day_pillar: "戊辰",
    day_branch: "辰",
    month_clash: "午",
    month_combine: "丑",
    day_clash: "戌",
    day_combine: "酉",
    six_spirit_start: "青龙",
    six_spirits: ["青龙", "朱雀", "勾陈", "腾蛇", "白虎", "玄武"],
  },
  element_counts: { 木: 0, 火: 3, 土: 4, 金: 0, 水: 1 },
  stem_relations: ["丙戊相生"],
  branch_relations: ["子午相冲"],
  element_season_status: { 木: "休", 火: "囚", 土: "死", 金: "相", 水: "旺" },
  previous_solar_term: null,
  next_solar_term: null,
  birth_profile: {
    calendar_type: "solar",
    input_date: "1990/01/01 12:00",
    is_leap_month: false,
    birth_place: "Shanghai, China",
    gender: "male",
    hour_uncertain: false,
    hour_candidates: [],
    dayun: {
      status: "available",
      algorithm: "sect2",
      direction: "forward",
      cycles: [
        { index: 1, label: "丁丑", ganzhi: "丁丑", start_year: 1996, end_year: 2005, start_age: 6, end_age: 15, years: [] },
        { index: 2, label: "戊寅", ganzhi: "戊寅", start_year: 2006, end_year: 2015, start_age: 16, end_age: 25, years: [] },
        { index: 3, label: "己卯", ganzhi: "己卯", start_year: 2016, end_year: 2025, start_age: 26, end_age: 35, years: [] },
        { index: 4, label: "庚辰", ganzhi: "庚辰", start_year: 2026, end_year: 2035, start_age: 36, end_age: 45, years: [] },
      ],
    },
    engines: { calendar: "lunar-python", dayun: "sxtwl" },
  },
  derived_schema_version: 4,
  rules_version: "shensha-2026.07-v2.1",
  shen_sha: [],
  structure: {
    day_master: { stem: "戊", element: "土", rooted: true, root_pillars: ["日"], month_status: "死" },
    day_master_relations: [],
    layered_distribution: {
      elements: {
        visible_stems: { 木: 0, 火: 1, 土: 3, 金: 0, 水: 0 },
        branch_main_qi: { 木: 0, 火: 2, 土: 1, 金: 0, 水: 1 },
        hidden_stems: { 木: 0, 火: 2, 土: 1, 金: 0, 水: 1 },
      },
      ten_gods: {
        visible_stems: { 伤官: 1, 偏印: 1, 比肩: 1 },
        hidden_stems: { 偏印: 1, 正财: 1, 比肩: 1, 正印: 1 },
      },
    },
    structural_relations: [],
    theme_profiles: [],
  },
  theme_profiles: [],
  statistics: {
    status: "available",
    baseline: {
      schema_version: 4,
      id: "bazi-calendar-1924-2044-v2-forward",
      chart_type: "bazi",
      kind: "calendar_sample_frequency",
      label: "1924–2044 calendar sample",
      start: "1924-02-05",
      end: "2044-02-04",
      timezone: "Asia/Shanghai",
      day_boundary: "forward",
      engine: "lunar-python",
      rules_version: "shensha-2026.07-v2.1",
      sample_unit: "minute",
      sample_weight: 63113934,
      method: "Boundary enumeration",
      hash: "sha256:test-fixture",
    },
    rarity_metrics: [],
    disclaimer: "Calendar-sample frequency is not a population estimate or fate score.",
  },
  period_layers: {
    dayun: [],
    current: { as_of: "2026-07-13", year: null, month: null },
    engine: "lunar-python",
  },
}

async function mockPublicConfig(page: Page) {
  await page.route("**/api/config", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(intentConfig) }),
  )
}

async function mockMetaphysics(page: Page) {
  await page.route("**/api/tools/metaphysics", (route) => {
    const corsHeaders = {
      "access-control-allow-origin": "*",
      "access-control-allow-methods": "POST, OPTIONS",
      "access-control-allow-headers": "content-type",
    }
    if (route.request().method() === "OPTIONS") return route.fulfill({ status: 204, headers: corsHeaders })
    return route.fulfill({ status: 200, contentType: "application/json", headers: corsHeaders, body: JSON.stringify(mockedMetaphysicsChart) })
  })
}

test("home intent hydrates a real topic and localized question hint", async ({ page }) => {
  await mockPublicConfig(page)
  await page.addInitScript(() => window.localStorage.removeItem("iching-workspace"))
  await page.goto("/en")
  await page.getByRole("link", { name: /^Career/ }).click()

  await expect(page).toHaveURL(/\/en\/app\?topic=career/)
  await expect(page.getByRole("combobox", { name: "Topic" })).toContainText("事业")
  await expect(page.getByRole("textbox", { name: "Question" })).toHaveValue(
    "What should I understand about my career direction, timing, and next action?",
  )
})

test("explicit intent overrides stale topic without replacing a draft question", async ({ page }) => {
  await mockPublicConfig(page)
  await page.addInitScript(() => {
    window.localStorage.setItem(
      "iching-workspace",
      JSON.stringify({
        state: {
          form: {
            topic: "财运",
            userQuestion: "Keep this drafted question",
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
          history: [],
          journal: {},
          view: "form",
          resultsTab: "summary",
        },
        version: 1,
      }),
    )
  })
  await page.goto("/zh/app?topic=relationship")

  await expect(page.getByRole("combobox", { name: "占卜主题" })).toContainText("感情")
  await expect(page.getByRole("textbox", { name: "具体问题" })).toHaveValue("Keep this drafted question")
})

test("home navigation is task-oriented and localized", async ({ page }) => {
  await page.goto("/zh")
  await expect(page.locator("html")).toHaveAttribute("lang", "zh-CN")
  const zhCastLink = page.getByRole("link", { name: "起卦", exact: true }).first()
  await expect(zhCastLink).toBeVisible()
  await expect(page.getByRole("link", { name: "查卦", exact: true }).first()).toBeVisible()
  await expect(page.getByRole("link", { name: "排盘", exact: true }).first()).toBeVisible()
  await expect(page.getByRole("heading", { name: /方向、时机与下一步/ })).toBeVisible()
  await expect(page.getByRole("link", { name: /^事业/ })).toHaveAttribute("href", /\/zh\/app\?topic=career/)
  await expect(page.getByRole("link", { name: "GitHub", exact: true })).toHaveCount(0)
  await page.goto("/zh/app")
  await expect(page.getByRole("link", { name: "起卦", exact: true }).first()).toHaveAttribute("aria-current", "page")

  await page.goto("/en")
  await expect(page.locator("html")).toHaveAttribute("lang", "en")
  await expect(page.getByRole("link", { name: "Cast", exact: true }).first()).toBeVisible()
  await expect(page.getByRole("link", { name: "Study", exact: true }).first()).toBeVisible()
  await expect(page.getByRole("link", { name: "Charts", exact: true }).first()).toBeVisible()
  for (const phrase of oldHomepagePhrases) {
    await expect(page.locator("body")).not.toContainText(phrase)
  }
})

test("public tools, library search, and hexagram sources expose consumer controls", async ({ page }) => {
  await page.goto("/en/tools")
  await expect(page.getByRole("heading", { name: /BaZi & Zi Wei Charts/i })).toBeVisible()
  await expect(page.getByRole("tab", { name: /current time/i })).toBeVisible()

  await page.goto("/en/library")
  await expect(page.getByRole("heading", { name: /explore the 64 hexagrams/i })).toBeVisible()
  const quickNav = page.getByRole("navigation", { name: "Browse 64 hexagrams" })
  await expect(quickNav.getByRole("link")).toHaveCount(64)
  await expect(quickNav.getByRole("link").first()).toHaveAttribute("href", "#hexagram-1")
  await expect(quickNav.getByRole("link").last()).toHaveAttribute("href", "#hexagram-64")
  await expect(page.getByRole("button", { name: /^(All|Change|Relationships|Work|Timing|Challenges)$/ })).toHaveCount(0)
  await expect(page.getByLabel(/search the yi/i)).toBeVisible()
  await expect(page.getByRole("status")).toHaveText("Showing 8 of 64 results")
  await page.getByLabel(/search the yi/i).fill("qian")
  await expect(page.getByRole("status")).toContainText(/result/i)
  await expect(page.getByText(/Qián/).first()).toBeVisible()
  await expect(page.locator("body")).not.toContainText("canonical slots")
  await expect(page.locator("body")).not.toContainText("source entries")

  await page.goto("/zh/library")
  for (const phrase of ["Source Library", "Hexagram Study Page", "canonical slots", "source entries"]) {
    await expect(page.locator("body")).not.toContainText(phrase)
  }

  await page.goto("/en/hexagram/qian")
  await expect(page.getByRole("heading", { name: /Hexagram 1/i })).toBeVisible()
  await expect(page.getByRole("link", { name: "Study", exact: true }).first()).toHaveAttribute("aria-current", "page")
  await expect(page.getByText(/Qián/).first()).toBeVisible()
  await expect(page.locator("body")).not.toContainText("1.gua")
  const firstSlot = page.locator("details").first()
  await firstSlot.locator("summary").first().press("Enter")
  const firstSource = firstSlot.locator("details").first()
  await firstSource.locator("summary").press("Enter")
  await expect(firstSource.locator('pre[tabindex="0"]')).toBeVisible()

  await page.goto("/zh/hexagram/qian")
  await expect(page.locator("body")).not.toContainText("1.gua")
  await expect(page.locator("body")).not.toContainText("Hexagram Study Page")
})

test("current location recommends a birth city but never applies it before confirmation", async ({ page }) => {
  await mockMetaphysics(page)
  await page.addInitScript(() => {
    Object.defineProperty(navigator, "geolocation", {
      configurable: true,
      value: {
        getCurrentPosition(success: PositionCallback) {
          success({ coords: { latitude: 31.23, longitude: 121.47 } } as GeolocationPosition)
        },
      },
    })
  })
  await page.route("**/api/locations", (route) => {
    if (route.request().method() !== "POST") return route.fallback()
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        result: { id: "CN:shanghai", name: "Shanghai", region: "Shanghai", country: "China", latitude: 31.216, longitude: 121.436, timezone: "Asia/Shanghai" },
        distanceKm: 4.2,
      }),
    })
  })

  await page.goto("/en/tools")
  await page.getByRole("tab", { name: "BaZi", exact: true }).click()
  await page.getByRole("button", { name: "Use current location" }).click()

  await expect(page.getByRole("region", { name: "Nearby city candidate" })).toContainText("Shanghai")
  await expect(page.getByText("Selected birth city")).toHaveCount(0)
  await page.getByRole("button", { name: "Confirm city" }).click()
  await expect(page.getByText("Selected birth city")).toBeVisible()
  await expect(page.getByText("Shanghai", { exact: true })).toBeVisible()
})

test("manual birth-city search invalidates a delayed current-location match", async ({ page }) => {
  await mockMetaphysics(page)
  let releaseNearest = () => {}
  let markNearestStarted = () => {}
  const nearestGate = new Promise<void>((resolve) => { releaseNearest = resolve })
  const nearestStarted = new Promise<void>((resolve) => { markNearestStarted = resolve })
  await page.addInitScript(() => {
    Object.defineProperty(navigator, "geolocation", {
      configurable: true,
      value: {
        getCurrentPosition(success: PositionCallback) {
          success({ coords: { latitude: 31.23, longitude: 121.47 } } as GeolocationPosition)
        },
      },
    })
  })
  await page.route("**/api/locations**", async (route) => {
    if (route.request().method() === "POST") {
      markNearestStarted()
      await nearestGate
      try {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            result: { id: "CN:shanghai", name: "Shanghai", region: "Shanghai", country: "China", latitude: 31.216, longitude: 121.436, timezone: "Asia/Shanghai" },
            distanceKm: 4.2,
          }),
        })
      } catch {
        // The production request is expected to be aborted when manual input wins.
      }
      return
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        results: [{ id: "GB:london", name: "London", region: "England", country: "United Kingdom", latitude: 51.507, longitude: -0.128, timezone: "Europe/London" }],
      }),
    })
  })

  await page.goto("/en/tools")
  await page.getByRole("tab", { name: "BaZi", exact: true }).click()
  await page.getByRole("button", { name: "Use current location" }).click()
  await nearestStarted
  await page.getByRole("combobox", { name: "Birth city" }).fill("London")
  releaseNearest()

  await expect(page.getByRole("option", { name: /London/ })).toBeVisible()
  await expect(page.getByRole("region", { name: "Nearby city candidate" })).toHaveCount(0)
  await page.getByRole("option", { name: /London/ }).click()
  await expect(page.getByText("Selected birth city")).toBeVisible()
  await expect(page.getByText("London", { exact: true })).toBeVisible()
})

test("signed-out My surface provides accessible auth without calling OAuth", async ({ page }) => {
  await page.goto("/en/profile")
  await expect(page.getByRole("heading", { name: /save and continue your readings/i })).toBeVisible()
  await expect(page.getByRole("button", { name: /continue with google/i })).toBeVisible()
  await expect(page.getByLabel("Email", { exact: true })).toHaveAttribute("autocomplete", "email")
  await expect(page.getByLabel("Password", { exact: true })).toHaveAttribute("autocomplete", "current-password")
  await page.getByRole("button", { name: /create an account/i }).click()
  await expect(page.getByLabel("Password", { exact: true })).toHaveAttribute("autocomplete", "new-password")
})

test("signed-in My shows saved readings and safe record controls", async ({ page }) => {
  const sessionId = "reading-2026-07-13"
  let deleteRequests = 0
  page.on("request", (request) => {
    if (request.method() === "DELETE" || (request.method() === "POST" && request.url().endsWith("/api/sessions"))) {
      deleteRequests += 1
    }
  })
  await page.route("**/auth/v1/token**", (route) => {
    const headers = {
      "access-control-allow-origin": "*",
      "access-control-allow-methods": "POST, OPTIONS",
      "access-control-allow-headers": "apikey, authorization, content-type, x-client-info",
    }
    if (route.request().method() === "OPTIONS") return route.fulfill({ status: 204, headers })
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      headers,
      body: JSON.stringify({
      access_token: "mock-access-token",
      token_type: "bearer",
      expires_in: 3600,
      expires_at: Math.floor(Date.now() / 1000) + 3600,
      refresh_token: "mock-refresh-token",
      user: {
        id: "00000000-0000-4000-8000-000000000001",
        aud: "authenticated",
        role: "authenticated",
        email: "reader@example.com",
        email_confirmed_at: "2026-07-13T00:00:00.000Z",
        app_metadata: { provider: "email", providers: ["email"] },
        user_metadata: { full_name: "Reader" },
        identities: [],
        created_at: "2026-07-13T00:00:00.000Z",
        updated_at: "2026-07-13T00:00:00.000Z",
      },
      }),
    })
  })
  await page.route("**/api/sessions", (route) => {
    const headers = { "access-control-allow-origin": "*", "access-control-allow-methods": "GET, OPTIONS", "access-control-allow-headers": "authorization" }
    if (route.request().method() === "OPTIONS") return route.fulfill({ status: 204, headers })
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      headers,
      body: JSON.stringify({ sessions: [{
        session_id: sessionId,
        summary_text: "Move after the budget owner confirms the timeline.",
        created_at: "2026-07-13T08:00:00.000Z",
        ai_enabled: true,
        followup_available: true,
        topic_label: "Career decision",
        method_label: "Three-coin method",
      }] }),
    })
  })
  await page.route(`**/api/sessions/${sessionId}/chat`, (route) => {
    const headers = { "access-control-allow-origin": "*", "access-control-allow-methods": "GET, OPTIONS", "access-control-allow-headers": "authorization" }
    if (route.request().method() === "OPTIONS") return route.fulfill({ status: 204, headers })
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      headers,
      body: JSON.stringify({
        session_id: sessionId,
        summary_text: "Move after the budget owner confirms the timeline.",
        initial_ai_text: null,
        messages: [],
      }),
    })
  })

  await page.goto("/en/profile")
  await page.getByLabel("Email", { exact: true }).fill("reader@example.com")
  await page.getByLabel("Password", { exact: true }).fill("test-password")
  await page.getByRole("button", { name: "Sign in", exact: true }).click()

  await expect(page.getByRole("heading", { name: "Saved readings" })).toBeVisible()
  await expect(page.getByRole("heading", { name: "Career decision" })).toBeVisible()
  await expect(page.getByRole("button", { name: "Download", exact: true })).toBeVisible()
  await expect(page.getByRole("button", { name: "Open session", exact: true })).toBeVisible()
  await expect(page.getByRole("button", { name: "Delete", exact: true })).toBeVisible()
  await expect(page.getByText("Your private home for readings and personal charts. Reopen any record without starting over.")).toHaveCount(1)

  const download = page.waitForEvent("download")
  await page.getByRole("button", { name: "Download", exact: true }).click()
  await download
  expect(deleteRequests).toBe(0)
})

test("divination desk does not regress to the stale loading-only state", async ({ page }) => {
  await page.goto("/en/app")
  await expect(page.locator("body")).not.toContainText("Loading workspace configuration...")
  await expect(
    page.getByText(/What are you actually deciding|The divination desk could not load|Preparing the divination desk/i).first(),
  ).toBeVisible()
  if (await page.locator(".oracle-mark").isVisible()) {
    await expect(page.locator(".oracle-mark")).toContainText("🔮")
  }
})

test("mobile divination desk exposes question coaching and casting controls", async ({ page, isMobile }) => {
  test.skip(!isMobile, "mobile-only smoke")
  await page.goto("/en/app")
  await expect(
    page.getByText(/What are you actually deciding|你现在真正要判断什么|The divination desk could not load|占卜台暂时无法加载/i).first(),
  ).toBeVisible()
  const question = page.getByRole("textbox", { name: /question|specific question|具体问题/i }).first()
  if (await question.isVisible()) {
    await question.fill("Will I get the job?")
    await expect(page.getByText(/Better as an inquiry question|更适合作为探索式问题/)).toBeVisible()
    await expect(page.getByRole("button", { name: /Toss one coin line|掷一爻铜钱/i })).toBeVisible()
  } else {
    await expect(page.getByText(/The divination desk could not load|占卜台暂时无法加载/i)).toBeVisible()
  }
})

test("exports one mocked BaZi PNG with a safe filename and no controls in its canvas", async ({ page }) => {
  await mockMetaphysics(page)
  await page.goto("/en/tools")
  await page.getByRole("tab", { name: "BaZi", exact: true }).click()
  await page.getByRole("button", { name: "Generate my chart", exact: true }).click()

  const exportTarget = page.locator("[data-chart-export-root]")
  await expect(exportTarget).toHaveCount(1)
  await expect(exportTarget).toHaveAttribute("aria-hidden", "true")
  await expect(exportTarget.locator("button, input, select, textarea")).toHaveCount(0)

  let downloads = 0
  page.on("download", () => { downloads += 1 })
  const downloadPromise = page.waitForEvent("download")
  await page.getByRole("button", { name: "Export chart", exact: true }).click()
  const download = await downloadPromise

  expect(download.suggestedFilename()).toBe("bazi-1990-01-01-12-00.png")
  const downloadPath = await download.path()
  expect(downloadPath).not.toBeNull()
  if (!downloadPath) throw new Error("Playwright did not provide the downloaded PNG path")
  const pngBytes = await readFile(downloadPath)
  const dataUrl = `data:image/png;base64,${pngBytes.toString("base64")}`
  const bitmap = await page.evaluate(async (source) => {
    const image = new Image()
    await new Promise<void>((resolve, reject) => {
      image.onload = () => resolve()
      image.onerror = () => reject(new Error("Downloaded PNG could not be decoded"))
      image.src = source
    })
    const canvas = document.createElement("canvas")
    canvas.width = image.naturalWidth
    canvas.height = image.naturalHeight
    const context = canvas.getContext("2d")
    if (!context) throw new Error("Canvas 2D context is unavailable")
    context.drawImage(image, 0, 0)
    const pixels = context.getImageData(0, 0, canvas.width, canvas.height).data
    const sampleEveryPixels = Math.max(1, Math.floor((canvas.width * canvas.height) / 50_000))
    const uniqueColors = new Set<string>()
    let opaqueSamples = 0
    for (let index = 0; index < pixels.length; index += sampleEveryPixels * 4) {
      if (pixels[index + 3] > 16) opaqueSamples += 1
      uniqueColors.add(`${pixels[index]}:${pixels[index + 1]}:${pixels[index + 2]}:${pixels[index + 3]}`)
    }
    return { width: image.naturalWidth, height: image.naturalHeight, opaqueSamples, uniqueColors: uniqueColors.size }
  }, dataUrl)
  expect(bitmap.width).toBeGreaterThanOrEqual(1_000)
  expect(bitmap.height).toBeGreaterThanOrEqual(500)
  expect(bitmap.opaqueSamples).toBeGreaterThan(1_000)
  expect(bitmap.uniqueColors).toBeGreaterThan(10)
  await page.waitForTimeout(100)
  expect(downloads).toBe(1)
})

test("recovers when the export target is unavailable", async ({ page }) => {
  await mockMetaphysics(page)
  await page.goto("/en/tools")
  await page.getByRole("tab", { name: "BaZi", exact: true }).click()
  await page.getByRole("button", { name: "Generate my chart", exact: true }).click()
  await page.locator("[data-chart-export-root]").evaluate((node) => node.remove())

  const exportButton = page.getByRole("button", { name: "Export chart", exact: true })
  await exportButton.click()
  await expect(page.getByText("Chart image could not be generated. Try again.")).toBeVisible()
  await expect(exportButton).toBeEnabled()
  await expect(exportButton).toHaveText(/Export chart/)
})
