# Task 1 report: Canonical Najia derivation and normalized payloads

## Status

Implemented on `codex/fix-divination-mechanics` with strict RED → GREEN test order.

## RED

Command:

```text
env ICHING_ARCHIVE_BASE=/tmp/iching-task1 PYTHONPATH=src pytest -q tests/test_najia_mechanics.py tests/test_session_service.py
```

Observed result before production changes:

```text
4 failed, 12 passed in 2.23s
```

The four failures matched the intended missing/corrupt behavior:

- `iching.core.najia` did not exist.
- `get_by_bottom("100010")` returned `山水蒙` instead of asymmetric `水雷屯` because the database binary columns were exposed backwards.
- `雷水解 → 坎为水` reused the changed hexagram's native six-relative labels instead of rebasing them to `震宫`.
- AI prompt/follow-up context consumed `najia_data` containing fixed source gods instead of the normalized session table.

## GREEN

Focused command:

```text
env ICHING_ARCHIVE_BASE=/tmp/iching-task1 PYTHONPATH=src pytest -q tests/test_najia_mechanics.py tests/test_session_service.py
```

Observed result after implementation:

```text
16 passed in 2.65s
```

Full Python regression command:

```text
env ICHING_ARCHIVE_BASE=/tmp/iching-task1 PYTHONPATH=src pytest -q
```

Observed result:

```text
58 passed, 1 warning in 3.06s
```

The warning is the existing Starlette `TestClient` / `httpx` deprecation warning.

The direct audited vector produced:

```text
changed relations: 父母戊子水, 妻财戊戌土, 官鬼戊申金, 子孙戊午火, 妻财戊辰土, 兄弟戊寅木
six gods: 青龙, 玄武, 白虎, 腾蛇, 勾陈, 朱雀
block_text == najia_text: True
changed hidden values: all empty
```

## Files changed

- `src/iching/core/najia.py`
  - Added palace-element lookup, five-element six-relative derivation, and relation rebasing.
- `src/iching/integrations/najia_repository.py`
  - Adapted the tracked SQLite database's reversed legacy binary and line-position column names at load time.
  - Added explicit physical `position` to line payloads.
- `src/iching/services/session.py`
  - Rebased changed relations to the main palace.
  - Added a reusable normalized session Najia builder.
  - Generated `najia_table`, `najia_data`, and `najia_text` from the same rows and day-stem god sequence.
  - Cleared changed-entry hidden values rather than exposing changed-palace-relative hidden labels.
- `src/iching/integrations/ai.py`
  - Made initial and follow-up AI contexts prefer the normalized `najia_table`, with legacy `najia_data` fallback.
- `tests/test_najia_mechanics.py`
  - Added relation, repository-boundary, exact transformed-vector, text/god, hidden-value, and AI-context tests.
- `tests/test_session_service.py`
  - Added the shared normalized payload contract at the AI handoff.
- `.superpowers/sdd/task-1-report.md`
  - Recorded the TDD evidence and compatibility review.

## Compatibility notes

- `data/najia.db` is unchanged. Legacy physical column names are normalized only after repository load.
- Public `binary_bottom_to_top` and `binary_top_to_bottom` now match their names. The session no longer reverses core bottom-to-top binaries before repository lookup.
- Public `position_top` is now the ordinal from the top, `position_bottom` is the ordinal from the bottom, and `position` explicitly carries the physical line number (`1` bottom through `6` top).
- Existing session response keys remain available: `najia_table`, `najia_data`, `najia_text`, and `najia_data.block_text`.
- AI uses the normalized table for new session payloads, but still accepts legacy payloads without a table.
- Changed hidden values are cleared because their original six-relative prefixes are referenced to the changed palace; exposing them unchanged would be mechanically false.
- Task 2 movement-marker behavior, frontend code, casting engines, backfill, and Supabase were not changed.

## Self-review

- Verified all five element relationships are covered by the derivation algorithm rather than vector-specific substitutions.
- Verified the asymmetric `水雷屯` vector catches both binary direction and line-position inversion.
- Verified the exact `雷水解 → 坎为水` top-to-bottom relations and 丁-day gods across table and structured payloads.
- Verified legacy text is generated from the normalized rows and shares the same gods.
- Verified fixed source gods cannot enter new-session AI prompts when a normalized table is present.
- Verified no tracked database rewrite or new runtime dependency was introduced.
- Verified no Task 2–4 file or behavior was intentionally modified.

## Review fixes: legacy AI sanitization and unknown-stem safety

Two Important review findings were addressed in a second strict RED → GREEN cycle.

### RED

Command:

```text
env ICHING_ARCHIVE_BASE=/tmp/iching-task1-review PYTHONPATH=src pytest -q tests/test_najia_mechanics.py tests/test_session_service.py
```

Observed before the review fixes:

```text
3 failed, 16 passed in 2.32s
```

Expected failures:

- The initial AI prompt exposed fixed source gods when a historical payload had `najia_data` but no `najia_table`.
- The follow-up AI context exposed the same fixed source gods.
- `_build_najia_table()` fell back to fixed database gods for an unknown day stem.

### GREEN

Focused command:

```text
env ICHING_ARCHIVE_BASE=/tmp/iching-task1-review PYTHONPATH=src pytest -q tests/test_najia_mechanics.py tests/test_session_service.py
```

Observed after the fixes:

```text
19 passed in 2.16s
```

Full regression command:

```text
env ICHING_ARCHIVE_BASE=/tmp/iching-task1-review PYTHONPATH=src pytest -q
```

Observed result:

```text
61 passed, 1 warning in 2.83s
```

The warning remains the pre-existing Starlette `TestClient` / `httpx` deprecation warning.

### Fix and compatibility evidence

- Day-stem six-god derivation now lives in `iching.core.najia` and is shared by session normalization and legacy AI sanitization.
- Missing or unknown day stems now emit six blank gods; source database gods are never used as a fallback.
- When `najia_table` is absent, AI receives a deep-copied, sanitized legacy payload rather than raw `najia_data`.
- Legacy `block_text` is removed from AI-visible fallback data because it embeds fixed source gods.
- Legacy line gods are recomputed from saved `day_stem` and physical line position; invalid/missing positions produce blank gods.
- Changed relations are rebased to the main palace when metadata is sufficient, and changed hidden values are cleared.
- Both initial and follow-up AI paths use the same sanitizer and have focused regression coverage.
- The sanitizer does not mutate the persisted/session payload supplied by the caller.
