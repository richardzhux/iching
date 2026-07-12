# Task 3 report: Correct yarrow and Meihua casting

## Status

Implemented on `codex/fix-divination-mechanics` with strict, minimal RED → GREEN coverage.

## RED

Focused casting command before production changes:

```text
env ICHING_ARCHIVE_BASE=/tmp/iching-task3-red PYTHONPATH=src pytest -q tests/test_divination_methods.py
```

Observed result:

```text
8 failed, 1 passed in 0.33s
```

The failures matched the intended defects: the yarrow implementation did not expose the canonical operation boundaries, Gregorian time fields produced the wrong Meihua trigrams, and line construction was top-to-bottom with reversed moving-line polarity. The number tuple test initially passed because the old and new tuple values were numerically identical despite reversed caller semantics, so it was immediately replaced before production edits with the required `[101, 202, 303]` generated-line orientation vector.

The tightened number vector and session consistency test then failed as expected:

```text
2 failed in 0.52s
```

## GREEN

Focused command:

```text
env ICHING_ARCHIVE_BASE=/tmp/iching-task3-green PYTHONPATH=src pytest -q tests/test_divination_methods.py tests/test_session_service.py
```

Observed result:

```text
23 passed in 2.11s
```

Full Python regression command:

```text
env ICHING_ARCHIVE_BASE=/tmp/iching-task3-full PYTHONPATH=src pytest -q
```

Observed result:

```text
72 passed, 1 warning in 3.11s
```

The warning is the existing Starlette `TestClient` / `httpx` deprecation warning.

## Files changed

- `src/iching/core/divination.py`
  - Models the three canonical yarrow operations from 49 stalks, yielding exact `6/7/8/9 = 1/16, 5/16, 7/16, 3/16` elementary weights.
  - Uses the first number as the upper trigram and the second as the lower trigram.
  - Uses lunar month/day, Chinese-New-Year year branch, and hour branch for classical time casting.
  - Returns bottom-to-top lines and retains the moving line's original polarity.
- `src/iching/services/session.py`
  - Resolves the cast timestamp before generating lines and injects the same timestamp into Meihua generation.
- `tests/test_divination_methods.py`
  - Adds deterministic operation-boundary/weight, number-order, lunar-time, year-boundary, and orientation vectors.
- `tests/test_session_service.py`
  - Adds one custom-timestamp consistency regression.
- `.superpowers/sdd/task-3-report.md`
  - Records RED/GREEN and scope evidence.

## Scope and concerns

- Coin casting, Najia, frontend, backfill, Supabase, and dependencies are unchanged.
- Historical lines are not rerolled.
- The Meihua calendar calculation uses the already-declared `sxtwl` dependency.
- The only test-suite warning is pre-existing and unrelated to this task.
