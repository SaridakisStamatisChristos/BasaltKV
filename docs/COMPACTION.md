# Compaction

Compaction rewrites current logical state into a sorted checksummed snapshot and then resets the WAL base sequence.

The snapshot contains only live key/value pairs. Tombstones are historical WAL implementation details, not part of the public logical state; removing them during compaction cannot resurrect a key because the replacement WAL starts at the snapshot's exact sequence.

The equivalence contract is:

```text
logical_state(before) == logical_state(after)
last_commit_sequence(before) == last_commit_sequence(after)
```

A new snapshot is fully written and `fsync`ed before atomic replacement. Only after the authoritative snapshot exists is a new WAL header for that snapshot sequence written, `fsync`ed, and atomically installed. Known temp files are safe to remove only after recovery has validated authoritative state.
