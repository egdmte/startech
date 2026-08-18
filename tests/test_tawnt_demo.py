# -*- coding: utf-8 -*-
"""``fake_main.py`` dosyasının gerçekten sahte ve fail-closed olduğunu kanıtlar."""

from __future__ import annotations

import ast
from contextlib import redirect_stdout
import importlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest

import fake_main
import tawnt
from examples import tawnt_demo


class FakeMainTest(unittest.TestCase):
    def setUp(self) -> None:
        tawnt.sifirla()
        importlib.reload(fake_main)

    def test_import_hicbir_dosya_ve_hareket_uretmez(self):
        previous_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            try:
                os.chdir(temp_path)
                before = set(temp_path.iterdir())
                importlib.reload(fake_main)
                after = set(temp_path.iterdir())
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(before, after)
        self.assertEqual(tawnt.BOOT, tawnt.systemState())
        self.assertFalse(tawnt.isMotionAllowed())

    def test_dosya_donanim_kutuphanesi_ithal_etmez_ve_tum_acik_apiyi_gosterir(self):
        imported_roots = set()
        tawnt_members = set()
        source_dir = Path(tawnt_demo.__file__).parent
        for source_path in source_dir.glob("*.py"):
            tree = ast.parse(source_path.read_text(encoding="utf-8-sig"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported_roots.update(
                        alias.name.split(".")[0] for alias in node.names
                    )
                elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                    imported_roots.add(node.module.split(".")[0])
                elif (
                    isinstance(node, ast.Attribute)
                    and isinstance(node.value, ast.Name)
                    and node.value.id == "tawnt"
                ):
                    tawnt_members.add(node.attr)

        allowed_imports = {
            "__future__", "dataclasses", "json", "pathlib", "tempfile", "tawnt"
        }
        self.assertEqual(set(), imported_roots - allowed_imports)

        public_methods = {
            "defineValue", "recordValue", "dependsOn", "requireMeasured",
            "validateBeforeStart", "seal", "valueState", "systemState",
            "definePhase", "enterPhase", "validatePhase", "arm", "disarm",
            "isMotionAllowed", "validateMotorCommand", "defineWatchdog",
            "heartbeat", "checkWatchdogs", "configureFaultStore", "latchFault",
            "resetFault", "scanDirectMotorWrites", "introduce", "acquire",
            "preacquire", "identifyRuntimeType", "IsTwinOf", "siblingIntAppr",
            "differenceSkew", "deger", "report", "sifirla",
            "declareUnexpectedSigint", "flushPWM", "evreDegisti",
            "pwmSerbestMi", "onShutdown", "kilitDurumu",
        }
        self.assertEqual(set(), public_methods - tawnt_members)

    def test_sahte_surucu_ham_sayi_kabul_etmez(self):
        driver = fake_main.FakeMotorDriver()
        with self.assertRaises(TypeError):
            driver.apply_validated((40, 45))  # type: ignore[arg-type]
        self.assertEqual([], driver.history)

    def test_butun_demo_gecerli_komutu_yazar_gecersizi_reddeder(self):
        with tempfile.TemporaryDirectory() as temp:
            result = fake_main.run_demo(Path(temp), verbose=False)
            fault_data = json.loads(
                (Path(temp) / "fake_fault.json").read_text(encoding="utf-8")
            )

        self.assertEqual(57, result.legacy_value)
        self.assertTrue(result.offline_assumption_accepted)
        self.assertEqual(tawnt.SEALED, result.sealed_value_state)
        self.assertEqual((40.0, 45.0), result.valid_command)
        self.assertTrue(result.invalid_command_rejected)
        self.assertEqual(tawnt.LATCHED_FAULT, result.latched_state)
        self.assertEqual(tawnt.VALIDATING, result.reset_state)
        self.assertGreaterEqual(result.scanner_findings, 1)
        self.assertIn((40.0, 45.0), result.fake_motor_history)
        self.assertEqual(tawnt.BOOT, result.final_module_state)
        self.assertFalse(fault_data["active"])

    def test_main_acikca_sahte_oldugunu_soyler(self):
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = fake_main.main()

        text = output.getvalue()
        self.assertEqual(0, exit_code)
        self.assertIn("SAHTE EĞİTİM PROGRAMI", text)
        self.assertIn("GPIO VE GERÇEK MOTOR YOK", text)
        self.assertEqual(tawnt.BOOT, tawnt.systemState())


if __name__ == "__main__":
    unittest.main()
