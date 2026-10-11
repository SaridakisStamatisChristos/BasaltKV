# Failure / Repair Ledger

Historical failures are retained even after repair.

## F-001 — Torn WAL header misclassified as arbitrary trailing bytes

- **Reproducer:** crash injection `during_wal_write` wrote half of the first BEGIN record; recovery raised `CorruptionError` instead of recognizing a torn final record.
- **Violated requirement:** H5 / R21.
- **Observed failure:** crash recovery could not reopen a database after a legitimate process death during a WAL header write.
- **Classification:** parser boundary defect.
- **Earliest invalidated phase:** SPEC (torn-tail recognition rule was underspecified in implementation condition).
- **Root cause:** short-tail logic used `RECORD_MAGIC.startswith(tail)`, which only works when the tail is shorter than the 4-byte magic; a partial header longer than four bytes begins with the magic but does not satisfy that predicate.
- **Repair:** classify a short tail as syntactically recognizable when either the tail starts with full `BKVR` magic or the tail itself is a prefix of the magic.
- **Regression:** `test_commit_crash_points_preserve_atomicity` at `during_wal_write`; `test_torn_final_record_is_recoverable_and_truncated_on_writable_open`.
- **Reverification:** full local suite green after repair.

## F-002 — Compaction crash test used an invalid expected-state oracle

- **Reproducer:** each compaction subtest recreated a database containing `k0..k9`, but helper asserted that unrelated key `base` existed.
- **Violated requirement:** evidence validity for H7/R21; implementation was not implicated.
- **Observed failure:** five compaction crash subtests failed despite recovered state being internally valid.
- **Classification:** test-oracle defect.
- **Earliest invalidated phase:** VERIFY.
- **Root cause:** baseline initialization in the subtest changed without updating helper assertion.
- **Repair:** capture the complete pre-crash logical state through an independent read-only open and compare recovered state to that oracle.
- **Regression:** `test_compaction_crash_points_are_restart_safe` across all five compaction crash points.
- **Reverification:** full local suite green after repair.

## F-003 — Evidence manifest included generated packaging metadata

- **Reproducer:** first manifest generation after local wheel build included `src/basaltkv.egg-info/*` and an empty scratch `tests/test_core.py.tmp`.
- **Violated requirement:** R27 evidence-manifest stability.
- **Observed failure:** source manifest contained non-authoritative/generated files and would vary after packaging cleanup.
- **Classification:** evidence-closure defect.
- **Earliest invalidated phase:** MANIFEST/EVIDENCE.
- **Root cause:** exclusion logic handled fixed build directories and `.pyc` files but not directories ending in `.egg-info`; scratch file had not been removed.
- **Repair:** remove scratch/generated metadata and make both manifest generator and independent verifier exclude any path component ending in `.egg-info`.
- **Regression:** regenerate manifest after packaging; verifier requires an exact authoritative file-set match.
- **Reverification:** final manifest verification passes on the cleaned tree.
