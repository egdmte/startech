"""Small compatibility types for KERİM's retained run log endpoint.

The previous vehicle runtime owned these names.  KERİM only needs to validate
received JSON records, so importing the deprecated runtime made the web service
needlessly depend on deleted car modules.  UZAKTAN may replace this protocol;
until then this module keeps the stored wire format readable and self-contained.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
import json
import math
from types import MappingProxyType
from typing import Any


RUN_CANCELLED = "RUN_CANCELLED"
RUN_STATES = frozenset(
    {
        "RUN_RECEIVED",
        "RUN_INITIATED",
        "RUN_HALT_NOCON",
        RUN_CANCELLED,
        "RUN_INTERRUPTED",
        "RUN_COMPLETED",
        "RUN_FAILED",
    }
)


class RunEventKind(str, Enum):
    FRAME = "FRAME"
    OBSERVATION = "OBSERVATION"
    STATE = "STATE"
    MOTOR_REQUEST = "MOTOR_REQUEST"
    MOTOR_ACCEPTED = "MOTOR_ACCEPTED"
    WARNING = "WARNING"
    FAULT = "FAULT"
    INFO = "INFO"


def _json_mapping(value: object) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("record data must be an object")
    try:
        encoded = json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True)
        decoded = json.loads(encoded)
    except (TypeError, ValueError) as exc:
        raise ValueError("record data must contain only finite JSON values") from exc
    if not isinstance(decoded, dict):
        raise ValueError("record data must be an object")
    return MappingProxyType(decoded)


@dataclass(frozen=True)
class RunEvent:
    run_id: str
    sequence: int
    recorded_at: float
    kind: RunEventKind
    module: str
    frame_id: int | None
    data: Mapping[str, Any]

    @classmethod
    def from_dict(cls, value: object) -> "RunEvent":
        expected = {
            "run_id",
            "sequence",
            "recorded_at",
            "kind",
            "module",
            "frame_id",
            "data",
        }
        if not isinstance(value, Mapping) or set(value) != expected:
            raise ValueError("run event has unexpected fields")
        run_id = value["run_id"]
        sequence = value["sequence"]
        recorded_at = value["recorded_at"]
        module = value["module"]
        frame_id = value["frame_id"]
        if not isinstance(run_id, str) or not run_id.strip():
            raise ValueError("run_id must be non-empty text")
        if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 0:
            raise ValueError("sequence must be a non-negative integer")
        if (
            isinstance(recorded_at, bool)
            or not isinstance(recorded_at, (int, float))
            or not math.isfinite(float(recorded_at))
            or recorded_at < 0
        ):
            raise ValueError("recorded_at must be finite and non-negative")
        if not isinstance(module, str) or not module.strip():
            raise ValueError("module must be non-empty text")
        if frame_id is not None and (
            isinstance(frame_id, bool)
            or not isinstance(frame_id, int)
            or frame_id < 0
        ):
            raise ValueError("frame_id must be a non-negative integer or null")
        try:
            kind = RunEventKind(value["kind"])
        except (TypeError, ValueError) as exc:
            raise ValueError("unknown run event kind") from exc
        return cls(
            run_id=run_id.strip(),
            sequence=sequence,
            recorded_at=float(recorded_at),
            kind=kind,
            module=module.strip(),
            frame_id=frame_id,
            data=_json_mapping(value["data"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "sequence": self.sequence,
            "recorded_at": self.recorded_at,
            "kind": self.kind.value,
            "module": self.module,
            "frame_id": self.frame_id,
            "data": dict(self.data),
        }


__all__ = ["RUN_CANCELLED", "RUN_STATES", "RunEvent", "RunEventKind"]
