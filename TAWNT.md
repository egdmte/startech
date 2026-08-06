# 3awnt (`tawnt.py`) — öğrenci ve geliştirici kılavuzu

> **Durum:** Deneysel prototip. Henüz aracın üretim çalışma zincirine bağlı değildir.
>
> **En önemli cümle:** 3awnt, kritik sayıların nereden geldiğini ve birbirleriyle
> çelişip çelişmediğini denetlemeye çalışan bir yazılım katmanıdır. Fiziksel acil
> durdurma sistemi değildir ve ölçüm yapıldığını kanıtlayamaz.

Bu belge dört şeyi birbirinden ayırır:

1. 3awnt'ın bugün gerçekten yaptığı işler,
2. bugün yapmadığı veya eksik yaptığı işler,
3. yeni araçta önerilen hibrit kullanım biçimi,
4. gelecekte eklenebilecek yöntemler.

Bir başlığın altında **ÖNERİ — HENÜZ YOK** yazıyorsa o özellik `tawnt.py` içinde varmış
gibi davranılamaz.

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

Sistemin adı `3awnt` olarak anılıyor; Python dosyası `tawnt.py` olmak zorunda, çünkü
Python modül adı rakamla başlayamaz.

Adın kökeni `защит` sözcüğünün bir yapay zekâ tokenleştirme hatasından gelmesidir.
İsim bir güvenlik sertifikası değildir; takımın projeye verdiği addır.

---

## 3. Bugün gerçekten bulunan yöntemler

Bu bölüm, mevcut `tawnt.py` dosyasının davranışını açıklar.

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

**Önemli mevcut sınır:** `preacquire`, `VARSAYILDI` kaynağını yalnızca kaynak türü
nedeniyle reddetmez. Yani “kritik değerler mutlaka ölçülmüş olmalı” kuralı bugün otomatik
uygulanmıyor. Bunu yapan gelecek yöntemi §8.2'de önerilmiştir.

### 3.4 `IsTwinOf(...)`: birlikte anlam taşıyan değerler

```python
tawnt.IsTwinOf("PERSP_SRC", "KARE")
```

Perspektif köşeleri, ölçüldükleri görüntü çözünürlüğü olmadan anlamlı değildir. İkiz
ilişkisi, iki değerden biri hiç atanmamışsa bunu açılış kontrolünde gösterir.

**Önemli mevcut sınır:** İki ikiz ilk kez atandıktan sonra yalnızca birinin yeniden
atanması bugün otomatik olarak “öteki eskidi” işareti üretmez. Revizyon takibi §8.3'te
önerilmiştir.

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

Kilit tek yönlüdür; aynı süreç içinde yeniden açılamaz. Ancak program yeniden başlatılırsa
bellekteki kilit sıfırlanır.

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
| Kilit | Beklenmeyen arıza sonrası yeniden çalışmayı engellemek | Hayır; süreç yeniden başlar |
| Susturma | Normal evre geçişinde geçici motor komutunu engellemek | Evet; evre değişince |

Susturma kalıcı kilidi açamaz.

### 3.11 `pwmSerbestMi()`: yazılım izni sorgusu

Motor katmanı bu sonucu kontrol edebilir:

```python
if not tawnt.pwmSerbestMi():
    surucu.hepsini_kapat()
    return
```

**Kritik mevcut davranış:** Yeni bir Python süreci başladığında `pwmSerbestMi()` bugün
`True` döner. Yani 3awnt tek başına “varsayılan kapalı” arming sistemi değildir. Gerçek
motor katmanı ayrıca kendi fail-closed durumunu uygulamalıdır.

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

6 Ağustos 2026 itibarıyla yapılan depo incelemesine göre:

- `tawnt.py` vardır fakat Git tarafından henüz izlenmemektedir.
- `TAWNT.md`, `tawnttest.py` ve `tawnt_guvenlik.log` da izlenmeyen dosyalardır.
- Üretim aracı çalışma zinciri 3awnt'ı çağırmamaktadır.
- Yalnızca `tawnttest.py` 3awnt'ı içe aktarmaktadır.
- Test dosyası çıktı üretir fakat otomatik `assert` kontrolleri içermez.
- SIGINT, SIGTERM, yakalanmamış hata, kamera watchdog'u ve GPIO sürücüsü bağlı değildir.
- Herhangi bir üretim motor sürücüsü `pwmSerbestMi()` sonucunu zorunlu kapı olarak kullanmaz.

Bu nedenle doğru ifade şudur:

> 3awnt için bir prototip vardır; araç güvenlik zincirine entegrasyon henüz yapılmamıştır.

“3awnt aracı koruyor” ifadesi bugün doğru değildir.

---

## 5. Bilinen sınırlar ve yanlış güven tehlikesi

1. `OLCULDU` etiketi ölçümü doğrulamaz; yalnızca beyanı saklar.
2. `preacquire`, varsayılan değerleri kaynak türü nedeniyle reddetmez.
3. İkizlerden biri tekrar değiştiğinde ötekinin eskidiğini takip etmez.
4. Kilit yalnızca çalışan Python sürecinin belleğindedir.
5. Servis programı otomatik yeniden başlatırsa kilit kaybolabilir.
6. Başlangıçta PWM izni açıktır; gerçek arming kapısı değildir.
7. Kapatma geri çağrısı fiziksel duruşu ispatlamaz.
8. 3awnt, motor kablolarının doğru bağlandığını bilemez.
9. 3awnt, yasak bir haberleşme modülünün araçtan fiziksel olarak çıkarıldığını bilemez.
10. 3awnt, kameranın gördüğü maskenin gerçekte doğru renge ait olduğunu bilemez.
11. Günlük dosyasına yazılması olayın gerçekleştiğini değil, yazılımın yazdığını gösterir.
12. Bütün kurallar tek modülde büyürse modül anlaşılması zor bir “tanrı nesne”ye dönüşebilir.
13. Başka bir modül doğrudan GPIO/PWM yazarsa bütün 3awnt kontrolleri atlanabilir.

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
| `tawnt.py` | Kritik değer kuralları, kaynaklar, ilişkiler ve yazılım kilidi | GPIO sürmek veya fiziksel duruş iddia etmek |
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

## 8. Gelecekte eklenebilecek 3awnt yöntemleri

Bu bölümdeki her madde **ÖNERİ — HENÜZ YOK** durumundadır. Her biri kod değişikliği için
ayrı plan, insan incelemesi, test ve Git commit gerektirir.

### 8.1 `seal()` — kayıt defterini dondurmak

Başlatma doğrulandıktan sonra kritik değerlerin sessizce değiştirilmesini engeller.
Kalibrasyon değişecekse yeni bir oturum veya açık bir yeniden-kalibrasyon işlemi gerekir.

### 8.2 `requireMeasured(...)` — ölçülmüş kaynak zorunluluğu

Örnek fikir:

```python
tawnt.requireMeasured("MAX_PWM", "MOTOR_GERILIMI", "PERSP_SRC")
```

Bu kapı `VARSAYILDI` ve gerekirse `DEVRALINDI` değerleri fiziksel test öncesinde reddeder.
Bilgisayar üzerindeki klip testinde farklı, gerçek motor testinde daha sıkı profil kullanılabilir.

### 8.3 `dependsOn(...)` ve revizyon sayacı

Bir değer değiştiğinde ona bağlı değerleri “eskimiş” yapar.

```python
tawnt.dependsOn("PERSP_SRC", "KARE", "KAMERA_YUKSEKLIGI")
```

Çözünürlük veya kamera yüksekliği değiştiğinde perspektif kalibrasyonu yeniden istenir.

### 8.4 `derive(...)` — türetilmiş değerin formülü

Bir değerin elle kopyalanması yerine hangi formülle üretildiğini kaydeder. Örneğin PWM
tavanı; pil gerilimi, motor nominal gerilimi ve güvenlik payından türetilebilir. Formül
ölçümün yerini almaz fakat hesabın tekrar üretilebilmesini sağlar.

### 8.5 `bindCalibrationProfile(...)` — kalibrasyonu donanıma bağlamak

Kalibrasyon dosyasına şunları bağlar:

- kamera kimliği,
- çözünürlük ve FPS,
- kamera yüksekliği/açısı,
- araç veya şasi kimliği,
- oluşturulma tarihi,
- kalibrasyonu yapan kişi.

Yanlış kamera profili yüklenirse araç silahlanmaz.

### 8.6 `arm()` / `disarm()` — fail-closed yazılım kapısı

Başlangıçta izin kapalı olur. Bütün self-testler geçmeden ve açık insan arming olayı
gelmeden PWM açılamaz. `disarm()` her zaman mümkündür; arıza kilidinden sonra `arm()`
reddedilir.

Bu yöntem fiziksel anahtarın yerini almaz.

### 8.7 `heartbeat(...)` / `watchdog(...)`

Kamera, kontrol döngüsü ve motor komutu güncellemesinin beklenen sürede gelip gelmediğini
izler. Süre aşımında son PWM'i korumak yerine sıfıra çeker ve kilitler.

Watchdog ayrı bir iş parçacığı veya süreç kullanacaksa, onun da donması ve saat kaynağının
nasıl seçileceği test edilmelidir.

### 8.8 `persistentFaultLatch(...)`

Ciddi arıza kilidini disk üzerinde saklar. Servis veya güç yeniden geldiğinde araç otomatik
olarak silahlanmaz. İnsan arızayı okur, nedeni çözer ve kontrollü sıfırlama yapar.

SD kart yazma hataları ve ani güç kesintisi düşünülmelidir; kayıt tek güvenlik noktası olamaz.

### 8.9 `snapshot(...)` — çalıştırılan sürümü tanımlamak

Şunların özet kimliğini kaydeder:

- Git commit,
- çalışma ağacı temiz/kirli durumu,
- yapılandırma dosyası hash'i,
- kalibrasyon dosyası hash'i,
- kullanılan yarışma kılavuzu sürümü.

“Hangi kodla bu turu yaptık?” sorusuna cevap verir.

### 8.10 `validateMessage(...)` — modüller arası sözleşme

Görüntü işleme ile durum makinesi arasında taşınan olay sözlüğünü doğrular. Örneğin eski
kodda `main.py`, `sign_type` beklerken olay üreticisi bu alanı üretmiyordu. Şema kontrolü
bu tür sessiz kopuklukları yakalar.

### 8.11 `competitionMode(...)`

Yarışma kipinde ağ sunucusu, uzaktan komut, debug arayüzü veya izin verilmeyen ayarların
yazılım tarafında açık olmadığını kontrol eder.

Sınırı açıktır: Yazılım fiziksel olarak bağlı bir modülü kesin biçimde kanıtlayamaz. Son
kontrol insana ve teknik kontrole aittir.

### 8.12 `faultInjection(...)` — hata enjekte etme

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

İncelenen commit, dosyalar, inceleyen kişiler, test sonuçları ve izin verilen test türünü
tek kayıtta toplar. “İnsan baktı” cümlesi yerine hangi sürüme kimin baktığını gösterir.

Bu da beyan sistemidir; kişinin kodu gerçekten anladığını otomatik kanıtlamaz.

### 8.14 `physicalStopConfirmed(...)` — yazılım ve gözlemi ayırmak

İki ayrı olayı saklar:

1. yazılım sıfır PWM istedi,
2. insan tekerleklerin durduğunu gözledi.

İkinci olay yalnızca insan tarafından girilebilir. Böylece günlük “kapat komutu gönderildi”
ile “araç fiziksel olarak durdu” ifadelerini karıştırmaz.

---

## 9. Test rehberi

### 9.1 Mevcut testin eksiği

`tawnttest.py` bugün örnek çıktı ve günlük oluşturuyor. Otomatik iddia (`assert`) olmadığı
için başarısız davranış test sürecini her zaman başarısız yapmaz.

### 9.2 Asgari birim testleri

Gelecek test planı en az şunları kapsamalıdır:

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
- kapatma geri çağrısı hata verse bile diğer geri çağrılar denenir,
- gerçek sürücü kullanılmadan motor kapısının fail-closed olduğu doğrulanır.

### 9.3 Entegrasyon testleri

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

Bu yapı tamamlanıp test edilene kadar 3awnt, **deneysel doğrulama prototipi** olarak
anılmalıdır.

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

> **ÖNERİ — HENÜZ UYGULANMADI.** Bu adlar mevcut `tawnt.py` içinde yoktur.

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

Evrenin gereksinimleri ayrıca doğrulanacaksa `enterPhase("SERIT_TAKIP")` sonrasında
ayrı bir `validatePhase("SERIT_TAKIP")` yöntemi önerilebilir.

---

## 15. LLM'nin tehlikeli PWM yazmasına karşı kapı

> **ÖNERİ — HENÜZ UYGULANMADI.** Aşağıdaki motor kapısı mevcut çalışma kodunda yoktur.

### 15.1 Neden `isExpectedCurrent()` değil?

Elektronikte **current** genellikle amper cinsinden elektrik akımıdır. Burada akım sensörü
ölçümü değil, PWM/motor komutu denetleniyor. Daha açık adlar
`isExpectedMotorCommand(...)` ve özellikle `validateMotorCommand(...)` olur.

Boolean kontrolün sonucu unutulabilir ve kod yine motorlara yazabilir.

Doğrulama gerçek yazmanın içinde zorunlu olmalıdır:

```python
# ÖNERİ — HENÜZ UYGULANMADI
def applyMotorCommand(sol, sag, evre):
    validateMotorCommand(sol, sag, evre)
    _writePwm(sol, sag)
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

`validateMotorCommand(...)` şunları kontrol etmelidir:

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
# ÖNERİ — ilk komut geçebilir; diğerleri reddedilir.
surucu.applyMotorCommand(45, 55, "SERIT_TAKIP")
surucu.applyMotorCommand(40, 40, "HATA")
surucu.applyMotorCommand(500, 500, "SERIT_TAKIP")
surucu.applyMotorCommand(float("nan"), 30, "SERIT_TAKIP")
```

### 15.3 Hardcoded değeri daha çalışmadan yakalamak

> **ÖNERİ — HENÜZ UYGULANMADI.** Statik bir test şunları arayabilir:

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
| `tawnt.py` | Kritik değer, kaynak, ilişki ve genel hareket izni |
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
