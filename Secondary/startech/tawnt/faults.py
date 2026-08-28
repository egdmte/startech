"""Shutdown callbacks, logging, and persistent fault-latch behavior."""

from __future__ import annotations

import io
import json
import os
from pathlib import Path
import tempfile
from typing import Any

from .model import (
    LATCHED_FAULT,
    MUTED,
    RECORDED,
    VALIDATING,
    TawntHatasi,
    now,
)
from .runtime import runtime


def onShutdown(fn):
    if fn not in runtime.kapatma_geri:
        runtime.kapatma_geri.append(fn)
    return fn


def log_line(satir: str) -> None:
    try:
        with io.open(runtime.gunluk_yolu, "a", encoding="utf-8") as handle:
            handle.write(satir + "\n")
    except Exception:
        pass


def apply_zero_callbacks(reason: str) -> None:
    for fn in tuple(runtime.kapatma_geri):
        try:
            fn()
        except Exception as exc:
            log_line("%s  CALLBACK_HATA  %r  %s" % (now(), exc, reason))


def _atomic_json_write(path: Path, data: dict[str, Any]) -> None:
    parent = path.parent
    if not parent.exists():
        raise TawntHatasi("Fault-store klasoru yok: %s" % parent)
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=str(parent), delete=False
        ) as handle:
            temp_name = handle.name
            json.dump(data, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except Exception as exc:
        if temp_name:
            try:
                os.unlink(temp_name)
            except OSError:
                pass
        if isinstance(exc, TawntHatasi):
            raise
        raise TawntHatasi("Fault-store atomik yazma basarisiz: %s" % exc) from exc


def configureFaultStore(path) -> str:
    """Kalıcı ciddi arıza kaydının açık yolunu ayarlar; dosya oluşturmaz."""

    resolved = Path(path).expanduser().resolve()
    if not resolved.parent.exists():
        raise TawntHatasi("Fault-store klasoru yok: %s" % resolved.parent)
    runtime.fault_store_path = resolved
    if not resolved.exists():
        return str(resolved)
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or "active" not in data:
            raise ValueError("active alani yok")
    except Exception as exc:
        runtime.kilit = {
            "sebep": "fault-store bozuk",
            "ayrinti": str(exc),
            "zaman": now(),
            "profile": runtime.profil,
        }
        runtime.armed = False
        runtime.sistem_durumu = LATCHED_FAULT
        return str(resolved)
    if data.get("active"):
        runtime.kilit = data.get("fault") or {
            "sebep": "kalici fault-store aktif",
            "ayrinti": "ayrinti yok",
            "zaman": now(),
            "profile": runtime.profil,
        }
        runtime.armed = False
        runtime.sistem_durumu = LATCHED_FAULT
    return str(resolved)


def _persist_active_fault() -> None:
    if runtime.fault_store_path is None:
        return
    _atomic_json_write(
        runtime.fault_store_path,
        {"version": 1, "active": True, "fault": runtime.kilit},
    )


def latchFault(reason: str, details: str = "", command=None):
    """Sıfır callback'lerini çağırır, ciddi kilit koyar ve mümkünse kalıcı yazar."""

    apply_zero_callbacks(reason)
    runtime.son_komut = (0.0, 0.0)
    if runtime.kilit is None:
        runtime.kilit = {
            "sebep": reason,
            "ayrinti": details,
            "zaman": now(),
            "profile": runtime.profil,
            "command": command,
        }
    runtime.armed = False
    runtime.sistem_durumu = LATCHED_FAULT
    try:
        _persist_active_fault()
    except TawntHatasi as exc:
        log_line("%s  FAULT_STORE_HATA  %s" % (now(), exc))
    log_line(
        "%s  KILIT  %s  %s" % (runtime.kilit["zaman"], reason, details)
    )
    return dict(runtime.kilit)


def declareUnexpectedSigint(sebep, ayrinti=""):
    """V1 uyumluluk adı; işletim sistemi sinyalini kendisi bağlamaz."""

    return latchFault(sebep, ayrinti)


def flushPWM(sebep, evre=None):
    """Geçici susturma; ciddi kilidi açamaz."""

    apply_zero_callbacks(sebep)
    runtime.son_komut = (0.0, 0.0)
    if runtime.kilit is None:
        runtime.susturma = {"sebep": sebep, "evre": evre}
        runtime.sistem_durumu = MUTED
    log_line("%s  SUSTUR (%s)  %s" % (now(), evre, sebep))
    return True


def resetFault(human: str, *, motor_power_off: bool = False) -> bool:
    """İnsan beyanıyla ciddi kilidi temizler; doğrudan ARMED durumuna geçmez."""

    if not isinstance(human, str) or not human.strip():
        raise TawntHatasi("resetFault insan adi/beyani ister.")
    if motor_power_off is not True:
        raise TawntHatasi("resetFault motor gucu kapali beyanini ister.")
    if runtime.kilit is None:
        raise TawntHatasi("Temizlenecek ciddi kilit yok.")

    previous = dict(runtime.kilit)
    apply_zero_callbacks("fault reset oncesi")
    reset_record = {
        "version": 1,
        "active": False,
        "previous_fault": previous,
        "reset": {"human": human.strip(), "time": now(), "motor_power_off": True},
    }
    if runtime.fault_store_path is not None:
        _atomic_json_write(runtime.fault_store_path, reset_record)
    runtime.kilit = None
    runtime.susturma = None
    runtime.armed = False
    runtime.son_komut = (0.0, 0.0)
    runtime.muhur = False
    runtime.validated_once = False
    for kayit in runtime.defter.values():
        if kayit["atandi"]:
            kayit["state"] = RECORDED
            kayit["validated_profile"] = None
    runtime.sistem_durumu = VALIDATING
    log_line("%s  RESET  %s" % (now(), human.strip()))
    return True


def kilitDurumu():
    return dict(runtime.kilit) if runtime.kilit else None
