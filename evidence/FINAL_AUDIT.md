# Final Adversarial Audit

This audit is authority-aware: local execution evidence closes local gates, while cross-platform compatibility claims are closed only by an observed GitHub Actions run on the implementation head.

## Hard invariant audit

1. **Acknowledged transaction disappear after process crash?** Local falsification found no counterexample; kill-after-ACK test reopens with the durable value. **VERIFIED locally.**
2. **Half a transaction visible?** Commit publication is one state swap under write lock; crash and concurrent-scan tests accept only all/none. **VERIFIED locally.**
3. **Aborted transaction survive recovery?** Abort writes no WAL; transaction tests/model parity remain unchanged. **VERIFIED locally.**
4. **Deleted key resurrect?** Delete/reopen/compaction tests remain absent after restart. **VERIFIED locally.**
5. **WAL truncation invent state?** Recognizable torn tail is excluded; arbitrary tail bytes fail. **VERIFIED locally.**
6. **Checksum corruption silently accepted?** WAL/snapshot checksum corruptions fail verifier/open. **VERIFIED locally.**
7. **Compaction lose live key?** Exact before/after model equality, repeated cycles, and crash points are green. **VERIFIED locally.**
8. **Compaction resurrect obsolete value?** Delete + compaction + reopen regression stays deleted. **VERIFIED locally.**
9. **Next commit sequence move backward?** Recovery restores strict last sequence and parser rejects discontinuity. **VERIFIED locally.**
10. **Concurrent writers violate atomicity?** Twenty concurrent writers produce one contiguous sequence set with final value matching max sequence. **VERIFIED locally.**
11. **Concurrent readers observe partial published state?** Coherent `scan()` readers never observe split paired writes in stress test. **VERIFIED locally.**
12. **Reopening twice cause unsafe writer behavior?** Second writer lock is rejected. **VERIFIED locally.**
13. **Malformed length trigger unbounded allocation?** Lengths are checked before payload read; huge-field regression fails closed. **VERIFIED locally.**
14. **Stale temp override newer database?** Temp files are never loaded as authoritative and are cleaned only after authoritative validation. **VERIFIED locally.**
15. **Repeated crash/recover/compact diverge from model?** Deterministic randomized model/cycle tests found no divergence. **VERIFIED locally.**
16. **Verifier detects every corruption class it claims?** Claimed structural/version/checksum/sequence/bounds classes have direct tests. Recognizable uncommitted tail is explicitly classified recoverable rather than corruption. **VERIFIED locally.**
17. **Documentation stronger than evidence?** Production/SOTA/serializable/network-filesystem/equivalent-Windows-power-loss claims are explicitly withheld. **VERIFIED by audit.**

## External CI closure

GitHub Actions run `38150293473` completed successfully on implementation commit
`24e17b7065a082f3432a5f32ccc3722cedfcbd1d`.

Observed green lanes:

- Linux, macOS, and Windows;
- Python 3.11, 3.12, and 3.13;
- static checks and full test suite on all nine OS/runtime combinations;
- package build and installed-wheel CLI smoke;
- evidence-manifest verification;
- benchmark smoke.

The evidence-closure commit that records this result changes legal/documentation/evidence
metadata only; it does not change BasaltKV runtime source or tests.

## Final verdict

**R7 ACCEPTANCE GATES CLOSED for the declared v0.1 experimental scope.**

This does **not** establish production readiness, formal verification, filesystem-independent
power-loss guarantees, cryptographic authenticity, or performance superiority.
