"""Tests for the memory-only differential-drive visual simulation bridge."""

from __future__ import annotations

import math
import unittest

import tawnt
from arac.simulasyon import (
    InvalidSimulationStep,
    SimulationError,
    VisualSimulationBridge,
    WebotsCommandAction,
)
from arac.surucu import MotorRequest, validate_request


class VisualSimulationBridgeTest(unittest.TestCase):
    def setUp(self):
        tawnt.sifirla()
        tawnt.definePhase(
            "WEBOTS_VISUAL",
            motion_allowed=True,
            allow_reverse=True,
            allow_pivot=True,
            max_pwm=1.0,
            max_difference=2.0,
            allowed_from=(None,),
        )
        tawnt.validateBeforeStart(profile=tawnt.OFFLINE)
        tawnt.enterPhase("WEBOTS_VISUAL")
        tawnt.arm("visual simulation unit test")

    def tearDown(self):
        tawnt.sifirla()

    def validated(self, left, right, reason="simulation test"):
        return validate_request(
            MotorRequest(left, right, "WEBOTS_VISUAL", reason)
        )

    def test_raw_requests_remain_rejected(self):
        bridge = VisualSimulationBridge()
        raw = MotorRequest(0.2, 0.2, "WEBOTS_VISUAL", "raw request")

        with self.assertRaises(TypeError):
            bridge.apply(raw)

        self.assertEqual((), bridge.history)

    def test_validated_request_maps_to_simulated_wheel_velocity(self):
        bridge = VisualSimulationBridge(max_wheel_velocity=10.0)

        bridge.apply(self.validated(0.4, -0.25))

        self.assertEqual(4.0, bridge.wheel_velocity.left)
        self.assertEqual(-2.5, bridge.wheel_velocity.right)
        self.assertEqual(WebotsCommandAction.APPLY, bridge.history[-1].action)

    def test_equal_wheels_move_straight(self):
        bridge = VisualSimulationBridge(
            max_wheel_velocity=10.0,
            wheel_radius=0.05,
            track_width=0.2,
        )
        bridge.apply(self.validated(0.5, 0.5))

        pose = bridge.step(2.0)

        self.assertAlmostEqual(0.5, pose.x)
        self.assertAlmostEqual(0.0, pose.y)
        self.assertAlmostEqual(0.0, pose.heading)
        self.assertEqual(2.0, pose.elapsed_seconds)

    def test_unequal_wheels_change_heading(self):
        bridge = VisualSimulationBridge(
            max_wheel_velocity=10.0,
            wheel_radius=0.05,
            track_width=0.2,
        )
        bridge.apply(self.validated(0.2, 0.6))

        pose = bridge.step(1.0)

        self.assertGreater(pose.heading, 0.0)
        self.assertGreater(pose.x, 0.0)
        self.assertTrue(math.isfinite(pose.y))

    def test_stop_freezes_pose_during_later_steps(self):
        bridge = VisualSimulationBridge()
        bridge.apply(self.validated(0.5, 0.5))
        moving_pose = bridge.step(0.5)
        bridge.stop("scripted stop")

        stopped_pose = bridge.step(1.0)

        self.assertEqual((0.0, 0.0), (
            bridge.wheel_velocity.left,
            bridge.wheel_velocity.right,
        ))
        self.assertAlmostEqual(moving_pose.x, stopped_pose.x)
        self.assertAlmostEqual(moving_pose.y, stopped_pose.y)
        self.assertEqual(WebotsCommandAction.STOP_REQUESTED, bridge.history[-1].action)

    def test_invalid_geometry_and_time_are_rejected(self):
        with self.assertRaises(InvalidSimulationStep):
            VisualSimulationBridge(track_width=0.0)
        with self.assertRaises(InvalidSimulationStep):
            VisualSimulationBridge(wheel_radius=float("nan"))

        bridge = VisualSimulationBridge()
        for invalid in (0.0, -1.0, float("inf"), True):
            with self.subTest(value=invalid):
                with self.assertRaises(InvalidSimulationStep):
                    bridge.step(invalid)

    def test_close_is_idempotent_and_prevents_more_motion(self):
        bridge = VisualSimulationBridge()
        bridge.close()
        bridge.close()

        self.assertEqual((0.0, 0.0), (
            bridge.wheel_velocity.left,
            bridge.wheel_velocity.right,
        ))
        with self.assertRaises(SimulationError):
            bridge.step(0.1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
