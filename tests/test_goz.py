"""Contract tests for KASIM's live USB/Pi RGB camera boundary."""

from __future__ import annotations

import unittest

import numpy as np

from arac.goz import (
    CameraExhausted,
    CameraReadFailure,
    CameraStatus,
    CameraUnavailable,
    FramePacket,
    InvalidFrame,
    OpenCvUsbCamera,
    PiCamera2Source,
    PreferredCamera,
    SequenceCamera,
    UnavailableCamera,
    build_preferred_camera,
    probe_camera,
)


class ArrayFrame:
    def __init__(self, width=640, height=480):
        self.shape = (height, width, 3)


class FakeCapture:
    def __init__(self, *, opened=True, frames=None):
        self.opened = opened
        self.frames = list(frames or [])
        self.released = False
        self.properties = {}

    def isOpened(self):
        return self.opened

    def read(self):
        if not self.frames:
            return False, None
        return True, self.frames.pop(0)

    def set(self, key, value):
        self.properties[key] = value
        return True

    def release(self):
        self.released = True


class FakePiCamera:
    def __init__(self, frames=None):
        self.frames = list(frames or [])
        self.configuration = None
        self.started = False
        self.closed = False

    def create_preview_configuration(self, **configuration):
        self.configuration = configuration
        return configuration

    def configure(self, configuration):
        self.configuration = configuration

    def start(self):
        self.started = True

    def capture_array(self, stream):
        if stream != "main" or not self.frames:
            raise RuntimeError("no Pi frame")
        return self.frames.pop(0)

    def close(self):
        self.closed = True


class StubCamera:
    def __init__(self, source, *, open_error=None, read_error=None):
        self.source = source
        self.open_error = open_error
        self.read_error = read_error
        self.open_count = 0
        self.close_count = 0
        self.frame_id = 0
        self._status = CameraStatus.DISCONNECTED

    @property
    def status(self):
        return self._status

    def open(self):
        self.open_count += 1
        if self.open_error is not None:
            self._status = CameraStatus.FAILED
            raise self.open_error
        self._status = CameraStatus.READY

    def read_frame(self):
        if self.read_error is not None:
            self._status = CameraStatus.FAILED
            raise self.read_error
        packet = FramePacket(
            self.frame_id,
            float(self.frame_id),
            ArrayFrame(),
            source=self.source,
        )
        self.frame_id += 1
        self._status = CameraStatus.STREAMING
        return packet

    def close(self):
        self.close_count += 1
        self._status = CameraStatus.DISCONNECTED


class FramePacketTest(unittest.TestCase):
    def test_valid_packet_preserves_metadata(self):
        frame = FramePacket(4, 1.25, {"pixels": "fake"}, source="unit-test")

        self.assertEqual(4, frame.frame_id)
        self.assertEqual(1.25, frame.captured_at)
        self.assertEqual("unit-test", frame.source)

    def test_malformed_packet_is_rejected(self):
        invalid_arguments = (
            (True, 0.0, {}),
            (-1, 0.0, {}),
            (0, float("nan"), {}),
            (0, -0.1, {}),
            (0, 0.0, None),
        )

        for frame_id, captured_at, payload in invalid_arguments:
            with self.subTest(values=(frame_id, captured_at, payload)):
                with self.assertRaises(InvalidFrame):
                    FramePacket(frame_id, captured_at, payload)

        with self.assertRaises(InvalidFrame):
            FramePacket(0, 0.0, {}, source=" ")


class SequenceCameraTest(unittest.TestCase):
    def make_camera(self):
        return SequenceCamera(
            (
                FramePacket(10, 1.0, {"value": "first"}),
                FramePacket(11, 2.0, {"value": "second"}),
            )
        )

    def test_lifecycle_and_exhaustion_are_explicit(self):
        camera = self.make_camera()
        self.assertEqual(CameraStatus.DISCONNECTED, camera.status)

        with self.assertRaises(CameraUnavailable):
            camera.read_frame()

        camera.open()
        self.assertEqual(CameraStatus.READY, camera.status)
        self.assertEqual(10, camera.read_frame().frame_id)
        self.assertEqual(CameraStatus.STREAMING, camera.status)
        self.assertEqual(11, camera.read_frame().frame_id)

        with self.assertRaises(CameraExhausted):
            camera.read_frame()
        self.assertEqual(CameraStatus.EXHAUSTED, camera.status)

        camera.close()
        camera.close()
        self.assertEqual(CameraStatus.DISCONNECTED, camera.status)

    def test_reopening_restarts_a_deterministic_sequence(self):
        camera = self.make_camera()
        camera.open()
        self.assertEqual(10, camera.read_frame().frame_id)
        camera.close()
        camera.open()

        self.assertEqual(10, camera.read_frame().frame_id)

    def test_duplicate_or_untyped_frames_are_rejected_at_construction(self):
        with self.assertRaises(InvalidFrame):
            SequenceCamera(
                (
                    FramePacket(1, 1.0, {}),
                    FramePacket(1, 2.0, {}),
                )
            )

        with self.assertRaises(InvalidFrame):
            SequenceCamera((FramePacket(1, 1.0, {}), object()))

    def test_physical_placeholder_always_refuses(self):
        camera = UnavailableCamera("school camera not connected")

        with self.assertRaisesRegex(CameraUnavailable, "school camera"):
            camera.open()
        self.assertEqual(CameraStatus.FAILED, camera.status)

        with self.assertRaises(CameraUnavailable):
            camera.read_frame()

        camera.close()
        self.assertEqual(CameraStatus.DISCONNECTED, camera.status)


class UsbCameraTest(unittest.TestCase):
    def test_usb_camera_captures_increasing_frames_and_releases(self):
        capture = FakeCapture(frames=[ArrayFrame(), ArrayFrame()])
        ticks = iter((10.0, 11.0))
        camera = OpenCvUsbCamera(
            2,
            capture_factory=lambda index: capture,
            clock=lambda: next(ticks),
        )

        camera.open()
        first = camera.read_frame()
        second = camera.read_frame()
        camera.close()

        self.assertEqual((0, 1), (first.frame_id, second.frame_id))
        self.assertEqual("usb:2", first.source)
        self.assertTrue(capture.released)
        self.assertEqual(CameraStatus.DISCONNECTED, camera.status)

    def test_unavailable_usb_is_released_and_reported(self):
        capture = FakeCapture(opened=False)
        camera = OpenCvUsbCamera(0, capture_factory=lambda index: capture)

        with self.assertRaisesRegex(CameraUnavailable, "index 0"):
            camera.open()

        self.assertTrue(capture.released)
        self.assertEqual(CameraStatus.FAILED, camera.status)

    def test_runtime_usb_failure_does_not_return_an_empty_frame(self):
        camera = OpenCvUsbCamera(
            0,
            capture_factory=lambda index: FakeCapture(opened=True),
        )
        camera.open()

        with self.assertRaises(CameraReadFailure):
            camera.read_frame()

        self.assertEqual(CameraStatus.FAILED, camera.status)

    def test_usb_frames_are_rgb_rotated_and_resolution_checked(self):
        raw = np.zeros((1, 2, 3), dtype=np.uint8)
        raw[0, 0] = [0, 0, 255]  # BGR red, moved to the right by rotation.
        capture = FakeCapture(frames=[raw])
        camera = OpenCvUsbCamera(
            0,
            size=(2, 1),
            rotate_180=True,
            capture_factory=lambda _index: capture,
        )
        camera.open()
        frame = camera.read_frame().payload
        camera.close()

        self.assertEqual([255, 0, 0], frame[0, 1].tolist())
        self.assertTrue(capture.properties)

    def test_usb_rejects_resolution_that_does_not_match_yaren(self):
        camera = OpenCvUsbCamera(
            0,
            size=(320, 240),
            capture_factory=lambda _index: FakeCapture(frames=[ArrayFrame(640, 480)]),
        )
        camera.open()
        with self.assertRaisesRegex(CameraReadFailure, "requires 320x240"):
            camera.read_frame()


class PiCameraTest(unittest.TestCase):
    def test_pi_camera_uses_preview_configuration_and_capture_array(self):
        fake = FakePiCamera([ArrayFrame(800, 600)])
        camera = PiCamera2Source(
            1,
            size=(800, 600),
            camera_factory=lambda number: fake,
            clock=lambda: 4.0,
        )

        camera.open()
        packet = camera.read_frame()
        camera.close()

        self.assertEqual("rpi:1", packet.source)
        self.assertEqual(
            {"main": {"size": (800, 600), "format": "RGB888"}},
            fake.configuration,
        )
        self.assertTrue(fake.started)
        self.assertTrue(fake.closed)

    def test_pi_initialization_failure_is_wrapped_and_closed(self):
        class BrokenPi(FakePiCamera):
            def start(self):
                raise RuntimeError("sensor unavailable")

        fake = BrokenPi()
        camera = PiCamera2Source(camera_factory=lambda number: fake)

        with self.assertRaisesRegex(CameraUnavailable, "sensor unavailable"):
            camera.open()

        self.assertTrue(fake.closed)

    def test_pi_configured_bgr_output_is_normalized_to_rgb(self):
        raw = np.array([[[255, 0, 0]]], dtype=np.uint8)
        fake = FakePiCamera([raw])
        camera = PiCamera2Source(
            size=(1, 1),
            bgr_output=True,
            camera_factory=lambda _number: fake,
        )
        camera.open()
        payload = camera.read_frame().payload
        camera.close()
        self.assertEqual([0, 0, 255], payload[0, 0].tolist())


class PreferredCameraTest(unittest.TestCase):
    def test_builder_carries_active_calibration_to_both_live_adapters(self):
        preferred = build_preferred_camera(
            3, size=(840, 630), bgr_output=True, rotate_180=True
        )
        usb, pi = preferred._candidates
        self.assertEqual((840, 630), usb.size)
        self.assertEqual((840, 630), pi.size)
        self.assertTrue(pi.bgr_output)
        self.assertTrue(usb.rotate_180)

    def test_usb_is_selected_before_pi(self):
        usb = StubCamera("usb:0")
        pi = StubCamera("rpi:0")
        preferred = PreferredCamera((usb, pi))

        preferred.open()
        packet = preferred.read_frame()
        preferred.close()

        self.assertEqual("usb:0", packet.source)
        self.assertEqual(1, usb.open_count)
        self.assertEqual(0, pi.open_count)

    def test_unavailable_usb_falls_back_to_pi(self):
        usb = StubCamera(
            "usb:0", open_error=CameraUnavailable("USB unavailable")
        )
        pi = StubCamera("rpi:0")
        preferred = PreferredCamera((usb, pi))

        preferred.open()
        packet = preferred.read_frame()

        self.assertEqual("rpi:0", packet.source)
        self.assertEqual(1, usb.open_count)
        self.assertEqual(1, pi.open_count)

    def test_all_unavailable_sources_raise_one_aggregate_error(self):
        preferred = PreferredCamera(
            (
                StubCamera("usb:0", open_error=CameraUnavailable("USB missing")),
                StubCamera("rpi:0", open_error=CameraUnavailable("Pi missing")),
            )
        )

        with self.assertRaisesRegex(CameraUnavailable, "USB missing.*Pi missing"):
            preferred.open()

    def test_runtime_read_failure_does_not_switch_sources(self):
        usb = StubCamera(
            "usb:0", read_error=CameraReadFailure("USB disconnected")
        )
        pi = StubCamera("rpi:0")
        preferred = PreferredCamera((usb, pi))
        preferred.open()

        with self.assertRaisesRegex(CameraReadFailure, "USB disconnected"):
            preferred.read_frame()

        self.assertEqual(0, pi.open_count)

    def test_probe_keeps_only_consistent_frame_metadata(self):
        camera = StubCamera("usb:0")
        ticks = iter((5.0, 5.25))

        result = probe_camera(camera, frame_count=3, clock=lambda: next(ticks))

        self.assertEqual("usb:0", result.source)
        self.assertEqual(3, result.frame_count)
        self.assertEqual((640, 480), (result.width, result.height))
        self.assertEqual(0.25, result.elapsed_seconds)
        self.assertGreaterEqual(camera.close_count, 1)

if __name__ == "__main__":
    unittest.main(verbosity=2)
