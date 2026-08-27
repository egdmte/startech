"""Regression checks for the race-era driving code.

These tests execute control arithmetic only. They do not claim to test the car.
"""
from __future__ import annotations

import importlib
import sys
import unittest
from pathlib import Path


LEGACY = Path(__file__).resolve().parents[1] / "LEGACY"


class LegacyDriveTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(LEGACY))
        cls.config = importlib.import_module("config")
        cls.controller_module = importlib.import_module("controller")
        cls.motor_module = importlib.import_module("motor")

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

    def test_visible_lane_noise_never_requests_reverse(self):
        controller = self.controller_module.PDController()
        for error in (0, 2, -2, 3, -3, 5, -5, 0):
            left, right = controller.compute(error)
            self.assertGreaterEqual(left, 0)
            self.assertGreaterEqual(right, 0)

    def test_prolonged_lane_loss_stops_both_wheels(self):
        controller = self.controller_module.PDController()
        controller.compute(50)
        output = None
        for _ in range(31):
            output = controller.compute(None)

        self.assertEqual((0.0, 0.0), output)

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

    def test_speed_bump_command_is_not_below_dead_zone(self):
        self.assertGreaterEqual(
            self.config.SPEED_BUMP_SPEED,
            self.config.DEAD_ZONE_MIN_PWM,
        )


if __name__ == "__main__":
    unittest.main()
