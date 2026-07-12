# Divination Mechanics Corrections Design

## Goal

Make every displayed and persisted chart use one canonical mechanics model: the cast lines define the main hexagram, transformed branches come from the changed hexagram, and all six-relative labels remain referenced to the main hexagram palace. Correct the yarrow-stalk and Meihua casting engines, and make existing Supabase snapshots repairable without changing their original cast lines or AI prose.

## Canonical mechanics

- A hexagram's palace element is the sole reference element for its visible six relatives.
- Main-line stems and branches come from the main hexagram's Najia entry.
- Changed-line stems and branches come from the changed hexagram's Najia entry, while their six-relative prefix is recomputed from the main palace element.
- Six gods are derived once from the cast day's heavenly stem and reused in the table, structured AI payload, and legacy text rendering.
- Old yang (`9`) displays `○→` and changes to yin; old yin (`6`) displays `×→` and changes to yang.
- The legacy SQLite column names for binary direction and line order are adapted at the repository boundary so callers receive correctly named semantics without rewriting the tracked database.

## Casting engines

- Yarrow casting begins with 49 usable stalks. Each of three operations splits the current total, removes one stalk from the right heap, counts both heaps by fours, and subtracts the remainders plus the removed stalk. The final line value is the remaining stalk count divided by four.
- Three-coin casting remains unchanged.
- Three-number Meihua casting uses the first number for the upper trigram, the second for the lower trigram, and the third for the moving line.
- Time-based Meihua casting uses year-branch number plus lunar month and lunar day for the upper trigram; adding the hour-branch number yields the lower trigram and moving line.
- Hexagram line arrays always cross the core boundary bottom-to-top. The moving line keeps its original polarity and is encoded as `9` for moving yang or `6` for moving yin.

## Persistence and compatibility

- New sessions persist a normalized `najia_table`, `najia_data`, and `najia_text` built from the same derived rows.
- Existing public response fields remain available. Legacy binary and line-position keys are emitted with corrected values, with an explicit physical `position` added for unambiguous consumers.
- The existing backfill command gains Najia refresh support. It remains dry-run by default, is idempotent, preserves `session_id`, cast lines, question/context, AI output, and chat messages, and updates only snapshots that differ.
- Historical yarrow casts are not rerolled. Their recorded six lines remain authoritative; only deterministic derived mechanics are repaired.

## Verification

- Unit tests cover palace-element relations, the exact `雷水解 → 坎为水` correction, six-god consistency, symbol mapping, legacy metadata adaptation, deterministic yarrow transitions, seeded distribution bounds, Meihua number/time vectors, and line orientation.
- Backfill tests prove dry-run/idempotent patching and preservation of non-mechanics fields.
- Full Python tests, frontend lint, frontend production build, and a Supabase dry-run must pass before applying the production backfill.

