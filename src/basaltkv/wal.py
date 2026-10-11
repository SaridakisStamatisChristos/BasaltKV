from __future__ import annotations

import os
import struct
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Iterable

from .constants import (
    FORMAT_VERSION,
    MAX_KEY_SIZE,
    MAX_RECORD_SIZE,
    MAX_VALUE_SIZE,
    REC_BEGIN,
    REC_COMMIT,
    REC_DELETE,
    REC_PUT,
    RECORD_MAGIC,
    WAL_MAGIC,
)
from .errors import CorruptionError, FormatVersionError, SizeLimitError
from .faults import crash_if

_WAL_PREFIX = struct.Struct(">8sHH16sQ")
_WAL_HEADER = struct.Struct(">8sHH16sQI")
_REC_NOCRC = struct.Struct(">4sBBHQQII")
_REC_HEADER = struct.Struct(">4sBBHQQIII")


@dataclass(frozen=True)
class WalHeader:
    db_id: bytes
    base_sequence: int


@dataclass(frozen=True)
class Operation:
    kind: int
    key: bytes
    value: bytes | None = None


@dataclass(frozen=True)
class CommittedTransaction:
    sequence: int
    operations: tuple[Operation, ...]


@dataclass(frozen=True)
class WalScan:
    header: WalHeader
    transactions: tuple[CommittedTransaction, ...]
    last_sequence: int
    truncate_to: int | None
    tail_truncated: bool


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


def encode_wal_header(db_id: bytes, base_sequence: int) -> bytes:
    if len(db_id) != 16:
        raise ValueError("db_id must be 16 bytes")
    prefix = _WAL_PREFIX.pack(WAL_MAGIC, FORMAT_VERSION, 0, db_id, base_sequence)
    return prefix + struct.pack(">I", _crc(prefix))


def decode_wal_header(raw: bytes) -> WalHeader:
    if len(raw) != _WAL_HEADER.size:
        raise CorruptionError("truncated WAL header")
    magic, version, flags, db_id, base, crc = _WAL_HEADER.unpack(raw)
    if magic != WAL_MAGIC:
        raise CorruptionError("invalid WAL magic")
    if version != FORMAT_VERSION:
        raise FormatVersionError(f"unsupported WAL version {version}")
    if flags != 0:
        raise CorruptionError("unsupported WAL flags")
    if _crc(raw[:-4]) != crc:
        raise CorruptionError("WAL header checksum mismatch")
    return WalHeader(db_id=db_id, base_sequence=base)


def create_wal(path: Path, db_id: bytes, base_sequence: int, *, sync: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "xb", buffering=0) as f:
        f.write(encode_wal_header(db_id, base_sequence))
        f.flush()
        if sync:
            os.fsync(f.fileno())
    if sync:
        _fsync_dir(path.parent)


def rewrite_wal_atomic(path: Path, db_id: bytes, base_sequence: int) -> None:
    tmp = path.with_name("wal.bkv.tmp")
    try:
        tmp.unlink()
    except FileNotFoundError:
        pass
    with open(tmp, "xb", buffering=0) as f:
        f.write(encode_wal_header(db_id, base_sequence))
        f.flush()
        os.fsync(f.fileno())
    crash_if("before_old_generation_removal")
    os.replace(tmp, path)
    _fsync_dir(path.parent)


def _validate_sizes(key: bytes, value: bytes | None) -> None:
    if len(key) > MAX_KEY_SIZE:
        raise SizeLimitError(f"key exceeds {MAX_KEY_SIZE} bytes")
    if value is not None and len(value) > MAX_VALUE_SIZE:
        raise SizeLimitError(f"value exceeds {MAX_VALUE_SIZE} bytes")


def _encode_record(kind: int, txid: int, seq: int, key: bytes = b"", value: bytes = b"") -> bytes:
    _validate_sizes(key, value if kind == REC_PUT else None)
    no_crc = _REC_NOCRC.pack(RECORD_MAGIC, FORMAT_VERSION, kind, 0, txid, seq, len(key), len(value))
    payload = key + value
    crc = _crc(no_crc + payload)
    return no_crc + struct.pack(">I", crc) + payload


def encode_transaction(sequence: int, operations: Iterable[Operation]) -> list[bytes]:
    ops = tuple(operations)
    records = [_encode_record(REC_BEGIN, sequence, 0)]
    for op in ops:
        if op.kind == REC_PUT:
            assert op.value is not None
            records.append(_encode_record(REC_PUT, sequence, 0, op.key, op.value))
        elif op.kind == REC_DELETE:
            records.append(_encode_record(REC_DELETE, sequence, 0, op.key, b""))
        else:
            raise ValueError("unknown operation kind")
    records.append(_encode_record(REC_COMMIT, sequence, sequence))
    return records


def append_transaction(path: Path, sequence: int, operations: Iterable[Operation], *, durable: bool) -> None:
    records = encode_transaction(sequence, operations)
    with open(path, "ab", buffering=0) as f:
        crash_if("before_wal_record_write")
        for idx, rec in enumerate(records):
            if idx == 0 and os.environ.get("BASALTKV_FAULT_POINT") == "during_wal_write":
                half = max(1, len(rec) // 2)
                f.write(rec[:half])
                os._exit(91)
            f.write(rec)
        crash_if("after_wal_write_before_flush")
        f.flush()
        crash_if("after_flush_before_fsync")
        if durable:
            os.fsync(f.fileno())
        crash_if("after_wal_fsync_before_ack")


def _read_record(f: BinaryIO, file_size: int) -> tuple[tuple[int, int, int, bytes, bytes], int] | None:
    start = f.tell()
    remaining = file_size - start
    if remaining == 0:
        return None
    if remaining < _REC_HEADER.size:
        tail = f.read()
        if tail.startswith(RECORD_MAGIC) or RECORD_MAGIC.startswith(tail):
            raise EOFError("torn record header")
        raise CorruptionError("unexpected trailing bytes in WAL")
    header = f.read(_REC_HEADER.size)
    magic, version, kind, reserved, txid, seq, key_len, value_len, crc = _REC_HEADER.unpack(header)
    if magic != RECORD_MAGIC:
        raise CorruptionError(f"invalid WAL record magic at offset {start}")
    if version != FORMAT_VERSION:
        raise FormatVersionError(f"unsupported WAL record version {version}")
    if reserved != 0:
        raise CorruptionError("nonzero WAL record reserved field")
    if kind not in {REC_BEGIN, REC_PUT, REC_DELETE, REC_COMMIT}:
        raise CorruptionError(f"unknown WAL record type {kind}")
    if key_len > MAX_KEY_SIZE or value_len > MAX_VALUE_SIZE or key_len + value_len > MAX_RECORD_SIZE:
        raise CorruptionError("WAL record length exceeds configured bounds")
    if kind in {REC_BEGIN, REC_COMMIT} and (key_len or value_len):
        raise CorruptionError("control WAL record carries payload")
    if kind == REC_DELETE and value_len:
        raise CorruptionError("delete WAL record carries a value")
    payload_len = key_len + value_len
    if file_size - f.tell() < payload_len:
        raise EOFError("torn WAL record payload")
    payload = f.read(payload_len)
    no_crc = header[:-4]
    if _crc(no_crc + payload) != crc:
        raise CorruptionError(f"WAL record checksum mismatch at offset {start}")
    return (kind, txid, seq, payload[:key_len], payload[key_len:]), start


def scan_wal(path: Path) -> WalScan:
    file_size = path.stat().st_size
    if file_size < _WAL_HEADER.size:
        raise CorruptionError("truncated WAL header")
    with open(path, "rb", buffering=0) as f:
        header = decode_wal_header(f.read(_WAL_HEADER.size))
        last_seq = header.base_sequence
        committed: list[CommittedTransaction] = []
        pending_txid: int | None = None
        pending_ops: list[Operation] = []
        pending_start: int | None = None
        tail_truncated = False
        truncate_to: int | None = None
        while True:
            record_start = f.tell()
            try:
                item = _read_record(f, file_size)
            except EOFError:
                tail_truncated = True
                truncate_to = pending_start if pending_start is not None else record_start
                break
            if item is None:
                break
            (kind, txid, seq, key, value), start = item
            if kind == REC_BEGIN:
                if pending_txid is not None:
                    raise CorruptionError("nested/interleaved WAL transaction")
                expected = last_seq + 1
                if txid != expected or seq != 0:
                    raise CorruptionError(f"impossible transaction id {txid}; expected {expected}")
                pending_txid = txid
                pending_ops = []
                pending_start = start
            elif kind in {REC_PUT, REC_DELETE}:
                if pending_txid is None or txid != pending_txid or seq != 0:
                    raise CorruptionError("WAL operation outside its active transaction")
                if kind == REC_PUT:
                    pending_ops.append(Operation(REC_PUT, key, value))
                else:
                    pending_ops.append(Operation(REC_DELETE, key, None))
            else:
                if pending_txid is None or txid != pending_txid:
                    raise CorruptionError("commit without matching active transaction")
                if seq != txid or seq != last_seq + 1:
                    raise CorruptionError("non-monotonic WAL commit sequence")
                committed.append(CommittedTransaction(seq, tuple(pending_ops)))
                last_seq = seq
                pending_txid = None
                pending_ops = []
                pending_start = None
        if pending_txid is not None and truncate_to is None:
            truncate_to = pending_start
        return WalScan(
            header=header,
            transactions=tuple(committed),
            last_sequence=last_seq,
            truncate_to=truncate_to,
            tail_truncated=tail_truncated,
        )


def truncate_wal(path: Path, size: int) -> None:
    if size < _WAL_HEADER.size:
        raise ValueError("refusing to truncate WAL below header")
    with open(path, "r+b", buffering=0) as f:
        f.truncate(size)
        f.flush()
        os.fsync(f.fileno())
