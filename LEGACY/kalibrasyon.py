#!/usr/bin/env python3
# =============================================================================
# kalibrasyon.py  —  SÜPER KOLAY KALİBRASYON MENÜSÜ
#
# Tüm kalibrasyon araçlarını tek menüden çalıştır.
# 
# Kullanım:
#   python kalibrasyon.py
#
# Bu araç sana:
# - Motor dengeleme yapar
# - HSV (beyaz şerit) kalibre eder  
# - Kuş bakışı perspektif ayarlar
# - PD parametreleri tunlar
# - Kameranın gördüklerini gösterir
# =============================================================================
import os
import subprocess
import sys
import time
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent


def _write_config_assignment(config_path: Path, assignments: dict) -> None:
    """LEGACY-032: config.py'ye ATOMIK ve DOGRULANMIS yaz.

    Eski kod dogrudan config.py'yi acip yazıyordu (re.sub + write_text).
    Yazma sirasinda kesinti/disk-dolu/IO hatasi olursa, ORIJINAL dosya
    KISMEN UZERINE YAZILMIS, GECERSIZ bir Python modulu olarak kalabilir
    — bu da HER ARACI (main.py dahil) baslangicta bozar.

    Bu fonksiyon:
      1. Degisikligi BELLEKTE uygular (orijinal dosyaya DOKUNMADAN).
      2. Sonucu `ast.parse` ile SOZDIZIMSEL olarak dogrular.
      3. Ayni klasorde bir GECICI KARDES dosyaya yazip flush+fsync yapar.
      4. `os.replace` ile ATOMIK olarak yerine koyar (POSIX'te ya
         TAMAMI ya HICBIRI gerceklesir; yarim dosya olusmaz).
    Herhangi bir adim basarisiz olursa ORIJINAL DOSYA DEGISMEDEN kalir.
    """
    import ast
    import re
    import tempfile

    content = config_path.read_text(encoding="utf-8")
    new_content = content
    for name, value in assignments.items():
        pattern = rf'^{re.escape(name)}\s*=\s*.+$'
        replacement = f"{name} = {value!r}"
        updated, count = re.subn(pattern, replacement, new_content,
                                 count=1, flags=re.MULTILINE)
        if count != 1:
            raise RuntimeError(
                f"config.py içinde '{name}' ataması tam olarak bir kez "
                f"bulunamadı (bulunan: {count})"
            )
        new_content = updated

    # Yazmadan ÖNCE doğrula: sonuç geçerli Python olmalı.
    try:
        ast.parse(new_content)
    except SyntaxError as exc:
        raise RuntimeError(
            f"oluşan config.py sözdizimi hatalı olurdu, YAZILMADI: {exc}"
        ) from exc

    # Geçici kardeş dosyaya yaz, flush+fsync, sonra ATOMİK yer değiştir.
    fd, tmp_path = tempfile.mkstemp(
        dir=str(config_path.parent), prefix=".config_tmp_", suffix=".py"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(new_content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, str(config_path))   # POSIX'te atomik
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

# Türkçe karakter desteği
try:
    sys.stdout.reconfigure(encoding='utf-8')
except (AttributeError, OSError):
    pass


def clear_screen():
    """Ekranı temizle."""
    os.system('clear' if os.name == 'posix' else 'cls')


def print_baslik(text):
    """Başlık göster."""
    print()
    print("╔" + "═" * 60 + "╗")
    print(f"║  {text:<58}║")
    print("╚" + "═" * 60 + "╝")
    print()


def bekle(saniye=1):
    """Belirli süre bekle."""
    time.sleep(saniye)


def basinca_devam():
    """Kullanıcı ENTER'a basana kadar bekle."""
    input("\n[ENTER]'a basın...")


def araci_calistir(script_name):
    """Bir LEGACY aracını doğru klasörden çalıştır ve hatasını gizleme."""
    script_path = SCRIPT_DIR / script_name
    subprocess.run(
        [sys.executable, str(script_path)],
        cwd=str(SCRIPT_DIR),
        check=True,
    )


# =============================================================================
# 1. MOTOR DENGELEME
# =============================================================================
def motor_dengeleme():
    """Aracı düz gidip ne kadar saptığını ölç."""
    clear_screen()
    print_baslik("1️⃣  MOTOR DENGELEME")
    
    print("📋 BU TEST NE YAPAR?")
    print("─" * 62)
    print("• Araç 2 saniye düz ileri gidecek")
    print("• Sapma miktarını ölçeceksin")
    print("• Program sana yeni TRIM değerlerini söyleyecek")
    print()
    print("📐 HAZIRLIK:")
    print("─" * 62)
    print("1. Aracı düz bir çizgiye hizala")
    print("2. Önünde en az 1.5 metre boşluk olsun")
    print("3. Cetvel veya mezura hazır olsun")
    print()
    
    # LEGACY-026: Bos girdi (sadece Enter) MOTOR HAREKETINI yetkilendiremez.
    # Eski kosul `secim != 'e' and secim != ''` idi: Enter'a basmak onay
    # sayiliyor, GPIO aciliyor ve geri sayimdan sonra 50/50 surus
    # basliyordu. Istem hicbir yerde varsayilan onay ilan etmiyor, ayni
    # menudeki diger surus istemleri ise acik 'e' istiyor.
    print()
    print("⚠️  UYARI: Bu test GERCEK MOTORLARI calistirir ve arac HAREKET EDER.")
    print("   Tekerleklerin yerden kesik veya onunde bos alan oldugundan emin olun.")
    secim = input("Test başlasın mı? Onaylamak icin 'E' yazin [E/H]: ").strip().lower()
    if secim != 'e':
        print("İptal edildi (acik onay verilmedi).")
        bekle()
        return
    
    try:
        from motor import MotorDriver
        motor = MotorDriver()
        motor.require_hardware()
    except Exception as e:
        print(f"❌ Motor başlatılamadı: {e}")
        basinca_devam()
        return
    
    try:
        print("\n3 saniye sonra başlıyor...")
        for i in [3, 2, 1]:
            print(f"  {i}...")
            bekle(1)

        print("\n🚗 İLERİ! (2 saniye)")
        motor.set_speed(50, 50)
        bekle(2.0)
    finally:
        try:
            motor.brake()
            bekle(0.5)
        finally:
            motor.stop()
    
    print("\n✅ Araç durdu!")
    print()
    print("📐 ÖLÇÜM:")
    print("─" * 62)
    print("Şimdi başlangıç çizgisinden ne kadar saptığını ölç.")
    print("• SAĞA saptıysa: pozitif değer (örn: +10)")
    print("• SOLA saptıysa: negatif değer (örn: -10)")
    print("• Düz gittiysе: 0")
    print()
    
    # LEGACY-027: Sonlu olmayan olcum (nan/inf) makul gorunen ama tamamen
    # keyfi trim tavsiyesi uretiyordu. Acikca reddet.
    import math as _math
    try:
        sapma = float(input("Sapma (cm, sağ=+, sol=-): "))
    except ValueError:
        print("❌ Geçersiz değer.")
        basinca_devam()
        return
    if not _math.isfinite(sapma):
        print("❌ Ölçüm sonlu bir sayı olmalı (nan/inf kabul edilmez).")
        basinca_devam()
        return
    if abs(sapma) > 500:
        print("❌ Ölçüm makul aralığın dışında (|sapma| > 500 cm).")
        basinca_devam()
        return

    # LEGACY-028: Olcum ZATEN TRIMLENMIS bir araca aittir (motor.set_speed
    # trim uygular). Tavsiyeleri 1.0 etrafinda yeniden kurmak, calisan bir
    # kalibrasyonu geri alir. Bu yuzden mevcut AKTIF trim tabani okunur ve
    # duzeltme ona GORECELI hesaplanir.
    try:
        from config import (LEFT_TRIM_LOW as _LTL, LEFT_TRIM_HIGH as _LTH,
                            RIGHT_TRIM_LOW as _RTL, RIGHT_TRIM_HIGH as _RTH)
    except Exception:
        _LTL = _LTH = _RTL = _RTH = 1.0

    print()
    print("📊 MEVCUT AKTİF TRIM TABANI (ölçüm bu değerlerle yapıldı):")
    print(f"   LEFT_TRIM_LOW={_LTL}  LEFT_TRIM_HIGH={_LTH}")
    print(f"   RIGHT_TRIM_LOW={_RTL} RIGHT_TRIM_HIGH={_RTH}")
    print()

    if abs(sapma) < 2:
        # LEGACY-028: Dengeli sonuc "1.0 yaz" DEMEZ; mevcut degerleri KORU der.
        print("✅ ARAÇ DENGELİ! Mevcut TRIM değerlerini DEĞİŞTİRMEYİN.")
        print("   Bu ölçüm yukarıdaki aktif trim tabanıyla yapıldı;")
        print("   1.0'a döndürmek çalışan kalibrasyonu geri alır.")
    else:
        # LEGACY-029: DOKUMANLI konvansiyon altinda (pozitif komut her iki
        # tekeri ILERI surer, sol/sag etiketleri fiziksel olarak dogru):
        # SAGA kivrilan aracin SOL tekeri, sag tekerine gore DAHA HIZLIDIR.
        # Duzeltme bu yuzden SOL tekeri azaltmalidir. Eski kod sag tekeri
        # azaltarak kivrimi ARTIRIYORDU. Sol sapma dali da simetrik olarak
        # tersti.
        oran = min(0.15, abs(sapma) / 100.0)
        if sapma > 0:
            yon, hedef = "SAĞA", "SOL"
            new_low  = round(_LTL * (1.0 - oran), 3)
            new_high = round(_LTH * (1.0 - oran), 3)
            adlar = ("LEFT_TRIM_LOW", "LEFT_TRIM_HIGH")
        else:
            yon, hedef = "SOLA", "SAĞ"
            new_low  = round(_RTL * (1.0 - oran), 3)
            new_high = round(_RTH * (1.0 - oran), 3)
            adlar = ("RIGHT_TRIM_LOW", "RIGHT_TRIM_HIGH")

        # LEGACY-071: Surucu sifir/negatif trimi reddeder; asla onermeyin.
        new_low  = max(0.05, new_low)
        new_high = max(0.05, new_high)

        print(f"⚠️  ARAÇ {yon} SAPIYOR ({abs(sapma):.1f} cm)")
        print(f"   Bu, {hedef} tekerleğin göreli olarak daha hızlı olduğu anlamına gelir.")
        print()
        print("📋 ÖNERİ — mevcut tabana GÖRECELİ düzeltme:")
        print("─" * 62)
        print(f"   {adlar[0]}  = {new_low}")
        print(f"   {adlar[1]} = {new_high}")
        print()
        print("⚠️  FİZİKSEL DOĞRULAMA GEREKLİ: Bu öneri, pozitif komutun her iki")
        print("   tekerleği İLERİ sürdüğü ve sol/sağ etiketlerinin fiziksel olarak")
        print("   doğru olduğu varsayımına dayanır. Uygulamadan önce tekerlekleri")
        print("   yerden kesip yön konvansiyonunu doğrulayın.")

    print()
    basinca_devam()


# =============================================================================
# 2. HSV KALİBRASYON (Beyaz Şerit Tespiti) — İNTERAKTİF
# =============================================================================
def hsv_kalibrasyon():
    """İnteraktif HSV ayarlama — slider'larla beyaz şerit eşiklerini bul."""
    clear_screen()
    print_baslik("2️⃣  HSV KALİBRASYON (BEYAZ ŞERİT)")
    
    print("📋 BU TEST NE YAPAR?")
    print("─" * 62)
    print("• Kamera açılır, canlı görüntü gösterilir")
    print("• 6 slider ile HSV eşikleri ayarlanır")
    print("• Beyaz şerit BEYAZ görünmeli, geri kalan SİYAH")
    print()
    print("🎮 KONTROLLER:")
    print("─" * 62)
    print("• Slider'ları ayarla → beyaz şerit ayrılana kadar")
    print("• 's' tuşu → değerleri kaydet ve config.py'ye yaz")
    print("• 'q' tuşu → çık")
    print()
    
    basinca_devam()
    
    try:
        import cv2
        import numpy as np
    except ImportError:
        print("❌ opencv-python kurulu değil")
        basinca_devam()
        return
    
    # Kamera başlat
    camera = None
    is_picam = False
    try:
        from picamera2 import Picamera2
        camera = Picamera2()
        try:
            camera.configure(camera.create_preview_configuration(
                main={"size": (640, 480), "format": "RGB888"}
            ))
            camera.start()
            time.sleep(1)
        except BaseException:
            try:
                camera.close()
            except Exception:
                pass
            raise
        is_picam = True
        print("✅ Pi kamerası açıldı")
    except Exception as pi_error:
        camera = cv2.VideoCapture(0)
        if not camera.isOpened():
            camera.release()
            print("❌ Kamera açılamadı!")
            print(f"   Pi kamera sonucu: {pi_error}")
            basinca_devam()
            return
        print("✅ USB kamera açıldı")
    
    bekle(1)
    
    try:
        # Slider penceresi oluştur
        cv2.namedWindow("HSV Ayarları", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("HSV Ayarları", 400, 300)

        # LEGACY-031: `from config import ...` zaten ICE AKTARILMIS
        # modulu okur — ayni surec icinde bu menu daha once ACILIP
        # KAYDETMISSE (ya da baska bir arac config.py'yi disaridan
        # degistirdiyse), burada hala ESKI (surec baslangicindaki)
        # degerler gorulur. importlib.reload ile GERCEKTEN GUNCEL dosya
        # okunur.
        import importlib
        import config as _cfg
        importlib.reload(_cfg)

        # LEGACY-031 (devam): Slider ARTIK KOR KORUNE 'NORMAL' ile
        # baslamiyor. Onizleme icin BIR kare orneklenip GERCEK V_mean
        # olculur; slider o anki AYDINLATMAYA uyan profille acilir —
        # boylece KARANLIK/PARLAK bir ortamda NORMAL degerlerle
        # baslayip yanlislikla o profili KAYDETME riski azalir.
        try:
            if is_picam:
                _probe = camera.capture_array()
                _probe_bgr = cv2.cvtColor(_probe, cv2.COLOR_RGB2BGR)
            else:
                _ok, _probe_bgr = camera.read()
                if not _ok:
                    raise RuntimeError("örnek kare alınamadı")
            _probe_v = float(np.mean(cv2.cvtColor(_probe_bgr, cv2.COLOR_BGR2HSV)[:, :, 2]))
        except Exception:
            _probe_v = 150.0   # bilinmiyorsa NORMAL varsay

        if _probe_v < 100:
            _initial_profile = "DARK"
        elif _probe_v > 200:
            _initial_profile = "BRIGHT"
        else:
            _initial_profile = "NORMAL"

        try:
            h_low, s_low, v_low = getattr(_cfg, f"WHITE_HSV_LOW_{_initial_profile}")
            h_high, s_high, v_high = getattr(_cfg, f"WHITE_HSV_HIGH_{_initial_profile}")
            print(f"   (Örnek V_mean={_probe_v:.0f} → {_initial_profile} "
                  "profili ile başlatılıyor)")
        except (AttributeError, TypeError, ValueError):
            h_low, s_low, v_low = 0, 0, 120
            h_high, s_high, v_high = 180, 85, 255

        cv2.createTrackbar("H Min", "HSV Ayarları", h_low, 180, lambda x: None)
        cv2.createTrackbar("S Min", "HSV Ayarları", s_low, 255, lambda x: None)
        cv2.createTrackbar("V Min", "HSV Ayarları", v_low, 255, lambda x: None)
        cv2.createTrackbar("H Max", "HSV Ayarları", h_high, 180, lambda x: None)
        cv2.createTrackbar("S Max", "HSV Ayarları", s_high, 255, lambda x: None)
        cv2.createTrackbar("V Max", "HSV Ayarları", v_high, 255, lambda x: None)

        print("\n🎮 PENCERE AÇILDI — Slider'ları ayarla")
        print("   's' = Kaydet | 'q' = Çık")

        while True:
            if is_picam:
                frame = camera.capture_array()
                frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            else:
                ret, frame_bgr = camera.read()
                if not ret:
                    raise RuntimeError("USB kamera kare üretemedi")

            h_low = cv2.getTrackbarPos("H Min", "HSV Ayarları")
            s_low = cv2.getTrackbarPos("S Min", "HSV Ayarları")
            v_low = cv2.getTrackbarPos("V Min", "HSV Ayarları")
            h_high = cv2.getTrackbarPos("H Max", "HSV Ayarları")
            s_high = cv2.getTrackbarPos("S Max", "HSV Ayarları")
            v_high = cv2.getTrackbarPos("V Max", "HSV Ayarları")

            hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
            v_mean = np.mean(hsv[:, :, 2])
            mask = cv2.inRange(
                hsv,
                np.array([h_low, s_low, v_low]),
                np.array([h_high, s_high, v_high]),
            )
            result = cv2.bitwise_and(frame_bgr, frame_bgr, mask=mask)

            info = f"V_mean: {v_mean:.0f} | "
            if v_mean < 100:
                info += "KARANLIK"
            elif v_mean > 200:
                info += "PARLAK"
            else:
                info += "NORMAL"
            cv2.putText(
                frame_bgr, info, (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                0.7, (0, 255, 255), 2,
            )
            cv2.putText(
                mask, "BEYAZ SERIT BURADA OLMALI", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, 200, 2,
            )

            cv2.imshow("Orjinal Görüntü", frame_bgr)
            cv2.imshow("Maske (Beyaz=ŞERİT)", mask)
            cv2.imshow("Sonuç", result)

            key = cv2.waitKey(30) & 0xFF
            if key == ord('q'):
                break
            if key != ord('s'):
                continue

            if v_mean < 100:
                profile = "DARK"
            elif v_mean > 200:
                profile = "BRIGHT"
            else:
                profile = "NORMAL"

            print()
            print("=" * 62)
            print("✅ HSV DEĞERLERİ KAYDEDİLİYOR...")
            print("=" * 62)
            print(f"   # {profile} ortam (V_mean={v_mean:.0f})")
            print(f"   WHITE_HSV_LOW_{profile}  = ({h_low}, {s_low}, {v_low})")
            print(f"   WHITE_HSV_HIGH_{profile} = ({h_high}, {s_high}, {v_high})")
            print()

            try:
                _write_config_assignment(
                    SCRIPT_DIR / "config.py",
                    {
                        f"WHITE_HSV_LOW_{profile}":  (h_low, s_low, v_low),
                        f"WHITE_HSV_HIGH_{profile}": (h_high, s_high, v_high),
                    },
                )
                print("✅ config.py OTOMATİK GÜNCELLENDİ! (atomik yazma doğrulandı)")
            except Exception as exc:
                print(f"⚠️  Otomatik güncelleme başarısız: {exc}")
                print("   ORİJİNAL config.py DEĞİŞTİRİLMEDİ (güvenli).")
                print("   Yukarıdaki değerleri manuel olarak yaz.")
            break
    finally:
        try:
            if is_picam:
                try:
                    camera.stop()
                finally:
                    close = getattr(camera, "close", None)
                    if close is not None:
                        close()
            else:
                camera.release()
        finally:
            cv2.destroyAllWindows()
    
    basinca_devam()


# =============================================================================
# 3. KAMERA TESTİ (Canlı Görüntü)
# =============================================================================
def kamera_testi():
    """Kameranın gördüklerini canlı izle."""
    clear_screen()
    print_baslik("3️⃣  KAMERA CANLI GÖRÜNTÜ")
    
    print("📋 BU TEST NE YAPAR?")
    print("─" * 62)
    print("• Kameranın gördüklerini canlı izlersin")
    print("• Şerit takibi nasıl çalışıyor görürsün")
    print("• 'q' tuşu ile çıkarsın")
    print()
    
    basinca_devam()
    
    try:
        araci_calistir("camera.py")
    except Exception as e:
        print(f"❌ Hata: {e}")
        basinca_devam()


# =============================================================================
# 4. PERSPEKTİF KALİBRASYON (Kuş Bakışı)
# =============================================================================
def perspektif_kalibrasyon():
    """Kuş bakışı perspektifin 4 köşesini ayarla."""
    clear_screen()
    print_baslik("4️⃣  PERSPEKTİF KALİBRASYON (KUŞ BAKIŞI)")
    
    print("📋 BU TEST NE YAPAR?")
    print("─" * 62)
    print("• Kameranın gördüklerinden 4 köşeli alan seçersin")
    print("• Bu alan 'kuş bakışı'na dönüştürülür")
    print("• Şerit takibi bu görüntüde yapılır")
    print()
    # LEGACY-033: Bu talimatlar eskiden calibrate.py'nin desteklemediği
    # 's' (kaydet) ve 'r' (sıfırla) tuşlarını vaat ediyordu. Gerçek dispatch
    # tablosu (calibrate.py) yalnızca şunları destekler: mevcut 4 noktayı
    # SÜRÜKLEME, ENTER (doğrulayıp EKRANA yazdırır — DİSKE OTOMATİK YAZMAZ),
    # ve 'q' (çık). Talimatları gerçek davranışla eşleştiriyoruz.
    print("🎮 KONTROLLER:")
    print("─" * 62)
    print("• Var olan 4 köşe noktasını FARE İLE SÜRÜKLEYİN")
    print("  (sıra: sol-üst, sağ-üst, sol-alt, sağ-alt)")
    print("• ENTER = geometriyi doğrula ve PERSP_SRC değerini EKRANA YAZDIR")
    print("  (bu adım config.py'yi OTOMATİK GÜNCELLEMEZ — yazdırılan")
    print("   değeri elle config.py'ye kopyalamanız gerekir)")
    print("• 'q' tuşu = kaydetmeden çık")
    print()
    
    basinca_devam()
    
    try:
        araci_calistir("calibrate.py")
    except Exception as e:
        print(f"❌ Hata: {e}")
        basinca_devam()


# =============================================================================
# 5. PD PARAMETRE TUNING
# =============================================================================
def pd_tuning():
    """PD parametrelerini interaktif ayarla."""
    clear_screen()
    print_baslik("5️⃣  PD PARAMETRE TUNING (KP/KD)")
    
    print("📋 BU TEST NE YAPAR?")
    print("─" * 62)
    print("• KP (oransal) ve KD (türevsel) kazançlarını ayarla")
    print("• Slider'larla canlı değiştir, etkisini gör")
    print()
    print("📊 PARAMETRELER:")
    print("─" * 62)
    print("• KP yüksek → hızlı tepki ama salınım riski")
    print("• KD yüksek → salınım azalır ama yavaş tepki")
    print()
    print("🎯 DOĞRU AYAR:")
    print("─" * 62)
    print("• Düz gidiş: ±5 piksel salınım")
    print("• Virajlar: hızlı dönüş, salınım yok")
    print()
    
    basinca_devam()
    
    try:
        araci_calistir("pd_tune.py")
    except Exception as e:
        print(f"❌ Hata: {e}")
        basinca_devam()


# =============================================================================
# 6. MOTOR İNTERAKTİF (W/A/S/D)
# =============================================================================
def motor_interaktif():
    """W/A/S/D ile motor kontrol et."""
    clear_screen()
    print_baslik("6️⃣  MOTOR İNTERAKTİF KONTROL (W/A/S/D)")
    
    print("📋 BU TEST NE YAPAR?")
    print("─" * 62)
    print("• Klavye ile motoru kontrol edersin")
    print("• Motor yönü doğru mu test edersin")
    print()
    print("🎮 KONTROLLER:")
    print("─" * 62)
    print("• W = İLERİ")
    print("• S = GERİ")
    print("• A = SOL DÖN")
    print("• D = SAĞ DÖN")
    print("• BOŞLUK = DUR")
    print("• Q = ÇIK")
    print()
    
    basinca_devam()
    
    try:
        araci_calistir("camtester.py")
    except Exception as e:
        print(f"❌ Hata: {e}")
        basinca_devam()


# =============================================================================
# 7. YOL TAKİP (Sadece Şerit)
# =============================================================================
def yol_takip_test():
    """Sadece şerit takibi (olay tespiti yok)."""
    clear_screen()
    print_baslik("7️⃣  YOL TAKİP TEST (SADECE ŞERİT)")
    
    print("📋 BU NE YAPAR?")
    print("─" * 62)
    print("• SADECE şerit takibi yapar")
    print("• Trafik ışığı, yaya geçidi, sollama YOK")
    print("• Pist üzerinde sadece düz/virajlı yolu takip eder")
    print()
    print("🎯 KULLANIM:")
    print("─" * 62)
    print("• Aracı pistin başına koy")
    print("• Konsola GG veya EZ yaz → Araç başlar")
    print("• Şeridi takip eder, dur durmadan gider")
    print("• Ctrl+C ile durdur")
    print()
    print("💡 İPUCU:")
    print("─" * 62)
    print("• Bu mod tamamen şerit takibi testidir")
    print("• Kalibrasyon (HSV, PD) bunda denenmesi rahattır")
    print()
    
    secim = input("Başlatılsın mı? [E/H]: ").strip().lower()
    if secim != 'e':
        return
    
    try:
        araci_calistir("yol_takip.py")
    except Exception as e:
        print(f"❌ Hata: {e}")
    
    basinca_devam()


# =============================================================================
# 8. ANA PROGRAM ÇALIŞTIR
# =============================================================================
def ana_program():
    """Ana sistemi çalıştır."""
    clear_screen()
    print_baslik("8️⃣  ANA PROGRAM ÇALIŞTIR (main.py)")
    
    print("📋 BU NE YAPAR?")
    print("─" * 62)
    print("• Otonom araç sistemi başlatılır")
    print("• Kırmızı ışık beklenir (veya GG/EZ yaz)")
    print()
    print("⚠️  ÖNEMLİ:")
    print("─" * 62)
    print("• Önce diğer kalibrasyonları YAP")
    print("• Aracı pistе koy")
    print("• Konsola GG yazınca araç başlar")
    print()
    
    secim = input("Başlatılsın mı? [E/H]: ").strip().lower()
    if secim != 'e':
        return
    
    try:
        araci_calistir("main.py")
    except Exception as e:
        print(f"❌ Hata: {e}")
    
    basinca_devam()


# =============================================================================
# ANA MENÜ
# =============================================================================
def ana_menu():
    """Ana menüyü göster ve seçim al."""
    while True:
        clear_screen()
        print()
        print("╔" + "═" * 60 + "╗")
        print("║" + " " * 60 + "║")
        print("║" + "    🚗 OTONOM ARAÇ KALİBRASYON MERKEZİ 🚗".center(70) + "║")
        print("║" + " " * 60 + "║")
        print("║" + "         MEB 2026 Robot Yarışması".center(60) + "║")
        print("║" + " " * 60 + "║")
        print("╚" + "═" * 60 + "╝")
        print()
        print("📋 KALİBRASYON ARAÇLARI:")
        print("─" * 62)
        print()
        print("  1️⃣   Motor Dengeleme        (Düz gidiyor mu?)")
        print("  2️⃣   HSV Kalibrasyon ⭐     (Beyaz şerit bulma)")
        print("  3️⃣   Kamera Canlı İzle      (Görüntü kontrolü)")
        print("  4️⃣   Perspektif Kalibrasyon (Kuş bakışı)")
        print("  5️⃣   PD Parametre Tuning    (Direksiyon tepkisi)")
        print("  6️⃣   Motor İnteraktif       (W/A/S/D kontrol)")
        print()
        print("─" * 62)
        print()
        print("  7️⃣   YOL TAKİP TEST       🚗 (Sadece şerit takibi)")
        print("  8️⃣   ANA PROGRAM ÇALIŞTIR  (main.py - tüm görevler)")
        print()
        print("  0    ÇIK")
        print()
        print("─" * 62)
        print("⭐ = Şu anki sorununa en yakın çözüm")
        print()
        
        try:
            secim = input("Seçim [0-8]: ").strip()
        except KeyboardInterrupt:
            print("\n\nÇıkılıyor...")
            break
        
        if secim == '0':
            print("\n✅ Görüşmek üzere!")
            break
        elif secim == '1':
            motor_dengeleme()
        elif secim == '2':
            hsv_kalibrasyon()
        elif secim == '3':
            kamera_testi()
        elif secim == '4':
            perspektif_kalibrasyon()
        elif secim == '5':
            pd_tuning()
        elif secim == '6':
            motor_interaktif()
        elif secim == '7':
            yol_takip_test()
        elif secim == '8':
            ana_program()
        else:
            print(f"\n❌ Geçersiz seçim: {secim}")
            bekle(1.5)


if __name__ == "__main__":
    # LEGACY-034: bu ust duzey giris noktasi da artik ACIK bir cikis
    # koduyla sonlanir — tutarlilik icin (bu betik kendisi bir baska
    # betik tarafindan check=True ile calistirilirsa dogru davranir).
    _exit_code = 0
    try:
        ana_menu()
    except KeyboardInterrupt:
        print("\n\nÇıkılıyor...")
        _exit_code = 130
    except Exception as e:
        print(f"\n❌ Hata: {e}")
        import traceback
        traceback.print_exc()
        _exit_code = 1
    raise SystemExit(_exit_code)
