"""
STARTECH-KASIM (CAMILA)
Kamera Akışı Sağlama ve İletim Modülü
Camera Acquisition and Monitoring Interface Layer Adapter

This module will own camera acquisition. Hardware access is not implemented yet.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from typing import Iterable, Protocol, runtime_checkable


class CameraError(RuntimeError):
    """Base error for a camera source that cannot honor its contract."""


class CameraUnavailable(CameraError):
    """Raised when code requests a camera implementation that does not exist."""


class InvalidFrame(CameraError, ValueError):
    """Raised when simulated or physical frame metadata is malformed."""


class CameraExhausted(CameraError):
    """Raised when a finite simulation has no frame left to return."""


class CameraStatus(str, Enum):
    """Observable lifecycle states shared by simulated and future real cameras."""

    DISCONNECTED = "DISCONNECTED"
    READY = "READY"
    STREAMING = "STREAMING"
    EXHAUSTED = "EXHAUSTED"
    FAILED = "FAILED"


def _is_finite_number(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


@dataclass(frozen=True)
class FramePacket:
    """One uniquely numbered frame and the time at which it was captured."""

    frame_id: int
    captured_at: float
    payload: object
    source: str = "simulation"

    def __post_init__(self) -> None:
        if isinstance(self.frame_id, bool) or not isinstance(self.frame_id, int):
            raise InvalidFrame("frame_id must be an integer, not a boolean or text")
        if self.frame_id < 0:
            raise InvalidFrame("frame_id cannot be negative")
        if not _is_finite_number(self.captured_at) or self.captured_at < 0:
            raise InvalidFrame("captured_at must be a finite non-negative number")
        if self.payload is None:
            raise InvalidFrame("a frame payload cannot be None")
        if not isinstance(self.source, str) or not self.source.strip():
            raise InvalidFrame("frame source must be a non-empty string")


@runtime_checkable
class CameraSource(Protocol):
    """Interface ARDA can use without knowing whether a camera is simulated."""

    @property
    def status(self) -> CameraStatus:
        """Return the current lifecycle state without opening the camera."""

    def open(self) -> None:
        """Prepare the source; this must not imply that a frame has arrived."""

    def read_frame(self) -> FramePacket:
        """Return one new frame or raise a camera-specific error."""

    def close(self) -> None:
        """Release the source; repeated calls must remain safe."""


class SequenceCamera:
    """Finite in-memory camera used by simulations and deterministic tests."""

    def __init__(self, frames: Iterable[FramePacket]) -> None:
        self._frames = tuple(frames)
        self._validate_sequence(self._frames)
        self._cursor = 0
        self._last_frame_id: int | None = None
        self._status = CameraStatus.DISCONNECTED

    @staticmethod
    def _validate_sequence(frames: tuple[FramePacket, ...]) -> None:
        previous: int | None = None
        for frame in frames:
            if not isinstance(frame, FramePacket):
                raise InvalidFrame("SequenceCamera accepts only FramePacket objects")
            if previous is not None and frame.frame_id <= previous:
                raise InvalidFrame("frame identifiers must be strictly increasing")
            previous = frame.frame_id

    @property
    def status(self) -> CameraStatus:
        return self._status

    def open(self) -> None:
        self._cursor = 0
        self._last_frame_id = None
        self._status = CameraStatus.READY

    def read_frame(self) -> FramePacket:
        if self._status == CameraStatus.DISCONNECTED:
            raise CameraUnavailable("camera must be opened before reading")
        if self._cursor >= len(self._frames):
            self._status = CameraStatus.EXHAUSTED
            raise CameraExhausted("the simulated camera has no frame left")

        frame = self._frames[self._cursor]
        if self._last_frame_id is not None and frame.frame_id <= self._last_frame_id:
            self._status = CameraStatus.FAILED
            raise InvalidFrame("camera attempted to replay a stale frame")

        self._cursor += 1
        self._last_frame_id = frame.frame_id
        self._status = CameraStatus.STREAMING
        return frame

    def close(self) -> None:
        self._status = CameraStatus.DISCONNECTED


class UnavailableCamera:
    """Fail-closed placeholder for the not-yet-written Raspberry Pi adapter."""

    def __init__(self, reason: str = "physical camera adapter is not implemented") -> None:
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("unavailable-camera reason must be a non-empty string")
        self.reason = reason.strip()
        self._status = CameraStatus.DISCONNECTED

    @property
    def status(self) -> CameraStatus:
        return self._status

    def open(self) -> None:
        self._status = CameraStatus.FAILED
        raise CameraUnavailable(self.reason)

    def read_frame(self) -> FramePacket:
        self._status = CameraStatus.FAILED
        raise CameraUnavailable(self.reason)

    def close(self) -> None:
        self._status = CameraStatus.DISCONNECTED
