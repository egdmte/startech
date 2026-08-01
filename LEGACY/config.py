# =============================================================================
# config.py  —  Tüm ayarlanabilir parametreler tek yerden
#
# Yarış günü önce calibrate.py, sonra camera.py çalıştır,
# değerleri buraya yapıştır, sistemi başlat.
# =============================================================================

# ---------------------------------------------------------------------------
# Kamera çözünürlüğü
# ---------------------------------------------------------------------------
WIDTH  = 800
HEIGHT = 680

# ---------------------------------------------------------------------------
# Perspektif / ROI
# ---------------------------------------------------------------------------
# Görüntünün alttan itibaren kaçta kaçını kullanalım (0.55 → üst %45 atılır).
ROI_TOP_RATIO = 0.55

# Perspektif dörtgeni — TAM KARE piksel koordinatları.
# Sıra: sol-üst, sağ-üst, sol-alt, sağ-alt
# Gerçek pistinize göre calibrate.py ile ayarlayın.
# ⚠️  800×680 çözünürlük için yeniden kalibre edilmeli (calibrate.py çalıştırın).
PERSP_SRC = [[160, 300], [480, 300], [0, 480], [640, 480]]  # sol-üst, sağ-üst, sol-alt, sağ-alt

# ---------------------------------------------------------------------------
# Şerit tespiti
# ---------------------------------------------------------------------------
# Histogramda minimum sütun toplamı — şerit tepe noktası geçerliliği için.
MIN_LANE_SIGNAL = 200

# Şerit Kalitesi Kontrolü: Histogram tepe noktası sinyal güvenliği
MIN_LANE_SIGNAL_QUALITY_RATIO = 1.0  # max(hist) < MIN_LANE_SIGNAL * ratio ise red et

# Yalnızca bir şerit görünüyorken kullanılan varsayılan şerit genişliği (px).
# Gerçek pistinizde camera.py ile ölçün.
ASSUMED_LANE_WIDTH = 300

# Beyaz şerit için HSV aralığı.
# camera.py'de tesis ışığı altında doğrulayın.
# ADAPTIF HSV: Parlaklık ortalamasına göre dinamik ayarlama
WHITE_HSV_LOW  = (0,   0,  140)
WHITE_HSV_HIGH = (180, 80, 255)

# Adaptif HSV profilleri (V_mean'e göre otomatik seçim)
# Karanlık: V_mean < 100
WHITE_HSV_LOW_DARK   = (0,   0,  80)
WHITE_HSV_HIGH_DARK  = (180, 100, 255)

# Normal: 100 <= V_mean <= 200
WHITE_HSV_LOW_NORMAL  = (0,   0,  90)
WHITE_HSV_HIGH_NORMAL = (180, 110, 255)

# Parlak: V_mean > 200
WHITE_HSV_LOW_BRIGHT  = (0,   0,  160)
WHITE_HSV_HIGH_BRIGHT = (180, 60, 255)

# Şerit sinyali MIN_LANE_SIGNAL'ın altına düştükten sonra kaç kare güvenilir.
LANE_MEMORY_FRAMES = 25

# Son bilinen konumdan kaç piksel içinde arama yapılır.
LANE_SEARCH_WINDOW = 120

# ---------------------------------------------------------------------------
# PD denetleyici — OPTIMIZE EDİLMİŞ
# ---------------------------------------------------------------------------
KP = 0.30   # oransal kazanç
KD = 0.45   # türevsel kazanç

# İntegral kazancı + anti-windup
# Sürekli virajda PD'nin sıfırlayamadığı kalıcı hatayı kapatır.
# INTEGRAL_MAX küçük tutulur ki dış-yörüngeye sürüklenmeyi düzeltsin ama
# uzun düz hatlarda biriken bias'la salınıma yol açmasın.
KI           = 0.04
INTEGRAL_MAX = 50.0

# Büyük hatalar için dinamik kazanç artışı (|error| > 30 iken etkin)
KP_LARGE_ERROR_MULT = 1.3  # oransal kazanç çarpanı
KD_LARGE_ERROR_MULT = 1.2  # türevsel kazanç çarpanı

# Derivative cap (salınım önleme)
DERIV_CAP = 150

# Crossing (viraj) için KD artırma (|derivative| > 50 iken etkin)
CROSSING_KD_MULT = 1.2  # türevsel kazanç çarpanı

# ---------------------------------------------------------------------------
# Motor hızları (0–100 %) — OPTIMIZE EDİLMİŞ
# ---------------------------------------------------------------------------
BASE_SPEED = 62   # hata = 0 iken seyir hızı
MIN_SPEED  = 25   # minimum hız (virajda durmama)
MAX_SPEED  = 85   # maksimum hız
K_SPEED    = 0.45 # hız = BASE - K_SPEED * |hata|

# Hız-Viraj Koordinasyonu: Derivative bazlı yavaşlama
DERIV_SLOWDOWN_THRESHOLD = 50   # |derivative| > 50 ise MIN_SPEED'e
DERIV_MEDIUM_THRESHOLD   = 30   # |derivative| > 30 ise BASE - 10

# Motor dengeleme katsayıları — mekanik dengesizliği giderir.
# Düşük hızda (< 40%) ve yüksek hızda (> 70%) ayrı profiller
LEFT_TRIM_LOW   = 1.0   # < 40% hızda sol trim
LEFT_TRIM_HIGH  = 1.0   # > 70% hızda sol trim
RIGHT_TRIM_LOW  = 1.0   # < 40% hızda sağ trim
RIGHT_TRIM_HIGH = 1.0   # > 70% hızda sağ trim

# Ölü bölge telafisi (20% ölü bölge)
DEAD_ZONE_PERCENT = 20   # PWM sinyalinin üst % kaçı ölü bölge
DEAD_ZONE_MIN_PWM = 30   # Ölü bölgeyi aşan minimum PWM

# ---------------------------------------------------------------------------
# GPIO pinleri (BCM numaralandırması)
# ---------------------------------------------------------------------------
RIGHT_IN1     = 17
RIGHT_IN2     = 27
LEFT_IN1      = 22
LEFT_IN2      = 23
LEFT_PWM_PIN  = 12
RIGHT_PWM_PIN = 13

# Fiziksel başlatma butonu (BCM).
# Yarışta bilgisayarsız başlatma → +50 puan bonusu.
START_BUTTON_PIN = 16

# ---------------------------------------------------------------------------
# Kamera renk sırası düzeltme
# ---------------------------------------------------------------------------
# Bazı Raspberry Pi / picamera2 donanım+sürüm kombinasyonlarında
# "RGB888" formatı talep edilmesine rağmen kare BGRA veya BGR sıralı gelebilir.
# Kameradan gelen görüntünün RENK KANALLARI TERS görünüyorsa (beyaz mavi gibi,
# turuncu mavi gibi) bu bayrağı True yapın.
CAMERA_BGR_OUTPUT  = False  # True → kamera BGR dönüyor, RGB'ye çevir
CAMERA_ROTATE_180  = True   # True → kamera 180° döndürülür (ters montaj)

# Sürüş sırasında önizleme penceresi (main.py). False = performans modu.
SHOW_PREVIEW = True

# ---------------------------------------------------------------------------
# Kayıt
# ---------------------------------------------------------------------------
LOG_DURATION_SEC = 120
LOG_FILE         = "error_log.csv"

# ---------------------------------------------------------------------------
# Olay tespiti — ROI'lar
# ---------------------------------------------------------------------------
# Trafik ışığı / levha için üst ROI
SIGNAL_ROI_TOP    = 0
SIGNAL_ROI_BOTTOM = 200

# Yol yüzeyi olayları (yaya geçidi, hemzemin, tümsek) için alt ROI
ROAD_ROI_TOP    = 300
ROAD_ROI_BOTTOM = 680

# ---------------------------------------------------------------------------
# Trafik ışığı renkleri — HSV
# ---------------------------------------------------------------------------
# KIRMIZI: ton çift aralıklıdır (0-10 ve 160-180)
RED_HSV_LOW1  = (0,   120, 80)
RED_HSV_HIGH1 = (10,  255, 255)
RED_HSV_LOW2  = (160, 120, 80)
RED_HSV_HIGH2 = (180, 255, 255)

# YEŞİL
GREEN_HSV_LOW  = (40,  80, 60)
GREEN_HSV_HIGH = (90, 255, 255)

# Geçerli sinyal blobu için minimum kontur alanı (px²)
SIGNAL_MIN_AREA = 300

# ---------------------------------------------------------------------------
# Yaya geçidi / hemzemin geçit tespiti
# ---------------------------------------------------------------------------
# Kaç adet yatay beyaz bant = yaya geçidi
# ⚠️ ÖNEMLİ: Düşük değer (2) düz yolu da yaya geçidi sanır!
# Gerçek yaya geçidinde 4-6 bant vardır.
CROSSWALK_MIN_STRIPES = 4

# Hemzemin X-deseni: her çapraz yönde en az kaç çizgi olmalı
HEMZEMIN_DIAG_MIN_LINES = 2

# ---------------------------------------------------------------------------
# Olay debounce
# ---------------------------------------------------------------------------
# Bir olay kaç ardışık karede görünmeli ki gerçek kabul edilsin
EVENT_DEBOUNCE_FRAMES = 6

# Olay "yakın" sayılması için road ROI'nun bu orandan sonraki alt diliminde
# desenin görünmesi gerekir (0.75 = ROI'nun alt %25'i = ~30 cm).
# Yaya geçidi ve hemzemin için "30 cm önce dur" kuralı (3.4.2, 3.4.4).
EVENT_NEAR_ROI_RATIO = 0.75

# ---------------------------------------------------------------------------
# Şerit kayıp failsafe
# ---------------------------------------------------------------------------
# Şerit algılanamadığında araç son dönüş yönünü korur (prev_error işaretinden).
# LANE_LOST_TURN_SEC saniye içinde şerit tekrar bulunmazsa araç durur.
LANE_LOST_TURN_SEC  = 3.5   # dönüş süresi (s) — arabaya göre ayarla
LANE_LOST_TURN_BIAS = 100   # şerit kayıpken kullanılan yapay hata büyüklüğü (px); yön prev_error'dan alınır

# ---------------------------------------------------------------------------
# Durum makinesi zamanlaması
# ---------------------------------------------------------------------------
CROSSWALK_WAIT_SEC  = 5.0   # yaya geçidinde bekleme (kural: ≥5 s)
HEMZEMIN_WAIT_SEC   = 5.0   # hemzemin geçitte bekleme (kural: ≥5 s)
SPEED_BUMP_SLOW_SEC = 1.5   # tümsek üzerinde yavaş geçiş süresi
SPEED_BUMP_SPEED    = 25    # tümsek geçişi sırasında hız (%)

# Yaklaşma hızı: yaya geçidi/hemzemin tespit edildi ama henüz yakın değil
# durumunda kullanılır. Şerit takibi açık kalır, sadece hız düşer.
APPROACH_SPEED       = 35
APPROACH_TIMEOUT_SEC = 4.0   # yaklaşma fazı bu süreyi aşarsa fallback fren

# ---------------------------------------------------------------------------
# Turuncu engel araç (sollama — 20×30×25 cm)
# ---------------------------------------------------------------------------
ORANGE_HSV_LOW  = (5,  140, 80)
ORANGE_HSV_HIGH = (20, 255, 255)  # H üst sınırı 20 → sarı ton (H≥22) ile çakışmaz
ORANGE_MIN_AREA = 1500   # px² — tetiklemek için minimum blob alanı

# ---------------------------------------------------------------------------
# Sollama manevra parametreleri
# ---------------------------------------------------------------------------
OVERTAKING_STEER_BIAS = 60   # sola geçiş için px cinsinden yapay hata
OVERTAKING_CROSS_SEC  = 1.2  # merkez çizgiyi geçme süresi (s)
OVERTAKING_PASS_SEC   = 2.5  # turuncu aracın yanından geçme süresi (s)
OVERTAKING_RETURN_SEC = 1.2  # sağ şeride dönme süresi (s)
OVERTAKING_SPEED      = 40   # sollama sırasında hız (%)

# ---------------------------------------------------------------------------
# Park etme (kırmızı slot — her zaman kırmızı, PDF'te onaylı)
# ---------------------------------------------------------------------------
PARKING_HSV_LOW1  = (0,   120, 80)
PARKING_HSV_HIGH1 = (10,  255, 255)
PARKING_HSV_LOW2  = (160, 120, 80)
PARKING_HSV_HIGH2 = (180, 255, 255)
PARKING_MIN_AREA     = 3000   # park manevrası sırasında min kırmızı blob alanı
PARKING_TRIGGER_AREA = 6000   # PARKING durumuna geçmek için eşik alanı
PARKING_ROI_TOP      = 240    # kırmızı slotları aramak için alt ROI y başlangıcı
# Park bölgesi tetikleyicisi: kırmızı blobun bbox alt-kenarı ROI'nin bu oranından
# büyük olmalı (yakın olduğunu garanti eder, uzaktaki kırmızı objelere takılmaz).
# Ayrıca turuncu engel aynı karede varsa park tetiklenmez (renk overlap koruması).
PARKING_NEAR_BOTTOM_RATIO = 0.70
PARKING_SPEED        = 30     # park ederken hız (%)
PARKING_CENTER_TOL   = 40     # kare merkezine px cinsinden tolerans

# ---------------------------------------------------------------------------
# Sarı araç — sollama YASAĞI bölgesinde karşı şerit engeli (20×45×25 cm)
# ---------------------------------------------------------------------------
# Kural: sarı araçlar (20×45×25 cm) sollama yasağı bölgesine yerleştirilir.
# Turuncu ile çakışmaması için H≥22'den başlıyoruz.
YELLOW_HSV_LOW  = (22, 100, 80)
YELLOW_HSV_HIGH = (38, 255, 255)
YELLOW_MIN_AREA = 1500   # Sarı blob için minimum alan (px²)

# ---------------------------------------------------------------------------
# Levha (işaret tabelası) tespiti — sinyal ROI içinde
# ---------------------------------------------------------------------------
# Mavi arka planlı levhalar: Park (P) ve Çıkmaz Yol (T) işaretleri
# Kılavuza göre levha boyutu: 13 cm genişlik, toplam 20 cm yükseklik (sap dahil)
SIGN_BLUE_HSV_LOW  = (100, 120, 80)   # Mavi levha alt HSV eşiği
SIGN_BLUE_HSV_HIGH = (130, 255, 255)  # Mavi levha üst HSV eşiği
SIGN_MIN_AREA      = 200              # Küçük levhalar için düşük alan eşiği (px²)

# ---------------------------------------------------------------------------
# Yansıma direnci — CLAHE + sütun sürekliliği (lane.py)
# ---------------------------------------------------------------------------
# CLAHE (Contrast Limited Adaptive Histogram Equalization):
#   Spot ışık / parlak zemin yansımalarını normalize eder.
#   clipLimit: 1.0 = kapalı  |  2.5 = dengeli  |  4.0 = güçlü (gürültü artar)
CLAHE_CLIP_LIMIT      = 2.5   # CLAHE kontrast sınırı
CLAHE_TILE_SIZE       = 8     # CLAHE kutucuk boyutu (piksel, 8 = önerilen)

# Sütun sürekliliği ağırlığı:
#   Kuş bakışı görüntüsünde bir sütun ancak LANE_CONTINUITY_RATIO * yükseklik kadar
#   beyaz piksel içeriyorsa tam ağırlık alır; daha azsa ağırlık orantılı düşürülür.
#   Şerit çizgileri dikey yönde sürekli → yüksek ağırlık.
#   Noktasal yansımalar → düşük ağırlık → histogram'dan baskılanır.
LANE_CONTINUITY_RATIO = 0.15  # [0.0–0.5]; düşük = daha permissif

# ---------------------------------------------------------------------------
# Çift bölge şerit takibi (yakın / uzak ağırlıklı hata)
# ---------------------------------------------------------------------------
# Kuş bakışı dikey olarak üç bölgeye ayrılır:
#   Üst  LANE_FAR_RATIO   → uzak görüş  : dönüş tahmini (look-ahead)
#   Orta                  → kullanılmaz
#   Alt  LANE_NEAR_RATIO  → yakın görüş : anlık yanal konum / ortalama
#
# Nihai hata = LANE_NEAR_WEIGHT × yakın_hata + LANE_FAR_WEIGHT × uzak_hata
# Toplamları 1.0 olması gerekmez; eksik bölge varsa diğeri tek başına kullanılır.
LANE_FAR_RATIO   = 0.35   # Kuş bakışının üst bu oranı = uzak görüş
LANE_NEAR_RATIO  = 0.40   # Kuş bakışının alt bu oranı = yakın görüş
LANE_FAR_WEIGHT  = 0.60   # Uzak hata ağırlığı  (dönüş öngörüsü)
LANE_NEAR_WEIGHT = 0.40   # Yakın hata ağırlığı (anlık ortalama)
