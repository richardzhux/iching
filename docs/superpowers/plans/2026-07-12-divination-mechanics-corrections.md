# Divination Mechanics Corrections Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Correct deterministic Najia mechanics, casting algorithms, UI symbols, AI payloads, and historical Supabase snapshots without changing recorded cast lines.

**Architecture:** Centralize palace-element and six-relative derivation in a small core module. Normalize legacy Najia repository data at its boundary, build every output from one derived row model, and make the existing backfill command recompute those deterministic fields. Keep casting algorithms isolated in `divination.py` with deterministic tests.

**Tech Stack:** Python 3.10+, pytest, SQLite Najia repository, FastAPI/Pydantic, Next.js 16/TypeScript, Supabase JSONB snapshots.

## Global Constraints

- Changed stems and branches come from the changed hexagram, but changed six relatives always use the main hexagram palace element.
- Old yang `9` displays `○→`; old yin `6` displays `×→`.
- Six gods must be identical in `najia_table`, `najia_data`, `najia_text`, and AI input for the same session.
- Historical cast lines and AI prose must never be regenerated or overwritten by the mechanics backfill.
- Backfill is dry-run by default and idempotent.
- No new runtime dependencies.

---

### Task 1: Canonical Najia derivation and normalized payloads

**Files:**
- Create: `src/iching/core/najia.py`
- Modify: `src/iching/integrations/najia_repository.py`
- Modify: `src/iching/services/session.py`
- Modify: `src/iching/integrations/ai.py`
- Test: `tests/test_najia_mechanics.py`
- Test: `tests/test_session_service.py`

**Interfaces:**
- Produces: `palace_element(palace: str) -> str`, `six_relative_label(reference_element: str, line_element: str) -> str`, `rebase_relation(relation: str, palace: str) -> str`.
- Produces: one normalized session Najia payload shared by rendering and AI.

- [ ] Write failing tests asserting `父母戊申金 → 官鬼戊申金` and `官鬼戊戌土 → 妻财戊戌土` when referenced to `震宫`.
- [ ] Run `pytest -q tests/test_najia_mechanics.py tests/test_session_service.py` and confirm the new assertions fail for the existing changed-entry lookup.
- [ ] Implement the five-element relation helpers and use them while building changed rows and structured payloads.
- [ ] Generate `najia_text` and all line `god` fields from the same day-stem-derived sequence; remove fixed source gods from AI-visible data.
- [ ] Adapt legacy binary and line-position database columns to correct public semantics at repository load time.
- [ ] Run the focused tests and confirm they pass.

### Task 2: Correct movement markers and frontend contract

**Files:**
- Modify: `src/iching/services/session.py`
- Modify: `frontend/src/components/workspace/najia-table.tsx`
- Modify: `tests/test_frontend_premium_contract.py`
- Test: `tests/test_najia_mechanics.py`

**Interfaces:**
- Consumes: `NajiaRow.movement_tag` containing `○→`, `×→`, or an empty string.
- Produces: the frontend renders `row.movement_tag` without re-deriving it.

- [ ] Add failing backend assertions for `6 → ×→` and `9 → ○→`, plus a frontend contract assertion that the hard-coded marker is absent.
- [ ] Run the focused Python tests and confirm failure.
- [ ] Correct `_movement_tag_from_value` and render `row.movement_tag` in the table.
- [ ] Run focused Python tests and `npm run lint` in `frontend/`.

### Task 3: Correct yarrow and Meihua casting

**Files:**
- Modify: `src/iching/core/divination.py`
- Create: `tests/test_divination_methods.py`

**Interfaces:**
- Keeps: `generate_lines(...) -> List[int]` in bottom-to-top order.
- Produces: `_calculate_trigrams(datetime) -> tuple[upper, lower, moving_line]` and `_calculate_from_numbers(...) -> tuple[upper, lower, moving_line]`.

- [ ] Add deterministic failing tests for yarrow remaining-stalk outcomes, a seeded distribution bounded around `1/16, 5/16, 7/16, 3/16`, first-number-as-upper Meihua behavior, the classical lunar time formula, and an upper-Zhen/lower-Kan orientation vector.
- [ ] Run `pytest -q tests/test_divination_methods.py` and confirm failures match the known root causes.
- [ ] Replace yarrow remainder classification with the remaining-stalk algorithm starting from 49.
- [ ] Correct Meihua number/time formulas and construct bottom-to-top lines while preserving the original moving-line polarity.
- [ ] Run focused tests and the complete Python suite.

### Task 4: Idempotent historical snapshot repair

**Files:**
- Modify: `tools/backfill_session_interpretations.py`
- Create: `tests/test_backfill_session_interpretations.py`
- Modify: `README.md`

**Interfaces:**
- Extends: `_compute_refreshed_snapshot(...)` to recompute `najia_table`, `najia_text`, and `session_dict.najia_data` from saved lines and saved cast time.
- Preserves: original lines, AI text, user context, and all unrelated snapshot keys.

- [ ] Add failing tests with a historical `雷水解 → 坎为水` snapshot and assert exact corrected changed relations, idempotency, and preservation of AI/user fields.
- [ ] Run `pytest -q tests/test_backfill_session_interpretations.py` and confirm failure.
- [ ] Reuse the canonical session Najia builder from Task 1 in the backfill path.
- [ ] Document dry-run and apply commands plus the non-reroll guarantee.
- [ ] Run focused tests, then a Supabase dry-run against all current sessions.
- [ ] After full verification, run the apply mode once and rerun dry-run expecting `changed: 0`.

### Task 5: Integrated verification and review

**Files:**
- Review all changed files from branch base `6207553`.

**Interfaces:**
- Produces no new runtime API; validates all previous tasks together.

- [ ] Run `env ICHING_ARCHIVE_BASE=/tmp/iching-verify PYTHONPATH=src pytest -q`.
- [ ] Run `npm run lint` and `npm run build` in `frontend/`.
- [ ] Run a deterministic mechanics audit across all 64 hexagrams and all five reference elements.
- [ ] Dispatch independent subagent code review with the complete branch diff and address every Critical or Important finding.
- [ ] Re-run the full verification commands after review fixes.

