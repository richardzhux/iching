# I Ching Studio

Modern 易经工作台，覆盖 CLI、Streamlit 调试界面、FastAPI 服务与 Next.js + shadcn/ui 前端。无论是传统五十蓍、三枚铜钱、梅花易数还是手动六爻输入，都可以在同一套核心推演逻辑上完成，占卜结果可扩展为 BaZi、五行、纳甲、AI 分析与自动归档。

## Repository Walkthrough

```
├── src/iching
│   ├── core/                     # Hexagram defs, BaZi, Najia, time utils, divination methods
│   ├── integrations/             # OpenAI analysis + Najia adapters
│   ├── services/session.py       # Session orchestration (lines generation, AI glue, archives)
│   ├── web/api/                  # FastAPI app, routers, CORS middleware
│   ├── web/models.py             # Pydantic DTOs shared between API + UI
│   └── web/service.py            # SessionRunner used by API & Streamlit
├── src/iching/gui/app.py         # Legacy Streamlit UI (now using SessionRunner)
├── iching5.py / src/iching/cli   # Terminal experience
├── frontend/                     # Next.js 16 App Router + Tailwind + shadcn/ui workspace
├── docs/                         # Frontend roadmap, deployment checklist
├── tests/                        # Pytest smoke tests + FastAPI contract test
├── requirements.txt              # Runtime deps for core + FastAPI + Streamlit
└── pyproject.toml                # Editable install for `src/` package layout
```

## Core Functionality

- **Divination engines** – 五十蓍草 (`s`), 三枚铜钱 (`c`), 梅花易数 (`m`), 随机/手动 (`x`) implemented in `iching.core.divination`. Manual mode validates six lines (6/7/8/9) and supports timestamp overrides.
- **Hexagram data pipeline** – loads Takashima/Guaci resources, renders卦辞文案、动爻、互卦、变卦等 (`iching.core.hexagram`).
- **BaZi & 五行** – `BaZiCalculator` computes stems/branches, elements strength, 旺相休囚.
- **Najia + 六亲/六神** – `iching.integrations.najia.Najia` compiles天干地支映射、动静爻、六神等结构化数据。
- **AI analysis** – `iching.integrations.ai.analyze_session` calls OpenAI (model/capability map) with optional reasoning + verbosity knobs, protected by `OPENAI_PW`.
- **SessionService** – single entry point handling method selection, manual lines, timestamp rules, AI gating, archive text generation, history buffer.

## User Interfaces

### CLI (`python iching5.py`)
- Guided prompts for topic, question, method; manual line input with validation loops.
- Uses TeeLogger to archive transcripts per session and prints BaZi/纳甲/AI output inline.

### Streamlit (`python gui.py`)
- Retained as a debugging dashboard; now delegates to `SessionRunner` so it mirrors API behavior.
- Custom CSS theme (glassmorphism) with topic/method/time controls, AI toggles, JSON inspector, download button.

### FastAPI (`uvicorn iching.web.api.main:app --reload`)

Endpoints:

| Method | Path             | Description                                                   |
| ------ | ---------------- | ------------------------------------------------------------- |
| GET    | `/`              | Simple heartbeat message                                      |
| GET    | `/api/health`    | Health probe for Render/uptime checks                         |
| GET    | `/api/config`    | Returns topics, methods, AI model metadata used by frontends |
| POST   | `/api/sessions`  | Validates payload, runs SessionService, saves archive file    |

Key behaviors:
- `SessionRunner` centralizes AI password validation, archive persistence (with temp fallback), and JSON-safe payloads.
- CORS is configurable via `ICHING_ALLOWED_ORIGINS`.
- Pydantic request schemas enforce manual-line length, timestamp presence when `use_current_time=false`, reasoning/verbosity toggles per model.

### Next.js Frontend (Vercel `frontend/`)

- **Technology stack**: Next.js 16 App Router, TypeScript strict mode, TailwindCSS 3, shadcn/ui components, Zustand, React Query, `sonner` toasts, custom glass theme.
- **Landing page (`/`)**: hero panel describing architecture, CTA to `/app`, feature list.
- **Workspace (`/app`)**:
  - _Cast Form_: multi-step control for topic, question, method selection (radio/select), manual lines, time toggle (current vs custom datetime picker), AI enable switch, password, model, reasoning & verbosity (dynamic per capability).
  - _Results panel_: tabs for 概要 / 卦辞 / 纳甲 / AI, each showing preformatted text from the backend.
  - _History drawer_: sheet storing last 10 sessions in-memory (front-end state) with timestamp + archive file hints.
  - _Download support_: backend still writes txt archives; frontend can extend to fetch `full_text` for blob downloads.
  - _Error handling_: HTTP errors from FastAPI are parsed into human-friendly toasts (e.g., missing method selection).
- **Theming**: global glass tokens, gradients, dark/light theme via `next-themes`, custom container widths, responsive layout.
- **Providers**: App-level wrappers for ThemeProvider, React Query Client, Sonner Toaster; Zustand store keeps form state & results.

## Hosting / Deployment

- **Backend**: Render service pointing at repo root, running `uvicorn iching.web.api.main:app`. Environment:
  - `PYTHONPATH=src` (or installed via `pip install -e .`).
  - `ICHING_ALLOWED_ORIGINS` list of frontend URLs (localhost + Vercel preview/prod).
  - Archives are written inside Render’s container (e.g., `/app/data/Hexarchive/guilty/...`). Swap to cloud storage later by overriding `CONFIG.paths`.
- **Frontend**: Vercel project targeting `frontend/`, env vars `NEXT_PUBLIC_API_BASE_URL=<hello>`, `NEXT_PUBLIC_APP_NAME=<world>`. Build command `npm run build`, automatic CDN + preview deploys, custom domain ready.
- **CI**: `.github/workflows/frontend-ci.yml` executes `npm ci`, `npm run lint`, `npm run build` for any `frontend/**` changes, preventing regressions before Vercel deploys.

## Development Workflow

```bash
# 1. Python deps + editable install
pip install -r requirements.txt
pip install -e .

# 2. Backend (FastAPI)
export ICHING_ALLOWED_ORIGINS=http://localhost:3000
uvicorn iching.web.api.main:app --reload

# 3. Frontend (Next.js)
cd frontend
cp .env.local.example .env.local  # if you create one
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000 npm run dev

# 4. Tests / lint
pytest                 # backend/unit
npm run lint           # frontend
npm run build          # ensure production build passes
```

## Reference Docs
- `docs/frontend-roadmap.md` – component plan, Tailwind/shadcn steps, state/data patterns.
- `docs/deployment.md` – Render + Vercel checklists, env vars, local dev commands.
- `README (this file)` – overarching architecture plus CLI/API usage.

# Next steps

a. ENTIRELY RESTRUCTURE FOR CLARITY, use more class and subclass ✅ 10.23  
b. 纠正山地剥的错误binary code ✅ 10.24  
c. 校对傅佩荣 ✅ 10.27  
d. meihua make 3 3digit nums ✅ 10.24  
e. count and classify jixiong in each yao, rate ✅ 10.30  
f. generate flow chart ✅ 11.2  
g. 加入自然意象 ✅ 11.3  
h. 加入psutil, tqdm ✅ 11.4
i. integrate with AI for analysis and explanation ✅ 8.14 (2025)
j. add UI with Gradio ✅ 9.4
k. 八卦纳甲 卦分八宫 旺相休囚和生旺墓绝 十二长生 世应 六亲 六神 用神等 ✅ 11.3
l. complete titled database for all 64 hexagrams ✅ 11.4
m. total restructure ✅ 11.4
n. changed UI to streamlit ✅ 11.5

# WARNING
THE MAKEFILE IN THIS REPOSITORY CONTAINS COMMANDS THAT MAY RESULT IN THE PERMANENT DELETION OF DATA OR SYSTEM DAMAGE. DO NOT RUN THIS MAKEFILE UNLESS YOU ARE PREPARED FOR PERMANENT DATA LOSS OR SYSTEM DAMAGE. USE ONLY IN A SECURE, ISOLATED ENVIRONMENT FOR TESTING PURPOSES.
