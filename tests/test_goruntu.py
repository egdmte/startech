"""Proof for KEREM's real lane pipeline and YAREN compatibility probe."""

from __future__ import annotations

import unittest

import numpy as np

from arac.goruntu import (
    InvalidObservation,
    LaneObservation,
    LaneVisionAnalyzer,
    StaleFrame,
)
from arac.goz import FramePacket


def calibration(width: int = 320, height: int = 240) -> dict[str, object]:
    profile = {"alt": [0, 0, 175], "ust": [180, 80, 255]}
    return {
        "kamera": {
            "genislik": width,
            "yukseklik": height,
            "bgr_cikis": False,
            "dondur_180": False,
        },
        "perspektif": {
            "olculen_cozunurluk": [width, height],
            "kaynak_noktalar": [
                [0, 0], [width - 1, 0], [0, height - 1], [width - 1, height - 1]
            ],
            "roi_ust_oran": 0.0,
        },
        "serit": {
            "beyaz_profiller": {
                "varsayilan": profile,
                "karanlik": profile,
                "normal": profile,
                "parlak": profile,
            },
            "profil_esikleri": {"karanlik_alti": 70, "parlak_ustu": 220},
            "min_sinyal": 100,
            "min_sinyal_kalite_orani": 1.0,
            "varsayilan_serit_genisligi": 180,
            "sureklilik_orani": 0.10,
            "clahe_sinir": 2.0,
            "clahe_kutucuk": 8,
        },
    }


def lane_frame(left: tuple[int, int] | None, right: tuple[int, int] | None) -> np.ndarray:
    frame = np.zeros((240, 320, 3), dtype=np.uint8)
    if left:
        frame[:, left[0] : left[1], :] = 255
    if right:
        frame[:, right[0] : right[1], :] = 255
    return frame


class LiveLaneAnalyzerTest(unittest.TestCase):
    def test_two_drawn_image_lanes_produce_centered_observation(self):
        analyzer = LaneVisionAnalyzer(calibration())
        result = analyzer.analyze(
            FramePacket(0, 1.0, lane_frame((65, 75), (245, 255)), "camera")
        )

        self.assertTrue(result.valid)
        self.assertAlmostEqual(0.0, result.normalized_error, delta=0.04)
        self.assertIsNotNone(result.debug_frame)
        self.assertEqual((240, 320, 3), result.debug_frame.shape)

    def test_shifted_lane_preserves_legacy_left_correction_sign(self):
        analyzer = LaneVisionAnalyzer(calibration())
        result = analyzer.analyze(
            FramePacket(0, 1.0, lane_frame((20, 30), (200, 210)), "camera")
        )

        self.assertTrue(result.valid)
        self.assertGreater(result.error_px, 0)
        self.assertGreater(result.normalized_error, 0)

    def test_one_lane_uses_configured_lane_width(self):
        analyzer = LaneVisionAnalyzer(calibration())
        result = analyzer.analyze(
            FramePacket(0, 1.0, lane_frame((65, 75), None), "camera")
        )

        self.assertTrue(result.valid)
        self.assertIsNotNone(result.left_lane_px)
        self.assertIsNone(result.right_lane_px)

    def test_no_lane_is_explicit_stop_evidence(self):
        result = LaneVisionAnalyzer(calibration()).analyze(
            FramePacket(0, 1.0, lane_frame(None, None), "camera")
        )

        self.assertFalse(result.valid)
        self.assertIsNone(result.error_px)
        self.assertEqual("no lane signal", result.reason)

    def test_remembered_lanes_cannot_validate_an_empty_current_frame(self):
        analyzer = LaneVisionAnalyzer(calibration())
        first = analyzer.analyze(
            FramePacket(0, 1.0, lane_frame((65, 75), (245, 255)), "camera")
        )
        result = analyzer.analyze(
            FramePacket(1, 2.0, lane_frame(None, None), "camera")
        )

        self.assertTrue(first.valid)
        self.assertFalse(result.valid)
        self.assertIsNone(result.error_px)
        self.assertIsNone(result.normalized_error)
        self.assertEqual(0.0, result.confidence)
        self.assertIsNone(result.left_lane_px)
        self.assertIsNone(result.right_lane_px)
        self.assertEqual(
            "lane memory has no current-frame evidence", result.reason
        )

    def test_resolution_mismatch_and_stale_frames_are_rejected(self):
        analyzer = LaneVisionAnalyzer(calibration())
        with self.assertRaisesRegex(InvalidObservation, "requires 320x240"):
            analyzer.analyze(FramePacket(
                0, 1.0, np.zeros((100, 100, 3), dtype=np.uint8), "controlled-test"
            ))

        analyzer = LaneVisionAnalyzer(calibration())
        analyzer.analyze(FramePacket(2, 1.0, lane_frame(None, None), "controlled-test"))
        with self.assertRaises(StaleFrame):
            analyzer.analyze(FramePacket(2, 2.0, lane_frame(None, None), "controlled-test"))

    def test_observation_record_excludes_debug_pixels(self):
        result = LaneVisionAnalyzer(calibration()).analyze(
            FramePacket(0, 1.0, lane_frame((65, 75), (245, 255)), "controlled-test")
        )
        record = result.record_data()

        self.assertNotIn("debug_frame", record)
        self.assertEqual(0, record["frame_id"])


class ObservationModelTest(unittest.TestCase):
    def test_invalid_lane_observation_cannot_claim_an_error(self):
        with self.assertRaises(InvalidObservation):
            LaneObservation(0, 1.0, False, 2.0, 0.1, 0.0, None, None, None, 20, "lost")


if __name__ == "__main__":
    unittest.main(verbosity=2)
