# I Ching Studio repository guidance

Apply the user's current scope and existing authorization. Read [README.md](README.md) for the product and local setup, [frontend/README.md](frontend/README.md) for UI work, and [docs/deployment.md](docs/deployment.md) for hosted changes. Historical roadmaps and the migration plan record prior decisions; they are not current deployment instructions.

## Current architecture

- Production: `https://iching.richardzhux.com`, with the additional alias `https://iching1.vercel.app`.
- One Vercel project, `iching`, deploys Next.js and FastAPI Services together from repository root; production source is `main`.
- `frontend/` contains Next.js 16, TypeScript, React, locale routes `/en` and `/zh`, and client-side Ziwei charting with the pinned `iztro` engine.
- Root `app.py` exports FastAPI from `src/iching/web/api/main.py`. Python calculation, interpretation, session, and integration code lives under `src/iching/`.
- Supabase remains the existing auth, saved reading/chart/chat, and durable AI accounting store. Render is retired; historical Render URLs are not active runtime dependencies or rollback targets.
- Production runtimes are Node.js 22.x and Python 3.12 (`.python-version`). Python runtime dependencies are in `requirements.txt` and `pyproject.toml`; optional tools belong in package extras.

## Routing and packaging invariants

- Repository-root `vercel.json` owns both services, build commands, function limits, image configuration, and routing. Keep the dashboard project root at repository root, with build/install/output overrides and frontend-only ignored-build filters cleared.
- `/api/locations` belongs to Next.js and must precede the backend `/api/*` rule. Other `/api/*`, `/openapi.json`, `/docs*`, and `/redoc` belong to FastAPI. Locale redirects live in `frontend/src/proxy.ts` and preserve query parameters.
- Production `NEXT_PUBLIC_API_BASE_URL` is empty or unset. The client appends `/api/...`; do not set its base to `/api`. Local development uses `http://localhost:8000`.
- Preserve native image optimization: `/_next/image` rewrites to `/_vercel/image`. Root image sizes, qualities, formats, and local source patterns must support the artwork used by Next.js.
- Root-only upload exclusions in `.vercelignore` must start with `/`. An unanchored `tools/` removes `frontend/src/app/[locale]/tools`, frontend tools components, and `src/iching/tools` from deployment.
- Preserve all required frontend source/public assets, Python modules, package data, calendar baselines, rule bundles, and reference files in the upload and function bundle. Local secrets, caches, and research-only files remain excluded.

## Data and serverless behavior

- `scripts/build_vercel_backend.py` generates ignored `data/interpretations.db` from tracked sources and validates the corpus, native calendar, timezones, and packaged rule/baseline files. Generate references at build time.
- Hosted requests use `ICHING_REFERENCE_READ_ONLY=1` and `ICHING_WEB_ARCHIVE_ENABLED=0`. Do not add startup writes to packaged references or depend on local files/caches for durable user state.
- Keep `ICHING_CASTING_SECRET` stable across instances and deployments so casting provenance remains valid.
- Preserve request IDs, Supabase AI admission/settlement, and replay semantics. A retry must not dispatch a duplicate paid request.
- Preserve private response cache headers, incremental SSE, gzip for large JSON responses, and lossless large-chart snapshot envelopes. Existing plain snapshots must remain readable.
- Keep source passages, provenance, rule versions, archive compatibility, uncertain inputs, and calendar boundary behavior intact. Statistical frequency and structural activity do not imply fortune or life quality.
- Preserve original PDFs, OCR, source corpora, and research evidence. Change generated data only through its existing generation path when the task requires it.

## Commands and verification

From repository root, in the Python environment installed with `python -m pip install -e '.[dev]'`:

```bash
ICHING_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3100 \
  python -m uvicorn app:app --reload --port 8000
ICHING_ENABLE_AI=0 python -m pytest -q
python scripts/build_vercel_backend.py
```

From `frontend/`:

```bash
npm ci
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 npm run dev
npm run lint
npm run build
npm run test:e2e -- e2e/journeys.spec.ts
```

Run checks appropriate to the change. Build before local Playwright journeys; `PLAYWRIGHT_BASE_URL` selects an existing server and avoids starting another. Journey API fixtures verify UI behavior; use actual backend requests for changed integration workflows. Keep routine tests free of paid AI calls. Use existing checks and focused regression tests rather than introducing a new framework.

For a release, deploy the complete pair from repository root, wait for Vercel `READY`, confirm the intended source commit and aliases, and check the relevant public frontend and backend behavior. Git success alone does not confirm deployment. Routing/packaging changes require both locales, tools client navigation, optimized images, and API checks. UI changes require desktop/mobile interaction and viewport checks. Restore complete Vercel pairs for rollback; older Render-dependent frontends cannot serve the retired API.

## Secrets, scope, and maintenance

- Keep credentials out of chat, logs, tracked files, screenshots, and browser bundles. Local `.env` files stay ignored; hosted configuration comes from Vercel environment variables. Supabase browser variables use only the public project URL and anon key.
- Preserve existing Production-only credential scope. Full-backend preview credentials need the scope authorized for that task; arbitrary branches must not receive production service-role or paid-provider secrets.
- Use synthetic, disposable acceptance fixtures; remove only records created for those checks and preserve existing user data.
- The user canceled recurring migration monitoring and handles billing review manually. Start a new automation only when requested.
- Keep changes focused. Do not add technical reports, logs, or new documentation beyond the requested scope; remove temporary diagnostics after use.
