# Premium Yi Institution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn I Ching Studio from an AI-forward prototype into a source-grounded reading desk with a public sample reading, graceful backend fallback, visible journal workflow, and browsable hexagram library.

**Architecture:** Keep the existing FastAPI/session pipeline and Next app. Add frontend-only public library helpers for indexable pages, improve the public homepage and workspace fallback states, and make journal/outcome tracking visible in the reading workflow without changing persistence contracts.

**Tech Stack:** Next.js App Router, React, TypeScript, Tailwind, FastAPI/Python tests.

---

### Task 1: Public Contract Tests

**Files:**
- Create: `tests/test_frontend_premium_contract.py`

- [ ] Write tests that verify public copy avoids AI-saas slop, shows a sample reading, exposes `/library` and `/hexagram/[slug]` routes, provides backend fallback escapes, and keeps the existing source-id reading brief contract.
- [ ] Run `pytest tests/test_frontend_premium_contract.py -q` and confirm failures before implementation.

### Task 2: Homepage Reading Desk

**Files:**
- Modify: `frontend/src/components/home/home-page.tsx`
- Modify: `frontend/src/i18n/catalog/en.ts`
- Modify: `frontend/src/i18n/catalog/zh.ts`

- [ ] Replace “From yarrow stalks to AI,” “Tired of ChatGPT-style vagueness,” “Coming Soon,” and developer-docs-first copy with a calmer bilingual reading-desk identity.
- [ ] Put one concrete sample reading above the fold with question, cast, primary hexagram, moving line, changed hexagram, classical passage, source-bound interpretation, and CTAs to workspace/library.
- [ ] Add safety language that readings are reflective interpretations, not medical, legal, financial, or fate-certain advice.

### Task 3: Workspace Fallback

**Files:**
- Modify: `frontend/src/components/workspace/cast-workspace.tsx`
- Modify: `frontend/src/lib/queries.ts`
- Modify: `frontend/src/i18n/messages.ts`
- Modify: `frontend/src/i18n/catalog/en.ts`
- Modify: `frontend/src/i18n/catalog/zh.ts`

- [ ] Replace one-line config loading with a dignified reading-desk skeleton.
- [ ] Replace backend error state with links to sample reading and source library, plus a retry action.
- [ ] Make the config query timeout/retry behavior finite so production does not leave users in an opaque loading state forever.

### Task 4: Public Source Library

**Files:**
- Create: `frontend/src/lib/hexagram-library.ts`
- Create: `frontend/src/app/[locale]/library/page.tsx`
- Create: `frontend/src/app/[locale]/hexagram/[slug]/page.tsx`
- Modify: `frontend/src/i18n/catalog/en.ts`
- Modify: `frontend/src/i18n/catalog/zh.ts`

- [ ] Build a static 64-hexagram helper from the existing guaxiang index data.
- [ ] Add a public library index route with search-oriented cards and source-language framing.
- [ ] Add public hexagram detail pages with number, Chinese name, English meaning, binary lines, source layers, and links back to the reading desk.

### Task 5: Journal Workflow

**Files:**
- Modify: `frontend/src/components/workspace/results-panel.tsx`
- Modify: `frontend/src/components/workspace/history-drawer.tsx`
- Modify: `frontend/src/lib/store.ts`

- [ ] Add a visible Journal section to the reading packet with status, pin, revisit date, and outcome note.
- [ ] Rename history drawer copy from developer-ish local sessions to a decision journal.
- [ ] Preserve existing local storage fields and cloud-session compatibility.

### Task 6: Verification And Publish

**Files:**
- All changed files

- [ ] Run `pytest -q`.
- [ ] Run `cd frontend && npm run lint`.
- [ ] Run `cd frontend && npm run build`.
- [ ] Run `git diff --check`.
- [ ] Commit the intended I Ching changes.
- [ ] Push the resulting commit to `main`.
