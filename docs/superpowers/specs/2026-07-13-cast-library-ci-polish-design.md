# Casting, Hexagram Library, and Frontend CI Polish

**Date:** 2026-07-13

## Goal

Finish the consumer-facing casting and hexagram-browsing surfaces without changing divination algorithms, production API topology, Vercel variables, Render variables, or production credentials.

## 1. Frontend CI isolation

- Keep the existing production environment contract unchanged.
- Give GitHub Actions explicit test-only public values for the API base URL and Supabase client configuration.
- Values are inert test-only configuration used so the optimized Next.js bundle reaches Playwright's mocked network routes.
- Do not copy production secrets into GitHub Actions.
- Keep lint, production build, and Chromium E2E as required workflow steps.

## 2. Canonical hexagram line rendering

- Replace gradient-based yin lines with two equal solid segments separated by a real transparent center gap.
- Use one reusable line/stack component for homepage samples, the 64-hexagram browse grid, and hexagram detail headers.
- Preserve existing foreground colors, dimensions, rounded ends, responsive sizing, and screen-reader hiding for decorative diagrams.
- Workspace line SVGs already use symmetric coordinates and remain unchanged unless verification finds a mismatch.

## 3. Casting page hierarchy

- Add a compact page title: `起卦` / `Cast`.
- Render the working flow in visible order: `1 问什么` → `2 怎么起` → `3 怎么解`.
- Keep optional background and advanced time/raw-line settings secondary.
- Do not reintroduce a large marketing or explanatory hero.

## 4. Topic control

- Keep the configured topic data source and current persistence rules.
- Make the topic selector full-width, calm, and visually consistent with the current input system.
- Preserve accessible labeling, keyboard behavior, URL intent hydration, and rejection of empty or unknown values.

## 5. Interpretation and AI controls

- Present `仅排盘` / `标准解读` / `深度解读` as one compact segmented row on desktop and a responsive grid on narrow screens.
- Show only the active mode's short explanation below the row.
- Remove the redundant AI enable switch: chart-only disables AI; standard and deep enable it through their existing preset actions.
- When AI is enabled, place model, reasoning, verbosity, and tone in one four-column desktop row, collapsing responsively.
- Keep password/login messaging available without dominating the settings panel.
- Preserve the backend model capability list and existing preset semantics.

## 6. Library search and navigation

- Remove the heuristic theme-filter buttons and their active-filter state.
- Keep name, number, pinyin, meaning, and source-text search.
- Add a reusable 1–64 quick navigation surface listing number and Chinese hexagram name.
- On the library index, navigation targets the matching in-page hexagram entry.
- On detail pages, navigation opens the selected hexagram directly.
- Desktop uses a sticky, independently scrollable left sidebar; narrow layouts use a compact horizontal navigation surface.

## 7. Visual and accessibility requirements

- Reuse current colors, typography, spacing tokens, focus rings, and radius system.
- Avoid new gradients, decorative card stacks, fake precision, or additional marketing copy.
- Preserve 44px primary touch targets where practical and accessible names for selectors and navigation.
- Respect reduced-motion behavior already present in the app.

## 8. Verification

- Contract checks cover removal of gradient yin glyphs, correct casting order, compact interpretation controls, removal of heuristic filters, quick navigation, and CI test variables.
- ESLint and the optimized production build must pass.
- Chromium tests cover casting intent/method flows and the library quick navigation.
- A focused visual comparison checks the three supplied problem areas at desktop width and the casting/library surfaces at mobile width.
- The GitHub Actions workflow is re-run after push; completion requires a green Frontend CI run.

## Out of scope

- No changes to hexagram, Najia, BaZi, Zi Wei, or AI interpretation algorithms.
- No Vercel or Render environment changes.
- No production secret rotation.
- No broader homepage, results-page, account, or chat redesign.
- No new hexagram theme taxonomy.
