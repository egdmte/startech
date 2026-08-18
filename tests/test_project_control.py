"""Focused behavior tests for the extracted project consistency checks."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from proje_kontrol.claims import check_file_names, check_section_references
from proje_kontrol.measurements import check_measurements
from proje_kontrol.repository import missing_documents


class ProjectControlTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def resolver(self, name: str) -> str | None:
        path = self.root / name
        return str(path) if path.exists() else None

    def write(self, name: str, text: str) -> Path:
        path = self.root / name
        path.write_text(text, encoding="utf-8")
        return path

    def test_missing_document_fails_closed(self):
        self.write("PLAN_New.md", "## 1. Plan\n")
        self.assertEqual(
            ["CLAUDE.md"],
            missing_documents(("PLAN_New.md", "CLAUDE.md"), self.resolver),
        )

    def test_filename_must_exist_or_be_allowed(self):
        self.write("PLAN_New.md", "Use missing.py and planned.py.\n")
        findings = check_file_names(
            ("PLAN_New.md",),
            self.resolver,
            {"PLAN_New.md"},
            {"planned.py"},
        )
        self.assertEqual(["PLAN_New.md:1  missing.py"], findings)

    def test_section_reference_must_resolve(self):
        plan = self.write("PLAN_New.md", "## 1. Start\nSee §1 and §9.\n")
        self.assertEqual(
            ["PLAN_New.md:2  §9"], check_section_references(str(plan))
        )

    def test_measurement_needs_date_or_uncertainty(self):
        self.write("CLAUDE.md", "Araç 30 FPS çalıştı.\n")
        self.assertEqual(
            ["CLAUDE.md:1  Araç 30 FPS çalıştı."],
            check_measurements(("CLAUDE.md",), self.resolver, []),
        )

        self.write("CLAUDE.md", "2026-08-06 koşusunda araç 30 FPS çalıştı.\n")
        self.assertEqual(
            [], check_measurements(("CLAUDE.md",), self.resolver, [])
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
