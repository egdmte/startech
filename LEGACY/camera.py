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

            # HSV bilgisi
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            cx, cy = cursor["x"], cursor["y"]
            h, s, v = hsv[cy, cx]
            cv2.putText(
                frame,
                f"HSV ({cx},{cy}): H={h} S={s} V={v}",
                (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 230, 230), 2,
            )
            cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)

            if show_bird or show_thresh:
                _, debug_rgb = detector.process(frame_rgb)
                display = cv2.cvtColor(debug_rgb, cv2.COLOR_RGB2BGR)
            else:
                display = frame

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
