"""3awnt davranış testleri.

Bu dosyada iki ayrı grup vardır:

1. TestTawntV1: Bugünkü tawnt.py davranışını gerçekten çalıştırır.
2. TestTawntV2Sozlesmesi: TAWNT.md içindeki gelecek sözleşmesini tarif eder.
   Henüz kodu bulunmayan her test, gerekçesi görünür biçimde skip edilir.

Skip edilen test başarılı sayılmaz. V2 uygulanırken ilgili skip kaldırılır ve test
gerçekten geçmeden özellik tamamlandı denmez.
"""

from __future__ import annotations

import importlib
import math
from pathlib import Path
import tempfile
import unittest

import tawnt


class TestTawntV1(unittest.TestCase):
    """Mevcut prototipin gerçekten yaptığı işleri doğrular."""

    def setUp(self):
        # sifirla() güvenlik kilidini ve callback'leri sıfırlamıyor. Testlerin
        # birbirinden bağımsız olması için modülü temiz bellekle yeniden yükle.
        self.tawnt = importlib.reload(tawnt)
        self.gecici = tempfile.TemporaryDirectory()
        self.tawnt._gunluk_yolu = str(
            Path(self.gecici.name) / "tawnt_guvenlik.log"
        )

    def tearDown(self):
        self.gecici.cleanup()

    def test_introduce_acquire_ve_deger(self):
        ad = self.tawnt.introduce(
            "MAX_PWM", min=0, max=100, preferred=57
        )
        sonuc = self.tawnt.acquire(
            ad,
            57,
            kaynak=self.tawnt.OLCULDU,
            kim="Egemen",
            tarih="2026-09-12",
        )

        self.assertEqual("MAX_PWM", ad)
        self.assertEqual(57, sonuc)
        self.assertEqual(57, self.tawnt.deger(ad))
        self.assertTrue(self.tawnt.preacquire(ad))

    def test_tekrar_tanim_ve_bozuk_sinir_reddedilir(self):
        self.tawnt.introduce("HIZ", min=0, max=100)

        with self.assertRaises(self.tawnt.TawntHatasi):
            self.tawnt.introduce("HIZ")
        with self.assertRaises(self.tawnt.TawntHatasi):
            self.tawnt.introduce("TERS", min=100, max=0)
        with self.assertRaises(self.tawnt.TawntHatasi):
            self.tawnt.introduce("TERCIH", min=0, max=10, preferred=20)

    def test_tanitilmadan_acquire_reddedilir(self):
        with self.assertRaises(self.tawnt.TawntHatasi):
            self.tawnt.acquire("BILINMEYEN", 10)

    def test_sinir_disi_deger_reddedilir(self):
        ad = self.tawnt.introduce("PWM", min=0, max=100)

        with self.assertRaises(self.tawnt.TawntHatasi):
            self.tawnt.acquire(ad, -1)
        with self.assertRaises(self.tawnt.TawntHatasi):
            self.tawnt.acquire(ad, 101)

    def test_olculdu_etiketi_tarih_ister(self):
        ad = self.tawnt.introduce("GERILIM", min=0, max=20)

        with self.assertRaises(self.tawnt.TawntHatasi):
            self.tawnt.acquire(ad, 10.2, kaynak=self.tawnt.OLCULDU)

    def test_preacquire_eksik_degeri_reddeder(self):
        ad = self.tawnt.introduce("KAMERA_FPS", min=1, max=120)

        with self.assertRaises(self.tawnt.TawntHatasi):
            self.tawnt.preacquire(ad)

    def test_v1_varsayilan_degeri_preacquire_kabul_eder(self):
        """Bu bir v1 sınırının kaydıdır; LIVE için istenen v2 davranışı değildir."""
        ad = self.tawnt.introduce("MAX_PWM", min=0, max=100)
        self.tawnt.acquire(ad, 57, kaynak=self.tawnt.VARSAYILDI)

        self.assertTrue(self.tawnt.preacquire(ad))

    def test_eksik_ikiz_reddedilir(self):
        perspektif = self.tawnt.introduce("PERSP_SRC")
        kare = self.tawnt.introduce("KARE")
        self.tawnt.IsTwinOf(perspektif, kare)
        self.tawnt.acquire(perspektif, [(0, 0)] * 4)

        with self.assertRaises(self.tawnt.TawntHatasi):
            self.tawnt.preacquire(perspektif)

    def test_bozuk_kardes_sirasi_reddedilir(self):
        olu = self.tawnt.introduce("OLU_BOLGE", min=0, max=100)
        hiz = self.tawnt.introduce("MIN_HIZ", min=0, max=100)
        self.tawnt.acquire(olu, 30)
        self.tawnt.acquire(hiz, 25)

        with self.assertRaises(self.tawnt.TawntHatasi):
            self.tawnt.siblingIntAppr(olu, "<=", hiz)

    def test_farkli_birimler_karsilastirilmaz(self):
        saniye = self.tawnt.introduce("TUREV_SANIYE")
        kare = self.tawnt.introduce("TUREV_KARE")
        self.tawnt.acquire(saniye, 50)
        self.tawnt.acquire(kare, 50)
        self.tawnt.identifyRuntimeType(saniye, "px/s")
        self.tawnt.identifyRuntimeType(kare, "px/kare")

        with self.assertRaises(self.tawnt.TawntHatasi):
            self.tawnt.siblingIntAppr(saniye, "<=", kare)

    def test_difference_skew_bir_pikseli_duzeltir_buyugunu_reddeder(self):
        koseler = [(0, 0), (10, 0), (0, 10), (9, 9)]
        duzeltilmis, tasindi = self.tawnt.differenceSkew(koseler, (10, 10))

        self.assertTrue(tasindi)
        self.assertEqual((10, 10), duzeltilmis[3])
        with self.assertRaises(self.tawnt.TawntHatasi):
            self.tawnt.differenceSkew(
                [(0, 0), (10, 0), (0, 10), (7, 7)], (10, 10)
            )

    def test_gecici_susturma_evre_degisince_kalkar(self):
        self.assertTrue(self.tawnt.pwmSerbestMi())
        self.tawnt.flushPWM("geçici görev arası", evre="YAYA")
        self.assertFalse(self.tawnt.pwmSerbestMi())

        sonuc = self.tawnt.evreDegisti("SERIT_TAKIP")

        self.assertTrue(sonuc)
        self.assertTrue(self.tawnt.pwmSerbestMi())

    def test_ciddi_kilit_evre_degisince_kalkmaz_ve_callback_calisir(self):
        kapanma_sayisi = []

        @self.tawnt.onShutdown
        def kapat():
            kapanma_sayisi.append(1)

        self.tawnt.declareUnexpectedSigint("kamera yok")

        self.assertEqual([1], kapanma_sayisi)
        self.assertFalse(self.tawnt.pwmSerbestMi())
        self.assertFalse(self.tawnt.evreDegisti("SERIT_TAKIP"))
        self.assertIsNotNone(self.tawnt.kilitDurumu())

    def test_report_kaynak_ve_degeri_gosterir(self):
        ad = self.tawnt.introduce("MAX_PWM", min=0, max=100)
        self.tawnt.acquire(
            ad,
            57,
            kaynak=self.tawnt.OLCULDU,
            tarih="2026-09-12",
        )

        rapor = self.tawnt.report()

        self.assertIn("OLCULDU", rapor)
        self.assertIn("MAX_PWM", rapor)
        self.assertIn("57", rapor)


class TestTawntV2Sozlesmesi(unittest.TestCase):
    """TAWNT.md §17–26 hedefleri; kod yazılana kadar bilerek atlanır."""

    @unittest.skip("V2 uygulanmadı: LIVE profili ve requireMeasured yok")
    def test_live_kritik_varsayilan_degeri_reddeder(self):
        tawnt.defineValue("MAX_PWM", critical=True)
        tawnt.recordValue("MAX_PWM", 57, source="VARSAYILDI")
        with self.assertRaises(tawnt.TawntHatasi):
            tawnt.validateBeforeStart(profile="LIVE")

    @unittest.skip("V2 uygulanmadı: başlangıç durumları ve arming kapısı yok")
    def test_program_baslangicinda_hareket_yasaktir(self):
        self.assertFalse(tawnt.isMotionAllowed())
        self.assertEqual("BOOT", tawnt.systemState())

    @unittest.skip("V2 uygulanmadı: seal ve değişmez kayıt yok")
    def test_dogrulamadan_sonra_deger_degistirilemez(self):
        tawnt.validateBeforeStart(profile="OFFLINE")
        tawnt.seal()
        with self.assertRaises(tawnt.TawntHatasi):
            tawnt.recordValue("MAX_PWM", 80)

    @unittest.skip("V2 uygulanmadı: bağımlılık revizyonu ve STALE durumu yok")
    def test_bagimlilik_degisince_deger_eskir(self):
        tawnt.recordValue("KARE", (800, 680))
        self.assertEqual("STALE", tawnt.valueState("PERSP_SRC"))

    @unittest.skip("V2 uygulanmadı: evreye bağlı zorunlu motor kapısı yok")
    def test_hata_evresinde_hareket_komutu_reddedilir(self):
        with self.assertRaises(tawnt.TawntHatasi):
            tawnt.validateMotorCommand(40, 40, phase="HATA")

    @unittest.skip("V2 uygulanmadı: NaN/aşırı PWM ciddi kilit sınıflandırması yok")
    def test_nan_ve_asiri_pwm_ciddi_kilit_uretir(self):
        for komut in ((math.nan, 30), (500, 500)):
            with self.assertRaises(tawnt.TawntHatasi):
                tawnt.validateMotorCommand(*komut, phase="SERIT_TAKIP")
            self.assertEqual("LATCHED_FAULT", tawnt.systemState())

    @unittest.skip("V2 uygulanmadı: kalıcı arıza deposu yok")
    def test_ciddi_kilit_restarttan_sonra_kalir(self):
        tawnt.latchFault("watchdog")
        yeniden = importlib.reload(tawnt)
        self.assertEqual("LATCHED_FAULT", yeniden.systemState())

    @unittest.skip("V2 uygulanmadı: insan ve motor anahtarı doğrulamalı reset yok")
    def test_insan_dogrulamasi_olmadan_reset_reddedilir(self):
        tawnt.latchFault("kamera yok")
        with self.assertRaises(tawnt.TawntHatasi):
            tawnt.resetFault(human=None, motor_power_off=False)

    @unittest.skip("V2 uygulanmadı: doğrudan GPIO/PWM statik tarayıcısı yok")
    def test_surucu_disinda_pwm_yazimi_bulunur(self):
        ihlaller = tawnt.scanDirectMotorWrites(Path(__file__).parent)
        self.assertEqual([], ihlaller)


if __name__ == "__main__":
    unittest.main(verbosity=2)
