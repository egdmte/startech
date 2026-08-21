"""
STARTECH-KEREM (CORA)
Kamera ile Engel ve Rota Eşleme Modülü
Camera Object Recognition Agent

KEREM converts a validated camera frame into a conservative observation. The
current analyzer reads deterministic simulation payloads; it performs no OpenCV
or physical-camera work.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import math
from typing import Protocol, runtime_checkable

from .goz import FramePacket


class VisionError(RuntimeError):
    """Base error for a vision request that cannot be interpreted safely."""


class InvalidObservation(VisionError, ValueError):
    """Raised when observation data is malformed or internally contradictory."""


class StaleFrame(VisionError):
    """Raised when an analyzer receives a duplicate or older frame identifier."""


def _is_finite_number(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


@dataclass(frozen=True)
class Observation:
    """What KEREM knows about one frame, including whether that knowledge is valid."""

    frame_id: int
    captured_at: float
    valid: bool
    lane_error: float | None
    detected_sign: str | None
    obstacle: bool | None
    confidence: float
    reason: str = ""

    def __post_init__(self) -> None:
        if isinstance(self.frame_id, bool) or not isinstance(self.frame_id, int):
            raise InvalidObservation("frame_id must be an integer")
        if self.frame_id < 0:
            raise InvalidObservation("frame_id cannot be negative")
        if not _is_finite_number(self.captured_at) or self.captured_at < 0:
            raise InvalidObservation("captured_at must be finite and non-negative")
        if not isinstance(self.valid, bool):
            raise InvalidObservation("valid must be a boolean")
        if not _is_finite_number(self.confidence):
            raise InvalidObservation("confidence must be a finite number")
        if not 0.0 <= float(self.confidence) <= 1.0:
            raise InvalidObservation("confidence must be between 0 and 1")
        if self.detected_sign is not None and (
            not isinstance(self.detected_sign, str)
            or not self.detected_sign.strip()
        ):
            raise InvalidObservation("detected_sign must be None or non-empty text")
        if not isinstance(self.reason, str):
            raise InvalidObservation("reason must be text")

        if self.valid:
            if not _is_finite_number(self.lane_error):
                raise InvalidObservation("a valid observation needs finite lane_error")
            if not -1.0 <= float(self.lane_error) <= 1.0:
                raise InvalidObservation("lane_error must be normalized to [-1, 1]")
            if not isinstance(self.obstacle, bool):
                raise InvalidObservation("a valid observation needs obstacle=True/False")
            if self.confidence <= 0:
                raise InvalidObservation("a valid observation needs positive confidence")
        else:
            if self.lane_error is not None:
                raise InvalidObservation("invalid observation cannot claim lane_error")
            if self.detected_sign is not None:
                raise InvalidObservation("invalid observation cannot claim a sign")
            if self.obstacle is not None:
                raise InvalidObservation("invalid observation cannot clear an obstacle")
            if self.confidence != 0:
                raise InvalidObservation("invalid observation must have zero confidence")
            if not self.reason.strip():
                raise InvalidObservation("invalid observation must explain why")

    @classmethod
    def invalid_from(cls, frame: FramePacket, reason: str) -> "Observation":
        """Create an explicit unknown result without inventing clear-road values."""

        return cls(
            frame_id=frame.frame_id,
            captured_at=frame.captured_at,
            valid=False,
            lane_error=None,
            detected_sign=None,
            obstacle=None,
            confidence=0.0,
            reason=reason,
        )


@runtime_checkable
class VisionAnalyzer(Protocol):
    """Interface implemented by simulation and future OpenCV analyzers."""

    def analyze(self, frame: FramePacket) -> Observation:
        """Analyze one new frame or raise a vision-specific error."""


class SimulatedVisionAnalyzer:
    """Convert explicit mapping payloads into validated observations."""

    _ALLOWED_FIELDS = {
        "valid",
        "lane_error",
        "detected_sign",
        "obstacle",
        "confidence",
        "reason",
    }

    def __init__(self) -> None:
        self._last_frame_id: int | None = None

    def analyze(self, frame: FramePacket) -> Observation:
        if not isinstance(frame, FramePacket):
            raise InvalidObservation("analyzer accepts only FramePacket objects")
        if self._last_frame_id is not None and frame.frame_id <= self._last_frame_id:
            raise StaleFrame("vision analyzer received a stale or duplicate frame")
        self._last_frame_id = frame.frame_id

        if not isinstance(frame.payload, Mapping):
            raise InvalidObservation("simulation payload must be a mapping")
        unknown = set(frame.payload) - self._ALLOWED_FIELDS
        if unknown:
            raise InvalidObservation(
                "unknown simulation fields: " + ", ".join(sorted(map(str, unknown)))
            )
        if "valid" not in frame.payload or not isinstance(frame.payload["valid"], bool):
            raise InvalidObservation("simulation payload needs explicit valid=True/False")

        if frame.payload["valid"] is False:
            claimed_fields = set(frame.payload) - {"valid", "reason"}
            if claimed_fields:
                raise InvalidObservation(
                    "invalid simulation payload cannot claim: "
                    + ", ".join(sorted(claimed_fields))
                )
            reason = frame.payload.get("reason")
            if not isinstance(reason, str) or not reason.strip():
                raise InvalidObservation("invalid simulation payload needs a reason")
            return Observation.invalid_from(frame, reason.strip())

        required = {"lane_error", "obstacle", "confidence"}
        missing = required - set(frame.payload)
        if missing:
            raise InvalidObservation(
                "valid simulation payload is missing: "
                + ", ".join(sorted(missing))
            )

        return Observation(
            frame_id=frame.frame_id,
            captured_at=frame.captured_at,
            valid=True,
            lane_error=frame.payload["lane_error"],
            detected_sign=frame.payload.get("detected_sign"),
            obstacle=frame.payload["obstacle"],
            confidence=frame.payload["confidence"],
            reason=str(frame.payload.get("reason", "")),
        )


class UnavailableVisionAnalyzer:
    """Return an explicit invalid observation until real perception exists."""

    def __init__(self, reason: str = "physical vision analyzer is not implemented") -> None:
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("unavailable-vision reason must be non-empty text")
        self.reason = reason.strip()

    def analyze(self, frame: FramePacket) -> Observation:
        if not isinstance(frame, FramePacket):
            raise InvalidObservation("analyzer accepts only FramePacket objects")
        return Observation.invalid_from(frame, self.reason)
