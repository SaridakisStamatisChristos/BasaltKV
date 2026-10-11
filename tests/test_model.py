from __future__ import annotations

import random
import tempfile
import unittest
from pathlib import Path

from basaltkv import Database


class ModelParityTests(unittest.TestCase):
    def test_randomized_reference_model(self):
        for seed in (1, 7, 19, 42, 1337, 99173):
            with self.subTest(seed=seed), tempfile.TemporaryDirectory() as td:
                rng = random.Random(seed)
                path = Path(td) / "db"
                model: dict[bytes, bytes] = {}
                db = Database.open(path)
                try:
                    for step in range(250):
                        action = rng.choice(("put", "delete", "txn", "abort", "reopen", "compact", "scan"))
                        key = f"k{rng.randrange(12)}".encode()
                        if action == "put":
                            value = rng.randbytes(rng.randrange(0, 32))
                            db.put(key, value)
                            model[key] = value
                        elif action == "delete":
                            db.delete(key)
                            model.pop(key, None)
                        elif action in {"txn", "abort"}:
                            tx = db.transaction()
                            staged = {}
                            for _ in range(rng.randrange(1, 5)):
                                k = f"k{rng.randrange(12)}".encode()
                                if rng.random() < 0.25:
                                    tx.delete(k); staged[k] = None
                                else:
                                    v = rng.randbytes(rng.randrange(0, 24))
                                    tx.put(k, v); staged[k] = v
                            if action == "abort":
                                tx.abort()
                            else:
                                tx.commit()
                                for k, v in staged.items():
                                    if v is None: model.pop(k, None)
                                    else: model[k] = v
                        elif action == "reopen":
                            db.close(); db = Database.open(path, create=False)
                        elif action == "compact":
                            db.compact()
                        else:
                            self.assertEqual(dict(db.scan()), model, f"seed={seed} step={step}")
                        self.assertEqual(dict(db.scan()), model, f"seed={seed} step={step} action={action}")
                finally:
                    db.close()
                with Database.open(path, create=False, read_only=True) as final:
                    self.assertEqual(dict(final.scan()), model)


if __name__ == "__main__":
    unittest.main()
