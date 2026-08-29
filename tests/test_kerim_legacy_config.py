from __future__ import annotations

import ast
import copy
from pathlib import Path
import unittest

from startech_cam.legacy_config import LegacyConfigError, generate_legacy_config
from startech_cam.repository import parse_document_text, refresh_calibration_stamp
from startech_cam.routes import _sync_perspective_for_camera


ROOT = Path(__file__).resolve().parent.parent
DOCUMENT_PATH = (
    ROOT / "arac" / "config" / "examples" / "yapilandirma-v2.ornek.json"
)
CONFIG_PATH = ROOT / "LEGACY" / "config.py"


def assigned_literals(source: str) -> dict[str, object]:
    result: dict[str, object] = {}
    for node in ast.parse(source).body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
        ):
            try:
                result[node.targets[0].id] = ast.literal_eval(node.value)
            except (TypeError, ValueError):
                pass
    return result


class KerimLegacyConfigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.template = CONFIG_PATH.read_text(encoding="utf-8")
        cls.document = parse_document_text(DOCUMENT_PATH.read_text(encoding="utf-8"))

    def test_generates_values_consumed_by_legacy(self) -> None:
        generated = generate_legacy_config(
            self.template, self.document, profile_tag="c7a2ee"
        )
        values = assigned_literals(generated)
        self.assertEqual(values["WIDTH"], 840)
        self.assertEqual(values["HEIGHT"], 630)
        self.assertEqual(values["PERSP_SRC"][3], [840, 630])
        self.assertEqual(values["KP"], 0.58)
        self.assertEqual(values["MAX_SPEED"], 57)
        self.assertEqual(values["GREEN_HSV_LOW"], (45, 90, 80))

    def test_preserves_gpio_and_unmapped_canon_values(self) -> None:
        before = assigned_literals(self.template)
        after = assigned_literals(generate_legacy_config(self.template, self.document))
        for name in (
            "RIGHT_IN1",
            "RIGHT_IN2",
            "LEFT_IN1",
            "LEFT_IN2",
            "LEFT_PWM_PIN",
            "RIGHT_PWM_PIN",
            "START_BUTTON_PIN",
            "LOG_DURATION_SEC",
            "CROSSWALK_WAIT_SEC",
        ):
            self.assertEqual(after[name], before[name], name)

    def test_rejects_signal_area_that_canon_cannot_represent(self) -> None:
        document = copy.deepcopy(self.document)
        document["kalibrasyon"]["renkler"]["yesil_isik"]["min_alan"] = 301
        refresh_calibration_stamp(document)
        with self.assertRaisesRegex(LegacyConfigError, "one SIGNAL_MIN_AREA"):
            generate_legacy_config(self.template, document)

    def test_rejects_template_missing_a_mapped_constant(self) -> None:
        template = self.template.replace("WIDTH  = 800", "REMOVED_WIDTH = 800", 1)
        with self.assertRaisesRegex(LegacyConfigError, "WIDTH"):
            generate_legacy_config(template, self.document)

    def test_camera_resize_updates_perspective_as_one_edit(self) -> None:
        updated = copy.deepcopy(self.document)
        updated["kalibrasyon"]["kamera"]["genislik"] = 640
        updated["kalibrasyon"]["kamera"]["yukseklik"] = 480
        changed = _sync_perspective_for_camera(updated, self.document)
        self.assertTrue(changed)
        perspective = updated["kalibrasyon"]["perspektif"]
        self.assertEqual(perspective["olculen_cozunurluk"], [640, 480])
        self.assertEqual(perspective["kaynak_noktalar"][3], [640, 480])
        refresh_calibration_stamp(updated)
        generate_legacy_config(self.template, updated)


if __name__ == "__main__":
    unittest.main()
