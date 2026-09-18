# YARIŞMA GÜNÜ STRATEJİ REHBERI

## GENEL PUANLAMA ÖZETİ

| Görev | Puan | Zorluk | Notlar |
|-------|------|--------|--------|
| Başlangıç (Trafik Işığı) | 50/25 | ⭐ | 3-15 saniye; 2 deneme |
| Yaya Geçidi | 50 | ⭐⭐ | 5+ sn bekleme |
| Hemzemin Geçit | 50 | ⭐⭐ | 5+ sn bekleme |
| Hız Tümsek | 50 | ⭐⭐⭐ | Mekanik zorluk |
| Sollama | 100 | ⭐⭐⭐⭐ | Sadece belirtilen bölge |
| Çıkmaz Yol | 100 | ⭐⭐⭐⭐ | Ön taraf tanıması kritik |
| Park Etme | 100 | ⭐⭐⭐⭐⭐ | Kırmızıya özel |
| Bölge Tamamlama | 50 | ⭐⭐ | Şerit ihlali cezası |
| Bitirme Süresi | Var | - | (4×60) - Sn |
| **TOPLAM MAKS** | **500+** | - | - |

---

## YARIŞMA ÖNCESI (1 Hafta Önce)

### ✅ Teknik Kontrol Listesi

- [ ] Kamera 320×240'ta keskin görüntü veriyor
- [ ] Trafik ışığı tespiti %95+ doğruluk (siyah arka, aydınlık ortam)
- [ ] Beyaz şerit stabilitesi ±20 piksel
- [ ] Motor balansı düz yolda ±5 cm sapma
- [ ] Pil 8+ saatlik enerji (`5×1.6V 2000mAh`)
- [ ] Tüm GPIO pinleri çalışıyor (LED testi)
- [ ] Telsiz/Bluetooth tamamen kapalı
- [ ] Başlangıç butonu çalışıyor

### ✅ Yazılım Kontrol Listesi

```bash
# Son test:
python pd_tune.py  # KP, KD değerlerini kaydet
python motor_balance_test.py  # Trim faktörlerini doğrula
python calibrate.py  # PERSP_SRC'yi pistte ölç
python camera.py  # Aydınlatma koşullarını test et
```

### ✅ Kalibrasyonu Kaydet

**config.py'de son doğrulanmış değerler:**
```python
# Kalibrasyonun tarihi ve yeri
KP = 0.60      # İyi kalibrasyon
KD = 0.44
KI = 0.016

PERSP_SRC = [
    [ 80, 150],   # Pistte ölçüldü
    [240, 150],
    [  0, 240],
    [320, 240],
]

LEFT_TRIM = 1.0   # Motorlar dengelenmiş
RIGHT_TRIM = 1.0
```

---

## YARIŞMA GÜNÜ (Saha'da)

### 🕐 Saati 8:00 - Hazırlanma

```
⏰ 8:00 - Teknik kontrol öncesi son kontroller
  □ Arabayı sıfırla (USB'ye tak, reset et)
  □ Pileri tam şarj et
  □ QR kod kare olduğundan emin ol
  □ Kameraya 180° döndü kontrol et
  
⏰ 8:15 - Teknik kontrol
  □ Boyut kontrolü (20×30×25 cm)
  □ Sensör kontrol (sadece kamera)
  □ Yazılım doğrulama
  
⏰ 8:30 - Pist tanıma turu
  □ Pist üzerinde araçla test tuşu
  □ Perspektif kalibrasyonu (calibrate.py)
  □ Aydınlatma koşullarını test et
  □ Trafik ışığı renklerini gözle kontrol et
```

### 🕐 Saati 9:00 - Deneme Turları

```
⏰ 9:00-11:00 - Deneme sürüşleri (tüm takımlar)

TURDA BAŞARILI OLMAK İÇİN:

1. BAŞLANGIÇ (Kritik - 3 sn)
   ✓ Trafik ışığını izle
   ✓ Yeşil → 1.5 sn bekle (hız kazandır)
   ✓ Hızlandırarak geç
   ✓ Başarısız: 2. deneme (25 puan)

2. YAYA GEÇİDİ (50 puan)
   ✓ Cam görüntüsünü takip
   ✓ 30 cm önünde dur
   ✓ 5 saniye bekle
   ✓ Zamanı yönet (timeout risk)

3. HEMZEMİN GEÇİT (50 puan)
   ✓ Diagonal çizgileri tanı
   ✓ 30 cm öncede dur
   ✓ 5 saniye bekle

4. HIZ TÜMSEK (50 puan)
   ✓ Sarı-siyah deseni gör
   ✓ Düşük hızla geç (~30%)
   ✓ TAKILI KALMAYACAK HİZ
   ✓ Takıldıysa: Tekrar konumlandır (0 puan)

5. SOLLAMA (100 puan) - ZORDUR
   ✓ Sarı aracı gör
   ✓ Sollama serbest tablasını takip
   ✓ SOL ŞERIDE GEÇ → SAĞ TARAF TURUN
   ✓ SAĞA DÖN → SOL ŞERIDE GERİ DÖN
   ✓ ÖNDEKİ ARAÇTAN SONRA
   ⚠ SOLLAMA YASAKLI BÖLGELERDE CEZA

6. ÇIKIMAZ YOL (100 puan) - ZORDUR
   ✓ Mavi "T" işaretini gör
   ✓ ÇIKMAZ YOLA GIRME!
   ✓ SAĞ DÖNÜŞ MANEVRASı
   ✓ Yol devam bölgesine dön

7. PARK ETME (100 puan) - ÇOKKK ZORDUR
   ✓ Kırmızı alan gör (240-400 piksel konum)
   ✓ KIRMIZI alana gir (diğerlerine DEĞİL!)
   ✓ Tamamen içinde dur
   
   RENKLER:
   • Kırmızı (SAĞ) → İSTENEN ✓
   • Mavi (ORTA)  → Hata ✗
   • Yeşil (SOL)  → Hata ✗

8. BÖLGE TAMAMLAMA (50 puan)
   ✓ Tüm bölgeleri geç
   ✓ Şerit ihlali CEZA (-0 puan bu bölge)
   ✓ Parkurdan çıkma = geri koyma

Bitirme Süresi Puanı:
  Bitirme Süresi Katsayısı = (4×60) - Bitirme Süresi (sn)
  = (240) - (Bitirme Süresi)
  
  150 sn = 240-150 = 90 puan
  200 sn = 240-200 = 40 puan
  240 sn = 240-240 = 0 puan
```

### 🕐 Saati 12:00 - Öğle Arası

```
⏰ 12:00-13:00
  □ Araç duruma göre ince ayar
  □ Yavaş gözüken görevler practice
  □ Pil tamamen şarj
  □ Takım moral kontrol
```

### 🕐 Saati 13:00 - Sıralama Turları

```
Tur 1 (Sıra belirleniyor):
  □ Stabil koşuş hedefle
  □ 1 hata → daha dikkatli
  □ Tüm görevleri tamamlamaya odaklan (puan > hız)

Tur 2 (Varsa):
  □ Tour 1'den öğren
  □ Agresif koşuş deneyebilir
  □ Toplam puan = Tur1 + Tur2
```

---

## GOREV BAZINDA STRATEJİ

### Görev 1: Trafik Işığı (50 puan)

**Amaç:** Yeşili bekle, 3 saniye içinde hareket et

```
TRAFİK IŞIĞI SÜRECI:
┌─────────────────────────────────────┐
│ KIRMIZI (3-8 sn)                   │
│  └─ Hazırlan, motorları test et    │
├─────────────────────────────────────┤
│ SARI (1-2 sn) ← HAZIR OL!           │
│  └─ 50% hız hazırla                │
├─────────────────────────────────────┤
│ YEŞİL ← BAŞLA!                      │
│  t=0.0s: Hızlandırma başla         │
│  t=1.5s: Sensör satırını geç       │
│  t=3.0s: BAŞARILI ✓                 │
└─────────────────────────────────────┘

KOD TİPİ:
def wait_for_green(self):
    while True:
        signal = traffic_light.read()
        if signal == GREEN:
            return True
        elif signal == TIMEOUT:
            return False  # 2. deneme
```

**Puan:**
- ✅ İlk deneme başarı: **50 puan**
- ⚠️ 2. deneme başarı: **25 puan**
- ❌ Her ikisi de başarısız: **0 puan** (devam et)

---

### Görev 2 & 4: Yaya Geçidi + Hemzemin Geçit (50 puan × 2)

**Amaç:** Tespit → Dur → 5 sn bekle

```
DETEKTÖRÜN İŞLEMİ:
┌─ Yaya geçidi: Beyaz bantlar
│  └─ HSV maskesi → Histogram
│  └─ Merkezde trafik işareti
│
└─ Hemzemin geçit: Çapraz çizgiler
   └─ Diagonal pattern
   └─ Beyaz-siyah alternans

DURUŞ KURALARI:
• Mesafe: ≤ 30 cm ✓
• Bekleme: ≥ 5 sn ✓
• Hareket: Hiçbir imkemez
```

**Risk Analizi:**
- Gölge → Maske başarısız → Geç dur
- Parlaklık → HSV threshold ayarı
- Çöp görünümü → Morfoloji için cv2.morphologyEx()

**Iyileştirme:**
```python
# HSV threshold'unu ayarla
WHITE_HSV_LOW = (0, 0, 130)      # ← Daya toleranslı
WHITE_HSV_HIGH = (180, 90, 255)  # ← Gölgede çalış

# Morfoloji
mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel_7x3)
```

---

### Görev 3: Hız Tümsek (50 puan)

**Amaç:** Siyah-sarı deseni tanı → Düşük hızla geç

```
DETEKTÖRÜN İŞLEMİ:
┌─ Sarı-siyah alternatif çizgiler
│  └─ ~60 piksel aralık
│  └─ Yolun ortasında
│
└─ Tekerleklere çarparsa:
   └─ Motor sesi duyulur
   └─ Omega açı sıçraması
   
BAŞARILI GEÇME:
• Hız < 40% (40/100 motor hızı)
• Virajlar minimize
• Düz gidiş
```

**Kritik:** Takılırsa **0 puan** (tekrar konumlandırma)

**Kod Örneği:**
```python
if speed_bump_detected():
    speed = 30  # Düşük hız
    for i in range(500):  # ~5 metre
        motor.set_speed(speed, speed)
        if not detect_speed_bump():
            break
```

---

### Görev 5: Sollama (100 puan) - EN ZOR

**Amaç:** Engel araçı > Sollama serbest > Sollama > Döner

```
SOLLAMA BÖLGES'Ü:
┌──────────────────────────────────┐
│ SOLLAMA YASAKLI (Sarı araç)     │
│                                  │
│ ──────────────────────────────  │ ← 2. şerit hattı
│ ──────────────────────────────  │ ← Orta hat
│                                  │
│ SOLLAMA SERBESt (Tablası var)   │ ← ŞU ALAN!
│                                  │
│ ──────────────────────────────  │ ← Orta hat
│ ──────────────────────────────  │ ← 3. şerit hattı
│                                  │
│ SOLLAMA YASAKLI (Sonra)         │
└──────────────────────────────────┘

BAŞARILI SOLLAMA ADIMLARI:
1. Turuncu araçı gör (20×30×25 cm)
2. Sollama serbest tabela gözlemle
3. Güvenli hız (60% altı)
4. SOL ŞERIDE DEĞİŞ (3 sn)
5. TURUNCU ARACIN ÜSTÜ GEÇŞ
6. SAĞ ŞERIDE DÖNŞ (3 sn)
7. ORIJINAL ŞERITTEN SONRA

BAŞARILI OLMAMAK:
❌ Sollama yasaklı bölgede şerit değişimi
❌ Sollama tamamlamadan viraj
❌ Turuncu araçla çarpışma
```

**Zorluk:** Tablasını tanı + Pozisyon hesapla + Hızlı refleks

**Algoritma:**
```python
def overtaking_maneuver():
    # 1. Turuncu araç tanı
    if detect_orange_obstacle():
        # 2. Sollama tabellasını kontrol et
        if not in_overtaking_zone():
            return False  # Bekle
        
        # 3. Sollama yönetimi
        steer_left_strong()   # SAĞ ŞERITE GEÇ
        delay(3)  # 3 saniye
        
        # 4. Öndeki araçtan sonra
        steer_straight()
        
        # 5. Sol şeride dön
        steer_right_soft()    # SOLA DÖN
        delay(3)
        
        return True  # ✅ 100 PUAN
```

---

### Görev 6: Çıkmaz Yol (100 puan) - EN ZORDUR

**Amaç:** T şeklini tanı → Girmeden dön

```
ÇIKIMAZ YOL DESENI:
        ↑
        │ (YOL DEVAM)
        │
    ───┴──────
   │ ÇIKIMAZ  │
   │ YASAKLI  │
    └─────────

TESPIT:
1. Mavi "T" işareti tablası
2. Şerit biter (başında demiş benzin)
3. Sadece sol ve sağ seçenekleri

STRATEJİ:
• ÇIKIMAZ YOLA GIRME!
• SAĞ DÖNÜŞ YAP (180°)
• YOL DEVAM BÖLÜMÜNE DÖN

BAŞARILI DÖNÜŞ:
   ╔═══════════════╗
   ║ SAĞ DÖNÜŞ     ║
   ║ (180 derece)  ║
   ║  ┌───→        ║
   ║  └──← ↩ Yol   ║
   ╚═══════════════╝
```

**Kritik:** Tabella'yı geç görmek = Girme ve diskalifiye

**Kod:**
```python
def dead_end_detection():
    if see_dead_end_sign():
        # SAĞI DÖNÜŞ (sağ tekerlek hızlı, sol yavaş)
        motor.set_speed(20, 80)  # SAĞ ÖN, SOL GERİ
        delay(1.8)  # ~180° dönüş
        
        motor.set_speed(60, 60)  # Devam
        return True
    return False
```

---

### Görev 7: Park Etme (100 puan)

**Amaç:** Kırmızı alana SADECE Kırmızı alana park et

```
PARK ALANLARININ RENKLERI:
┌─────────────┬──────────────┬──────────────┐
│   KIRMIZI   │     MAVİ     │    YEŞİL     │
│   (İSTENEN) │  (YANLIŞ ✗)  │ (YANLIŞ ✗)   │
└─────────────┴──────────────┴──────────────┘

BAŞARILI PARK:
1. Aracın % 90+ kırmızı alanda
2. Hareket etmemiş (5 sn)
3. Dosyal konumda

BAŞARILI OLMAMAK:
❌ Mavi alanda park
❌ Yeşil alanda park
❌ Sınırdan taşan
```

**Puan:** Park, **100 puan**; Hatalı renk, **0 puan**

---

## ZAMANLAMA STRATEJİSİ

```
ZAM TUR (4 DAKİKA = 240 SANİYE):

0s      ├─ Başlangıç (3s)
3s      ├─ Yaya Geçidi (10s)
13s     ├─ Hemzemin Geçit (10s)
23s     ├─ Hız Tümsek (15s) ← ZAMAN HARCAYICI
38s     ├─ Sollama (20s) ← ZAMAN HARCAYICI
58s     ├─ Çıkmaz Yol (15s)
73s     ├─ Park Etme (20s)
93s     ├─ Kalan alan + güvenlik
240s    └─ TUR BİTİŞİ

ZAMAN KULLANIMI:
- ✅ Başlangıç: 3/3 (100%)
- ✅ Yaya Geçidi: 10/10 (100%)
- ⚠️ Hız Tümsek: 15/30 (50%)
- ⚠️ Sollama: 20/40 (50%)
- ⚠️ Çıkmaz Yol: 15/30 (50%)
- ⚠️ Park: 20/60 (33%) ← ÇOKKK ZAMAN

HIZLANDIRMA FIKIRLERI:
→ Park etme yazılımını önceden optimize et
→ Sollama reflekslerini test et
→ Çıkmaz yol tespitini hızlandır
```

---

## KRİTİK HATA YÖNETME

| Hata | Etki | Kurtarma |
|------|------|---------|
| Trafik ışığı tespiti başarısız | 0 puan (2. deneme var) | Tablo'yu gözle kontrol et |
| Yaya geçidi geçişi | 0 puan | Yolda devam, puan kaybı |
| Hız tümsek taksı | 0 puan | Tekrar konumlandır (hakem) |
| Sollama bölge dışında | 0 puan | Güvenli bölgede tekrar dene |
| Çıkmaz yola giriş | Diskalifiye | SAĞ DÖNE BAŞARISISIZ |
| Park rengine hata | 0 puan | Devam ederek bitişe git |
| Parkurdan çıkma | 0 puan çıktığı bölge | Hakem konumlandırır |

---

## MORAL VE HARITA KURALLARI

### ✅ Başarılı Olmak İçin:

1. **Kalite > Hız:** 100 puan 150 saniyede > 50 puan 50 saniyede
2. **Stabil Sürüş:** Kontrol kaybı = Zaman ve puan kaybı
3. **Risk Yönetimi:** Başarısızlığa tahammül et (2. denemeleri var)
4. **Hakem Saygısı:** Yardım iste, şikayet etme
5. **Yazılımı Sıfırla:** Her turda kod reload et (eski hata kalmaz)

### ⚠️ Diskalifiye Riskler:

- ❌ Çıkmaz yola giriş + çıkamama
- ❌ Parkurdan çıkıp dönmeme
- ❌ Sensör kullanma (Lidar, ultrasonik)
- ❌ Uzaktan kontrolü aktif (IR, Bluetooth)
- ❌ QR kodu sökme/hasar
- ❌ Parkur hasarı

---

## ŞANS VE MUHIBBET

**En Önemli 3 Şey:**

1. 🎯 **Trafik Işığı:** İlk 3 saniye başarılı = morale boost
2. 🚗 **Sollama:** Başarılı = 100 puan, başarısız = 0 puan (risk/reward)
3. 🅿️ **Park:** En zorlu ancak öngörülebilir

**En Kolayı:** Yaya Geçidi + Hemzemin Geçit (100 puan rahat)

**Zaman Tasarrufu:** Hız Tümsek'i 10 saniyede geç (15 yerine)

---

## YARIŞMA SONRASI

```
Tur Bittikten Sonra:

□ Error_log.csv'yi analiz et
  - Hata volatilitesi kontrol et
  - En kötü bölgeler tanımla

□ Harita feedback al:
  - Görev başarı/başarısızlık nedenleri
  - Teknik problemler

□ Tur 2'ye hazırlan (varsa):
  - Kalibrasyon ayarla
  - Pili şarj et
  - Yazılımı sıfırla
```

---

## SON NOTLAR

✨ **Başarının Sırrı:** Kontrol ve öngörülebilirlik

- Hızlı ama puan kaybı > Yavaş ama dolu puan
- Yazılımı güven > Yazılımı aşırı karmaşıklaştır
- Test et > Teoriye güven

🎯 **Hedef:** 300+ puan (sürü ortalaması ~200)
💎 **Gerçekçi Amaç:** 250+ puan (ilk 10'ya giriş)
🏆 **Hayal:** 400+ puan (çok iyi)

---

## HIZLI REFERANS KARTLAR

### Motor Hızları:
- İnce maneuver: 30%
- Normal: 60%
- Hızlı: 80%
- MAX: 100% (tehlikeli)

### Zaman Bütçesi:
- Başlangıç: 3-5 sn
- Her görev: 10-20 sn
- Bitirme: İdeal <150 sn

### Puan Dağılımı:
- Zorunlu (Başlangıç + Yaya + Hemzemin + Tümsek): 200 puan
- Zor (Sollama + Çıkmaz + Park): 300 puan
- Sürü Bölge: 50 puan
- Zaman Bonus: 0-240 puan

**Tavsiye:** İlk 200 puanı garantile, sonra ek 100 hedefle.

