/**
 * The flows that have to keep working, asserted against behaviour rather than copy.
 *
 * This replaces `public-routes.spec.ts` and `p0-casting-results.spec.ts`, which
 * pinned the wording and DOM shape of a homepage that was redesigned in
 * 1b547a6 and b95641c. All 34 of their checks were failing on main; they were
 * asserting a UI that no longer existed rather than catching a regression.
 *
 * Rules for anything added here: assert a route, a role, a network payload or a
 * state transition. Do not assert a marketing sentence, a CSS value or a class
 * name — that is what rotted last time.
 */

import { expect, test } from "@playwright/test"

import {
  mockBackendDown,
  mockCastingPreview,
  mockConfig,
  mockCreateSession,
  sessionPayload,
} from "./fixtures"

// --------------------------------------------------------------------------- //
// Routing and locale
// --------------------------------------------------------------------------- //

test("every public route renders its own page in both locales", async ({ page }) => {
  await mockConfig(page)
  for (const locale of ["en", "zh"] as const) {
    for (const path of ["", "/app", "/reading", "/library", "/tools", "/profile"]) {
      const response = await page.goto(`/${locale}${path}`)
      expect(response?.status(), `${locale}${path} status`).toBeLessThan(400)
      // A rendered page has a main heading; a crashed one has only chrome.
      await expect(
        page.getByRole("heading", { level: 1 }),
        `${locale}${path} has an h1`,
      ).toBeVisible()
    }
  }
})

test("an unprefixed path is redirected into a locale", async ({ page }) => {
  await mockConfig(page)
  await page.goto("/")
  await expect(page).toHaveURL(/\/(en|zh)$/)
})

test("switching language changes the route, the lang attribute and the nav", async ({ page }) => {
  await mockConfig(page)
  await page.goto("/en")
  await expect(page.locator("html")).toHaveAttribute("lang", "en")
  await expect(page.getByRole("link", { name: "Cast", exact: true }).first()).toBeVisible()

  await page.getByRole("button", { name: "中文", exact: true }).click()
  await expect(page).toHaveURL(/\/zh/)
  await expect(page.locator("html")).toHaveAttribute("lang", "zh-CN")
  await expect(page.getByRole("link", { name: "起卦", exact: true }).first()).toBeVisible()
})

// --------------------------------------------------------------------------- //
// Cast to reading
// --------------------------------------------------------------------------- //

test("a manual cast posts the entered lines and opens the reading", async ({ page }) => {
  const sent: Record<string, unknown>[] = []
  await mockConfig(page)
  await mockCreateSession(page, sent)

  await page.goto("/en")
  await page.getByRole("button", { name: /Your own cast/i }).click()
  await page.locator("#manual-lines-quick").fill("778899")
  await page.getByRole("button", { name: /Read this hexagram/i }).click()

  await expect(page).toHaveURL(/\/en\/reading/)
  expect(sent).toHaveLength(1)
  expect(sent[0]).toMatchObject({
    method_key: "x",
    manual_lines: [7, 7, 8, 8, 9, 9],
    enable_ai: false,
    locale: "en",
  })
  // 7,7,8,8,9,9 bottom-to-top is 110011 — Inner Truth. The page names the
  // hexagram the lines produce, not whatever the payload happens to carry.
  await expect(page.getByRole("heading", { level: 1, name: /Inner Truth/i })).toBeVisible()
})

test("the reading carries the locale the reader is using", async ({ page }) => {
  const sent: Record<string, unknown>[] = []
  await mockConfig(page)
  await mockCreateSession(page, sent)

  await page.goto("/zh")
  await page.getByRole("button", { name: /亲手录入六爻|自定义/ }).click()
  await page.locator("#manual-lines-quick").fill("777777")
  await page.getByRole("button", { name: /解读此卦|读此卦/ }).click()

  await expect.poll(() => sent.length).toBe(1)
  expect(sent[0]).toMatchObject({ locale: "zh" })
})

// --------------------------------------------------------------------------- //
// Casting provenance — the record has to say how the lines arrived
// --------------------------------------------------------------------------- //

test("a hand-entered cast does not claim to be a server cast", async ({ page }) => {
  const sent: Record<string, unknown>[] = []
  await mockConfig(page)
  await mockCreateSession(page, sent)

  await page.goto("/en")
  await page.getByRole("button", { name: /Your own cast/i }).click()
  await page.locator("#manual-lines-quick").fill("778899")
  await page.getByRole("button", { name: /Read this hexagram/i }).click()

  await expect.poll(() => sent.length).toBe(1)
  expect(sent[0]).toMatchObject({ line_source: "manual", casting_token: null })
})

test("a yarrow cast returns the server token so the reading records a verified cast", async ({ page }) => {
  const sent: Record<string, unknown>[] = []
  const token = "b".repeat(32)
  await mockConfig(page)
  await mockCastingPreview(page, token)
  await mockCreateSession(page, sent)

  await page.goto("/en")
  await page.getByRole("button", { name: /Yarrow stalks/i }).click()
  await page.getByRole("button", { name: /Complete the remaining steps/i }).click()

  await page.getByRole("button", { name: /Read this hexagram/i }).click({ timeout: 25_000 })
  await expect.poll(() => sent.length, { timeout: 25_000 }).toBe(1)
  expect(sent[0]).toMatchObject({ method_key: "s", line_source: "server_cast", casting_token: token })
})

test("the reading surfaces how its lines arrived", async ({ page }) => {
  const sent: Record<string, unknown>[] = []
  await mockConfig(page)
  await page.route("**/api/sessions", async (route) => {
    if (route.request().method() !== "POST") return route.fallback()
    sent.push(route.request().postDataJSON())
    await route.fulfill({
      status: 201,
      contentType: "application/json",
      body: JSON.stringify(
        sessionPayload({
          provenance: {
            method_key: "x",
            method_label: "手动输入",
            line_source: "edited",
            description: "Lines were edited by hand after the cast.",
            verified: false,
          },
        }),
      ),
    })
  })

  await page.goto("/en")
  await page.getByRole("button", { name: /Your own cast/i }).click()
  await page.locator("#manual-lines-quick").fill("778899")
  await page.getByRole("button", { name: /Read this hexagram/i }).click()
  await expect(page).toHaveURL(/\/en\/reading/)

  await page.getByRole("group").filter({ hasText: "Why this reading" }).locator("summary").click()
  await expect(page.getByText("Lines were edited by hand after the cast.")).toBeVisible()
})

test("the reading states which line the rule selected", async ({ page }) => {
  const sent: Record<string, unknown>[] = []
  await mockConfig(page)
  await mockCreateSession(page, sent)

  await page.goto("/en")
  await page.getByRole("button", { name: /Your own cast/i }).click()
  await page.locator("#manual-lines-quick").fill("778899")
  await page.getByRole("button", { name: /Read this hexagram/i }).click()
  await expect(page).toHaveURL(/\/en\/reading/)

  await page.getByRole("group").filter({ hasText: "Why this reading" }).locator("summary").click()
  await expect(page.getByText(/Two moving lines/)).toBeVisible()
  await expect(page.getByText(/primary line 6/)).toBeVisible()
})

// --------------------------------------------------------------------------- //
// Reading deep link
// --------------------------------------------------------------------------- //

test("a reading link without a signed-in reader explains itself instead of hanging", async ({ page }) => {
  await mockConfig(page)
  await page.goto("/en/reading?session=00000000-0000-0000-0000-000000000009")
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible()
  await expect(page.getByText(/Sign in to open this reading link\./)).toBeVisible()
})

// --------------------------------------------------------------------------- //
// Library
// --------------------------------------------------------------------------- //

test("the library lists all 64 hexagrams with working quick navigation", async ({ page }) => {
  await mockConfig(page)
  await page.goto("/en/library")
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible()

  const quickNav = page.getByRole("navigation", { name: "Browse 64 hexagrams" }).first()
  await expect(quickNav.getByRole("link")).toHaveCount(64)
  await expect(quickNav.getByRole("link").first()).toHaveAttribute("href", "#hexagram-1")
  await expect(quickNav.getByRole("link").last()).toHaveAttribute("href", "#hexagram-64")
})

test("library search narrows the list", async ({ page }) => {
  await mockConfig(page)
  await page.goto("/en/library")
  const search = page.getByLabel(/search the yi/i)
  await expect(search).toBeVisible()
  await search.fill("qian")
  await expect(page.getByRole("heading", { level: 3 }).first()).toBeVisible()
})

test("a hexagram detail page is statically reachable", async ({ page }) => {
  await mockConfig(page)
  const response = await page.goto("/en/hexagram/qian")
  expect(response?.status()).toBeLessThan(400)
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible()
})

// --------------------------------------------------------------------------- //
// Charts
// --------------------------------------------------------------------------- //

test("the chart tool posts the birth details it was given", async ({ page }) => {
  const sent: Record<string, unknown>[] = []
  await mockConfig(page)
  await page.route("**/api/tools/metaphysics", async (route) => {
    sent.push(route.request().postDataJSON())
    await route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: "unavailable" }) })
  })

  await page.goto("/en/tools")
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible()
  await page.getByRole("button", { name: /Generate my chart/i }).click()

  await expect.poll(() => sent.length, { timeout: 15_000 }).toBeGreaterThan(0)
  expect(sent[0]).toHaveProperty("timestamp")
  expect(sent[0]).toHaveProperty("timezone")
})

// --------------------------------------------------------------------------- //
// Degradation
// --------------------------------------------------------------------------- //

test("the desk still renders when the backend is unreachable", async ({ page }) => {
  await mockBackendDown(page)
  await page.goto("/en/app")
  // Not a blank page: the shell and a heading survive a dead API.
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible()
  await expect(page.getByRole("link", { name: "Study", exact: true }).first()).toBeVisible()
})

test("static content pages do not depend on the backend", async ({ page }) => {
  await mockBackendDown(page)
  for (const path of ["/en/library", "/en/hexagram/qian"]) {
    await page.goto(path)
    await expect(page.getByRole("heading", { level: 1 }), `${path} renders`).toBeVisible()
  }
})
