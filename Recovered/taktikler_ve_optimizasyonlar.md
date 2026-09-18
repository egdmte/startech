# Otonom Araç Sistemi: Taktikler ve Kod Optimizasyonları

## 1. ALGÍLAMA (PERCEPTION) OPTİMİZASYONLARI

### 1.1 Adaptif HSV Tuning
**Problem:** Değişken ışık koşullarında (güneş, gölge) beyaz şerit kaybı.

**Çözüm - lane.py'ye eklenecek:**
```python
# Dinamik HSV aralığı ayarlaması
def adaptive_hsv_range(self, frame):
    """Işık koşullarına göre HSV aralığını dinamik ayarla"""
    hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
    v_mean = hsv[:, :, 2].mean()
    
    # Parlaklığa göre eşik ayarı
    if v_mean > 200:  # Aşırı parlak
        WHITE_HSV_LOW = (0, 0, 160)
        WHITE_HSV_HIGH = (180, 60, 255)
    elif v_mean < 100:  # Karanlık
        WHITE_HSV_LOW = (0, 0, 80)
        WHITE_HSV_HIGH = (180, 100, 255)
    else:  # Normal
        WHITE_HSV_LOW = (0, 0, 130)
        WHITE_HSV_HIGH = (180, 90, 255)
    
    return WHITE_HSV_LOW, WHITE_HSV_HIGH
```

### 1.2 Multi-Channel Detection (İkili Algılama)
**Taktik:** Yalnızca HSV yerine RGB + canny edge detection kombinasyonu.

```python
def multi_channel_detection(self, bird):
    """HSV + Edge Detection = daha güvenilir"""
    # Kanal 1: HSV masking (mevcut)
    hsv = cv2.cvtColor(bird, cv2.COLOR_RGB2HSV)
    mask_hsv = cv2.inRange(hsv, np.array(WHITE_HSV_LOW), np.array(WHITE_HSV_HIGH))
    
    # Kanal 2: Edge detection
    gray = cv2.cvtColor(bird, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 100, 200)
    
    # Kanal 3: Morphological closing (mevcut)
    mask = cv2.morphologyEx(mask_hsv, cv2.MORPH_CLOSE, self._k_close)
    
    # Birleştir (AND işlemi = her iki kanala uymalı)
    combined = cv2.bitwise_and(mask, edges)
    return combined
```

### 1.3 Çift-Şerit Kalitesi Kontrolü
**Problem:** Tek şerit görünce yanlış pozisyon hesabı.

```python
def validate_lane_quality(self, left_peak, right_peak, left_valid, right_valid):
    """Şerit güvenilirliğini kontrol et"""
    if not (left_valid and right_valid):
        # Sadece bir şerit varsa, histogramda güç kontrolü
        histogram = np.sum(self.last_mask, axis=0)
        if histogram.max() < MIN_LANE_SIGNAL * 1.5:
            return None, False  # Çok zayıf algılama
    
    # Şeritler arasında makul mesafe kontrolü
    lane_width = right_peak - left_peak
    if not (100 < lane_width < 200):  # Önceden ölçülmüş gerçek genişlik
        return None, False
    
    return (left_peak, right_peak), True
```

---

## 2. KONTROL (CONTROL) OPTİMİZASYONLARI

### 2.1 Dinamik PID Kazançları
**Problem:** Tek PD değeri tüm koşullar için yeterli değil (düz → viraj).

**controller.py'ye eklenecek:**
```python
def compute_adaptive(self, error):
    """Hata büyüklüğüne göre KP/KD adaptif ayarlanır"""
    abs_error = abs(error) if error else 0
    
    # Küçük hata (düz yol) - hassas kontrol
    if abs_error < 10:
        kp_eff = KP * 0.8
        kd_eff = KD * 1.2
    # Orta hata (hafif viraj)
    elif abs_error < 30:
        kp_eff = KP
        kd_eff = KD
    # Büyük hata (keskin viraj) - agresif kontrol
    else:
        kp_eff = KP * 1.3
        kd_eff = KD * 1.5
    
    correction = kp_eff * error + kd_eff * derivative
    return correction
```

### 2.2 Hız-Viraj Koordinasyonu
**Taktik:** Viraja girerken hızı düşür, düz bölgede artır.

```python
def intelligent_speed(self, error, derivative):
    """Virajın sıklığına ve şiddetine göre hız ayarla"""
    sharpness = abs(derivative)  # Hata değişim hızı
    
    # Ani viraj = keskin hız düşüşü
    if sharpness > 50:
        return MIN_SPEED
    elif sharpness > 30:
        return BASE_SPEED - K_SPEED * abs(error) - 10  # ek 10 birim düş
    else:
        return BASE_SPEED - K_SPEED * abs(error)
```

### 2.3 Anti-Salınım (Anti-Oscillation)
**Problem:** Düşük KP → geri kalan sapma, yüksek KP → sürekli salınım.

```python
# controller.py'de mevcut CROSSING_KD_BOOST'u geliştir
def ultra_damping_mode(self):
    """Salınım algılandığında aşırı sönümleme"""
    # Eğer son 3 frame'de işaret değiştiyse = salınıyor
    if len(self.error_history) >= 3:
        signs = [e > 0 if e else self.prev_error > 0 
                 for e in self.error_history[-3:]]
        if signs.count(True) != len(signs):  # işaret değişti
            return KD * 3.0  # Normal 1.8 yerine 3.0
    return KD * _CROSSING_KD_BOOST
```

### 2.4 Gecikme Kompensasyonu
**Problem:** Kamera → işlem → motor = ~50ms gecikme = geç tepki.

```python
def predictive_control(self, error, derivative):
    """50ms sonrasını tahmin et"""
    dt = 0.05  # 50ms
    predicted_error = error + derivative * dt
    
    # Tahminli hataya göre düzelt
    correction = KP * predicted_error + KD * derivative
    return correction
```

---

## 3. GÖREV-SPESIFIK STRATEJİLER

### 3.1 Trafik Işığı (Görev 1)
**Mevcut:** 3 saniye içinde hareket → Sorun: Işık süresi değişkeni.

**Iyileştirme:**
```python
def smart_start(self):
    """Işık rengini algılayıp hareket et"""
    # Green dedektörü ekle
    green_hsv_low = (40, 80, 60)
    green_hsv_high = (90, 255, 255)
    
    while True:
        frame = camera.capture()
        hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
        
        # Işığın üst bölümünü kontrol et
        light_region = hsv[0:50, frame.shape[1]//2-20:frame.shape[1]//2+20]
        mask = cv2.inRange(light_region, green_hsv_low, green_hsv_high)
        
        if mask.sum() > 500:  # Yeşil algılandı
            return True
```

### 3.2 Yaya Geçidi & Hemzemin Geçit (Görev 2 & 4)
**Problem:** 30cm mesafe koşulu hassas. Overshoot riski.

```python
def gentle_stop(self, distance, target_distance=30):
    """30cm'de hassaslaşan durdurma"""
    if distance > 50:
        speed = 50  # Full speed
    elif distance > 30:
        speed = 30  # Orta hız
    elif distance > 15:
        speed = 15  # Yavaş yavaş
    elif distance > 5:
        speed = 5   # Çok yavaş
    else:
        speed = 0   # Dur
    
    return speed
```

### 3.3 Sollama (Görev 5) - KRITIK
**Problem:** Karşı araçla çarpma riski. PDF'de sollama yasağı var.

**Taktik - Güvenli Sollama:**
```python
def safe_overtake(self, detected_car_pos, overtak_zone_bounds):
    """3-aşamalı güvenli sollama"""
    
    # Aşama 1: Yaklaş
    self.motor.set_speed(40, 40)  # Sabit hızla araç arkasına git
    time.sleep(1)
    
    # Aşama 2: Sollama serbest bölgede misiniz?
    if not self.in_overtake_zone(overtak_zone_bounds):
        return False  # Riskli, hız düşür ve arkada kalıştır
    
    # Aşama 3: Sol şeride geç (kontrollü sapma)
    for _ in range(5):  # 0.5 saniye
        left, right = self.controller.compute(error=+60)  # +60px = sola çok sapma
        self.motor.set_speed(left, right)
        time.sleep(0.1)
    
    # Aşama 4: Sağa dönerek sollama tamamla
    for _ in range(5):
        left, right = self.controller.compute(error=-60)  # sağa dön
        self.motor.set_speed(left, right)
        time.sleep(0.1)
    
    return True
```

### 3.4 Çıkmaz Yol (Görev 6)
**Mevcut:** Tabela veya bölüm algılama → sağa dön.

**Iyileştirme - Maksimum İtiyat:**
```python
def dead_end_strategy(self, sign_detected, dead_end_ahead):
    """Çıkmaz emin olunca dön"""
    if sign_detected:
        # Hemen dönme, biraz daha ilerle ve şerit sonu kontrolü yap
        time.sleep(0.5)
        
        # Şerit sonu mu (white end)?
        if self.detect_lane_end():
            # Hızlı 180° dönüş
            self.motor.set_speed(-50, 50)  # Sol tekerlek geri, sağ ileri
            time.sleep(1.8)  # 180° döner
            self.motor.set_speed(60, 60)  # İleri git
            return True
```

### 3.5 Park Etme (Görev 7) - PUAN MAKSİMİZASYON
**Problem:** Kırmızı alana tam ortalanma zor. Tolerans var mı?

```python
def precision_parking(self, red_area_bounds):
    """Kırmızı alan merkezine hassas park"""
    red_area_center = (red_area_bounds.left + red_area_bounds.right) // 2
    
    # Park bölgesine yaklaş
    while not self.close_to_park_zone():
        self.motor.set_speed(30, 30)
    
    # Fine-tuning: alan merkezine hizala
    for _ in range(20):  # 2 saniye hassas ayar
        current_x = self.get_car_center_x()
        error = red_area_center - current_x
        
        # Mini PD kontroller (normal kontrol kapalı)
        left = 20 + error * 0.1
        right = 20 - error * 0.1
        self.motor.set_speed(left, right)
        time.sleep(0.1)
    
    self.motor.brake()
```

---

## 4. MOTOR KALIBRASYONU (motor.py)

### 4.1 Hız Ölçeklendirme Matrisi
**Problem:** LEFT_TRIM/RIGHT_TRIM lineer değil, türev hızlarda farklı.

```python
def nonlinear_speed_curve(self, speed):
    """Küçük hızlarda ölü bölge (dead zone) telafisi"""
    dead_zone = 20  # 0-20% hiç hareket etmiyor
    
    if abs(speed) < dead_zone:
        return 0
    
    # 20% altında hızlı yükseliş, sonra doğrusal
    if abs(speed) < 50:
        return (speed - dead_zone * sign(speed)) * 1.3
    else:
        return speed
```

### 4.2 Motor Karşılığı Tablosu
```python
MOTOR_RESPONSE_MAP = {
    "low_speed": {"left": 1.05, "right": 1.00},      # Düşük hız
    "medium_speed": {"left": 1.02, "right": 1.00},   # Orta hız
    "high_speed": {"left": 1.00, "right": 1.00},     # Yüksek hız
}
```

---

## 5. SENSÖR FÜZYONU (Kameranın Ötesinde)

### 5.1 Kestirim Sensörü (Virtual Sensor)
**Taktik:** Tarihçeyi kullanarak kaybolan şeridi tahmin et.

```python
class LaneMemory:
    def __init__(self):
        self.trajectory_history = []  # Son 10 frame'in pozisyonu
    
    def predict_next_lane(self):
        """Eğri uygulaması ile gelecek şerit pozisyonunu tahmin et"""
        if len(self.trajectory_history) < 3:
            return None
        
        x = np.arange(len(self.trajectory_history))
        y = np.array(self.trajectory_history)
        z = np.polyfit(x, y, 2)  # 2. derece polinom
        p = np.poly1d(z)
        
        next_lane_pos = p(len(self.trajectory_history))
        return int(next_lane_pos)
```

### 5.2 İmplicit Hız Sensörü
**Fikir:** Şerit kaymadan hızı tahmin et.

```python
def estimate_speed(self, frame_shift):
    """Şeritlerin hareket hızından araç hızını tahmin et"""
    # frame_shift = bu frame'de şerit kaç pixel kaydı
    # piksel/frame → cm/s'ye çevir
    estimated_speed = frame_shift * (PIXELS_TO_CM_RATIO) * (FPS)
    return estimated_speed
```

---

## 6. YAZILIM MİMARİSİ İYİLEŞTİRMELERİ

### 6.1 İlk Olayı Döngü Ayrımlaması
**Problem:** Mainloop'ta her frame işlem → CPU yükü.

```python
# main.py'de
EVENT_SKIP_FRAMES = 3  # Zaten var

# Iyileştirme: Dinamik skip
def adaptive_skip():
    """CPU kullanım % ise skip artır"""
    if cpu_usage > 80:
        EVENT_SKIP_FRAMES = 5
    elif cpu_usage < 40:
        EVENT_SKIP_FRAMES = 2
```

### 6.2 Paralel İşleme (Multithread)
```python
import threading

class ParallelProcessing:
    def __init__(self):
        self.frame_thread = threading.Thread(target=self.capture_loop)
        self.control_thread = threading.Thread(target=self.control_loop)
        self.frame_queue = queue.Queue(maxsize=2)
    
    def capture_loop(self):
        """Kamera başında"""
        while True:
            frame = camera.capture()
            try:
                self.frame_queue.put_nowait(frame)
            except queue.Full:
                pass  # Yeni frame bekleniyor
    
    def control_loop(self):
        """Kontrol thread'i"""
        while True:
            frame = self.frame_queue.get()
            error, _ = detector.process(frame)
            left, right = controller.compute(error)
            motor.set_speed(left, right)
```

---

## 7. HATA AYIKLAMA & TELEMETRI

### 7.1 Geliştirilmiş Logging
```python
# logger.py'ye ekle
class TelemetryLogger:
    def log_frame(self, error, left_speed, right_speed, fps):
        """Her frame'i detaylı kaydet"""
        self.data.append({
            "timestamp": time.time(),
            "error_px": error,
            "left_speed": left_speed,
            "right_speed": right_speed,
            "fps": fps,
            "derivative": error - self.prev_error,
        })
```

### 7.2 Real-Time Görselleştirme
```python
def visualize_control(frame_rgb, error, kp_term, kd_term, correction):
    """Kontrol terimlerini görüntüye yaz"""
    debug_frame = frame_rgb.copy()
    h, w = debug_frame.shape[:2]
    
    # Hata göstergesi
    cv2.line(debug_frame, (w//2, 0), (w//2, h), (0, 255, 0), 2)  # Orta çizgi
    error_x = w//2 + error
    cv2.line(debug_frame, (int(error_x), 0), (int(error_x), h), (0, 0, 255), 2)
    
    # Sayısal bilgi
    cv2.putText(debug_frame, f"Err: {error:+.1f}px", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
    cv2.putText(debug_frame, f"KP: {kp_term:.1f}  KD: {kd_term:.1f}", (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
    
    return debug_frame
```

---

## 8. UYGULANMA PRİYORİTESİ (Zaman Baskısında)

| Sıra | Taktik | Kazanç | Zorluk |
|------|--------|--------|--------|
| **1** | Adaptif HSV tuning | +30 puan | Düşük |
| **2** | Hız-viraj koordinasyonu | +20 puan | Düşük |
| **3** | Çıkmaz yol güvenliği | +15 puan | Orta |
| **4** | Sollama optimizasyonu | +25 puan | Yüksek |
| **5** | Park etme hassasiyeti | +15 puan | Orta |
| **6** | Multi-channel detection | +20 puan | Yüksek |
| **7** | Paralel işleme | +10 FPS | Yüksek |

---

## 9. HIZLI TEST ŞABLONU

```bash
# pd_tune.py'yi çalıştırır ve KP/KD bulur
python pd_tune.py

# Motor dengesi kontrol eder
python motor_balance_test.py

# HSV değerlerini ayarlar
python hsv_tune.py

# Perspektif eğriltmeyi kalibrer
python calibrate.py

# Kamerası kontrol eder
python camera.py
```

---

## ÖZET: Yarışmadan Önce Yapılacaklar

✅ **Kesinlikle yapın:**
1. Motor trim değerlerini tekrar ölçün (düz gidiş testi)
2. HSV aralığını gerçek pistin ışığında ayarlayın
3. PD kazançlarını gerçek hız testinde optimize edin
4. Park etme sensörü eğrileri ölçün

⚠️ **Deneyebilirseniz:**
1. Adaptif HSV (ışık değişkenliği için)
2. Hız-viraj koordinasyonu
3. Çıkmaz yol emin olduktan sonra dönüş

🚫 **Riskli (yarışma gününde test etmeyin):**
1. Paralel işleme (debug'u zorlaştırır)
2. Sollama agresif ayarı (kural ihlali riski)

---

**Not:** Tüm bu taktikleri **kodla değil konfigürasyon dosyasıyla** kontrol edin (config.py). Böylece yarışma sırasında hızlı ayar yapabilirsiniz.
