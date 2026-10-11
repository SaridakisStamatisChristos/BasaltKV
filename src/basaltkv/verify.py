from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .constants import LOCK_FILE, SNAPSHOT_FILE, WAL_FILE
from .errors import BasaltKVError, CorruptionError, LockError
from .locking import ProcessFileLock
from .snapshot import load_snapshot
from .wal import scan_wal


@dataclass(frozen=True)
class VerifyReport:
    ok: bool
    database_id: str | None = None
    snapshot_sequence: int = 0
    wal_base_sequence: int = 0
    last_sequence: int = 0
    committed_transactions: int = 0
    uncommitted_tail: bool = False
    messages: tuple[str, ...] = field(default_factory=tuple)


def verify_database(path: str | Path) -> VerifyReport:
    root = Path(path)
    messages: list[str] = []
    lock = ProcessFileLock(root / LOCK_FILE, exclusive=False)
    try:
        lock.acquire()
    except LockError as exc:
        return VerifyReport(ok=False, messages=(str(exc),))
    try:
        wal_path = root / WAL_FILE
        snap_path = root / SNAPSHOT_FILE
        if not wal_path.exists():
            return VerifyReport(ok=False, messages=("WAL is missing",))
        try:
            scan = scan_wal(wal_path)
            snapshot_seq = 0
            if snap_path.exists():
                snap = load_snapshot(snap_path)
                snapshot_seq = snap.sequence
                if snap.db_id != scan.header.db_id:
                    raise CorruptionError("snapshot/WAL database identity mismatch")
                if snapshot_seq < scan.header.base_sequence:
                    raise CorruptionError("snapshot sequence predates WAL base")
                if snapshot_seq > scan.last_sequence:
                    raise CorruptionError("snapshot sequence is ahead of WAL history")
            elif scan.header.base_sequence != 0:
                raise CorruptionError("WAL requires missing snapshot")
            if scan.truncate_to is not None:
                messages.append("recoverable uncommitted/torn WAL tail detected")
            messages.append("persistent framing, checksums, identities, and sequence structure verified")
            return VerifyReport(
                ok=True,
                database_id=scan.header.db_id.hex(),
                snapshot_sequence=snapshot_seq,
                wal_base_sequence=scan.header.base_sequence,
                last_sequence=scan.last_sequence,
                committed_transactions=len(scan.transactions),
                uncommitted_tail=scan.truncate_to is not None,
                messages=tuple(messages),
            )
        except BasaltKVError as exc:
            return VerifyReport(ok=False, messages=(str(exc),))
        except OSError as exc:
            return VerifyReport(ok=False, messages=(f"I/O error: {exc}",))
    finally:
        lock.release()
