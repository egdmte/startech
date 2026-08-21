"""Contract tests for the hardware-free KASIM/CAMILA camera scaffold."""

from __future__ import annotations

import unittest

from arac.goz import (
    CameraExhausted,
    CameraStatus,
    CameraUnavailable,
    FramePacket,
    InvalidFrame,
    SequenceCamera,
    UnavailableCamera,
)


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


if __name__ == "__main__":
    unittest.main(verbosity=2)
