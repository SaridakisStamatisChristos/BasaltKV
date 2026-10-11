# Claims Ledger

| Claim | State | Evidence / calibration |
|---|---|---|
| Atomic multi-key write publication | VERIFIED (local) | transaction tests and concurrent scan visibility |
| Durable-mode acknowledged commit survives immediate process kill | VERIFIED (local) | kill-after-ACK subprocess regression |
| Deterministic recovery excludes uncommitted/torn transaction tails | VERIFIED (local) | fault injection, torn-tail regression, model parity |
| Structural/checksum corruption fails closed for claimed classes | VERIFIED (local) | corruption suite; verifier output |
| Compaction preserves logical contents across tested crash boundaries | VERIFIED (local) | equivalence tests + five compaction crash points |
| Commit sequences remain monotonic across reopen/concurrent writers | VERIFIED (local) | sequence and concurrency regressions |
| Package/CLI install and execute from a wheel | VERIFIED (local + CI) | local packaging rehearsal plus GitHub Actions run `38150293473` package lane |
| Linux/macOS/Windows and Python 3.11-3.13 compatibility | VERIFIED (CI) | GitHub Actions run `38150293473`: all nine OS/runtime test lanes green |
| Evidence manifest verifies on implementation head | VERIFIED (CI) | GitHub Actions run `38150293473` manifest lane green |
| Benchmark harness executes reproducibly in CI | VERIFIED (CI smoke) | GitHub Actions run `38150293473` benchmark-smoke lane green; no competitor claim |
| Production-ready | UNVERIFIED / NOT CLAIMED | no production workload, long-duration soak, filesystem matrix, independent security audit, or broad deployment evidence |
| SOTA/faster than other databases | N/A / NOT CLAIMED | benchmark has no competitor baseline |
| Cryptographic tamper authenticity | N/A / NOT CLAIMED | CRC32 detects accidental corruption; it is not a MAC/signature |
