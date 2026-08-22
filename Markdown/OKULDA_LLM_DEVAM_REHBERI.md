# STARTECH okulda devam rehberi — LLM ajanları için

> **Belge türü:** Uygulama ve güvenlik devir notu
>
> **Hedef okur:** Bu depoda okulda çalışacak yapay zekâ kodlama ajanları ve kodu inceleyecek ekip üyeleri
>
> **Durum tarihi:** 2026-08-22
>
> **Temel simülasyon sözleşmesi commit'i:** `2384a0a`
>
> **Kamera zinciri commit'i:** `70f6840`
>
> **Bu tarihteki doğrulama:** 126 test geçti; `arac` TAWNT doğrudan motor yazımı taraması 0 bulgu;
> Webots başsız koşusu `STARTECH_WEBOTS_OK` üretti
>
> **Bilinen depo kontrolü:** `kontrol.py`, ekip tarafından ayrıca düzenlenmiş
> `HATA_DEFTERI.md:256` içindeki henüz bulunmayan `motor_balance.py` atfı nedeniyle düşüyor
>
> **Kapsam:** Uygulanmış kamera tanılamasını ve donanımsız simülasyon sözleşmelerini okulda
> ölçülü biçimde gerçek araca bağlama hazırlığı
>
> **Bu belge fiziksel araç kullanma izni değildir.**

## 1. Bu belgenin amacı

Bu rehber, bir sonraki ajanın “dosya boş görünüyor, hemen GPIO kodu yazayım” diye
başlamasını önlemek için yazıldı. Mevcut dosyalar boş şablon değildir. Her biri, gerçek
donanım bağlanmadan önce veri sınırlarını ve güvenli başarısız olma davranışını tanımlayan
çalışan bir simülasyon sözleşmesidir.

Okulda amaç bu sözleşmeleri atmak değil, kanıtlanmış küçük adımlarla gerçek bağdaştırıcılar
eklemektir. Fiziksel araçla ilgili her iddia gözlem ve ölçüm gerektirir. Birim testinin
geçmesi, tekerleğin gerçekten durduğunu veya kameranın gerçekten doğru gördüğünü kanıtlamaz.

## 2. Ajanın ilk okuma sırası

Her yeni görevde aşağıdaki sırayı koru:

1. `AGENTS_READ_ME.txt` dosyasını baştan sona oku. Bu dosya en üst depo sözleşmesidir.
2. Kullanıcının o görevdeki en son açık talebini belirle.
3. `git status --short` ile ekibin var olan değişikliklerini gör. Onları kendi değişikliğin
   sanma, silme veya geri alma.
4. İlgili üretim dosyasını ve testini birlikte oku.
5. `Markdown/PLAN_New.md` ile doğrulanmış kod arasında fark varsa bunu raporla. Plan dosyasını
   açık talep olmadan düzenleme.
6. Değişiklikten önce `AGENTS_READ_ME.txt` içindeki zorunlu planı hazırla ve onay al.
7. Yalnızca onaylanan dosyalara ve davranışlara dokun.
8. Önce simülasyon ve hata yollarını test et.
9. Fiziksel deneye geçmeden önce ayrıca canlı donanım yetkisi ve son onay al.

## 3. Yetki ve gerçeklik etiketleri

Ajan bütün açıklamalarında aşağıdaki ayrımları korumalıdır:

| Etiket | Anlamı | Örnek |
|---|---|---|
| `IMPLEMENTED` | Kod depoda var ve yazılım testi var | `SequenceCamera` kare sırasını reddedebiliyor |
| `SIMULATED` | Bellek içi veya kayıtlı veri ile çalışıyor | `FakeMotorDriver` komutu yalnızca geçmişe ekliyor |
| `PROPOSED` | Tasarım düşünülmüş ama kodlanmamış | Raspberry Pi üzerinde yarış sürüş döngüsü |
| `PHYSICALLY_UNVERIFIED` | Kod olabilir ama araçta ölçülmemiş | Pi kamera açılması, PWM yön eşlemesi veya gerçek durma süresi |
| `PHYSICALLY_VERIFIED` | İnsan gözetiminde ölçülmüş ve kayıt altına alınmış | Belirli tarihli, belirli düzenekte ölçülen durma testi |

`READY`, `PASSED`, `SAFE` ve benzeri kelimeler bağlamsız kullanılmamalıdır. Örneğin
“DORA simulation self-check passed” doğrudur; “car is safe” aynı testten çıkarılamaz.

## 4. Güncel modül adları

Bu isimler kaynak dosyaların modül açıklamalarında bulunan güncel isimlerdir:

| Dosya | Türkçe ad | İngilizce ad | Kısa sorumluluk |
|---|---|---|---|
| `arac/main.py` | STARTECH-ARDA | ADAM | Uygulama girişi ve üst düzey orkestrasyon |
| `arac/goz.py` | STARTECH-KASIM | CAMILA | Kamera edinimi ve kare paketleme |
| `arac/goruntu.py` | STARTECH-KEREM | CORA | Kareden ihtiyatlı gözlem üretimi |
| `arac/durum.py` | STARTECH-DORA | SARA | Saf ve belirlenmiş durum geçişleri |
| `arac/kayit.py` | STARTECH-KADER | BLAIR | Karakutu yazılım kayıtları |
| `arac/surucu.py` | STARTECH-OSMAN | MATT | Motor çıkışına giden tek planlı sınır |
| `tawnt.py` | TAWNT / 3awnt | TAWNT / 3awnt | Bildirim, doğrulama ve hareket kapısı |

Eski belgelerde farklı açılımlar bulunabilir. Eski planı güncel gerçeklik sanarak kaynak
dosyalarını eski isimlere döndürme. Çelişkiyi kullanıcıya göster ve hangi belgenin
güncelleneceği için ayrı yetki al.

TAWNT adı ve mizahı özellikle korunacaktır. `arac/tawnt.py` üzerinde bu çalışma kapsamında
değişiklik yapılmadı ve gelecek ajan da açık onay olmadan değiştirmemelidir.

## 5. Şu anki mimari

Beklenen tek yönlü veri akışı şöyledir:

```text
KASIM CameraSource
        |
        v
    FramePacket
        |
        v
KEREM VisionAnalyzer
        |
        v
    Observation -------> KADER kayıtları
        |
        v
ARDA karar/orkestrasyon
        |
        v
DORA StateEvent -> StateSnapshot -------> KADER kayıtları
        |
        v
OSMAN MotorRequest -> TAWNT doğrulaması -> MotorDriver
        |
        +--------------------------------> KADER kayıtları
```

Bu akışta hiçbir modül OSMAN'ı atlayarak fiziksel PWM yazamaz. ARDA ikinci bir gizli motor
yolu oluşturmamalıdır. DORA motor sürmez; yalnızca durum üretir. KEREM karar vermez;
yalnızca gözlem üretir. KADER kayıt tutar; fiziksel sonuç kanıtlamaz.

## 6. Mevcut doğrulanmış sözleşmeler

### 6.1 KASIM / CAMILA — `arac/goz.py`

Mevcut durum:

- Bellek içi kamera sözleşmesi: `IMPLEMENTED` ve `SIMULATED`.
- USB/OpenCV ve Raspberry Pi/Picamera2 bağdaştırıcıları: `IMPLEMENTED`.
- Dizüstü bilgisayardaki `usb:0`: 22 Ağustos 2026 tarihinde üç kare, `640x480`
  çözünürlük ile yalnızca edinim düzeyinde `PHYSICALLY_VERIFIED`.
- Araçtaki Raspberry Pi kamerası: `PHYSICALLY_UNVERIFIED`.

Temel nesneler:

- `FramePacket(frame_id, captured_at, payload, source)`
- `CameraStatus`
- `CameraSource` protokolü
- `SequenceCamera`
- `UnavailableCamera`
- `OpenCvUsbCamera`
- `PiCamera2Source`
- `PreferredCamera`
- `CameraProbeResult`
- `build_preferred_camera()`
- `probe_camera()`

Korunan kurallar:

- `frame_id` negatif olamaz ve boolean olamaz.
- `captured_at` sonlu, negatif olmayan bir sayıdır.
- `payload` `None` olamaz.
- Kaynak adı boş olamaz.
- Simülasyon kare kimlikleri kesin olarak artmalıdır.
- Kamera açılmadan kare okunamaz.
- Sonlu kaynak bittiğinde eski kare tekrar verilmez; `CameraExhausted` oluşur.
- Fiziksel sağlayıcı yoksa `UnavailableCamera` açıkça hata verir.
- `close()` tekrar çağrılabilir.
- Otomatik seçim önce istenen USB kamera indeksini, yalnızca açılamazsa Picamera2'yi dener.
- İki kaynak da açılamazsa iki sebebi içeren `CameraUnavailable` oluşur.
- Bir kaynak açıldıktan sonraki okuma hatasında diğer kameraya sessizce geçilmez;
  `CameraReadFailure` oluşur. Böylece karelerin kökeni bir çalışmanın ortasında değişmez.
- Tanılama sonlu sayıda kare okur; kaynak, kare sayısı, çözünürlük ve geçen süreyi raporlar.
- Aynı tanılama içindeki kaynak ve çözünürlük değişirse hata verir.
- Tanılama kare görüntüsünü diske kaydetmez.

USB bağımlılığı `requirements-camera-usb.txt` ile kurulur. Picamera2, Raspberry Pi OS'nin
sağladığı sistem paketi olarak beklenir; normal bilgisayardaki pip gereksinimlerine zorla
eklenmemelidir.

### 6.2 KEREM / CORA — `arac/goruntu.py`

Mevcut durum: `SIMULATED`, OpenCV/gerçek algı `PROPOSED`.

Temel nesneler:

- `Observation`
- `VisionAnalyzer` protokolü
- `SimulatedVisionAnalyzer`
- `UnavailableVisionAnalyzer`

Korunan kurallar:

- Geçerli gözlemde normalize `lane_error` aralığı `[-1, 1]` olmalıdır.
- Geçerli gözlem, açık `obstacle=True/False` ve pozitif güven değeri taşımalıdır.
- Güven değeri `[0, 1]` aralığındadır.
- Geçersiz gözlem yolun açık olduğunu iddia edemez.
- Geçersiz gözlemde `lane_error`, işaret ve engel alanları `None` kalır.
- Geçersiz gözlem güveni sıfırdır ve açıklayıcı sebebi vardır.
- Aynı veya daha eski kare ikinci defa çözümlenmez.
- Bilinmeyen simülasyon alanları sessizce kabul edilmez.

Gerçek görüntü kodu “algılama olmadı” durumunu `obstacle=False` olarak çevirmemelidir.
Görüntü yoksa veya çözümleme güvenilmezse sonuç bilinmeyendir ve üst katman durmalıdır.

### 6.3 DORA / SARA — `arac/durum.py`

Mevcut durum: `IMPLEMENTED` ve `SIMULATED`; fiziksel davranış bağlantısı
`PHYSICALLY_UNVERIFIED`.

Durumlar:

```text
BOOT
SELF_TEST
READY
WAITING_FOR_GREEN
DRIVING
STOPPING
WAITING
FINISHED
FAULT
```

Temel nesneler:

- `StateEvent`
- `StateSnapshot`
- saf `transition(snapshot, event)` fonksiyonu
- küçük durum tutucu `StateMachine`

Korunan kurallar:

- İzin verilmeyen durum geçişi `IllegalTransition` üretir.
- Reddedilen olay, önceki durumu değiştirmez.
- Eski zaman damgası veya tekrarlanan/eski kare reddedilir.
- `STOP_REQUESTED` ve `FAULT_DETECTED` boş sebep kabul etmez.
- `RESET_REQUESTED` açık insan onayı olmadan kurulamaz.
- Her normal durumdan `FAULT` durumuna geçilebilir.
- DORA'nın bir duruma geçmesi motorun fiziksel olarak o işi yaptığını kanıtlamaz.

Önemli örnek: `STOPPING` yazılımın durma istediğini ifade eder. `WAITING` durumuna geçiş,
ileride gerçek sürücü geri bildirimi veya insan tarafından doğrulanmış durma koşulu ile
beslenmelidir. Sadece zaman geçti diye fiziksel durma iddia edilmemelidir.

### 6.4 KADER / BLAIR — `arac/kayit.py`

Mevcut durum: bellek ve JSONL için `IMPLEMENTED`; araçtaki kalıcı kayıt yolu
`PROPOSED`.

Temel nesneler:

- `RecordKind`
- `BlackBoxRecord`
- `MemoryBlackBox`
- `JsonlBlackBox`

Korunan kurallar:

- Kayıt verisi gerçek JSON türlerinden oluşmalıdır.
- `NaN`, sonsuz sayı, metin olmayan anahtar ve serileştirilemeyen nesne reddedilir.
- Kayıt sıra numarası kesintisiz artar.
- Kare kimliği geriye gidemez.
- JSONL yeniden açıldığında eski satırlar tamamen doğrulanır.
- Boş veya bozuk satır sessizce atlanmaz.
- Diske yazma tamamlanmadan kayıt bellek listesine kabul edilmez.
- Kayıt dosyası açıkça `append()` çağrılana kadar oluşturulmaz.

KADER satırı yalnızca yazılımın satır yazdığını kanıtlar. “STOP_REQUESTED” kaydı, PWM'nin
sıfıra indiğinin veya tekerleğin durduğunun fiziksel kanıtı değildir.

### 6.5 OSMAN / MATT — `arac/surucu.py`

Mevcut durum: `SIMULATED` ve varsayılan fiziksel çıkış `BLOCKED`.

Temel nesneler:

- `MotorRequest`
- `ValidatedDriveRequest`
- `validate_request()`
- `MotorDriver` protokolü
- `FakeMotorDriver`
- `BlockedMotorDriver`

Korunan kurallar:

- Sol ve sağ istekler normalize `[-1, 1]` aralığındadır.
- Her istek faz, sebep, oluşturma zamanı ve isteğe bağlı kare kökeni taşır.
- Ham `MotorRequest` doğrudan sürücüye verilemez.
- Önce TAWNT'nin `ValidatedMotorCommand` nesnesi alınmalıdır.
- TAWNT komutu ile istek fazı ve değerleri tam eşleşmelidir.
- `FakeMotorDriver` yalnızca belleğe kayıt ekler.
- `BlockedMotorDriver` doğrulanmış komutu bile fiziksel çıkışa göndermez.
- `stop()` bir durma isteğidir; fiziksel durma kanıtı değildir.
- Bu dosyada GPIO veya PWM kütüphanesi yoktur.

Gerçek sürücü bu sınırın içine eklenecek son parçadır. Başka hiçbir dosyaya GPIO yazımı
eklenmemelidir.

### 6.6 ARDA / ADAM — `arac/main.py`

Mevcut durum: donanımsız komut arayüzü ve sınırlı öz denetim `IMPLEMENTED`.

Komut arayüzü:

```text
--mode simulation|vehicle
--language tr|en
--auto
--no-color
--version
--check-camera
--usb-index INDEX
--camera-frames 1..30
```

Davranış:

- Varsayılan mod simülasyondur.
- `vehicle` modu fiziksel bağdaştırıcılar incelenene kadar hata kodu `2` ile reddedilir.
- `--auto` yalnızca Enter beklemesini atlar; aracı arm etmez.
- Gerçek kamera ancak açıkça `--check-camera` verildiğinde açılır.
- Kamera tanılaması motor sürücüsü seçmez, TAWNT'yi arm etmez ve sürekli döngü başlatmaz.
- Simülasyon öz denetimi tam olarak bir kare işler.
- Bir geçerli gözlem üretir.
- DORA'yı `BOOT -> SELF_TEST -> READY` yönünde iki olayla ilerletir.
- KADER'e bellekte üç kayıt ekler.
- Bloke motor sürücüsüne durma isteği bırakır.
- TAWNT'yi arm etmez ve motor komutu doğrulamaz.
- Sürekli sürüş döngüsü başlatmaz.
- Öz denetimde hata olursa güvenli biçimde `2` ile çıkar.

Bu öz denetimi yarış sürüş döngüsüne çevirmek okulda yapılacak ayrı, onaylı bir iştir.

### 6.7 Görsel motor simülasyonu — `arac/simulasyon.py` ve `sim/`

Mevcut durum: `IMPLEMENTED` ve `SIMULATED`; fiziksel araç modeli değildir.

- `VisualSimulationBridge`, yalnızca `ValidatedDriveRequest` kabul eder.
- Kabul edilen istek önce `FakeMotorDriver` geçmişine yazılır.
- Normalize sol/sağ değerler, Webots'taki dört sanal tekerlek motoruna açısal hız olarak
  eşlenir.
- Basit diferansiyel sürüş hesabı, birim testler için belirlenmiş `x`, `y` ve yön üretir.
- Webots kendi fizik motorunu kullandığı için hesaplanan yol ile ekrandaki yolun tamamen
  aynı olması beklenmez.
- `sim/controllers/arda_visual/arda_visual.py` sonlu beş hareket parçası çalıştırır,
  sonunda dört sanal motoru sıfırlar ve çıkar.
- Denetleyici TAWNT'nin `OFFLINE` profilini kullanır; GPIO, PWM veya fiziksel sürücü
  içe aktarmaz.
- Windows'ta proje yerel `runtime.ini`, bozuk Microsoft Store `python` takma adı yerine
  `py`; Linux/macOS'ta `python3` seçer.

Görsel çalıştırma ve başsız smoke testi için `sim/README.md` esas alınmalıdır. Başarılı
başsız denetim `STARTECH_WEBOTS_OK` satırı üretir. Bu satır yalnızca simülasyonun bittiğini
kanıtlar; gerçek tekerlek yönü, hız, fren, tutunma veya durma mesafesi hakkında kanıt değildir.

## 7. Mevcut test haritası

| Test dosyası | Koruduğu ana sınır |
|---|---|
| `tests/test_arac_main.py` | ARDA CLI, açık kamera tanılaması, reddedilen araç modu ve sınırlı öz denetim |
| `tests/test_goz.py` | Kare doğrulama, USB→Pi açma sırası, okuma hatası, tanılama ve kaynak yaşam döngüsü |
| `tests/test_goruntu.py` | Geçersiz verinin “yol açık” sayılmaması ve eski kare reddi |
| `tests/test_durum.py` | Geçişler, hata, durma, devam, sıfırlama ve eski olay reddi |
| `tests/test_kayit.py` | JSON güvenliği, sıra, geri yükleme ve bozuk dosya reddi |
| `tests/test_surucu.py` | TAWNT kapısı, sahte sürücü ve bloke fiziksel sınır |
| `tests/test_simulasyon.py` | Ham istek reddi, sanal tekerlek eşlemesi, hareket, dönüş, stop ve kapanış |

Windows'ta `python` komutu Microsoft Store takma adına gidiyorsa çalışan Python
başlatıcısını kullan:

```powershell
py -3.13 -m unittest discover -s tests -v
```

Yalnızca bu yeni sınırları hızlı kontrol etmek için:

```powershell
py -3.13 -m unittest tests.test_arac_main tests.test_goz tests.test_goruntu tests.test_durum tests.test_surucu tests.test_kayit tests.test_simulasyon -v
```

Komut örneği:

```powershell
py -3.13 -m arac.main --mode simulation --language tr --no-color --auto
```

Motorlara dokunmadan sonlu USB→Pi kamera tanılaması:

```powershell
py -3.13 -m arac.main --auto --check-camera --camera-frames 3 --language en --no-color
```

`vehicle` modunun reddedilmesi şu aşamada başarısızlık değil, beklenen güvenlik
davranışıdır.

## 8. Evde yapılabilecekler ve okulda yapılması gerekenler

### Evde, araç olmadan yapılabilecekler

- Veri sınıfları ve protokoller.
- Kayıtlı kare veya video dosyası kullanan analiz.
- Simülasyon dünya verileri.
- Durum geçişleri.
- Sahte motor sürücüsü.
- Webots içindeki dört tekerlekli görsel motor simülasyonu.
- Hatalı, eksik, eski ve bozuk veri testleri.
- JSON şema ve kalibrasyon dosyası doğrulaması.
- CLI ve raporlama.
- Tekrarlanabilir performans ölçüm araçları.

### Okulda, araç yanında yapılması gerekenler

- Kamera aygıt yolunun ve çözünürlüğünün gerçek tespiti.
- Kamera montaj açısının ölçülmesi.
- Lens, görüş alanı, pozlama ve kare hızının ölçülmesi.
- Motor pinlerinin kablodan doğrulanması.
- Sol/sağ motor yönünün ayrı ayrı gözlenmesi.
- Güvenli PWM alt ve üst sınırlarının ölçülmesi.
- Fiziksel stop davranışı ve gecikmesinin ölçülmesi.
- Batarya gerilimi altında davranışın gözlenmesi.
- Tekerlekler havadayken ve sonra düşük hızda zemin testi.
- Fiziksel sonuçların tarih, düzenek ve ölçüm ile kaydedilmesi.

Evde pin, PWM, kamera veya geometri değeri tahmin edip “varsayılan kalibrasyon” olarak
üretim koduna koyma. Bilinmeyen değer açıkça bilinmeyen kalmalıdır.

## 9. Her okul oturumunun başlangıç kontrol listesi

### Yazılım başlamadan

- [ ] `AGENTS_READ_ME.txt` okundu.
- [ ] Kullanıcının güncel talebi ve izin kapsamı yazıldı.
- [ ] `git status --short` kaydedildi.
- [ ] Var olan kullanıcı değişiklikleri ayrıldı.
- [ ] Son doğrulanmış testler çalıştırıldı.
- [ ] Deneyin simülasyon mu fiziksel mi olduğu açıkça etiketlendi.
- [ ] Yarış kuralı etkisi varsa kullanılan resmi kılavuzun tarihi ve sürümü belirtildi.
- [ ] Değişiklik planı sunuldu ve onay alındı.

### Fiziksel güç verilmeden

- [ ] Güncel kod ve kablolama bilgisi incelendi.
- [ ] Beklenen sonuç yazıldı.
- [ ] Olası hata türleri yazıldı.
- [ ] Yazılımsal ve fiziksel durdurma yöntemi yazıldı.
- [ ] İnsan, kodu ve deney adımlarını gözden geçirdi.
- [ ] Aracı tutacak veya sınırlayacak kişi hazır.
- [ ] Motor ve Raspberry Pi güç anahtarlarına erişim açık.
- [ ] Egemen canlı donanım işlemini açıkça yetkilendirdi.
- [ ] Tehlikeli adımdan hemen önce son onay tekrar alındı.
- [ ] İlk deney en düşük enerjili yöntem olarak seçildi.

## 10. Zorunlu fiziksel test sırası

Uygulanabilir olduğu ölçüde sıra şöyledir:

1. Mock/sahte sürücü.
2. Motorlar fiziksel olarak ayrılmış durumda mantık testi.
3. Tekerlekler yerden kaldırılmış durumda test.
4. En düşük uygulanabilir PWM ile kısa test.
5. Düşük hızlı, sınırlı zemin testi.
6. Yalnızca önceki sonuçlar beklenen gibi ise daha serbest hareket.

Beklenmeyen davranışta test durur. Ajan o anda daha geniş veya daha enerjik yeni bir test
uydurmaz. Yeni deney için yeni plan ve izin gerekir.

## 11. Acil durdurma bilgisi

Ekip tarafından verilen fiziksel talimatlar:

- Bilgisayardan kontrol ediliyorsa ve sistem cevap veriyorsa önce `CTRL+C` kullan.
- Motorların kapanması gerekiyorsa aracı güvenle altından tut, kaldır ve üç hücreli pil
  yuvasının yanındaki anahtarı `O` konumuna getir.
- Raspberry Pi için iki hücreli pil yuvasındaki anahtarı kullan.
- Raspberry Pi gücünü aniden kesmek SD kartı bozabilir; fiziksel tehlike yoksa düzenli
  kapatma tercih edilir.
- Hareket anlık fiziksel tehlike yaratıyorsa önce motorları durdurmak gerekir; SD kartı
  korumak ikinci önceliktir.

`CTRL+C` tek başına acil durdurma değildir. Algı veya kontrol döngüsü çöktüğünde son PWM
komutunun kendiliğinden sıfırlandığını varsayma.

## 12. KASIM'ı okulda doğrulama ve geliştirme planı

Amaç: Uygulanmış USB→Picamera2 seçim zincirini araç üzerindeki gerçek Raspberry Pi
kamerasında doğrulamak; ölçülen davranış gerekirse mevcut `CameraSource` sözleşmesini
bozmadan küçük düzeltmeler yapmak.

Önce keşfedilecek gerçekler:

- Kamera modeli ve bağlantı türü.
- İşletim sistemi ve kamera kitaplığı sürümü.
- Aygıtın gerçekten açıldığı yöntem.
- Desteklenen çözünürlük ve kare hızları.
- Zaman damgasının kaynağı ve birimi.
- Açma, okuma ve kapatma zaman aşımı davranışı.
- Kablo kopması veya kamera kaybında oluşan hata.

Önerilen küçük dilimler:

1. Motor gücü kapalıyken Picamera2 paketinin ve kamera aygıtının varlığını doğrula.
2. USB kamera bağlı değilken `--check-camera --camera-frames 1` ile yalnızca aç/oku/kapat
   deneyi yap; kareyi algıya gönderme ve görüntüyü kaydetme.
3. Kaynağın `rpi:0` olarak raporlandığını ve kaynak bırakıldıktan sonra yeniden
   açılabildiğini doğrula.
4. On adet karede artan `frame_id`, çözünürlük ve geçen süreyi ölç.
5. Kamera çıkarıldığında veya kapatıldığında iki kaynak da yoksa fail-closed davranışı
   doğrula.
6. USB kamera bağlanırsa aynı komutun `usb:0` seçtiğini doğrula; bir çalışma ortasında
   kaynak değiştirmeye çalışma.

Kabul ölçütleri:

- Açılmayan kamera fiziksel sürüşü başlatamaz.
- Eski kare tekrar kullanılamaz.
- Okuma süresi aşılırsa açık hata oluşur.
- `close()` hata sonrasında da kaynakları bırakır.
- Test çıktılarına kamera modeli, çözünürlük, FPS ve tarih yazılır.

## 13. KEREM'i okulda geliştirme planı

Amaç: Gerçek veya önceden kaydedilmiş kareden ölçülebilir, ihtiyatlı `Observation` üretmek.

Önce veri topla:

- Düz yol, sola/sağa sapma, kavşak, başlangıç ışığı ve bitiş işareti.
- Farklı aydınlatma, gölge ve parlama.
- Kısmen kapanmış veya bulanık görüntü.
- Engelli ve engelsiz kareler.
- Bilerek bozuk veya eksik kareler.

Her kayıt için gerçek etiketler insan tarafından yazılmalı. Ajan, görüntü adından veya
beklentiden etiket uydurmamalıdır.

Ölçülebilir metrikler:

- Şerit hatası için ortalama mutlak hata.
- Engel için yanlış negatif ve yanlış pozitif sayısı.
- İşaret için karışıklık matrisi.
- Geçersiz/bilinmeyen sonuç oranı.
- Kare başına işlem süresi ve en kötü gecikme.

Güvenli hata davranışı:

- Kare yoksa `Observation.valid=False`.
- Algı güveni belirlenen sınırın altındaysa bilinmeyen.
- Bilinmeyen sonuç yolun açık olduğu anlamına gelmez.
- Eski kareden yeni motor isteği üretilemez.
- İşleme yetişmiyorsa eski kare kuyruğu sınırsız büyütülmez.

İlk KEREM testi canlı motor sürmemelidir. Önce kayıtlı veri, sonra canlı kamera ve sahte
sürücü, en son kontrollü fiziksel bütünleşme yapılır.

## 14. DORA'yı okulda geliştirme planı

Amaç: Gözlem ve sistem sağlık durumlarını açık olaylara dönüştürmek; doğrudan motor sürmek
değil.

Her yeni olay için ajan şunları yazmalıdır:

1. Olayı hangi modül üretir?
2. Hangi kanıta dayanır?
3. Hangi mevcut durumlarda kabul edilir?
4. Hangi yeni duruma geçer?
5. Eski veya yinelenen olay nasıl reddedilir?
6. KADER'e hangi alanlar yazılır?
7. Hata halinde en güvenli hedef durum nedir?

Ek geçiş eklenirse hem başarılı yol hem de yasak geçiş testi yazılmalıdır. `FAULT` veya
`STOPPING` durumundan doğrudan `DRIVING` durumuna gizli kestirme ekleme. Reset insan onayı
istemeye devam etmelidir.

DORA'nın “hareket durdu” olayını kabul etmesi için gerçek sistemde kullanılacak kanıt
ayrıca tasarlanmalıdır. Yalnızca motor komutunun sıfır olması fiziksel hızın sıfır olduğu
anlamına gelmez.

## 15. KADER'i okulda geliştirme planı

Amaç: Deney ve hata geçmişini elektrik kesintisi ve yeniden başlatma durumlarında
olabildiğince anlaşılır tutmak.

Okulda karar verilmesi gerekenler:

- Raspberry Pi üzerindeki yazılabilir kayıt dizini.
- Depolama kotası.
- Dosya döndürme/arsivleme yöntemi.
- Her deney için `run_id` biçimi.
- Saat kaynağı ve saat yanlışsa uygulanacak yöntem.
- Disk dolduğunda davranış.
- Güç kaybında yarım JSONL satırının nasıl raporlanacağı.
- Kişisel veya gereksiz görüntü verisinin tutulup tutulmayacağı.

Yeni kayıt türü eklerken:

- JSON alanlarını belgeleyin.
- Kaynak modülü belirtin.
- Varsa `frame_id` kökenini koruyun.
- Kalibrasyon sürümünü veya hash'ini ekleyin.
- Yazılım isteği ile fiziksel ölçümü ayrı kayıt türlerinde tutun.

Bozuk kayıt dosyasını sessizce düzeltip yarışa devam etmek yerine hata açıkça görünmeli ve
operatör kararı istenmelidir.

## 16. OSMAN'ı okulda geliştirme planı

Amaç: TAWNT doğrulamasından geçmiş motor isteğini, son bir fail-closed kapı üzerinden
fiziksel sürücüye iletmek.

Bu modül en son bağlanmalıdır.

Önce insan tarafından doğrulanacak gerçekler:

- Motor sürücü kartının tam modeli.
- Sol ve sağ kanal pinleri.
- Yön pinlerinin gerçek anlamı.
- PWM frekansı.
- Güvenli başlangıç duty cycle değeri.
- Motorun harekete başladığı minimum değer.
- Ters yön ve fren/coast davranışı.
- Güç açılışında pinlerin varsayılan durumu.
- İşlem çöktüğünde çıkışın davranışı.

Kod kuralları:

- GPIO/PWM kütüphanesi yalnızca OSMAN'ın gerçek bağdaştırıcısında bulunur.
- Constructor fiziksel hareket üretmez.
- Varsayılan çıkış sıfır/off olur.
- Ham `MotorRequest` kabul edilmez.
- Sadece `ValidatedDriveRequest` kabul edilir.
- Arm ve sağlık şartları her uygulamada yeniden kontrol edilir.
- `stop()` tekrar tekrar güvenle çağrılabilir.
- Hata ve `close()` yolları sıfır çıkış ister.
- Sol veya sağ kanal yazımı yarıda kalırsa hata açıkça raporlanır.
- Son PWM komutunu “araç durdu” diye kaydetme.

İlk fiziksel sürücü testi ARDA'nın tam sürüş döngüsüyle yapılmamalıdır. Küçük, süre sınırlı,
insan gözetimli ve tekerlekleri kaldırılmış bir sözleşme testi olmalıdır.

## 17. ARDA'yı okulda geliştirme planı

Amaç: Tek bir üst düzey döngüde kamera, algı, durum, motor ve kaydı birleştirmek.

Önerilen bütünleşme sırası:

1. `SequenceCamera + SimulatedVisionAnalyzer + StateMachine + MemoryBlackBox + FakeMotorDriver`.
2. Kayıtlı gerçek kare + gerçek KEREM + `FakeMotorDriver`.
3. Canlı KASIM + gerçek KEREM + `FakeMotorDriver`.
4. Canlı KASIM + gerçek KEREM + bloke OSMAN.
5. İnsan onaylı, süre sınırlı fiziksel OSMAN deneyi.
6. Yalnızca bütün önceki kanıtlar yeterliyse sınırlı tam döngü.

Her döngü adımında açık sıra:

```text
frame al
-> frame geçerliliğini denetle
-> observation üret
-> observation geçerliliğini denetle
-> DORA olayını ve yeni durumu üret
-> motor isteğini gerekçesiyle üret veya açık stop iste
-> TAWNT doğrulaması
-> OSMAN uygulaması
-> KADER kayıtları
```

Herhangi bir aşama hata verirse daha eski “iyi” sonuçla körlemesine devam etme. Hata DORA'ya
bildirilmeli, motor katmanından stop istenmeli ve kanıt KADER'e yazılmalıdır. Bunun fiziksel
durma garantisi olmadığı kullanıcıya gösterilmelidir.

ARDA içine ikinci motor sürücü yolu, ikinci kontrol döngüsü veya TAWNT'yi atlayan “test
kolaylığı” ekleme.

## 18. Kalibrasyon ve yapılandırma kökeni

Her kritik değer şu bilgilerle izlenebilmelidir:

- Değerin adı.
- Sayısal değer ve birim.
- Nerede ölçüldüğü.
- Kim tarafından ölçüldüğü.
- Tarih ve kullanılan araç düzeni.
- Ham ölçüm veya dosya referansı.
- Geçerli olduğu donanım sürümü.
- Onay durumu.

Tahmin, ölçüm değildir. Örnek değer, araç kalibrasyonu değildir. LLM tarafından önerilen
değer fiziksel kanıt olmadan yalnızca `PROPOSED` olabilir.

Mevcut şema ve örnek dosyaları:

- `config/schema/ayarlar-v1.schema.json`
- `config/schema/kalibrasyon-v1.schema.json`
- `config/examples/ayarlar-v1.ornek.json`
- `config/examples/kalibrasyon-v1.ornek.json`

Ajan yeni ayar alanı eklemeden önce doğrulama kodunu, şemayı, geçerli örneği ve geçersiz
örnek testini birlikte planlamalıdır. Yapılandırma değişikliği tek başına motor davranışını
kanıtlamaz.

## 19. İstek doğrulama matrisi

| Sınır | Geçerli örnek | Zorunlu ret örneği | Ret sonucu |
|---|---|---|---|
| KASIM kare | Artan kimlik, sonlu zaman, payload var | Tekrarlanan kimlik | `InvalidFrame` veya `CameraExhausted` |
| KEREM gözlem | Açık valid, normalize hata, engel bool | Geçersiz ama `obstacle=False` iddiası | `InvalidObservation` |
| DORA olay | İzinli geçiş, yeni zaman/kare | `BOOT -> DRIVING` | `IllegalTransition`, durum değişmez |
| KADER kayıt | JSON-safe veri, doğru sıra | `NaN` veya geriye giden kare | `InvalidRecord` / `RecordOrderError` |
| OSMAN istek | Normalize değer, faz, sebep | Ham istek veya arm edilmemiş TAWNT | Ret; fiziksel yazım yok |
| ARDA araç modu | Gelecekte tüm bağdaştırıcılar incelenmiş | Bugünkü `--mode vehicle` | Çıkış kodu `2` |

Yeni ajan yalnızca başarılı yol testi yazmamalıdır. Her sınır için en az bir bozuk, bir eski
ve bir fail-closed senaryosu değerlendirilmelidir.

## 20. Hata tepki tablosu

| Hata | Yazılımın ilk tepkisi | Fiziksel iddia |
|---|---|---|
| Kamera açılamıyor | Başlatmayı reddet, FAULT iste, kaydet | Araç duruyor deneme |
| Kare zaman aşımı | Eski kareyi kullanma, stop iste, kaydet | Stop isteğinin uygulandığını ölçmeden söyleme |
| Algı geçersiz | Bilinmeyen say, sürüş komutu üretme | Yol açık deneme |
| Eski olay | DORA reddeder, durumu korur, kaydet | Önceki fiziksel hal bilinmiyor olabilir |
| Kayıt diski dolu | Hata bildir, politikasına göre fail closed | Kayıt yoksa olay olmadı deneme |
| TAWNT reddi | OSMAN'a uygulama gönderme, kaydet | Fiziksel çıkışın sıfır olduğunu ayrıca doğrula |
| GPIO yazım hatası | Stop/close iste, operatöre bildir | Fiziksel anahtara hazırlan |
| Kontrol döngüsü çökmesi | En dış `finally` ile stop/close iste | Son PWM'nin kaybolduğunu varsayma |

## 21. Gelecek ajan için plan şablonu

Her üretim değişikliğinden önce aşağıdaki bölümler doldurulmalıdır. Son cümle depo
sözleşmesindeki metinle tam aynı olmalıdır.

```markdown
## Main reason

Doğrulanmış mevcut durum ve ulaşılmak istenen küçük sonuç.

## Recreation

- Oluşturulacak dosyalar ve yaklaşık satırlar
- Değiştirilecek dosyalar ve yaklaşık ekleme/silme
- Taşınacak veya silinecek dosyalar

## Recreation reason

Her dosyada şimdi ne olduğu, sonra ne olacağı ve farkın neden gerekli olduğu.

## Proof

- Birim testleri
- Sözleşme ve hata testleri
- Varsa kayıtlı görüntü metrikleri
- Varsa insan gözetimli fiziksel ölçüm planı

## Summary

Dosyalar, tahmini ekleme/silme, riskler, hariç tutulan işler ve commit planı.

Do you approve? If you have questions, ask now.
```

Onay yalnızca yazılan kapsamı kapsar. Yeni donanım kararı, yeni özellik veya farklı dosya
için ek plan gerekir.

## 22. Her değişiklikten sonra kanıt şablonu

```markdown
### Yazılım kanıtı

- Çalıştırılan komut:
- Geçen test sayısı:
- Başarısız test sayısı:
- Bilinen başlangıç hataları:
- Yeni değişikliğin yol açtığı hatalar:

### Fiziksel kanıt

- Durum: NOT RUN / OBSERVED / MEASURED
- Tarih ve yer:
- İnsan gözetmen:
- Araç düzeni:
- Ölçüm:
- Beklenen sonuç:
- Gözlenen sonuç:
- Durdurma yöntemi:

### Git

- Değişen dosyalar:
- Tam eklenen/silinen satırlar:
- Commit:
- Hariç tutulan kullanıcı değişiklikleri:
```

Fiziksel deney yapılmadıysa alanı boş bırakma; açıkça `NOT RUN` yaz.

## 23. Commit disiplini

- Her onaylı mantıksal değişikliği ayrı commit yap.
- İlgisiz kullanıcı değişikliklerini stage etme.
- `git diff --cached --check` çalıştır.
- Commit'ten önce tam testleri çalıştır.
- Hook çalışmıyorsa sebebi ve kullanılan alternatif doğrulamayı açıkça raporla.
- Commit geçmişini yeniden yazma.
- `reset --hard`, force push veya izinsiz uzak depoya push yapma.
- Tam dosya ve satır sayılarını `git show --stat` ve `git show --numstat` ile raporla.

## 24. Yasak kısa yollar

Aşağıdakileri yapma:

- ARDA, DORA veya KEREM'den doğrudan GPIO/PWM yazmak.
- TAWNT doğrulamasını “sadece test” gerekçesiyle atlamak.
- `BlockedMotorDriver` yerine sessizce gerçek sürücü seçmek.
- Eksik algıyı `obstacle=False` olarak kabul etmek.
- Son kamera karesini sonsuza kadar yeniden kullanmak.
- Zaman aşımını gizlemek.
- Motor isteğini fiziksel hareket kanıtı saymak.
- Log satırını fiziksel durma kanıtı saymak.
- Plan dosyasındaki eski bilgi yüzünden çalışan kodu yeniden yazmak.
- Kullanıcının kirli çalışma ağacını temizlemek.
- Açık istek olmadan `PLAN_New.md` düzenlemek.
- İnsan incelemesi olmadan fiziksel aracı çalıştırmak.
- Egemen'in canlı donanım izni olmadan güç vermek veya gerçek motor komutu göndermek.
- “Tüm sistem hazır/güvenli” gibi kanıttan geniş sonuç çıkarmak.

## 25. Bilinmeyen ve okulda doldurulacak bilgiler

Bu belge yazıldığı anda aşağıdakiler doğrulanmış değildir:

- [ ] Raspberry Pi modeli ve işletim sistemi sürümü.
- [ ] Araçtaki Raspberry Pi kamera modeli, Picamera2 sürümü ve aygıt numarası.
- [ ] Kamera çözünürlük/FPS/pozlama değerleri.
- [ ] Kamera montaj geometrisi.
- [ ] Motor sürücü kartı modeli.
- [ ] GPIO pin haritası.
- [ ] PWM frekansı ve güvenli duty cycle sınırları.
- [ ] Sol/sağ ileri yön işaretleri.
- [ ] Fren ve coast davranışı.
- [ ] Fiziksel durma gecikmesi ve mesafesi.
- [ ] Araç üzerindeki kalıcı log dizini ve disk kotası.
- [ ] Yarış günü kullanılacak tam kalibrasyon sürümü.
- [ ] 2026 resmi yarış kılavuzunun en güncel baskısı ve son duyurular.

Bu değerlerden herhangi biri kod değişikliğini etkiliyorsa ajan varsayım yapmadan önce ekibe
sormalıdır. Ölçülen değer, ölçüm tarihi ve yöntemiyle kaydedilmelidir.

## 26. Okul oturumu için önerilen ilk görev

İlk fiziksel günün hedefi aracı sürmek olmamalıdır. Önerilen en küçük yararlı görev:

1. Güncel git durumunu ve test sonucunu kaydet.
2. Kamera ve motor donanımının tam modellerini fotoğraf/etiket üzerinden insanla doğrula.
3. Kablolama haritasını insan incelemesiyle çıkar.
4. Motor gücü kapalıyken uygulanmış USB→Pi zincirinin tek karelik doğrulama planını sun.
5. Onaydan sonra `--check-camera --camera-frames 1` ile Picamera2 aç/oku/kapat sınırını
   doğrula; ancak kanıtlanan bir uyumsuzluk varsa küçük bağdaştırıcı düzeltmesi öner.
6. Motorlar kapalıyken on karelik süre ve kaynak kaybı davranışını ayrı onayla ölç.
7. Sonuçları yazılım kanıtından ayrı fiziksel gözlem olarak kaydet.
8. Oturumu küçük, odaklı commit ve açık kalan gerçekler listesiyle bitir.

Bu sıra, gerçek bilgi toplar ve motor riskine girmeden simülasyon sözleşmesini ilk fiziksel
bağdaştırıcıya dönüştürür.

## 27. Ajanın görev sonu raporu

Görev sonunda kullanıcıya yalnızca “bitti” deme. Şunları açıkça bildir:

- Bu değişiklik tam olarak neyi sağladı.
- Hangi iddiaların testlerle doğrulandığı.
- Fiziksel test yapılıp yapılmadığı.
- Hangi şeylerin hâlâ öneri veya bilinmeyen olduğu.
- Değişen dosyalar ve tam satır sayıları.
- Oluşturulan commit kimlikleri.
- Korunan, stage edilmeyen kullanıcı değişiklikleri.
- Test veya hook sorunu varsa gerçek sebebi.

Genel projenin tamamlandığına yalnızca ekip karar verir.

## 28. Kısa İngilizce devir özeti

Future agents: the six `arac` modules are intentional, tested contracts, not empty
placeholders. Preserve their fail-closed boundaries. Do not touch TAWNT, do not edit
`PLAN_New.md`, and do not add hardware access without a separately approved plan. KASIM has
an implemented USB-first, Picamera2-second camera cascade; USB acquisition was checked on a
Windows laptop, but the Pi camera remains physically unverified. ARDA opens it only through
the explicit finite `--check-camera` diagnostic. OSMAN is the only planned physical motor
gateway; every motion request must pass existing TAWNT validation. The Webots demo also
passes requests through TAWNT and `FakeMotorDriver`, but it never proves physical motion.
At school, verify one adapter at a time while motor power remains off. A software log or
requested stop is not proof of physical behavior. Human review, Egemen's live-hardware
authorization, immediate final confirmation, reachable power switches, and the least
energetic test order are mandatory.
