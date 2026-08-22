"""Behavior tests for the hardware-free STARTECH-ARDA CLI scaffold."""

from __future__ import annotations

import io
import unittest
from unittest.mock import patch

from arac import durum, goruntu, goz, kayit, main, surucu


class ArdaCliTest(unittest.TestCase):
    def run_cli(self, arguments, input_fn=lambda _: ""):
        output = io.StringIO()
        exit_code = main.run(arguments, input_fn=input_fn, output=output)
        return exit_code, output.getvalue()

    def test_module_identities_match_the_agreed_names(self):
        identities = {
            durum: ("STARTECH-DORA (SARA)", "Durum Okuma ve Raporlama"),
            goruntu: ("STARTECH-KEREM (CORA)", "Camera Object Recognition Agent"),
            goz: ("STARTECH-KASIM (CAMILA)", "Camera Acquisition and Monitoring"),
            kayit: ("STARTECH-KADER (BLAIR)", "Black-box Logging"),
            main: ("STARTECH-ARDA (ADAM)", "Autonomous Driving Analysis Module"),
            surucu: ("STARTECH-OSMAN (MATT)", "Motor Actuation and Transfer Terminal"),
        }

        for module, expected_parts in identities.items():
            with self.subTest(module=module.__name__):
                self.assertIsNotNone(module.__doc__)
                for expected in expected_parts:
                    self.assertIn(expected, module.__doc__)

    def test_english_simulation_renders_truthful_state(self):
        exit_code, output = self.run_cli(
            ["--mode", "simulation", "--language", "en", "--no-color"]
        )

        self.assertEqual(main.EXIT_OK, exit_code)
        self.assertIn("STARTECH // ARDA (ADAM)", output)
        self.assertIn("STARTUP STATE", output)
        self.assertIn("[SIMULATED]", output)
        self.assertIn("[BLOCKED", output)
        self.assertIn("Bounded self-check passed", output)
        self.assertIn("No continuous driving loop was started", output)

    def test_turkish_is_the_default_language(self):
        exit_code, output = self.run_cli(["--no-color"])

        self.assertEqual(main.EXIT_OK, exit_code)
        self.assertIn("BAŞLANGIÇ DURUMU", output)
        self.assertIn("Sınırlı öz denetim geçti", output)
        self.assertIn("ARDA simülasyon sözleşmeleri hazır", output)

    def test_auto_skips_prompt_but_does_not_claim_arming(self):
        def unexpected_input(_prompt):
            self.fail("--auto must not request terminal input")

        exit_code, output = self.run_cli(
            ["--auto", "--language", "en", "--no-color"],
            input_fn=unexpected_input,
        )

        self.assertEqual(main.EXIT_OK, exit_code)
        self.assertIn("Automatic vehicle arming remains impossible", output)
        self.assertNotIn("ARMED", output)

    def test_vehicle_mode_fails_closed_even_with_auto(self):
        def unexpected_input(_prompt):
            self.fail("refused vehicle mode must not request input")

        exit_code, output = self.run_cli(
            [
                "--mode",
                "vehicle",
                "--auto",
                "--language",
                "en",
                "--no-color",
            ],
            input_fn=unexpected_input,
        )

        self.assertEqual(main.EXIT_NOT_READY, exit_code)
        self.assertIn("VEHICLE", output)
        self.assertIn("NOT CONNECTED", output)
        self.assertIn("Vehicle mode refused", output)
        self.assertIn("No physical motor command", output)

    def test_vehicle_mode_never_runs_the_simulation_probe(self):
        with patch(
            "arac.main.run_simulation_probe",
            side_effect=AssertionError("vehicle mode must refuse before probing"),
        ):
            exit_code, _output = self.run_cli(
                ["--mode", "vehicle", "--auto", "--no-color"]
            )

        self.assertEqual(main.EXIT_NOT_READY, exit_code)

    def test_real_camera_check_is_explicit_and_reports_metadata(self):
        result = goz.CameraProbeResult(
            source="usb:0",
            frame_count=3,
            width=640,
            height=480,
            elapsed_seconds=0.125,
        )
        with patch("arac.main.run_camera_diagnostic", return_value=result) as probe:
            exit_code, output = self.run_cli(
                [
                    "--auto",
                    "--check-camera",
                    "--camera-frames",
                    "3",
                    "--language",
                    "en",
                    "--no-color",
                ]
            )

        self.assertEqual(main.EXIT_OK, exit_code)
        probe.assert_called_once()
        self.assertIn("Checking USB camera 0 first", output)
        self.assertIn("source=usb:0", output)
        self.assertIn("resolution=640x480", output)

    def test_camera_check_failure_stops_before_simulation_probe(self):
        with (
            patch(
                "arac.main.run_camera_diagnostic",
                side_effect=goz.CameraUnavailable("USB and Pi unavailable"),
            ),
            patch(
                "arac.main.run_simulation_probe",
                side_effect=AssertionError("self-check must not follow camera failure"),
            ),
        ):
            exit_code, output = self.run_cli(
                ["--auto", "--check-camera", "--language", "en", "--no-color"]
            )

        self.assertEqual(main.EXIT_NOT_READY, exit_code)
        self.assertIn("Camera check failed closed", output)
        self.assertIn("USB and Pi unavailable", output)

    def test_bounded_probe_exercises_only_simulated_boundaries(self):
        result = main.run_simulation_probe()

        self.assertEqual(durum.VehicleState.READY, result.final_state)
        self.assertTrue(result.observation_valid)
        self.assertEqual(3, result.record_count)
        self.assertEqual("BLOCKED", result.motor_state)
        self.assertGreaterEqual(result.stop_request_count, 1)

    def test_probe_failure_is_reported_and_fails_closed(self):
        with patch(
            "arac.main.run_simulation_probe",
            side_effect=RuntimeError("deliberate test failure"),
        ):
            exit_code, output = self.run_cli(
                ["--auto", "--language", "en", "--no-color"]
            )

        self.assertEqual(main.EXIT_NOT_READY, exit_code)
        self.assertIn("Simulation self-check failed closed", output)
        self.assertIn("deliberate test failure", output)

    def test_keyboard_interrupt_exits_without_starting(self):
        def interrupt(_prompt):
            raise KeyboardInterrupt

        exit_code, output = self.run_cli(
            ["--language", "en", "--no-color"], input_fn=interrupt
        )

        self.assertEqual(main.EXIT_INTERRUPTED, exit_code)
        self.assertIn("no hardware action was taken", output)
        self.assertNotIn("simulation scaffold is ready", output)

    def test_missing_confirmation_input_fails_closed(self):
        def end_of_input(_prompt):
            raise EOFError

        exit_code, output = self.run_cli(
            ["--language", "en", "--no-color"], input_fn=end_of_input
        )

        self.assertEqual(main.EXIT_NOT_READY, exit_code)
        self.assertIn("confirmation input was unavailable", output)
        self.assertNotIn("simulation scaffold is ready", output)

    def test_argument_parser_defaults_to_safe_simulation(self):
        options = main.parse_options([])

        self.assertEqual(main.SIMULATION, options.mode)
        self.assertEqual("tr", options.language)
        self.assertFalse(options.automatic)
        self.assertFalse(options.check_camera)
        self.assertEqual(0, options.usb_index)
        self.assertEqual(3, options.camera_frames)


if __name__ == "__main__":
    unittest.main(verbosity=2)
