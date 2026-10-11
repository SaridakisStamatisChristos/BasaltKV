# Claims Ledger

| Claim | State | Evidence / calibration |
|---|---|---|
| Atomic multi-key write publication | VERIFIED (local) | transaction tests and concurrent scan visibility |
| Durable-mode acknowledged commit survives immediate process kill | VERIFIED (local) | kill-after-ACK subprocess regression |
| Deterministic recovery excludes uncommitted/torn transaction tails | VERIFIED (local) | fault injection, torn-tail regression, model parity |
| Structural/checksum corruption fails closed for claimed classes | VERIFIED (local) | corruption suite; verifier output |
| Compaction preserves logical contents across tested crash boundaries | VERIFIED (local) | equivalence tests + five compaction crash points |
| Commit sequences remain monotonic across reopen/concurrent writers | VERIFIED (local) | sequence and concurrency regressions |
| Package/CLI install and execute from a wheel | VERIFIED (local) | packaging rehearsal recorded in local verification evidence |
| Linux/macOS/Windows and Python 3.11-3.13 compatibility | UNVERIFIED until final GitHub Actions matrix completes | workflow declares and executes matrix; source presence alone is not evidence |
| Production-ready | UNVERIFIED / NOT CLAIMED | no production workload, long-duration soak, filesystem matrix, independent security audit, or broad deployment evidence |
| SOTA/faster than other databases | N/A / NOT CLAIMED | benchmark has no competitor baseline |
| Cryptographic tamper authenticity | N/A / NOT CLAIMED | CRC32 detects accidental corruption; it is not a MAC/signature |
