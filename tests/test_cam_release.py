"""Tests for CAM's deployment revision evidence."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from startech_cam.release import resolve_release


class CamReleaseTest(unittest.TestCase):
    def test_reads_loose_git_head(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".git" / "refs" / "heads").mkdir(parents=True)
            (root / ".git" / "HEAD").write_text(
                "ref: refs/heads/master\n", encoding="utf-8"
            )
            (root / ".git" / "refs" / "heads" / "master").write_text(
                "b" * 40 + "\n", encoding="utf-8"
            )
            with patch.dict("os.environ", {}, clear=True):
                self.assertEqual("b" * 40, resolve_release(root))

    def test_environment_requires_a_full_commit(self):
        with patch.dict("os.environ", {"CAM_RELEASE": "short"}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "40-character"):
                resolve_release(Path("missing"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
