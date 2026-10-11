from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "evidence" / "MANIFEST.sha256"
EXCLUDED_DIRS = {".git", ".venv", "build", "dist", "__pycache__", ".pytest_cache"}
EXCLUDED_FILES = {"evidence/MANIFEST.sha256"}


def included_files():
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT).as_posix()
        parts = path.relative_to(ROOT).parts
        if rel in EXCLUDED_FILES or any(part in EXCLUDED_DIRS or part.endswith(".egg-info") for part in parts):
            continue
        if path.suffix in {".pyc", ".whl"}:
            continue
        yield path, rel


def main() -> int:
    lines = []
    for path, rel in included_files():
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f"{digest}  {rel}")
    MANIFEST.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {len(lines)} entries to {MANIFEST.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
