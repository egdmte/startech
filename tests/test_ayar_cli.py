"""Behavior tests for the YAREN terminal settings/profile manager."""

from __future__ import annotations

from datetime import datetime, timezone
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from arac import ayar_cli
from startech.configuration.profiles import ProfileStore


PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = PROJECT_ROOT / "config" / "examples"


class YarenCliTest(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "registry"
        self.store = ProfileStore(
            self.root,
            id_factory=lambda: "1" * 32,
            selection_id_factory=lambda: "2" * 32,
            now=lambda: datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc),
        )

    def run_cli(self, arguments, *, input_fn=lambda _prompt: ""):
        output = io.StringIO()
        result = ayar_cli.run(
            ["--profile-root", str(self.root), "--no-color", *arguments],
            input_fn=input_fn,
            output=output,
        )
        return result, output.getvalue()

    def import_profile(self):
        return self.store.import_pair(
            EXAMPLES / "kalibrasyon-v1.ornek.json",
            EXAMPLES / "ayarlar-v1.ornek.json",
            name="Baseline",
        )

    def test_setting_parser_accepts_only_documented_numeric_paths(self):
        self.assertEqual(("hiz.hedef", 48), ayar_cli.parse_setting_assignment("hiz.hedef=48"))
        self.assertEqual(("kontrol.kp", 0.5), ayar_cli.parse_setting_assignment("kontrol.kp=0.5"))
        with self.assertRaises(ValueError):
            ayar_cli.parse_setting_assignment("motor.pwm=100")
        with self.assertRaises(ValueError):
            ayar_cli.parse_setting_assignment("hiz.hedef=true")
        with self.assertRaises(ValueError):
            ayar_cli.parse_setting_assignment("hiz.hedef=48.5")

    def test_import_command_installs_but_does_not_select(self):
        result, output = self.run_cli(
            [
                "import",
                str(EXAMPLES / "kalibrasyon-v1.ornek.json"),
                str(EXAMPLES / "ayarlar-v1.ornek.json"),
                "--name",
                "Baseline",
            ]
        )
        self.assertEqual(ayar_cli.EXIT_OK, result)
        self.assertIn("Installed for review", output)
        self.assertIn("warnings", output)
        self.assertFalse(self.store.active_path.exists())

    def test_settings_command_creates_variant_and_keeps_parent(self):
        parent = self.import_profile()
        with patch("arac.ayar_cli.ProfileStore") as store_type:
            store_type.return_value = self.store
            self.store._id_factory = lambda: "3" * 32
            result, output = self.run_cli(
                [
                    "settings",
                    parent.manifest.profile_id,
                    "--name",
                    "Slow test",
                    "--set",
                    "hiz.hedef=48",
                    "--set",
                    "kontrol.kp=0.5",
                ]
            )
        self.assertEqual(ayar_cli.EXIT_OK, result)
        self.assertIn("parent unchanged", output)
        child = self.store.load_profile("3" * 32)
        self.assertEqual(48, child.settings["hiz"]["hedef"])
        self.assertEqual(50, parent.settings["hiz"]["hedef"])

    def test_warning_activation_refuses_without_exact_review_evidence(self):
        profile = self.import_profile()
        result, output = self.run_cli(["activate", profile.manifest.profile_id])
        self.assertEqual(ayar_cli.EXIT_INVALID, result)
        self.assertIn("exact current warning digest", output)

        result, output = self.run_cli(
            [
                "activate",
                profile.manifest.profile_id,
                "--warning-digest",
                profile.manifest.warning_digest,
                "--reviewer",
                "school team",
            ]
        )
        self.assertEqual(ayar_cli.EXIT_OK, result)
        self.assertIn("NOT ARMED", output)

    def test_diagnosis_reports_missing_active_profile(self):
        result, output = self.run_cli(["diagnose"])
        self.assertEqual(ayar_cli.EXIT_INVALID, result)
        self.assertIn("valid", output)
        self.assertIn("False", output)
        self.assertIn("NOT ARMED", output)

    def test_interactive_menu_can_exit_without_writes(self):
        result, output = self.run_cli(["interactive"], input_fn=lambda _prompt: "0")
        self.assertEqual(ayar_cli.EXIT_OK, result)
        self.assertIn("STARTECH-YAREN", output)
        self.assertIn("vehicle remains unarmed", output)
        self.assertFalse(self.root.exists())

    def test_interactive_warning_selection_requires_literal_ack(self):
        profile = self.import_profile()
        values = iter(("5", profile.manifest.profile_id, "no", "0"))
        result, output = self.run_cli(
            ["interactive"], input_fn=lambda _prompt: next(values)
        )
        self.assertEqual(ayar_cli.EXIT_OK, result)
        self.assertIn("Selection cancelled", output)
        self.assertFalse(self.store.active_path.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
