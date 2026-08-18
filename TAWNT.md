# 3awnt (`tawnt.py` API'si ve `startech/tawnt/`) — öğrenci ve geliştirici kılavuzu

> **Durum (6 Ağustos 2026):** V2 güvenlik çekirdeği kodlandı ve otomatik testleri
> geçiyor. Henüz aracın gerçek motor/PWM çalışma zincirine bağlı değildir.
>
> **En önemli cümle:** 3awnt, kritik sayıların nereden geldiğini ve birbirleriyle
> çelişip çelişmediğini denetlemeye çalışan bir yazılım katmanıdır. Fiziksel acil
> durdurma sistemi değildir ve ölçüm yapıldığını kanıtlayamaz.

Bu belge dört şeyi birbirinden ayırır:

1. 3awnt'ın bugün gerçekten yaptığı işler,
2. bugün yapmadığı veya eksik yaptığı işler,
3. yeni araçta önerilen hibrit kullanım biçimi,
4. gelecekte eklenebilecek yöntemler.

Bir başlığın altında **ÖNERİ — HENÜZ YOK** yazıyorsa o özellik 3awnt API'sinde varmış
gibi davranılamaz. **KÜTÜPHANEDE UYGULANDI** ifadesi ise kodun ve birim testinin var
olduğunu söyler; gerçek araç entegrasyonu veya fiziksel güvenlik kanıtı değildir.

---

> **Dosya düzeni (18 Ağustos 2026):** `tawnt.py`, eski `import tawnt` kullanımını
> koruyan küçük ve açık API kapısıdır. Asıl uygulama `startech/tawnt/` altında değerler,
> hareket, arıza, ortak durum ve statik tarama sorumluluklarına ayrılmıştır. Bu yalnız
> kod düzenidir; 3awnt hâlâ gerçek `arac/surucu.py` zincirine bağlı değildir.

---

## 0. Kafası karışanlar için küçük sürüm

Önce büyük resmi bilmek yeterlidir: 3awnt bir **kural ve izin defteridir**. Sayıları
kendi kendine ölçmez ve motor sürmez; sizin verdiğiniz bilgiyi denetler ve bir komutun
yazılım kurallarına göre kabul edilip edilmediğini söyler.

En yaygın sıra şudur:

```text
defineValue            Bu değer nedir, sınırları ne?
    ↓
recordValue            Değeri kaç, nereden geldi?
    ↓
dependsOn              Başka hangi değere bağlı?
    ↓
defineWatchdog         Hangi bileşen düzenli haber vermeli?
    ↓
definePhase            Bu görev evresinde neye izin var?
    ↓
validateBeforeStart    Başlamadan önce her şey hazır mı?
    ↓
enterPhase + arm       Hangi evredeyiz ve insan izin verdi mi?
    ↓
validateMotorCommand   Bu tek motor komutu gerçekten kabul edilebilir mi?
```

Tamamen sahte ve açıklamalı çalışan örnek için:

```powershell
python fake_main.py
```

`fake_main.py` gerçek motor, GPIO veya kamera kullanmaz. Yalnız bellek içindeki
`FakeMotorDriver` listesine sayı yazar.

### 0.1 Değer yöntemleri

#### `defineValue(...)`

Bir değerin adını ve kurallarını tanımlar: “`MAX_PWM` diye bir değer olacak ve 0–100
arasında kalacak.” Henüz gerçek değeri kaydetmez; yalnız boş bir kayıt ve sınırlar oluşturur.

#### `recordValue(...)`

Tanımlanmış kayda gerçek değeri, kaynağı, kişiyi, tarihi ve notu ekler. Değer sınır dışıysa
veya `OLCULDU` denip tarih verilmediyse kaydı reddeder.

#### `dependsOn(...)`

Bir değerin başka hangi değere bağlı olduğunu bildirir. Örneğin kamera çözünürlüğü
değişirse ona bağlı perspektif noktalarını `STALE`, yani eskimiş yapar.

#### `requireMeasured(...)`

Seçilen profillerde bir değerin mutlaka `OLCULDU` kaynağı taşımasını ister. Bu etiket
ölçümün gerçekten yapıldığını kanıtlamaz; yalnız insanın ölçtüğünü beyan ettiğini gösterir.

#### `validateBeforeStart(...)`

Başlangıçtan önce değerleri, kaynakları, bağımlılıkları ve sıralama kurallarını topluca
denetler. Başarılı olması motor izni vermez; sistemi yalnız `READY_UNARMED` durumuna getirir.

#### `seal()`

Doğrulanmış değerleri koşu sırasında değiştirilemez hâle getirir. `arm()` gerektiğinde bunu
otomatik çağırır; kalibrasyon değişecekse yeni doğrulama oturumu gerekir.

#### `valueState(...)`

Tek bir değerin `DEFINED`, `RECORDED`, `VALIDATED`, `STALE` veya `SEALED` durumunu döndürür.
Bu yalnız sorgudur; değeri veya sistem durumunu değiştirmez.

#### `deger(...)`

Kaydedilmiş değerin kendisini döndürür; örneğin `57`. Ad tanıtılmamışsa veya henüz değer
atanmamışsa hata üretir.

#### `identifyRuntimeType(...)`

Değere `% PWM`, `px/s` veya `px/kare` gibi birim/tip etiketi ekler. Etiketi ölçmez;
uyuşmayan birimlerin yanlışlıkla karşılaştırılmasını önlemeye yardım eder.

#### `IsTwinOf(...)`

İki değerin birlikte anlam taşıdığını bildirir. Bir ikizin eksik olması veya sonradan
değişmesi, diğer kaydın yeniden kontrol edilmesini gerektirir.

#### `siblingIntAppr(...)`

`MIN_SPEED <= TARGET_SPEED <= MAX_SPEED` gibi bir sıralama kuralı kurar. Değerlerin her
biri kendi sınırında olsa bile birlikte çelişiyorlarsa doğrulamayı reddeder.

### 0.2 Eski ve yeni değer adları

#### `introduce(...)`

`defineValue(...)` yönteminin eski uyumluluk adıdır. Yeni kod daha anlaşılır olduğu için
`defineValue(...)` kullanmalıdır; eski kod hemen bozulmasın diye `introduce(...)` korunur.

#### `acquire(...)`

`recordValue(...)` yönteminin eski uyumluluk adıdır. `kaynak`, `kim`, `tarih` ve `notu`
Türkçe parametrelerini kabul eder.

#### `preacquire(...)`

Eski başlangıç kontrolüdür; adı yanıltıcı olsa da `acquire` işleminden **sonra**, program
başlamadan önce çalışır. Profil ve `STALE` kurallarını zorlamadığı için yeni LIVE kodunda
`validateBeforeStart(...)` tercih edilmelidir.

### 0.3 Sistem, evre ve hareket yöntemleri

#### `systemState()`

Sistemin şu an `BOOT`, `READY_UNARMED`, `ARMED`, `MUTED` veya `LATCHED_FAULT` gibi hangi
durumda olduğunu döndürür. Yalnız bilgi verir; sistemi açmaz veya kapatmaz.

#### `definePhase(...)`

Bir görev evresinin hareket politikasını tanımlar: PWM tavanı, ters yön, pivot, hız değişimi,
zorunlu değerler ve watchdog'lar. Evreyi tanımlamak o evreye geçmek veya motoru açmak değildir.

#### `validatePhase(...)`

Belirli evrenin zorunlu değerlerini ve heartbeat'lerini kontrol eder. Eksik gereksinimde
evreyi hazır kabul etmez ve güvenli tarafta kalmak için sahte/sıfır çıkış geri çağrılarını dener.

#### `enterPhase(...)`

İzin verilen görev evresine geçer ve geçmeden önce `validatePhase(...)` çalıştırır. Geçici
susturma uygun evre değişiminde kalkabilir; ciddi kilit asla evre değişimiyle kalkmaz.

#### `arm(...)`

Doğrulanmış ve evresi seçilmiş sisteme açık insan yazılım izni verir. LIVE profilinde
donanım yetkisi ve son onay bayraklarını ister; bunların doğru olduğunu fiziksel olarak göremez.

#### `disarm(...)`

Hareket iznini kaldırır ve kayıtlı duruş geri çağrılarını çalıştırır. Yazılımın sıfır istemesi,
tekerleklerin gerçekten durduğunun fiziksel kanıtı değildir.

#### `isMotionAllowed()`

Sistem, arming, evre, susturma ve kilit durumuna göre şu an hareket izni olup olmadığını
`True/False` olarak döndürür. Yalnız sorgudur; `True` dönmesi kendi başına PWM yazmaz.

#### `validateMotorCommand(...)`

Tek bir sol/sağ komutunu durum, evre, sınır, yön, fark, slew ve watchdog kurallarından
geçirir. Başarılıysa `ValidatedMotorCommand` döndürür; fiziksel PWM'i kendisi yazmaz.

#### `ValidatedMotorCommand`

3awnt'ın kabul ettiği sol, sağ, evre, profil ve zaman bilgilerini taşıyan değişmez sonuç
nesnesidir. Gelecekte gerçek sürücü ham sayıyı değil, bu doğrulanmış nesneyi kullanmalıdır.

#### `TawntHatasi`

Bir 3awnt kuralı bozulduğunda yükseltilen özel Python hatasıdır. Çağıran kod bu hatayı
yutup eski PWM ile devam etmemeli; güvenli duruma geçmelidir.

### 0.4 Watchdog yöntemleri

#### `defineWatchdog(...)`

Kamera veya kontrol döngüsünün izin verilen en uzun sessizlik süresini tanımlar. Bu yalnız
zaman kuralıdır; kameranın doğru görüntü verdiğini kanıtlamaz.

#### `heartbeat(...)`

Tanımlı bileşenin “bu döngü noktasına ulaştım” zamanını yeniler. Kodun çalıştığını gösterir,
üretilen verinin doğru veya güvenli olduğunu göstermez.

#### `checkWatchdogs(...)`

İstenen heartbeat'lerin hiç gelmemiş veya süresini aşmış olup olmadığını denetler. Eksik
heartbeat'te hata üretir; LIVE motor kapısında bu durum ciddi kilide dönüşebilir.

### 0.5 Duruş, kilit ve kalıcılık yöntemleri

#### `onShutdown(...)`

3awnt duruş istediğinde çağrılacak işlevi kaydeder. Geri çağrının doğru sürücüye bağlı ve
fiziksel olarak etkili olduğunu 3awnt tek başına kanıtlayamaz.

#### `flushPWM(...)`

Normal evre geçişi gibi durumlarda geçici hareket susturması oluşturur ve sıfır çıkış
geri çağrılarını dener. Bu ciddi kilit değildir; uygun farklı evreye geçince kalkabilir.

#### `latchFault(...)`

Ciddi arıza kaydı oluşturur, sistemi `LATCHED_FAULT` yapar ve hareket iznini kaldırır.
Fault-store yapılandırılmışsa kayıt diske de yazılır ve Python yeniden başlasa bile kalabilir.

#### `configureFaultStore(...)`

Kalıcı ciddi kilit JSON dosyasının yolunu ayarlar ve varsa eski kilidi okur. Yalnız yolu
ayarlamak dosya oluşturmaz; fault veya reset yazıldığında dosya oluşur.

#### `resetFault(...)`

Kilit temizlemek için insan adı ve `motor_power_off=True` beyanı ister. Reset sonrası
sistem `ARMED` olmaz; yeniden `VALIDATING`, doğrulama ve arming gerekir.

#### `kilitDurumu()`

Aktif ciddi kilidin neden, ayrıntı, zaman ve profil bilgilerini sözlük olarak döndürür.
Kilit yoksa `None` döndürür ve hiçbir durumu değiştirmez.

#### `declareUnexpectedSigint(...)`

`latchFault(...)` kullanan eski uyumluluk adıdır. Adına rağmen CTRL+C veya işletim sistemi
sinyalini kendiliğinden yakalamaz; `main.py` sinyali ayrıca bağlamalıdır.

### 0.6 İnceleme ve yardımcı yöntemler

#### `scanDirectMotorWrites(...)`

Python dosyalarında şüpheli doğrudan motor/PWM yazımı ve sabit motor komutu arayan AST
taramasıdır. Yararlı bir alarmdır fakat gizlenmiş her bypass'ı bulacağının garantisi yoktur.

#### `report()`

Kayıtlı değerleri, kaynakları, birimleri ve durumları insanın okuyabileceği metne dönüştürür.
Rapor yazılım beyanını gösterir; ölçüm veya fiziksel başarı kanıtı değildir.

#### `differenceSkew(...)`

Perspektif dörtgeninin sağ-alt köşesindeki en fazla bir piksellik sınır farkını düzeltir.
Daha büyük çözünürlük uyuşmazlığını gizlemek yerine reddeder ve yeniden kalibrasyon ister.

#### `sifirla()`

3awnt'ın süreç içi belleğini testler arasında temizler. **Yalnız test/demo içindir; gerçek
araç kodu çağırmamalıdır** ve diskteki fault-store dosyasını silmez.

#### `evreDegisti(...)`

Eski evre değiştirme uyumluluk adıdır. Evre `definePhase(...)` ile tanımlıysa yeni
`enterPhase(...)` yolunu kullanır; tanımsız eski kullanım yalnız geçici susturmayı yönetir.

#### `pwmSerbestMi()`

`isMotionAllowed()` yönteminin eski Türkçe uyumluluk adıdır. Yalnız izin durumunu sorar;
PWM üretmez, motor açmaz ve ciddi kilidi kaldırmaz.

---

## 1. 3awnt neden var?

Mayıs 2026 aracındaki birçok hata, tek başına yanlış bir sayıdan değil, **hikâyesi
kaybolmuş bir sayıdan** doğdu:

- Perspektif köşeleri 640×480 görüntü için seçilmişti; görüntü daha sonra 800×680 oldu.
- Motor trimleri `1.0` olarak kaldı. Bunun ölçülmüş sonuç mu, geçici varsayım mı olduğu
  koddan anlaşılamıyordu.
- Türev sınırı ile hesaplanan türev farklı zaman birimleri taşıyordu.
- Birbirine bağlı hız değerleri ayrı ayrı makul görünürken birlikte çelişiyordu.

3awnt'ın amacı şu soruları görünür kılmaktır:

- Bu değer nereden geldi?
- Kim ölçtü veya devraldı?
- Ne zaman ölçüldü?
- Hangi aralıkta olmalı?
- Hangi başka değerle birlikte değişmek zorunda?
- Birimi nedir?
- Başlatmadan önce gerçekten hazır mı?

3awnt bir “doğruluk makinesi” değildir. Yanlış bilgi girilirse yanlış bilgiyi düzenli
biçimde saklayabilir. Bu yüzden insan incelemesinin yerine geçmez.

---

## 2. İsim nereden geliyor?

Sistemin adı `3awnt` olarak anılıyor; dış API dosyası `tawnt.py` olmak zorunda, çünkü
Python modül adı rakamla başlayamaz.

Takımın açılımı **3rd-party Automated Watchdog for Network Threats** biçimindedir.
Ayrıca ad, “korumak” anlamıyla ilişkilendirilen `защит` yazısının bir yapay zekâ
tokenleştirme hatasından doğmuştur.

Bu açılım hedeflenen kimliği anlatır; bugünkü 3awnt API'si **ağ trafiğini izlemez**, paket
incelemez ve ağ saldırısı tespit etmez. Şu an kritik değerleri, sistem durumunu, heartbeat'i
ve motor komutu politikasını denetleyen yerel bir Python güvenlik katmanıdır. İsim bir
güvenlik sertifikası değildir.

---

## 3. V1 uyumluluk yöntemleri

Bu bölüm, mevcut `tawnt` API'sinin doğrulanmış davranışını açıklar.

### 3.1 `introduce(...)`: değeri önceden tanıtmak

Bir kritik değer kullanılmadan önce adı, sınırları ve açıklaması tanıtılır:

```python
import tawnt

tawnt.introduce(
    "MAX_PWM",
    min=0,
    max=100,
    preferred=57,
    aciklama="Motor gerilimine göre izin verilen PWM üst sınırı",
)
```

Neden iki aşama var? Çünkü sınır, değer girilmeden önce bilinmelidir. Sonradan eklenen
bir sınır daha önce kabul edilmiş değeri güvenilir hâle getirmez.

Her sayaç veya geçici değişken 3awnt'a tanıtılmaz. Şu soruyu sorun:

> Bu değer yanlış olursa araç yanlış karar verir, zarar görür veya test sonucu
> anlamsızlaşır mı?

Cevap hayırsa normal değişken olarak kalabilir.

### 3.2 `acquire(...)`: değeri ve kaynağını kaydetmek

```python
tawnt.acquire(
    "MAX_PWM",
    57,
    kaynak=tawnt.OLCULDU,
    kim="Egemen",
    tarih="2026-09-12",
    notu="Tam PWM sırasında motor uçlarında multimetreyle ölçüldü",
)
```

Mevcut üç kaynak etiketi:

| Etiket | Anlamı | Güvenli yorum |
|---|---|---|
| `OLCULDU` | Bir insan ölçtüğünü beyan ediyor | Tarih zorunludur; ölçümün kendisi doğrulanmaz |
| `DEVRALINDI` | Eski koddan veya belgeden geldi | Tekrar ölçülene kadar kesin kabul edilmez |
| `VARSAYILDI` | Tahmin veya başlangıç değeri | Deney tasarlamak için kullanılabilir; kritik fiziksel test için yeterli olmayabilir |

Tarihsiz `OLCULDU` reddedilir. Bu iyi bir korumadır fakat bir kişinin gerçekten
multimetre kullandığını ispatlamaz.

### 3.3 `preacquire(...)`: başlatma öncesi toplu kontrol

```python
tawnt.preacquire("MAX_PWM", "OLU_BOLGE", "PERSP_SRC", "KARE")
```

Bugünkü uygulama şunları denetler:

- isim tanıtılmış mı,
- değer atanmış mı,
- değer belirtilen sınırlar içinde mi,
- ikiz değer de atanmış mı,
- kayıtlı kardeş sıralaması tutuyor mu.

**Önemli sınır:** Geriye uyumluluk için `preacquire`, `VARSAYILDI` kaynağını yalnızca
kaynak türü nedeniyle reddetmez. Gerçek araç için bunun yerine kritik değer
`critical=True` ile tanımlanmalı ve `validateBeforeStart(profile=LIVE)` kullanılmalıdır;
bu kapı ölçülmemiş kritik değeri reddeder.

### 3.4 `IsTwinOf(...)`: birlikte anlam taşıyan değerler

```python
tawnt.IsTwinOf("PERSP_SRC", "KARE")
```

Perspektif köşeleri, ölçüldükleri görüntü çözünürlüğü olmadan anlamlı değildir. İkiz
ilişkisi, iki değerden biri hiç atanmamışsa bunu açılış kontrolünde gösterir.

V2 çekirdeğinde ikizler aynı zamanda karşılıklı bağımlılık olarak kaydedilir. Birinin
değeri değişirse diğeri `STALE` olur ve tekrar doğrulanmadan `LIVE` başlangıcını geçemez.

### 3.5 `siblingIntAppr(...)`: sayısal sıralama ilişkisi

```python
tawnt.siblingIntAppr(
    "OLU_BOLGE", "<=", "MIN_HIZ",
    "<=", "HEDEF_HIZ", "<=", "MAX_HIZ",
)
```

Bu yöntem tek tek geçerli görünen değerlerin birlikte anlamsız olmasını yakalamaya
çalışır. Örneğin eski değerlerde:

- `OLU_BOLGE = 30`
- `MIN_HIZ = 25`

olduğunda `30 <= 25` doğru değildir. Aynı şekilde hedef hız 62 iken tavan 57 yapılırsa
`62 <= 57` ilişkisi bozulur.

Desteklenen işleçler: `<`, `<=`, `>`, `>=`, `==`.

### 3.6 `identifyRuntimeType(...)`: birim etiketi

```python
tawnt.identifyRuntimeType("DERIV_CAP", "px/s")
tawnt.identifyRuntimeType("KARE_BASI_DEGISIM", "px/kare")
```

Amaç, piksel/saniye ile piksel/kare gibi farklı birimleri yanlışlıkla karşılaştırmamaktır.
30 FPS'te bu fark yaklaşık 30 katlık hata doğurabilir.

Bu yöntem gerçek bir fiziksel birim kütüphanesi değildir. Birimler yazı olarak bildirilir;
etiketi doğru yazmak yine geliştiricinin sorumluluğudur.

### 3.7 `differenceSkew(...)`: köşe sapması

```python
koseler, tasindi = tawnt.differenceSkew(koseler, (800, 680))
```

Bugünkü niyet:

- en fazla 1 piksel farkı indeks/koordinat yuvarlaması kabul etmek,
- daha büyük çözünürlük uyuşmazlığını reddetmek.

640×480 için seçilmiş köşeleri 800×680 görüntüye sadece “uzatarak” taşımak doğru değildir.
Dörtgen yeniden ölçülmelidir. Tek köşeyi taşımak tüm perspektifi deforme edebilir.

### 3.8 `onShutdown(...)`: kapatma geri çağrıları

```python
@tawnt.onShutdown
def motorlari_kapat():
    surucu.hepsini_kapat()
```

3awnt GPIO veya motor sürücüsü tanımaz. Kapatma isteğini kayıtlı işleve iletir. Bu tasarım,
Windows'taki testlerin Raspberry Pi kütüphanelerine bağımlı olmamasını sağlar.

**Fakat:** yalnızca bir geri çağrı kaydetmek motorların fiziksel olarak kapandığını
kanıtlamaz. Geri çağrı hiç kaydedilmemiş, hata vermiş veya yanlış sürücüye bağlanmış olabilir.

### 3.9 `declareUnexpectedSigint(...)`: süreç içi kilit

```python
tawnt.declareUnexpectedSigint(
    "kamera kare üretmiyor",
    "12 ardışık kare None döndü",
)
```

Bugünkü uygulamada bu çağrı:

1. kayıtlı kapatma işlevlerini çağırır,
2. olayı günlüğe yazmaya çalışır,
3. süreç içindeki kilidi kapatır,
4. `pwmSerbestMi()` sonucunu `False` yapar.

Adında `SIGINT` geçmesi, yöntemin işletim sistemi sinyalini kendiliğinden yakaladığı anlamına
gelmez. `main.py` ayrıca `SIGINT`, `SIGTERM` ve beklenmeyen hataları bağlamalıdır.

Kilit tek yönlüdür. `configureFaultStore(...)` ile kalıcı kayıt yapılandırılmışsa program
yeniden başlasa da geri yüklenir. `LIVE` profili kalıcı kayıt yolu olmadan başlangıç
doğrulamasını reddeder.

### 3.10 `flushPWM(...)` ve `evreDegisti(...)`: geçici susturma

```python
tawnt.flushPWM("Görev bitti; yeni evre bekleniyor", evre="YAYA_GECIDI")
tawnt.evreDegisti("SERIT_TAKIP")
```

Susturma, normal bir evre geçişinde PWM'i geçici olarak engellemek içindir. Yeni evreye
geçilince kalkabilir.

Kilit ile susturma aynı şey değildir:

| Durum | Amaç | Kendiliğinden kalkar mı? |
|---|---|---|
| Kilit | Beklenmeyen arıza sonrası yeniden çalışmayı engellemek | Hayır; insan kontrollü reset gerekir |
| Susturma | Normal evre geçişinde geçici motor komutunu engellemek | Evet; evre değişince |

Susturma kalıcı kilidi açamaz.

### 3.11 `pwmSerbestMi()`: yazılım izni sorgusu

Motor katmanı bu sonucu kontrol edebilir:

```python
if not tawnt.pwmSerbestMi():
    surucu.hepsini_kapat()
    return
```

**Kritik mevcut davranış:** Yeni bir Python süreci başladığında `pwmSerbestMi()`
`False` döner. Başlangıç doğrulaması, evre seçimi ve `arm()` tamamlanmadan hareket izni
verilmez. Buna rağmen gerçek motor katmanı bu sonucu zorunlu kapı yapmadıkça 3awnt fiziksel
PWM'i engelleyemez.

### 3.12 `report()`: beyan raporu

`report()`, kayıtlı değerleri ve kaynaklarını insanın okuyabileceği biçimde gösterir.

Bu çıktı:

- hangi sayıların ölçülmüş diye işaretlendiğini,
- hangilerinin devralındığını,
- hangilerinin varsayım olduğunu

gösterebilir. Ölçümün gerçekten yapıldığını kanıtlayamaz. SUBIRU veya başka bir sistem
bu raporu tek başına `KANIT` kabul etmemelidir.

---

## 4. Bugünkü gerçek entegrasyon durumu

6 Ağustos 2026 itibarıyla:

- `tawnt.py`, `startech/tawnt/`, `tests/test_tawnt.py` ve bu kılavuz Git tarafından izlenmektedir.
- V2 çekirdeği ve sahte öğretici ana program toplam 39 otomatik `unittest` davranış
  testiyle doğrulanmaktadır: 34 çekirdek testi + 5 `fake_main.py` testi.
- Değer yaşam döngüsü, OFFLINE/BENCH/LIVE profilleri, fail-closed arming, evre politikası,
  heartbeat/watchdog, kalıcı ciddi kilit ve statik motor erişimi taraması kütüphanede vardır.
- Üretim aracı çalışma zinciri 3awnt'ı henüz çağırmamaktadır.
- SIGINT, SIGTERM, yakalanmamış hata, kamera üreticisi ve GPIO sürücüsü henüz bağlanmamıştır.
- Hiçbir üretim motor sürücüsü `validateMotorCommand(...)` sonucunu zorunlu fiziksel kapı
  olarak kullanmamaktadır.

Bu nedenle doğru ifade şudur:

> 3awnt v2 kütüphanesi vardır ve testlidir; araç güvenlik zincirine entegrasyonu henüz
> yapılmamıştır.

“3awnt aracı koruyor” ifadesi bugün doğru değildir.

---

## 5. Bilinen sınırlar ve yanlış güven tehlikesi

1. `OLCULDU` etiketi ölçümü doğrulamaz; yalnızca beyanı saklar.
2. Geriye uyumlu `preacquire`, varsayılan değerleri kaynak türü nedeniyle reddetmez;
   `LIVE` için `validateBeforeStart` kullanılmalıdır.
3. Kalıcı kilit yalnız `configureFaultStore(...)` doğru yapılandırılmışsa restarttan sonra kalır.
4. `resetFault(..., motor_power_off=True)` fiziksel anahtarı okuyamaz; insan beyanını kaydeder.
5. Heartbeat yalnız bu Python sürecindeki üreticinin yöntemi çağırdığını gösterir; kameranın
   doğru görüntü verdiğini kanıtlamaz.
6. Başlangıçta hareket izni kapalıdır; fakat motor sürücüsü 3awnt'ı çağırmazsa atlanabilir.
7. Kapatma geri çağrısı fiziksel duruşu ispatlamaz.
8. 3awnt, motor kablolarının doğru bağlandığını bilemez.
9. 3awnt, yasak bir haberleşme modülünün araçtan fiziksel olarak çıkarıldığını bilemez.
10. 3awnt, kameranın gördüğü maskenin gerçekte doğru renge ait olduğunu bilemez.
11. Günlük dosyasına yazılması olayın gerçekleştiğini değil, yazılımın yazdığını gösterir.
12. Bütün kurallar tek modülde büyürse modül anlaşılması zor bir “tanrı nesne”ye dönüşebilir.
13. Statik tarama şüpheli doğrudan GPIO/PWM yazımlarını bulmaya çalışır; dinamik veya
    gizlenmiş her bypass'ı bulacağının garantisi yoktur.

En tehlikeli hata, çalışmayan koruma değil; çalıştığı sanılan korumadır.

---

## 6. Önerilen hibrit yapı

> **ÖNERİ — HENÜZ ÜRETİMDE YOK**

Hibrit sözcüğü burada iki yaklaşımın birlikte kullanılması demektir:

- Kurallar ve kritik değerlerin hikâyesi merkezde tutulur.
- Fiziksel karar, ilgili donanımın sahibi olan modülde uygulanır.

### Basit benzetme

3awnt okulun kural defteri gibidir. “Bu deney için izin var mı?” sorusuna cevap verir.
`surucu.py` ise laboratuvar dolabının gerçek anahtarıdır. Defter izin verse bile dolabı
açan tek yer odur. Defter dolabı fiziksel olarak kilitlemez.

### Sorumluluk dağılımı

| Parça | Sorumluluğu | Yapmaması gereken |
|---|---|---|
| `tawnt.py` | Kararlı dış API ve geriye uyumlu adlar | Kendi içinde güvenlik durumunu çoğaltmak |
| `startech/tawnt/` | Kritik değer, hareket, arıza, ortak durum ve tarama kuralları | GPIO sürmek veya fiziksel duruş iddia etmek |
| `ayar.py` | JSON dosyalarını yüklemek, şemayı doğrulamak, 3awnt'a değer vermek | PWM üretmek |
| `surucu.py` | Motor komutunun tek fiziksel çıkışı, fail-closed kapı | Kontrolü atlayarak doğrudan GPIO vermek |
| `durum.py` | Aracın durumunu ve izin verilen geçişleri yönetmek | Motor pinlerine doğrudan yazmak |
| `main.py` | Bileşenleri bağlamak, sinyalleri ve beklenmeyen hataları yakalamak | Güvenlik hatasını yutup eski PWM ile devam etmek |
| `kayit.py` | Olay, kare, komut ve hata geçmişini kaydetmek | Kayıt var diye fiziksel başarı iddia etmek |
| `bildir.py` | LED/buzzer ile insana durum göstermek | Tek güvenlik kanalı olmak |

### Önerilen izin zinciri

Motor komutu yalnızca bütün soruların cevabı evet ise uygulanmalıdır:

1. Yapılandırma okundu mu?
2. Zorunlu değerler doğrulandı mı?
3. İnsan tarafından arming yapıldı mı?
4. Durum makinesi motor sürmeye izin veriyor mu?
5. Kamera ve kontrol döngüsü zamanında veri üretiyor mu?
6. Kalıcı arıza kilidi kapalı mı?
7. Geçici PWM susturması kapalı mı?
8. Komut sınırlar içinde ve sonlu bir sayı mı?
9. Gerçek sürücü test modu yerine yanlışlıkla açılmadı mı?

Sorulardan biri hayırsa `surucu.py` sıfır PWM uygulamalı ve komutu reddetmelidir.

### Neden yalnızca 3awnt içinde yapmıyoruz?

Çünkü 3awnt fiziksel motor sürücüsünü tanımaz. Her şeyi ona verirsek Windows testleri
zorlaşır, modül büyür ve başka kodun onu atlaması kolaylaşır.

### Neden her modüle ayrı ayrı dağıtmıyoruz?

Çünkü aynı kural farklı yerlerde farklı biçimde yazılırsa zamanla birbirinden kopar.
Merkezi kayıt, bütün kritik değerleri tek raporda görmeyi ve ortak test yazmayı kolaylaştırır.

Hibrit yapı, merkezi açıklama ile yerel fiziksel uygulamayı birleştirir.

---

## 7. Önerilen açılış sırası

> **ÖNERİ — entegrasyon planı onaylanmadan uygulanmaz.**

1. `surucu.py` oluşturulur; başlangıç durumu kesin olarak kapalıdır.
2. Kapatma geri çağrısı 3awnt'a kaydedilir.
3. Kritik değerler `introduce` ile tanıtılır.
4. İkizler, sıralamalar ve birimler bildirilir.
5. `ayar.py` JSON dosyalarını şemaya göre yükler.
6. Her değer kaynağıyla birlikte `acquire` edilir.
7. Ölçülmesi zorunlu değerler için daha sıkı kapı çalıştırılır.
8. Yapılandırma ve kod kimliği kayda yazılır.
9. Sahte sürücüyle self-test yapılır.
10. Sistem `HAZIR_AMA_SILAHLI_DEGIL` durumuna gelir.
11. İnsan incelemesi ve Egemen'in donanım izni alınır.
12. Tehlikeli adımdan hemen önce son onay istenir.
13. Fiziksel arming ayrı bir olayla yapılır.
14. Watchdog sağlıklıysa motor komutu kabul edilir.

Programın açılması motorların otomatik olarak silahlanması anlamına gelmemelidir.

---

## 8. Uygulanan ve gelecekte eklenebilecek yöntemler

Her yöntemin durumu kendi başlığının altında yazılıdır. “Uygulandı” yalnız kütüphane ve
otomatik test anlamına gelir; araç entegrasyonu yine ayrı plan ve insan incelemesi ister.

### 8.1 `seal()` — kayıt defterini dondurmak

> **KÜTÜPHANEDE UYGULANDI.** `arm()` da doğrulanmış değerleri otomatik mühürler.

Başlatma doğrulandıktan sonra kritik değerlerin sessizce değiştirilmesini engeller.
Kalibrasyon değişecekse yeni bir oturum veya açık bir yeniden-kalibrasyon işlemi gerekir.

### 8.2 `requireMeasured(...)` — ölçülmüş kaynak zorunluluğu

> **KÜTÜPHANEDE UYGULANDI.** Ayrıca `critical=True`, değeri `LIVE` için otomatik olarak
> ölçüm zorunluluğuna ekler.

Örnek:

```python
tawnt.requireMeasured("MAX_PWM", "MOTOR_GERILIMI", "PERSP_SRC")
```

Bu kapı `VARSAYILDI` ve gerekirse `DEVRALINDI` değerleri fiziksel test öncesinde reddeder.
Bilgisayar üzerindeki klip testinde farklı, gerçek motor testinde daha sıkı profil kullanılabilir.

### 8.3 `dependsOn(...)` ve revizyon sayacı

> **KÜTÜPHANEDE UYGULANDI.** Bilinmeyen ad ve bağımlılık döngüsü reddedilir.

Bir değer değiştiğinde ona bağlı değerleri “eskimiş” yapar.

```python
tawnt.dependsOn("PERSP_SRC", "KARE", "KAMERA_YUKSEKLIGI")
```

Çözünürlük veya kamera yüksekliği değiştiğinde perspektif kalibrasyonu yeniden istenir.

### 8.4 `derive(...)` — türetilmiş değerin formülü

> **ÖNERİ — HENÜZ YOK.**

Bir değerin elle kopyalanması yerine hangi formülle üretildiğini kaydeder. Örneğin PWM
tavanı; pil gerilimi, motor nominal gerilimi ve güvenlik payından türetilebilir. Formül
ölçümün yerini almaz fakat hesabın tekrar üretilebilmesini sağlar.

### 8.5 `bindCalibrationProfile(...)` — kalibrasyonu donanıma bağlamak

> **ÖNERİ — HENÜZ YOK.**

Kalibrasyon dosyasına şunları bağlar:

- kamera kimliği,
- çözünürlük ve FPS,
- kamera yüksekliği/açısı,
- araç veya şasi kimliği,
- oluşturulma tarihi,
- kalibrasyonu yapan kişi.

Yanlış kamera profili yüklenirse araç silahlanmaz.

### 8.6 `arm()` / `disarm()` — fail-closed yazılım kapısı

> **KÜTÜPHANEDE UYGULANDI.** `LIVE` arming, donanım yetkisi ve son onay bayraklarını
> açıkça ister; bu bayraklar yine çağıran insan arayüzünün beyanıdır.

Başlangıçta izin kapalı olur. Bütün self-testler geçmeden ve açık insan arming olayı
gelmeden PWM açılamaz. `disarm()` her zaman mümkündür; arıza kilidinden sonra `arm()`
reddedilir.

Bu yöntem fiziksel anahtarın yerini almaz.

### 8.7 `defineWatchdog(...)`, `heartbeat(...)`, `checkWatchdogs(...)`

> **KÜTÜPHANEDE UYGULANDI.** Evreler `required_watchdogs=(...)` ile gerekli heartbeat'leri
> belirtir. Eksik veya gecikmiş heartbeat evreyi/komutu reddeder; `LIVE` komutunda kilitler.

Kamera, kontrol döngüsü ve motor komutu güncellemesinin beklenen sürede gelip gelmediğini
izler. Süre aşımında son PWM'i korumak yerine sıfıra çeker ve kilitler.

Watchdog ayrı bir iş parçacığı veya süreç kullanacaksa, onun da donması ve saat kaynağının
nasıl seçileceği test edilmelidir.

### 8.8 `configureFaultStore(...)`, `latchFault(...)`, `resetFault(...)`

> **KÜTÜPHANEDE UYGULANDI.** JSON kayıt geçici dosya + atomik değiştirme ile yazılır.
> Bozuk kayıt güvenli tarafta kalıp kilit kabul edilir.

Ciddi arıza kilidini disk üzerinde saklar. Servis veya güç yeniden geldiğinde araç otomatik
olarak silahlanmaz. İnsan arızayı okur, nedeni çözer ve kontrollü sıfırlama yapar.

SD kart yazma hataları ve ani güç kesintisi düşünülmelidir; kayıt tek güvenlik noktası olamaz.

### 8.9 `snapshot(...)` — çalıştırılan sürümü tanımlamak

> **ÖNERİ — HENÜZ YOK.**

Şunların özet kimliğini kaydeder:

- Git commit,
- çalışma ağacı temiz/kirli durumu,
- yapılandırma dosyası hash'i,
- kalibrasyon dosyası hash'i,
- kullanılan yarışma kılavuzu sürümü.

“Hangi kodla bu turu yaptık?” sorusuna cevap verir.

### 8.10 `validateMessage(...)` — modüller arası sözleşme

> **ÖNERİ — HENÜZ YOK.**

Görüntü işleme ile durum makinesi arasında taşınan olay sözlüğünü doğrular. Örneğin eski
kodda `main.py`, `sign_type` beklerken olay üreticisi bu alanı üretmiyordu. Şema kontrolü
bu tür sessiz kopuklukları yakalar.

### 8.11 `competitionMode(...)`

> **ÖNERİ — HENÜZ YOK.** Bugünkü isim açılımında “Network Threats” bulunsa da kodda
> ağ izleme veya yarışma ağı denetimi yoktur.

Yarışma kipinde ağ sunucusu, uzaktan komut, debug arayüzü veya izin verilmeyen ayarların
yazılım tarafında açık olmadığını kontrol eder.

Sınırı açıktır: Yazılım fiziksel olarak bağlı bir modülü kesin biçimde kanıtlayamaz. Son
kontrol insana ve teknik kontrole aittir.

### 8.12 `faultInjection(...)` — hata enjekte etme

> **ÖNERİ — HENÜZ YOK.** Bazı hata senaryoları birim testlerinde tek tek uygulanır;
> birleşik bir fault-injection aracı yoktur.

Sahte motor sürücüsüyle şu senaryolar otomatik denenir:

- kamera kare üretmiyor,
- NaN veya sonsuz motor komutu,
- kontrol döngüsü gecikiyor,
- yapılandırma eksik,
- kapatma geri çağrısı hata veriyor,
- evre değişirken PWM geliyor,
- süreç yeniden başlıyor.

Her senaryoda gerçek GPIO yerine kaydedilen komutların sıfıra indiği doğrulanır.

### 8.13 `reviewManifest(...)` — insan inceleme kaydı

> **ÖNERİ — HENÜZ YOK.**

İncelenen commit, dosyalar, inceleyen kişiler, test sonuçları ve izin verilen test türünü
tek kayıtta toplar. “İnsan baktı” cümlesi yerine hangi sürüme kimin baktığını gösterir.

Bu da beyan sistemidir; kişinin kodu gerçekten anladığını otomatik kanıtlamaz.

### 8.14 `physicalStopConfirmed(...)` — yazılım ve gözlemi ayırmak

> **ÖNERİ — HENÜZ YOK.**

İki ayrı olayı saklar:

1. yazılım sıfır PWM istedi,
2. insan tekerleklerin durduğunu gözledi.

İkinci olay yalnızca insan tarafından girilebilir. Böylece günlük “kapat komutu gönderildi”
ile “araç fiziksel olarak durdu” ifadelerini karıştırmaz.

---

## 9. Test rehberi

### 9.1 Bugünkü otomatik test

`tests/test_tawnt.py`, `unittest` ile çalışan 34 assertion tabanlı çekirdek testi içerir.
`tests/test_tawnt_demo.py` ayrıca donanım bağımsızlığını ve öğretici akışı denetleyen 5 test içerir;
toplam 39 test çalışır. Testlerin geçmesi gerçek GPIO, kamera veya tekerlek davranışını
doğrulamaz.

### 9.2 Asgari birim testleri

Bugünkü birim testleri en az şunları kapsar:

- sınır içindeki değer kabul edilir,
- sınır dışındaki değer reddedilir,
- tarihsiz `OLCULDU` reddedilir,
- eksik ikiz reddedilir,
- ikizlerden biri güncellenince diğeri eskimiş sayılır,
- bozuk kardeş sırası reddedilir,
- farklı birimler karşılaştırılmaz,
- 1 piksel sapma ve büyük sapma ayrı davranır,
- kilitten sonra bütün açma girişimleri reddedilir,
- yeniden başlatma politikası açıkça test edilir,
- program başlarken hareket izninin kapalı olduğu doğrulanır,
- eksik/gecikmiş heartbeat reddedilir,
- `LIVE` kilidinin yeniden yüklemede kaldığı doğrulanır,
- doğrudan ve hardcoded motor erişimi taranır.

### 9.3 Henüz yapılmayan entegrasyon testleri

- Geçerli JSON ile sahte sürücü hazır fakat silahsız kalır.
- Eksik veya yanlış çözünürlüklü JSON ile başlatma reddedilir.
- Kamera kaybında en geç belirlenen sürede sıfır PWM kaydedilir.
- Yakalanmamış hata son PWM'i korumaz.
- Yanlış `sign_type` şeması durum makinesine ulaşmadan reddedilir.
- Kilitli süreç otomatik servis yeniden başlatmasında kendiliğinden sürüşe geçmez.

### 9.4 Fiziksel doğrulama

Fiziksel test, yazılım testi bittikten ve insanlar kodu inceledikten sonra yapılır:

1. Motorlar bağlı değilken test,
2. tekerlekler yerden kesikken düşük PWM,
3. ulaşılabilir fiziksel anahtar ve ikinci kişi,
4. beklenmeyen durumda CTRL+C,
5. motorlar durmazsa aracı alttan güvenli biçimde kaldırıp üçlü pil yatağı anahtarını O'ya alma,
6. Raspberry Pi için ikili pil yatağının anahtarını kullanma; ani kesmenin SD kartı bozabileceğini bilme,
7. tekerleklerin gerçekten durduğunu insan gözüyle doğrulama.

Her fiziksel adım için Egemen'in izni ve tehlikeli işlemden hemen önce son onay gerekir.

---

## 10. Öğrenciler için kısa kullanım özeti

Bir kritik sayı eklerken:

1. Sayının neden kritik olduğunu yaz.
2. Geçerli aralığını `introduce` ile tanıt.
3. Kaynağını dürüstçe seç: ölçüldü, devralındı veya varsayıldı.
4. Ölçüldüyse kişi, tarih ve yöntem ekle.
5. Bağlı olduğu çözünürlük, kamera veya başka değer varsa ilişki kur.
6. Birimini yaz.
7. Açılış kapısına ekle.
8. Geçerli ve geçersiz örneklerle otomatik test yaz.
9. Raporu oku; onu fiziksel kanıt diye sunma.

Bir güvenlik yöntemi eklerken:

1. Hangi arızayı yakaladığını yaz.
2. Arızadan sonra son PWM'e ne olduğunu açıkla.
3. Yöntemin atlanabileceği yolları ara.
4. Sahte sürücüyle hata enjekte et.
5. Program yeniden başlarsa ne olacağını test et.
6. İnsan ve fiziksel anahtar adımını kaldırma.

---

## 11. Son hüküm

3awnt fikri değerlidir çünkü proje hatalarının ortak kökünü—kaynağı, birimi ve bağı
kaybolmuş kritik değerleri—hedefler. Tek başına bırakılırsa yanlış güven üretebilir.

Bu yüzden önerilen yön şudur:

> 3awnt kuralları ve geçmişi merkezileştirsin; `ayar.py` veriyi yüklesin; `surucu.py`
> fiziksel kapıyı uygulasın; `main.py` ve `durum.py` arızaları yönetsin; `kayit.py`
> ne olduğunu kaydetsin; insanlar da fiziksel sonucu doğrulasın.

Araç bağlantısı tamamlanıp kontrollü fiziksel test yapılana kadar 3awnt,
**test edilmiş deneysel güvenlik kütüphanesi** olarak anılmalıdır.

---

## 12. `introduce → acquire → preacquire` nasıl çalışır?

Bugünkü sıra `introduce → acquire → preacquire → değeri kullan` biçimindedir: kurallarını
tanımla, değerini ve kaynağını kaydet, başlamadan önce doğrula, sonra kullan.

`preacquire` adı biraz yanıltıcıdır: `acquire` işleminden önce değil, araç başlatılmadan
önce çalışır.

### 12.1 `introduce(...)`: değerin kurallarını tanımlar

```python
import tawnt

MAX_PWM = tawnt.introduce(
    "MAX_PWM",
    min=0,
    max=100,
    preferred=57,
    aciklama="Motor PWM güvenlik tavanı",
)
```

Bu çağrı henüz `MAX_PWM = 57` yapmaz. `_defter["MAX_PWM"]` içine sınırları koyar;
`deger=None`, `kaynak=None` ve `atandi=False` olarak başlatır. `preferred=57` otomatik
değer değildir; yalnız önerilen başlangıç bilgisidir.
`introduce(...)`; tekrar kullanılan adı, `min > max` durumunu ve sınır dışı tercih
değerini reddeder.

### 12.2 `acquire(...)`: değeri ve hikâyesini kaydeder

```python
tawnt.acquire(
    MAX_PWM,
    57,
    kaynak=tawnt.OLCULDU,
    kim="Egemen",
    tarih="2026-09-12",
    notu="Motor uçlarında yük altında ölçüldü",
)
```

Bu çağrı aynı kayda değer, kaynak, kişi ve tarih ekler; `atandi=True` yapar. Şunları
kontrol eder:

1. Ad önceden tanıtılmış mı?
2. Kaynak `OLCULDU`, `DEVRALINDI` veya `VARSAYILDI` mı?
3. Değer bildirilen sınırlar içinde mi?
4. Kaynak `OLCULDU` ise tarih var mı?

Örneğin `tawnt.acquire("HIC_TANITILMADI", 80)` reddedilir.

### 12.3 `preacquire(...)` önceki bilgiyi nasıl bulur?

```python
tawnt.preacquire(MAX_PWM)
```

Üç yöntem de aynı çalışan `tawnt` modülündeki `_defter` sözlüğünü kullanır.
`preacquire(...)` istenen adların:

- tanıtılmış olduğunu,
- değer aldığını,
- sınırlar içinde kaldığını,
- `_ikizler` içindeki eşinin atandığını,
- `_zincirler` içindeki sıralamaların hâlâ doğru olduğunu

denetler.

```python
KARE = tawnt.introduce("KARE")
PERSP_SRC = tawnt.introduce("PERSP_SRC")

tawnt.IsTwinOf(PERSP_SRC, KARE)
tawnt.acquire(PERSP_SRC, dort_kose)
tawnt.preacquire(PERSP_SRC)  # KARE atanmadığı için başarısız
```

Bugünkü önemli sınır: `preacquire`, yalnız kaynak türü nedeniyle `VARSAYILDI` değerini
reddetmez ve ölçümün gerçekten yapıldığını bilemez.

### 12.4 Aynı dosyada olmak zorunda mı?

Hayır. Aynı Python sürecinde aynı `tawnt` modülünü kullanmaları yeterlidir. Örneğin
`ayar.py`, `MAX_PWM` değerini tanıtıp JSON'dan `acquire(...)` edebilir; `main.py` ise
`ayar.yukle(...)` sonrasında `tawnt.preacquire(ayar.MAX_PWM)` çağırabilir.

Python aynı süreçte normal olarak aynı modül nesnesini paylaşır. Kayıtlar şu durumlarda
paylaşılmaz:

- ayrı Python süreçleri,
- programın yeniden başlaması,
- dosyanın iki farklı modül adıyla yüklenmesi.

`_defter` yalnız bellektedir; program kapanınca kaybolur. `introduce(...)` tarafından
döndürülen `MAX_PWM` adını sonraki çağrılarda kullanmak, adı tekrar yazmaktan doğacak
yazım hatalarını azaltır.

---

## 13. Normal `VAR = DATA` atamasından farkı

Normal `MAX_PWM = 57` atamasında Python yalnız adı 57 değerine bağlar. Sayının neden seçildiğini,
ölçülüp ölçülmediğini, sınırını, birimini veya hangi donanıma ait olduğunu bilmez.

| Özellik | `VAR = DATA` | 3awnt kaydı |
|---|---|---|
| Değeri saklar | Evet | Evet |
| Minimum/maksimum bilir | Hayır | Bildirilirse evet |
| Kaynak ve tarih taşır | Hayır | Beyan olarak evet |
| İkiz/sıralama ilişkisi | Hayır | Evet |
| Başlatma kapısı | Hayır | `preacquire` ile |
| Fiziksel doğruluğu kanıtlar | Hayır | Hayır |
| Doğrudan PWM'i engeller | Hayır | Tek başına hayır |

Normal değişken yasak değildir. Sayaçlar, geçici görüntü sonuçları ve sıradan yerel
değerler normal kalır. 3awnt yalnız yanlışlığı aracı, güvenliği veya test sonucunu
anlamlı biçimde bozabilecek kritik değerlere uygulanır.

---

## 14. Daha açık yöntem adları

> **KÜTÜPHANEDE UYGULANDI.** Eski adlar geriye uyumluluk için tutulmuştur.

| Bugünkü ad | Önerilen ad | Anlamı |
|---|---|---|
| `introduce(...)` | `defineValue(...)` | Değerin kurallarını tanımla |
| `acquire(...)` | `recordValue(...)` | Değeri ve kaynağını kaydet |
| `preacquire(...)` | `validateBeforeStart(...)` | Başlatmadan önce doğrula |
| `evreDegisti(...)` | `enterPhase(...)` | Yeni evreye gir |
| `pwmSerbestMi()` | `isMotionAllowed()` | Şu anda hareket izni var mı? |

`identityPreacquire()` mevcut `evreDegisti(...)` için uygun değildir. Bugünkü yöntem
kimlik veya değer doğrulamaz; evre değişince geçici PWM susturmasını kaldırır, kalıcı
arıza kilidini kaldırmaz.

`enterPhase("SERIT_TAKIP")`, geçişe izin vermeden önce `validatePhase(...)` çağırır;
evrenin zorunlu değerlerini ve watchdog'larını denetler.

---

## 15. LLM'nin tehlikeli PWM yazmasına karşı kapı

> **KISMEN UYGULANDI.** Komut doğrulama ve statik tarama 3awnt API'sinde vardır;
> gerçek `surucu.py` yazma yoluna henüz bağlanmamıştır.

### 15.1 Neden `isExpectedCurrent()` değil?

Elektronikte **current** genellikle amper cinsinden elektrik akımıdır. Burada akım sensörü
ölçümü değil, PWM/motor komutu denetleniyor. Daha açık adlar
`isExpectedMotorCommand(...)` ve özellikle `validateMotorCommand(...)` olur.

Boolean kontrolün sonucu unutulabilir ve kod yine motorlara yazabilir.

Doğrulama gerçek yazmanın içinde zorunlu olmalıdır:

```python
# ENTEGRASYON ÖRNEĞİ — surucu.py içinde henüz uygulanmadı
def applyMotorCommand(sol, sag, evre):
    komut = tawnt.validateMotorCommand(sol, sag, phase=evre)
    _writePwm(komut.left, komut.right)
```

`_writePwm(...)` özel kalır. Başka modül gerçek GPIO/PWM yazamaz.

### 15.2 Beklenen komut evreye göre değişir

| Evre | İzin verilen davranış |
|---|---|
| Açılış / silahsız | Yalnız `(0, 0)` |
| Yeşil bekleme | Yalnız `(0, 0)` |
| Şerit takip | İki taraf ileri; sınırlı fark ve değişim |
| Yaya/hemzemin duruşu | Yalnız `(0, 0)` |
| Tümsek | İleri; daha düşük tavan |
| Çıkmaz yol | Karşı yön yalnız bu manevrada mümkün |
| Park | Düşük hız |
| Hata | Yalnız `(0, 0)`; hareket kilitli |

`validateMotorCommand(...)` şunları kontrol eder:

- değerler sayı mı, `NaN` veya sonsuz mu,
- ölçülmüş PWM tavanı içinde mi,
- sistem silahlı mı,
- evre harekete ve yönlere izin veriyor mu,
- sol/sağ farkı ve önceki komuta göre değişim makul mü,
- watchdog sağlıklı mı,
- kilit veya susturma var mı.

Geçersiz komutta önce sıfır PWM, sonra kayıt ve uygun kilit uygulanmalıdır. Tehlikeli
değer sessizce clamp edilip sürüşe devam etmemelidir.

```python
# Entegrasyon örneği — ilk komut geçebilir; diğerleri reddedilir.
surucu.applyMotorCommand(45, 55, "SERIT_TAKIP")
surucu.applyMotorCommand(40, 40, "HATA")
surucu.applyMotorCommand(500, 500, "SERIT_TAKIP")
surucu.applyMotorCommand(float("nan"), 30, "SERIT_TAKIP")
```

### 15.3 Hardcoded değeri daha çalışmadan yakalamak

> **KÜTÜPHANEDE UYGULANDI.** `scanDirectMotorWrites(...)` Python AST taramasıyla şunları arar:

- `surucu.py` dışında motor GPIO/PWM yazımı,
- açıklamasız sabit motor sayıları,
- `motor.value` gibi doğrudan erişim,
- test dışından özel `_writePwm(...)` çağrısı,
- doğrulanmış yapılandırmayı atlayan PWM tavanı.

Statik test “bu kod şüpheli” der; çalışma anı kapısı “bu komut uygulanamaz” der. İkisi
birlikte kullanılır.

---

## 16. Bu yapıda hangi dosya ne yapar?

> **ÖNERİ — HENÜZ UYGULANMADI.**

| Dosya | Sorumluluğu |
|---|---|
| `tawnt.py` + `startech/tawnt/` | Kritik değer, kaynak, ilişki ve genel hareket izni |
| `ayar.py` | Değerleri tanıtmak ve JSON'dan kaydetmek |
| `main.py` | Başlatma doğrulamasını çağırmak |
| `durum.py` | Güncel evre ve geçiş izinleri |
| `surucu.py` | Her komutu doğrulamak ve tek gerçek PWM çıkışı olmak |
| `kayit.py` | İstenen, reddedilen ve uygulanan komutları kaydetmek |
| Statik test | Hardcoded değer ve doğrudan motor erişimini bulmak |

```text
ayar.py yükler
      ↓
3awnt sınır ve kaynağı doğrular
      ↓
main.py başlangıç kapısını çalıştırır
      ↓
durum.py evre iznini verir
      ↓
surucu.py HER motor komutunu yeniden doğrular
      ↓
yalnız güvenli komut gerçek PWM'e ulaşır
      ↓
kayit.py istek, ret ve sonucu yazar
```

En önemli kural:

> 3awnt doğru yapılandırılmış olsa bile `surucu.py` atlanabiliyorsa araç korunmuyor.

---

## 17. 3awnt v2 davranış sözleşmesi ve uygulama durumu

> **KÜTÜPHANEDE UYGULANDI; ARAÇTA ENTEGRE DEĞİL.** Bu bölüm hem beklenen davranışı hem
> de test edilen çekirdeği açıklar. `surucu.py` bağlantısı ve kontrollü fiziksel test
> yapılmadan “araç korunuyor” denemez.

Sözleşmenin amacı yöntem adlarını çoğaltmak değil, şu soruya kesin cevap vermektir:

> Belirli bir anda gerçek motor komutunun uygulanabilmesi için nelerin doğru olması gerekir?

### 17.1 Değişmez güvenlik kuralları

V2 uygulaması hangi biçimde yazılırsa yazılsın aşağıdaki kurallar bozulamaz:

1. Programın başlaması motor izni vermez.
2. Motorlar varsayılan olarak kapalıdır.
3. Gerçek PWM'e giden tek yol `surucu.py` içindeki zorunlu kapıdır.
4. Geçersiz komut fiziksel çıkışa ulaşmadan reddedilir.
5. Yakalanmamış hata son PWM'i korumaz.
6. Evre değişimi ciddi arıza kilidini kaldıramaz.
7. Python veya servis yeniden başlatmak ciddi kilidi kendiliğinden kaldıramaz.
8. Yazılımın “sıfır PWM istedim” kaydı, tekerleklerin fiziksel olarak durduğunu kanıtlamaz.
9. `OLCULDU` etiketi ölçüm beyanıdır; ölçümün gerçekten yapıldığını kanıtlamaz.
10. İnsan incelemesi ve Egemen'in canlı donanım izni olmadan `LIVE` hareket yoktur.

Bu kurallardan biri yalnız kullanım alışkanlığına bağlıysa koruma eksiktir. Mümkün olan
kurallar kod ve test tarafından zorlanmalıdır.

---

## 18. Çalışma profilleri

> **KÜTÜPHANEDE UYGULANDI.** Profil, `validateBeforeStart(profile=...)` ile seçilir.

Tek bir doğrulama seviyesi hem Windows klip testi hem gerçek araç için uygun değildir.
V2 üç açık profil kullanır:

| Profil | Kullanım | Motor çıkışı | Varsayım politikası |
|---|---|---|---|
| `OFFLINE` | Video, algoritma ve masaüstü testi | Gerçek çıkış kesinlikle yok | `VARSAYILDI` kabul edilebilir; raporda görünür |
| `BENCH` | Sahte sürücü veya fiziksel olarak kısıtlı test | Varsayılan sahte; gerçek için ayrıca insan kapısı | Kritik varsayımlar uyarı veya ret olabilir |
| `LIVE` | Zeminde gerçek araç hareketi | Yalnız silahlı ve doğrulanmış sistem | Güvenlik-kritik değerler `OLCULDU` olmalı |

Profil kod içinde gizli bir Boolean olmayacaktır:

```python
tawnt.validateBeforeStart(profile=tawnt.LIVE)
```

`LIVE` seçmek tek başına motorları açmaz. Yalnız daha sıkı doğrulama kurallarını seçer.

### 18.1 Güvenlik-kritik değer örnekleri

Gerçek hareketten önce ölçülmesi veya fiziksel olarak doğrulanması beklenenler:

- motor PWM tavanı,
- motor uç gerilimi,
- motor ölü bölgesi,
- sol/sağ motor eşlemesi,
- motor trimleri,
- kamera çözünürlüğü,
- perspektif dörtgeni ve bağlı kamera profili.

Renk eşikleri de gerçek pistte yeniden ölçülmelidir; fakat yanlış renk değeri ile doğrudan
motor aşırı gerilimi aynı hata sınıfına konmak zorunda değildir. Kritik alan listesi şema
içinde açıkça belirtilir.

---

## 19. Kritik değerin yaşam döngüsü

> **KÜTÜPHANEDE UYGULANDI.** Durum `valueState(ad)` ile sorgulanabilir.

Bir v2 değeri aşağıdaki durumlardan birindedir:

| Durum | Anlamı |
|---|---|
| `UNDEFINED` | Ad ve kurallar yok |
| `DEFINED` | Kurallar var, değer yok |
| `RECORDED` | Değer ve kaynak kaydedildi |
| `VALIDATED` | Seçilen profil için kontrolleri geçti |
| `STALE` | Bağlı bir değer/donanım değişti veya tazelik süresi geçti |
| `SEALED` | Başlangıç tamamlandı; koşu sırasında sessizce değiştirilemez |

Örnek geçiş:

```text
defineValue → DEFINED
recordValue → RECORDED
validateBeforeStart → VALIDATED
seal → SEALED
kamera çözünürlüğü değişti → STALE
```

Kurallar:

- `UNDEFINED` veya `DEFINED` değer zorunlu kapıdan geçemez.
- `STALE` değer `LIVE` profilinde kullanılamaz.
- `SEALED` değer normal atamayla değiştirilemez.
- Değişiklik gerekiyorsa açık yeniden-kalibrasyon oturumu başlatılır.
- Bir bağımlılık değiştiğinde ona bağlı değerler otomatik `STALE` olur.

Örnek: kamera çözünürlüğü değişirse perspektif dörtgeni ve ona bağlı ROI değerleri
eskimiş sayılır.

---

## 20. Sistem ve hareket durumları

> **KÜTÜPHANEDE UYGULANDI.** Bunlar yarışma görev evrelerinden ayrıdır.

| Durum | Anlamı | Hareket |
|---|---|---|
| `BOOT` | Program açılıyor | Yasak |
| `VALIDATING` | Ayarlar ve bağımlılıklar kontrol ediliyor | Yasak |
| `READY_UNARMED` | Kontroller geçti, insan izni bekleniyor | Yasak |
| `ARMED` | Açık insan arming'i alındı | Evre izin verirse mümkün |
| `MUTED` | Geçici görev/evre susturması | Yasak |
| `LATCHED_FAULT` | Ciddi arıza kilitlendi | Yasak |

Normal sıra:

```text
BOOT → VALIDATING → READY_UNARMED → ARMED
```

Program hiçbir koşulda `BOOT → ARMED` atlaması yapmaz.

### 20.1 Arming sözleşmesi

`arm()` için gerekenler:

- profil ve yapılandırma doğrulandı,
- zorunlu değerler `VALIDATED`,
- ciddi kilit yok,
- gerçek sürücü seçildiyse insan incelemesi kaydedildi,
- Egemen canlı donanım izni verdi,
- tehlikeli adımdan hemen önce son onay alındı.

Arming program açılışından miras kalmaz. Yeniden başlatmada tekrar insan kapısı gerekir.

---

## 21. Hata seviyeleri

> **KÜTÜPHANEDE UYGULANAN POLİTİKA:** OFFLINE/BENCH motor reddi `MUTED`, `LIVE`
> motor reddi `LATCHED_FAULT` üretir. Ayrıntılı hata sınıfları araç entegrasyonuyla
> daraltılabilir; çalışma sırasında LLM bu seviyeyi seçmez.

| Seviye | Davranış | Örnek |
|---|---|---|
| `WARNING` | Kaydet; güvenli davranış sürüyorsa devam edebilir | Opsiyonel değer eski |
| `STOP` | Komutu reddet, sıfır PWM uygula | Geçici evre uyuşmazlığı |
| `LATCHED_FAULT` | Sıfır PWM, kalıcı hareket yasağı | `NaN`, watchdog kaybı, bypass girişimi |

`LIVE` profilinde aşağıdakiler ciddi kilit üretir:

- sayı olmayan, `NaN` veya sonsuz motor komutu,
- belirlenen mutlak güvenlik sınırının çok üzerindeki PWM,
- hareketin yasak olduğu evrede hareket komutu,
- şerit takipte izinsiz ters yön/pivot,
- kamera veya kontrol watchdog süresi aşımı,
- gerçek motor kapısını atlama girişimi,
- yakalanmamış ana döngü hatası.

Küçük ayar uyuşmazlıklarında sessiz clamp yerine açık ret tercih edilir. Hangi hatanın
`STOP`, hangisinin `LATCHED_FAULT` olduğu test tablosunda sabitlenir; çalışma sırasında
LLM veya çağıran modül karar vermez.

---

## 22. Ciddi kilidin kalıcılığı ve sıfırlanması

> **KÜTÜPHANEDE UYGULANDI.** `LIVE`, önce `configureFaultStore(...)` çağrılmasını ister.

V2 ciddi arızası süreç/servis yeniden başlatmasında kaybolmaz. Kalıcı kayıtta en az:

- neden,
- ayrıntı,
- zaman,
- profil,
- Git commit/yapılandırma damgası (gelecekteki `snapshot(...)` entegrasyonu ile),
- reddedilen son komut

bulunur.

Kalıcı kayıt bozuk veya okunamıyorsa `LIVE` sistemi güvenli tarafta kalır ve silahlanmaz.
SD karta yazılamaması fiziksel motor kapatmayı engellemez; önce çıkış sıfırlanır, sonra
kayıt denenir.

### 22.1 İnsan sıfırlama sözleşmesi

Kilit ancak şu koşullarla temizlenebilir:

1. Motor güç anahtarının kapalı olduğu insan tarafından doğrulandı.
2. Arıza nedeni okundu ve çözüldü.
3. Sıfırlayan kişi ve zaman kaydedildi.
4. Sistem yeniden `VALIDATING` durumundan geçti.
5. Yeni arming ve son onay alındı.

`enterPhase`, servis restartı, yeni config yükleme veya özel bir metin kilidi açamaz.

---

## 23. V2 API sözleşmesi

> **KÜTÜPHANEDE UYGULANDI.** Eski adlar uyumluluk takma adı olarak kalır.

| Yöntem | Başarı sonucu | Başarısızlık |
|---|---|---|
| `defineValue(...)` | Ad/handle | Geçersiz veya tekrar tanım hatası |
| `recordValue(...)` | Kaydedilen değer | Kaynak, tarih, tip veya sınır hatası |
| `dependsOn(...)` | Bağımlılık kaydı | Döngü veya bilinmeyen ad hatası |
| `requireMeasured(...)` | Kural kaydı | Bilinmeyen ad hatası |
| `validateBeforeStart(profile)` | Doğrulama özeti | Tek toplu hata raporu |
| `seal()` | Değerleri değişmez yapar | Eksik doğrulama hatası |
| `valueState(name)` | Tek değerin yaşam durumu | Bilinmeyen ad hatası |
| `systemState()` | Güncel sistem durumu | Yan etki yapmaz |
| `definePhase(...)` | Evre adı ve politikası | Geçersiz/tekrar evre veya gereksinim hatası |
| `enterPhase(phase)` | Yeni evre | İzin verilmeyen geçiş hatası |
| `validatePhase(phase)` | Evre hazır | Eksik gereksinim ve sıfır PWM |
| `arm(human, ...)` | `ARMED` durumu | Doğrulama, evre, insan veya LIVE onayı eksikse ret |
| `disarm(reason)` | Hareket iznini kaldırır | Sıfır geri çağrıları yine denenir |
| `isMotionAllowed()` | Yalnız durum sorgusu | Yan etki yapmaz |
| `validateMotorCommand(...)` | `ValidatedMotorCommand` | Sıfır isteği + profile göre susturma/kilit |
| `defineWatchdog(...)` | Watchdog adı | Boş ad, tekrar veya geçersiz süre hatası |
| `heartbeat(...)` | Süreç içi monoton zaman | Bilinmeyen watchdog hatası |
| `checkWatchdogs(...)` | `True` | Eksik veya gecikmiş heartbeat hatası |
| `configureFaultStore(path)` | Kalıcı kayıt yolu | Bozuk kayıt güvenli kilit kabul edilir |
| `latchFault(...)` | Kilit kaydı | Kapatma yine denenir |
| `resetFault(...)` | `VALIDATING` durumuna dönüş | İnsan/anahtar koşulu eksikse ret |
| `scanDirectMotorWrites(...)` | Şüpheli erişim listesi | Tarama yolu yoksa hata |

Boolean sonuç güvenlik için tek başına kullanılmaz. `validateMotorCommand(...)` ya
doğrulanmış bir komut döndürür ya da komutun gerçek çıkışa ulaşmasını engeller.

---

## 24. Motor komutunun zorunlu doğrulama sırası

> **DOĞRULAMA KÜTÜPHANEDE UYGULANDI; FİZİKSEL YAZMA BAĞLANTISI HENÜZ YOK.**

`surucu.applyMotorCommand(sol, sag, evre)` şu sırayı izler:

1. Gerçek sürücü seçili mi?
2. Sistem `ARMED` mı?
3. Kilit veya susturma var mı?
4. Evre hareket ve yönlere izin veriyor mu?
5. Değerler sayı ve sonlu mu?
6. Mutlak/ölçülmüş sınırlar içinde mi?
7. Sol/sağ farkı evre için uygun mu?
8. Önceki komuta göre değişim slew sınırında mı?
9. Kamera ve kontrol heartbeat'i güncel mi?
10. Doğrulanmış komut özel fiziksel yazma yöntemine gönderilir.

Herhangi bir adım başarısızsa 10. adıma geçilmez. Önce sıfır PWM denenir, sonra hata
kaydedilir. Çağıran kodun Boolean sonucu kontrol etmeyi unutması bu kapıyı atlayamaz.

---

## 25. V2 test sözleşmesi

Bu sözleşme test adı olarak da okunabilmelidir. Asgari test grupları:

### Bugünkü davranışı doğrulayan v1 testleri

- tekrar tanım ve bozuk sınır reddedilir,
- tanıtılmadan değer kaydı reddedilir,
- sınır dışı değer ve tarihsiz ölçüm reddedilir,
- eksik ikiz ve bozuk kardeş sırası reddedilir,
- farklı birim karşılaştırması reddedilir,
- perspektif sapma sınırı uygulanır,
- geçici susturma evre değişince kalkar,
- ciddi süreç-içi kilit evre değişince kalkmaz.

### Uygulanan v2 testleri

- `LIVE`, varsayılan güvenlik-kritik değeri reddeder,
- başlangıç silahsızdır,
- değerler doğrulamadan sonra mühürlenir,
- bağımlılık değişince değer `STALE` olur,
- evreye aykırı komut fiziksel yazmaya ulaşmaz,
- `NaN` ve aşırı PWM ciddi kilit üretir,
- kilit restarttan sonra kalır,
- insan doğrulaması olmadan reset reddedilir,
- doğrudan PWM/GPIO erişimi statik kontrolde bulunur.

Bu maddeler artık atlanmıyor. `tests/test_tawnt.py` 34, `tests/test_tawnt_demo.py` 5 assertion tabanlı
test çalıştırır; toplam 39 testte `skipped` yoktur. Bu sonuç kütüphane ve sahte eğitim
akışı davranışının kanıtıdır, fiziksel araç testinin yerine geçmez.

---

## 26. Sözleşmenin sınırı

Bu v2 sözleşmesi yazılımın ne yapması gerektiğini açıklar. Şunları hâlâ kanıtlayamaz:

- fiziksel anahtarın çalıştığını,
- motor kablolarının doğru eşlendiğini,
- tekerleklerin sıfır PWM sonrası gerçekten durduğunu,
- ölçümün gerçekten yapıldığını,
- yarışma alanında yasak donanım bulunmadığını.

Bu nedenle son zincir değişmez:

```text
yazılım doğrulaması + assertion testleri + insan kod incelemesi
                   + kontrollü fiziksel test + fiziksel anahtar
```

V2 kütüphane kodu ve sahte eğitim programı uygulanmıştır. Gerçek `main.py`/`surucu.py`
entegrasyonu, insan incelemesi ve fiziksel test yine ayrı plan ve ayrı onay ister.

---

## 27. Sık sorulan sorular (FAQ)

### “Bütün çağrıların aynı dosyada mı olması gerekiyor?”

Hayır. Örneğin `ayar.py` değerleri tanımlayıp kaydedebilir, `main.py` başlangıç kontrolünü
çalıştırabilir ve `surucu.py` motor komutunu doğrulatabilir.

Gereken şey aynı dosya değil, aynı çalışan Python sürecinde aynı `tawnt` modülünün
kullanılmasıdır:

```python
# ayar.py
import tawnt
MAX_PWM = tawnt.defineValue("MAX_PWM", min=0, max=100)

# main.py — aynı Python sürecinde
import tawnt
import ayar
tawnt.recordValue(ayar.MAX_PWM, 57)
```

İki ayrı Python programı kendi ayrı belleklerine sahiptir. Bir süreçte yapılan
`recordValue(...)`, başka süreçte kendiliğinden görünmez.

### “Bilgiler nereye kaydediliyor?”

Normal değer kayıtları, ilişkiler, evreler ve heartbeat'ler çalışan Python sürecinin
belleğinde tutulur. Bunlar otomatik olarak JSON, Python veya ayar dosyasına yazılmaz.

Yalnız ciddi fault kaydı, önce `configureFaultStore(path)` çağrılmışsa seçilen JSON dosyasına
yazılır. Bazı olaylar ayrıca `tawnt_guvenlik.log` günlüğüne yazılmaya çalışılır.

### “Program kapanınca değerler kayboluyor mu?”

Evet; normal 3awnt defteri süreç belleğidir ve Python kapanınca kaybolur. Yeni başlangıçta
ayar dosyaları tekrar yüklenmeli, değerler tekrar kaydedilmeli ve doğrulama yeniden yapılmalıdır.

Kalıcı fault-store farklıdır: aktif ciddi kilit JSON'da kaldıysa yeniden başlatmada okunabilir.
Bu yüzden LIVE doğrulaması yapılandırılmış fault-store ister.

### “3awnt ayar dosyamın yerine mi geçiyor?”

Hayır. `ayarlar.json` veya `kalibrasyon.json` değerleri kalıcı olarak saklar; gelecekteki
`ayar.py` bu dosyaları okur ve değerleri 3awnt'a verir.

3awnt'ın görevi yüklenen değerin sınırını, kaynağını ve ilişkilerini denetlemektir. Dosya
okuma, şema doğrulama ve 3awnt doğrulaması birbirini tamamlayan ayrı adımlardır.

### “`MAX_PWM = 57` ile `recordValue("MAX_PWM", 57)` aynı şey mi?”

Hayır. Normal atama yalnız Python adını sayıya bağlar; sayının sınırını, kaynağını, tarihini
ve bağımlılıklarını bilmez.

`recordValue(...)` önceden tanımlanmış kurallara göre kontrol yapar ve değerin hikâyesini
aynı kayıtta tutar. Yine de sayının fiziksel olarak doğru olduğunu kanıtlayamaz.

### “Neden önce `defineValue`, sonra `recordValue` var?”

Çünkü bir sayıyı kabul etmeden **önce** hangi kurala uyması gerektiğini bilmek isteriz.
Önce `57`yi kabul edip sonra “tavan aslında 50'ymiş” demek güvenli değildir.

İki adım ayrıca “değer henüz ölçülmedi” durumunu görünür yapar: kayıt `DEFINED` olur ama
değer gelene kadar `RECORDED` olmaz.

### “`introduce/acquire/preacquire` mı, yeni adlar mı kullanılmalı?”

Yeni kodda `defineValue/recordValue/validateBeforeStart` kullanılmalıdır; ne yaptıkları
adlarından daha açık anlaşılır. Eski üç ad, mevcut prototip kod hemen bozulmasın diye tutulur.

Eski `preacquire` profil ve `STALE` kurallarını tam uygulamaz. Özellikle LIVE başlangıcında
`validateBeforeStart(profile=tawnt.LIVE)` kullanılır.

### “`OLCULDU` yazınca 3awnt ölçüm yapıldığını biliyor mu?”

Hayır. `OLCULDU`, “bir insan bu değerin ölçüldüğünü beyan ediyor” demektir; 3awnt multimetreyi,
ölçüm yöntemini veya kişinin kimliğini göremez.

Tarih ve not zorunluluğu kaydı daha incelenebilir yapar. Fiziksel ölçümün kanıtı yine insan
incelemesi, yöntem ve gerekiyorsa fotoğraf/video veya test kaydıdır.

### “`critical=True` ne yapıyor?”

Değeri güvenlik-kritik olarak işaretler ve LIVE profilinde `OLCULDU` olmasını zorunlu kılar.
OFFLINE profilinde algoritmayı denemek için varsayım kullanılabilir.

Bu bayrak sayının doğru olduğunu kanıtlamaz. Yalnız yanlışlıkla varsayımla LIVE doğrulamasına
geçilmesini engeller.

### “`STALE` ne demek?”

Değer kaydedilmiş olabilir ama dayandığı başka bilgi değiştiği için artık güvenilemez demektir.
Örneğin çözünürlük değişince eski perspektif noktaları sayısal olarak hâlâ mevcut olsa da eskidir.

`STALE` değer yeniden hesaplanmalı veya ölçülmeli, `recordValue(...)` ile kaydedilmeli ve
başlangıç doğrulamasından tekrar geçmelidir.

### “`seal()` yaptıktan sonra değeri değiştirebilir miyim?”

Normal `recordValue(...)` ile değiştiremezsiniz; amaç koşu ortasında sessiz kalibrasyon
değişimini engellemektir. `arm()` değerleri otomatik mühürleyebilir.

Değişiklik gerçekten gerekiyorsa hareket izni kaldırılmalı ve açık bir yeni doğrulama oturumu
başlatılmalıdır. Gerçek araç entegrasyonunda bunun tam prosedürü ayrıca tasarlanacaktır.

### “`validateBeforeStart()` geçti; motorlar artık çalışır mı?”

Hayır. Bu yöntem yalnız verileri doğrular ve sistemi `READY_UNARMED` yapar.

Hareket için uygun evre, sağlıklı watchdog, açık `arm(...)` ve her tek komutta
`validateMotorCommand(...)` gerekir. Üstelik gerçek sürücünün bu kapıyı zorunlu kullanması gerekir.

### “`arm()` fiziksel anahtarı açıyor mu?”

Hayır. `arm()` yalnız yazılım durumunu `ARMED` yapar ve verilen insan/onay bilgilerini beyan
olarak kabul eder.

Fiziksel motor anahtarı ayrı bir donanımdır. Yazılım arming'i fiziksel anahtarın veya insan
güvenlik kontrolünün yerine geçmez.

### “`isMotionAllowed()` True ise araç kesin hareket eder mi?”

Hayır. `True`, yalnız 3awnt'ın bildiği yazılım koşullarının izin verdiğini söyler; PWM yazmaz.

Aynı şekilde `False`, gerçek sürücü 3awnt'ı atlıyorsa fiziksel motoru tek başına durduramaz.
Bu nedenle gerçek PWM'e giden tek yolun `surucu.py` olması kritik tasarım kuralıdır.

### “`validateMotorCommand()` motorlara yazıyor mu?”

Hayır. Başarılı komutu `ValidatedMotorCommand` nesnesi olarak geri döndürür.

Gelecekte `surucu.py`, yalnız bu nesnenin `left` ve `right` alanlarını özel fiziksel yazma
yoluna aktarmalıdır. Bugünkü `fake_main.py` bunu yalnız bellek listesinde gösterir.

### “Neden Boolean yerine `ValidatedMotorCommand` dönüyor?”

`if validate(...):` kontrolü çağıran kişi tarafından unutulabilir veya yanlış kullanılabilir.
Doğrulanmış nesne, gerçek sürücünün ham sayıyla doğrulanmış sonucu ayırmasını kolaylaştırır.

Bu yine mutlak bypass koruması değildir. Başka kod doğrudan GPIO yazabiliyorsa nesneyi tamamen
atlayabilir; statik tarama ve mimari inceleme bu yüzden ayrıca gerekir.

### “Heartbeat geldiyse kamera doğru çalışıyor mu?”

Kesin olarak hayır. Heartbeat yalnız ilgili kodun belirli bir süre içinde o satıra ulaştığını
gösterir.

Siyah görüntü, yanlış renk maskesi veya donmuş ama tekrar gönderilen eski kare ayrı kontroller
ister. Ayrıca bütün Python süreci donarsa süreç-içi watchdog da çalışamayabilir.

### “`flushPWM` ile `latchFault` arasındaki fark ne?”

`flushPWM(...)` normal görev geçişi için geçici susturmadır; uygun farklı evreye geçince
kalkabilir. Örneğin bir tabeladan sonra yeni görev kararını beklerken kullanılabilir.

`latchFault(...)` ciddi arızadır ve evre değişimiyle kalkmaz. İnsan nedeni çözmeden ve
`resetFault(...)` koşullarını sağlamadan yeniden arming yapılamaz.

### “Fault dosyasını silersem kilit açılır mı?”

Dosyayı dışarıdan silmek güvenli veya onaylı reset yöntemi değildir. Çalışan süreç kilidi
bellekte tutabilir; ayrıca arıza nedenini ve inceleme izini yok etmiş olursunuz.

Doğru yazılım yolu `resetFault(human, motor_power_off=True)` çağrısıdır ve ardından yeniden
doğrulama gerekir. Gerçek araçta insan önce fiziksel durumu ayrıca kontrol etmelidir.

### “`resetFault(..., motor_power_off=True)` anahtarı gerçekten kontrol ediyor mu?”

Hayır. `True` değeri bir insan beyanıdır; 3awnt fiziksel anahtarın konumunu okuyamaz.

Bu parametrenin amacı tehlikeli bir resetin düşünmeden tek kelimeyle yapılmasını zorlaştırmak
ve kimin reset istediğini kaydetmektir. Donanım kanıtı olarak sunulmamalıdır.

### “`sifirla()` ile fault-store da silinir mi?”

Hayır. `sifirla()` test/demo için süreç içi sözlükleri ve durumları temizler; disk üzerindeki
JSON fault dosyasını silmez.

Gerçek araç kodunun bu yöntemi çağırması yasak kabul edilmelidir. Testler birbirinden bağımsız
olsun diye `tests/test_tawnt.py` ve `fake_main.py` kullanır.

### “3awnt ağ tehditlerini izliyor mu?”

Hayır. Açılımında “3rd-party Automated Watchdog for Network Threats” bulunmasına rağmen bugünkü
kod ağ paketi, soket, sunucu veya saldırı izlemez.

Bugünkü işlevi değer, durum, heartbeat, motor komutu ve fault politikasıdır. Ağ güvenliği ancak
ayrı özellik planı, resmi yarışma kuralı kontrolü ve testlerle eklenebilir.

### “3awnt fiziksel acil durdurma düğmesi mi?”

Hayır. Yazılım duruş isteği gönderebilir fakat tekerleklerin, sürücünün veya güç hattının
gerçekten durduğunu göremez.

Fiziksel anahtar, insan gözetimi ve kontrollü test sırası değişmez. Yazılım güvenliği bunlara
ek bir katmandır, onların yerine geçmez.

### “En kolay nereden başlamalıyım?”

Önce `fake_main.py` dosyasını çalıştırın ve ekrandaki üç dersi okuyun. Sonra bu belgedeki
§0 küçük sürümde yalnız kullandığınız yönteme bakın.

Gerçek projeye bağlamak için doğrudan kopyalama yapmayın. `ayar.py`, `main.py` ve `surucu.py`
entegrasyonu ayrı plan, insan kod incelemesi ve önce sahte sürücü testi gerektirir.
