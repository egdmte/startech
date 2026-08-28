"""STARTECH-ADAM: local warning and run-session coordination.

KERİM may request one autonomous run, but this module owns the countdown on the
vehicle.  The browser is only an operator surface: closing it does not shorten the
warning, and losing the authenticated car/server heartbeat prevents or stops output.

The serial notifier is a real hardware boundary for the Arduino firmware under
``firmware/adam``.  It has no silent or simulated fallback.  A remotely requested run
is rejected when the configured ADAM serial device cannot be opened and acknowledged.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import math
from pathlib import Path
import time
from typing import Any, Protocol

from .kayit import JsonlBlackBox, RecordKind


WARNING_SECONDS = 30
ADAM_BAUD_RATE = 115_200
ADAM_READY_LINE = "ADAM_READY"


class AdamError(RuntimeError):
    """Base error for a run warning or ADAM hardware failure."""


class AdamHardwareUnavailable(AdamError):
    """Raised when the real LED/buzzer controller cannot be reached."""


class AdamState(str, Enum):
    RUN_RECEIVED = "RUN_RECEIVED"
    RUN_INITIATED = "RUN_INITIATED"
    RUN_HALT_NOCON = "RUN_HALT_NOCON"
    RUN_CANCELLED = "RUN_CANCELLED"
    RUN_INTERRUPTED = "RUN_INTERRUPTED"
    RUN_COMPLETED = "RUN_COMPLETED"
    RUN_FAILED = "RUN_FAILED"


class RunControl(str, Enum):
    ACTIVE = "ACTIVE"
    CANCEL_REQUESTED = "CANCEL_REQUESTED"
    CONNECTION_LOST = "CONNECTION_LOST"


@dataclass(frozen=True)
class VehicleRunCommand:
    """One closed, short-lived request to start the existing ARDA drive path."""

    command_id: str
    operator: str
    issued_at: int
    countdown_seconds: int = WARNING_SECONDS
    mode: str = "LANE_FOLLOW"
    mute_buzzer: bool = False

    def __post_init__(self) -> None:
        if (
            not isinstance(self.command_id, str)
            or len(self.command_id) != 32
            or any(character not in "0123456789abcdef" for character in self.command_id)
        ):
            raise ValueError("vehicle run command id must be 32 lowercase hexadecimal characters")
        if (
            not isinstance(self.operator, str)
            or self.operator != self.operator.strip()
            or not 2 <= len(self.operator) <= 120
        ):
            raise ValueError("vehicle run operator must be a 2..120 character legal name")
        if isinstance(self.issued_at, bool) or not isinstance(self.issued_at, int):
            raise ValueError("vehicle run issue time must be an integer epoch")
        if self.countdown_seconds != WARNING_SECONDS:
            raise ValueError(f"vehicle run warning must last exactly {WARNING_SECONDS} seconds")
        if self.mode != "LANE_FOLLOW":
            raise ValueError("vehicle run mode is not supported")
        if not isinstance(self.mute_buzzer, bool):
            raise ValueError("mute_buzzer must be a boolean")


@dataclass(frozen=True)
class VehicleRunReceipt:
    """Software result for one remote run; it never claims physical movement."""

    command_id: str
    operator: str
    state: AdamState
    exit_code: int
    started_at_utc: str
    finished_at_utc: str
    log_file: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "command_id": self.command_id,
            "operator": self.operator,
            "state": self.state.value,
            "exit_code": self.exit_code,
            "started_at_utc": self.started_at_utc,
            "finished_at_utc": self.finished_at_utc,
            "log_file": self.log_file,
            "stop_requested": self.state
            in {
                AdamState.RUN_HALT_NOCON,
                AdamState.RUN_CANCELLED,
                AdamState.RUN_INTERRUPTED,
                AdamState.RUN_COMPLETED,
                AdamState.RUN_FAILED,
            },
            "physical_motion_observed": False,
        }


class AdamNotifier(Protocol):
    def notify(self, state: AdamState) -> None: ...

    def close(self) -> None: ...


SerialFactory = Callable[..., object]


class SerialAdamNotifier:
    """Real 115200-baud controller for the ADAM Arduino warning firmware."""

    def __init__(
        self,
        port: str,
        *,
        muted: bool = False,
        serial_factory: SerialFactory | None = None,
        reset_wait: Callable[[float], None] = time.sleep,
    ) -> None:
        if not isinstance(port, str) or not port.strip():
            raise AdamHardwareUnavailable("ADAM serial port is not configured")
        if serial_factory is None:
            try:
                from serial import Serial
            except ImportError as exc:
                raise AdamHardwareUnavailable(
                    "pyserial is required for the ADAM LED/buzzer controller"
                ) from exc
            serial_factory = Serial
        try:
            self._serial = serial_factory(
                port=port.strip(),
                baudrate=ADAM_BAUD_RATE,
                timeout=2.0,
                write_timeout=2.0,
            )
            reset_wait(2.0)
            reset_input = getattr(self._serial, "reset_input_buffer", None)
            if callable(reset_input):
                reset_input()
            self._write("PING")
            readline = getattr(self._serial, "readline", None)
            if not callable(readline):
                raise AdamHardwareUnavailable("ADAM serial device cannot return its identity")
            reply = readline()
            if not isinstance(reply, (bytes, bytearray)):
                raise AdamHardwareUnavailable("ADAM serial identity response is invalid")
            if bytes(reply).decode("ascii", errors="replace").strip() != ADAM_READY_LINE:
                raise AdamHardwareUnavailable("ADAM firmware did not acknowledge the connection")
            self._write("MUTE" if muted else "UNMUTE")
        except AdamHardwareUnavailable:
            self._close_quietly()
            raise
        except Exception as exc:
            self._close_quietly()
            raise AdamHardwareUnavailable(f"ADAM serial device could not open: {exc}") from exc

    def _write(self, command: str) -> None:
        write = getattr(self._serial, "write", None)
        flush = getattr(self._serial, "flush", None)
        if not callable(write) or not callable(flush):
            raise AdamHardwareUnavailable("ADAM serial device is not writable")
        encoded = (command + "\n").encode("ascii")
        written = write(encoded)
        if written is not None and written != len(encoded):
            raise AdamHardwareUnavailable("ADAM serial command was only partially written")
        flush()

    def notify(self, state: AdamState) -> None:
        if not isinstance(state, AdamState):
            raise TypeError("ADAM notification needs an AdamState")
        command = {
            AdamState.RUN_RECEIVED: "RUN_RECEIVED",
            AdamState.RUN_INITIATED: "RUN_INITIATED",
            AdamState.RUN_HALT_NOCON: "RUN_HALT_NOCON",
            AdamState.RUN_FAILED: "RUN_HALT_NOCON",
            AdamState.RUN_CANCELLED: "OFF",
            AdamState.RUN_INTERRUPTED: "OFF",
            AdamState.RUN_COMPLETED: "OFF",
        }[state]
        self._write(command)

    def _close_quietly(self) -> None:
        connection = getattr(self, "_serial", None)
        close = getattr(connection, "close", None)
        if callable(close):
            try:
                close()
            except Exception:
                pass

    def close(self) -> None:
        self._close_quietly()


RunHeartbeat = Callable[[JsonlBlackBox, bool], RunControl]
DriveRunner = Callable[[VehicleRunCommand, JsonlBlackBox, RunHeartbeat], int]
NotifierFactory = Callable[[str, bool], AdamNotifier]


def _utc_text(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat(timespec="milliseconds")


def _record_state(
    black_box: JsonlBlackBox,
    state: AdamState,
    command: VehicleRunCommand,
    **data: Any,
) -> None:
    black_box.append(
        RecordKind.STATE,
        "ADAM",
        {
            "state": state.value,
            "operator": command.operator,
            "mode": command.mode,
            **data,
        },
    )


def _default_notifier(port: str, muted: bool) -> AdamNotifier:
    return SerialAdamNotifier(port, muted=muted)


def _default_drive_runner(
    command: VehicleRunCommand,
    black_box: JsonlBlackBox,
    heartbeat: RunHeartbeat,
    *,
    profile_root: str | Path | None,
    usb_index: int,
    log_dir: Path,
) -> int:
    # Imported lazily because arac.main also exposes the YAREN CLI.
    from .main import StartupOptions, run_drive

    options = StartupOptions(
        action="drive",
        profile_root=None if profile_root is None else Path(profile_root),
        usb_index=usb_index,
        frames=0,
        preview=False,
        operator=command.operator,
        confirm_output=True,
        start="button",
        bench_left=0.0,
        bench_right=0.0,
        bench_seconds=0.5,
        log_dir=log_dir,
        color=True,
    )
    return run_drive(
        options,
        black_box=black_box,
        remote_start_authorized=True,
        link_control=lambda current: heartbeat(current, False),
    )


def execute_vehicle_run(
    command: VehicleRunCommand,
    *,
    heartbeat: RunHeartbeat,
    adam_port: str,
    profile_root: str | Path | None = None,
    usb_index: int = 0,
    log_dir: str | Path = Path("runs"),
    notifier_factory: NotifierFactory = _default_notifier,
    drive_runner: DriveRunner | None = None,
    clock: Callable[[], float] = time.monotonic,
    epoch: Callable[[], float] = time.time,
    sleep: Callable[[float], None] = time.sleep,
    status: Callable[[str], None] = lambda _message: None,
) -> VehicleRunReceipt:
    """Warn locally, maintain the KERİM lease and enter the existing ARDA path."""

    if not isinstance(command, VehicleRunCommand):
        raise TypeError("vehicle run executor needs VehicleRunCommand")
    if not callable(heartbeat):
        raise TypeError("vehicle run executor needs a heartbeat callback")
    selected_log_dir = Path(log_dir)
    selected_log_dir.mkdir(parents=True, exist_ok=True)
    log_path = selected_log_dir / f"vehicle-run-{command.command_id}.jsonl"
    black_box = JsonlBlackBox(log_path, command.command_id)
    notifier = notifier_factory(adam_port, command.mute_buzzer)
    started_epoch = epoch()
    final_state = AdamState.RUN_FAILED
    exit_code = 2

    def finish(state: AdamState, code: int) -> VehicleRunReceipt:
        nonlocal final_state, exit_code
        final_state = state
        exit_code = code
        return VehicleRunReceipt(
            command_id=command.command_id,
            operator=command.operator,
            state=state,
            exit_code=code,
            started_at_utc=_utc_text(started_epoch),
            finished_at_utc=_utc_text(epoch()),
            log_file=log_path.name,
        )

    def halt_for_connection_loss() -> VehicleRunReceipt:
        notifier.notify(AdamState.RUN_HALT_NOCON)
        _record_state(
            black_box,
            AdamState.RUN_HALT_NOCON,
            command,
            reason="KERİM heartbeat lost; local manual activation is required",
        )
        status(
            f"KERİM connection lost. Output is halted; use local ARDA activation. "
            f"Local log: {log_path}"
        )
        return finish(AdamState.RUN_HALT_NOCON, 3)

    try:
        notifier.notify(AdamState.RUN_RECEIVED)
        _record_state(
            black_box,
            AdamState.RUN_RECEIVED,
            command,
            countdown_seconds=command.countdown_seconds,
        )
        status(
            f"Run {command.command_id} received. ADAM started the local "
            f"{command.countdown_seconds}-second warning."
        )
        control = heartbeat(black_box, True)
        if control == RunControl.CONNECTION_LOST:
            return halt_for_connection_loss()
        if control == RunControl.CANCEL_REQUESTED:
            notifier.notify(AdamState.RUN_CANCELLED)
            _record_state(black_box, AdamState.RUN_CANCELLED, command, reason="cancelled before countdown")
            heartbeat(black_box, True)
            return finish(AdamState.RUN_CANCELLED, 4)

        deadline = clock() + command.countdown_seconds
        previous_remaining = command.countdown_seconds
        while True:
            remaining = max(0, int(math.ceil(deadline - clock())))
            if remaining <= 0:
                break
            sleep(min(1.0, max(0.0, deadline - clock())))
            remaining = max(0, int(math.ceil(deadline - clock())))
            if remaining != previous_remaining:
                black_box.append(
                    RecordKind.INFO,
                    "ADAM",
                    {
                        "state": AdamState.RUN_RECEIVED.value,
                        "countdown_remaining": remaining,
                    },
                )
                previous_remaining = remaining
            control = heartbeat(black_box, True)
            if control == RunControl.CONNECTION_LOST:
                return halt_for_connection_loss()
            if control == RunControl.CANCEL_REQUESTED:
                notifier.notify(AdamState.RUN_CANCELLED)
                _record_state(
                    black_box,
                    AdamState.RUN_CANCELLED,
                    command,
                    reason="operator cancelled during warning",
                )
                heartbeat(black_box, True)
                return finish(AdamState.RUN_CANCELLED, 4)

        notifier.notify(AdamState.RUN_INITIATED)
        _record_state(black_box, AdamState.RUN_INITIATED, command)
        control = heartbeat(black_box, True)
        if control == RunControl.CONNECTION_LOST:
            return halt_for_connection_loss()
        if control == RunControl.CANCEL_REQUESTED:
            notifier.notify(AdamState.RUN_CANCELLED)
            _record_state(black_box, AdamState.RUN_CANCELLED, command, reason="cancelled before ARDA start")
            heartbeat(black_box, True)
            return finish(AdamState.RUN_CANCELLED, 4)

        selected_runner = drive_runner
        if selected_runner is None:
            selected_runner = lambda requested, records, live_heartbeat: _default_drive_runner(
                requested,
                records,
                live_heartbeat,
                profile_root=profile_root,
                usb_index=usb_index,
                log_dir=selected_log_dir,
            )
        result = selected_runner(command, black_box, heartbeat)
        if result == 3:
            notifier.notify(AdamState.RUN_HALT_NOCON)
            return finish(AdamState.RUN_HALT_NOCON, result)
        if result == 4:
            notifier.notify(AdamState.RUN_CANCELLED)
            _record_state(black_box, AdamState.RUN_CANCELLED, command, reason="operator cancelled live run")
            heartbeat(black_box, True)
            return finish(AdamState.RUN_CANCELLED, result)
        if result == 130:
            notifier.notify(AdamState.RUN_INTERRUPTED)
            _record_state(black_box, AdamState.RUN_INTERRUPTED, command, reason="SIGINT or local operator interrupt")
            heartbeat(black_box, True)
            return finish(AdamState.RUN_INTERRUPTED, result)
        notifier.notify(AdamState.RUN_COMPLETED)
        _record_state(black_box, AdamState.RUN_COMPLETED, command, exit_code=result)
        heartbeat(black_box, True)
        return finish(AdamState.RUN_COMPLETED, result)
    except KeyboardInterrupt:
        notifier.notify(AdamState.RUN_INTERRUPTED)
        _record_state(black_box, AdamState.RUN_INTERRUPTED, command, reason="SIGINT")
        try:
            heartbeat(black_box, True)
        except Exception:
            pass
        raise
    except Exception as exc:
        try:
            notifier.notify(AdamState.RUN_FAILED)
            _record_state(
                black_box,
                AdamState.RUN_FAILED,
                command,
                error_type=type(exc).__name__,
                error=str(exc)[:500],
            )
            heartbeat(black_box, True)
        except Exception:
            pass
        raise
    finally:
        notifier.close()


__all__ = [
    "ADAM_BAUD_RATE",
    "ADAM_READY_LINE",
    "WARNING_SECONDS",
    "AdamError",
    "AdamHardwareUnavailable",
    "AdamNotifier",
    "AdamState",
    "RunControl",
    "SerialAdamNotifier",
    "VehicleRunCommand",
    "VehicleRunReceipt",
    "execute_vehicle_run",
]
