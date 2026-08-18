"""Mission phases, arming, watchdogs, and motor-command validation."""

from __future__ import annotations

import math
import time
from typing import Iterable

from .faults import apply_zero_callbacks, latchFault, log_line
from .model import (
    ARMED,
    BOOT,
    LATCHED_FAULT,
    LIVE,
    MUTED,
    READY_UNARMED,
    STOP,
    VALIDATED,
    VALIDATING,
    SEALED,
    TawntHatasi,
    ValidatedMotorCommand,
    now,
)
from .runtime import runtime
from .values import (
    _collect_value_errors,
    _invalidate_startup_validation,
    _is_finite_number,
    _is_number,
    _require_name,
    _require_unsealed,
    seal,
)


def definePhase(
    name: str,
    *,
    motion_allowed: bool = False,
    allow_reverse: bool = False,
    allow_pivot: bool = False,
    max_pwm: float = 0,
    max_difference: float | None = None,
    max_slew: float | None = None,
    required_values: Iterable[str] = (),
    required_watchdogs: Iterable[str] = (),
    allowed_from: Iterable[str] | None = None,
) -> str:
    """Evreye ait hareket zarfını tanımlar."""

    _require_unsealed()
    _invalidate_startup_validation()
    if not isinstance(name, str) or not name:
        raise TawntHatasi("Evre adi bos olamaz.")
    if name in runtime.evreler:
        raise TawntHatasi("Evre zaten tanimli: %s" % name)
    required_values = tuple(required_values)
    required_watchdogs = tuple(required_watchdogs)
    for value in required_values:
        _require_name(value)
    for watchdog in required_watchdogs:
        if watchdog not in runtime.watchdogs:
            raise TawntHatasi("Tanimlanmamis watchdog: %s" % watchdog)
    for label, value in (
        ("max_pwm", max_pwm),
        ("max_difference", max_difference),
        ("max_slew", max_slew),
    ):
        if value is not None and (not _is_finite_number(value) or value < 0):
            raise TawntHatasi("%s negatif olmayan bir sayi olmali." % label)
    runtime.evreler[name] = {
        "motion_allowed": bool(motion_allowed),
        "allow_reverse": bool(allow_reverse),
        "allow_pivot": bool(allow_pivot),
        "max_pwm": float(max_pwm),
        "max_difference": (
            None if max_difference is None else float(max_difference)
        ),
        "max_slew": None if max_slew is None else float(max_slew),
        "required_values": tuple(required_values),
        "required_watchdogs": tuple(required_watchdogs),
        "allowed_from": None if allowed_from is None else set(allowed_from),
    }
    return name


def validatePhase(phase: str) -> bool:
    if phase not in runtime.evreler:
        raise TawntHatasi("Tanimlanmamis evre: %s" % phase)
    policy = runtime.evreler[phase]
    errors = _collect_value_errors(
        policy["required_values"], profile=runtime.profil, strict_v2=True
    )
    for ad in policy["required_values"]:
        state = runtime.defter[ad]["state"]
        if state not in (VALIDATED, SEALED):
            errors.append("%s: evre icin dogrulanmamis (%s)" % (ad, state))
    try:
        checkWatchdogs(policy["required_watchdogs"])
    except TawntHatasi as exc:
        errors.append(str(exc))
    if errors:
        details = "\n  - ".join(errors)
        runtime.son_komut = (0.0, 0.0)
        if runtime.armed and runtime.profil == LIVE:
            latchFault("evre dogrulamasi basarisiz", details)
        elif runtime.kilit is None:
            apply_zero_callbacks("evre dogrulamasi basarisiz")
            runtime.susturma = {
                "sebep": "evre dogrulamasi basarisiz",
                "evre": phase,
                "kind": "phase_validation",
            }
            runtime.sistem_durumu = MUTED
        raise TawntHatasi("validatePhase basarisiz:\n  - " + details)
    if (
        runtime.susturma is not None
        and runtime.susturma.get("kind") == "phase_validation"
        and runtime.susturma.get("evre") == phase
    ):
        runtime.susturma = None
        if runtime.armed:
            runtime.sistem_durumu = ARMED
        elif runtime.validated_once:
            runtime.sistem_durumu = READY_UNARMED
        else:
            runtime.sistem_durumu = VALIDATING
    return True


def enterPhase(phase: str) -> bool:
    """İzin verilen yeni evreye girer; geçici susturma farklı evrede kalkar."""

    if phase not in runtime.evreler:
        raise TawntHatasi("Tanimlanmamis evre: %s" % phase)
    policy = runtime.evreler[phase]
    if (
        policy["allowed_from"] is not None
        and runtime.evre not in policy["allowed_from"]
    ):
        raise TawntHatasi(
            "%r evresinden %r evresine gecis yasak." % (runtime.evre, phase)
        )
    validatePhase(phase)
    previous = runtime.evre
    runtime.evre = phase
    if runtime.susturma is not None and runtime.susturma.get("evre") != phase:
        runtime.susturma = None
    if runtime.kilit is not None:
        runtime.sistem_durumu = LATCHED_FAULT
    elif runtime.susturma is not None:
        runtime.sistem_durumu = MUTED
    elif runtime.armed:
        runtime.sistem_durumu = ARMED
    elif runtime.validated_once:
        runtime.sistem_durumu = READY_UNARMED
    log_line("%s  EVRE  %s -> %s" % (now(), previous, phase))
    return isMotionAllowed()


def evreDegisti(yeniEvre):
    """V1 uyumluluk adı; tanımlı evrede ``enterPhase`` kullanılır."""

    if yeniEvre in runtime.evreler:
        return enterPhase(yeniEvre)
    runtime.evre = yeniEvre
    if runtime.susturma is not None and runtime.susturma.get("evre") != yeniEvre:
        runtime.susturma = None
    if runtime.kilit is not None:
        runtime.sistem_durumu = LATCHED_FAULT
    elif runtime.armed:
        runtime.sistem_durumu = ARMED
    elif runtime.validated_once:
        runtime.sistem_durumu = READY_UNARMED
    else:
        runtime.sistem_durumu = BOOT
    return isMotionAllowed()


def arm(
    human: str,
    *,
    live_hardware_authorized: bool = False,
    final_confirmation: bool = False,
) -> bool:
    """Doğrulanmış sistemi açık insan beyanıyla silahlandırır."""

    if runtime.kilit is not None:
        raise TawntHatasi("Ciddi kilit varken arm reddedildi.")
    if runtime.sistem_durumu != READY_UNARMED:
        raise TawntHatasi("arm icin sistem READY_UNARMED olmali.")
    if not isinstance(human, str) or not human.strip():
        raise TawntHatasi("arm icin insan adi/beyani gerekir.")
    if runtime.evre is None:
        raise TawntHatasi("arm icin once bir evre secilmeli.")
    validatePhase(runtime.evre)
    if runtime.profil == LIVE:
        if runtime.fault_store_path is None:
            raise TawntHatasi("LIVE arm kalici fault-store ister.")
        if not live_hardware_authorized or not final_confirmation:
            raise TawntHatasi(
                "LIVE arm icin donanim yetkisi ve son onay gerekir."
            )
    if not runtime.muhur:
        seal()
    runtime.armed = True
    runtime.sistem_durumu = ARMED
    log_line("%s  ARM  %s  profil=%s" % (now(), human, runtime.profil))
    return True


def disarm(reason: str = "insan istegi") -> bool:
    apply_zero_callbacks(reason)
    runtime.armed = False
    runtime.son_komut = (0.0, 0.0)
    if runtime.kilit is not None:
        runtime.sistem_durumu = LATCHED_FAULT
    elif runtime.validated_once:
        runtime.sistem_durumu = READY_UNARMED
    else:
        runtime.sistem_durumu = BOOT
    log_line("%s  DISARM  %s" % (now(), reason))
    return True


def systemState() -> str:
    return runtime.sistem_durumu


def isMotionAllowed() -> bool:
    if not runtime.armed or runtime.sistem_durumu != ARMED:
        return False
    if (
        runtime.kilit is not None
        or runtime.susturma is not None
        or runtime.evre is None
    ):
        return False
    policy = runtime.evreler.get(runtime.evre)
    return bool(policy and policy["motion_allowed"])


def pwmSerbestMi():
    """V1 uyumluluk adı; v2'de başlangıçta False döner."""

    return isMotionAllowed()


def defineWatchdog(name: str, timeout_seconds: float) -> str:
    """Kamera/kontrol gibi bir üreticinin izin verilen sessizlik süresini tanımlar."""

    _require_unsealed()
    _invalidate_startup_validation()
    if not isinstance(name, str) or not name.strip():
        raise TawntHatasi("Watchdog adi bos olamaz.")
    if name in runtime.watchdogs:
        raise TawntHatasi("Watchdog zaten tanimli: %s" % name)
    if not _is_finite_number(timeout_seconds) or timeout_seconds <= 0:
        raise TawntHatasi("Watchdog timeout pozitif bir sayi olmali.")
    runtime.watchdogs[name] = {
        "timeout": float(timeout_seconds),
        "last_monotonic": None,
        "last_wall_time": None,
    }
    return name


def heartbeat(name: str) -> float:
    """Bir üreticinin sağlıklı döngü ürettiğini süreç içi saatle kaydeder."""

    if name not in runtime.watchdogs:
        raise TawntHatasi("Tanimlanmamis watchdog: %s" % name)
    current = time.monotonic()
    runtime.watchdogs[name]["last_monotonic"] = current
    runtime.watchdogs[name]["last_wall_time"] = now()
    return current


def checkWatchdogs(names: Iterable[str] | None = None) -> bool:
    """Eksik veya süresi geçmiş heartbeat varsa hata üretir."""

    selected = tuple(names) if names is not None else tuple(runtime.watchdogs)
    current = time.monotonic()
    errors = []
    for name in selected:
        if name not in runtime.watchdogs:
            errors.append("%s: watchdog tanimli degil" % name)
            continue
        record = runtime.watchdogs[name]
        if record["last_monotonic"] is None:
            errors.append("%s: hic heartbeat gelmedi" % name)
            continue
        age = current - record["last_monotonic"]
        if age > record["timeout"]:
            errors.append(
                "%s: heartbeat %.3f s eski; tavan %.3f s"
                % (name, age, record["timeout"])
            )
    if errors:
        raise TawntHatasi("Watchdog basarisiz:\n  - " + "\n  - ".join(errors))
    return True


def _command_severity() -> str:
    return LATCHED_FAULT if runtime.profil == LIVE else STOP


def _reject_motor_command(reason: str, severe=True):
    runtime.son_komut = (0.0, 0.0)
    if severe and _command_severity() == LATCHED_FAULT:
        latchFault("motor komutu reddedildi", reason)
    else:
        apply_zero_callbacks(reason)
        runtime.susturma = {"sebep": reason, "evre": runtime.evre}
        runtime.sistem_durumu = MUTED
        log_line("%s  STOP  %s" % (now(), reason))
    raise TawntHatasi(reason)


def validateMotorCommand(left, right, phase: str | None = None):
    """Komutu doğrular; fiziksel PWM yazmaz."""

    selected_phase = phase or runtime.evre
    if selected_phase != runtime.evre:
        _reject_motor_command("Komut evresi guncel evreyle ayni degil.")
    if not isMotionAllowed():
        _reject_motor_command("Sistem su anda harekete izin vermiyor.")
    policy = runtime.evreler[selected_phase]
    try:
        checkWatchdogs(policy["required_watchdogs"])
    except TawntHatasi as exc:
        _reject_motor_command(str(exc))

    for label, value in (("left", left), ("right", right)):
        if not _is_number(value) or not math.isfinite(float(value)):
            _reject_motor_command("%s PWM sonlu bir sayi degil." % label)
    left, right = float(left), float(right)

    if abs(left) > policy["max_pwm"] or abs(right) > policy["max_pwm"]:
        _reject_motor_command("PWM evre tavanini asiyor.")
    if not policy["allow_reverse"] and (left < 0 or right < 0):
        _reject_motor_command("Bu evrede ters yon yasak.")
    if left * right < 0 and not policy["allow_pivot"]:
        _reject_motor_command("Bu evrede pivot yasak.")
    if (
        policy["max_difference"] is not None
        and abs(left - right) > policy["max_difference"]
    ):
        _reject_motor_command("Sol/sag PWM farki evre sinirini asiyor.")
    if policy["max_slew"] is not None:
        if (
            abs(left - runtime.son_komut[0]) > policy["max_slew"]
            or abs(right - runtime.son_komut[1]) > policy["max_slew"]
        ):
            _reject_motor_command("PWM degisimi slew sinirini asiyor.", severe=False)

    runtime.son_komut = (left, right)
    return ValidatedMotorCommand(left, right, selected_phase, runtime.profil, now())
