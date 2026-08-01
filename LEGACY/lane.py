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
    CLAHE_CLIP_LIMIT, CLAHE_TILE_SIZE, LANE_CONTINUITY_RATIO,
    LANE_FAR_RATIO, LANE_NEAR_RATIO, LANE_FAR_WEIGHT, LANE_NEAR_WEIGHT,
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

        # CLAHE: spot ışık / zemin yansımalarını normalize eder
        self._clahe = cv2.createCLAHE(
            clipLimit=CLAHE_CLIP_LIMIT,
            tileGridSize=(CLAHE_TILE_SIZE, CLAHE_TILE_SIZE),
        )

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

        # 2. CLAHE: L kanalında yerel kontrast eşitleme (yansıma/spot ışık direnci)
        #    Spot yansımalar CLAHE sonrası normalize olur; şerit çizgileri korunur.
        lab = cv2.cvtColor(bird, cv2.COLOR_RGB2LAB)
        l_ch, a_ch, b_ch = cv2.split(lab)
        l_eq = self._clahe.apply(l_ch)
        bird_proc = cv2.cvtColor(cv2.merge([l_eq, a_ch, b_ch]), cv2.COLOR_LAB2RGB)

        # 3. Beyaz piksel maskesi (HSV tabanlı) — ADAPTİF HSV
        hsv  = cv2.cvtColor(bird_proc, cv2.COLOR_RGB2HSV)

        # Parlaklık ortalamasını hesapla (V kanalı — CLAHE sonrası)
        v_mean = np.mean(hsv[:, :, 2])

        # Parlaklığa göre HSV aralığını seç
        if v_mean < 100:
            white_low  = np.array(WHITE_HSV_LOW_DARK,   dtype=np.uint8)
            white_high = np.array(WHITE_HSV_HIGH_DARK,  dtype=np.uint8)
        elif v_mean > 200:
            white_low  = np.array(WHITE_HSV_LOW_BRIGHT,  dtype=np.uint8)
            white_high = np.array(WHITE_HSV_HIGH_BRIGHT, dtype=np.uint8)
        else:
            white_low  = np.array(WHITE_HSV_LOW_NORMAL,  dtype=np.uint8)
            white_high = np.array(WHITE_HSV_HIGH_NORMAL, dtype=np.uint8)

        mask = cv2.inRange(hsv, white_low, white_high)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN,  self._kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, self._kernel)

        # 4. Sütun sürekliliği ağırlığı (yansıma filtresi)
        #    Şerit çizgileri kuş bakışında dikey yönde süreklidir.
        #    Noktasal yansımalar yalnızca birkaç satırı etkiler → ağırlık düşer.
        col_cov = (mask > 0).sum(axis=0).astype(np.float32)
        min_cov = max(float(self.bird_h) * LANE_CONTINUITY_RATIO, 1.0)
        continuity_w = np.minimum(col_cov / min_cov, 1.0)

        # 5. Yakın / uzak dilim histogramları
        #    Uzak  (üst LANE_FAR_RATIO)  → dönüş tahmini / look-ahead
        #    Yakın (alt LANE_NEAR_RATIO) → anlık yanal konum / ortalama
        near_rows  = int(self.bird_h * LANE_NEAR_RATIO)
        far_rows   = int(self.bird_h * LANE_FAR_RATIO)
        near_start = self.bird_h - near_rows

        def _slice_hist(m):
            h = np.sum(m, axis=0).astype(np.float32) * continuity_w
            return cv2.GaussianBlur(h.reshape(1, -1), (1, 31), 0).flatten()

        near_hist = _slice_hist(mask[near_start:])
        far_hist  = _slice_hist(mask[:far_rows])

        # 6. Tepe bulma — yakın: hafıza destekli  |  uzak: serbest look-ahead
        near_lp, near_ls = self._find_peak(
            near_hist, 0, self.mid,
            self._left_mem[0]  if self._left_mem  else None)
        near_rp, near_rs = self._find_peak(
            near_hist, self.mid, self.bird_w,
            self._right_mem[0] if self._right_mem else None)
        far_lp, far_ls = self._find_peak(far_hist, 0,        self.mid,    None)
        far_rp, far_rs = self._find_peak(far_hist, self.mid, self.bird_w, None)

        # 7. Hafıza güncelleme (yakın bölge — daha kararlı)
        left_valid  = self._update_memory('left',  near_lp, near_ls)
        right_valid = self._update_memory('right', near_rp, near_rs)

        if left_valid:  near_lp = self._left_mem[0]
        if right_valid: near_rp = self._right_mem[0]

        # 8. Ağırlıklı hata — yakın (anlık ortalama) + uzak (dönüş tahmini)
        def _center(lp, lv, rp, rv):
            if lv and rv:  return (lp + rp) // 2
            elif lv:       return lp + ASSUMED_LANE_WIDTH // 2
            elif rv:       return rp - ASSUMED_LANE_WIDTH // 2
            return None

        near_c = _center(near_lp, left_valid, near_rp, right_valid)
        far_c  = _center(far_lp,  far_ls,     far_rp,  far_rs)

        if near_c is None and far_c is None:
            return None, self._blank_debug(bird, mask)
        elif near_c is None:
            error = self.mid - int(far_c)
        elif far_c is None:
            error = self.mid - int(near_c)
        else:
            error = int(LANE_NEAR_WEIGHT * (self.mid - near_c)
                       + LANE_FAR_WEIGHT  * (self.mid - far_c))

        lane_center = int(np.clip(self.mid - error, 0, self.bird_w - 1))

        # 9. Debug görüntüsü
        debug = self._draw_debug(bird_proc, mask, near_lp, near_rp,
                                 left_valid, right_valid, lane_center, error, v_mean,
                                 far_lp if far_ls else None, far_rp if far_rs else None)
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
                    lv, rv, center, error, v_mean=0,
                    far_lp=None, far_rp=None) -> np.ndarray:
        debug = cv2.addWeighted(bird, 0.6,
                                cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB), 0.4, 0)
        h     = self.bird_h
        far_h = int(h * LANE_FAR_RATIO)  # uzak görüş çizgileri üst bölgede
        if lv:
            cv2.line(debug, (lp, 0), (lp, h), (0, 220, 0), 2)
        if rv:
            cv2.line(debug, (rp, 0), (rp, h), (0, 220, 0), 2)
        if far_lp is not None:
            cv2.line(debug, (far_lp, 0), (far_lp, far_h), (0, 200, 220), 1)
        if far_rp is not None:
            cv2.line(debug, (far_rp, 0), (far_rp, far_h), (0, 200, 220), 1)
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

    # ------------------------------------------------------------------
    def update_clahe(self, clip: float, tile: int) -> None:
        """Çalışma zamanında CLAHE parametrelerini günceller (tune.py için)."""
        self._clahe = cv2.createCLAHE(
            clipLimit=float(clip),
            tileGridSize=(int(tile), int(tile)),
        )