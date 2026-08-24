"""Behaviour tests for merged configuration v2 and stable SAC contract v1."""

from __future__ import annotations

import copy
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from startech.configuration.combined import (
    COMBINED_SCHEMA,
    combined_config_errors,
    combined_schema_errors,
    merge_v1_pair,
    split_v2,
)
from startech.configuration.validation import json_oku


ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "config" / "examples"


def sac_intent() -> dict[str, object]:
    return {
        "sozlesme_surumu": 1,
        "kamera": {
            "yon_derecesi": 180,
            "yakalama_profili": "640x480",
            "tanima_hassasiyeti": "conservative",
            "raspberry_pi_oncelikli": False,
        },
        "guc": {
            "minimum_hiz_yuzde": 25,
            "maksimum_hiz_yuzde": 57,
        },
        "hesaplama": {
            "baslangic_onlemi": "individual-buttons",
            "servis_durumu": "on",
            "m3th_sikiligi": "full",
            "etkin_moduller": ["yaren", "arda", "kasim", "m3th"],
        },
        "surus": {
            "komut_kaybi_eylemi": "disarm-wait",
            "surucu_cikis_modu": "off",
            "direksiyon_merkez_yuzde": 0,
            "direksiyon_azami_hareket_yuzde": 40,
        },
        "tekerlek": {
            "sol_duzeltme_yuzde": 0,
            "sag_duzeltme_yuzde": 0,
            "sol_yon": "normal",
            "sag_yon": "normal",
        },
    }


def session_evidence() -> dict[str, object]:
    return {
        "simulasyon": True,
        "fiziksel_cikis_aktif": False,
        "fiziksel_dogrulama_yapildi": False,
        "tam_cikis_onaylandi": False,
        "prototip_kilidi_onaylandi": False,
        "mekanik_inceleme": ["wheels-secured", "motors-mounted", "path-clear"],
        "fiziksel_hizalama_dogrulandi": False,
    }


class CombinedConfigurationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.calibration = json_oku(EXAMPLES / "kalibrasyon-v1.ornek.json")
        cls.settings = json_oku(EXAMPLES / "ayarlar-v1.ornek.json")
        cls.combined_example = json_oku(EXAMPLES / "yapilandirma-v2.ornek.json")

    def merge(self, **overrides):
        arguments = {
            "name": "School bench profile",
            "source": "DEFAULT",
            "sac_intent": sac_intent(),
            "session_evidence": session_evidence(),
            "now": lambda: "2026-08-24T12:00:00+00:00",
            "identifier": lambda: "c7a2ee",
        }
        arguments.update(overrides)
        return merge_v1_pair(self.calibration, self.settings, **arguments)

    def test_schema_is_valid_draft_2020_12(self):
        Draft202012Validator.check_schema(COMBINED_SCHEMA)

    def test_combined_example_is_valid(self):
        self.assertEqual([], combined_config_errors(self.combined_example))

    def test_valid_pair_becomes_valid_v2_without_mutating_inputs(self):
        original_calibration = copy.deepcopy(self.calibration)
        original_settings = copy.deepcopy(self.settings)
        combined = self.merge()
        self.assertEqual([], combined_config_errors(combined))
        self.assertEqual(2, combined["sema_surumu"])
        self.assertEqual(1, combined["sac_niyeti"]["sozlesme_surumu"])
        self.assertEqual(original_calibration, self.calibration)
        self.assertEqual(original_settings, self.settings)

    def test_split_returns_independent_v1_documents(self):
        combined = self.merge()
        calibration, settings = split_v2(combined)
        self.assertEqual(self.calibration, calibration)
        self.assertEqual(self.settings, settings)
        calibration["kamera"]["genislik"] = 1
        self.assertNotEqual(
            calibration["kamera"]["genislik"],
            combined["kalibrasyon"]["kamera"]["genislik"],
        )

    def test_assisted_speed_changes_settings_and_clamps_target(self):
        intent = sac_intent()
        intent["guc"] = {
            "minimum_hiz_yuzde": 51,
            "maksimum_hiz_yuzde": 57,
        }
        combined = self.merge(sac_intent=intent)
        self.assertEqual(51, combined["ayarlar"]["hiz"]["min"])
        self.assertEqual(51, combined["ayarlar"]["hiz"]["hedef"])
        self.assertEqual(57, combined["ayarlar"]["hiz"]["max"])

    def test_unknown_outer_and_intent_fields_are_rejected(self):
        combined = self.merge()
        combined["unknown"] = True
        self.assertTrue(combined_schema_errors(combined))
        combined = self.merge()
        combined["sac_niyeti"]["kamera"]["unknown"] = True
        self.assertTrue(combined_schema_errors(combined))

    def test_invalid_nested_pair_is_rejected(self):
        calibration = copy.deepcopy(self.calibration)
        calibration["kamera"]["genislik"] = "840"
        with self.assertRaisesRegex(ValueError, "kalibrasyon.kamera.genislik"):
            merge_v1_pair(
                calibration,
                self.settings,
                name="Broken",
                source="DEFAULT",
                sac_intent=sac_intent(),
                session_evidence=session_evidence(),
            )

    def test_required_sac_modules_are_semantic_requirements(self):
        intent = sac_intent()
        intent["hesaplama"]["etkin_moduller"] = ["yaren", "arda"]
        with self.assertRaisesRegex(ValueError, "kasim"):
            self.merge(sac_intent=intent)

    def test_full_output_requires_both_session_acknowledgements(self):
        intent = sac_intent()
        intent["surus"]["surucu_cikis_modu"] = "full"
        with self.assertRaisesRegex(ValueError, "iki SAC onayı"):
            self.merge(sac_intent=intent)
        evidence = session_evidence()
        evidence["tam_cikis_onaylandi"] = True
        evidence["prototip_kilidi_onaylandi"] = True
        combined = self.merge(sac_intent=intent, session_evidence=evidence)
        self.assertEqual([], combined_config_errors(combined))

    def test_speed_intent_must_be_ordered(self):
        intent = sac_intent()
        intent["guc"] = {
            "minimum_hiz_yuzde": 70,
            "maksimum_hiz_yuzde": 40,
        }
        with self.assertRaisesRegex(ValueError, "minimum hız"):
            self.merge(sac_intent=intent)


if __name__ == "__main__":
    unittest.main(verbosity=2)
