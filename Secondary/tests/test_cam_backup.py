"""Tests for consistent CAM SQLite backup creation."""

from __future__ import annotations

import hashlib
import sqlite3
import tempfile
import unittest
from pathlib import Path

from deployment.backup_cam import backup_sqlite


class CamBackupTest(unittest.TestCase):
    def test_online_backup_contains_committed_rows_and_checksum(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database = root / "cam.sqlite3"
            connection = sqlite3.connect(database)
            connection.execute("CREATE TABLE evidence(value TEXT NOT NULL)")
            connection.execute("INSERT INTO evidence VALUES ('real-row')")
            connection.commit()
            backup = backup_sqlite(database, root / "backups", label="abcdef123456")
            connection.close()

            restored = sqlite3.connect(backup)
            self.assertEqual(
                "real-row", restored.execute("SELECT value FROM evidence").fetchone()[0]
            )
            restored.close()
            checksum = backup.with_suffix(backup.suffix + ".sha256")
            self.assertEqual(
                hashlib.sha256(backup.read_bytes()).hexdigest(),
                checksum.read_text(encoding="ascii").split()[0],
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
