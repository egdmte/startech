# Entegrasyon Rehberi: Taktikleri Projeye Ekleme

## FAZA 1: Motion Smoothing (Uygulaması En Kolay - Başlayın Buradan)

### Adım 1: motor.py'yi Değiştir

**Dosya:** `motor.py`

**Ekle (sınıf tanımından sonra):**

```python
class SmoothedMotorDriver(MotorDriver):
    """Motor hızlarını yumuşatarak jittering'i azaltır."""
    
    def __init__(self, smoothing_factor=0.7):
        super().__init__()
        self.prev_left = 0.0
        self.prev_right = 0.0
        self.smoothing = smoothing_factor
    
    def set_speed(self, left: float, right: float) -> None:
        """Exponential moving average ile hızları yumuşat."""
        # Yumuşatılmış değerler
        left_smooth = (self.smoothing * left + 
                      (1 - self.smoothing) * self.prev_left)
        right_smooth = (self.smoothing * right + 
                       (1 - self.smoothing) * self.prev_right)
        
        # Önceki MotorDriver sınıfını çalıştır
        super().set_speed(left_smooth, right_smooth)
        
        # Hafızaya al
        self.prev_left = left_smooth
        self.prev_right = right_smooth
```

### Adım 2: main.py'yi Güncelle

**Değiştir:**
```python
# Eski (motorun) yerine:
motor = MotorDriver()

# Yeni:
motor = SmoothedMotorDriver(smoothing_factor=0.7)
```

### Adım 3: Ayar Yapma

İlk denemede `smoothing_factor` değerlerini test et:

| Factor | Etki | Ne zaman kullan |
|--------|------|-----------------|
| 0.5 | Az yumuşatma, hızlı tepki | Virajlar sık |
| 0.7 | Dengeli (önerilen) | Normal koşullar |
| 0.9 | Çok yumuşatma, yavaş tepki | Düz yollar |

---

## FAZA 2: Dynamic Speed Control

### Adım 1: config.py'ye Ekle

```python
# Dinamik hız kontrolü parametreleri
SPEED_CURVE_FACTOR = 0.5      # Eğride hız azalma oranı (0-1)
SPEED_ERROR_FACTOR = 0.02     # Her piksel hata için hız düşmesi
MIN_DYNAMIC_SPEED = 20        # En düşük hız
```

### Adım 2: controller.py'yi Değiştir

**compute() metodunun içinde, hız hesaplanırken:**

```python
# Eski kod (line ~65):
speed = float(BASE_SPEED - K_SPEED * abs(error))

# Yeni kod:
# Hata ve eğriye göre dinamik hız
error_factor = max(0.5, 1.0 - (abs(error) / 50.0))
speed = float(BASE_SPEED * error_factor)
speed = float(np.clip(speed, MIN_SPEED, MAX_SPEED))
```

### Adım 3: Test Komutu

```bash
python pd_tune.py
# Eşik değerleri döngülerle test et
```

---

## FAZA 3: Adaptive PID (İleri - Opsiyonel)

### Adım 1: controller.py'ye Yeni Sınıf Ekle

```python
import collections

class AdaptivePDController(PDController):
    """Hata volatilitesine göre KD dinamik ayarlayan PID."""
    
    def __init__(self):
        super().__init__()
        self.error_history = collections.deque(maxlen=10)
    
    def compute(self, error) -> tuple:
        """Volatiliteyi kullanarak KD'yi adapt et."""
        global KD
        
        # Hata geçmişi güncelle
        if error is not None:
            self.error_history.append(error)
        else:
            self.error_history.append(0)
        
        # Volatiliteyi hesapla
        if len(self.error_history) >= 5:
            volatility = np.std(list(self.error_history))
        else:
            volatility = 0
        
        # Volatilite yüksekse KD'yi artır
        kd_original = KD
        if volatility > 50:
            KD = KD * 1.2
        elif volatility > 30:
            KD = KD * 1.05
        # else: KD değişmez
        
        # Normal compute
        left, right = super().compute(error)
        
        # KD'yi geri al
        KD = kd_original
        
        return left, right
```

### Adım 2: Aktivasyon

main.py'de:
```python
# Eski:
ctrl = PDController()

# Yeni (test için):
ctrl = AdaptivePDController()
```

---

## FAZA 4: Battery Monitoring (Opsiyonel ama Güvenli)

### Adım 1: Yeni Dosya Oluştur

**Dosya:** `battery.py`

```python
# battery.py - Pil durumunu izler
import time
try:
    from machine import ADC, Pin  # Raspberry Pi Pico
    BOARD_TYPE = 'pico'
except ImportError:
    BOARD_TYPE = 'pi'  # Raspberry Pi 4/5
    ADC = None

class BatteryMonitor:
    def __init__(self, adc_pin=26):
        self.voltage_history = []
        self.BOARD_TYPE = BOARD_TYPE
        
        if self.BOARD_TYPE == 'pico':
            self.adc = ADC(Pin(adc_pin))
        else:
            self.adc = None  # Pi'de simülasyon
    
    def get_voltage(self):
        """Mevcut pil voltajını oku."""
        if self.BOARD_TYPE == 'pico':
            raw = self.adc.read_u16()
            voltage = (raw / 65535) * 3.3 * 3  # Direnç bölücü
        else:
            # Simülasyon: sabit voltaj
            voltage = 8.4
        
        self.voltage_history.append(voltage)
        if len(self.voltage_history) > 20:
            self.voltage_history.pop(0)
        
        return voltage
    
    def get_speed_factor(self):
        """Voltaja göre hız kompenzasyonu (1.0 = normal)."""
        if not self.voltage_history:
            return 1.0
        
        avg_voltage = sum(self.voltage_history) / len(self.voltage_history)
        
        if avg_voltage < 7.0:
            print(f"🔴 UYARI: Çok düşük pil ({avg_voltage:.2f}V)")
            return 1.5
        elif avg_voltage < 7.5:
            print(f"🟡 Düşük pil ({avg_voltage:.2f}V)")
            return 1.3
        elif avg_voltage < 8.0:
            return 1.1
        else:
            return 1.0
    
    def is_critical(self):
        """Pil kritik mi?"""
        if not self.voltage_history:
            return False
        return sum(self.voltage_history) / len(self.voltage_history) < 6.5

# Kullanım örneği
if __name__ == "__main__":
    battery = BatteryMonitor()
    for i in range(10):
        voltage = battery.get_voltage()
        factor = battery.get_speed_factor()
        print(f"Voltaj: {voltage:.2f}V, Hız Faktörü: {factor:.2f}")
        time.sleep(1)
```

### Adım 2: main.py'ye Entegre Et

```python
from battery import BatteryMonitor

battery = BatteryMonitor()

# Ana döngüde (her frame):
voltage = battery.get_voltage()
speed_factor = battery.get_speed_factor()

# Hızları kompenzasyonla uygula
motor.set_speed(
    left * speed_factor,
    right * speed_factor
)

if battery.is_critical():
    print("Pil kritik! Yarışmayı durdur.")
    motor.brake()
    break
```

---

## FAZA 5: Parking Pre-Detection

### Adım 1: events.py'ye Ekle

```python
class ParkingPreDetector:
    """Park etme bölgesine yaklaşıldığını önceden tespit eder."""
    
    def __init__(self):
        from config import PARKING_ROI_TOP, SIGN_BLUE_HSV_LOW, SIGN_BLUE_HSV_HIGH
        self.roi_top = PARKING_ROI_TOP
        self.blue_low = np.array(SIGN_BLUE_HSV_LOW)
        self.blue_high = np.array(SIGN_BLUE_HSV_HIGH)
    
    def detect(self, frame):
        """Mavi park işareti ara."""
        roi = frame[:self.roi_top + 50, :]
        
        if roi.size == 0:
            return False
        
        hsv_roi = cv2.cvtColor(roi, cv2.COLOR_RGB2HSV)
        blue_mask = cv2.inRange(hsv_roi, self.blue_low, self.blue_high)
        
        detected = blue_mask.sum() > 500
        
        if detected:
            print("🅿️ Park bölgesine yaklaşılıyor...")
        
        return detected
```

### Adım 2: main.py'de Kullan

```python
from events import ParkingPreDetector

parking_pre = ParkingPreDetector()

# Ana döngüde:
if parking_pre.detect(frame):
    print("Park hazırlığı: Hızı düşür")
    # Kontrol yazılımında park modu hazırla
```

---

## TEST VE DOĞRULAMA

### Hızlı Entegrasyon Kontrol Listesi

```python
# test_integration.py
def test_motor_smoothing():
    """Motor yumuşatmasını test et."""
    motor = SmoothedMotorDriver(0.7)
    
    # Test: Ani hız değişimi
    motor.set_speed(100, 100)
    motor.set_speed(0, 0)
    motor.set_speed(50, 50)
    print("✅ Motor smoothing OK")

def test_dynamic_speed():
    """Dinamik hız kontrolünü test et."""
    ctrl = PDController()
    
    # Farklı hatalarla test
    for error in [0, 10, 50, 100]:
        left, right = ctrl.compute(error)
        print(f"Error: {error:3d}px → Speed: {abs(left):6.1f}")
    print("✅ Dynamic speed OK")

def test_battery():
    """Pil izlemeyi test et."""
    battery = BatteryMonitor()
    
    voltage = battery.get_voltage()
    factor = battery.get_speed_factor()
    print(f"Voltaj: {voltage:.2f}V → Faktör: {factor:.2f}")
    print("✅ Battery monitoring OK")

# Çalıştır:
if __name__ == "__main__":
    test_motor_smoothing()
    test_dynamic_speed()
    test_battery()
    print("\n🎯 Tüm testler geçti!")
```

### Yarışmada Etkinleştirme Sırası

1. **Hemen Etkinleştir (Düşük Risk):**
   - [ ] Motion Smoothing
   - [ ] Battery Monitoring

2. **Test Ettikten Sonra:**
   - [ ] Dynamic Speed Control
   - [ ] Parking Pre-Detection

3. **İleri (Zaman Varsa):**
   - [ ] Adaptive PID
   - [ ] Dual Lane Detector

---

## YAPILANDIRMA ŞABLONU

**config.py'ye eklenecek yeni parametreler:**

```python
# === MOTOR SMOOTHING ===
MOTOR_SMOOTHING_FACTOR = 0.7

# === DYNAMIC SPEED ===
SPEED_CURVE_FACTOR = 0.5
SPEED_ERROR_THRESHOLD = 50  # piksel

# === BATTERY ===
BATTERY_ADC_PIN = 26
BATTERY_CRITICAL = 6.5  # volt
BATTERY_COMPENSATION = True

# === PARKING ===
PARKING_PRE_DETECTION = True
PARKING_PRE_ROI_BUFFER = 50  # piksel
```

---

## SORUN GİDERME

| Problem | Çözüm |
|---------|-------|
| Motor çok yavaş hareket ediyor | smoothing_factor'ü 0.5'e düşür |
| Motor hızı düşüyor | Pilini kontrol et; BATTERY_CRITICAL'ı test et |
| Park algılaması çalışmıyor | PARKING_ROI_TOP'ı kalibrasyonla |
| Virajlarda sallanıyor | Adaptive PID'yi etkinleştir |
| Şerit kayboluyor | Dual Lane Detector'ü ekle |

---

## PERFORMANS ETKİSİ BEKLENTİSİ

| Taktik | CPU Yükü | Hız Artışı | Stabilite |
|--------|----------|-----------|-----------|
| Motion Smoothing | % | +15-20% | +++ |
| Dynamic Speed | ++ | +10% | ++ |
| Adaptive PID | +++ | +20% | ++ |
| Battery Monitor | + | Negatif (faydalı) | ++ |
| Parking Pre-Det | ++ | 0% | ++ |

