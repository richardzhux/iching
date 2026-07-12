# Task 2 report: Correct movement markers and frontend contract

## Status

Implemented on `codex/fix-divination-mechanics` with strict RED → GREEN test order.

## RED

Command:

```text
env ICHING_ARCHIVE_BASE=/tmp/iching-task2-red PYTHONPATH=src pytest -q tests/test_najia_mechanics.py tests/test_frontend_premium_contract.py
```

Observed result before production changes:

```text
2 failed, 28 passed in 0.63s
```

The two failures matched the intended missing behavior:

- `_movement_tag_from_value(9)` returned `×→` instead of `○→`; the inverse mapping for `6` was therefore also wrong.
- The Najia table frontend did not consume `row.movement_tag` and instead contained a hard-coded `×→` marker.

The backend contract also asserts that `7`, `8`, and `None` produce an empty string.

## GREEN

Focused command:

```text
env ICHING_ARCHIVE_BASE=/tmp/iching-task2-green PYTHONPATH=src pytest -q tests/test_najia_mechanics.py tests/test_frontend_premium_contract.py
```

Observed result after implementation:

```text
30 passed in 0.52s
```

Frontend lint command:

```text
cd frontend && npm run lint
```

Observed result:

```text
eslint exited 0
```

Lint emitted the existing informational warning that `baseline-browser-mapping` data is over two months old.

Full Python regression command:

```text
env ICHING_ARCHIVE_BASE=/tmp/iching-task2-full PYTHONPATH=src pytest -q
```

Observed result:

```text
62 passed, 1 warning in 3.19s
```

The warning is the existing Starlette `TestClient` / `httpx` deprecation warning.

## Files changed

- `src/iching/services/session.py`
  - Corrected old yin `6 → ×→` and old yang `9 → ○→`; all other values remain unmarked.
- `frontend/src/components/workspace/najia-table.tsx`
  - Renders the backend-provided `row.movement_tag` and retains the neutral dot for an empty tag.
- `tests/test_najia_mechanics.py`
  - Added exact backend assertions for `9`, `6`, `7`, `8`, and `None`.
- `tests/test_frontend_premium_contract.py`
  - Requires `row.movement_tag` and rejects hard-coded `×→` or `○→` frontend literals.
- `.superpowers/sdd/task-2-report.md`
  - Records the TDD evidence and scope review.

## Self-review

- Verified the marker meanings match the plan's global constraints.
- Verified stable yin, stable yang, and missing values remain empty rather than acquiring movement markers.
- Verified the frontend consumes the backend contract instead of re-deriving movement semantics from `is_moving`.
- Verified empty movement tags preserve the existing neutral-dot presentation.
- Verified no casting, backfill, Supabase, database, dependency, or unrelated session behavior was changed.
- Verified `git diff --check` passes.
