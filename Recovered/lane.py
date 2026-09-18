# =============================================================================
# lane.py  —  Kuş bakışı perspektif dönüşümü ile çift beyaz şerit dedektörü
#             + ADAPTIF HSV + Şerit Kalitesi Kontrolü
# =============================================================================
import cv2
import numpy as np

from config import (
    WIDTH, HEIGHT, ROI_TOP_RATIO, PERSP_SRC,
    MIN_LANE_SIGNAL, ASSUMED_LANE_WIDTH,
    WHITE_HSV_LOW, WHITE_HSV_HIGH,
    WHITE_HSV_LOW_DARK, WHITE_HSV_HIGH_DARK,
    WHITE_HSV_LOW_NORMAL, WHITE_HSV_HIGH_NORMAL,
    WHITE_HSV_LOW_BRIGHT, WHITE_HSV_HIGH_BRIGHT,
    LANE_MEMORY_FRAMES, LANE_SEARCH_WINDOW,
    MIN_LANE_SIGNAL_QUALITY_RATIO,
)


class LaneDetector:
    """Kuş bakışı görünümünde sol ve sağ beyaz şerit çizgilerini bulur,
    aralarındaki orta noktanın yanal hatasını döndürür.

    hata > 0  →  şerit merkezi kare merkezinin SOLunda  →  sola dön
    hata < 0  →  şerit merkezi kare merkezinin SAĞında  →  sağa dön
    """

    def __init__(self):
        self.bird_w = WIDTH
        self.bird_h = int(HEIGHT * (1.0 - ROI_TOP_RATIO))
        self.mid    = self.bird_w // 2

        src = np.float32(PERSP_SRC)
        dst = np.float32([
            [0,           0],
            [self.bird_w, 0],
            [0,           self.bird_h],
            [self.bird_w, self.bird_h],
        ])
        self.M    = cv2.getPerspectiveTransform(src, dst)
        self.Minv = cv2.getPerspectiveTransform(dst, src)

        # Şerit konumu hafızası: (son_sütun, son_görüldükten_bu_yana_kare)
        self._left_mem:  tuple | None = None
        self._right_mem: tuple | None = None

        # Morfoloji kernel'i (3×3 — ince bant çizgilerini korur)
        self._kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))

    # ------------------------------------------------------------------
    def process(self, frame: np.ndarray) -> tuple:
        """RGB kareyi işler.

        Döndürür
        --------
        error : int | None
        debug : np.ndarray  — açıklamalı kuş bakışı görüntüsü (RGB)
        """
        # 1. Kuş bakışı perspektif dönüşümü
        bird = cv2.warpPerspective(frame, self.M, (self.bird_w, self.bird_h))

        # 2. Beyaz piksel maskesi (HSV tabanlı) — ADAPTIF HSV
        hsv  = cv2.cvtColor(bird, cv2.COLOR_RGB2HSV)
        
        # Parlaklık ortalamasını hesapla (V kanalı)
        v_mean = np.mean(hsv[:, :, 2])
        
        # Parlaklığa göre HSV aralığını seç
        if v_mean < 100:
            # Karanlık ortam
            white_low = np.array(WHITE_HSV_LOW_DARK, dtype=np.uint8)
            white_high = np.array(WHITE_HSV_HIGH_DARK, dtype=np.uint8)
        elif v_mean > 200:
            # Parlak ortam
            white_low = np.array(WHITE_HSV_LOW_BRIGHT, dtype=np.uint8)
            white_high = np.array(WHITE_HSV_HIGH_BRIGHT, dtype=np.uint8)
        else:
            # Normal ortam
            white_low = np.array(WHITE_HSV_LOW_NORMAL, dtype=np.uint8)
            white_high = np.array(WHITE_HSV_HIGH_NORMAL, dtype=np.uint8)
        
        mask = cv2.inRange(hsv, white_low, white_high)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN,  self._kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, self._kernel)

        # 3. Sütun histogramı (Gauss yumuşatmalı)
        histogram = np.sum(mask, axis=0).astype(np.float32)
        histogram = cv2.GaussianBlur(
            histogram.reshape(1, -1), (1, 31), 0
        ).flatten()

        # 4. Arama penceresiyle tepe bulma
        left_peak,  left_seen  = self._find_peak(
            histogram, 0, self.mid,
            self._left_mem[0]  if self._left_mem  else None,
        )
        right_peak, right_seen = self._find_peak(
            histogram, self.mid, self.bird_w,
            self._right_mem[0] if self._right_mem else None,
        )

        # 5. Şerit hafızası güncelleme
        left_valid  = self._update_memory('left',  left_peak,  left_seen)
        right_valid = self._update_memory('right', right_peak, right_seen)

        if left_valid:
            left_peak  = self._left_mem[0]
        if right_valid:
            right_peak = self._right_mem[0]

        # 6. Şerit merkezi ve hata hesabı
        if left_valid and right_valid:
            lane_center = (left_peak + right_peak) // 2
        elif left_valid:
            lane_center = left_peak + ASSUMED_LANE_WIDTH // 2
        elif right_valid:
            lane_center = right_peak - ASSUMED_LANE_WIDTH // 2
        else:
            return None, self._blank_debug(bird, mask)

        lane_center = int(np.clip(lane_center, 0, self.bird_w - 1))
        error = self.mid - lane_center

        # 7. Debug görüntüsü
        debug = self._draw_debug(bird, mask, left_peak, right_peak,
                                 left_valid, right_valid, lane_center, error, v_mean)
        return error, debug

    # ------------------------------------------------------------------
    def _update_memory(self, side: str, peak: int, seen: bool) -> bool:
        """Hafızayı günceller; şerit hâlâ geçerliyse True döndürür."""
        attr = f'_{side}_mem'
        if seen:
            setattr(self, attr, (peak, 0))
            return True
        mem = getattr(self, attr)
        if mem is not None:
            col, age = mem
            if age < LANE_MEMORY_FRAMES:
                setattr(self, attr, (col, age + 1))
                return True
            setattr(self, attr, None)
        return False

    # ------------------------------------------------------------------
    def _find_peak(self, histogram: np.ndarray,
                   lo: int, hi: int,
                   last_known: int | None) -> tuple:
        """[lo, hi) aralığında ağırlıklı ağırlık merkezi tepe noktasını bulur.

        last_known belirtilmişse arama penceresi daraltılır.
        (tepe_sütunu, geçerli_mi) döndürür.
        """
        if last_known is not None:
            w_lo = max(lo, last_known - LANE_SEARCH_WINDOW)
            w_hi = min(hi, last_known + LANE_SEARCH_WINDOW)
        else:
            w_lo, w_hi = lo, hi

        region = histogram[w_lo:w_hi]
        total  = float(region.sum())

        if total < MIN_LANE_SIGNAL:
            # Dar pencerede bulunamadı — tam yarıya bak
            region = histogram[lo:hi]
            total  = float(region.sum())
            if total < MIN_LANE_SIGNAL:
                fallback = last_known if last_known is not None else (lo + hi) // 2
                return fallback, False
            centroid = int(np.average(np.arange(lo, hi), weights=region))
        else:
            centroid = int(np.average(np.arange(w_lo, w_hi), weights=region))

        return int(np.clip(centroid, lo, hi - 1)), True

    # ------------------------------------------------------------------
    def _draw_debug(self, bird, mask, lp, rp,
                    lv, rv, center, error, v_mean=0) -> np.ndarray:
        debug = cv2.addWeighted(bird, 0.6,
                                cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB), 0.4, 0)
        h = self.bird_h
        if lv:
            cv2.line(debug, (lp, 0), (lp, h), (0, 220, 0), 2)
        if rv:
            cv2.line(debug, (rp, 0), (rp, h), (0, 220, 0), 2)
        cv2.line(debug, (center,   0), (center,   h), (255,  60,  0), 2)
        cv2.line(debug, (self.mid, 0), (self.mid, h), (  0,  80, 255), 1)
        
        # Hata ve parlaklık bilgisi
        cv2.putText(debug, f"err:{error:+d}px  V:{v_mean:.0f}", (8, 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (230, 230, 0), 2)
        label = ("Sol+Sağ" if (lv and rv) else
                 "Yalnız Sol" if lv else "Yalnız Sağ")
        cv2.putText(debug, label, (8, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.50, (0, 200, 200), 1)
        return debug

    # ------------------------------------------------------------------
    def _blank_debug(self, bird: np.ndarray, mask: np.ndarray) -> np.ndarray:
        debug = cv2.addWeighted(bird, 0.6,
                                cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB), 0.4, 0)
        cv2.putText(debug, "SERIT YOK",
                    (self.bird_w // 2 - 70, self.bird_h // 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 0, 0), 2)
        return debug