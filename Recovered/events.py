# =============================================================================
# events.py  —  Görsel olay dedektörü
#
# Tespit eder:
#   • Trafik ışığı      → 'red' | 'green' | None
#   • Yaya geçidi       → bool  (yatay beyaz-koyu şerit deseni)
#   • Hemzemin geçit    → bool  (demiryolu geçidi — X şerit deseni)
#   • Tümsek            → bool  (yol ROI'da güçlü yatay kenar)
#   • Turuncu araç      → bool  (yol ROI'da turuncu engel)
#   • Çıkmaz yol        → bool  (merkez yol ROI'da büyük engel veya şerit bitiyor)
#   • Park bölgesi      → bool  (çerçeve altında kırmızı slot görünümü)
#
# NOT: Yarışma kurallarında (MEB 2026 PDF) dur işareti YOKTUR.
#
# Tüm tespitler debounce'ludur: bir olay N ardışık karede görünmeden
# True olarak raporlanmaz.
# =============================================================================
import cv2
import numpy as np

from config import (
    WIDTH, HEIGHT,
    SIGNAL_ROI_TOP, SIGNAL_ROI_BOTTOM,
    ROAD_ROI_TOP, ROAD_ROI_BOTTOM,
    RED_HSV_LOW1, RED_HSV_HIGH1,
    RED_HSV_LOW2, RED_HSV_HIGH2,
    GREEN_HSV_LOW, GREEN_HSV_HIGH,
    WHITE_HSV_LOW, WHITE_HSV_HIGH,
    SIGNAL_MIN_AREA, CROSSWALK_MIN_STRIPES, HEMZEMIN_DIAG_MIN_LINES,
    EVENT_DEBOUNCE_FRAMES,
    ORANGE_HSV_LOW, ORANGE_HSV_HIGH, ORANGE_MIN_AREA,
    YELLOW_HSV_LOW, YELLOW_HSV_HIGH, YELLOW_MIN_AREA,
    DEAD_END_MIN_AREA,
    DEAD_END_ROI_LEFT, DEAD_END_ROI_RIGHT,
    DEAD_END_ROI_TOP, DEAD_END_ROI_BOTTOM,
    DEAD_END_FWD_WHITE_MAX, DEAD_END_NEAR_WHITE_MIN,
    PARKING_HSV_LOW1, PARKING_HSV_HIGH1,
    PARKING_HSV_LOW2, PARKING_HSV_HIGH2,
    PARKING_TRIGGER_AREA, PARKING_ROI_TOP,
    SIGN_BLUE_HSV_LOW, SIGN_BLUE_HSV_HIGH, SIGN_MIN_AREA,
)


# ---------------------------------------------------------------------------
# Yardımcı fonksiyonlar
# ---------------------------------------------------------------------------

def _circularity(contour: np.ndarray) -> float:
    area = cv2.contourArea(contour)
    peri = cv2.arcLength(contour, True)
    if peri < 1:
        return 0.0
    return (4 * np.pi * area) / (peri * peri)


def _red_mask(hsv: np.ndarray) -> np.ndarray:
    m1 = cv2.inRange(hsv, np.array(RED_HSV_LOW1,  dtype=np.uint8),
                          np.array(RED_HSV_HIGH1, dtype=np.uint8))
    m2 = cv2.inRange(hsv, np.array(RED_HSV_LOW2,  dtype=np.uint8),
                          np.array(RED_HSV_HIGH2, dtype=np.uint8))
    return cv2.bitwise_or(m1, m2)


def _green_mask(hsv: np.ndarray) -> np.ndarray:
    return cv2.inRange(hsv, np.array(GREEN_HSV_LOW,  dtype=np.uint8),
                            np.array(GREEN_HSV_HIGH, dtype=np.uint8))


def _white_mask(hsv: np.ndarray) -> np.ndarray:
    return cv2.inRange(hsv, np.array(WHITE_HSV_LOW,  dtype=np.uint8),
                            np.array(WHITE_HSV_HIGH, dtype=np.uint8))


def _orange_mask(hsv: np.ndarray) -> np.ndarray:
    return cv2.inRange(hsv, np.array(ORANGE_HSV_LOW,  dtype=np.uint8),
                            np.array(ORANGE_HSV_HIGH, dtype=np.uint8))


def _yellow_mask(hsv: np.ndarray) -> np.ndarray:
    """Sarı araç maskesi — sollama yasağı bölgesindeki sarı engel araçları."""
    return cv2.inRange(hsv, np.array(YELLOW_HSV_LOW,  dtype=np.uint8),
                            np.array(YELLOW_HSV_HIGH, dtype=np.uint8))


def _sign_blue_mask(hsv: np.ndarray) -> np.ndarray:
    """Mavi levha maskesi — Park (P) ve Çıkmaz Yol (T) işaret tabelaları."""
    return cv2.inRange(hsv, np.array(SIGN_BLUE_HSV_LOW,  dtype=np.uint8),
                            np.array(SIGN_BLUE_HSV_HIGH, dtype=np.uint8))


def _parking_mask(hsv: np.ndarray) -> np.ndarray:
    p1 = cv2.inRange(hsv, np.array(PARKING_HSV_LOW1, dtype=np.uint8),
                          np.array(PARKING_HSV_HIGH1, dtype=np.uint8))
    p2 = cv2.inRange(hsv, np.array(PARKING_HSV_LOW2, dtype=np.uint8),
                          np.array(PARKING_HSV_HIGH2, dtype=np.uint8))
    return cv2.bitwise_or(p1, p2)


def _largest_circular_blob(mask: np.ndarray, min_area: float,
                            circ_min: float = 0.55) -> float:
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    best = 0.0
    for c in cnts:
        area = cv2.contourArea(c)
        if area < min_area:
            continue
        if _circularity(c) >= circ_min:
            best = max(best, area)
    return best


def _largest_blob_area(mask: np.ndarray, min_area: float) -> float:
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    best = 0.0
    for c in cnts:
        a = cv2.contourArea(c)
        if a >= min_area:
            best = max(best, a)
    return best


# ---------------------------------------------------------------------------
# Ana sınıf
# ---------------------------------------------------------------------------

class EventDetector:
    """BGR kamera karesinden iz olaylarını tespit eder.

    Her döngü iterasyonunda ``detect(frame)`` çağrısı yapın.
    Döndürür dict:
        {
            'traffic_light':  'red' | 'green' | None,
            'crosswalk':      bool,
            'hemzemin':       bool,
            'speed_bump':     bool,
            'orange_car':     bool,
            'dead_end':       bool,
            'parking_zone':   bool,
        }
    """

    def __init__(self):
        # Debounce sayaçları — her olay için ayrı tutulan ardışık kare sayısı.
        # 'yellow_car': sollama yasağı bölgesindeki sarı araç
        # 'sign_blue' : mavi levha (park veya çıkmaz yol işareti)
        self._db: dict = {k: 0 for k in (
            'red', 'green', 'crosswalk', 'hemzemin',
            'speed_bump', 'orange_car', 'yellow_car',
            'dead_end', 'parking_zone', 'sign_blue',
        )}
        self._light: str | None = None
        self._k3 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        self._k5 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))

    # ------------------------------------------------------------------
    def detect(self, frame: np.ndarray) -> dict:
        """RGB kareyi işler ve olay sözlüğü döndürür.

        Döndürür dict:
            traffic_light  : 'red' | 'green' | None
            crosswalk      : bool  — yaya geçidi (kural 3.4.2: ≥5 s dur)
            hemzemin       : bool  — hemzemin geçit (kural 3.4.4: ≥5 s dur)
            speed_bump     : bool  — hız tümsek (kural 3.4.3: yavaşla)
            orange_car     : bool  — sollama hedefi turuncu araç (kural 3.4.5)
            yellow_car     : bool  — sollama YASAĞI bölgesi sarı engel araç
            dead_end       : bool  — çıkmaz yol (kural 3.4.6: sağa dön)
            parking_zone   : bool  — kırmızı park slotu görünür (kural 3.4.7)
            sign_blue      : bool  — mavi levha (Park P veya Çıkmaz T tabelası)
        """
        hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)

        # ----------------------------------------------------------------
        # Üst ROI: trafik ışığı + levha tespiti
        # ----------------------------------------------------------------
        sig_hsv = hsv[SIGNAL_ROI_TOP:SIGNAL_ROI_BOTTOM, :]

        # Trafik ışığı: yuvarlak kırmızı/yeşil blob (Şekil 7: 30-35 cm yükseklik)
        red_m   = cv2.morphologyEx(_red_mask(sig_hsv),   cv2.MORPH_OPEN, self._k5)
        green_m = cv2.morphologyEx(_green_mask(sig_hsv), cv2.MORPH_OPEN, self._k5)
        raw_red   = _largest_circular_blob(red_m,   SIGNAL_MIN_AREA) > 0
        raw_green = _largest_circular_blob(green_m, SIGNAL_MIN_AREA) > 0

        # Mavi levha tespiti — Park (P) veya Çıkmaz Yol (T) işaret tabelası.
        # Levhalar küçüktür (13 cm), sinyal ROI'nun sağ / sol kenarında belirir.
        raw_sign_blue = self._detect_sign_blue(sig_hsv)

        # ----------------------------------------------------------------
        # Alt ROI: yol yüzeyi olayları
        # ----------------------------------------------------------------
        road_hsv = hsv[ROAD_ROI_TOP:ROAD_ROI_BOTTOM, :]
        road_bgr = cv2.cvtColor(
            frame[ROAD_ROI_TOP:ROAD_ROI_BOTTOM, :], cv2.COLOR_RGB2BGR
        )

        # ÖNEMLİ: crosswalk ve hemzemin RAW değerleri dead_end tespitinden ÖNCE
        # hesaplanmalıdır. Yaya geçidi / hemzemin bölgelerinde _detect_dead_end
        # Method 2'si yanlış tetiklenebilir; bu iki değeri ona geçirerek baskılıyoruz.
        raw_crosswalk  = self._detect_stripe_pattern(road_hsv)
        raw_hemzemin   = self._detect_hemzemin(road_bgr)
        raw_speed_bump = self._detect_speed_bump(road_bgr)

        # Turuncu araç — sollama serbest bölgesindeki 20×30×25 cm turuncu engel
        orange_m = cv2.morphologyEx(_orange_mask(road_hsv), cv2.MORPH_OPEN, self._k5)
        raw_orange_car = _largest_blob_area(orange_m, ORANGE_MIN_AREA) > 0

        # Sarı araç — sollama YASAĞI bölgesindeki 20×45×25 cm sarı karşı şerit engeli.
        # Turuncu ile karıştırılmaması için HSV alt sınırı H=22'den başlar.
        yellow_m = cv2.morphologyEx(_yellow_mask(road_hsv), cv2.MORPH_OPEN, self._k5)
        raw_yellow_car = _largest_blob_area(yellow_m, YELLOW_MIN_AREA) > 0

        # Çıkmaz yol — raw_crosswalk ve raw_hemzemin geçilerek yanlış tetiklenme önlenir
        raw_dead_end = self._detect_dead_end(hsv, raw_crosswalk, raw_hemzemin)

        # Park bölgesi — kırmızı slot rengi (kılavuz Şekil 6)
        park_m = cv2.morphologyEx(
            _parking_mask(hsv[PARKING_ROI_TOP:, :]), cv2.MORPH_OPEN, self._k5
        )
        raw_parking_zone = _largest_blob_area(park_m, PARKING_TRIGGER_AREA) > 0

        # ----------------------------------------------------------------
        # Debounce — her olay EVENT_DEBOUNCE_FRAMES ardışık karede görünmeli
        # ----------------------------------------------------------------
        c_red          = self._debounce('red',          raw_red)
        c_green        = self._debounce('green',        raw_green)
        c_crosswalk    = self._debounce('crosswalk',    raw_crosswalk)
        c_hemzemin     = self._debounce('hemzemin',     raw_hemzemin)
        c_bump         = self._debounce('speed_bump',   raw_speed_bump)
        c_orange       = self._debounce('orange_car',   raw_orange_car)
        c_yellow       = self._debounce('yellow_car',   raw_yellow_car)
        c_dead_end     = self._debounce('dead_end',     raw_dead_end)
        c_parking_zone = self._debounce('parking_zone', raw_parking_zone)
        c_sign_blue    = self._debounce('sign_blue',    raw_sign_blue)

        # Trafik ışığı durumu: onaylanmış kırmızı/yeşile göre güncellenir
        if c_red:
            self._light = 'red'
        elif c_green:
            self._light = 'green'

        return {
            'traffic_light': self._light,
            'crosswalk':     c_crosswalk,
            'hemzemin':      c_hemzemin,
            'speed_bump':    c_bump,
            'orange_car':    c_orange,
            'yellow_car':    c_yellow,
            'dead_end':      c_dead_end,
            'parking_zone':  c_parking_zone,
            'sign_blue':     c_sign_blue,
        }

    # ------------------------------------------------------------------
    def _debounce(self, key: str, raw: bool) -> bool:
        if raw:
            self._db[key] = min(self._db[key] + 1, EVENT_DEBOUNCE_FRAMES + 1)
        else:
            self._db[key] = 0
        return self._db[key] >= EVENT_DEBOUNCE_FRAMES

    # ------------------------------------------------------------------
    @staticmethod
    def _detect_stripe_pattern(road_hsv: np.ndarray) -> bool:
        """≥N adet yatay beyaz bant tespit eder (yaya geçidi veya hemzemin)."""
        white     = _white_mask(road_hsv)
        roi_h     = white.shape[0]
        stripe_h  = max(1, roi_h // 12)
        threshold = WIDTH * stripe_h * 0.20
        bands = 0
        for i in range(0, roi_h - stripe_h, stripe_h):
            if white[i:i + stripe_h, :].sum() / 255 > threshold:
                bands += 1
        return bands >= CROSSWALK_MIN_STRIPES

    # ------------------------------------------------------------------
    @staticmethod
    def _detect_speed_bump(road_bgr: np.ndarray) -> bool:
        """Yatay Canny kenarları → tümsek."""
        gray  = cv2.cvtColor(road_bgr, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 50, 150)
        return int((edges.sum(axis=1) / 255 > WIDTH * 0.55).sum()) >= 2

    # ------------------------------------------------------------------
    @staticmethod
    def _detect_hemzemin(road_bgr: np.ndarray) -> bool:
        """X-desen çapraz çizgiler → hemzemin geçit.

        Her iki çapraz yönde de en az HEMZEMIN_DIAG_MIN_LINES çizgi gerekir.
        """
        gray  = cv2.cvtColor(road_bgr, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180,
                                threshold=30, minLineLength=40, maxLineGap=15)
        if lines is None:
            return False
        pos_diag = 0   # \ yönü
        neg_diag = 0   # / yönü
        for line in lines:
            x1, y1, x2, y2 = line[0]
            dx, dy = x2 - x1, y2 - y1
            if dx == 0:
                continue
            angle = np.degrees(np.arctan2(abs(dy), abs(dx)))
            if 25 <= angle <= 65:
                if dx * dy > 0:
                    pos_diag += 1
                else:
                    neg_diag += 1
        return (pos_diag >= HEMZEMIN_DIAG_MIN_LINES and
                neg_diag >= HEMZEMIN_DIAG_MIN_LINES)

    # ------------------------------------------------------------------
    def _detect_sign_blue(self, sig_hsv: np.ndarray) -> bool:
        """Sinyal ROI'da mavi arka planlı levha (Park P veya Çıkmaz T) tespit eder.

        Mavi levhalar: kılavuz Şekil 10 — 13 cm genişlik, 20 cm toplam yükseklik.
        Trafik ışığına kıyasla daha küçük ve dikdörtgen şekilli olduklarından
        yuvarlak blob filtresi yerine basit alan eşiği kullanılır.
        """
        blue_m = cv2.morphologyEx(
            _sign_blue_mask(sig_hsv), cv2.MORPH_OPEN, self._k3
        )
        return _largest_blob_area(blue_m, SIGN_MIN_AREA) > 0

    # ------------------------------------------------------------------
    def _detect_dead_end(self, full_hsv: np.ndarray,
                         crosswalk_raw: bool = False,
                         hemzemin_raw: bool = False) -> bool:
        """İki yöntemli çıkmaz yol dedektörü.

        Yöntem 1: merkez ROI'da büyük engel blobu (T-şekilli bariyer).
        Yöntem 2: ileri bölgede her iki yanda beyaz piksel yok,
                  yakın bölgede var (şerit bitiyor / yol sonu görünümü).

        Parametreler
        ------------
        crosswalk_raw : bool
            Bu karede ham yaya geçidi tespiti varsa True.
        hemzemin_raw  : bool
            Bu karede ham hemzemin geçit tespiti varsa True.

        NOT: Yöntem 2 yaya geçidi veya hemzemin bölgelerinde YANLIŞ TETİKLENEBİLİR.
        Bu bölgelerde yol şeritleri near-ROI'yu doldurur, fwd-ROI boş görünebilir.
        crosswalk_raw veya hemzemin_raw True ise Yöntem 2 devre dışı bırakılır.
        """
        # ---- Yöntem 1: merkez ROI'da büyük engel blobu ----
        roi = full_hsv[DEAD_END_ROI_TOP:DEAD_END_ROI_BOTTOM,
                       DEAD_END_ROI_LEFT:DEAD_END_ROI_RIGHT]
        not_black = cv2.inRange(roi,
                                np.array((0,    0,  50), dtype=np.uint8),
                                np.array((180, 255, 255), dtype=np.uint8))
        not_white = cv2.bitwise_not(_white_mask(roi))
        obstacle  = cv2.morphologyEx(
            cv2.bitwise_and(not_black, not_white), cv2.MORPH_OPEN, self._k5
        )
        if _largest_blob_area(obstacle, DEAD_END_MIN_AREA) > 0:
            return True

        # ---- Yöntem 2: ileride şerit yok, yakında şerit var ----
        # Yaya geçidi / hemzemin bölgesindeyken bu yöntemi ATLA.
        # Bu bölgelerdeki yol işaretleri near-ROI'yu beyaza doldurur,
        # fwd-ROI boş görünebilir → yanlış çıkmaz yol tetiklemesi riski.
        if crosswalk_raw or hemzemin_raw:
            return False

        fwd_white   = _white_mask(full_hsv[SIGNAL_ROI_BOTTOM:ROAD_ROI_TOP, :])
        left_white  = int(fwd_white[:, :WIDTH // 2].sum() / 255)
        right_white = int(fwd_white[:, WIDTH // 2:].sum() / 255)
        lane_absent = (left_white  < DEAD_END_FWD_WHITE_MAX and
                       right_white < DEAD_END_FWD_WHITE_MAX)
        near_white  = int(_white_mask(
            full_hsv[ROAD_ROI_TOP:ROAD_ROI_BOTTOM, :]
        ).sum() / 255)
        return lane_absent and near_white > DEAD_END_NEAR_WHITE_MIN

    # ------------------------------------------------------------------
    def debug_frame(self, frame: np.ndarray, events: dict) -> np.ndarray:
        """Olay ROI'larını ve aktif olayları kareye çizer."""
        vis = frame.copy()
        cv2.rectangle(vis, (0, SIGNAL_ROI_TOP), (WIDTH - 1, SIGNAL_ROI_BOTTOM),
                      (0, 200, 200), 1)
        cv2.rectangle(vis, (0, ROAD_ROI_TOP), (WIDTH - 1, ROAD_ROI_BOTTOM),
                      (200, 200, 0), 1)
        cv2.rectangle(vis,
                      (DEAD_END_ROI_LEFT, DEAD_END_ROI_TOP),
                      (DEAD_END_ROI_RIGHT, DEAD_END_ROI_BOTTOM),
                      (255, 0, 255), 1)

        light = events['traffic_light']
        light_col = ((255, 0, 0)   if light == 'red'   else
                     (0, 255, 0)   if light == 'green' else
                     (180, 180, 180))
        cv2.putText(vis, f"ISIK:{light or '--'}", (WIDTH - 160, 24),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, light_col, 2)

        y = 50
        for key, label, color in [
            ('crosswalk',    'YAYA GECİDİ',  (255, 200,   0)),
            ('hemzemin',     'HEMZEMİN',     (  0, 180, 255)),
            ('speed_bump',   'TÜMSEK',        (255, 165,   0)),
            ('orange_car',   'TURUNCU ARAC', (255, 120,   0)),
            ('yellow_car',   'SARI ARAC',    (220, 220,   0)),
            ('dead_end',     'ÇIKMAZ YOL',   (255,  50,   0)),
            ('parking_zone', 'PARK BÖLGE',   (255,   0, 200)),
            ('sign_blue',    'MAVİ LEVHA',   ( 80, 120, 255)),
        ]:
            if events.get(key):
                cv2.putText(vis, label, (WIDTH - 210, y),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                y += 26
        return vis