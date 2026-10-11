# Concurrency Model

BasaltKV has two lock layers.

- `LOCK` is an OS advisory lock. Normal writable opens request an exclusive lock; read-only opens request a shared/read lock. This prevents incompatible concurrent writer processes. The OS releases the advisory lock on process exit, so a crash does not leave a permanent logical lock lease.
- `RWLock` is an in-process writer-preferring readers/writer lock. Multiple readers may run concurrently. Commits, compaction, and close obtain the write side and therefore cannot overlap one another or an active reader critical section.

Lock order is fixed: the process lock is acquired once during open, then operation-level `RWLock` scopes are used. No operation reacquires the process lock, avoiding lock-order cycles.

Compaction currently holds the write lock for its full persistence sequence. This prioritizes correctness over latency and is a documented v0.1 limitation.
