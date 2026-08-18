"""Shared constants and immutable public result types for 3awnt."""

from __future__ import annotations

import datetime
from dataclasses import dataclass


class TawntHatasi(Exception):
    """3awnt bir ihlal buldu; çağıran kod güvenli tarafta kalmalıdır."""


OLCULDU = "olculdu"
VARSAYILDI = "varsayildi"
DEVRALINDI = "devralindi"
KAYNAKLAR = (OLCULDU, VARSAYILDI, DEVRALINDI)

OFFLINE = "OFFLINE"
BENCH = "BENCH"
LIVE = "LIVE"
PROFILLER = (OFFLINE, BENCH, LIVE)

DEFINED = "DEFINED"
RECORDED = "RECORDED"
VALIDATED = "VALIDATED"
STALE = "STALE"
SEALED = "SEALED"

BOOT = "BOOT"
VALIDATING = "VALIDATING"
READY_UNARMED = "READY_UNARMED"
ARMED = "ARMED"
MUTED = "MUTED"
LATCHED_FAULT = "LATCHED_FAULT"

WARNING = "WARNING"
STOP = "STOP"


@dataclass(frozen=True)
class ValidatedMotorCommand:
    """Gerçek sürücüye gönderilmeye uygun olduğu doğrulanmış komut."""

    left: float
    right: float
    phase: str
    profile: str
    timestamp: str


def now() -> str:
    """Return the wall-clock timestamp format used by existing logs and records."""

    return datetime.datetime.now().isoformat(timespec="seconds")
