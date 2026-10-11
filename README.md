# BasaltKV

**A crash-consistent embedded transactional key-value store with verifiable durability.**

BasaltKV is a local-first, single-node embedded database for software tools, local services, build systems, research infrastructure, and applications that want durable binary key/value storage without an external database server.

BasaltKV owns its persistence format, write-ahead log (WAL), recovery logic, transaction semantics, in-memory index, compaction protocol, and integrity verifier. It does **not** wrap SQLite, RocksDB, LMDB, LevelDB, Redis, PostgreSQL, or another database engine. The v0.1 runtime uses only the Python standard library.

## Status

v0.1 is an **alpha / experimental systems implementation**. The repository contains executable correctness, crash-injection, corruption, model-parity, concurrency, packaging, and manifest gates. See `evidence/FINAL_AUDIT.md` and `evidence/CLAIMS.md` before relying on a claim.

## Core properties

- arbitrary binary keys and values, including empty keys/values;
- atomic multi-key write transactions;
- durable WAL acknowledgement in the default `durable` mode;
- deterministic restart recovery and uncommitted-tail exclusion;
- monotonic commit sequences;
- concurrent readers with serialized writers;
- atomic scan visibility across a commit;
- checksummed, versioned WAL and snapshot formats;
- restart-safe snapshot compaction;
- fail-closed handling of unsupported versions and structural/checksum corruption;
- read-only `verify` command;
- CLI plus intentionally small library API;
- deterministic crash/fault injection for persistence boundaries.

## Install

```bash
python -m pip install .
basaltkv --version
```

Python 3.11+ is required. There are no runtime dependencies.

## Library quick start

```python
from basaltkv import Database

with Database.open("./data") as db:
    db.put(b"answer", b"42")

    with db.transaction() as tx:
        tx.put(b"left", b"same-commit")
        tx.put(b"right", b"same-commit")

    assert db.get(b"answer") == b"42"
    print(db.scan(prefix=b"a"))
    db.compact()
```

Transactions provide **read-committed per-call reads plus read-your-writes**. BasaltKV does not claim serializable isolation. `scan()` is one coherent reader operation and therefore sees either the state before or after a committed multi-key transaction, never a partially applied in-memory state.

## CLI

```bash
basaltkv init ./data
basaltkv put ./data hello world
basaltkv get ./data hello --output text
basaltkv scan ./data
basaltkv info ./data
basaltkv verify ./data
basaltkv compact ./data
basaltkv delete ./data hello
```

Binary CLI data uses explicit `text`, `hex`, or `base64` encodings; values are never silently decoded.

## Durability modes

`durable` is the default. A commit is acknowledged only after the complete WAL transaction, including its commit marker, has been written, flushed, and `fsync` has succeeded. Only then is the new logical state published to readers.

`relaxed` flushes Python/user-space buffers but does not call `fsync` for each commit. It can lose acknowledged state after OS/power failure and must not be treated as equivalent to `durable`.

The exact hardware/filesystem assumptions and rename/directory-sync boundaries are documented in `docs/DURABILITY.md`.

## Persistence layout

A database directory contains:

```text
LOCK                 advisory process lock file
wal.bkv              versioned checksummed write-ahead log
snapshot.bkv         optional compacted logical snapshot
snapshot.bkv.tmp     temporary compaction file; never authoritative
wal.bkv.tmp          temporary WAL reset file; never authoritative
```

See `docs/STORAGE_FORMAT.md` for the byte-level format.

## Limits

- maximum key size: 1 MiB;
- maximum value size: 64 MiB;
- all persisted length fields are bounds-checked before payload reads/allocations;
- writers are serialized by design;
- compaction currently blocks database operations while it snapshots and resets the WAL.

## Verify

`basaltkv verify <path>` is read-only. It checks format versions, header/record framing, CRC32 checksums, database identity, commit-sequence continuity, transaction structure, and snapshot/WAL sequence agreement. A syntactically recognizable final torn/uncommitted WAL tail is reported as recoverable; arbitrary trailing bytes are rejected.

## Development gates

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python tools/static_check.py
PYTHONPATH=src python benchmarks/bench.py --quick
python tools/verify_manifest.py
```

CI runs the real test and package commands on Linux, macOS, and Windows across supported Python versions.

## What BasaltKV does **not** guarantee

BasaltKV v0.1 does not provide serializable transactions, multi-process write concurrency, distributed replication, consensus, clustering, sharding, SQL, remote multi-tenancy, authentication, encryption at rest, network-filesystem safety, protection against malicious code in the same trusted process, or survival of storage-device lies that violate documented `fsync`/atomic-rename assumptions. It is not yet claimed production-ready.

The repository contains no open-source license grant. Public visibility is not permission to copy, modify, or redistribute; the repository owner must add a license if one is intended.

## Documentation

- `docs/ARCHITECTURE.md`
- `docs/STORAGE_FORMAT.md`
- `docs/DURABILITY.md`
- `docs/TRANSACTIONS.md`
- `docs/RECOVERY.md`
- `docs/COMPACTION.md`
- `docs/CONCURRENCY.md`
- `docs/OPERATIONS.md`
- `docs/SECURITY.md`
- `docs/DEVELOPMENT.md`
- `docs/BENCHMARKS.md`
- `docs/LIMITATIONS.md`
- `docs/MIGRATIONS.md`
- `evidence/`
