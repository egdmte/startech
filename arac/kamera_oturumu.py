"""Finite KASIM camera-session recording and deterministic offline replay.

A completed session is a directory containing numbered JPEG frames and one strict
``manifest.json``.  The manifest is written last, so a directory left behind by an
interrupted capture cannot be mistaken for a valid session.  This module never sends
motor commands and does not claim that recorded images prove physical vehicle motion.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import re
import statistics
from typing import Any, Protocol
import uuid

from .goz import (
    CameraError,
    CameraExhausted,
    CameraSource,
    CameraStatus,
    FramePacket,
    InvalidFrame,
    _frame_dimensions,
)


SCHEMA_VERSION = 1
MANIFEST_NAME = "manifest.json"
INCOMPLETE_NAME = "incomplete.json"
FRAME_DIRECTORY = "frames"
PIXEL_FORMAT = "BGR8"
IMAGE_FORMAT = "jpeg"
MAX_SESSION_FRAMES = 30_000
_FRAME_PATH = re.compile(r"^frames/[0-9]{6}\.jpg$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class CameraSessionError(CameraError):
    """Base error for recording or replaying a camera evidence session."""


class SessionAlreadyExists(CameraSessionError, FileExistsError):
    """Raised when capture would overwrite an existing path."""


class InvalidSession(CameraSessionError, ValueError):
    """Raised when a manifest violates the versioned session contract."""


class SessionIntegrityError(CameraSessionError):
    """Raised when a stored frame is missing, changed or undecodable."""


class FrameCodecError(CameraSessionError):
    """Raised when image encoding or decoding is unavailable or fails."""


class FrameCodec(Protocol):
    """Encode/decode boundary kept injectable for deterministic unit tests."""

    def encode(self, payload: object, source: str) -> bytes:
        """Return one JPEG-compatible byte payload."""

    def decode(self, encoded: bytes) -> object:
        """Return one array-like BGR frame payload."""


class OpenCvJpegCodec:
    """JPEG codec for BGR arrays from the current OpenCV and Picamera2 adapters.

    Picamera2's ``RGB888`` stream name maps to BGR byte order in its array/JPEG
    helpers.  KASIM deliberately requests that format so both live adapters arrive
    here in the OpenCV-compatible BGR order recorded by the manifest.
    """

    def __init__(self, *, quality: int = 95) -> None:
        if isinstance(quality, bool) or not isinstance(quality, int):
            raise ValueError("JPEG quality must be an integer")
        if not 1 <= quality <= 100:
            raise ValueError("JPEG quality must be between 1 and 100")
        self.quality = quality

    @staticmethod
    def _cv2() -> object:
        try:
            return importlib.import_module("cv2")
        except ImportError as exc:
            raise FrameCodecError(
                "OpenCV is unavailable; install requirements-camera-usb.txt"
            ) from exc

    def encode(self, payload: object, source: str) -> bytes:
        _frame_dimensions(payload)
        cv2 = self._cv2()
        encode = getattr(cv2, "imencode", None)
        quality_key = getattr(cv2, "IMWRITE_JPEG_QUALITY", None)
        if not callable(encode) or quality_key is None:
            raise FrameCodecError("OpenCV does not provide JPEG encoding")
        try:
            accepted, encoded = encode(
                ".jpg", payload, [int(quality_key), self.quality]
            )
        except Exception as exc:
            raise FrameCodecError(f"JPEG encoding failed: {exc}") from exc
        if not accepted or encoded is None:
            raise FrameCodecError("OpenCV refused to encode the camera frame")
        try:
            result = encoded.tobytes()
        except (AttributeError, TypeError, ValueError) as exc:
            raise FrameCodecError("OpenCV returned unusable encoded frame data") from exc
        if not result:
            raise FrameCodecError("OpenCV returned an empty JPEG")
        return result

    def decode(self, encoded: bytes) -> object:
        if not isinstance(encoded, bytes) or not encoded:
            raise FrameCodecError("encoded frame must contain bytes")
        cv2 = self._cv2()
        try:
            numpy = importlib.import_module("numpy")
        except ImportError as exc:
            raise FrameCodecError("NumPy is unavailable for JPEG replay") from exc
        decode = getattr(cv2, "imdecode", None)
        unchanged = getattr(cv2, "IMREAD_COLOR", None)
        from_buffer = getattr(numpy, "frombuffer", None)
        uint8 = getattr(numpy, "uint8", None)
        if not callable(decode) or unchanged is None or not callable(from_buffer):
            raise FrameCodecError("OpenCV/NumPy does not provide JPEG decoding")
        try:
            payload = decode(from_buffer(encoded, dtype=uint8), unchanged)
        except Exception as exc:
            raise FrameCodecError(f"JPEG decoding failed: {exc}") from exc
        if payload is None:
            raise FrameCodecError("stored JPEG could not be decoded")
        _frame_dimensions(payload)
        return payload


def _is_number(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _positive_integer(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise InvalidSession(f"{name} must be a positive integer")
    return value


def _non_negative_number(value: object, name: str) -> float:
    if not _is_number(value) or float(value) < 0:
        raise InvalidSession(f"{name} must be a finite non-negative number")
    return float(value)


def _strict_object(value: object, expected: set[str], name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise InvalidSession(f"{name} must be a JSON object")
    keys = set(value)
    missing = expected - keys
    unknown = keys - expected
    if missing:
        raise InvalidSession(f"{name} is missing fields: {', '.join(sorted(missing))}")
    if unknown:
        raise InvalidSession(f"{name} has unknown fields: {', '.join(sorted(unknown))}")
    return value


def _non_empty_text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InvalidSession(f"{name} must be non-empty text")
    return value.strip()


@dataclass(frozen=True)
class RecordedFrame:
    """One immutable frame entry from a recording manifest."""

    frame_id: int
    offset_seconds: float
    path: str
    sha256: str

    def __post_init__(self) -> None:
        if isinstance(self.frame_id, bool) or not isinstance(self.frame_id, int):
            raise InvalidSession("frame_id must be an integer")
        if self.frame_id < 0:
            raise InvalidSession("frame_id cannot be negative")
        _non_negative_number(self.offset_seconds, "offset_seconds")
        if not isinstance(self.path, str) or not _FRAME_PATH.fullmatch(self.path):
            raise InvalidSession("frame path must match frames/000000.jpg")
        if not isinstance(self.sha256, str) or not _SHA256.fullmatch(self.sha256):
            raise InvalidSession("frame sha256 must be 64 lowercase hexadecimal characters")

    def to_dict(self) -> dict[str, object]:
        return {
            "frame_id": self.frame_id,
            "offset_seconds": self.offset_seconds,
            "path": self.path,
            "sha256": self.sha256,
        }

    @classmethod
    def from_dict(cls, value: object) -> "RecordedFrame":
        item = _strict_object(
            value,
            {"frame_id", "offset_seconds", "path", "sha256"},
            "frame entry",
        )
        return cls(
            frame_id=item["frame_id"],
            offset_seconds=_non_negative_number(
                item["offset_seconds"], "offset_seconds"
            ),
            path=item["path"],
            sha256=item["sha256"],
        )


@dataclass(frozen=True)
class SessionManifest:
    """Validated metadata required to replay a finite camera session."""

    session_id: str
    created_at_utc: str
    source: str
    width: int
    height: int
    elapsed_seconds: float
    observed_fps: float
    warnings: tuple[str, ...]
    frames: tuple[RecordedFrame, ...]
    schema_version: int = SCHEMA_VERSION
    pixel_format: str = PIXEL_FORMAT
    image_format: str = IMAGE_FORMAT

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise InvalidSession(
                f"unsupported camera-session schema version: {self.schema_version}"
            )
        _non_empty_text(self.session_id, "session_id")
        _non_empty_text(self.created_at_utc, "created_at_utc")
        _non_empty_text(self.source, "source")
        _positive_integer(self.width, "width")
        _positive_integer(self.height, "height")
        _non_negative_number(self.elapsed_seconds, "elapsed_seconds")
        _non_negative_number(self.observed_fps, "observed_fps")
        if self.pixel_format != PIXEL_FORMAT:
            raise InvalidSession(f"pixel_format must be {PIXEL_FORMAT}")
        if self.image_format != IMAGE_FORMAT:
            raise InvalidSession(f"image_format must be {IMAGE_FORMAT}")
        if not isinstance(self.warnings, tuple) or not all(
            isinstance(item, str) and item.strip() for item in self.warnings
        ):
            raise InvalidSession("warnings must contain only non-empty text")
        if not isinstance(self.frames, tuple) or not self.frames:
            raise InvalidSession("a completed session must contain at least one frame")

        previous_id: int | None = None
        previous_offset: float | None = None
        for index, frame in enumerate(self.frames):
            if not isinstance(frame, RecordedFrame):
                raise InvalidSession("frames must contain RecordedFrame values")
            expected_path = f"{FRAME_DIRECTORY}/{index:06d}.jpg"
            if frame.path != expected_path:
                raise InvalidSession("frame paths must be contiguous and ordered")
            if previous_id is not None and frame.frame_id <= previous_id:
                raise InvalidSession("recorded frame identifiers must increase")
            if previous_offset is not None and frame.offset_seconds < previous_offset:
                raise InvalidSession("recorded frame timestamps cannot move backwards")
            previous_id = frame.frame_id
            previous_offset = frame.offset_seconds

        if self.frames[0].offset_seconds != 0.0:
            raise InvalidSession("the first frame offset must be zero")
        if not math.isclose(
            self.elapsed_seconds,
            self.frames[-1].offset_seconds,
            rel_tol=1e-9,
            abs_tol=1e-9,
        ):
            raise InvalidSession("elapsed_seconds must match the final frame offset")

    @property
    def frame_count(self) -> int:
        return len(self.frames)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "session_id": self.session_id,
            "created_at_utc": self.created_at_utc,
            "source": self.source,
            "width": self.width,
            "height": self.height,
            "frame_count": self.frame_count,
            "elapsed_seconds": self.elapsed_seconds,
            "observed_fps": self.observed_fps,
            "pixel_format": self.pixel_format,
            "image_format": self.image_format,
            "warnings": list(self.warnings),
            "frames": [frame.to_dict() for frame in self.frames],
        }

    @classmethod
    def from_dict(cls, value: object) -> "SessionManifest":
        item = _strict_object(
            value,
            {
                "schema_version",
                "session_id",
                "created_at_utc",
                "source",
                "width",
                "height",
                "frame_count",
                "elapsed_seconds",
                "observed_fps",
                "pixel_format",
                "image_format",
                "warnings",
                "frames",
            },
            "session manifest",
        )
        schema_version = item["schema_version"]
        if isinstance(schema_version, bool) or not isinstance(schema_version, int):
            raise InvalidSession("schema_version must be an integer")
        frame_count = _positive_integer(item["frame_count"], "frame_count")
        raw_frames = item["frames"]
        if not isinstance(raw_frames, list):
            raise InvalidSession("frames must be a JSON array")
        frames = tuple(RecordedFrame.from_dict(frame) for frame in raw_frames)
        if frame_count != len(frames):
            raise InvalidSession("frame_count does not match the frames array")
        raw_warnings = item["warnings"]
        if not isinstance(raw_warnings, list):
            raise InvalidSession("warnings must be a JSON array")
        warnings = tuple(raw_warnings)
        return cls(
            schema_version=schema_version,
            session_id=_non_empty_text(item["session_id"], "session_id"),
            created_at_utc=_non_empty_text(
                item["created_at_utc"], "created_at_utc"
            ),
            source=_non_empty_text(item["source"], "source"),
            width=_positive_integer(item["width"], "width"),
            height=_positive_integer(item["height"], "height"),
            elapsed_seconds=_non_negative_number(
                item["elapsed_seconds"], "elapsed_seconds"
            ),
            observed_fps=_non_negative_number(item["observed_fps"], "observed_fps"),
            pixel_format=item["pixel_format"],
            image_format=item["image_format"],
            warnings=warnings,
            frames=frames,
        )


@dataclass(frozen=True)
class ReplaySummary:
    """Result of decoding and validating every frame in one session."""

    session_id: str
    source: str
    frame_count: int
    width: int
    height: int
    elapsed_seconds: float
    observed_fps: float
    warnings: tuple[str, ...]


ProgressCallback = Callable[[int, int, FramePacket], None]


def _json_pairs_without_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise InvalidSession(f"duplicate JSON field: {key}")
        result[key] = value
    return result


def _atomic_write(path: Path, payload: bytes) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        temporary.write_bytes(payload)
        os.replace(temporary, path)
    except OSError as exc:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise CameraSessionError(f"could not persist {path.name}: {exc}") from exc


def _json_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _load_manifest(root: Path) -> SessionManifest:
    manifest_path = root / MANIFEST_NAME
    if not manifest_path.is_file():
        raise InvalidSession(f"completed manifest is missing: {manifest_path}")
    try:
        raw = manifest_path.read_text(encoding="utf-8")
        value = json.loads(raw, object_pairs_hook=_json_pairs_without_duplicates)
    except InvalidSession:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise InvalidSession(f"could not read session manifest: {exc}") from exc
    return SessionManifest.from_dict(value)


def _session_warnings(packets: list[FramePacket]) -> tuple[str, ...]:
    warnings: list[str] = []
    intervals: list[float] = []
    for previous, current in zip(packets, packets[1:]):
        if current.frame_id > previous.frame_id + 1:
            warnings.append(
                f"frame-id gap: {previous.frame_id}->{current.frame_id}"
            )
        interval = current.captured_at - previous.captured_at
        intervals.append(interval)
        if interval == 0:
            warnings.append(f"equal timestamp at frame {current.frame_id}")

    positive_intervals = [interval for interval in intervals if interval > 0]
    if len(positive_intervals) >= 3:
        median = statistics.median(positive_intervals)
        for index, interval in enumerate(intervals, start=1):
            if interval > max(median * 3.0, median + 0.100):
                warnings.append(
                    f"long frame interval before frame {packets[index].frame_id}: "
                    f"{interval:.6f}s"
                )
    return tuple(warnings)


def _write_incomplete_marker(root: Path, captured_frames: int, error: BaseException) -> None:
    marker = {
        "schema_version": SCHEMA_VERSION,
        "complete": False,
        "captured_frames": captured_frames,
        "error_type": type(error).__name__,
        "error": str(error),
    }
    try:
        _atomic_write(root / INCOMPLETE_NAME, _json_bytes(marker))
    except CameraSessionError:
        # The original capture failure remains the useful error to report.
        pass


def record_camera_session(
    camera: CameraSource,
    output_directory: str | Path,
    *,
    frame_count: int,
    codec: FrameCodec | None = None,
    progress: ProgressCallback | None = None,
    session_id_factory: Callable[[], str] = lambda: uuid.uuid4().hex,
    utc_now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
) -> SessionManifest:
    """Record a finite camera session without overwriting any existing path."""

    if not isinstance(camera, CameraSource):
        raise TypeError("camera session recorder needs a CameraSource")
    if (
        isinstance(frame_count, bool)
        or not isinstance(frame_count, int)
        or not 1 <= frame_count <= MAX_SESSION_FRAMES
    ):
        raise ValueError(
            f"record frame count must be between 1 and {MAX_SESSION_FRAMES}"
        )
    if progress is not None and not callable(progress):
        raise TypeError("progress must be callable")
    root = Path(output_directory)
    try:
        root.mkdir(parents=True, exist_ok=False)
    except FileExistsError as exc:
        raise SessionAlreadyExists(f"session path already exists: {root}") from exc
    except OSError as exc:
        raise CameraSessionError(f"could not create session directory: {exc}") from exc

    frames_directory = root / FRAME_DIRECTORY
    try:
        frames_directory.mkdir()
    except OSError as exc:
        error = CameraSessionError(f"could not create frames directory: {exc}")
        _write_incomplete_marker(root, 0, error)
        raise error from exc

    selected_codec = codec or OpenCvJpegCodec()
    packets: list[FramePacket] = []
    records: list[RecordedFrame] = []
    expected_source: str | None = None
    expected_dimensions: tuple[int, int] | None = None
    first_timestamp: float | None = None
    previous_id: int | None = None
    previous_timestamp: float | None = None
    failure: BaseException | None = None

    try:
        camera.open()
        for index in range(frame_count):
            packet = camera.read_frame()
            width, height = _frame_dimensions(packet.payload)
            if expected_source is None:
                expected_source = packet.source
                expected_dimensions = (width, height)
                first_timestamp = packet.captured_at
            elif packet.source != expected_source:
                raise InvalidFrame("camera source changed during one recording")
            elif (width, height) != expected_dimensions:
                raise InvalidFrame("camera resolution changed during one recording")
            if previous_id is not None and packet.frame_id <= previous_id:
                raise InvalidFrame("camera recording received a stale frame identifier")
            if previous_timestamp is not None and packet.captured_at < previous_timestamp:
                raise InvalidFrame("camera recording timestamp moved backwards")

            encoded = selected_codec.encode(packet.payload, packet.source)
            if not isinstance(encoded, bytes) or not encoded:
                raise FrameCodecError("frame codec returned empty or non-byte data")
            relative_path = f"{FRAME_DIRECTORY}/{index:06d}.jpg"
            _atomic_write(root / Path(relative_path), encoded)
            offset = float(packet.captured_at - first_timestamp)
            records.append(
                RecordedFrame(
                    frame_id=packet.frame_id,
                    offset_seconds=offset,
                    path=relative_path,
                    sha256=hashlib.sha256(encoded).hexdigest(),
                )
            )
            packets.append(packet)
            previous_id = packet.frame_id
            previous_timestamp = packet.captured_at
            if progress is not None:
                progress(index + 1, frame_count, packet)
    except BaseException as exc:
        failure = exc
    finally:
        try:
            camera.close()
        except BaseException as exc:
            if failure is None:
                failure = exc

    if failure is not None:
        _write_incomplete_marker(root, len(records), failure)
        raise failure

    if expected_source is None or expected_dimensions is None:
        error = CameraSessionError("camera recording completed without frames")
        _write_incomplete_marker(root, len(records), error)
        raise error

    elapsed = records[-1].offset_seconds
    observed_fps = (len(records) - 1) / elapsed if elapsed > 0 else 0.0
    manifest = SessionManifest(
        session_id=_non_empty_text(session_id_factory(), "session_id"),
        created_at_utc=utc_now().astimezone(timezone.utc).isoformat(),
        source=expected_source,
        width=expected_dimensions[0],
        height=expected_dimensions[1],
        elapsed_seconds=elapsed,
        observed_fps=observed_fps,
        warnings=_session_warnings(packets),
        frames=tuple(records),
    )
    _atomic_write(root / MANIFEST_NAME, _json_bytes(manifest.to_dict()))
    return manifest


class RecordedCameraSource:
    """Strict finite CameraSource backed by a completed session directory."""

    def __init__(
        self,
        session_directory: str | Path,
        *,
        codec: FrameCodec | None = None,
    ) -> None:
        self.session_directory = Path(session_directory)
        self._codec = codec or OpenCvJpegCodec()
        self._manifest: SessionManifest | None = None
        self._cursor = 0
        self._status = CameraStatus.DISCONNECTED

    @property
    def status(self) -> CameraStatus:
        return self._status

    @property
    def manifest(self) -> SessionManifest:
        if self._manifest is None:
            raise CameraSessionError("recorded session has not been opened")
        return self._manifest

    def open(self) -> None:
        self.close()
        try:
            manifest = _load_manifest(self.session_directory)
        except CameraSessionError:
            self._status = CameraStatus.FAILED
            raise
        self._manifest = manifest
        self._cursor = 0
        self._status = CameraStatus.READY

    def read_frame(self) -> FramePacket:
        if self._manifest is None or self._status not in {
            CameraStatus.READY,
            CameraStatus.STREAMING,
        }:
            raise CameraSessionError("recorded session must be opened before replay")
        if self._cursor >= self._manifest.frame_count:
            self._status = CameraStatus.EXHAUSTED
            raise CameraExhausted("recorded camera session has no frame left")

        record = self._manifest.frames[self._cursor]
        frame_path = self.session_directory / Path(record.path)
        try:
            encoded = frame_path.read_bytes()
        except OSError as exc:
            self._status = CameraStatus.FAILED
            raise SessionIntegrityError(
                f"recorded frame is missing or unreadable: {record.path}"
            ) from exc
        if hashlib.sha256(encoded).hexdigest() != record.sha256:
            self._status = CameraStatus.FAILED
            raise SessionIntegrityError(
                f"recorded frame checksum mismatch: {record.path}"
            )
        try:
            payload = self._codec.decode(encoded)
            dimensions = _frame_dimensions(payload)
        except CameraError:
            self._status = CameraStatus.FAILED
            raise
        if dimensions != (self._manifest.width, self._manifest.height):
            self._status = CameraStatus.FAILED
            raise SessionIntegrityError(
                f"recorded frame resolution mismatch: {record.path}"
            )

        self._cursor += 1
        self._status = CameraStatus.STREAMING
        return FramePacket(
            frame_id=record.frame_id,
            captured_at=record.offset_seconds,
            payload=payload,
            source=f"recording:{self._manifest.source}",
        )

    def close(self) -> None:
        self._manifest = None
        self._cursor = 0
        self._status = CameraStatus.DISCONNECTED


def inspect_recorded_session(
    session_directory: str | Path,
    *,
    codec: FrameCodec | None = None,
    progress: ProgressCallback | None = None,
) -> ReplaySummary:
    """Decode every recorded frame and return validated, payload-free metadata."""

    camera = RecordedCameraSource(session_directory, codec=codec)
    camera.open()
    try:
        manifest = camera.manifest
        for index in range(manifest.frame_count):
            packet = camera.read_frame()
            if progress is not None:
                progress(index + 1, manifest.frame_count, packet)
        return ReplaySummary(
            session_id=manifest.session_id,
            source=manifest.source,
            frame_count=manifest.frame_count,
            width=manifest.width,
            height=manifest.height,
            elapsed_seconds=manifest.elapsed_seconds,
            observed_fps=manifest.observed_fps,
            warnings=manifest.warnings,
        )
    finally:
        camera.close()
