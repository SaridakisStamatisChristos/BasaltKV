# Requirement Coverage Ledger

`VERIFIED (local)` means directly executed local evidence on the implementation revision recorded in `VERIFICATION.md`. `VERIFIED (CI)` means the cross-platform gate has been observed in GitHub Actions. Evidence remains scoped to the documented revision, environment, and test surface.

| ID | Requirement / invariant | Criticality | Implementation | Acceptance evidence | State |
|---|---|---:|---|---|---|
| H1 | Atomic transaction visibility; no partial multi-key publication | HARD | `db.py` copy-and-swap under write lock | transaction + concurrent scan tests | VERIFIED (local) |
| H2 | Durable acknowledgement survives immediate process termination | HARD | WAL fsync before state publication/ack | kill-after-ACK subprocess test | VERIFIED (local) |
| H3 | Deleted keys do not resurrect | HARD | tombstone replay + snapshot live-state rewrite | delete/reopen/compaction tests | VERIFIED (local) |
| H4 | Recovery preserves logical commit order | HARD | strict contiguous sequence parser | reorder/sequence corruption + model tests | VERIFIED (local) |
| H5 | Uncommitted WAL data excluded | HARD | pending transaction discarded/truncated | torn-tail + crash-point tests | VERIFIED (local) |
| H6 | Corruption fails closed | HARD | magic/version/CRC/bounds/state-machine checks | corruption suite | VERIFIED (local) |
| H7 | Compaction preserves logical state | HARD | snapshot-first atomic replacement | equivalence + repeated model/cycle tests | VERIFIED (local) |
| H8 | Persistent snapshots represent one coherent logical commit point | HARD | snapshot created under database write lock with exact commit sequence | compaction equivalence + crash tests | VERIFIED (local) |
| H9 | Commit identity monotonically increases | HARD | `last_sequence + 1`, strict recovery continuity | reopen + concurrent writer tests | VERIFIED (local) |
| H10 | Explicit persistent format versioning | HARD | version fields in WAL/records/snapshot | unsupported-version test + format spec | VERIFIED (local) |
| R11 | Binary get/put/delete/exists/scan/stats/close | HARD | public `Database` API | core + CLI tests | VERIFIED (local) |
| R12 | Atomic multi-key transactions with abort/misuse errors | HARD | `Transaction` | core transaction tests | VERIFIED (local) |
| R13 | Owned WAL with framing/type/tx/order/checksum/commit marker | HARD | `wal.py` | parser tests + `STORAGE_FORMAT.md` | VERIFIED (local) |
| R14 | Deterministic recovery and next-sequence restoration | HARD | `Database.open`, `scan_wal` | reopen/model tests | VERIFIED (local) |
| R15 | Strong and relaxed durability modes are distinct | HARD | `DurabilityMode` | durable crash test + code/docs inspection | VERIFIED (local) |
| R16 | Concurrent readers and controlled writers without deadlock | HARD | process lock + writer-preferring RW lock | concurrency tests | VERIFIED (local) |
| R17 | Restart-safe compaction with safe temp handling | HARD | `snapshot.py`, `rewrite_wal_atomic` | five compaction crash points | VERIFIED (local) |
| R18 | Read-only integrity verifier | HARD | `verify.py`, CLI | CLI/corruption tests | VERIFIED (local) |
| R19 | Bounded parsing of malicious lengths | HARD | maximum key/value/record bounds | huge-length corruption test | VERIFIED (local) |
| R20 | Stable installable library + practical CLI | HARD | `pyproject.toml`, `cli.py` | local wheel/install smoke + CI package lane | VERIFIED (local + CI) |
| R21 | Crash/fault injection harness covers persistence boundaries | HARD | `faults.py` + subprocess tests | 10 deterministic crash points | VERIFIED (local) |
| R22 | Reference-model/property campaign | HARD | `test_model.py` | 6 seeds × 250 randomized operations | VERIFIED (local) |
| R23 | Reproducible benchmark harness + environment metadata | SHOULD | `benchmarks/bench.py` | committed local benchmark JSON + CI smoke | VERIFIED (local + CI) |
| R24 | Security/trust boundary and size/filesystem assumptions documented | HARD | `docs/SECURITY.md`, `DURABILITY.md` | documentation audit | VERIFIED (local) |
| R25 | Exact on-disk format specification + migration policy | HARD | format + migration docs | format parser tests/docs | VERIFIED (local) |
| R26 | Cross-platform CI executes actual gates | HARD | `.github/workflows/ci.yml` | GitHub Actions run `38151073381` on `4912e6568e7fa662f95e8f5a2b78acd13a2ae347` | VERIFIED (CI) |
| R27 | Evidence manifest hashes authoritative repository files | HARD | manifest tools | local manifest verification + CI manifest lane | VERIFIED (local + CI) |
| R28 | No hidden external database engine | HARD | standard-library core + static forbidden-import gate | static check | VERIFIED (local + CI) |
| R29 | Scope remains single-node embedded store | HARD | architecture/non-goals | source/docs audit | VERIFIED (local) |
