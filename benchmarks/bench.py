from __future__ import annotations

import argparse
import json
import os
import platform
import random
import shutil
import sys
import tempfile
import time
from pathlib import Path

from basaltkv import Database


def timed(fn):
    start = time.perf_counter()
    result = fn()
    return time.perf_counter() - start, result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--output")
    args = ap.parse_args()
    cfg = {
        "puts": 1000 if args.quick else 10000,
        "gets": 3000 if args.quick else 50000,
        "batches": 100 if args.quick else 1000,
        "batch_size": 10,
        "mixed": 1000 if args.quick else 10000,
    }
    rng = random.Random(20261011)
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "benchdb"
        db = Database.open(path)
        put_s, _ = timed(lambda: [db.put(f"k{i}".encode(), rng.randbytes(64)) for i in range(cfg["puts"])])
        keys = [f"k{rng.randrange(cfg['puts'])}".encode() for _ in range(cfg["gets"])]
        get_s, _ = timed(lambda: [db.get(k) for k in keys])

        def batches():
            for b in range(cfg["batches"]):
                with db.transaction() as tx:
                    for i in range(cfg["batch_size"]):
                        tx.put(f"batch-{b}-{i}".encode(), rng.randbytes(32))
        batch_s, _ = timed(batches)

        def mixed():
            for i in range(cfg["mixed"]):
                if rng.random() < 0.7:
                    db.get(f"k{rng.randrange(cfg['puts'])}".encode())
                else:
                    db.put(f"m{rng.randrange(300)}".encode(), rng.randbytes(48))
        mixed_s, _ = timed(mixed)
        db.close()

        recovery_s, db = timed(lambda: Database.open(path, create=False))
        size_before = sum(p.stat().st_size for p in path.glob("*.bkv"))
        compaction_s, _ = timed(db.compact)
        size_after = sum(p.stat().st_size for p in path.glob("*.bkv"))
        final_stats = db.stats()
        db.close()

    result = {
        "schema": 1,
        "mode": "quick" if args.quick else "full",
        "environment": {
            "python": sys.version.split()[0],
            "implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "cpu_count": os.cpu_count(),
        },
        "config": cfg,
        "metrics": {
            "sequential_puts_seconds": put_s,
            "sequential_puts_ops_per_second": cfg["puts"] / put_s,
            "random_gets_seconds": get_s,
            "random_gets_ops_per_second": cfg["gets"] / get_s,
            "batched_writes_seconds": batch_s,
            "batched_write_ops_per_second": (cfg["batches"] * cfg["batch_size"]) / batch_s,
            "mixed_seconds": mixed_s,
            "mixed_ops_per_second": cfg["mixed"] / mixed_s,
            "reopen_recovery_seconds": recovery_s,
            "compaction_seconds": compaction_s,
            "database_bytes_before_compaction": size_before,
            "database_bytes_after_compaction": size_after,
        },
        "final_stats": final_stats,
        "comparative_claim": None,
        "note": "Single-environment reproducibility benchmark; no SOTA or competitor claim.",
    }
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
