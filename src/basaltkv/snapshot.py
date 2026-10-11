from __future__ import annotations

import os
import struct
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .constants import FORMAT_VERSION, MAX_KEY_SIZE, MAX_VALUE_SIZE, SNAPSHOT_MAGIC, SNAPSHOT_TMP_FILE
from .errors import CorruptionError, FormatVersionError
from .faults import crash_if

_SNAP_PREFIX = struct.Struct(">8sHH16sQQQ")
_SNAP_HEADER = struct.Struct(">8sHH16sQQQI")
_ENTRY_HEADER = struct.Struct(">III")


@dataclass(frozen=True)
class Snapshot:
    db_id: bytes
    sequence: int
    compaction_count: int
    state: dict[bytes, bytes]


def _crc(data: bytes) -> int:
    return zlib.crc32(data) & 0xFFFFFFFF


def _fsync_dir(path: Path) -> None:
    if os.name == "nt":
        return
    flags = getattr(os, "O_DIRECTORY", 0) | os.O_RDONLY
    fd = os.open(path, flags)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def encode_snapshot(db_id: bytes, sequence: int, compaction_count: int, state: Mapping[bytes, bytes]) -> bytes:
    items = sorted(state.items())
    prefix = _SNAP_PREFIX.pack(SNAPSHOT_MAGIC, FORMAT_VERSION, 0, db_id, sequence, compaction_count, len(items))
    out = bytearray(prefix)
    out.extend(struct.pack(">I", _crc(prefix)))
    for key, value in items:
        if len(key) > MAX_KEY_SIZE or len(value) > MAX_VALUE_SIZE:
            raise ValueError("snapshot entry exceeds configured bounds")
        payload = key + value
        entry_prefix = struct.pack(">II", len(key), len(value))
        out.extend(_ENTRY_HEADER.pack(len(key), len(value), _crc(entry_prefix + payload)))
        out.extend(payload)
    return bytes(out)


def write_snapshot_atomic(path: Path, db_id: bytes, sequence: int, compaction_count: int, state: Mapping[bytes, bytes]) -> None:
    tmp = path.with_name(SNAPSHOT_TMP_FILE)
    data = encode_snapshot(db_id, sequence, compaction_count, state)
    try:
        tmp.unlink()
    except FileNotFoundError:
        pass
    with open(tmp, "xb", buffering=0) as f:
        if os.environ.get("BASALTKV_FAULT_POINT") == "during_snapshot_creation":
            half = max(1, len(data) // 2)
            f.write(data[:half])
            f.flush()
            os._exit(91)
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    crash_if("after_snapshot_write_before_rename")
    os.replace(tmp, path)
    crash_if("after_rename_before_dir_sync")
    _fsync_dir(path.parent)


def load_snapshot(path: Path) -> Snapshot:
    data = path.read_bytes()
    if len(data) < _SNAP_HEADER.size:
        raise CorruptionError("truncated snapshot header")
    magic, version, flags, db_id, seq, compactions, count, crc = _SNAP_HEADER.unpack_from(data, 0)
    if magic != SNAPSHOT_MAGIC:
        raise CorruptionError("invalid snapshot magic")
    if version != FORMAT_VERSION:
        raise FormatVersionError(f"unsupported snapshot version {version}")
    if flags != 0:
        raise CorruptionError("unsupported snapshot flags")
    if _crc(data[: _SNAP_HEADER.size - 4]) != crc:
        raise CorruptionError("snapshot header checksum mismatch")
    offset = _SNAP_HEADER.size
    state: dict[bytes, bytes] = {}
    last_key: bytes | None = None
    for _ in range(count):
        if len(data) - offset < _ENTRY_HEADER.size:
            raise CorruptionError("truncated snapshot entry header")
        key_len, value_len, entry_crc = _ENTRY_HEADER.unpack_from(data, offset)
        offset += _ENTRY_HEADER.size
        if key_len > MAX_KEY_SIZE or value_len > MAX_VALUE_SIZE:
            raise CorruptionError("snapshot entry length exceeds configured bounds")
        total = key_len + value_len
        if len(data) - offset < total:
            raise CorruptionError("truncated snapshot entry payload")
        key = data[offset : offset + key_len]
        value = data[offset + key_len : offset + total]
        offset += total
        if _crc(struct.pack(">II", key_len, value_len) + key + value) != entry_crc:
            raise CorruptionError("snapshot entry checksum mismatch")
        if last_key is not None and key <= last_key:
            raise CorruptionError("snapshot keys are duplicate or out of order")
        last_key = key
        state[key] = value
    if offset != len(data):
        raise CorruptionError("unexpected trailing bytes in snapshot")
    return Snapshot(db_id=db_id, sequence=seq, compaction_count=compactions, state=state)
