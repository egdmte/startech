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

try:
    import msvcrt
except ImportError:
    msvcrt = None

try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass

# Kamera: Pi'de picamera2, USB/Windows tarafında OpenCV
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
from motor import MotorDriver, MotorHardwareUnavailable

def parse_args(argv=None):
    """Komut satırını yalnızca program gerçekten çalıştırıldığında oku."""
    parser = argparse.ArgumentParser(description='Otonom Araç - SADECE ŞERİT TAKİBİ')
    parser.add_argument('--no-stream', action='store_true',
                        help='Flask MJPEG yayınını devre dışı bırak')
    parser.add_argument('--auto', action='store_true',
                        help='GG/EZ beklemeden hemen başla (otomatik mod)')
    return parser.parse_args(argv)


# ---------------------------------------------------------------------------
# Kamera sınıfı
# ---------------------------------------------------------------------------
class Camera:
    """Pi kamerası veya USB kamerasını yönetir."""
    
    def __init__(self):
        self.cam = None
        if _USE_PICAMERA:
            self.cam = Picamera2()
            try:
                self.cam.configure(self.cam.create_preview_configuration(
                    main={"size": (WIDTH, HEIGHT), "format": "RGB888"}
                ))
                self.cam.start()
                time.sleep(1)
            except BaseException:
                try:
                    self.cam.close()
                except Exception:
                    pass
                raise
            print("[yol_takip] Pi kamerası açıldı")
        else:
            self.cam = cv2.VideoCapture(0)
            if not self.cam.isOpened():
                self.cam.release()
                raise RuntimeError("USB kamera açılamadı")
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
                raise RuntimeError("USB kamera kare üretemedi")
            # OpenCV BGR döner, RGB'ye çevir
            return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    def close(self):
        if _USE_PICAMERA:
            try:
                self.cam.stop()
            finally:
                close = getattr(self.cam, "close", None)
                if close is not None:
                    close()
        else:
            self.cam.release()


# ---------------------------------------------------------------------------
# Global durum
# ---------------------------------------------------------------------------
_running = True
_started = False
_latest_frame: np.ndarray | None = None
_cur_error: float | None = None
_fps = 0.0
camera = None
lane_detector = None
controller = None
motor = None
logger = None
_cleanup_done = False
_worker_failed = False


def read_key_nonblocking() -> str:
    """Windows veya POSIX terminalinden varsa tek karakter oku."""
    if msvcrt is not None:
        return msvcrt.getwch() if msvcrt.kbhit() else ""
    try:
        if sys.stdin in select.select([sys.stdin], [], [], 0.001)[0]:
            return sys.stdin.read(1)
    except (OSError, ValueError):
        return ""
    return ""


# ---------------------------------------------------------------------------
# Sürüş döngüsü
# ---------------------------------------------------------------------------
def drive_loop():
    """Ana sürüş döngüsü — sadece şerit takibi."""
    global _latest_frame, _started, _cur_error, _fps
    
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
            ch = read_key_nonblocking().upper()
            if ch:
                _input_buffer += ch

                if len(_input_buffer) >= 2:
                    last_two = _input_buffer[-2:]
                    if last_two in ("GG", "EZ"):
                        print(
                            f"\n[KLAVYE] '{last_two}' yazıldı — "
                            "ŞERİT TAKİBİ BAŞLATILIYOR!"
                        )
                        _started = True
                        controller.reset()
                        _input_buffer = ""
        
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
            motor.coast()
        
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


def guarded_drive_loop():
    """Sürüş thread'i çökerse son PWM komutunu taşımadan motoru durdur."""
    global _running, _worker_failed
    try:
        drive_loop()
    except Exception as exc:
        import traceback
        print(f"\n[yol_takip] SÜRÜŞ HATASI: {exc}")
        traceback.print_exc()
        _worker_failed = True
        _running = False
    finally:
        if motor is not None:
            try:
                motor.stop()
            except Exception as exc:
                print(f"[yol_takip] Acil motor kapatma hatası: {exc}")


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
def _shutdown(sig=None, frame=None):
    """Ctrl+C ile temiz çıkış."""
    global _running, _cleanup_done
    if _cleanup_done:
        if sig is not None:
            raise SystemExit(128 + int(sig))
        return
    _cleanup_done = True
    print("\n[yol_takip] Kapatılıyor...")
    _running = False
    if motor is not None:
        try:
            motor.stop()
        except Exception as exc:
            print(f"[yol_takip] Motor kapatma hatası: {exc}")
    if camera is not None:
        try:
            camera.close()
        except Exception as exc:
            print(f"[yol_takip] Kamera kapatma hatası: {exc}")
    # Eklendi 5 Agustos 2026: finish() hicbir yerde cagrilmiyordu, yani
    # stabilite raporu da CSV de asla uretilmiyordu. 20.7 adim 3 "raporu oku"
    # diyor; okunacak rapor yoktu.
    if logger is not None:
        try:
            logger.finish()
        except Exception as exc:
            print(f"[yol_takip] Logger kapatma hatası: {exc}")
    if controller is not None:
        try:
            controller.tani_raporu()
        except Exception as exc:
            print(f"[yol_takip] Denetleyici raporu üretilemedi: {exc}")
    if sig is not None:
        raise SystemExit(128 + int(sig))


def main(argv=None) -> int:
    global camera, lane_detector, controller, motor, logger
    global _started, _running, _cleanup_done, _worker_failed
    global _latest_frame, _cur_error, _fps

    _running = True
    _cleanup_done = False
    _worker_failed = False
    _started = False
    _latest_frame = None
    _cur_error = None
    _fps = 0.0
    args = parse_args(argv)
    exit_code = 0

    # Tüm bileşenleri başlat
    try:
        signal.signal(signal.SIGINT, _shutdown)
        signal.signal(signal.SIGTERM, _shutdown)
        print()
        print("╔══════════════════════════════════════════════════════════╗")
        print("║   🚗 YOL TAKİP — BASİT SİSTEMİ 🚗                        ║")
        print("║                                                          ║")
        print("║   Sadece şerit takibi (olay tespiti yok)                ║")
        print("╚══════════════════════════════════════════════════════════╝")
        print()

        print("[yol_takip] Bileşenler başlatılıyor...")

        motor = MotorDriver()
        motor.require_hardware()
        camera = Camera()
        lane_detector = LaneDetector()
        controller = PDController()
        logger = ErrorLogger()

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

        t = threading.Thread(target=guarded_drive_loop, daemon=True)
        t.start()

        if args.no_stream:
            print("[yol_takip] --no-stream modu: Web yayını kapalı")
            print("[yol_takip] Durdurmak için Ctrl+C")
            while _running:
                time.sleep(1)
        else:
            app = setup_flask()
            if app:
                print("[yol_takip] 🌐 Web yayını: http://0.0.0.0:5000")
                print("[yol_takip] Tarayıcıdan açabilirsiniz (debug için)")
                print()
                from werkzeug.serving import make_server
                server = make_server('0.0.0.0', 5000, app)
                server.timeout = 0.5
                try:
                    while _running:
                        server.handle_request()
                finally:
                    server.server_close()
            else:
                print("[yol_takip] Flask yok, sadece konsol modu")
                while _running:
                    time.sleep(1)
        if _worker_failed:
            exit_code = 1
    except MotorHardwareUnavailable as exc:
        exit_code = 1
        print(f"[yol_takip] BAŞLATILAMADI: {exc}")
    except KeyboardInterrupt:
        exit_code = 1 if _worker_failed else 130
    except Exception as exc:
        import traceback
        exit_code = 1
        print(f"[yol_takip] FATAL HATA: {exc}")
        traceback.print_exc()
    finally:
        _shutdown()

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
