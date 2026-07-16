# BaZi Classics Consumer OS Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Each milestone has one implementer, one independent review gate, one commit, and one push.

**Goal:** Build a source-traceable Zi Ping rule engine and turn its results, statistical baselines, and period activations into the clearest and most compelling consumer BaZi product in the market.

**Architecture:** A single `BaziFactGraph` records chart facts; versioned classical rule bundles decide patterns and formation paths; a `ConsumerClaim` compiler turns verified rule results into identity, expression paths, signatures, rare combinations, and activation windows; statistics only describe incidence or direction, while life K-lines compare each user with their own long-term baseline. Shen Xiaozhan's core, Xu Lewu's commentary, and *Yuanhai Ziping* remain independent layers.

**Tech Stack:** Python 3.10+, FastAPI, Pydantic, sxtwl, lunar-python, JSON/JSONL rule bundles, SQLite task ledger, Next.js 16, React 19, TypeScript, Tailwind CSS, SVG, Supabase JSONB snapshots.

## Global Constraints

- Work only on `codex/july-15th-experimental`; do not create another branch or worktree and do not modify or merge `main`.
- Push one reviewed commit after each completed milestone.
- Keep the entire repository below 2 GB. Use 1.85 GB as the soft stop; raw scans, OCR, ledgers, and logs live under ignored `references/` or `.cache/classics/`; logs rotate at 10 MB and retain at most five files.
- Do not persist chain-of-thought, repeated OCR, page images, temporary diffs, or per-run test logs in Git.
- Do not add Stripe, billing UI, Supabase tables, public data, or environment variables.
- Never equate rarity with quality. Remove destiny, career-quality, wealth-quality, relationship-quality, and health scores from the active contract.
- Consumer numbers must name exactly what they measure: incidence, directional position, personal-period index, or structural distinctiveness.
- The default consumer surface is `我是谁 | 人生 K 线 | 完整命盘`; engineering metadata and source disputes stay behind `查看依据`.
- Preserve existing private persistence, export, old snapshot readability, and deterministic output.
- Use targeted tests per milestone; run broad suites only at integration gates.

## Model and Reasoning Routing

- **Luna + low reasoning:** OCR cleanup, headers/footers, page segmentation, duplicate detection, schema-valid formatting.
- **Luna + medium reasoning:** character-level OCR disagreement triage that does not change rule meaning.
- **Terra + high reasoning:** proposition extraction, example structure, first-pass AST, ConsumerClaim drafting, deterministic data transforms.
- **Sol + xhigh reasoning:** source conflicts, rule exceptions, damage/rescue binding, cross-chapter arbitration, adversarial review, architecture review.
- **Sol + max reasoning:** only disputes that remain unresolved after two independent passes; never for bulk extraction.
- Built-in Codex subagents do not expose a model-selection parameter. They are limited to scoped implementation/review roles; any future external corpus runner must persist the explicit model and reasoning setting above in each work item. No paid Batch/API corpus run is launched implicitly.
- Working budget target: Luna 50%, Terra 32%, Sol 18% of the approximately 1.5B-token ceiling. Completion gates, not token exhaustion, end the Goal.

---

### Task 1: Mission Preflight and Product-Safety Contract

**Files:**
- Create: `scripts/check_workspace_budget.py`
- Modify: `.gitignore`
- Modify: `src/iching/core/metaphysics_consumer.py`
- Modify: `frontend/src/types/api.ts`
- Test: `tests/test_metaphysics_consumer_baseline.py`

**Interfaces:**
- Produces `check_workspace_budget(root, soft_bytes, hard_bytes) -> WorkspaceBudgetResult`.
- Deprecates active `main_score`, `subjects[].score`, `raw_score`, and score-derived global/cohort rank generation while keeping old snapshots readable.
- Keeps K-line personal baseline semantics but stops feeding it artificial natal quality scores.

- [ ] Add an ignored classics cache and a deterministic repository-size guard with 1.85 GB soft and 2 GB hard thresholds.
- [ ] Remove `_theme_score`, `score_bazi_consumer_themes`, `_PATTERN_THEME_BONUS`, and the 43-point/28–98 scoring path from live profile generation.
- [ ] Replace score-bearing subject payloads with descriptive path fields and optional directional/incidence metadata.
- [ ] Preserve legacy optional TypeScript fields only for rendering old snapshots; new builders must not populate them.
- [ ] Add focused assertions that no new chart returns naked life-quality scores and that hidden wealth is described as an expression path, not poverty.
- [ ] Run the focused Python contract tests and commit `refactor: remove life quality scores and guard workspace budget`.

### Task 2: Source Freeze and Vertical Corpus Slice

**Files:**
- Create: `research/classics/sources/manifest.json`
- Create: `research/classics/ziping_zhenquan/manifest.json`
- Create: `research/classics/ziping_zhenquan/segments/zzq.useful-god.success-failure-rescue.jsonl`
- Create: `research/classics/ziping_zhenquan/segments/zzq.pattern.direct-officer.jsonl`
- Create: matching proposition, rule, and example shards under `research/classics/ziping_zhenquan/`
- Test: `tests/bazi_rules/test_source_manifest.py`

**Interfaces:**
- `SourceWitness` separates textual authority, provenance, rights, completeness, role, and witness relation.
- `SourceLocator` records witness, scan page, printed page, column/line or bbox, short quote, quote hash, and URL.
- `Proposition` records layer, text type, explicit/inferred conditions, exceptions, source segments, and review status.

- [ ] Download the public-domain *Gengcun Ji*, the 1926 Qin Shen'an volume-two operational witness, and the independent World Library witness into ignored `references/classics/raw/` and record SHA-256 values.
- [ ] Treat 8bei8, Dongli, CText, Wikisource, and unlicensed GitHub mirrors as search aids only; no production rule may depend solely on them.
- [ ] Preserve diplomatic traditional text separately from normalized search text; OpenCC output never overwrites the witness text.
- [ ] Complete two end-to-end chapters: `论用神成败救应` and `论正官`, including original text, commentary boundary, atomic propositions, examples, and non-rule classification.
- [ ] Visually verify every quote used by a production proposition against a scan.
- [ ] Run source-manifest validation and commit `data: establish ziping vertical source corpus`.

### Task 3: Fact Graph, Rule Schema, and Deterministic Compiler

**Files:**
- Create: `src/iching/core/bazi_rules/primitives.py`
- Create: `src/iching/core/bazi_rules/schema.py`
- Create: `src/iching/core/bazi_rules/fact_graph.py`
- Create: `src/iching/core/bazi_rules/predicates.py`
- Create: `src/iching/core/bazi_rules/compiler.py`
- Test: `tests/bazi_rules/test_fact_graph.py`
- Test: `tests/bazi_rules/test_rule_compiler.py`

**Interfaces:**

```python
TruthValue = Literal["true", "false", "unknown"]

def build_bazi_fact_graph(
    pillars: Iterable[Mapping[str, Any]],
    *,
    hour_uncertain: bool = False,
) -> BaziFactGraph: ...

def compile_rule_bundle(
    definitions: Sequence[RuleDefinition],
    propositions: Mapping[str, Proposition],
) -> CompiledRuleBundle: ...
```

- [ ] Centralize stems, branches, hidden stems, elements, ten gods, and relation primitives without changing existing public imports.
- [ ] Record explicit pillar positions, month qi levels, exposed/hidden occurrences, roots, relations, complete combinations, and input completeness without pattern judgment.
- [ ] Implement three-valued predicates: `all`, `any`, `not`, `fact_equals`, `fact_in`, `exists_occurrence`, `count_compare`, `relation_exists`, `root_exists`, `month_command_equals`, `god_exposed`, `combination_complete`.
- [ ] Reject source-less production rules, invalid locators/hashes, duplicate IDs, unknown operators, cycles, and unresolved precedence.
- [ ] Prove two compilations produce the same digest and commit `feat: add source-backed bazi rule compiler`.

### Task 4: Pattern Lifecycle Engine and Direct-Officer Slice

**Files:**
- Create: `src/iching/core/bazi_rules/engine.py`
- Create: `src/iching/core/bazi_rules/registry.py`
- Create: `src/iching/core/bazi_rules/adapter.py`
- Create: `src/iching/core/bazi_rules/bundles/zzq-shen-canonical-v1.json`
- Modify: `src/iching/core/bazi_patterns.py`
- Modify: `src/iching/core/metaphysics.py`
- Test: `tests/bazi_rules/test_engine_lifecycle.py`
- Test: `tests/bazi_rules/test_zzq_vertical_slice.py`

**Interfaces:**
- Executes `candidate -> formation -> damage -> rescue -> purity -> transformation -> special_gate -> resolution`.
- Returns `formed | broken | rescued | mixed | transformed | candidate | rejected | undetermined | ambiguous`.
- Preserves `assess_patterns(pillars, structure) -> dict` through an adapter.

- [ ] Bind each damage to a specific formation path and accept rescue only when it resolves that actual damage.
- [ ] Encode direct-officer candidate, wealth/resource formation paths, hurting-officer damage, resource rescue, officer/killing mixing, and explicit conflicts from the reviewed propositions.
- [ ] Remove list-order fallbacks and artificial effectiveness/share thresholds from the new path.
- [ ] Build the fact graph once per chart and share it with structure and pattern evaluation.
- [ ] Shadow the new result beside the legacy result, classify every focused difference, and commit `feat: compile direct-officer lifecycle from ziping sources`.

### Task 5: Complete Classical Bundles and Overlays

**Files:**
- Extend: `research/classics/ziping_zhenquan/`
- Extend: `src/iching/core/bazi_rules/bundles/zzq-shen-canonical-v1.json`
- Create: `src/iching/core/bazi_rules/bundles/zzq-xu-commentary-v1.json`
- Create: `src/iching/core/bazi_rules/bundles/yuanhai-ziping-v1.json`
- Test: `tests/bazi_rules/test_classical_examples.py`

**Interfaces:**
- Shen core is the only default authority.
- Xu and *Yuanhai* remain separately loadable overlays; only scan-verified propositions with complete operational predicates may become executable relations, and neither can silently overwrite the default result.
- **Reviewed scope correction (2026-07-16):** the first *Yuanhai* tranche is a source-bound, zero-executable overlay. Weak/follow, education, and life/death passages are preserved as non-predictive source records until a complete formation/damage/rescue predicate can be justified. This is an intentional fail-closed milestone, not a completed *Yuanhai* doctrine engine.

- [ ] Expand the Shen bundle through seven killings, wealth, resource, output, month prosperity/robbery, yang blade, and strict special patterns.
- [ ] Give every rule a positive case, missing-condition case, damage case, rescue case where applicable, precedence case, and traceable proposition.
- [ ] Compile Xu commentary only where a dated witness can be verified; exclude later annotations and unresolved attribution.
- [x] Compile the first *Yuanhai* source tranche for month command, ordinary patterns, weak/follow structures, education/achievement passages, and pattern life/death concepts from scan-verified text; bind it as zero-executable until operational predicates are source-complete.
- [ ] Preserve author claims separately from current engine expectations in classical examples.
- [ ] Commit `feat: complete independent ziping classical rule layers`.

### Task 6: ConsumerClaim Compiler

**Files:**
- Create: `src/iching/core/consumer_claims.py`
- Modify: `src/iching/core/metaphysics_consumer.py`
- Modify: `frontend/src/types/api.ts`
- Test: `tests/test_consumer_claims.py`

**Interfaces:**

```ts
type ConsumerClaim = {
  id: string
  slot: "hero" | "theme" | "signature" | "combination" | "timeline"
  theme?: "career" | "wealth" | "relationship" | "rhythm"
  title: string
  summary: string
  importance: "foundation" | "primary" | "major" | "supporting" | "auxiliary"
  classicalRole: "pattern" | "formation_path" | "damage" | "rescue" | "expression" | "supporting_marker"
  direction?: DirectionMetric
  comparison?: ComparisonMetric
  activation?: ActivationWindow
  evidenceIds: string[]
  ruleIds: string[]
  sourceIds: string[]
}
```

- [ ] Generate exactly one pattern identity, four expression paths, three-to-five non-duplicate signature structures, zero-to-four meaningful combinations, and three future windows for a complete chart.
- [ ] Order by classical importance first and statistical distinctiveness second; a rare single ShenSha cannot outrank the month-command pattern.
- [ ] Replace headline keyword guessing with stable backend `path_id` and claim IDs.
- [ ] Rename achievements to rare structure combinations; single ordinary ShenSha stays in the full chart.
- [ ] Return concise consumer copy first and source/evidence IDs for progressive disclosure.
- [ ] Commit `feat: compile chart facts into consumer claims`.

### Task 7: Statistical Semantics and Personal Life K-Line

**Files:**
- Modify: `src/iching/core/metaphysics_statistics.py`
- Modify: `src/iching/core/metaphysics_consumer.py`
- Modify: `scripts/generate_bazi_baseline.py`
- Modify: `frontend/src/components/tools/life-kline-chart.tsx`
- Test: `tests/test_metaphysics_statistics.py`
- Test: `tests/test_life_kline.py`

**Interfaces:**
- Binary features display incidence.
- Ordered features display an upper/lower tail only when resolution supports it.
- Bipolar metrics translate low percentiles into the opposite semantic direction.
- K-line values are relative to the user's own long-term baseline of 100 and never compare life quality between users.

- [ ] Stop displaying exact-tie percentage as the default comparison; use tail probability for ordered metrics.
- [ ] Suppress precise rankings when same-mass exceeds 25%; use broad directional copy for 10–25% and exact `前约 X%` only below 10%.
- [ ] Remove default overall K-line and retain career, wealth, relationship, and rhythm series.
- [ ] Compute monthly activation from natal path + Da Yun + year + month + new formations/damage/rescue, with real deterministic OHLC and named drivers.
- [ ] Put three key windows before the chart; default to a simple trend, with professional candlesticks one action away.
- [ ] Add the pattern bundle digest to the statistical registry and generate g4 baselines only after the bundle freezes.
- [ ] Commit `feat: align statistics and kline with consumer semantics`.

### Task 8: Consumer Result Experience

**Files:**
- Modify: `frontend/src/components/tools/consumer-identity.tsx`
- Modify: `frontend/src/components/tools/metaphysics-achievements.tsx`
- Modify: `frontend/src/components/tools/bazi-chart-view.tsx`
- Modify: `frontend/src/lib/chart-markdown.ts`
- Modify: `frontend/src/app/globals.css`
- Test: `tests/test_frontend_premium_contract.py`

**Interfaces:**
- `我是谁`: identity hero, four paths, five signatures, rare combinations, twelve-month preview.
- `人生 K 线`: three windows, simple trend, professional K-line, year/month driver drawer.
- `完整命盘`: four-pillar table, pattern decision tree, complete evidence, periods, statistics, ShenSha, and classical sources.

- [ ] Render pattern title, formation path, status, one memorable sentence, and three compact tags in the hero.
- [ ] Add one relative-position or incidence highlight and next activation to each theme path.
- [ ] Show the pattern decision tree with fact -> rule -> proposition -> scan progression.
- [ ] Merge exports under one share menu for identity, rare combination, future window, and full report.
- [ ] Keep tables internally scrollable and eliminate page-level overflow at 390 px.
- [ ] Commit `feat: deliver the bazi consumer operating system`.

### Task 9: Snapshot V7, Integration, and Production Handoff

**Files:**
- Modify: `src/iching/web/models.py`
- Modify: `src/iching/web/api/routes.py`
- Modify: `frontend/src/components/tools/metaphysics-tools.tsx`
- Modify: `tests/test_chart_archive.py`
- Modify: `tests/test_api.py`

**Interfaces:**
- Adds `rule_versions = {calendar, pattern_bundle, pattern_digest, shensha, consumer}`.
- Adds `GET /api/tools/metaphysics/pattern-rules/{bundle_id}/{rule_id}`.
- Reads schema 6 snapshots unchanged; only explicit recalculation writes schema 7.

- [ ] Include rule bundle digest in live charts, saved snapshots, exports, and statistical compatibility checks.
- [ ] Return source-backed rule summaries on demand without embedding the corpus or full trace in each snapshot.
- [ ] Ensure statistics/version failure degrades only statistics, not pillars, pattern, periods, or saved-chart loading.
- [ ] Classify every legacy/new shadow difference and close all P0/P1 findings.
- [ ] Run focused Python integration, frontend lint/build, desktop/mobile browser smoke, and repository-size guard.
- [ ] Perform a whole-branch source/rule/product review, commit `chore: finalize bazi classical consumer os`, and push the branch without merging.

## Completion Gates

The Goal is complete only when all are true:

```text
source_pages_terminal == source_pages_total
rule_segments_terminal == rule_segments_total
production_rules_without_source == 0
production_quotes_unverified == 0
parseable_examples_without_fixture == 0
naked_life_scores == 0
feature_ranks_without_semantic_direction == 0
single_shensha_as_primary_identity == 0
shadow_diffs_unclassified == 0
workspace_bytes < 2_000_000_000
p0_open == 0
p1_open == 0
integration_checks_passed == true
```
