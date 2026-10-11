# BasaltKV On-Disk Format v1

All integers are unsigned **big-endian**. All checksum fields use IEEE CRC-32 (`zlib.crc32`) over exactly the bytes stated below. All reserved/flags fields must be zero in v1. Parsers reject unsupported versions and out-of-bound length fields before payload reads.

## Files

- `wal.bkv` — required authoritative WAL.
- `snapshot.bkv` — optional authoritative compacted state.
- `LOCK` — advisory lock carrier; not logical state.
- `snapshot.bkv.tmp`, `wal.bkv.tmp` — non-authoritative temporary files.

## WAL header — 40 bytes

```text
+0   8   magic              ASCII "BKVWAL01"
+8   2   version            1
+10  2   flags              0
+12 16   database_id        opaque UUID bytes
+28  8   base_sequence      snapshot sequence required by this WAL
+36  4   crc32              CRC32(bytes 0..35)
```

A WAL with nonzero `base_sequence` requires `snapshot.bkv` with `snapshot.sequence >= base_sequence` and matching `database_id`.

## WAL record header — 36 bytes

```text
+0   4   magic              ASCII "BKVR"
+4   1   version            1
+5   1   type               BEGIN=1, PUT=2, DELETE=3, COMMIT=4
+6   2   reserved           0
+8   8   txid               transaction identity
+16  8   sequence           0 except COMMIT; COMMIT sequence == txid
+24  4   key_length
+28  4   value_length
+32  4   crc32
+36  ... key bytes || value bytes
```

The record CRC is over bytes 0..31 followed by the key/value payload (the CRC field itself is excluded).

v1 transaction grammar is strictly contiguous and non-interleaved:

```text
BEGIN(txid=N, seq=0)
  (PUT(txid=N, seq=0) | DELETE(txid=N, seq=0))*
COMMIT(txid=N, seq=N)
```

`N` must equal the previous committed sequence + 1. PUT permits zero-length keys/values. DELETE permits a zero-length key but must have `value_length = 0`. BEGIN/COMMIT must have both lengths zero.

A clean EOF after complete uncommitted records, or a final syntactically recognizable record torn at EOF, is an uncommitted crash tail. Recovery excludes the entire pending transaction and writable open truncates back to its BEGIN. Non-record arbitrary trailing bytes are corruption.

## Snapshot header — 56 bytes

```text
+0   8   magic              ASCII "BKVSNP01"
+8   2   version            1
+10  2   flags              0
+12 16   database_id
+28  8   sequence           logical commit sequence represented
+36  8   compaction_count
+44  8   entry_count
+52  4   crc32              CRC32(bytes 0..51)
```

## Snapshot entry

```text
+0   4   key_length
+4   4   value_length
+8   4   crc32
+12 ... key bytes || value bytes
```

Entry CRC is over `key_length || value_length || key || value` with the two lengths encoded as big-endian u32. Entries must be strictly increasing by raw key bytes, which simultaneously detects duplicate keys and gives deterministic snapshots.

## Bounds

- key length <= 1,048,576 bytes;
- value length <= 67,108,864 bytes;
- record aggregate length is additionally bounded before payload read.

## Compaction / atomic replacement

`snapshot.bkv.tmp` is written, flushed, and fsynced; then atomically replaces `snapshot.bkv`. The directory is fsynced where POSIX permits. Only then is `wal.bkv.tmp` created with `base_sequence = snapshot.sequence`, fsynced, atomically renamed over `wal.bkv`, and the directory fsynced again.

Temporary files never override authoritative filenames during recovery. A crash after snapshot replacement but before WAL reset is valid: recovery validates the old WAL's continuous history through the new snapshot sequence and skips already represented commits.

## Compatibility

Format v1 has no automatic migration. Any incompatible layout or semantic change requires a new version. Unknown versions fail closed.
