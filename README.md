# I Ching Studio

Modern 易经工作台 that spans CLI, Streamlit, FastAPI, and a Next.js + shadcn/ui frontend. Traditional methods (五十蓍、三枚铜钱、梅花易数、手动六爻) all run on the same SessionRunner so BaZi、五行、纳甲、AI 分析、自动归档 stay consistent across surfaces.

## Table of Contents
1. [Overview](#overview)
2. [Highlights](#highlights)
3. [Repository Layout](#repository-layout)
4. [Quick Start](#quick-start)
5. [Architecture](#architecture)
6. [Supabase Integration & Data Governance](#supabase-integration--data-governance)
7. [User Interfaces](#user-interfaces)
8. [Operations & Deployment](#operations--deployment)
9. [Reference Docs](#reference-docs)
10. [Delivery Milestones](#delivery-milestones)

## Overview

I Ching Studio standardizes divination, BaZi analysis, Najia mapping, and AI commentary with a single orchestration service. The backend enforces quota, rate limiting, and archive rules; Supabase keeps authenticated chat history; the Next.js workspace gives users a polished surface for casts, AI responses, and transcript downloads.

## Highlights

- **Divination engines** – 五十蓍草 (`s`), 三枚铜钱 (`c`), 梅花易数 (`m`), 随机/手动 (`x`) in `iching.core.divination`, including manual validation for 6/7/8/9 line values and timestamp overrides.
- **Hexagram pipeline** – `iching.core.hexagram` renders 卦辞、动爻、互卦、变卦 sourced from Takashima/Guaci data.
- **BaZi & 五行** – `BaZiCalculator` computes stems/branches, 旺相休囚, and strength meta for downstream Najia logic.
- **Najia + 六亲/六神** – `iching.integrations.najia_repository.NajiaRepository` reads `data/najia.db` to serve structured 本卦/变卦行, 六神, 伏神，`najia_table` further injects per-line relation markers、伏神、动爻符号、世应标记，并以日干推导出的六神顺序填充神煞列。
- **AI analysis** – `iching.integrations.ai.analyze_session` gates OpenAI calls via `OPENAI_PW`, model capability map, reasoning/verbosity knobs, and a Supabase history sink.
- **SessionService/SessionRunner** – one entry point for method selection, manual lines, AI gating, archive text generation, follow-up chat quotas, and JSON-safe payloads shared by CLI, Streamlit, API, and frontend.
- **Tone-aware prompts** – AI outputs honor `normal / wenyan / modern / academic` tone settings via explicit system instructions and are mirrored in follow-up chats so users can keep a consistent style across casts.

## Repository Layout

```
├── src/iching
│   ├── core/                     # Hexagram defs, BaZi, time utils, divination engines
│   ├── integrations/             # OpenAI adapters, Supabase REST client, Najia repository
│   ├── services/session.py       # Session orchestration + archive generation
│   ├── web/api/                  # FastAPI app, routers, CORS middleware
│   ├── web/models.py             # Pydantic DTOs shared by API + UI
│   └── web/service.py            # SessionRunner + ChatService
├── src/iching/gui/app.py         # Streamlit UI (debug dashboard)
├── iching5.py / src/iching/cli   # Legacy terminal experience
├── frontend/                     # Next.js 16 App Router + Tailwind + shadcn/ui workspace
├── docs/                         # Roadmap, deployment checklist, Supabase schema
├── tests/                        # Pytest smoke + FastAPI contract tests
├── requirements.txt              # Runtime deps for core/FastAPI/Streamlit
└── pyproject.toml                # Editable install for `src/`
```

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+ (Next.js 16 + Turbopack)
- OpenAI + Supabase credentials (for AI + cloud history)

### Setup & Run

```bash
# Python deps + editable install
pip install -r requirements.txt
pip install -e .

# Backend (FastAPI)
export ICHING_ALLOWED_ORIGINS=http://localhost:3000
uvicorn iching.web.api.main:app --reload

# Frontend (Next.js workspace)
cd frontend
cp .env.local.example .env.local
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000 npm run dev
```

### Tests & Quality Gates

```bash
pytest                 # backend smoke + FastAPI contract tests
npm run lint           # ESLint + TypeScript checks
npm run build          # Next.js production build
```

`.github/workflows/frontend-ci.yml` enforces the lint/build pipeline on every PR touching `frontend/**`.

## Architecture

### Layered services
- `src/iching/web/api/routes.py` exposes REST endpoints, `web/models.py` owns DTOs, and `web/service.py` hosts `SessionRunner` so CLI, Streamlit, and API surfaces reuse identical orchestration logic.
- Integration code (OpenAI, Supabase REST/Auth, Najia SQLite) lives under `src/iching/integrations/`, keeping secrets + HTTP clients isolated for easier mocking.

### Session lifecycle & payloads
- `SessionRunner` enforces `SessionService.TOPIC_MAP` + `AVAILABLE_METHODS` plus a 2,000-character `user_question` guard before every cast; timestamps default to current time but support explicit overrides for manual cases.
- `SessionService` assembles BaZi/Eight Characters, 旺相休囚, Takashima/Guaci text packages, Najia 主/互卦 data, and per-line 六亲/六神 metadata (动爻标记、伏神、marker、世应) while deriving the 六神顺序 from the日干 to populate the table rows.
- Every run emits a normalized `SessionPayload`: summary, `hex_sections`, `hex_overview`, `bazi_detail`, `najia_table`, archive path, AI usage, auth flag, and a JSON-safe `session_dict` (Python objects are serialized and round-tripped to strings).
- Archives land in `config.paths.archive_complete_dir` (defaults to `~/Documents/Hexarchive/guilty`), and `_save_archive` transparently falls back to `/tmp/iching-archives` if the primary path is not writable.
- When AI responses exist (or when the caller is authenticated) the payload is snapshotted into Supabase + `SessionStateStore`, preserving the OpenAI `response_id` so follow-up chats can resume the same reasoning thread.

### AI Model Matrix

| Surface | Model | Reasoning choices | Default | Verbosity? | Default |
|---------|-------|-------------------|---------|------------|---------|
| Session (initial AI) | `gpt-5.1` | `none / minimal / low / medium / high` | `medium` | Yes | `medium` |
| Session | `gpt-5-mini` | `minimal / low / medium / high` | `medium` | Yes | `medium` |
| Session | `gpt-4.1` | _none_ | – | No | – |
| Follow-up chat (default) | `gpt-5-mini` | `minimal / low / medium / high` | `medium` | Yes | `medium` |
| Follow-up chat (deep) | `gpt-5.1` | `none / minimal / low / medium / high` | `medium` | Yes | `medium` |

- `MODEL_CAPABILITIES` guards unsupported reasoning/verbosity combinations.
- Supabase sessions persist the last-used follow-up model so `/app` can rehydrate state across reloads.

### AI orchestration pipeline
- AI is locked behind both Supabase authentication and the `OPENAI_PW` shared secret; `RateLimiter.ensure_ai_quota` caps each IP at 50 successful AI runs per day before SessionService even calls OpenAI.
- `start_analysis` builds a single OpenAI Responses API call with `SYSTEM_PROMPT_PRO`, merges the chosen tone (`normal / wenyan / modern / academic`) from `TONE_PROFILES`, and clamps reasoning/verbosity to the model’s capabilities; JSON payloads sent to OpenAI embed the full session dict so the model can reason about lines + Najia context.
- `_request_openai_response` automatically retries without reasoning or verbosity knobs when the API rejects unsupported combinations, so costly casts don’t fail due to capability drift.
- `continue_analysis` reuses `previous_response_id`, tone, reasoning, and verbosity for follow-up chat so multi-turn discussions stay within the same OpenAI thread and inherit the right safety envelope.

### Rate limits & gating
- IP-based throttling: `RateLimiter` caps each client IP at 1,000 total attempts/day and 50 successful AI runs/day, resetting counters every UTC midnight.
- Question hygiene: `SessionRunner` throws if `user_question` exceeds 2,000 characters or if the topic/method doesn’t align with `TOPIC_MAP` / `AVAILABLE_METHODS`.
- Follow-up quotas: each Supabase session is limited to 10 follow-up turns (`ICHING_CHAT_TURN_LIMIT`), 150k accumulated tokens (`ICHING_CHAT_TOKEN_LIMIT`), and 3,000 characters per question (`ICHING_CHAT_MESSAGE_LIMIT`) before `ChatRateLimitError` short-circuits the request.
- Per-user metering: `UserTokenLimiter` tracks tokens across all sessions using an in-memory counter that resets daily and rejects traffic once the default 300k-token allowance is spent, complementing the per-session guardrails.

### Session cache & follow-up bridge
- `SessionStateStore` caches up to `ICHING_SESSION_CACHE_LIMIT` sessions (default 100) for six hours (`ICHING_SESSION_CACHE_TTL_SECONDS`), keeping summary text, the first AI response, OpenAI response IDs, token counts, and the JSON `session_payload` ready for chat APIs even before Supabase persistence completes.
- `ChatService.record_session_snapshot` copies `SessionPayload` + profile info into Supabase `sessions` and seeds `chat_messages` with the initial assistant reply so downloads reflect the complete narrative.
- When logged-out casts are later claimed by authenticated users, `_claim_anonymous_session` reassigns rows from `ANONYMOUS_USER_ID` and `_persist_initial_message` backfills the transcript; if Supabase has no row yet, `ensure_session_row` rebuilds it directly from `SessionStateStore`.
- Session storage is automatically GC’d: `_enforce_session_limit` trims each user to 50 Supabase sessions, and the in-memory store evicts by LRU or TTL so long-lived workers don’t leak.
- `list_sessions` derives topic/method labels from `payload_snapshot` or the `summary_text`, guaranteeing the `/profile` UI displays consistent badges even if legacy rows lack explicit columns.

### Frontend state discipline
- Providers in `frontend/src/components/providers` wrap Theme/Auth/Query contexts.
- React Query (`frontend/src/lib/queries.ts`) handles server mutations; Zustand (`frontend/src/lib/store.ts`) persists cast form + results + local history.
- `sonner` toasts + custom error parsing turn FastAPI errors into user-friendly feedback.

## Supabase Integration & Data Governance

- **Tables & payloads** – `public.sessions` holds summary text, `initial_ai_text`, follow-up model metadata, chat turn counters, token counts, and the complete `payload_snapshot` so `/profile` can hydrate without recomputation; `public.chat_messages` captures every Q/A turn with role, tokens_in/out, model, reasoning, verbosity, tone, timestamps, and user profile fields for audit-friendly transcripts.
- **Auth boundary & verification** – Supabase Auth (email/password + Google OAuth) only runs in-browser; FastAPI verifies every Bearer token via `/auth/v1/user` using the service-role key (`SupabaseRestClient`), then issues REST calls on behalf of the user so quotas/logging stay centralized server-side without RLS.
- **Anonymous handoff & caps** – logged-out casts write rows under `ANONYMOUS_USER_ID`; when a user later signs in, `_claim_anonymous_session` reassigns ownership (or rebuilds rows from `SessionStateStore`). `USER_SESSION_LIMIT` (default 50) keeps each account trimmed by deleting the oldest Supabase sessions and clearing the matching cache entries.
- **Quotas & limits** – follow-ups enforce `ICHING_CHAT_TURN_LIMIT` (10 turns/session), `ICHING_CHAT_TOKEN_LIMIT` (150k tokens/session), `ICHING_CHAT_MESSAGE_LIMIT` (3k chars/message), and `ICHING_USER_DAILY_TOKEN_LIMIT` (300k tokens/day/user). `UserTokenLimiter` resets counters daily per user so transcripts are throttled before any OpenAI spend once the allowance is exhausted.
- **Client-side history** – when unauthenticated, the frontend caches the last 10 sessions only in Zustand + `localStorage`; authenticated flows always read/write Supabase endpoints and benefit from payload snapshots + download-ready text.
- **Retention** – `docs/supabase-schema.sql` ships `purge_old_sessions()` plus optional pg_cron automation to delete sessions (and cascading chat logs) older than 90 days, making the regulated window explicit in git.
- **Profile/API flows** – `GET /api/sessions`, `GET/POST /api/sessions/{id}/chat`, `GET /api/config`, and `DELETE /api/sessions/{id}` cover listing, continuing, downloading, and deleting history; `list_sessions` back-fills topic/method badges from `payload_snapshot`/summary so even legacy data renders reliably in `/profile`.

## User Interfaces

### CLI (`python iching5.py`)
- Guided prompts for topic/question/method, manual line input with validation, and TeeLogger transcript archives.

### Streamlit (`python gui.py`)
- Debug-oriented dashboard reusing `SessionRunner`; includes topic/method/time controls, AI toggles, JSON inspector, download button, and custom glassmorphism styling.

### FastAPI (`uvicorn iching.web.api.main:app --reload`)

| Method | Path             | Description                                                   |
| ------ | ---------------- | ------------------------------------------------------------- |
| GET    | `/`              | Heartbeat                                                     |
| GET    | `/api/health`    | Render uptime probe                                           |
| GET    | `/api/config`    | Topics, methods, AI model metadata                            |
| POST   | `/api/sessions`  | Validates payload, runs SessionService, saves archive         |

Key behaviors: centralized AI password validation, archive persistence (with temp fallback), JSON-safe payloads, `ICHING_ALLOWED_ORIGINS` control, Pydantic schema enforcement for manual lines + timestamps + capability toggles.

### Next.js workspace (`frontend/`)
- **Stack**: Next.js 16 App Router, TypeScript, TailwindCSS 3, shadcn/ui, React Query, Zustand, `sonner` toasts, glass theme via `next-themes`.
- **Landing `/`**: hero panel, architecture overview, CTA into `/app`.
- **Workspace `/app`**: cast form (topic, method, manual lines, datetime toggle, AI password + model/verbosity controls), results tabs (概要/卦辞/纳甲/AI), history drawer (last 10 sessions), download support, rich error handling.
- **Profile `/profile`**: Supabase auth popover (email/password + Google OAuth), cloud history list with topic·method·time badges, avatar/name/email, actions for follow-up chat, transcript download, delete.

## Operations & Deployment

- **Backend (Render)** – run `uvicorn iching.web.api.main:app` with `PYTHONPATH=src` or `pip install -e .`. Required env vars: `ICHING_ALLOWED_ORIGINS`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `OPENAI_PW`. Optional knobs include `ICHING_CHAT_TURN_LIMIT` (default 10), `ICHING_CHAT_TOKEN_LIMIT` (150k tokens/session), `ICHING_CHAT_MESSAGE_LIMIT` (3k chars/message), `ICHING_USER_DAILY_TOKEN_LIMIT` (300k tokens/user/day), `ICHING_USER_SESSION_LIMIT` (50 Supabase rows/user), `ICHING_SESSION_CACHE_LIMIT` (100 cached sessions), `ICHING_SESSION_CACHE_TTL_SECONDS` (6h), and `ICHING_ANON_USER_ID`.
- **Archives** – saved to `config.paths.archive_complete_dir` (defaults to `~/Documents/Hexarchive/guilty` or `/app/data/Hexarchive/...` in production). `_save_archive` auto-falls back to `/tmp/iching-archives` if the target volume is read-only so transcripts are never lost.
- **Path config** – `build_app_config` honors `ICHING_DATA_DIR`, `ICHING_GUACI_DIR`, `ICHING_TAKASHIMA_DIR`, `ICHING_SYMBOLIC_DIR`, `ICHING_ENGLISH_DIR`, `ICHING_GUA_INDEX_FILE`, `ICHING_NAJIA_DB`, `ICHING_ARCHIVE_BASE/COMPLETE/ACQUITTAL`, materializing directories at startup so Takashima/Guaci assets and Najia SQLite resources are always on disk.
- **Frontend (Vercel)** – project root `frontend/`, env vars `NEXT_PUBLIC_API_BASE_URL`, `NEXT_PUBLIC_APP_NAME`, `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, build command `npm run build`.
- **CI/CD** – frontend workflow blocks merges without lint/build; deployment + schema docs stay versioned in `docs/`.
- **Operational guardrails** – rate limiting (`RateLimiter`), AI password gating, quota env vars, Supabase retention SQL, and DTO validation make production behavior explicit and auditable.

## Reference Docs
- `docs/frontend-roadmap.md` – component breakdown, Tailwind/shadcn plan, UI state/data patterns.
- `docs/deployment.md` – Render + Vercel checklists, env vars, local dev commands.
- `docs/supabase-schema.sql` – helper SQL for `sessions` + `chat_messages` tables and retention jobs.

## Delivery Milestones

A. ENTIRELY RESTRUCTURE FOR CLARITY, use more class and subclass ✅ 2024.10.23
b. 纠正山地剥的错误binary code ✅ 10.24
c. 校对傅佩荣 ✅ 10.27
d. meihua make 3 3digit nums ✅ 10.24
e. count and classify jixiong in each yao, rate ✅ 10.30
f. generate flow chart ✅ 11.2
g. 加入自然意象 ✅ 11.3
h. 加入psutil, tqdm ✅ 11.4
I. integrate with AI for analysis and explanation ✅ 2025.8.14
j. add UI with Gradio ✅ 9.4
k. 八卦纳甲 卦分八宫 旺相休囚和生旺墓绝 十二长生 世应 六亲 六神 用神等 ✅ 11.3
l. complete titled database for all 64 hexagrams ✅ 11.4
M. TOTAL RESTRUCTURE ✅ 11.4
n. changed UI to streamlit ✅ 11.5
o. add nextjs frontend with shadcn/ui ✅ 11.6
p. deploy to render and vercel ✅ 11.7
q. big UI upgrade and numerous bug fixes ✅ 11.11
R. MAJOR UPGRADE: supabase integration for user auth and chat history ✅ 11.14
