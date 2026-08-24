"""Real, bounded workshop motor execution shared by ARDA and CAM SAC."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
import math
from pathlib import Path
import time
from typing import Any

import tawnt

from .ayar import ActiveConfiguration, load_active_configuration
from .kayit import JsonlBlackBox, RecordKind
from .surucu import (
    GpioZeroMotorDriver,
    MotorDriver,
    MotorRequest,
    OutputWatchdog,
    validate_request,
)


WORKSHOP_PHASE = "BENCH_OUTPUT"
MAXIMUM_OUTPUT_PERCENT = 35.0
MINIMUM_DURATION_SECONDS = 0.05
MAXIMUM_DURATION_SECONDS = 3.0
COMMAND_SOURCES = frozenset({"ARDA_CLI", "CAM_SAC"})


def _finite_number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")
    converted = float(value)
    if not math.isfinite(converted):
        raise ValueError(f"{name} must be finite")
    return converted


@dataclass(frozen=True)
class WorkshopCommand:
    """One explicit physical-output request with no open-ended control channel."""

    command_id: str
    operator: str
    left_percent: float
    right_percent: float
    duration_seconds: float
    source: str
    cam_issued_at: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.command_id, str) or not 1 <= len(self.command_id) <= 80:
            raise ValueError("workshop command id must contain 1..80 characters")
        if (
            not isinstance(self.operator, str)
            or self.operator != self.operator.strip()
            or not 2 <= len(self.operator) <= 120
        ):
            raise ValueError("workshop operator must be a 2..120 character legal name")
        if self.source not in COMMAND_SOURCES:
            raise ValueError("workshop command source is not allowed")
        left = _finite_number(self.left_percent, "left percent")
        right = _finite_number(self.right_percent, "right percent")
        duration = _finite_number(self.duration_seconds, "duration")
        if abs(left) > MAXIMUM_OUTPUT_PERCENT or abs(right) > MAXIMUM_OUTPUT_PERCENT:
            raise ValueError("workshop output is limited to -35..35 percent")
        if not MINIMUM_DURATION_SECONDS <= duration <= MAXIMUM_DURATION_SECONDS:
            raise ValueError("workshop duration is limited to 0.05..3 seconds")
        if self.cam_issued_at is not None and (
            isinstance(self.cam_issued_at, bool) or not isinstance(self.cam_issued_at, int)
        ):
            raise ValueError("CAM issue time must be an integer epoch")
        object.__setattr__(self, "left_percent", left)
        object.__setattr__(self, "right_percent", right)
        object.__setattr__(self, "duration_seconds", duration)


@dataclass(frozen=True)
class WorkshopReceipt:
    """Software evidence returned only after the bounded execution has ended."""

    command_id: str
    operator: str
    source: str
    profile_id: str
    requested_left_percent: float
    requested_right_percent: float
    applied_left: float
    applied_right: float
    duration_seconds: float
    started_at_utc: str
    finished_at_utc: str
    stop_requested: bool
    run_id: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "command_id": self.command_id,
            "operator": self.operator,
            "source": self.source,
            "profile_id": self.profile_id,
            "requested_left_percent": self.requested_left_percent,
            "requested_right_percent": self.requested_right_percent,
            "applied_left": self.applied_left,
            "applied_right": self.applied_right,
            "duration_seconds": self.duration_seconds,
            "started_at_utc": self.started_at_utc,
            "finished_at_utc": self.finished_at_utc,
            "stop_requested": self.stop_requested,
            "run_id": self.run_id,
            "physical_motion_observed": False,
        }


def _utc_text(moment: datetime) -> str:
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).isoformat(timespec="milliseconds")


def execute_workshop_command(
    command: WorkshopCommand,
    *,
    profile_root: str | Path | None = None,
    configuration: ActiveConfiguration | None = None,
    driver: MotorDriver | None = None,
    log_dir: Path = Path("runs"),
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    utc_now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
) -> WorkshopReceipt:
    """Execute one real workshop command through TAWNT and the GPIO driver."""

    if not isinstance(command, WorkshopCommand):
        raise TypeError("workshop executor requires WorkshopCommand")
    configuration = configuration or load_active_configuration(profile_root)
    selected_driver = driver or GpioZeroMotorDriver(configuration.calibration["motor"])
    log_dir.mkdir(parents=True, exist_ok=True)
    stamp = utc_now().strftime("%Y%m%d-%H%M%S")
    run_id = f"workshop-{stamp}-{command.command_id[:12]}"
    black_box = JsonlBlackBox(log_dir / f"{run_id}.jsonl", run_id)
    watchdog = OutputWatchdog(selected_driver)
    armed = False
    started_at = ""
    finished_at = ""
    applied_left = 0.0
    applied_right = 0.0
    try:
        selected_driver.stop("workshop pre-start electrical stop")
        tawnt.sifirla()
        tawnt.onShutdown(lambda: selected_driver.stop("TAWNT zero callback"))
        tawnt.defineWatchdog("control", timeout_seconds=0.5)
        tawnt.heartbeat("control")
        tawnt.definePhase(
            WORKSHOP_PHASE,
            motion_allowed=True,
            allow_reverse=True,
            allow_pivot=True,
            max_pwm=MAXIMUM_OUTPUT_PERCENT / 100.0,
            max_difference=(MAXIMUM_OUTPUT_PERCENT * 2) / 100.0,
            required_watchdogs=("control",),
        )
        tawnt.validateBeforeStart(profile=tawnt.BENCH)
        tawnt.enterPhase(WORKSHOP_PHASE)
        tawnt.arm(
            command.operator,
            live_hardware_authorized=False,
            final_confirmation=False,
        )
        armed = True
        watchdog.start()
        request = MotorRequest(
            command.left_percent / 100.0,
            command.right_percent / 100.0,
            WORKSHOP_PHASE,
            f"bounded workshop command {command.command_id}",
        )
        validated = validate_request(request)
        started_at = _utc_text(utc_now())
        final_command = selected_driver.apply(validated) or validated.command
        applied_left = final_command.left
        applied_right = final_command.right
        black_box.append(
            RecordKind.MOTOR_ACCEPTED,
            "OSMAN",
            {
                "command_id": command.command_id,
                "source": command.source,
                "operator": command.operator,
                "cam_issued_at": command.cam_issued_at,
                "requested_left_percent": command.left_percent,
                "requested_right_percent": command.right_percent,
                "applied_left": applied_left,
                "applied_right": applied_right,
                "seconds": command.duration_seconds,
            },
        )
        deadline = clock() + command.duration_seconds
        while clock() < deadline:
            tawnt.heartbeat("control")
            watchdog.touch()
            sleep(min(0.05, max(0.0, deadline - clock())))
    except Exception as exc:
        selected_driver.stop(f"workshop fault: {type(exc).__name__}")
        try:
            black_box.append(
                RecordKind.FAULT,
                "ARDA",
                {
                    "command_id": command.command_id,
                    "type": type(exc).__name__,
                    "message": str(exc),
                },
            )
        except Exception:
            pass
        raise
    finally:
        watchdog.close()
        selected_driver.stop("workshop duration ended")
        finished_at = _utc_text(utc_now())
        if armed:
            tawnt.disarm("workshop duration ended")
        selected_driver.close()
    return WorkshopReceipt(
        command_id=command.command_id,
        operator=command.operator,
        source=command.source,
        profile_id=configuration.profile_id,
        requested_left_percent=command.left_percent,
        requested_right_percent=command.right_percent,
        applied_left=applied_left,
        applied_right=applied_right,
        duration_seconds=command.duration_seconds,
        started_at_utc=started_at,
        finished_at_utc=finished_at,
        stop_requested=True,
        run_id=run_id,
    )


__all__ = [
    "COMMAND_SOURCES",
    "MAXIMUM_DURATION_SECONDS",
    "MAXIMUM_OUTPUT_PERCENT",
    "MINIMUM_DURATION_SECONDS",
    "WORKSHOP_PHASE",
    "WorkshopCommand",
    "WorkshopReceipt",
    "execute_workshop_command",
]
