#!/usr/bin/env python3
# =============================================================================
# pd_tune.py  —  KP / KD interaktif PD kazanç ayarlama aracı
#
# Evde (herhangi bir zemine beyaz bant yapıştırarak) çalıştırılabilir.
# Araç giderken hata logunu canlı ekrana basar; salınım / gecikme görürsün.
#
# Kullanım:
#   python pd_tune.py
#
# Adımlar:
#   1) Başlangıç KP/KD değerlerini gir (config.py'den oku)
#   2) Araç gider, hata grafiği terminale çizilir
#   3) q = dur, değerleri ayarla, tekrar dene
#   4) İyi görünen değerleri config.py'ye yaz
# =============================================================================
import sys
import time
import threading
import collections
import math

try:
    from lane import LaneDetector
    from controller import PDController
    from motor import MotorDriver, MotorHardwareUnavailable
except ImportError:
    print("lane.py / controller.py / motor.py bulunamadı. Aynı klasörde çalıştır.")
    sys.exit(1)

try:
    from picamera2 import Picamera2
    _USE_PI = True
except ImportError:
    _USE_PI = False

import cv2
from config import WIDTH, HEIGHT


# ---------------------------------------------------------------------------
# Kamera
# ---------------------------------------------------------------------------
class _Cam:
    def __init__(self):
        self._c = None
        self._cap = None
        if _USE_PI:
            self._c = Picamera2()
            try:
                self._c.configure(self._c.create_preview_configuration(
                    main={"size": (WIDTH, HEIGHT), "format": "RGB888"}
                ))
                self._c.start()
                time.sleep(1)
            except BaseException:
                try:
                    self._c.close()
                except Exception:
                    pass
                raise
        else:
            self._cap = cv2.VideoCapture(0)
            if not self._cap.isOpened():
                self._cap.release()
                raise RuntimeError("USB kamera açılamadı")
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH,  WIDTH)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)

    def capture(self):
        if _USE_PI:
            return self._c.capture_array()
        ret, f = self._cap.read()
        if not ret:
            raise RuntimeError("USB kamera kare üretemedi")
        return cv2.cvtColor(cv2.resize(f, (WIDTH, HEIGHT)), cv2.COLOR_BGR2RGB)

    def stop(self):
        if _USE_PI:
            try:
                self._c.stop()
            finally:
                close = getattr(self._c, "close", None)
                if close is not None:
                    close()
        else:
            self._cap.release()


# ---------------------------------------------------------------------------
# ASCII hata grafiği (terminal genişliği kadar)
# ---------------------------------------------------------------------------
GRAPH_WIDTH  = 60
GRAPH_HEIGHT = 15
ERROR_SCALE  = 200   # ±200 px = tam grafik yüksekliği

def draw_graph(errors: collections.deque) -> str:
    rows = []
    mid  = GRAPH_HEIGHT // 2
    for row in range(GRAPH_HEIGHT):
        line = []
        for i, e in enumerate(list(errors)[-GRAPH_WIDTH:]):
            # e: -ERROR_SCALE..+ERROR_SCALE → 0..GRAPH_HEIGHT
            # LEGACY-073: Satir indeksi YUKARIDAN AŞAĞIYA artar (row=0 en
            # ust), ama alt bilgi etiketi "+ERROR_SCALE YUKARI" diyordu.
            # Eski isaret pozitif hatayi ALT satira ciziyordu — etiketle
            # ZIT. Isareti ters cevir: pozitif hata artik DAHA KUCUK satir
            # indeksine (goruntude daha YUKARI) haritalanir.
            mapped = mid - int((e / ERROR_SCALE) * mid)
            mapped = max(0, min(GRAPH_HEIGHT - 1, mapped))
            if row == mid:
                ch = '─' if mapped != mid else '┼'
            elif row == mapped:
                ch = '█'
            else:
                ch = ' '
            line.append(ch)
        rows.append('│' + ''.join(line) + '│')
    rows.insert(0,  f"┌{'─'*GRAPH_WIDTH}┐  hata (px)")
    rows.append(   f"└{'─'*GRAPH_WIDTH}┘  +{ERROR_SCALE}↑  0─── -{ERROR_SCALE}↓")
    return '\n'.join(rows)


# ---------------------------------------------------------------------------
# Ana döngü
# ---------------------------------------------------------------------------
def run_tuning(kp: float, kd: float, duration: float = 10.0):
    if not all(math.isfinite(v) for v in (kp, kd, duration)) or duration <= 0:
        raise ValueError("KP, KD ve süre sonlu olmalı; süre sıfırdan büyük olmalı")

    mot  = MotorDriver()
    mot.require_hardware()
    errors  = collections.deque(maxlen=GRAPH_WIDTH * 2)
    # LEGACY-074: 'errors' yalnizca SON 120 GECERLI kareyi tutan bir
    # GORUNTULEME kuyrugudur. Eski ozet SADECE bunu kullaniyordu — kayip
    # kareler tamamen ATILIYOR, erken salinim (kuyruk dolup taskinca)
    # SESSIZCE UNUTULUYORDU. Tam kosu istatistikleri AYRI izlenir.
    _total_valid = 0
    _total_lost  = 0
    _full_sum    = 0.0
    _full_sumsq  = 0.0
    running = True
    cam = None
    thread = None
    nonblock = False
    fd = None
    old = None

    try:
        cam = _Cam()
        det = LaneDetector()
        ctrl = PDController()

        # LEGACY-075: Eski kod PAYLASILAN modul degiskenlerini
        # (controller.KP/KD) DEGISTIRIYORDU ve hicbir zaman GERI YUKLEMIYORDU.
        # Ayni interpreter'daki HER PDController ornegi (gecmis, simdiki,
        # gelecek) test kazanclarini goruyordu; config.KP/config.KD ise
        # eski degerleri raporlamaya devam ediyordu (tutarsizlik). Kazanclar
        # artik yalnizca BU ORNEGE atanir — paylasilan durum degismez.
        ctrl.KP = kp
        ctrl.KD = kd

        start = time.time()
        print(f"\nKP={kp}  KD={kd}  |  {duration}s test  |  q=dur")
        print("─" * 50)

        try:
            import tty, termios
            fd = sys.stdin.fileno()
            if not sys.stdin.isatty():
                raise OSError("stdin bir TTY değil — ham mod anlamsız")
            old = termios.tcgetattr(fd)
            tty.setraw(fd)
            nonblock = True
        except Exception as exc:
            nonblock = False
            # LEGACY-076: Eski kod bu istisnayi YUTUYOR, dinleyiciyi
            # SESSIZCE devre disi birakiyor, ama arac yine de hareket
            # dongusune giriyordu — ekranda hala 'q=dur' YAZARKEN. Ilan
            # edilen dur girdisi yoksa KAPALI-GUVENLI ol: motor testine
            # HIC girme.
            print(f"\n[pd_tune] HATA: klavye ham modu kurulamadi ({exc}).")
            print("[pd_tune] 'q=dur' girdisi bu haliyle ÇALIŞMAYACAKTI — "
                  "GÜVENLİK için test BAŞLATILMIYOR.")
            print("[pd_tune] Gerçek bir terminalden çalıştırın, ya da "
                  "--noninteractive gibi ayrı bir mod ekleyin.")
            return

        def key_listener():
            nonlocal running
            if not nonblock:
                return
            import select
            while running:
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    ch = sys.stdin.read(1)
                    if ch in ('q', 'Q'):
                        running = False

        thread = threading.Thread(target=key_listener, daemon=True)
        thread.start()

        while running and (time.time() - start) < duration:
            frame = cam.capture()
            error, _ = det.process(frame)
            if error is not None:
                errors.append(float(error))
                _total_valid += 1
                _full_sum    += float(error)
                _full_sumsq  += float(error) ** 2
            else:
                _total_lost += 1

            l, r = ctrl.compute(error)
            mot.set_speed(l, r)

            # Terminali temizle ve grafik çiz
            print("\033[H\033[J", end="")
            error_text = f"{error:+.0f}px" if error is not None else "SERIT YOK"
            print(f"KP={kp:.3f}  KD={kd:.3f}  |  "
                  f"hata={error_text}  |  "
                  f"süre={time.time()-start:.1f}s  |  q=dur")
            print(draw_graph(errors))

            stats_arr = list(errors)
            if stats_arr:
                print(f"\nOrtalama: {sum(stats_arr)/len(stats_arr):+.1f}px  |  "
                      f"Maks: {max(abs(e) for e in stats_arr):.0f}px  |  "
                      f"Std: {(sum((e - sum(stats_arr)/len(stats_arr))**2 for e in stats_arr)/len(stats_arr))**0.5:.1f}px")

    finally:
        running = False
        # LEGACY-077: Eski sira ONCE thread.join(timeout=0.5) SONRA fren
        # idi — dinleyici thread'i yavas/bloke olursa motor, gereksiz
        # yere 0.5 saniyeye kadar KOMUTLU kalmaya devam ediyordu. Fren
        # ARTIK HERSEYDEN ONCE gelir; is parcaciklarina katilmak ve
        # kaynaklari geri yuklemek ondan SONRA olur.
        try:
            try:
                mot.brake()
                time.sleep(0.3)
            finally:
                mot.stop()
        finally:
            try:
                if thread is not None:
                    thread.join(timeout=0.5)
            finally:
                try:
                    if cam is not None:
                        cam.stop()
                finally:
                    if nonblock and fd is not None and old is not None:
                        try:
                            termios.tcsetattr(fd, termios.TCSADRAIN, old)
                        except Exception as exc:
                            print(f"\nTerminal geri yüklenemedi: {exc}")

    # Özet
    if errors:
        ea = list(errors)
        mean = sum(ea) / len(ea)
        std  = (sum((e-mean)**2 for e in ea) / len(ea)) ** 0.5

        # LEGACY-074: TAM KOŞU istatistikleri (SON kuyruk değil).
        _total_frames = _total_valid + _total_lost
        _coverage = (_total_valid / _total_frames) if _total_frames else 0.0
        _full_mean = (_full_sum / _total_valid) if _total_valid else 0.0
        _full_std = (((_full_sumsq / _total_valid) - _full_mean ** 2) ** 0.5
                    if _total_valid else 0.0)

        print(f"\n{'='*50}")
        print(f"SONUÇ  KP={kp}  KD={kd}")
        print(f"  Kapsam        : {_total_valid}/{_total_frames} kare geçerli "
              f"({_coverage*100:.0f}%), {_total_lost} kayıp")
        print(f"  Son {len(ea)} kare — Ortalama: {mean:+.1f}px  Std: {std:.1f}px")
        print(f"  TÜM koşu     — Ortalama: {_full_mean:+.1f}px  Std: {_full_std:.1f}px")
        print("  Tavsiye:")

        # LEGACY-074: Kapsam yetersizse (kayıp kare oranı yüksek) niteliksiz
        # bir 'stabil' hükmü verme — kayıp süresince denetleyici GÜVENLİ
        # DURMUŞ olabilir, bu da düşük std'yi YANILTICI şekilde iyi gösterir.
        if _coverage < 0.70:
            print(f"  ⚠️  DÜŞÜK KAPSAM (%{_coverage*100:.0f} geçerli) — "
                  "'stabil/salınımlı' hükmü GÜVENİLMEZ. Kayıp kareler "
                  "muhtemelen serit kaybı/güvenli duruş nedeniyle; "
                  "önce algılama güvenilirliğini düzeltin.")
        elif _full_std > 30 or std > 30:
            print("  ⚠️  Yüksek salınım → KP'yi azalt veya KD'yi artır")
        elif _full_std > 15 or std > 15:
            print("  ⚠️  Orta salınım → KD'yi biraz artır")
        else:
            print("  ✅  Stabil görünüyor! (tam koşu ve son pencere ikisi de)")
        if abs(mean) > 20 or abs(_full_mean) > 20:
            print(f"  ⚠️  Kalıcı sapma (son:{mean:+.0f}px tam-koşu:{_full_mean:+.0f}px) "
                  "→ LEFT_TRIM/RIGHT_TRIM kontrol et")
    else:
        print("\nSONUÇ: Geçerli şerit hatası ölçülemedi.")
        if _total_lost:
            print(f"  ({_total_lost} kare işlendi, hepsi şerit kaybı)")


# ---------------------------------------------------------------------------
# Giriş noktası
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import config as cfg
    print("PD Kazanç Ayarlama Aracı")
    print(f"Mevcut değerler: KP={cfg.KP}  KD={cfg.KD}\n")

    # LEGACY-034: cikis kodu artik gercek sonucu yansitiyor —
    # kalibrasyon.py'nin `subprocess.run(check=True)` cagirani basarisiz
    # bir donenimi/girdiyi basari SANMASIN.
    _exit_code = 0
    try:
        kp_in = input(f"Yeni KP [{cfg.KP}]: ").strip()
        kd_in = input(f"Yeni KD [{cfg.KD}]: ").strip()
        dur_in = input("Test süresi (saniye) [10]: ").strip()

        kp  = float(kp_in)  if kp_in  else cfg.KP
        kd  = float(kd_in)  if kd_in  else cfg.KD
        dur = float(dur_in) if dur_in else 10.0

        run_tuning(kp, kd, dur)

        print("\n📋 config.py'ye yaz:")
        print(f"   KP = {kp}")
        print(f"   KD = {kd}")

    except KeyboardInterrupt:
        print("\nKesintiye uğradı.")
        _exit_code = 130
    except MotorHardwareUnavailable as exc:
        print(f"\nBaşlatılamadı: {exc}")
        _exit_code = 1
    except ValueError:
        print("Geçersiz sayı girişi.")
        _exit_code = 1

    raise SystemExit(_exit_code)
