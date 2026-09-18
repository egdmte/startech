# =============================================================================
# controller.py  —  PD direksiyon denetleyicisi — OPTIMIZE EDİLMİŞ
#                   + Hız-Viraj Koordinasyonu
#                   + Dinamik Kazanç (Büyük Hatalar)
#                   + Ölü Bölge Telafisi
# =============================================================================
import time

import numpy as np

from config import (
    KP, KD, BASE_SPEED, MIN_SPEED, MAX_SPEED, K_SPEED,
    KP_LARGE_ERROR_MULT, KD_LARGE_ERROR_MULT,
    DERIV_CAP, CROSSING_KD_MULT,
    DERIV_SLOWDOWN_THRESHOLD, DERIV_MEDIUM_THRESHOLD,
    LEFT_TRIM_LOW, LEFT_TRIM_HIGH,
    RIGHT_TRIM_LOW, RIGHT_TRIM_HIGH,
    DEAD_ZONE_PERCENT, DEAD_ZONE_MIN_PWM,
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
        dt  = max(now - self.prev_time, 1e-3)

        if error is None:
            self.lost_frames += 1
            error = self.prev_error * 0.8   # giderek düzleşir
        else:
            self.lost_frames = 0

        # Derivative hesabı + Cap (salınım önleme)
        derivative = (error - self.prev_error) / dt
        derivative = float(np.clip(derivative, -DERIV_CAP, DERIV_CAP))

        # Hız-Viraj Koordinasyonu: Derivative bazlı hız kontrol
        speed = float(BASE_SPEED - K_SPEED * abs(error))
        
        if abs(derivative) > DERIV_SLOWDOWN_THRESHOLD:
            # Hızlı değişim → MIN_SPEED'e git
            speed = MIN_SPEED
        elif abs(derivative) > DERIV_MEDIUM_THRESHOLD:
            # Orta değişim → BASE - 10
            speed = BASE_SPEED - 10
        
        speed = float(np.clip(speed, MIN_SPEED, MAX_SPEED))

        # Dinamik Kazanç: Büyük hatalar için KP/KD çarpanı
        kp_eff = KP
        kd_eff = KD
        
        if abs(error) > 30:
            kp_eff *= KP_LARGE_ERROR_MULT
            kd_eff *= KD_LARGE_ERROR_MULT
        
        # Crossing (viraj) için KD artırma
        if abs(derivative) > 50:
            kd_eff *= CROSSING_KD_MULT

        # Direksiyon düzeltme hesabı
        correction = kp_eff * error + kd_eff * derivative

        if self.lost_frames > _LOST_FRAMES_STOP:
            speed = 0.0

        # Tekerlek hızları
        left  = float(np.clip(speed + correction, -MAX_SPEED, MAX_SPEED))
        right = float(np.clip(speed - correction, -MAX_SPEED, MAX_SPEED))

        # Ölü Bölge Telafisi: Motor gözlenebilir hareket için offset
        left = self._apply_dead_zone_compensation(left)
        right = self._apply_dead_zone_compensation(right)

        # Hız profiline göre trim seçimi
        left = self._apply_speed_dependent_trim(left)
        right = self._apply_speed_dependent_trim(right)

        self.prev_error = error
        self.prev_time  = now

        return left, right

    # ------------------------------------------------------------------
    def _apply_dead_zone_compensation(self, pwm: float) -> float:
        """Motor ölü bölgesi için PWM offset uygulaması."""
        if pwm == 0:
            return 0.0
        
        sign = 1 if pwm > 0 else -1
        abs_pwm = abs(pwm)
        
        # Ölü bölgeyi hesapla (% cinsinden)
        dead_zone_width = (DEAD_ZONE_PERCENT / 100.0) * 100.0
        
        if abs_pwm < DEAD_ZONE_MIN_PWM:
            # Çok düşük PWM → minimum PWM'e kaldır
            return sign * DEAD_ZONE_MIN_PWM
        
        return pwm

    # ------------------------------------------------------------------
    def _apply_speed_dependent_trim(self, pwm: float) -> float:
        """Hız profiline göre LEFT/RIGHT trim seçimi."""
        abs_pwm = abs(pwm)
        
        if abs_pwm < 40:
            # Düşük hız profili
            trim = LEFT_TRIM_LOW if pwm >= 0 else RIGHT_TRIM_LOW
        elif abs_pwm > 70:
            # Yüksek hız profili
            trim = LEFT_TRIM_HIGH if pwm >= 0 else RIGHT_TRIM_HIGH
        else:
            # Lineer interpolasyon
            ratio = (abs_pwm - 40) / 30.0
            if pwm >= 0:
                trim = LEFT_TRIM_LOW + ratio * (LEFT_TRIM_HIGH - LEFT_TRIM_LOW)
            else:
                trim = RIGHT_TRIM_LOW + ratio * (RIGHT_TRIM_HIGH - RIGHT_TRIM_LOW)
        
        return pwm * trim

    # ------------------------------------------------------------------
    def reset(self) -> None:
        """İç durumu sıfırla (örn. bir duraklamadan sonra)."""
        self.prev_error  = 0.0
        self.prev_time   = time.time()
        self.lost_frames = 0