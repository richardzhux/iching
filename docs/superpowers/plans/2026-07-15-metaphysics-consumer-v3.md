# Metaphysics Consumer V3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the BaZi and Zi Wei result surfaces into a deterministic consumer product centered on identity, ranked themes, life K-lines, and collectible configurations.

**Architecture:** Extend the Python BaZi engine with versioned pattern, ShenSha-effect, combination, score, ranking, archetype, timeline, and structural-twin payloads. Extend the client-side Zi Wei engine with the same consumer contract using the existing iztro chart and public baseline. Render both through three result destinations: identity, life K-line, and full chart; keep raw professional data available but secondary.

**Tech Stack:** Python 3.10+/FastAPI/Pydantic, sxtwl, lunar-python, Next.js 16, React 19, TypeScript, iztro 2.5.8, Tailwind CSS, SVG charts, Supabase JSONB snapshots.

## Global Constraints

- No Stripe, billing UI, new environment variables, or public user data.
- Scores and K-line values must be deterministic; AI may phrase explanations but never generate numbers.
- Main score and the four theme scores use 0–100 values plus global and cohort percentile ranks.
- Remove `7/7 evidence-family activity` as a consumer metric.
- BaZi evidence priority is original structure/pattern (cap 65), documented combinations (cap 20), and effective ShenSha (cap 15), with explicit constraints subtracting from the raw score.
- Consumer copy leads with identity and rankings; methodology, hashes, engines, and sources remain one click away.
- Default result navigation is `我是谁 | 人生 K 线 | 完整命盘`.
- Preserve private local/Supabase chart persistence and export compatibility.
- Keep one optional, unused `capability_key` seam; do not implement entitlements.
- Avoid page-level horizontal overflow at 390px; professional tables may scroll inside their own containers.

---

### Task 1: V3 consumer data contracts

**Files:**
- Create: `src/iching/core/metaphysics_consumer.py`
- Modify: `src/iching/core/metaphysics.py`
- Modify: `src/iching/web/models.py`
- Modify: `frontend/src/types/api.ts`
- Test: `tests/test_metaphysics_consumer.py`

**Interfaces:**
- Produces `ConsumerIdentity`, `ThemeScore`, `ComparisonRank`, `PatternAssessment`, `ShenShaState`, `ShenShaCombination`, `LifeKlineSeries`, and `StructuralTwin` JSON-compatible payloads.
- `build_metaphysics_chart()` returns `consumer`, increments `derived_schema_version` to `6`, and snapshots remain JSONB-compatible.

- [ ] Define typed payload dictionaries and a stable `CONSUMER_RULES_VERSION`.
- [ ] Add the `consumer` response field and frontend types without changing existing raw chart fields.
- [ ] Add a schema-contract test proving serialization and backwards-compatible raw fields.
- [ ] Run `pytest -q tests/test_metaphysics_consumer.py tests/test_metaphysics.py`.

### Task 2: BaZi pattern and ShenSha-effect engine

**Files:**
- Create: `src/iching/core/bazi_patterns.py`
- Create: `src/iching/core/shensha_effects.py`
- Modify: `src/iching/core/shensha.py`
- Modify: `src/iching/core/metaphysics.py`
- Test: `tests/test_bazi_patterns.py`
- Test: `tests/test_shensha_effects.py`

**Interfaces:**
- `assess_patterns(pillars, structure) -> PatternAssessment` evaluates month-command candidates, transparency/meetings, formation, break, rescue, and strict special-pattern gates.
- `evaluate_shensha_effects(hits, pillars, structure) -> {hits, combinations}` assigns `发力|有力|可见|受制` and provenance tiers `classical_named|classical_interaction|product_cluster`.

- [ ] Implement ordinary patterns: 正官、七杀、正财、偏财、食神、伤官、正印、偏印、建禄、阳刃.
- [ ] Implement strict follow/exclusive patterns: 从财、从杀、从儿、从旺/从强、曲直、炎上、稼穑、从革、润下.
- [ ] Implement rule-specific effect flags using roots, season, void, clash/punishment/harm/break, and structure echo.
- [ ] Implement the first documented combinations: 禄马同乡/交驰、学堂会禄/会贵/朝驿马、二德扶持、将星扶德天乙加临、羊刃带禄官印相资、德秀学堂财官、有文有印.
- [ ] Add bold modern product clusters without labeling them ancient patterns.
- [ ] Run the focused pattern and ShenSha tests.

### Task 3: Scores, rankings, archetypes, and twins

**Files:**
- Modify: `src/iching/core/metaphysics_consumer.py`
- Modify: `src/iching/core/metaphysics_statistics.py`
- Modify: `scripts/generate_bazi_baseline.py`
- Create: `src/iching/core/data/bazi-consumer-1924-2044-c1-forward.json`
- Create: `src/iching/core/data/bazi-consumer-1924-2044-c1-current.json`
- Test: `tests/test_metaphysics_consumer.py`

**Interfaces:**
- `build_bazi_consumer_profile(chart_facts, baseline) -> consumer` returns main score, four theme scores, global/cohort ranks, one primary archetype, five salient fingerprints, achievements, and structural twins.
- Consumer baseline stores compact histograms, selected readable joint features, cohort histograms, archetype thresholds, and representative cluster states rather than full signatures.

- [ ] Define deterministic supporting and constraining weights with family caps 65/20/15.
- [ ] Map raw scores through weighted empirical CDFs for `score`, `global_percentile`, `global_top_percentage`, `cohort_percentile`, and `cohort_top_percentage`.
- [ ] Build 18 dramatic but distinct BaZi archetypes and non-repeating fingerprint salience ranking.
- [ ] Build structural-family clusters with three representative calendar states.
- [ ] Generate compact consumer baselines and validate their hashes/denominators.
- [ ] Ensure repeated generation of the same chart returns byte-equivalent consumer numbers.

### Task 4: Deterministic BaZi life K-line

**Files:**
- Modify: `src/iching/core/metaphysics_consumer.py`
- Modify: `src/iching/core/metaphysics.py`
- Modify: `src/iching/web/api/routes.py`
- Modify: `src/iching/web/models.py`
- Modify: `frontend/src/lib/api.ts`
- Test: `tests/test_metaphysics_consumer.py`
- Test: `tests/test_api.py`

**Interfaces:**
- `build_life_kline(cycles, natal_scores) -> LifeKlineSeries` computes five deterministic series: 综合、事业、财富、感情、健康.
- Annual candle semantics are `open=first solar-term month`, `close=last`, `high=max(12 months)`, `low=min(12 months)`, `volume=weighted activation/constraint intensity`.

- [ ] Convert existing Da Yun/year/month activations into signed deterministic monthly scores.
- [ ] Produce the default ten-year window, full-life data, MA3/MA5/MA10, peaks, troughs, reversals, and top-three stages.
- [ ] Add an on-demand timeline API so unopened cycles do not inflate the initial payload.
- [ ] Verify identical inputs always produce identical OHLC values and `high >= open/close >= low`.

### Task 5: Zi Wei consumer engine

**Files:**
- Create: `frontend/src/lib/ziwei-consumer.ts`
- Modify: `frontend/src/lib/ziwei-statistics.ts`
- Modify: `scripts/generate_ziwei_baseline.mjs`
- Create: `src/iching/core/data/ziwei-consumer-1924-2044-c1.json`
- Modify: `frontend/src/types/api.ts`
- Test: `tests/test_frontend_premium_contract.py`

**Interfaces:**
- `buildZiweiConsumerProfile(chart, horoscope, statistics) -> ZiweiConsumerProfile` returns main/four-theme ranks, archetype, five fingerprints, achievements, twins, and life K-line.
- Zi Wei scoring uses key-palace stars/brightness, four transformations, body palace, auspicious/challenging distributions, palace relationships, and period activations.

- [ ] Define 18 Zi Wei archetypes and a deterministic fusion-title matrix with BaZi archetypes.
- [ ] Add global and same-life-star-combination cohort rankings.
- [ ] Build five deterministic theme K-line series from monthly iztro horoscope states.
- [ ] Add compact Zi Wei consumer baseline histograms and representative structural families.
- [ ] Keep raw chart generation and period switching non-blocking if consumer statistics fail.

### Task 6: Consumer result UI, export, and sharing

**Files:**
- Create: `frontend/src/components/tools/consumer-identity.tsx`
- Create: `frontend/src/components/tools/life-kline-chart.tsx`
- Create: `frontend/src/components/tools/metaphysics-achievements.tsx`
- Modify: `frontend/src/components/tools/bazi-chart-view.tsx`
- Modify: `frontend/src/components/tools/ziwei-chart-view.tsx`
- Modify: `frontend/src/components/tools/metaphysics-tools.tsx`
- Modify: `frontend/src/lib/chart-markdown.ts`
- Modify: `frontend/src/app/globals.css`

**Interfaces:**
- Shared identity component consumes system-specific profiles through one normalized prop contract.
- Shared SVG K-line consumes `LifeKlineSeries`, supports five series, zoom window, crosshair/tap detail, moving averages, period bands, peaks/troughs, and responsive fallback.

- [ ] Replace `simple/study/professional` as primary navigation with `我是谁|人生 K 线|完整命盘` while keeping professional detail in the full-chart view.
- [ ] Render identity title, total score, global/cohort top percentages, four subject cards, five fingerprints, and achievement rarity/status.
- [ ] Render deterministic candlesticks, moving averages, volume, current year, period bands, top-three stages, and twelve-month detail.
- [ ] Add structural-twin and share-card sections; expose the existing comparison entry point without creating billing UI.
- [ ] Update PNG/Markdown export to lead with identity/ranking/K-line summaries.
- [ ] Ensure all result controls have accessible names and mobile-safe internal scrolling.

### Task 7: Persistence, polish, review, and release handoff

**Files:**
- Modify: `frontend/src/components/tools/metaphysics-tools.tsx`
- Modify: `frontend/src/lib/chart-markdown.ts`
- Modify: `tests/test_shensha.py`
- Modify: `tests/test_frontend_premium_contract.py`
- Modify: `frontend/e2e/public-routes.spec.ts`

**Interfaces:**
- Local and Supabase snapshots preserve V3 consumer payloads; older snapshots recalculate when normalized inputs are available.

- [ ] Upgrade snapshot compatibility from schema 5 to 6 and keep old raw snapshots readable.
- [ ] Preserve restart/new-chart behavior, local restore, Supabase save/reopen, and exports.
- [ ] Run focused Python tests, frontend lint/build, and one browser smoke pass on desktop/mobile.
- [ ] Perform a whole-branch code/design review and fix critical/important findings.
- [ ] Commit the branch and report all seven deliverables; do not merge without a new explicit instruction.
