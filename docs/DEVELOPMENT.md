# Development Guide

Requirements: Python 3.11+.

```bash
PYTHONPATH=src python tools/static_check.py
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python benchmarks/bench.py --quick
python tools/verify_manifest.py
```

Packaging rehearsal:

```bash
python -m pip wheel . --no-deps --no-build-isolation -w dist
python -m venv .venv
.venv/bin/python -m pip install dist/basaltkv-0.1.0-py3-none-any.whl
.venv/bin/basaltkv --version
```

On Windows use `.venv\\Scripts\\python` and `.venv\\Scripts\\basaltkv.exe`.

Any persistence-format change must update `docs/STORAGE_FORMAT.md`, format-version policy, fixtures/tests where relevant, and the evidence ledger. Incompatible drift without a version change is a defect.
