# Transaction Semantics

Write transactions stage `put`/`delete` operations in memory. `Transaction.get` returns a staged value/deletion first, otherwise it reads the database's currently committed state.

## Isolation

The contract is **read committed per read operation + read-your-writes**. It is not serializable and does not provide a long-lived read snapshot. A `scan()` call is coherent because it executes under one read lock; it observes one complete committed state.

## Commit

Writers are serialized. Under the database write lock BasaltKV:

1. chooses `sequence = last_sequence + 1`;
2. appends `BEGIN`, ordered mutation records, and `COMMIT(sequence)` to the WAL;
3. performs the selected durability barrier;
4. constructs the new logical state;
5. atomically replaces the in-memory state reference;
6. advances `last_sequence`;
7. returns the sequence to the caller.

If persistence fails, the new state is not published. A failed or completed transaction object is unusable thereafter. Empty transactions are rejected explicitly. Abort writes no logical change.

## Conflicts

Concurrent writers are deterministic at the storage level: they acquire the single writer critical section one at a time and receive monotonically increasing commit sequences. The final value of a key is the value written by the highest committed sequence affecting that key.
