from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECK_DIRS = [ROOT / "src", ROOT / "tests", ROOT / "tools", ROOT / "benchmarks"]
FORBIDDEN_CORE_IMPORTS = {"sqlite3", "rocksdb", "lmdb", "plyvel", "redis", "psycopg", "sqlalchemy"}


def main() -> int:
    errors: list[str] = []
    for base in CHECK_DIRS:
        for path in sorted(base.rglob("*.py")):
            text = path.read_text(encoding="utf-8")
            try:
                tree = ast.parse(text, filename=str(path))
            except SyntaxError as exc:
                errors.append(f"{path.relative_to(ROOT)}: syntax error: {exc}")
                continue
            for no, line in enumerate(text.splitlines(), 1):
                if line.rstrip() != line:
                    errors.append(f"{path.relative_to(ROOT)}:{no}: trailing whitespace")
                if "\t" in line:
                    errors.append(f"{path.relative_to(ROOT)}:{no}: tab character")
            if path.is_relative_to(ROOT / "src" / "basaltkv"):
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        names = {n.name.split(".")[0] for n in node.names}
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        names = {node.module.split(".")[0]}
                    else:
                        continue
                    bad = names & FORBIDDEN_CORE_IMPORTS
                    if bad:
                        errors.append(f"{path.relative_to(ROOT)}: forbidden database dependency import: {sorted(bad)}")
    if errors:
        print("STATIC CHECK FAILED")
        print("\n".join(errors))
        return 1
    print("STATIC CHECK PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
