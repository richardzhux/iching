# I Ching Studio: Founder-Facing Product Execution Memo

This memo is grounded in what is already implemented in this repository and framed the way startup founders evaluate product leaders: ship velocity, measurement discipline, outcome ownership, and go-to-market clarity.

## Product Analytics (Amplitude/Mixpanel/GA4) — I ship + measure

### Current truth in this codebase
- No client analytics SDK is wired yet (no existing Amplitude/Mixpanel/GA4 instrumentation in frontend code).
- The backend already captures analytics-grade behavioral and cost data in Supabase:
  - `sessions`: `session_id`, `user_id`, `ai_model`, `followup_model`, `chat_turns`, `tokens_used`, `summary_text`, `payload_snapshot`, timestamps.
  - `chat_messages`: `role`, `tokens_in`, `tokens_out`, `model`, `reasoning`, `verbosity`, `tone`, timestamps.
- Product journey is already expressed as stable API boundaries:
  - `POST /api/sessions` -> reading created
  - `POST /api/sessions/{session_id}/chat` -> follow-up used
  - `GET /api/sessions` -> cloud history behavior
  - `DELETE /api/sessions/{session_id}` -> churn/cleanup signal

### Ship plan (first 7-10 days)
- Implement one canonical event schema and mirror it to Amplitude, Mixpanel, and GA4.
- Standardize identity:
  - anonymous browser ID pre-login
  - alias/merge to Supabase `user_id` after auth
- Event contract:
  - `reading_created` with `topic`, `method_key`, `locale`, `ai_enabled`, `ai_model`
  - `followup_sent` and `followup_completed` with `model`, `reasoning`, `verbosity`, `tone`, `latency_ms`, `tokens_total`
  - `session_opened_from_history`, `session_exported`, `session_deleted`
- Dashboard pack:
  - activation funnel: config loaded -> reading created -> first follow-up -> second follow-up
  - retention and reopen behavior by cohort
  - token economics by model/reasoning profile

### Founder takeaway
- Architecture is already measurement-ready.
- This is an instrumentation-and-dashboard sprint, not a platform rewrite.

## PRDs & User Stories — basic PM muscle, very ATS-friendly

### PRD example (realistically shippable from current architecture)

#### Title
- Increase follow-up activation after first reading

#### Problem
- The product delivers first value (reading output), but the sticky value loop is follow-up conversation on the same session context.

#### Objective
- Increase `% of sessions with >=1 successful follow-up` while protecting latency and token efficiency.

#### Non-goals
- No new casting methods
- No interpretation corpus expansion
- No new external data providers

#### User stories
- As a first-time user, I want a clear next action after seeing my reading so I can continue decision-making immediately.
- As a returning user, I want to reopen old sessions and continue from context without recasting.
- As an operator, I want guardrails on token usage while preserving answer quality.

#### Requirements
- Add first-follow-up prompt chips under initial AI output.
- Preserve session-level chat controls (model/reasoning/verbosity/tone) across follow-ups.
- Track activation outcomes with event-level observability.

#### Acceptance criteria
- Signed-in user can generate a reading and send first follow-up in <=2 clicks from results view.
- Reopened sessions with valid snapshot can follow up successfully without recasting.
- Activation metric is queryable by date, locale, model, and topic in analytics.

### Founder takeaway
- The PRD is directly tied to existing components, API routes, and data schema, so execution risk is controlled.

## OKRs / Metrics — shows you think in outcomes

### Objective 1: Improve activation quality
- KR1: Increase `reading -> first follow-up conversion` by 30% from baseline.
- KR2: Keep follow-up API error rate under 2%.
- KR3: Keep median first-follow-up latency under 8 seconds for default model.

### Objective 2: Improve retained engagement
- KR1: Increase `% of users with >=2 sessions in trailing 7 days` by 20%.
- KR2: Increase `% of sessions reopened from cloud history` by 25%.
- KR3: Keep `% of sessions deleted within 10 minutes` below 10%.

### Objective 3: Improve unit economics without sacrificing utility
- KR1: Reduce median tokens per successful follow-up by 15%.
- KR2: Increase intentional control usage (non-default model/reasoning/verbosity) to 40%.

### Metric definitions mapped to current schema
- `Session Created`: upsert into `public.sessions`
- `Follow-up Completed`: assistant row in `public.chat_messages` for same `session_id`
- `Activation`: at least one user+assistant follow-up pair
- `Retention Proxy`: repeated sessions by same `user_id` in trailing window
- `Cost`: `tokens_in + tokens_out` and session-level `tokens_used`

### Founder takeaway
- The OKRs connect behavior, retention, and cost, so product decisions are tied to business outcomes.

## GTM / Positioning — better than “Content Strategy” for product roles

### Positioning statement
- For founders/operators facing ambiguous, high-stakes decisions, I Ching Studio is an evidence-linked decision workflow that combines classical interpretation, structured outputs, and controllable AI follow-up in one persistent session thread.

### Why this positioning is credible now
- Deterministic interpretation assembly (slot-based, source-aware) instead of pure prompt improvisation.
- Follow-up chat continues the same session context, not disconnected one-off prompts.
- Cloud history supports cross-device continuation, export, and revisit behavior.
- Bilingual UX (`/en`, `/zh`) supports broader acquisition from day one.

### ICP and wedge
- Primary ICP: startup founders, operators, and knowledge workers who need structured reflection for repeat decisions.
- Beachhead workflow: setup -> reading -> follow-up -> reopen/export.

### GTM motion (pragmatic)
- Acquisition: founder-led content using concrete decision walkthroughs, not generic astrology content.
- Activation: prompt immediate follow-up question after first reading.
- Retention: reopen prior sessions and continue unresolved threads.
- Expansion: team/shared workflows once single-user behavior stabilizes.

### Founder takeaway
- Positioning is rooted in actual product behavior visible in this repo, not marketing abstraction.

## Experiment Design (grown-up A/B testing)

### Experiment operating standard
- Every experiment is pre-registered with:
  - hypothesis
  - primary metric
  - guardrail metrics
  - target segment
  - minimum runtime and decision threshold
  - rollback condition
- Statistical discipline:
  - two-sided tests for conversion metrics
  - predefined success threshold before launch

### Experiment 1: Follow-up prompt chips
- Hypothesis: suggested prompts increase first-follow-up conversion.
- Primary metric: `% of sessions with >=1 follow-up within 10 minutes`.
- Guardrails: error rate, median latency, token usage, delete rate.
- Ship rule: launch if relative lift >=10% with no meaningful guardrail regression.

### Experiment 2: Default chat model policy
- Hypothesis: defaulting first follow-up to `gpt-5-mini` improves speed while preserving continuation behavior.
- Primary metric: follow-up completion rate.
- Guardrails: latency, second-follow-up rate, token cost.
- Ship rule: keep if completion is neutral/up and latency meaningfully improves.

### Experiment 3: Results tab sequencing
- Hypothesis: defaulting post-read view to AI chat increases activation vs summary-first.
- Primary metric: `reading -> first follow-up conversion`.
- Guardrails: summary engagement and churn proxies.
- Ship rule: keep only if activation lift survives guardrails.

### Founder takeaway
- This is a decision system, not ad hoc A/B testing.
- Experiments are tied to product controls already implemented and measurable now.

## Repo evidence used
- `README.md`
- `docs/supabase-schema.sql`
- `src/iching/web/api/routes.py`
- `src/iching/web/chat_service.py`
- `src/iching/web/service.py`
- `frontend/src/components/workspace/cast-form.tsx`
- `frontend/src/components/workspace/chat-panel.tsx`
- `frontend/src/components/profile/profile-page.tsx`
- `frontend/src/lib/api.ts`
- `tests/test_api.py`
- `tests/test_session_service.py`
- `tests/test_interpretation_repository.py`
