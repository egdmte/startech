"""Behavior tests for YAREN's immutable calibration/settings registry."""

from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest

from jsonschema import Draft202012Validator

from startech.configuration.profiles import (
    ACTIVE_NAME,
    PROFILE_SCHEMA,
    ActiveProfileArchiveError,
    ActiveProfileError,
    InvalidJsonFile,
    InvalidProfile,
    ProfileAlreadyExists,
    ProfileIntegrityError,
    ProfileLocation,
    ProfileStore,
    WarningAcknowledgementRequired,
    default_profile_root,
    profile_schema_errors,
)
from startech.configuration.validation import json_oku
from startech.configuration.combined import combined_config_errors


PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = PROJECT_ROOT / "config" / "examples"
CALIBRATION = EXAMPLES / "kalibrasyon-v1.ornek.json"
SETTINGS = EXAMPLES / "ayarlar-v1.ornek.json"


class DeterministicClock:
    def __init__(self) -> None:
        self.value = datetime(2026, 8, 22, 10, 0, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        current = self.value
        self.value += timedelta(seconds=1)
        return current


class IdentifierFactory:
    def __init__(self, start: int = 1) -> None:
        self.value = start

    def __call__(self) -> str:
        result = f"{self.value:032x}"
        self.value += 1
        return result


class ProfileStoreTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "registry"
        self.store = ProfileStore(
            self.root,
            id_factory=IdentifierFactory(1),
            selection_id_factory=IdentifierFactory(100),
            now=DeterministicClock(),
        )

    def import_example(self, *, name: str = "School baseline"):
        return self.store.import_pair(CALIBRATION, SETTINGS, name=name)

    def settings_copy(self) -> dict[str, object]:
        return copy.deepcopy(json_oku(SETTINGS))

    def test_profile_schema_is_valid_draft_2020_12(self):
        Draft202012Validator.check_schema(PROFILE_SCHEMA)

    def test_schema_binds_each_hash_to_the_correct_filename(self):
        profile = self.import_example()
        value = profile.manifest.to_dict()
        value["kalibrasyon"]["dosya"] = "ayarlar.json"
        self.assertTrue(profile_schema_errors(value))

    def test_default_root_is_outside_the_project_and_overrideable(self):
        explicit = default_profile_root(
            environment={"STARTECH_PROFILE_ROOT": "D:/profiles"},
            platform_name="nt",
            home=Path("C:/Users/test"),
        )
        windows = default_profile_root(
            environment={"LOCALAPPDATA": "C:/Local"},
            platform_name="nt",
            home=Path("C:/Users/test"),
        )
        linux = default_profile_root(
            environment={"XDG_CONFIG_HOME": "/tmp/config"},
            platform_name="posix",
            home=Path("/home/test"),
        )
        self.assertEqual(Path("D:/profiles"), explicit)
        self.assertEqual(Path("C:/Local/STARTECH/configuration"), windows)
        self.assertEqual(Path("/tmp/config/startech/configuration"), linux)

    def test_import_installs_canonical_pair_with_full_hashes_and_warning(self):
        profile = self.import_example()

        self.assertEqual(ProfileLocation.INSTALLED, profile.location)
        self.assertEqual("00000000000000000000000000000001", profile.manifest.profile_id)
        self.assertEqual("IMPORT", profile.manifest.source_type)
        self.assertEqual((840, 630), (profile.manifest.width, profile.manifest.height))
        self.assertEqual(64, len(profile.manifest.calibration_sha256))
        self.assertEqual(64, len(profile.manifest.settings_sha256))
        self.assertIn("ölü bölgesinin altında", " ".join(profile.manifest.warnings))
        self.assertEqual(
            [profile.manifest.profile_id],
            [summary.profile_id for summary in self.store.list_profiles()],
        )

        for filename in ("kalibrasyon.json", "ayarlar.json", "profil.json"):
            text = (profile.directory / filename).read_text(encoding="utf-8")
            self.assertTrue(text.endswith("\n"))
            self.assertEqual(json.loads(text), json.loads(text, object_pairs_hook=dict))

    def test_combined_import_is_idempotent_and_never_changes_active_selection(self):
        active = self.import_example(name="Active baseline")
        selection = self.store.activate_profile(
            active.manifest.profile_id,
            warning_digest=active.manifest.warning_digest,
            reviewer="student",
        )
        document = json_oku(EXAMPLES / "yapilandirma-v2.ornek.json")
        self.assertFalse(combined_config_errors(document))
        installed = self.store.import_combined(document, deployment_id="cam:c7a2ee")
        repeated = self.store.import_combined(document, deployment_id="cam:c7a2ee")

        self.assertEqual(installed.manifest.profile_id, repeated.manifest.profile_id)
        self.assertEqual(selection, self.store.load_active_selection())
        self.assertNotEqual(active.manifest.profile_id, installed.manifest.profile_id)

        changed = copy.deepcopy(document)
        changed["ayarlar"]["hiz"]["hedef"] += 1
        with self.assertRaises(ProfileIntegrityError):
            self.store.import_combined(changed, deployment_id="cam:c7a2ee")

    def test_malformed_duplicate_and_non_object_json_are_rejected(self):
        bad = Path(self.temporary.name) / "bad.json"
        bad.write_text('{"sema_surumu": 1, "sema_surumu": 1}', encoding="utf-8")
        with self.assertRaises(InvalidJsonFile):
            self.store.import_pair(bad, SETTINGS, name="duplicate")

        bad.write_text("[]", encoding="utf-8")
        with self.assertRaises(InvalidJsonFile):
            self.store.import_pair(bad, SETTINGS, name="array")

    def test_invalid_pair_does_not_create_an_installed_profile(self):
        invalid_settings = self.settings_copy()
        invalid_settings["hiz"]["min"] = 90
        path = Path(self.temporary.name) / "invalid-settings.json"
        path.write_text(json.dumps(invalid_settings), encoding="utf-8")

        with self.assertRaises(InvalidProfile):
            self.store.import_pair(CALIBRATION, path, name="invalid")
        self.assertFalse(self.store.profiles_directory.exists())

    def test_identifier_collision_never_overwrites_an_existing_profile(self):
        fixed_id = "1" * 32
        store = ProfileStore(
            self.root,
            id_factory=lambda: fixed_id,
            selection_id_factory=IdentifierFactory(100),
            now=DeterministicClock(),
        )
        first = store.import_pair(CALIBRATION, SETTINGS, name="first")
        original = (first.directory / "profil.json").read_bytes()
        with self.assertRaises(ProfileAlreadyExists):
            store.import_pair(CALIBRATION, SETTINGS, name="second")
        self.assertEqual(original, (first.directory / "profil.json").read_bytes())

    def test_installed_file_mutation_is_detected(self):
        profile = self.import_example()
        path = profile.directory / "ayarlar.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        value["hiz"]["hedef"] = 51
        path.write_text(
            json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        with self.assertRaises(ProfileIntegrityError):
            self.store.load_profile(profile.manifest.profile_id)

    def test_warning_profile_requires_exact_digest_and_named_reviewer(self):
        profile = self.import_example()
        with self.assertRaises(WarningAcknowledgementRequired):
            self.store.activate_profile(profile.manifest.profile_id)
        with self.assertRaises(WarningAcknowledgementRequired):
            self.store.activate_profile(
                profile.manifest.profile_id,
                warning_digest="0" * 64,
                reviewer="student",
            )
        with self.assertRaises(WarningAcknowledgementRequired):
            self.store.activate_profile(
                profile.manifest.profile_id,
                warning_digest=profile.manifest.warning_digest,
            )

        selection = self.store.activate_profile(
            profile.manifest.profile_id,
            warning_digest=profile.manifest.warning_digest,
            reviewer="school team",
        )
        self.assertEqual(profile.manifest.profile_id, selection.profile_id)
        self.assertEqual("school team", selection.warning_reviewer)
        self.assertEqual(
            profile.manifest.profile_id,
            self.store.load_active_profile().manifest.profile_id,
        )

    def test_settings_variant_preserves_parent_and_original(self):
        parent = self.import_example()
        original = (parent.directory / "ayarlar.json").read_bytes()
        settings = self.settings_copy()
        settings["hiz"]["hedef"] = 49
        child = self.store.create_settings_variant(
            parent.manifest.profile_id,
            settings,
            name="Slower test",
            note="classroom simulation only",
        )

        self.assertEqual("SETTINGS_VARIANT", child.manifest.source_type)
        self.assertEqual(parent.manifest.profile_id, child.manifest.parent_profile_id)
        self.assertEqual(original, (parent.directory / "ayarlar.json").read_bytes())
        differences = self.store.compare_profiles(
            parent.manifest.profile_id, child.manifest.profile_id
        )
        self.assertEqual(["ayarlar.hiz.hedef"], [item.path for item in differences])

    def test_active_pointer_and_history_fail_closed(self):
        profile = self.import_example()
        self.store.activate_profile(
            profile.manifest.profile_id,
            warning_digest=profile.manifest.warning_digest,
            reviewer="student",
        )
        self.assertEqual(1, len(self.store.activation_history()))
        self.assertTrue(self.store.activation_history()[0].committed)

        pointer = json.loads(self.store.active_path.read_text(encoding="utf-8"))
        pointer["ayarlar_sha256"] = "0" * 64
        self.store.active_path.write_text(
            json.dumps(pointer, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        with self.assertRaises(ActiveProfileError):
            self.store.load_active_selection()

    def test_missing_history_entry_invalidates_active_pointer(self):
        profile = self.import_example()
        selection = self.store.activate_profile(
            profile.manifest.profile_id,
            warning_digest=profile.manifest.warning_digest,
            reviewer="student",
        )
        (self.store.history_directory / f"{selection.selection_id}.json").unlink()
        with self.assertRaises(ActiveProfileError):
            self.store.load_active_selection()

    def test_diagnosis_checks_observed_camera_resolution(self):
        profile = self.import_example()
        self.store.activate_profile(
            profile.manifest.profile_id,
            warning_digest=profile.manifest.warning_digest,
            reviewer="student",
        )
        self.assertTrue(self.store.diagnose_active(camera_dimensions=(840, 630)).valid)
        diagnosis = self.store.diagnose_active(camera_dimensions=(640, 480))
        self.assertFalse(diagnosis.valid)
        self.assertIn("resolution", " ".join(diagnosis.errors))

    def test_active_profile_cannot_be_archived_and_other_profiles_can(self):
        active = self.import_example(name="active")
        other = self.store.import_pair(CALIBRATION, SETTINGS, name="other")
        self.store.activate_profile(
            active.manifest.profile_id,
            warning_digest=active.manifest.warning_digest,
            reviewer="student",
        )
        with self.assertRaises(ActiveProfileArchiveError):
            self.store.archive_profile(active.manifest.profile_id)

        archived = self.store.archive_profile(other.manifest.profile_id)
        self.assertEqual(ProfileLocation.ARCHIVED, archived.location)
        restored = self.store.restore_profile(other.manifest.profile_id)
        self.assertEqual(ProfileLocation.INSTALLED, restored.location)

    def test_export_never_overwrites_destination(self):
        profile = self.import_example()
        destination = Path(self.temporary.name) / "exported"
        self.assertEqual(
            destination,
            self.store.export_profile(profile.manifest.profile_id, destination),
        )
        with self.assertRaises(ProfileAlreadyExists):
            self.store.export_profile(profile.manifest.profile_id, destination)

    def test_archive_profile_cannot_be_selected(self):
        profile = self.import_example()
        self.store.archive_profile(profile.manifest.profile_id)
        with self.assertRaises(Exception) as caught:
            self.store.activate_profile(profile.manifest.profile_id)
        self.assertNotIsInstance(caught.exception, WarningAcknowledgementRequired)
        self.assertFalse((self.root / ACTIVE_NAME).exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
