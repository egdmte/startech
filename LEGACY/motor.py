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


class MotorConfigInvalid(ValueError):
    """Aktüatör ayarları geçersizken GPIO açılmadan önce gönderilen hata."""


def _validate_actuator_config() -> None:
    """LEGACY-068: Aktüatör ayarlarını GPIO etkinleştirilmeden ÖNCE doğrula.

    DEAD_ZONE_MIN_PWM NaN/sonsuz ya da 100'den büyükse, ölü bölge
    dönüşümü düşük bir komutu %100 doluluğa çevirebilir. Bu değerleri
    clip ile gizlemek yerine, hiçbir çıkış açılmadan reddet.
    """
    dz = DEAD_ZONE_MIN_PWM
    if not isinstance(dz, (int, float)) or isinstance(dz, bool):
        raise MotorConfigInvalid(
            f"DEAD_ZONE_MIN_PWM sayısal olmalı (bulunan: {dz!r})"
        )
    dz = float(dz)
    if not math.isfinite(dz):
        raise MotorConfigInvalid(
            f"DEAD_ZONE_MIN_PWM sonlu olmalı (bulunan: {dz!r})"
        )
    if not 0.0 <= dz <= 100.0:
        raise MotorConfigInvalid(
            f"DEAD_ZONE_MIN_PWM 0 ile 100 arasında olmalı (bulunan: {dz})"
        )
    for name, trim in (
        ("LEFT_TRIM_LOW", LEFT_TRIM_LOW),
        ("LEFT_TRIM_HIGH", LEFT_TRIM_HIGH),
        ("RIGHT_TRIM_LOW", RIGHT_TRIM_LOW),
        ("RIGHT_TRIM_HIGH", RIGHT_TRIM_HIGH),
    ):
        if not isinstance(trim, (int, float)) or isinstance(trim, bool):
            raise MotorConfigInvalid(f"{name} sayısal olmalı (bulunan: {trim!r})")
        trim = float(trim)
        if not math.isfinite(trim) or trim <= 0.0:
            raise MotorConfigInvalid(
                f"{name} sonlu ve sıfırdan büyük olmalı (bulunan: {trim})"
            )


class MotorDriver:
    """İki DC motoru H-köprüsü üzerinden (örn. L298N) kontrol eder.

    Hız değerleri [-100, 100] aralığındadır:
      pozitif → ileri, negatif → geri, 0 → serbest.
    gpiozero yoksa hareket komutları hata verir; araç sürülmüş gibi davranılmaz.
    """

    def __init__(self):
        # LEGACY-068: Geçersiz ayarlar hiçbir GPIO çıkışı açılmadan reddedilir.
        _validate_actuator_config()
        self._has_gpio = _HAS_GPIO
        self._closed = not _HAS_GPIO
        # LEGACY-069: Kapatma başarısı cihaz başına izlenir; başarısız
        # kapatma "tamamlandı" sayılmaz ve yeniden denenebilir.
        self._cleanup_failures: list[str] = []
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
                "GPIO kütüphanesi yok - Windows üzerinden çalışıyor olabilir misiniz?"
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
            # LEGACY-068: Ölü bölge dönüşümünden SONRA tekrar doğrula.
            # Clamp'e geçersiz bir değerin ulaşması, düşük bir komutun
            # %100 doluluğa dönüşmesi demektir; bunu clip ile gizleme.
            if not math.isfinite(left) or not math.isfinite(right):
                raise ValueError("Ölü bölge sonrası motor hızı sonlu değil")
            if abs(left) > 100.0 or abs(right) > 100.0:
                raise ValueError(
                    f"Ölü bölge sonrası motor hızı sınır dışı "
                    f"(sol={left}, sağ={right}); ayarlar geçersiz"
                )

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
    def stop(self) -> bool:
        """Çıkışları sıfırla ve GPIO kaynaklarını serbest bırak.

        LEGACY-069: Kapatma BAŞARISI cihaz başına izlenir. Eski davranışta
        `_closed` daha çıkışlar sıfırlanmadan True yapılıyor, hatalar
        yutuluyor ve sonraki `stop()` çağrıları hiçbir şey denemeden
        dönüyordu — yani arka uç hâlâ aktif komut tutuyorken yazılım
        "kapandı" diyebiliyordu.

        Dönüş: tüm cihazlar başarıyla enerjisizleştirilip kapatıldıysa True.
        Başarısızlık durumunda nesne kapanmış SAYILMAZ; tekrar çağrılabilir.
        """
        if not self._has_gpio:
            return True

        failures: list[str] = []

        # 1) Önce çıkışları sıfırla — her birini bağımsız dene, ilk hata
        #    diğerlerini engellemesin.
        for name, pwm in (("right_pwm", self._right_pwm),
                          ("left_pwm", self._left_pwm)):
            if pwm is None:
                continue
            try:
                pwm.value = 0
            except Exception as exc:
                failures.append(f"{name} sıfırlanamadı: {exc}")

        # 2) Yön pinlerini de düşür (H-köprüsünü serbest bırak).
        for name, pin in (("right_in1", self._right_in1),
                          ("right_in2", self._right_in2),
                          ("left_in1", self._left_in1),
                          ("left_in2", self._left_in2)):
            if pin is None:
                continue
            try:
                pin.off()
            except Exception as exc:
                failures.append(f"{name} kapatılamadı: {exc}")

        # 3) Cihazları kapat.
        failures.extend(self._close_devices())

        self._cleanup_failures = failures
        if failures:
            # Kapanma TAMAMLANMADI: bayrakları koru ki tekrar denenebilsin.
            print("[motor] UYARI: motor kapatma tamamlanamadı:")
            for msg in failures:
                print(f"  - {msg}")
            print("[motor] Çıkış hâlâ aktif olabilir — "
                  "bağımsız donanım kesme kullanın.")
            return False

        self._closed = True
        self._has_gpio = False
        return True

    @property
    def cleanup_failed(self) -> bool:
        """Son stop() denemesi eksik kaldıysa True."""
        return bool(self._cleanup_failures)

    @property
    def cleanup_failures(self) -> list[str]:
        """Son stop() denemesindeki başarısız işlemlerin açıklamaları."""
        return list(self._cleanup_failures)

    def _close_devices(self) -> list[str]:
        """Cihazları kapat; başarısız olanların açıklamalarını döndür.

        LEGACY-069: Başarıyla kapanan cihaz None yapılır, böylece yeniden
        denemede yalnızca gerçekten kapanmamış olanlar denenir.
        """
        failures: list[str] = []
        for attr in ("_right_in1", "_right_in2", "_left_in1", "_left_in2",
                     "_right_pwm", "_left_pwm"):
            dev = getattr(self, attr, None)
            if dev is None:
                continue
            try:
                dev.close()
            except Exception as exc:
                failures.append(f"{attr.lstrip('_')} close() başarısız: {exc}")
            else:
                setattr(self, attr, None)
        return failures

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
