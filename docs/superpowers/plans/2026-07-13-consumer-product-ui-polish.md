# Consumer Product UI Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the approved ten-surface consumer product polish with P0 casting/result trust fixes first and P1 BaZi, Zi Wei, current-time, and account upgrades second.

**Architecture:** Preserve the existing Next.js/App Router, Zustand, Radix UI, FastAPI, deterministic metaphysics, and source-drawer architecture. Recompose large surfaces into focused presentational helpers, move expert controls behind progressive disclosure, and change deterministic fallback semantics in the Python service where the misleading result originates.

**Tech Stack:** Next.js 16, React 19, TypeScript, Tailwind CSS, Radix UI, Framer Motion, Playwright, FastAPI/Pydantic, pytest, lunar-python/sxtwl, iztro.

## Global Constraints

- Work only on `codex/product-ui-production-polish` until all review gates pass; then commit, merge into `main`, and push `main` as explicitly authorized by the user.
- P0 result trust and casting usability precede all P1/P2 work.
- The result page has exactly three tabs: `summary`, `hex`, `ai`; the existing `hex` ID is relabeled `卦盘与依据` for persisted-state compatibility.
- Chinese primary UI contains no `Source Library`, `Hexagram Study Page`, `canonical slots`, `source entries`, `男 / Male`, `sect1`, or `sect2`.
- Deterministic chart facts and school-specific interpretation remain visibly separate.
- Preserve existing source traceability, auth, Supabase transcript behavior, reduced-motion behavior, and dark/light themes.
- Add only focused regression/contract/e2e coverage; do not expand the test matrix without a concrete regression risk.

---

### Task 1: P0 casting and result hierarchy

**Files:**
- Modify: `tests/test_frontend_premium_contract.py`
- Modify: `tests/test_session_service.py`
- Modify: `src/iching/services/session.py`
- Modify: `frontend/src/lib/store.ts`
- Modify: `frontend/src/types/api.ts`
- Modify: `frontend/src/components/workspace/cast-form.tsx`
- Modify: `frontend/src/components/workspace/results-panel.tsx`
- Modify: `frontend/src/i18n/catalog/zh.ts`
- Modify: `frontend/src/i18n/catalog/en.ts`

**Interfaces:**
- Consumes: existing `ReadingBrief`, `SessionPayload`, source drawer, `ChatPanel`, model capability config.
- Produces: `ResultsTab = "summary" | "hex" | "ai"`; three-step cast UI; neutral no-moving-line semantics; qualitative timing strength.

- [ ] **Step 1: Write failing P0 contract tests**

Add assertions that results use three tabs, merge chart/source content under `evidence`, omit numeric confidence rendering, label stable state as `无动爻`, expose the three casting step labels, and preserve the source drawer.

- [ ] **Step 2: Run P0 tests and verify RED**

Run: `env ICHING_ARCHIVE_BASE=/tmp/iching-ui-archive python -m pytest tests/test_frontend_premium_contract.py tests/test_session_service.py -q`

Expected: failures for four-tab results, `格局稳定`, numeric fallback confidence, and missing step labels.

- [ ] **Step 3: Fix deterministic fallback semantics**

Change no-moving `stance` display semantics to neutral `stable`/`无动爻`, replace generic fallback conclusions with a source-grounded orientation, and set deterministic timing confidence to `null` rather than invented percentages. Keep parsed AI confidence optional for backward compatibility. Unknown sources must be labeled unknown, and an unresolved source ID must not silently open a different passage.

- [ ] **Step 4: Recompose casting and results**

Render steps `1 问什么`, `2 怎么起`, `3 怎么解`; default novice flow remains usable without expert settings. Replace four tab triggers with `断卦`, `卦盘与依据`, `继续追问`; render chart, Najia, decisive passages, and source drawer in the merged `hex` tab. Limit summary evidence/actions to three and move follow-up chips into chat. Remove hard-coded model latency estimates and use capability data from `/api/config`. Ensure browser-generated coin lines are saved as the coin method without being rerolled or misattributed as manual input.

- [ ] **Step 5: Run P0 tests and verify GREEN**

Run the Step 2 command and require zero failures.

- [ ] **Step 6: Commit P0**

Commit message: `feat: focus casting and reading results`

### Task 2: P1 current-time and BaZi consumer experience

**Files:**
- Modify: `tests/test_frontend_premium_contract.py`
- Modify: `frontend/src/components/tools/metaphysics-tools.tsx`
- Create: `frontend/src/components/tools/bazi-chart-view.tsx`
- Create: `frontend/src/components/tools/metaphysics-controls.tsx`
- Modify: `frontend/src/types/api.ts`

**Interfaces:**
- Consumes: `MetaphysicsChart`, `calculateMetaphysicsChart`, existing deterministic birth profile and Da Yun payload.
- Produces: `BaziChartView` with `isCurrent` mode; basic/professional controls; historical solar-term description; current Da Yun highlighting.

- [ ] **Step 1: Write failing BaZi/tool contracts**

Assert that the tools surface includes basic/professional labels, programmatic control IDs/labels, no mixed gender or sect identifiers in Chinese UI, a day-master identity summary, current Da Yun selection, and separate current/historical solar-term rendering.

- [ ] **Step 2: Run focused contracts and verify RED**

Run: `python -m pytest tests/test_frontend_premium_contract.py -q`

- [ ] **Step 3: Split controls and result presentation**

Move reusable BaZi inputs into `metaphysics-controls.tsx`; render calendar, birth date/time, place, and gender first. Put timezone, longitude, true-solar, day boundary, leap month, and algorithm under `details` titled `专业排盘设置`. Associate labels using `htmlFor`, `id`, `aria-labelledby`, or `aria-label`.

- [ ] **Step 4: Build the consumer BaZi hierarchy**

Create `bazi-chart-view.tsx` with a day-master/four-pillar/current-Da-Yun summary, readable five-element bars, highlighted current cycle based on the chart timestamp year, hour-uncertain alternatives, and collapsed professional facts/engine notes.

- [ ] **Step 5: Correct solar-term behavior**

Pass `isCurrent` only for the current-time tab. Live countdown uses `Date.now()` only when `isCurrent` is true; historical charts show the next solar-term timestamp and days relative to `calculation_timestamp`.

- [ ] **Step 6: Run focused contracts and build**

Run: `python -m pytest tests/test_frontend_premium_contract.py -q`

Run: `npm run build` from `frontend/`.

- [ ] **Step 7: Commit BaZi/tools**

Commit message: `feat: present bazi as a consumer chart`

### Task 3: P1 interactive Zi Wei result

**Files:**
- Modify: `tests/test_frontend_premium_contract.py`
- Modify: `frontend/src/components/tools/metaphysics-tools.tsx`
- Create: `frontend/src/components/tools/ziwei-chart-view.tsx`

**Interfaces:**
- Consumes: iztro `IFunctionalAstrolabe`, `IFunctionalHoroscope`, `IFunctionalPalace`.
- Produces: consumer digest; selected-palace state; accessible palace buttons/detail; scrollable narrow-screen chart.

- [ ] **Step 1: Write failing Zi Wei contracts**

Assert that palace cells render as buttons, selected palace details exist, summary includes current decadal/yearly/four-transformation content, and professional provenance is collapsed.

- [ ] **Step 2: Run contract test and verify RED**

Run: `python -m pytest tests/test_frontend_premium_contract.py -q`

- [ ] **Step 3: Implement interactive chart**

Move the chart into `ziwei-chart-view.tsx`. Render the personal/current-period digest first, preserve the 4x4 chart at a readable minimum width inside horizontal overflow on narrow screens, and make every palace a focusable button with `aria-pressed` and a focused detail panel.

- [ ] **Step 4: Simplify Zi Wei inputs**

Keep calendar, birth time, place/gender, and horoscope date visible. Place leap-month, late-Zi, school, chart type, and year boundary in `专业排盘设置`. Keep `iztro 2.5.8 · MIT` in professional details only.

- [ ] **Step 5: Run contracts and build**

Run the Step 2 command, then `npm run build` from `frontend/`.

- [ ] **Step 6: Commit Zi Wei**

Commit message: `feat: add interactive ziwei chart guidance`

### Task 4: Home, navigation, archive, hexagram, and account polish

**Files:**
- Modify: `tests/test_frontend_premium_contract.py`
- Modify: `frontend/e2e/public-routes.spec.ts`
- Modify: `frontend/src/app/globals.css`
- Modify: `frontend/src/app/[locale]/layout.tsx`
- Modify: `frontend/src/components/providers/i18n-provider.tsx`
- Modify: `frontend/src/components/home/home-page.tsx`
- Modify: `frontend/src/app/[locale]/library/page.tsx`
- Modify: `frontend/src/components/library/library-search.tsx`
- Modify: `frontend/src/app/[locale]/hexagram/[slug]/page.tsx`
- Modify: `frontend/src/components/profile/profile-page.tsx`
- Modify: `frontend/src/i18n/catalog/zh.ts`
- Modify: `frontend/src/i18n/catalog/en.ts`

**Interfaces:**
- Consumes: existing locale routing, archive index/search, Supabase auth/history components.
- Produces: task-oriented navigation, compact home, consumer archive/detail, one signed-out account conversion surface.

- [ ] **Step 1: Write failing consumer-language contracts and public e2e expectations**

Assert the approved navigation labels and active state, hydrated document language, banned internal strings, home intent shortcuts, localized archive meanings, safe hexagram learning action, live search result count, and single signed-out auth surface.

- [ ] **Step 2: Run contracts and verify RED**

Run: `python -m pytest tests/test_frontend_premium_contract.py -q`

- [ ] **Step 3: Polish global hierarchy and home**

Use task labels in navigation, add `aria-current`, remove GitHub and duplicate profile text links from the primary navigation, and update document language from the locale provider. Move 经典 to secondary weight, shorten the hero to fit the first viewport, add four intent links, keep one compact sample result, and replace the three-card strip with a simple proof row/divider.

- [ ] **Step 4: Rework archive and hexagram detail**

Remove consumer-facing database counts, raw slot keys, and internal English labels. Show localized meaning/theme summaries in archive cards and announce search result counts. On detail pages, lead with meaning and situations, add a six-line progression index, use keyboard-reachable per-slot collapsed source sections with sticky-header-safe anchors, and remove any action that implies preselecting a divination result.

- [ ] **Step 5: Rework signed-out My page**

Render a single login-first panel with three benefits, privacy copy, Google-first sign-in, visible form labels, and correct autocomplete attributes. Do not render empty metrics/account summary for guests. Preserve all signed-in cloud record operations and map raw provider errors to consumer-safe messages.

- [ ] **Step 6: Run contracts and e2e**

Run: `python -m pytest tests/test_frontend_premium_contract.py -q`

Run: `npm run test:e2e -- --project=chromium` from `frontend/`.

- [ ] **Step 7: Commit public/account polish**

Commit message: `feat: polish consumer journeys across the app`

### Task 5: Production verification and whole-branch review

**Files:**
- Modify only files required by verified defects.

**Interfaces:**
- Consumes: complete branch diff and production-like local frontend/backend.
- Produces: clean build/test evidence, desktop/mobile browser evidence, reviewed branch commits.

- [ ] **Step 1: Run backend and frontend verification**

Run: `env ICHING_ARCHIVE_BASE=/tmp/iching-ui-archive python -m pytest tests/test_frontend_premium_contract.py tests/test_metaphysics.py tests/test_session_service.py -q`

Run: `npm run lint` from `frontend/`.

Run: `npm run build` from `frontend/`.

Run: `npm run test:e2e -- --project=chromium` from `frontend/`.

- [ ] **Step 2: Run Browser QA**

Flow: `/zh` → intent shortcut → `/zh/app` → chart-only cast → three-tab result; `/zh/tools` → current → BaZi result → Zi Wei result; `/zh/library` → hexagram detail; `/zh/profile` signed-out. Check desktop and mobile, page identity, meaningful DOM, overlays, console warnings/errors, screenshots, keyboard focus, and one interaction per surface.

- [ ] **Step 3: Request whole-branch code review**

Generate a review package from `git merge-base main HEAD` through `HEAD`. Reviewer checks all ten requirements, React performance, accessibility, trust language, backward compatibility, and test quality.

- [ ] **Step 4: Fix every Critical or Important finding and re-verify**

Use the focused test file for each fix, then repeat Step 1 and relevant Browser flow.

- [ ] **Step 5: Record the checkpoint**

Record branch state, exact per-surface completion, verification evidence, and remaining limitations. Keep all work on `codex/product-ui-production-polish`; final commit, merge, and push happen only after Tasks 6–8 pass.

### Task 6: Production-safe birth-place resolution

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`
- Create: `frontend/src/app/api/locations/route.ts`
- Create: `frontend/src/lib/location-search.ts`
- Create: `frontend/src/components/tools/birth-place-field.tsx`
- Modify: `frontend/src/components/tools/metaphysics-controls.tsx`
- Modify: `frontend/src/components/tools/metaphysics-tools.tsx`
- Modify: `tests/test_frontend_premium_contract.py`
- Modify: `frontend/e2e/public-routes.spec.ts`

**Interfaces:**
- Consumes: `city-timezones@1.3.4`, browser `Intl` timezone, optional browser Geolocation API, current `birthPlace`, `timezone`, and `longitude` form state.
- Produces: `GET /api/locations?q=<query>&locale=<zh|en>` returning at most eight `{ id, name, region, country, latitude, longitude, timezone }` results; `POST /api/locations` accepting bounded latitude/longitude and returning a confirmable nearest-city candidate; `BirthPlaceField` resolves one explicit selection and updates place/timezone/longitude.

- [ ] **Step 1: Add failing location contracts**

Assert that the location route rejects queries shorter than two characters, caps results, returns timezone/longitude, includes Chinese aliases, and that the birth-place field exposes a named combobox/listbox with resolved-state copy and a manual fallback. Assert browser timezone initialization, user-gesture-only geolocation, bounded nearest-city resolution, explicit confirmation, privacy copy, and non-blocking denied/timeout fallbacks.

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests/test_frontend_premium_contract.py -q`

Expected: failures for missing location route, search field, resolved place state, and dependency.

- [ ] **Step 3: Add the local resolver and route**

Pin `city-timezones` to `1.3.4`. Normalize and deduplicate local results in `location-search.ts`; use a small explicit Chinese alias table for common Chinese-speaking regions; require a deliberate user selection; never call a third-party geocoder at runtime.

- [ ] **Step 4: Integrate the accessible field**

Create `BirthPlaceField` with debounced local API search, keyboard-operable results, loading/empty/error states, country/region disambiguation, a clear action, and an optional current-location action. Read the browser IANA timezone by default without permission. Request geolocation only from the current-location button, match coordinates locally, show the candidate for confirmation, and keep manual search usable on denial/error. On confirmed selection update visible place, IANA timezone, and longitude. Explain that current location may differ from birth place and that manual professional settings override resolved values.

- [ ] **Step 5: Verify GREEN**

Run the Step 2 command, then run `npm run lint` from `frontend/`.

### Task 7: Share-ready BaZi and Zi Wei consumer results

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`
- Create: `frontend/src/components/tools/chart-export-button.tsx`
- Create: `frontend/src/lib/chart-export.ts`
- Modify: `frontend/src/components/tools/bazi-chart-view.tsx`
- Modify: `frontend/src/components/tools/ziwei-chart-view.tsx`
- Modify: `frontend/src/components/tools/metaphysics-tools.tsx`
- Modify: `frontend/src/app/globals.css`
- Modify: `tests/test_frontend_premium_contract.py`
- Modify: `frontend/e2e/public-routes.spec.ts`

**Interfaces:**
- Consumes: rendered deterministic `MetaphysicsChart`, iztro chart/horoscope snapshot, existing locale/theme, `html-to-image@1.11.13` lazy import.
- Produces: dedicated `[data-chart-export-root]` share canvases and `ChartExportButton` that downloads a high-resolution PNG with a safe localized filename.

- [ ] **Step 1: Add failing consumer/export contracts**

Assert one export action per completed BaZi/Zi Wei result, a dedicated bounded export root, excluded control/professional regions, localized failure copy, collapsed Zi Wei edit controls after generation, identity/current-period facts before raw charts, and timeline/current-cycle semantics.

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests/test_frontend_premium_contract.py -q`

Expected: failures for the missing export component/share canvas and consumer result hierarchy.

- [ ] **Step 3: Implement reusable lazy PNG export**

Pin `html-to-image` to `1.11.13`. Lazy-import `toPng` on click, render at a bounded high-resolution pixel ratio, filter `[data-export-exclude]`, download with a safe filename, prevent double submission, and surface localized success/failure states.

- [ ] **Step 4: Recompose BaZi**

Render one share-ready identity canvas, a coherent four-pillar composition, a five-element report chapter, and a horizontally navigable Da Yun timeline with the current period emphasized. Convert ordinary nested cards to plain sections/dividers; leave detailed facts in one professional disclosure.

- [ ] **Step 5: Recompose Zi Wei**

Collapse the completed chart's editing controls behind `修改资料`, lead with a share-ready identity/current-period canvas, retain the readable interactive twelve-palace chart, and restyle palace detail/provenance as clear chapters rather than a card mosaic.

- [ ] **Step 6: Verify GREEN and build**

Run the Step 2 command, then `npm run lint` and `npm run build` from `frontend/`.

### Task 8: Final density, review, and integration gate

**Files:**
- Modify only files required by verified defects.

**Interfaces:**
- Consumes: the complete working-tree diff from `744b7de`, the design specification, and all task reports.
- Produces: a reviewed, committed feature branch; a verified merge commit or fast-forward on `main`; pushed `origin/main`.

- [ ] **Step 1: Run the final density pass**

Inspect Home, casting, three reading tabs, tools inputs/results, archive, hexagram detail, and My. Remove border/card treatment when it does not communicate interactivity, selection, containment, or a distinct result surface. Keep keyboard focus and contrast visible.

- [ ] **Step 2: Run full verification**

Run: `env ICHING_ARCHIVE_BASE=/tmp/iching-ui-archive python -m pytest tests/test_frontend_premium_contract.py tests/test_metaphysics.py tests/test_session_service.py tests/test_divination_methods.py -q`

Run: `npm run lint`, `npm run build`, and `npm run test:e2e -- --list --project=chromium` from `frontend/`. Run browser bodies when the environment permits local server binding.

- [ ] **Step 3: Whole-branch review and fix wave**

Give the reviewer the complete diff including untracked production files. Require explicit Critical/Important/Minor findings and a merge-readiness verdict. Dispatch one fix wave for every Critical or Important item, rerun covering tests, and re-review.

- [ ] **Step 4: Commit, merge, verify, and push**

Commit on `codex/product-ui-production-polish`, switch to `main`, merge without force, rerun the focused Python regression plus frontend production build, then push `main` to `origin`. Report exact commit hashes and any browser-environment limitation.
