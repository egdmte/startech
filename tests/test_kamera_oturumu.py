"""Recording, integrity and deterministic replay tests for camera sessions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from arac.goz import (
    CameraExhausted,
    CameraReadFailure,
    CameraStatus,
    FramePacket,
    InvalidFrame,
)
from arac.kamera_oturumu import (
    INCOMPLETE_NAME,
    MANIFEST_NAME,
    InvalidSession,
    RecordedCameraSource,
    SessionAlreadyExists,
    SessionIntegrityError,
    inspect_recorded_session,
    record_camera_session,
)


@dataclass(frozen=True)
class FakeImage:
    shape: tuple[int, int, int]
    value: int


class JsonImageCodec:
    def encode(self, payload, source):
        return json.dumps(
            {"shape": list(payload.shape), "value": payload.value, "source": source},
            sort_keys=True,
        ).encode("utf-8")

    def decode(self, encoded):
        value = json.loads(encoded.decode("utf-8"))
        return FakeImage(tuple(value["shape"]), value["value"])


class StubCamera:
    def __init__(self, frames, *, read_error_at=None, close_error=None):
        self.frames = tuple(frames)
        self.read_error_at = read_error_at
        self.close_error = close_error
        self.cursor = 0
        self.opened = False
        self.closed = False
        self._status = CameraStatus.DISCONNECTED

    @property
    def status(self):
        return self._status

    def open(self):
        self.cursor = 0
        self.opened = True
        self.closed = False
        self._status = CameraStatus.READY

    def read_frame(self):
        if self.read_error_at == self.cursor:
            self._status = CameraStatus.FAILED
            raise CameraReadFailure("deliberate capture failure")
        if self.cursor >= len(self.frames):
            self._status = CameraStatus.EXHAUSTED
            raise CameraExhausted("stub exhausted")
        packet = self.frames[self.cursor]
        self.cursor += 1
        self._status = CameraStatus.STREAMING
        return packet

    def close(self):
        self.closed = True
        self._status = CameraStatus.DISCONNECTED
        if self.close_error is not None:
            raise self.close_error


def packets(*, source="usb:0", ids=(0, 1, 2), times=(10.0, 10.1, 10.2)):
    return tuple(
        FramePacket(
            frame_id=frame_id,
            captured_at=captured_at,
            payload=FakeImage((480, 640, 3), index),
            source=source,
        )
        for index, (frame_id, captured_at) in enumerate(zip(ids, times))
    )


class CameraSessionTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.codec = JsonImageCodec()

    def tearDown(self):
        self.temp.cleanup()

    def record(self, name="session", frames=None, **kwargs):
        camera = StubCamera(packets() if frames is None else frames, **kwargs)
        path = self.root / name
        manifest = record_camera_session(
            camera,
            path,
            frame_count=len(camera.frames),
            codec=self.codec,
            session_id_factory=lambda: "session-fixed",
            utc_now=lambda: datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc),
        )
        return path, camera, manifest

    def test_record_and_replay_round_trip_is_repeatable(self):
        path, camera, manifest = self.record()

        self.assertTrue(camera.opened)
        self.assertTrue(camera.closed)
        self.assertTrue((path / MANIFEST_NAME).is_file())
        self.assertFalse((path / INCOMPLETE_NAME).exists())
        self.assertEqual("session-fixed", manifest.session_id)
        self.assertEqual("usb:0", manifest.source)
        self.assertEqual((640, 480), (manifest.width, manifest.height))
        self.assertEqual(3, manifest.frame_count)
        self.assertAlmostEqual(0.2, manifest.elapsed_seconds)
        self.assertAlmostEqual(10.0, manifest.observed_fps)

        replay = RecordedCameraSource(path, codec=self.codec)
        rounds = []
        for _ in range(2):
            replay.open()
            current = [replay.read_frame() for _ in range(3)]
            with self.assertRaises(CameraExhausted):
                replay.read_frame()
            replay.close()
            rounds.append(
                tuple(
                    (item.frame_id, item.captured_at, item.source, item.payload.value)
                    for item in current
                )
            )

        self.assertEqual(rounds[0], rounds[1])
        for actual, expected in zip(
            (item[1] for item in rounds[0]), (0.0, 0.1, 0.2)
        ):
            self.assertAlmostEqual(expected, actual)
        self.assertTrue(all(item[2] == "recording:usb:0" for item in rounds[0]))

    def test_progress_reports_every_captured_and_replayed_frame(self):
        captured = []
        camera = StubCamera(packets())
        path = self.root / "progress"
        manifest = record_camera_session(
            camera,
            path,
            frame_count=3,
            codec=self.codec,
            progress=lambda current, total, packet: captured.append(
                (current, total, packet.frame_id)
            ),
        )
        replayed = []

        summary = inspect_recorded_session(
            path,
            codec=self.codec,
            progress=lambda current, total, packet: replayed.append(
                (current, total, packet.frame_id)
            ),
        )

        self.assertEqual([(1, 3, 0), (2, 3, 1), (3, 3, 2)], captured)
        self.assertEqual(captured, replayed)
        self.assertEqual(manifest.session_id, summary.session_id)
        self.assertEqual(3, summary.frame_count)

    def test_existing_output_is_never_overwritten(self):
        path = self.root / "existing"
        path.mkdir()
        sentinel = path / "mine.txt"
        sentinel.write_text("keep", encoding="utf-8")

        with self.assertRaisesRegex(SessionAlreadyExists, "already exists"):
            record_camera_session(
                StubCamera(packets()),
                path,
                frame_count=3,
                codec=self.codec,
            )

        self.assertEqual("keep", sentinel.read_text(encoding="utf-8"))

    def test_interrupted_capture_has_marker_but_no_completed_manifest(self):
        camera = StubCamera(packets(), read_error_at=1)
        path = self.root / "incomplete"

        with self.assertRaisesRegex(CameraReadFailure, "deliberate"):
            record_camera_session(
                camera,
                path,
                frame_count=3,
                codec=self.codec,
            )

        self.assertTrue(camera.closed)
        self.assertFalse((path / MANIFEST_NAME).exists())
        marker = json.loads((path / INCOMPLETE_NAME).read_text(encoding="utf-8"))
        self.assertFalse(marker["complete"])
        self.assertEqual(1, marker["captured_frames"])
        with self.assertRaisesRegex(InvalidSession, "manifest is missing"):
            RecordedCameraSource(path, codec=self.codec).open()

    def test_keyboard_interrupt_closes_camera_and_leaves_incomplete_evidence(self):
        class InterruptedCamera(StubCamera):
            def read_frame(inner_self):
                if inner_self.cursor == 1:
                    raise KeyboardInterrupt
                return super().read_frame()

        camera = InterruptedCamera(packets())
        path = self.root / "keyboard-interrupt"

        with self.assertRaises(KeyboardInterrupt):
            record_camera_session(
                camera,
                path,
                frame_count=3,
                codec=self.codec,
            )

        self.assertTrue(camera.closed)
        self.assertFalse((path / MANIFEST_NAME).exists())
        marker = json.loads((path / INCOMPLETE_NAME).read_text(encoding="utf-8"))
        self.assertEqual("KeyboardInterrupt", marker["error_type"])
        self.assertEqual(1, marker["captured_frames"])

    def test_changed_source_resolution_id_and_timestamp_are_rejected(self):
        normal = list(packets())
        cases = {
            "source": normal[:1]
            + [
                FramePacket(1, 10.1, FakeImage((480, 640, 3), 1), source="rpi:0")
            ],
            "resolution": normal[:1]
            + [FramePacket(1, 10.1, FakeImage((720, 1280, 3), 1), source="usb:0")],
            "identifier": normal[:1]
            + [FramePacket(0, 10.1, FakeImage((480, 640, 3), 1), source="usb:0")],
            "timestamp": normal[:1]
            + [FramePacket(1, 9.9, FakeImage((480, 640, 3), 1), source="usb:0")],
        }

        for name, frames in cases.items():
            with self.subTest(name=name):
                path = self.root / name
                with self.assertRaises(InvalidFrame):
                    record_camera_session(
                        StubCamera(frames),
                        path,
                        frame_count=2,
                        codec=self.codec,
                    )
                self.assertFalse((path / MANIFEST_NAME).exists())

    def test_timing_and_identifier_anomalies_become_visible_warnings(self):
        frames = packets(
            ids=(2, 4, 5, 6, 7),
            times=(1.0, 1.0, 1.1, 1.2, 2.0),
        )
        _path, _camera, manifest = self.record(frames=frames)

        combined = " | ".join(manifest.warnings)
        self.assertIn("frame-id gap", combined)
        self.assertIn("equal timestamp", combined)
        self.assertIn("long frame interval", combined)

    def test_missing_or_modified_frame_is_rejected(self):
        missing_path, _camera, _manifest = self.record(name="missing")
        (missing_path / "frames" / "000001.jpg").unlink()
        missing = RecordedCameraSource(missing_path, codec=self.codec)
        missing.open()
        missing.read_frame()
        with self.assertRaisesRegex(SessionIntegrityError, "missing or unreadable"):
            missing.read_frame()

        changed_path, _camera, _manifest = self.record(name="changed")
        (changed_path / "frames" / "000000.jpg").write_bytes(b"changed")
        changed = RecordedCameraSource(changed_path, codec=self.codec)
        changed.open()
        with self.assertRaisesRegex(SessionIntegrityError, "checksum mismatch"):
            changed.read_frame()

    def test_decoded_resolution_mismatch_is_rejected_after_valid_hash(self):
        path, _camera, _manifest = self.record(name="dimension")
        frame_path = path / "frames" / "000000.jpg"
        replacement = self.codec.encode(FakeImage((10, 20, 3), 7), "usb:0")
        frame_path.write_bytes(replacement)
        manifest_path = path / MANIFEST_NAME
        value = json.loads(manifest_path.read_text(encoding="utf-8"))
        value["frames"][0]["sha256"] = hashlib.sha256(replacement).hexdigest()
        manifest_path.write_text(json.dumps(value), encoding="utf-8")

        replay = RecordedCameraSource(path, codec=self.codec)
        replay.open()
        with self.assertRaisesRegex(SessionIntegrityError, "resolution mismatch"):
            replay.read_frame()

    def test_manifest_rejects_unknown_fields_count_mismatch_and_path_escape(self):
        for name in ("unknown", "count", "escape"):
            with self.subTest(name=name):
                path, _camera, _manifest = self.record(name=name)
                manifest_path = path / MANIFEST_NAME
                value = json.loads(manifest_path.read_text(encoding="utf-8"))
                if name == "unknown":
                    value["surprise"] = True
                elif name == "count":
                    value["frame_count"] = 99
                else:
                    value["frames"][0]["path"] = "../outside.jpg"
                manifest_path.write_text(json.dumps(value), encoding="utf-8")

                with self.assertRaises(InvalidSession):
                    RecordedCameraSource(path, codec=self.codec).open()

    def test_manifest_rejects_duplicate_json_fields(self):
        path, _camera, _manifest = self.record(name="duplicate")
        manifest_path = path / MANIFEST_NAME
        raw = manifest_path.read_text(encoding="utf-8")
        raw = raw.replace('"schema_version": 1,', '"schema_version": 1,\n  "schema_version": 1,', 1)
        manifest_path.write_text(raw, encoding="utf-8")

        with self.assertRaisesRegex(InvalidSession, "duplicate JSON field"):
            RecordedCameraSource(path, codec=self.codec).open()

    def test_invalid_frame_count_is_rejected_before_creating_a_directory(self):
        for value in (0, 30_001, True):
            with self.subTest(value=value):
                path = self.root / f"invalid-{value}"
                with self.assertRaises(ValueError):
                    record_camera_session(
                        StubCamera(packets()),
                        path,
                        frame_count=value,
                        codec=self.codec,
                    )
                self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
