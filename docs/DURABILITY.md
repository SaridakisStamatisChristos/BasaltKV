# Durability and Crash Model

## Default durable commit

For `DurabilityMode.DURABLE`, acknowledgement occurs only after the full transaction WAL bytes (including the commit marker) are written and `fsync(wal)` returns successfully. Logical publication happens after that barrier.

Persistence order:

```text
BEGIN + mutations + COMMIT -> write -> flush -> fsync(WAL) -> publish memory state -> acknowledge
```

A crash before the complete commit marker leaves no committed transaction. A process crash after WAL `fsync` but before API acknowledgement can expose the fully committed transaction after restart; this is an allowed acknowledgement-uncertainty outcome.

## Relaxed mode

`RELAXED` omits per-commit `fsync`. It is intended only where the caller accepts loss of recently acknowledged commits on OS/power failure.

## Compaction ordering

```text
write snapshot.tmp -> flush -> fsync(snapshot.tmp)
-> atomic replace snapshot -> fsync(directory where supported)
-> write wal.tmp(base = snapshot sequence) -> fsync(wal.tmp)
-> atomic replace WAL -> fsync(directory where supported)
```

Snapshot replacement intentionally precedes WAL reset. If a crash occurs between them, recovery validates the old WAL through the new snapshot sequence and skips already snapshotted commits. Resetting the WAL first would create an unrecoverable data-loss window and is therefore forbidden.

## Hardware/filesystem assumptions

The strongest guarantee assumes a local filesystem/storage stack where successful `fsync` provides the durability semantics advertised by the OS, same-filesystem `os.replace` is atomic, and the storage device does not falsely report persistence. POSIX directory `fsync` is used after authoritative renames. Windows does not expose a portable directory-`fsync` equivalent through Python; atomic replacement is used, so the power-loss guarantee around directory-entry persistence is weaker and explicitly not claimed equivalent to POSIX. Network/distributed filesystems are unsupported unless independently validated.
