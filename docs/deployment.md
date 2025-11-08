# Deployment Checklist

## FastAPI backend (Render/Railway/Fly.io)

1. **Repository** – expose the repo or a backend-only fork to the hosting provider.
2. **Build command**
   ```bash
   pip install -r requirements.txt
   ```
3. **Start command**
   ```bash
   uvicorn iching.web.api.main:app --host 0.0.0.0 --port $PORT
   ```
4. **Environment variables**
   - `OPENAI_API_KEY` – if AI integrations are enabled.
   - `OPENAI_PW` – password that unlocks AI mode via the API/UI.
   - `ICHING_ALLOWED_ORIGINS` – comma-separated list of frontend origins (e.g., `https://iching.vercel.app,https://staging-iching.vercel.app`).
   - Any data paths you override from `AppConfig` (defaults work for relative paths).
5. **Scaling**
   - Minimum instance size: 512 MB RAM is enough; CPU optimized if AI traffic grows.
   - Enable Render cron/worker if you plan on adding background archive cleanup tasks.
6. **Observability**
   - Enable logs & metrics dashboards.
   - Optional: send logs to Logtail/Datadog for AI auditing.

## Next.js frontend (Vercel)

1. **Create project** – point Vercel to the `frontend/` folder (after you scaffold it).
2. **Environment variables**
   - `NEXT_PUBLIC_API_BASE_URL` – URL of the FastAPI deployment.
   - `NEXT_PUBLIC_APP_NAME` – optional string used in the UI.
3. **Build command** – defaults from `create-next-app` (`pnpm build`, `npm run build`, or `yarn build`).
4. **Preview branches** – make sure preview URLs are whitelisted in `ICHING_ALLOWED_ORIGINS`.
5. **Custom domain** – add `CNAME` or `A` record pointing to Vercel once ready.

## Local development workflow

1. Start FastAPI locally: `uvicorn iching.web.api.main:app --reload`.
2. Export `ICHING_ALLOWED_ORIGINS=http://localhost:3000`.
3. In the frontend project, set `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000`.
4. Run `npm run dev` (Next.js) and iterate on UI components against the live API.
