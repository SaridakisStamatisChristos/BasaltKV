from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class CLITests(unittest.TestCase):
    def test_cli_roundtrip_verify_info_compact(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "db"
            env = os.environ.copy()
            env["PYTHONPATH"] = str(Path(__file__).parents[1] / "src")
            base = [sys.executable, "-m", "basaltkv"]
            def run(*args):
                return subprocess.run(base + list(args), env=env, text=True, capture_output=True)
            self.assertEqual(run("init", str(path)).returncode, 0)
            self.assertEqual(run("put", str(path), "6b6579", "00ff", "--key-encoding", "hex", "--value-encoding", "hex").returncode, 0)
            got = run("get", str(path), "6b6579", "--key-encoding", "hex", "--output", "hex")
            self.assertEqual(got.returncode, 0)
            self.assertEqual(got.stdout.strip(), "00ff")
            self.assertEqual(run("verify", str(path)).returncode, 0)
            self.assertEqual(run("compact", str(path)).returncode, 0)
            self.assertEqual(run("info", str(path)).returncode, 0)
            self.assertEqual(run("delete", str(path), "key").returncode, 0)
            self.assertEqual(run("get", str(path), "key").returncode, 1)


if __name__ == "__main__":
    unittest.main()
