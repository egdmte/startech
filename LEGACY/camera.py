# =============================================================================
# camera.py  —  Ayar / tanılama için canlı kamera görüntüleyici
#
# Gösterir:
#   - İmleç altındaki pikselin HSV değeri
#   - İkili beyaz-şerit eşik katmanı ('t' ile aç/kapat)
#   - Kuş bakışı perspektif eğriltmesi ('b' ile aç/kapat)
#
# 'q' → çık
# =============================================================================
import time

import cv2

from config import WIDTH, HEIGHT
from lane import LaneDetector


def main() -> int:
    picam2 = None
    usb_camera = None
    try:
        try:
            from picamera2 import Picamera2
            picam2 = Picamera2()
            cfg = picam2.create_preview_configuration(
                main={"size": (WIDTH, HEIGHT), "format": "RGB888"}
            )
            picam2.configure(cfg)
            picam2.start()
            time.sleep(2)
            print("Kamera: Picamera2")
        except Exception as pi_error:
            if picam2 is not None:
                try:
                    picam2.close()
                except Exception:
                    pass
                picam2 = None
            usb_camera = cv2.VideoCapture(0)
            if not usb_camera.isOpened():
                usb_camera.release()
                raise RuntimeError(
                    f"Pi kamera ve USB kamera açılamadı (Pi: {pi_error})"
                ) from pi_error
            usb_camera.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
            usb_camera.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)
            print("Kamera: USB / VideoCapture")

        detector = LaneDetector()
        cursor = {"x": WIDTH // 2, "y": HEIGHT // 2}

        def on_mouse(event, x, y, flags, param):
            if event == cv2.EVENT_MOUSEMOVE:
                cursor["x"], cursor["y"] = x, y

        cv2.namedWindow("Kamera")
        cv2.setMouseCallback("Kamera", on_mouse)

        show_thresh = False
        show_bird = False

        print("Kontroller: 't' = eşik | 'b' = kuş bakışı | 'q' = çık")

        while True:
            if picam2 is not None:
                frame_rgb = picam2.capture_array()
            else:
                ok, frame = usb_camera.read()
                if not ok:
                    raise RuntimeError("USB kamera kare üretemedi")
                frame = cv2.resize(frame, (WIDTH, HEIGHT))
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)

            # LEGACY-006: 't' ve 'b' artik detector.process()'in TEK
            # donen degeri olan (tam açıklamalı) `debug` görüntüsünü
            # PAYLAŞMIYOR. Her mod, lane.py'nin şimdi açıkça sunduğu
            # (LEGACY-005/006 düzeltmesi) AYRI, ADLANDIRILMIŞ bir çıktıyı
            # gösterir:
            #   ham (raw)  -> orijinal kare
            #   'b' kuş bakışı -> detector.last_bird_proc (CLAHE sonrası,
            #                     açıklamasız kuş bakışı — GERÇEK dönüşüm)
            #   't' eşik   -> detector.last_mask (GERÇEK ikili 0/255 maske)
            if show_bird or show_thresh:
                _, _debug_rgb = detector.process(frame_rgb)   # yan etki: last_* alanları doldurur
                if show_thresh:
                    display = cv2.cvtColor(detector.last_mask, cv2.COLOR_GRAY2BGR)
                    mode_hsv_source = detector.last_bird_hsv   # eşiği üreten UZAY
                    mode_label = "ESIK (kuş-bakışı HSV)"
                else:  # show_bird
                    display = cv2.cvtColor(detector.last_bird_proc, cv2.COLOR_RGB2BGR)
                    mode_hsv_source = detector.last_bird_hsv
                    mode_label = "KUŞ BAKIŞI (CLAHE sonrası)"
            else:
                display = frame
                mode_hsv_source = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                mode_label = "HAM"

            # LEGACY-005: İmleç HER ZAMAN GÖSTERİLEN görüntünün kendi
            # koordinat uzayından örneklenir — ham kareden DEĞİL. Eski
            # kod kuş-bakışı/eşik modunda bile daima HAM kareyi
            # örnekliyordu; bu, gösterilen pikselin GERÇEK HSV'siyle
            # HİÇBİR İLGİSİ olmayan bir okuma üretiyordu (farklı
            # koordinat/perspektif uzayı). Sınırlar da GÖSTERİLEN
            # görüntünün GERÇEK boyutuna göre kırpılır (kuş-bakışı,
            # ham kareden daha kısa olabilir).
            disp_h, disp_w = display.shape[:2]
            cx = max(0, min(cursor["x"], disp_w - 1))
            cy = max(0, min(cursor["y"], disp_h - 1))
            h, s, v = mode_hsv_source[cy, cx]
            cv2.putText(
                display,
                f"[{mode_label}] HSV ({cx},{cy}): H={h} S={s} V={v}",
                (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 230, 230), 2,
            )
            cv2.circle(display, (cx, cy), 5, (0, 0, 255), -1)

            cv2.imshow("Kamera", display)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('t'):
                show_thresh = not show_thresh
                show_bird   = False
            elif key == ord('b'):
                show_bird   = not show_bird
                show_thresh = False

        return 0
    except Exception as exc:
        print(f"[camera.py] HATA: {exc}")
        return 1
    finally:
        try:
            if picam2 is not None:
                try:
                    picam2.stop()
                finally:
                    close = getattr(picam2, "close", None)
                    if close is not None:
                        close()
            if usb_camera is not None:
                usb_camera.release()
        finally:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    raise SystemExit(main())
