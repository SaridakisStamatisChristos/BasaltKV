from __future__ import annotations

import os
from pathlib import Path

from .errors import LockError


class ProcessFileLock:
    """Cross-process advisory lock using only the Python standard library."""

    def __init__(self, path: Path, *, exclusive: bool) -> None:
        self.path = path
        self.exclusive = exclusive
        self._file = None

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        f = open(self.path, "a+b", buffering=0)
        if f.seek(0, os.SEEK_END) == 0:
            f.write(b"\0")
            f.flush()
        f.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                mode = msvcrt.LK_NBLCK if self.exclusive else msvcrt.LK_NBRLCK
                msvcrt.locking(f.fileno(), mode, 1)
            else:
                import fcntl
                mode = fcntl.LOCK_EX if self.exclusive else fcntl.LOCK_SH
                fcntl.flock(f.fileno(), mode | fcntl.LOCK_NB)
        except OSError as exc:
            f.close()
            kind = "writer" if self.exclusive else "reader"
            raise LockError(f"database {kind} lock is already held: {self.path}") from exc
        self._file = f

    def release(self) -> None:
        f = self._file
        if f is None:
            return
        try:
            if os.name == "nt":
                import msvcrt
                f.seek(0)
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        finally:
            f.close()
            self._file = None

    def __enter__(self) -> "ProcessFileLock":
        self.acquire()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.release()
