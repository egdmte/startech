#!/usr/bin/env python3
# =============================================================================
# yol_takip.py  —  SADECE ŞERİT TAKİBİ (olay tespiti YOK)
#
# Bu dosya main.py'nin BASİTLEŞTİRİLMİŞ versiyonudur:
# - ✅ Şerit takibi (PD denetleyici + adaptif HSV)
# - ✅ Motor kontrolü
# - ✅ Kamera görüntüsü
# - ❌ Trafik ışığı YOK
# - ❌ Yaya geçidi YOK
# - ❌ Hemzemin geçit YOK
# - ❌ Hız tümsek YOK
# - ❌ Çıkmaz yol YOK
# - ❌ Sollama YOK
# - ❌ Park YOK
#
# Sadece pist üzerinde şerit takibi test etmek için.
#
# Kullanım:
#   python yol_takip.py            (test modu - GG/EZ ile başlat)
#   python yol_takip.py --auto     (otomatik başlat - hemen hareket et)
#   python yol_takip.py --no-stream (Flask yayını olmadan)
# =============================================================================
import argparse
import select
import signal
import sys
import threading
import time

import cv2
import numpy as np

# Kamera: Pi'de picamera2, geliştirme için OpenCV
try:
    from picamera2 import Picamera2
    _USE_PICAMERA = True
except ImportError:
    _USE_PICAMERA = False
    print("[yol_takip] picamera2 bulunamadı — OpenCV VideoCapture kullanılıyor")

from config import WIDTH, HEIGHT, CAMERA_BGR_OUTPUT
from controller import PDController
from lane import LaneDetector
from logger import ErrorLogger
from motor import MotorDriver

# ---------------------------------------------------------------------------
# Komut satırı argümanları
# ---------------------------------------------------------------------------
parser = argparse.ArgumentParser(description='Otonom Araç - SADECE ŞERİT TAKİBİ')
parser.add_argument('--no-stream', action='store_true',
                    help='Flask MJPEG yayınını devre dışı bırak')
parser.add_argument('--auto', action='store_true',
                    help='GG/EZ beklemeden hemen başla (otomatik mod)')
args = parser.parse_args()


# ---------------------------------------------------------------------------
# Kamera sınıfı
# ---------------------------------------------------------------------------
class Camera:
    """Pi kamerası veya USB kamerasını yönetir."""
    
    def __init__(self):
        if _USE_PICAMERA:
            self.cam = Picamera2()
            self.cam.configure(self.cam.create_preview_configuration(
                main={"size": (WIDTH, HEIGHT), "format": "RGB888"}
            ))
            self.cam.start()
            time.sleep(1)
            print("[yol_takip] Pi kamerası açıldı")
        else:
            self.cam = cv2.VideoCapture(0)
            self.cam.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
            self.cam.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)
            print("[yol_takip] USB kamera açıldı")
    
    def capture(self) -> np.ndarray:
        """Kameradan bir kare al (RGB formatında)."""
        if _USE_PICAMERA:
            frame = self.cam.capture_array()
            # BGR ↔ RGB düzeltme (kamera ayarına göre)
            if CAMERA_BGR_OUTPUT:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            return frame
        else:
            ret, frame = self.cam.read()
            if not ret:
                return np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
            # OpenCV BGR döner, RGB'ye çevir
            return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    def close(self):
        if _USE_PICAMERA:
            self.cam.stop()
        else:
            self.cam.release()


# ---------------------------------------------------------------------------
# Global durum
# ---------------------------------------------------------------------------
_running = True
_started = args.auto  # --auto bayrağıyla hemen başla
_latest_frame: np.ndarray | None = None
_cur_error: float | None = None
_fps = 0.0


# ---------------------------------------------------------------------------
# Sürüş döngüsü
# ---------------------------------------------------------------------------
def drive_loop():
    """Ana sürüş döngüsü — sadece şerit takibi."""
    global _latest_frame, _running, _started, _cur_error, _fps
    
    print("[yol_takip] Sürüş döngüsü başladı")
    
    # Klavye buffer
    _input_buffer = ""
    
    # FPS hesabı
    fps_counter = 0
    fps_start = time.time()
    
    while _running:
        # 1. Kameradan kare al
        frame = camera.capture()
        
        # 2. Şerit tespit
        error, debug = lane_detector.process(frame)
        _cur_error = error
        
        # 3. Klayvye girdisi (GG veya EZ ile başla)
        if not _started:
            if sys.stdin in select.select([sys.stdin], [], [], 0.001)[0]:
                try:
                    ch = sys.stdin.read(1).upper()
                    _input_buffer += ch
                    
                    if len(_input_buffer) >= 2:
                        last_two = _input_buffer[-2:]
                        if last_two == "GG" or last_two == "EZ":
                            print(f"\n[KLAYVYE] '{last_two}' yazıldı — ŞERİT TAKİBİ BAŞLATILIYOR!")
                            _started = True
                            controller.reset()
                            _input_buffer = ""
                except:
                    pass
        
        # 4. Motor kontrolü
        if _started:
            # Şerit takibi — PD denetleyici
            l, r = controller.compute(error)
            motor.set_speed(l, r)
            
            # Hata logla (CSV'ye)
            #
            # DUZELTILDI 5 Agustos 2026 — burada UC ayri hata vardi ve ucu birlikte
            # 20.7 deneyini tamamen olcusuz birakiyordu:
            #
            #  1. logger.log(...) diye bir metot YOK. ErrorLogger'da update() ve
            #     finish() var (logger.py'nin kendi ornek kullanimi da oyle diyor).
            #     Serit ilk bulundugu karede AttributeError ile cokuyordu.
            #  2. Imza da yanlisti: update yalnizca error alir, (error, l, r) degil.
            #  3. 'if error is not None' korumasi, KAYIP kareleri logger'a hic
            #     ulastirmiyordu. Oysa kayip kare sayaci tam olarak update(None)
            #     ile artiyor — yani "kayip serit yuzdesi" her zaman %0 cikardi.
            #     20.7'nin okumamizi istedigi ilk sayi budur.
            logger.update(error)   # None DA gonderilir; kayip kareyi o sayar
        else:
            # Henüz başlamadı — durur
            motor.brake()
        
        # 5. Debug görüntüsünü kaydet (web yayını için)
        _latest_frame = debug
        
        # 6. FPS hesabı
        fps_counter += 1
        if fps_counter >= 30:
            now = time.time()
            _fps = fps_counter / (now - fps_start)
            fps_counter = 0
            fps_start = now
            
            # Konsola yazdır
            if _started:
                err_str = f"{error:+d}" if error is not None else "None"
                print(f"\r[yol_takip] FPS: {_fps:.1f} | Hata: {err_str}px | "
                      f"Sol: {motor._left_pwm.value*100:.0f}% | "
                      f"Sağ: {motor._right_pwm.value*100:.0f}%", end='', flush=True)
    
    print("\n[yol_takip] Sürüş döngüsü durdu")


# ---------------------------------------------------------------------------
# Flask web sunucu (debug için)
# ---------------------------------------------------------------------------
def setup_flask():
    """MJPEG yayını için Flask sunucu kur."""
    try:
        from flask import Flask, Response, render_template_string
    except ImportError:
        print("[yol_takip] Flask kurulu değil — yayın devre dışı")
        return None
    
    app = Flask(__name__)
    
    HTML = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Yol Takip - Debug</title>
        <style>
            body { 
                background: #1a1a1a; 
                color: #fff; 
                font-family: monospace;
                padding: 20px; 
                margin: 0;
            }
            h1 { color: #4ade80; }
            .info { 
                background: #2a2a2a; 
                padding: 15px; 
                border-radius: 8px;
                margin-bottom: 20px;
            }
            img { 
                max-width: 100%; 
                border: 2px solid #4ade80;
                border-radius: 8px;
            }
            .stat { 
                display: inline-block; 
                margin-right: 20px;
                padding: 5px 10px;
                background: #333;
                border-radius: 4px;
            }
        </style>
    </head>
    <body>
        <h1>🚗 Yol Takip — Debug Yayını</h1>
        <div class="info">
            <span class="stat">Mod: SADECE ŞERİT TAKİBİ</span>
            <span class="stat" id="fps">FPS: --</span>
            <span class="stat" id="err">Hata: --</span>
            <span class="stat" id="status">Durum: --</span>
        </div>
        <img src="/stream" />
        
        <script>
            setInterval(async () => {
                const r = await fetch('/api/status');
                const d = await r.json();
                document.getElementById('fps').textContent = 'FPS: ' + d.fps.toFixed(1);
                document.getElementById('err').textContent = 'Hata: ' + (d.error !== null ? d.error.toFixed(0) + 'px' : '--');
                document.getElementById('status').textContent = 'Durum: ' + (d.started ? '🟢 SÜRÜYOR' : '🔴 BEKLIYOR (GG yaz)');
            }, 200);
        </script>
    </body>
    </html>
    """
    
    @app.route('/')
    def index():
        return render_template_string(HTML)
    
    @app.route('/stream')
    def stream():
        def generate():
            while _running:
                if _latest_frame is None:
                    time.sleep(0.05)
                    continue
                # RGB → BGR dönüştür (cv2 için)
                frame_bgr = cv2.cvtColor(_latest_frame, cv2.COLOR_RGB2BGR)
                ret, jpg = cv2.imencode('.jpg', frame_bgr,
                                         [cv2.IMWRITE_JPEG_QUALITY, 70])
                if ret:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' +
                           jpg.tobytes() + b'\r\n')
                time.sleep(0.033)  # ~30 FPS
        
        return Response(generate(),
                       mimetype='multipart/x-mixed-replace; boundary=frame')
    
    @app.route('/api/status')
    def api_status():
        return {
            'fps': float(_fps),
            'error': float(_cur_error) if _cur_error is not None else None,
            'started': _started,
        }
    
    return app


# ---------------------------------------------------------------------------
# Ana program
# ---------------------------------------------------------------------------
def _shutdown(sig, frame):
    """Ctrl+C ile temiz çıkış."""
    global _running
    print("\n[yol_takip] Kapatılıyor...")
    _running = False
    motor.brake()
    time.sleep(0.5)
    motor.stop()
    camera.close()
    # Eklendi 5 Agustos 2026: finish() hicbir yerde cagrilmiyordu, yani
    # stabilite raporu da CSV de asla uretilmiyordu. 20.7 adim 3 "raporu oku"
    # diyor; okunacak rapor yoktu.
    try:
        logger.finish()
        controller.tani_raporu()
    except Exception as _e:
        print("[yol_takip] Rapor uretilemedi: %s" % _e)
    sys.exit(0)


signal.signal(signal.SIGINT, _shutdown)
signal.signal(signal.SIGTERM, _shutdown)


if __name__ == "__main__":
    # Tüm bileşenleri başlat
    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║   🚗 YOL TAKİP — BASİT SİSTEMİ 🚗                        ║")
    print("║                                                          ║")
    print("║   Sadece şerit takibi (olay tespiti yok)                ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()
    
    print("[yol_takip] Bileşenler başlatılıyor...")
    
    camera         = Camera()
    lane_detector  = LaneDetector()
    controller     = PDController()
    motor          = MotorDriver()
    logger         = ErrorLogger()
    
    print("[yol_takip] ✅ Tüm bileşenler hazır")
    print()
    
    if args.auto:
        print("[yol_takip] 🚀 OTOMATİK MOD — Hemen başlıyor!")
        _started = True
    else:
        print("[yol_takip] BAŞLAMA YÖNTEMİ:")
        print("[yol_takip]   • Konsola 'GG' veya 'EZ' yazın → Araç başlar")
        print("[yol_takip]   • Ctrl+C → Durdurmak için")
    
    print()
    print("[yol_takip] Sürüş thread'i başlatılıyor...")
    
    # Sürüş döngüsünü ayrı thread'de başlat
    t = threading.Thread(target=drive_loop, daemon=True)
    t.start()
    
    # Flask sunucusu (eğer istenirse)
    if args.no_stream:
        print("[yol_takip] --no-stream modu: Web yayını kapalı")
        print("[yol_takip] Durdurmak için Ctrl+C")
        try:
            while _running:
                time.sleep(1)
        except KeyboardInterrupt:
            _shutdown(None, None)
    else:
        app = setup_flask()
        if app:
            print("[yol_takip] 🌐 Web yayını: http://0.0.0.0:5000")
            print("[yol_takip] Tarayıcıdan açabilirsiniz (debug için)")
            print()
            try:
                app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
            except KeyboardInterrupt:
                _shutdown(None, None)
        else:
            print("[yol_takip] Flask yok, sadece konsol modu")
            try:
                while _running:
                    time.sleep(1)
            except KeyboardInterrupt:
                _shutdown(None, None)
