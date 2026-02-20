# I Ching Studio

I Ching Studio is a modern I Ching decision platform that combines classical divination, structured textual interpretation, and AI-assisted follow-up into one production-oriented product stack.

It is built for serious, repeatable analysis: users can cast readings, inspect line-level evidence, continue multi-turn AI discussion, and persist full history across devices.

## Product Snapshot

- **Core value proposition**: trustworthy, evidence-linked I Ching analysis instead of generic chatbot-style ambiguity.
- **Delivery model**: web app (`Next.js 16`) + API platform (`FastAPI`) + structured interpretation data layer (`SQLite + Supabase history`).
- **Current readiness**: live-capable architecture with auth, quotas, history persistence, multilingual UI, and deterministic interpretation assembly.

## Delivered Priorities (This Cycle)

These are the exact priorities that were deliberately planned and are now implemented:

1. **Model upgrade across product surfaces**
- Replaced `gpt-5.1` with `gpt-5.2` in the primary model flow.
- Maintained backward compatibility via alias mapping (`gpt-5.1 -> gpt-5.2`).
- Preserved the same reasoning/verbosity behavior profile expected from the prior 5.1 setup.

2. **Chat model expansion**
- Added `gpt-4.1` in follow-up chat alongside `gpt-5-mini` and `gpt-5.2`.
- Preserved capability-aware controls so unsupported knobs are automatically gated.

3. **Bilingual, one-tap language UX**
- Added locale routing and language switching (`/en`, `/zh`) with one-button toggling.
- Updated homepage copy to keep Chinese and English messaging aligned and vivid.

4. **Interpretation data platform upgrade**
- Migrated interpretation retrieval to a slot-based SQL architecture.
- Integrated Takashima content at the **line slot level** (not merely as an author-level appendix).
- Kept `用九` / `用六` handling intact for 乾/坤 full-moving conditions.

5. **Historical data consistency**
- Added retroactive backfill tooling so existing Supabase sessions can be upgraded to the new interpretation structure.

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
| `gpt-5.2` | `none`, `minimal`, `low`, `medium`, `high` | yes | `medium` | `medium` |
| `gpt-5-mini` | `minimal`, `low`, `medium`, `high` | yes | `medium` | `medium` |
| `gpt-4.1` | none | no | n/a | n/a |

Compatibility:
- `MODEL_ALIASES` maps `gpt-5.1` to `gpt-5.2`.

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
# dry-run sample
python tools/backfill_session_interpretations.py --limit 100

# dry-run for specific sessions
python tools/backfill_session_interpretations.py --session-ids "uuid-a,uuid-b"

# apply globally (service key scope)
python tools/backfill_session_interpretations.py --apply
```

Operational note:
- Unfiltered `--apply` with service-role credentials can update all users’ session snapshots in the project.

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
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000 npm run dev
```

Open: `http://localhost:3000`

## Environment Variables

### Backend (AI + Auth)
- `OPENAI_API_KEY`
- `OPENAI_PW`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`

### Backend (Key operational controls)
- `ICHING_CHAT_MODEL` (default `gpt-5-mini`)
- `ICHING_CHAT_TURN_LIMIT` (default `10`)
- `ICHING_CHAT_TOKEN_LIMIT` (default `150000`)
- `ICHING_CHAT_MESSAGE_LIMIT` (default `3000`)
- `ICHING_USER_DAILY_TOKEN_LIMIT` (default `300000`)
- `ICHING_USER_SESSION_LIMIT` (default `50`)
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
