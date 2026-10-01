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

The Python build generates `data/interpretations.db` from tracked sources and validates 64 hexagrams, 450 slots, native calendar imports, timezones, packaged baselines, and rule bundles. Hosted startup opens reference databases read-only and creates no archive directories. `.vercelignore` excludes local secrets/caches from uploads, and function include/exclude rules preserve the generated database and required source assets.

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

Do not give arbitrary preview branches production service-role or paid-provider credentials. The protected `iching-migration-preview` project is the controlled migration validation environment. Other full-backend previews need an explicitly provisioned credential scope. Never upload `.env` files or store credentials in this guide.

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

AI calls use a shared 135-second provider budget and preserve the 120-second stalled-read allowance. One final read may extend provider work to about 255 seconds, leaving settlement time inside the 300-second function. The browser enters recovery after 180 seconds and retains the request ID. Supabase admission/settlement prevents duplicate paid dispatch; stale pending requests become uncertain after 15 minutes and retain their reservations.

Large chart responses use HTTP gzip. The browser losslessly compresses snapshots larger than 256 KiB into `iching.chart-snapshot.gzip.v1` envelopes before uploading. Supabase keeps the existing 2 MiB snapshot storage cap; the API reconstructs up to 32 MiB and validates the original schema/rule metadata. Legacy plain snapshots remain readable. SSE is excluded from compression. Live acceptance preserved a 25,395,733-byte full-life chart exactly, with a 1,175,542-byte response and a 1,535,827-byte save request.

## Live release

October 1, 2026: the public production domains were promoted to complete deployment `dpl_2YhNHuJyX2BxxX8BPn8GSDG2t9DN` (application source `36c449f`). Authenticated archive, casting provenance, normal and full-life chart reconstruction, paid request replay, and real SSE passed through the public domain. Supabase data/auth stayed in the existing project. Backend regression checks: 727; desktop/mobile journeys: 32. This complete deployment is the initial Vercel rollback target.

## Rollback and Render retirement

The historical retained deployment is `dpl_AJNtRDwmRavckiWEqYVcPXKRAZNB`, source `11ce5c9602d9eef7d56584d1c9cae4cafc4b3262`. It still uses Render. Resume Render before returning to that deployment if its compute has been suspended. Rebuilding old source also requires restoring the old `frontend` project root and Next.js dashboard preset.

Keep complete, verified Vercel frontend/backend pairs for rollback after Render retirement. Supabase is unchanged, so saved user data does not need reverse migration. The two October 1 admission migrations are compatible with the old host. The old Render application cannot decode newly compressed chart snapshots; use a retained complete Vercel pair for a full rollback. Resuming the historical Render deployment alone only restores its original reading/plain-chart behavior.

The migrated Render service is `srv-d47b67qli9vc738jnat0`, URL `https://iching-p9j9.onrender.com`, with one $7/month instance, no persistent disk, no secret files, and no linked environment groups. Its auto-deploy is off. Workspace billing showed one included service, a free Hobby workspace plan, and a $7 projected October service charge. Suspending this service stops further compute accrual; already accrued usage remains payable. Permanently deleting it removes the resume option.

The user requested stopping the $7 charge after live acceptance. Suspend compute after production verification and retain the recoverable service as a free fallback. Observe production errors, SSE completion, ledger states, and incremental Vercel usage for 48 hours after cutover. Old open browser tabs can still contain the previous Render API URL; refresh them to load the migrated client.

## Local development

```bash
uvicorn iching.web.api.main:app --reload
cd frontend
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 npm run dev
```

Set `ICHING_ALLOWED_ORIGINS=http://localhost:3000` locally. Local commands retain writable reference preparation; hosted functions use only packaged references and Supabase persistence.
