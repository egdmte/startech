"""Validation and persistence tests for KADER."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from arac.kayit import (
    BlackBoxRecord,
    InvalidRecord,
    JsonlBlackBox,
    MemoryBlackBox,
    RecordKind,
    RecordOrderError,
)


class BlackBoxRecordTest(unittest.TestCase):
    def test_data_is_canonical_and_read_only(self):
        record = BlackBoxRecord(
            run_id="run-1",
            sequence=0,
            recorded_at=1.0,
            kind=RecordKind.INFO,
            module="ARDA",
            data={"nested": [1, 2, {"ready": True}]},
        )

        self.assertEqual([1, 2, {"ready": True}], record.data["nested"])
        with self.assertRaises(TypeError):
            record.data["extra"] = True

    def test_non_json_and_non_finite_values_are_rejected(self):
        invalid_data = (
            {"number": float("nan")},
            {"number": float("inf")},
            {1: "non-text key"},
            {"object": object()},
        )

        for data in invalid_data:
            with self.subTest(data=data):
                with self.assertRaises(InvalidRecord):
                    BlackBoxRecord(
                        "run-1",
                        0,
                        1.0,
                        RecordKind.INFO,
                        "ARDA",
                        data,
                    )


class MemoryBlackBoxTest(unittest.TestCase):
    def test_sequences_are_contiguous_and_frames_do_not_move_backwards(self):
        box = MemoryBlackBox("run-memory")
        first = box.append(
            RecordKind.FRAME,
            "KASIM",
            {"source": "simulation"},
            frame_id=5,
            recorded_at=1.0,
        )
        second = box.append(
            RecordKind.OBSERVATION,
            "KEREM",
            {"valid": True},
            frame_id=5,
            recorded_at=1.1,
        )

        self.assertEqual((0, 1), (first.sequence, second.sequence))
        with self.assertRaises(RecordOrderError):
            box.append(
                RecordKind.FRAME,
                "KASIM",
                {"source": "simulation"},
                frame_id=4,
                recorded_at=1.2,
            )
        self.assertEqual(2, len(box.records))


class JsonlBlackBoxTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "run.jsonl"

    def tearDown(self):
        self.temp.cleanup()

    def test_constructor_does_not_create_a_file_and_append_is_jsonl(self):
        box = JsonlBlackBox(self.path, "run-jsonl")
        self.assertFalse(self.path.exists())

        box.append(
            RecordKind.STATE,
            "DORA",
            {"state": "READY"},
            frame_id=2,
            recorded_at=10.0,
        )

        lines = self.path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(1, len(lines))
        self.assertEqual("READY", json.loads(lines[0])["data"]["state"])

    def test_existing_valid_run_is_recovered_and_appended(self):
        box = JsonlBlackBox(self.path, "run-jsonl")
        box.append(RecordKind.INFO, "ARDA", {"step": 1}, recorded_at=1.0)

        resumed = JsonlBlackBox(self.path, "run-jsonl")
        resumed.append(RecordKind.INFO, "ARDA", {"step": 2}, recorded_at=2.0)

        self.assertEqual((0, 1), tuple(item.sequence for item in resumed.records))
        self.assertEqual(2, len(self.path.read_text(encoding="utf-8").splitlines()))

    def test_corrupt_blank_or_different_run_is_rejected(self):
        cases = (
            "\n",
            "not-json\n",
            json.dumps(
                BlackBoxRecord(
                    "different-run",
                    0,
                    1.0,
                    RecordKind.INFO,
                    "ARDA",
                    {},
                ).to_dict()
            )
            + "\n",
        )

        for content in cases:
            with self.subTest(content=content):
                self.path.write_text(content, encoding="utf-8")
                with self.assertRaises((InvalidRecord, RecordOrderError)):
                    JsonlBlackBox(self.path, "run-jsonl")


if __name__ == "__main__":
    unittest.main(verbosity=2)
