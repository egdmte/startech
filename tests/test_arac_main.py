"""End-to-end contract proof for ARDA's actual vehicle paths."""

from __future__ import annotations

from io import StringIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import tawnt
from arac import ayar, durum, goruntu, goz, kayit, main, surucu
from arac.ayar import ActiveConfiguration
from arac.goruntu import LaneObservation
from arac.goz import CameraStatus, FramePacket
from arac.kayit import RecordKind


def active_configuration() -> ActiveConfiguration:
    calibration = {
        "kamera": {
            "genislik": 320,
            "yukseklik": 240,
            "bgr_cikis": False,
            "dondur_180": False,
        },
        "motor": {
            "olculdu": None,
            "sol_trim_dusuk": 1.0,
            "sol_trim_yuksek": 1.0,
            "sag_trim_dusuk": 1.0,
            "sag_trim_yuksek": 1.0,
            "olu_bolge_min_pwm": 30,
            "olu_bolge_yuzde": 20,
        },
    }
    settings = {
        "kontrol": {
            "kp": 0.5,
            "kd": 0.2,
            "ki": 0.0,
            "integral_max": 50,
            "deriv_cap": 150,
        },
        "hiz": {"hedef": 50, "min": 25, "max": 57, "k_speed": 0.45},
    }
    return ActiveConfiguration(
        profile_id="a" * 32,
        name="school car",
        calibration_sha256="b" * 64,
        settings_sha256="c" * 64,
        warning_digest="d" * 64,
        warnings=(),
        calibration=calibration,
        settings=settings,
    )


def lane_result(frame_id: int, *, valid: bool = True) -> LaneObservation:
    return LaneObservation(
        frame_id=frame_id,
        captured_at=float(frame_id + 1),
        valid=valid,
        error_px=0.0 if valid else None,
        normalized_error=0.0 if valid else None,
        confidence=0.9 if valid else 0.0,
        lane_center_px=160 if valid else None,
        left_lane_px=70 if valid else None,
        right_lane_px=250 if valid else None,
        brightness=120,
        reason="" if valid else "no lane signal",
    )


class StubCamera:
    def __init__(self, count: int = 10):
        self.count = count
        self.next_id = 0
        self.opened = False
        self.closed = False

    @property
    def status(self):
        return CameraStatus.STREAMING if self.opened else CameraStatus.DISCONNECTED

    def open(self):
        self.opened = True

    def read_frame(self):
        if self.next_id >= self.count:
            raise RuntimeError("camera exhausted")
        frame = FramePacket(
            self.next_id,
            float(self.next_id + 1),
            object(),
            source="live-camera",
        )
        self.next_id += 1
        return frame

    def close(self):
        self.closed = True
        self.opened = False


class StubAnalyzer:
    def __init__(self, *, fail_at: int | None = None):
        self.fail_at = fail_at
        self.calls = []

    def analyze(self, frame):
        self.calls.append(frame.frame_id)
        if frame.frame_id == self.fail_at:
            raise RuntimeError("vision failed")
        return lane_result(frame.frame_id)


class RecordingDriver:
    def __init__(self, events=None):
        self.events = events if events is not None else []
        self.applied = []
        self.closed = False

    def apply(self, request):
        self.applied.append(request)
        self.events.append(("apply", request.request.frame_id))

    def stop(self, reason="stop"):
        self.events.append(("stop", reason))

    def close(self):
        self.closed = True
        self.events.append(("close", None))


class ArdaTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.temp = Path(temporary.name)
        tawnt.sifirla()

    def tearDown(self):
        tawnt.sifirla()

    def options(self, action: str, **changes) -> main.StartupOptions:
        values = {
            "action": action,
            "profile_root": None,
            "usb_index": 0,
            "frames": 2,
            "preview": False,
            "operator": None,
            "confirm_output": False,
            "start": "enter",
            "bench_left": 0.0,
            "bench_right": 0.0,
            "bench_seconds": 0.1,
            "log_dir": self.temp / "runs",
            "color": False,
        }
        values.update(changes)
        return main.StartupOptions(**values)

    def test_module_identities_remain_the_agreed_names(self):
        expected = {
            main: "STARTECH-ARDA",
            ayar: "STARTECH-YAREN",
            durum: "STARTECH-DORA",
            goz: "STARTECH-KASIM",
            goruntu: "STARTECH-KEREM",
            kayit: "STARTECH-KADER",
            surucu: "STARTECH-OSMAN",
        }
        for module, identity in expected.items():
            with self.subTest(module=module.__name__):
                self.assertIn(identity, module.__doc__)

    def test_cli_defaults_to_real_arda_menu_not_simulation(self):
        options = main.parse_options([])
        self.assertEqual("interactive", options.action)
        self.assertFalse(hasattr(main, "SIMULATION"))

    def test_physical_actions_require_one_name_and_confirmation(self):
        for arguments in (["--drive"], ["--bench", "--operator", "Ada Lovelace"]):
            with self.subTest(arguments=arguments), self.assertRaises(SystemExit):
                main.parse_options(arguments)

        options = main.parse_options([
            "--drive", "--operator", "Ada Lovelace", "--confirm-output",
        ])
        self.assertEqual("Ada Lovelace", options.operator)

    def test_observation_uses_live_frames_and_never_constructs_a_driver(self):
        camera = StubCamera(2)
        analyzer = StubAnalyzer()
        output = StringIO()
        options = self.options("observe")
        with patch("arac.main.GpioZeroMotorDriver", side_effect=AssertionError("motor")):
            result = main.run_observation(
                options,
                configuration=active_configuration(),
                camera=camera,
                analyzer=analyzer,
                output=output,
            )

        self.assertEqual(main.EXIT_OK, result)
        self.assertEqual([0, 1], analyzer.calls)
        self.assertTrue(camera.closed)
        self.assertIn("confidence=0.90", output.getvalue())

    def test_live_drive_reaches_validated_driver_and_writes_full_loop_log(self):
        camera = StubCamera(3)  # one preflight frame + two controlled frames
        analyzer = StubAnalyzer()
        driver = RecordingDriver()
        options = self.options(
            "drive", operator="Ada Lovelace", confirm_output=True
        )
        result = main.run_drive(
            options,
            configuration=active_configuration(),
            camera=camera,
            analyzer=analyzer,
            driver=driver,
            input_fn=lambda _prompt: "",
            output=StringIO(),
        )

        self.assertEqual(main.EXIT_OK, result)
        self.assertEqual(2, len(driver.applied))
        self.assertTrue(all(
            isinstance(item, surucu.ValidatedDriveRequest) for item in driver.applied
        ))
        self.assertTrue(driver.closed)
        log_path = next(options.log_dir.glob("drive-*.jsonl"))
        records = kayit.JsonlBlackBox(log_path, log_path.stem).records
        kinds = [record.kind for record in records]
        self.assertEqual(2, kinds.count(RecordKind.OBSERVATION))
        self.assertEqual(2, kinds.count(RecordKind.MOTOR_ACCEPTED))

    def test_drive_stops_physically_before_fault_is_logged(self):
        events = []
        driver = RecordingDriver(events)
        options = self.options(
            "drive", operator="Ada Lovelace", confirm_output=True
        )

        def log_event(_box, kind, _module, _data, **_kwargs):
            events.append(("log", kind))

        with patch("arac.main._log", side_effect=log_event):
            with self.assertRaisesRegex(RuntimeError, "vision failed"):
                main.run_drive(
                    options,
                    configuration=active_configuration(),
                    camera=StubCamera(3),
                    analyzer=StubAnalyzer(fail_at=1),
                    driver=driver,
                    input_fn=lambda _prompt: "",
                    output=StringIO(),
                )

        fault_stop = next(
            index for index, event in enumerate(events)
            if event[0] == "stop" and "drive fault" in event[1]
        )
        fault_log = next(
            index for index, event in enumerate(events)
            if event == ("log", RecordKind.FAULT)
        )
        self.assertLess(fault_stop, fault_log)

    def test_lost_lane_sends_zero_through_tawnt_and_driver(self):
        class LostAnalyzer(StubAnalyzer):
            def analyze(self, frame):
                self.calls.append(frame.frame_id)
                return lane_result(frame.frame_id, valid=frame.frame_id == 0)

        driver = RecordingDriver()
        options = self.options(
            "drive", frames=1, operator="Ada Lovelace", confirm_output=True
        )
        main.run_drive(
            options,
            configuration=active_configuration(),
            camera=StubCamera(2),
            analyzer=LostAnalyzer(),
            driver=driver,
            input_fn=lambda _prompt: "",
            output=StringIO(),
        )
        command = driver.applied[0].command
        self.assertEqual((0.0, 0.0), (command.left, command.right))

    def test_bench_is_real_bounded_output_even_with_unmeasured_trim(self):
        driver = RecordingDriver()
        options = self.options(
            "bench",
            operator="Ada Lovelace",
            confirm_output=True,
            bench_left=20,
            bench_right=-15,
            bench_seconds=0.05,
        )

        class Clock:
            def __init__(self):
                self.value = 0.0

            def __call__(self):
                self.value += 0.02
                return self.value

        result = main.run_bench(
            options,
            configuration=active_configuration(),
            driver=driver,
            clock=Clock(),
            sleep=lambda _seconds: None,
        )
        self.assertEqual(main.EXIT_OK, result)
        self.assertEqual((0.2, -0.15), (
            driver.applied[0].command.left, driver.applied[0].command.right,
        ))
        self.assertTrue(driver.closed)

    def test_direct_run_cannot_bypass_output_confirmation(self):
        with self.assertRaisesRegex(ValueError, "confirmation"):
            main.run_drive(
                self.options("drive", operator="Ada"),
                configuration=active_configuration(),
                camera=StubCamera(),
                analyzer=StubAnalyzer(),
                driver=RecordingDriver(),
            )

    def test_interactive_menu_keeps_yaren_cam_gateway(self):
        options = self.options("interactive")
        with patch("arac.main.run_configuration_menu", return_value=7) as gateway:
            result = main.run(options, input_fn=lambda _prompt: "4", output=StringIO())
        self.assertEqual(7, result)
        gateway.assert_called_once()

    def test_yaren_delegation_preserves_full_interactive_gateway(self):
        options = self.options("yaren", profile_root=self.temp / "profiles")
        with patch("arac.main.run_yaren_cli", return_value=0) as yaren:
            result = main.run_configuration_menu(options, output=StringIO())
        self.assertEqual(0, result)
        arguments = yaren.call_args.args[0]
        self.assertEqual([
            "--root", str(self.temp / "profiles"), "interactive"
        ], arguments)


if __name__ == "__main__":
    unittest.main(verbosity=2)
