"""STARTECH-KEREM: live lane perception and YAREN diagnostics.

The production analyzer consumes RGB frames from KASIM and uses the active
YAREN calibration. There is no generated-observation production path.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import importlib
import math
from typing import Any, Protocol, runtime_checkable

from .goz import FramePacket


class VisionError(RuntimeError):
    """Base error for a frame that cannot be interpreted."""


class VisionUnavailable(VisionError):
    """Raised when the live perception dependencies are unavailable."""


class InvalidObservation(VisionError, ValueError):
    """Raised when observation data is malformed or contradictory."""


class StaleFrame(VisionError):
    """Raised when an analyzer receives a duplicate or older frame."""


def _is_finite_number(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


@dataclass(frozen=True)
class LaneObservation:
    """One lane estimate produced from a real camera frame.

    ``error_px`` follows the LEGACY vehicle convention: positive means the lane
    centre is left of the image centre and therefore asks for a left correction.
    """

    frame_id: int
    captured_at: float
    valid: bool
    error_px: float | None
    normalized_error: float | None
    confidence: float
    lane_center_px: int | None
    left_lane_px: int | None
    right_lane_px: int | None
    brightness: float
    reason: str = ""
    debug_frame: Any | None = None

    def __post_init__(self) -> None:
        if isinstance(self.frame_id, bool) or not isinstance(self.frame_id, int):
            raise InvalidObservation("frame_id must be an integer")
        if self.frame_id < 0:
            raise InvalidObservation("frame_id cannot be negative")
        if not _is_finite_number(self.captured_at) or self.captured_at < 0:
            raise InvalidObservation("captured_at must be finite and non-negative")
        if not isinstance(self.valid, bool):
            raise InvalidObservation("valid must be a boolean")
        if not isinstance(self.reason, str):
            raise InvalidObservation("reason must be text")
        if not _is_finite_number(self.confidence) or not 0 <= self.confidence <= 1:
            raise InvalidObservation("confidence must be between 0 and 1")
        if not _is_finite_number(self.brightness) or not 0 <= self.brightness <= 255:
            raise InvalidObservation("brightness must be between 0 and 255")
        if self.valid:
            if not _is_finite_number(self.error_px):
                raise InvalidObservation("valid lane result needs error_px")
            if not _is_finite_number(self.normalized_error):
                raise InvalidObservation("valid lane result needs normalized_error")
            if not -1 <= float(self.normalized_error) <= 1:
                raise InvalidObservation("normalized_error must be in [-1, 1]")
            if self.lane_center_px is None or self.confidence <= 0:
                raise InvalidObservation("valid lane result needs a centre and confidence")
        else:
            if self.error_px is not None or self.normalized_error is not None:
                raise InvalidObservation("invalid lane result cannot claim an error")
            if self.lane_center_px is not None or self.confidence != 0:
                raise InvalidObservation("invalid lane result cannot claim a centre")
            if not self.reason.strip():
                raise InvalidObservation("invalid lane result must explain why")

    def record_data(self) -> dict[str, object]:
        """Return JSON-safe telemetry without retaining the image payload."""

        return {
            "frame_id": self.frame_id,
            "captured_at": self.captured_at,
            "valid": self.valid,
            "error_px": self.error_px,
            "normalized_error": self.normalized_error,
            "confidence": self.confidence,
            "lane_center_px": self.lane_center_px,
            "left_lane_px": self.left_lane_px,
            "right_lane_px": self.right_lane_px,
            "brightness": self.brightness,
            "reason": self.reason,
        }


class LaneVisionAnalyzer:
    """Perspective-warped adaptive white-lane detector from the working LEGACY path."""

    FAR_RATIO = 0.35
    NEAR_RATIO = 0.40
    FAR_WEIGHT = 0.60
    NEAR_WEIGHT = 0.40
    MEMORY_FRAMES = 25
    SEARCH_WINDOW = 120

    def __init__(self, calibration: Mapping[str, Any]) -> None:
        if not isinstance(calibration, Mapping):
            raise TypeError("lane analyzer needs a YAREN calibration mapping")
        try:
            cv2 = importlib.import_module("cv2")
            np = importlib.import_module("numpy")
        except ImportError as exc:
            raise VisionUnavailable(
                "live lane perception needs OpenCV and NumPy"
            ) from exc

        camera = calibration["kamera"]
        perspective = calibration["perspektif"]
        lane = calibration["serit"]
        self.width = int(camera["genislik"])
        self.height = int(camera["yukseklik"])
        measured = tuple(int(item) for item in perspective["olculen_cozunurluk"])
        if measured != (self.width, self.height):
            raise InvalidObservation(
                "perspective calibration resolution does not match the camera"
            )
        self.bird_width = self.width
        self.bird_height = int(self.height * (1 - float(perspective["roi_ust_oran"])))
        if self.bird_height < 2:
            raise InvalidObservation("perspective ROI leaves no usable image")

        self._cv2 = cv2
        self._np = np
        source = np.float32(perspective["kaynak_noktalar"])
        target = np.float32(
            [[0, 0], [self.bird_width - 1, 0],
             [0, self.bird_height - 1],
             [self.bird_width - 1, self.bird_height - 1]]
        )
        self._matrix = cv2.getPerspectiveTransform(source, target)
        self._profiles = lane["beyaz_profiller"]
        self._profile_thresholds = lane["profil_esikleri"]
        self._minimum_signal = float(lane["min_sinyal"])
        self._minimum_quality_ratio = float(lane["min_sinyal_kalite_orani"])
        self._assumed_lane_width = int(lane["varsayilan_serit_genisligi"])
        self._continuity_ratio = float(lane["sureklilik_orani"])
        tile = int(lane["clahe_kutucuk"])
        self._clahe = cv2.createCLAHE(
            clipLimit=float(lane["clahe_sinir"]), tileGridSize=(tile, tile)
        )
        self._kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        self._left_memory: tuple[int, int] | None = None
        self._right_memory: tuple[int, int] | None = None
        self._last_frame_id: int | None = None

    def analyze(self, frame: FramePacket) -> LaneObservation:
        if not isinstance(frame, FramePacket):
            raise InvalidObservation("lane analyzer accepts only FramePacket objects")
        if self._last_frame_id is not None and frame.frame_id <= self._last_frame_id:
            raise StaleFrame("lane analyzer received a stale or duplicate frame")
        self._last_frame_id = frame.frame_id

        shape = getattr(frame.payload, "shape", None)
        if not isinstance(shape, tuple) or len(shape) < 2:
            raise InvalidObservation("camera payload is not an image array")
        if (int(shape[1]), int(shape[0])) != (self.width, self.height):
            raise InvalidObservation(
                f"camera produced {int(shape[1])}x{int(shape[0])}; "
                f"active calibration requires {self.width}x{self.height}"
            )

        cv2, np = self._cv2, self._np
        bird = cv2.warpPerspective(
            frame.payload, self._matrix, (self.bird_width, self.bird_height)
        )
        lab = cv2.cvtColor(bird, cv2.COLOR_RGB2LAB)
        lightness, channel_a, channel_b = cv2.split(lab)
        equalized = self._clahe.apply(lightness)
        processed = cv2.cvtColor(
            cv2.merge((equalized, channel_a, channel_b)), cv2.COLOR_LAB2RGB
        )
        hsv = cv2.cvtColor(processed, cv2.COLOR_RGB2HSV)
        brightness = float(np.mean(hsv[:, :, 2]))
        profile_name = self._select_profile(brightness)
        profile = self._profiles.get(profile_name, self._profiles["varsayilan"])
        mask = cv2.inRange(
            hsv,
            np.array(profile["alt"], dtype=np.uint8),
            np.array(profile["ust"], dtype=np.uint8),
        )
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, self._kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, self._kernel)

        column_coverage = (mask > 0).sum(axis=0).astype(np.float32)
        required_coverage = max(self.bird_height * self._continuity_ratio, 1.0)
        continuity = np.minimum(column_coverage / required_coverage, 1.0)
        near_rows = max(1, int(self.bird_height * self.NEAR_RATIO))
        far_rows = max(1, int(self.bird_height * self.FAR_RATIO))

        def histogram(part: Any) -> Any:
            values = np.sum(part, axis=0).astype(np.float32) * continuity
            return cv2.GaussianBlur(values.reshape(1, -1), (1, 31), 0).flatten()

        near_histogram = histogram(mask[self.bird_height - near_rows :])
        far_histogram = histogram(mask[:far_rows])
        midpoint = self.bird_width // 2

        near_left, near_left_seen, near_left_quality = self._find_peak(
            near_histogram, 0, midpoint,
            self._left_memory[0] if self._left_memory else None,
        )
        near_right, near_right_seen, near_right_quality = self._find_peak(
            near_histogram, midpoint, self.bird_width,
            self._right_memory[0] if self._right_memory else None,
        )
        left_valid = self._update_memory("left", near_left, near_left_seen)
        right_valid = self._update_memory("right", near_right, near_right_seen)
        if left_valid and self._left_memory:
            near_left = self._left_memory[0]
        if right_valid and self._right_memory:
            near_right = self._right_memory[0]

        far_left, far_left_seen, far_left_quality = self._find_peak(
            far_histogram, 0, midpoint, None
        )
        far_right, far_right_seen, far_right_quality = self._find_peak(
            far_histogram, midpoint, self.bird_width, None
        )
        near_center = self._lane_center(
            near_left, left_valid, near_right, right_valid
        )
        far_center = self._lane_center(
            far_left, far_left_seen, far_right, far_right_seen
        )

        if near_center is None and far_center is None:
            return LaneObservation(
                frame_id=frame.frame_id,
                captured_at=frame.captured_at,
                valid=False,
                error_px=None,
                normalized_error=None,
                confidence=0.0,
                lane_center_px=None,
                left_lane_px=near_left if left_valid else None,
                right_lane_px=near_right if right_valid else None,
                brightness=brightness,
                reason="no lane signal",
                debug_frame=self._draw_debug(processed, mask, None, None, None),
            )

        if near_center is None:
            lane_center = float(far_center)
        elif far_center is None:
            lane_center = float(near_center)
        else:
            lane_center = (
                self.NEAR_WEIGHT * near_center + self.FAR_WEIGHT * far_center
            )
        error = float(midpoint - lane_center)
        normalized = max(-1.0, min(1.0, error / max(midpoint, 1)))
        qualities = [
            value for value, seen in (
                (near_left_quality, left_valid),
                (near_right_quality, right_valid),
                (far_left_quality, far_left_seen),
                (far_right_quality, far_right_seen),
            ) if seen
        ]
        confidence = min(1.0, max(qualities, default=0.01))
        if confidence <= 0:
            confidence = 0.01
        center_int = int(round(lane_center))
        return LaneObservation(
            frame_id=frame.frame_id,
            captured_at=frame.captured_at,
            valid=True,
            error_px=error,
            normalized_error=normalized,
            confidence=confidence,
            lane_center_px=center_int,
            left_lane_px=near_left if left_valid else None,
            right_lane_px=near_right if right_valid else None,
            brightness=brightness,
            debug_frame=self._draw_debug(
                processed, mask,
                near_left if left_valid else None,
                near_right if right_valid else None,
                center_int,
            ),
        )

    def _select_profile(self, brightness: float) -> str:
        if brightness < float(self._profile_thresholds["karanlik_alti"]):
            return "karanlik"
        if brightness > float(self._profile_thresholds["parlak_ustu"]):
            return "parlak"
        return "normal"

    def _find_peak(
        self, histogram: Any, lower: int, upper: int, last: int | None
    ) -> tuple[int, bool, float]:
        if last is None:
            search_lower, search_upper = lower, upper
        else:
            search_lower = max(lower, last - self.SEARCH_WINDOW)
            search_upper = min(upper, last + self.SEARCH_WINDOW)
        region = histogram[search_lower:search_upper]
        total = float(region.sum())
        if total < self._minimum_signal:
            search_lower, search_upper = lower, upper
            region = histogram[lower:upper]
            total = float(region.sum())
        if total < self._minimum_signal:
            fallback = last if last is not None else (lower + upper) // 2
            return fallback, False, 0.0
        coordinates = self._np.arange(search_lower, search_upper)
        position = int(self._np.average(coordinates, weights=region))
        quality = total / max(self._minimum_signal * self._minimum_quality_ratio, 1.0)
        return max(lower, min(upper - 1, position)), True, min(1.0, quality)

    def _update_memory(self, side: str, position: int, seen: bool) -> bool:
        attribute = f"_{side}_memory"
        if seen:
            setattr(self, attribute, (position, 0))
            return True
        memory = getattr(self, attribute)
        if memory is not None and memory[1] < self.MEMORY_FRAMES:
            setattr(self, attribute, (memory[0], memory[1] + 1))
            return True
        setattr(self, attribute, None)
        return False

    def _lane_center(
        self, left: int, left_valid: bool, right: int, right_valid: bool
    ) -> float | None:
        if left_valid and right_valid:
            return (left + right) / 2
        if left_valid:
            return left + self._assumed_lane_width / 2
        if right_valid:
            return right - self._assumed_lane_width / 2
        return None

    def _draw_debug(
        self, image: Any, mask: Any, left: int | None,
        right: int | None, center: int | None,
    ) -> Any:
        cv2 = self._cv2
        debug = cv2.addWeighted(
            image, 0.65, cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB), 0.35, 0
        )
        if left is not None:
            cv2.line(debug, (left, 0), (left, self.bird_height - 1), (0, 220, 0), 2)
        if right is not None:
            cv2.line(debug, (right, 0), (right, self.bird_height - 1), (0, 220, 0), 2)
        if center is not None:
            cv2.line(debug, (center, 0), (center, self.bird_height - 1), (255, 60, 0), 2)
        cv2.line(
            debug, (self.bird_width // 2, 0),
            (self.bird_width // 2, self.bird_height - 1), (0, 80, 255), 1,
        )
        return debug


# ---------------------------------------------------------------------------
# YAREN bounded diagnostic compatibility. This is not ARDA's driving vision.

@dataclass(frozen=True)
class Observation:
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
        if (
            self.frame_id < 0 or not _is_finite_number(self.captured_at)
            or self.captured_at < 0
        ):
            raise InvalidObservation("frame metadata is invalid")
        if not isinstance(self.valid, bool):
            raise InvalidObservation("valid must be a boolean")
        if not _is_finite_number(self.confidence) or not 0 <= self.confidence <= 1:
            raise InvalidObservation("confidence must be between 0 and 1")
        if not isinstance(self.reason, str):
            raise InvalidObservation("reason must be text")
        if self.detected_sign is not None and (
            not isinstance(self.detected_sign, str) or not self.detected_sign.strip()
        ):
            raise InvalidObservation("detected_sign must be non-empty text or None")
        if self.valid:
            if not _is_finite_number(self.lane_error) or not -1 <= self.lane_error <= 1:
                raise InvalidObservation("valid observation needs normalized lane_error")
            if not isinstance(self.obstacle, bool) or self.confidence <= 0:
                raise InvalidObservation("valid observation is incomplete")
        elif (
            self.lane_error is not None or self.detected_sign is not None
            or self.obstacle is not None or self.confidence != 0 or not self.reason.strip()
        ):
            raise InvalidObservation("invalid observation must contain only a reason")

    @classmethod
    def invalid_from(cls, frame: FramePacket, reason: str) -> "Observation":
        return cls(frame.frame_id, frame.captured_at, False, None, None, None, 0.0, reason)


@runtime_checkable
class VisionAnalyzer(Protocol):
    def analyze(self, frame: FramePacket) -> Observation:
        """Analyze a bounded diagnostic frame."""


__all__ = [
    "InvalidObservation", "LaneObservation", "LaneVisionAnalyzer", "Observation",
    "StaleFrame", "VisionAnalyzer", "VisionError", "VisionUnavailable",
]
