# Recovery Algorithm

On open BasaltKV:

1. acquires the process lock;
2. requires and validates `wal.bkv` (or creates it for a new writable database);
3. validates the optional snapshot header, CRCs, bounded entry framing, strictly increasing key order, database identity, and sequence;
4. validates the WAL header, database identity, format, and CRC;
5. parses WAL records with bounded lengths and CRC validation;
6. enforces one non-interleaved transaction at a time and exact monotonic commit sequence;
7. rejects malformed control records, duplicate commits, reordered operations, unsupported versions, and arbitrary trailing bytes;
8. discards only a syntactically recognizable final uncommitted/torn transaction tail;
9. on writable open, truncates that recoverable tail back to the transaction boundary and `fsync`s the truncation;
10. replays committed transactions newer than the snapshot sequence;
11. restores `next sequence = last committed sequence + 1`;
12. removes only known non-authoritative temp files after authoritative state has validated.

Recovery never treats a temp compaction file as authoritative.
