"""Software contracts for ADAM's real serial and vehicle-run coordination paths."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from arac.adam import (
    AdamHardwareUnavailable,
    AdamState,
    RunControl,
    SerialAdamNotifier,
    VehicleRunCommand,
    execute_vehicle_run,
)
from arac.kayit import JsonlBlackBox


class FakeSerial:
    def __init__(self, **_kwargs) -> None:
        self.writes: list[bytes] = []
        self.closed = False

    def reset_input_buffer(self) -> None:
        return None

    def write(self, value: bytes) -> int:
        self.writes.append(value)
        return len(value)

    def flush(self) -> None:
        return None

    def readline(self) -> bytes:
        return b"ADAM_READY\n"

    def close(self) -> None:
        self.closed = True


class RecordingNotifier:
    def __init__(self) -> None:
        self.states: list[AdamState] = []
        self.closed = False

    def notify(self, state: AdamState) -> None:
        self.states.append(state)

    def close(self) -> None:
        self.closed = True


class AdvancingClock:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        return self.value

    def sleep(self, seconds: float) -> None:
        self.value += seconds


class AdamTest(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def command(self, **changes) -> VehicleRunCommand:
        values = {
            "command_id": "a" * 32,
            "operator": "Ada Lovelace",
            "issued_at": 1_800_000_000,
            "countdown_seconds": 30,
            "mode": "LANE_FOLLOW",
            "mute_buzzer": False,
        }
        values.update(changes)
        return VehicleRunCommand(**values)

    def test_serial_notifier_requires_firmware_identity_and_sends_named_states(self):
        opened: list[FakeSerial] = []

        def factory(**kwargs):
            self.assertEqual("COM7", kwargs["port"])
            serial = FakeSerial(**kwargs)
            opened.append(serial)
            return serial

        notifier = SerialAdamNotifier(
            "COM7",
            muted=True,
            serial_factory=factory,
            reset_wait=lambda _seconds: None,
        )
        notifier.notify(AdamState.RUN_RECEIVED)
        notifier.notify(AdamState.RUN_INITIATED)
        notifier.notify(AdamState.RUN_HALT_NOCON)
        notifier.close()

        self.assertEqual(
            [
                b"PING\n",
                b"MUTE\n",
                b"RUN_RECEIVED\n",
                b"RUN_INITIATED\n",
                b"RUN_HALT_NOCON\n",
            ],
            opened[0].writes,
        )
        self.assertTrue(opened[0].closed)

    def test_serial_notifier_has_no_silent_hardware_fallback(self):
        class WrongFirmware(FakeSerial):
            def readline(self) -> bytes:
                return b"SOMETHING_ELSE\n"

        with self.assertRaisesRegex(AdamHardwareUnavailable, "did not acknowledge"):
            SerialAdamNotifier(
                "COM7",
                serial_factory=lambda **kwargs: WrongFirmware(**kwargs),
                reset_wait=lambda _seconds: None,
            )

    def test_local_countdown_survives_without_a_browser_and_then_runs_arda(self):
        clock = AdvancingClock()
        notifier = RecordingNotifier()
        heartbeat_calls: list[tuple[int, bool]] = []
        drive_calls: list[str] = []

        def heartbeat(black_box: JsonlBlackBox, force: bool) -> RunControl:
            heartbeat_calls.append((len(black_box.records), force))
            return RunControl.ACTIVE

        def drive(command, black_box, live_heartbeat):
            drive_calls.append(command.command_id)
            self.assertEqual(RunControl.ACTIVE, live_heartbeat(black_box, False))
            return 0

        receipt = execute_vehicle_run(
            self.command(),
            heartbeat=heartbeat,
            adam_port="COM7",
            log_dir=self.root,
            notifier_factory=lambda _port, _muted: notifier,
            drive_runner=drive,
            clock=clock,
            sleep=clock.sleep,
            epoch=lambda: 1_800_000_000 + clock.value,
        )

        self.assertEqual(30.0, clock.value)
        self.assertEqual(["a" * 32], drive_calls)
        self.assertEqual(
            [
                AdamState.RUN_RECEIVED,
                AdamState.RUN_INITIATED,
                AdamState.RUN_COMPLETED,
            ],
            notifier.states,
        )
        self.assertEqual(AdamState.RUN_COMPLETED, receipt.state)
        self.assertTrue(notifier.closed)
        records = JsonlBlackBox(self.root / receipt.log_file, "a" * 32).records
        states = [record.data.get("state") for record in records if record.module == "ADAM"]
        self.assertIn(AdamState.RUN_RECEIVED.value, states)
        self.assertIn(AdamState.RUN_INITIATED.value, states)
        self.assertIn(AdamState.RUN_COMPLETED.value, states)
        self.assertGreaterEqual(len(heartbeat_calls), 32)

    def test_connection_loss_during_warning_halts_before_arda(self):
        clock = AdvancingClock()
        notifier = RecordingNotifier()
        calls = [RunControl.ACTIVE, RunControl.CONNECTION_LOST]

        receipt = execute_vehicle_run(
            self.command(),
            heartbeat=lambda _box, _force: calls.pop(0),
            adam_port="COM7",
            log_dir=self.root,
            notifier_factory=lambda _port, _muted: notifier,
            drive_runner=lambda *_args: self.fail("ARDA must not start"),
            clock=clock,
            sleep=clock.sleep,
            epoch=lambda: 1_800_000_000 + clock.value,
        )

        self.assertEqual(AdamState.RUN_HALT_NOCON, receipt.state)
        self.assertEqual(3, receipt.exit_code)
        self.assertEqual(
            [AdamState.RUN_RECEIVED, AdamState.RUN_HALT_NOCON],
            notifier.states,
        )

    def test_operator_can_cancel_during_the_vehicle_owned_warning(self):
        clock = AdvancingClock()
        notifier = RecordingNotifier()
        calls = [RunControl.ACTIVE, RunControl.CANCEL_REQUESTED, RunControl.ACTIVE]
        receipt = execute_vehicle_run(
            self.command(),
            heartbeat=lambda _box, _force: calls.pop(0),
            adam_port="COM7",
            log_dir=self.root,
            notifier_factory=lambda _port, _muted: notifier,
            drive_runner=lambda *_args: self.fail("ARDA must not start"),
            clock=clock,
            sleep=clock.sleep,
            epoch=lambda: 1_800_000_000 + clock.value,
        )
        self.assertEqual(AdamState.RUN_CANCELLED, receipt.state)
        self.assertEqual(4, receipt.exit_code)


if __name__ == "__main__":
    unittest.main(verbosity=2)
