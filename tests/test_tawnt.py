"""3awnt v1 uyumluluğu ve v2 davranış sözleşmesi testleri."""

from __future__ import annotations

import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import tawnt
from tawnt_core.runtime import runtime


class TawntTestCase(unittest.TestCase):
    def setUp(self):
        self.tawnt = tawnt
        self.tawnt.sifirla()
        self.gecici = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.gecici.name)
        runtime.gunluk_yolu = str(self.temp_path / "guvenlik.log")

    def tearDown(self):
        self.gecici.cleanup()

    def fault_store(self):
        path = self.temp_path / "fault.json"
        self.tawnt.configureFaultStore(path)
        return path

    def measured(self, name="MAX_PWM", value=57, **kwargs):
        key = self.tawnt.defineValue(name, critical=True, **kwargs)
        self.tawnt.recordValue(
            key,
            value,
            source=self.tawnt.OLCULDU,
            human="Egemen",
            date="2026-09-12",
            note="test olcumu",
        )
        return key

    def ready_phase(
        self,
        *,
        profile=None,
        phase="SERIT_TAKIP",
        motion_allowed=True,
        allow_reverse=False,
        allow_pivot=False,
        max_pwm=100,
        max_difference=100,
        max_slew=100,
        required_values=(),
        required_watchdogs=(),
    ):
        t = self.tawnt
        profile = profile or t.OFFLINE
        if profile == t.LIVE:
            self.fault_store()
        t.definePhase(
            phase,
            motion_allowed=motion_allowed,
            allow_reverse=allow_reverse,
            allow_pivot=allow_pivot,
            max_pwm=max_pwm,
            max_difference=max_difference,
            max_slew=max_slew,
            required_values=required_values,
            required_watchdogs=required_watchdogs,
        )
        t.validateBeforeStart(profile=profile)
        t.enterPhase(phase)
        t.arm(
            "Egemen",
            live_hardware_authorized=(profile == t.LIVE),
            final_confirmation=(profile == t.LIVE),
        )


class TestV1Uyumlulugu(TawntTestCase):
    def test_introduce_acquire_deger_ve_preacquire(self):
        t = self.tawnt
        ad = t.introduce("MAX_PWM", min=0, max=100, preferred=57)
        sonuc = t.acquire(
            ad, 57, kaynak=t.OLCULDU, kim="Egemen", tarih="2026-09-12"
        )
        self.assertEqual("MAX_PWM", ad)
        self.assertEqual(57, sonuc)
        self.assertEqual(57, t.deger(ad))
        self.assertTrue(t.preacquire(ad))

    def test_tekrar_tanim_bozuk_sinir_ve_tanitilmamis_deger_reddedilir(self):
        t = self.tawnt
        t.introduce("HIZ", min=0, max=100)
        with self.assertRaises(t.TawntHatasi):
            t.introduce("HIZ")
        with self.assertRaises(t.TawntHatasi):
            t.introduce("TERS", min=100, max=0)
        with self.assertRaises(t.TawntHatasi):
            t.acquire("BILINMEYEN", 10)

    def test_sinir_disi_ve_tarihsiz_olcum_reddedilir(self):
        t = self.tawnt
        pwm = t.introduce("PWM", min=0, max=100)
        for value in (-1, 101):
            with self.assertRaises(t.TawntHatasi):
                t.acquire(pwm, value)
        with self.assertRaises(t.TawntHatasi):
            t.acquire(pwm, 50, kaynak=t.OLCULDU)

    def test_v1_preacquire_varsayilani_kabul_eder(self):
        t = self.tawnt
        ad = t.introduce("MAX_PWM", min=0, max=100)
        t.acquire(ad, 57, kaynak=t.VARSAYILDI)
        self.assertTrue(t.preacquire(ad))

    def test_eksik_ikiz_ve_bozuk_sira_reddedilir(self):
        t = self.tawnt
        perspektif = t.introduce("PERSP_SRC")
        kare = t.introduce("KARE")
        t.IsTwinOf(perspektif, kare)
        t.acquire(perspektif, [(0, 0)] * 4)
        with self.assertRaises(t.TawntHatasi):
            t.preacquire(perspektif)

        t.sifirla()
        runtime.gunluk_yolu = str(self.temp_path / "guvenlik.log")
        olu = t.introduce("OLU_BOLGE", min=0, max=100)
        hiz = t.introduce("MIN_HIZ", min=0, max=100)
        t.acquire(olu, 30)
        t.acquire(hiz, 25)
        with self.assertRaises(t.TawntHatasi):
            t.siblingIntAppr(olu, "<=", hiz)

    def test_farkli_birimler_karsilastirilmaz(self):
        t = self.tawnt
        saniye = t.introduce("TUREV_SANIYE")
        kare = t.introduce("TUREV_KARE")
        t.acquire(saniye, 50)
        t.acquire(kare, 50)
        t.identifyRuntimeType(saniye, "px/s")
        t.identifyRuntimeType(kare, "px/kare")
        with self.assertRaises(t.TawntHatasi):
            t.siblingIntAppr(saniye, "<=", kare)

    def test_difference_skew_bir_pikseli_duzeltir_buyugunu_reddeder(self):
        t = self.tawnt
        fixed, moved = t.differenceSkew(
            [(0, 0), (10, 0), (0, 10), (9, 9)], (10, 10)
        )
        self.assertTrue(moved)
        self.assertEqual((10, 10), fixed[3])
        with self.assertRaises(t.TawntHatasi):
            t.differenceSkew([(0, 0), (10, 0), (0, 10), (7, 7)], (10, 10))

    def test_report_kaynak_deger_ve_durum_gosterir(self):
        t = self.tawnt
        ad = t.introduce("MAX_PWM", min=0, max=100)
        t.acquire(ad, 57, kaynak=t.OLCULDU, tarih="2026-09-12")
        rapor = t.report()
        self.assertIn("OLCULDU", rapor)
        self.assertIn("MAX_PWM", rapor)
        self.assertIn("RECORDED", rapor)


class TestDegerYasamDongusu(TawntTestCase):
    def test_nan_ve_sonsuz_yapilandirma_degerleri_reddedilir(self):
        t = self.tawnt
        with self.assertRaises(t.TawntHatasi):
            t.defineValue("BOZUK_MIN", min=math.nan)
        ad = t.defineValue("MAX_PWM", min=0, max=100)
        with self.assertRaises(t.TawntHatasi):
            t.recordValue(ad, math.inf)

    def test_kritik_deger_live_profilinde_olculmus_olmali(self):
        t = self.tawnt
        self.fault_store()
        ad = t.defineValue("MAX_PWM", min=0, max=100, critical=True)
        t.recordValue(ad, 57, source=t.VARSAYILDI)
        with self.assertRaises(t.TawntHatasi):
            t.validateBeforeStart(profile=t.LIVE)
        self.assertEqual(t.VALIDATING, t.systemState())

    def test_offline_varsayilan_degeri_kabul_eder(self):
        t = self.tawnt
        ad = t.defineValue("MAX_PWM", min=0, max=100, critical=True)
        t.recordValue(ad, 57, source=t.VARSAYILDI)
        summary = t.validateBeforeStart(profile=t.OFFLINE)
        self.assertEqual(t.READY_UNARMED, summary["state"])
        self.assertEqual(t.VALIDATED, t.valueState(ad))

    def test_live_fault_store_olmadan_dogrulanmaz(self):
        t = self.tawnt
        self.measured()
        with self.assertRaises(t.TawntHatasi):
            t.validateBeforeStart(profile=t.LIVE)

    def test_bagimlilik_degisince_deger_stale_olur(self):
        t = self.tawnt
        kare = t.defineValue("KARE")
        perspektif = t.defineValue("PERSP_SRC")
        t.dependsOn(perspektif, kare)
        t.recordValue(kare, (800, 680))
        t.recordValue(perspektif, [(0, 0)] * 4)
        t.validateBeforeStart(profile=t.OFFLINE)
        self.assertEqual(t.VALIDATED, t.valueState(perspektif))

        t.recordValue(kare, (640, 480))

        self.assertEqual(t.STALE, t.valueState(perspektif))
        with self.assertRaises(t.TawntHatasi):
            t.validateBeforeStart(profile=t.OFFLINE)

    def test_bagimlilik_dongusu_reddedilir(self):
        t = self.tawnt
        a = t.defineValue("A")
        b = t.defineValue("B")
        t.dependsOn(a, b)
        with self.assertRaises(t.TawntHatasi):
            t.dependsOn(b, a)

    def test_muhur_deger_degisikligini_reddeder(self):
        t = self.tawnt
        ad = t.defineValue("MAX_PWM", min=0, max=100)
        t.recordValue(ad, 57)
        t.validateBeforeStart(profile=t.OFFLINE)
        t.seal()
        self.assertEqual(t.SEALED, t.valueState(ad))
        with self.assertRaises(t.TawntHatasi):
            t.recordValue(ad, 60)


class TestSistemVeMotorKapisi(TawntTestCase):
    def test_sonsuz_evre_ve_watchdog_siniri_reddedilir(self):
        t = self.tawnt
        with self.assertRaises(t.TawntHatasi):
            t.definePhase("BOZUK", motion_allowed=True, max_pwm=math.inf)
        with self.assertRaises(t.TawntHatasi):
            t.defineWatchdog("kamera", timeout_seconds=math.nan)

    def test_program_baslangicinda_hareket_yasaktir(self):
        t = self.tawnt
        self.assertEqual(t.BOOT, t.systemState())
        self.assertFalse(t.isMotionAllowed())
        self.assertFalse(t.pwmSerbestMi())

    def test_offline_arming_ve_gecerli_komut(self):
        t = self.tawnt
        self.ready_phase(max_pwm=80, max_difference=30, max_slew=60)
        self.assertEqual(t.ARMED, t.systemState())
        self.assertTrue(t.isMotionAllowed())

        command = t.validateMotorCommand(40, 50, phase="SERIT_TAKIP")

        self.assertIsInstance(command, t.ValidatedMotorCommand)
        self.assertEqual((40.0, 50.0), (command.left, command.right))

    def test_heartbeat_gelmeden_gerekli_evreye_girilemez(self):
        t = self.tawnt
        kamera = t.defineWatchdog("kamera", timeout_seconds=1.0)
        t.definePhase(
            "SERIT_TAKIP",
            motion_allowed=True,
            max_pwm=80,
            required_watchdogs=(kamera,),
        )
        t.validateBeforeStart(profile=t.OFFLINE)

        with self.assertRaises(t.TawntHatasi):
            t.enterPhase("SERIT_TAKIP")
        self.assertFalse(t.isMotionAllowed())

    def test_taze_heartbeat_izin_verir_suresi_gecen_live_kilidi_uretir(self):
        t = self.tawnt
        self.measured()
        kamera = t.defineWatchdog("kamera", timeout_seconds=1.0)
        t.heartbeat(kamera)
        self.ready_phase(
            profile=t.LIVE,
            max_pwm=80,
            required_watchdogs=(kamera,),
        )
        self.assertIsInstance(
            t.validateMotorCommand(30, 30, phase="SERIT_TAKIP"),
            t.ValidatedMotorCommand,
        )

        runtime.watchdogs[kamera]["last_monotonic"] -= 2.0
        with self.assertRaises(t.TawntHatasi):
            t.validateMotorCommand(30, 30, phase="SERIT_TAKIP")
        self.assertEqual(t.LATCHED_FAULT, t.systemState())
        self.assertFalse(t.isMotionAllowed())

    def test_armed_evre_watchdog_hatasi_susturur_duzelince_yeniden_girilebilir(self):
        t = self.tawnt
        kamera = t.defineWatchdog("kamera", timeout_seconds=1.0)
        t.definePhase("A", motion_allowed=True, max_pwm=80)
        t.definePhase(
            "B",
            motion_allowed=True,
            max_pwm=80,
            required_watchdogs=(kamera,),
            allowed_from=("A",),
        )
        t.validateBeforeStart(profile=t.OFFLINE)
        t.enterPhase("A")
        t.arm("Egemen")

        with self.assertRaises(t.TawntHatasi):
            t.enterPhase("B")
        self.assertEqual(t.MUTED, t.systemState())
        self.assertFalse(t.isMotionAllowed())

        t.heartbeat(kamera)
        self.assertTrue(t.enterPhase("B"))
        self.assertEqual(t.ARMED, t.systemState())

    def test_dogrulama_sonrasi_yeni_politika_tekrar_dogrulama_ister(self):
        t = self.tawnt
        t.definePhase("A", motion_allowed=True, max_pwm=80)
        t.validateBeforeStart(profile=t.OFFLINE)
        t.definePhase("B", motion_allowed=True, max_pwm=80)
        self.assertEqual(t.VALIDATING, t.systemState())
        t.enterPhase("B")
        with self.assertRaises(t.TawntHatasi):
            t.arm("Egemen")

        t.validateBeforeStart(profile=t.OFFLINE)
        t.enterPhase("B")
        self.assertTrue(t.arm("Egemen"))

    def test_live_arm_insan_yetkisi_ve_son_onay_ister(self):
        t = self.tawnt
        key = self.measured()
        self.fault_store()
        t.definePhase(
            "SERIT_TAKIP", motion_allowed=True, max_pwm=57,
            required_values=(key,),
        )
        t.validateBeforeStart(profile=t.LIVE)
        t.enterPhase("SERIT_TAKIP")
        with self.assertRaises(t.TawntHatasi):
            t.arm("Egemen")
        self.assertTrue(
            t.arm(
                "Egemen",
                live_hardware_authorized=True,
                final_confirmation=True,
            )
        )

    def test_hareketsiz_evrede_komut_reddedilir(self):
        t = self.tawnt
        self.ready_phase(phase="HATA", motion_allowed=False, max_pwm=0)
        self.assertFalse(t.isMotionAllowed())
        with self.assertRaises(t.TawntHatasi):
            t.validateMotorCommand(40, 40, phase="HATA")
        self.assertEqual(t.MUTED, t.systemState())

    def test_nan_ve_asiri_pwm_live_kilidi_uretir(self):
        for left, right in ((math.nan, 30), (500, 500)):
            with self.subTest(left=left, right=right):
                self.tearDown()
                self.setUp()
                t = self.tawnt
                self.measured()
                self.ready_phase(profile=t.LIVE, max_pwm=100)
                with self.assertRaises(t.TawntHatasi):
                    t.validateMotorCommand(left, right, phase="SERIT_TAKIP")
                self.assertEqual(t.LATCHED_FAULT, t.systemState())
                self.assertFalse(t.isMotionAllowed())

    def test_ters_yon_pivot_fark_ve_slew_politikalari(self):
        t = self.tawnt
        self.ready_phase(max_pwm=100, max_difference=20, max_slew=10)
        t.validateMotorCommand(5, 5, phase="SERIT_TAKIP")
        with self.assertRaises(t.TawntHatasi):
            t.validateMotorCommand(-5, 5, phase="SERIT_TAKIP")
        self.assertEqual(t.MUTED, t.systemState())

        # Yeni temiz oturum: fark sınırı.
        self.tearDown()
        self.setUp()
        t = self.tawnt
        self.ready_phase(max_pwm=100, max_difference=20, max_slew=100)
        with self.assertRaises(t.TawntHatasi):
            t.validateMotorCommand(20, 60, phase="SERIT_TAKIP")

    def test_pivot_yalniz_izinli_evrede_gecer(self):
        t = self.tawnt
        self.ready_phase(
            phase="CIKMAZ",
            allow_reverse=True,
            allow_pivot=True,
            max_pwm=80,
            max_difference=160,
            max_slew=100,
        )
        command = t.validateMotorCommand(-40, 40, phase="CIKMAZ")
        self.assertEqual((-40.0, 40.0), (command.left, command.right))

    def test_gecici_susturma_farkli_evrede_kalkar_kilit_kalkmaz(self):
        t = self.tawnt
        t.definePhase("A", motion_allowed=True, max_pwm=100)
        t.definePhase("B", motion_allowed=True, max_pwm=100, allowed_from=("A",))
        t.validateBeforeStart(profile=t.OFFLINE)
        t.enterPhase("A")
        t.arm("Egemen")
        t.flushPWM("gorev arasi", evre="A")
        self.assertEqual(t.MUTED, t.systemState())
        t.enterPhase("B")
        self.assertTrue(t.isMotionAllowed())

        t.latchFault("kamera yok")
        self.assertFalse(t.evreDegisti("A"))
        self.assertEqual(t.LATCHED_FAULT, t.systemState())


class TestKaliciKilit(TawntTestCase):
    def test_import_ve_configure_dosya_olusturmaz(self):
        path = self.temp_path / "fault.json"
        self.assertFalse(path.exists())
        self.tawnt.configureFaultStore(path)
        self.assertFalse(path.exists())

    def test_ciddi_kilit_reload_sonrasi_yuklenir(self):
        path = self.fault_store()
        self.tawnt.latchFault("watchdog", "kamera gecikti")
        self.assertTrue(path.exists())

        script = (
            "import sys, tawnt; "
            "tawnt.configureFaultStore(sys.argv[1]); "
            "print(tawnt.systemState()); "
            "print(tawnt.isMotionAllowed()); "
            "print(tawnt.kilitDurumu()['sebep'])"
        )
        result = subprocess.run(
            [sys.executable, "-c", script, str(path)],
            cwd=Path(__file__).resolve().parent.parent,
            check=True,
            capture_output=True,
            text=True,
        )

        self.assertEqual(["LATCHED_FAULT", "False", "watchdog"], result.stdout.splitlines())

    def test_bozuk_fault_store_fail_closed(self):
        path = self.temp_path / "fault.json"
        path.write_text("{bozuk-json", encoding="utf-8")
        self.tawnt.configureFaultStore(path)
        self.assertEqual(self.tawnt.LATCHED_FAULT, self.tawnt.systemState())
        self.assertIn("bozuk", self.tawnt.kilitDurumu()["sebep"])

    def test_reset_insan_ve_motor_gucu_beyani_ister(self):
        t = self.tawnt
        path = self.fault_store()
        t.latchFault("kamera yok")
        with self.assertRaises(t.TawntHatasi):
            t.resetFault("", motor_power_off=True)
        with self.assertRaises(t.TawntHatasi):
            t.resetFault("Egemen", motor_power_off=False)

        self.assertTrue(t.resetFault("Egemen", motor_power_off=True))
        self.assertEqual(t.VALIDATING, t.systemState())
        self.assertIsNone(t.kilitDurumu())
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertFalse(data["active"])
        self.assertEqual("Egemen", data["reset"]["human"])


class TestStatikTarama(TawntTestCase):
    def test_dogrudan_motor_yazimi_ve_hardcoded_komut_bulunur(self):
        (self.temp_path / "unsafe.py").write_text(
            "motor.value = 1.0\nset_pwm(90, 90)\n", encoding="utf-8"
        )
        (self.temp_path / "controller.py").write_text(
            "surucu.applyMotorCommand(50, 60, 'SERIT')\n", encoding="utf-8"
        )
        (self.temp_path / "safe.py").write_text(
            "surucu.applyMotorCommand(sol, sag, evre)\n", encoding="utf-8"
        )
        (self.temp_path / "surucu.py").write_text(
            "def _writePwm(sol, sag):\n    pass\n", encoding="utf-8"
        )

        violations = self.tawnt.scanDirectMotorWrites(self.temp_path)
        paths = {item["path"] for item in violations}

        self.assertIn("unsafe.py", paths)
        self.assertIn("controller.py", paths)
        self.assertNotIn("safe.py", paths)
        self.assertNotIn("surucu.py", paths)

    def test_syntax_hatasi_raporlanir(self):
        (self.temp_path / "broken.py").write_text("if :\n", encoding="utf-8")
        violations = self.tawnt.scanDirectMotorWrites(self.temp_path)
        self.assertEqual("broken.py", violations[0]["path"])
        self.assertEqual(0, violations[0]["line"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
