# -*- coding: utf-8 -*-
# revision 13/08/2026 D/M/Y 


#       ⋂
#    o(>)(<)o
#     \ ⋃ /
#      \|/
#       |
#      / \
#     /   \
#  [ - ]  [ - ]


# proudly maintained by startech team
# definitely not forced into doing this

# imported as module 3 tawnt (m3t)

"""3awnt — kritik değer ve hareket güvenliği çekirdeği.

ADIN HİKÂYESİ
    3AWNT iki bağlantılı anlam taşır:

    * 3rd-party Automated Watchdog for Network Threats.
    * Bir AI tokenleştirme hatasında ortaya çıkan ``защит`` parçası; Rusçada
      "korumak/koruma" anlam alanındaki sözcüklerle bağlantılıdır.

    Python modül adı rakamla başlayamadığı için dosyanın adı ``tawnt.py``dir.
    "Network Threats" proje adının açılımıdır; bu modül ağ trafiği, paket veya
    soket izlemez. Böyle bir özellik ayrıca planlanıp test edilmedikçe yoktur.

NE İŞE YARAR
    Kritik değerlerin sınırını, kaynağını, birimini ve bağımlılıklarını tutar;
    çalışma profiline göre başlangıç kapısı kurar; evre politikalarını ve motor
    komutlarını doğrular; ciddi yazılım arızalarını kilitleyebilir.

NE İŞE YARAMAZ
    Ölçüm yapıldığını, insanın kimliğini, fiziksel anahtarın kapalı olduğunu veya
    motorların gerçekten durduğunu kanıtlayamaz. Bunlar beyan ve insan doğrulamasıdır.
    GPIO/PWM yazmaz; gerçek fiziksel kapı gelecekte ``surucu.py``nin sorumluluğudur.


While importing, import tawnt as
"import tawnt as m3t"
"""

from __future__ import annotations

import ast
import datetime
from dataclasses import dataclass
import io
import json
import math
import os
from pathlib import Path
import tempfile
import time
from typing import Any, Iterable


class TawntHatasi(Exception):
    """3awnt bir ihlal buldu; çağıran kod güvenli tarafta kalmalıdır."""


# Değer kaynakları ---------------------------------------------------------
OLCULDU = "olculdu"
VARSAYILDI = "varsayildi"
DEVRALINDI = "devralindi"
_KAYNAKLAR = (OLCULDU, VARSAYILDI, DEVRALINDI)

# Çalışma profilleri -------------------------------------------------------
OFFLINE = "OFFLINE"
BENCH = "BENCH"
LIVE = "LIVE"
_PROFILLER = (OFFLINE, BENCH, LIVE)

# Değer yaşam döngüsü ------------------------------------------------------
DEFINED = "DEFINED"
RECORDED = "RECORDED"
VALIDATED = "VALIDATED"
STALE = "STALE"
SEALED = "SEALED"

# Sistem durumları ---------------------------------------------------------
BOOT = "BOOT"
VALIDATING = "VALIDATING"
READY_UNARMED = "READY_UNARMED"
ARMED = "ARMED"
MUTED = "MUTED"
LATCHED_FAULT = "LATCHED_FAULT"

# Hata seviyeleri ----------------------------------------------------------
WARNING = "WARNING"
STOP = "STOP"


@dataclass(frozen=True)
class ValidatedMotorCommand:
    """Immutable motor command produced by the TAWNT validation boundary."""

    left: float
    right: float
    phase: str
    profile: str
    timestamp: str


# Bellek kayıtları ---------------------------------------------------------
_defter: dict[str, dict[str, Any]] = {}
_ikizler: list[tuple[str, str]] = []
_zincirler: list[tuple[Any, ...]] = []
_bagimliliklar: dict[str, set[str]] = {}
_olcum_profilleri: dict[str, set[str]] = {}

_profil = OFFLINE
_sistem_durumu = BOOT
_muhur = False
_validated_once = False
_armed = False
_evre: str | None = None
_evreler: dict[str, dict[str, Any]] = {}
_watchdogs: dict[str, dict[str, Any]] = {}
_son_komut = (0.0, 0.0)

_kilit: dict[str, Any] | None = None
_susturma: dict[str, Any] | None = None
_kapatma_geri: list[Any] = []
_gunluk_yolu = "tawnt_guvenlik.log"
_fault_store_path: Path | None = None


__all__ = [
    # Hata ve sonuç nesnesi
    "TawntHatasi", "ValidatedMotorCommand",
    # Kaynaklar
    "OLCULDU", "VARSAYILDI", "DEVRALINDI",
    # Profiller
    "OFFLINE", "BENCH", "LIVE",
    # Değer durumları
    "DEFINED", "RECORDED", "VALIDATED", "STALE", "SEALED",
    # Sistem durumları ve seviyeler
    "BOOT", "VALIDATING", "READY_UNARMED", "ARMED", "MUTED",
    "LATCHED_FAULT", "WARNING", "STOP",
    # V2 API
    "defineValue", "recordValue", "dependsOn", "requireMeasured",
    "validateBeforeStart", "seal", "valueState", "systemState",
    "definePhase", "enterPhase", "validatePhase", "arm", "disarm",
    "isMotionAllowed", "validateMotorCommand",
    "defineWatchdog", "heartbeat", "checkWatchdogs",
    "configureFaultStore", "latchFault", "resetFault",
    "scanDirectMotorWrites",
    # V1 uyumluluğu
    "introduce", "acquire", "preacquire", "identifyRuntimeType",
    "IsTwinOf", "siblingIntAppr", "differenceSkew", "deger", "report",
    "sifirla", "declareUnexpectedSigint", "flushPWM", "evreDegisti",
    "pwmSerbestMi", "onShutdown", "kilitDurumu",
]


def _now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def _require_name(ad: str) -> dict[str, Any]:
    if ad not in _defter:
        raise TawntHatasi("'%s' tanitilmamis." % ad)
    return _defter[ad]


def _require_unsealed() -> None:
    if _muhur:
        raise TawntHatasi(
            "3awnt defteri muhurlu; kosu sirasinda kritik deger degistirilemez."
        )


def _invalidate_startup_validation() -> None:
    """Doğrulama sonrası değişen yapı için yeniden başlangıç kontrolü ister."""

    global _validated_once, _sistem_durumu
    if _validated_once:
        _validated_once = False
        if _kilit is None:
            _sistem_durumu = VALIDATING


def _validate_profile(profile: str) -> str:
    if profile not in _PROFILLER:
        raise TawntHatasi(
            "Bilinmeyen profil %r; beklenen: %s"
            % (profile, ", ".join(_PROFILLER))
        )
    return profile


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_finite_number(value: Any) -> bool:
    return _is_number(value) and math.isfinite(float(value))


def _compare_bound(ad: str, value: Any, bound: Any, label: str, op) -> None:
    if bound is None:
        return
    try:
        failed = op(value, bound)
    except TypeError as exc:
        raise TawntHatasi(
            "'%s': %s siniri %r ile deger %r karsilastirilamiyor."
            % (ad, label, bound, value)
        ) from exc
    if failed:
        direction = "altinda" if label == "min" else "ustunde"
        raise TawntHatasi(
            "'%s' = %r, %s siniri (%r) %s."
            % (ad, value, label, bound, direction)
        )


def _record_dependency_snapshot(ad: str) -> None:
    kayit = _defter[ad]
    kayit["dependency_snapshot"] = {
        dep: _defter[dep]["revision"] for dep in _bagimliliklar.get(ad, set())
    }


def _invalidate_dependents(changed: str, visited: set[str] | None = None) -> None:
    if visited is None:
        visited = set()
    if changed in visited:
        return
    visited.add(changed)

    for dependent, dependencies in _bagimliliklar.items():
        if changed not in dependencies or dependent not in _defter:
            continue
        kayit = _defter[dependent]
        if kayit["atandi"] and kayit["state"] in (VALIDATED, SEALED):
            kayit["state"] = STALE
            kayit["validated_profile"] = None
        _invalidate_dependents(dependent, visited)


def _has_dependency_path(start: str, target: str, visited=None) -> bool:
    if start == target:
        return True
    if visited is None:
        visited = set()
    if start in visited:
        return False
    visited.add(start)
    return any(
        _has_dependency_path(dep, target, visited)
        for dep in _bagimliliklar.get(start, set())
    )


def reset() -> None:
    """Remove all values, phases, and watchdogs; reset system state to BOOT."""
   

    global _profil, _sistem_durumu, _muhur, _validated_once, _armed, _evre
    global _son_komut, _kilit, _susturma, _fault_store_path

    _defter.clear()
    _ikizler.clear()
    _zincirler.clear()
    _bagimliliklar.clear()
    _olcum_profilleri.clear()
    _evreler.clear()
    _watchdogs.clear()
    _kapatma_geri.clear()

    _profil = OFFLINE
    _sistem_durumu = BOOT
    _muhur = False
    _validated_once = False
    _armed = False
    _evre = None
    _son_komut = (0.0, 0.0)
    _kilit = None
    _susturma = None
    _fault_store_path = None


# Değer yaşam döngüsü ======================================================
def defineValue(
    ad: str,
    min=None,
    max=None,
    preferred=None,
    aciklama: str = "",
    critical: bool = False,
):
    """Defines the values and records it for usage.
    
    Kinda similar to x=y, but with more metadata and validation."""

    _require_unsealed()
    _invalidate_startup_validation()
    if not isinstance(ad, str) or not ad.strip():
        raise TawntHatasi("Deger adi bos olmayan bir yazi olmali.")
    if ad in _defter:
        raise TawntHatasi("'%s' zaten tanitilmis." % ad)
    for label, value in (("min", min), ("max", max), ("preferred", preferred)):
        if _is_number(value) and not _is_finite_number(value):
            raise TawntHatasi("'%s': %s sonlu bir sayi olmali." % (ad, label))
    if min is not None and max is not None and min > max:
        raise TawntHatasi("'%s': min (%r) max'tan (%r) buyuk." % (ad, min, max))
    if preferred is not None:
        if min is not None and preferred < min:
            raise TawntHatasi("'%s': preferred min'in altinda." % ad)
        if max is not None and preferred > max:
            raise TawntHatasi("'%s': preferred max'i geciyor." % ad)

    _defter[ad] = {
        "min": min,
        "max": max,
        "preferred": preferred,
        "aciklama": aciklama,
        "critical": bool(critical),
        "deger": None,
        "kaynak": None,
        "kim": None,
        "tarih": None,
        "notu": "",
        "tip": None,
        "atandi": False,
        "state": DEFINED,
        "revision": 0,
        "validated_profile": None,
        "dependency_snapshot": {},
    }
    _bagimliliklar.setdefault(ad, set())
    if critical:
        _olcum_profilleri.setdefault(ad, set()).add(LIVE)
    return ad


def introduce(ad, min=None, max=None, preferred=None, aciklama=""):
    """Calls defineValue."""

    return defineValue(ad, min, max, preferred, aciklama)


def recordValue(
    ad: str,
    deger,
    source=VARSAYILDI,
    human=None,
    date=None,
    note="",
    **legacy,
):
    """Records a defined value with its source and updates dependencies."""

    global _sistem_durumu, _validated_once
    _require_unsealed()

    # Türkçe v1 anahtarlarını da kabul et.
    source = legacy.pop("kaynak", source)
    human = legacy.pop("kim", human)
    date = legacy.pop("tarih", date)
    note = legacy.pop("notu", note)
    if legacy:
        raise TawntHatasi("Bilinmeyen recordValue alanlari: %s" % sorted(legacy))

    kayit = _require_name(ad)
    if source not in _KAYNAKLAR:
        raise TawntHatasi(
            "'%s': kaynak %r degil; %s olmali."
            % (ad, source, ", ".join(_KAYNAKLAR))
        )
    if _is_number(deger) and not _is_finite_number(deger):
        raise TawntHatasi("'%s': deger sonlu bir sayi olmali." % ad)
    _compare_bound(ad, deger, kayit["min"], "min", lambda x, y: x < y)
    _compare_bound(ad, deger, kayit["max"], "max", lambda x, y: x > y)
    if source == OLCULDU and not date:
        raise TawntHatasi(
            "'%s' olculdu deniyor ama tarih yok. Tarihsiz olcum, olcum degildir."
            % ad
        )

    kayit.update(
        deger=deger,
        kaynak=source,
        kim=human,
        tarih=date,
        notu=note,
        atandi=True,
        state=RECORDED,
        revision=kayit["revision"] + 1,
        validated_profile=None,
        dependency_snapshot={},
    )
    _invalidate_dependents(ad)
    _validated_once = False
    if _sistem_durumu in (READY_UNARMED, ARMED):
        _sistem_durumu = VALIDATING
    return deger


def acquire(ad, deger, kaynak=VARSAYILDI, kim=None, tarih=None, notu=""):
    """Calls recordValue"""

    return recordValue(
        ad, deger, source=kaynak, human=kim, date=tarih, note=notu
    )


def retint(ad):
    """Returns the value of a defined variable, raising an error if it is not assigned."""
    kayit = _require_name(ad)
    if not kayit["atandi"]:
        raise TawntHatasi("'%s' henuz atanmadi." % ad)
    return kayit["deger"]


def valueState(ad: str) -> str:
    """Returns the state of the variable given by name."""
    return _require_name(ad)["state"]


def identifyRuntimeType(ad: str, tip: str):
    _require_unsealed()
    _invalidate_startup_validation()
    _require_name(ad)["tip"] = tip
    return ad


def dependsOn(dependent: str, *dependencies: str) -> bool:
    """Invalidates the dependent variable if dependencies change within runtime."""

    _require_unsealed()
    _invalidate_startup_validation()
    _require_name(dependent)
    if not dependencies:
        raise TawntHatasi("dependsOn en az bir bagimlilik ister.")

    for dependency in dependencies:
        _require_name(dependency)
        if dependency == dependent or _has_dependency_path(dependency, dependent):
            raise TawntHatasi(
                "Bagimlilik dongusu: %s -> %s" % (dependent, dependency)
            )

    _bagimliliklar.setdefault(dependent, set()).update(dependencies)
    return True


def IsTwinOf(a: str, b: str) -> bool:
    """Checks if two variables are twins... or related to each other, whatever..."""

    _require_name(a)
    _require_name(b)
    if (a, b) not in _ikizler and (b, a) not in _ikizler:
        _ikizler.append((a, b))
    if b not in _bagimliliklar.get(a, set()):
        dependsOn(a, b)
    if a not in _bagimliliklar.get(b, set()):
        # Karşılıklı bağımlılık normal döngü denetimine takılacağı için ikiz özel durumdur.
        _bagimliliklar.setdefault(b, set()).add(a)
    return _defter[a]["atandi"] and _defter[b]["atandi"]


def requireMeasured(*names: str, profiles: Iterable[str] = (LIVE,)) -> bool:
    """Checks if a variable has been measured under the specified profiles."""

    _require_unsealed()
    _invalidate_startup_validation()
    profile_set = {_validate_profile(profile) for profile in profiles}
    for name in names:
        _require_name(name)
        _olcum_profilleri.setdefault(name, set()).update(profile_set)
    return True


_OPLAR = {
    "<": lambda x, y: x < y,
    "<=": lambda x, y: x <= y,
    ">": lambda x, y: x > y,
    ">=": lambda x, y: x >= y,
    "==": lambda x, y: x == y,
}


def _zinciri_dogrula(zincir) -> bool:
    sorunlar = []
    for i in range(0, len(zincir) - 2, 2):
        sol_ad, op, sag_ad = zincir[i], zincir[i + 1], zincir[i + 2]
        if op not in _OPLAR:
            raise TawntHatasi("Bilinmeyen operator: %r" % op)
        sol, sag = _require_name(sol_ad), _require_name(sag_ad)
        if not (sol["atandi"] and sag["atandi"]):
            continue
        if sol["tip"] and sag["tip"] and sol["tip"] != sag["tip"]:
            raise TawntHatasi(
                "'%s' (%s) ile '%s' (%s) farkli tipte; karsilastirilamaz."
                % (sol_ad, sol["tip"], sag_ad, sag["tip"])
            )
        if not _OPLAR[op](sol["deger"], sag["deger"]):
            sorunlar.append(
                "%s (%r) %s %s (%r) DEGIL"
                % (sol_ad, sol["deger"], op, sag_ad, sag["deger"])
            )
    if sorunlar:
        raise TawntHatasi("Kardes sirasi bozuk:\n  - " + "\n  - ".join(sorunlar))
    return True


def siblingIntAppr(*zincir) -> bool:
    """Handles multiple mathematical relations between sibling variables, e.g., a < b > c."""
    _require_unsealed()
    _invalidate_startup_validation()
    if len(zincir) < 3 or len(zincir) % 2 == 0:
        raise TawntHatasi(
            "siblingIntAppr: ad, op, ad, op, ad ... bicimi bekleniyor."
        )
    kayit = tuple(zincir)
    if kayit not in _zincirler:
        _zincirler.append(kayit)
    return _zinciri_dogrula(kayit)


def _collect_value_errors(names: Iterable[str], profile=None, strict_v2=False):
    errors = []
    for ad in names:
        if ad not in _defter:
            errors.append("%s: hic tanitilmadi" % ad)
            continue
        kayit = _defter[ad]
        if not kayit["atandi"]:
            errors.append("%s: deger atanmadi" % ad)
            continue
        try:
            _compare_bound(ad, kayit["deger"], kayit["min"], "min", lambda x, y: x < y)
            _compare_bound(ad, kayit["deger"], kayit["max"], "max", lambda x, y: x > y)
        except TawntHatasi as exc:
            errors.append(str(exc))

        if strict_v2 and kayit["state"] == STALE:
            errors.append("%s: bagimliligi degisti; deger STALE" % ad)
        if profile in _olcum_profilleri.get(ad, set()) and kayit["kaynak"] != OLCULDU:
            errors.append("%s: %s profili OLCULDU kaynak istiyor" % (ad, profile))

        if strict_v2:
            for dep in _bagimliliklar.get(ad, set()):
                dep_record = _defter.get(dep)
                if not dep_record or not dep_record["atandi"]:
                    errors.append("%s: bagimliligi %s atanmadi" % (ad, dep))

    for a, b in _ikizler:
        for x, y in ((a, b), (b, a)):
            if x in names and _defter[x]["atandi"] and not _defter[y]["atandi"]:
                errors.append("%s atanmis ama ikizi %s atanmamis" % (x, y))
    return errors


def preacquire(*names: str) -> bool:
    """V1 açılış kontrolü; kaynak profili ve STALE durumunu zorlamaz."""

    errors = _collect_value_errors(names, strict_v2=False)
    if errors:
        raise TawntHatasi("preacquire basarisiz:\n  - " + "\n  - ".join(errors))
    for chain in _zincirler:
        _zinciri_dogrula(chain)
    return True


def validateBeforeStart(*names: str, profile: str = OFFLINE):
    """Seçilen profil için bütün zorunlu değerleri doğrular."""

    global _profil, _sistem_durumu, _validated_once, _armed
    _validate_profile(profile)
    if _kilit is not None:
        _sistem_durumu = LATCHED_FAULT
        raise TawntHatasi("Ciddi ariza kilidi varken baslangic dogrulanamaz.")
    if profile == LIVE and _fault_store_path is None:
        raise TawntHatasi("LIVE profili kalici fault-store yapilandirmasi ister.")

    _profil = profile
    _sistem_durumu = VALIDATING
    _armed = False
    selected = tuple(names) if names else tuple(_defter)
    errors = _collect_value_errors(selected, profile=profile, strict_v2=True)
    for chain in _zincirler:
        try:
            _zinciri_dogrula(chain)
        except TawntHatasi as exc:
            errors.append(str(exc))
    if errors:
        raise TawntHatasi(
            "validateBeforeStart basarisiz:\n  - " + "\n  - ".join(dict.fromkeys(errors))
        )

    for ad in selected:
        kayit = _defter[ad]
        kayit["state"] = VALIDATED
        kayit["validated_profile"] = profile
        _record_dependency_snapshot(ad)
    _validated_once = True
    _sistem_durumu = READY_UNARMED
    return {
        "profile": profile,
        "validated": selected,
        "state": _sistem_durumu,
    }


def seal() -> bool:
    """Doğrulanmış değerleri koşu boyunca değiştirilemez yapar."""

    global _muhur
    if _sistem_durumu not in (READY_UNARMED, ARMED):
        raise TawntHatasi("seal icin once validateBeforeStart gecmeli.")
    invalid = [
        ad for ad, kayit in _defter.items()
        if kayit["atandi"] and kayit["state"] not in (VALIDATED, SEALED)
    ]
    if invalid:
        raise TawntHatasi("Dogrulanmamis degerler muhurlenemez: %s" % invalid)
    for kayit in _defter.values():
        if kayit["atandi"]:
            kayit["state"] = SEALED
    _muhur = True
    return True


# Perspektif yardımcı yöntemi ==============================================
def differenceSkew(koseler, kareBoyutu, snap=1):
    if len(koseler) != 4:
        raise TawntHatasi("differenceSkew: dort kose bekleniyor.")
    g, y = kareBoyutu
    sx, sy = koseler[3]
    dx, dy = g - sx, y - sy
    if dx == 0 and dy == 0:
        return list(koseler), False
    if abs(dx) <= snap and abs(dy) <= snap:
        yeni = list(koseler)
        yeni[3] = (g, y)
        return yeni, True
    raise TawntHatasi(
        "Sag-alt kose (%d,%d), kare %dx%d; %d px yatay, %d px dikey uzakta. "
        "3awnt tek koseyi tasiyarak dortgeni deforme etmez."
        % (sx, sy, g, y, dx, dy)
    )


# Evre ve hareket ==========================================================
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
    if name in _evreler:
        raise TawntHatasi("Evre zaten tanimli: %s" % name)
    required_values = tuple(required_values)
    required_watchdogs = tuple(required_watchdogs)
    for value in required_values:
        _require_name(value)
    for watchdog in required_watchdogs:
        if watchdog not in _watchdogs:
            raise TawntHatasi("Tanimlanmamis watchdog: %s" % watchdog)
    for label, value in (
        ("max_pwm", max_pwm),
        ("max_difference", max_difference),
        ("max_slew", max_slew),
    ):
        if value is not None and (not _is_finite_number(value) or value < 0):
            raise TawntHatasi("%s negatif olmayan bir sayi olmali." % label)
    _evreler[name] = {
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
    global _susturma, _sistem_durumu, _son_komut
    if phase not in _evreler:
        raise TawntHatasi("Tanimlanmamis evre: %s" % phase)
    policy = _evreler[phase]
    errors = _collect_value_errors(
        policy["required_values"], profile=_profil, strict_v2=True
    )
    for ad in policy["required_values"]:
        state = _defter[ad]["state"]
        if state not in (VALIDATED, SEALED):
            errors.append("%s: evre icin dogrulanmamis (%s)" % (ad, state))
    try:
        checkWatchdogs(policy["required_watchdogs"])
    except TawntHatasi as exc:
        errors.append(str(exc))
    if errors:
        details = "\n  - ".join(errors)
        _son_komut = (0.0, 0.0)
        if _armed and _profil == LIVE:
            latchFault("evre dogrulamasi basarisiz", details)
        elif _kilit is None:
            _apply_zero_callbacks("evre dogrulamasi basarisiz")
            _susturma = {
                "sebep": "evre dogrulamasi basarisiz",
                "evre": phase,
                "kind": "phase_validation",
            }
            _sistem_durumu = MUTED
        raise TawntHatasi("validatePhase basarisiz:\n  - " + details)
    if (
        _susturma is not None
        and _susturma.get("kind") == "phase_validation"
        and _susturma.get("evre") == phase
    ):
        _susturma = None
        if _armed:
            _sistem_durumu = ARMED
        elif _validated_once:
            _sistem_durumu = READY_UNARMED
        else:
            _sistem_durumu = VALIDATING
    return True


def enterPhase(phase: str) -> bool:
    """İzin verilen yeni evreye girer; geçici susturma farklı evrede kalkar."""

    global _evre, _susturma, _sistem_durumu
    if phase not in _evreler:
        raise TawntHatasi("Tanimlanmamis evre: %s" % phase)
    policy = _evreler[phase]
    if policy["allowed_from"] is not None and _evre not in policy["allowed_from"]:
        raise TawntHatasi("%r evresinden %r evresine gecis yasak." % (_evre, phase))
    validatePhase(phase)
    previous = _evre
    _evre = phase
    if _susturma is not None and _susturma.get("evre") != phase:
        _susturma = None
    if _kilit is not None:
        _sistem_durumu = LATCHED_FAULT
    elif _susturma is not None:
        _sistem_durumu = MUTED
    elif _armed:
        _sistem_durumu = ARMED
    elif _validated_once:
        _sistem_durumu = READY_UNARMED
    _gunluge_yaz("%s  EVRE  %s -> %s" % (_now(), previous, phase))
    return isMotionAllowed()


def evreDegisti(yeniEvre):
    """V1 uyumluluk adı; tanımlı evrede ``enterPhase`` kullanılır."""

    global _susturma, _sistem_durumu, _evre
    if yeniEvre in _evreler:
        return enterPhase(yeniEvre)
    # Eski kodda evre politikası yoktu; yalnız geçici susturma kalkıyordu.
    _evre = yeniEvre
    if _susturma is not None and _susturma.get("evre") != yeniEvre:
        _susturma = None
    if _kilit is not None:
        _sistem_durumu = LATCHED_FAULT
    elif _armed:
        _sistem_durumu = ARMED
    elif _validated_once:
        _sistem_durumu = READY_UNARMED
    else:
        _sistem_durumu = BOOT
    return isMotionAllowed()


def arm(
    human: str,
    *,
    live_hardware_authorized: bool = False,
    final_confirmation: bool = False,
) -> bool:
    """Doğrulanmış sistemi açık insan beyanıyla silahlandırır."""

    global _armed, _sistem_durumu
    if _kilit is not None:
        raise TawntHatasi("Ciddi kilit varken arm reddedildi.")
    if _sistem_durumu != READY_UNARMED:
        raise TawntHatasi("arm icin sistem READY_UNARMED olmali.")
    if not isinstance(human, str) or not human.strip():
        raise TawntHatasi("arm icin insan adi/beyani gerekir.")
    if _evre is None:
        raise TawntHatasi("arm icin once bir evre secilmeli.")
    validatePhase(_evre)
    if _profil == LIVE:
        if _fault_store_path is None:
            raise TawntHatasi("LIVE arm kalici fault-store ister.")
        if not live_hardware_authorized or not final_confirmation:
            raise TawntHatasi(
                "LIVE arm icin donanim yetkisi ve son onay gerekir."
            )
    if not _muhur:
        seal()
    _armed = True
    _sistem_durumu = ARMED
    _gunluge_yaz("%s  ARM  %s  profil=%s" % (_now(), human, _profil))
    return True


def disarm(reason: str = "insan istegi") -> bool:
    """Send a DISARM request to the code heartbeat system to handle DISARM events."""
    global _armed, _sistem_durumu, _son_komut
    _apply_zero_callbacks(reason)
    _armed = False
    _son_komut = (0.0, 0.0)
    if _kilit is not None:
        _sistem_durumu = LATCHED_FAULT
    elif _validated_once:
        _sistem_durumu = READY_UNARMED
    else:
        _sistem_durumu = BOOT
    _gunluge_yaz("%s  DISARM  %s" % (_now(), reason))
    return True


def systemState() -> str:
    """Returns which state is currently active."""
    return _sistem_durumu


def isMotionAllowed() -> bool:
    """Is this car ARMED and not blocked via m3t?"""
    if not _armed or _sistem_durumu != ARMED:
        return False
    if _kilit is not None or _susturma is not None or _evre is None:
        return False
    policy = _evreler.get(_evre)
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
    if name in _watchdogs:
        raise TawntHatasi("Watchdog zaten tanimli: %s" % name)
    if not _is_finite_number(timeout_seconds) or timeout_seconds <= 0:
        raise TawntHatasi("Watchdog timeout pozitif bir sayi olmali.")
    _watchdogs[name] = {
        "timeout": float(timeout_seconds),
        "last_monotonic": None,
        "last_wall_time": None,
    }
    return name


def heartbeat(name: str) -> float:
    """Bir üreticinin sağlıklı döngü ürettiğini süreç içi saatle kaydeder."""

    if name not in _watchdogs:
        raise TawntHatasi("Tanimlanmamis watchdog: %s" % name)
    now = time.monotonic()
    _watchdogs[name]["last_monotonic"] = now
    _watchdogs[name]["last_wall_time"] = _now()
    return now


def checkWatchdogs(names: Iterable[str] | None = None) -> bool:
    """Eksik veya süresi geçmiş heartbeat varsa hata üretir."""

    selected = tuple(names) if names is not None else tuple(_watchdogs)
    now = time.monotonic()
    errors = []
    for name in selected:
        if name not in _watchdogs:
            errors.append("%s: watchdog tanimli degil" % name)
            continue
        record = _watchdogs[name]
        if record["last_monotonic"] is None:
            errors.append("%s: hic heartbeat gelmedi" % name)
            continue
        age = now - record["last_monotonic"]
        if age > record["timeout"]:
            errors.append(
                "%s: heartbeat %.3f s eski; tavan %.3f s"
                % (name, age, record["timeout"])
            )
    if errors:
        raise TawntHatasi("Watchdog basarisiz:\n  - " + "\n  - ".join(errors))
    return True


def _command_severity() -> str:
    return LATCHED_FAULT if _profil == LIVE else STOP


def _reject_motor_command(reason: str, severe=True):
    global _susturma, _sistem_durumu, _son_komut
    _son_komut = (0.0, 0.0)
    if severe and _command_severity() == LATCHED_FAULT:
        latchFault("motor komutu reddedildi", reason)
    else:
        _apply_zero_callbacks(reason)
        _susturma = {"sebep": reason, "evre": _evre}
        _sistem_durumu = MUTED
        _gunluge_yaz("%s  STOP  %s" % (_now(), reason))
    raise TawntHatasi(reason)


def validateMotorCommand(left, right, phase: str | None = None):
    """Check if this PWM request is safe and in understandable range."""

    global _son_komut
    selected_phase = phase or _evre
    if selected_phase != _evre:
        _reject_motor_command("Komut evresi guncel evreyle ayni degil.")
    if not isMotionAllowed():
        _reject_motor_command("Sistem su anda harekete izin vermiyor.")
    policy = _evreler[selected_phase]
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
            abs(left - _son_komut[0]) > policy["max_slew"]
            or abs(right - _son_komut[1]) > policy["max_slew"]
        ):
            _reject_motor_command("PWM degisimi slew sinirini asiyor.", severe=False)

    _son_komut = (left, right)
    return ValidatedMotorCommand(left, right, selected_phase, _profil, _now())


# Kapatma, susturma ve kalıcı kilit ========================================
def onShutdown(fn):
    if fn not in _kapatma_geri:
        _kapatma_geri.append(fn)
    return fn


def _gunluge_yaz(satir: str) -> None:
    try:
        with io.open(_gunluk_yolu, "a", encoding="utf-8") as handle:
            handle.write(satir + "\n")
    except Exception:
        pass


def _apply_zero_callbacks(reason: str) -> None:
    for fn in tuple(_kapatma_geri):
        try:
            fn()
        except Exception as exc:
            _gunluge_yaz("%s  CALLBACK_HATA  %r  %s" % (_now(), exc, reason))


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
    """Checks the fault store path and initializes it if necessary."""

    global _fault_store_path, _kilit, _sistem_durumu, _armed
    resolved = Path(path).expanduser().resolve()
    if not resolved.parent.exists():
        raise TawntHatasi("Fault-store klasoru yok: %s" % resolved.parent)
    _fault_store_path = resolved
    if not resolved.exists():
        return str(resolved)
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or "active" not in data:
            raise ValueError("active alani yok")
    except Exception as exc:
        _kilit = {
            "sebep": "fault-store bozuk",
            "ayrinti": str(exc),
            "zaman": _now(),
            "profile": _profil,
        }
        _armed = False
        _sistem_durumu = LATCHED_FAULT
        return str(resolved)
    if data.get("active"):
        _kilit = data.get("fault") or {
            "sebep": "kalici fault-store aktif",
            "ayrinti": "ayrinti yok",
            "zaman": _now(),
            "profile": _profil,
        }
        _armed = False
        _sistem_durumu = LATCHED_FAULT
    return str(resolved)


def _persist_active_fault() -> None:
    if _fault_store_path is None:
        return
    _atomic_json_write(
        _fault_store_path,
        {"version": 1, "active": True, "fault": _kilit},
    )


def latchFault(reason: str, details: str = "", command=None):
    """Invalidate the integrity of the system and cause an emergency shutdown."""

    global _kilit, _armed, _sistem_durumu, _son_komut
    _apply_zero_callbacks(reason)
    _son_komut = (0.0, 0.0)
    if _kilit is None:
        _kilit = {
            "sebep": reason,
            "ayrinti": details,
            "zaman": _now(),
            "profile": _profil,
            "command": command,
        }
    _armed = False
    _sistem_durumu = LATCHED_FAULT
    try:
        _persist_active_fault()
    except TawntHatasi as exc:
        _gunluge_yaz("%s  FAULT_STORE_HATA  %s" % (_now(), exc))
    _gunluge_yaz("%s  KILIT  %s  %s" % (_kilit["zaman"], reason, details))
    return dict(_kilit)


def declareUnexpectedSigint(sebep, ayrinti=""):
    """Calls latchFault with a SIGINT reason."""

    return latchFault(sebep, ayrinti)


def flushPWM(sebep, evre=None):
    """Disable PWM output compeletely."""

    global _susturma, _sistem_durumu, _son_komut
    _apply_zero_callbacks(sebep)
    _son_komut = (0.0, 0.0)
    if _kilit is None:
        _susturma = {"sebep": sebep, "evre": evre}
        _sistem_durumu = MUTED
    _gunluge_yaz("%s  SUSTUR (%s)  %s" % (_now(), evre, sebep))
    return True


def resetFault(human: str, *, motor_power_off: bool = False) -> bool:
    """Resets the fault state and restores integrity for human operator."""

    global _kilit, _armed, _sistem_durumu, _susturma, _son_komut, _muhur
    global _validated_once
    if not isinstance(human, str) or not human.strip():
        raise TawntHatasi("resetFault insan adi/beyani ister.")
    if motor_power_off is not True:
        raise TawntHatasi("resetFault motor gucu kapali beyanini ister.")
    if _kilit is None:
        raise TawntHatasi("Temizlenecek ciddi kilit yok.")

    previous = dict(_kilit)
    _apply_zero_callbacks("fault reset oncesi")
    reset_record = {
        "version": 1,
        "active": False,
        "previous_fault": previous,
        "reset": {"human": human.strip(), "time": _now(), "motor_power_off": True},
    }
    if _fault_store_path is not None:
        _atomic_json_write(_fault_store_path, reset_record)
    _kilit = None
    _susturma = None
    _armed = False
    _son_komut = (0.0, 0.0)
    _muhur = False
    _validated_once = False
    for kayit in _defter.values():
        if kayit["atandi"]:
            kayit["state"] = RECORDED
            kayit["validated_profile"] = None
    _sistem_durumu = VALIDATING
    _gunluge_yaz("%s  RESET  %s" % (_now(), human.strip()))
    return True


def lockStatus():
    """Is this car locked?"""
    return dict(_kilit) if _kilit else None


# Statik doğrudan motor erişimi taraması ===================================
_DIRECT_MOTOR_CALL_NAMES = {
    "_writePwm", "write_pwm", "motorlara_yaz", "set_pwm", "setMotor",
    "ChangeDutyCycle", "PWMOutputDevice",
}
_GATED_MOTOR_CALL_NAMES = {"applyMotorCommand", "validateMotorCommand"}
_DIRECT_ASSIGN_ATTRS = {"value", "duty_cycle", "pwm"}
_MOTOR_HINTS = {"motor", "pwm", "left", "right", "sol", "sag", "surucu"}


def _call_name(node) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _root_name(node) -> str:
    while isinstance(node, ast.Attribute):
        node = node.value
    return node.id.lower() if isinstance(node, ast.Name) else ""


def scanDirectMotorWrites(root, allowed_files=("surucu.py", "tawnt.py", "tawnttest.py")):
    """Check for hardcoded direct motor/PWM writes in the source code, flags them for m3t integration.

    This is not fool-proof and will not replace Find&Replace.
    """

    base = Path(root)
    if not base.exists():
        raise TawntHatasi("Tarama yolu yok: %s" % base)
    allowed = {str(name).replace("\\", "/") for name in allowed_files}
    files = [base] if base.is_file() else sorted(base.rglob("*.py"))
    violations = []

    for path in files:
        relative = path.name if base.is_file() else path.relative_to(base).as_posix()
        if relative in allowed or path.name in allowed:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        except (OSError, SyntaxError) as exc:
            violations.append({"path": relative, "line": 0, "reason": str(exc)})
            continue

        for node in ast.walk(tree):
            if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                targets = (
                    node.targets if isinstance(node, ast.Assign) else [node.target]
                )
                for target in targets:
                    if not isinstance(target, ast.Attribute):
                        continue
                    root_name = _root_name(target)
                    if (
                        target.attr in _DIRECT_ASSIGN_ATTRS
                        and any(hint in root_name for hint in _MOTOR_HINTS)
                    ):
                        violations.append({
                            "path": relative,
                            "line": node.lineno,
                            "reason": "dogrudan motor/PWM alan atamasi",
                        })
            elif isinstance(node, ast.Call):
                name = _call_name(node.func)
                if name not in _DIRECT_MOTOR_CALL_NAMES | _GATED_MOTOR_CALL_NAMES:
                    continue
                numeric = [
                    arg for arg in node.args
                    if isinstance(arg, ast.Constant)
                    and isinstance(arg.value, (int, float))
                    and not isinstance(arg.value, bool)
                ]
                if name in _GATED_MOTOR_CALL_NAMES and not numeric:
                    continue
                violations.append({
                    "path": relative,
                    "line": node.lineno,
                    "reason": (
                        "dogrudan motor/PWM cagrisi; hardcoded sayi var"
                        if numeric
                        else "dogrudan motor/PWM cagrisi"
                    ),
                })
    return violations


# Rapor ====================================================================
def report() -> str:
    """Returns the latest state."""
    if not _defter:
        return "tawnt: defter bos."
    lines = [
        "tawnt defteri — %s" % datetime.date.today().strftime("%d.%m.%Y"),
        "(bu bir beyan listesidir, kanit degil)",
        "profil=%s sistem=%s evre=%s" % (_profil, _sistem_durumu, _evre),
        "",
        "%-10s %-22s %-12s %-10s %-10s %s"
        % ("KAYNAK", "AD", "DEGER", "TIP", "DURUM", "NOT"),
        "-" * 96,
    ]
    order = {OLCULDU: 0, DEVRALINDI: 1, VARSAYILDI: 2, None: 3}
    for ad in sorted(_defter, key=lambda item: (order[_defter[item]["kaynak"]], item)):
        kayit = _defter[ad]
        lines.append(
            "%-10s %-22s %-12s %-10s %-10s %s"
            % (
                (kayit["kaynak"] or "ATANMADI").upper(),
                ad,
                repr(kayit["deger"]) if kayit["atandi"] else "-",
                kayit["tip"] or "-",
                kayit["state"],
                ((kayit["tarih"] or "") + " " + (kayit["notu"] or "")).strip(),
            )
        )
    not_measured = [ad for ad in _defter if _defter[ad]["kaynak"] != OLCULDU]
    lines.extend(["", "olculmemis/atanmamis: %d" % len(not_measured)])
    return "\n".join(lines)
