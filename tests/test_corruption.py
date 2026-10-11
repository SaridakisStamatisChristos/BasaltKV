from __future__ import annotations

import os
import struct
import tempfile
import unittest
from pathlib import Path

from basaltkv import CorruptionError, Database, verify_database
from basaltkv.constants import SNAPSHOT_FILE, SNAPSHOT_TMP_FILE, WAL_FILE
from basaltkv.wal import _WAL_HEADER, _REC_HEADER


class CorruptionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "db"
        with Database.open(self.path) as db:
            db.put(b"a", b"1")
            db.put(b"b", b"2")

    def tearDown(self):
        self.tmp.cleanup()

    def _wal(self) -> Path:
        return self.path / WAL_FILE

    def test_zero_length_wal_fails_closed(self):
        self._wal().write_bytes(b"")
        self.assertFalse(verify_database(self.path).ok)
        with self.assertRaises(CorruptionError):
            Database.open(self.path, create=False)

    def test_truncated_wal_header_fails_closed(self):
        data = self._wal().read_bytes()
        self._wal().write_bytes(data[:10])
        self.assertFalse(verify_database(self.path).ok)

    def test_checksum_corruption_fails_closed(self):
        data = bytearray(self._wal().read_bytes())
        data[_WAL_HEADER.size + _REC_HEADER.size - 1] ^= 0x01
        self._wal().write_bytes(data)
        self.assertFalse(verify_database(self.path).ok)

    def test_random_appended_bytes_fail_closed(self):
        with open(self._wal(), "ab") as f:
            f.write(b"XYZ-not-a-record")
        self.assertFalse(verify_database(self.path).ok)

    def test_torn_final_record_is_recoverable_and_truncated_on_writable_open(self):
        data = self._wal().read_bytes()
        # Remove final commit bytes so the last transaction is unacknowledgeable.
        self._wal().write_bytes(data[:-7])
        report = verify_database(self.path)
        self.assertTrue(report.ok)
        self.assertTrue(report.uncommitted_tail)
        with Database.open(self.path, create=False) as db:
            # First transaction remains; torn second transaction is excluded.
            self.assertEqual(db.get(b"a"), b"1")
            self.assertIsNone(db.get(b"b"))
        self.assertTrue(verify_database(self.path).ok)

    def test_unsupported_wal_version_fails_closed(self):
        data = bytearray(self._wal().read_bytes())
        data[8:10] = (99).to_bytes(2, "big")
        self._wal().write_bytes(data)
        self.assertFalse(verify_database(self.path).ok)

    def test_huge_length_field_fails_before_allocation(self):
        data = bytearray(self._wal().read_bytes())
        # First record key_len field begins at header + 24 bytes within the record header.
        off = _WAL_HEADER.size + 24
        data[off:off+4] = (0xFFFFFFFF).to_bytes(4, "big")
        self._wal().write_bytes(data)
        self.assertFalse(verify_database(self.path).ok)

    def test_duplicate_commit_record_fails(self):
        data = self._wal().read_bytes()
        # Second transaction's final commit is the final fixed-size record (no payload).
        duplicate = data[-_REC_HEADER.size:]
        with open(self._wal(), "ab") as f:
            f.write(duplicate)
        self.assertFalse(verify_database(self.path).ok)

    def test_reordered_records_fail(self):
        data = self._wal().read_bytes()
        # Swap first transaction BEGIN and PUT records (known small key/value sizes).
        h = _WAL_HEADER.size
        begin = data[h:h+_REC_HEADER.size]
        put_len = _REC_HEADER.size + 2
        put = data[h+_REC_HEADER.size:h+_REC_HEADER.size+put_len]
        rest = data[h+_REC_HEADER.size+put_len:]
        self._wal().write_bytes(data[:h] + put + begin + rest)
        self.assertFalse(verify_database(self.path).ok)

    def test_corrupted_snapshot_fails_closed(self):
        with Database.open(self.path, create=False) as db:
            db.compact()
        snap = self.path / SNAPSHOT_FILE
        data = bytearray(snap.read_bytes())
        data[-1] ^= 0x80
        snap.write_bytes(data)
        self.assertFalse(verify_database(self.path).ok)

    def test_stale_temp_snapshot_never_overrides_authoritative_state(self):
        (self.path / SNAPSHOT_TMP_FILE).write_bytes(b"attacker-controlled-stale-temp")
        with Database.open(self.path, create=False) as db:
            self.assertEqual(db.get(b"a"), b"1")
        self.assertFalse((self.path / SNAPSHOT_TMP_FILE).exists())


    def test_missing_snapshot_is_valid_only_before_compaction(self):
        # Snapshot is optional while WAL base is zero.
        self.assertTrue(verify_database(self.path).ok)
        with Database.open(self.path, create=False) as db:
            db.compact()
        (self.path / SNAPSHOT_FILE).unlink()
        self.assertFalse(verify_database(self.path).ok)
        with self.assertRaises(CorruptionError):
            Database.open(self.path, create=False)

    def test_snapshot_wal_identity_mismatch_fails(self):
        with Database.open(self.path, create=False) as db:
            db.compact()
        other = Path(self.tmp.name) / "other"
        with Database.open(other) as db:
            db.put(b"x", b"y")
            db.compact()
        # Copy a structurally valid, checksummed snapshot from a different database.
        (self.path / SNAPSHOT_FILE).write_bytes((other / SNAPSHOT_FILE).read_bytes())
        self.assertFalse(verify_database(self.path).ok)

    def test_verifier_does_not_mutate_authoritative_files(self):
        before = {name: (self.path / name).read_bytes() for name in (WAL_FILE,) if (self.path / name).exists()}
        report = verify_database(self.path)
        self.assertTrue(report.ok)
        after = {name: (self.path / name).read_bytes() for name in before}
        self.assertEqual(after, before)


if __name__ == "__main__":
    unittest.main()
