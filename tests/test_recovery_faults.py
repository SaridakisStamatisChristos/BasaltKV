from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from basaltkv import Database, verify_database


class FaultInjectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "db"
        with Database.open(self.path) as db:
            db.put(b"base", b"1")
        self.env_base = os.environ.copy()
        self.env_base["PYTHONPATH"] = str(Path(__file__).parents[1] / "src")

    def tearDown(self):
        self.tmp.cleanup()

    def _crash_commit(self, point: str):
        code = r'''
import sys
from basaltkv import Database
with Database.open(sys.argv[1], create=False) as db:
    with db.transaction() as tx:
        tx.put(b"x", b"2")
        tx.put(b"y", b"2")
'''
        env = self.env_base.copy()
        env["BASALTKV_FAULT_POINT"] = point
        cp = subprocess.run([sys.executable, "-c", code, str(self.path)], env=env)
        self.assertEqual(cp.returncode, 91)
        with Database.open(self.path, create=False) as db:
            state = dict(db.scan())
        self.assertEqual(state[b"base"], b"1")
        self.assertIn((b"x" in state, b"y" in state), {(False, False), (True, True)})
        if b"x" in state:
            self.assertEqual(state[b"x"], b"2")
            self.assertEqual(state[b"y"], b"2")
        self.assertTrue(verify_database(self.path).ok)

    def test_commit_crash_points_preserve_atomicity(self):
        for point in (
            "before_wal_record_write",
            "during_wal_write",
            "after_wal_write_before_flush",
            "after_flush_before_fsync",
            "after_wal_fsync_before_ack",
        ):
            with self.subTest(point=point):
                # Recreate baseline per fault because a prior allowed later commit may survive.
                self.tmp.cleanup()
                self.tmp = tempfile.TemporaryDirectory()
                self.path = Path(self.tmp.name) / "db"
                with Database.open(self.path) as db:
                    db.put(b"base", b"1")
                self._crash_commit(point)

    def _crash_compact(self, point: str):
        code = r'''
import sys
from basaltkv import Database
with Database.open(sys.argv[1], create=False) as db:
    db.compact()
'''
        with Database.open(self.path, create=False, read_only=True) as before_db:
            before = dict(before_db.scan())
        env = self.env_base.copy()
        env["BASALTKV_FAULT_POINT"] = point
        cp = subprocess.run([sys.executable, "-c", code, str(self.path)], env=env)
        self.assertEqual(cp.returncode, 91)
        with Database.open(self.path, create=False) as db:
            self.assertEqual(dict(db.scan()), before)
        self.assertTrue(verify_database(self.path).ok)

    def test_compaction_crash_points_are_restart_safe(self):
        for point in (
            "during_snapshot_creation",
            "after_snapshot_write_before_rename",
            "after_rename_before_dir_sync",
            "before_old_generation_removal",
            "during_compaction_cleanup",
        ):
            with self.subTest(point=point):
                self.tmp.cleanup()
                self.tmp = tempfile.TemporaryDirectory()
                self.path = Path(self.tmp.name) / "db"
                with Database.open(self.path) as db:
                    for i in range(10):
                        db.put(f"k{i}".encode(), f"v{i}".encode())
                self._crash_compact(point)


if __name__ == "__main__":
    unittest.main()
