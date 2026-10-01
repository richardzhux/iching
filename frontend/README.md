# I Ching Studio frontend

This is the Next.js 16 App Router frontend for I Ching Studio. It provides Chinese and English casting, readings, the 64-hexagram library, BaZi and Ziwei tools, authentication, and saved history. Production is [iching.richardzhux.com](https://iching.richardzhux.com).

The repository-root Vercel project deploys this frontend and the Python FastAPI backend together. See [the root README](../README.md), [deployment guide](../docs/deployment.md), and [agent instructions](../AGENTS.md).

## Local development

Use Node.js 22.x. From this directory:

```bash
npm ci
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 npm run dev
```

Open [localhost:3000](http://localhost:3000). Start the FastAPI backend in another terminal from the repository root using the root README's Python setup:

```bash
source .venv/bin/activate
ICHING_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3100 \
  python -m uvicorn app:app --reload --port 8000
```

Public browser settings can be stored in ignored `frontend/.env.local`:

| Variable | Local development | Production |
| --- | --- | --- |
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000` | Empty or unset; same-origin API |
| `NEXT_PUBLIC_SUPABASE_URL` | Existing Supabase public project URL | Same existing project |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Existing Supabase public anon key | Same existing project |
| `NEXT_PUBLIC_APP_NAME` | Optional display name | Optional display name |

Public variables are compiled into browser bundles. Keep `SUPABASE_SERVICE_KEY`, `OPENAI_API_KEY`, `OPENAI_PW`, and `ICHING_CASTING_SECRET` in the server environment. The API client adds `/api` itself, so the API base must not be `/api`. `src/lib/env.ts` uses the local API by default in development and the same origin by default in production.

## Application structure

| Location | Responsibility |
| --- | --- |
| `src/app/[locale]/` | Localized home, reading, library/detail, tools, and profile routes |
| `src/app/api/locations/route.ts` | Next.js location search and coordinate matching |
| `src/proxy.ts` | Locale redirects, preserving query parameters |
| `src/components/` | Casting, results, charts, archive, and shared UI |
| `src/lib/api.ts`, `src/types/api.ts` | API transport and payload contracts |
| `src/lib/supabase-browser.ts`, `src/lib/store.ts` | Browser authentication and workspace state |
| `src/lib/ziwei-terms.ts`, `src/lib/frequency-display.ts` | Shared chart terminology and frequency presentation |
| `public/autumn/` | Courtyard, leaf, coin, and stone artwork |
| `e2e/journeys.spec.ts` | Desktop/mobile workflow and deployment regression checks |

## Build and check

```bash
npm run lint
npm run build
npm run test:e2e -- e2e/journeys.spec.ts
```

Playwright starts the production build on `http://127.0.0.1:3100` and runs desktop and mobile projects. Build first. Its API fixtures exercise UI contracts without paid AI calls; verify actual backend workflows separately when they change.

To test the built frontend against the separately running local API, set the API base at build time:

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 npm run build
npm run start -- --hostname 127.0.0.1 --port 3100
```

To run the journey suite against an existing local or deployed server:

```bash
PLAYWRIGHT_BASE_URL=https://iching.richardzhux.com \
  npm run test:e2e -- e2e/journeys.spec.ts
```

## Vercel deployment rules

Deploy from the repository root. Root `vercel.json` defines `frontend` and `backend` Services; do not replace it with a frontend-only project root or build filter. `/api/locations` must reach Next.js before the backend `/api/*` rule. Other API paths reach FastAPI.

Native image optimization is configured in root `vercel.json`: `/_next/image` rewrites to `/_vercel/image`, with the supported sizes, quality, format, and `/autumn/` source pattern. Keep this configuration aligned with new artwork.

Root `.vercelignore` excludes root maintenance directories using anchored patterns such as `/tools/`. An unanchored `tools/` would also remove this application's tools routes/components and Python runtime modules from the upload. After routing, image, or upload changes, verify both locales, client-side tools navigation, optimized artwork, and mobile library width on the deployed application.
