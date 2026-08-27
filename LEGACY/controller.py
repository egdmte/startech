# =============================================================================
# controller.py  —  PD direksiyon denetleyicisi — OPTIMIZE EDİLMİŞ
#                   + Hız-Viraj Koordinasyonu
#                   + Dinamik Kazanç (Büyük Hatalar)
#                   + Ölü Bölge Telafisi
# =============================================================================
import math
import time

import numpy as np

from config import (
    KP, KD, KI, INTEGRAL_MAX, BASE_SPEED, MIN_SPEED, MAX_SPEED, K_SPEED,
    KP_LARGE_ERROR_MULT, KD_LARGE_ERROR_MULT,
    DERIV_CAP, CROSSING_KD_MULT,
    DERIV_SLOWDOWN_THRESHOLD, DERIV_MEDIUM_THRESHOLD,
    DEAD_ZONE_MIN_PWM,
)

# Kaç ardışık kayıp kare sonra tamamen duralım
_LOST_FRAMES_STOP = 30


class PDController:
    """Yanal piksel hatasını diferansiyel tekerlek hızlarına dönüştüren PD denetleyici.

    hata > 0  →  araç şerit merkezinin SAĞında  →  sola dön
    hata < 0  →  araç şerit merkezinin SOLunda  →  sağa dön
    """

    def __init__(self):
        self.prev_error:  float = 0.0
        self.prev_time:   float = time.time()
        self.lost_frames: int   = 0
        self.integral:    float = 0.0
        self._has_seen_lane: bool = False

        # Tani sayaclari — eklendi 5 Agustos 2026. Davranisi DEGISTIRMEZ,
        # yalnizca sayar. Sebep: 20.7 deneyi "arac duzeldi mi" diye soruyor,
        # ama hangi dalin kac kez calistigini bilmeden cevap yorumlanamaz.
        self.tani = {"kare": 0, "yavaslama": 0, "orta": 0,
                     "deriv_doydu": 0, "pivot": 0, "kayip": 0}

    # ------------------------------------------------------------------
    def compute(self, error) -> tuple:
        """(sol_hız, sağ_hız) tuple'ı döndürür, her biri yüzde [0, 100].

        Şerit görünmüyorsa error=None geçin; araç yavaşlar ve
        son direksiyon yönünü korur.
        
        OPTIMIZASYONLAR:
        - Hız-Viraj Koordinasyonu: Derivative bazlı yavaşlama
        - Dinamik Kazanç: Büyük hatalar için KP/KD çarpanı
        - Ölü Bölge Telafisi: PWM sinyalini offset et
        """
        now = time.time()
        dt = max(now - self.prev_time, 1e-3)

        if error is None:
            self.lost_frames += 1
            if not self._has_seen_lane:
                self.tani["kare"] += 1
                self.tani["kayip"] += 1
                self.prev_time = now
                return 0.0, 0.0
            error = self.prev_error * 0.8   # giderek düzleşir
            error_for_integration = None    # integratörü dondur
            derivative = 0.0                # uydurma girdinin turevi yoktur
        else:
            self.lost_frames = 0
            self._has_seen_lane = True
            error_for_integration = error
            # Esikler piksel/kare cinsindedir. FPS'e bolmek, kamera gurultusunu
            # 30 kat buyutup normal serit takibini pivot komutuna ceviriyordu.
            derivative = error - self.prev_error

        # Kareler arasi hata degisimi + cap (salınım önleme)
        derivative = float(np.clip(derivative, -DERIV_CAP, DERIV_CAP))

        # İntegral + anti-windup (yalnızca güvenilir error'da biriktir)
        if error_for_integration is not None:
            self.integral += error_for_integration * dt
            self.integral = float(np.clip(self.integral, -INTEGRAL_MAX, INTEGRAL_MAX))

        # Hız-Viraj Koordinasyonu: Derivative bazlı hız kontrol
        # Hem düzde salınım hem de keskin viraj girişinde türev büyüdüğünde yavaşla.
        speed = float(BASE_SPEED - K_SPEED * abs(error))
        if error_for_integration is None:
            speed = MIN_SPEED

        self.tani["kare"] += 1
        # DIKKAT: bu noktada 'error' artik None OLAMAZ — yukarida
        # prev_error*0.8 ile degistirildi. Kayip kareyi tespit etmenin dogru
        # yolu error_for_integration'dir. (Ilk yazimda bunu kacirdim ve sayac
        # her zaman 0 gosterdi; testte yakalandi.)
        if error_for_integration is None:
            self.tani["kayip"] += 1
        if abs(derivative) >= DERIV_CAP:
            self.tani["deriv_doydu"] += 1

        if abs(derivative) > DERIV_SLOWDOWN_THRESHOLD:
            speed = MIN_SPEED
            self.tani["yavaslama"] += 1
        elif abs(derivative) > DERIV_MEDIUM_THRESHOLD:
            speed = min(speed, BASE_SPEED - 10)
            self.tani["orta"] += 1

        speed = float(np.clip(speed, MIN_SPEED, MAX_SPEED))

        # Dinamik Kazanç: Büyük hatalar için KP/KD çarpanı
        kp_eff = KP
        kd_eff = KD

        if abs(error) > 30:
            kp_eff *= KP_LARGE_ERROR_MULT
            kd_eff *= KD_LARGE_ERROR_MULT

        # Crossing (viraj) için KD artırma. Ayni esigi tek kaynaktan kullan.
        if abs(derivative) > DERIV_SLOWDOWN_THRESHOLD:
            kd_eff *= CROSSING_KD_MULT

        # Direksiyon düzeltme hesabı (PID)
        correction = kp_eff * error + KI * self.integral + kd_eff * derivative

        if self.lost_frames >= _LOST_FRAMES_STOP:
            speed = 0.0
            correction = 0.0
            self.integral = 0.0   # tam durunca biriken bias'i temizle

        # Serit takip denetleyicisi pivot yapmaz. |correction| > speed iki
        # tekeri zit yone surup Mayis kosusundaki spirali uretiyordu. Bir teker
        # sifira inebilir; geri vitese gecemez.
        requested_correction = correction
        correction = float(np.clip(correction, -speed, speed))
        if correction != requested_correction:
            self.tani["pivot"] += 1

        # Ham tekerlek hızları (clip + ölü bölge telafisi pair olarak yapılır)
        left_raw  = speed + correction
        right_raw = speed - correction

        # Ölü Bölge Telafisi: common-mode'u kaldır, diferansiyeli koru
        left, right = self._apply_dead_zone_pair(left_raw, right_raw)

        self.prev_error = error
        self.prev_time = now

        return left, right

    # ------------------------------------------------------------------
    def tani_raporu(self) -> None:
        """Hangi dalin ne siklikta calistigini yazdirir. Eklendi 5 Agustos 2026.

        Neden: PLAN_New.md 20.7 "araci surun ve raporu okuyun" diyor. Mevcut
        rapor hatanin ne kadar buyuk oldugunu soyluyor ama denetleyicinin NE
        YAPTIGINI soylemiyor. Asagidaki dort sayi arasindaki fark, "kalibrasyon
        yanlisti" ile "kontrol yasasi kendi kendini bogdu" arasindaki farktir.
        """
        t = self.tani
        n = max(t["kare"], 1)
        def y(k):
            return "%6d  (%5.1f %%)" % (t[k], 100.0 * t[k] / n)
        print("")
        print("======================================")
        print("       DENETLEYICI TANI RAPORU        ")
        print("======================================")
        print("  Toplam kare      : %6d" % t["kare"])
        print("  Serit kayip      : %s" % y("kayip"))
        print("  MIN_SPEED'e dustu: %s" % y("yavaslama"))
        print("  Orta yavaslama   : %s" % y("orta"))
        print("  Turev DOYDU      : %s" % y("deriv_doydu"))
        print("  Engellenen pivot : %s" % y("pivot"))
        print("======================================")
        print("  Nasil okunur:")
        print("   - 'MIN_SPEED'e dustu' yuksekse (yuzde 20 ustu), arac neredeyse")
        print("     hep %d hizinda demektir; BASE_SPEED=%d hic kullanilmiyor." % (
              MIN_SPEED, BASE_SPEED))
        print("   - 'Engellenen pivot' sifirdan buyukse eski denetleyici")
        print("     tekerleri zit yone surmeye calisacakti. Komut tek teker")
        print("     sifira inecek sekilde sinirlandi.")
        print("   - Turev piksel/KARE cinsindendir. Bir karede %d px degisim"
              % DERIV_SLOWDOWN_THRESHOLD)
        print("     MIN_SPEED'i tetikler.")
        print("======================================")
        print("")

    # ------------------------------------------------------------------
    def _apply_dead_zone_pair(self, left: float, right: float) -> tuple:
        """İki tekerleğe birlikte ölü bölge telafisi.

        Eski sürüm her tekeri bağımsız ±DEAD_ZONE_MIN_PWM'e çekiyordu →
        küçük diferansiyel komutlar (ör. 20 / 10) ikisi de 30/30'a yuvarlanıp
        bias yok oluyordu. Bu sürüm common-mode bileşeni kaldırır,
        diferansiyeli (yön komutu) bozmadan korur.

        Aynı işaretli tekerleklerde common+diff ayrıştırması; karşıt işaretli
        (pivot) durumda her tekeri bağımsız kaldırır.
        """
        # İkisi de tam sıfırsa dokunma
        if left == 0.0 and right == 0.0:
            return 0.0, 0.0
        # Denetleyici pivotu sinirlarken bir tekeri bilerek sifira indirir.
        # Olu bolge telafisi duran tekeri yeniden calistirmamali.
        if left == 0.0:
            right_out = (math.copysign(DEAD_ZONE_MIN_PWM, right)
                         if abs(right) < DEAD_ZONE_MIN_PWM else right)
            return 0.0, float(np.clip(right_out, -MAX_SPEED, MAX_SPEED))
        if right == 0.0:
            left_out = (math.copysign(DEAD_ZONE_MIN_PWM, left)
                        if abs(left) < DEAD_ZONE_MIN_PWM else left)
            return float(np.clip(left_out, -MAX_SPEED, MAX_SPEED)), 0.0

        same_sign = (left >= 0 and right >= 0) or (left <= 0 and right <= 0)

        if same_sign:
            common = (left + right) / 2.0
            diff   = (left - right) / 2.0
            if common != 0.0 and abs(common) < DEAD_ZONE_MIN_PWM:
                common = math.copysign(DEAD_ZONE_MIN_PWM, common)
            left_out  = common + diff
            right_out = common - diff
            # İkinci geçiş: ortak-mod yükseltmesi sonrasında ayrı tekerlekler
            # hâlâ ölü bölgedeyse bağımsız kaldır (diferansiyel yön korunur).
            if 0 < abs(left_out) < DEAD_ZONE_MIN_PWM:
                left_out = math.copysign(DEAD_ZONE_MIN_PWM, left_out)
            if 0 < abs(right_out) < DEAD_ZONE_MIN_PWM:
                right_out = math.copysign(DEAD_ZONE_MIN_PWM, right_out)
        else:
            # Pivot — tekerlekler ters yönde, bağımsız kaldır
            left_out  = (math.copysign(DEAD_ZONE_MIN_PWM, left)
                         if 0 < abs(left) < DEAD_ZONE_MIN_PWM else left)
            right_out = (math.copysign(DEAD_ZONE_MIN_PWM, right)
                         if 0 < abs(right) < DEAD_ZONE_MIN_PWM else right)

        return (float(np.clip(left_out,  -MAX_SPEED, MAX_SPEED)),
                float(np.clip(right_out, -MAX_SPEED, MAX_SPEED)))

    # ------------------------------------------------------------------
    def reset(self) -> None:
        """İç durumu sıfırla (örn. bir duraklamadan sonra)."""
        self.prev_error  = 0.0
        self.prev_time   = time.time()
        self.lost_frames = 0
        self.integral    = 0.0
        self._has_seen_lane = False
        # NOT: self.tani sayaclari BILEREK sifirlanmiyor. reset() bir kosu
        # icinde birkac kez cagrilabilir; tani sayilari ise TUM kosuyu
        # ozetlemeli, yoksa 20.7 raporu son parcayi anlatir.
