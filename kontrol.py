#!/usr/bin/env python3
# =============================================================================
# kontrol.py  —  belgelerdeki iddiaları koda karşı doğrular
#
# NEDEN VAR: §21. Dört belge, var olmayan dokuz sabit, beş metot, on dosya adı
# ve ölçülmemiş her metriği güvenle iddia etti. Hepsi tek bir grep ile
# yakalanabilirdi. CLAUDE.md zaten "belgede adı geçen her sabit, metot veya
# dosya grep ile bulunabilmelidir" diyor — bu dosya o kuralı hatırlanacak bir
# şey olmaktan çıkarıp çalışan bir kontrole dönüştürür.
#
# Kullanım:
#     python kontrol.py            hepsini çalıştır
#     python kontrol.py --liste    hangi kontroller var
#
# Çıkış kodu 0 = temiz, 1 = en az bir kontrol düştü. Commit kancasına uygun.
# =============================================================================

import os
import re
import sys

KOK = os.path.dirname(os.path.abspath(__file__))
IZIN_DOSYASI = os.path.join(KOK, "kontrol-izin.txt")

BELGELER = ["PLAN_New.md", "HATA_DEFTERI.md", "CLAUDE.md"]


def belge_yolu(ad):
    """
    Belgeyi depoda NEREDE olursa olsun bulur.

    Neden boyle: 5 Agustos'ta belgeler Markdown/ altina tasindi ve bu betik
    onlari kokte aradi. Bulamadi, hicbir sey kontrol etmedi, ve dort kontrolun
    ucu TAMAM dedi. Bulunamayan bir belge artik BASARISIZLIKTIR — "bakmadim"
    demek olan bir yesil, en kotu ciktidir.
    """
    for kok, klasorler, dosyalar in os.walk(KOK):
        klasorler[:] = [k for k in klasorler if k not in ATLA_KLASOR]
        if ad in dosyalar:
            return os.path.join(kok, ad)
    return None


def belgeler_eksik():
    """Beklenen belgelerden bulunamayanlar."""
    return [a for a in BELGELER if belge_yolu(a) is None]

# Taranacak kaynak dosyalar — belgede adı geçen şeyin burada bulunması beklenir.
KAYNAK_UZANTILAR = (".py", ".cs", ".js", ".json", ".sh", ".service", ".txt", ".md")
ATLA_KLASOR = {".git", ".venv", "venv", "node_modules", "__pycache__",
               "obj", "bin", ".vs", "packages"}


# ---------------------------------------------------------------------------
def kaynak_metni():
    """Depodaki bütün metni tek bir dizge olarak toplar."""
    parcalar = []
    for kok, klasorler, dosyalar in os.walk(KOK):
        klasorler[:] = [k for k in klasorler if k not in ATLA_KLASOR]
        for d in dosyalar:
            if d.endswith(KAYNAK_UZANTILAR):
                try:
                    with open(os.path.join(kok, d), encoding="utf-8",
                              errors="ignore") as f:
                        parcalar.append(f.read())
                except OSError:
                    pass
    return "\n".join(parcalar)


def dosya_adlari():
    """Depodaki bütün dosya adları."""
    adlar = set()
    for kok, klasorler, dosyalar in os.walk(KOK):
        klasorler[:] = [k for k in klasorler if k not in ATLA_KLASOR]
        adlar.update(dosyalar)
    return adlar


def izinliler():
    """
    Henüz yazılmamış ama planlanan şeyler. İki kaynaktan gelir:
      1. PLAN_New.md §4'teki dosya listesi — planın kendi listesi
      2. kontrol-izin.txt — elle eklenenler, her satırda bir ad
    """
    izin = set()

    plan = belge_yolu("PLAN_New.md")
    if plan:
        with open(plan, encoding="utf-8") as f:
            metin = f.read()
        # §4'teki ilk kod bloğu dosya yerleşimidir
        m = re.search(r"^## 4\. .*?```(.*?)```", metin, re.S | re.M)
        if m:
            for satir in m.group(1).splitlines():
                for ad in re.findall(r"[\w./-]+\.\w+", satir):
                    izin.add(os.path.basename(ad))

    if os.path.exists(IZIN_DOSYASI):
        with open(IZIN_DOSYASI, encoding="utf-8") as f:
            for satir in f:
                satir = satir.split("#")[0].strip()
                if satir and not satir.startswith("SATIR:"):
                    izin.add(satir)
    return izin


def satir_muafiyetleri():
    """
    'SATIR: ...' ile baslayan girisler, o metni iceren HERHANGI bir satiri
    muaf tutar. Satir numarasi degil metin kullaniyoruz — belge duzenlendiginde
    numaralar kayar, metin kalir.
    """
    muaf = []
    if os.path.exists(IZIN_DOSYASI):
        with open(IZIN_DOSYASI, encoding="utf-8") as f:
            for satir in f:
                satir = satir.split("#")[0].strip()
                if satir.startswith("SATIR:"):
                    muaf.append(satir[6:].strip())
    return muaf


# ---------------------------------------------------------------------------
def kontrol_dosya_adlari(kaynak, adlar, izin):
    """Belgelerde adı geçen her dosya ya vardır ya da planlanmıştır."""
    bulgular = []
    kalip = re.compile(r"\b([\w-]+\.(?:py|cs|js|json|md|txt|sh|service|csproj|html))\b")

    for belge in BELGELER:
        yol = belge_yolu(belge)
        if yol is None:
            continue
        with open(yol, encoding="utf-8") as f:
            for no, satir in enumerate(f, 1):
                for ad in kalip.findall(satir):
                    if ad in adlar or ad in izin:
                        continue
                    bulgular.append("%s:%d  %s" % (belge, no, ad))
    return bulgular


def kontrol_sabitler(kaynak, izin):
    """
    Belgelerde geçen BUYUK_HARFLI_SABIT adları kodda bulunmalı.
    §21'in tam olarak yakaladığı hata sınıfı: ADAPTIVE_HSV_ENABLED gibi
    hiç var olmamış sabitler.
    """
    bulgular = []
    kalip = re.compile(r"\b([A-Z][A-Z0-9]*(?:_[A-Z0-9]+){1,})\b")
    # Belge dilinde geçen ama sabit olmayan şeyler
    yoksay = {"MEB", "HSV", "PWM", "GPIO", "CLAHE", "JSON", "HTTP", "HTTPS",
              "SUBIRU", "LEGACY", "PLAN", "UYARI", "DIKKAT", "STOP",
              "GG", "EZ", "RC", "SD", "USB", "CSI", "RTC", "NAT", "VPS",
              "API", "URL", "UTF", "SHA", "R2", "PD", "CV", "ML", "OK"}

    for belge in BELGELER:
        yol = belge_yolu(belge)
        if yol is None:
            continue
        with open(yol, encoding="utf-8") as f:
            for no, satir in enumerate(f, 1):
                for ad in kalip.findall(satir):
                    if ad in yoksay or ad in izin:
                        continue
                    if re.search(r"\b%s\b" % re.escape(ad), kaynak) and \
                       kaynak.count(ad) > satir.count(ad):
                        continue
                    bulgular.append("%s:%d  %s" % (belge, no, ad))
    return bulgular


def kontrol_bolum_atiflari():
    """
    PLAN_New.md içindeki §N ve "section N" atıfları gerçek başlıklara gitmeli.
    Bölümler yeniden numaralandığında sessizce bozulur — 2 Ağustos'ta üç kez oldu.
    """
    yol = belge_yolu("PLAN_New.md")
    if yol is None:
        return ["PLAN_New.md bulunamadi"]
    with open(yol, encoding="utf-8") as f:
        metin = f.read()

    basliklar = set()
    for m in re.finditer(r"^#{2,3} (\d+(?:\.\d+[a-z]?)?)\.", metin, re.M):
        basliklar.add(m.group(1))

    bulgular = []
    for no, satir in enumerate(metin.splitlines(), 1):
        for atif in re.findall(r"§(\d+(?:\.\d+[a-z]?)?)", satir):
            kok_no = atif.split(".")[0]
            if atif not in basliklar and kok_no not in basliklar:
                bulgular.append("PLAN_New.md:%d  §%s" % (no, atif))
        for atif in re.findall(r"[Ss]ection (\d+)", satir):
            if atif not in basliklar:
                bulgular.append("PLAN_New.md:%d  section %s" % (no, atif))
    return bulgular


def kontrol_olcumler():
    """
    CLAUDE.md: bir performans sayısı ancak gerçek bir koşudan geldiyse ve
    yanında o koşunun tarihi varsa yazılabilir.

    FPS / px / yüzde içeren satırlarda ya bir yıl ya da tahmin olduğunu
    söyleyen bir kelime aranır.
    """
    # Sayi ile birim ARASINDA bosluk sart.
    #
    # Neden: 5 Agustos'ta belgelere inline SVG semalari eklendi. CSS'te
    # "font: 12px ..." yazar ve bu bir performans iddiasi DEGILDIR — bir yazi
    # boyutudur. Bosluksuz "12px" bir CSS uzunlugu, bosluklu "15 px" ise
    # insanin yazdigi bir cumledir. §21'de uydurulan iddialar ("+-15 px",
    # "28-30 FPS") bosluklu yazilmisti, yani gercek hata sinifi hala yakalanir.
    #
    # Bu kurali gevsetmek yerine daraltiyoruz: 22 yanlis pozitif, kontrolun
    # tamamini gormezden gelinir hale getirir — ki en tehlikeli sonuc odur.
    kalip = re.compile(r"\b\d+(?:[.,]\d+)?\s+(fps|FPS|px)\b")
    # Tahmin olduğunu söyleyen ifadeler, VE bir sayının uydurma olduğunu
    # söyleyen ifadeler. "Bu sayı ölçülmedi" cümlesi, ölçülmemiş bir sayı
    # iddiası değildir — uydurmanın kaydı uydurma değildir (§21).
    tahmin = re.compile(r"(tahmin|hedef|beklenen|olmalı|civar|yaklaşık|~|"
                        r"uydur|iddia|ölçülmedi|asla ölçül|"
                        r"expect|target|should|about|roughly|estimate|"
                        r"never (?:measured|taken|run)|invented|fabricat|"
                        r"claimed|asserted|presented as)", re.I)
    yil = re.compile(r"\b20\d\d\b")

    muaf = satir_muafiyetleri()
    bulgular = []
    for belge in BELGELER:
        yol = belge_yolu(belge)
        if yol is None:
            continue
        with open(yol, encoding="utf-8") as f:
            satirlar = f.read().splitlines()

        for i, satir in enumerate(satirlar):
            if not kalip.search(satir):
                continue
            if any(m and m in satir for m in muaf):
                continue
            # Baglami da bak: "Uydurulmus olcumler:" basligi altindaki madde
            # isaretleri kendi baslarina bir iddia degildir. Insanlar boyle yazar.
            baglam = "\n".join(satirlar[max(0, i - 3):i + 2])
            if yil.search(baglam) or tahmin.search(baglam):
                continue
            bulgular.append("%s:%d  %s" % (belge, i + 1, satir.strip()[:90]))
    return bulgular


# ---------------------------------------------------------------------------
KONTROLLER = [
    ("Beklenen belgeler bulunabiliyor mu",
     lambda k, a, i: ["BULUNAMADI: " + b for b in belgeler_eksik()]),
    ("Belgede adı geçen dosyalar var mı",
     lambda k, a, i: kontrol_dosya_adlari(k, a, i)),
    ("Belgede adı geçen sabitler kodda var mı",
     lambda k, a, i: kontrol_sabitler(k, i)),
    ("PLAN_New.md bölüm atıfları geçerli mi",
     lambda k, a, i: kontrol_bolum_atiflari()),
    ("Performans sayıları tarih taşıyor mu",
     lambda k, a, i: kontrol_olcumler()),
]


def main():
    if "--liste" in sys.argv:
        for ad, _ in KONTROLLER:
            print(" -", ad)
        return 0

    kaynak = kaynak_metni()
    adlar = dosya_adlari()
    izin = izinliler()

    dusen = 0
    for ad, islev in KONTROLLER:
        bulgular = islev(kaynak, adlar, izin)
        if bulgular:
            dusen += 1
            print("\n[DUSTU] %s  (%d)" % (ad, len(bulgular)))
            for b in bulgular[:20]:
                print("        " + b)
            if len(bulgular) > 20:
                print("        ... ve %d tane daha" % (len(bulgular) - 20))
        else:
            print("[TAMAM] %s" % ad)

    print("")
    if dusen:
        print("%d kontrol dustu. Yanlis pozitifse kontrol-izin.txt'ye ekleyin."
              % dusen)
        return 1
    print("Butun kontroller temiz.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
