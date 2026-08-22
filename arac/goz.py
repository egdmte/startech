"""
STARTECH-KASIM (CAMILA)
Kamera Akışı Sağlama ve İletim Modülü
Camera Acquisition and Monitoring Interface Layer Adapter

This module will own camera acquisition. Hardware access is not implemented yet.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
import importlib
import math
import time
from typing import Iterable, Protocol, runtime_checkable


class CameraError(RuntimeError):
    """Base error for a camera source that cannot honor its contract."""


class CameraUnavailable(CameraError):
    """Raised when code requests a camera implementation that does not exist."""


class InvalidFrame(CameraError, ValueError):
    """Raised when simulated or physical frame metadata is malformed."""


class CameraExhausted(CameraError):
    """Raised when a finite simulation has no frame left to return."""


class CameraReadFailure(CameraError):
    """Raised when an opened physical camera cannot return a usable new frame."""


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


def _frame_dimensions(payload: object) -> tuple[int, int]:
    """Read ``width, height`` from an array-like payload without importing NumPy."""

    shape = getattr(payload, "shape", None)
    if not isinstance(shape, tuple) or len(shape) < 2:
        raise InvalidFrame("physical frame payload must expose a height/width shape")
    try:
        height = int(shape[0])
        width = int(shape[1])
    except (TypeError, ValueError, OverflowError) as exc:
        raise InvalidFrame("physical frame dimensions must be integers") from exc
    if height <= 0 or width <= 0:
        raise InvalidFrame("physical frame dimensions must be positive")
    return width, height


@dataclass(frozen=True)
class CameraProbeResult:
    """Metadata from a finite diagnostic; image payloads are never retained here."""

    source: str
    frame_count: int
    width: int
    height: int
    elapsed_seconds: float

    def __post_init__(self) -> None:
        if not isinstance(self.source, str) or not self.source.strip():
            raise ValueError("probe source must be non-empty text")
        if (
            isinstance(self.frame_count, bool)
            or not isinstance(self.frame_count, int)
            or self.frame_count <= 0
        ):
            raise ValueError("probe frame_count must be a positive integer")
        for name, value in (("width", self.width), ("height", self.height)):
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"probe {name} must be a positive integer")
        if not _is_finite_number(self.elapsed_seconds) or self.elapsed_seconds < 0:
            raise ValueError("probe elapsed_seconds must be finite and non-negative")


class OpenCvUsbCamera:
    """USB camera adapter using a lazily imported OpenCV ``VideoCapture``."""

    def __init__(
        self,
        device_index: int = 0,
        *,
        capture_factory: Callable[[int], object] | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if (
            isinstance(device_index, bool)
            or not isinstance(device_index, int)
            or device_index < 0
        ):
            raise ValueError("USB camera index must be a non-negative integer")
        self.device_index = device_index
        self._capture_factory = capture_factory
        self._clock = clock
        self._capture: object | None = None
        self._next_frame_id = 0
        self._status = CameraStatus.DISCONNECTED

    @property
    def status(self) -> CameraStatus:
        return self._status

    def _default_factory(self) -> Callable[[int], object]:
        try:
            cv2 = importlib.import_module("cv2")
        except ImportError as exc:
            raise CameraUnavailable(
                "OpenCV is unavailable; install requirements-camera-usb.txt"
            ) from exc
        factory = getattr(cv2, "VideoCapture", None)
        if not callable(factory):
            raise CameraUnavailable("OpenCV does not provide VideoCapture")
        return factory

    def open(self) -> None:
        self.close()
        factory = self._capture_factory or self._default_factory()
        try:
            capture = factory(self.device_index)
            is_opened = getattr(capture, "isOpened", None)
            if not callable(is_opened) or not bool(is_opened()):
                release = getattr(capture, "release", None)
                if callable(release):
                    release()
                raise CameraUnavailable(
                    f"USB camera index {self.device_index} could not be opened"
                )
        except CameraUnavailable:
            self._status = CameraStatus.FAILED
            raise
        except Exception as exc:
            self._status = CameraStatus.FAILED
            raise CameraUnavailable(
                f"USB camera index {self.device_index} failed during open: {exc}"
            ) from exc

        self._capture = capture
        self._next_frame_id = 0
        self._status = CameraStatus.READY

    def read_frame(self) -> FramePacket:
        if self._capture is None or self._status not in {
            CameraStatus.READY,
            CameraStatus.STREAMING,
        }:
            raise CameraUnavailable("USB camera must be opened before reading")
        read = getattr(self._capture, "read", None)
        if not callable(read):
            self._status = CameraStatus.FAILED
            raise CameraReadFailure("OpenCV capture object has no read method")
        try:
            received, payload = read()
        except Exception as exc:
            self._status = CameraStatus.FAILED
            raise CameraReadFailure(f"USB camera read failed: {exc}") from exc
        if not received or payload is None:
            self._status = CameraStatus.FAILED
            raise CameraReadFailure("USB camera returned no frame")
        _frame_dimensions(payload)

        packet = FramePacket(
            frame_id=self._next_frame_id,
            captured_at=self._clock(),
            payload=payload,
            source=f"usb:{self.device_index}",
        )
        self._next_frame_id += 1
        self._status = CameraStatus.STREAMING
        return packet

    def close(self) -> None:
        capture, self._capture = self._capture, None
        if capture is not None:
            release = getattr(capture, "release", None)
            if callable(release):
                try:
                    release()
                except Exception as exc:
                    self._status = CameraStatus.FAILED
                    raise CameraError(f"USB camera release failed: {exc}") from exc
        self._status = CameraStatus.DISCONNECTED


class PiCamera2Source:
    """CSI camera adapter using Raspberry Pi's lazily imported Picamera2 API."""

    def __init__(
        self,
        camera_number: int = 0,
        *,
        size: tuple[int, int] = (640, 480),
        camera_factory: Callable[[int], object] | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if (
            isinstance(camera_number, bool)
            or not isinstance(camera_number, int)
            or camera_number < 0
        ):
            raise ValueError("Pi camera number must be a non-negative integer")
        if (
            not isinstance(size, tuple)
            or len(size) != 2
            or any(isinstance(item, bool) or not isinstance(item, int) or item <= 0 for item in size)
        ):
            raise ValueError("Pi camera size must contain two positive integers")
        self.camera_number = camera_number
        self.size = size
        self._camera_factory = camera_factory
        self._clock = clock
        self._camera: object | None = None
        self._next_frame_id = 0
        self._status = CameraStatus.DISCONNECTED

    @property
    def status(self) -> CameraStatus:
        return self._status

    def _default_factory(self) -> Callable[[int], object]:
        try:
            module = importlib.import_module("picamera2")
        except ImportError as exc:
            raise CameraUnavailable(
                "Picamera2 is unavailable; install the Raspberry Pi OS camera package"
            ) from exc
        factory = getattr(module, "Picamera2", None)
        if not callable(factory):
            raise CameraUnavailable("picamera2 does not provide Picamera2")
        return factory

    def open(self) -> None:
        self.close()
        factory = self._camera_factory or self._default_factory()
        camera: object | None = None
        try:
            camera = factory(self.camera_number)
            create_configuration = getattr(
                camera, "create_preview_configuration", None
            )
            configure = getattr(camera, "configure", None)
            start = getattr(camera, "start", None)
            if not all(callable(item) for item in (create_configuration, configure, start)):
                raise CameraUnavailable("Picamera2 object lacks acquisition methods")
            configuration = create_configuration(
                main={"size": self.size, "format": "RGB888"}
            )
            configure(configuration)
            start()
        except CameraUnavailable:
            self._status = CameraStatus.FAILED
            self._close_failed_open(camera)
            raise
        except Exception as exc:
            self._status = CameraStatus.FAILED
            self._close_failed_open(camera)
            raise CameraUnavailable(f"Raspberry Pi camera could not be opened: {exc}") from exc

        self._camera = camera
        self._next_frame_id = 0
        self._status = CameraStatus.READY

    @staticmethod
    def _close_failed_open(camera: object | None) -> None:
        close = getattr(camera, "close", None)
        if callable(close):
            try:
                close()
            except Exception:
                pass

    def read_frame(self) -> FramePacket:
        if self._camera is None or self._status not in {
            CameraStatus.READY,
            CameraStatus.STREAMING,
        }:
            raise CameraUnavailable("Raspberry Pi camera must be opened before reading")
        capture_array = getattr(self._camera, "capture_array", None)
        if not callable(capture_array):
            self._status = CameraStatus.FAILED
            raise CameraReadFailure("Picamera2 object has no capture_array method")
        try:
            payload = capture_array("main")
        except Exception as exc:
            self._status = CameraStatus.FAILED
            raise CameraReadFailure(f"Raspberry Pi camera read failed: {exc}") from exc
        if payload is None:
            self._status = CameraStatus.FAILED
            raise CameraReadFailure("Raspberry Pi camera returned no frame")
        _frame_dimensions(payload)

        packet = FramePacket(
            frame_id=self._next_frame_id,
            captured_at=self._clock(),
            payload=payload,
            source=f"rpi:{self.camera_number}",
        )
        self._next_frame_id += 1
        self._status = CameraStatus.STREAMING
        return packet

    def close(self) -> None:
        camera, self._camera = self._camera, None
        if camera is not None:
            close = getattr(camera, "close", None)
            if callable(close):
                try:
                    close()
                except Exception as exc:
                    self._status = CameraStatus.FAILED
                    raise CameraError(f"Raspberry Pi camera close failed: {exc}") from exc
        self._status = CameraStatus.DISCONNECTED


class PreferredCamera:
    """Open candidate cameras in order and retain the first available source."""

    def __init__(self, candidates: Iterable[CameraSource]) -> None:
        self._candidates = tuple(candidates)
        if not self._candidates:
            raise ValueError("preferred camera needs at least one candidate")
        if not all(isinstance(item, CameraSource) for item in self._candidates):
            raise TypeError("all preferred-camera candidates must implement CameraSource")
        self._active: CameraSource | None = None
        self._status = CameraStatus.DISCONNECTED

    @property
    def status(self) -> CameraStatus:
        return self._active.status if self._active is not None else self._status

    @property
    def active(self) -> CameraSource | None:
        return self._active

    def open(self) -> None:
        self.close()
        failures: list[str] = []
        for candidate in self._candidates:
            try:
                candidate.open()
            except CameraUnavailable as exc:
                failures.append(f"{type(candidate).__name__}: {exc}")
                try:
                    candidate.close()
                except CameraError as close_error:
                    failures.append(
                        f"{type(candidate).__name__} close: {close_error}"
                    )
                continue
            self._active = candidate
            self._status = CameraStatus.READY
            return

        self._status = CameraStatus.FAILED
        raise CameraUnavailable("; ".join(failures))

    def read_frame(self) -> FramePacket:
        if self._active is None:
            raise CameraUnavailable("no preferred camera has been opened")
        try:
            return self._active.read_frame()
        except CameraError:
            self._status = CameraStatus.FAILED
            raise

    def close(self) -> None:
        first_error: CameraError | None = None
        for candidate in self._candidates:
            try:
                candidate.close()
            except CameraError as exc:
                if first_error is None:
                    first_error = exc
        self._active = None
        self._status = CameraStatus.DISCONNECTED
        if first_error is not None:
            raise first_error


def build_preferred_camera(usb_index: int = 0) -> PreferredCamera:
    """Build the requested USB-first, Raspberry-Pi-second camera chain."""

    return PreferredCamera(
        (
            OpenCvUsbCamera(device_index=usb_index),
            PiCamera2Source(camera_number=0),
        )
    )


def probe_camera(
    camera: CameraSource,
    *,
    frame_count: int = 3,
    clock: Callable[[], float] = time.monotonic,
) -> CameraProbeResult:
    """Capture a finite number of frames and retain metadata, never image data."""

    if not isinstance(camera, CameraSource):
        raise TypeError("probe_camera needs a CameraSource")
    if (
        isinstance(frame_count, bool)
        or not isinstance(frame_count, int)
        or not 1 <= frame_count <= 30
    ):
        raise ValueError("camera probe frame_count must be between 1 and 30")

    started_at = clock()
    packets: list[FramePacket] = []
    try:
        camera.open()
        for _ in range(frame_count):
            packets.append(camera.read_frame())
    finally:
        camera.close()
    elapsed = clock() - started_at
    if not _is_finite_number(elapsed) or elapsed < 0:
        raise CameraError("camera probe clock moved backwards or became invalid")

    source = packets[0].source
    width, height = _frame_dimensions(packets[0].payload)
    previous_id: int | None = None
    for packet in packets:
        packet_width, packet_height = _frame_dimensions(packet.payload)
        if packet.source != source:
            raise InvalidFrame("camera source changed during one diagnostic")
        if (packet_width, packet_height) != (width, height):
            raise InvalidFrame("camera resolution changed during one diagnostic")
        if previous_id is not None and packet.frame_id <= previous_id:
            raise InvalidFrame("camera probe received stale frame identifiers")
        previous_id = packet.frame_id

    return CameraProbeResult(
        source=source,
        frame_count=len(packets),
        width=width,
        height=height,
        elapsed_seconds=float(elapsed),
    )
