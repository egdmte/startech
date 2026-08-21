"""Safety-boundary tests for the hardware-free OSMAN/MATT scaffold."""

from __future__ import annotations

import unittest

import tawnt
from arac.surucu import (
    BlockedMotorDriver,
    DriverAction,
    FakeMotorDriver,
    InvalidMotorRequest,
    MotorRequest,
    PhysicalOutputBlocked,
    validate_request,
)


class MotorRequestModelTest(unittest.TestCase):
    def test_invalid_values_and_missing_provenance_are_rejected(self):
        invalid_pairs = (
            (True, 0.0),
            (float("nan"), 0.0),
            (float("inf"), 0.0),
            (1.1, 0.0),
        )

        for left, right in invalid_pairs:
            with self.subTest(values=(left, right)):
                with self.assertRaises(InvalidMotorRequest):
                    MotorRequest(left, right, "SIM_DRIVE", "unit test")

        with self.assertRaises(InvalidMotorRequest):
            MotorRequest(0.0, 0.0, "", "unit test")
        with self.assertRaises(InvalidMotorRequest):
            MotorRequest(0.0, 0.0, "SIM_DRIVE", "")

    def test_stop_factory_is_still_an_unvalidated_request(self):
        request = MotorRequest.stop(
            phase="SIM_DRIVE",
            reason="state requested stop",
            frame_id=7,
            created_at=1.0,
        )

        self.assertEqual((0.0, 0.0), (request.left, request.right))
        self.assertEqual(7, request.frame_id)


class MotorDriverTest(unittest.TestCase):
    def setUp(self):
        tawnt.sifirla()
        tawnt.definePhase(
            "SIM_DRIVE",
            motion_allowed=True,
            allow_reverse=True,
            allow_pivot=True,
            max_pwm=1.0,
            max_difference=2.0,
            allowed_from=(None,),
        )
        tawnt.validateBeforeStart(profile=tawnt.OFFLINE)
        tawnt.enterPhase("SIM_DRIVE")
        tawnt.arm("OSMAN unit test")

    def tearDown(self):
        tawnt.sifirla()

    def test_fake_driver_accepts_only_tawnt_validated_request(self):
        raw = MotorRequest(0.25, 0.2, "SIM_DRIVE", "lane correction", frame_id=3)
        driver = FakeMotorDriver()

        with self.assertRaises(TypeError):
            driver.apply(raw)

        validated = validate_request(raw)
        driver.apply(validated)
        self.assertEqual(1, len(driver.history))
        self.assertEqual(DriverAction.APPLY, driver.history[0].action)
        self.assertEqual((0.25, 0.2), (driver.history[0].left, driver.history[0].right))

    def test_validation_fails_closed_when_tawnt_is_not_armed(self):
        tawnt.sifirla()
        request = MotorRequest(0.0, 0.0, "SIM_DRIVE", "unarmed request")

        with self.assertRaises(tawnt.TawntHatasi):
            validate_request(request)

    def test_blocked_driver_refuses_even_a_validated_command(self):
        request = validate_request(
            MotorRequest(0.1, 0.1, "SIM_DRIVE", "physical placeholder test")
        )
        driver = BlockedMotorDriver("school motors unavailable")

        with self.assertRaisesRegex(PhysicalOutputBlocked, "school motors"):
            driver.apply(request)

        driver.stop("test cleanup")
        driver.close()
        driver.close()
        self.assertEqual(["test cleanup", "blocked driver closing"], driver.stop_requests)

    def test_fake_driver_close_is_idempotent_and_records_zero_request(self):
        driver = FakeMotorDriver()
        driver.close()
        driver.close()

        self.assertEqual(
            [DriverAction.STOP_REQUESTED, DriverAction.CLOSE],
            [item.action for item in driver.history],
        )
        self.assertTrue(all(item.left == item.right == 0.0 for item in driver.history))


if __name__ == "__main__":
    unittest.main(verbosity=2)
