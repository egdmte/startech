# =============================================================================
# main.py  —  Otonom şerit takip ana giriş noktası
#
# Mimari
# ------
#   drive_loop()   → ayrı thread: kare al → tespit et → PD → motorlar
#   Flask sunucu   → ana thread: port 5000'de MJPEG debug yayını
#
# Başlatma (yayın ile, test için):   python main.py
# Başlatma (yarış modu, Wi-Fi kapalı): python main.py --no-stream
# Yayın: http://<raspberry-pi-ip>:5000/
#
# !! ÖNEMLİ: Yarış sırasında Wi-Fi KAPALI olmalı (kural 2.3).
#    Yarış koşuları için --no-stream kullanın. Flask yalnızca test içindir.
# =============================================================================
import argparse
import signal
import sys
import threading
import time

import cv2
import numpy as np

# Kamera: Pi'de picamera2, geliştirme/test için OpenCV VideoCapture
try:
    from picamera2 import Picamera2
    _USE_PICAMERA = True
except ImportError:
    _USE_PICAMERA = False
    print("[main] picamera2 bulunamadı — OpenCV VideoCapture kullanılıyor (geliştirme modu)")

from config import (
    WIDTH, HEIGHT,
    CROSSWALK_WAIT_SEC, HEMZEMIN_WAIT_SEC,
    SPEED_BUMP_SLOW_SEC, SPEED_BUMP_SPEED,
    OVERTAKING_STEER_BIAS, OVERTAKING_CROSS_SEC,
    OVERTAKING_PASS_SEC, OVERTAKING_RETURN_SEC, OVERTAKING_SPEED,
    DEAD_END_TURN_SEC, DEAD_END_TURN_SPEED,
    PARKING_HSV_LOW1, PARKING_HSV_HIGH1,
    PARKING_HSV_LOW2, PARKING_HSV_HIGH2,
    PARKING_MIN_AREA, PARKING_ROI_TOP,
    PARKING_SPEED, PARKING_CENTER_TOL,
    START_BUTTON_PIN, CAMERA_BGR_OUTPUT,
)
from controller import PDController
from events import EventDetector
from lane import LaneDetector
from logger import ErrorLogger
from motor import MotorDriver

# ---------------------------------------------------------------------------
# Komut satırı argümanları
# ---------------------------------------------------------------------------
parser = argparse.ArgumentParser(description='Otonom Araç')
parser.add_argument('--no-stream', action='store_true',
                    help='Flask MJPEG yayınını devre dışı bırak (yarış modu — Wi-Fi kapalı olmalı)')
args = parser.parse_args()

# ---------------------------------------------------------------------------
# Kamera sarmalayıcı  (Pi → picamera2 | geliştirme → OpenCV VideoCapture)
# ---------------------------------------------------------------------------
class _Camera:
    def __init__(self):
        if _USE_PICAMERA:
            self._cam = Picamera2()
            cfg = self._cam.create_preview_configuration(
                main={"size": (WIDTH, HEIGHT), "format": "RGB888"}
            )
            self._cam.configure(cfg)
            self._cam.start()
            time.sleep(2)
        else:
            self._cap = cv2.VideoCapture(0)
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH,  WIDTH)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)

    def capture(self) -> np.ndarray:
        """Her iki arka uçtan da RGB kare döndürür.

        Renk kanalı düzeltme notu
        -------------------------
        picamera2 bazı donanım/sürüm kombinasyonlarında 4 kanallı (RGBA/BGRA)
        ya da BGR sıralı frame dönebilir. Görüntüde renk takası varsa
        config.py içindeki CAMERA_BGR_OUTPUT = True yapın.
        """
        if _USE_PICAMERA:
            frame = self._cam.capture_array()
            # 4 kanallıysa (RGBA / BGRx) → 3 kanala indir
            if frame.ndim == 3 and frame.shape[2] == 4:
                frame = frame[:, :, :3]
            # Donanım BGR dönüyorsa RGB'ye çevir
            if CAMERA_BGR_OUTPUT:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            return frame
        ret, frame = self._cap.read()
        if not ret:
            return np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
        frame = cv2.resize(frame, (WIDTH, HEIGHT))
        return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    def stop(self):
        if _USE_PICAMERA:
            self._cam.stop()
        else:
            self._cap.release()


# ---------------------------------------------------------------------------
# Donanım başlatma
# ---------------------------------------------------------------------------
camera         = _Camera()
lane_detector  = LaneDetector()
controller     = PDController()
motor          = MotorDriver()
logger         = ErrorLogger()
event_detector = EventDetector()

# ---------------------------------------------------------------------------
# Paylaşılan durum
# ---------------------------------------------------------------------------
_latest_frame: bytes | None = None
_frame_lock  = threading.Lock()
_running     = True
_cur_events: dict = {}
_cur_state:  str  = 'BEKLIYOR'
_cur_error:  float | None = None   # güncel yanal piksel hatası (web API için)
_flipped:    bool = False

# ---------------------------------------------------------------------------
# Durum makinesi değişkenleri
# ---------------------------------------------------------------------------
# Durumlar:
#   BEKLIYOR    — yeşil trafik ışığı bekleniyor (yarış henüz başlamadı)
#                 Kural 3.4.1: yeşil ışıktan itibaren ≤3 saniyede hareket et
#   SURUYOR     — normal şerit takip (PD denetleyici aktif)
#   KIRMIZI_ISIK— kırmızı trafik ışığında duruldu
#   YAYA_GECİDİ — yaya geçidinde bekle (kural 3.4.2: ≥5 s, mesafe ≤30 cm)
#   HEMZEMIN    — hemzemin geçitte bekle (kural 3.4.4: ≥5 s, mesafe ≤30 cm)
#   TUMSEK      — hız tümsek üzerinde yavaş geç (kural 3.4.3)
#   CIKMAZ_YOL  — sağa dön, çıkmaz yola GİRME (kural 3.4.6)
#   SOLLAMA     — turuncu aracı geç, 3 aşamalı açık döngü manevra (kural 3.4.5)
#   PARK        — kırmızı park slotunu bul ve içine gir (kural 3.4.7)
#   PARK_TAMAM  — yarış tamamlandı, sabit dur
_state       = 'BEKLIYOR'  # Yarış her zaman BEKLIYOR → yeşil ışık ile başlar
_state_timer = 0.0
_ovt_phase   = 0   # sollama alt aşaması: 0=geç, 1=takip, 2=dön


# ---------------------------------------------------------------------------
# Sürüş döngüsü  (ayrı bir daemon thread'de çalışır)
# ---------------------------------------------------------------------------
def drive_loop() -> None:
    global _latest_frame, _running, _state, _state_timer
    global _cur_events, _cur_state, _cur_error, _ovt_phase

    while _running:
        frame  = camera.capture()
        error, debug = lane_detector.process(frame)
        events       = event_detector.detect(frame)
        _cur_events  = events
        light        = events['traffic_light']
        now          = time.time()

        # ----------------------------------------------------------------
        # Durum makinesi
        # ----------------------------------------------------------------
        if _state == 'SURUYOR':
            if light == 'red':
                # Kırmızı ışık → anında dur
                _state = 'KIRMIZI_ISIK'
                motor.brake()

            elif events['crosswalk']:
                # Yaya geçidi — kural 3.4.2: ≥30 cm mesafede dur, ≥5 s bekle.
                # NOT: Bu kontrol dead_end'den ÖNCE gelmeli.
                # Yaya geçidi bölgesinde _detect_dead_end Yöntem-2 yanlış
                # tetiklenebilir (near-ROI beyaz dolu, fwd-ROI boş görünür).
                _state       = 'YAYA_GECİDİ'
                _state_timer = now
                motor.brake()

            elif events['hemzemin']:
                # Hemzemin geçit — kural 3.4.4: ≥30 cm mesafede dur, ≥5 s bekle.
                # Aynı şekilde dead_end'den önce kontrol edilmeli.
                _state       = 'HEMZEMIN'
                _state_timer = now
                motor.brake()

            elif events['speed_bump']:
                # Hız tümsek — kural 3.4.3: yavaşlayarak tümsek üzerinden geç
                _state       = 'TUMSEK'
                _state_timer = now

            elif events['dead_end']:
                # Çıkmaz yol — kural 3.4.6: girme, sağa tank dönüşü yap.
                # Kendi parametreleri (DEAD_END_TURN_*) kullanılır.
                _state       = 'CIKMAZ_YOL'
                _state_timer = now
                motor.set_speed(*_apply_dir(DEAD_END_TURN_SPEED, -DEAD_END_TURN_SPEED))

            elif events['orange_car'] and not events['yellow_car']:
                # Turuncu araç VE sarı araç YOK → sollama serbest bölgesi,
                # kural 3.4.5 gereği geç. Sarı araç görünüyorsa sollama yasağı
                # bölgesindeyiz, manevra yapma.
                _state       = 'SOLLAMA'
                _state_timer = now
                _ovt_phase   = 0

            elif events['parking_zone']:
                # Park bölgesi — kural 3.4.7: kırmızı slota park et
                _state = 'PARK'
                controller.reset()

            else:
                # Normal sürüş: PD denetleyici ile şerit merkezi takibi
                l, r = controller.compute(error)
                motor.set_speed(*_apply_dir(l, r))

        elif _state == 'BEKLIYOR':
            # Yarış başlamadan önceki bekleme durumu.
            # Kural 3.4.1: Trafik ışığı yeşile dönünce ≤3 saniye içinde hareket et.
            # İlk denemede doğru başlangıç → 50 puan; ikinci denemede → 25 puan.
            motor.brake()
            if light == 'green':
                _state = 'SURUYOR'
                controller.reset()
                print("[main] Yeşil ışık algılandı — HAREKET! (Kural 3.4.1)")

        elif _state == 'KIRMIZI_ISIK':
            motor.brake()
            if light == 'green':
                _state = 'SURUYOR'
                controller.reset()

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
            l, r  = controller.compute(error)
            denom = max(abs(l), abs(r), 1)
            scale = SPEED_BUMP_SPEED / denom
            motor.set_speed(*_apply_dir(l * scale, r * scale))
            if now - _state_timer >= SPEED_BUMP_SLOW_SEC:
                _state = 'SURUYOR'
                controller.reset()

        elif _state == 'CIKMAZ_YOL':
            # Kural 3.4.6: Çıkmaz yola GİRMEDEN sağa dön.
            # Tank dönüşü: sol tekerlek ileri (+hız), sağ tekerlek geri (-hız).
            # DEAD_END_TURN_SEC ve DEAD_END_TURN_SPEED config.py'den ayarlanır.
            motor.set_speed(*_apply_dir(DEAD_END_TURN_SPEED, -DEAD_END_TURN_SPEED))
            if now - _state_timer >= DEAD_END_TURN_SEC:
                _state = 'SURUYOR'
                controller.reset()

        elif _state == 'SOLLAMA':
            _run_overtaking(error, now)

        elif _state == 'PARK':
            _run_parking(frame, error)

        elif _state == 'PARK_TAMAM':
            motor.brake()   # yarış bitti, sabit kal

        _cur_state = _state
        _cur_error = error   # web API'sine anlık hata değerini aktar

        # ---- Kayıt ve yayın --------------------------------------------
        logger.update(error)
        if not args.no_stream:
            composite = _build_stream_frame(frame, debug, error, events, _state)
            # picamera2 RGB888 → composite RGB → BGR dönüşümü → imencode → tarayıcı ✓
            # Renk kanalları yanlışsa config.py → CAMERA_BGR_OUTPUT = True deneyin.
            ret, buf = cv2.imencode(
                '.jpg',
                cv2.cvtColor(composite, cv2.COLOR_RGB2BGR),
                [cv2.IMWRITE_JPEG_QUALITY, 82],
            )
            if ret:
                with _frame_lock:
                    _latest_frame = buf.tobytes()


# ---------------------------------------------------------------------------
# Sollama alt durum makinesi  (3 aşamalı açık döngü manevra)
# ---------------------------------------------------------------------------
def _run_overtaking(error, now: float) -> None:
    """Aşama 0 (CROSS_SEC):  Sola steer — zıt şeride geç.
       Aşama 1 (PASS_SEC):   Normal sürüş — turuncu aracın yanından geç.
       Aşama 2 (RETURN_SEC): Sağa steer — orijinal şeride dön.
    """
    global _state, _ovt_phase, _state_timer

    elapsed = now - _state_timer

    if _ovt_phase == 0:
        eff_error = (error or 0) - OVERTAKING_STEER_BIAS
        l, r = controller.compute(eff_error)
        scale = OVERTAKING_SPEED / max(abs(l), abs(r), 1)
        motor.set_speed(*_apply_dir(l * scale, r * scale))
        if elapsed >= OVERTAKING_CROSS_SEC:
            _ovt_phase   = 1
            _state_timer = now

    elif _ovt_phase == 1:
        l, r = controller.compute(error)
        scale = OVERTAKING_SPEED / max(abs(l), abs(r), 1)
        motor.set_speed(*_apply_dir(l * scale, r * scale))
        if elapsed >= OVERTAKING_PASS_SEC:
            _ovt_phase   = 2
            _state_timer = now

    elif _ovt_phase == 2:
        eff_error = (error or 0) + OVERTAKING_STEER_BIAS
        l, r = controller.compute(eff_error)
        scale = OVERTAKING_SPEED / max(abs(l), abs(r), 1)
        motor.set_speed(*_apply_dir(l * scale, r * scale))
        if elapsed >= OVERTAKING_RETURN_SEC:
            _state     = 'SURUYOR'
            _ovt_phase = 0
            controller.reset()


# ---------------------------------------------------------------------------
# Park etme yardımcısı
# ---------------------------------------------------------------------------
def _run_parking(frame: np.ndarray, error) -> None:
    """Kırmızı park slotuna yönel ve içine gir."""
    global _state

    hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
    roi = hsv[PARKING_ROI_TOP:, :]

    m1 = cv2.inRange(roi, np.array(PARKING_HSV_LOW1,  dtype=np.uint8),
                          np.array(PARKING_HSV_HIGH1, dtype=np.uint8))
    m2 = cv2.inRange(roi, np.array(PARKING_HSV_LOW2,  dtype=np.uint8),
                          np.array(PARKING_HSV_HIGH2, dtype=np.uint8))
    red_mask = cv2.bitwise_or(m1, m2)

    cnts, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    best_cx   = None
    best_area = 0.0
    for c in cnts:
        area = cv2.contourArea(c)
        if area > best_area:
            best_area = area
            M = cv2.moments(c)
            if M['m00'] > 0:
                best_cx = int(M['m10'] / M['m00'])

    if best_area < PARKING_MIN_AREA or best_cx is None:
        # Kırmızı slot görünmüyor — şerit takibe devam et
        l, r = controller.compute(error)
        scale = PARKING_SPEED / max(abs(l), abs(r), 1)
        motor.set_speed(*_apply_dir(l * scale, r * scale))
        return

    # Kırmızı blob'un yatay merkezine doğru yönel
    off = best_cx - (WIDTH // 2)
    if abs(off) <= PARKING_CENTER_TOL and best_area > PARKING_MIN_AREA * 4:
        motor.brake()
        _state = 'PARK_TAMAM'
        return

    steer     = float(off) * 0.3
    l         = PARKING_SPEED + steer
    r         = PARKING_SPEED - steer
    motor.set_speed(*_apply_dir(l, r))


# ---------------------------------------------------------------------------
# Yön yardımcısı
# ---------------------------------------------------------------------------
def _apply_dir(left: float, right: float) -> tuple:
    """_flipped True ise motorları ters çevir (araç ters bağlanmışsa)."""
    if _flipped:
        return -right, -left
    return left, right


# ---------------------------------------------------------------------------
# Stream kare oluşturucu
# ---------------------------------------------------------------------------
_INSET_W = 213
_INSET_H = 120

_STATE_COLORS = {
    'BEKLIYOR':    (180, 180, 180),  # gri  — yeşil ışık bekleniyor
    'SURUYOR':     (100, 255, 100),  # yeşil — normal sürüş
    'KIRMIZI_ISIK':(255,   0,   0),  # kırmızı — dur
    'YAYA_GECİDİ': (255, 200,   0),  # sarı  — yaya geçidi bekleme
    'HEMZEMIN':    (  0, 180, 255),  # açık mavi — hemzemin bekleme
    'TUMSEK':      (255, 165,   0),  # turuncu — yavaş geç
    'CIKMAZ_YOL':  (255,  50,   0),  # kırmızı-turuncu — sağa dön
    'SOLLAMA':     (  0, 255, 128),  # açık yeşil — sollama manevra
    'PARK':        (  0, 220, 255),  # cyan — park arama
    'PARK_TAMAM':  ( 50, 255,  50),  # parlak yeşil — tamamlandı
}


def _build_stream_frame(cam_frame, bird_debug, error, events, state) -> np.ndarray:
    out = event_detector.debug_frame(cam_frame, events)

    err_str = f"hata:{error:+d}px" if error is not None else "hata:--"
    cv2.putText(out, err_str, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (230, 230, 0), 2)

    scol = _STATE_COLORS.get(state, (200, 200, 200))
    cv2.putText(out, state, (10, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.8, scol, 2)

    dir_label = "YON: TERS"   if _flipped else "YON: ILERI"
    dir_color = (255, 80,  0) if _flipped else (100, 255, 100)
    cv2.putText(out, dir_label, (10, 88), cv2.FONT_HERSHEY_SIMPLEX, 0.6, dir_color, 2)

    if error is None and state == 'SURUYOR':
        cv2.putText(out, "SERIT YOK", (WIDTH // 2 - 70, HEIGHT // 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.1, (255, 0, 0), 3)

    if bird_debug is not None:
        inset = cv2.resize(bird_debug, (_INSET_W, _INSET_H))
        x0 = WIDTH  - _INSET_W - 4
        y0 = HEIGHT - _INSET_H - 4
        out[y0:y0 + _INSET_H, x0:x0 + _INSET_W] = inset
        cv2.rectangle(out, (x0 - 1, y0 - 1), (x0 + _INSET_W, y0 + _INSET_H),
                      (200, 200, 200), 1)
    return out


# ---------------------------------------------------------------------------
# Flask web arayüzü  (yalnızca --no-stream kullanılmadığında aktif)
# ---------------------------------------------------------------------------
if not args.no_stream:
    from flask import Flask, Response, jsonify

    app = Flask(__name__)

    # ---- MJPEG kare üreteci ------------------------------------------------
    def _gen_frames():
        """Sonsuz MJPEG kare akışı üretir."""
        while True:
            with _frame_lock:
                data = _latest_frame
            if data is None:
                time.sleep(0.04)
                continue
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + data + b'\r\n')
            time.sleep(0.033)   # ~30 fps sınırı

    # ---- /  — Ana dashboard sayfası ----------------------------------------
    @app.route('/')
    def index():
        # Statik HTML döndürülür; canlı veri JavaScript ile /api/status'tan çekilir.
        return """<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Otonom Araç — Kontrol Paneli</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: 'Segoe UI', system-ui, sans-serif;
    background: #0d1117; color: #c9d1d9;
    min-height: 100vh; padding: 12px;
  }
  /* ---- başlık ---- */
  .header {
    display: flex; align-items: center; gap: 14px;
    background: #161b22; border: 1px solid #30363d;
    border-radius: 10px; padding: 10px 18px; margin-bottom: 12px;
  }
  .header h1 { font-size: 1.2em; font-weight: 700; color: #e6edf3; flex: 1; }
  .state-badge {
    font-size: 0.95em; font-weight: 700; padding: 5px 16px;
    border-radius: 20px; background: #21262d; border: 2px solid #30363d;
    min-width: 130px; text-align: center; transition: color 0.3s, border-color 0.3s;
  }
  .error-chip {
    font-size: 0.85em; font-family: monospace;
    background: #21262d; border: 1px solid #30363d;
    border-radius: 8px; padding: 4px 12px;
  }
  /* ---- ana ızgara ---- */
  .grid {
    display: grid;
    grid-template-columns: 1fr 280px;
    gap: 12px;
  }
  @media (max-width: 900px) { .grid { grid-template-columns: 1fr; } }
  /* ---- kamera paneli ---- */
  .cam-panel {
    background: #161b22; border: 1px solid #30363d;
    border-radius: 10px; overflow: hidden;
  }
  .cam-panel img {
    width: 100%; display: block;
    image-rendering: auto;
  }
  .cam-legend {
    font-size: 0.75em; color: #6e7681;
    padding: 6px 12px; border-top: 1px solid #21262d;
  }
  /* ---- sağ panel ---- */
  .side-panel {
    display: flex; flex-direction: column; gap: 12px;
  }
  .card {
    background: #161b22; border: 1px solid #30363d;
    border-radius: 10px; padding: 14px;
  }
  .card-title {
    font-size: 0.78em; font-weight: 600; letter-spacing: .06em;
    color: #8b949e; text-transform: uppercase; margin-bottom: 10px;
  }
  /* ---- olay göstergesi ---- */
  .event-row {
    display: flex; align-items: center; gap: 10px;
    padding: 5px 0; border-bottom: 1px solid #21262d;
  }
  .event-row:last-child { border-bottom: none; }
  .dot {
    width: 11px; height: 11px; border-radius: 50%;
    background: #30363d; flex-shrink: 0;
    transition: background 0.2s, box-shadow 0.2s;
  }
  .dot.active {
    background: var(--clr);
    box-shadow: 0 0 8px var(--clr);
  }
  .event-label { font-size: 0.88em; }
  .event-sub { font-size: 0.75em; color: #6e7681; margin-left: auto; }
  /* ---- trafik ışığı ---- */
  .tl-row { display: flex; gap: 8px; margin-bottom: 6px; align-items: center; }
  .tl-dot {
    width: 22px; height: 22px; border-radius: 50%;
    background: #21262d; border: 2px solid #30363d;
    transition: background .3s, box-shadow .3s;
  }
  .tl-dot.lit-red   { background: #e53935; box-shadow: 0 0 12px #e5393599; }
  .tl-dot.lit-green { background: #43a047; box-shadow: 0 0 12px #43a04799; }
  /* ---- direksiyon göstergesi ---- */
  .steer-wrap { margin-top: 6px; }
  .steer-bar-bg {
    height: 8px; background: #21262d;
    border-radius: 4px; position: relative; overflow: hidden;
  }
  .steer-bar-fill {
    position: absolute; top: 0; height: 100%;
    background: #58a6ff; border-radius: 4px;
    transition: left .1s, width .1s;
  }
  .steer-labels { display:flex; justify-content:space-between; font-size:.7em; color:#6e7681; margin-top:3px; }
  /* ---- kontrol butonları ---- */
  .btn {
    display: block; width: 100%;
    padding: 8px; margin-bottom: 6px;
    border: none; border-radius: 7px; cursor: pointer;
    font-size: 0.9em; font-weight: 600; color: #fff;
    transition: opacity .2s;
  }
  .btn:last-child { margin-bottom: 0; }
  .btn:hover { opacity: .85; }
  .btn-green  { background: #238636; }
  .btn-red    { background: #b91c1c; }
  .btn-blue   { background: #1d4ed8; }
  .btn-purple { background: #7c3aed; }
  /* ---- bağlantı durumu ---- */
  .conn-dot {
    display: inline-block; width:8px; height:8px;
    border-radius:50%; background:#6e7681; margin-right:5px;
    transition: background .5s;
  }
  .conn-dot.ok { background: #3fb950; }
</style>
</head>
<body>

<!-- Başlık çubuğu -->
<div class="header">
  <h1>&#129302; Otonom Araç — MEB 2026</h1>
  <span class="error-chip" id="error-chip">Hata: ??</span>
  <span class="state-badge" id="state-badge">---</span>
</div>

<!-- Ana ızgara -->
<div class="grid">

  <!-- Kamera akışı -->
  <div class="cam-panel">
    <img id="feed" src="/video_feed" alt="Kamera akışı">
    <div class="cam-legend">
      Yeşil çizgi = şerit kenarları &nbsp;|&nbsp;
      Kırmızı çizgi = şerit merkezi &nbsp;|&nbsp;
      Mavi çizgi = görüntü merkezi
    </div>
  </div>

  <!-- Sağ panel -->
  <div class="side-panel">

    <!-- Trafik ışığı -->
    <div class="card">
      <div class="card-title">Trafik Işığı</div>
      <div class="tl-row">
        <div class="tl-dot" id="tl-red"   title="Kırmızı"></div>
        <div class="tl-dot" id="tl-green" title="Yeşil"></div>
        <span id="tl-label" style="font-size:.9em; margin-left:4px; color:#8b949e">—</span>
      </div>
    </div>

    <!-- Algılanan olaylar -->
    <div class="card">
      <div class="card-title">Algılanan Olaylar</div>

      <div class="event-row">
        <div class="dot" id="ev-crosswalk" style="--clr:#fbbf24" title="Yaya Geçidi"></div>
        <span class="event-label">Yaya Geçidi</span>
        <span class="event-sub">≥5 s dur</span>
      </div>
      <div class="event-row">
        <div class="dot" id="ev-hemzemin" style="--clr:#38bdf8" title="Hemzemin Geçit"></div>
        <span class="event-label">Hemzemin Geçit</span>
        <span class="event-sub">≥5 s dur</span>
      </div>
      <div class="event-row">
        <div class="dot" id="ev-speed_bump" style="--clr:#fb923c" title="Hız Tümsek"></div>
        <span class="event-label">Hız Tümsek</span>
        <span class="event-sub">yavaşla</span>
      </div>
      <div class="event-row">
        <div class="dot" id="ev-orange_car" style="--clr:#f97316" title="Turuncu Araç"></div>
        <span class="event-label">Turuncu Araç</span>
        <span class="event-sub">solla</span>
      </div>
      <div class="event-row">
        <div class="dot" id="ev-yellow_car" style="--clr:#facc15" title="Sarı Araç"></div>
        <span class="event-label">Sarı Araç</span>
        <span class="event-sub">yasak bölge</span>
      </div>
      <div class="event-row">
        <div class="dot" id="ev-dead_end" style="--clr:#ef4444" title="Çıkmaz Yol"></div>
        <span class="event-label">Çıkmaz Yol</span>
        <span class="event-sub">sağa dön</span>
      </div>
      <div class="event-row">
        <div class="dot" id="ev-parking_zone" style="--clr:#a855f7" title="Park Bölgesi"></div>
        <span class="event-label">Park Bölgesi</span>
        <span class="event-sub">kırmızı slot</span>
      </div>
      <div class="event-row">
        <div class="dot" id="ev-sign_blue" style="--clr:#60a5fa" title="Mavi Levha"></div>
        <span class="event-label">Mavi Levha</span>
        <span class="event-sub">P / T işareti</span>
      </div>
    </div>

    <!-- Direksiyon göstergesi -->
    <div class="card">
      <div class="card-title">Direksiyon / Yanal Hata</div>
      <div class="steer-wrap">
        <div class="steer-bar-bg">
          <div class="steer-bar-fill" id="steer-fill" style="left:50%;width:2px;"></div>
        </div>
        <div class="steer-labels"><span>&#8592; Sol</span><span>Merkez</span><span>Sağ &#8594;</span></div>
      </div>
      <div style="text-align:center; margin-top:6px; font-size:.85em; font-family:monospace;" id="error-val">0 px</div>
    </div>

    <!-- Kontrol butonları -->
    <div class="card">
      <div class="card-title">Kontroller</div>
      <button class="btn btn-blue"   id="btn-flip"  onclick="doFlip()">&#8646; Yön Değiştir</button>
      <button class="btn btn-purple" onclick="doAction('/park')">&#128663; Park Moduna Geç</button>
      <button class="btn btn-green"  onclick="doAction('/start')">&#9654; Sürmeye Başla</button>
      <button class="btn btn-red"    onclick="doAction('/reset')">&#8635; Denetleyici Sıfırla</button>
    </div>

    <!-- Bağlantı durumu -->
    <div style="font-size:.78em; color:#6e7681; padding:4px 2px;">
      <span class="conn-dot" id="conn-dot"></span>
      <span id="conn-label">Bağlanıyor...</span>
      &nbsp;|&nbsp; <span id="fps-label">-- fps</span>
    </div>

  </div><!-- side-panel -->
</div><!-- grid -->

<script>
// ---------------------------------------------------------------------------
// Renk haritası — durum makinesi durumlarına karşılık gelen CSS renkleri
// ---------------------------------------------------------------------------
const STATE_COLORS = {
  'BEKLIYOR':    '#6e7681',
  'SURUYOR':     '#3fb950',
  'KIRMIZI_ISIK':'#f85149',
  'YAYA_GECİDİ': '#e3b341',
  'HEMZEMIN':    '#58a6ff',
  'TUMSEK':      '#fb8f44',
  'CIKMAZ_YOL':  '#f78166',
  'SOLLAMA':     '#56d364',
  'PARK':        '#79c0ff',
  'PARK_TAMAM':  '#3fb950',
};

let lastUpdate = 0;
let frameCount = 0;
let fpsTimer = 0;

// ---------------------------------------------------------------------------
// /api/status endpoint'ini sorgula ve arayüzü güncelle
// ---------------------------------------------------------------------------
function fetchStatus() {
  fetch('/api/status')
    .then(r => r.ok ? r.json() : null)
    .then(data => {
      if (!data) return;
      updateState(data.state);
      updateTrafficLight(data.traffic_light);
      updateEvents(data.events);
      updateError(data.error);
      // Bağlantı göstergesi
      document.getElementById('conn-dot').className = 'conn-dot ok';
      document.getElementById('conn-label').textContent =
        'Bağlı — ' + new Date().toLocaleTimeString('tr-TR');
      lastUpdate = Date.now();
    })
    .catch(() => {
      document.getElementById('conn-dot').className = 'conn-dot';
      document.getElementById('conn-label').textContent = 'Bağlantı yok';
    });
}

function updateState(state) {
  const badge = document.getElementById('state-badge');
  const color = STATE_COLORS[state] || '#8b949e';
  badge.textContent = state || '---';
  badge.style.color = color;
  badge.style.borderColor = color + '55';
}

function updateTrafficLight(light) {
  document.getElementById('tl-red').className   = 'tl-dot' + (light === 'red'   ? ' lit-red'   : '');
  document.getElementById('tl-green').className = 'tl-dot' + (light === 'green' ? ' lit-green' : '');
  const labels = { red: 'KIRMIZI', green: 'YEŞİL', null: '—' };
  document.getElementById('tl-label').textContent = labels[light] || '—';
}

function updateEvents(events) {
  const keys = ['crosswalk','hemzemin','speed_bump','orange_car',
                'yellow_car','dead_end','parking_zone','sign_blue'];
  for (const k of keys) {
    const dot = document.getElementById('ev-' + k);
    if (dot) {
      dot.className = 'dot' + (events[k] ? ' active' : '');
    }
  }
}

function updateError(err) {
  const chip  = document.getElementById('error-chip');
  const val   = document.getElementById('error-val');
  const fill  = document.getElementById('steer-fill');
  if (err === null || err === undefined) {
    chip.textContent = 'Hata: --';
    val.textContent  = '-- px';
    fill.style.left  = '50%';
    fill.style.width = '2px';
    return;
  }
  // Hata +/- 200px aralığında normalize et
  const clamp = Math.max(-200, Math.min(200, err));
  const pct   = 50 + (clamp / 200) * 50;   // 0–100 %
  const w     = Math.abs(clamp) / 200 * 50; // genişlik
  const left  = clamp >= 0 ? 50 : pct;
  fill.style.left  = left + '%';
  fill.style.width = Math.max(2, w) + '%';
  chip.textContent = 'Hata: ' + (err >= 0 ? '+' : '') + Math.round(err) + ' px';
  val.textContent  = (err >= 0 ? '+' : '') + Math.round(err) + ' px';
}

// ---------------------------------------------------------------------------
// Kontrol buton aksiyonları
// ---------------------------------------------------------------------------
function doFlip() {
  fetch('/flip').then(() => {
    const btn = document.getElementById('btn-flip');
    btn.textContent = btn.textContent.includes('İLERİ') ? '⇆ İLERİ Moda Dön' : '⇆ Yön Değiştir';
  });
}

function doAction(url) {
  fetch(url).catch(() => {});
}

// ---------------------------------------------------------------------------
// Başlat: 250 ms'de bir durum güncelle
// ---------------------------------------------------------------------------
setInterval(fetchStatus, 250);
fetchStatus();
</script>
</body>
</html>"""

    # ---- /api/status — JSON durum endpoint'i --------------------------------
    @app.route('/api/status')
    def api_status():
        """Anlık durum, olaylar ve direksiyon hatasını JSON olarak döndürür.

        Döndürür:
            state         : str   — mevcut durum makinesi durumu
            error         : float | null — piksel cinsinden yanal hata
            traffic_light : str | null  — 'red' | 'green' | null
            events        : dict  — bool değerli olay sözlüğü
            direction     : str   — 'ILERI' | 'TERS'
        """
        evts = dict(_cur_events)
        light = evts.pop('traffic_light', None)
        data = {
            'state':         _cur_state,
            'error':         _cur_error,
            'traffic_light': light,
            'direction':     'TERS' if _flipped else 'ILERI',
            'events':        {k: bool(v) for k, v in evts.items()},
        }
        return jsonify(data)

    # ---- /flip  — yön değiştir ----------------------------------------------
    @app.route('/flip')
    def flip_direction():
        global _flipped
        _flipped = not _flipped
        controller.reset()
        motor.brake()
        return ('', 204)

    # ---- /park  — park moduna geç -------------------------------------------
    @app.route('/park')
    def enter_parking():
        global _state
        _state = 'PARK'
        controller.reset()
        return ('', 204)

    # ---- /start — BEKLIYOR durumunu atla (test için) ------------------------
    @app.route('/start')
    def manual_start():
        """Web arayüzünden manuel başlatma — yalnızca test modu için.
        NOT: Yarış sırasında bu endpoint KAPALI olmalı (kural 2.3).
        """
        global _state
        if _state == 'BEKLIYOR':
            _state = 'SURUYOR'
            controller.reset()
        return ('', 204)

    # ---- /reset — denetleyici sıfırla ---------------------------------------
    @app.route('/reset')
    def reset_controller():
        controller.reset()
        return ('', 204)

    # ---- /video_feed — MJPEG akışı ------------------------------------------
    @app.route('/video_feed')
    def video_feed():
        return Response(_gen_frames(),
                        mimetype='multipart/x-mixed-replace; boundary=frame')


# ---------------------------------------------------------------------------
# Düzgün kapatma
# ---------------------------------------------------------------------------
def _shutdown(sig, frame) -> None:
    global _running
    print("\n[main] Kapatılıyor...")
    _running = False
    motor.stop()
    logger.finish()
    camera.stop()
    sys.exit(0)


signal.signal(signal.SIGINT,  _shutdown)
signal.signal(signal.SIGTERM, _shutdown)


# ---------------------------------------------------------------------------
# Giriş noktası
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    # Başlangıç butonu (yarışta +50 bonus puan — kural 3.4.1).
    # Araç harici bilgisayar bağlantısı olmadan buton ile başlatılabiliyorsa
    # 50 ek ödül puanı verilir.
    if _USE_PICAMERA:
        try:
            from gpiozero import Button as _StartBtn
            _btn = _StartBtn(START_BUTTON_PIN)
            print(f"[main] GPIO{START_BUTTON_PIN}'de başlangıç butonu bekleniyor...")
            _btn.wait_for_press()
            print("[main] Buton basıldı — BAŞLA!")
        except Exception as _e:
            print(f"[main] Başlangıç butonu kullanılamıyor ({_e}), trafik ışığı bekleniyor.")

    print("[main] Sürüş thread'i başlatılıyor...")
    t = threading.Thread(target=drive_loop, daemon=True)
    t.start()

    if args.no_stream:
        print("[main] --no-stream modu: Wi-Fi yayını devre dışı (yarış modu).")
        print("[main] Durdurmak için Ctrl+C.")
        while _running:
            time.sleep(1)
    else:
        print("[main] http://0.0.0.0:5000 adresinde web yayını başlatılıyor")
        app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)