# Local Verification Record

Execution environment used for the R7 campaign:

- Linux x86_64 container
- Python 3.13.5
- standard-library runtime dependencies only

Observed gates before manifest generation:

- `PYTHONPATH=src python -m unittest discover -s tests -v` — **PASS**, 34 test methods.
- randomized reference model — **PASS**, seeds `1, 7, 19, 42, 1337, 99173`, 250 steps each.
- deterministic write crash points — **PASS**, 5 points.
- deterministic compaction crash points — **PASS**, 5 points.
- corruption suite — **PASS** for checksum, unsupported version, impossible/reordered transaction structure, duplicate commit, huge length, stale temp, snapshot corruption, missing required snapshot, zero-length/truncated WAL header, random appended bytes, and recoverable torn final transaction handling.

Additional observed gates:

- `PYTHONPATH=src python tools/static_check.py` — **PASS**.
- wheel build with pinned `setuptools==82.0.1` using `--no-build-isolation` — **PASS**; built `basaltkv-0.1.0-py3-none-any.whl`.
- clean venv wheel install + `basaltkv --version` + init/put/get/verify smoke — **PASS**.
- quick reproducibility benchmark — **PASS** as a harness; results are stored in `BENCHMARK_LOCAL.json` and are not comparative claims.
- evidence manifest — generated only after authoritative files are frozen, then independently verified by `tools/verify_manifest.py`.
