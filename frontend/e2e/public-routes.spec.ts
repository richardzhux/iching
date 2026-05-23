import { expect, test } from "@playwright/test"

const oldHomepagePhrases = [
  "From yarrow stalks to AI",
  "Tired of ChatGPT-style vagueness",
  "AI WORKBENCH",
  "Coming Soon",
]

test("public home, method, library, and hexagram pages render current product surface", async ({ page }) => {
  await page.goto("/en")
  await expect(page.getByRole("heading", { name: /serious reading desk/i })).toBeVisible()
  for (const phrase of oldHomepagePhrases) {
    await expect(page.locator("body")).not.toContainText(phrase)
  }

  await page.goto("/en/method")
  await expect(page.getByRole("heading", { name: /method, sources, and boundaries/i })).toBeVisible()
  await expect(page.getByText(/AI synthesis is allowed/i)).toBeVisible()

  await page.goto("/en/library")
  await expect(page.getByRole("heading", { name: /classical archive study library/i })).toBeVisible()
  await page.getByLabel(/search the yi/i).fill("qian")
  await expect(page.getByText(/Qián/).first()).toBeVisible()

  await page.goto("/en/hexagram/qian")
  await expect(page.getByRole("heading", { name: /Hexagram 1/i })).toBeVisible()
  await expect(page.getByText(/Qián/).first()).toBeVisible()
})

test("reading desk does not regress to the stale loading-only state", async ({ page }) => {
  await page.goto("/en/app")
  await expect(page.locator("body")).not.toContainText("Loading workspace configuration...")
  await expect(
    page.getByText(/What are you actually deciding|The reading desk could not load|Preparing the reading desk/i).first(),
  ).toBeVisible()
})

test("mobile reading desk exposes question coaching and casting controls", async ({ page, isMobile }) => {
  test.skip(!isMobile, "mobile-only smoke")
  await page.goto("/en/app")
  const question = page.getByLabel("Question")
  if (await question.isVisible()) {
    await question.fill("Will I get the job?")
    await expect(page.getByText(/Better as an inquiry question/i)).toBeVisible()
    await expect(page.getByRole("button", { name: /Toss one coin line/i })).toBeVisible()
  } else {
    await expect(page.getByText(/The reading desk could not load/i)).toBeVisible()
  }
})
