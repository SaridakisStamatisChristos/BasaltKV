# Operations and Troubleshooting

## Integrity check

Run:

```bash
basaltkv verify /path/to/db
```

Exit 0 means the verifier accepted the structural/checksum/sequence contract. Exit 2 means corruption, I/O failure, or inability to obtain the read lock. Verification never mutates logical contents.

## Recovery notices

A recoverable final torn/uncommitted WAL tail is reported by the verifier. The next writable open truncates it back to the beginning of the incomplete transaction and `fsync`s that repair. Arbitrary trailing bytes, checksum failures, unsupported versions, and impossible sequence structure are fail-closed and require restoring a known-good copy or forensic repair outside BasaltKV.

## Backup

For v0.1, take backups only while the database is closed, or copy a database after a successful compaction while holding exclusive application-level control. Online backup is not implemented.

## Disk full / fsync failure

Treat a commit exception as not acknowledged. Do not retry the same `Transaction` object; create a new one after resolving the storage problem. Reopen/verify before continuing if the failure occurred during persistence.
