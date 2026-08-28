"""Merged STARTECH configuration v2 and stable SAC-contract v1 support.

The outer v2 document keeps a validated v1 calibration/settings pair intact and
records assisted choices separately.  Only selected driving behaviour with an
unambiguous v1 meaning is projected into ``ayarlar``.  Camera, wheel and hardware
claims remain intent or evidence until a supervised converter can justify them.
"""

from __future__ import annotations

import copy
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from .validation import (
    AYARLAR_SEMASI,
    KALIBRASYON_SEMASI,
    ayarlari_dogrula,
    json_oku,
    kalibrasyonu_dogrula,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
COMBINED_SCHEMA_PATH = PROJECT_ROOT / "config" / "schema" / "yapilandirma-v2.schema.json"
COMBINED_SCHEMA_VERSION = 2
SAC_CONTRACT_VERSION = 1

COMBINED_SCHEMA = json_oku(COMBINED_SCHEMA_PATH)
_REGISTRY = Registry().with_resources(
    (
        (KALIBRASYON_SEMASI["$id"], Resource.from_contents(KALIBRASYON_SEMASI)),
        (AYARLAR_SEMASI["$id"], Resource.from_contents(AYARLAR_SEMASI)),
    )
)


def _error_path(error: Any) -> str:
    path = ".".join(str(part) for part in error.absolute_path)
    return path or "<kok>"


def combined_schema_errors(value: object) -> list[str]:
    """Return stable, readable Draft 2020-12 errors for a merged document."""

    validator = Draft202012Validator(COMBINED_SCHEMA, registry=_REGISTRY)
    errors = sorted(
        validator.iter_errors(value),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    return [f"{_error_path(error)}: {error.message}" for error in errors]


def combined_semantic_errors(value: dict[str, Any]) -> list[str]:
    """Validate relationships not fully described by the JSON schema."""

    errors: list[str] = []
    calibration = value["kalibrasyon"]
    settings = value["ayarlar"]
    errors.extend(f"kalibrasyon.{error}" for error in kalibrasyonu_dogrula(calibration))
    errors.extend(f"ayarlar.{error}" for error in ayarlari_dogrula(settings))

    intent = value["sac_niyeti"]
    if intent is None:
        return errors

    power = intent["guc"]
    if power["minimum_hiz_yuzde"] > power["maksimum_hiz_yuzde"]:
        errors.append("sac_niyeti.guc minimum hız azami hızdan büyük olamaz")

    required_modules = {"yaren", "arda", "kasim"}
    enabled_modules = set(intent["hesaplama"]["etkin_moduller"])
    missing_modules = sorted(required_modules - enabled_modules)
    if missing_modules:
        errors.append(
            "sac_niyeti.hesaplama zorunlu modülleri eksik: "
            + ", ".join(missing_modules)
        )

    if intent["surus"]["surucu_cikis_modu"] == "full":
        evidence = value["oturum_kaniti"]
        if not evidence["tam_cikis_onaylandi"]:
            errors.append("full sürücü çıkışı SAC profil onayı olmadan kaydedilemez")
    return errors


def combined_config_errors(value: object) -> list[str]:
    """Validate structure first, then safe cross-field relationships."""

    schema_errors = combined_schema_errors(value)
    if schema_errors:
        return schema_errors
    assert isinstance(value, dict)
    return combined_semantic_errors(value)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _identifier() -> str:
    return secrets.token_hex(3)


def _project_assisted_speed(
    settings: dict[str, Any], sac_intent: dict[str, Any]
) -> None:
    """Apply only the SAC values with a direct, non-measurement v1 meaning."""

    power = sac_intent["guc"]
    minimum = power["minimum_hiz_yuzde"]
    maximum = power["maksimum_hiz_yuzde"]
    speed = settings["hiz"]
    speed["min"] = minimum
    speed["max"] = maximum
    speed["hedef"] = min(max(speed["hedef"], minimum), maximum)


def merge_v1_pair(
    calibration: dict[str, Any],
    settings: dict[str, Any],
    *,
    name: str,
    source: str,
    sac_intent: dict[str, Any] | None,
    session_evidence: dict[str, Any],
    workflow: str = "SAC",
    now: Callable[[], str] = _utc_now,
    identifier: Callable[[], str] = _identifier,
) -> dict[str, Any]:
    """Return a new merged v2 document without mutating either v1 input."""

    calibration_copy = copy.deepcopy(calibration)
    settings_copy = copy.deepcopy(settings)
    intent_copy = copy.deepcopy(sac_intent)
    evidence_copy = copy.deepcopy(session_evidence)
    if intent_copy is not None:
        _project_assisted_speed(settings_copy, intent_copy)

    combined = {
        "sema_surumu": COMBINED_SCHEMA_VERSION,
        "profil": {
            "ad": name,
            "is_akisi": workflow,
            "kaynak": source,
            "olusturuldu_utc": now(),
            "kimlik": identifier(),
        },
        "kalibrasyon": calibration_copy,
        "ayarlar": settings_copy,
        "sac_niyeti": intent_copy,
        "oturum_kaniti": evidence_copy,
    }
    errors = combined_config_errors(combined)
    if errors:
        raise ValueError("; ".join(errors))
    return combined


def split_v2(value: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return independent v1 calibration/settings copies from a valid v2 file."""

    errors = combined_config_errors(value)
    if errors:
        raise ValueError("; ".join(errors))
    return copy.deepcopy(value["kalibrasyon"]), copy.deepcopy(value["ayarlar"])


__all__ = [
    "COMBINED_SCHEMA",
    "COMBINED_SCHEMA_VERSION",
    "SAC_CONTRACT_VERSION",
    "combined_config_errors",
    "combined_schema_errors",
    "combined_semantic_errors",
    "merge_v1_pair",
    "split_v2",
]
