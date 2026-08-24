"""Safe YAREN capability checks for CAM.

The collector reports what each probe actually establishes.  It deliberately
does not import ``arac.surucu`` and never arms, activates, steers, or requests a
motor output.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import queue
import threading
import time
from pathlib import Path
from typing import Any

from startech.configuration.profiles import ProfileStore

from . import tawnt
from .durum import EventType, StateEvent, StateMachine
from .goruntu import SimulatedVisionAnalyzer
from .goz import (
    CameraProbeResult,
    CameraUnavailable,
    FramePacket,
    build_preferred_camera,
    probe_camera,
)
from .kayit import MemoryBlackBox, RecordKind


CAPABILITY_STATUSES = frozenset(
    {
        "LIVE",
        "RESPONDED",
        "SIMULATED",
        "BLOCKED_BY_POLICY",
        "UNAVAILABLE",
        "FAILED",
        "UNVERIFIED",
    }
)


@dataclass(frozen=True)
class CapabilityResult:
    module: str
    name: str
    status: str
    scope: str
    detail: str
    duration_ms: int
    facts: Mapping[str, Any]

    def __post_init__(self) -> None:
        if self.status not in CAPABILITY_STATUSES:
            raise ValueError("unknown capability status")
        for value in (self.module, self.name, self.scope, self.detail):
            if not isinstance(value, str) or not value.strip():
                raise ValueError("capability text fields must be non-empty")
        if isinstance(self.duration_ms, bool) or self.duration_ms < 0:
            raise ValueError("capability duration must be non-negative")
        if not isinstance(self.facts, Mapping):
            raise ValueError("capability facts must be a mapping")

    def to_dict(self) -> dict[str, Any]:
        return {
            "module": self.module,
            "name": self.name,
            "status": self.status,
            "scope": self.scope,
            "detail": self.detail,
            "duration_ms": self.duration_ms,
            "facts": dict(self.facts),
        }


Probe = Callable[[], tuple[str, str, Mapping[str, Any]]]


def _bounded_probe(
    module: str,
    name: str,
    scope: str,
    probe: Probe,
    *,
    timeout_seconds: float,
    clock: Callable[[], float],
) -> CapabilityResult:
    started = clock()
    results: queue.Queue[tuple[bool, object]] = queue.Queue(maxsize=1)

    def invoke() -> None:
        try:
            results.put((True, probe()))
        except BaseException as exc:  # one failed module must not hide other results
            results.put((False, exc))

    thread = threading.Thread(
        target=invoke,
        name=f"yaren-check-{module.lower()}",
        daemon=True,
    )
    thread.start()
    thread.join(timeout_seconds)
    duration_ms = max(0, int(round((clock() - started) * 1000)))
    if thread.is_alive():
        return CapabilityResult(
            module,
            name,
            "FAILED",
            scope,
            f"Probe exceeded the {timeout_seconds:g} second diagnostic limit.",
            duration_ms,
            {"timed_out": True},
        )
    succeeded, value = results.get_nowait()
    if not succeeded:
        detail = f"{type(value).__name__}: {value}"[:500]
        unavailable = isinstance(value, CameraUnavailable)
        return CapabilityResult(
            module,
            name,
            "UNAVAILABLE" if unavailable else "FAILED",
            scope,
            detail,
            duration_ms,
            {},
        )
    status, detail, facts = value  # type: ignore[misc]
    return CapabilityResult(
        module,
        name,
        status,
        scope,
        detail[:500],
        duration_ms,
        facts,
    )


def _profile_probe(store: ProfileStore) -> tuple[str, str, Mapping[str, Any]]:
    diagnosis = store.diagnose_active()
    if not diagnosis.valid:
        return (
            "FAILED",
            "; ".join(diagnosis.errors) or "Active profile diagnosis failed.",
            {"warnings": list(diagnosis.warnings)},
        )
    profile = store.load_active_profile()
    return (
        "RESPONDED",
        "The selected immutable profile passed its integrity checks.",
        {
            "profile_id": profile.manifest.profile_id,
            "calibration_sha256": profile.manifest.calibration_sha256,
            "settings_sha256": profile.manifest.settings_sha256,
            "warnings": list(diagnosis.warnings),
        },
    )


def _camera_probe(camera_factory: Callable[[], object]) -> tuple[str, str, Mapping[str, Any]]:
    result: CameraProbeResult = probe_camera(camera_factory(), frame_count=1)  # type: ignore[arg-type]
    return (
        "LIVE",
        "A real frame was captured and discarded after metadata inspection.",
        {
            "source": result.source,
            "frame_count": result.frame_count,
            "width": result.width,
            "height": result.height,
            "elapsed_seconds": result.elapsed_seconds,
        },
    )


def _vision_probe() -> tuple[str, str, Mapping[str, Any]]:
    frame = FramePacket(
        1,
        1.0,
        {
            "valid": True,
            "lane_error": 0.0,
            "obstacle": False,
            "confidence": 1.0,
            "reason": "deterministic diagnostic",
        },
        "yaren-diagnostic",
    )
    observation = SimulatedVisionAnalyzer().analyze(frame)
    return (
        "SIMULATED",
        "The deterministic vision contract responded; real recognition was not tested.",
        {"valid": observation.valid, "frame_id": observation.frame_id},
    )


def _state_probe() -> tuple[str, str, Mapping[str, Any]]:
    machine = StateMachine()
    machine.apply(StateEvent(EventType.BEGIN_SELF_TEST, occurred_at=1.0))
    snapshot = machine.apply(StateEvent(EventType.SELF_TEST_PASSED, occurred_at=2.0))
    return (
        "RESPONDED",
        "The software-only BOOT → SELF_TEST → READY transitions completed.",
        {"state": snapshot.state.value, "revision": snapshot.revision},
    )


def _black_box_probe() -> tuple[str, str, Mapping[str, Any]]:
    black_box = MemoryBlackBox("yaren-diagnostic")
    appended = black_box.append(
        RecordKind.INFO,
        "YAREN",
        {"diagnostic": True},
        recorded_at=1.0,
    )
    restored = black_box.records[0]
    if restored != appended:
        raise RuntimeError("in-memory record could not be read back")
    return (
        "RESPONDED",
        "An in-memory diagnostic record was validated, appended, and read back.",
        {"record_count": len(black_box.records), "persistent_storage_tested": False},
    )


def _tawnt_probe() -> tuple[str, str, Mapping[str, Any]]:
    return (
        "RESPONDED",
        "Read-only TAWNT state functions responded; no state was armed or reset.",
        {
            "system_state": tawnt.systemState(),
            "motion_allowed": tawnt.isMotionAllowed(),
            "lock_present": tawnt.lockStatus() is not None,
        },
    )


def collect_capability_report(
    device_id: str,
    *,
    profile_root: str | Path | None = None,
    camera_factory: Callable[[], object] = build_preferred_camera,
    timeout_seconds: float = 8.0,
    epoch: Callable[[], int] = lambda: int(time.time()),
    clock: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    """Run independent, bounded checks and return a JSON-safe v1 report."""

    if not isinstance(device_id, str) or not device_id.strip():
        raise ValueError("device_id must be non-empty text")
    if timeout_seconds <= 0 or timeout_seconds > 30:
        raise ValueError("diagnostic timeout must be greater than zero and at most 30 seconds")
    store = ProfileStore(profile_root)
    definitions: tuple[tuple[str, str, str, Probe], ...] = (
        (
            "YAREN",
            "Configuration registry",
            "Selected profile integrity",
            lambda: _profile_probe(store),
        ),
        (
            "KASIM",
            "Camera acquisition",
            "One physical frame; USB first, Raspberry Pi fallback",
            lambda: _camera_probe(camera_factory),
        ),
        (
            "KEREM",
            "Camera recognition",
            "Deterministic software simulation only",
            _vision_probe,
        ),
        (
            "DORA",
            "State analysis",
            "Software-only safe state transitions",
            _state_probe,
        ),
        (
            "KADER",
            "Black-box logging",
            "In-memory append/read contract",
            _black_box_probe,
        ),
        (
            "M3TH",
            "TAWNT safety declaration",
            "Read-only process state",
            _tawnt_probe,
        ),
    )
    results = [
        _bounded_probe(
            module,
            name,
            scope,
            probe,
            timeout_seconds=timeout_seconds,
            clock=clock,
        )
        for module, name, scope, probe in definitions
    ]
    results.extend(
        (
            CapabilityResult(
                "OSMAN",
                "Motor driver",
                "BLOCKED_BY_POLICY",
                "Not executed or imported by YAREN diagnostics",
                "Motor output is deliberately outside the web-link protocol.",
                0,
                {"tested": False},
            ),
            CapabilityResult(
                "STEERING",
                "Steering hardware",
                "UNVERIFIED",
                "No standalone safe hardware probe exists",
                "No steering command was sent.",
                0,
                {"tested": False},
            ),
            CapabilityResult(
                "ARDA",
                "Diagnostic coordinator",
                "RESPONDED",
                "Capability orchestration only",
                "ARDA vehicle mode was not launched.",
                0,
                {"reported_modules": len(results) + 3},
            ),
        )
    )
    return {
        "version": 1,
        "device_id": device_id.strip(),
        "checked_at": epoch(),
        "results": [result.to_dict() for result in results],
    }


__all__ = [
    "CAPABILITY_STATUSES",
    "CapabilityResult",
    "collect_capability_report",
]
