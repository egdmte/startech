"""Reusable validation for ``kalibrasyon.json`` and ``ayarlar.json`` v1."""

from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCHEMA_DIR = PROJECT_ROOT / "config" / "schema"


def json_oku(yol: Path) -> dict[str, Any]:
    """UTF-8 JSON dosyasını sözlüğe çevirir."""

    with yol.open("r", encoding="utf-8-sig") as dosya:
        return json.load(dosya)


KALIBRASYON_SEMASI = json_oku(SCHEMA_DIR / "kalibrasyon-v1.schema.json")
AYARLAR_SEMASI = json_oku(SCHEMA_DIR / "ayarlar-v1.schema.json")


def _yol_yaz(error: Any) -> str:
    yol = ".".join(str(parca) for parca in error.absolute_path)
    return yol or "<kok>"


def sema_hatalari(veri: dict[str, Any], sema: dict[str, Any]) -> list[str]:
    """Bütün JSON Schema hatalarını okunabilir ve kararlı sırayla döndürür."""

    dogrulayici = Draft202012Validator(sema)
    hatalar = sorted(
        dogrulayici.iter_errors(veri),
        key=lambda error: tuple(str(parca) for parca in error.absolute_path),
    )
    return [f"{_yol_yaz(error)}: {error.message}" for error in hatalar]


def kisa_ozet_hesapla(kalibrasyon: dict[str, Any]) -> str:
    """StarTechConfig.KisaOzet ile aynı altı haneli özeti hesaplar."""

    ozet_icin = copy.deepcopy(kalibrasyon)
    ozet_icin.pop("damga", None)
    sikistirilmis = json.dumps(
        ozet_icin,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(sikistirilmis.encode("utf-8")).hexdigest()[:6]


def _hsv_araliklari(kalibrasyon: dict[str, Any]):
    for profil_adi, hsv_araligi in kalibrasyon["serit"]["beyaz_profiller"].items():
        yield f"serit.beyaz_profiller.{profil_adi}", hsv_araligi

    for renk_adi, renk in kalibrasyon["renkler"].items():
        if renk_adi == "_aciklama":
            continue
        for sira, hsv_araligi in enumerate(renk["araliklar"]):
            yield f"renkler.{renk_adi}.araliklar[{sira}]", hsv_araligi


def kalibrasyon_anlam_hatalari(
    kalibrasyon: dict[str, Any],
    *,
    ozet_kontrolu: bool = True,
) -> list[str]:
    """JSON Schema'nın tek başına anlatamadığı alanlar arası kuralları sınar."""

    hatalar: list[str] = []
    genislik = kalibrasyon["kamera"]["genislik"]
    yukseklik = kalibrasyon["kamera"]["yukseklik"]
    perspektif = kalibrasyon["perspektif"]

    if perspektif["olculen_cozunurluk"] != [genislik, yukseklik]:
        hatalar.append(
            "perspektif.olculen_cozunurluk kamera çözünürlüğüyle aynı olmalı"
        )

    noktalar = perspektif["kaynak_noktalar"]
    for sira, (x, y) in enumerate(noktalar):
        if not (0 <= x <= genislik and 0 <= y <= yukseklik):
            hatalar.append(
                f"perspektif.kaynak_noktalar[{sira}] kamera sınırının dışında"
            )

    sol_ust, sag_ust, sol_alt, sag_alt = noktalar
    ust_genislik = sag_ust[0] - sol_ust[0]
    alt_genislik = sag_alt[0] - sol_alt[0]
    if ust_genislik <= 0 or alt_genislik <= 0:
        hatalar.append("perspektif sağ köşeleri sol köşelerin sağında olmalı")
    elif ust_genislik >= alt_genislik:
        hatalar.append("perspektif üst kenarı alt kenardan dar olmalı")

    if sol_ust[1] >= sol_alt[1] or sag_ust[1] >= sag_alt[1]:
        hatalar.append("perspektif üst köşeleri alt köşelerin üstünde olmalı")

    esikler = kalibrasyon["serit"]["profil_esikleri"]
    if esikler["karanlik_alti"] >= esikler["parlak_ustu"]:
        hatalar.append("karanlık profil eşiği parlak profil eşiğinden küçük olmalı")

    for ad, hsv_araligi in _hsv_araliklari(kalibrasyon):
        alt = hsv_araligi["alt"]
        ust = hsv_araligi["ust"]
        if any(alt[index] > ust[index] for index in range(3)):
            hatalar.append(f"{ad}: HSV alt sınırı üst sınırdan büyük olamaz")
        if alt == ust:
            hatalar.append(f"{ad}: HSV alt ve üst sınırı aynı olamaz")

    turuncu_ust_h = kalibrasyon["renkler"]["turuncu_arac"]["araliklar"][0]["ust"][0]
    sari_alt_h = kalibrasyon["renkler"]["sari_arac"]["araliklar"][0]["alt"][0]
    if turuncu_ust_h >= sari_alt_h:
        hatalar.append("turuncu üst H, sarı alt H değerinden küçük olmalı")

    park = kalibrasyon["renkler"]["kirmizi_park"]
    if park["tetik_alan"] < park["min_alan"]:
        hatalar.append("kırmızı park tetik alanı min_alan değerinden küçük olamaz")

    zaman = kalibrasyon["damga"]["zaman"]
    try:
        datetime.strptime(zaman, "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        hatalar.append("damga.zaman gerçek bir takvim tarihi olmalı")

    olculdu = kalibrasyon["motor"]["olculdu"]
    if olculdu is not None:
        try:
            datetime.strptime(olculdu, "%Y-%m-%d")
        except ValueError:
            hatalar.append("motor.olculdu gerçek bir takvim tarihi veya null olmalı")

    if ozet_kontrolu:
        hesaplanan = kisa_ozet_hesapla(kalibrasyon)
        if kalibrasyon["damga"]["ozet"] != hesaplanan:
            hatalar.append(
                "damga.ozet içerikle uyuşmuyor: "
                f"beklenen {hesaplanan}, bulunan {kalibrasyon['damga']['ozet']}"
            )

    return hatalar


def ayarlar_anlam_hatalari(ayarlar: dict[str, Any]) -> list[str]:
    """Ayar alanlarının birbirine göre geçerli olup olmadığını sınar."""

    hatalar: list[str] = []
    hiz = ayarlar["hiz"]
    if not hiz["min"] <= hiz["hedef"] <= hiz["max"]:
        hatalar.append("hız sırası min <= hedef <= max olmalı")
    return hatalar


def kalibrasyon_uyarilari(kalibrasyon: dict[str, Any]) -> list[str]:
    """Kaydı engellemeyen fakat insanın incelemesi gereken durumları döndürür."""

    uyarilar: list[str] = []
    motor = kalibrasyon["motor"]
    trim_adlari = (
        "sol_trim_dusuk",
        "sol_trim_yuksek",
        "sag_trim_dusuk",
        "sag_trim_yuksek",
    )
    trimler = [motor[ad] for ad in trim_adlari]
    if any(trim < 0.5 or trim > 1.5 for trim in trimler):
        uyarilar.append("trimlerden biri 0,5-1,5 uyarı aralığının dışında")
    if motor["olculdu"] is not None and all(
        abs(trim - 1.0) < 0.0001 for trim in trimler
    ):
        uyarilar.append("motor ölçüldü denmiş fakat dört trim de hâlâ 1,0")
    return uyarilar


def ayarlar_uyarilari(
    ayarlar: dict[str, Any],
    kalibrasyon: dict[str, Any] | None = None,
) -> list[str]:
    """StarTechConfig'in insan onayıyla kaydedebildiği şüpheli değerleri döndürür."""

    uyarilar: list[str] = []
    kontrol = ayarlar["kontrol"]
    if kontrol["ki"] > 0.2:
        uyarilar.append("KI 0,2 üstünde; integral birikimi incelenmeli")

    if kalibrasyon is not None:
        min_hiz = ayarlar["hiz"]["min"]
        olu_bolge = kalibrasyon["motor"]["olu_bolge_min_pwm"]
        if 0 < min_hiz < olu_bolge:
            uyarilar.append("minimum hız motor ölü bölgesinin altında")
    return uyarilar


def kalibrasyonu_dogrula(kalibrasyon: dict[str, Any]) -> list[str]:
    """Önce yapıyı, yapı sağlamsa alanlar arası kuralları doğrular."""

    hatalar = sema_hatalari(kalibrasyon, KALIBRASYON_SEMASI)
    if hatalar:
        return hatalar
    return kalibrasyon_anlam_hatalari(kalibrasyon)


def ayarlari_dogrula(ayarlar: dict[str, Any]) -> list[str]:
    """Önce yapıyı, yapı sağlamsa hız ilişkilerini doğrular."""

    hatalar = sema_hatalari(ayarlar, AYARLAR_SEMASI)
    if hatalar:
        return hatalar
    return ayarlar_anlam_hatalari(ayarlar)
