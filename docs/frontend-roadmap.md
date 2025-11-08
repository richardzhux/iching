# Next.js + shadcn Frontend Roadmap

The FastAPI backend is ready for consumption. Use this guide to stand up the new React experience.

## 1. Bootstrap the project

```bash
cd frontend
npx create-next-app@latest . \
nd --eslint --app --src-dir --import-alias "@/*"
npm install @tanstack/react-query zustand class-variance-authority clsx lucide-react
```

> Tip: initialize the repo root `frontend/` folder before running the command, then commit the scaffolding as the first frontend commit.

## 2. Configure Tailwind + shadcn/ui

```bash
npx shadcn-ui@latest init
npx shadcn-ui@latest add button input textarea select radio-group switch dialog sheet tabs tooltip toast separator card popover
```

- Add `src/lib/utils.ts` with the standard `cn` helper.
- Set up global CSS tokens in `src/styles/globals.css` to mirror the branding from Streamlit (purple gradient, glass panels).
- Extend `tailwind.config.ts` with font families and color palette.

## 3. App structure

- `src/app/layout.tsx` – root layout with font imports, theme provider, and React Query client provider.
- `src/app/page.tsx` – public splash/landing page with CTA to `/app`.
- `src/app/app/layout.tsx` – authenticated workspace shell (sidebar + main content).
- `src/app/app/page.tsx` – “Cast Hexagram” workflow: multi-step form, AI panel, results tabs, session history drawer.
- `src/app/api/preview/route.ts` – optional proxy for local development if you want to hide backend URL.

## 4. Data layer

- Create `src/lib/api.ts` with a typed `fetcher` that reads `process.env.NEXT_PUBLIC_API_BASE_URL`.
- Use React Query for mutations/queries:
  - `useConfigQuery` → `GET /api/config`
  - `useSessionMutation` → `POST /api/sessions`
  - `useSessionHistory` (local state or backend once implemented)
- Share global state via Zustand (topic/method defaults, AI toggles, password caching).

## 5. UI primitives & interactions

- Buttons/Toggles: shadcn `Button`, `ToggleGroup`.
- Form: use `react-hook-form` + `zod` for validation (manual lines, time, password).
- Panels: `Tabs` for Summary/Hexagram/Najia/AI, `Sheet` for settings drawer, `Dialog` for share/export.
- Notifications: `useToast` for success/failure, streaming indicator for AI.
- Downloads: create a `Blob` from `full_text` and trigger browser download (no temp file needed).

## 6. Environment & deployment

- `.env.local`
  ```
  NEXT_PUBLIC_API_BASE_URL=https://<render-app>.onrender.com
  NEXT_PUBLIC_APP_NAME=I Ching Web
  ```
- Add Vercel project, set `NEXT_PUBLIC_API_BASE_URL` to the Render URL (staging/prod).
- CI: add GitHub Actions workflow to run `npm run lint && npm run build`.

## 7. Future enhancements

- Add WebSocket/SSE endpoint on FastAPI for streaming AI output.
- Provide authenticated routes + Supabase/Auth0 integration if needed.
- Build a session timeline view with search/filter and saved favorites.
