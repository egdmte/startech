"""Tests for ARDA's fail-closed active-configuration loader."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest

from arac.ayar import ConfigurationLoadError, load_active_configuration
from startech.configuration.profiles import ProfileStore


PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = PROJECT_ROOT / "config" / "examples"


class ActiveConfigurationTest(unittest.TestCase):
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

    def select_example(self):
        profile = self.store.import_pair(
            EXAMPLES / "kalibrasyon-v1.ornek.json",
            EXAMPLES / "ayarlar-v1.ornek.json",
            name="School baseline",
        )
        self.store.activate_profile(
            profile.manifest.profile_id,
            warning_digest=profile.manifest.warning_digest,
            reviewer="school team",
        )
        return profile

    def test_missing_selection_fails_closed(self):
        with self.assertRaises(ConfigurationLoadError):
            load_active_configuration(self.root)

    def test_selected_profile_loads_as_immutable_snapshot(self):
        profile = self.select_example()
        active = load_active_configuration(
            self.root, camera_dimensions=(840, 630)
        )
        self.assertEqual(profile.manifest.profile_id, active.profile_id)
        self.assertEqual((840, 630), active.camera_dimensions)
        self.assertFalse(active.motor_measurement_recorded)
        with self.assertRaises(TypeError):
            active.settings["hiz"]["hedef"] = 60
        with self.assertRaises(TypeError):
            active.calibration["perspektif"]["kaynak_noktalar"][0][0] = 0

    def test_camera_resolution_mismatch_fails_closed(self):
        self.select_example()
        with self.assertRaisesRegex(ConfigurationLoadError, "resolution"):
            load_active_configuration(self.root, camera_dimensions=(640, 480))

    def test_tampered_selected_profile_fails_closed(self):
        profile = self.select_example()
        settings_path = profile.directory / "ayarlar.json"
        settings_path.write_text("{}\n", encoding="utf-8")
        with self.assertRaises(ConfigurationLoadError):
            load_active_configuration(self.root)


if __name__ == "__main__":
    unittest.main(verbosity=2)
