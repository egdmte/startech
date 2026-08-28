"""Single process-local state container shared by all TAWNT modules."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .model import BOOT, OFFLINE


@dataclass
class RuntimeState:
    defter: dict[str, dict[str, Any]] = field(default_factory=dict)
    ikizler: list[tuple[str, str]] = field(default_factory=list)
    zincirler: list[tuple[Any, ...]] = field(default_factory=list)
    bagimliliklar: dict[str, set[str]] = field(default_factory=dict)
    olcum_profilleri: dict[str, set[str]] = field(default_factory=dict)

    profil: str = OFFLINE
    sistem_durumu: str = BOOT
    muhur: bool = False
    validated_once: bool = False
    armed: bool = False
    evre: str | None = None
    evreler: dict[str, dict[str, Any]] = field(default_factory=dict)
    watchdogs: dict[str, dict[str, Any]] = field(default_factory=dict)
    son_komut: tuple[float, float] = (0.0, 0.0)

    kilit: dict[str, Any] | None = None
    susturma: dict[str, Any] | None = None
    kapatma_geri: list[Any] = field(default_factory=list)
    gunluk_yolu: str = "tawnt_guvenlik.log"
    fault_store_path: Path | None = None

    def reset(self) -> None:
        """Reset process-local state without deleting a persistent fault file."""

        self.defter.clear()
        self.ikizler.clear()
        self.zincirler.clear()
        self.bagimliliklar.clear()
        self.olcum_profilleri.clear()
        self.evreler.clear()
        self.watchdogs.clear()
        self.kapatma_geri.clear()

        self.profil = OFFLINE
        self.sistem_durumu = BOOT
        self.muhur = False
        self.validated_once = False
        self.armed = False
        self.evre = None
        self.son_komut = (0.0, 0.0)
        self.kilit = None
        self.susturma = None
        self.fault_store_path = None


runtime = RuntimeState()


def sifirla() -> None:
    """Yalnız testler için bütün süreç-içi durumu sıfırlar."""

    runtime.reset()
