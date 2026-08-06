# SIRA — zaman çizelgesi ve yapılacaklar

> **Amaç:** Bu dosya, projenin hangi sırayla ilerleyeceğini öğrenci diliyle anlatır.
> Ayrıntılı teknik gerekçeler `Markdown/PLAN_New.md` içindedir.
>
> **Son güncelleme:** 6 Ağustos 2026
>
> **Kural:** Bir kutunun işaretli olması için yalnızca “yaptık” denmesi yetmez. İlgili
> çıkış kanıtı bulunmalıdır. Burada doğrulanmamış hiçbir iş tamamlandı gösterilmez.

---

## 1. İşaretler nasıl okunur?

| İşaret | Anlamı |
|---|---|
| `[ ]` | Yapılmadı veya yapıldığı doğrulanmadı |
| `[~]` | Başlandı fakat çıkış şartı tamamlanmadı |
| `[x]` | Kanıtıyla tamamlandı |
| `[?]` | Gerçek araç veya insan cevabı olmadan doğrulanamaz |
| `İKİ KİŞİ` | Fiziksel risk veya hatayı fark etme ihtiyacı nedeniyle yalnız yapılmaz |
| `EGEMEN SON ONAYI` | Tehlikeli fiziksel adımdan hemen önce Egemen tekrar onay verir |
| `KAPI` | Bu tamamlanmadan sonraki aşama başlamaz |

Bir görev için üç ayrı şey vardır:

1. **İş:** Ne yapacağız?
2. **Neden:** Bunu neden şimdi yapıyoruz?
3. **Çıkış kanıtı:** Bittiğini ne gösterecek?

Kodun var olması, özelliğin çalıştığını kanıtlamaz. Bir kere çalışması da tekrar edilebilir
olduğunu kanıtlamaz.

---

## 2. Değişmeyen güvenlik sırası

Fiziksel araçla her oturumdan önce:

- [ ] Kullanılacak commit ve kirli/temiz Git durumu kaydedildi.
- [ ] AI tarafından yazılan veya değiştirilen kod insanlar tarafından okundu.
- [ ] Testin amacı, beklenen sonucu ve durdurma yöntemi yüksek sesle açıklandı.
- [ ] Motor anahtarı ve Raspberry Pi anahtarı bulundu; ulaşılabilir durumda.
- [ ] CTRL+C'nin yalnızca yazılım isteği olduğu, fiziksel anahtarın yerine geçmediği biliniyor.
- [ ] Aracı güvenli biçimde alttan tutabilecek ikinci kişi hazır. `İKİ KİŞİ`
- [ ] İlk deneme mümkün olan en düşük enerji düzeyinde seçildi.
- [ ] Egemen canlı donanım testine izin verdi.
- [ ] Tehlikeli komuttan hemen önce Egemen son onayı verdi. `EGEMEN SON ONAYI`

Durdurma sırası:

1. Bilgisayardan kontrol ediliyorsa ve sistem cevap veriyorsa CTRL+C.
2. Motorların durması gerekiyorsa araç alttan güvenli biçimde tutulup kaldırılır.
3. Üçlü pil yatağının yanındaki motor anahtarı `O` konumuna alınır.
4. Raspberry Pi için ikili pil yatağının anahtarı kullanılır.
5. Raspberry Pi gücünü aniden kesmenin SD kartı bozabileceği unutulmaz.
6. Fiziksel tehlike varsa önce motorlar durdurulur; SD kart ikinci önceliktir.

---

# A. AĞUSTOS 2026 — araç olmadan temel hazırlık

Bu aşamada fiziksel araç kullanılmaz.

## A1. Depo gerçeğini kaydet

- [x] Ana Git deposu ve uzak depolar bulundu.
- [x] `.githooks` yolu yapılandırılmış durumda.
- [ ] Mevcut kullanıcı değişiklikleri insan tarafından gözden geçirilecek.
- [ ] İzlenmeyen 3awnt dosyalarının projeye alınıp alınmayacağı Egemen tarafından kararlaştırılacak.
- [ ] `CLAUDE.md`, gerçek Git durumuyla karşılaştırılıp ayrı planla güncellenecek.

**Neden:** Eski belgelerde “uzak depo yok” veya “kanca yok” gibi artık doğru olmayan
ifadeler bulunuyor. Belgeye değil, doğrulanmış depo durumuna göre hareket etmeliyiz.

**Çıkış kanıtı:** `git status`, uzak depo listesi ve `core.hooksPath` sonucu takımca görüldü.

## A2. Ana ajan sözleşmesi

- [~] `AGENTS_READ_ME.txt` hazırlanıyor.
- [ ] Egemen ve T metni okuyup kabul edecek.
- [ ] Yeni bir ajanla küçük, risksiz bir deneme yapılarak kuralların anlaşıldığı gözlenecek.

**Çıkış kanıtı:** Ajan; yetki sırasını, plan zorunluluğunu ve araç öncesi insan kapısını
doğru biçimde açıklayabiliyor.

## A3. 3awnt karar noktası

- [x] Mevcut prototipin ne yaptığı incelendi.
- [x] Mevcut sınırlar belirlendi.
- [x] Hibrit mimari belgelendi.
- [ ] 3awnt'ın yeni `arac/` yapısına girip girmeyeceği Egemen tarafından onaylanacak.
- [ ] Onaylanırsa entegrasyon için ayrı kod planı yazılacak.

**KAPI:** Bu aşamada 3awnt “araç güvenliği tamamlandı” diye sunulamaz.

## A4. Belgeleri ve gerçek kodu eşleştir

- [ ] `kontrol.py` içindeki mevcut belge kontrol hatası ele alınacak.
- [ ] `motor_balance.py` / `motor_balance_test.py` isim uyuşmazlığı ayrı planla çözülecek.
- [ ] `CLAUDE.md` içindeki güncelliğini kaybetmiş Git iddiaları ayrı planla düzeltilecek.
- [ ] SUBIRU'nun boş `tasks.json` dosyası başlangıç görevleriyle doldurulacak.
- [ ] `owners.py` içindeki yalnız baş harf kullanımı takım kararına göre açıklanacak.

**Neden:** Yanlış belge, yanlış kod kadar tehlikelidir; bir sonraki öğrenci yanlış şeyi
doğru sanarak zaman kaybedebilir.

## A5. Kalibrasyon aracını masaüstünde doğrula

- [ ] `StarTechConfig` için gerçek depo/yedek durumu doğrulanacak.
- [ ] Araç derlenecek.
- [ ] Geçerli bir `kalibrasyon.json` üretilecek ve insanlar tarafından okunacak.
- [ ] Aynı dosyanın iki kez gönderilmesinde beklenen 201/409 davranışı doğrulanacak.
- [ ] Altı renk maskesinin önizlemesi kontrol edilecek.

**Çıkış kanıtı:** Üretilmiş JSON, ekran görüntüsü veya kayıt ve tekrarlanabilir sunucu testi.

---

# B. EYLÜL İLK GÜN — yalnızca ölç, kod yazma

> **Bu oturumun kuralı:** Araç başında yeni özellik yazılmaz. Önce bilinmeyenler ölçülür.

## B1. Güç sistemi

- [?] Motor tarafındaki pil sayısı: 2S mi 3S mi?
- [?] Tam PWM'de motor uçlarındaki gerçek gerilim ölçüldü mü?
- [?] Motor etiketindeki nominal gerilim gerçekten 6 V mu?

**Neden:** 3S yaklaşık 10–12 V seviyesine çıkabilir. 6 V motor için PWM tavanı gerekebilir.
2S ise aynı tavan gereksiz yere performansı düşürebilir. Sayı tahmin edilmeyecek.

**Çıkış kanıtı:** Multimetre değeri, pil durumu, tarih, ölçen kişi ve kullanılan yöntem.

## B2. Motor kablolaması — `İKİ KİŞİ`

- [?] Her L298N kanalının hangi fiziksel motora gittiği kablo takip edilerek çizildi.
- [?] Düzenin sol/sağ mı, ön/arka mı olduğu kesinleştirildi.
- [?] Motorların L298N `OUT` uçlarında olduğu doğrulandı; `IN` yalnız mantık girişidir.

**KAPI:** Bu cevaplar gelmeden direksiyon karışım işareti seçilmez ve fiziksel kontrol testi
yapılmaz.

## B3. Raspberry Pi ve kamera

- [?] `dtoverlay=pwm-2chan` gerçekten etkin mi?
- [?] Kamera CSI mı USB mi?
- [?] `picamera2` veya seçilen arka uç gerçek kare üretiyor mu?
- [?] Gerçek çözünürlük ve FPS nedir?

**Çıkış kanıtı:** Sistem yapılandırması, küçük kamera testi ve zaman damgalı örnek kare.

## B4. Yarışma uygunluk ölçümleri — `İKİ KİŞİ`

- [?] Araç 20×30 cm taban sınırına uyuyor mu?
- [?] Yükseklik 25 cm altında mı?
- [?] Teker çapları 10 cm veya altında mı?
- [?] Kamera dışında sensör veya bağlı/bağsız yasak donanım var mı?
- [?] Fiziksel başlatma butonu var ve çalışıyor mu?

**Not:** Bunlar 2026 kılavuzuna ait tarihli başlangıç değerleridir. Yeni kılavuz çıkınca
yeniden kontrol edilir.

## B5. Ölçümleri kaydet

- [ ] Her cevap tarih, kişi ve yöntemle kaydedildi.
- [ ] `[UNVERIFIED]` etiketi yalnızca gerçek kanıt varsa kaldırıldı.
- [ ] Çelişen belge veya kablo şeması ayrıca not edildi.

Ölçüp yazmamak, sonraki ekip açısından ölçmemekle aynıdır.

---

# C. EYLÜL İLK HAFTA — yeniden yazmadan önce ucuz deney

Bu deney, eski aracın iki güçlü arıza adayını düşük maliyetle sınar. Kalıcı özellik
geliştirme değildir. `LEGACY/` değişikliği yapılacaksa ayrıca onaylanmış plan gerekir.

## C1. Trim hatalarını önce düzelt

- [ ] Trim seçimi PWM işaretine göre değil teker kimliğine göre yapılacak.
- [ ] Trimin hem `controller.py` hem `motor.py` içinde iki kez uygulanması engellenecek.
- [ ] `motor_balance_test.py` ile gerçek yapılandırma anahtarları eşleştirilecek.

**Neden:** Trimler 1.0 iken bu hatalar görünmez. Gerçek ölçüm girildiği anda doğru ölçüm
yanlış uygulanabilir.

## C2. Perspektifi tek değişken olarak sına — `İKİ KİŞİ`

- [ ] Aracın gerçek kamerası ve gerçek yüksekliği kullanıldı.
- [ ] 800×680 veya ölçülen gerçek çözünürlük için köşeler yeniden seçildi.
- [ ] Başka kontrol değeri değiştirilmeden sürüş yapıldı.
- [ ] Kayıt ve rapor okundu.

## C3. Motor trimini ikinci değişken olarak sına — `İKİ KİŞİ`

- [ ] Fiziksel asimetri ölçüldü.
- [ ] Yalnız trim değerleri değiştirildi.
- [ ] Aynı parkur ve benzer pil koşulunda tekrar test edildi.
- [ ] Önce/sonra sonucu sayıyla karşılaştırıldı.

## C4. Teşhis sırasında integral

- [ ] `KI = 0` tutuldu.

**Neden:** İntegral sabit sapmayı bir süre gizleyip virajda boşaltabilir. İlk teşhiste
perspektif ve mekanik asimetriyi ayrı görmek istiyoruz.

**Çıkış kararı:**

- Araç belirgin düzelirse yeniden yazma yine yapılabilir; fakat eski bilgiyi taşıyan kontrollü
  bir mimari çalışması olur.
- Düzelmezse iki güçlü aday elenmiş olur; rastgele kazanç ayarına geçilmez.

---

# D. FAZ 1 — güvenli motor temeli, Eylül–Ekim

> **Amaç:** Araç şeridi görmeden önce, verilen sol/sağ komutun öngörülebilir ve güvenli
> fiziksel davranış ürettiğini kanıtlamak.

- [ ] `arac/ayar.py`: ayar ve kalibrasyon dosyalarını yükler, şema ve çözünürlük kontrolü yapar.
- [ ] `arac/surucu.py`: sahte ve gerçek sürücü arka uçları; başlangıçta motorlar kapalı.
- [ ] `arac/bildir.py`: LED/buzzer ile açık durum bildirimi.
- [ ] 3awnt kullanılacaksa ayrı planla yalnızca bu mimariye bağlanır.
- [ ] Bütün motor komutlarının `surucu.py` üzerinden geçtiği otomatik denetlenir.
- [ ] NaN, sonsuz, sınır dışı ve kilitli komut testleri yazılır.
- [ ] Sahte sürücüyle hata enjeksiyonu yapılır.
- [ ] İnsan kod incelemesi tamamlanır.
- [ ] Tekerlekler yerden kesikken düşük PWM testi yapılır. `İKİ KİŞİ` `EGEMEN SON ONAYI`
- [ ] Zeminde düşük hızlı kavis testi yapılır. `İKİ KİŞİ` `EGEMEN SON ONAYI`

**Çıkış kanıtı / KAPI:** `(60, 80)` ve ayna komutu, güvenli sınırlar içinde üçer kez
tekrarlanabilir kavis üretir; durdurma denemesi motorları gözle görünür biçimde durdurur;
ölçülen trim ve bağlantı yönü kaydedilir.

---

# E. FAZ 2 — şeridi görmek, Ekim–Kasım

Bu fazın büyük kısmı kayıtlı video ile, araç hareket etmeden yapılabilir.

- [ ] Bantla düz, iki yönlü viraj ve kesikli şerit bölümü kurulur.
- [ ] Kayıtlar aracın kendi kamerası ve gerçek kamera yüksekliğinden alınır. `İKİ KİŞİ`
- [ ] `arac/goz.py`: USB, Picamera2 ve video dosyası arka uçları.
- [ ] `arac/goruntu.py`: şerit tespiti ve güven değeri.
- [ ] Perspektif kalibrasyonu kamera profiline bağlanır.
- [ ] Renk maskeleri gerçek kare üzerinde insan gözüyle önizlenir.
- [ ] Sabit bir test klibi seti ayrılır; ayar sırasında değiştirilmez.

**Çıkış kanıtı / KAPI:** Ayrılmış test klibinde, kesikli bölümler dâhil karelerin en az
%95'inde makul şerit merkezi. Sonuç sayı ve klip kimliğiyle kaydedilir.

---

# F. FAZ 3 — döngüyü kapatmak, Kasım–Ocak

> **Yılın ana kilometre taşı:** Araç görev yapmasa bile şeridi kendi başına güvenilir
> biçimde takip edebilmeli.

- [ ] `arac/durum.py`: görev sırası sabit olmayan durum makinesi.
- [ ] PD kontrolü; işaret yönü fiziksel ölçüm sonrası karara bağlanır.
- [ ] Ölü bölge, hız tavanı ve hedef hız birlikte tutarlı hâle getirilir.
- [ ] Slew/rampa sınırı ile ani PWM değişimi azaltılır.
- [ ] `arac/kayit.py`: kare, görüntü, durum, hata ve motor komutunu aynı zaman çizgisinde tutar.
- [ ] Kamera ve kontrol döngüsü watchdog'u tasarlanıp ayrı planla uygulanır.
- [ ] `arac.service`, buton ve LED ile ekransız/telsizsiz başlatma kurulur.
- [ ] Kayıp kamera ve yakalanmamış hata testlerinde son PWM korunmaz.
- [ ] Pistte kazanç ayarı yapılır. `İKİ KİŞİ` `EGEMEN SON ONAYI`

**Çıkış kanıtı / KAPI:** Dizüstü bağlı değilken, yalnız fiziksel butonla başlayan üç
ardışık tur; sıfır şerit ihlali ve insan müdahalesi yok. Tur süreleri ve kayıt kimlikleri
yazılır.

**Yarıyıl kararı:**

- Başarılıysa görev geliştirmeye geç.
- Başarısızsa kapsamı küçült: önce sollama, sonra çıkmaz yol, sonra tümsek ertelenebilir.
- Şerit takibi ertelenmez; bütün görevlerin temelidir.

---

# G. YENİ MEB KILAVUZU ÇIKINCA

- [ ] Resmî PDF ve yayın tarihi kaydedilir.
- [ ] Puanlar eski kılavuzla karşılaştırılır.
- [ ] Boyut, teker, sensör, haberleşme ve başlangıç kuralları karşılaştırılır.
- [ ] Görev tanımları ve görev sırası kuralları karşılaştırılır.
- [ ] Başvuru tarihi ve gerekli belgeler kaydedilir.
- [ ] Çelişki varsa geliştirme durdurulup US'a bildirilir.
- [ ] `PLAN_New.md` yalnızca açık belge güncelleme onayıyla değiştirilir.

---

# H. FAZ 4 — görevler, Ocak–Mart

Her görev için aynı döngü kullanılır:

1. Kayıtlı görüntüde algıla.
2. Sahte sürücüyle davranışı doğrula.
3. İnsan kod incelemesi yap.
4. İzole fiziksel parkurda düşük hızla dene.
5. On deneme kaydet.
6. En az sekizi puan davranışı üretiyorsa sonraki göreve geç.

Önerilen sıra:

- [ ] Trafik ışığıyla başlatma — düşük zorluk, yüksek değer ve her turun ön koşulu.
- [ ] Yaya geçidi ve hemzemin geçit — benzer durma davranışları birlikte geliştirilebilir.
- [ ] Hız tümseği — hız azaltma; seçilen hız ölü bölgenin altında olmamalı.
- [ ] Park — turun sonunda ve izole test edilebilir.
- [ ] Çıkmaz yol — levha türü ile durum makinesi arasındaki `sign_type` sözleşmesi gerekir.
- [ ] Sollama — bilinçli şerit değiştirdiği ve tuzak nesne içerdiği için en son.

**KAPI:** Bir görev, kayıtları okunmadan ve başarısız denemeleri açıklanmadan tamamlandı
sayılmaz.

---

# I. MART — başvuru

2026 referansı: son tarih 20 Mart 18.00, yarışma 6–8 Mayıs; uzatma duyurusu daha sonra
gelmişti. Yeni yılın tarihleri ayrıca doğrulanacaktır.

- [ ] Başvurular açılır açılmaz takvime birincil ve yedek sorumlu girilir.
- [ ] Ana sorumlu danışman öğretmen, yedek Egemen olarak doğrulanır veya güncellenir.
- [ ] Form, bütün belgeler ve kura kaydı ayrı ayrı tamamlanır.
- [ ] Son güne bırakılmaz; aracın o gün çalışmasına bağlanmaz.
- [ ] Yüklenen dosyaların indirilebilir kopyası saklanır.

**Çıkış kanıtı:** Resmî sistemde tamamlanmış durum ve okulun erişebildiği yükleme kaydı.

---

# J. FAZ 5 — tam turlar, Mart–Nisan

- [ ] Farklı ışık koşullarında uçtan uca turlar.
- [ ] Görev sırası turlar arasında değiştirilir.
- [ ] Her koşudan sonra kara kutu okunur.
- [ ] Piller farklı doluluklarda denenir.
- [ ] Yedek parçalar takılıp çıkarılarak gerçekten sınanır.
- [ ] Kalibrasyon dosyasının yanlış kamera/çözünürlükle başlamayı reddettiği doğrulanır.

**Çıkış kanıtı / KAPI:** Beş ardışık tam tur; her biri yeni kılavuzdaki süre sınırına
uyar ve takımın önceden belirlediği puan hedefini aşar.

---

# K. NİSAN — yarışma hazırlığı

- [ ] Yedekler Şubat ayına kadar sipariş edilmiş ve denenmiş olacak.
- [ ] Pil ve şarj planı hazırlanacak.
- [ ] Ethernet kablosu, SD kart kopyası ve gerekli araçlar paketlenecek.
- [ ] Kalibrasyon özeti ile yarışma öncesi kontrol listesi basılacak.
- [ ] Sahada bulunacak iki öğrenci ve yedek roller belirlenecek.
- [ ] Yasak uzaktan kontrol/haberleşme donanımı insan tarafından fiziksel kontrol edilecek.
- [ ] Kullanılacak Git commit etiketlenecek; kirli çalışma ağacıyla yarışmaya gidilmeyecek.

---

# L. MAYIS — yarışma

- [ ] Teknik kontrolden önce boyut, teker, sensör ve buton yeniden kontrol edilir.
- [ ] Deneme turu tek resmî kalibrasyon penceresi kabul edilir.
- [ ] Renk/şerit/işaret önceliği yeni kılavuza göre uygulanır.
- [ ] Görevlerin o turdaki sırası gözlenip not edilir.
- [ ] Her turdan önce basılı kontrol listesi iki kişiyle işaretlenir.
- [ ] Turlar arasında kayıtlar ve yapılandırma kopyalanır.
- [ ] Kanıtsız, son dakika ve kapsam dışı kod değişikliği yapılmaz.

---

# M. MAYIS SONRASI

- [ ] Yeni aracın kayıtları ve başarısızlıkları HATA DEFTERİ'ne dürüstçe işlenir.
- [ ] `LEGACY/`, yalnızca yeni sistem onu ölçülebilir testte geçtiğinde arşivlenir.
- [ ] Alan adı, VPS, GitHub, Vercel/R2 ve diğer hesapların sahipliği tek kişiye bağlı
  kalmayacak biçimde karara bağlanır.
- [ ] Mezuniyet öncesi erişim devri ve kurtarma yöntemleri sınanır.
- [ ] Bir sonraki ekip için çalışan sistem, kaynaklar ve kanıtlı başlangıç noktası bırakılır.

---

## 3. Bugünkü kısa TODO

Sıradaki işler, araç olmadan yapılabilecek sırayla:

1. [ ] Bu belge paketini Egemen ve T insan gözüyle inceleyecek.
2. [ ] 3awnt prototipinin Git'e alınıp alınmayacağı kararlaştırılacak.
3. [ ] Yeni `arac/` yapısına 3awnt entegrasyonu için ayrı plan hazırlanacak veya ertelenecek.
4. [ ] `kontrol.py` temel hatasının ayrı planı hazırlanacak.
5. [ ] SUBIRU başlangıç görevleri girilecek.
6. [ ] Kalibrasyon aracı masaüstünde gerçek JSON üretecek şekilde kanıtlanacak.
7. [ ] Eylül ölçüm formu hazırlanacak; ancak ölçüm sonuçları araç görülmeden doldurulmayacak.
8. [ ] Direksiyon işareti ve motor trim dosyası çelişkileri US tarafından karara bağlanacak.

---

## 4. Tek cümlelik yol haritası

**Önce gerçeği ölç; sonra motoru güvenli ve tekrarlanabilir sür; sonra kayıtlı videoda
şeridi gör; sonra ikisini kapalı döngüde birleştir; en son görevleri tek tek ekle ve her
iddianı kayıtla kanıtla.**
