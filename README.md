# I Ching Studio

I Ching Studio is a modern I Ching decision platform that combines classical divination, structured textual interpretation, and AI-assisted follow-up into one production-oriented product stack.

It is built for serious, repeatable analysis: users can cast readings, inspect line-level evidence, continue multi-turn AI discussion, and persist full history across devices.

## Product Snapshot

- **Core value proposition**: trustworthy, evidence-linked I Ching analysis instead of generic chatbot-style ambiguity.
- **Delivery model**: web app (`Next.js 16`) + API platform (`FastAPI`) + structured interpretation data layer (`SQLite + Supabase history`).
- **Current readiness**: live-capable architecture with auth, quotas, history persistence, multilingual UI, and deterministic interpretation assembly.

## Delivered Priorities (Current)

These are the exact priorities that were deliberately planned and are now implemented:

1. **Model upgrade across product surfaces**
- `gpt-5.6-terra` is the default model for initial interpretation and follow-up.
- `gpt-5.6-sol` is the deep-analysis option.
- Both GPT-5.6 profiles expose `none`, `low`, `medium`, `high`, `xhigh`, and `max` reasoning; verbosity defaults to `medium`.
- Legacy mini model names normalize to Terra, while GPT-5.5, GPT-5.3 Codex, and GPT-4.1 remain available.

2. **Streaming follow-up chat**
- Assistant text streams incrementally over SSE and persists only after completion.
- Chat supports stop, copy, edit, regenerate, model switching, and capability-aware controls.
- GPT-5.6 responses use persisted `all_turns` reasoning context while the response chain remains on the same model; switching models rebuilds context from the fixed cast and recent transcript.

3. **Bilingual, one-tap language UX**
- Added locale routing and language switching (`/en`, `/zh`) with one-button toggling.
- Updated homepage copy to keep Chinese and English messaging aligned and vivid.

4. **Interpretation data platform upgrade**
- Migrated interpretation retrieval to a slot-based SQL architecture.
- Integrated Takashima content at the **line slot level** (not merely as an author-level appendix).
- Kept `用九` / `用六` handling intact for 乾/坤 full-moving conditions.

5. **Historical data consistency**
- Added retroactive backfill tooling so existing Supabase sessions can be upgraded to the new interpretation structure.

6. **Metaphysics tools**
- Added current Chinese-calendar facts, exact solar-term countdown, month command, day branch, void branches, clashes/combinations, and six-spirit starting order.
- Added solar/lunar BaZi charting with historical timezone/DST behavior, true-solar-time correction, explicit late-Zi-hour rules, uncertain-hour candidates, selectable Da Yun start rules, and `sxtwl`/`lunar_python` cross-checking.
- Added Zi Wei Dou Shu charting with the pinned MIT-licensed `iztro` engine, solar/lunar input, leap-month handling, standard/Zhongzhou schools, heaven/earth/human chart modes, four transformations, and decadal/annual periods.

## Why This Product Is Defensible

- **Deterministic interpretation engine**: results are assembled by explicit hexagram/line/use slots instead of ad-hoc prompt-only generation.
- **Evidence-first AI flow**: AI reasoning is anchored to structured session payloads (hexagram, lines, Najia, BaZi, classical text sections).
- **Compounding data asset**: interpretation entries are normalized and versionable, enabling future multi-author expansion without architecture rewrite.
- **Cross-device continuity**: cloud session persistence and follow-up chat state provide product stickiness.

## Core User Functions (Prioritized)

1. **Cast and interpret**
- Multiple casting methods with timestamp controls and manual line input validation.
- Output includes summary, hexagram sections, Najia table, and AI analysis.

2. **Model-controlled AI analysis**
- User-selectable model and effort controls when supported by capability matrix.
- Tone modes (`normal`, `wenyan`, `modern`, `academic`) for output style consistency.

3. **Follow-up AI chat on same reading**
- Chat continues from the original reading context (same session narrative).
- Supports model switching in chat with quota enforcement.

4. **Cloud history and session lifecycle**
- Supabase-backed session listing, reopen, follow-up, export, and delete.
- Local fallback history for signed-out usage.

5. **Bilingual operation**
- Locale-specific routes and content for both Chinese and English users.

## AI Model Strategy (Current)

Defined in `src/iching/integrations/ai.py` (`MODEL_CAPABILITIES`):

| Model | Reasoning options | Verbosity control | Default reasoning | Default verbosity |
| --- | --- | --- | --- | --- |
| `gpt-5.6-terra` | `none`, `low`, `medium`, `high`, `xhigh`, `max` | yes | `medium` | `medium` |
| `gpt-5.6-sol` | `none`, `low`, `medium`, `high`, `xhigh`, `max` | yes | `high` | `medium` |
| `gpt-5.5` | `none`, `low`, `medium`, `high`, `xhigh` | yes | `medium` | `medium` |
| `gpt-5.3-codex` | `minimal`, `low`, `medium`, `high` | yes | `medium` | `medium` |
| `gpt-4.1` | none | no | n/a | n/a |

Compatibility:
- `MODEL_ALIASES` maps `gpt-5.1` and `gpt-5.2` to GPT-5.5, legacy mini names to Terra, and `gpt-5.6` to Sol.

## Interpretation Knowledge Architecture (SQL)

The platform now uses a normalized, slot-based interpretation system:

- 64 hexagrams x 1 gua slot = 64
- 64 hexagrams x 6 line slots = 384
- `用九` + `用六` slots = 2
- Total = **450 canonical interpretation slots**

Example slot keys:
- `1.gua`
- `1.line.1`
- `1.use.yong_jiu`

Schema entities (in `src/iching/integrations/interpretation_repository.py`):
- `interpretation_trigram`
- `interpretation_hexagram`
- `interpretation_slot`
- `interpretation_source`
- `interpretation_entry`

Production constraints include:
- Strict slot kind validation (`gua`, `line`, `use`)
- `line_no` only valid for `line`
- `use_kind` only valid for `use`
- `use` entries restricted to 乾(`yong_jiu`) and 坤(`yong_liu`)

Ordering guarantee:
- `gua` -> `line` (`line_no ASC`, bottom-to-top) -> `use`, then source priority.

## Data Sources and Content Pipeline

Tracked source assets:
- `data/guaci/` (64 structured files)
- `data/takashima_structured/` (64 structured files)
- `data/takashima/` (raw corpus)
- `data/guaxiang.txt`
- `data/najia.db`

Generated artifact:
- `data/interpretations.db` (intentionally ignored in Git)

Build/update scripts:

```bash
# regenerate structured Takashima files (if raw source changed)
python tools/prepare_takashima.py \
  --source-dir data/takashima \
  --guaci-dir data/guaci \
  --output-dir data/takashima_structured

# sync SQL interpretation DB from source folders
python tools/sync_interpretation_db.py
```

Expected counts with current corpus:
- Slots: `450`
- Guaci entries: `450`
- Takashima entries: `450`

## Supabase Persistence and Retroactive Backfill

Core cloud tables (see `docs/supabase-schema.sql`):
- `public.sessions`
- `public.chat_messages`

Backfill tool for historical sessions:

```bash
# dry-run sample (default; performs no writes)
python tools/backfill_session_interpretations.py --limit 100

# dry-run for specific sessions
python tools/backfill_session_interpretations.py --session-ids "uuid-a,uuid-b"

# apply the deterministic repair globally (service key scope)
python tools/backfill_session_interpretations.py --apply

# apply only selected sessions
python tools/backfill_session_interpretations.py --apply --session-ids "uuid-a,uuid-b"
```

Operational note:
- Unfiltered `--apply` with service-role credentials can update all users’ session snapshots in the project.
- The command reports concise per-row skip/failure reasons to stderr and prints aggregate JSON statistics to stdout.
- Writes are scoped by `(session_id, user_id)` and guarded by the row's original `updated_at`; concurrent changes are skipped, and the repair does not modify `updated_at`.
- The repair is idempotent and derives Najia fields and six gods only from each snapshot's saved lines and `current_time_str`. Missing or invalid inputs skip the whole snapshot.
- Historical yarrow and other casts are never rerolled. Saved lines, AI prose/IDs/usage, reading briefs, full text, user context, chats, and unrelated snapshot keys are preserved.
- Supabase session retention is `365 days`; deleting or purging a session cascades to its `chat_messages`.

## System Architecture

### Frontend
- `frontend/` (Next.js 16 App Router, TypeScript)
- Locale middleware and localized routes (`/en`, `/zh`)
- Workspace for casting + results + follow-up chat
- Profile surface for auth and cloud history

### Backend
- `src/iching/web/api` (FastAPI routes and DTOs)
- `SessionRunner` + `SessionService` as orchestration core
- AI integration with model capability enforcement
- Rate limiting and access password gate for AI usage

### Data Layer
- Najia lookup: `data/najia.db`
- Interpretation retrieval: `data/interpretations.db` (generated)
- Supabase for auth/session/chat persistence

## API Surface

Primary endpoints:
- `GET /api/health`
- `GET /api/config`
- `POST /api/sessions`
- `GET /api/sessions`
- `DELETE /api/sessions/{session_id}`
- `GET /api/sessions/{session_id}/chat`
- `POST /api/sessions/{session_id}/chat`
- `POST /api/sessions/{session_id}/chat/stream`
- `POST /api/tools/metaphysics`

## Local Development

### Prerequisites
- Python 3.11+
- Node.js 20+
- npm

### Backend Setup

```bash
pip install -r requirements.txt
pip install -e .

export ICHING_ALLOWED_ORIGINS=http://localhost:3000
uvicorn iching.web.api.main:app --reload
```

### Frontend Setup

```bash
cd frontend
npm install
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 npm run dev
```

Open: `http://localhost:3000`

## Environment Variables

### Backend (AI + Auth)
- `OPENAI_API_KEY`
- `OPENAI_PW`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`

### Backend (Key operational controls)
- `ICHING_CHAT_MODEL` (default `gpt-5.6-terra`)
- `ICHING_CHAT_TURN_LIMIT` (default `10`)
- `ICHING_CHAT_TOKEN_LIMIT` (default `150000`)
- `ICHING_CHAT_MESSAGE_LIMIT` (default `10000`)
- `ICHING_USER_DAILY_TOKEN_LIMIT` (default `300000`)
- `ICHING_USER_SESSION_LIMIT` (default `500`)
- `ICHING_SESSION_CACHE_LIMIT` (default `100`)
- `ICHING_SESSION_CACHE_TTL_SECONDS` (default `21600`)
- `ICHING_INTERPRETATION_DB` (default `data/interpretations.db`)

### Frontend
- `NEXT_PUBLIC_API_BASE_URL`
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`

## Deployment Footprint

- **Frontend**: Vercel (reads from `main`)
- **Backend**: Render (FastAPI service)
- **Database/Auth**: Supabase

Recommended production checks:
1. Frontend `NEXT_PUBLIC_API_BASE_URL` points to active backend URL.
2. Backend CORS (`ICHING_ALLOWED_ORIGINS`) includes frontend origin.
3. Supabase and OpenAI secrets are set on backend environment.

## Quality and Verification

Backend test baseline:

```bash
pytest -q
```

Frontend quality gates:

```bash
cd frontend
npm run lint
npm run build
```

## Repository Layout

```text
.
├── data/
├── docs/
├── frontend/
├── src/iching/
├── tests/
└── tools/
```

## References

- `docs/deployment.md`
- `docs/frontend-roadmap.md`
- `docs/supabase-schema.sql`
