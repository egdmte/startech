# =============================================================================
# lane.py  —  Kuş bakışı perspektif dönüşümü ile çift beyaz şerit dedektörü
#             + ADAPTIF HSV + Şerit Kalitesi Kontrolü
# =============================================================================
import cv2
import numpy as np
import time

from config import (
    WIDTH, HEIGHT, ROI_TOP_RATIO, PERSP_SRC,
    MIN_LANE_SIGNAL, ASSUMED_LANE_WIDTH,
    WHITE_HSV_LOW_DARK, WHITE_HSV_HIGH_DARK,
    WHITE_HSV_LOW_NORMAL, WHITE_HSV_HIGH_NORMAL,
    WHITE_HSV_LOW_BRIGHT, WHITE_HSV_HIGH_BRIGHT,
    LANE_MEMORY_FRAMES, LANE_SEARCH_WINDOW,
    MIN_LANE_SIGNAL_QUALITY_RATIO,
    LANE_PEAK_CONTRAST_MIN, LANE_MAX_OCCUPANCY, LANE_MIN_PEAK_WIDTH,
    LANE_DUAL_PEAK_MIN_SEP,
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

        # LEGACY-039: GOZLEM durumu, tahmin edilen hatadan AYRI tutulur.
        # Tuketici (main) boylece "gercek serit gozlemi ne zaman kayboldu"
        # sorusunu, onbellekten uretilen sayisal hataya bakmadan
        # cevaplayabilir ve guvenlik zamanlayicisini dogru anda baslatir.
        self.lane_observed: bool = False
        self.left_observed: bool = False
        self.right_observed: bool = False
        self.frames_since_observation: int = 0
        self._last_observation_time: float | None = None

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
            # LEGACY-037: OpenCV cekirdek sirasi (genislik, yukseklik).
            # (1, 31) bir SATIRLIK eksene 31 piksellik cekirdek uyguluyordu,
            # yani islem tamamen etkisizdi (bit-for-bit ayni histogram).
            # Sutunlar boyunca yumusatma icin cekirdek (31, 1) olmali.
            return cv2.GaussianBlur(h.reshape(1, -1), (31, 1), 0).flatten()

        near_hist = _slice_hist(mask[near_start:])
        far_hist  = _slice_hist(mask[:far_rows])

        # --- LEGACY-038 ------------------------------------------------
        # Sabit sol/sag yari bolumlemesi, her iki gercek sinir da ayni
        # yariya dustugunde (keskin viraj / buyuk yanal kayma) ikisini
        # TEK sinir gibi ortaliyor ve karsi tarafa yarim serit genisligi
        # ekleyerek buyuk bir hata uretiyordu. Once GLOBAL olarak iki ayri
        # tepe aramayi dene; bulunursa yari bolumlemesini atla.
        dual = self._find_dual_peaks(near_hist)

        # 6. Tepe bulma — yakın: hafıza destekli  |  uzak: serbest look-ahead
        near_lp, near_ls = self._find_peak(
            near_hist, 0, self.mid,
            self._left_mem[0]  if self._left_mem  else None)
        near_rp, near_rs = self._find_peak(
            near_hist, self.mid, self.bird_w,
            self._right_mem[0] if self._right_mem else None)
        far_lp, far_ls = self._find_peak(far_hist, 0,        self.mid,    None)
        far_rp, far_rs = self._find_peak(far_hist, self.mid, self.bird_w, None)

        # LEGACY-038: Global olarak iki ayri, yeterince ayrik tepe
        # bulunduysa bunlar gercek sinirlardir — yari bolumlemesinin
        # ortalamasi yerine bunlari kullan.
        if dual is not None:
            near_lp, near_rp = dual
            near_ls = near_rs = True

        # 7. Hafıza güncelleme (yakın bölge — daha kararlı)
        left_valid  = self._update_memory('left',  near_lp, near_ls)
        right_valid = self._update_memory('right', near_rp, near_rs)

        # LEGACY-039: GOZLENEN ile HATIRLANAN siniri ayirt et. Eski kodda
        # 25 kare boyunca onbellekteki sinir, taze gozlemden ayirt
        # edilemiyordu: tuketici (main) serit-kaybi zamanlayicisini ancak
        # error None olunca baslatiyor, yani arac ~25 kare boyunca eski
        # tahmini "guncel kanit" sayarak surmeye devam ediyordu.
        self.left_observed  = bool(near_ls)
        self.right_observed = bool(near_rs)
        self.lane_observed  = bool(near_ls or near_rs)
        if self.lane_observed:
            self._last_observation_time = time.monotonic()
        self.frames_since_observation = (
            0 if self.lane_observed else self.frames_since_observation + 1)

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
    def _find_dual_peaks(self, histogram: np.ndarray):
        """LEGACY-038: Histogramda iki ayri, yeterince ayrik serit tepesi ara.

        Kare merkezine gore yari bolumlemesi YAPMAZ; tepeleri global olarak
        bulur. Iki gecerli tepe yeterince ayriksa (sol, sag) dondurur,
        aksi halde None.
        """
        if histogram.size == 0:
            return None
        peak_val = float(histogram.max())
        if peak_val <= 0:
            return None

        thresh = peak_val * 0.5
        above = histogram > thresh

        # Surekli kosulari (run) cikar
        runs = []
        start = None
        for i, flag in enumerate(above):
            if flag and start is None:
                start = i
            elif not flag and start is not None:
                runs.append((start, i - 1))
                start = None
        if start is not None:
            runs.append((start, len(above) - 1))

        # Serit benzeri genislikteki kosulari tut
        valid = [(a, b) for (a, b) in runs
                 if (b - a + 1) >= LANE_MIN_PEAK_WIDTH]
        if len(valid) < 2:
            return None

        # En guclu iki kosuyu sec (toplam agirliga gore)
        scored = sorted(
            valid, key=lambda r: float(histogram[r[0]:r[1] + 1].sum()),
            reverse=True)[:2]

        centers = []
        for (a, b) in scored:
            seg = histogram[a:b + 1]
            centers.append(int(np.average(np.arange(a, b + 1), weights=seg)))
        centers.sort()

        if (centers[1] - centers[0]) < LANE_DUAL_PEAK_MIN_SEP:
            return None
        return centers[0], centers[1]

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
        total = float(region.sum())

        def has_lane_signal(values: np.ndarray, signal_total: float) -> bool:
            """Serit benzeri bir tepe var mi? Genis dusuk seviyeli gurultuyu,
            duzgun (serit-siz) zemini ve minik izole lekeleri reddeder.

            LEGACY-035: Eski kontrol yalnizca toplam kutle ve tepe degerine
            bakiyordu. Duzgun gri/beyaz bir zemin esigi gecince iki yarinin
            agirlik merkezi "iki serit" sayiliyor, ortalanmis sahte bir yol
            uretiliyor ve serit-kaybi korumasi devre disi kaliyordu.

            LEGACY-036: Minik izole bir parlama da gecerli serit sayilip
            buyuk bir direksiyon hatasi uretebiliyordu.
            """
            if values.size == 0 or signal_total < MIN_LANE_SIGNAL:
                return False
            peak = float(values.max())
            if peak < MIN_LANE_SIGNAL * MIN_LANE_SIGNAL_QUALITY_RATIO:
                return False

            # --- LEGACY-035: YEREL TEPE KONTRASTI ---------------------
            # Gercek bir serit, cevresine gore belirgin bir tepe yapar.
            # Duzgun bir zeminde tepe ~ ortalama olur; boyle bir sinyal
            # serit DEGILDIR.
            mean = float(values.mean())
            if mean > 0 and (peak / mean) < LANE_PEAK_CONTRAST_MIN:
                return False

            # --- LEGACY-035: DOYMUS KAPLAMA KONTROLU ------------------
            # Sutunlarin cok buyuk bolumu esigi geciyorsa bu bir serit
            # degil, genis beyaz bir yuzeydir.
            occupied = float((values > (peak * 0.5)).sum()) / float(values.size)
            if occupied > LANE_MAX_OCCUPANCY:
                return False

            # --- LEGACY-036: SERIT BENZERI GENISLIK -------------------
            # Tepe cevresindeki surekli kosu, serit genisligi araliginda
            # olmali. Tek/iki sutunluk bir leke serit degildir.
            thresh = peak * 0.5
            above = values > thresh
            pk = int(np.argmax(values))
            lo_i = pk
            while lo_i > 0 and above[lo_i - 1]:
                lo_i -= 1
            hi_i = pk
            while hi_i < values.size - 1 and above[hi_i + 1]:
                hi_i += 1
            run = hi_i - lo_i + 1
            if run < LANE_MIN_PEAK_WIDTH:
                return False

            return True

        if not has_lane_signal(region, total):
            # Dar pencerede bulunamadı — tam yarıya bak
            region = histogram[lo:hi]
            total = float(region.sum())
            if not has_lane_signal(region, total):
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
