# Yapılandırma Sözleşmesi — `kalibrasyon.json` ve `ayarlar.json`

Bu belge, StarTechConfig aracının ürettiği iki JSON dosyasının **v1 biçimini**
öğrencilerin okuyup açıklayabileceği şekilde tanımlar. Şema dosyaları bilgisayarın
okuduğu kesin kurallardır; bu belge aynı kuralların insan dilindeki açıklamasıdır.

> Bu sözleşmenin geçmesi aracın fiziksel olarak güvenli olduğunu kanıtlamaz. Yalnızca
> dosyanın beklenen alanlara, tiplere ve alanlar arası ilişkilere sahip olduğunu kanıtlar.
> Gerçek araç kullanımı için ölçüm, insan kod incelemesi, Egemen'in donanım izni ve
> ulaşılabilir fiziksel güç anahtarı hâlâ zorunludur.

## 1. Neden iki dosya var?

### `kalibrasyon.json`: araçta veya ortamda ölçülenler

Bu dosya şu sorulara cevap verir:

- Kamera hangi çözünürlükte çalıştı?
- Pist dörtgeninin köşeleri görüntünün neresinde?
- Beyaz şerit ve görev renkleri bu ışıkta hangi HSV aralığında?
- Motorların ölü bölgesi ve sağ/sol düzeltme çarpanları ne?

Kamera yeri, ışık, motor, tekerlek veya çözünürlük değişirse kalibrasyon eskiyebilir.

### `ayarlar.json`: ekip tarafından seçilen davranış

Bu dosya şu sorulara cevap verir:

- PID katsayıları ne?
- Araç hangi PWM yüzdesini hedefliyor?
- İzin verilen asgari ve azami hız ne?
- Bir desen ROI'nin ne kadar aşağısına geldiğinde “yakın” sayılıyor?

Bu değerler ölçüm sonucu olmak zorunda değildir; ekip test kanıtlarına bakarak seçer.

Kısa kural:

> “Bu araca/kameraya/piste ait fiziksel gerçek mi?” → kalibrasyon  
> “Aracın nasıl davranmasını istiyoruz?” → ayarlar

## 2. Dosyalar nerede?

Bu depodaki dosyalar canlı araç ayarı değildir:

- `config/schema/kalibrasyon-v1.schema.json`: bilgisayar sözleşmesi
- `config/schema/ayarlar-v1.schema.json`: bilgisayar sözleşmesi
- `config/schema/profil-v1.schema.json`: iki dosyayı eşleyen YAREN zarfı
- `config/examples/kalibrasyon-v1.ornek.json`: test örneği
- `config/examples/ayarlar-v1.ornek.json`: test örneği

StarTechConfig kullanıcının seçtiği klasöre gerçek `kalibrasyon.json` ve
`ayarlar.json` dosyalarını birlikte yazar. `config/examples` altındaki dosyaları
Raspberry Pi'ye kopyalamayın; isimlerindeki `.ornek` bunu hatırlatır.

YAREN'in kurulu profilleri depo içinde tutulmaz. Varsayılan yerler:

- Windows: `%LOCALAPPDATA%\STARTECH\configuration`
- Linux/Raspberry Pi: `$XDG_CONFIG_HOME/startech/configuration`; değişken yoksa
  `~/.config/startech/configuration`

`STARTECH_PROFILE_ROOT` ortam değişkeni veya komut satırındaki `--profile-root`, test
ve taşınabilir okul oturumları için bu konumu değiştirebilir.

## 3. `kalibrasyon.json` bölümleri

| Bölüm | Ne anlatır? | Önemli birim/biçim |
|---|---|---|
| `sema_surumu` | Dosya dilinin sürümü | v1 için tam olarak `1` |
| `damga` | Üretim zamanı ve içerik özeti | yerel tarih-saat, 6 haneli özet |
| `kamera` | Kalibrasyon sırasında kullanılan görüntü | piksel, boolean |
| `perspektif` | Kuş bakışına çevrilecek dört köşe | `[x, y]` piksel koordinatı |
| `serit` | Beyaz şerit profilleri ve kalite eşikleri | OpenCV HSV, piksel, oran |
| `renkler` | Görev nesnelerinin renk ve alan eşikleri | OpenCV HSV, piksel kare |
| `motor` | Motora özel trim ve ölü bölge | çarpan, PWM yüzdesi, tarih/null |

### 3.1 Damga ve kısa özet

`damga.ozet` tam SHA-256 metni değildir. StarTechConfig şu sırayı uygular:

1. Kalibrasyon nesnesinin kopyasını alır.
2. Üst düzey `damga` bölümünü tamamen çıkarır.
3. JSON'u boşluksuz biçime dönüştürür.
4. UTF-8 baytlarının SHA-256 özetini hesaplar.
5. İlk üç baytı altı küçük onaltılık karakter olarak yazar.

Örneğin `e11b19`. Bu kısa değer kazara değişikliği yakalamaya yardım eder; güvenlik
imzası, kimlik doğrulama veya kötü niyetli değiştirmeye karşı koruma değildir.

`damga.zaman` saat dilimi taşımayan yerel saattir. Bu nedenle farklı bilgisayarların
saatleri yanlışsa yalnız zaman alanına bakarak kesin sıralama yapılmamalıdır.

### 3.2 Kamera ve perspektif birlikte düşünülür

`kamera.genislik` ve `kamera.yukseklik`, `perspektif.olculen_cozunurluk` ile aynı
olmalıdır. Perspektif noktaları yalnız bu çözünürlükte geçerlidir.

Nokta sırası değişmez:

1. sol üst
2. sağ üst
3. sol alt
4. sağ alt

Koordinatlarda kenar dahildir. Örneğin 840×630 görüntü için `[840, 630]`, aracın
mevcut sözleşmesinde sağ-alt **kenar koordinatı** olarak kabul edilir. Bu değer bir
görüntü dizisini indekslemek için doğrudan kullanılmamalıdır.

Doğrulayıcı ayrıca şunları bekler:

- Sağ noktalar sol noktaların sağında olmalı.
- Üst kenar alt kenardan dar olmalı.
- Üst noktalar alt noktaların üstünde olmalı.
- Hiçbir koordinat kalibrasyon karesinin dışına çıkmamalı.

### 3.3 HSV biçimi

Her HSV değeri `[H, S, V]` sırasındadır:

- `H`: 0–180
- `S`: 0–255
- `V`: 0–255

Bu OpenCV ölçeğidir; bazı resim programlarının 0–360 ton ölçeğiyle aynı değildir.
Her `alt` bileşeni karşılık gelen `ust` bileşeninden büyük olamaz. Alt ve üst üçlüsü
tamamen aynıysa aralık hiçbir şeyi seçemeyeceği için reddedilir.

Turuncu aracın üst H değeri, sarı aracın alt H değerinden küçük olmalıdır. Bu ayrım
yarışma görevi açısından önemlidir; sarı tuzak aracın turuncu sanılması davranışı
değiştirebilir.

### 3.4 Motor alanları

`motor.olculdu` iki biçimden birindedir:

- `null`: ölçüm henüz yapılmadı.
- `YYYY-MM-DD`: ölçüm yapıldığı iddia edilen tarih.

Bir tarih yazılması ölçümün gerçekten yapıldığını kanıtlamaz. İnsan ölçüm formu ve
gözlemci kaydı yine gereklidir.

Dört trim değeri motor PWM'ine uygulanan çarpanlardır. Mevcut StarTechConfig bunları
`kalibrasyon.json` içine yazar. PLAN_New daha önce bu yerleşimi açık karar olarak
kesinleştirmediği için v1 şeması yalnız **bugünkü gerçek biçimi** belgeler; gelecekteki
v2 tasarım kararını kendiliğinden vermez.

0,5–1,5 dışındaki trimler şema tarafından otomatik silinmez; güçlü bir insan uyarısı
üretir. `olculdu` tarihliyken dört trim de 1,0 ise ölçümün gerçekten yapılıp yapılmadığı
tekrar sorulur.

## 4. `ayarlar.json` bölümleri

### `kontrol`

- `kp`: anlık şerit hatasına tepki
- `kd`: hatanın ne kadar hızlı değiştiğine tepki
- `ki`: zamanla biriken küçük hataya tepki
- `integral_max`: KI birikiminin sınırı
- `deriv_cap`: ani türev sıçramasının sınırı

`kp` ve `kd` sıfırdan büyük olmalıdır. `ki = 0` teşhis sırasında geçerlidir.
`ki > 0.2` dosyayı otomatik olarak bozuk yapmaz fakat savrulma riski nedeniyle insan
uyarısı üretir.

### `hiz`

`min`, `hedef` ve `max` tam sayı PWM yüzdeleridir ve 0–100 arasında olmalıdır:

```text
min <= hedef <= max
```

`k_speed` yüzde değil, şerit hatasına göre hız azaltma çarpanıdır. v1 sözleşmesinde
0–5 aralığındadır.

`hiz.max_not` açıklamadır; voltaj ölçümü değildir. “%57 anma gerilimidir” yazması,
motor uçlarında yük altında gerçekten güvenli voltaj görüldüğünü kanıtlamaz.

### `olay`

`yakin_roi_orani`, 0 ile 1 arasında görüntü oranıdır. Mevcut açıklamada yaklaşık
30 cm ile ilişkilendirilir; kamera yüksekliği/açısı değişirse bu yorum yeniden
ölçülmelidir.

## 5. Kesin hata ile uyarı farkı

### Kesin hata — dosya kullanılmamalı

- Eksik veya bilinmeyen alan
- Sayı yerine metin
- Yanlış şema sürümü
- PWM yüzdesinin 0–100 dışında olması
- `min <= hedef <= max` sırasının bozulması
- HSV sınırlarının veya alt/üst ilişkisinin bozulması
- Kamera ve perspektif çözünürlüğünün uyuşmaması
- Perspektif noktasının görüntü dışında olması
- İçerikle uyuşmayan kısa özet

### Uyarı — insan bilinçli karar vermeli

- `KI > 0.2`
- Trim değerinin 0,5–1,5 dışında olması
- Motor “ölçüldü” denmesine rağmen bütün trimlerin 1,0 kalması
- Asgari hızın ölçülen motor ölü bölgesinin altında olması

Uyarı “güvenlidir” anlamına gelmez. Yalnız durumun otomatik olarak tek bir doğru
cevabı olmadığını belirtir.

## 6. YAREN profil zarfı ve durumları

STARTECH-YAREN (CLARA), mevcut v1 dosyalarını değiştirmeden bir
`kalibrasyon.json` + `ayarlar.json` çiftini dış bir `profil.json` ile eşler. Tam adları:

- **Yapılandırma Arşivleme, Revizyon ve Etkinleştirme Noktası**
- **Configuration Loading, Archival and Revision Agent**

Her kurulu profil klasöründe yalnız üç dosya vardır:

```text
<profil-kimligi>/
    kalibrasyon.json
    ayarlar.json
    profil.json
```

`profil.json`; iki dosyanın tam SHA-256 özetini, kamera uyumluluğunu, üretim kaynağını,
ebeveyn revizyonunu ve güncel uyarı kümesinin özetini kaydeder. Kurulum sırasında JSON
şemaları ve alanlar arası kurallar yeniden denetlenir. Daha sonra tek bir bayt bile
değişirse profil bütünlük denetimini geçmez.

YAREN durumları özellikle birbirinden ayrıdır:

- **Imported / Kuruldu:** Çift doğrulandı ve inceleme için arşive alındı.
- **Review required / İnceleme gerekli:** Uyarılar varsa seçimden önce insan bunları
  görüp adını kaydetmelidir.
- **Selected / Seçildi:** ARDA'nın okuyacağı atomik işaretçi bu profile yöneliyor.
- **Archived / Arşivlendi:** Normal seçim listesinden çıkarıldı; veri silinmedi.
- **Safe to drive / Sürüşe güvenli:** YAREN bu durumu hiçbir zaman vermez.

Seçim TAWNT'ı başlatmaz, motor sürücüsü oluşturmaz ve aracı arm etmez. Etkin profil
arşivlenemez. Ayar düzenleyicisi mevcut dosyanın üstüne yazmak yerine ebeveyni belli
yeni bir profil oluşturur. v1 arayüzünde silme komutu bilerek yoktur.

### 6.1 Kayıt yapısı

```text
configuration/
    aktif-profil.json
    profiles/<kimlik>/...
    archive/<kimlik>/...
    history/<secim-kimligi>.json
    .staging/
```

`aktif-profil.json` profil kimliğini, iki tam özeti, uyarı özetini ve önceki seçim
kimliğini birlikte taşır. Aynı kayıt `history/` altında yoksa veya kayıt profil
özetleriyle uyuşmuyorsa `arac/ayar.py` güvenli biçimde yüklemeyi reddeder. Seçim
geçmişinde tamamlanmamış atomik yazımlar "orphaned" olarak görülebilir; etkin zincirin
parçası sayılmaz.

### 6.2 Kullanım

Kılavuzlu menü:

```powershell
py -3.13 -m arac.ayar_cli
```

ARDA içinden aynı menü:

```powershell
py -3.13 -m arac.main --auto --configuration --language tr
```

Otomasyon için alt komutlar `list`, `show`, `import`, `settings`, `activate`,
`compare`, `diagnose`, `history`, `archive`, `restore` ve `export` olarak sunulur.
Örneğin bir ayarı değiştirirken yalnız izin verilen sayısal yollar kullanılır:

```powershell
py -3.13 -m arac.ayar_cli settings <ebeveyn-kimligi> `
  --name "Yavaş sınıf testi" --set hiz.hedef=48 --set kontrol.kp=0.5
```

Bu komut ebeveyn profilini değiştirmez ve yeni profili otomatik seçmez.

## 7. Bugün bilerek çözülmeyen farklılıklar

İnceleme sırasında iki ayar grubu görüldü:

- Masaüstü dosyası: `kp=0.30`, `kd=0.45`, `ki=0.04`
- Son paylaşılan metin: `kp=0.58`, `kd=0.60`, `ki=0.20`

İki grup da v1 biçimine uyabilir. Şema “hangisi daha iyi sürer?” sorusunu cevaplayamaz.
Bu, kayıtlı video/bench testi ve insan değerlendirmesi gerektirir.

Ayrıca 960×540 ve 840×630 kalibrasyon çıktıları görüldü. İki çözünürlük de teknik
olarak geçerli olabilir; fakat bir çözünürlüğün perspektif noktaları diğerinde
kullanılamaz.

## 8. v1 dosyalarında bulunmayan kaynak bilgileri

Mevcut `kalibrasyon.json` ve `ayarlar.json` v1 dosyalarında şunlar yoktur:

- Kamera cihaz kimliği veya seri numarası
- Her alan için “kim, hangi araçla, nasıl ölçtü?” kaydı
- Kalibrasyonun son geçerlilik tarihi
- `ayarlar.json` içine gömülü eş kalibrasyon damgası (YAREN bunu dış zarfla eşler)
- Tam uzunlukta, güvenlik amaçlı dijital imza

Şema bunları varmış gibi göstermez. Eklenmeleri istenirse `sema_surumu: 2` için ayrı
bir plan, göç yöntemi, araç güncellemesi ve test gerekir.

## 9. Sürüm değiştirme kuralları

1. Bilinmeyen şema sürümü sessizce v1 olarak okunmaz.
2. Alan adı değiştirilirse eski alan sessizce kaybedilmez.
3. Dönüşüm, eski dosyanın üstüne yazmadan yeni bir dosya üretir.
4. Dönüşümden sonra yeni kısa özet hesaplanır.
5. Eski ve yeni dosya aynı testlerden geçirilir.
6. İnsan incelemesi yapılmadan yeni dosya araca yüklenmez.

## 10. Testi çalıştırma

Geliştirme bağımlılığı kurulduktan sonra depo kökünde:

```powershell
py -3.13 -m unittest -v tests.test_configuration tests.test_profiles tests.test_ayar tests.test_ayar_cli
```

Testler gerçek motorları çalıştırmaz. Geçerli örnekleri yükler, kasıtlı bozuk kopyalar
oluşturur ve bunların reddedildiğini doğrular.

## 11. Sık sorulan sorular

### İki JSON aynı dosyada olmak zorunda mı?

Hayır. Bilerek ayrıdırlar. StarTechConfig ikisini aynı klasöre birlikte kaydeder.

### İki dosyanın birbirine ait olduğu nasıl anlaşılır?

İki v1 dosyasının kendi içinde ortak kimlik yoktur. YAREN, içeriği değiştirmeden ikisini
`profil.json` içindeki ayrı tam SHA-256 değerleriyle eşler. Profil dışındaki iki başıboş
JSON'un birbirine ait olduğu yalnız dosya içeriklerinden kesin olarak anlaşılamaz.

### `VAR = DATA` yazmakla JSON alanı yazmak aynı mı?

Hayır. Basit değişken yalnız o çalışan programdaki değerdir. JSON alanı türü, adı,
sürümü ve diğer alanlarla ilişkisi doğrulanabilen kalıcı veridir.

### Şema geçtiyse dosyayı araca koyabilir miyiz?

Hayır. Önce değerlerin bu fiziksel araç için ölçüldüğü veya bilinçli seçildiği
kanıtlanmalı, kod insanlar tarafından incelenmeli ve donanım testi ayrıca
yetkilendirilmelidir.

### `damga.ozet` dosyanın güvenli olduğunu kanıtlar mı?

Hayır. Kazara değişikliği fark etmeye yarar. Altı karakter kısa olduğu ve gizli anahtar
kullanmadığı için saldırıya dayanıklı imza değildir.

### Neden canlı dosyalar depodaki örneklerin üstüne yazılmıyor?

Örnekler testin her bilgisayarda tekrar çalışabilmesi içindir. Canlı kalibrasyonlar
araç, kamera ve ölçüm oturumuna aittir; örnekle karışmaları tehlikelidir.

## 12. Mevcut araçta görülen doğrulama boşluğu

StarTechConfig, `kalibrasyon.json` yüklerken şema sürümünü kontrol eder. Mevcut
`AyarlariUygula` yolu ise `ayarlar.json` içindeki `sema_surumu` alanını aynı kesinlikle
kontrol etmiyor ve bazı eksik bölümleri sessizce atlayabiliyor. Bu belge veya test dosyası
WinForms uygulamasını kendiliğinden düzeltmez.

YAREN'in `arac/ayar.py` yükleyicisi seçili profilde iki şemayı, tam özetleri, uyarı
onayını, geçmiş kaydını ve istenirse gerçek kameradan gözlenen çözünürlüğü birlikte
denetler. Bu, WinForms uygulamasındaki sessiz atlama davranışını değiştirmez ve fiziksel
araçta hangi değerlerin doğru olduğunu kanıtlamaz. Web/WinForms göçü ayrı bir değişikliktir.
