# Requirement Coverage Ledger

States are R7 evidence states. `VERIFIED` below means directly executed local evidence on the revision used to generate this manifest; GitHub CI is a separate external gate.

| ID | Requirement / invariant | Criticality | Implementation | Acceptance evidence | Local state |
|---|---|---:|---|---|---|
| H1 | Atomic transaction visibility; no partial multi-key publication | HARD | `db.py` copy-and-swap under write lock | transaction + concurrent scan tests | VERIFIED |
| H2 | Durable acknowledgement survives immediate process termination | HARD | WAL fsync before state publication/ack | kill-after-ACK subprocess test | VERIFIED |
| H3 | Deleted keys do not resurrect | HARD | tombstone replay + snapshot live-state rewrite | delete/reopen/compaction tests | VERIFIED |
| H4 | Recovery preserves logical commit order | HARD | strict contiguous sequence parser | reorder/sequence corruption + model tests | VERIFIED |
| H5 | Uncommitted WAL data excluded | HARD | pending transaction discarded/truncated | torn-tail + crash-point tests | VERIFIED |
| H6 | Corruption fails closed | HARD | magic/version/CRC/bounds/state-machine checks | corruption suite | VERIFIED |
| H7 | Compaction preserves logical state | HARD | snapshot-first atomic replacement | equivalence + repeated model/cycle tests | VERIFIED |
| H8 | Persistent snapshots represent one coherent logical commit point | HARD | snapshot created under database write lock with exact commit sequence | compaction equivalence + crash tests | VERIFIED |
| H9 | Commit identity monotonically increases | HARD | `last_sequence + 1`, strict recovery continuity | reopen + concurrent writer tests | VERIFIED |
| H10 | Explicit persistent format versioning | HARD | version fields in WAL/records/snapshot | unsupported-version test + format spec | VERIFIED |
| R11 | Binary get/put/delete/exists/scan/stats/close | HARD | public `Database` API | core + CLI tests | VERIFIED |
| R12 | Atomic multi-key transactions with abort/misuse errors | HARD | `Transaction` | core transaction tests | VERIFIED |
| R13 | Owned WAL with framing/type/tx/order/checksum/commit marker | HARD | `wal.py` | parser tests + `STORAGE_FORMAT.md` | VERIFIED |
| R14 | Deterministic recovery and next-sequence restoration | HARD | `Database.open`, `scan_wal` | reopen/model tests | VERIFIED |
| R15 | Strong and relaxed durability modes are distinct | HARD | `DurabilityMode` | durable crash test + code/docs inspection | VERIFIED |
| R16 | Concurrent readers and controlled writers without deadlock | HARD | process lock + writer-preferring RW lock | concurrency tests | VERIFIED |
| R17 | Restart-safe compaction with safe temp handling | HARD | `snapshot.py`, `rewrite_wal_atomic` | five compaction crash points | VERIFIED |
| R18 | Read-only integrity verifier | HARD | `verify.py`, CLI | CLI/corruption tests | VERIFIED |
| R19 | Bounded parsing of malicious lengths | HARD | maximum key/value/record bounds | huge-length corruption test | VERIFIED |
| R20 | Stable installable library + practical CLI | HARD | `pyproject.toml`, `cli.py` | local wheel/install smoke | VERIFIED |
| R21 | Crash/fault injection harness covers persistence boundaries | HARD | `faults.py` + subprocess tests | 10 deterministic crash points | VERIFIED |
| R22 | Reference-model/property campaign | HARD | `test_model.py` | 6 seeds × 250 randomized operations | VERIFIED |
| R23 | Reproducible benchmark harness + environment metadata | SHOULD | `benchmarks/bench.py` | committed local benchmark JSON | VERIFIED |
| R24 | Security/trust boundary and size/filesystem assumptions documented | HARD | `docs/SECURITY.md`, `DURABILITY.md` | documentation audit | VERIFIED |
| R25 | Exact on-disk format specification + migration policy | HARD | format + migration docs | format parser tests/docs | VERIFIED |
| R26 | Cross-platform CI executes actual gates | HARD | `.github/workflows/ci.yml` | requires observed GitHub Actions run on final commit | UNVERIFIED |
| R27 | Evidence manifest hashes authoritative repository files | HARD | manifest tools | local manifest verification | VERIFIED |
| R28 | No hidden external database engine | HARD | standard-library core + static forbidden-import gate | static check | VERIFIED |
| R29 | Scope remains single-node embedded store | HARD | architecture/non-goals | source/docs audit | VERIFIED |
