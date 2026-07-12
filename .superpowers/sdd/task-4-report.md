# Task 4 report: Idempotent historical snapshot repair

## Status

Implemented with a minimal RED → GREEN cycle. No live Supabase endpoint was accessed or mutated, per the task constraint.

## RED

Command before production changes:

```text
env ICHING_ARCHIVE_BASE=/tmp/iching-task4-red PYTHONPATH=src pytest -q tests/test_backfill_session_interpretations.py
```

Observed result:

```text
3 failed in 0.62s
```

The failures matched the missing behavior: the refresh function had no canonical Najia repository input, and the Supabase client had no owner-scoped optimistic-concurrency update primitive.

## GREEN and sanity verification

Focused command:

```text
env ICHING_ARCHIVE_BASE=/tmp/iching-task4-green PYTHONPATH=src pytest -q tests/test_backfill_session_interpretations.py
```

Observed result:

```text
3 passed in 0.62s
```

Full Python sanity command:

```text
env ICHING_ARCHIVE_BASE=/tmp/iching-task4-full PYTHONPATH=src pytest -q
```

Observed result:

```text
76 passed, 1 warning in 3.43s
```

The warning is the pre-existing Starlette `TestClient` / `httpx` deprecation warning.

## Implemented contract

- Rebuilds top-level `najia_table` / `najia_text` and nested `session_dict.najia_table` / `najia_text` / `najia_data` with the canonical session builder.
- Uses only saved lines and strict saved `current_time_str` parsing; missing or invalid input skips atomically without a wall-clock fallback.
- Preserves the original saved line representation, AI prose/analysis, response IDs, usage, reading brief, full text, context, chats, and unrelated keys.
- Is idempotent and does not reroll historical yarrow or other casts.
- Applies with `(session_id, user_id, original updated_at)` PostgREST predicates, requires exactly one returned row, and rejects payloads that attempt to modify `updated_at`.
- Keeps dry-run as the default and emits concise per-row skip/failure diagnostics to stderr.

## Files changed

- `tools/backfill_session_interpretations.py`
- `src/iching/integrations/supabase_client.py`
- `tests/test_backfill_session_interpretations.py`
- `README.md`
- `.superpowers/sdd/task-4-report.md`

## Scope note

The planned production dry-run/apply steps were intentionally not performed because this implementation task explicitly prohibited live Supabase access or mutation. The README contains the commands and safety guarantees for an authorized operator.

## Review fix: legacy top-level Najia data

A focused regression exposed that snapshots without `session_dict` retained stale top-level `najia_data` even though their top-level table and text were repaired.

RED:

```text
env ICHING_ARCHIVE_BASE=/tmp/iching-task4-legacy-red PYTHONPATH=src pytest -q tests/test_backfill_session_interpretations.py
1 failed, 2 passed in 0.67s
```

The legacy shape now receives canonical top-level `najia_data`; modern nested snapshots retain the existing patch contract.

GREEN:

```text
env ICHING_ARCHIVE_BASE=/tmp/iching-task4-legacy-green PYTHONPATH=src pytest -q tests/test_backfill_session_interpretations.py
3 passed in 0.58s
```
