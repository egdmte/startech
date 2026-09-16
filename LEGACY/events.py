# =============================================================================
# events.py  —  Görsel olay dedektörü
#
# Tespit eder:
#   • Trafik ışığı      → 'green' | None  (yarış başlangıcı için; kırmızı tespit edilmez)
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

# This module belongs to the code lineage used during the competition.
# Working does not mean perfect, but it successfully detected certain events.
#
# See HATA_DEFTERI_PAYLASIM.pdf for historically observed issues.
# Check the current implementation before reporting them; some may already be fixed.
#
# A closely related May 7 version is available on the master branch of
# ototot-yedek. It may not be identical to the final on-site version.
#
# Improve this module through focused fixes. Do not replace working behavior
# without a concrete reason.
#




import cv2
import numpy as np

from config import (
    WIDTH,
    SIGNAL_ROI_TOP, SIGNAL_ROI_BOTTOM,
    ROAD_ROI_TOP, ROAD_ROI_BOTTOM,
    GREEN_HSV_LOW, GREEN_HSV_HIGH,
    WHITE_HSV_LOW, WHITE_HSV_HIGH,
    SIGNAL_MIN_AREA, CROSSWALK_MIN_STRIPES, HEMZEMIN_DIAG_MIN_LINES,
    EVENT_DEBOUNCE_FRAMES, EVENT_NEAR_ROI_RATIO,
    ORANGE_HSV_LOW, ORANGE_HSV_HIGH, ORANGE_MIN_AREA,
    YELLOW_HSV_LOW, YELLOW_HSV_HIGH, YELLOW_MIN_AREA,

    PARKING_HSV_LOW1, PARKING_HSV_HIGH1,
    PARKING_HSV_LOW2, PARKING_HSV_HIGH2,
    PARKING_TRIGGER_AREA, PARKING_ROI_TOP,
    PARKING_NEAR_BOTTOM_RATIO,
    SIGN_BLUE_HSV_LOW, SIGN_BLUE_HSV_HIGH, SIGN_MIN_AREA,
    OBSTACLE_CORRIDOR_LEFT_RATIO, OBSTACLE_CORRIDOR_RIGHT_RATIO,
    OBSTACLE_MIN_CORRIDOR_OVERLAP,
    CROSSWALK_ROW_FILL_RATIO, CROSSWALK_MIN_STRIPE_ROWS,
    CROSSWALK_MAX_STRIPE_ROWS, CROSSWALK_MIN_GAP_ROWS,
    SPEED_BUMP_MIN_SPAN_ROWS, SPEED_BUMP_MAX_SPAN_ROWS,
    SPEED_BUMP_MIN_BODY_TEXTURE, SPEED_BUMP_MAX_INNER_EDGE_ROWS,
    HEMZEMIN_SLOPE_TOL, HEMZEMIN_ICEPT_TOL, HEMZEMIN_MIN_STRIPES,
    TRAFFIC_LIGHT_CIRC_MIN, TRAFFIC_LIGHT_ASPECT_MIN,
    TRAFFIC_LIGHT_ASPECT_MAX, TRAFFIC_LIGHT_MAX_EXTENT, TRAFFIC_LIGHT_MAX_AREA,
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
                            circ_min: float = TRAFFIC_LIGHT_CIRC_MIN,
                            max_area: float | None = None) -> float:
    """LEGACY-016: Trafik lambasi ADAYI icin sekil/boyut/en-boy kontrolu.

    Eski esik (circ_min=0.55) bir KAREYI kabul ediyordu: ideal bir karenin
    dairesellii ~0.785, yani 0.55'in cok uzerinde. Lamba muhafazasi,
    en-boy orani ve azami alan kontrolu de yoktu; bu yuzden ROI'daki kalici
    yesil bir nesne (yaprak, afis, kutu) debounce sonrasi YESIL ISIK olarak
    mandallanip bekleyen araci baslatabiliyordu.

    Gercek bir lamba: yuksek dairesellik, kareye yakin en-boy orani ve
    makul bir boyut araligi.
    """
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    best = 0.0
    for c in cnts:
        area = cv2.contourArea(c)
        if area < min_area:
            continue
        if max_area is not None and area > max_area:
            continue                      # cok buyuk: lamba degil, yuzey
        if _circularity(c) < circ_min:
            continue

        x, y, w, h = cv2.boundingRect(c)
        if w == 0 or h == 0:
            continue
        aspect = float(w) / float(h)
        if not (TRAFFIC_LIGHT_ASPECT_MIN <= aspect <= TRAFFIC_LIGHT_ASPECT_MAX):
            continue                      # uzun/yassi: lamba degil

        # Doluluk: daire, kendi sinirlayici kutusunun ~pi/4'unu (%78.5)
        # doldurur; kare ~%100 doldurur. Bu, kareyi daireden ayiran
        # dairesellikten BAGIMSIZ ikinci bir kanittir.
        extent = area / float(w * h)
        if extent > TRAFFIC_LIGHT_MAX_EXTENT:
            continue

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


def _largest_blob_area_and_bottom(mask: np.ndarray, min_area: float) -> tuple:
    """En büyük (alan ≥ min_area) blobun (alanını, bbox alt-kenar y'sini) döndürür.

    Bulamazsa (0.0, 0). Park alanı yakınlık kontrolü için kullanılır:
    aynı renkte uzaktaki bir leke yerine yakındaki büyük park slotuna karar verir.
    """
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    best_area = 0.0
    best_bottom = 0
    # LEGACY-017: Eski kod ONCE ROI'daki EN BUYUK kirmizi konturu seciyor,
    # yakinlik testini YALNIZCA o kazanana uyguluyordu. Bu yuzden gecerli,
    # yakin ama kucuk bir park slotu, uzaktaki daha buyuk bir kirmizi leke
    # yuzunden tamamen kayboluyordu. Simdi HER kontur once alan + yakinlik
    # icin suzuluyor, siralama ancak UYGUN adaylar arasinda yapiliyor.
    roi_h = mask.shape[0]
    near_y = roi_h * EVENT_NEAR_ROI_RATIO
    eligible = []
    for c in cnts:
        a = cv2.contourArea(c)
        if a < min_area:
            continue
        x, y, w, h = cv2.boundingRect(c)
        bottom = y + h
        if bottom >= near_y:            # yakinlik testini HER adaya uygula
            eligible.append((a, bottom))

    if eligible:
        # Uygun adaylar arasinda en yakin olani (en alt kenar) tercih et;
        # esitlikte daha buyuk alan kazanir.
        eligible.sort(key=lambda t: (t[1], t[0]), reverse=True)
        best_area, best_bottom = eligible[0]
        return best_area, best_bottom

    # Uygun yakin aday yoksa, geriye donuk uyumluluk icin en buyugu bildir
    # (yakin degil, yani tuketici park kararini vermeyecek).
    for c in cnts:
        a = cv2.contourArea(c)
        if a >= min_area and a > best_area:
            x, y, w, h = cv2.boundingRect(c)
            best_area = a
            best_bottom = y + h
    return best_area, best_bottom


# ---------------------------------------------------------------------------
# Ana sınıf
# ---------------------------------------------------------------------------

class EventDetector:
    """BGR kamera karesinden iz olaylarını tespit eder.

    Her döngü iterasyonunda ``detect(frame)`` çağrısı yapın.
    Döndürür dict:
        {
            'traffic_light':  'green' | None,
            'crosswalk':      bool,
            'hemzemin':       bool,
            'speed_bump':     bool,
            'orange_car':     bool,
            'parking_zone':   bool,
        }
    """

    def __init__(self):
        self._db: dict = {k: 0 for k in (
            'green', 'crosswalk', 'crosswalk_close',
            'hemzemin', 'hemzemin_close',
            'speed_bump', 'orange_car', 'yellow_car',
            'parking_zone', 'sign_blue',
        )}
        self._light: str | None = None
        self._k3 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        self._k5 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))

    # ------------------------------------------------------------------
    def detect(self, frame: np.ndarray) -> dict:
        """RGB kareyi işler ve olay sözlüğü döndürür.

        Döndürür dict:
            traffic_light  : 'green' | None  (yarış başlangıcı için)
            crosswalk      : bool  — yaya geçidi (kural 3.4.2: ≥5 s dur)
            hemzemin       : bool  — hemzemin geçit (kural 3.4.4: ≥5 s dur)
            speed_bump     : bool  — hız tümsek (kural 3.4.3: yavaşla)
            orange_car     : bool  — sollama hedefi turuncu araç (kural 3.4.5)
            yellow_car     : bool  — sollama YASAĞI bölgesi sarı engel araç
            parking_zone   : bool  — kırmızı park slotu görünür (kural 3.4.7)
            sign_blue      : bool  — mavi levha (Park P tabelası)
        """
        hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)

        # ----------------------------------------------------------------
        # Üst ROI: trafik ışığı + levha tespiti
        # ----------------------------------------------------------------
        sig_hsv = hsv[SIGNAL_ROI_TOP:SIGNAL_ROI_BOTTOM, :]

        # Trafik ışığı: yuvarlak yeşil blob (Şekil 7: 30-35 cm yükseklik)
        # Kırmızı tespiti kaldırıldı — yarışta yalnızca yeşil ışık aranır;
        # kırmızı/diğer hâl BEKLIYOR'da implicit olarak frenle ele alınır.
        green_m = cv2.morphologyEx(_green_mask(sig_hsv), cv2.MORPH_OPEN, self._k5)
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

        raw_crosswalk, raw_crosswalk_close = self._detect_stripe_pattern(road_hsv)
        raw_hemzemin,  raw_hemzemin_close  = self._detect_hemzemin(road_bgr)
        raw_speed_bump = self._detect_speed_bump(road_bgr)

        # --- LEGACY-018 ------------------------------------------------
        # Turuncu/sari kontrolleri TUM GENISLIKTEKI yol ROI'sini kullaniyor
        # ve yalnizca asgari kontur alanina bakiyordu; nesnenin surulebilir
        # seride ait olup olmadigiyla hic ilgilenmiyordu. Sonuc: kare
        # kenarindaki, yolu HIC kapatmayan turuncu bir nesne sollama
        # manevrasi baslatabiliyor; ilgisiz bir sari leke de sollamayi
        # yasaklayabiliyordu. Adaylar artik surus koridoruyla iliskilendirilir.
        corridor_lo = int(road_hsv.shape[1] * OBSTACLE_CORRIDOR_LEFT_RATIO)
        corridor_hi = int(road_hsv.shape[1] * OBSTACLE_CORRIDOR_RIGHT_RATIO)

        def _in_corridor(mask, min_area):
            """Konturu yalnizca surus koridoruyla ORTUSUYORSA kabul et."""
            cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL,
                                       cv2.CHAIN_APPROX_SIMPLE)
            best = 0.0
            for c in cnts:
                a = cv2.contourArea(c)
                if a < min_area:
                    continue
                x, y, w, h = cv2.boundingRect(c)
                # Koridorla yatay ortusme orani
                ox = max(0, min(x + w, corridor_hi) - max(x, corridor_lo))
                if w > 0 and (ox / float(w)) >= OBSTACLE_MIN_CORRIDOR_OVERLAP:
                    best = max(best, a)
            return best

        # Turuncu araç — sollama serbest bölgesindeki 20×30×25 cm turuncu engel
        orange_m = cv2.morphologyEx(_orange_mask(road_hsv), cv2.MORPH_OPEN, self._k5)
        raw_orange_car = _in_corridor(orange_m, ORANGE_MIN_AREA) > 0

        # Sarı araç — sollama YASAĞI bölgesindeki 20×45×25 cm sarı karşı şerit engeli.
        # Turuncu ile karıştırılmaması için HSV alt sınırı H=22'den başlar.
        yellow_m = cv2.morphologyEx(_yellow_mask(road_hsv), cv2.MORPH_OPEN, self._k5)
        raw_yellow_car = _in_corridor(yellow_m, YELLOW_MIN_AREA) > 0

        # Park bölgesi — kırmızı slot rengi (kılavuz Şekil 6).
        # İki ek koşul: (a) blob alt-kenarı ROI'nin yakın kısmında, (b) aynı karede
        # turuncu engel yoksa. Bu, uzaktaki kırmızılara ve turuncu/kırmızı renk
        # overlap'ine karşı koruma sağlar.
        park_roi = hsv[PARKING_ROI_TOP:, :]
        park_m = cv2.morphologyEx(_parking_mask(park_roi), cv2.MORPH_OPEN, self._k5)
        park_area, park_bottom = _largest_blob_area_and_bottom(
            park_m, PARKING_TRIGGER_AREA
        )
        park_roi_h = park_m.shape[0]
        # --- LEGACY-019 ------------------------------------------------
        # Eski kosul `and not raw_orange_car` idi: karede HERHANGI bir yerde
        # turuncu bir nesne bulunmasi, onunla hicbir ilgisi olmayan gecerli
        # bir kirmizi park slotunu TOPTAN iptal ediyordu. Turuncu (H=5..20)
        # ile kirmizi (H=0..10) araliklari ortustugu icin ayni slot hem
        # orange_car=True hem parking_zone=False uretebiliyor, tuketici de
        # park yerine sollamayi secebiliyordu.
        #
        # Dogru cozum: belirsizlik ADAY BAZINDA cozulur. Turuncu engel
        # yalnizca park adayiyla UZAYSAL olarak ortusuyorsa o adayi iptal
        # eder; ilgisiz turuncu lekelerin veto yetkisi yoktur.
        park_blocked = False
        if park_area > 0:
            o_cnts, _ = cv2.findContours(orange_m, cv2.RETR_EXTERNAL,
                                         cv2.CHAIN_APPROX_SIMPLE)
            p_cnts, _ = cv2.findContours(park_m, cv2.RETR_EXTERNAL,
                                         cv2.CHAIN_APPROX_SIMPLE)
            p_boxes = [cv2.boundingRect(c) for c in p_cnts
                       if cv2.contourArea(c) >= PARKING_TRIGGER_AREA]
            for oc in o_cnts:
                if cv2.contourArea(oc) < ORANGE_MIN_AREA:
                    continue
                ox, oy, ow, oh = cv2.boundingRect(oc)
                # Turuncu kontur ROI ofseti ile park ROI'sine tasinir
                oy_p = oy + (road_hsv.shape[0] - park_roi_h)
                for (px, py, pw, ph) in p_boxes:
                    ix = max(0, min(ox + ow, px + pw) - max(ox, px))
                    iy = max(0, min(oy_p + oh, py + ph) - max(oy_p, py))
                    if ix > 0 and iy > 0:
                        park_blocked = True
                        break
                if park_blocked:
                    break

        raw_parking_zone = (
            park_area > 0
            and park_bottom > park_roi_h * PARKING_NEAR_BOTTOM_RATIO
            and not park_blocked
        )

        # ----------------------------------------------------------------
        # Debounce — her olay EVENT_DEBOUNCE_FRAMES ardışık karede görünmeli
        # ----------------------------------------------------------------
        c_green        = self._debounce('green',        raw_green)
        c_crosswalk    = self._debounce('crosswalk',    raw_crosswalk)
        c_crosswalk_cl = self._debounce('crosswalk_close', raw_crosswalk_close)
        c_hemzemin     = self._debounce('hemzemin',     raw_hemzemin)
        c_hemzemin_cl  = self._debounce('hemzemin_close',  raw_hemzemin_close)
        c_bump         = self._debounce('speed_bump',   raw_speed_bump)
        c_orange       = self._debounce('orange_car',   raw_orange_car)
        c_yellow       = self._debounce('yellow_car',   raw_yellow_car)
        c_parking_zone = self._debounce('parking_zone', raw_parking_zone)
        c_sign_blue    = self._debounce('sign_blue',    raw_sign_blue)

        # Trafik ışığı durumu: onaylanmış yeşile göre güncellenir
        if c_green:
            self._light = 'green'

        return {
            'traffic_light':   self._light,
            'crosswalk':       c_crosswalk,
            'crosswalk_close': c_crosswalk_cl,
            'hemzemin':        c_hemzemin,
            'hemzemin_close':  c_hemzemin_cl,
            'speed_bump':      c_bump,
            'orange_car':      c_orange,
            'yellow_car':      c_yellow,
            'parking_zone':    c_parking_zone,
            'sign_blue':       c_sign_blue,
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
    def _detect_stripe_pattern(road_hsv: np.ndarray) -> tuple:
        """≥N adet yatay beyaz bant tespit eder (yaya geçidi).

        Döndürür (detected, near):
            detected — desen var mı
            near     — desenin alt-kenarı ROI'nin yakın diliminde mi
                       (yakın = kuralın 30 cm önce dur eşiğine geldik)

        İYİLEŞTİRİLDİ: Daha katı kontroller (false positive azaltma):
        1. Min 4 bant (eskiden 2)
        2. Bantlar arasında BOŞLUK olmalı (siyah ara)
        3. Bantlar BENZER kalınlıkta olmalı
        4. Her bant kare genişliğinin > %40'ı kadar olmalı
        """
        white     = _white_mask(road_hsv)
        roi_h     = white.shape[0]
        roi_w     = white.shape[1]

        # --- LEGACY-022 / LEGACY-023 ---------------------------------
        # Eski yontem ROI'yi 12 kaba banda boluyordu. Bunun uc ayri
        # kusuru vardi:
        #   1) Ince seritler cok daha yuksek bantlarin icinde kayboluyordu
        #      (%40 doluluk esigini gecemiyorlardi).
        #   2) range(0, roi_h - stripe_h, stripe_h) son tam bandi hic
        #      ornekleme kapsamina almiyordu; roi_h 12'ye tam bolundugunde
        #      EN YAKIN serit dusuyordu.
        #   3) white_band_count = sum(bands) AYNI seride ait komsu bantlari
        #      ayri serit sayiyordu; uc genis serit dort serit gibi gecip
        #      gereksiz bir durusa yol aciyordu.
        #
        # Dogru olcum: SATIR BAZLI doluluk sinyalinden gercek beyaz
        # kosulari (run) cikar, her birinin kalinligini dogrula, sonra
        # gercek serit konumlarina gore yakinlik karari ver.
        row_fill = (white > 0).sum(axis=1).astype(np.float32) / float(roi_w)
        occupied = row_fill > CROSSWALK_ROW_FILL_RATIO

        runs = []
        start = None
        for i, flag in enumerate(occupied):
            if flag and start is None:
                start = i
            elif not flag and start is not None:
                runs.append((start, i - 1))
                start = None
        if start is not None:
            # TUM satirlari kapsa — son serit ROI tabanina dayaniyorsa da
            # sayilmali (eski kodun kaybettigi durum).
            runs.append((start, len(occupied) - 1))

        # Gercek serit kalinligindaki kosulari tut; gurultu satirlarini at.
        stripes = [(a, b) for (a, b) in runs
                   if CROSSWALK_MIN_STRIPE_ROWS <= (b - a + 1) <= CROSSWALK_MAX_STRIPE_ROWS]

        # LEGACY-023: AYRI serit sayisi (kosular), dolu bant sayisi degil.
        if len(stripes) < CROSSWALK_MIN_STRIPES:
            return False, False

        # Seritler arasinda gercek KARANLIK bosluk bulunmali; aksi halde
        # bu duz beyaz bir yuzeydir.
        gaps = [stripes[i + 1][0] - stripes[i][1] - 1
                for i in range(len(stripes) - 1)]
        if not gaps or min(gaps) < CROSSWALK_MIN_GAP_ROWS:
            return False, False

        # Yakinlik: GERCEK serit konumuna gore. ROI'nin alt diliminde
        # sonlanan bir serit varsa desen kareye yakin demektir.
        near_y = roi_h * EVENT_NEAR_ROI_RATIO
        near = any(b >= near_y for (a, b) in stripes)
        return True, near

    # ------------------------------------------------------------------
    @staticmethod
    def _detect_speed_bump(road_bgr: np.ndarray) -> bool:
        """Yatay Canny kenarları → tümsek."""
        gray  = cv2.cvtColor(road_bgr, cv2.COLOR_BGR2GRAY)
        blur  = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blur, 50, 150)

        # --- LEGACY-024 -----------------------------------------------
        # Eski olcut TAMAMEN "iki satirda WIDTH*0.55'ten fazla kenar
        # pikseli" idi. Duz bir beyaz dikdortgen (siradan yol isareti,
        # hatta yaya gecidi boyasi) ust ve alt kenarini verdiginde tumsek
        # sayiliyor, gereksiz fren + yavas mod tetikleniyordu. Iki genel
        # kenar FIZIKSEL YUKSEKLIK kaniti degildir.
        rows = (edges.sum(axis=1) / 255) > (WIDTH * 0.55)
        edge_rows = np.flatnonzero(rows)
        if edge_rows.size < 2:
            return False

        # 1) Kenar ciftleri ARASINDA tumsek govdesine karsilik gelen
        #    makul bir yukseklik olmali (cok ince = duz boya).
        span = int(edge_rows[-1] - edge_rows[0])
        if not (SPEED_BUMP_MIN_SPAN_ROWS <= span <= SPEED_BUMP_MAX_SPAN_ROWS):
            return False

        # 2) Tumsek govdesi, duz boyaya gore DAHA FAZLA ic doku tasir
        #    (egim/golge). Duz bir dikdortgenin ici neredeyse kenarsizdir.
        top, bot = int(edge_rows[0]), int(edge_rows[-1])
        body = edges[top + 1:bot, :]
        if body.size == 0:
            return False
        body_density = float((body > 0).sum()) / float(body.size)
        if body_density < SPEED_BUMP_MIN_BODY_TEXTURE:
            return False

        # 3) Yaya gecidi ayrimi: govde icinde COK sayida duzenli yatay
        #    kenar varsa bu bir gecit deseni, tumsek degil.
        body_rows = ((body.sum(axis=1) / 255) > (WIDTH * 0.55)).sum()
        if body_rows >= SPEED_BUMP_MAX_INNER_EDGE_ROWS:
            return False

        return True

    # ------------------------------------------------------------------
    @staticmethod
    def _detect_hemzemin(road_bgr: np.ndarray) -> tuple:
        """X-desen çapraz çizgiler → hemzemin geçit.

        Döndürür (detected, near):
            detected — her iki çapraz yönde HEMZEMIN_DIAG_MIN_LINES çizgi
            near     — çaprazlardan en az biri ROI'nin yakın diliminde sonlanıyor
                       (30 cm eşiği için).
        """
        gray  = cv2.cvtColor(road_bgr, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180,
                                threshold=30, minLineLength=40, maxLineGap=15)
        if lines is None:
            return False, False
        roi_h    = road_bgr.shape[0]
        near_y   = roi_h * EVENT_NEAR_ROI_RATIO

        # --- LEGACY-025 -----------------------------------------------
        # Eski kod Hough parcalarini yalnizca EGIM ISARETINE gore sayiyor,
        # bunlarin gercekten KESISIP kesismedigine hic bakmiyordu. Birbirini
        # hic kesmeyen iki ayri egik serit siniri (ornegin bir virajin iki
        # kenari) "X deseni" sayilip gereksiz hemzemin durusu tetikliyordu.
        # Ayrica AYNI seridin iki kenari iki bagimsiz cizgi gibi sayiliyordu.
        pos_segs, neg_segs = [], []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            dx, dy = x2 - x1, y2 - y1
            if dx == 0:
                continue
            angle = np.degrees(np.arctan2(abs(dy), abs(dx)))
            if 25 <= angle <= 65:
                seg = (float(x1), float(y1), float(x2), float(y2))
                if dx * dy > 0:
                    pos_segs.append(seg)
                else:
                    neg_segs.append(seg)

        # 1) Ayni fiziksel seride ait yinelenen parcalari KUMELE.
        def _cluster(segs):
            """Benzer egim + benzer offset'li parcalari tek serit sayar."""
            clusters = []
            for (x1, y1, x2, y2) in segs:
                dx = x2 - x1
                if dx == 0:
                    continue
                slope = (y2 - y1) / dx
                icept = y1 - slope * x1
                placed = False
                for cl in clusters:
                    if (abs(cl['slope'] - slope) < HEMZEMIN_SLOPE_TOL
                            and abs(cl['icept'] - icept) < HEMZEMIN_ICEPT_TOL):
                        cl['segs'].append((x1, y1, x2, y2))
                        placed = True
                        break
                if not placed:
                    clusters.append({'slope': slope, 'icept': icept,
                                     'segs': [(x1, y1, x2, y2)]})
            return clusters

        pos_cl = _cluster(pos_segs)
        neg_cl = _cluster(neg_segs)

        # NOT: HEMZEMIN_DIAG_MIN_LINES ham PARCA sayisi icin ayarlanmisti.
        # Artik kumelenmis FIZIKSEL serit sayiyoruz, bu yuzden esik
        # HEMZEMIN_MIN_STRIPES'tir. Yanlis pozitifi eleyen asil kosul
        # asagidaki GERCEK KESISIM sartidir.
        if (len(pos_cl) < HEMZEMIN_MIN_STRIPES
                or len(neg_cl) < HEMZEMIN_MIN_STRIPES):
            return False, False

        # 2) GERCEK bir kesisim ROI icinde bulunmali.
        roi_w = road_bgr.shape[1]
        cross_y = None
        for a in pos_cl:
            for b in neg_cl:
                denom = a['slope'] - b['slope']
                if abs(denom) < 1e-6:
                    continue
                ix = (b['icept'] - a['icept']) / denom
                iy = a['slope'] * ix + a['icept']
                if 0 <= ix < roi_w and 0 <= iy < roi_h:
                    cross_y = iy if cross_y is None else max(cross_y, iy)
        if cross_y is None:
            return False, False        # kesismiyorlar -> X degil

        near = cross_y >= near_y
        return True, near

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
    def debug_frame(self, frame: np.ndarray, events: dict) -> np.ndarray:
        """Olay ROI'larını ve aktif olayları kareye çizer."""
        vis = frame.copy()
        cv2.rectangle(vis, (0, SIGNAL_ROI_TOP), (WIDTH - 1, SIGNAL_ROI_BOTTOM),
                      (0, 200, 200), 1)
        cv2.rectangle(vis, (0, ROAD_ROI_TOP), (WIDTH - 1, ROAD_ROI_BOTTOM),
                      (200, 200, 0), 1)
        light = events['traffic_light']
        light_col = ((0, 255, 0) if light == 'green' else (180, 180, 180))
        cv2.putText(vis, f"ISIK:{light or '--'}", (WIDTH - 160, 24),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, light_col, 2)

        y = 50
        for key, label, color in [
            ('crosswalk',    'YAYA GECİDİ',  (255, 200,   0)),
            ('hemzemin',     'HEMZEMİN',     (  0, 180, 255)),
            ('speed_bump',   'TÜMSEK',        (255, 165,   0)),
            ('orange_car',   'TURUNCU ARAC', (255, 120,   0)),
            ('yellow_car',   'SARI ARAC',    (220, 220,   0)),

            ('parking_zone', 'PARK BÖLGE',   (255,   0, 200)),
            ('sign_blue',    'MAVİ LEVHA',   ( 80, 120, 255)),
        ]:
            if events.get(key):
                cv2.putText(vis, label, (WIDTH - 210, y),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                y += 26
        return vis