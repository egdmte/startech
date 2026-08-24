"""Finite Webots visualization driven through TAWNT's Webots-only bridge.

The devices in this file are Webots simulation devices. This controller never
imports GPIO libraries and cannot address the physical STARTECH car.
"""

from __future__ import annotations

import os
from pathlib import Path
import sys

from controller import Supervisor


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

import tawnt
from arac.simulasyon import VisualSimulationBridge
from arac.surucu import MotorRequest, validate_request


PHASE = "WEBOTS_VISUAL"
MAX_WHEEL_VELOCITY = 8.0
DEMO_SEGMENTS = (
    (2.4, 0.55, 0.55, "leave the start line"),
    (1.4, 0.25, 0.65, "demonstrate a left arc"),
    (1.8, 0.60, 0.60, "continue straight"),
    (1.2, 0.60, 0.20, "demonstrate a right arc"),
    (1.4, 0.45, 0.45, "approach the finish line"),
)


def configure_tawnt_for_visual_demo() -> None:
    """Create one offline-only phase for simulated motion."""

    tawnt.sifirla()
    tawnt.definePhase(
        PHASE,
        motion_allowed=True,
        allow_reverse=True,
        allow_pivot=True,
        max_pwm=1.0,
        max_difference=2.0,
        allowed_from=(None,),
    )
    tawnt.validateBeforeStart(profile=tawnt.OFFLINE)
    tawnt.enterPhase(PHASE)
    tawnt.arm("finite Webots visual simulation")


class ArdaVisualController:
    """Apply a finite sequence to Webots' four simulated wheel motors."""

    MOTOR_NAMES = (
        "front left wheel motor",
        "rear left wheel motor",
        "front right wheel motor",
        "rear right wheel motor",
    )

    def __init__(self) -> None:
        self.robot = Supervisor()
        self.time_step = int(self.robot.getBasicTimeStep())
        self.bridge = VisualSimulationBridge(
            max_wheel_velocity=MAX_WHEEL_VELOCITY,
            wheel_radius=0.045,
            track_width=0.164,
        )
        self.motors = [self.robot.getDevice(name) for name in self.MOTOR_NAMES]
        if any(motor is None for motor in self.motors):
            raise RuntimeError("Webots world is missing a named wheel motor")
        for motor in self.motors:
            motor.setPosition(float("inf"))
            motor.setVelocity(0.0)

    def apply_segment(self, left: float, right: float, reason: str) -> None:
        request = MotorRequest(left, right, PHASE, reason)
        validated = validate_request(request)
        self.bridge.apply(validated)
        targets = self.bridge.wheel_velocity
        for motor in self.motors[:2]:
            motor.setVelocity(targets.left)
        for motor in self.motors[2:]:
            motor.setVelocity(targets.right)
        print(
            "STARTECH_WEBOTS_SEGMENT "
            f"left={left:.2f} right={right:.2f} reason={reason}"
        )

    def request_stop(self, reason: str) -> None:
        self.bridge.stop(reason)
        for motor in self.motors:
            motor.setVelocity(0.0)

    def run(self) -> None:
        configure_tawnt_for_visual_demo()
        dt = self.time_step / 1000.0
        try:
            for duration, left, right, reason in DEMO_SEGMENTS:
                self.apply_segment(left, right, reason)
                remaining = duration
                while remaining > 0:
                    if self.robot.step(self.time_step) == -1:
                        return
                    self.bridge.step(dt)
                    remaining -= dt
            self.request_stop("finite visual demonstration completed")
            self.robot.step(self.time_step)
            pose = self.bridge.pose
            print(
                "STARTECH_WEBOTS_OK "
                f"x={pose.x:.3f} y={pose.y:.3f} heading={pose.heading:.3f} "
                f"events={len(self.bridge.history)}",
                flush=True,
            )
        finally:
            self.request_stop("Webots controller cleanup")
            self.bridge.close()
            tawnt.sifirla()

        if os.environ.get("STARTECH_WEBOTS_AUTOCLOSE") == "1":
            self.robot.step(self.time_step)
            self.robot.simulationQuit(0)


if __name__ == "__main__":
    ArdaVisualController().run()
