"""
STARTECH-KADER
Karakutu Analiz, Depolama ve Erişim Raporlayıcısı
Black-box Logging, Analysis and Incident Recording

KADER records software evidence. A record proves that this process wrote data; it
does not prove that a physical camera observed something or that a motor stopped.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
import json
import math
import os
from pathlib import Path
import time
from types import MappingProxyType
from typing import Any


class BlackBoxError(RuntimeError):
    """Base error for a record that cannot be accepted or persisted."""


class InvalidRecord(BlackBoxError, ValueError):
    """Raised when record metadata or JSON data violates the logging contract."""


class RecordOrderError(BlackBoxError):
    """Raised when sequence or frame identifiers move backwards."""


class RecordKind(str, Enum):
    """Stable categories that remain understandable across module revisions."""

    FRAME = "FRAME"
    OBSERVATION = "OBSERVATION"
    STATE = "STATE"
    MOTOR_REQUEST = "MOTOR_REQUEST"
    MOTOR_ACCEPTED = "MOTOR_ACCEPTED"
    WARNING = "WARNING"
    FAULT = "FAULT"
    INFO = "INFO"


def _is_finite_number(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _validate_json_value(value: Any, path: str = "data") -> None:
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise InvalidRecord(f"{path} contains NaN or infinity")
        return
    if isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _validate_json_value(item, f"{path}[{index}]")
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise InvalidRecord(f"{path} contains a non-text mapping key")
            _validate_json_value(item, f"{path}.{key}")
        return
    raise InvalidRecord(f"{path} contains non-JSON value {type(value).__name__}")


def _canonical_mapping(data: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(data, Mapping):
        raise InvalidRecord("record data must be a mapping")
    _validate_json_value(data)
    encoded = json.dumps(data, ensure_ascii=False, allow_nan=False, sort_keys=True)
    decoded = json.loads(encoded)
    return MappingProxyType(decoded)


def _validate_run_id(run_id: str) -> str:
    if not isinstance(run_id, str) or not run_id.strip():
        raise InvalidRecord("run_id must be non-empty text")
    return run_id.strip()


@dataclass(frozen=True)
class BlackBoxRecord:
    """One immutable, JSON-safe event in a recorded or physical run."""

    run_id: str
    sequence: int
    recorded_at: float
    kind: RecordKind
    module: str
    data: Mapping[str, Any]
    frame_id: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _validate_run_id(self.run_id))
        if isinstance(self.sequence, bool) or not isinstance(self.sequence, int):
            raise InvalidRecord("sequence must be an integer")
        if self.sequence < 0:
            raise InvalidRecord("sequence cannot be negative")
        if not _is_finite_number(self.recorded_at) or self.recorded_at < 0:
            raise InvalidRecord("recorded_at must be finite and non-negative")
        if not isinstance(self.kind, RecordKind):
            raise InvalidRecord("kind must be a RecordKind")
        if not isinstance(self.module, str) or not self.module.strip():
            raise InvalidRecord("module must be non-empty text")
        object.__setattr__(self, "module", self.module.strip())
        if self.frame_id is not None:
            if isinstance(self.frame_id, bool) or not isinstance(self.frame_id, int):
                raise InvalidRecord("frame_id must be an integer or None")
            if self.frame_id < 0:
                raise InvalidRecord("frame_id cannot be negative")
        object.__setattr__(self, "data", _canonical_mapping(self.data))

    def to_dict(self) -> dict[str, Any]:
        """Return a plain mapping suitable for one JSONL line."""

        return {
            "run_id": self.run_id,
            "sequence": self.sequence,
            "recorded_at": float(self.recorded_at),
            "kind": self.kind.value,
            "module": self.module,
            "frame_id": self.frame_id,
            "data": dict(self.data),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "BlackBoxRecord":
        """Validate and reconstruct one record read from JSONL."""

        if not isinstance(value, Mapping):
            raise InvalidRecord("JSONL record must be an object")
        expected = {
            "run_id",
            "sequence",
            "recorded_at",
            "kind",
            "module",
            "frame_id",
            "data",
        }
        unknown = set(value) - expected
        missing = expected - set(value)
        if unknown or missing:
            details = []
            if missing:
                details.append("missing=" + ",".join(sorted(missing)))
            if unknown:
                details.append("unknown=" + ",".join(sorted(map(str, unknown))))
            raise InvalidRecord("invalid JSONL fields: " + " ".join(details))
        try:
            kind = RecordKind(value["kind"])
        except (TypeError, ValueError) as exc:
            raise InvalidRecord("unknown record kind") from exc
        return cls(
            run_id=value["run_id"],
            sequence=value["sequence"],
            recorded_at=value["recorded_at"],
            kind=kind,
            module=value["module"],
            frame_id=value["frame_id"],
            data=value["data"],
        )


class MemoryBlackBox:
    """Validated append-only records held only in process memory."""

    def __init__(self, run_id: str) -> None:
        self.run_id = _validate_run_id(run_id)
        self._records: list[BlackBoxRecord] = []
        self._last_frame_id: int | None = None

    @property
    def records(self) -> tuple[BlackBoxRecord, ...]:
        return tuple(self._records)

    def _build_record(
        self,
        kind: RecordKind,
        module: str,
        data: Mapping[str, Any],
        *,
        frame_id: int | None,
        recorded_at: float | None,
    ) -> BlackBoxRecord:
        return BlackBoxRecord(
            run_id=self.run_id,
            sequence=len(self._records),
            recorded_at=time.time() if recorded_at is None else recorded_at,
            kind=kind,
            module=module,
            data=data,
            frame_id=frame_id,
        )

    def _accept(self, record: BlackBoxRecord) -> BlackBoxRecord:
        if record.run_id != self.run_id:
            raise RecordOrderError("record belongs to a different run")
        if record.sequence != len(self._records):
            raise RecordOrderError("record sequence is not contiguous")
        if (
            record.frame_id is not None
            and self._last_frame_id is not None
            and record.frame_id < self._last_frame_id
        ):
            raise RecordOrderError("frame_id moved backwards")
        self._records.append(record)
        if record.frame_id is not None:
            self._last_frame_id = record.frame_id
        return record

    def append(
        self,
        kind: RecordKind,
        module: str,
        data: Mapping[str, Any],
        *,
        frame_id: int | None = None,
        recorded_at: float | None = None,
    ) -> BlackBoxRecord:
        """Validate and append one in-memory record."""

        record = self._build_record(
            kind,
            module,
            data,
            frame_id=frame_id,
            recorded_at=recorded_at,
        )
        return self._accept(record)


class JsonlBlackBox:
    """Append-only UTF-8 JSONL recorder with validated restart recovery."""

    def __init__(self, path: str | Path, run_id: str) -> None:
        self.path = Path(path)
        if not self.path.parent.exists():
            raise BlackBoxError(f"log directory does not exist: {self.path.parent}")
        if self.path.exists() and self.path.is_dir():
            raise BlackBoxError("log path points to a directory")
        self._memory = MemoryBlackBox(run_id)
        if self.path.exists():
            self._load_existing()

    @property
    def records(self) -> tuple[BlackBoxRecord, ...]:
        return self._memory.records

    def _load_existing(self) -> None:
        with self.path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    raise InvalidRecord(f"blank JSONL line at {line_number}")
                try:
                    value = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise InvalidRecord(
                        f"invalid JSONL at line {line_number}: {exc.msg}"
                    ) from exc
                self._memory._accept(BlackBoxRecord.from_dict(value))

    def append(
        self,
        kind: RecordKind,
        module: str,
        data: Mapping[str, Any],
        *,
        frame_id: int | None = None,
        recorded_at: float | None = None,
    ) -> BlackBoxRecord:
        """Persist exactly one validated record before accepting it in memory."""

        record = self._memory._build_record(
            kind,
            module,
            data,
            frame_id=frame_id,
            recorded_at=recorded_at,
        )
        encoded = json.dumps(
            record.to_dict(),
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        try:
            with self.path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(encoded + "\n")
                handle.flush()
                os.fsync(handle.fileno())
        except OSError as exc:
            raise BlackBoxError(f"could not append black-box record: {exc}") from exc
        return self._memory._accept(record)
