"""Proof for the real bounded workshop executor without claiming physical motion."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest

import tawnt

from arac.atolye import WorkshopCommand, execute_workshop_command
from arac.ayar import ActiveConfiguration


PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = PROJECT_ROOT / "config" / "examples"


def active_configuration() -> ActiveConfiguration:
    calibration = json.loads(
        (EXAMPLES / "kalibrasyon-v1.ornek.json").read_text(encoding="utf-8")
    )
    settings = json.loads(
        (EXAMPLES / "ayarlar-v1.ornek.json").read_text(encoding="utf-8")
    )
    return ActiveConfiguration(
        profile_id="a" * 32,
        name="school car",
        calibration_sha256="b" * 64,
        settings_sha256="c" * 64,
        warning_digest="d" * 64,
        warnings=(),
        calibration=calibration,
        settings=settings,
    )


class RecordingDriver:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.applied = []
        self.stops: list[str] = []
        self.closed = False

    def apply(self, request):
        if self.fail:
            raise RuntimeError("driver failure")
        self.applied.append(request)

    def stop(self, reason="stop"):
        self.stops.append(reason)

    def close(self):
        self.closed = True


class AdvancingClock:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        self.value += 0.02
        return self.value


class WorkshopExecutorTest(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        tawnt.sifirla()

    def tearDown(self) -> None:
        tawnt.sifirla()

    def command(self, **changes) -> WorkshopCommand:
        values = {
            "command_id": "1" * 32,
            "operator": "Ada Lovelace",
            "left_percent": 20.0,
            "right_percent": -15.0,
            "duration_seconds": 0.05,
            "source": "CAM_SAC",
            "cam_issued_at": 1_800_000_000,
        }
        values.update(changes)
        return WorkshopCommand(**values)

    def test_command_rejects_values_outside_the_physical_envelope(self):
        for changes in (
            {"left_percent": 35.01},
            {"right_percent": float("nan")},
            {"duration_seconds": 3.01},
            {"operator": " "},
            {"source": "REMOTE_SHELL"},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.command(**changes)

    def test_executor_applies_one_tawnt_validated_command_then_requests_stop(self):
        driver = RecordingDriver()
        moment = datetime(2026, 8, 24, 12, 0, tzinfo=timezone.utc)
        receipt = execute_workshop_command(
            self.command(),
            configuration=active_configuration(),
            driver=driver,
            log_dir=self.root,
            clock=AdvancingClock(),
            sleep=lambda _seconds: None,
            utc_now=lambda: moment,
        )

        self.assertEqual(1, len(driver.applied))
        self.assertEqual((0.2, -0.15), (
            driver.applied[0].command.left,
            driver.applied[0].command.right,
        ))
        self.assertTrue(driver.closed)
        self.assertIn("workshop duration ended", driver.stops)
        self.assertTrue(receipt.stop_requested)
        self.assertFalse(receipt.to_dict()["physical_motion_observed"])
        self.assertEqual(1_800_000_000, receipt.cam_issued_at)
        self.assertEqual(1, len(list(self.root.glob("workshop-*.jsonl"))))

    def test_driver_failure_requests_stop_before_closing_and_returns_no_receipt(self):
        driver = RecordingDriver(fail=True)
        with self.assertRaisesRegex(RuntimeError, "driver failure"):
            execute_workshop_command(
                self.command(),
                configuration=active_configuration(),
                driver=driver,
                log_dir=self.root,
                clock=AdvancingClock(),
                sleep=lambda _seconds: None,
            )
        self.assertTrue(any("workshop fault" in reason for reason in driver.stops))
        self.assertTrue(driver.closed)


if __name__ == "__main__":
    unittest.main(verbosity=2)
