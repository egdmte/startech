"""Critical-value registry, provenance, dependency, and validation rules."""

from __future__ import annotations

import datetime
import math
from typing import Any, Iterable

from .model import (
    ARMED,
    DEFINED,
    DEVRALINDI,
    KAYNAKLAR,
    LATCHED_FAULT,
    LIVE,
    OLCULDU,
    OFFLINE,
    PROFILLER,
    READY_UNARMED,
    RECORDED,
    SEALED,
    STALE,
    VALIDATED,
    VALIDATING,
    VARSAYILDI,
    TawntHatasi,
)
from .runtime import runtime


def _require_name(ad: str) -> dict[str, Any]:
    if ad not in runtime.defter:
        raise TawntHatasi("'%s' tanitilmamis." % ad)
    return runtime.defter[ad]


def _require_unsealed() -> None:
    if runtime.muhur:
        raise TawntHatasi(
            "TAWNT defteri muhurlu; kosu sirasinda kritik deger degistirilemez."
        )


def _invalidate_startup_validation() -> None:
    """Doğrulama sonrası değişen yapı için yeniden başlangıç kontrolü ister."""

    if runtime.validated_once:
        runtime.validated_once = False
        if runtime.kilit is None:
            runtime.sistem_durumu = VALIDATING


def _validate_profile(profile: str) -> str:
    if profile not in PROFILLER:
        raise TawntHatasi(
            "Bilinmeyen profil %r; beklenen: %s"
            % (profile, ", ".join(PROFILLER))
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
    kayit = runtime.defter[ad]
    kayit["dependency_snapshot"] = {
        dep: runtime.defter[dep]["revision"]
        for dep in runtime.bagimliliklar.get(ad, set())
    }


def _invalidate_dependents(changed: str, visited: set[str] | None = None) -> None:
    if visited is None:
        visited = set()
    if changed in visited:
        return
    visited.add(changed)

    for dependent, dependencies in runtime.bagimliliklar.items():
        if changed not in dependencies or dependent not in runtime.defter:
            continue
        kayit = runtime.defter[dependent]
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
        for dep in runtime.bagimliliklar.get(start, set())
    )


def defineValue(
    ad: str,
    min=None,
    max=None,
    preferred=None,
    aciklama: str = "",
    critical: bool = False,
):
    """Kritik değerin adını, sınırlarını ve rolünü tanımlar."""

    _require_unsealed()
    _invalidate_startup_validation()
    if not isinstance(ad, str) or not ad.strip():
        raise TawntHatasi("Deger adi bos olmayan bir yazi olmali.")
    if ad in runtime.defter:
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

    runtime.defter[ad] = {
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
    runtime.bagimliliklar.setdefault(ad, set())
    if critical:
        runtime.olcum_profilleri.setdefault(ad, set()).add(LIVE)
    return ad


def introduce(ad, min=None, max=None, preferred=None, aciklama=""):
    """V1 uyumluluk adı; yeni kodda ``defineValue`` kullanılır."""

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
    """Tanımlanmış değeri kaynağıyla kaydeder ve bağımlıları eskitir."""

    _require_unsealed()
    source = legacy.pop("kaynak", source)
    human = legacy.pop("kim", human)
    date = legacy.pop("tarih", date)
    note = legacy.pop("notu", note)
    if legacy:
        raise TawntHatasi("Bilinmeyen recordValue alanlari: %s" % sorted(legacy))

    kayit = _require_name(ad)
    if source not in KAYNAKLAR:
        raise TawntHatasi(
            "'%s': kaynak %r degil; %s olmali."
            % (ad, source, ", ".join(KAYNAKLAR))
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
    runtime.validated_once = False
    if runtime.sistem_durumu in (READY_UNARMED, ARMED):
        runtime.sistem_durumu = VALIDATING
    return deger


def acquire(ad, deger, kaynak=VARSAYILDI, kim=None, tarih=None, notu=""):
    """V1 uyumluluk adı; yeni kodda ``recordValue`` kullanılır."""

    return recordValue(
        ad, deger, source=kaynak, human=kim, date=tarih, note=notu
    )


def deger(ad):
    kayit = _require_name(ad)
    if not kayit["atandi"]:
        raise TawntHatasi("'%s' henuz atanmadi." % ad)
    return kayit["deger"]


def valueState(ad: str) -> str:
    return _require_name(ad)["state"]


def identifyRuntimeType(ad: str, tip: str):
    _require_unsealed()
    _invalidate_startup_validation()
    _require_name(ad)["tip"] = tip
    return ad


def dependsOn(dependent: str, *dependencies: str) -> bool:
    """Bir değer değişince hangi değerlerin eski sayılacağını bildirir."""

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

    runtime.bagimliliklar.setdefault(dependent, set()).update(dependencies)
    return True


def IsTwinOf(a: str, b: str) -> bool:
    """İki değerin birlikte anlam taşıdığını bildirir."""

    _require_name(a)
    _require_name(b)
    if (a, b) not in runtime.ikizler and (b, a) not in runtime.ikizler:
        runtime.ikizler.append((a, b))
    if b not in runtime.bagimliliklar.get(a, set()):
        dependsOn(a, b)
    if a not in runtime.bagimliliklar.get(b, set()):
        runtime.bagimliliklar.setdefault(b, set()).add(a)
    return runtime.defter[a]["atandi"] and runtime.defter[b]["atandi"]


def requireMeasured(*names: str, profiles: Iterable[str] = (LIVE,)) -> bool:
    """Belirli profillerde değerlerin OLCULDU olmasını zorunlu kılar."""

    _require_unsealed()
    _invalidate_startup_validation()
    profile_set = {_validate_profile(profile) for profile in profiles}
    for name in names:
        _require_name(name)
        runtime.olcum_profilleri.setdefault(name, set()).update(profile_set)
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
    _require_unsealed()
    _invalidate_startup_validation()
    if len(zincir) < 3 or len(zincir) % 2 == 0:
        raise TawntHatasi(
            "siblingIntAppr: ad, op, ad, op, ad ... bicimi bekleniyor."
        )
    kayit = tuple(zincir)
    if kayit not in runtime.zincirler:
        runtime.zincirler.append(kayit)
    return _zinciri_dogrula(kayit)


def _collect_value_errors(names: Iterable[str], profile=None, strict_v2=False):
    errors = []
    for ad in names:
        if ad not in runtime.defter:
            errors.append("%s: hic tanitilmadi" % ad)
            continue
        kayit = runtime.defter[ad]
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
        if (
            profile in runtime.olcum_profilleri.get(ad, set())
            and kayit["kaynak"] != OLCULDU
        ):
            errors.append("%s: %s profili OLCULDU kaynak istiyor" % (ad, profile))

        if strict_v2:
            for dep in runtime.bagimliliklar.get(ad, set()):
                dep_record = runtime.defter.get(dep)
                if not dep_record or not dep_record["atandi"]:
                    errors.append("%s: bagimliligi %s atanmadi" % (ad, dep))

    for a, b in runtime.ikizler:
        for x, y in ((a, b), (b, a)):
            if (
                x in names
                and runtime.defter[x]["atandi"]
                and not runtime.defter[y]["atandi"]
            ):
                errors.append("%s atanmis ama ikizi %s atanmamis" % (x, y))
    return errors


def preacquire(*names: str) -> bool:
    """V1 açılış kontrolü; kaynak profili ve STALE durumunu zorlamaz."""

    errors = _collect_value_errors(names, strict_v2=False)
    if errors:
        raise TawntHatasi("preacquire basarisiz:\n  - " + "\n  - ".join(errors))
    for chain in runtime.zincirler:
        _zinciri_dogrula(chain)
    return True


def validateBeforeStart(*names: str, profile: str = OFFLINE):
    """Seçilen profil için bütün zorunlu değerleri doğrular."""

    _validate_profile(profile)
    if runtime.kilit is not None:
        runtime.sistem_durumu = LATCHED_FAULT
        raise TawntHatasi("Ciddi ariza kilidi varken baslangic dogrulanamaz.")
    if profile == LIVE and runtime.fault_store_path is None:
        raise TawntHatasi("LIVE profili kalici fault-store yapilandirmasi ister.")

    runtime.profil = profile
    runtime.sistem_durumu = VALIDATING
    runtime.armed = False
    selected = tuple(names) if names else tuple(runtime.defter)
    errors = _collect_value_errors(selected, profile=profile, strict_v2=True)
    for chain in runtime.zincirler:
        try:
            _zinciri_dogrula(chain)
        except TawntHatasi as exc:
            errors.append(str(exc))
    if errors:
        raise TawntHatasi(
            "validateBeforeStart basarisiz:\n  - "
            + "\n  - ".join(dict.fromkeys(errors))
        )

    for ad in selected:
        kayit = runtime.defter[ad]
        kayit["state"] = VALIDATED
        kayit["validated_profile"] = profile
        _record_dependency_snapshot(ad)
    runtime.validated_once = True
    runtime.sistem_durumu = READY_UNARMED
    return {
        "profile": profile,
        "validated": selected,
        "state": runtime.sistem_durumu,
    }


def seal() -> bool:
    """Doğrulanmış değerleri koşu boyunca değiştirilemez yapar."""

    if runtime.sistem_durumu not in (READY_UNARMED, ARMED):
        raise TawntHatasi("seal icin once validateBeforeStart gecmeli.")
    invalid = [
        ad
        for ad, kayit in runtime.defter.items()
        if kayit["atandi"] and kayit["state"] not in (VALIDATED, SEALED)
    ]
    if invalid:
        raise TawntHatasi("Dogrulanmamis degerler muhurlenemez: %s" % invalid)
    for kayit in runtime.defter.values():
        if kayit["atandi"]:
            kayit["state"] = SEALED
    runtime.muhur = True
    return True


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
        "TAWNT tek koseyi tasiyarak dortgeni deforme etmez."
        % (sx, sy, g, y, dx, dy)
    )


def report() -> str:
    if not runtime.defter:
        return "tawnt: defter bos."
    lines = [
        "tawnt defteri — %s" % datetime.date.today().strftime("%d.%m.%Y"),
        "(bu bir beyan listesidir, kanit degil)",
        "profil=%s sistem=%s evre=%s"
        % (runtime.profil, runtime.sistem_durumu, runtime.evre),
        "",
        "%-10s %-22s %-12s %-10s %-10s %s"
        % ("KAYNAK", "AD", "DEGER", "TIP", "DURUM", "NOT"),
        "-" * 96,
    ]
    order = {OLCULDU: 0, DEVRALINDI: 1, VARSAYILDI: 2, None: 3}
    for ad in sorted(
        runtime.defter,
        key=lambda item: (order[runtime.defter[item]["kaynak"]], item),
    ):
        kayit = runtime.defter[ad]
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
    not_measured = [
        ad for ad in runtime.defter if runtime.defter[ad]["kaynak"] != OLCULDU
    ]
    lines.extend(["", "olculmemis/atanmamis: %d" % len(not_measured)])
    return "\n".join(lines)
