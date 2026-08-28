"""Behavior tests for the v1 calibration and settings contracts."""

from __future__ import annotations

import copy
import unittest
from pathlib import Path
from typing import Any, Callable

from jsonschema import Draft202012Validator

from startech.configuration import (
    AYARLAR_SEMASI,
    KALIBRASYON_SEMASI,
    PROFILE_SCHEMA,
    ayarlar_uyarilari,
    ayarlari_dogrula,
    json_oku,
    kalibrasyon_anlam_hatalari,
    kalibrasyon_uyarilari,
    kalibrasyonu_dogrula,
    kisa_ozet_hesapla,
    sema_hatalari,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXAMPLE_DIR = PROJECT_ROOT / "config" / "examples"


class YapilandirmaSemasiTesti(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.kalibrasyon = json_oku(EXAMPLE_DIR / "kalibrasyon-v1.ornek.json")
        cls.ayarlar = json_oku(EXAMPLE_DIR / "ayarlar-v1.ornek.json")

    def kalibrasyonu_degistir(self, degistir: Callable[[dict[str, Any]], None]):
        veri = copy.deepcopy(self.kalibrasyon)
        degistir(veri)
        return veri

    def ayarlari_degistir(self, degistir: Callable[[dict[str, Any]], None]):
        veri = copy.deepcopy(self.ayarlar)
        degistir(veri)
        return veri

    def test_semalar_draft_2020_12_icin_gecerli(self):
        Draft202012Validator.check_schema(KALIBRASYON_SEMASI)
        Draft202012Validator.check_schema(AYARLAR_SEMASI)
        Draft202012Validator.check_schema(PROFILE_SCHEMA)

    def test_ornek_kalibrasyon_gecerli(self):
        self.assertEqual([], kalibrasyonu_dogrula(self.kalibrasyon))

    def test_ornek_ayarlar_gecerli(self):
        self.assertEqual([], ayarlari_dogrula(self.ayarlar))

    def test_kisa_ozet_startechconfig_ile_ayni(self):
        self.assertEqual("e11b19", kisa_ozet_hesapla(self.kalibrasyon))

    def test_pid_degerleri_bir_surumu_dogru_ilan_etmez(self):
        masaustu = self.ayarlari_degistir(
            lambda veri: veri["kontrol"].update(kp=0.3, kd=0.45, ki=0.04)
        )
        self.assertEqual([], ayarlari_dogrula(masaustu))
        self.assertEqual([], ayarlari_dogrula(self.ayarlar))

    def test_eksik_motor_reddedilir(self):
        veri = self.kalibrasyonu_degistir(lambda kal: kal.pop("motor"))
        self.assertTrue(sema_hatalari(veri, KALIBRASYON_SEMASI))

    def test_bilinmeyen_alan_reddedilir(self):
        veri = self.ayarlari_degistir(lambda ayar: ayar.update(gizli_pwm=100))
        self.assertTrue(sema_hatalari(veri, AYARLAR_SEMASI))

    def test_yanlis_sema_surumu_reddedilir(self):
        veri = self.kalibrasyonu_degistir(lambda kal: kal.update(sema_surumu=2))
        self.assertTrue(sema_hatalari(veri, KALIBRASYON_SEMASI))

    def test_sayi_yerine_metin_reddedilir(self):
        veri = self.kalibrasyonu_degistir(
            lambda kal: kal["kamera"].update(genislik="840")
        )
        self.assertTrue(sema_hatalari(veri, KALIBRASYON_SEMASI))

    def test_hiz_sirasi_reddedilir(self):
        veri = self.ayarlari_degistir(lambda ayar: ayar["hiz"].update(min=60))
        self.assertIn("hız sırası", " ".join(ayarlari_dogrula(veri)))

    def test_kamera_perspektif_cozunurluk_uyusmazligi_reddedilir(self):
        veri = self.kalibrasyonu_degistir(
            lambda kal: kal["perspektif"].update(olculen_cozunurluk=[960, 540])
        )
        self.assertIn(
            "kamera çözünürlüğü",
            " ".join(kalibrasyon_anlam_hatalari(veri, ozet_kontrolu=False)),
        )

    def test_kamera_disindaki_nokta_reddedilir(self):
        veri = self.kalibrasyonu_degistir(
            lambda kal: kal["perspektif"]["kaynak_noktalar"][3].__setitem__(0, 841)
        )
        self.assertIn(
            "kamera sınırının dışında",
            " ".join(kalibrasyon_anlam_hatalari(veri, ozet_kontrolu=False)),
        )

    def test_ters_perspektif_reddedilir(self):
        veri = self.kalibrasyonu_degistir(
            lambda kal: kal["perspektif"]["kaynak_noktalar"][1].__setitem__(0, 100)
        )
        self.assertIn(
            "sağ köşeleri",
            " ".join(kalibrasyon_anlam_hatalari(veri, ozet_kontrolu=False)),
        )

    def test_hsv_dizin_siniri_reddedilir(self):
        veri = self.kalibrasyonu_degistir(
            lambda kal: kal["renkler"]["mavi_levha"]["araliklar"][0]["ust"].__setitem__(0, 181)
        )
        self.assertTrue(sema_hatalari(veri, KALIBRASYON_SEMASI))

    def test_hsv_alt_ust_sirasi_reddedilir(self):
        veri = self.kalibrasyonu_degistir(
            lambda kal: kal["renkler"]["mavi_levha"]["araliklar"][0].update(
                alt=[140, 100, 70]
            )
        )
        self.assertIn(
            "alt sınırı",
            " ".join(kalibrasyon_anlam_hatalari(veri, ozet_kontrolu=False)),
        )

    def test_bos_hsv_araligi_reddedilir(self):
        veri = self.kalibrasyonu_degistir(
            lambda kal: kal["renkler"]["mavi_levha"]["araliklar"][0].update(
                ust=[95, 100, 70]
            )
        )
        self.assertIn(
            "aynı olamaz",
            " ".join(kalibrasyon_anlam_hatalari(veri, ozet_kontrolu=False)),
        )

    def test_turuncu_sari_cakismasi_reddedilir(self):
        veri = self.kalibrasyonu_degistir(
            lambda kal: kal["renkler"]["sari_arac"]["araliklar"][0]["alt"].__setitem__(0, 20)
        )
        self.assertIn(
            "turuncu üst H",
            " ".join(kalibrasyon_anlam_hatalari(veri, ozet_kontrolu=False)),
        )

    def test_icerik_degistiginde_eski_ozet_reddedilir(self):
        veri = self.kalibrasyonu_degistir(
            lambda kal: kal["kamera"].update(dondur_180=False)
        )
        self.assertIn("damga.ozet", " ".join(kalibrasyon_anlam_hatalari(veri)))

    def test_gercek_olmayan_tarih_reddedilir(self):
        veri = self.kalibrasyonu_degistir(
            lambda kal: kal["damga"].update(zaman="2026-02-31T12:00:00")
        )
        self.assertIn(
            "takvim tarihi",
            " ".join(kalibrasyon_anlam_hatalari(veri, ozet_kontrolu=False)),
        )

    def test_olculdu_ama_trimler_bir_uyarisidir(self):
        veri = self.kalibrasyonu_degistir(
            lambda kal: kal["motor"].update(olculdu="2026-08-06")
        )
        self.assertEqual(
            [], kalibrasyon_anlam_hatalari(veri, ozet_kontrolu=False)
        )
        self.assertIn("dört trim", " ".join(kalibrasyon_uyarilari(veri)))

    def test_minimum_hiz_olu_bolgenin_altindaysa_uyarir(self):
        self.assertIn(
            "ölü bölgesinin altında",
            " ".join(ayarlar_uyarilari(self.ayarlar, self.kalibrasyon)),
        )

    def test_yuksek_ki_kaydi_engellemez_fakat_uyarir(self):
        veri = self.ayarlari_degistir(lambda ayar: ayar["kontrol"].update(ki=0.21))
        self.assertEqual([], ayarlari_dogrula(veri))
        self.assertIn("KI 0,2 üstünde", " ".join(ayarlar_uyarilari(veri)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
