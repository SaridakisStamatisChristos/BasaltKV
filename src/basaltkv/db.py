from __future__ import annotations

import os
import time
import uuid
from enum import Enum
from pathlib import Path
from threading import Lock
from typing import Iterator

from .constants import (
    LOCK_FILE,
    MAX_KEY_SIZE,
    MAX_VALUE_SIZE,
    REC_DELETE,
    REC_PUT,
    SNAPSHOT_FILE,
    SNAPSHOT_TMP_FILE,
    WAL_FILE,
    WAL_TMP_FILE,
)
from .errors import ClosedError, CorruptionError, ReadOnlyError, SizeLimitError, TransactionError
from .faults import crash_if
from .locking import ProcessFileLock
from .rwlock import RWLock
from .snapshot import load_snapshot, write_snapshot_atomic
from .wal import Operation, append_transaction, create_wal, rewrite_wal_atomic, scan_wal, truncate_wal


class DurabilityMode(str, Enum):
    DURABLE = "durable"
    RELAXED = "relaxed"


def _as_bytes(value: bytes | bytearray | memoryview, name: str) -> bytes:
    if not isinstance(value, (bytes, bytearray, memoryview)):
        raise TypeError(f"{name} must be bytes-like")
    return bytes(value)


def _validate_key(key: bytes) -> None:
    if len(key) > MAX_KEY_SIZE:
        raise SizeLimitError(f"key exceeds {MAX_KEY_SIZE} bytes")


def _validate_value(value: bytes) -> None:
    if len(value) > MAX_VALUE_SIZE:
        raise SizeLimitError(f"value exceeds {MAX_VALUE_SIZE} bytes")


class Database:
    def __init__(self) -> None:
        raise RuntimeError("use Database.open()")

    @classmethod
    def open(
        cls,
        path: str | os.PathLike[str],
        *,
        create: bool = True,
        read_only: bool = False,
        durability: DurabilityMode | str = DurabilityMode.DURABLE,
    ) -> "Database":
        started = time.perf_counter()
        root = Path(path)
        if not root.exists():
            if not create or read_only:
                raise FileNotFoundError(root)
            root.mkdir(parents=True)
        if not root.is_dir():
            raise NotADirectoryError(root)

        self = object.__new__(cls)
        self._path = root
        self._read_only = read_only
        self._durability = DurabilityMode(durability)
        self._rw = RWLock()
        self._sequence_lock = Lock()
        self._closed = False
        self._session_transactions = 0
        self._session_puts = 0
        self._session_deletes = 0

        self._process_lock = ProcessFileLock(root / LOCK_FILE, exclusive=not read_only)
        self._process_lock.acquire()
        try:
            wal_path = root / WAL_FILE
            snap_path = root / SNAPSHOT_FILE
            if not wal_path.exists():
                if snap_path.exists():
                    raise CorruptionError("snapshot exists but WAL is missing")
                if read_only or not create:
                    raise FileNotFoundError(wal_path)
                create_wal(wal_path, uuid.uuid4().bytes, 0, sync=True)

            wal_scan = scan_wal(wal_path)
            if snap_path.exists():
                snap = load_snapshot(snap_path)
                if snap.db_id != wal_scan.header.db_id:
                    raise CorruptionError("snapshot/WAL database identity mismatch")
                if snap.sequence < wal_scan.header.base_sequence:
                    raise CorruptionError("snapshot sequence predates WAL base sequence")
                if snap.sequence > wal_scan.last_sequence:
                    raise CorruptionError("snapshot sequence is ahead of WAL history")
                state = dict(snap.state)
                snapshot_seq = snap.sequence
                compactions = snap.compaction_count
            else:
                if wal_scan.header.base_sequence != 0:
                    raise CorruptionError("nonzero WAL base requires a snapshot")
                state = {}
                snapshot_seq = 0
                compactions = 0

            for tx in wal_scan.transactions:
                if tx.sequence <= snapshot_seq:
                    continue
                for op in tx.operations:
                    if op.kind == REC_PUT:
                        assert op.value is not None
                        state[op.key] = op.value
                    else:
                        state.pop(op.key, None)

            self._db_id = wal_scan.header.db_id
            self._state = state
            self._last_sequence = wal_scan.last_sequence
            self._compaction_count = compactions
            self._recovery_truncated_tail = wal_scan.truncate_to is not None
            if wal_scan.truncate_to is not None and not read_only:
                truncate_wal(wal_path, wal_scan.truncate_to)

            if not read_only:
                # Known temp names can never outrank verified authoritative files.
                for tmp_name in (SNAPSHOT_TMP_FILE, WAL_TMP_FILE):
                    try:
                        (root / tmp_name).unlink()
                    except FileNotFoundError:
                        pass
            self._recovery_duration_ms = (time.perf_counter() - started) * 1000.0
            return self
        except Exception:
            self._process_lock.release()
            raise

    @property
    def path(self) -> Path:
        return self._path

    @property
    def durability(self) -> DurabilityMode:
        return self._durability

    @property
    def read_only(self) -> bool:
        return self._read_only

    def _ensure_open(self) -> None:
        if self._closed:
            raise ClosedError("database is closed")

    def get(self, key: bytes | bytearray | memoryview) -> bytes | None:
        key_b = _as_bytes(key, "key")
        _validate_key(key_b)
        with self._rw.read():
            self._ensure_open()
            value = self._state.get(key_b)
            return None if value is None else bytes(value)

    def exists(self, key: bytes | bytearray | memoryview) -> bool:
        return self.get(key) is not None

    def put(self, key: bytes | bytearray | memoryview, value: bytes | bytearray | memoryview) -> int:
        tx = self.transaction()
        tx.put(key, value)
        return tx.commit()

    def delete(self, key: bytes | bytearray | memoryview) -> int:
        tx = self.transaction()
        tx.delete(key)
        return tx.commit()

    def transaction(self) -> "Transaction":
        self._ensure_open()
        if self._read_only:
            raise ReadOnlyError("database is read-only")
        return Transaction(self)

    def scan(self, prefix: bytes | bytearray | memoryview | None = None) -> list[tuple[bytes, bytes]]:
        if prefix is not None:
            prefix_b = _as_bytes(prefix, "prefix")
            _validate_key(prefix_b)
        else:
            prefix_b = None
        with self._rw.read():
            self._ensure_open()
            items = self._state.items()
            if prefix_b is not None:
                items = ((k, v) for k, v in items if k.startswith(prefix_b))
            return [(bytes(k), bytes(v)) for k, v in sorted(items)]

    def _commit(self, ops: list[Operation], durability: DurabilityMode | None = None) -> int:
        if not ops:
            raise TransactionError("cannot commit an empty transaction")
        mode = durability or self._durability
        with self._rw.write():
            self._ensure_open()
            if self._read_only:
                raise ReadOnlyError("database is read-only")
            sequence = self._last_sequence + 1
            append_transaction(self._path / WAL_FILE, sequence, ops, durable=(mode is DurabilityMode.DURABLE))
            # Only expose the transaction after its complete WAL commit marker has been written,
            # and in DURABLE mode only after fsync succeeded.
            new_state = self._state.copy()
            puts = deletes = 0
            for op in ops:
                if op.kind == REC_PUT:
                    assert op.value is not None
                    new_state[op.key] = op.value
                    puts += 1
                else:
                    new_state.pop(op.key, None)
                    deletes += 1
            self._state = new_state
            self._last_sequence = sequence
            self._session_transactions += 1
            self._session_puts += puts
            self._session_deletes += deletes
            return sequence

    def compact(self) -> int:
        with self._rw.write():
            self._ensure_open()
            if self._read_only:
                raise ReadOnlyError("database is read-only")
            new_count = self._compaction_count + 1
            write_snapshot_atomic(
                self._path / SNAPSHOT_FILE,
                self._db_id,
                self._last_sequence,
                new_count,
                self._state,
            )
            # Snapshot replacement precedes WAL reset. A crash in between leaves the old WAL,
            # which recovery validates and safely skips through snapshot.sequence.
            rewrite_wal_atomic(self._path / WAL_FILE, self._db_id, self._last_sequence)
            crash_if("during_compaction_cleanup")
            self._compaction_count = new_count
            return new_count

    def flush(self) -> None:
        with self._rw.read():
            self._ensure_open()
            if self._read_only:
                return
            with open(self._path / WAL_FILE, "r+b", buffering=0) as f:
                os.fsync(f.fileno())

    def stats(self) -> dict[str, int | float | str | bool]:
        with self._rw.read():
            self._ensure_open()
            wal = self._path / WAL_FILE
            snap = self._path / SNAPSHOT_FILE
            return {
                "keys": len(self._state),
                "live_bytes": sum(len(k) + len(v) for k, v in self._state.items()),
                "wal_bytes": wal.stat().st_size if wal.exists() else 0,
                "snapshot_bytes": snap.stat().st_size if snap.exists() else 0,
                "last_commit_sequence": self._last_sequence,
                "compaction_count": self._compaction_count,
                "recovery_duration_ms": round(self._recovery_duration_ms, 3),
                "recovery_truncated_tail": self._recovery_truncated_tail,
                "session_transactions": self._session_transactions,
                "session_puts": self._session_puts,
                "session_deletes": self._session_deletes,
                "durability": self._durability.value,
                "read_only": self._read_only,
            }

    def close(self) -> None:
        if self._closed:
            return
        with self._rw.write():
            if self._closed:
                return
            self._closed = True
            self._process_lock.release()

    def __enter__(self) -> "Database":
        self._ensure_open()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


class Transaction:
    def __init__(self, db: Database) -> None:
        self._db = db
        self._writes: dict[bytes, bytes | None] = {}
        self._active = True

    def _ensure_active(self) -> None:
        if not self._active:
            raise TransactionError("transaction is no longer active")

    def put(self, key: bytes | bytearray | memoryview, value: bytes | bytearray | memoryview) -> "Transaction":
        self._ensure_active()
        key_b = _as_bytes(key, "key")
        value_b = _as_bytes(value, "value")
        _validate_key(key_b)
        _validate_value(value_b)
        self._writes[key_b] = value_b
        return self

    def delete(self, key: bytes | bytearray | memoryview) -> "Transaction":
        self._ensure_active()
        key_b = _as_bytes(key, "key")
        _validate_key(key_b)
        self._writes[key_b] = None
        return self

    def get(self, key: bytes | bytearray | memoryview) -> bytes | None:
        self._ensure_active()
        key_b = _as_bytes(key, "key")
        _validate_key(key_b)
        if key_b in self._writes:
            value = self._writes[key_b]
            return None if value is None else bytes(value)
        return self._db.get(key_b)

    def commit(self, *, durability: DurabilityMode | str | None = None) -> int:
        self._ensure_active()
        mode = None if durability is None else DurabilityMode(durability)
        ops: list[Operation] = []
        for key, value in self._writes.items():
            if value is None:
                ops.append(Operation(REC_DELETE, key, None))
            else:
                ops.append(Operation(REC_PUT, key, value))
        try:
            sequence = self._db._commit(ops, mode)
            self._active = False
            return sequence
        except Exception:
            # A failed commit remains explicitly unusable; callers must create a new transaction.
            self._active = False
            raise

    def abort(self) -> None:
        self._ensure_active()
        self._writes.clear()
        self._active = False

    def __enter__(self) -> "Transaction":
        self._ensure_active()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if not self._active:
            return
        if exc_type is None:
            self.commit()
        else:
            self.abort()
