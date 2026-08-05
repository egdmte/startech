# SIRA — ne önce, ne sonra

`PLAN_New.md` neyi yapacağımızı söylüyor. Bu dosya **hangi sırayla** yapacağımızı söylüyor.

**Araç yapıldı ve hareket ediyor.** Şasi, motorlar, kamera, güç — hepsi duruyor. Bu yıl
yapılacak iş donanım değil: **yazılım ve kalibrasyon.**

Her adımın yanında **neyi açtığı** yazıyor. Bir adımı atlamak istiyorsan, neyi kilitli
bırakacağını görerek atla.

**İKİ KİŞİ** işareti olanlar tek başına yapılamaz veya yapılmamalıdır.

---

# A. ŞİMDİ — ağustos, araç okulda

Hiçbiri araç gerektirmez. Toplam yarım gün.

**A1. `StarTechConfig` bir depoya girsin · 15 dk**
Önce `.gitignore`'a .NET satırları (`bin/`, `obj/`, `.vs/`, `*.user`, `sunucu.json`),
sonra commit, sonra push.
→ *Açtığı:* her şey. İki günlük iş şu anda tek diskte.

**A2. Satır sonları · 5 dk**
```
git config core.autocrlf false
printf '* text=auto eol=lf\n*.pdf binary\n' > .gitattributes
git add --renormalize .
git commit -m "Satır sonlarını normalleştir"
```
→ *Açtığı:* Eylül. Şu an `LEGACY/` içindeki her diff 293 satır gürültü.

**A3. Kancayı kur · 1 dk** — `git config core.hooksPath .githooks`

**A4. Kalibrasyon aracını derle, bir dosya üret · 1–2 saat**
Derle, OLUŞTUR'a bas, çıkan `kalibrasyon.json`'u aç ve oku. Sonra aynı dosyayı iki kez
gönder: **201, sonra 409.**
→ *Açtığı:* araç zinciri gerçek olur. Şu ana kadar hepsi tasarım.

**A5. SUBIRU'ya görevleri gir · 30 dk**
`tasks.json` hâlâ `[]`, `owners.py` hâlâ baş harfler.

**A6. Ajan readme'sini bitir**

**A7. Renk maskesi önizlemesi · ~1 saat** *(isteğe bağlı ama en değerlisi)*
Şu an yalnızca beyaz için çalışıyor. Altı renk önizlemesiz — ve turuncu/sarı, gözle
doğrulanamayan tek ayar olduğu hâlde 100 puanlık olan.

---

# B. ARAÇLA İLK OTURUM — eylül, ilk gün

**Hiçbir kod yazma. Sadece ölç.** Yanlış bir sayı üzerine kurulan bir aylık iş,
Mayıs'ta kaybedilen şeydi.

**B1. Pilleri say · 2 dk** — motor tarafında 2 hücre mi 3 mü?
3S → motorlara ~10 V → 6 V motorun %175'i → `max_pwm` ≈ %57.
2S → ~6–7 V → doğru → `max_pwm` ≈ %100.
→ *Açtığı:* B2 ve bütün kontrol ayarları.

**B2. Multimetreyle ölç · 5 dk** — tam PWM'de motor uçlarında gerçek gerilim. Ve motorun
üzerindeki etiket: gerçekten 6 V mu?

**B3. İki kablo izle · 10 dk · İKİ KİŞİ** — hangi L298N hangi motorlara gidiyor,
**sol/sağ mı ön/arka mı?** Şematik çapraz çiziyor, geri kalan her şey sol/sağ diyor.
Ön/arka çıkarsa §6'daki kontrol yasası hiç çalışmaz.
→ *Blokerdir.*

**B4. Motorlar OUT'ta mı, IN'de mi · 2 dk** — belgede iki kez IN yazıyor. IN mantık
girişidir, motor akımı taşımaz.

**B5. `dtoverlay=pwm-2chan` var mı · 5 dk** — yoksa GPIO 12/13 yazılım PWM'i kullanır,
yük altında titrer, suç bir hafta kazançlara atılır.

**B6. Diskalifiye kontrolleri · 10 dk · İKİ KİŞİ**
20 × 30 cm kutuya sığıyor mu, 25 cm altında mı, teker ≤ 10 cm mi · kamera dışında sensör
var mı (bağlı olmayanlar dâhil) · başlatma butonu var mı (50 puan).

**B7. Kamerayı doğrula · 5 dk** — CSI mi USB mi, ve `picamera2` ile **kare geliyor mu** —
takılı olması değil.

**B8. Bul, yaz, işaretle** — yedi cevabı `PLAN_New.md` §15'e yaz ve `[UNVERIFIED]`
etiketlerini kaldır. Ölçüp yazmamak, ölçmemekle aynı şey.

---

# C. UCUZ DENEY — eylül, ilk hafta

**Yeniden yazmadan önce.** §20.7. Bir öğleden sonra, ve cevabı çok değerli.

**C1. §3.3'teki iki trim hatasını ÖNCE düzelt**
Trimler 1.0 olduğu sürece görünmezler; ölçülen değer girildiği an etkinleşirler. Önce
düzeltmezsen doğru bir ölçüm aracı **daha kötü** hale getirir.
- `controller.py`: trim, PWM'in işaretine göre değil **tekerlek kimliğine** göre seçilmeli
- Trim iki kez uygulanıyor (`controller.py` + `motor.py`) — biri kalkmalı

**C2. `motor_balance_test.py`'yi düzelt** — `LEFT_TRIM`/`RIGHT_TRIM` yazdırıyor, config
dört ad okuyor. Muhtemelen trimlerin 1.0 kalma sebebi bu.

**C3. `PERSP_SRC`'yi düzelt · TEK değişken · İKİ KİŞİ**
`calibrate.py` çalıştır, 800×680 için köşeleri al. **Sadece bunu değiştir.**
`yol_takip.py` ile sür, `logger.py` raporunu oku, sayıyı tarihiyle yaz.

**C4. Trimleri ölç · İKİNCİ değişken · İKİ KİŞİ** — sonra tekrar sür, tekrar oku, tekrar yaz.

**C5. Teşhis boyunca `KI = 0`** — integral, sabit sapmayı düzlükte gizler ve viraja
boşaltır. Kapalıyken sapma temiz bir sabit hata olarak görünür.

> **Sonuç ne olursa olsun kazanç.** Araç düzelirse, kod bir ölçüm uzaktaymış — ve
> yeniden yazma bir kurtarma değil, kontrollü bir öğrenme olur. Düzelmezse, en olası
> iki sebebi bir öğleden sonraya elemişsin.

---

# D. FAZ 1 — araç yumuşak dönebiliyor mu · eylül–ekim

Bundan öncesi ölçüm, bundan sonrası inşa.

1. `ayar.py` — iki JSON'u okur, doğrular, **çözünürlük uyuşmazlığında başlatmayı reddeder**
2. `surucu.py` — sahte (mock) ve gerçek arka uçlar, **varsayılan motorlar kapalı**
3. `bildir.py` — LED/buzzer durum çıkışı
4. **İKİ KİŞİ** — tekerlekler yerden kesikken elle çeşitli PWM oranları sür
5. **İKİ KİŞİ** — sonra yerde: kavis mi çiziyor, kendi etrafında mı dönüyor

**Çıkış testi:** (60, 80) komutu, iki yönde de, üç kez üst üste tekrarlanabilir bir kavis
çiziyor — ve asimetri trimi yazılmış durumda.

---

# E. FAZ 2 — şeridi görmek · ekim–kasım

Büyük ölçüde **araçsız** yapılabilir. Kötü haftaların fazı budur.

1. **İKİ KİŞİ** — pisti bantla (§18.2): düz, iki yöne viraj, bir kesikli bölüm
2. **İKİ KİŞİ** — görüntü çek. **Aracın kendi kamerasıyla, aracın kendi yüksekliğinden.**
   Telefonla ayakta çekilen görüntünün perspektifi tutmaz ve ROI ayarları taşınmaz
3. `goz.py` — USB, picamera2 ve video-dosyası arka uçları
4. `goruntu.py` — şerit tespiti, Windows'ta kayıtlı videoya karşı geliştirilir
5. Kalibrasyon aracını gerçek kareyle bitir (A7 buraya bağlanır)

**Çıkış testi:** ayrılmış bir klipte karelerin **%95'inde** makul bir şerit merkezi —
kesikli bölümler dâhil, kimse ortada ayar değiştirmeden. Sabit klip seti, ölçülmüş sayı,
yazılmış.

---

# F. FAZ 3 — döngüyü kapat · kasım–ocak

**Yılın en kritik fazı. Kilometre taşı burada.**

1. `durum.py` — durum makinesi, görev sırası **sabit değil** (§2.4)
2. Kontrol yasası (§6) — PD, ölü bölge, slew limiti, `max_pwm` B2'den
3. `kayit.py` — kara kutu. **Kare numarası ile anlık görüntü adı aynı olmalı**
4. `arac.service` + buton + LED — ekransız, telsizsiz açılış (§5)
5. **İKİ KİŞİ** — pistte kazanç ayarı

**Çıkış testi:** üç ardışık tur, **sıfır şerit ihlali**, elle müdahale yok, yalnızca
butonla başlatılmış, dizüstü bağlı değil. Tur sürelerini yaz — zaman bonusunun taban
çizgisi bu.

> **KİLOMETRE TAŞI — yarıyıl tatili:** araç düz bir pisti kendi başına dönebiliyor mu?
> **Evet** → altı görev için yer var. **Hayır** → görev kesmeye başla: önce sollama,
> sonra çıkmaz yol, sonra tümsek. **Şerit takibinden asla feragat etme.**

---

# G. OCAK — yeni kılavuz

Yayınlandığında dur ve `PLAN_New.md` §2 ile satır satır karşılaştır. Kurallar değişir;
komite değiştirme hakkını açıkça saklı tutuyor. Puanlar, ölçüler, görev tanımları.

---

# H. FAZ 4 — görevler, teker teker · ocak–mart

Her biri tam çalışır ve kaydedilmiş olmadan bir sonrakine geçme. Puan/zorluk sırası:

1. **Trafik ışığı başlangıcı** (50 + 50) — en yüksek değer, en düşük zorluk, ve zaten
   her zamanlı koşunun ön koşulu
2. **Yaya geçidi + hemzemin** (50 + 50) — aynı dedektör, aynı davranış, iki puan
3. **Hız tümseği** (50) — çoğunlukla hız düşürme. Dikkat: §19, `SPEED_BUMP_SPEED` ölü
   bölgenin altında kalamaz
4. **Park** (100) — iyi yalıtılmış, turun sonunda, prova edilebilir
5. **Çıkmaz yol** (100) — levha tespiti + ayrılmış pivot. `sign_type` bağlantısı burada
   (§20.3c, ~20 satır)
6. **Sollama** (100) — en son. Kasten şerit değiştiren tek görev, tuzak nesnesi olan tek
   görev, ve hata yapmanın atlamaktan kötü olduğu tek görev

**Her görev için çıkış testi:** on deneme, en az sekizi puan alıyor, onunun da kaydı
okunmuş.

---

# I. MART — başvuru

2026'da son tarih **20 Mart 18:00**'di, uzatma 14 Mart'ta duyuruldu. Yarışma 6–8 Mayıs.

- **Aracın çalışmasına bağlı değil.** Başvurular açılır açılmaz başvur.
- Belgelerin **tamamı** yüklenmeli; form tek başına yetmiyor. Ayrıca **kura kaydı** adımı var.
- **Sahibi: danışman öğretmen, yedeği Egemen.** Tek sahipli geri dönülmez tarih olmaz.

---

# J. FAZ 5 — tam turlar · mart–nisan

1. Uçtan uca turlar, **farklı ışıklarda**
2. **Görevlerin sırasını turlar arasında değiştir** — §7'nin gizlice bir sıraya
   bağlı olmadığını kanıtla
3. Her koşudan sonra kara kutuyu oku. İstisnasız
4. Yedekleri tak, çıkar, tekrar tak — denenmemiş yedek yedek değildir

**Çıkış testi:** beş ardışık tam tur, her biri 240 sn altında, her biri Faz 4'ten
belirlenen hedefin üstünde.

---

# K. NİSAN — yarışma hazırlığı

- Yedekleri **şubatta** sipariş et, nisanda değil (§16.3)
- Kontrol listesini bas (§17.5) — kalibrasyon özetiyle aynı kâğıdın iki yüzü
- Sürücü ve gözcü rollerini belirle (§17.2) — sahada aynı anda en fazla iki öğrenci
- Piller dolu, yedekleri de dolu. Pistte şarj süresi verilmiyor
- Ethernet kablosu çantada

---

# L. MAYIS — yarışma

- **Deneme turu tek kalibrasyon penceresi.** Sıra: turuncu↔sarı → beyaz şerit → kırmızı
  park → yeşil ışık → mavi işaretler (§17.3)
- Koşudan önce piste bak, **görevlerin bu turdaki sırasını not et**
- Her turdan önce 14 maddelik listeyi işaretle. İlk dördü diskalifiye sebebi
- Turlar arasında kayıtları SD karttan kopyala

---

# M. MAYIS SONRASI

§25. Yeni araç artık legacy'dir. `LEGACY/` ancak yeni araç onu pistte yendiğinde ve bu
bir kayıtta göründüğünde arşivlenir.

Ve alan adı, Vercel, R2, VPS, GitHub — hepsi tek bir kişinin hesabında. Son dönem
bitmeden karara bağlanmalı.

---

## Tek cümlelik özet

**Şimdi:** yedekle, derle, bir dosya üret.
**Eylül ilk gün:** hiçbir şey yazma, yedi şey ölç.
**Eylül ilk hafta:** quad'ı düzelt, sür, oku — yeniden yazmadan önce.
**Yarıyıla kadar:** araç düz pisti kendi başına dönsün.
**Sonra:** görevler, teker teker, en ucuzundan başlayarak.
