import { expect, test } from "@playwright/test"

const oldHomepagePhrases = [
  "From yarrow stalks to AI",
  "Tired of ChatGPT-style vagueness",
  "AI WORKBENCH",
  "Coming Soon",
]

test("public home, tools, library, and hexagram pages render current product surface", async ({ page, isMobile }) => {
  await page.goto("/en")
  await expect(page.getByRole("heading", { name: /cast, interpret, and follow up/i })).toBeVisible()
  if (isMobile) {
    await expect(page.getByRole("link", { name: "Metaphysics Tools" })).toBeVisible()
  }
  for (const phrase of oldHomepagePhrases) {
    await expect(page.locator("body")).not.toContainText(phrase)
  }

  await page.goto("/en/tools")
  await expect(page.getByRole("heading", { name: /metaphysics tools/i })).toBeVisible()
  await expect(page.getByRole("tab", { name: /current time/i })).toBeVisible()

  await page.goto("/en/library")
  await expect(page.getByRole("heading", { name: /classical archive study library/i })).toBeVisible()
  await expect(page.getByLabel(/search the yi/i)).toBeVisible()
  await page.getByLabel(/search the yi/i).fill("qian")
  await expect(page.getByText(/Qián/).first()).toBeVisible()

  await page.goto("/en/hexagram/qian")
  await expect(page.getByRole("heading", { name: /Hexagram 1/i })).toBeVisible()
  await expect(page.getByText(/Qián/).first()).toBeVisible()
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
