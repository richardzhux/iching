# Consumer Product UI Polish Design

## Goal

Turn the existing technically capable application into a consumer-ready divination product whose first screen, casting flow, reading result, metaphysics tools, archive, and account surface are immediately understandable to a first-time user while preserving professional source traceability.

## Approved Product Direction

The product is a professional divination, interpretation, follow-up, and case-management tool. Consumer outcomes must appear before raw algorithms, source counts, engine names, or expert settings.

The top-level product jobs are:

- 问卦 / Divination
- 八字 / BaZi
- 紫微 / Zi Wei
- 我的 / My Records

The classical archive remains available as a secondary knowledge entry rather than competing with the primary jobs.

## Visual Thesis

A calm, dark amethyst divination instrument with restrained warm-metal highlights: conclusion-first, card-light, and professional without looking like an admin dashboard. Three surface levels establish hierarchy: decisive result, ordinary working content, and collapsed professional metadata.

## Content Plan

1. The home page promises a concrete outcome and offers four common intents.
2. The casting flow explains what the user is asking, how the cast is made, and how deeply it should be interpreted.
3. The result page answers first, proves second, and continues the conversation third.
4. BaZi and Zi Wei show a personal digest and current period before the raw chart.
5. Archive and account pages prioritize user tasks over database metrics and empty dashboards.

## Interaction Thesis

- Progressive disclosure keeps novice inputs visible and expert settings in a sheet or details region.
- Result tabs use a three-part mental model: 断卦, 卦盘与依据, 继续追问.
- Subtle entry and state transitions clarify the active result, current fortune period, and selected Zi Wei palace while respecting reduced-motion preferences.

## Requirements By Surface

### 1. Home

- Replace institutional explanation with a concrete promise: direction, timing or conditions, and next action.
- Offer 事业, 感情, 选择, and 近况 shortcuts that open the casting page with an understandable starting context.
- Keep one compact sample result and one primary call to action.
- Remove the repetitive three-card feature strip and excess first-viewport height.

### 2. Casting

- Present three explicit steps: 问什么, 怎么起, 怎么解.
- Default to a beginner path and explain every traditional method in plain language.
- Keep context, raw line values, custom time, and detailed AI controls behind progressive disclosure.
- Show the AI value and login path inline when a signed-out user selects standard or deep interpretation.
- Use 起卦 consistently for the primary action.
- Browser-generated coin lines remain the exact submitted lines and are attributed to the three-coin method rather than rerolled or stored as manual input.

### 3. Reading Result

- Use exactly three tabs: 断卦, 卦盘与依据, 继续追问.
- The first viewport contains one judgment, at most three decisive reasons, timing or trigger conditions without numeric pseudo-confidence, risks, and at most three actions.
- Merge the current chart and source tabs. Show the chart first; open full source text in the existing source drawer.
- Keep outcome journaling in a separate collapsible record, not a fourth tab.
- Replace the no-moving-lines label “格局稳定” with the neutral “无动爻”.
- Legacy fallback text must be useful and must not pretend to be an AI interpretation.
- Deterministic fallback timing must not display invented percentages.
- Unknown sources are attributed honestly, and unresolved source links never substitute an unrelated first passage.

### 4. Current Time

- Show a consumer digest first: Gregorian/lunar date, solar term, four pillars, month command, day branch, void branches, and the next solar term.
- Keep engine/version and detailed rule notes in a professional details section.
- Only show a live countdown when the chart represents the current moment. Historical charts show the exact solar-term timestamp and relative distance from the chart time.

### 5. BaZi

- Basic inputs: calendar, birth date/time, place, and gender.
- Professional settings: timezone, longitude, true-solar correction, late-Zi boundary, leap month, and Da Yun algorithm.
- All controls have programmatic labels; Chinese UI does not mix “男 / Male” or expose `sect1`/`sect2` as the primary label.
- The result begins with a shareable identity summary: day master, four pillars, current Da Yun where available, and calculation rule.
- Add a readable five-element distribution, highlight the current Da Yun cycle, and collapse raw professional facts.
- Do not declare strength, pattern, favorable element, or deterministic fate without a selected and named school.

### 6. Zi Wei

- Separate basic and professional input settings.
- Result begins with soul/body rulers, five-element class, current decadal period, current annual period, and four transformations.
- Highlight the selected/current palace. Palace cells are buttons and open a focused detail panel.
- Narrow screens use horizontally scrollable/zoomable chart space rather than unreadably compressing all twelve palaces.
- Keep iztro license and engine provenance inside professional details.

### 7. Classical Archive

- Remove `canonical slots`, `source entries`, coverage counts, and internal English labels from the consumer header and cards.
- Add theme-oriented browsing and retain search.
- Each hexagram card shows number, Chinese name, pinyin, a localized one-line meaning, and themes; source completeness remains in a low-priority data note only where useful.

### 8. Hexagram Detail

- Lead with what the hexagram means, common situations, and the six-line progression.
- Replace “用此卦起一条阅读” with a learning-safe action; users cannot preselect a divination result.
- Default source sections to concise previews and allow expansion per source or slot.
- Remove slot IDs, technical source counts, and mixed internal labels from the primary reading path.

### 9. My

- Rename 个人中心 to 我的.
- Signed-out state has one conversion surface with three benefits, a privacy statement, and the actual login controls.
- Do not show empty archive metrics or duplicate guest/auth requirement panels before login.
- Signed-in state continues to show cloud records, export, deletion, and follow-up.

### 10. Global System

- Desktop navigation emphasizes user jobs and keeps 经典 as secondary.
- The active route is exposed visually and with `aria-current`; hydrated locale updates the document language for Chinese and English routes.
- Remove implementation-facing English, engine strings, and source metrics from Chinese primary surfaces.
- Reduce decorative borders/cards where plain sections and dividers preserve meaning.
- Associate every label with its input/select/switch, preserve visible focus, 44px mobile tap targets, reduced motion, and readable muted-text contrast.
- Search result updates expose a live result count; source reading regions and detail navigation remain keyboard reachable below the sticky header.
- Preserve the existing theme and source-traceability architecture; no new backend persistence or paid feature is introduced.

## Data And Trust Boundaries

- Deterministic chart facts remain distinct from school-specific interpretation.
- Existing API payloads are reused unless a missing fact is required for correctness.
- AI access remains authenticated and current conversations remain stored through the existing transcript pipeline.
- No medical, legal, financial, emergency, or fate-certain claim is introduced.

## Acceptance

- The result page exposes exactly three top-level tabs and contains no “格局稳定” or numeric confidence label.
- A signed-out first-time user can understand and complete a chart-only cast without opening professional settings.
- The BaZi page no longer displays a zero live countdown for a historical birth chart.
- Current Da Yun and Zi Wei periods are visually identifiable when present.
- Chinese primary UI contains none of: `Source Library`, `Hexagram Study Page`, `canonical slots`, `source entries`, `男 / Male`, `sect1`, `sect2`.
- Public desktop and mobile smoke flows render without framework overlays or relevant console errors.
- Frontend production build, focused backend tests, contract tests, and Playwright public-route tests pass.

## Scope Check

This is one coordinated product-hierarchy release across shared navigation, casting/results, metaphysics, archive, and account surfaces. The work is split into independently reviewable tasks, but all tasks share the same vocabulary and visual hierarchy and therefore remain in one branch and one specification.

## Production Consumer Finish Addendum

### Product Principle

The metaphysics tools are not an archive browser or an algorithm console. They should make a consumer feel that a personal chart has been prepared for them, let them understand the most important deterministic facts immediately, and create a satisfying object they can save or share. Professional traceability remains available without leading the experience.

### Reference Direction

Use the public consumer hierarchy associated with products such as 测测 as a structural reference: personal identity first, current stage second, chart and supporting facts third, and professional parameters last. Do not clone another product's colors, assets, copy, proprietary interpretations, or layout pixel-for-pixel. Preserve this app's amethyst and warm-metal theme, deterministic trust boundary, and existing component system.

### Visual Thesis

The BaZi and Zi Wei result should feel like a personal celestial dossier rather than a dashboard: one quiet identity canvas, a small number of clearly separated chapters, deliberate elemental color, generous breathing room, and one share action. Borders only mark interactive or semantically distinct regions. Ordinary explanatory content uses spacing and dividers.

### Birth-place Resolution

- The birth-place field becomes an accessible city search with explicit selectable results.
- The browser IANA timezone initializes automatically without requesting location permission.
- An optional `使用当前位置 / Use current location` action requests browser geolocation only after a user gesture, matches the coordinates against the local city dataset, and asks the user to confirm the result before applying it as a birth place.
- Current coordinates are processed locally and are not sent to a third-party geocoder or persisted. Permission denial, unsupported devices, timeout, or an unclear nearest-city match falls back to ordinary city search without blocking chart generation.
- The current-location result explicitly reminds the consumer that current location may not be their birth place.
- Resolution is local-first and production-safe: use a version-pinned, MIT-licensed city/timezone dataset in the server route instead of a public unauthenticated geocoding service whose terms forbid commercial use or autocomplete.
- Selecting a city fills its IANA timezone and longitude while preserving the visible place name. Latitude may be retained for provenance but is not sent to the current chart API because the algorithm only requires longitude.
- Chinese aliases cover the common mainland, Hong Kong, Macau, and Taiwan city names; Romanized/global cities use the dataset search.
- Ambiguous cities show country and first-level region. No result means the user can still continue with manual timezone/longitude in professional settings.
- The UI states when a place has been resolved and allows the consumer to clear or replace it. Manual professional edits remain authoritative after selection.

### Consumer BaZi Result

- Replace the bordered dashboard stack with a result header, a share-ready identity canvas, and chapter sections.
- The identity canvas includes day master, four pillars, birth place/time, calculation mode, and current Da Yun when available.
- Four pillars are visually legible as a single composition, using restrained five-element accents rather than unrelated card colors.
- Five-element distribution and Da Yun become readable report chapters. The current cycle is emphasized in a horizontally navigable timeline.
- Professional pillars, hidden stems, ten gods, Na Yin, void branches, engines, and algorithm notes remain in a collapsed facts section.
- Do not synthesize strength, favorable element, pattern, personality, or fortune claims without a named interpretation school.

### Consumer Zi Wei Result

- After generation, collapse the input form behind a concise “修改资料” disclosure so the result owns the viewport.
- Lead with a share-ready identity and current-period canvas containing five-element class, soul/body rulers, target date, decadal period, annual period, and four transformations.
- Keep the twelve-palace chart readable and interactive; use a quieter chart frame, selected/current emphasis, and a focused palace detail chapter instead of many equal-weight cards.
- Professional provenance and school controls remain available but visually secondary.

### One-click Export

- BaZi and Zi Wei each expose one primary `导出命盘 / Export chart` action after a successful calculation.
- Export produces a high-resolution PNG from a dedicated share canvas, not a screenshot of the whole form or browser chrome.
- The exported canvas contains product attribution, chart type, deterministic identity/current-period facts, generation date, and a short “排盘事实，不含确定性命运断语” trust note.
- Inputs, buttons, loading states, collapsed professional settings, and private account data never appear in the image.
- File names are deterministic and filesystem-safe. Export failures show a localized consumer error and do not leave the UI stuck.
- Export uses a version-pinned MIT-licensed client library and is lazy-loaded only when the user requests export.

### Acceptance Addendum

- Selecting a known Chinese or global city updates the visible resolved place, IANA timezone, and longitude without an external network request.
- Browser timezone initializes automatically; current-location lookup occurs only after a user gesture and never applies a city without confirmation.
- Denied/failed geolocation leaves manual city search and professional timezone/longitude controls fully usable.
- A failed or ambiguous lookup never silently chooses a city.
- BaZi and Zi Wei show their result before their editing controls after generation and expose a single export action.
- The export target is a dedicated, bounded share canvas and generates a PNG without control chrome.
- Consumer result chapters use spacing/dividers as the default; professional facts remain collapsed.
- Frontend lint, production build, focused backend/contract tests, and discoverable browser flows pass before merge.
- A whole-branch reviewer reports no open Critical or Important findings before the branch is merged into `main` and pushed.
