# Casting, Hexagram Library, and Frontend CI Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Correct hexagram glyphs, restore a natural casting flow, modernize compact AI controls, add 1–64 navigation, and make Frontend CI self-contained.

**Architecture:** Add two focused reusable presentation components: one for symmetric hexagram lines/stacks and one for responsive 1–64 navigation. Recompose the existing casting form without changing its store, API payload, preset actions, or model capability source. Give GitHub Actions inert test-only public configuration so the existing Playwright route mocks can run against the optimized build.

**Tech Stack:** Next.js 16 App Router, React 19, TypeScript, Tailwind CSS, Radix UI, Playwright, GitHub Actions.

## Global Constraints

- Do not modify Vercel or Render configuration.
- Do not add, copy, or rotate production credentials.
- Do not change divination, Najia, BaZi, Zi Wei, or AI interpretation algorithms.
- Preserve configured topic, method, and model data sources.
- Reuse current colors, typography, spacing, focus rings, and radius tokens.
- Desktop order is `1 问什么` → `2 怎么起` → `3 怎么解`.
- Yin lines use two equal solid segments with a real transparent center gap.

---

### Task 1: Self-contained Frontend CI

**Files:**
- Modify: `.github/workflows/frontend-ci.yml`
- Test: `tests/test_frontend_premium_contract.py`

**Interfaces:**
- Consumes: Playwright route mocks already defined in `frontend/e2e/*.spec.ts`.
- Produces: build-time `NEXT_PUBLIC_API_BASE_URL`, `NEXT_PUBLIC_SUPABASE_URL`, and `NEXT_PUBLIC_SUPABASE_ANON_KEY` test-only values for the CI job.

- [ ] **Step 1: Add a failing workflow contract**

Assert that Frontend CI contains job-level test-only public configuration and does not reference deployment secrets.

- [ ] **Step 2: Run the focused contract and verify failure**

Run: `python -m pytest tests/test_frontend_premium_contract.py -q`

Expected: FAIL because the workflow currently defines no CI public environment.

- [ ] **Step 3: Add inert job-level configuration**

Add under `jobs.build`:

```yaml
env:
  NEXT_PUBLIC_API_BASE_URL: http://127.0.0.1:8001
  NEXT_PUBLIC_SUPABASE_URL: https://ci-test.supabase.co
  NEXT_PUBLIC_SUPABASE_ANON_KEY: ci-test-anon-key
```

- [ ] **Step 4: Run the focused contract**

Run: `python -m pytest tests/test_frontend_premium_contract.py -q`

Expected: PASS.

### Task 2: Canonical hexagram glyph and quick navigation

**Files:**
- Create: `frontend/src/components/hexagram/hexagram-glyph.tsx`
- Create: `frontend/src/components/hexagram/hexagram-quick-nav.tsx`
- Modify: `frontend/src/components/home/home-page.tsx`
- Modify: `frontend/src/app/[locale]/library/page.tsx`
- Modify: `frontend/src/app/[locale]/hexagram/[slug]/page.tsx`
- Modify: `frontend/src/components/library/library-search.tsx`
- Modify: `frontend/src/lib/hexagram-copy.ts`
- Test: `tests/test_frontend_premium_contract.py`
- Test: `frontend/e2e/public-routes.spec.ts`

**Interfaces:**
- Produces: `HexagramGlyph({ lines, className, lineClassName, gapClassName })` for six-line diagrams.
- Produces: `HexagramQuickNav({ locale, mode, activeSlug? })`, where `mode` is `"anchors" | "routes"`.
- Consumes: `HEXAGRAM_LIBRARY`, `hexagramLines`, `withLocale`, and existing locale types.

- [ ] **Step 1: Add failing contracts**

Require no `bg-gradient-to-r` yin glyphs in consumer pages, no `HEXAGRAM_THEME_FILTERS` in search UI, and a reusable quick-navigation component on library and detail pages.

- [ ] **Step 2: Run contracts and verify failure**

Run: `python -m pytest tests/test_frontend_premium_contract.py -q`

Expected: FAIL on gradient glyphs, theme filters, and missing navigation.

- [ ] **Step 3: Build the shared glyph**

Render yang as one solid bar and yin as two `flex-1` solid bars separated by a fixed center gap. Map supplied line values without gradients or shadows.

- [ ] **Step 4: Replace consumer diagram implementations**

Use `HexagramGlyph` in the homepage sample, library cards, and hexagram detail header. Retain current sizes through component props.

- [ ] **Step 5: Remove heuristic theme filtering**

Delete active-theme state, theme buttons, `HEXAGRAM_THEME_FILTERS`, and `matchesThemeFilter`. Keep query ranking and the existing result limit.

- [ ] **Step 6: Add responsive 1–64 navigation**

Use a sticky left sidebar at `lg` widths and a horizontal scroll list below `lg`. Library links target `#hexagram-N`; detail links target localized detail routes. Add stable IDs to library entries.

- [ ] **Step 7: Add a browser assertion**

Verify the theme-filter buttons are absent, `64` quick links are present, and selecting `#64` updates the URL fragment.

- [ ] **Step 8: Run focused contracts and E2E**

Run: `python -m pytest tests/test_frontend_premium_contract.py -q`

Run: `npm run test:e2e -- --project=chromium --grep "library"`

Expected: PASS.

### Task 3: Casting hierarchy and compact AI settings

**Files:**
- Modify: `frontend/src/components/workspace/cast-form.tsx`
- Modify: `frontend/src/i18n/catalog/en.ts`
- Modify: `frontend/src/i18n/catalog/zh.ts`
- Test: `tests/test_frontend_premium_contract.py`
- Test: `frontend/e2e/p0-casting-results.spec.ts`
- Test: `frontend/e2e/public-routes.spec.ts`

**Interfaces:**
- Consumes: existing `readingModes`, `setForm`, `updateForm`, `activeModel`, model capability data, auth state, and method builder.
- Produces: the same `SessionRequest` payload and preset behavior with a new visual order.

- [ ] **Step 1: Add failing hierarchy contracts**

Require a compact page title, source-order markers for question/cast/interpret, a three-column interpretation selector, no duplicate AI switch, a four-column desktop AI control row, and a full-width topic trigger.

- [ ] **Step 2: Run contracts and verify failure**

Run: `python -m pytest tests/test_frontend_premium_contract.py -q`

Expected: FAIL on current `1 → 3 → 2` structure and oversized settings.

- [ ] **Step 3: Recompose the form sections**

Move casting method and builder immediately after the question section. Place interpretation after casting and add `data-cast-step="question|cast|interpret"` markers for stable tests.

- [ ] **Step 4: Compact topic and interpretation controls**

Make the topic trigger `h-11 w-full`. Render the three reading presets in one `sm:grid-cols-3` group and one active-description row.

- [ ] **Step 5: Remove redundant AI switch and compact controls**

Keep preset actions authoritative. When AI is enabled, render model, reasoning, verbosity, and tone in `xl:grid-cols-4`; keep password/login support in a separate compact row.

- [ ] **Step 6: Run focused contracts and casting E2E**

Run: `python -m pytest tests/test_frontend_premium_contract.py -q`

Run: `npm run test:e2e -- --project=chromium --grep "intent|coin builder|divination desk"`

Expected: PASS.

### Task 4: Production verification and CI confirmation

**Files:**
- Modify only if verification finds an in-scope defect.

**Interfaces:**
- Consumes: completed tasks 1–3.
- Produces: a clean branch commit and a green Frontend CI workflow.

- [ ] **Step 1: Run static verification**

Run: `npm run lint`

Run: `npm run build`

Expected: both PASS; production build generates all localized pages.

- [ ] **Step 2: Run focused Python contracts**

Run: `env ICHING_ARCHIVE_BASE=/tmp/iching-ui-archive python -m pytest tests/test_frontend_premium_contract.py tests/test_metaphysics.py tests/test_session_service.py tests/test_divination_methods.py -q`

Expected: PASS.

- [ ] **Step 3: Run desktop and mobile browser suites**

Run: `npm run test:e2e`

Expected: all applicable tests PASS; the desktop project skips only the explicitly mobile-only assertion.

- [ ] **Step 4: Inspect rendered screenshots**

Capture `/zh/app`, `/zh/library`, and one `/zh/hexagram/<slug>` desktop state plus `/zh/app` mobile. Confirm symmetric yin gaps, title visibility, 1→2→3 order, compact AI controls, and usable 1–64 navigation.

- [ ] **Step 5: Commit and push the feature branch**

Stage only in-scope files and commit with `fix: polish casting and hexagram navigation`.

- [ ] **Step 6: Re-run Frontend CI**

Push the branch and inspect the new Frontend CI run. Completion requires lint, build, and Chromium E2E to be green.
