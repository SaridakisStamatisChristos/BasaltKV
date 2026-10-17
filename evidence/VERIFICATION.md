# Verification Record

This document is the canonical verification summary for BasaltKV v0.1. It records observed evidence and its scope; it does not promote BasaltKV beyond its documented alpha / experimental status.

## Evidence boundaries

Local execution evidence closes only the local gates described below. Cross-platform compatibility is supported by observed GitHub Actions runs. These results do **not** establish production readiness, formal verification, filesystem-independent power-loss guarantees, cryptographic authenticity, or performance superiority.

## Local verification

Recorded implementation environment:

- Linux x86_64 container;
- Python 3.13.5;
- standard-library runtime dependencies only.

Observed gates:

- `PYTHONPATH=src python -m unittest discover -s tests -v` — **PASS**, 34 test methods.
- randomized reference model — **PASS**, seeds `1, 7, 19, 42, 1337, 99173`, 250 steps each.
- deterministic write crash points — **PASS**, 5 points.
- deterministic compaction crash points — **PASS**, 5 points.
- corruption suite — **PASS** for checksum, unsupported version, impossible/reordered transaction structure, duplicate commit, huge length, stale temp, snapshot corruption, missing required snapshot, zero-length/truncated WAL header, random appended bytes, and recoverable torn final transaction handling.
- `PYTHONPATH=src python tools/static_check.py` — **PASS**.
- wheel build with pinned `setuptools==82.0.1` using `--no-build-isolation` — **PASS**; built `basaltkv-0.1.0-py3-none-any.whl`.
- clean virtual-environment wheel install plus `basaltkv --version`, init/put/get/verify smoke — **PASS**.
- quick reproducibility benchmark — **PASS** as a harness; the committed results in `BENCHMARK_LOCAL.json` are single-environment observations, not comparative claims.
- evidence manifest — generated after authoritative files were frozen and independently checked by `tools/verify_manifest.py`.

## Invariant audit

The following failure questions were exercised by the repository's tests, fault injection, model checks, and source/documentation audit:

1. **Can an acknowledged durable transaction disappear after immediate process termination?** No counterexample was observed in the kill-after-ACK regression.
2. **Can half of a committed multi-key transaction become visible?** No; publication is a single state swap under the write lock, and crash/concurrent-scan tests accept only all-or-none visibility.
3. **Can an aborted transaction survive recovery?** No observed counterexample; abort writes no WAL and transaction/model tests remain consistent.
4. **Can a deleted key resurrect after reopen or compaction?** No observed counterexample in delete/reopen/compaction regressions.
5. **Can WAL truncation invent state?** Recognizable torn tails are excluded; arbitrary trailing bytes fail closed.
6. **Can checksum corruption be silently accepted?** Tested WAL/snapshot checksum corruptions fail verification/open.
7. **Can compaction lose live keys or resurrect obsolete values?** Exact before/after model equality, delete regressions, repeated cycles, and compaction crash points are green.
8. **Can the next commit sequence move backward?** Recovery restores the last sequence and rejects discontinuity.
9. **Can concurrent writers violate transaction atomicity or sequence monotonicity?** The concurrency regression produces a contiguous sequence set with final state matching the highest sequence.
10. **Can concurrent readers observe a partially published transaction?** Coherent `scan()` readers did not observe split paired writes in the stress regression.
11. **Can two writable opens bypass the process lock?** The second writer is rejected.
12. **Can malformed persisted lengths trigger unbounded allocation?** Length bounds are checked before payload reads; the huge-length corruption regression fails closed.
13. **Can stale temporary files override authoritative state?** Temporary files are never loaded as authoritative and are cleaned only after authoritative validation.
14. **Can repeated crash/recover/compact cycles diverge from the reference model?** The deterministic randomized model/cycle tests found no divergence.
15. **Does the verifier detect the corruption classes it claims?** Direct tests cover structural, version, checksum, sequence, and bounds failures; recognizable uncommitted tails are classified as recoverable rather than corruption.
16. **Are documentation claims stronger than the evidence?** Production-readiness, SOTA, serializable-isolation, network-filesystem, cryptographic-authenticity, and equivalent cross-platform power-loss claims remain explicitly withheld.

## GitHub Actions evidence

Two observed CI runs establish the current cross-platform gate history:

- Run `38150293473` completed successfully on implementation commit `24e17b7065a082f3432a5f32ccc3722cedfcbd1d`.
- Run `38151073381` completed successfully on repository head `4912e6568e7fa662f95e8f5a2b78acd13a2ae347`; that head changed legal/documentation/evidence metadata only relative to the implementation commit.

Observed green lanes included:

- Linux, macOS, and Windows;
- Python 3.11, 3.12, and 3.13;
- static checks and the full test suite on all nine OS/runtime combinations;
- package build and installed-wheel CLI smoke;
- evidence-manifest verification;
- benchmark smoke.

## Canonical evidence set

The active evidence surface is intentionally limited to:

- `ASSUMPTIONS.md`;
- `BENCHMARK_LOCAL.json`;
- `CLAIMS.md`;
- `REQUIREMENTS.md`;
- `VERIFICATION.md`;
- `MANIFEST.sha256`.

Implementation-session repair chronology and superseded audit/session notes remain available in Git history, but they are not canonical product evidence.
