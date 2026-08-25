"""Tests for CAM's deployment revision evidence."""

from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import zipfile

from deployment.write_release_reference import write_reference
from startech_cam.repository import DEFAULT_DOCUMENT
from startech_cam.release import resolve_release
from startech_cam.vehicle_release import (
    Revision,
    build_vehicle_bundle,
    inspect_release_sources,
)


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


class KerimVehicleBundleTest(unittest.TestCase):
    def make_repository(self, root: Path) -> str:
        for directory in ("arac", "startech", "config"):
            (root / directory).mkdir(parents=True, exist_ok=True)
            (root / directory / "kept.txt").write_text(
                f"{directory} committed\n", encoding="utf-8"
            )
        for filename in (
            "tawnt.py",
            "requirements.txt",
            "requirements-camera-usb.txt",
            "AGENTS_READ_ME.txt",
            "PROJECT_MAP.md",
            "TAWNT.md",
        ):
            (root / filename).write_text(f"{filename}\n", encoding="utf-8")
        commands = (
            ["git", "init", "--initial-branch=master"],
            ["git", "add", "."],
            [
                "git",
                "-c",
                "user.name=KERIM Test",
                "-c",
                "user.email=kerim@example.invalid",
                "commit",
                "-m",
                "exact vehicle source",
            ],
        )
        for command in commands:
            subprocess.run(command, cwd=root, check=True, capture_output=True)
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        subprocess.run(
            ["git", "update-ref", "refs/remotes/origin/master", commit],
            cwd=root,
            check=True,
            capture_output=True,
        )
        return commit

    def test_comparison_does_not_call_a_cached_remote_latest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            commit = self.make_repository(root)
            sources = inspect_release_sources(root=root, refresh_remote=False)
            self.assertEqual(commit, sources.server.commit)
            self.assertEqual(commit, sources.repository.commit)
            self.assertEqual("same", sources.relation)
            self.assertFalse(sources.remote_current)

    def test_published_reference_is_verified_without_web_worker_git_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            commit = self.make_repository(root)
            reference = root / "shared" / "published-master.json"
            write_reference(
                git_directory=root / ".git",
                output=reference,
                commit=commit,
            )
            sources = inspect_release_sources(
                root=root,
                refresh_remote=False,
                reference_file=reference,
            )
            self.assertTrue(sources.remote_current)
            self.assertEqual(commit, sources.repository.commit)
            self.assertEqual("same", sources.relation)

    def test_bundle_contains_only_committed_source_and_one_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            commit = self.make_repository(root)
            (root / "arac" / "uncommitted.py").write_text(
                "must not ship\n", encoding="utf-8"
            )
            revision = Revision(
                commit=commit,
                committed_at_utc="2026-08-25T12:00:00+00:00",
                source="server",
            )
            document = json.loads(DEFAULT_DOCUMENT.read_text(encoding="utf-8"))
            bundle = build_vehicle_bundle(
                root=root,
                revision=revision,
                profile_tag="abc123",
                document=document,
                now=datetime(2026, 8, 25, 12, 30, tzinfo=timezone.utc),
            )
            self.assertEqual(commit, bundle.commit)
            with zipfile.ZipFile(BytesIO(bundle.body)) as archive:
                names = set(archive.namelist())
                self.assertIn("startech-vehicle/arac/kept.txt", names)
                self.assertNotIn("startech-vehicle/arac/uncommitted.py", names)
                self.assertIn("KERIM_RELEASE/manifest.json", names)
                manifest = json.loads(
                    archive.read("KERIM_RELEASE/manifest.json").decode("utf-8")
                )
                self.assertEqual(commit, manifest["source"]["git_commit"])
                self.assertEqual("abc123", manifest["profile"]["kerim_tag"])
                self.assertEqual("PHYSICALLY UNVERIFIED", manifest["physical_status"])
                self.assertEqual(
                    {"requirements.txt", "requirements-camera-usb.txt"},
                    set(manifest["dependency_file_sha256"]),
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
