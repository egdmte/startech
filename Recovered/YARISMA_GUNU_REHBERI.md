# 🏁 YARIŞMA GÜNÜ KONTROL VE KALİBRASYON PROSEDÜRÜ
## MEB 2026 Otonom Araç — 30 Dakikalık Hazırlık Planı

---

## ⏰ ZAMAN TABLOSU

| Saat | Görev | Süre |
|---|---|---|
| T-30min | Motor Dengeleme | 5 min |
| T-25min | Kamera Kontrolü | 5 min |
| T-20min | PD Fine-tuning | 10 min |
| T-10min | Sistem Kontrolü | 10 min |
| T-0min | **BAŞLAT** | — |

---

## AŞAMA 1: MOTOR DENGELEME (5 dakika)

### Amaç
Araç düz giderken sola veya sağa sapmıyor mu kontrol etmek.

### Adımlar

1. **Arabayı Başlat**
   ```bash
   cd /path/to/otonomaraciste
   python motor_balance_test.py
   ```

2. **Çıktıyı Gözle**
   ```
   LEFT PWM: 50%  RIGHT PWM: 50%
   
   Test 1: SAĞA MI SAPIYOR? → NO ✓
   Test 2: SOLA MI SAPIYOR? → NO ✓
   ```

3. **Sapıyorsa Düzelt**
   
   **Eğer SAĞA sapmış:**
   ```python
   # config.py satır 100:
   RIGHT_TRIM_LOW  = 0.95   # 1.0 → 0.95 (sağ motoru azalt)
   ```
   Tekrar test et → Hâlâ sapmıyor mu? 0.93'e düşür.

   **Eğer SOLA sapmış:**
   ```python
   # config.py satır 98:
   LEFT_TRIM_LOW  = 0.95   # 1.0 → 0.95 (sol motoru azalt)
   ```

4. **Başarılı İşaret**
   ✅ Motor dengesi OK → AŞAMA 2'ye geç

---

## AŞAMA 2: KAMERA KONTROLÜ (5 dakika)

### Amaç
Beyaz şerit belirgin, siyah çizgiler siyah olmalı.

### Adımlar

1. **Kamera Programını Çalıştır**
   ```bash
   python camera.py
   ```

2. **Ekrana Bak**
   ```
   ┌─────────────────────────────────────┐
   │ KUŞBAKIŞI GÖRÜNÜM (Optimize)       │
   │                                     │
   │  🟥 BEYAZ ŞERİT (kırmızı)         │
   │  ⬛ SİYAH ASFALT (siyah)           │
   │                                     │
   │  err:±30px  V:145  (V = parlaklık) │
   │  Sol+Sağ                           │
   └─────────────────────────────────────┘
   ```

3. **V (Parlaklık) Değerini Not Et**
   ```
   V < 100  → Karanlık ortam
   100 ≤ V ≤ 200 → Normal
   V > 200  → Çok parlak
   ```

4. **Sorunlar ve Çözümleri**

   **Sorun: Beyaz şerit görünmüyor**
   ```python
   # config.py satır 51-60 (Adaptif HSV)
   
   # Eğer V < 100 (karanlık):
   WHITE_HSV_LOW_DARK = (0, 0, 60)  # 80 → 60 (daha düşük V eşiği)
   
   # Eğer V > 200 (parlak):
   WHITE_HSV_LOW_BRIGHT = (0, 0, 180)  # 160 → 180 (daha yüksek V eşiği)
   ```

   **Sorun: Çok gürültülü (siyah lekeler)**
   ```python
   # config.py satır 54-60
   WHITE_HSV_HIGH_DARK  = (180, 90, 255)  # 100 → 90 (S aralığını dar)
   WHITE_HSV_HIGH_BRIGHT = (180, 50, 255) # 60 → 50
   ```

5. **Başarılı İşaret**
   ✅ Şerit net, gürültü az → AŞAMA 3'e geç

---

## AŞAMA 3: PD FINE-TUNING (10 dakika)

### Amaç
Düz gidiş stabil, virajlarda salınım yok, dönüş tepkisi yeterli.

### Adımlar

1. **PD Tuning Programını Başlat**
   ```bash
   python pd_tune.py
   ```

2. **İnteraktif Testler**
   
   **Test A: Düz Gidiş (Hiçbir hata)**
   ```
   Q: "Düz gidiş sürüyor mü?" 
   
   ✅ EVET → OK
   ❌ HAYIR → KP azalt (0.60 → 0.55)
   ```

   **Test B: Virajlarda Salınım**
   ```
   Q: "Virajda sol-sağ-sol titretme yapıyor mu?"
   
   ✅ HAYIR → OK
   ❌ EVET → KD azalt (0.44 → 0.38)
   ```

   **Test C: Virajı Kaçırma**
   ```
   Q: "Virajı hızlı açamıyor mu? (gecikme)"
   
   ✅ HAYIR → OK
   ❌ EVET → KP artır (0.60 → 0.65)
   ```

3. **Örnek Ayarlamalar**
   
   | Sorun | Çözüm | config.py satır |
   |---|---|---|
   | Çok salınıyor | KD azalt (0.44 → 0.38) | 72 |
   | Virajı kaçıyor | KP artır (0.60 → 0.65) | 71 |
   | Kenarında kayıyor | KP_LARGE_ERROR_MULT artır (1.3 → 1.5) | 75 |

4. **Başarılı İşaret**
   ✅ Düz, virajlı, kavisli gidiş stabil → AŞAMA 4'e geç

---

## AŞAMA 4: SİSTEM KONTROLÜ (10 dakika)

### Amaç
Olay tespiti, durum makinesi, WiFi kapalı mı kontrol etmek.

### Adımlar

1. **Ana Programı Başlat**
   ```bash
   python main.py
   ```

2. **Ekran Çıktısı Kontrol**
   ```
   ┌──────────────────────────────────┐
   │ STATE: LANE_FOLLOWING            │
   │ Error: ±15px                     │
   │ Speed: 62%                       │
   │ FPS: 28                          │
   │ Lane Memory: 0/25 frames         │
   └──────────────────────────────────┘
   ```

3. **Kontrol Listesi**
   - [ ] FPS ≥ 25 (yeterli hız)
   - [ ] Error ±20px içinde (düz gidiş)
   - [ ] WiFi kapı (kurallar)
   - [ ] Pil şarjı %100

4. **Beklenen Davranışlar**
   
   | Olay | Beklenen Tepki |
   |---|---|
   | Kırmızı ışık | STOP → Durmak |
   | Yeşil ışık | GO → Hareket |
   | Yaya geçidi | WAIT 5 saniye |
   | Hız tümsek | SLOW 1.5 saniye |
   | Turuncu araç | OVERTAKE (viraj) |

5. **Hataları Logla**
   ```
   error_log.csv oluştuyor mu?
   Hata sayısı < 5 ise OK
   ```

---

## 🔴 ACIL DURUMLAR

### Motor Hiç Dönmüyor
```bash
# Motor test'i kontrol et
python motor_balance_test.py

# Eğer motor hiç dönmüyorsa:
# 1. Batarya kontrolü (voltaj ≥7V)
# 2. GPIO pinleri (config.py satır 110-115)
# 3. Motor sürücüsü (H-köprü devresinde kısır dize?)
```

### Şerit Hiç Görünmüyor
```bash
# Kamera test'i
python camera.py

# Ekranda sadece siyah görünüyorsa:
# - Objektif temiz mi?
# - Kamera yazılımı kurulu mu? (picamera2)
# - HSV aralığı çok dar mı?

# Hızlı çözüm:
WHITE_HSV_LOW_NORMAL = (0, 0, 60)    # Geniş aralık
WHITE_HSV_HIGH_NORMAL = (180, 255, 255)
```

### Tüm Kontroller Başarısız
```
❌ BAŞLATMA → Hemen dur, bağlantı kontrolü yap
- USB / Raspberry Pi bağlantısı
- Python 3.9+, OpenCV, numpy kurulu mu?
- Dosyalar doğru dizinde mi?
```

---

## ✅ BAŞLAMA ÖNCESİ KONTROL LİSTESİ

```
MOTOR:
  ☐ Motor testi başarılı (dengeleme OK)
  ☐ LEFT_TRIM / RIGHT_TRIM doğru
  
KAMERA:
  ☐ Beyaz şerit net görünüyor
  ☐ V (parlaklık) değeri normal (100-200)
  ☐ FPS ≥ 25
  
PD KONTROL:
  ☐ Düz gidiş sürüyor
  ☐ Virajlarda salınım yok
  ☐ Dönüş tepkisi yeterli
  
SİSTEM:
  ☐ WiFi KAPAL
  ☐ Batarya %100
  ☐ SD Kart / Storage OK
  ☐ error_log.csv temiz

OLAY TESPİTİ (isteğe bağlı):
  ☐ Trafik ışığı tanınıyor
  ☐ Yaya geçidi tanınıyor
  ☐ Çıkmaz yol tanınıyor
```

---

## 🎯 BAŞLAMA KOMUTU

```bash
# Tüm kontroller tamam → şu kodu çalıştır:
python main.py

# Araç otomatik olarak:
# 1. Trafik ışığı yeşil olduğunda başlar
# 2. Veya START_BUTTON=16 basılırsa başlar
# 3. 4 dakika boyunca parkuru bitirmeye çalışır
```

---

## 📊 İYİ İŞARETLER

✅ **Başarı Göstergeleri:**
- Motor testi: Hiç sapma
- Kamera: Beyaz şerit stabil
- PD tuning: Salınım < %5
- Ana program: FPS 28-30, Error ±10px
- Olaylar: Tespit oranı > 80%

---

## 📝 NOTLAR

1. **Her Pistede Kalibrasyon Gerekli**
   - Yazılı piste göre ayarlanmış değerler başka pistede başarısız olabilir
   - Yarış sabahı 30 dakika test sürüşü yapılmalı

2. **Parça Parça Kontrol Et**
   - Tüm sistemi bir seferde kontrol etmeyin
   - Motor → Kamera → PD → Sistem sırası ile

3. **Zaman Yönetimi**
   - 30 dakika yeterli mi değil mi kontrol et
   - Eksikse, önceki gün test yapmaya başla

---

**HAZIRLANMA BAŞLAMA:** T-30 dakika  
**BAŞLAMA SAATİ:** Trafik ışığı yeşil
**HEDEF:** 4 dakika içinde maksimum puan
