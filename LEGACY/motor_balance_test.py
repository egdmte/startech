#!/usr/bin/env python3
# =============================================================================
# motor_balance_test.py  —  Sol/sağ motor denge kalibrasyonu
#
# Araç düz bir zeminde ilerlerken sapıyorsa bu scripti çalıştır.
# Ölçüm yaparak LEFT_TRIM / RIGHT_TRIM değerlerini hesaplar.
#
# Kullanım:
#   python motor_balance_test.py
#
# Gerekli: Düz zemin (en az 1 metre), cetvel veya mezura
# =============================================================================
import time
import sys
import math

try:
    from motor import MotorDriver, MotorHardwareUnavailable
except ImportError:
    print("motor.py bulunamadı. Aynı klasörde çalıştır.")
    sys.exit(1)

TEST_SPEED    = 50    # % — test hızı
TEST_DURATION = 2.0   # saniye — ne kadar ileri gideceği
TRACK_LENGTH  = None  # cm — gerçek mesafe (ölçeceksin)

motor = None

def run_straight_test():
    if motor is None:
        raise RuntimeError("Motor başlatılmadı")
    print("\n" + "="*50)
    print("  MOTOR DENGE TESTİ")
    print("="*50)
    print(f"\nAraç {TEST_DURATION} saniye boyunca {TEST_SPEED}% hızda ileri gidecek.")
    print("Başlamadan önce aracı düz bir çizgiye hizala.")
    print("\nHazır mısın? 3 saniye sonra başlıyor...")
    time.sleep(3)

    motor.set_speed(TEST_SPEED, TEST_SPEED)
    # LEGACY-070: Istenen hiz DEAD_ZONE_MIN_PWM'in altindaysa (ya da
    # trim sonrasi altina duserse), motor.py komutu tabana YUKSELTIR.
    # O zaman "TEST_SPEED hizinda gidiyor" yazisi YANLISTIR — gercekte
    # UYGULANAN PWM farklidir ve bu, trim cikarimini gecersiz kilar
    # (doygun bolgede iki teker HER ZAMAN esitlenir, gercek dengesizlik
    # gizlenir). Gercek uygulanan degerleri OKUYUP goster.
    _actual_l = getattr(motor, "_left_pwm", None)
    _actual_r = getattr(motor, "_right_pwm", None)
    _clamped = False
    if _actual_l is not None and _actual_r is not None:
        _al, _ar = _actual_l.value * 100, _actual_r.value * 100
        if abs(_al - TEST_SPEED) > 0.5 or abs(_ar - TEST_SPEED) > 0.5:
            _clamped = True
            print(f"\n⚠️  UYARI: istenen hız {TEST_SPEED}% idi, GERÇEK uygulanan "
                  f"PWM: sol={_al:.1f}% sağ={_ar:.1f}% (ölü bölge/trim tabanı "
                  "devreye girdi).")
            print("   Bu ölçüm, DOYGUN bölgede yapıldığı için trim çıkarımı "
                  "GÜVENİLMEZ olabilir — iki teker taban tarafından eşitlenmiş "
                  "olabilir. --hiz ile DEAD_ZONE_MIN_PWM'in belirgin üzerinde "
                  "bir değer (örn. 40+) seçerek tekrarlayın.")
    time.sleep(TEST_DURATION)
    motor.brake()
    time.sleep(0.5)
    motor.coast()

    print("\nAraç durdu.")
    print("Şimdi aracın başlangıç çizgisinden ne kadar saptığını ölç.")
    print("(Sağ sapma = pozitif, Sol sapma = negatif)")
    
    try:
        sapma = float(input("\nSapma miktarı (cm, sağ = +, sol = -): "))
        mesafe = float(input("Toplam ilerlenen mesafe (cm): "))
    except ValueError:
        print("Geçersiz giriş.")
        return

    if not math.isfinite(sapma) or not math.isfinite(mesafe) or mesafe <= 0:
        print("Sapma sonlu, mesafe sonlu ve sıfırdan büyük olmalı.")
        return

    # Sapma oranı hesabı
    oran = sapma / mesafe

    print(f"\nSapma oranı: {oran:.4f}")

    if _clamped:
        print("\n⚠️  Bu ölçüm ölü bölge/trim tabanında YAPILDI (yukarıdaki")
        print("   uyarıya bakın) — aşağıdaki trim önerisi GÜVENİLMEZ olabilir.")

    if abs(sapma) < 2:
        print("\n✅ Araç dengeli! Trim değişikliği gerekmiyor.")
        print("   config.py'deki dört değer de 1.0 kalabilir:")
        print("   LEFT_TRIM_LOW / LEFT_TRIM_HIGH / RIGHT_TRIM_LOW / RIGHT_TRIM_HIGH")
        return

    # LEGACY-029 (bu dosyadaki ayni formul yonu — denetimin "same formula
    # direction" olarak isaretledigi yer): DOKUMANLI ileri-yonlu kablolama
    # altinda (pozitif komut HER IKI tekeri ileri surer), SAGA sapan bir
    # aracin SOL tekeri SAG tekere gore DAHA HIZLIDIR. Duzeltme SOL tekeri
    # azaltmalidir. Eski kod SAG tekeri azaltiyordu — bu sapmayi ARTIRIRDI.
    # LEGACY-071: sonuc asla sifir/negatif olamaz (surucu boylelerini
    # reddeder).
    oran_clamped = min(abs(oran), 0.30)   # asiri duzeltmeyi sinirla
    if sapma > 0:
        # Sağa sapıyor → SOL teker hızlı → SOL trim azalt (SAĞ değil)
        new_left  = max(0.05, round(1.0 - oran_clamped * 0.5, 3))
        new_right = 1.0
        print(f"\n⚠️  Araç SAĞA sapıyor ({sapma:.1f} cm)")
        print(f"   Bu, SOL tekerin göreli olarak daha hızlı olduğu anlamına gelir.")
        print(f"   Ölçülen oran: sol {new_left}, sağ {new_right}")
    else:
        # Sola sapıyor → SAĞ teker hızlı → SAĞ trim azalt (SOL değil)
        new_right = max(0.05, round(1.0 - oran_clamped * 0.5, 3))
        new_left  = 1.0
        print(f"\n⚠️  Araç SOLA sapıyor ({sapma:.1f} cm)")
        print(f"   Bu, SAĞ tekerin göreli olarak daha hızlı olduğu anlamına gelir.")
        print(f"   Ölçülen oran: sol {new_left}, sağ {new_right}")
    print("   ⚠️  FİZİKSEL DOĞRULAMA GEREKLİ: bu öneri, pozitif komutun her iki")
    print("   tekerleği İLERİ sürdüğü varsayımına dayanır. Uygulamadan önce")
    print("   tekerlekleri yerden kesip yön konvansiyonunu doğrulayın.")

    # -----------------------------------------------------------------
    # DÜZELTİLDİ 5 Ağustos 2026 — PLAN_New.md 20.3e, HATA_DEFTERİ hata 3.
    #
    # Bu betik eskiden "LEFT_TRIM" ve "RIGHT_TRIM" adlarını yazdırıyordu.
    # config.py bu iki adı OKUMUYOR. Gerçekte dört değer var:
    #   LEFT_TRIM_LOW  LEFT_TRIM_HIGH  RIGHT_TRIM_LOW  RIGHT_TRIM_HIGH
    # Yani çıktıyı yapıştıran kişi config.py'ye hiçbir etkisi olmayan iki
    # satır ekliyordu; ölçüm yapılmış gibi görünüyor, araç değişmiyordu.
    # Mayıs'ta dört trim'in de 1.0 kalmasının muhtemel sebebi budur.
    # -----------------------------------------------------------------
    profil = ("LOW" if TEST_SPEED < 40 else
              "HIGH" if TEST_SPEED > 70 else "ARADA")

    print("\n📋 config.py'ye yapıştır — DÖRT ad da config.py'nin okuduğu adlardır:")
    if profil == "LOW":
        print(f"   LEFT_TRIM_LOW   = {new_left}")
        print(f"   RIGHT_TRIM_LOW  = {new_right}")
        print("   (HIGH profili için testi 70'in ÜSTÜNDE bir hızla tekrarla)")
    elif profil == "HIGH":
        print(f"   LEFT_TRIM_HIGH  = {new_left}")
        print(f"   RIGHT_TRIM_HIGH = {new_right}")
        print("   (LOW profili için testi 40'ın ALTINDA bir hızla tekrarla)")
    else:
        print(f"   ⚠️  TEST_SPEED = {TEST_SPEED} — bu değer 40 ile 70 ARASINDA.")
        print("   motor.py:_get_trim bu aralıkta LOW ve HIGH'ı harmanlıyor,")
        print("   yani bu ölçüm İKİ profilden hiçbirini temiz vermiyor.")
        print("   Betiği iki kez çalıştır:")
        print("     python motor_balance_test.py --hiz 35   → LOW profili")
        print("     python motor_balance_test.py --hiz 80   → HIGH profili")
        print(f"   (ölçülen oranlar yine de: sol {new_left}, sağ {new_right})")

    print("\nDeğişikliği yaptıktan sonra testi tekrar çalıştırarak doğrula.")


def run_pwm_sweep():
    """Her iki motoru ayrı ayrı test eder — fiziksel fark var mı kontrol eder."""
    if motor is None:
        raise RuntimeError("Motor başlatılmadı")
    print("\n" + "="*50)
    print("  PWM SÜPÜRME TESTİ (tek tek motor)")
    print("="*50)

    # LEGACY-072: Eski kod --hiz/--sure NE VERILIRSE VERILSIN her zaman
    # %50 / 1.5s kullaniyordu. Baslangicta 'TEST_SPEED=X TEST_DURATION=Y'
    # yazdirilip GERCEKTE farkli, SABIT degerler uygulaniyordu — dusuk bir
    # test hizi secen biri, cagriya bakarak beklemedigi kadar YUKSEK bir
    # gercek komut alabiliyordu. Simdi taninmis/dogrulanmis ayarlar
    # kullanilir ve gercek supurme degerleri onay ISTEMINDEN ONCE
    # acikca yazdirilir.
    spd = TEST_SPEED
    dur = TEST_DURATION
    print(f"\nSüpürme ayarları: hız={spd}%  süre={dur}s  (--hiz / --sure ile ayarlanır)")

    for side, spd_l, spd_r in [
        ("SOL  motor ileri", spd, 0),
        ("SAĞ  motor ileri", 0,  spd),
        ("Her ikisi", spd, spd),
    ]:
        input(f"\n[ENTER] → {side} testi ({spd}%, {dur}s) başlasın")
        motor.set_speed(spd_l, spd_r)
        time.sleep(dur)
        motor.brake()
        time.sleep(0.3)
        motor.coast()

    print("\nTest bitti. Motor seslerini / hızlarını karşılaştır.")
    print("Belirgin fark varsa fiziksel sorun (motor bağlantısı, direnç) olabilir.")


if __name__ == "__main__":
    # --hiz eklendi 5 Agustos 2026. Sebep: cikti "testi 35 ve 80 ile tekrarla"
    # diyordu ama hizi degistirmenin tek yolu dosyayi elle duzenlemekti.
    # Calistirilamayan bir talimat, talimat degildir.
    import argparse
    _ap = argparse.ArgumentParser(description="Motor denge kalibrasyonu")
    _ap.add_argument("--hiz", type=float, default=TEST_SPEED,
                     help="test hizi %% (LOW profili icin <40, HIGH icin >70)")
    _ap.add_argument("--sure", type=float, default=TEST_DURATION,
                     help="ileri gidis suresi, saniye")
    _a = _ap.parse_args()
    TEST_SPEED    = _a.hiz
    TEST_DURATION = _a.sure

    if (not math.isfinite(TEST_SPEED) or not 0 < TEST_SPEED <= 100
            or not math.isfinite(TEST_DURATION) or TEST_DURATION <= 0):
        _ap.error("--hiz 0..100 arasında, --sure sıfırdan büyük ve sonlu olmalı")

    print("Motor Denge Kalibrasyonu")
    print(f"   TEST_SPEED = {TEST_SPEED}  TEST_DURATION = {TEST_DURATION}")
    print("")
    print("  ⚠️  TEKERLEKLER YERDEN YUKSEK OLSUN — bu betik motorlari dondurur.")
    print("      Ilk calistirmada araci havada veya bloklu tut (CLAUDE.md).")
    print("")
    print("1) Düz gidiş testi (trim hesapla)")
    print("2) PWM süpürme testi (motor fiziksel kontrolü)")

    # LEGACY-034: Yakalanan her hata artik ACIKCA bir cikis koduyla
    # bildiriliyor. Eski kod hatayi yazdirip SIFIR (basari) koduyla
    # cikiyordu; kalibrasyon.py'nin `subprocess.run(check=True)` ile
    # calistirdigi cagiran, basarisiz bir donanim/girdi denemesini
    # BASARILI sanip devam edebiliyordu.
    _exit_code = 0
    try:
        motor = MotorDriver()
        motor.require_hardware()
        sec = input("\nSeçim (1/2): ").strip()
        if sec == "1":
            run_straight_test()
        elif sec == "2":
            run_pwm_sweep()
        else:
            print("Geçersiz seçim.")
            _exit_code = 1
    except KeyboardInterrupt:
        print("\nKesintiye uğradı.")
        _exit_code = 130
    except MotorHardwareUnavailable as exc:
        print(f"\nBaşlatılamadı: {exc}")
        _exit_code = 1
    finally:
        if motor is not None:
            motor.stop()
    raise SystemExit(_exit_code)
