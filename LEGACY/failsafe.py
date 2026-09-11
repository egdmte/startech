"""
failsafe.py — autonomous vehicle runtime safety supervisor.

Important:
    This module is deliberately independent from lane/event detection.
    Any code path that commands the motors should pass through the supervisor.

Policy:
    - Safe state is (0, 0).
    - Watchdogs are fail-closed.
    - A latched failure cannot be cleared by a normal detector update.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from time import monotonic
from typing import Optional


@dataclass(frozen=True)
class SafetyLimits:
    frame_timeout_sec: float = 0.25
    max_frame_age_sec: float = 0.20
    max_loop_dt_sec: float = 0.15
    min_loop_hz: float = 15.0
    loop_bad_count_limit: int = 5
    frame_bad_count_limit: int = 3
    motor_heartbeat_timeout_sec: float = 0.30
    max_motor_asymmetry: float = 70.0
    max_command_jump_per_frame: float = 35.0
    max_abs_lane_error_px: float = 600.0
    max_abs_derivative_px_frame: float = 250.0
    max_degraded_drive_sec: float = 0.75
    motor_command_min: float = 0.0
    motor_command_max: float = 100.0


class SafetySupervisor:
    """Runtime gatekeeper for motor commands."""

    def __init__(self, limits: SafetyLimits = SafetyLimits()) -> None:
        self.limits = limits
        self.latched = False
        self.reason: Optional[str] = None
        self.started_at = monotonic()
        self.last_frame_at: Optional[float] = None
        self.last_command_at: Optional[float] = None
        self.last_good_command_at: Optional[float] = None
        self.last_left = 0.0
        self.last_right = 0.0
        self.loop_bad_count = 0
        self.frame_bad_count = 0
        self.degraded_started_at: Optional[float] = None

    @property
    def stopped(self) -> bool:
        return self.latched

    def trip(self, reason: str) -> tuple[float, float]:
        self.latched = True
        self.reason = reason
        return 0.0, 0.0

    def startup_ready(self, now: Optional[float] = None,
                      startup_neutral_sec: float = 0.75) -> bool:
        now = monotonic() if now is None else now
        return (now - self.started_at) >= startup_neutral_sec

    def note_frame(self, frame_timestamp: float,
                   now: Optional[float] = None) -> bool:
        """Register a frame. False means the frame is too old."""
        now = monotonic() if now is None else now
        age = now - frame_timestamp

        if not isfinite(age) or age < 0:
            self.frame_bad_count += 1
        elif age > self.limits.frame_timeout_sec:
            self.frame_bad_count += 1
        else:
            self.frame_bad_count = 0
            self.last_frame_at = now

        if self.frame_bad_count >= self.limits.frame_bad_count_limit:
            self.trip("camera/frame watchdog")
            return False

        return not self.latched and age <= self.limits.max_frame_age_sec

    def note_loop(self, dt: float,
                  now: Optional[float] = None) -> bool:
        """Check control-loop timing."""
        if not isfinite(dt) or dt <= 0 or dt > self.limits.max_loop_dt_sec:
            self.loop_bad_count += 1
        else:
            hz = 1.0 / dt
            if hz < self.limits.min_loop_hz:
                self.loop_bad_count += 1
            else:
                self.loop_bad_count = 0

        if self.loop_bad_count >= self.limits.loop_bad_count_limit:
            self.trip("control loop watchdog")
            return False
        return not self.latched

    def validate_lane(self, error: float, derivative: float) -> bool:
        if not isfinite(error) or not isfinite(derivative):
            self.trip("non-finite lane control value")
            return False
        if abs(error) > self.limits.max_abs_lane_error_px:
            self.trip("lane error out of plausible range")
            return False
        if abs(derivative) > self.limits.max_abs_derivative_px_frame:
            self.trip("lane derivative out of plausible range")
            return False
        return not self.latched

    def degraded_mode(self, active: bool,
                       now: Optional[float] = None) -> bool:
        """Allow temporary degradation, but never indefinitely."""
        now = monotonic() if now is None else now
        if not active:
            self.degraded_started_at = None
            return not self.latched

        if self.degraded_started_at is None:
            self.degraded_started_at = now
            return not self.latched

        if now - self.degraded_started_at > self.limits.max_degraded_drive_sec:
            self.trip("degraded-drive timeout")
            return False

        return not self.latched

    def command(self, left: float, right: float,
                now: Optional[float] = None) -> tuple[float, float]:
        """
        Validate and return a motor command.

        Any violation returns (0, 0) and latches the supervisor.
        The actual GPIO layer must still ensure that STOP writes both channels low.
        """
        now = monotonic() if now is None else now

        if self.latched:
            return 0.0, 0.0

        if not self.startup_ready(now):
            return 0.0, 0.0

        if not (isfinite(left) and isfinite(right)):
            return self.trip("NaN/inf motor command")

        lo = self.limits.motor_command_min
        hi = self.limits.motor_command_max
        if not (lo <= left <= hi and lo <= right <= hi):
            return self.trip("motor command out of range")

        if abs(left - right) > self.limits.max_motor_asymmetry:
            return self.trip("excessive motor asymmetry")

        if self.last_command_at is not None:
            dl = abs(left - self.last_left)
            dr = abs(right - self.last_right)
            if dl > self.limits.max_command_jump_per_frame or \
               dr > self.limits.max_command_jump_per_frame:
                return self.trip("abrupt motor command change")

        self.last_left = left
        self.last_right = right
        self.last_command_at = now
        self.last_good_command_at = now
        return left, right

    def heartbeat_ok(self, now: Optional[float] = None) -> bool:
        """Must be called independently of camera/control calculations."""
        now = monotonic() if now is None else now
        if self.latched:
            return False
        if self.last_command_at is None:
            self.trip("motor command heartbeat never established")
            return False
        if now - self.last_command_at > self.limits.motor_heartbeat_timeout_sec:
            self.trip("motor command heartbeat timeout")
            return False
        return True

    def clear_after_manual_reset(self) -> None:
        """
        Explicit re-arm point.

        Do not call this automatically after a transient detector recovery.
        """
        self.latched = False
        self.reason = None
        self.last_frame_at = None
        self.last_command_at = None
        self.last_good_command_at = None
        self.last_left = 0.0
        self.last_right = 0.0
        self.loop_bad_count = 0
        self.frame_bad_count = 0
        self.degraded_started_at = None
        self.started_at = monotonic()


def safe_stop(stop_motors, supervisor: SafetySupervisor) -> None:
    """Single emergency-stop helper; stop_motors must be idempotent."""
    supervisor.trip(supervisor.reason or "external stop")
    try:
        stop_motors()
    finally:
        # Never let cleanup failure mask the fact that the supervisor is latched.
        pass
