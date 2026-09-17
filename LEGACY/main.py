# =============================================================================
# main.py  —  Otonom şerit takip ana giriş noktası (BASİT VERSİYON)
#
# Özellikler:
#   - Web sitesi YOK (sadece CMD/terminal)
#   - GG veya EZ yazınca araç elle başlatılır
#   - SPACE (boşluk) tuşu = HEMEN başlat (anında, tek tuş)
#   - Q tuşu = programdan çık
#   - GPIO 16 buton kaldırıldı
#
# Kullanım: python main.py
# =============================================================================
import os
import signal
import sys
import threading
import time

try:
    import termios
    import tty
except ImportError:
    termios = None
    tty = None

try:
    import msvcrt
except ImportError:
    msvcrt = None

import cv2
import numpy as np

# Kamera: Pi'de picamera2, geliştirme/test için OpenCV VideoCapture
try:
    from picamera2 import Picamera2
    _USE_PICAMERA = True
except ImportError:
    _USE_PICAMERA = False
    print("[main] picamera2 bulunamadı — USB/Windows kamera yolu kullanılıyor")

# GPIO buton: Pi'de gpiozero.Button; yoksa fiziksel buton kullanılamaz.
# Bu try/except sayesinde Pi olmadan da kod çalışır; buton beklenmez.
try:
    from gpiozero import Button as _GpioButton
    _HAS_BUTTON = True
except ImportError:
    _GpioButton = None  # type: ignore[assignment]
    _HAS_BUTTON = False

from config import (
    WIDTH, HEIGHT,
    CROSSWALK_WAIT_SEC, HEMZEMIN_WAIT_SEC,
    SPEED_BUMP_SLOW_SEC, SPEED_BUMP_SPEED,
    APPROACH_SPEED, APPROACH_TIMEOUT_SEC, APPROACH_RECOVERY_SEC,
    CAMERA_STARTUP_TIMEOUT_SEC, EVENT_REARM_HYSTERESIS_FRAMES,
    PARKING_CONFIRM_FRAMES,
    SPEED_BUMP_MAX_EXTEND_MULT, PARKING_TARGET_LOST_SEC,
    OVERTAKING_STEER_BIAS, OVERTAKING_CROSS_SEC,
    OVERTAKING_PASS_SEC, OVERTAKING_RETURN_SEC, OVERTAKING_SPEED,

    PARKING_HSV_LOW1, PARKING_HSV_HIGH1,
    PARKING_HSV_LOW2, PARKING_HSV_HIGH2,
    PARKING_MIN_AREA, PARKING_ROI_TOP,
    PARKING_SPEED, PARKING_CENTER_TOL,
    CAMERA_BGR_OUTPUT, CAMERA_ROTATE_180, SHOW_PREVIEW,
    LANE_LOST_TURN_SEC,
    START_BUTTON_PIN,
)
from controller import PDController
from events import EventDetector
from lane import LaneDetector
from logger import ErrorLogger
from motor import MotorDriver, MotorHardwareUnavailable


# ---------------------------------------------------------------------------
# Kamera sarmalayıcı
# ---------------------------------------------------------------------------
class _Camera:
    # LEGACY-044: Kabul edilebilir kare yaşı. capture_array() hata
    # vermeden bloke olursa _latest sonsuza dek eskir; bu sınır olmadan
    # araç çok eski bir sahneye göre sürülmeye devam eder.
    MAX_FRAME_AGE_SEC = 0.5

    def __init__(self):
        self._latest:  np.ndarray | None = None
        self._latest_ts: float | None = None   # monotonik yakalama zamanı
        self._seq: int = 0                     # kare sıra numarası
        self._error: Exception | None = None
        self._lock    = threading.Lock()
        self._running = True
        self._stopped = False
        self._pi = None
        self._cv = None
        self._size_warned = False   # LEGACY-043: uyariyi bir kez yazdir
        self._ready = threading.Event()   # LEGACY-042: ilk gercek kare

        if _USE_PICAMERA:
            self._pi = Picamera2()
            try:
                cfg = self._pi.create_preview_configuration(
                    main={"format": "RGB888", "size": (WIDTH, HEIGHT)},
                    buffer_count=4,          # starvation önleme
                )
                self._pi.configure(cfg)
                self._pi.start()
                # LEGACY-042: Eski kod SABIT 2 saniye uyuyor, SONRA
                # yayimlama thread'ini baslatiyordu. __init__ dondugunde
                # _loop() HENUZ TEK KARE BILE yayimlamamis olabiliyordu;
                # capture() hemen "kare yok" hatasi veriyor ve drive_loop
                # bunu SINIRSIZ, gecikmesiz yeniden deneyip 30 hatada
                # iptal ediyordu — saglikli ama yavas baslayan bir kamera
                # bile baslangici engelleyebiliyordu. Simdi: thread HEMEN
                # baslar, __init__ ilk GERCEK karenin yayimlanmasini
                # (monotonik bir sure siniriyla) BEKLER.
                threading.Thread(target=self._loop, daemon=True).start()
                if not self._ready.wait(timeout=CAMERA_STARTUP_TIMEOUT_SEC):
                    raise RuntimeError(
                        f"Pi kamerası {CAMERA_STARTUP_TIMEOUT_SEC}s içinde "
                        "ilk kareyi üretmedi"
                    )
            except BaseException:
                try:
                    self._pi.close()
                except Exception:
                    pass
                raise
        else:
            self._cv = cv2.VideoCapture(0)
            if not self._cv.isOpened():
                self._cv.release()
                raise RuntimeError("USB camera could not be opened")
            self._cv.set(cv2.CAP_PROP_FRAME_WIDTH,  WIDTH)
            self._cv.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)

    def _loop(self) -> None:
        """Kameradan sürekli kare çeken arka plan thread'i.

        Ana döngü ne kadar yavaş işlerse işlesin kamera pipeline'ı
        boşta kalmaz; buffer I/O hatası önlenir.
        """
        while self._running:
            try:
                frame = self._pi.capture_array()
                # Pi 5 / yeni libcamera: RGB888 bazen XRGB8888 (4 kanal) gelir
                if frame.ndim == 3 and frame.shape[2] == 4:
                    frame = frame[:, :, :3]
                frame = frame.copy()     # DMA buffer sahipliğini al
                if CAMERA_BGR_OUTPUT:
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                if CAMERA_ROTATE_180:
                    frame = cv2.rotate(frame, cv2.ROTATE_180)
                with self._lock:
                    # LEGACY-044: Görüntü, monotonik yakalama zamanı ve
                    # sıra numarası TEK atomik işlemde yayımlanır.
                    self._latest = frame
                    self._latest_ts = time.monotonic()
                    self._seq += 1
                self._ready.set()   # LEGACY-042: ilk gercek kare yayimlandi
            except Exception as exc:
                with self._lock:
                    self._error = exc
                self._running = False

    def capture(self) -> np.ndarray:
        if _USE_PICAMERA:
            with self._lock:
                if self._error is not None:
                    raise RuntimeError("Pi camera capture failed") from self._error
                if self._latest is None:
                    raise RuntimeError("Pi camera has not produced a frame")
                # LEGACY-044: Üretici thread capture_array() içinde hata
                # VERMEDEN takılabilir; bu durumda _error boş kalır ve
                # kamera failsafe'i hiç tetiklenmez. Tek güvenilir kanıt
                # karenin YAŞIdır — bayatsa sür komutu üretme.
                age = time.monotonic() - self._latest_ts
                if age > self.MAX_FRAME_AGE_SEC:
                    raise RuntimeError(
                        f"Pi camera frame stale ({age:.2f}s, seq={self._seq}); "
                        "kare üreticisi takılmış olabilir"
                    )
                return self._latest
        else:
            ret, frame = self._cv.read()
            if not ret:
                raise RuntimeError("USB camera capture failed")
            # LEGACY-043: Bazi USB arka uclari ISTENEN boyutu HONOR ETMEZ
            # (orn. 800x680 istenip 640x480 dondurulur). Bu, asagi akis
            # perspektif noktalarini, piksel-alan esiklerini, ROI'lari ve
            # sabit genislik oranlarini (tumsek genislik kontrolu gibi)
            # KALIBRE EDILMEMIS bir kare karsisinda calistirir — hata
            # vermez, sessizce YANLIS sonuc uretir. camera.py'deki
            # gorsellestirici zaten yeniden boyutluyordu; calisan yol
            # boyutlanmiyordu, bu da dagitim uyusmazligini gizliyordu.
            actual_h, actual_w = frame.shape[:2]
            if (actual_w, actual_h) != (WIDTH, HEIGHT):
                frame = cv2.resize(frame, (WIDTH, HEIGHT),
                                   interpolation=cv2.INTER_LINEAR)
                if not self._size_warned:
                    print(f"[main] UYARI: USB kamera {actual_w}x{actual_h} "
                          f"döndürdü, istenen {WIDTH}x{HEIGHT} değil. "
                          "Kareler yeniden ölçekleniyor.")
                    self._size_warned = True
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            if CAMERA_ROTATE_180:
                frame = cv2.rotate(frame, cv2.ROTATE_180)
            return frame

    def stop(self):
        if self._stopped:
            return
        self._stopped = True
        self._running = False
        if _USE_PICAMERA:
            try:
                time.sleep(0.1)
                self._pi.stop()
            finally:
                close = getattr(self._pi, "close", None)
                if close is not None:
                    close()
        else:
            self._cv.release()


# ---------------------------------------------------------------------------
# Bileşenler
# ---------------------------------------------------------------------------
tur_kayit = None    # TurKaydedici — tur kaydi (kontrol yolu disinda)
camera = None
lane_detector = None
controller = None
motor = None
logger = None
event_detector = None


# ---------------------------------------------------------------------------
# Global durum değişkenleri
# ---------------------------------------------------------------------------
_running         = True
_state           = 'BEKLIYOR'
_state_timer     = 0.0
_ovt_phase       = 0
_manual_green    = False   # GG/EZ/SPACE/buton ile elle yeşil başlangıç onayı
_lane_lost_time: float | None = None   # şerit kayıp failsafe zamanlayıcısı
_crosswalk_consumed = False
_hemzemin_consumed = False
_speed_bump_consumed = False
_orange_car_consumed = False
# LEGACY-056: rearm histerezisi icin ardisik-yanlis-kare sayaclari
_crosswalk_false_count = 0
_hemzemin_false_count = 0
_speed_bump_false_count = 0
_orange_car_false_count = 0

# Yarış zaman tracking (Görev/PDF 4.4: 240 sn üst sınır + bitirme katsayısı)
_race_start_time: float | None = None
_finish_printed       = False
_time_warning_printed = False
_button_handle = None      # gpiozero.Button referansı (shutdown'da close)
_shutdown_complete = False
_kb_thread = None

# Tabela tabanlı sollama yasağı
_NO_OVERTAKE_SEC = 8.0          # sollamabam tabelası sonrası yasak süresi
_no_overtake_until: float = 0.0 # bu zamana kadar sollama yapma

# --- LEGACY-046: bağımsız motor komut watchdog'u ---------------------------
# Sürüş döngüsü herhangi bir yerde bloke olursa (USB kamera okuma, OpenCV
# işleme, pencere çizimi, konsol çıktısı, CSV dışa aktarma) son motor
# komutu süresiz aktif kalır. 'q' yalnızca bayrak koyar; bloke bir çağrıyı
# kesemez. Bu watchdog sürüş döngüsünden BAĞIMSIZ çalışır ve döngü
# ilerlemeyi bıraktığında motorları frenler.
_loop_heartbeat: float = 0.0        # drive_loop her turda günceller
_WATCHDOG_TIMEOUT_SEC = 1.0        # bu süre boyunca ilerleme yoksa frenle
_watchdog_thread = None
_watchdog_tripped = False


def _motor_watchdog() -> None:
    """Sürüş döngüsünden bağımsız komut süre sınırı uygulayıcısı."""
    global _watchdog_tripped
    while _running:
        try:
            hb = _loop_heartbeat
            if hb and (time.monotonic() - hb) > _WATCHDOG_TIMEOUT_SEC:
                if not _watchdog_tripped:
                    _watchdog_tripped = True
                    try:
                        print(f"\n[watchdog] Sürüş döngüsü "
                              f"{_WATCHDOG_TIMEOUT_SEC}s ilerlemedi — FREN.")
                    except Exception:
                        pass
                if motor is not None:
                    try:
                        motor.brake()
                    except Exception:
                        pass
            elif hb:
                _watchdog_tripped = False
        except Exception:
            pass
        time.sleep(0.1)


# ---------------------------------------------------------------------------
# Klavye dinleme thread'i (raw mode — tek tuş)
# ---------------------------------------------------------------------------
def keyboard_listener():
    """Ayrı thread'de klavye dinler. GG, EZ veya SPACE = başlat."""
    global _manual_green, _running

    fd = None
    old_settings = None
    try:
        if termios is not None and tty is not None:
            import select
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            tty.setcbreak(fd)

            def read_key():
                # LEGACY-047: sys.stdin.read(1) TextIOWrapper icine fazladan
                # karakter ONBELLEKLEYEBILIR (prefetch). select() alttaki
                # descriptor'i kontrol eder; Python'un kendi tamponundaki
                # bekleyen bir tusu GOREMEZ. Sonuc: yapistirilmis 'GG' ya da
                # arka arkaya gelen bir DUR tusu, daha fazla girdi gelene
                # kadar islenmeden bekleyebiliyordu. os.read() dogrudan
                # descriptor'dan okur, TextIOWrapper tamponunu devre disi
                # birakir.
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    try:
                        return os.read(fd, 1).decode(errors='replace')
                    except OSError:
                        return ""
                return ""
        elif msvcrt is not None:
            def read_key():
                if msvcrt.kbhit():
                    return msvcrt.getwch()
                time.sleep(0.05)
                return ""
        else:
            print("\n[KLAVYE] Tek tuş girişi bu sistemde kullanılamıyor.")
            return

        buffer = ""

        while _running:
            ch = read_key()
            
            if not ch:
                continue
            
            # Çıkış tuşu
            if ch == 'q' or ch == 'Q':
                print("\n[KLAVYE] Q basıldı — Çıkılıyor...")
                _running = False
                break
            
            # SPACE (boşluk) = anında başlat
            if ch == ' ':
                if not _manual_green:
                    print("\n[KLAVYE] SPACE basıldı — YEŞİL IŞIK! 🚦")
                    _manual_green = True
                continue
            
            # Karakter buffer'a ekle (büyük harfe çevir)
            buffer += ch.upper()
            
            # Buffer çok büyükse kısalt
            if len(buffer) > 10:
                buffer = buffer[-10:]
            
            # GG veya EZ kontrol
            if buffer.endswith("GG") or buffer.endswith("EZ"):
                cmd = buffer[-2:]
                if not _manual_green:
                    print(f"\n[KLAVYE] '{cmd}' yazıldı — YEŞİL IŞIK! 🚦")
                    _manual_green = True
                buffer = ""
    
    except Exception as e:
        print(f"\n[KLAVYE] Hata: {e}")
    finally:
        # Terminal'i normal moda döndür
        if termios is not None and fd is not None and old_settings is not None:
            try:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Yön yardımcısı
# ---------------------------------------------------------------------------
def _apply_dir(left: float, right: float) -> tuple:
    """Direksiyon değerlerini motorlara uygulamaya hazırla."""
    return left, right


def _send_motor(left: float, right: float) -> None:
    """TUM hareket komutlari bu fonksiyondan gecer (motor.brake() haric).

    LEGACY-048: Klavye thread'i _running=False yaptiginda, ana dongu
    zaten while kosulunu GECMIS ve mevcut yinelemenin icindeydi. Eski
    kod bu yinelemede baska bir motor.set_speed cagrisini ONLEMIYORDU;
    kapanma yalnizca dongu sinirinda gerceklesiyordu. Bu fonksiyon,
    komutu donanima ULASTIRMADAN HEMEN ONCE durdurma bayragini tekrar
    kontrol eder — dongu ust seviyesindeki tek bir kontrol yeterli degil.
    """
    if not _running:
        if motor is not None:
            try:
                motor.brake()
            except Exception:
                pass
        return
    motor.set_speed(left, right)


# ---------------------------------------------------------------------------
# Sollama alt durum makinesi (3 aşamalı)
# ---------------------------------------------------------------------------
# LEGACY-050: Faz suresi DUVAR SAATI DEGIL, biriken GERCEK HAREKET
# suresidir. Eski kod her seritsiz karede _state_timer'i 'now'a sifirliyordu;
# serit geri geldiginde faz esigi SIFIRDAN basliyor, o zamana kadar
# katedilen mesafe/donus TAMAMEN cop oluyordu. Kayip tekrarlandiginda
# manevra sureklice uzayabiliyordu. Simdi ilerleme yalnizca GERCEKTEN
# hareket edilirken (error is not None) birikir; kayipta DONUYOR, sifirlanmiyor.
_ovt_phase_elapsed: float = 0.0
_ovt_last_call: float | None = None


def _run_overtaking(error, now: float) -> None:
    global _state, _ovt_phase, _state_timer
    global _ovt_phase_elapsed, _ovt_last_call

    dt = 0.0 if _ovt_last_call is None else max(0.0, now - _ovt_last_call)
    _ovt_last_call = now

    if error is None:
        motor.brake()
        # LEGACY-050: _state_timer ARTIK SIFIRLANMIYOR — biriken ilerleme
        # korunuyor. Yalnizca "hareket etmiyoruz" gercegini yansitiyoruz.
        return

    # LEGACY-050: Sure yalnizca GERCEK hareket sirasinda birikir.
    _ovt_phase_elapsed += dt
    elapsed = _ovt_phase_elapsed

    # LEGACY-051: Faz ilerlemesi icin GORSEL serit kaniti da aranir —
    # yalnizca duvar/hareket suresine guvenmek, gercekte serit degisimi
    # hic gozlenmeden manevranin "tamamlandigini" ilan edebiliyordu.
    _lane_ok = getattr(lane_detector, 'lane_observed', True)

    if _ovt_phase == 0:
        eff_error = error - OVERTAKING_STEER_BIAS
        l, r = controller.compute(eff_error)
        scale = OVERTAKING_SPEED / max(abs(l), abs(r), 1)
        _send_motor(*_apply_dir(l * scale, r * scale))
        if elapsed >= OVERTAKING_CROSS_SEC and _lane_ok:
            _ovt_phase = 1
            _ovt_phase_elapsed = 0.0
    elif _ovt_phase == 1:
        l, r = controller.compute(error)
        scale = OVERTAKING_SPEED / max(abs(l), abs(r), 1)
        _send_motor(*_apply_dir(l * scale, r * scale))
        if elapsed >= OVERTAKING_PASS_SEC and _lane_ok:
            _ovt_phase = 2
            _ovt_phase_elapsed = 0.0
    elif _ovt_phase == 2:
        eff_error = error + OVERTAKING_STEER_BIAS
        l, r = controller.compute(eff_error)
        scale = OVERTAKING_SPEED / max(abs(l), abs(r), 1)
        _send_motor(*_apply_dir(l * scale, r * scale))
        if elapsed >= OVERTAKING_RETURN_SEC and _lane_ok:
            _state = 'SURUYOR'
            _ovt_phase = 0
            _ovt_phase_elapsed = 0.0
            _ovt_last_call = None
            controller.reset()


# ---------------------------------------------------------------------------
# Park etme
# ---------------------------------------------------------------------------
_park_target_lost_since: float | None = None   # LEGACY-052
_park_confirm_count: int = 0   # LEGACY-053: ardisik dogrulama sayaci


def _run_parking(frame: np.ndarray, error) -> None:
    global _state, _park_target_lost_since, _park_confirm_count
    
    hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
    roi = hsv[PARKING_ROI_TOP:, :]
    
    m1 = cv2.inRange(roi, np.array(PARKING_HSV_LOW1, dtype=np.uint8),
                          np.array(PARKING_HSV_HIGH1, dtype=np.uint8))
    m2 = cv2.inRange(roi, np.array(PARKING_HSV_LOW2, dtype=np.uint8),
                          np.array(PARKING_HSV_HIGH2, dtype=np.uint8))
    red_mask = cv2.bitwise_or(m1, m2)
    
    cnts, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    best_cx = None
    best_area = 0.0
    for c in cnts:
        area = cv2.contourArea(c)
        if area > best_area:
            best_area = area
            M = cv2.moments(c)
            if M['m00'] > 0:
                best_cx = int(M['m10'] / M['m00'])
    
    if best_area < PARKING_MIN_AREA or best_cx is None:
        # LEGACY-052: Eski kod, kirmizi hedef kayboldugunda SINIRSIZCA
        # serit takibine devam ediyordu (PARKING_SPEED ile) — hicbir hedef-
        # kaybi butcesi, arama siniri veya guvenli-duruma donus yoktu. Simdi
        # kayip suresi izlenir; butce asilirsa arac DURUR (sonsuz ilerlemez).
        now_mono = time.monotonic()
        if _park_target_lost_since is None:
            _park_target_lost_since = now_mono
        lost_for = now_mono - _park_target_lost_since

        _park_confirm_count = 0   # LEGACY-053: hedef kayipken ilerleme yok
        if lost_for >= PARKING_TARGET_LOST_SEC:
            motor.brake()
            return
        if error is None:
            motor.brake()
            return
        l, r = controller.compute(error)
        scale = PARKING_SPEED / max(abs(l), abs(r), 1)
        _send_motor(*_apply_dir(l * scale, r * scale))
        return

    # Hedef yeniden goruldu — kayip zamanlayicisini temizle.
    _park_target_lost_since = None

    off = best_cx - (WIDTH // 2)
    # LEGACY-053: TEK KARELIK bir merkezleme+alan okumasi TAM ARAC
    # KAPSANIMINI (containment) KANITLAMAZ — bu, kalibre edilmis zemin
    # duzlemi + arac ayak izi POZ TAHMINI gerektirir ve GERCEK OLCUM
    # olmadan kod-tarafinda guvenilir sekilde uygulanamaz. Ancak burada
    # yapabilecegimiz gercek bir iyilestirme var: TEK bir gurultulu/
    # ANLIK kare ile "PARK TAMAM" ilan ETME. Kosul PARKING_CONFIRM_FRAMES
    # ARDISIK karede DOGRULANMADAN tamamlanma ilan edilmez; herhangi bir
    # karede kosul bozulursa sayac SIFIRLANIR (gecici bir blob sicramasi
    # yetmez).
    if abs(off) <= PARKING_CENTER_TOL and best_area > PARKING_MIN_AREA * 4:
        motor.brake()
        _park_confirm_count += 1
        if _park_confirm_count >= PARKING_CONFIRM_FRAMES:
            _state = 'PARK_TAMAM'
        return
    else:
        _park_confirm_count = 0
    
    # LEGACY-054: Ham `PARKING_SPEED ± 0.3*off` sınırsızdır. 339 px'lik bir
    # sapma yaklaşık (131.7, -71.7) üretir: motor katmanı pozitif tarafı
    # kırpar ama NEGATİF tarafa izin verir; sonuç, ilan edilen park hızının
    # çok üzerinde güçlü bir PIVOT olur. Park ileri-yönlü bir manevradır:
    # direksiyon düzeltmesi, ortak ölçeklemeden ÖNCE taban hıza doyurulur.
    steer = float(off) * 0.3
    steer = max(-PARKING_SPEED, min(PARKING_SPEED, steer))   # ileri-yönlü kalsın
    l = PARKING_SPEED + steer
    r = PARKING_SPEED - steer

    # Hiçbir tekerlek park hızının üstüne çıkmasın (ortak ölçekleme).
    peak = max(abs(l), abs(r))
    if peak > PARKING_SPEED:
        scale = PARKING_SPEED / peak
        l *= scale
        r *= scale

    # Savunma amaçlı son kontrol: park sırasında ters yön komutu yok.
    l = max(0.0, min(float(PARKING_SPEED), l))
    r = max(0.0, min(float(PARKING_SPEED), r))
    _send_motor(*_apply_dir(l, r))


# ---------------------------------------------------------------------------
# Sürüş döngüsü (ana mantık)
# ---------------------------------------------------------------------------
def drive_loop() -> None:
    global _running, _state, _state_timer, _ovt_phase, _lane_lost_time
    global _race_start_time, _finish_printed, _time_warning_printed, _no_overtake_until
    global _crosswalk_consumed, _hemzemin_consumed
    global _speed_bump_consumed, _orange_car_consumed
    global _crosswalk_false_count, _hemzemin_false_count
    global _speed_bump_false_count, _orange_car_false_count
    global _loop_heartbeat
    global _ovt_phase_elapsed, _ovt_last_call, _park_target_lost_since
    global _park_confirm_count
    global _preview_disabled

    frame_count = 0
    _preview_disabled = False   # LEGACY-064
    _last_processed_seq = None   # LEGACY-045
    last_print = time.monotonic()   # LEGACY-055

    _err_count = 0

    while _running:
      try:
        # LEGACY-046: Watchdog kalp atışı. Bu satıra ulaşılamıyorsa
        # (bloke kamera okuma, işleme, çizim, disk G/Ç) bağımsız
        # watchdog thread'i motorları frenler.
        _loop_heartbeat = time.monotonic()
        frame = camera.capture()

        # LEGACY-045: Islem dongusu Pi kamerasindan HIZLI calisirsa, ayni
        # yayimlanmis kare BIRDEN FAZLA kez islenebilir. Bu, TEK bir
        # optik gozlemin ardisik-kare dogrulamasini (event debounce,
        # serit hafizasi, kontrolor turevi/integrali) sahte sekilde
        # BIRDEN FAZLA kez ilerletmesine yol acar — ornegin tek bir
        # yesil kare, 6 karelik baslama esigini tek basina doldurabilir.
        # Kamera sira numarasi degismediyse bu YENI bir gozlem degildir.
        _cur_seq = getattr(camera, '_seq', None)
        if _cur_seq is not None and _cur_seq == _last_processed_seq:
            _err_count = 0   # capture basarili — bu bir HATA degil
            time.sleep(0.005)   # yeni kare bekle; kontrol yolunu mesgul etme
            continue
        _last_processed_seq = _cur_seq

        if tur_kayit is not None:
            tur_kayit.telemetri(durum=_state, hata=None)
        error, debug = lane_detector.process(frame)
        events = event_detector.detect(frame)
        light = events['traffic_light']
        # LEGACY-055: TUM kontrol sureleri (state_timer, race_start_time,
        # lane_lost_time, no_overtake_until) bu 'now' ile karsilastirilir.
        # time.time() DUVAR SAATIDIR; sistem saati ayarlanirsa (NTP senk,
        # elle duzeltme) her bekleme/manevra/yasak suresi yanlis hesaplanir.
        # time.monotonic() sistem saatinden BAGIMSIZDIR ve yalnizca ileri akar.
        now = time.monotonic()

        # LEGACY-056: Rearm ARTIK tek bir yanlis karede olmuyor. Her olay
        # icin ardisik YANLIS kare sayacini tutuyoruz; sayac
        # EVENT_REARM_HYSTERESIS_FRAMES'e ulasinca (onaylamayla AYNI esik)
        # bayrak gercekten geri aciliyor. Boylece devam eden bir manevra
        # sirasindaki tek karelik bir goz kirpma, ayni nesne icin ikinci
        # bir dur/manevra TETIKLEYEMEZ.
        if not events['crosswalk']:
            _crosswalk_false_count += 1
            if _crosswalk_false_count >= EVENT_REARM_HYSTERESIS_FRAMES:
                _crosswalk_consumed = False
        else:
            _crosswalk_false_count = 0
        if not events['hemzemin']:
            _hemzemin_false_count += 1
            if _hemzemin_false_count >= EVENT_REARM_HYSTERESIS_FRAMES:
                _hemzemin_consumed = False
        else:
            _hemzemin_false_count = 0
        if not events['speed_bump']:
            _speed_bump_false_count += 1
            if _speed_bump_false_count >= EVENT_REARM_HYSTERESIS_FRAMES:
                _speed_bump_consumed = False
        else:
            _speed_bump_false_count = 0
        if not events['orange_car']:
            _orange_car_false_count += 1
            if _orange_car_false_count >= EVENT_REARM_HYSTERESIS_FRAMES:
                _orange_car_consumed = False
        else:
            _orange_car_false_count = 0

        # GG/EZ/SPACE/buton ile elle başlangıç onayı
        if _manual_green:
            light = 'green'

        # 240 sn yarış zaman uyarısı (Kural 4.4)
        if (_race_start_time is not None
                and not _time_warning_printed
                and now - _race_start_time > 240.0):
            _time_warning_printed = True
            print("[main] ⚠  240 sn DOLDU — hakem turu sonlandirabilir!")

        # ================================================================
        # LEGACY-058: KÜRESEL GÜVENLİK ARBİTRAJI
        # ================================================================
        # Olaylar her turda tespit ediliyor, ancak özel durum dalları
        # yalnızca kendi yerel koşullarını ele alıyordu: hareket hâlindeki
        # YAYA_YAKLAS / HEMZEMIN_YAKLAS / TUMSEK / SOLLAMA / PARK durumları
        # yeni beliren bir durdurma olayını ya da sollama yasağını tamamen
        # görmezden geliyordu. Durum makinesine girmeden ÖNCE, hareketli
        # her durum için izin verilen kesintileri değerlendir.
        _MOVING_STATES = ('YAYA_YAKLAS', 'HEMZEMIN_YAKLAS', 'TUMSEK',
                          'SOLLAMA', 'PARK', 'SURUYOR')
        if _state in _MOVING_STATES:
            _abort_reason = None

            # 1) Çıkmaz sokak tabelası her hareketli durumu keser.
            if events.get('sign_type') == 'cikmazsokak':
                _abort_reason = "ÇIKMAZ SOKAK tabelası"
                _safe_state = 'CIKMAZSOKAK'

            # 2) Yakın yaya geçidi: TUMSEK/SOLLAMA/PARK sırasında da durdurur.
            elif (events['crosswalk'] and events['crosswalk_close']
                  and not _crosswalk_consumed and _state != 'YAYA_YAKLAS'):
                _abort_reason = "yakın YAYA GEÇİDİ"
                _safe_state = 'YAYA_GECİDİ'
                _crosswalk_consumed = True

            # 3) Yakın hemzemin geçit: aynı şekilde.
            elif (events['hemzemin'] and events['hemzemin_close']
                  and not _hemzemin_consumed and _state != 'HEMZEMIN_YAKLAS'):
                _abort_reason = "yakın HEMZEMİN GEÇİT"
                _safe_state = 'HEMZEMIN'
                _hemzemin_consumed = True

            # 4) SOLLAMA sırasında beliren sarı araç = sollama yasağı.
            #    Manevrayı sürdürmek yerine güvenli şekilde iptal et.
            elif _state == 'SOLLAMA' and events['yellow_car']:
                _abort_reason = "SOLLAMA sırasında SARI ARAÇ belirdi"
                _safe_state = 'ENGEL_BEKLE'

            if _abort_reason is not None:
                print(f"[main] ⚠  GÜVENLİK KESİNTİSİ ({_state}): {_abort_reason}")
                if tur_kayit is not None:
                    tur_kayit.durum_degisti(_state, _safe_state,
                                            sebep=_abort_reason)
                motor.brake()
                _state = _safe_state
                _state_timer = now
                _ovt_phase = 0
                controller.reset()
                logger.update(error)
                _err_count = 0
                continue

        # ================================================================
        # Durum makinesi
        # ================================================================
        if _state == 'BEKLIYOR':
            motor.brake()
            if light == 'green':
                _state = 'SURUYOR'
                controller.reset()
                if _race_start_time is None:
                    _race_start_time = now
                    # LEGACY-040: kayit penceresi TAM BURADA baslar —
                    # BEKLIYOR'da gecen sure penceriyi tuketmez.
                    if logger is not None:
                        logger.start_recording()
                print("[main] 🚦 YEŞİL IŞIK ALGILANDI — HAREKET! (Kural 3.4.1)")

        elif _state == 'SURUYOR':
            sign = events.get('sign_type')

            # Tabela tepkileri — yol tespitinden önce kontrol edilir
            if sign == 'cikmazsokak':
                _state = 'CIKMAZSOKAK'
                motor.brake()
                print("[main] 🚫 ÇIKMAZ SOKAK tabelası — araç durdu")
                # Aynı karedeki başka bir olayın bu duruşu geçersiz kılmasına izin verme.
                logger.update(error)
                _err_count = 0
                continue
            elif sign == 'sollamabam':
                _no_overtake_until = now + _NO_OVERTAKE_SEC
                print(f"[main] ⛔ SOLLAMA YASAĞI — {_NO_OVERTAKE_SEC:.0f}s geçerli")

            if events['crosswalk'] and not _crosswalk_consumed:
                if events['crosswalk_close']:
                    _state = 'YAYA_GECİDİ'
                    _state_timer = now
                    _crosswalk_consumed = True
                    motor.brake()
                else:
                    _state = 'YAYA_YAKLAS'
                    _state_timer = now
                    motor.brake()
            elif events['hemzemin'] and not _hemzemin_consumed:
                if events['hemzemin_close']:
                    _state = 'HEMZEMIN'
                    _state_timer = now
                    _hemzemin_consumed = True
                    motor.brake()
                else:
                    _state = 'HEMZEMIN_YAKLAS'
                    _state_timer = now
                    motor.brake()
            elif events['speed_bump'] and not _speed_bump_consumed:
                _state = 'TUMSEK'
                _state_timer = now
                _speed_bump_consumed = True
                motor.brake()
            elif (events['orange_car'] and not _orange_car_consumed
                  and not events['yellow_car'] and now >= _no_overtake_until):
                _state = 'SOLLAMA'
                _state_timer = now
                _ovt_phase = 0
                _ovt_phase_elapsed = 0.0     # LEGACY-050: taze giris
                _ovt_last_call = None
                _orange_car_consumed = True
                motor.brake()
            # LEGACY-060: Engel VAR ama geçiş izni YOK (sarı araç görünür
            # ya da sollama yasağı aktif). Eski kodda bu koşullar yalnızca
            # sollama dalını devre dışı bırakıyor, kontrol normal şerit
            # takibine düşüyordu — yani araç, tam da geçmesi yasakken
            # algılanan engele doğru sürmeye devam ediyordu. Engel varlığı
            # geçiş izninden BAĞIMSIZ ele alınır: güvenli bekleme durumu.
            elif events['orange_car'] and not _orange_car_consumed:
                _blocker = ("sarı araç" if events['yellow_car']
                            else "sollama yasağı")
                print(f"[main] 🛑 ENGEL var, geçiş yasak ({_blocker}) — "
                      "güvenli bekleme")
                _state = 'ENGEL_BEKLE'
                _state_timer = now
                motor.brake()
            elif events['parking_zone']:
                _state = 'PARK'
                _park_target_lost_since = None   # LEGACY-052: taze giris
                _park_confirm_count = 0          # LEGACY-053: taze giris
                controller.reset()
                motor.brake()
            else:
                # Normal sürüş — şerit kayıp failsafe
                #
                # LEGACY-039: Zamanlayici artik "error is None" yerine
                # GERCEK GOZLEM kaybinda baslar. Eski kodda serit detektoru
                # 25 kare boyunca onbellekten sayisal bir hata uretiyordu;
                # bu sure boyunca error None OLMADIGI icin guvenlik
                # zamanlayicisi hic baslamiyor, arac bayat tahminle
                # surmeye devam ediyordu. Sinirli tahmini direksiyona izin
                # verilir, ancak guvenlik saati gercek kayipta isler.
                _lane_seen = getattr(lane_detector, 'lane_observed', error is not None)
                if not _lane_seen and _lane_lost_time is None:
                    _lane_lost_time = now
                    print("[main] ⚠  SERIT GOZLEMI KAYIP — güvenlik saati başladı")
                elif _lane_seen:
                    _lane_lost_time = None

                if _lane_lost_time is not None and (now - _lane_lost_time) >= LANE_LOST_TURN_SEC:
                    # Gercek gozlem uzun suredir yok → guvenli dur
                    motor.brake()
                    controller.reset()
                elif error is None:
                    if _lane_lost_time is None:
                        _lane_lost_time = now
                        print("[main] ⚠  SERIT KAYIP — son gerçek yön korunuyor")
                    lost_sec = now - _lane_lost_time
                    if lost_sec < LANE_LOST_TURN_SEC:
                        # Denetleyicinin son gerçek yönünü türev üretmeden azalt.
                        l, r = controller.compute(None)
                        _send_motor(*_apply_dir(l, r))
                    else:
                        # Süre doldu, hâlâ şerit yok → güvenli dur
                        motor.brake()
                else:
                    if _lane_lost_time is not None:
                        print("[main] OK serit tekrar bulundu")
                        _lane_lost_time = None
                        controller.reset()
                    l, r = controller.compute(error)
                    _send_motor(*_apply_dir(l, r))

        elif _state == 'YAYA_YAKLAS':
            # Yaya geçidini gördük, henüz 30 cm eşiğine gelmedik — yavaş yaklaş.
            #
            # LEGACY-061: Zaman asimi eskiden DOGRUDAN 'basariyla varildi'
            # anlamina geliyordu (YAYA_GECIDI'ye gecip olayi TUKETIYORDU),
            # araç durmus olsa veya seridi kaybetmis olsa bile. Bu, aracin
            # gerekli durma noktasindan cok once beklemesine, sonra GERCEK
            # gecidin uzerinden GECMESINE yol acabilirdi. Zaman asimi artik
            # bir ARIZA/yeniden-deneme durumudur: DUR ve konum kanitini
            # (yakin tespit) bekle; sonsuz surmeyi de onlemek icin sinirli
            # bir kurtarma penceresinden sonra guvenli sekilde olayi tuket.
            timeout = (now - _state_timer) >= APPROACH_TIMEOUT_SEC
            if events['crosswalk_close']:
                _state = 'YAYA_GECİDİ'
                _state_timer = now
                _crosswalk_consumed = True
                motor.brake()
            elif timeout:
                # Konum kaniti YOK — arizali yaklasma. Dur, tekrar deneme.
                motor.brake()
                if (now - _state_timer) >= (APPROACH_TIMEOUT_SEC
                                            + APPROACH_RECOVERY_SEC):
                    print("[main] ⚠ YAYA_YAKLAS: yakin tespit hic gelmedi — "
                          "güvenli sekilde tüketiliyor")
                    _state = 'YAYA_GECİDİ'
                    _state_timer = now
                    _crosswalk_consumed = True
            elif error is None:
                motor.brake()
            else:
                l, r = controller.compute(error)
                scale = APPROACH_SPEED / max(abs(l), abs(r), 1)
                _send_motor(*_apply_dir(l * scale, r * scale))

        elif _state == 'HEMZEMIN_YAKLAS':
            timeout = (now - _state_timer) >= APPROACH_TIMEOUT_SEC
            if events['hemzemin_close']:
                _state = 'HEMZEMIN'
                _state_timer = now
                _hemzemin_consumed = True
                motor.brake()
            elif timeout:
                motor.brake()
                if (now - _state_timer) >= (APPROACH_TIMEOUT_SEC
                                            + APPROACH_RECOVERY_SEC):
                    print("[main] ⚠ HEMZEMIN_YAKLAS: yakin tespit hic gelmedi "
                          "— güvenli sekilde tüketiliyor")
                    _state = 'HEMZEMIN'
                    _state_timer = now
                    _hemzemin_consumed = True
            elif error is None:
                motor.brake()
            else:
                l, r = controller.compute(error)
                scale = APPROACH_SPEED / max(abs(l), abs(r), 1)
                _send_motor(*_apply_dir(l * scale, r * scale))

        elif _state == 'YAYA_GECİDİ':
            motor.brake()
            if now - _state_timer >= CROSSWALK_WAIT_SEC:
                _state = 'SURUYOR'
                controller.reset()

        elif _state == 'HEMZEMIN':
            motor.brake()
            if now - _state_timer >= HEMZEMIN_WAIT_SEC:
                _state = 'SURUYOR'
                controller.reset()

        elif _state == 'TUMSEK':
            if error is None:
                motor.brake()
            else:
                l, r = controller.compute(error)
                scale = SPEED_BUMP_SPEED / max(abs(l), abs(r), 1)
                _send_motor(*_apply_dir(l * scale, r * scale))
            # LEGACY-062: Sabit sureli yavas mod, arac o sure boyunca hic
            # hareket etmemis (serit kaybi nedeniyle frenlemis) OLSA BILE
            # doluyordu; speed_bump_consumed=True kaldigi icin normal hiz
            # dogrudan tumsegin USTUNDE devam edebiliyordu. Simdi cikis icin
            # HEM sure dolmus HEM de GORSEL olarak tumsek artik algilanmiyor
            # olmali (araç fiilen gecmis). Yalnizca sure yeterli degildir.
            _bump_time_ok = (now - _state_timer) >= SPEED_BUMP_SLOW_SEC
            _bump_visually_clear = not events.get('speed_bump', False)
            if _bump_time_ok and _bump_visually_clear:
                _state = 'SURUYOR'
            elif (now - _state_timer) >= SPEED_BUMP_SLOW_SEC * SPEED_BUMP_MAX_EXTEND_MULT:
                # Guvenlik supabi: gorsel temizlik hic gelmezse (sensor
                # kaybi vb.) sonsuza dek yavas modda KALMA — sinirli bir
                # uzatmadan sonra yine de devam et.
                _state = 'SURUYOR'

        elif _state == 'SOLLAMA':
            _run_overtaking(error, now)

        elif _state == 'PARK':
            _run_parking(frame, error)

        elif _state == 'ENGEL_BEKLE':
            # LEGACY-060: Güvenli engel bekleme. Araç DURUR; sollama ancak
            # açık bir "temiz" kontrolünden sonra başlar. Zaman aşımıyla
            # kendiliğinden sürüşe dönmez — engel gerçekten kalkmalıdır.
            motor.brake()
            _clear = (not events['orange_car']
                      and not events['yellow_car']
                      and now >= _no_overtake_until)
            if _clear:
                print("[main] ✅ Engel kalktı ve geçiş serbest — sürüşe dönülüyor")
                _state = 'SURUYOR'
                controller.reset()
                _orange_car_consumed = False

        elif _state == 'CIKMAZSOKAK':
            motor.brake()

        elif _state == 'PARK_TAMAM':
            motor.brake()
            if not _finish_printed:
                _finish_printed = True
                if _race_start_time is not None:
                    elapsed = now - _race_start_time
                    bonus = 240.0 - elapsed
                    print(f"[main] 🏁 BITIRME: {elapsed:.1f}s | "
                          f"Bitirme katsayisi: {bonus:+.0f} (Kural 4.3)")
        
        # ---- Kayıt ----
        logger.update(error)

        # ---- Önizleme penceresi ----
        # LEGACY-064: GUI cagrisi surus mantigindan IZOLE edilir. Bir
        # imshow/waitKey hatasi (orn. headless ortamda calisan gorunum
        # destegi olmayan bir OpenCV derlemesi) surus HATASI sayilip
        # _err_count'u ARTIRMAZ ve kapatmayi TETIKLEMEZ — yalnizca
        # onizleme kendini KAPATIR, arac surmeye devam eder.
        if SHOW_PREVIEW and not _preview_disabled:
            try:
                raw_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                cv2.putText(raw_bgr,
                            f"{_state} | {f'{error:+d}px' if error is not None else 'SERIT YOK'}",
                            (8, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 255), 2)
                debug_bgr = cv2.cvtColor(debug, cv2.COLOR_RGB2BGR)
                debug_bgr = cv2.resize(debug_bgr, (WIDTH, debug_bgr.shape[0]))
                cv2.imshow('Otonom Arac', np.vstack([raw_bgr, debug_bgr]))
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    _running = False
            except Exception as exc:
                _preview_disabled = True
                print(f"[main] UYARI: önizleme penceresi kullanılamıyor "
                      f"({exc}); GUI olmadan (headless) devam ediliyor.")
                try:
                    cv2.destroyAllWindows()
                except Exception:
                    pass

        # ---- Periyodik bilgi (her 2 saniyede bir) ----
        frame_count += 1
        if now - last_print >= 2.0:
            err_str   = f"{error:+d}px" if error is not None else "SERIT_YOK"
            light_str = light or "yok"
            fps       = frame_count / (now - last_print)
            ev_flags  = " ".join(
                k.upper() for k, v in events.items()
                if v and k not in ('traffic_light', 'sign_type', 'sign_blue')
            ) or "-"
            if events.get('sign_type'):
                ev_flags += f" TABELA:{events['sign_type']}"
            t_str = (f"t={now - _race_start_time:.0f}s "
                     if _race_start_time is not None else "")
            print(f"[main] [{_state:14s}] {t_str}err={err_str:8s} | "
                  f"isik={light_str:5s} | olaylar={ev_flags} | FPS={fps:.1f}")
            frame_count = 0
            last_print  = now

        _err_count = 0

      except Exception as _e:
        _err_count += 1
        import traceback
        print(f"[main] KARE HATASI ({_err_count}): {_e}")
        # Bir onceki PWM komutunu hata boyunca tasimak yerine hemen dur.
        motor.brake()
        if _err_count == 1:
            traceback.print_exc()
        if _err_count >= 30:
            raise RuntimeError("Art arda 30 kare işlenemedi") from _e


# ---------------------------------------------------------------------------
# Kapatma
# ---------------------------------------------------------------------------
def _shutdown(sig=None, frame=None) -> None:
    """LEGACY-065: Durdurma niyeti önce mandallanır, motor enerjisi
    HERHANGİ bir tanılama çıktısından ÖNCE kesilir, ve 'tamamlandı'
    bayrağı yalnızca temizlik GERÇEKTEN çalıştıktan sonra konur.

    Eski sıralama `_shutdown_complete = True` -> print() -> motor.stop()
    şeklindeydi: print bloke olur ya da hata verirse (örn. kırık boru)
    hiçbir cihaz temizliği yapılmıyor, üstelik bayrak zaten True olduğu
    için sonraki tüm kapatma denemeleri de anında geri dönüyordu.
    """
    global _running, _shutdown_complete

    # 1) Durdurma niyetini derhal mandalla — sürüş döngüsü bir sonraki
    #    adımda duracak. Bu bayrak tanılamadan bağımsızdır.
    _running = False

    if _shutdown_complete:
        if sig is not None:
            raise SystemExit(128 + int(sig))
        return

    # 2) Motor enerjisini KES — hiçbir çıktı denemesinden önce.
    motor_ok = True
    if motor is not None:
        try:
            result = motor.stop()
            motor_ok = result is not False
        except Exception:
            motor_ok = False
            try:
                motor.brake()
            except Exception:
                pass

    # 3) Tanılama çıktısı ancak şimdi; hata verirse temizlik zaten yapıldı.
    try:
        print("\n[main] Kapatılıyor...")
    except Exception:
        pass

    # 4) Kalan kaynaklar; her biri bağımsız, biri diğerini engellemez.
    if tur_kayit is not None:
        try:
            tur_kayit.bitir(sonuc=_state)
        except Exception:
            pass

    cleanup_ok = motor_ok
    for name, cleanup in (
        ("camera", camera.stop if camera is not None else None),
        ("logger", logger.finish if logger is not None else None),
        ("button", _button_handle.close if _button_handle is not None else None),
        ("windows", cv2.destroyAllWindows),
    ):
        if cleanup is None:
            continue
        try:
            cleanup()
        except Exception as e:
            cleanup_ok = False
            try:
                print(f"[main] {name} kapatma hatasi: {e}")
            except Exception:
                pass

    if _kb_thread is not None and _kb_thread is not threading.current_thread():
        _kb_thread.join(timeout=0.5)

    # 5) Yalnızca temizlik gerçekten tamamlandıysa 'tamamlandı' işaretle.
    #    Aksi hâlde bayrak False kalır ve kapatma YENİDEN denenebilir.
    if cleanup_ok:
        _shutdown_complete = True
    else:
        try:
            print("[main] UYARI: kapatma eksik kaldı — yeniden denenebilir.")
        except Exception:
            pass

    if sig is not None:
        raise SystemExit(128 + int(sig))


def _on_button_pressed() -> None:
    """Fiziksel start butonu (Kural 3.4.1, +50 puan): elle başlangıç onayı."""
    global _manual_green
    if not _manual_green:
        print("\n[main] 🔘 BUTON basıldı — YEŞİL IŞIK! 🚦")
        _manual_green = True


def _setup_start_button():
    """gpiozero.Button ile fiziksel start butonu bağla.

    Pi/gpiozero yoksa veya pin meşgulse sessizce skip — kod yine
    klavye/yeşil ışık ile çalışır. Bu sayede buton donanımı hazır
    olmasa bile geliştirme/test sürer.
    """
    global _button_handle
    if not _HAS_BUTTON:
        print("[main] gpiozero yok — fiziksel buton devre dışı (klavye/ışık aktif).")
        return
    try:
        _button_handle = _GpioButton(
            START_BUTTON_PIN, pull_up=True, bounce_time=0.05
        )
        _button_handle.when_pressed = _on_button_pressed
        print(f"[main] ✅ Fiziksel start butonu hazır (GPIO {START_BUTTON_PIN}).")
    except Exception as e:
        _button_handle = None
        print(f"[main] Buton kurulumu basarisiz ({e}) — klavye/ışık ile başlatın.")


# ---------------------------------------------------------------------------
# Giriş noktası
# ---------------------------------------------------------------------------
def main() -> int:
    global camera, lane_detector, controller, motor, logger, event_detector, tur_kayit
    global _kb_thread, _running, _shutdown_complete, _state, _state_timer
    global _ovt_phase, _manual_green, _lane_lost_time, _race_start_time
    global _finish_printed, _time_warning_printed, _button_handle
    global _crosswalk_consumed, _hemzemin_consumed
    global _speed_bump_consumed, _orange_car_consumed, _no_overtake_until
    global _crosswalk_false_count, _hemzemin_false_count
    global _speed_bump_false_count, _orange_car_false_count
    global _watchdog_thread, _loop_heartbeat, _watchdog_tripped
    global _ovt_phase_elapsed, _ovt_last_call, _park_target_lost_since
    global _preview_disabled, _park_confirm_count

    _running = True
    _shutdown_complete = False
    _loop_heartbeat = 0.0        # döngü başlayana kadar watchdog tetiklenmez
    _watchdog_tripped = False
    _state = 'BEKLIYOR'
    _state_timer = 0.0
    _ovt_phase = 0
    _ovt_phase_elapsed = 0.0    # LEGACY-050
    _ovt_last_call = None
    _park_target_lost_since = None   # LEGACY-052
    _park_confirm_count = 0          # LEGACY-053
    _manual_green = False
    _lane_lost_time = None
    _race_start_time = None
    _finish_printed = False
    _time_warning_printed = False
    _button_handle = None
    _crosswalk_consumed = False
    _hemzemin_consumed = False
    _speed_bump_consumed = False
    _orange_car_consumed = False
    _crosswalk_false_count = 0    # LEGACY-056
    _hemzemin_false_count = 0
    _speed_bump_false_count = 0
    _orange_car_false_count = 0
    _no_overtake_until = 0.0
    _kb_thread = None

    exit_code = 0
    try:
        signal.signal(signal.SIGINT, _shutdown)
        signal.signal(signal.SIGTERM, _shutdown)

        motor = MotorDriver()
        motor.require_hardware()
        camera = _Camera()
        lane_detector = LaneDetector()
        controller = PDController()
        logger = ErrorLogger()
        event_detector = EventDetector()

        # Tur kaydi — diske JSONL. Arka plan thread'inde yazar, surus
        # dongusunu bloke etmez. Hata olursa kayit sessizce devre disi
        # kalir; surus etkilenmez.
        try:
            from tur_kaydedici import TurKaydedici
            tur_kayit = TurKaydedici()
            tur_kayit.baslat(tur_adi="yaris")
        except Exception as exc:
            print(f"[main] Tur kaydi baslatilamadi (surus etkilenmez): {exc}")
            tur_kayit = None

        print()
        print("[main] ╔════════════════════════════════════════════╗")
        print("[main] ║   OTONOM ARAÇ — BAŞLAMA MODUNDA            ║")
        print("[main] ╚════════════════════════════════════════════╝")
        print()
        print("[main] BAŞLAMA YÖNTEMI:")
        print("[main]   1️⃣  Trafik ışığı yeşil olur     → Araç otomatik başlar")
        print("[main]   2️⃣  'GG' veya 'EZ' yazın        → Elle başlangıç onayı")
        print("[main]   3️⃣  SPACE (boşluk) tuşu basın   → Araç hemen başlar (kısayol)")
        print(f"[main]   4️⃣  Fiziksel buton (GPIO {START_BUTTON_PIN}) → +50 puan (Kural 3.4.1)")
        print()
        print("[main] DİĞER:")
        print("[main]   Q tuşu        → Programdan çık")
        print("[main]   Ctrl+C        → Acil durdurma")
        print()

        # Klavye dinleyiciyi ayrı thread'de başlat
        _kb_thread = threading.Thread(target=keyboard_listener, daemon=True)
        _kb_thread.start()

        # LEGACY-046: Sürüş döngüsünden bağımsız motor komut watchdog'u.
        # Kontrol yolu herhangi bir yerde bloke olursa motorları frenler.
        # NOT: Bu bir YAZILIM koruması; bağımsız FİZİKSEL acil durdurma
        # mekanizmasının yerini tutmaz.
        _watchdog_thread = threading.Thread(target=_motor_watchdog, daemon=True)
        _watchdog_thread.start()

        # Fiziksel start butonu (varsa) — bekletmez, donanım yoksa pas geçer
        _setup_start_button()

        print("[main] Kamera, lane detector, event detector hazir.")
        print("[main] Ayar icin: python tune.py")
        print("[main]")
        print("[main] ✅ Sistem hazir - YESIL ISIK BEKLENIYOR...")
        print()

        drive_loop()
    except KeyboardInterrupt:
        exit_code = 130
    except MotorHardwareUnavailable as e:
        exit_code = 1
        print(f"[main] BAŞLATILAMADI: {e}")
    except Exception as e:
        import traceback
        exit_code = 1
        print(f"[main] FATAL HATA: {e}")
        traceback.print_exc()
    finally:
        _shutdown()

    return exit_code


if __name__ == '__main__':
    raise SystemExit(main())
