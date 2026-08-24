"""Read-only runtime boundary for the active STARTECH configuration.

STARTECH-YAREN
Yapılandırma Arşivleme, Revizyon ve Etkinleştirme Noktası
Configuration Loading, Archival and Revision Agent

This module loads only a YAREN-selected profile whose envelope, hashes, warning
review and optional camera resolution still agree.  Loading a profile does not
arm TAWNT, create a motor driver or claim that the vehicle is safe to drive.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

from startech.configuration.profiles import ProfileError, ProfileStore


class ConfigurationLoadError(RuntimeError):
    """Raised when ARDA cannot safely consume the selected configuration."""


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


@dataclass(frozen=True)
class ActiveConfiguration:
    """Immutable snapshot of one integrity-checked selected profile."""

    profile_id: str
    name: str
    calibration_sha256: str
    settings_sha256: str
    warning_digest: str
    warnings: tuple[str, ...]
    calibration: Mapping[str, Any]
    settings: Mapping[str, Any]

    @property
    def camera_dimensions(self) -> tuple[int, int]:
        camera = self.calibration["kamera"]
        return (camera["genislik"], camera["yukseklik"])

    @property
    def motor_measurement_recorded(self) -> bool:
        """Report file evidence only; this is not proof of a physical test."""

        return self.calibration["motor"]["olculdu"] is not None


def load_active_configuration(
    root: str | Path | None = None,
    *,
    camera_dimensions: tuple[int, int] | None = None,
) -> ActiveConfiguration:
    """Load an immutable active profile or fail closed with one public error."""

    store = ProfileStore(root)
    try:
        diagnosis = store.diagnose_active(camera_dimensions=camera_dimensions)
        if not diagnosis.valid:
            detail = "; ".join(diagnosis.errors) or "active profile is invalid"
            raise ConfigurationLoadError(detail)
        loaded = store.load_active_profile()
    except ConfigurationLoadError:
        raise
    except ProfileError as exc:
        raise ConfigurationLoadError(str(exc)) from exc

    manifest = loaded.manifest
    return ActiveConfiguration(
        profile_id=manifest.profile_id,
        name=manifest.name,
        calibration_sha256=manifest.calibration_sha256,
        settings_sha256=manifest.settings_sha256,
        warning_digest=manifest.warning_digest,
        warnings=manifest.warnings,
        calibration=_freeze(loaded.calibration),
        settings=_freeze(loaded.settings),
    )


__all__ = [
    "ActiveConfiguration",
    "ConfigurationLoadError",
    "load_active_configuration",
]
