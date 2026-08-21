"""
STARTECH-OSMAN (MATT)
Otonom Sürüş Motor Aktarım Noktası
Motor Actuation and Transfer Terminal

OSMAN is the only planned route to physical motor output. This scaffold contains
structural request validation, a Tawnt validation bridge, a memory-only driver,
and a physical-output placeholder that always refuses commands.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import math
import time
from typing import Protocol, runtime_checkable

import tawnt


class MotorOutputError(RuntimeError):
    """Base error for a motor request that cannot safely reach a driver."""


class InvalidMotorRequest(MotorOutputError, ValueError):
    """Raised before Tawnt when request structure or normalized values are invalid."""


class PhysicalOutputBlocked(MotorOutputError):
    """Raised by the placeholder that represents unavailable physical hardware."""


class DriverAction(str, Enum):
    """Actions recorded by test drivers without claiming physical movement."""

    APPLY = "APPLY"
    STOP_REQUESTED = "STOP_REQUESTED"
    CLOSE = "CLOSE"


def _is_finite_number(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


@dataclass(frozen=True)
class MotorRequest:
    """Untrusted normalized motor intent produced above the physical driver."""

    left: float
    right: float
    phase: str
    reason: str
    frame_id: int | None = None
    created_at: float = field(default_factory=time.monotonic)

    def __post_init__(self) -> None:
        for name, value in (("left", self.left), ("right", self.right)):
            if not _is_finite_number(value):
                raise InvalidMotorRequest(f"{name} must be a finite number")
            if not -1.0 <= float(value) <= 1.0:
                raise InvalidMotorRequest(f"{name} must be normalized to [-1, 1]")
        if not isinstance(self.phase, str) or not self.phase.strip():
            raise InvalidMotorRequest("phase must be non-empty text")
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise InvalidMotorRequest("every motor request must explain its reason")
        if self.frame_id is not None:
            if isinstance(self.frame_id, bool) or not isinstance(self.frame_id, int):
                raise InvalidMotorRequest("frame_id must be an integer or None")
            if self.frame_id < 0:
                raise InvalidMotorRequest("frame_id cannot be negative")
        if not _is_finite_number(self.created_at) or self.created_at < 0:
            raise InvalidMotorRequest("created_at must be finite and non-negative")

    @classmethod
    def stop(
        cls,
        *,
        phase: str,
        reason: str,
        frame_id: int | None = None,
        created_at: float | None = None,
    ) -> "MotorRequest":
        """Create an explicit zero request; it still requires Tawnt validation."""

        values = {
            "left": 0.0,
            "right": 0.0,
            "phase": phase,
            "reason": reason,
            "frame_id": frame_id,
        }
        if created_at is not None:
            values["created_at"] = created_at
        return cls(**values)


@dataclass(frozen=True)
class ValidatedDriveRequest:
    """A MotorRequest paired with the exact command object returned by Tawnt."""

    request: MotorRequest
    command: tawnt.ValidatedMotorCommand

    def __post_init__(self) -> None:
        if not isinstance(self.request, MotorRequest):
            raise TypeError("request must be a MotorRequest")
        if not isinstance(self.command, tawnt.ValidatedMotorCommand):
            raise TypeError("command must come from tawnt.validateMotorCommand")
        if self.command.phase != self.request.phase:
            raise InvalidMotorRequest("Tawnt command phase does not match the request")
        if (
            float(self.command.left) != float(self.request.left)
            or float(self.command.right) != float(self.request.right)
        ):
            raise InvalidMotorRequest("Tawnt command values do not match the request")


@dataclass(frozen=True)
class DriverEvent:
    """Memory-only evidence of what a fake or blocked driver was asked to do."""

    action: DriverAction
    left: float
    right: float
    reason: str
    frame_id: int | None
    recorded_at: float = field(default_factory=time.monotonic)


def validate_request(request: MotorRequest) -> ValidatedDriveRequest:
    """Pass a structurally valid request through Tawnt's existing motion gate."""

    if not isinstance(request, MotorRequest):
        raise TypeError("validate_request accepts only MotorRequest")
    command = tawnt.validateMotorCommand(
        request.left,
        request.right,
        phase=request.phase,
    )
    return ValidatedDriveRequest(request=request, command=command)


@runtime_checkable
class MotorDriver(Protocol):
    """Driver boundary; raw MotorRequest objects are intentionally not accepted."""

    def apply(self, request: ValidatedDriveRequest) -> None:
        """Apply a Tawnt-validated request or raise a driver-specific error."""

    def stop(self, reason: str) -> None:
        """Request a zero output without claiming that physical motion stopped."""

    def close(self) -> None:
        """Release resources; repeated calls must remain safe."""


class FakeMotorDriver:
    """Memory-only driver for simulations; it contains no GPIO or PWM library."""

    def __init__(self) -> None:
        self._history: list[DriverEvent] = []
        self._closed = False

    @property
    def history(self) -> tuple[DriverEvent, ...]:
        return tuple(self._history)

    def apply(self, request: ValidatedDriveRequest) -> None:
        if self._closed:
            raise MotorOutputError("fake driver is closed")
        if not isinstance(request, ValidatedDriveRequest):
            raise TypeError("driver accepts only ValidatedDriveRequest")
        self._history.append(
            DriverEvent(
                action=DriverAction.APPLY,
                left=float(request.command.left),
                right=float(request.command.right),
                reason=request.request.reason.strip(),
                frame_id=request.request.frame_id,
            )
        )

    def stop(self, reason: str) -> None:
        if not isinstance(reason, str) or not reason.strip():
            raise InvalidMotorRequest("stop request needs a non-empty reason")
        self._history.append(
            DriverEvent(
                action=DriverAction.STOP_REQUESTED,
                left=0.0,
                right=0.0,
                reason=reason.strip(),
                frame_id=None,
            )
        )

    def close(self) -> None:
        if self._closed:
            return
        self.stop("fake driver closing")
        self._closed = True
        self._history.append(
            DriverEvent(
                action=DriverAction.CLOSE,
                left=0.0,
                right=0.0,
                reason="fake driver closed",
                frame_id=None,
            )
        )


class BlockedMotorDriver:
    """Default physical placeholder: all motion requests are rejected."""

    def __init__(self, reason: str = "physical motor adapter is not implemented") -> None:
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("blocked-driver reason must be non-empty text")
        self.reason = reason.strip()
        self.stop_requests: list[str] = []
        self.closed = False

    def apply(self, request: ValidatedDriveRequest) -> None:
        if not isinstance(request, ValidatedDriveRequest):
            raise TypeError("driver accepts only ValidatedDriveRequest")
        raise PhysicalOutputBlocked(self.reason)

    def stop(self, reason: str) -> None:
        if not isinstance(reason, str) or not reason.strip():
            raise InvalidMotorRequest("stop request needs a non-empty reason")
        self.stop_requests.append(reason.strip())

    def close(self) -> None:
        if self.closed:
            return
        self.stop("blocked driver closing")
        self.closed = True
