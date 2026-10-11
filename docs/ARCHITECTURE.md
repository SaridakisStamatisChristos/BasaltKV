# Architecture

## Topology lock

BasaltKV intentionally has five runtime components:

1. `db.py` — public database/transaction state machine and atomic in-memory publication.
2. `wal.py` — owned WAL framing, append, strict replay parser, tail recovery, WAL reset.
3. `snapshot.py` — owned snapshot framing, checksums, bounded parser, atomic snapshot replacement.
4. `locking.py` + `rwlock.py` — process and in-process concurrency boundaries.
5. `verify.py` — read-only integrity verifier built directly on the persistence parsers.

The CLI is an adapter, not a storage layer. There is no hidden database dependency or service process.

## State model

On open, BasaltKV loads the optional snapshot into an in-memory `dict[bytes, bytes]`, validates/replays WAL commits after the snapshot sequence, and publishes that recovered state. Each successful write transaction builds a new dictionary from the prior state and swaps the reference while holding the write lock. This makes publication atomic with respect to `get`/`scan` operations.

## Dependency graph

```text
CLI -> public API -> Database
                     |  |  \
                     |  |   -> RWLock
                     |  -> Snapshot
                     -> WAL
Database/Verifier -> ProcessFileLock
Verifier ---------> Snapshot + WAL parsers
```

Forbidden coupling: WAL/snapshot code must not call the public database API during parsing or verification; recovery must not verify itself by round-tripping through the same mutation path.

## Design choice

Python 3.11+ was chosen because correctness and auditability dominate raw throughput for v0.1, and the standard library provides the required binary struct packing, CRC32, `fsync`, atomic replace, threading, subprocess crash tests, and cross-platform file-lock primitives. A Rust implementation was considered for lower latency and stronger compile-time guarantees, but the execution environment did not provide a Rust toolchain; making Rust a hard assumption would have converted local execution evidence into unverified prose. The persistence format is language-neutral and can support a future independent implementation.
