# Otonom Araç Projesine Eklenebilecek Taktikler

## 1. ADAPTIVE PID TUNING (Uyarlanabilir PID Ayarlama)

### Sorun
Mevcut PID kontrolörü statik kazançlar kullanıyor. Farklı hız ve dönüş senaryolarında optimal olmayabilir.

### Çözüm
```python
# controller.py'ye eklenecek
class AdaptivePDController(PDController):
    def __init__(self):
        super().__init__()
        self.error_history = collections.deque(maxlen=10)
        self.speed = BASE_SPEED
    
    def compute(self, error):
        """Hatanın büyüklüğüne göre KP/KD dinamik ayarlama"""
        self.error_history.append(error if error else 0)
        
        # Hata volatilitesini hesapla
        if len(self.error_history) > 1:
            volatility = np.std(list(self.error_history))
        else:
            volatility = 0
        
        # Volatilite yüksekse KD'yi artır (sönümleme)
        kd_adaptive = KD * (1 + volatility / 100)
        
        # Orijinal compute'u çalıştır
        left, right = super().compute(error)
        
        return left, right
```

**Avantajları:**
- Kargo hızında daha iyi dengeyi
- Virajlarda daha stabil hareket
- Ani değişimlere hızlı tepki

---

## 2. LANE DETECTION'DA REDUNDANCY (Çift Şerit Takibi)

### Sorun
Tek çerit algılamasında gölge/parlaklık değişimleri sorun oluşturabiliyor.

### Çözüm
```python
# lane.py'ye eklenecek
class DualLaneDetector(LaneDetector):
    def __init__(self):
        super().__init__()
        self.canny_detector = True
    
    def process(self, frame: np.ndarray) -> tuple:
        """HSV + Canny edge detection kombinasyonu"""
        # Orijinal HSV metodu
        error_hsv, debug_hsv = super().process(frame)
        
        # Canny edge detection yedek metod
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        
        # Canny'de lane çizgilerini bul
        bird = cv2.warpPerspective(edges, self.M, (self.bird_w, self.bird_h))
        
        # Eğer HSV zayıfsa Canny'e geç
        if error_hsv is None:
            return self._process_canny(bird), debug_hsv
        
        return error_hsv, debug_hsv
    
    def _process_canny(self, bird_edges):
        histogram = np.sum(bird_edges, axis=0)
        # ... şerit bulma mantığı
```

**Avantajları:**
- Aşırı parlak/koyu alanlarda dayanıklılık
- Beyaz şerit yokken gri çizgiler kullanılabilir
- Weathering conditions'a daha toleranslı

---

## 3. PREDICTION-BASED STEERING (Tahmin Tabanlı Yönlendirme)

### Sorun
PID mevcut hataya tepki veriyor; öngörülü hareket yapmıyor.

### Çözüm
```python
# controller.py'ye eklenecek
class PredictivePDController(PDController):
    def __init__(self):
        super().__init__()
        self.error_buffer = collections.deque(maxlen=5)
    
    def compute(self, error):
        """Hata trendini tahmin et"""
        if error is not None:
            self.error_buffer.append(error)
        
        # Doğrusal tahmin
        if len(self.error_buffer) > 2:
            errors = np.array(list(self.error_buffer))
            # Basit trend analizi
            trend = errors[-1] - errors[0]
            predicted_error = error + (trend / len(self.error_buffer)) if error else 0
        else:
            predicted_error = error
        
        # Tahmini hata ile kontrol
        left, right = super().compute(predicted_error)
        
        return left, right
```

---

## 4. MULTI-TASK EVENT DETECTION (Eşzamanlı Olay Tespiti)

### Sorun
events.py yalnızca ardışık olayları tespit ediyor; paralel olaylar (trafik ışığı + yaya geçidi) için iyileştirilebilir.

### Çözüm
```python
# events.py'ye eklenecek ek sınıf
class ParallelEventDetector:
    def __init__(self):
        self.signal_detector = SignalDetector()
        self.crosswalk_detector = CrosswalkDetector()
        self.priority_queue = []
    
    def detect(self, frame, lane_center):
        """Tüm olayları paralel olarak tespit et"""
        events = []
        
        # Signal detection
        signal = self.signal_detector.detect(frame)
        if signal:
            events.append(('traffic_signal', signal['color'], 100))
        
        # Crosswalk detection
        crosswalk = self.crosswalk_detector.detect(frame)
        if crosswalk:
            events.append(('crosswalk', crosswalk['position'], 50))
        
        # Prilarite göre sırala
        events.sort(key=lambda x: x[2], reverse=True)
        
        return events[0] if events else None
```

---

## 5. DYNAMIC SPEED CONTROL (Dinamik Hız Kontrolü)

### Sorun
BASE_SPEED sabit; virajlarda yavaşlamıyor, düz yollarda hızlandırılamıyor.

### Çözüm
```python
# controller.py'ye eklenecek
def compute_dynamic_speed(self, error, curve_severity):
    """Hata ve eğrinin keskinliğine göre hız belirle"""
    
    # Eğri keskinliğine göre hız faktörü
    curve_factor = 1.0 - (abs(curve_severity) / 100.0) * 0.5
    
    # Hata büyüklüğüne göre hız
    error_factor = max(0.5, 1.0 - (abs(error) / 50.0))
    
    # Dinamik hız
    dynamic_speed = BASE_SPEED * curve_factor * error_factor
    
    return np.clip(dynamic_speed, MIN_SPEED, MAX_SPEED)
```

---

## 6. PARKING AREA PRE-DETECTION (Park Öncesi Ön Tespit)

### Sorun
Park etme bölgesine girerken renk tayini hemen başlanıyor; erken hazırlık yapılamıyor.

### Çözüm
```python
# events.py'ye eklenecek
class ParkingPreDetector:
    def __init__(self):
        self.parking_sign_region = config.PARKING_ROI_TOP
        self.pre_alert_distance = 200  # piksel
    
    def pre_detect(self, frame, lane_center):
        """Park etme bölgesine yaklaşıldığını tespit et"""
        roi_top = int(self.parking_sign_region)
        roi = frame[roi_top:roi_top+100, :]
        
        # Mavi park işareti ara
        blue_hsv_low = np.array(config.SIGN_BLUE_HSV_LOW)
        blue_hsv_high = np.array(config.SIGN_BLUE_HSV_HIGH)
        
        hsv_roi = cv2.cvtColor(roi, cv2.COLOR_RGB2HSV)
        blue_mask = cv2.inRange(hsv_roi, blue_hsv_low, blue_hsv_high)
        
        if blue_mask.sum() > 500:
            return 'parking_ahead'
        
        return None
```

---

## 7. MOTION SMOOTHING (Hareket Yumuşatma)

### Sorun
Kontrol sinyalleri jittery olabilir; motor terimleri sallanır.

### Çözüm
```python
# motor.py'ye eklenecek
class SmoothedMotorDriver(MotorDriver):
    def __init__(self, smoothing_factor=0.7):
        super().__init__()
        self.prev_left = 0
        self.prev_right = 0
        self.smoothing = smoothing_factor
    
    def set_speed(self, left: float, right: float) -> None:
        """Exponential moving average ile yumuşatma"""
        left_smooth = (self.smoothing * left + 
                      (1 - self.smoothing) * self.prev_left)
        right_smooth = (self.smoothing * right + 
                       (1 - self.smoothing) * self.prev_right)
        
        super().set_speed(left_smooth, right_smooth)
        
        self.prev_left = left_smooth
        self.prev_right = right_smooth
```

---

## 8. CALIBRATION VALIDATION (Kalibrasyon Doğrulama)

### Sorun
Kalibrasyon hatalı olabilir; ilk turda detect edilmez.

### Çözüm
```python
# Yeni dosya: validate_calibration.py
class CalibrationValidator:
    def __init__(self):
        self.frame_count = 0
        self.lane_detections = []
    
    def validate(self, frame):
        """İlk 100 karede şerit deteksiyonunun stabilitesini kontrol et"""
        lane = LaneDetector()
        error, _ = lane.process(frame)
        
        if self.frame_count < 100:
            if error is not None:
                self.lane_detections.append(abs(error))
            self.frame_count += 1
        else:
            # İstatistik kontrol
            if len(self.lane_detections) < 50:
                print("⚠️ UYARI: Yetersiz şerit deteksiyonu!")
                return False
            
            stability = np.std(self.lane_detections)
            if stability > 100:
                print(f"⚠️ UYARI: Düşük stabilite ({stability:.1f} px)")
                return False
            
            print(f"✅ Kalibrasyon OK (Stabilite: {stability:.1f} px)")
            return True
        
        return None
```

---

## 9. BATTERY VOLTAGE MONITORING (Pil Voltaj İzleme)

### Sorun
Pil düşerse motor hızları düşer; kontroller başarısız olur.

### Çözüm
```python
# Yeni: battery_monitor.py
class BatteryMonitor:
    def __init__(self, adc_pin=26):
        self.adc = ADC(Pin(adc_pin))
        self.voltage_history = collections.deque(maxlen=20)
    
    def get_voltage(self):
        """ADC okuma (Raspberry Pi Pico örneği)"""
        raw = self.adc.read_u16()
        voltage = (raw / 65535) * 3.3 * 3  # 3.3V * 3 bölücü
        self.voltage_history.append(voltage)
        return voltage
    
    def get_speed_compensation(self):
        """Voltaja göre hız kompenzasyonu"""
        avg_voltage = np.mean(list(self.voltage_history))
        
        if avg_voltage < 8.0:
            print(f"🔋 Düşük pil: {avg_voltage:.2f}V")
            return 1.2  # 20% hız artışı
        elif avg_voltage < 7.0:
            return 1.5  # 50% artış
        else:
            return 1.0  # Normal
```

---

## 10. OVERTAKING OPTIMIZATION (Sollama Optimizasyonu)

### Sorun
Sollama sabit parametrelerle; engel mesafesine duyarlı değil.

### Çözüm
```python
# controller.py'ye eklenecek
def adaptive_overtaking_steer(self, obstacle_distance):
    """Engel mesafesine göre sollama açısı"""
    if obstacle_distance > 100:
        return 60  # Uzak: normal sollama
    elif obstacle_distance > 50:
        return 40  # Yakın: daha yumuşak
    else:
        return 0   # Çok yakın: sollama yapma, dur
```

---

## UYGULAMA ÖNCELIĞI

1. **Yüksek Etki, Düşük Çalışma:**
   - Motion Smoothing (#7)
   - Adaptive PID (#1)
   - Dynamic Speed (#5)

2. **Orta Etki, Orta Çalışma:**
   - Dual Lane Detector (#2)
   - Parking Pre-Detection (#6)
   - Battery Monitoring (#9)

3. **Gelişmiş (Zaman Varsa):**
   - Predictive Steering (#3)
   - Parallel Event Detection (#4)
   - Calibration Validation (#8)
   - Overtaking Optimization (#10)

---

## HIZLI TEST ÖNERİLERİ

### Motion Smoothing Testi
```bash
python pd_tune.py  # Smoothing factor ile
# 0.5 vs 0.7 vs 0.9 karşılaştır
```

### Speed Control Testi
```bash
python motor_balance_test.py
# Hızlı dönemeler test et
```

### Lane Stability Testi
```bash
python camera.py
# Farklı aydınlatmada 't' ile eşik göster
```

---

## İNTEGRASYON KONTROL LİSTESİ

- [ ] config.py'ye yeni parametreler ekle
- [ ] Test dosyaları oluştur
- [ ] Motor hızlandırması test et
- [ ] PID kazançlarını yeniden ayarla
- [ ] error_log.csv analizini güncelle
- [ ] Gerçek parkurda test et
