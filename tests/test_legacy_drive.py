"""Regression checks for the race-era driving code.

These tests execute control arithmetic only. They do not claim to test the car.
"""
from __future__ import annotations

import importlib
import io
import csv
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock


LEGACY = Path(__file__).resolve().parents[1] / "LEGACY"


class LegacyDriveTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(LEGACY))
        cls.config = importlib.import_module("config")
        cls.controller_module = importlib.import_module("controller")
        cls.lane_module = importlib.import_module("lane")
        cls.motor_module = importlib.import_module("motor")
        cls.logger_module = importlib.import_module("logger")

    @classmethod
    def tearDownClass(cls):
        sys.path.remove(str(LEGACY))

    def test_lane_loss_does_not_reverse_the_last_turn(self):
        controller = self.controller_module.PDController()
        controller.compute(100)
        left, right = controller.compute(None)

        self.assertGreaterEqual(left, 0)
        self.assertGreaterEqual(right, 0)
        self.assertGreaterEqual(left, right)

    def test_controller_does_not_move_before_seeing_a_lane(self):
        controller = self.controller_module.PDController()

        self.assertEqual((0.0, 0.0), controller.compute(None))

    def test_visible_lane_noise_never_requests_reverse(self):
        controller = self.controller_module.PDController()
        for error in (0, 2, -2, 3, -3, 5, -5, 0):
            left, right = controller.compute(error)
            self.assertGreaterEqual(left, 0)
            self.assertGreaterEqual(right, 0)

    def test_prolonged_lane_loss_stops_both_wheels(self):
        controller = self.controller_module.PDController()
        controller.compute(50)
        for _ in range(29):
            self.assertNotEqual((0.0, 0.0), controller.compute(None))

        self.assertEqual((0.0, 0.0), controller.compute(None))

    def test_medium_derivative_does_not_accelerate_a_sharp_curve(self):
        controller = self.controller_module.PDController()
        controller.prev_error = 69
        controller._has_seen_lane = True

        with mock.patch.multiple(
            self.controller_module,
            KP=0.0,
            KD=0.0,
            KI=0.0,
        ):
            left, right = controller.compute(100)

        expected = max(self.config.MIN_SPEED, self.config.DEAD_ZONE_MIN_PWM)
        self.assertEqual(expected, left)
        self.assertEqual(expected, right)

    def test_lane_controller_clamps_a_pivot_to_one_stopped_wheel(self):
        controller = self.controller_module.PDController()
        left, right = controller.compute(500)

        self.assertGreaterEqual(left, 0)
        self.assertGreaterEqual(right, 0)
        self.assertTrue(left == 0 or right == 0)

    def test_motor_dead_zone_is_the_final_output_rule(self):
        floor = self.config.DEAD_ZONE_MIN_PWM
        apply_floor = self.motor_module.MotorDriver._apply_dead_zone

        self.assertEqual(floor, apply_floor(floor - 5))
        self.assertEqual(-floor, apply_floor(-floor + 5))
        self.assertEqual(0, apply_floor(0))

    def test_motor_command_fails_when_gpio_is_unavailable(self):
        with mock.patch.object(self.motor_module, "_HAS_GPIO", False):
            motor = self.motor_module.MotorDriver()

        self.assertFalse(motor.hardware_available)
        with self.assertRaisesRegex(RuntimeError, "hareket komutu gönderilmedi"):
            motor.set_speed(30, 30)

    def test_invalid_motor_command_closes_real_outputs(self):
        class FakeDevice:
            def __init__(self):
                self.value = 0.0
                self.closed = False

            def on(self):
                self.value = 1.0

            def off(self):
                self.value = 0.0

            def close(self):
                self.closed = True

        motor = self.motor_module.MotorDriver.__new__(
            self.motor_module.MotorDriver
        )
        devices = [FakeDevice() for _ in range(6)]
        (
            motor._right_in1,
            motor._right_in2,
            motor._left_in1,
            motor._left_in2,
            motor._right_pwm,
            motor._left_pwm,
        ) = devices
        motor._has_gpio = True
        motor._closed = False

        with self.assertRaisesRegex(ValueError, "sonlu"):
            motor.set_speed(float("nan"), 30)

        self.assertFalse(motor.hardware_available)
        self.assertTrue(all(device.closed for device in devices))

    def test_diffuse_histogram_noise_is_not_a_lane(self):
        detector = self.lane_module.LaneDetector()
        histogram = self.lane_module.np.ones(detector.bird_w, dtype=float)

        _, valid = detector._find_peak(
            histogram,
            0,
            detector.mid,
            None,
        )

        self.assertFalse(valid)

    def test_lane_only_module_does_not_parse_cli_on_import(self):
        with mock.patch.object(sys, "argv", ["pytest", "--not-a-lane-option"]):
            module = importlib.import_module("yol_takip")

        self.assertTrue(callable(module.main))

    def test_sign_tool_does_not_open_camera_on_import(self):
        sys.modules.pop("sign_test", None)
        with mock.patch("cv2.VideoCapture") as video_capture:
            module = importlib.import_module("sign_test")

        video_capture.assert_not_called()
        self.assertTrue(callable(module.main))

    def test_speed_bump_command_is_not_below_dead_zone(self):
        self.assertGreaterEqual(
            self.config.SPEED_BUMP_SPEED,
            self.config.DEAD_ZONE_MIN_PWM,
        )

    def test_diagnostic_report_does_not_crash(self):
        controller = self.controller_module.PDController()
        controller.compute(0)

        with redirect_stdout(io.StringIO()) as output:
            controller.tani_raporu()

        self.assertIn("DENETLEYICI TANI RAPORU", output.getvalue())

    def test_lost_lane_is_not_recorded_as_perfect_zero_error(self):
        with tempfile.TemporaryDirectory() as directory:
            csv_path = Path(directory) / "errors.csv"
            logger = self.logger_module.ErrorLogger(
                duration_sec=999,
                export_file=str(csv_path),
            )
            logger.update(None)
            logger.update(12)

            with redirect_stdout(io.StringIO()) as output:
                logger.finish()

            with csv_path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.reader(handle))

        self.assertEqual("", rows[1][2])
        self.assertEqual("12.0", rows[2][2])
        self.assertIn("Gecerli hata : 1 kare", output.getvalue())


if __name__ == "__main__":
    unittest.main()
