"""
STARTECH-DORA
Durum Okuma ve Raporlama Algoritması
State Analysis and Recognition Algorithm

DORA is a deterministic state machine. It performs no camera, logging, network,
Tawnt, or motor work; ARDA supplies validated events and consumes new snapshots.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import math
import time


class StateError(RuntimeError):
    """Base error for invalid state-machine requests."""


class InvalidStateEvent(StateError, ValueError):
    """Raised when an event contains malformed or unsafe metadata."""


class IllegalTransition(StateError):
    """Raised when an otherwise valid event is forbidden in the current state."""


class StaleStateEvent(StateError):
    """Raised when an event is older than the accepted state or camera frame."""


class VehicleState(str, Enum):
    """High-level states; none of these directly imply physical motor output."""

    BOOT = "BOOT"
    SELF_TEST = "SELF_TEST"
    READY = "READY"
    WAITING_FOR_GREEN = "WAITING_FOR_GREEN"
    DRIVING = "DRIVING"
    STOPPING = "STOPPING"
    WAITING = "WAITING"
    FINISHED = "FINISHED"
    FAULT = "FAULT"


class EventType(str, Enum):
    """Requests that may cause one explicit state transition."""

    BEGIN_SELF_TEST = "BEGIN_SELF_TEST"
    SELF_TEST_PASSED = "SELF_TEST_PASSED"
    PREPARE_START = "PREPARE_START"
    GREEN_DETECTED = "GREEN_DETECTED"
    STOP_REQUESTED = "STOP_REQUESTED"
    MOTION_STOPPED = "MOTION_STOPPED"
    RESUME_REQUESTED = "RESUME_REQUESTED"
    FINISH_DETECTED = "FINISH_DETECTED"
    FAULT_DETECTED = "FAULT_DETECTED"
    RESET_REQUESTED = "RESET_REQUESTED"


def _is_finite_number(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


@dataclass(frozen=True)
class StateEvent:
    """One validated request to change DORA's state."""

    event_type: EventType
    occurred_at: float = field(default_factory=time.monotonic)
    frame_id: int | None = None
    reason: str = ""
    human_confirmed: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.event_type, EventType):
            raise InvalidStateEvent("event_type must be an EventType")
        if not _is_finite_number(self.occurred_at) or self.occurred_at < 0:
            raise InvalidStateEvent("occurred_at must be finite and non-negative")
        if self.frame_id is not None:
            if isinstance(self.frame_id, bool) or not isinstance(self.frame_id, int):
                raise InvalidStateEvent("frame_id must be an integer or None")
            if self.frame_id < 0:
                raise InvalidStateEvent("frame_id cannot be negative")
        if not isinstance(self.reason, str):
            raise InvalidStateEvent("reason must be text")
        if not isinstance(self.human_confirmed, bool):
            raise InvalidStateEvent("human_confirmed must be a boolean")
        if self.event_type in {EventType.FAULT_DETECTED, EventType.STOP_REQUESTED}:
            if not self.reason.strip():
                raise InvalidStateEvent(
                    f"{self.event_type.value} must include a non-empty reason"
                )
        if self.event_type == EventType.RESET_REQUESTED and not self.human_confirmed:
            raise InvalidStateEvent("RESET_REQUESTED needs explicit human confirmation")


@dataclass(frozen=True)
class StateSnapshot:
    """DORA's complete externally readable state after one accepted event."""

    state: VehicleState = VehicleState.BOOT
    revision: int = 0
    entered_at: float = 0.0
    last_frame_id: int | None = None
    reason: str = "initial state"

    def __post_init__(self) -> None:
        if not isinstance(self.state, VehicleState):
            raise ValueError("state must be a VehicleState")
        if isinstance(self.revision, bool) or not isinstance(self.revision, int):
            raise ValueError("revision must be an integer")
        if self.revision < 0:
            raise ValueError("revision cannot be negative")
        if not _is_finite_number(self.entered_at) or self.entered_at < 0:
            raise ValueError("entered_at must be finite and non-negative")
        if self.last_frame_id is not None:
            if (
                isinstance(self.last_frame_id, bool)
                or not isinstance(self.last_frame_id, int)
                or self.last_frame_id < 0
            ):
                raise ValueError("last_frame_id must be a non-negative integer or None")
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise ValueError("snapshot reason must be non-empty text")


_TRANSITIONS = {
    (VehicleState.BOOT, EventType.BEGIN_SELF_TEST): VehicleState.SELF_TEST,
    (VehicleState.SELF_TEST, EventType.SELF_TEST_PASSED): VehicleState.READY,
    (VehicleState.READY, EventType.PREPARE_START): VehicleState.WAITING_FOR_GREEN,
    (
        VehicleState.WAITING_FOR_GREEN,
        EventType.GREEN_DETECTED,
    ): VehicleState.DRIVING,
    (VehicleState.DRIVING, EventType.STOP_REQUESTED): VehicleState.STOPPING,
    (VehicleState.STOPPING, EventType.MOTION_STOPPED): VehicleState.WAITING,
    (VehicleState.WAITING, EventType.RESUME_REQUESTED): VehicleState.DRIVING,
    (VehicleState.DRIVING, EventType.FINISH_DETECTED): VehicleState.FINISHED,
    (VehicleState.FAULT, EventType.RESET_REQUESTED): VehicleState.BOOT,
    (VehicleState.FINISHED, EventType.RESET_REQUESTED): VehicleState.BOOT,
}


def transition(snapshot: StateSnapshot, event: StateEvent) -> StateSnapshot:
    """Return the next state without mutating the supplied snapshot."""

    if not isinstance(snapshot, StateSnapshot):
        raise TypeError("snapshot must be a StateSnapshot")
    if not isinstance(event, StateEvent):
        raise TypeError("event must be a StateEvent")
    if event.occurred_at < snapshot.entered_at:
        raise StaleStateEvent("event timestamp is older than the current state")
    if (
        event.frame_id is not None
        and snapshot.last_frame_id is not None
        and event.frame_id <= snapshot.last_frame_id
    ):
        raise StaleStateEvent("event frame is duplicate or older than the current state")

    if event.event_type == EventType.FAULT_DETECTED:
        target = VehicleState.FAULT
    else:
        target = _TRANSITIONS.get((snapshot.state, event.event_type))

    if target is None:
        raise IllegalTransition(
            f"{event.event_type.value} is not allowed while state is {snapshot.state.value}"
        )

    reason = event.reason.strip() or event.event_type.value.lower()
    return StateSnapshot(
        state=target,
        revision=snapshot.revision + 1,
        entered_at=float(event.occurred_at),
        last_frame_id=(
            event.frame_id if event.frame_id is not None else snapshot.last_frame_id
        ),
        reason=reason,
    )


class StateMachine:
    """Small mutable holder around the pure ``transition`` function."""

    def __init__(self, initial: StateSnapshot | None = None) -> None:
        self._snapshot = initial or StateSnapshot()

    @property
    def snapshot(self) -> StateSnapshot:
        return self._snapshot

    def apply(self, event: StateEvent) -> StateSnapshot:
        """Store and return an accepted transition; preserve state on rejection."""

        next_snapshot = transition(self._snapshot, event)
        self._snapshot = next_snapshot
        return next_snapshot
