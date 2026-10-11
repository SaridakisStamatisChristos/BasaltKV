from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "evidence" / "MANIFEST.sha256"
EXCLUDED_DIRS = {".git", ".venv", "build", "dist", "__pycache__", ".pytest_cache"}
EXCLUDED_FILES = {"evidence/MANIFEST.sha256"}


def authoritative_paths() -> set[str]:
    result = set()
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT).as_posix()
        parts = path.relative_to(ROOT).parts
        if rel in EXCLUDED_FILES or any(part in EXCLUDED_DIRS or part.endswith(".egg-info") for part in parts):
            continue
        if path.suffix in {".pyc", ".whl"}:
            continue
        result.add(rel)
    return result


def main() -> int:
    if not MANIFEST.is_file():
        print("MANIFEST VERIFY FAIL: manifest missing")
        return 1
    expected: dict[str, str] = {}
    for no, line in enumerate(MANIFEST.read_text(encoding="utf-8").splitlines(), 1):
        if not line:
            continue
        try:
            digest, rel = line.split("  ", 1)
        except ValueError:
            print(f"MANIFEST VERIFY FAIL: malformed line {no}")
            return 1
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            print(f"MANIFEST VERIFY FAIL: invalid digest line {no}")
            return 1
        if rel in expected:
            print(f"MANIFEST VERIFY FAIL: duplicate path {rel}")
            return 1
        expected[rel] = digest
    actual_paths = authoritative_paths()
    if set(expected) != actual_paths:
        print("MANIFEST VERIFY FAIL: file set mismatch")
        print("missing from manifest:", sorted(actual_paths - set(expected)))
        print("missing from tree:", sorted(set(expected) - actual_paths))
        return 1
    for rel, digest in expected.items():
        path = ROOT / rel
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != digest:
            print(f"MANIFEST VERIFY FAIL: checksum mismatch: {rel}")
            return 1
    print(f"MANIFEST VERIFY PASS: {len(expected)} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
