# =============================================================================
# tur_kaydedici.py — Tur (tour) kayit araci
#
# Bir yaris turunu olay olay diske kaydeder: durum gecisleri, olaylar,
# motor komutlari, serit hatasi, watchdog tetiklemeleri, kapatma sonucu.
#
# TASARIM NOTU — R2'ye gecis:
#   Depolama, `TurDeposu` arayuzunun arkasindadir. Diskten R2'ye gecmek
#   icin YALNIZCA `R2Deposu` sinifini doldurup `TurKaydedici(depo=...)`
#   parametresini degistirmek yeterlidir. Kaydedici mantigi degismez.
#
# GUVENLIK NOTU:
#   Kayit, KONTROL YOLUNUN disindadir. Tum yazma islemleri arka plan
#   thread'inde ve kuyruk uzerinden yapilir; kuyruk dolarsa en eski
#   kayit dusurulur. Kayit hicbir kosulda surus dongusunu BLOKE ETMEZ
#   (bkz. LEGACY-046: disk G/C kontrol yolunda olmamali).
#
# Kullanim:
#     from tur_kaydedici import TurKaydedici
#     kayit = TurKaydedici()
#     kayit.baslat(tur_adi="deneme-1")
#     kayit.olay("durum", eski="BEKLIYOR", yeni="SURUYOR")
#     kayit.telemetri(hata=12.0, sol=55.0, sag=45.0, durum="SURUYOR")
#     kayit.bitir(sonuc="PARK_TAMAM")
# =============================================================================
from __future__ import annotations

import json
import os
import queue
import threading
import time
import uuid
from typing import Any


# ---------------------------------------------------------------------------
# Depolama arayuzu
# ---------------------------------------------------------------------------
class TurDeposu:
    """Depolama arka ucu arayuzu. R2'ye gecerken yalnizca bu uygulanir."""

    def ac(self, tur_id: str) -> None:
        raise NotImplementedError

    def yaz(self, satirlar: list[str]) -> None:
        """Bir veya daha fazla JSONL satirini kalici hale getirir."""
        raise NotImplementedError

    def kapat(self, ozet: dict) -> str | None:
        """Kaydi sonlandirir; erisim adresini (yol/URL) dondurur."""
        raise NotImplementedError


class DiskDeposu(TurDeposu):
    """Yerel diske JSONL yazar. Varsayilan arka uc."""

    def __init__(self, klasor: str = "turlar"):
        self.klasor = klasor
        self._yol: str | None = None
        self._fh = None

    def ac(self, tur_id: str) -> None:
        os.makedirs(self.klasor, exist_ok=True)
        self._yol = os.path.join(self.klasor, f"{tur_id}.jsonl")
        # satir tamponlu: her satir hemen diske gider, ama fsync yapilmaz
        self._fh = open(self._yol, "a", encoding="utf-8", buffering=1)

    def yaz(self, satirlar: list[str]) -> None:
        if self._fh is None:
            return
        for satir in satirlar:
            self._fh.write(satir + "\n")

    def kapat(self, ozet: dict) -> str | None:
        if self._fh is None:
            return self._yol
        try:
            self._fh.write(json.dumps(
                {"tip": "ozet", **ozet}, ensure_ascii=False) + "\n")
            self._fh.flush()
            os.fsync(self._fh.fileno())
        except Exception:
            pass
        finally:
            try:
                self._fh.close()
            except Exception:
                pass
            self._fh = None
        return self._yol


class R2Deposu(TurDeposu):
    """Cloudflare R2 arka ucu — HENUZ BAGLANMADI.

    Baska bir oturumda doldurulacak. Iskelet bilerek birakildi:
    kaydedici mantigi bu sinifin GERCEKLENMESINDEN bagimsizdir.

    Doldurma notlari:
      - R2, S3 uyumlu API sunar; boto3 ile `endpoint_url` R2 hesabina
        yonlendirilir.
      - Satirlari TEK TEK gondermeyin; `yaz()` zaten toplu (batch) cagrilir.
        Tampon biriktirip cok parcali yukleme (multipart) ya da periyodik
        put_object tercih edin.
      - Ag hatasi surusu ETKILEMEMELI: hatalari yutup yerel bir yedege
        dusun (asagidaki `yedek` parametresi bunun icindir).
    """

    def __init__(self, bucket: str, anahtar_onek: str = "turlar/",
                 yedek: TurDeposu | None = None):
        self.bucket = bucket
        self.anahtar_onek = anahtar_onek
        self.yedek = yedek or DiskDeposu()
        self._tampon: list[str] = []
        self._tur_id: str | None = None

    def ac(self, tur_id: str) -> None:
        self._tur_id = tur_id
        self._tampon = []
        # Su an yalnizca yerel yedek aktif.
        self.yedek.ac(tur_id)

    def yaz(self, satirlar: list[str]) -> None:
        self._tampon.extend(satirlar)
        self.yedek.yaz(satirlar)
        # TODO(R2): tampon esigi asilinca put_object ile gonder.

    def kapat(self, ozet: dict) -> str | None:
        # TODO(R2): son tamponu yukle, nesne anahtarini dondur.
        return self.yedek.kapat(ozet)


# ---------------------------------------------------------------------------
# Kaydedici
# ---------------------------------------------------------------------------
class TurKaydedici:
    """Tur olaylarini kontrol yolunu bloke etmeden kaydeder."""

    def __init__(self, depo: TurDeposu | None = None,
                 kuyruk_boyu: int = 2000,
                 telemetri_araligi: float = 0.2):
        self.depo = depo or DiskDeposu()
        self._q: queue.Queue = queue.Queue(maxsize=kuyruk_boyu)
        self._thread: threading.Thread | None = None
        self._calisiyor = False
        self._tur_id: str | None = None
        self._t0: float | None = None
        self._dusen = 0            # kuyruk dolulugu nedeniyle atilan kayit
        self._sayac = 0
        self._telemetri_araligi = telemetri_araligi
        self._son_telemetri = 0.0
        self._ozet: dict[str, Any] = {}

    # ------------------------------------------------------------------
    @property
    def tur_id(self) -> str | None:
        return self._tur_id

    @property
    def dusen_kayit(self) -> int:
        return self._dusen

    # ------------------------------------------------------------------
    def baslat(self, tur_adi: str | None = None) -> str:
        """Yeni bir tur kaydi acar; tur kimligini dondurur."""
        if self._calisiyor:
            return self._tur_id or ""
        damga = time.strftime("%Y%m%d-%H%M%S")
        kisa = uuid.uuid4().hex[:6]
        self._tur_id = f"{damga}-{tur_adi or 'tur'}-{kisa}"
        self._t0 = time.monotonic()
        self._dusen = 0
        self._sayac = 0
        self._ozet = {}

        try:
            self.depo.ac(self._tur_id)
        except Exception as exc:
            print(f"[tur_kaydedici] Depo acilamadi, kayit devre disi: {exc}")
            self._tur_id = None
            return ""

        self._calisiyor = True
        self._thread = threading.Thread(target=self._yazar, daemon=True)
        self._thread.start()
        self.olay("tur_basladi", tur_adi=tur_adi or "tur")
        return self._tur_id

    # ------------------------------------------------------------------
    def olay(self, tip: str, **alanlar) -> None:
        """Bir olayi kuyruga koyar. ASLA bloke etmez, ASLA hata firlatmaz."""
        if not self._calisiyor:
            return
        kayit = {
            "tip": tip,
            "t": round(time.monotonic() - (self._t0 or 0.0), 4),
            "n": self._sayac,
            **alanlar,
        }
        self._sayac += 1
        try:
            self._q.put_nowait(kayit)
        except queue.Full:
            # En eskiyi dusur, yeniyi al — kayit surusu bekletmez.
            try:
                self._q.get_nowait()
                self._dusen += 1
                self._q.put_nowait(kayit)
            except Exception:
                self._dusen += 1

    # ------------------------------------------------------------------
    def telemetri(self, **alanlar) -> None:
        """Hiz sinirlamali telemetri; her kareyi yazmaz."""
        if not self._calisiyor:
            return
        simdi = time.monotonic()
        if (simdi - self._son_telemetri) < self._telemetri_araligi:
            return
        self._son_telemetri = simdi
        self.olay("telemetri", **alanlar)

    # ------------------------------------------------------------------
    def durum_degisti(self, eski: str, yeni: str, sebep: str = "") -> None:
        self.olay("durum", eski=eski, yeni=yeni, sebep=sebep)

    def uyari(self, mesaj: str, **alanlar) -> None:
        self.olay("uyari", mesaj=mesaj, **alanlar)

    # ------------------------------------------------------------------
    def bitir(self, sonuc: str = "bilinmiyor", **alanlar) -> str | None:
        """Kaydi kapatir; erisim adresini dondurur."""
        if not self._calisiyor:
            return None
        self.olay("tur_bitti", sonuc=sonuc, **alanlar)
        self._calisiyor = False
        if self._thread is not None:
            self._thread.join(timeout=3.0)

        ozet = {
            "tur_id": self._tur_id,
            "sonuc": sonuc,
            "sure_sn": round(time.monotonic() - (self._t0 or 0.0), 3),
            "kayit_sayisi": self._sayac,
            "dusen_kayit": self._dusen,
            **self._ozet,
        }
        try:
            yol = self.depo.kapat(ozet)
        except Exception as exc:
            print(f"[tur_kaydedici] Depo kapatilamadi: {exc}")
            return None
        if self._dusen:
            print(f"[tur_kaydedici] UYARI: {self._dusen} kayit dusuruldu "
                  "(kuyruk doldu).")
        print(f"[tur_kaydedici] Tur kaydedildi: {yol}")
        return yol

    # ------------------------------------------------------------------
    def _yazar(self) -> None:
        """Arka plan yazar thread'i — tum disk G/C burada."""
        toplu: list[str] = []
        while self._calisiyor or not self._q.empty():
            try:
                kayit = self._q.get(timeout=0.2)
                toplu.append(json.dumps(kayit, ensure_ascii=False))
            except queue.Empty:
                pass
            if toplu and (len(toplu) >= 50 or self._q.empty()):
                try:
                    self.depo.yaz(toplu)
                except Exception:
                    # Kayit hatasi surusu etkilemez; sessizce dusur.
                    pass
                toplu = []
        if toplu:
            try:
                self.depo.yaz(toplu)
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Okuma / ozet yardimcisi
# ---------------------------------------------------------------------------
def turu_oku(yol: str) -> list[dict]:
    """Kaydedilmis bir turu satir satir okur."""
    kayitlar = []
    with open(yol, encoding="utf-8") as fh:
        for satir in fh:
            satir = satir.strip()
            if not satir:
                continue
            try:
                kayitlar.append(json.loads(satir))
            except json.JSONDecodeError:
                continue
    return kayitlar


def turu_ozetle(yol: str) -> None:
    """Bir turun kisa metin ozetini yazdirir."""
    kayitlar = turu_oku(yol)
    if not kayitlar:
        print("Kayit bulunamadi.")
        return
    durumlar = [k for k in kayitlar if k.get("tip") == "durum"]
    uyarilar = [k for k in kayitlar if k.get("tip") == "uyari"]
    ozet = next((k for k in kayitlar if k.get("tip") == "ozet"), {})

    print(f"Tur: {ozet.get('tur_id', '?')}")
    print(f"Sonuc: {ozet.get('sonuc', '?')}  "
          f"Sure: {ozet.get('sure_sn', '?')} sn  "
          f"Kayit: {ozet.get('kayit_sayisi', len(kayitlar))}")
    if ozet.get("dusen_kayit"):
        print(f"Dusen kayit: {ozet['dusen_kayit']}")
    print(f"\nDurum gecisleri ({len(durumlar)}):")
    for d in durumlar:
        sebep = f"  ({d['sebep']})" if d.get("sebep") else ""
        print(f"  {d['t']:8.2f}s  {d.get('eski','?'):>16s} -> "
              f"{d.get('yeni','?')}{sebep}")
    if uyarilar:
        print(f"\nUyarilar ({len(uyarilar)}):")
        for u in uyarilar:
            print(f"  {u['t']:8.2f}s  {u.get('mesaj','')}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        turu_ozetle(sys.argv[1])
    else:
        print("Kullanim: python3 tur_kaydedici.py <turlar/xxx.jsonl>")
