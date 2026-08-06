# -*- coding: utf-8 -*-
"""
tawnt  —  bir sayinin nereden geldigini unutmasini engelleyen kayit defteri.

ADIN HIKAYESI
    5 Agustos 2026'da bir Rus fiili, "not to <sey> against it" cumlesinin
    ortasina dusup commit'lendi, push'landi ve hicbir kontrol farketmedi.
    O fiil "защит" idi; Latin harfleriyle okuyan bir goze "3awnt" gibi
    gorunur ve Rusca'da KORUMA demek. Python bir modul adinin rakamla
    baslamasina izin vermedigi icin: tawnt.

    Yani: butun korumalari yenerek depoya giren bir kelimenin adini
    tasiyan bir koruma modulu. Etimoloji dogru, kaynagi utandiricidir.

NE ISE YARAR
    Mayis 2026'yi kaybettiren dort hatanin dordu de AYNI hatadir:
    hikayesini kaybetmis bir sayi.

      hata 1     PERSP_SRC 640x480'de olculdu, 800x680'de kullanildi.
                 Hangi karede olculdugu hicbir yerde yazmiyordu.
      hata 4/5   Dort trim 1.0'da duruyordu. "Olctum, 1.0 cikti" ile
                 "hic olcmedim" ayirt edilemiyordu.
      hata 20    DERIV_CAP piksel/SANIYE ile karsilastiriliyor ama
                 piksel/KARE gibi secilmis.

    tawnt bu dordunu de gorunur kilar. Sayilar normal sayi gibi davranir;
    yaninda kim, ne zaman, hangi birimde ve neye bagli oldugu durur.

NE ISE YARAMAZ  — bunu yukari yazmak sart
    acquire("MAX_PWM", 57, kaynak="olculdu") cagrisinin gercekten
    multimetre tutup tutmadigini BILEMEZ. Hicbir sey bilemez.
    tawnt bir KANIT sistemi degildir; bir BEYAN sistemidir.

    Kazandirdigi sey: yalan artik grep'lenebilir. Bugun config.py'de
    olculmus bir sabit ile uydurulmus bir sabit birbirinin tipatip aynisi
    gorunuyor. tawnt ile gorunmuyorlar.

    Eger bir gun tawnt.report() cikitisi "kanit" diye bir yere alintilanirsa,
    PLAN_New.md bolum 21 tekrar ediyor demektir. Rapor bir beyan listesidir.
"""

import datetime
import io

__all__ = [
    "TawntHatasi", "introduce", "acquire", "preacquire",
    "identifyRuntimeType", "IsTwinOf", "siblingIntAppr", "differenceSkew",
    "report", "sifirla",
    "declareUnexpectedSigint", "flushPWM", "evreDegisti", "pwmSerbestMi",
    "onShutdown", "kilitDurumu",
]


class TawntHatasi(Exception):
    """tawnt bir sorun buldu. Arac calismamali."""


# Kayit: ad -> alan sozlugu
_defter = {}
_ikizler = []      # (a, b) ciftleri
_zincirler = []    # [(ad, op, ad, op, ...)]

OLCULDU = "olculdu"
VARSAYILDI = "varsayildi"
DEVRALINDI = "devralindi"
_KAYNAKLAR = (OLCULDU, VARSAYILDI, DEVRALINDI)


def sifirla():
    """Testler icin. Uretimde cagrilmaz."""
    _defter.clear()
    del _ikizler[:]
    del _zincirler[:]


# ---------------------------------------------------------------------------
def introduce(ad, min=None, max=None, preferred=None, aciklama=""):
    """Bir degeri TANITIR: sinirlarini ve tercih edilenini bildirir.

    Deger henuz atanmadi. introduce yalnizca zarfi cizer; icini acquire
    doldurur. Ayirmanin sebebi, sinirlarin degerden ONCE bilinmesi
    gerektigidir — sonra konan bir sinir, konulmus degeri hicbir zaman
    sorgulamaz.
    """
    if ad in _defter:
        raise TawntHatasi("'%s' zaten tanitilmis." % ad)

    if min is not None and max is not None and min > max:
        raise TawntHatasi(
            "'%s': min (%r) max'tan (%r) buyuk." % (ad, min, max))

    if preferred is not None:
        if min is not None and preferred < min:
            raise TawntHatasi(
                "'%s': preferred (%r) min'in (%r) altinda." % (ad, preferred, min))
        if max is not None and preferred > max:
            raise TawntHatasi(
                "'%s': preferred (%r) max'i (%r) geciyor." % (ad, preferred, max))

    _defter[ad] = {
        "min": min, "max": max, "preferred": preferred,
        "aciklama": aciklama,
        "deger": None, "kaynak": None, "kim": None, "tarih": None,
        "not": None, "tip": None, "atandi": False,
    }
    return ad


def acquire(ad, deger, kaynak=VARSAYILDI, kim=None, tarih=None, notu=""):
    """Tanitilmis bir degere DEGER atar ve nereden geldigini kaydeder.

    kaynak: "olculdu" | "varsayildi" | "devralindi"
    """
    if ad not in _defter:
        raise TawntHatasi("'%s' introduce edilmeden acquire edildi." % ad)
    if kaynak not in _KAYNAKLAR:
        raise TawntHatasi(
            "'%s': kaynak %r degil, sunlardan biri olmali: %s"
            % (ad, kaynak, ", ".join(_KAYNAKLAR)))

    k = _defter[ad]

    if k["min"] is not None and deger < k["min"]:
        raise TawntHatasi(
            "'%s' = %r, alt siniri (%r) altinda." % (ad, deger, k["min"]))
    if k["max"] is not None and deger > k["max"]:
        raise TawntHatasi(
            "'%s' = %r, ust sinirini (%r) geciyor." % (ad, deger, k["max"]))

    if kaynak == OLCULDU and not tarih:
        # PLAN_New bolum 21'in kurali: olculmus bir sayi tarihsiz yazilamaz.
        raise TawntHatasi(
            "'%s' olculdu deniyor ama tarih yok. Tarihsiz olcum, olcum degildir."
            % ad)

    k.update(deger=deger, kaynak=kaynak, kim=kim, tarih=tarih,
             notu=notu, atandi=True)
    return deger


def _al(ad):
    if ad not in _defter:
        raise TawntHatasi("'%s' tanitilmamis." % ad)
    return _defter[ad]


def deger(ad):
    """Atanmis degeri dondurur."""
    k = _al(ad)
    if not k["atandi"]:
        raise TawntHatasi("'%s' henuz atanmadi." % ad)
    return k["deger"]


# ---------------------------------------------------------------------------
def identifyRuntimeType(ad, tip):
    """Bir degerin CALISMA ANI TIPINI (birimini) bildirir.

    HATA 20 ICIN VAR. controller.py'de turev piksel/SANIYE cinsinden
    hesaplaniyor ama karsilastirildigi esikler (50 ve 150) piksel/KARE
    gibi secilmis. 30 FPS'te bu, esigi 30 kat yanlis yapar ve kod
    calismaya devam eder.

    Farkli tipteki iki deger siblingIntAppr ile karsilastirilirsa hata verir.
    """
    _al(ad)["tip"] = tip
    return ad


# ---------------------------------------------------------------------------
def IsTwinOf(a, b):
    """a ve b birbiri olmadan ANLAMSIZDIR; ikisi birlikte degisir.

    HATA 1 ICIN VAR. PERSP_SRC ile olculdugu kare boyutu. Biri degisip
    digeri kalirsa dortgen sessizce anlamini yitirir — Mayis'ta tam olarak
    bu oldu ve hicbir sey sikayet etmedi.

    Hem BEYAN eder hem DURUMU dondurur: adi soru gibi okundugu icin
    `if tawnt.IsTwinOf(...)` yazan biri de dogru bir sey yapmis olur.
    Ikisinin de atanmis olup olmadigini dondurur.
    """
    _al(a); _al(b)
    if (a, b) not in _ikizler and (b, a) not in _ikizler:
        _ikizler.append((a, b))
    return _defter[a]["atandi"] and _defter[b]["atandi"]


def siblingIntAppr(*zincir):
    """Kardes degerler arasindaki SIRAYI bildirir ve dogrular.

    Kullanim:
        tawnt.siblingIntAppr("OLU_BOLGE", "<=", "MIN_HIZ",
                             "<=", "HEDEF_HIZ", "<=", "MAX_HIZ")

    BOLUM 6.1 ICIN VAR. Bolum 6, tavani %57'ye cekmeyi oneriyor ama
    BASE_SPEED 62'de kaliyor — tavanin altinda seyir hizi bir celiskidir.
    Ayrica LEGACY'de MIN_SPEED (25) zaten OLU BOLGENIN (30) altinda ve bu
    Mayis'tan beri boyle.
    """
    if len(zincir) < 3 or len(zincir) % 2 == 0:
        raise TawntHatasi(
            "siblingIntAppr: ad, op, ad, op, ad ... bicimi bekleniyor.")

    _zincirler.append(tuple(zincir))
    return _zinciri_dogrula(tuple(zincir))


_OPLAR = {
    "<":  lambda x, y: x < y,
    "<=": lambda x, y: x <= y,
    ">":  lambda x, y: x > y,
    ">=": lambda x, y: x >= y,
    "==": lambda x, y: x == y,
}


def _zinciri_dogrula(zincir):
    sorunlar = []
    for i in range(0, len(zincir) - 2, 2):
        solAd, op, sagAd = zincir[i], zincir[i + 1], zincir[i + 2]
        if op not in _OPLAR:
            raise TawntHatasi("Bilinmeyen operator: %r" % op)

        sol, sag = _al(solAd), _al(sagAd)
        if not (sol["atandi"] and sag["atandi"]):
            continue   # henuz atanmamis; preacquire bunu yakalar

        if sol["tip"] and sag["tip"] and sol["tip"] != sag["tip"]:
            raise TawntHatasi(
                "'%s' (%s) ile '%s' (%s) farkli tipte — karsilastirilamaz. "
                "Bkz. hata 20." % (solAd, sol["tip"], sagAd, sag["tip"]))

        if not _OPLAR[op](sol["deger"], sag["deger"]):
            sorunlar.append("%s (%r) %s %s (%r) DEGIL"
                            % (solAd, sol["deger"], op, sagAd, sag["deger"]))

    if sorunlar:
        raise TawntHatasi("Kardes sirasi bozuk:\n  - " + "\n  - ".join(sorunlar))
    return True


# ---------------------------------------------------------------------------
def differenceSkew(koseler, kareBoyutu, snap=1):
    """Dortgenin sag-alt kosesi kare kosesine ne kadar yakin?

    <= snap piksel  ->  koseye tasinir (piksel indeksi / koordinat karisikligi)
    >  snap piksel  ->  HATA. Duzeltilmez.

    NEDEN DUZELTILMEZ: 5 Agustos 2026'da olculdu. Mayis'ta sag-alt kose
    (640,480), kare (800,680) idi — 160 ve 200 piksel, yani %20 ve %29.
    Bunu "yakin" sayacak bir tolerans, her dagilmis dortgeni de yakalar.

    Daha kotusu: SADECE sag-alt koseyi tasimak dortgeni olceklemez,
    DEFORME eder. Alt kenar yatayken egik hale gelir (480/480 -> 480/680),
    alt kenarin ortasi 320'den 400'e kayar, ve getPerspectiveTransform bunu
    itirazsiz kabul edip yanlis bir kus bakisi uretir. Arac calisir.
    Gorunurde makul, gercekte yanlis — hata 1'in tarifi bu.

    koseler: [(x,y) x4], sira: sol-ust, sag-ust, sol-alt, sag-alt
    kareBoyutu: (genislik, yukseklik)
    Donus: (duzeltilmis_koseler, tasindi_mi)
    """
    if len(koseler) != 4:
        raise TawntHatasi("differenceSkew: dort kose bekleniyor.")

    g, y = kareBoyutu
    sx, sy = koseler[3]
    dx, dy = g - sx, y - sy

    if dx == 0 and dy == 0:
        return list(koseler), False

    if abs(dx) <= snap and abs(dy) <= snap:
        yeni = list(koseler)
        yeni[3] = (g, y)
        return yeni, True

    raise TawntHatasi(
        "Sag-alt kose (%d,%d), kare %dx%d — %d px yatay, %d px dikey uzakta "
        "(%%%.0f / %%%.0f). Bu bir yuvarlama farki degil; ya dortgen baska bir "
        "cozunurlukte olculdu ya da bilerek iceri alindi. tawnt duzeltmez: tek "
        "koseyi tasimak dortgeni olceklemez, deforme eder."
        % (sx, sy, g, y, dx, dy, 100.0 * dx / g, 100.0 * dy / y))


# ---------------------------------------------------------------------------
def preacquire(*adlar):
    """Bu degerler GERCEK olmadan devam etmez.

    Kontrol ettigi seyler:
      - tanitilmis mi
      - deger atanmis mi
      - sinirlar icinde mi
      - ikizi de atanmis mi
      - kayitli kardes zincirleri hala tutuyor mu

    Kritik degerler icin acilista cagrilir. Tavani hala tahmin olan bir
    aracin calismayi reddetmesi bir KONTROLDUR; belgeye yazilmis bir kural
    degildir.
    """
    eksik = []

    for ad in adlar:
        if ad not in _defter:
            eksik.append("%s: hic tanitilmadi (introduce yok)" % ad)
            continue

        k = _defter[ad]
        if not k["atandi"]:
            eksik.append("%s: tanitildi ama deger atanmadi" % ad)
            continue

        if k["min"] is not None and k["deger"] < k["min"]:
            eksik.append("%s = %r, alt sinir %r" % (ad, k["deger"], k["min"]))
        if k["max"] is not None and k["deger"] > k["max"]:
            eksik.append("%s = %r, ust sinir %r" % (ad, k["deger"], k["max"]))

    for a, b in _ikizler:
        for x, y in ((a, b), (b, a)):
            if x in adlar and _defter[x]["atandi"] and not _defter[y]["atandi"]:
                eksik.append("%s atanmis ama ikizi %s atanmamis — ikisi "
                             "birbiri olmadan anlamsiz (hata 1)" % (x, y))

    if eksik:
        raise TawntHatasi("preacquire basarisiz:\n  - " + "\n  - ".join(eksik))

    for z in _zincirler:
        _zinciri_dogrula(z)

    return True


# ---------------------------------------------------------------------------
def report():
    """Neyin uzerinde durdugunu yazdirir. KANIT DEGIL, BEYAN listesidir."""
    if not _defter:
        return "tawnt: defter bos."

    satirlar = []
    satirlar.append("tawnt defteri — %s"
                    % datetime.date.today().strftime("%d.%m.%Y"))
    satirlar.append("(bu bir beyan listesidir, kanit degil)")
    satirlar.append("")
    satirlar.append("%-10s %-22s %-12s %-10s %s"
                    % ("KAYNAK", "AD", "DEGER", "TIP", "NOT"))
    satirlar.append("-" * 78)

    sira = {OLCULDU: 0, DEVRALINDI: 1, VARSAYILDI: 2, None: 3}
    for ad in sorted(_defter, key=lambda a: (sira[_defter[a]["kaynak"]], a)):
        k = _defter[ad]
        satirlar.append("%-10s %-22s %-12s %-10s %s" % (
            (k["kaynak"] or "ATANMADI").upper(),
            ad,
            repr(k["deger"]) if k["atandi"] else "-",
            k["tip"] or "-",
            (k["tarih"] or "") + (" " + (k.get("notu") or "")).rstrip(),
        ))

    varsayilan = [a for a in _defter if _defter[a]["kaynak"] != OLCULDU]
    satirlar.append("")
    satirlar.append("Olculmemis deger sayisi: %d / %d"
                    % (len(varsayilan), len(_defter)))
    if varsayilan:
        satirlar.append("Bunlar tahmin: " + ", ".join(sorted(varsayilan)))

    return "\n".join(satirlar)


# ===========================================================================
# GUVENLIK — motorlar
#
# BU BOLUMDE TEK KURAL VAR:
#   Kilitlenmis bir kapatmayi HICBIR SEY geri alamaz. Yeniden baslatma disinda.
#
# NEDEN: CLAUDE.md diyor ki "motorlar acilista ve HER yakalanmamis hatada
# kapali olmali, onceki guvenli durum asla varsayilmamali". Iptal edilebilir
# bir kapatma tam olarak onceki durumu varsayar.
#
# Ve bir dizgeyle ("DEVRUN" gibi) motorlari geri acan mekanizma, CLAUDE.md'nin
# reddedilecek fikir ornegi olarak saydigi GG/EZ kisayolunun ta kendisidir.
# Yarisi baslatan bir kisayol kotu; ariza sirasinda motorlari geri veren bir
# dizge daha kotu.
#
# BU YUZDEN IKI AYRI SEY:
#   declareUnexpectedSigint()  ->  KILIT. Tek yonlu. Yalnizca restart acar.
#   flushPWM()                 ->  SUSTURMA. Kapsamli, evre sonunda biter.
#
# Ve susturma KILIDI ACAMAZ. Asagidaki testte kanitlanmistir.
# ===========================================================================

_kilit = None          # None = serbest;  dict = kilitli (tek yonlu)
_susturma = None       # None = serbest;  dict = bu evre icin susturulmus
_kapatma_geri = []     # motor katmaninin kaydettigi geri cagrilar
_gunluk_yolu = "tawnt_guvenlik.log"


def onShutdown(fn):
    """Motor katmani kapatma islevini BURAYA kaydeder.

    tawnt gpiozero'yu IMPORT ETMEZ ve etmemeli: o zaman kalibrasyon araci,
    Windows ve klip testleri tawnt'i import edemezdi. LEGACY bu sorunu
    import korumasiyla cozmustu; burada cozum daha basit — donanimi tawnt
    hic tanimaz, sadece "kapat" diye seslenir.
    """
    if fn not in _kapatma_geri:
        _kapatma_geri.append(fn)
    return fn


def _gunluge_yaz(satir):
    try:
        with io.open(_gunluk_yolu, "a", encoding="utf-8") as f:
            f.write(satir + "\n")
    except Exception:
        # Gunluge yazamamak, motorlari kapatmayi ENGELLEMEZ. Sira onemli:
        # once donanim, sonra kayit.
        pass


def declareUnexpectedSigint(sebep, ayrinti=""):
    """Beklenmeyen bir sey oldu: her seyi kapat, kilitle, kaydet.

    TEK YONLUDUR. Bundan sonra pwmSerbestMi() surekli False doner ve bunu
    degistirmenin tek yolu programi yeniden baslatmaktir.

    NOT — ADI HAKKINDA: "Sigint" Ctrl+C sinyalinin adidir, ama bu islev
    her turlu beklenmeyen durum icin. signal.SIGINT'i BAGLAMAZ; onu
    main.py ayrica baglamali ve buraya yonlendirmeli. Ad yaniltmasin.
    """
    global _kilit
    if _kilit is None:
        _kilit = {
            "sebep": sebep,
            "ayrinti": ayrinti,
            "zaman": datetime.datetime.now().isoformat(timespec="seconds"),
        }

    # Once donanim.
    for fn in _kapatma_geri:
        try:
            fn()
        except Exception as e:
            _gunluge_yaz("[!] kapatma geri cagrisi patladi: %r" % (e,))

    _gunluge_yaz("%s  KILIT  %s  %s" % (_kilit["zaman"], sebep, ayrinti))
    return _kilit


def flushPWM(sebep, evre=None):
    """PWM cikisini SUSTURUR — kapsamli, gecici.

    Kilit DEGILDIR. Evre degisince (evreDegisti) kendiliginden biter.
    Kullanim ornegi: bir gorev bitti, sonraki baslayana kadar motor istemiyoruz.

    Kilitli durumda cagrilirsa hicbir sey degismez — zaten kapali.
    """
    global _susturma
    _susturma = {"sebep": sebep, "evre": evre}
    for fn in _kapatma_geri:
        try:
            fn()
        except Exception as e:
            _gunluge_yaz("[!] susturma geri cagrisi patladi: %r" % (e,))
    _gunluge_yaz("%s  SUSTUR (%s)  %s"
                 % (datetime.datetime.now().isoformat(timespec="seconds"),
                    evre, sebep))
    return True


def evreDegisti(yeniEvre):
    """Yeni evre basladi: SUSTURMA kalkar. KILIT KALKMAZ.

    Bu ayrimin tamami budur. Bir gorev arasi susturma normaldir ve kendi
    kendine biter. Bir ariza kilidi bitmez.
    """
    global _susturma
    if _susturma is not None and _susturma.get("evre") != yeniEvre:
        _susturma = None
    return pwmSerbestMi()


def pwmSerbestMi():
    """Motor katmaninin SORDUGU tek soru. Baska yerden karar verilmez."""
    return _kilit is None and _susturma is None


def kilitDurumu():
    """Kilit varsa sozlugu, yoksa None. Ozet ekranlari icin."""
    return dict(_kilit) if _kilit else None
