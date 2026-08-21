"""Contract tests for the deterministic KEREM/CORA vision scaffold."""

from __future__ import annotations

import unittest

from arac.goruntu import (
    InvalidObservation,
    Observation,
    SimulatedVisionAnalyzer,
    StaleFrame,
    UnavailableVisionAnalyzer,
)
from arac.goz import FramePacket


def frame(frame_id, payload):
    return FramePacket(frame_id, float(frame_id), payload, source="vision-test")


class SimulatedVisionAnalyzerTest(unittest.TestCase):
    def test_valid_payload_becomes_a_valid_observation(self):
        analyzer = SimulatedVisionAnalyzer()
        result = analyzer.analyze(
            frame(
                1,
                {
                    "valid": True,
                    "lane_error": -0.25,
                    "detected_sign": "stop",
                    "obstacle": True,
                    "confidence": 0.8,
                },
            )
        )

        self.assertTrue(result.valid)
        self.assertEqual(-0.25, result.lane_error)
        self.assertEqual("stop", result.detected_sign)
        self.assertTrue(result.obstacle)

    def test_invalid_payload_stays_unknown_instead_of_clear(self):
        analyzer = SimulatedVisionAnalyzer()
        result = analyzer.analyze(
            frame(1, {"valid": False, "reason": "camera exposure lost"})
        )

        self.assertFalse(result.valid)
        self.assertIsNone(result.lane_error)
        self.assertIsNone(result.detected_sign)
        self.assertIsNone(result.obstacle)
        self.assertEqual(0.0, result.confidence)

    def test_invalid_payload_cannot_smuggle_a_clear_road_claim(self):
        analyzer = SimulatedVisionAnalyzer()

        with self.assertRaises(InvalidObservation):
            analyzer.analyze(
                frame(
                    1,
                    {
                        "valid": False,
                        "reason": "unknown",
                        "obstacle": False,
                    },
                )
            )

    def test_unknown_missing_and_non_finite_fields_are_rejected(self):
        payloads = (
            {"valid": True, "lane_error": 0.0, "obstacle": False},
            {
                "valid": True,
                "lane_error": float("nan"),
                "obstacle": False,
                "confidence": 0.8,
            },
            {
                "valid": True,
                "lane_error": 0.0,
                "obstacle": False,
                "confidence": 1.2,
            },
            {
                "valid": True,
                "lane_error": 0.0,
                "obstacle": False,
                "confidence": 0.8,
                "surprise": 1,
            },
        )

        for index, payload in enumerate(payloads):
            with self.subTest(payload=payload):
                with self.assertRaises(InvalidObservation):
                    SimulatedVisionAnalyzer().analyze(frame(index, payload))

    def test_stale_frame_is_rejected(self):
        analyzer = SimulatedVisionAnalyzer()
        payload = {
            "valid": True,
            "lane_error": 0.0,
            "obstacle": False,
            "confidence": 1.0,
        }
        analyzer.analyze(frame(2, payload))

        with self.assertRaises(StaleFrame):
            analyzer.analyze(frame(2, payload))

    def test_unavailable_analyzer_returns_explicit_invalid_result(self):
        result = UnavailableVisionAnalyzer("OpenCV adapter missing").analyze(
            frame(4, {"ignored": True})
        )

        self.assertFalse(result.valid)
        self.assertIn("OpenCV", result.reason)


class ObservationModelTest(unittest.TestCase):
    def test_invalid_observation_cannot_have_positive_claims(self):
        with self.assertRaises(InvalidObservation):
            Observation(0, 0.0, False, 0.0, None, None, 0.0, "invalid")


if __name__ == "__main__":
    unittest.main(verbosity=2)
