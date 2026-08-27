# =============================================================================
# motor.py  —  Düşük seviyeli H-köprüsü motor sürücüsü  (gpiozero — Pi 5 uyumlu)
# =============================================================================
import math

try:
    from gpiozero import Device, DigitalOutputDevice, PWMOutputDevice
    _HAS_GPIO = True
except ImportError:
    _HAS_GPIO = False
    print("[motor] gpiozero bulunamadı — motor donanımı kullanılamıyor")

from config import (
    RIGHT_IN1, RIGHT_IN2, LEFT_IN1, LEFT_IN2,
    LEFT_PWM_PIN, RIGHT_PWM_PIN,
    LEFT_TRIM_LOW, LEFT_TRIM_HIGH,
    RIGHT_TRIM_LOW, RIGHT_TRIM_HIGH,
    DEAD_ZONE_MIN_PWM,
)


class MotorHardwareUnavailable(RuntimeError):
    """Gerçek motor GPIO çıkışı kurulamadığında gönderilen açık hata."""


class MotorDriver:
    """İki DC motoru H-köprüsü üzerinden (örn. L298N) kontrol eder.

    Hız değerleri [-100, 100] aralığındadır:
      pozitif → ileri, negatif → geri, 0 → serbest.
    gpiozero yoksa hareket komutları hata verir; araç sürülmüş gibi davranılmaz.
    """

    def __init__(self):
        self._has_gpio = _HAS_GPIO
        self._closed = not _HAS_GPIO
        self._right_in1 = None
        self._right_in2 = None
        self._left_in1 = None
        self._left_in2 = None
        self._right_pwm = None
        self._left_pwm = None
        if not self._has_gpio:
            return
        try:
            self._right_in1 = DigitalOutputDevice(RIGHT_IN1)
            self._right_in2 = DigitalOutputDevice(RIGHT_IN2)
            self._left_in1  = DigitalOutputDevice(LEFT_IN1)
            self._left_in2  = DigitalOutputDevice(LEFT_IN2)
            # PWMOutputDevice değer aralığı 0.0 – 1.0
            self._right_pwm = PWMOutputDevice(RIGHT_PWM_PIN)
            self._left_pwm  = PWMOutputDevice(LEFT_PWM_PIN)
            factory = Device.pin_factory
            factory_type = type(factory)
            if ("mock" in factory_type.__name__.lower()
                    or ".mock" in factory_type.__module__.lower()):
                raise MotorHardwareUnavailable(
                    "gpiozero mock pin factory gerçek motor çıkışı değildir"
                )
            self._closed = False
        except Exception as exc:
            self._close_devices()
            self._has_gpio = False
            self._closed = True
            raise MotorHardwareUnavailable(
                f"Motor GPIO çıkışları açılamadı: {exc}"
            ) from exc

    @property
    def hardware_available(self) -> bool:
        """Gerçek GPIO motor çıkışı kurulmuşsa True döndürür."""
        return self._has_gpio and not self._closed

    def require_hardware(self) -> None:
        """Motor kullanan bir programı gerçek GPIO yoksa açıkça durdurur."""
        if not self._has_gpio or self._closed:
            raise MotorHardwareUnavailable(
                "Motor GPIO donanımı kullanılamıyor; hareket komutu gönderilmedi"
            )

    # ------------------------------------------------------------------
    def set_speed(self, left: float, right: float) -> None:
        """[-100, 100] aralığında tekerlek hızlarını uygular.

        Hız-bağımlı TRIM uygulanır:
        - < 40%: LOW profili
        - > 70%: HIGH profili
        - Arası: lineer interpolasyon
        """
        self.require_hardware()
        try:
            left  = float(left)
            right = float(right)
            if not math.isfinite(left) or not math.isfinite(right):
                raise ValueError("Motor hızı sonlu bir sayı olmalı")

            # Hız-bağımlı trim seçimi
            left_trim = self._get_trim(left, LEFT_TRIM_LOW, LEFT_TRIM_HIGH)
            right_trim = self._get_trim(right, RIGHT_TRIM_LOW, RIGHT_TRIM_HIGH)
            if (not math.isfinite(left_trim) or not math.isfinite(right_trim)
                    or left_trim <= 0 or right_trim <= 0):
                raise ValueError(
                    "Motor trim değerleri sonlu ve sıfırdan büyük olmalı"
                )

            left  = left * left_trim
            right = right * right_trim
            if not math.isfinite(left) or not math.isfinite(right):
                raise ValueError("Trim sonrası motor hızı sonlu değil")
            # Motor olu bolgesi son uygulanacak kuraldir. Main'in
            # yaklasma/tumsek hiz olceklemesi telafiyi geri alamaz.
            left = self._apply_dead_zone(left)
            right = self._apply_dead_zone(right)
            left  = max(-100.0, min(100.0, left))
            right = max(-100.0, min(100.0, right))

            self._apply(self._left_in1, self._left_in2, self._left_pwm, left)
            self._apply(self._right_in1, self._right_in2, self._right_pwm, right)
        except Exception:
            self.stop()
            raise

    # ------------------------------------------------------------------
    @staticmethod
    def _get_trim(pwm: float, trim_low: float, trim_high: float) -> float:
        """Hız profiline göre trim değeri döndür (lineer interpolasyon)."""
        abs_pwm = abs(pwm)
        
        if abs_pwm < 40:
            return trim_low
        elif abs_pwm > 70:
            return trim_high
        else:
            # Lineer interpolasyon: 40% ile 70% arasında
            ratio = (abs_pwm - 40) / 30.0
            return trim_low + ratio * (trim_high - trim_low)

    @staticmethod
    def _apply_dead_zone(pwm: float) -> float:
        if pwm == 0.0 or abs(pwm) >= DEAD_ZONE_MIN_PWM:
            return pwm
        return DEAD_ZONE_MIN_PWM if pwm > 0 else -DEAD_ZONE_MIN_PWM

    # ------------------------------------------------------------------
    def brake(self) -> None:
        """Aktif fren: her iki yön pini HIGH, H-köprüsü etkin."""
        if not self._has_gpio or self._closed:
            return
        for pin in (self._right_in1, self._right_in2,
                    self._left_in1,  self._left_in2):
            pin.on()
        self._right_pwm.value = 1.0
        self._left_pwm.value  = 1.0

    def coast(self) -> None:
        """GPIO kaynaklarını kapatmadan iki motor çıkışını enerjisiz bırakır."""
        if not self._has_gpio or self._closed:
            return
        self._right_pwm.value = 0.0
        self._left_pwm.value = 0.0
        for pin in (self._right_in1, self._right_in2,
                    self._left_in1, self._left_in2):
            pin.off()

    # ------------------------------------------------------------------
    def stop(self) -> None:
        """Serbest frenleme ve tüm GPIO kaynaklarını serbest bırakma."""
        if not self._has_gpio or self._closed:
            return
        self._closed = True
        for pwm in (self._right_pwm, self._left_pwm):
            try:
                pwm.value = 0
            except Exception:
                pass
        self._close_devices()
        self._has_gpio = False

    def _close_devices(self) -> None:
        for dev in (self._right_in1, self._right_in2,
                    self._left_in1, self._left_in2,
                    self._right_pwm, self._left_pwm):
            if dev is None:
                continue
            try:
                dev.close()
            except Exception:
                pass

    # ------------------------------------------------------------------
    @staticmethod
    def _apply(
        pin_fwd: "DigitalOutputDevice",
        pin_rev: "DigitalOutputDevice",
        pwm:     "PWMOutputDevice",
        speed:   float,
    ) -> None:
        # Yön pinlerini yük altındayken değiştirme.
        pwm.value = 0.0
        # ⚠️ MOTOR YÖNÜ TERSİ ÇEVRİLDİ (ileri↔geri)
        if speed >= 0:
            # Pozitif → GERI (pin_rev ON)
            pin_fwd.off()
            pin_rev.on()
        else:
            # Negatif → İLERİ (pin_fwd ON)
            pin_fwd.on()
            pin_rev.off()
        pwm.value = abs(speed) / 100.0
