# Deployment

Deploy Next.js and FastAPI together in the existing Vercel `iching` project. The public domain is `iching.richardzhux.com`; Supabase remains the existing database and authentication provider. Repository-root `vercel.json` owns the service definitions, build commands, function limits, and routing.

## Project configuration

- Repository: `richardzhux/iching`, production branch `main`.
- Root directory: repository root (empty), with no dashboard build/install/output overrides or ignored-build command.
- Node.js: 22.x. Python: 3.12 via `.python-version`.
- Function region: `cle1`, close to the existing Supabase Ohio region.
- Next.js service: `frontend/`, `npm ci`, `npm run build`; locale redirects use `frontend/src/proxy.ts` with the Node runtime.
- FastAPI service: root `app.py`, `python scripts/build_vercel_backend.py`, 300-second function duration.
- `/api/locations` reaches Next.js; other `/api/*`, `/openapi.json`, `/docs*`, and `/redoc` reach FastAPI.
- `/_next/image` rewrites to Vercel's `/_vercel/image` optimizer before the service routing rules. Root `images` configuration permits the current `/autumn/` artwork, supported widths, quality 75, and WebP output.

The Python build generates `data/interpretations.db` from tracked sources and validates 64 hexagrams, 450 slots, native calendar imports, timezones, packaged baselines, and rule bundles. Hosted startup opens reference databases read-only and creates no archive directories. `.vercelignore` excludes local secrets/caches from uploads, and function include/exclude rules preserve the generated database and required source assets.

Root-only exclusions must be anchored, such as `/tools/`, `/tests/`, and `/docs/`. An unanchored `tools/` also excludes frontend tools routes/components and `src/iching/tools`, causing missing pages or backend imports. Before a packaging change is released, use `vercel deploy --dry --json` from repository root and verify that required frontend routes, public artwork, Python modules, package data, and the backend build script are included. Keep native image configuration and its rewrite when changing service routing.

## Environment variables

Keep these encrypted and server-only in **Production**:

| Name | Purpose |
| --- | --- |
| `SUPABASE_URL` | Existing Supabase project URL |
| `SUPABASE_SERVICE_KEY` | Server-only persistence and admission RPCs |
| `OPENAI_API_KEY` | Existing model provider |
| `OPENAI_PW` | Existing app AI access password |
| `ICHING_CASTING_SECRET` | Stable signing value shared across every instance/deployment |
| `ICHING_REFERENCE_READ_ONLY` | `1` |
| `ICHING_WEB_ARCHIVE_ENABLED` | `0` |
| `ICHING_ALLOWED_ORIGINS` | Production domains and explicitly allowed local origins |

Retain existing quota defaults unless deliberately changed: daily user tokens 300000, session tokens 150000, chat turns 10, `ICHING_USER_SESSION_LIMIT` (saved sessions per user, default 500). `ICHING_GLOBAL_DAILY_TOKEN_LIMIT` can impose a server-wide token cap. Chart admission is shared through the service-role-only `admit_public_calculation` RPC; each worker also retains its local concurrency limit.

Browser variables are `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, optional `NEXT_PUBLIC_APP_NAME`, and **empty** `NEXT_PUBLIC_API_BASE_URL` in production. The empty base uses the same domain; do not set it to `/api`, because the client appends that prefix.

Do not give arbitrary preview branches production service-role or paid-provider credentials. The protected `iching-migration-preview` project was used for controlled validation and removed after two complete production deployments passed acceptance. Other full-backend previews need an explicitly provisioned credential scope. Never upload `.env` files or store credentials in this guide.

## Deploy and verify

From the repository root, using an authenticated Vercel CLI linked to `iching`:

```bash
vercel deploy --prod --skip-domain
vercel curl /api/health --deployment <new-deployment-url>
# Validate the complete deployment, then assign production domains.
vercel promote <new-deployment-url>
```

Git deployments from `main` build the complete frontend/backend pair. Keep the production source commit aligned with `main`. A deployment from the temporary project cannot be promoted into `iching`; deploy the tested source into the existing project first.

Before promotion, verify locale routing, location search/matching, readings/reference passages, authenticated history, saved BaZi/Ziwei snapshots, real streamed chat, and same-ID replay across deployments. Private API responses use `Cache-Control: private, no-store, no-transform`, including SSE without body buffering. Use disposable synthetic fixtures and remove them after testing.

Routing or packaging changes also require both `/en/tools` and `/zh/tools`, BaZi/Ziwei tab navigation with server-component requests, all localized library detail pages, public scripts/styles/fonts, and native optimized images. Check desktop/mobile workflows and document width; the mobile library's horizontal quick-navigation strip must scroll within the viewport. `frontend/e2e/journeys.spec.ts` covers tools navigation, optimized artwork, and library width/anchors in both desktop and mobile projects. Run it against the released URL with `PLAYWRIGHT_BASE_URL`; mocked API fixtures still require separate real-backend acceptance checks for changed integrations.

AI calls use a shared 135-second provider budget and preserve the 120-second stalled-read allowance. One final read may extend provider work to about 255 seconds, leaving settlement time inside the 300-second function. The browser enters recovery after 180 seconds and retains the request ID. Supabase admission/settlement prevents duplicate paid dispatch; stale pending requests become uncertain after 15 minutes and retain their reservations.

Large chart responses use HTTP gzip. The browser losslessly compresses snapshots larger than 256 KiB into `iching.chart-snapshot.gzip.v1` envelopes before uploading. Supabase keeps the existing 2 MiB snapshot storage cap; the API reconstructs up to 32 MiB and validates the original schema/rule metadata. Legacy plain snapshots remain readable. SSE is excluded from compression. Live acceptance preserved a 25,395,733-byte full-life chart exactly, with a 1,175,542-byte response and a 1,535,827-byte save request.

## Accepted application releases

The latest audited application release on October 1, 2026 is `9e860ae` (`dpl_CdakUfKiL526SM1UfKuW23xDaPsT`), following the routing/upload/image repair `93f882e`. Both services reached `READY` and served the production aliases. The audit passed 149 public page URLs, 149 server-component/navigation responses, 58 static assets, 12 responsive image variants, 48 rendered desktop/mobile route visits, real BaZi/Ziwei/statistics/manual-reading workflows, all 727 backend tests, and 36 desktop/mobile journeys. No unexpected resource 404s or application errors remained. The mobile library overflow discovered during that audit was repaired. Paid AI generation was not rerun during the resource audit; its cutover acceptance is recorded below.

These are dated acceptance records, not a substitute for inspecting the active deployment before a future release or rollback.

October 1, 2026: the public production domains were promoted to complete deployment `dpl_2YhNHuJyX2BxxX8BPn8GSDG2t9DN` (application source `36c449f`). Authenticated archive, casting provenance, normal and full-life chart reconstruction, paid request replay, and real SSE passed through the public domain. Supabase data/auth stayed in the existing project. Backend regression checks: 727; desktop/mobile journeys: 32. This complete deployment is the initial Vercel rollback target. The main-branch deployment `dpl_7Dfc2KGpoT8vP2aF3bB5Dirb6VET` (`06370c9`) also passed cross-deployment archive checks. Production was returned to it after successfully restoring and checking the initial Vercel pair.

## Rollback and Render retirement

Prefer a retained complete Vercel pair with the current routing/upload/image repairs, such as the audited `dpl_CdakUfKiL526SM1UfKuW23xDaPsT`. Inventory retained deployments and aliases before restoring one. The initial pairs `dpl_2YhNHuJyX2BxxX8BPn8GSDG2t9DN` and `dpl_7Dfc2KGpoT8vP2aF3bB5Dirb6VET` verified archive recovery and rollback, but predate the tools/image fixes and can reintroduce those regressions. Supabase is unchanged, so saved user data does not need reverse migration. The historical deployment `dpl_AJNtRDwmRavckiWEqYVcPXKRAZNB` depends on the retired Render backend and is no longer a usable rollback target.

The retired Render service was `srv-d47b67qli9vc738jnat0`, URL `https://iching-p9j9.onrender.com`, with one $7/month instance, no persistent disk, no secret files, and no linked environment groups. Its auto-deploy was switched off before source publication. The user deleted the entire Render project on October 1 after public-domain acceptance. The old backend subsequently returned 404 with `x-render-routing: no-server`, while Vercel health remained 200. The user reported a free Hobby workspace and approximately $0.20 of already accrued October usage. That accrued amount remains payable; the retired service no longer incurs its recurring compute charge. Render's Hobby workspace has no monthly plan fee.

The recurring observation automation was deleted at the user's request. Future billing review is manual. Incremental Vercel usage still draws from the team's existing shared Pro credit; no zero-overage forecast is asserted. Old open browser tabs can still contain the previous Render API URL or deployment-pinned image URLs; hard refresh them to load the current client and artwork.

## Local development

```bash
# Terminal 1, repository root after the README's Python environment setup:
source .venv/bin/activate
ICHING_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3100 \
  python -m uvicorn app:app --reload --port 8000

# Terminal 2:
cd frontend
npm ci
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 npm run dev
```

Local commands retain writable reference preparation; hosted functions use only packaged references and Supabase persistence. See [the root README](../README.md) for setup and [frontend/README.md](../frontend/README.md) for build-time API configuration and browser tests. Repository [AGENTS.md](../AGENTS.md) records the routing, packaging, and persistence invariants for future changes.
