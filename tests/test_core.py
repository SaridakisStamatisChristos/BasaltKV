from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

from basaltkv import (
    ClosedError,
    Database,
    LockError,
    ReadOnlyError,
    TransactionError,
    verify_database,
)


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "db"

    def tearDown(self):
        self.tmp.cleanup()

    def test_binary_put_get_delete_and_empty_values(self):
        with Database.open(self.path) as db:
            self.assertEqual(db.put(b"\x00key", b"\xff\x00"), 1)
            self.assertEqual(db.get(b"\x00key"), b"\xff\x00")
            self.assertTrue(db.exists(b"\x00key"))
            db.put(b"", b"")
            self.assertEqual(db.get(b""), b"")
            db.delete(b"\x00key")
            self.assertIsNone(db.get(b"\x00key"))

    def test_atomic_multi_key_transaction_and_abort(self):
        with Database.open(self.path) as db:
            tx = db.transaction()
            tx.put(b"a", b"1").put(b"b", b"2")
            self.assertEqual(tx.get(b"a"), b"1")
            self.assertEqual(tx.commit(), 1)
            self.assertEqual(dict(db.scan()), {b"a": b"1", b"b": b"2"})
            tx2 = db.transaction()
            tx2.put(b"a", b"x").delete(b"b")
            tx2.abort()
            self.assertEqual(dict(db.scan()), {b"a": b"1", b"b": b"2"})

    def test_transaction_misuse_is_explicit(self):
        with Database.open(self.path) as db:
            tx = db.transaction()
            tx.put(b"x", b"1")
            tx.commit()
            with self.assertRaises(TransactionError):
                tx.commit()
            with self.assertRaises(TransactionError):
                db.transaction().commit()

    def test_reopen_equivalence_and_monotonic_sequence(self):
        with Database.open(self.path) as db:
            self.assertEqual(db.put(b"a", b"1"), 1)
            self.assertEqual(db.put(b"b", b"2"), 2)
        with Database.open(self.path, create=False) as db:
            self.assertEqual(dict(db.scan()), {b"a": b"1", b"b": b"2"})
            self.assertEqual(db.put(b"c", b"3"), 3)
        with Database.open(self.path, create=False, read_only=True) as db:
            self.assertEqual(db.stats()["last_commit_sequence"], 3)

    def test_prefix_scan_is_sorted_and_complete(self):
        with Database.open(self.path) as db:
            for k in (b"aa2", b"b", b"aa1", b"aa0"):
                db.put(k, k[::-1])
            self.assertEqual([k for k, _ in db.scan(b"aa")], [b"aa0", b"aa1", b"aa2"])

    def test_read_only_rejects_writes(self):
        with Database.open(self.path) as db:
            db.put(b"a", b"1")
        with Database.open(self.path, create=False, read_only=True) as db:
            self.assertEqual(db.get(b"a"), b"1")
            with self.assertRaises(ReadOnlyError):
                db.put(b"b", b"2")

    def test_close_is_idempotent_and_operations_fail(self):
        db = Database.open(self.path)
        db.close()
        db.close()
        with self.assertRaises(ClosedError):
            db.get(b"x")

    def test_writer_lock_rejects_second_writer(self):
        first = Database.open(self.path)
        try:
            with self.assertRaises(LockError):
                Database.open(self.path, create=False)
        finally:
            first.close()

    def test_concurrent_readers_and_atomic_scan_visibility(self):
        with Database.open(self.path) as db:
            with db.transaction() as tx:
                tx.put(b"left", b"0").put(b"right", b"0")
            failures = []
            stop = threading.Event()

            def reader():
                while not stop.is_set():
                    state = dict(db.scan())
                    if state.get(b"left") != state.get(b"right"):
                        failures.append(state)
                        stop.set()

            threads = [threading.Thread(target=reader) for _ in range(6)]
            for t in threads:
                t.start()
            for i in range(1, 100):
                v = str(i).encode()
                with db.transaction() as tx:
                    tx.put(b"left", v).put(b"right", v)
            stop.set()
            for t in threads:
                t.join(2)
            self.assertEqual(failures, [])

    def test_compaction_equivalence_and_no_resurrection(self):
        with Database.open(self.path) as db:
            db.put(b"gone", b"old")
            db.put(b"live", b"v1")
            db.delete(b"gone")
            db.put(b"live", b"v2")
            before = db.scan()
            wal_before = db.stats()["wal_bytes"]
            db.compact()
            self.assertEqual(db.scan(), before)
            self.assertLess(db.stats()["wal_bytes"], wal_before)
        with Database.open(self.path, create=False) as db:
            self.assertEqual(db.scan(), before)
            self.assertIsNone(db.get(b"gone"))

    def test_compaction_immediately_after_reopen(self):
        with Database.open(self.path) as db:
            db.put(b"a", b"1")
        with Database.open(self.path, create=False) as db:
            db.compact()
        self.assertTrue(verify_database(self.path).ok)

    def test_repeated_crash_recover_style_cycles_without_fault(self):
        model = {}
        for i in range(15):
            with Database.open(self.path) as db:
                key = f"k{i % 4}".encode()
                if i % 5 == 0:
                    db.delete(key)
                    model.pop(key, None)
                else:
                    value = f"v{i}".encode()
                    db.put(key, value)
                    model[key] = value
                if i % 3 == 0:
                    db.compact()
            with Database.open(self.path, create=False, read_only=True) as check:
                self.assertEqual(dict(check.scan()), model)


    def test_concurrent_writers_are_serialized_without_lost_commits(self):
        with Database.open(self.path) as db:
            committed = []
            guard = threading.Lock()

            def writer(i):
                value = f"v{i}".encode()
                seq = db.put(b"shared", value)
                with guard:
                    committed.append((seq, value))

            threads = [threading.Thread(target=writer, args=(i,)) for i in range(20)]
            for t in threads:
                t.start()
            for t in threads:
                t.join(5)
            self.assertEqual(len(committed), 20)
            seqs = sorted(seq for seq, _ in committed)
            self.assertEqual(seqs, list(range(1, 21)))
            expected = max(committed)[1]
            self.assertEqual(db.get(b"shared"), expected)

    def test_readers_remain_consistent_across_concurrent_compaction(self):
        with Database.open(self.path) as db:
            for i in range(50):
                db.put(f"k{i}".encode(), f"v{i}".encode())
            expected = db.scan()
            failures = []
            stop = threading.Event()

            def reader():
                while not stop.is_set():
                    if db.scan() != expected:
                        failures.append(True)
                        stop.set()

            threads = [threading.Thread(target=reader) for _ in range(4)]
            for t in threads:
                t.start()
            for _ in range(4):
                db.compact()
            stop.set()
            for t in threads:
                t.join(2)
            self.assertEqual(failures, [])

    def test_close_waits_for_active_reader_then_closes(self):
        db = Database.open(self.path)
        entered = threading.Event()
        release = threading.Event()

        def held_reader():
            with db._rw.read():  # white-box lifetime test of the documented lock boundary
                entered.set()
                release.wait(2)

        t = threading.Thread(target=held_reader)
        t.start()
        self.assertTrue(entered.wait(1))
        closed = threading.Event()

        def closer():
            db.close()
            closed.set()

        c = threading.Thread(target=closer)
        c.start()
        time.sleep(0.05)
        self.assertFalse(closed.is_set())
        release.set()
        t.join(2); c.join(2)
        self.assertTrue(closed.is_set())

    def test_durable_ack_survives_immediate_process_kill(self):
        code = r'''
import sys,time
from basaltkv import Database
p=sys.argv[1]
with Database.open(p) as db:
    db.put(b"ack", b"durable")
    print("ACK", flush=True)
    time.sleep(30)
'''
        env = os.environ.copy()
        env["PYTHONPATH"] = str(Path(__file__).parents[1] / "src")
        proc = subprocess.Popen([sys.executable, "-c", code, str(self.path)], stdout=subprocess.PIPE, text=True, env=env)
        self.assertEqual(proc.stdout.readline().strip(), "ACK")
        proc.kill()
        proc.wait(timeout=5)
        proc.stdout.close()
        with Database.open(self.path, create=False, read_only=True) as db:
            self.assertEqual(db.get(b"ack"), b"durable")


if __name__ == "__main__":
    unittest.main()
