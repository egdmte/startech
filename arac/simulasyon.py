"""
STARTECH visual motion simulation bridge

This module turns TAWNT-validated, memory-only motor events into deterministic
differential-drive motion. It has no Webots, GPIO, PWM, or physical-motor import.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

from .surucu import (
    FakeMotorDriver,
    InvalidMotorRequest,
    MotorOutputError,
    ValidatedDriveRequest,
)


class SimulationError(RuntimeError):
    """Base error for invalid visual-simulation operations."""


class InvalidSimulationStep(SimulationError, ValueError):
    """Raised when time or geometry would make motion meaningless."""


def _finite(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _positive(name: str, value: object) -> float:
    if not _finite(value) or float(value) <= 0:
        raise InvalidSimulationStep(f"{name} must be a finite positive number")
    return float(value)


@dataclass(frozen=True)
class WheelVelocity:
    """Target angular velocity for simulated left and right wheels, in rad/s."""

    left: float
    right: float

    def __post_init__(self) -> None:
        if not _finite(self.left) or not _finite(self.right):
            raise InvalidSimulationStep("wheel velocities must be finite numbers")


@dataclass(frozen=True)
class SimulationPose:
    """Planar center pose produced by the simple differential-drive model."""

    x: float = 0.0
    y: float = 0.0
    heading: float = 0.0
    elapsed_seconds: float = 0.0

    def __post_init__(self) -> None:
        for name, value in (
            ("x", self.x),
            ("y", self.y),
            ("heading", self.heading),
            ("elapsed_seconds", self.elapsed_seconds),
        ):
            if not _finite(value):
                raise InvalidSimulationStep(f"pose {name} must be finite")
        if self.elapsed_seconds < 0:
            raise InvalidSimulationStep("pose elapsed_seconds cannot be negative")


class VisualSimulationBridge:
    """MotorDriver-compatible recorder and deterministic visual motion source.

    ``apply`` accepts only the same ``ValidatedDriveRequest`` used by OSMAN's
    fake driver. ``step`` advances a lightweight planar model for tests and
    reporting. Webots may consume ``wheel_velocity`` to move simulated devices.
    """

    def __init__(
        self,
        *,
        max_wheel_velocity: float = 8.0,
        wheel_radius: float = 0.045,
        track_width: float = 0.15,
        recorder: FakeMotorDriver | None = None,
    ) -> None:
        self.max_wheel_velocity = _positive(
            "max_wheel_velocity", max_wheel_velocity
        )
        self.wheel_radius = _positive("wheel_radius", wheel_radius)
        self.track_width = _positive("track_width", track_width)
        self._recorder = recorder or FakeMotorDriver()
        if not isinstance(self._recorder, FakeMotorDriver):
            raise TypeError("visual simulation recorder must be FakeMotorDriver")
        self._wheel_velocity = WheelVelocity(0.0, 0.0)
        self._pose = SimulationPose()
        self._closed = False

    @property
    def wheel_velocity(self) -> WheelVelocity:
        return self._wheel_velocity

    @property
    def pose(self) -> SimulationPose:
        return self._pose

    @property
    def history(self):
        return self._recorder.history

    def apply(self, request: ValidatedDriveRequest) -> None:
        if self._closed:
            raise MotorOutputError("visual simulation bridge is closed")
        if not isinstance(request, ValidatedDriveRequest):
            raise TypeError("visual simulation accepts only ValidatedDriveRequest")
        self._recorder.apply(request)
        self._wheel_velocity = WheelVelocity(
            float(request.command.left) * self.max_wheel_velocity,
            float(request.command.right) * self.max_wheel_velocity,
        )

    def stop(self, reason: str) -> None:
        if not isinstance(reason, str) or not reason.strip():
            raise InvalidMotorRequest("visual simulation stop needs a reason")
        self._wheel_velocity = WheelVelocity(0.0, 0.0)
        self._recorder.stop(reason.strip())

    def step(self, elapsed_seconds: float) -> SimulationPose:
        if self._closed:
            raise SimulationError("visual simulation bridge is closed")
        dt = _positive("elapsed_seconds", elapsed_seconds)

        left_linear = self._wheel_velocity.left * self.wheel_radius
        right_linear = self._wheel_velocity.right * self.wheel_radius
        linear_velocity = (left_linear + right_linear) / 2.0
        angular_velocity = (right_linear - left_linear) / self.track_width
        mid_heading = self._pose.heading + angular_velocity * dt / 2.0
        next_heading = self._pose.heading + angular_velocity * dt
        next_heading = math.atan2(math.sin(next_heading), math.cos(next_heading))

        self._pose = SimulationPose(
            x=self._pose.x + linear_velocity * math.cos(mid_heading) * dt,
            y=self._pose.y + linear_velocity * math.sin(mid_heading) * dt,
            heading=next_heading,
            elapsed_seconds=self._pose.elapsed_seconds + dt,
        )
        return self._pose

    def close(self) -> None:
        if self._closed:
            return
        self.stop("visual simulation closing")
        self._recorder.close()
        self._closed = True
