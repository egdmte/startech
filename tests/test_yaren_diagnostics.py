"""Evidence-bound tests for YAREN's safe capability report."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np

from arac.goz import CameraStatus, CameraUnavailable, FramePacket
from arac.yaren_diagnostics import collect_capability_report
from startech.configuration.profiles import ProfileStore


PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = PROJECT_ROOT / "config" / "examples"


class ScriptedCamera:
    def __init__(self, *, unavailable: str | None = None) -> None:
        self.unavailable = unavailable
        self.opened = False

    @property
    def status(self) -> CameraStatus:
        return CameraStatus.STREAMING if self.opened else CameraStatus.DISCONNECTED

    def open(self) -> None:
        if self.unavailable:
            raise CameraUnavailable(self.unavailable)
        self.opened = True

    def read_frame(self) -> FramePacket:
        image = np.zeros((630, 840, 3), dtype=np.uint8)
        image[:, 220:235] = 255
        image[:, 605:620] = 255
        return FramePacket(1, 1.0, image, source="USB:0")

    def close(self) -> None:
        self.opened = False


class YarenDiagnosticsTest(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "profiles"
        store = ProfileStore(self.root)
        profile = store.import_pair(
            EXAMPLES / "kalibrasyon-v1.ornek.json",
            EXAMPLES / "ayarlar-v1.ornek.json",
            name="Diagnostic baseline",
        )
        store.activate_profile(
            profile.manifest.profile_id,
            warning_digest=profile.manifest.warning_digest,
            reviewer="test student",
        )

    def statuses(self, report) -> dict[str, str]:
        return {item["module"]: item["status"] for item in report["results"]}

    def test_report_uses_real_camera_frames_and_real_lane_analysis(self):
        report = collect_capability_report(
            "YAREN-school-car",
            profile_root=self.root,
            camera_factory=ScriptedCamera,
            epoch=lambda: 1_800_000_000,
            clock=lambda: 1.0,
        )
        statuses = self.statuses(report)
        self.assertEqual("LIVE", statuses["KASIM"])
        self.assertEqual("LIVE", statuses["KEREM"])
        self.assertEqual("UNVERIFIED", statuses["OSMAN"])
        self.assertEqual("UNVERIFIED", statuses["STEERING"])
        self.assertEqual("RESPONDED", statuses["YAREN"])
        self.assertEqual(9, len(report["results"]))

    def test_importing_diagnostics_does_not_import_the_motor_driver(self):
        completed = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import sys; import arac.yaren_diagnostics; "
                    "print('loaded' if 'arac.surucu' in sys.modules else 'not-loaded')"
                ),
            ],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual("not-loaded", completed.stdout.strip())

    def test_unavailable_camera_is_not_reported_as_a_pass(self):
        report = collect_capability_report(
            "YAREN-school-car",
            profile_root=self.root,
            camera_factory=lambda: ScriptedCamera(
                unavailable="school camera is disconnected"
            ),
            epoch=lambda: 1_800_000_000,
            clock=lambda: 1.0,
        )
        self.assertEqual("UNAVAILABLE", self.statuses(report)["KASIM"])
        camera_result = next(
            item for item in report["results"] if item["module"] == "KASIM"
        )
        self.assertIn("disconnected", camera_result["detail"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
