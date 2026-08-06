# PLAN — Dyl-Startech Otonom Araç

> **Belgenin görevi:** Aracın teknik ve yönetsel ana başvuru kaynağı.
>
> **İlk yazım:** 1 Ağustos 2026
>
> **Öğrenci-dostu yeniden yazım:** 6 Ağustos 2026
>
> **Kural temeli:** 2026 Otonom Araç Kategori Kılavuzu ve 2026 Uygulama Kılavuzu.
> Yeni kılavuz veya resmî duyuru bu belgeyle çelişirse resmî kaynak üstündür.

Bu plan gerçeğin yerine geçmez. Kod, donanım ve resmî kurallar değişebilir. Bir madde
“yapılmadı” diyorsa önce depoyu kontrol et; yapılmışsa tekrar yapma, çelişkiyi US'a bildir.

---

## 0. Önce burayı oku

### 0.1 Beş temel gerçek

1. `LEGACY/` içindeki eski yazılım değersiz değildir. PD direksiyon, dinamik kazanç,
   uyarlanabilir ışık profilleri, `gpiozero`, `picamera2`, olay debounce'u ve eğitimli
   tabela sınıflandırıcısı içerir.
2. Mayıs 2026 başarısızlığının güçlü adayları kötü algoritmadan çok tamamlanmamış
   kalibrasyon, bağlanmamış özellik ve yanlış belgedir.
3. Eski perspektif dörtgeni 640×480 koordinatlarını 800×680 karede kullanır. Bu, en güçlü
   tek arıza adayıdır; fiziksel testle yeniden ölçülmelidir.
4. Motor trimleri ölçülmemiş görünmektedir. Ölçüm aracı, yapılandırmanın artık okumadığı
   isimleri yazdırır; araç düzeltilmeden ölçüme güvenilmez.
5. Bazı eski TXT belgeleri var olmayan sabit, yöntem, dosya ve performans sayıları ileri
   sürer. Kodda bulunamayan bir iddia doğru kabul edilmez.

### 0.2 Projenin mevcut durumu — 6 Ağustos 2026

- `LEGACY/` 4 Mayıs 2026 uygulamasını taşır ve yeni sistem için referanstır.
- Yeni `arac/` çalışma zinciri henüz yoktur.
- Git deposunda VPS `origin` ve GitHub `github` uzakları vardır.
- `core.hooksPath=.githooks` yapılandırılmıştır.
- SUBIRU çalışır fakat `subiru/data/tasks.json` hâlâ boştur.
- 3awnt prototipi vardır fakat üretim çalışma zincirine bağlı değildir ve dosyaları henüz
  Git tarafından izlenmemektedir.
- Çalışma ağacı kullanıcı değişiklikleri içerir; bunlar korunacaktır.
- `kontrol.py`, HATA DEFTERİ'ndeki `motor_balance` + `.py` adı nedeniyle mevcut durumda
  hata verir; gerçek dosya `motor_balance_test.py` adındadır.

### 0.3 Araçla ilk oturumda yapılacaklar

Kod yazmadan önce:

1. Motor kablolarını izleyip sol/sağ eşlemesini fiziksel olarak doğrula.
2. Motorların L298N `OUT` uçlarına bağlı olduğunu doğrula.
3. Gerçek PWM yöntemini ve frekansını belirle.
4. Tam yükte motor uçlarındaki gerilimi multimetreyle ölç.
5. Pil paketlerini, motor etiketini, kamera türünü ve araç ölçülerini kaydet.
6. Perspektif dörtgeni ve trimleri sırayla sınayan ucuz deneyi yap.

Fiziksel testten önce insan incelemesi, iki kişi, Egemen'in donanım izni ve tehlikeli
adımdan hemen önce son onay zorunludur. Ayrıntılı sıra `SIRA.md` içindedir.

### 0.4 Bu belge nasıl kullanılır?

| Aradığın konu | Bölüm |
|---|---:|
| Yarışma kuralları ve puan | §2 |
| Mayıs arızasının nedenleri | §3 |
| İzin verilen dosya yapısı | §4 |
| Ekransız/telsizsiz başlatma | §5 |
| Direksiyon ve hız kontrolü | §6 |
| Durum makinesi | §7 |
| Görüntü işleme | §8 |
| Ayarlar ve kalibrasyon | §9 |
| Kara kutu | §10 |
| İş bölümü | §11 |
| Sıralı çalışma | §12 ve `SIRA.md` |
| Güvenlik | §13 |
| Açık sorular | §15 |
| Satın alma ve yarışma günü | §16–18 |
| Eski koddan ne taşınacak | §20 |
| Belge güvenilirliği | §21 |
| SUBIRU | §22 |
| Eski kararların gerekçesi | §23 |
| Terimler | §24 |

### 0.5 Plan ve değişiklik kuralları

- Bu dosyayı, yol haritasını veya TODO'yu yalnız Egemen ya da T açıkça istediğinde değiştir.
- Egemen bu planı açıkça geçersiz kılabilir veya belirli bir deney için istisna verebilir.
- Yeni bir kaynak dosya gerekiyorsa önce plan ve dosya listesi onaylanır.
- `[DOĞRULANMADI]` işaretli bilgi fiziksel veya resmî kanıt olmadan temel alınmaz.
- Değişiklikler `Tuna.txt` içine sade dille kaydedilir.
- AI kodu araçta kullanılmadan önce insanlar tarafından okunur ve anlaşılır.
- Projenin tamamlandığına yalnız US karar verir.

---

## 1. Proje

Bu depoda üç ana parça vardır:

- **Yeni araç (`arac/`)**: Raspberry Pi 5 üzerinde çalışan, yalnız kamera kullanan otonom
  araç. Yeni mimari henüz uygulanmamıştır.
- **Eski araç (`LEGACY/`)**: 4 Mayıs 2026 tarihli çalışan uygulama. Okunacak, ölçülecek ve
  yeni sistemle karşılaştırılacak referans.
- **SUBIRU (`subiru/`)**: Görev sahipliği ve kanıt takibi için küçük Flask panosu. Adı
  “Şununla bir uğraşsan” sözünden gelir.

### 1.1 Takım

| Kişi | Mevcut/önerilen sorumluluk |
|---|---|
| Egemen Y. K. | Yazılım mimarisi, ana döngü, canlı donanım yetkisi |
| Tuna B. | Donanım, kalibrasyon, fiziksel test ve kayıt toplama |
| Mehmet E. U. | Danışman öğretmen ve başvuru işlemleri |

Günlük proje kararlarında Egemen ve T birincil otoritedir. SCHOOL daha düşük yetkilidir;
ancak resmî yarışma gereklilikleri ve başvuru süreci kendi yetki alanında bağlayıcıdır.

Kılavuz lise seviyesinde en fazla üç öğrenci ve zorunlu danışman öğretmene izin verir.
Sahada aynı anda en fazla iki öğrenci bulunabilir; danışman aktif rol alamaz. Üçüncü
öğrenci gelirse test/pist/kayıt alt sistemi veya park görevini uçtan uca üstlenebilir.

### 1.2 Çalışma düzeni

Yaz boyunca fiziksel araç çalışması yapılmaz; esas çalışma okul dönemindedir. Bu nedenle
plan tarihten çok bağımlılık sırasına dayanır. Bir fazın çıkış testi geçmeden sonraki faz
açılmaz.

---

## 2. Yarışma kuralları — 2026 başlangıç kaynağı

> **Uyarı:** Aşağıdaki değerler 2026 kılavuzundan alınmıştır. 2027 kılavuzu yayınlanınca
> satır satır yeniden doğrulanacaktır.

### 2.1 Puanlama

| Görev | Puan | Koşul |
|---|---:|---|
| Haricî bilgisayar olmadan buton/benzeri başlatma | 50 | Koşu öncesi yetenek puanı |
| Yeşilde doğru başlama | 50 | İlk deneme; ikinci deneme 25 |
| Yaya geçidi | 50 | 30 cm içinde dur, en az 5 saniye bekle |
| Hemzemin geçit | 50 | 30 cm içinde dur, en az 5 saniye bekle |
| Hız tümseği | 50 | Pist/şerit dışına çıkmadan geç |
| Sollama | 100 | Yalnız sollama izin bölgesinde |
| Çıkmaz yol | 100 | Girmeden algıla ve sağa dön |
| Park | 100 | Kırmızı alana tamamen gir |
| Bölge tamamlama | 50 | Yorum belirsiz: toplam mı, bölge başına mı? |
| Görev toplamı | 600 | 2026 tablosu |
| Süre katsayısı | `240 − bitiş saniyesi` | Parkur tamamlanırsa |

Sonuçlar:

- Dört dakikalık, yani 240 saniyelik sert sınır vardır.
- Hız puanı büyük olabilir; 120 saniyede bitirmek 120 ek puan verir.
- Turların puanları toplanır. Tek parlak tur yerine sürekli güvenilirlik önemlidir.
- Önce güvenilir şerit takibi, sonra kara kutu kanıtına göre kontrollü hız artışı yapılır.
- Bölge tamamlama puanının her bölge için olup olmadığı koordinatöre sorulmalıdır; cevap
  gelene kadar 50 toplam varsayımıyla plan yapılır.

### 2.2 Diskalifiye doğurabilecek teknik sınırlar

- Araç 20×30 cm kutuya rahatça sığmalı; yükseklik en fazla 25 cm.
- Teker çapı en fazla 10 cm; ağırlık sınırı yok.
- Algılama yalnız kamerayla yapılır. Lidar, IR, ultrasonik veya mesafe sensörü yasaktır.
- Kamera sayısı için sınır belirtilmemiştir.
- Kontrol kartı, motor sayısı ve RPM için özel sınır yoktur.
- Takımın geliştirdiği/açıklayabildiği yazılım gerekir; hazır ticari kontrol sistemi veya
  indirilen otonom proje kabul edilmez.
- OpenCV gibi kütüphaneler kullanılabilir.
- Bluetooth, Wi‑Fi, IR ve RF koşu sırasında kapalı olmalıdır. Aktif uzaktan kontrol veya
  aktif haberleşme modülü diskalifiye sebebidir.
- Sıvı, yanıcı, patlayıcı veya basınçlı enerji kaynağı kullanılamaz.
- Kayıtta verilen QR kod sabit gövdeye takılır; sökülmesi, taşınması veya zarar görmesi
  diskalifiye doğurabilir.
- Turlar arasında lastik ve pil değişebilir. Elektronik parça yalnız aynı tür ve aynı
  konumla değiştirilebilir; gövde değiştirilemez.

AI tarafından yazılmış kod hakkında kılavuz açık bir madde içermiyor. Takım kararı:
AI kodu kullanılabilir; insanlar kodu incelemeli, anlamalı ve hakeme açıklayabilmelidir.

### 2.3 Pist ve nesneler

- Zemin siyahtır; yol kenarları beyaz, çizgiler düz veya kesikli olabilir.
- Başlangıçtan yaklaşık 1 m sonra, ±%10 toleransla trafik ışığı vardır.
- Işık kırmızı/sarı/yeşil ve rastgele zamanlıdır; araç yeşilden sonra 3 saniye içinde
  hareket etmelidir.
- Sollanacak turuncu araç 20×30×25 cm'dir ve yalnız izin verilen bölgede bulunur.
- Sarı tuzak araçlar 20×45×25 cm'dir; sollama yasak bölgelerde veya karşı şeritte olabilir.
- İşaretler 13×20 cm'dir: yaya, hemzemin, tümsek, sollama serbest, çıkmaz ve park.
- Park alanları kırmızı, mavi ve yeşildir; yerleri turdan tura değişir. Hedef kırmızıdır.
- Mavi yol kenarı işaretleri bölge tamamlamayı gösterir.

Turuncu ve sarı ayrımı projenin en riskli renk kararıdır. İki nesne aynı karede ve yarışma
ışığı altında kalibre edilmelidir. Birini ayrı ayrı ayarlamak örtüşmeyi gizler.

### 2.4 Görev sırası sabit değildir

Yaya geçidi, hemzemin geçit ve tümsek yerleri/sırası hakemlerce değiştirilebilir. Park
renklerinin yerleri de değişir. Durum makinesi sabit görev dizisi kullanmayacaktır.

### 2.5 İki kamera seçeneği

Şerit takibi aşağıya bakan dar/yakın görüntü ister; tabela ve ışık daha ileri/geniş görüntü
ister. İki kamera yasal görünüyor ve Faz 4 sonrası düşünülebilir. Faz 1–2'de eklenmez;
kalibrasyon ve işlem maliyetini erken ikiye katlar. `goz.py` baştan çoklu arka uca uygun
yazılır.

### 2.6 Tarihler ve kaynak disiplini

18. yarışma 6–8 Mayıs 2026'da Antalya'da yapıldı. 2026 kılavuzu yaklaşık Ocak ayında
yayınlandı; başvuru 20 Mart 18.00 civarında kapandı. 2027 tarihi ve belgeleri henüz
bilinemez. Ocak 2027'de resmî kaynak yeniden okunacaktır.

Otonom Araç için ayrıca tasarım/üretim raporu istenmediği 2026 kılavuzundan anlaşılmıştır;
başvuru için Uygulama Kılavuzu ayrıca kontrol edilmelidir. Kaynaksız kural cümlesi kılavuz
alıntısı gibi yazılmayacaktır.

---

## 3. Mayıs 2026'da ne yanlış gitti?

### 3.1 Araçta gerçekten bulunanlar

Eski araç; kamera alma, kuş bakışı dönüşüm, şerit histogramı, süreklilik puanı, dinamik
PD kontrol, olay debounce'u, görev durumları, motor katmanı, Picamera2, kayıt ve tabela
modeli içeriyordu. “Hiçbir şey yapılmamıştı” doğru değildir.

### 3.2 Perspektif dörtgeni — en güçlü aday

`PERSP_SRC = [[160,300],[480,300],[0,480],[640,480]]` değerleri 640×480 geometrisine
aittir; çalışma görüntüsü 800×680'e çıkmıştır. Kodda uyarı vardır fakat kalibrasyon
yapılmamıştır. Sonuç yaklaşık 80 piksel yatay önyargı ve aracın en yakın yol bölümünün
kaybı olabilir.

**Kanıt durumu:** Kod ve koordinat uyuşmazlığı doğrulandı; yarışma davranışının tek nedeni
olduğu doğrulanmadı. Ucuz deneyle sınanacaktır.

### 3.3 Motor dengesi ölçülmedi

Dört trim değeri de `1.0` görünür. Bu “ölçtük ve eşit çıktı” ile “hiç ölçmedik” durumunu
ayıramaz. Ölçüm aracının yazdığı adlar ile config'in okuduğu dört ad uyuşmamaktadır.

### 3.4 İki gizli trim hatası

- Trim teker kimliğine göre değil PWM işaretine göre seçiliyor olabilir.
- Trim hem `controller.py` hem `motor.py` içinde uygulanarak iki kez çarpılıyor olabilir.

Değerler 1.0 iken görünmezler; gerçek trim girildiğinde ortaya çıkarlar. Ölçümden önce
düzeltilmeleri gerekir.

### 3.5 Başlatma butonu kaldırıldı

`LEGACY/main.py`, GPIO 16 butonunun kaldırıldığını ve klavye `GG`/`EZ`/boşluk ile başlatma
olduğunu gösterir. Bu yöntem dış bilgisayar gerektirir ve 50 puanı riske atar. Egemen,
2S güç anahtarını başlangıç olarak düşünmüştür; 2026 gözleminde hakemler Pi'ın açılmasını
beklemiştir. Ayrı GPIO butonu yine geliştirme hızını ve kural değişimine dayanıklılığı
artırır. 2027 metni görülmeden “güç anahtarı kesin yasaktır” denmeyecektir.

### 3.6 Çıkmaz yol bağlantısı kopuk

Eski ana döngü `sign_type` alanını tüketir; olay üreticisi bu alanı üretmez. Böylece eğitimli
tabela sınıflandırıcısı bulunsa bile sonuç durum makinesine ulaşmaz. Düzeltme küçük olabilir
fakat kalıcı değişiklik ayrı plan gerektirir.

### 3.7 Motor gerilimi

Fotoğrafa ve takım beyanına göre motorlar ayrı 3S 18650 paketten, Pi ise step-down üzerinden
2S paketten besleniyor. Motorlar 6 V ise L298N kaybından sonra yaklaşık 9–10,6 V görebilir.
Bu tam görevde yaklaşık %175 nominal gerilim demektir.

`max_pwm ≈ 57` yalnız aritmetik başlangıç tahminidir. Motor etiketi, yük altındaki gerilim
ve ölü bölge ölçülmeden uygulanmaz.

### 3.8 Mayıs koşusu gözlemi

5 Ağustos'ta eklenen takım gözlemine göre araç açıldı, ilerledi fakat şerit kararlılığı ve
görev bağlantıları beklenen sonucu vermedi. Bu anlatım tarihli insan gözlemidir; kara kutu
kaydı olmadığı için sayısal kanıt değildir.

### 3.9 Hâlâ olası fakat kanıtsız nedenler

- Işık ve HSV eşikleri,
- lastik/mekanik asimetri,
- pilin yük altında çökmesi,
- yazılım PWM titreşimi,
- kamera montajı veya açı değişimi,
- kesikli şeritte zayıf sinyal,
- motor akım sınırı.

Rastgele kazanç değiştirerek değil, tek değişkenli deneylerle eleneceklerdir.

### 3.10 Neden kesin cevap yok?

Koşu başına eşzamanlı kare, durum, hata, düzeltme ve PWM kaydı yoktu. Bu yüzden yeni sistem
için kara kutu isteğe bağlı değildir.

---

## 4. Dosya yapısı

Yeni araç için onaylanmış çekirdek yapı:

```text
arac/
  main.py              Başlangıç, ana döngü ve sinyal yönetimi
  durum.py             Durum makinesi
  goz.py               USB, Picamera2 ve video girişi
  goruntu.py           Şerit, renk, ışık ve tabela algılama
  surucu.py            Sahte/gerçek motor sürücüsü; tek PWM çıkışı
  ayar.py              Ayar ve kalibrasyon yükleme/doğrulama
  kayit.py             Kara kutu
  bildir.py            LED/buzzer durum bildirimi
  ayarlar.json         Seçilmiş kontrol ve davranış değerleri
  kalibrasyon.json     Ölçülmüş kamera, renk ve motor değerleri
arac.service           Açılışta kontrollü çalıştırma
requirements.txt       Sabitlenmiş bağımlılık sürümleri
klipler/               Tekrarlanabilir görüntü testleri veya manifestleri
subiru/                Görev ve kanıt panosu
LEGACY/                4 Mayıs 2026 referansı
Markdown/PLAN_New.md   Bu belge
AGENTS_READ_ME.txt     Ajan çalışma sözleşmesi
SIRA.md                Zaman çizelgesi ve TODO
TAWNT.md               3awnt kılavuzu
Tuna.txt               Sade değişiklik kaydı
kontrol.py             Belge iddialarını denetleyen araç
kontrol-izin.txt       Gerekçeli denetim istisnaları
.githooks/pre-commit   Commit öncesi belge kontrolü
Markdown/pdf_yap.py    Onaylanırsa PDF anlık görüntülerini üretir
```

3awnt'ın üretim yapısına eklenmesi henüz kararlaştırılmamıştır. `tawnt.py`, entegrasyon
planı Egemen tarafından onaylanmadan yeni aracın zorunlu dosya listesine girmiş sayılmaz.

### 4.1 `LEGACY/` kuralı

Eski durum Git'te korunmuştur. Bundan sonra yalnız açıkça planlanmış teşhis değişiklikleri
yapılabilir. Yeni kalıcı özellik eski klasöre yazılmaz. Yeni araç onu pistte ve kayıtta
geçmeden silinmez.

### 4.2 Depo dışındaki iki sistem

- `kalibrasyon-sunucu/`: Vercel + Cloudflare R2 sürüm geçmişi ve sistem anahtarı;
  `dymtal.avartech.net`, panel `/startech`, ayrı Git deposu `egdmte/avartech-r2`.
- `StarTechConfig/`: Windows .NET Framework 4.7.2 WinForms kalibrasyon aracı. Önceki kayda
  göre tek diskteydi ve Git deposu değildi; güncel durumu doğrulanmalıdır.

`sunucu.json` ortak parolayı taşır ve hiçbir depoya commit edilmez.

### 4.3 Yeni dosya kuralı

Liste dışı dosya gerekiyorsa önce neden, sahibi, test biçimi ve bakım maliyeti planlanır.
Araç çalışma zinciri ağ kodunu içe aktarmayacaktır.

---

## 5. Ekransız ve telsizsiz başlatma

Koşu sırasında Wi‑Fi/SSH yoktur. Önerilen yol:

1. Pi açılır, `arac.service` `main.py`yi başlatır.
2. `ayar.py` iki JSON'u okur; motorlar kapalı kalır.
3. `goz.py` yalnız cihaz açılışını değil gerçek kare gelişini doğrular.
4. Sistem hazır fakat silahsız bekler.
5. Fiziksel buton veya yeni kılavuzun kabul ettiği tetikleyici koşuyu başlatır.
6. Sistem yalnız yeşili gözlemlemeye geçer.

Önerilen sinyaller:

| Sinyal | Anlam |
|---|---|
| Yavaş yanıp sönme | Açılıyor / ayar yükleniyor |
| Sabit ışık | Hazır, insan tetiklemesini bekliyor |
| Hızlı yanıp sönme | Ayar veya kamera hatası; başlatma yok |
| Çift bip | Tetikleme alındı, yeşil bekleniyor |
| Sürekli uyarı | `HATA`; motor komutu sıfır |

“Yazılım önceden yüklenmiş olmalı” biçimindeki eski cümlenin madde/page kaynağı yoktur.
2026 uygulamasında hakemlerin açılışı beklediği Egemen tarafından gözlenmiştir. Tercih ile
resmî zorunluluk karıştırılmayacaktır.

---

## 6. Kontrol yasası

Normal şerit takibi pivot değil, iki tarafı ileri süren diferansiyel PD kontrolüdür.

Her karede:

1. Şerit sınırlarından merkez tahmin edilir.
2. Hata, şerit merkezi ile görüntü merkezi farkı olarak hesaplanır.
3. `KP` hataya tepki, `KD` değişime sönüm verir. Eski başlangıç değerleri `KP=0.30`,
   `KD=0.45` idi; kanıt değil başlangıç noktasıdır.
4. Düzeltme iki yana zıt işaretle eklenir/çıkarılır.
5. Büyük hatada taban hız düşürülür.
6. Bütün komutlar ölçülmüş güvenli aralığa sıkıştırılır.

Gerekli ekler:

- küçük hata ölü bandı,
- PWM değişim hızı sınırı,
- kısa şerit kaybında son yönü kısa süre koruyup yavaşlama,
- daha uzun kayıpta güvenli arama veya duruş,
- mekanik asimetri trimi yalnız tek yerde,
- pivot yalnız çıkmaz yol ve gerekirse park hizası için.

### 6.1 Çözülmemiş işaret çelişkisi

Planın bazı yerleri hata işaretini ve sol/sağ karışımını farklı yorumlar. Egemen sol/sağ
kablolama olduğunu beyan etmiştir; şema farklı görünmektedir. Fiziksel kablo takibi ve
tekerlek-havada test yapılmadan denklem kesinleştirilmez.

### 6.2 Hız tavanı, ölü bölge ve hedef hız birlikte seçilir

Eski değerler yaklaşık `MIN_SPEED=25`, `BASE_SPEED=62`, `MAX_SPEED=85`,
`DEAD_ZONE_MIN_PWM=30` idi. `max_pwm=57` tek başına uygulanırsa:

- taban hız tavandan büyük kalır,
- oransal küçültmede minimum hız ölü bölgenin altına düşer,
- kullanılabilir kontrol bandı yaklaşık 55 birimden 27 birime iner.

Önce yük altında gerilim ve gerçek ölü bölge ölçülür; sonra MIN, BASE, MAX ve tavan tek
bir takım olarak seçilir. Kazançlar, ölü bant, slew, trim ve hızlar `ayarlar.json` içinde
olur; sabit kod içine gömülmez.

### 6.3 PWM frekansı

Eski `gpiozero.PWMOutputDevice` frekans belirtmez; varsayılan yaklaşık 100 Hz olabilir.
Önce gerçekten ne çalıştığı ölçülür. `dtoverlay=pwm-2chan` tek başına GPIO12/13'e donanım
PWM sağlamayabilir; varsayılan eşleme 18/19 olabilir ve gpiozero sysfs donanım PWM'ini
kullanmayabilir. “Overlay eklendi” ile “motor donanım PWM kullanıyor” aynı iddia değildir.

---

## 7. Durum makinesi (`durum.py`)

Bu adlar yeni sistem için öneridir; mevcut kodda uygulanmış sayılmaz:

| Durum | Görev | Çıkış |
|---|---|---|
| `BEKLE` | Motorlar kapalı, insan tetiklemesini bekler | Tetikleme |
| Işık bekle | Yalnız yeşili izler | Yeşil |
| `SERIT_TAKIP` | Şerit ve tamamlanmamış görev işaretleri | Görev tetiklenir |
| Geçit dur | Yaya/hemzeminde durur | En az 5 s |
| `TUMSEK` | Düşük hız | Özellik geçilir |
| `SOLLAMA` | İzin bölgesinde şerit değiştirir ve döner | Manevra tamamlanır |
| `CIKMAZ` | Girmeden sağa döner | Dönüş tamamlanır |
| `PARK` | Kırmızı alanı bulur ve tamamen girer | Durur |
| `BITTI` | Motorlar kapalı, kayıt boşaltılır | Son |
| `HATA` | Motorlar kapalı, arıza kaydı | İnsan müdahalesi |

`SERIT_TAKIP` merkezdir. Tamamlanan tek seferlik görev yeniden tetiklenmez. Yaya, hemzemin
ve tümsek herhangi sırada gelebilir. Sollama için izin tabelası gerekir; turuncu araç tek
başına izin değildir. 30 cm konumu kameradan kalibre edilir ve ücretsiz pay için 5 yerine
6 saniye bekleme düşünülebilir.

---

## 8. Görüntü işleme (`goruntu.py`)

Önerilen kare sırası:

1. `goz.py`den kare al.
2. Küçük çalışma çözünürlüğüne indir.
3. Yakın şerit ROI'si ve gerekirse uzak bakış bandı seç.
4. HSV'ye dönüştür.
5. Yalnız mevcut durumun ihtiyacı olan maskeleri çalıştır.
6. Morfolojik açma/kapama ile gürültüyü temizle.
7. Ham görüntü yerine küçük, şeması doğrulanmış sonuç üret.

Eski `lane.py`den korunacak fikirler: histogram, süreklilik ağırlığı, önceki merkezin
hafızası, tek sınırdan merkez tahmini, dinamik güven. Kesikli şerit başarısı kayıtlı kliple
ölçülmelidir.

Tabela sınıflandırması için eğitimli model kullanılabilir; şerit, geçit, tümsek ve renk
segmentasyonu klasik görüntü işleme kalır. `sign_type` alanı üretici ve tüketicide aynı
şemaya bağlanır.

---

## 9. Yapılandırma ve kalibrasyon

### 9.1 İki dosya ve sahiplik

- `kalibrasyon.json`: farklı pist, ışık, kamera montajı veya motor onarımında yeniden
  ölçülecek değerler. Tuna'nın ölçüm alanı.
- `ayarlar.json`: davranış ve kronometreyle seçilen kontrol değerleri. Egemen'in karar alanı.

**Çözülmemiş çelişki:** Eski planın bazı yerleri motor trimlerini `ayarlar.json`, bazı
yerleri `kalibrasyon.json` içine koyar. Trim fiziksel ölçüm olduğundan kalibrasyon dosyası
mantıklı görünür; US karar vermeden sessizce taşınmaz.

### 9.2 Kalibrasyon aracı ilkeleri

1. Fotoğraf ve canlı kamera desteği.
2. Araç olmadan Windows'ta geliştirilebilirlik.
3. Çözünürlüğü perspektif bloğuyla birlikte yazma; uyuşmazlıkta `ayar.py` başlatmayı reddeder.
4. Geçici dosya + yeniden adlandırma ile atomik kayıt.
5. Zaman ve kısa içerik hash'i taşıyan `damga`.
6. Ağ olmadan kaydetme; ağ hiçbir zaman açılışı bloklamaz.
7. Sıra: kamera → perspektif → beyaz şerit → turuncu/sarı → kırmızı park → yeşil → mavi.
8. Turuncu ve sarıyı aynı fotoğrafta, örtüşmeyi ayrı renkte gösterme.
9. Çıktı Python değil JSON'dur.

İlk mockup'ta bulunan ve düzeltildiği kaydedilen hatalar: 800×600 yerine gerçek 800×680,
iki `KP` etiketi, yanlış `K_Speed=65`, yanlış `D_C=8`, yanlış `Max hız=65`.

### 9.3 Şema durumu

Sürüm 1 şemasında `damga`, `kamera`, `perspektif`, `serit`, `renkler`, `motor` blokları
vardır. Her renk bir aralık listesidir; kırmızı renk çemberi sarımı nedeniyle iki aralık
gerektirebilir. `motor.olculdu` başlangıçta `null` olmalıdır; ölçülmemiş `1.0` ölçülmüş gibi
görünmemelidir.

Kaydetmeyi reddeden doğrulamalar: HSV sınırı, alt>üst, kare dışı perspektif köşesi,
turuncu/sarı hue çakışması, minimum hızın ölü bölgenin altında olması.

Araç derlenmiştir fakat gerçek araçta kullanılan kalibrasyon üretildiği doğrulanmamıştır.
“Yazıldı” ile “aracı kalibre etti” aynı değildir.

### 9.4 Sürüm sunucusu

`dymtal.avartech.net`, Vercel ve Cloudflare R2 üzerinde eklemeli sürüm geçmişidir. Kalibrasyon
ve ayarlar aynı damgayla yüklenir. Disk kaydı ağdan bağımsızdır; indirme hash'i yazmadan önce
doğrulanır; Git asıl kaynaktır.

Sunucu arabaya bağlanmaz; Pi yarışma dışında sunucuyu yoklar. Sunucu anahtarı kapalıysa,
sunucu yoksa, sürüm yoksa veya hash bozuksa araç güncelleme yapmaz. Bu fail-closed tasarımdır.

Araç çalışma zinciri ağ kodunu içe aktarmayacaktır. `getir.py` ayrı araçtır. Koşu sırasında
Wi‑Fi/RF kapalıdır; VPS canlı telemetri veya uzaktan kontrol için kullanılmaz.

Kalp atışı geçmişi tasarımı henüz uygulanmamıştır. Mevcut tek anahtar son kaydı ezer; tarihçe
kanıtı sağlamaz. Öneri, saat ve makine adına göre eklemeli anahtarlar kullanmaktır. `kim`
alanı istemci beyanıdır; sunucu zamanı ve R2 `LastModified` daha güvenilirdir.

### 9.5 Pi üzerindeki araç

WinForms .NET Framework 4.7.2 Linux'ta çalışmaz. Pistte gerekirse küçük Flask altkümesi
yalnız renkleri önizler ve kaydeder. Ortak kod zorunlu değildir; ortak sözleşme JSON şemasıdır.
Tek kesin doğrulayıcı `ayar.py` olur; masaüstü aracının doğrulaması kullanıcı kolaylığıdır.

---

## 10. Kara kutu (`kayit.py`)

Her kare için en az:

- zaman,
- kare numarası,
- durum,
- şerit merkez hatası,
- düzeltme,
- sol/sağ PWM isteği ve uygulanan sonuç,
- algılanan olay,
- hata/kilit durumu

kaydedilir. Durum değişiminde, şerit kaybında ve arızada görüntü anlık görüntüsü alınır.
Koşu klasörüne iki JSON'un kopyası ve mümkünse Git commit/hash bilgisi eklenir.

Satır kayıtları ucuzdur; her kare tam görüntü SD kartı ve döngüyü yavaşlatabilir. Görüntü
frekansı ayarlanır ve kaydın açık/kapalı döngü süresi ölçülür. Kayıt, fiziksel başarının
yerine geçmez; kötü koşuyu yeniden kurmaya yarar.

---

## 11. İş bölümü

| Tuna / T | Egemen |
|---|---|
| Şasi, kablo, güç, motor montajı | Mimari ve ana döngü |
| 20×30×25 cm ve QR yeri | `goruntu.py`, `durum.py`, `surucu.py` |
| Kalibrasyon ölçümleri ve pistte renk ayarı | Kontrol yasası ve ayar kararları |
| Aracın kamerasıyla kayıt toplama | Kara kutu ve teşhis |
| Fiziksel buton, LED, buzzer | Açılış yolu ve servis |
| Pil, yedek, fiziksel test | Entegrasyon ve build |
| Aracı sürerek sistemi kırmaya çalışma | Hata nedenini bulma |

Tuna'nın çıktıları mümkün olduğunca depoya iz bırakır: kalibrasyon JSON'u, klip manifesti,
donanım fotoğrafı ve ölçüm kaydı. Git'te iz yoksa SUBIRU “çalışmadı” diyemez; “Git'ten
gözlenemiyor” der.

Üçüncü öğrenci için en temiz alan pist/test/kayıt veya 100 puanlık park görevidir.

---

## 12. Yapım sırası ve faz kapıları

Tam ayrıntı `SIRA.md` içindedir.

| Faz | Amaç | Çıkış kapısı |
|---|---|---|
| 0 | Depo, belge, ölçüm hazırlığı | Yedek, görevler, araç öncesi kontrol hazır |
| Ucuz deney | Perspektif ve trim adaylarını sınamak | Tek değişkenli önce/sonra kayıt |
| 1 | Güvenli motor temeli | Tekrarlanabilir iki yönlü kavis ve duruş |
| 2 | Şeridi görmek | Ayrılmış klipte ≥%95 makul merkez |
| 3 | Döngüyü kapatmak | Üç ardışık müdahalesiz, ihlalsiz tur |
| 4 | Görevler | Görev başına 10 denemede en az 8 başarı |
| 5 | Tam tur | Beş ardışık süre/puan hedefli tur |

Yarıyıl kilometre taşı: Araç düz pisti tek başına dönebiliyor mu? Hayırsa görev kapsamı
daraltılır; şerit takibi korunur. Önerilen vazgeçme sırası: sollama, çıkmaz yol, tümsek.

Opsiyonel C# WinForms koşu analiz aracı Faz 4 sonrasına ertelenir. Kara kutu basit araçlarla
okunabiliyorsa yeni analiz ürünü yapılmaz.

---

## 13. Test ve güvenlik

### 13.1 Yazılım kuralları

- Motorlar açılışta kapalıdır.
- Yakalanmamış hata, kamera kaybı veya geçersiz motor komutu son PWM'i korumaz.
- Gerçek PWM'e giden tek yol `surucu.py` olur.
- İlk kontrol testi gerçek motor yerine sahte sürücüyle yapılır.
- İlk fiziksel testte tekerlekler yerden kesilir veya güvenli biçimde engellenir.
- Görüntü değişiklikleri bütün sabit kliplerde yeniden denenir.
- En az iki farklı ışık koşulu kullanılır.
- Bir güvenlik günlüğü, fiziksel duruş kanıtı diye sunulmaz.

### 13.2 Hareket eden aracı durdurma

Yazılım tepkisi varsa önce CTRL+C kullanılabilir. Motorlar durmuyorsa veya davranış
anlaşılmıyorsa:

1. Araç güvenli biçimde alttan tutulur ve kaldırılır.
2. Üçlü pil yatağının yanındaki motor anahtarı `O` konumuna alınır.
3. Raspberry Pi için ikili pil yatağının anahtarı kullanılır.
4. Pi gücünü aniden kesmenin SD kartı bozabileceği bilinir.
5. Fiziksel tehlike varsa motoru durdurmak SD kartı korumaktan önce gelir.

Araç hareketliyken masada test yapılmaz. Duman, çarpma sonrası devam, hızlı yanlış yön veya
yalnızca “ne yaptığını anlamıyorum” durumu durdurmak için yeterlidir.

### 13.3 Fiziksel test yetkisi

AI kodu önce insanlar tarafından okunur. Egemen canlı donanım testini onaylar. Tehlikeli
komuttan hemen önce son onay tekrar alınır. Geri alınamaz veya çok ağır kurtarma gerektiren
işlem için Egemen ve T'nin açık ortak onayı gerekir.

### 13.4 Pil ve yük

Pil gerilimi boşta değil motor yükü altında ölçülür. Boşta sağlıklı görünen hücre yükte
çökebilir ve yazılım hatasına benzeyen rastgele yeniden başlama yaratabilir.

### 13.5 Kütüphane ve kamera

- Raspberry Pi 5 için klasik `RPi.GPIO` uygun değildir; eski kod zaten `gpiozero` kullanır.
- CSI Pi Camera için `picamera2`, USB kamera için OpenCV/uygun USB arka ucu kullanılır.
- Donanım PWM'i kullanıldığı ayrıca kanıtlanır; yalnız overlay satırı yeterli değildir.

### 13.6 Risk kaydı

| Risk | Sonuç | Önlem |
|---|---|---|
| SD kart bozulması | Tam veri kaybı | Çalışan kart imajı ve test edilmiş yedek |
| Tek bilgisayarda depo | Tam kaynak kaybı | İki uzak depo ve erişim devri |
| Ölçü sınırı ihlali | Yarışmaya girememe | İlk fiziksel oturumda cetvelle ölçüm |
| Yasak sensör/modül | Diskalifiye | Fiziksel iki kişilik kontrol |
| Pi brownout | Rastgele hata | Ayrı besleme, yük altında ölçüm |
| QR kod hasarı | Diskalifiye | Sabit, düz, sökülmeyen yer |
| Boş pil | Koşu kaybı | Dolu ve denenmiş yedek |
| L298N/motor arızası | Günler/haftalar | Erken alınmış test edilmiş yedek |
| Turuncu/sarı karışması | Yanlış sollama | Aynı karede ortak kalibrasyon |
| Yeni kılavuz değişikliği | Yeniden çalışma | Ocak karşılaştırma kapısı |
| Tek kişinin sistemi bilmesi | Takım kırılganlığı | Kontrol listesi, eğitim, üçüncü öğrenci |
| 3awnt'a yanlış güven | Korumasız fiziksel hareket | Hibrit kapı, sahte sürücü, insan doğrulaması |

---

## 14. Teknik belgede düzeltilmesi gerekenler

Bu bölüm proje kodunu değil, hakeme/okula sunulan teknik anlatımın doğruluğunu hedefler.

- “Python 3.19” yoktur; kullanılan gerçek Python sürümü Pi üzerinde ölçülmelidir.
- Raspberry Pi 5 için RPi.GPIO yerine gerçek kullanılan `gpiozero` yazılmalıdır.
- Motorların L298N `IN` uçlarına değil `OUT` uçlarına bağlı olduğu doğru gösterilmelidir.
- Motor eşlemesi kablo takibiyle doğrulanıp şemaya işlenmelidir.
- Kamera türü “şimdiki CSI, hedefte USB + CSI/video arka ucu” olarak anlatılmalıdır.
- Performans yüzdeleri, FPS ve hata oranları tarihli test olmadan yazılmamalıdır.
- Tabela modelinin varlığı ile klasik CV kararı çelişki değildir: model yalnız tabela
  sınıflandırması, klasik CV diğer algılama görevleri içindir.
- Kullanılmayan/bağlanmamış görevler uygulanmış gibi gösterilmemelidir.

Bu değişiklikler ayrı belge planı olmadan yapılmayacaktır.

---

## 15. Açık sorular ve kanıt kaynağı

| # | Soru | Mevcut durum | Gerekli kanıt / zaman |
|---:|---|---|---|
| 1 | Motor eşlemesi sol/sağ mı? | Egemen sol/sağ diyor; şema çelişiyor | Kablo takibi, Faz 1 |
| 2 | Ölçüler kurala uyuyor mu? | Egemen uyduğunu beyan etti | Cetvel ölçümü, Faz 1 |
| 3 | Kamera dışı sensör var mı? | Egemen olmadığını beyan etti | Fiziksel kontrol, Faz 1 |
| 4 | Başlatma butonu ne olacak? | Fiziksel buton yok; 2S anahtarı düşünülüyor | 2027 kılavuzu + tasarım kararı |
| 5 | Motor uç gerilimi nedir? | 3S motor, 2S+step-down Pi beyanı var | Yük altında multimetre |
| 6 | Motor sayısı ve kanal yükü? | Dört motor, kanal başına iki paralel | Akım ölçümü |
| 7 | Varsayılan kamera? | CSI şimdi; USB hedef, ikisi de desteklenecek | Egemen kararı, Faz 2 |
| 8 | Kesikli şerit başarısı? | Çalışması bekleniyor | Kayıtlı klip testi |
| 9 | Bölge puanı toplam mı, bölge başına mı? | Egemen bölge başına okuyor; metin belirsiz | Koordinatör cevabı |
| 10 | Pistte dizüstü kullanılabilir mi? | Egemen'e göre evet | Yeni kılavuz/organizasyon teyidi |
| 11 | Üçüncü öğrenci geliyor mu? | Muhtemel | Takım kararı |
| 12 | 2027 tarihler? | Henüz bilinemez | Resmî duyuru |
| 13 | Başvuru ve kura belgeleri? | Öğretmen robot/takım bilgilerini giriyor | Uygulama kılavuzu |
| 14 | CV mi ML mi? | Kapandı: tabela için model, diğerleri klasik CV | Kod ve test |
| 15 | StarTechConfig yedekli mi? | Eski kayda göre tek diskte | Git/remote doğrulaması şimdi |

### 15.1 Beyan ile ölçüm arasındaki fark

Egemen'in aracı kendi elleriyle kurmuş olması, değişken adından daha güçlü kaynaktır; yine
de fiziksel ölçümün yerini almaz. Bu nedenle motor eşlemesi ve ölçüler için plan ilerleyebilir,
ama ilk oturumda iki dakikalık doğrulama yine yapılır.

### 15.2 Yetki ve sahip sütunu

Soru “Tuna'nın işi” veya “Egemen'in işi” diye kişiye itilmez. Gereken kaynak yazılır:
araç, cetvel, multimetre, dizüstü, koordinatör veya takım kararı. Oturumdaki uygun kişiler
birlikte tamamlar.

---

## 16. Parçalar, bütçe ve satın alma

### 16.1 Araçta olduğu söylenenler — doğrula

- Raspberry Pi 5,
- CSI kamera; USB kamera hedefi,
- dört DC redüktörlü motor,
- L298N sürücüler,
- 3S motor pil yatağı,
- 2S Pi pil yatağı ve step-down,
- şasi ve tekerlekler.

Liste, fotoğraf veya beyanla değil fiziksel sayımla kesinleşir.

### 16.2 Planın gerektirdikleri

- Fiziksel başlatma butonu veya yeni kılavuzun kesin kabul ettiği tetikleyici,
- durum LED'i ve/veya buzzer,
- güvenli anahtar erişimi,
- multimetre,
- metre/cetvel,
- Ethernet kablosu,
- pist bandı/çıktıları ve karton görev nesneleri.

### 16.3 Yarışmadan önce test edilmiş yedekler

- bir L298N,
- bir takım motor,
- imajı alınmış ve açılışı denenmiş SD kart,
- USB kamera,
- pil hücreleri,
- kablolar, bağlantı elemanları ve lastikler.

Yedekler Nisan'da değil Şubat'a kadar alınır. Araçta denenmemiş parça yedek sayılmaz.

### 16.4 Opsiyonel Faz 4+ parçaları

- İkinci kamera,
- daha uygun motor sürücüsü,
- mekanik koruma veya kamera montaj iyileştirmesi.

Opsiyonel parça, kanıtlı bir sorunu çözmeden alınmaz.

### 16.5 Para ve sorumluluk

Satın alma listesinde ürün, neden, yaklaşık fiyat, son sipariş tarihi, teslim alan kişi ve
araçta test edildi tarihi bulunmalıdır. Okul desteği ve takım katkısı yazılı kararla ayrılır.

---

## 17. Başvuru ve yarışma günü

### 17.1 Başvuru

2026 referansı: son tarih 20 Mart 18.00; uzatma duyurusu 14 Mart'ta gelmişti; yarışma
6–8 Mayıs'tı. Uzatma beklenmez. Araç hazır olmasa da başvuru erken yapılır.

Form, istenen belgeler ve kura kaydı farklı adımlar olabilir. Ana sorumlu danışman öğretmen,
yedek Egemen olarak planlanmıştır; yeni kılavuzda doğrulanır.

### 17.2 Sahadaki roller

En fazla iki öğrenci:

- **Sürücü/uygulayıcı:** Aracı yerleştirir, anahtarları ve başlatmayı yönetir.
- **Gözlemci/kayıtçı:** Pist sırasını, kontrol listesini, süreyi ve belirtileri izler.

İki kişi de fiziksel durdurma yöntemini bilmelidir.

### 17.3 Deneme turu

Deneme turu gerçek ışık ve nesnelerle tek kalibrasyon penceresi olabilir. Önerilen öncelik:

1. Kamera gerçekten kare üretiyor mu?
2. Turuncu ve sarı ayrımı,
3. beyaz şerit,
4. kırmızı park,
5. yeşil ışık,
6. mavi işaretler.

Yeni kılavuz farklı sıra gerektirirse yeni sıra kullanılır. Büyük mimari değişiklik yapılmaz;
yalnız önceden tasarlanmış kalibrasyon yolları kullanılır.

### 17.4 Çantada bulunacaklar

- Basılı kontrol ve kalibrasyon özeti,
- şarjlı ana ve yedek piller,
- test edilmiş SD kart,
- Ethernet kablosu,
- uygun tornavida/anahtar,
- yedek L298N/motor/kamera/kablo,
- Git commit ve yapılandırma damgasının yazılı kaydı.

### 17.5 Her tur öncesi kontrol listesi

1. Ölçüler ve tekerler kurala uygun.
2. Kamera dışında yasak sensör/modül yok.
3. Radyo/haberleşme kapalı.
4. QR kod sabit ve sağlam.
5. Gövde gevşek değil.
6. Kamera montajı ve açısı sabit.
7. Motor ve Pi pilleri dolu.
8. Anahtarlar ulaşılabilir.
9. Doğru commit ve iki JSON damgası kullanılıyor.
10. Kamera kare üretiyor.
11. Kalibrasyon çözünürlüğü gerçek kamerayla aynı.
12. Motorlar hazır durumunda kapalı.
13. Durum LED'i/buzzer doğru anlamı veriyor.
14. İki öğrenci görev ve fiziksel durdurmayı biliyor.

---

## 18. Deneme pisti

### 18.1 Kaçınılacak hata

Tam yarışma pistini ilk günden pahalı biçimde kopyalamaya çalışma. Önce kontrol döngüsünün
ihtiyacı olan küçük, değiştirilebilir parçaları kur.

### 18.2 Aşama 1 — bant, Eylül

Siyah veya uygun koyu zemin üzerinde beyaz bantla:

- düz,
- iki yöne viraj,
- kesikli bölüm,
- yeterli güvenli kaçış alanı.

Kayıtlar aracın kendi kamerası ve gerçek yüksekliğinden çekilir. Telefonla ayakta çekilen
görüntü perspektif kalibrasyonu için eşdeğer değildir.

### 18.3 Aşama 2 — basılı parçalar, Kasım

Kılavuz ölçülerine göre işaret ve şerit parçaları modüler basılır. Bölümler farklı sıraya
konabilir; böylece durum makinesinin sabit sıraya bağlanmadığı sınanır.

### 18.4 Görev nesneleri

Turuncu ve sarı araçlar belirtilen ölçülerde karton/maket olabilir. Tabelalar 13×20 cm
ölçeğinde hazırlanır. Park alanları turdan tura yer değiştirir.

### 18.5 Alan ve sahiplik

Pistin kurulacağı, söküleceği ve saklanacağı yer okul tarafından belirlenir. Bir kişi
manifest, hasar ve eksik parçaları takip eder; fiziksel çıktı Git'ten görünmüyorsa fotoğraf
ve not eklenir.

### 18.6 Maliyet ve zaman

Önce ucuz bant pisti, sonra işe yaradığı kanıtlanan parçaların baskısı. Pist, arabanın
çalışmasını beklemez; Faz 2 için görüntü üretir.

---

## 19. Konuşmanın bıraktığı yer

6 Ağustos 2026 itibarıyla yeni bilgi ve kararlar:

- US esas olarak Egemen ve T'dir.
- SCHOOL günlük proje kararlarında daha düşük yetkilidir; resmî yarışma ayrıntıları ayrı
  ve bağlayıcıdır.
- Egemen `PLAN_New.md`yi açıkça geçersiz kılabilir.
- Egemen canlı donanım işlemlerini yetkilendirir; tehlikeli adımdan hemen önce son onay alınır.
- Geri dönüşsüz veya aşırı kurtarma gerektiren işlemler Egemen ve T'nin ortak onayını ister.
- AI kodu kullanılabilir; insan incelemesi zorunludur.
- Araçla herhangi işlemden önce kod ve prosedür insanlar tarafından incelenir.
- 3awnt'ın hibrit kullanımı olumlu karşılandı fakat kod entegrasyonu henüz onaylanmadı.
- 3awnt bugün üretime bağlı değildir; önerilen yöntemler uygulanmış gibi gösterilemez.
- Ana ajan sözleşmesi İngilizce, öğrenci ve proje belgeleri Türkçe olacaktır.

Eski kimlik sorgusu, parmak izi veya takım arkadaşına kapı koyma önerileri reddedilmiştir.
Sorun erişim değil, inceleme ve kanıttır.

---

## 20. `LEGACY/`den miras

### 20.1 Neden yeniden yazılıyor?

Amaç eski algoritmaları değersiz saymak değil; takımın anlayabildiği, sorumlulukları ayrılmış,
test edilebilir bir yapı kurmaktır. Eski belge bazı hataları “kasıtlı” diye savunur ve yeni
öğrencinin bütün sistemi açıklamasını zorlaştırır.

### 20.2 Ana kural

> Yapıyı yeniden yaz; doğrulanmış bilgiyi miras al.

### 20.3 Dosya triyajı

**Korunacak fikirler:**

- `lane.py`: histogram, devamlılık, tek kenardan merkez, perspektif yaklaşımı,
- `controller.py`: PD, dinamik kazanç, türev sönümü,
- `events.py`: debounce ve görev algılama fikirleri,
- `motor.py`: gpiozero ve iki kanal soyutlaması,
- `camera.py`: Picamera2 arka ucu,
- eğitimli tabela modeli ve eğitim akışı,
- mevcut tanı/test araçlarının yararlı parçaları.

**Düzeltilmeden taşınmayacaklar:**

- 640×480 perspektifin 800×680 karede kullanılması,
- trim seçimi ve çift uygulama,
- `sign_type` kopukluğu,
- butonsuz klavye başlangıcı,
- kare başı hatada frenlemeden devam etme,
- art arda yaklaşık 30 hata boyunca son PWM'in kalabilmesi,
- kapanışta var olmayan `logger.close()` çağrısı,
- birim uyuşmazlıkları,
- ölü bölge altındaki hız,
- bütün görevleri her karede ve sabit sırada arama.

### 20.4 Silmeden önce çıkarılacaklar

Her eski dosya için:

1. hangi davranışı gerçekten sağlıyor,
2. hangi sabitlere bağlı,
3. hangi testle doğrulanabilir,
4. yeni hangi modüle taşınacak,
5. hangi kusur tekrar edilmeyecek

yazılır. Kod kopyalamak yerine davranış sözleşmesi çıkarılır.

### 20.5 Sabitlerin hikâyesi

Kritik her sayının kaynak etiketi olmalıdır: ölçüldü, devralındı veya varsayıldı. Ölçüm
kişi, tarih, birim ve yöntem taşır. Bu 3awnt ile uygulanabilir fakat insan kanıtının yerine
geçmez.

### 20.6 Eski kod ne zaman arşivlenir?

Yeni araç aynı deneme pistinde, benzer koşullarda ve kayıtlı sonuçla eskiyi geçince.
Mart geldi diye veya “eski görünüyor” diye değil.

### 20.7 Ucuz deney

Yeniden yazmadan önce:

1. İki trim kod hatasını düzelt.
2. Motor denge aracının yazdığı adları düzelt.
3. `KI=0` ile yalnız perspektifi yeniden ölç ve test et.
4. Sonra yalnız trimleri ölç ve tekrar test et.
5. Her koşunun raporunu ve tarihini sakla.

Sonuç başarılı da olsa başarısız da olsa değerlidir. Yalnız bu deney için `LEGACY/`
değişikliği ayrı onaylı plan ister.

### 20.8 En değerli küçük bağlantı

Tabela sınıflandırıcısının ürettiği türü olay sözlüğüne ve durum makinesine bağlayan
`sign_type` düzeltmesi yaklaşık küçük bir değişiklik olabilir; çıkmaz yolun 100 puanını
açabilir. Küçük olması plansız yapılacağı anlamına gelmez.

### 20.9 Belge hastalığı

Eski dokümanlar yapılmamış işi yapılmış, ölçülmemiş değeri optimize edilmiş gösterdi.
Asıl ders “daha çok belge” değil, her iddiayı kodda veya kanıtta bulabilmektir.

---

## 21. Belge denetimi

### 21.1 On saniyelik yeniden üretim

Adı geçen dosya, sabit ve yöntem `rg` ile aranır; Git durumu ve gerçek kod açılır;
performans sayısının tarihi/klibi/logu bulunur. Bulunamıyorsa iddia doğrulanmamıştır.

### 21.2 Güvenilmeyecek eski TXT belgeleri

Önceki denetimde şu belgelerin var olmayan içerikler ürettiği kaydedildi:

- `BASLA_BURADAN.txt`,
- `DOSYALAR_GUNCELEME_DURUSU.txt`,
- `DEGISIKLIKLER_OZET.txt`,
- `IMPLEMENTATION_SUMMARY.txt`.

İçlerindeki “tüm güncellemeler tamamlandı” türü ifadeler kanıt değildir.

### 21.3 Daha dürüst fakat sürüklenmiş belgeler

`LEGACY/CLAUDE.md` gerçek mimariyi daha iyi anlatır ancak bugünkü kodla her satırı aynı
değildir. Teknik belge hakeme yöneliktir ve gerçek kullanılan kütüphane/donanımı doğru
yansıtmalıdır.

### 21.4 İki farklı sorun

- **Uydurma:** Kodda hiç olmayan şeyi varmış gibi yazmak.
- **Sürüklenme:** Bir zamanlar doğru olan belgenin kod değişince eskimesi.

İlki kaynak kontrolüyle, ikincisi otomatik denetim ve düzenli güncellemeyle azaltılır.

### 21.5 `kontrol.py` sınırı

Araç; dosya adı, ALL_CAPS sabit, bölüm bağlantısı ve tarihli performans iddiası gibi şeyleri
kontrol eder. Fakat izin verilen dosya listesindeki yanlış ad kendi kendini affedebilir.
Betik, kaynağını aldığı planı bütünüyle doğrulayamaz; insan okuması gerekir.

Ön kontrol kancası Python/Python3 PATH'te yoksa denetimi atlayabilir. Kancanın çalışması
ayrıca test edilir.

### 21.6 Bugünkü temel hata

`kontrol.py`, değiştirilmiş HATA DEFTERİ içinde geçen `motor_balance` + `.py` dosya adını
bulamaz; depoda `motor_balance_test.py` vardır. Bu belge paketi o kullanıcı değişikliğine dokunmaz;
ayrı planla düzeltilir.

### 21.7 Eylemler

- Uydurma belgeler referans olarak kullanılmaz.
- Her iddia için aranabilir kod/kanıt gerekir.
- PDF'ler Markdown değişince otomatik olarak doğru sayılmaz.
- Belge kontrolü başarısızsa temel ve yeni hata ayrılır.
- Ajanlar tamamlanma durumunu kendi kendine ilan etmez.

---

## 22. SUBIRU v2 — kanıt odaklı tasarım

### 22.1 Amaç

Pano dolu görünmek için değil, doğru görünmek için vardır. Bugün `tasks.json=[]` olduğundan
gerçek görev yönetimi yapmıyor.

### 22.2 Önerilen görev alanları

- kimlik ve başlık,
- faz,
- tür: `code`, `kalibrasyon`, `donanim`, `test`, `idari`,
- dosyalar,
- bağımlılıklar,
- durum,
- kanıt,
- son güncelleme ve gerekirse tazelik süresi.

### 22.3 Git'ten otomatik gözlem

Kod görevinde son dokunan commit görülebilir. Donanım işi Git'ten görünmüyorsa pano
“gecikti” demez; “Git'ten gözlenemiyor” der. Fotoğraf, ölçüm veya manifest eklemek fiziksel
emeği görünür kılar.

### 22.4 Kanıt türleri

| Görev türü | Kabul edilen değer | Denetim |
|---|---|---|
| Kod | Commit hash | Git'te çözümleniyor mu? |
| Kalibrasyon | Sayı, birim, yer, tarih | İnsan ve şema |
| Donanım | Fotoğraf yolu + not | Dosya mevcut mu? |
| Test | Koşu günlüğü/klip | Var ve boş değil mi? |
| İdari | Kimin onayladığını belirten not | İnsan |

“Yaptım” tek başına tamamlanma kanıtı değildir.

### 22.5 Kalibrasyonun eskimesi

Işık, motor, kamera açısı ve pist değişir. Kalibrasyon görevleri `fresh_until` taşıyabilir;
Eylül ölçümü Mart'ta eski olarak görünür. Bu başarısızlık değil, yeniden ölçme işaretidir.

### 22.6 Faz kapıları

Her fazın çıkış testi ayrı `test` görevidir. Kanıt olmadan sonraki faz açılmaz. Pano planı
hatırlatır; fiziksel gerçeği kendisi doğrulamaz.

### 22.7 Kim tamamlandı işareti koyabilir?

İnsanlar ve açıkça geçen doğrulama betikleri. Bir LLM görev oluşturabilir veya kanıt
önerebilir; `done` durumunu kendi kararıyla vermez.

### 22.8 Aşamalı yapım

| Aşama | İçerik |
|---|---|
| 1 | Tür + kanıt; kanıtsız `done` yok |
| 2 | Git geçmişinden otomatik durum |
| 3 | Kalibrasyon tazeliği |
| 4 | Faz kapıları |
| 5 | `kontrol.py` sonucunu otomatik kanıt yapmak |

Önce gerçek görevler girilir; Aşama 1 kullanılmadan Aşama 2'ye geçilmez.

### 22.9 VPS'ye taşıma

Aşama 2'den sonra düşünülebilir. Önce `debug=False`, ortamdan güçlü secret ve üretim WSGI
sunucusu gerekir. Flask debug sunucusu ve sabit `subiru-dev-secret` internete açılmaz.

VPS araçla koşu sırasında konuşmaz. Canlı telemetri, uzaktan durdurma veya uzaktan komut
yarışma kuralına ve güvenlik amacına aykırıdır. Loglar koşudan sonra yüklenebilir.

### 22.10 Sistemin yapamayacakları

SUBIRU kimseyi çalıştıramaz ve tek taraflı dayatılamaz. Amaç suçlamak değil, eksik kanıtı
erken ve ucuz göstermektir. Tuna bu mekanizmayı kullanılmadan önce görüp kabul etmelidir.

---

## 23. Karar geçmişi

| Tarih | Karar | Neden / reddedilen seçenek |
|---|---|---|
| 1 Ağu | Yeni yapı yazılacak, eski silinmeyecek | Anlaşılır mimari; yerinde rastgele onarım reddedildi |
| 1 Ağu | Yeni araç eskiyi kanıtla geçmeden `LEGACY/` kalacak | Geri dönüş ve kıyas |
| 1 Ağu | Önce ucuz perspektif/trim deneyi | Aylar yerine bir öğleden sonra bilgi |
| 1 Ağu | Takım arkadaşına kimlik/parmak izi kapısı yok | Sorun erişim değil inceleme |
| 2 Ağu | Kalibrasyon ve ayarlar iki dosya | Ölçülen ile seçileni ve sahipliği ayırmak |
| 2 Ağu | Atölye aracı WinForms | Araçta çalışmayacak, Windows iş akışına uygun |
| 2 Ağu | JSON anahtarları Türkçe | Proje adlandırması ve sahibi için anlaşılır |
| 3 Ağu | Sunucu eklemeli, üzerine yazmaz | Geçmiş ve çakışmasız damga |
| 3 Ağu | İki JSON aynı damgayla sürümlenir | Yarım geri yüklemeyi engellemek |
| 3 Ağu | Araç sunucuyu yoklar; sunucu arabaya bağlanmaz | Gelen bağlantı/uzaktan yüzey yok |
| 3 Ağu | Sunucu anahtarı uzakta, araç çalışma kodundan ayrı | Yarışma dışı güncellemeyi merkezden kapatma |
| 3 Ağu | İkinci kontrol döngüsü kopyası yok | İki farklı `main.py` yarışta ayrışır |
| 3 Ağu | Doğrudan laptop→Pi düğmesi yok | Sunucu + Ethernet yedeği yeterli görüldü |
| 3 Ağu | Kalibrasyon sunucusu ana uygulamadan ayrı | Gerçek kullanıcı uygulamasını riske atmamak |
| 3 Ağu | Pi aracı WinForms portu değil küçük altküme | .NET Framework Linux'ta çalışmaz |
| 3 Ağu | JSON şeması sözleşmedir | Diller farklı olabilir; `ayar.py` son doğrulayıcı |
| 3 Ağu | `kontrol.py` ve commit öncesi kanca | Belge iddialarını aranabilir yapmak |
| 5 Ağu | Tabela modeli + klasik CV birlikte | Model yalnız sınıflandırma, CV geri kalan işler |
| 5 Ağu | Pistte dizüstü mümkün diye kaydedildi | Egemen bilgisi; yeni kılavuzda tekrar kontrol |
| 5 Ağu | Üçüncü öğrenci muhtemel | Test/pist veya Tuna'nın alanını paylaşabilir |
| 6 Ağu | AI kodu serbest, insan incelemesi zorunlu | Öğrenciler kodu anlamalı ve sahiplenmeli |
| 6 Ağu | Egemen canlı donanım yetkilisi ve son onay | Tehlikeli hareketten önce açık insan kapısı |
| 6 Ağu | 3awnt için hibrit yapı önerisi | Merkezi kurallar + `surucu.py`de fiziksel uygulama |
| 6 Ağu | Ana ajan promptu İngilizce, diğer belgeler Türkçe | Türkçe anlamayan ajanların kuralı kaçırmaması |

### 23.1 Hâlâ çözülmemiş kararlar

1. Direksiyon hata işareti ve sol/sağ motor karışımının kesin yönü.
2. Motor trimlerinin `kalibrasyon.json` mı `ayarlar.json` mı içinde olacağı.
3. 3awnt'ın üretim mimarisine girip girmeyeceği ve hangi yöntemlerinin önce yapılacağı.
4. Fiziksel başlatmada ayrı GPIO butonu mu yalnız güç anahtarı mı kullanılacağı.
5. Üçüncü öğrencinin katılımı ve alanı.
6. Bölge tamamlama puanının yorumu.

US kararı olmadan bu maddelerden biri sessizce kapatılmaz.

---

## 24. Sözlük

| Terim | Bu projedeki anlamı |
|---|---|
| US | Başta Egemen ve T olmak üzere proje takımı |
| SCHOOL | Öğretmenler, okul yönetimi ve geniş okul takımı |
| Bölge tamamlama | İşaretli bölgeyi pist/karşı şerit ihlali olmadan tamamlama |
| Şerit ihlali | Aracın herhangi bölümünün karşı şeride geçmesi |
| Sollama serbest | Sollamaya izin veren tabela; turuncu araç tek başına izin değildir |
| Deneme turu | Gerçek pist ışığında kısa kalibrasyon fırsatı |
| Kura kaydı | Başvurudan ayrı olabilen resmî kura adımı |
| `LEGACY/` | 4 Mayıs 2026 kodu; referans ve kıyas |
| SUBIRU | Görev ve kanıt panosu |
| 3awnt | Kritik değer beyan/doğrulama prototipi; fiziksel E-stop değil |
| Damga | Zaman + kısa içerik hash'i |
| Kalibrasyon | Ortam/donanım değişince yeniden ölçülen değer |
| Ayar | Takımın davranış için seçtiği değer |
| HSV | Renk tonu, doygunluk ve parlaklık sayı sistemi |
| `PERSP_SRC` | Kuş bakışı dönüşüm için görüntüdeki dört yol köşesi |
| ROI | İşlenen görüntü bölgesi |
| CLAHE | Yerel kontrast dengeleme yöntemi |
| Ölü bölge | PWM verildiği hâlde motorun dönmediği alt aralık |
| Trim | Ucuz motorların taraf hız farkını düzeltme katsayısı |
| PD/KP/KD/KI | Hata, sönüm ve uzun süreli sapma terimleriyle kontrol |
| Debounce | Bir algıyı kabul etmeden birkaç kare sürmesini isteme |
| Homografi | Perspektif dörtgenini dikdörtgene eşleyen 3×3 dönüşüm |
| Watchdog | Döngü/kamera zamanında çalışmazsa arıza üreten gözcü |
| Fail-closed | Arıza durumunda izin vermek yerine hareketsiz kalma |
| Arming | Sistem hazır olduktan sonra motor komutuna açık insan izni verme |
| Kara kutu | Koşu sırasında durum, görüntü, hata ve PWM geçmişi |
| R2 | Kalibrasyon sürümlerini tutan Cloudflare nesne depolaması |
| Append-only | Eski veriyi ezmeden yeni sürüm ekleme |

---

## 25. Mayıs 2027 sonrası devir

Yeni `arac/` sistemi bir sonraki takımın legacy'si olacaktır. Devredilecekler:

- Güncel depo ve çalışan commit,
- güncel `PLAN_New.md`, HATA DEFTERİ ve ajan sözleşmesi,
- yarışma koşu kayıtları,
- son `kalibrasyon.json` ve nerede/hangi ışıkta üretildiği,
- fiziksel araç ve test edilmiş yedekler,
- SD kart imajı ve yeniden kurma adımları,
- hesap sahipliği ve kurtarma bilgileri.

Alan adı, Vercel, R2, VPS ve GitHub bugün büyük ölçüde Egemen'in hesaplarına bağlıdır.
Mezuniyet öncesi seçeneklerden biri açıkça seçilmelidir:

1. sahipliği devam edecek öğrenciye devretmek,
2. okul hesabına taşımak,
3. sunucuyu geçici kabul edip deponun tek başına yeterli olmasını sağlamak.

Sunucu kolaylıktır; Git deposu ve yerel çalışma zinciri asıl sistem olmalıdır. Sonraki
takımın kim olacağına veya aracı nasıl değiştireceğine bu belge onların adına karar vermez.

---

## Son özet

Bu projenin ana yolu şudur:

1. Resmî kuralı ve fiziksel gerçeği doğrula.
2. Eski kodun bilgisini çıkar; kusurunu kopyalama.
3. Motor çıkışını varsayılan kapalı ve tek kapılı yap.
4. Görüntüyü sabit kliplerde ölç.
5. İki sistemi düşük riskli testlerle birleştir.
6. Görevleri birer birer, kanıtla ekle.
7. Her koşuyu kara kutuyla okunabilir yap.
8. İnsan incelemesi ve fiziksel anahtarları yazılım güvenliğinin üstünde tut.

Plan yol gösterir; gerçek kod, ölçüm, resmî kılavuz ve US'ın açık kararı son sözü söyler.
