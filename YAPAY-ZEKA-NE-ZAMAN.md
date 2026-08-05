# Yapay zekâyı ne zaman kullanmalı, ne zaman kullanmamalı

Bu dosya bir kural listesi değil, tek bir soruya indirgenebilir:

> ## **Cevap yanlışsa, bunu nasıl anlarım?**

Cevabı varsa — derleyici, bir test, bir multimetre, dört satırlık bir betik — soru
güvenlidir. Cevabı yoksa, dikkatli ol; §21 tam olarak orada oldu.

---

## 1. Hiçbir yere gitmeyecekler

Model kalitesinden bağımsız. Ücretli, ücretsiz, yerel, fark etmez.

- `sunucu.json`, R2 anahtarları, paylaşılan şifre
- Tam isimler, okul adı, ilçe
- Gerçek kullanıcı verisi (ana Vercel uygulamasından hiçbir şey)

`.gitignore` bir dosyayı **okumayı** engellemez. Claude Code gibi araçlar dosyaları
kendiliğinden açar; onları `sunucu.json`'un bulunduğu klasörde çalıştırma.

---

## 2. Kendin yap — yapay zekâ gereksiz

**Bir makine zaten kontrol ediyorsa.** Derliyor mu, test geçiyor mu, `kontrol.py` temiz mi.
Bunları sormanın anlamı yok; çalıştır, gör.

**Bir ölçüm cevaplıyorsa.** Kaç hücre var, motor uçlarında kaç volt var, hangi kablo
nereye gidiyor. Yapay zekâ bunları bilemez ve tahmin ederse zarar verir. Bugün "3S ise
şu, 2S ise bu" diye geçen onlarca mesaj, dört pili saymamış olmanın bedeliydi.

**Dört satırlık bir betikle çözülüyorsa.** 3 Ağustos'ta iki gerçek hata bu şekilde
bulundu — soruyu sormak yapay zekâdandı, cevabı bulan betik senindi.

**Kodun ne yaptığını anlamak.** Bunu dışarıya vermek, kendi aracını açıklayamaz hale
gelmenin yoludur — ve kılavuz §2.2 açıklayabilmeyi şart koşuyor. Sor, ama cevabı
sen doğrula.

---

## 3. Yapay zekâ kullan

**Çalıştırarak kontrol edemediğin şeyler.** Neden Mayıs'ta kaybettik, bu tasarım doğru mu,
bu hata neye mal oluyor. Yanlış cevabın doğru göründüğü yer burasıdır — ve iyi model
farkını da burada yaratır.

**Mekanik kod.** JSON okuyucu, kaydedici, form, LED sürücüsü. Derleyici zaten hakem.
Kim yazdığı önemsiz.

**Anlamadığın bir şeyi açıklatmak** — ama §4'teki kontrolle birlikte.

**Yazdığın bir şeye ikinci göz.** "Bunda ne yanlış olabilir" sorusu ucuzdur.

---

## 4. Cevabı aldıktan sonra — dört kontrol

**Tahmin ettir, sonra çalıştır.** "Bu fonksiyona 50 verirsem ne döner?" Sonra çalıştır.
Uyuşmuyorsa ya kod ya açıklama yanlış; ikisi de değerli bilgi.

**Satırı numarasıyla istet.** "Denetleyici integrali donduruyor" değil —
`controller.py:57`, yapıştırılmış. Sonra dosyayı aç. Açıklama uydurulabilir, satır
numarası dört saniyede kontrol edilir.

**"Bunu ne çürütür?" diye sor.** Gerçek bir bulgunun bir testi vardır. Uydurma olanın
cevabı bulanıklaşır, çünkü altında bir şey yoktur.

**Aynı soruyu iki farklı oturumda sor.** Gerçek bulgular sabittir. Uydurmalar kayar —
başka sabit, başka dosya adı, aynı özgüven.

---

## 5. Uyarı işaretleri

Bunlar okurken hata gibi görünmez. Cevap gibi görünür.

| İşaret | Ne demek |
|---|---|
| Bir dosya, sabit veya metot adı verdi | `grep` at. §21'in tamamı bu |
| Bir sayı verdi | Nereden geldiğini sor. Aritmetiği yeniden kuramıyorsan süstür |
| Hiç "bilmiyorum" demiyor | Bir yerde tahmin ediyor demektir |
| Her şeye katılıyor | Değerlendirmiyor, tekrarlıyor |
| **Belge hakkında değil, yazarlar hakkında konuşuyor** | **İncelemedi. Övgü, incelemenin yerine geçmez — sayfadan alıntı yapmaya başladığı yere kadar okumamıştır** |
| Zaten karara bağlanmış bir şeyi yeniden açıyor | Bağlamı takip etmiyor — o bağlamla ilgili söylediği her şey şüpheli |
| Kesin konuşuyor ("imkânsız", "asla") | Genelde "bir yolu var ama ben bilmiyorum" demektir |

---

## 6. Sormadan önce

**Soru keskin mi?** "Şerit takibi nasıl yapılır" pahalı ve işe yaramaz.
"`lane.py:148`'de `error` neden `mid - near_c`?" ucuz ve kesin.

**Bağlamı verdim mi?** Sıfırdan başlayan her oturum, seni yakalamakla bütçe harcar.
`SIRA.md` ve §0.0 bunun için var — sürüklenmeyi önlemek kadar, parayı da korurlar.

**Bunu kendim çözebilir miyim?** Genelde evet, gerçekler için. Genelde hayır, tasarım için.

---

## Tek cümle

Yapay zekâyı **kontrol edebildiğin** işlerde rahatça, **kontrol edemediğin** işlerde
dikkatle kullan — ve hangisi olduğunu, sormadan önce bil.
