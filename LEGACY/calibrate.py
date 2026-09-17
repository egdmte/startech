# =============================================================================
# calibrate.py  —  Perspektif eğriltme interaktif kalibrasyon aracı
#                  (Raspberry Pi / Picamera2 sürümü)
#
# Dört yeşil tutacağı kamera görüntüsündeki yol trapezoidinin köşelerine sürükle.
# ENTER'a bas → config.py'ye yapıştırmaya hazır PERSP_SRC değerlerini yazdırır.
# 'q' → kaydetmeden çık.
#
# Nokta sırası:  sol-üst, sağ-üst, sol-alt, sağ-alt
# =============================================================================
import cv2
import numpy as np
from config import WIDTH, HEIGHT, PERSP_SRC, validate_perspective_quad

try:
    from picamera2 import Picamera2
    _USE_PI = True
except ImportError:
    _USE_PI = False

POINT_RADIUS   = 8
POINT_COLOR    = (0, 255, 0)
SELECTED_COLOR = (0, 0, 255)
LINE_COLOR     = (255, 200, 0)


def draw_overlay(frame: np.ndarray, pts: list, selected: int) -> np.ndarray:
    vis   = frame.copy()
    order = [0, 1, 3, 2, 0]   # kapalı dörtgen çiz
    for i in range(len(order) - 1):
        p1 = tuple(pts[order[i]])
        p2 = tuple(pts[order[i + 1]])
        cv2.line(vis, p1, p2, LINE_COLOR, 1)
    for i, (x, y) in enumerate(pts):
        color = SELECTED_COLOR if i == selected else POINT_COLOR
        cv2.circle(vis, (x, y), POINT_RADIUS, color, -1)
        cv2.putText(vis, str(i), (x + 10, y - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
    cv2.putText(vis, "Noktaları sürükle | ENTER=doğrula/yazdır | q=çık",
                (8, HEIGHT - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    return vis


def main():
    # Kamera başlat (Pi veya USB)
    picam2 = None
    cap = None
    if _USE_PI:
        try:
            import time
            picam2 = Picamera2()
            cfg = picam2.create_preview_configuration(
                main={"format": "RGB888", "size": (WIDTH, HEIGHT)}
            )
            picam2.configure(cfg)
            picam2.start()
            time.sleep(1)
        except Exception as exc:
            print(f"Pi kamera açılamadı, USB deneniyor: {exc}")
            if picam2 is not None:
                try:
                    picam2.close()
                except Exception:
                    pass
            picam2 = None

    if picam2 is not None:
        def _get_frame():
            f = picam2.capture_array()
            return cv2.cvtColor(f, cv2.COLOR_RGB2BGR)
        def _stop():
            try:
                picam2.stop()
            finally:
                close = getattr(picam2, "close", None)
                if close is not None:
                    close()
        cam_label = "Pi Camera"
    else:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            cap.release()
            raise RuntimeError("USB kamera açılamadı")
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)
        def _get_frame():
            ret, f = cap.read()
            if not ret:
                raise RuntimeError("USB kamera kare üretemedi")
            return f
        def _stop():
            cap.release()
        cam_label = "USB Camera"

    # LEGACY-001: Kamera SORUMLULUK SINIRI artik ACILDIGI ANDAN itibaren
    # TEK bir try/finally ile korunur. Eski kodda pencere/callback kurulumu
    # (namedWindow, setMouseCallback, pts listesi olusturma) kamerayi
    # koruyan try/finally'nin DISINDA kalıyordu — bu adimlardan biri
    # (ornegin GUI kurulumu, Ctrl+C) istisna atarsa kamera KAPATILMADAN
    # yayilıyordu. Simdi acilistan sonraki HER SEY bu blogun icinde.
    try:
        pts      = [list(p) for p in PERSP_SRC]
        selected = -1
        dragging = False

        def on_mouse(event, x, y, flags, param):
            nonlocal selected, dragging
            if event == cv2.EVENT_LBUTTONDOWN:
                dists = [abs(x - p[0]) + abs(y - p[1]) for p in pts]
                idx   = int(np.argmin(dists))
                if dists[idx] < POINT_RADIUS * 3:
                    selected = idx
                    dragging = True
            elif event == cv2.EVENT_MOUSEMOVE and dragging:
                # LEGACY-004: np.clip Python int degil NumPy SKALER
                # dondurur (NumPy 2.x'te np.int64). int() ile ACIKCA
                # Python builtin'e cevir — aksi halde bu sayilar pts
                # icinde TASINIR ve export anindaki int() donusumune
                # kadar NumPy tipinde kalirdi (export zaten donusturuyor,
                # ama kaynakta da temiz tutmak hatasiz).
                pts[selected] = [int(np.clip(x, 0, WIDTH - 1)),
                                int(np.clip(y, 0, HEIGHT - 1))]
            elif event == cv2.EVENT_LBUTTONUP:
                dragging = False

        cv2.namedWindow(f"Kalibrasyon ({cam_label})")
        cv2.setMouseCallback(f"Kalibrasyon ({cam_label})", on_mouse)

        print(f"Kamera: {cam_label}")
        print("Dört köşe tutacağını şerit sınırlarına sürükleyin.")
        print("Nokta sırası:  0=sol-üst  1=sağ-üst  2=sol-alt  3=sağ-alt")
        print("ENTER = doğrula ve yazdır (KAYDETMEZ), 'q' = çık.")

        while True:
            frame = _get_frame()
            if frame.shape[1] != WIDTH or frame.shape[0] != HEIGHT:
                frame = cv2.resize(frame, (WIDTH, HEIGHT))

            vis = draw_overlay(frame, pts, selected if dragging else -1)
            cv2.imshow(f"Kalibrasyon ({cam_label})", vis)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("Kalibrasyon iptal edildi.")
                break
            elif key in (13, 10):   # ENTER
                # LEGACY-003: Eski kod noktalari yalnizca SURUKLEME
                # sirasinda kare sinirlarina KIRPIYORDU (np.clip); ENTER'da
                # HICBIR geometrik gecerlilik kontrolu yoktu. Cakisik,
                # dogrusal, kendini kesen ya da ters (ust/alt karismis)
                # bir dortgen SESSIZCE yazdirilip config.py'ye
                # yapistirilmaya hazir sunulabiliyordu — dejenere/ters bir
                # homografi aktif serit girdisini BOZAR. Simdi export
                # ANINDA ayni geometrik kontrol calisir; gecersizse
                # REDDEDILIR, SON GECERLI nokta seti korunur.
                _problems = validate_perspective_quad(
                    [[int(x), int(y)] for x, y in pts], WIDTH, HEIGHT)
                if _problems:
                    print("\n❌ GEÇERSİZ dörtgen — KAYDEDİLMEDİ:")
                    for _p in _problems:
                        print(f"   - {_p}")
                    print("   Köşeleri düzeltip tekrar ENTER'a basın.")
                else:
                    print("\n# Bunu config.py'ye yapıştır:")
                    print(f"PERSP_SRC = {[[int(x), int(y)] for x, y in pts]}")
                    break
    finally:
        # LEGACY-001: IC ICE finally — kamera kapatma basarisiz olsa BILE
        # pencere temizligi yine de DENENIR (biri digerini engellemez).
        try:
            _stop()
        finally:
            try:
                cv2.destroyAllWindows()
            except Exception:
                pass


if __name__ == "__main__":
    main()
