# =============================================================================
# test_motor_critical.py — LEGACY-068 / LEGACY-069 donanımsız regresyon testi
#
# Gerçek GPIO, gerçek kamera veya gerçek motor AÇILMAZ. Tüm cihazlar sahtedir.
# Çalıştırma:  python3 test_motor_critical.py
# =============================================================================
import math
import sys
import types


# ---------------------------------------------------------------- sahte gpiozero
class FakePWM:
    def __init__(self, pin, fail_zero=False, fail_close=False):
        self.pin = pin
        self.value = 0.0
        self.closed = False
        self._fail_zero = fail_zero
        self._fail_close = fail_close
        self.zero_attempts = 0
        self.close_attempts = 0

    def __setattr__(self, name, val):
        if name == "value" and getattr(self, "_fail_zero", False) and val == 0:
            object.__setattr__(self, "zero_attempts",
                               getattr(self, "zero_attempts", 0) + 1)
            raise OSError("sahte PWM sıfırlama hatası")
        object.__setattr__(self, name, val)

    def close(self):
        self.close_attempts += 1
        if self._fail_close:
            raise OSError("sahte PWM kapatma hatası")
        self.closed = True


class FakePin:
    def __init__(self, pin):
        self.pin = pin
        self.state = False
        self.closed = False

    def on(self):
        self.state = True

    def off(self):
        self.state = False

    def close(self):
        self.closed = True


class FakeFactory:
    pass


def install_fake_gpiozero():
    mod = types.ModuleType("gpiozero")
    mod.DigitalOutputDevice = FakePin
    mod.PWMOutputDevice = FakePWM

    class Device:
        pin_factory = FakeFactory()
    mod.Device = Device
    sys.modules["gpiozero"] = mod


# ---------------------------------------------------------------- yardımcılar
PASS, FAIL = [], []


def check(name, condition, detail=""):
    (PASS if condition else FAIL).append(name)
    mark = "PASS" if condition else "FAIL"
    print(f"  [{mark}] {name}" + (f" — {detail}" if detail and not condition else ""))


def fresh_motor(**config_overrides):
    """config ve motor modüllerini temiz yeniden yükler."""
    for m in ("motor", "config"):
        sys.modules.pop(m, None)
    import config
    for k, v in config_overrides.items():
        setattr(config, k, v)
    import motor
    return motor


# ---------------------------------------------------------------- LEGACY-068
def test_068_invalid_deadzone_rejected():
    print("\nLEGACY-068 — geçersiz ölü bölge tam doluluğa dönüşmemeli")
    for label, bad in (("NaN", float("nan")),
                       ("sonsuz", float("inf")),
                       ("101", 101.0)):
        motor = fresh_motor(DEAD_ZONE_MIN_PWM=bad)
        try:
            drv = motor.MotorDriver()
        except motor.MotorConfigInvalid:
            check(f"DEAD_ZONE_MIN_PWM={label} GPIO açılmadan reddedildi", True)
            continue
        except Exception as exc:
            check(f"DEAD_ZONE_MIN_PWM={label} reddedildi", False,
                  f"beklenmeyen hata {type(exc).__name__}: {exc}")
            continue
        # Reddedilmediyse: (10,10) çıkışı %100 oluyor mu?
        try:
            drv.set_speed(10, 10)
        except Exception:
            pass
        out = max(abs(drv._left_pwm.value), abs(drv._right_pwm.value))
        check(f"DEAD_ZONE_MIN_PWM={label} GPIO açılmadan reddedildi", False,
              f"kabul edildi, (10,10) -> PWM {out}")

    # Geçerli ayar hâlâ çalışmalı
    motor = fresh_motor(DEAD_ZONE_MIN_PWM=30)
    try:
        drv = motor.MotorDriver()
        drv.set_speed(10, 10)
        ok = abs(drv._left_pwm.value - 0.30) < 1e-9
        check("geçerli ayar (30) çalışmayı sürdürüyor", ok,
              f"PWM={drv._left_pwm.value}")
    except Exception as exc:
        check("geçerli ayar (30) çalışmayı sürdürüyor", False, str(exc))


# ---------------------------------------------------------------- LEGACY-069
def test_069_failed_stop_retryable():
    print("\nLEGACY-069 — başarısız kapatma gizlenmemeli ve yeniden denenmeli")
    motor = fresh_motor(DEAD_ZONE_MIN_PWM=30)
    drv = motor.MotorDriver()

    # PWM'i 0.62'ye getir, sonra sıfırlama ve kapatmayı başarısız yap.
    drv._left_pwm.value = 0.62
    drv._right_pwm.value = 0.62
    for pwm in (drv._left_pwm, drv._right_pwm):
        object.__setattr__(pwm, "_fail_zero", True)
        object.__setattr__(pwm, "_fail_close", True)

    first = drv.stop()
    check("başarısız kapatma False döndürüyor (sessizce 'tamam' demiyor)",
          first is False, f"döndü: {first}")
    check("başarısızlıklar görünür şekilde raporlanıyor",
          drv.cleanup_failed and len(drv.cleanup_failures) > 0)

    attempts_before = drv._left_pwm.zero_attempts
    second = drv.stop()
    attempts_after = drv._left_pwm.zero_attempts
    check("ikinci stop() gerçekten yeniden deniyor (hiçbir şey yapmadan dönmüyor)",
          attempts_after > attempts_before,
          f"deneme {attempts_before} -> {attempts_after}")

    # Şimdi hatayı kaldır; üçüncü deneme başarılı olmalı.
    for pwm in (drv._left_pwm, drv._right_pwm):
        object.__setattr__(pwm, "_fail_zero", False)
        object.__setattr__(pwm, "_fail_close", False)
    lpwm, rpwm = drv._left_pwm, drv._right_pwm   # stop() başarıda ref'leri None yapar
    third = drv.stop()
    check("hata giderildikten sonra stop() başarılı oluyor", third is True,
          f"döndü: {third}")
    check("başarılı kapatmadan sonra PWM sıfır",
          lpwm.value == 0 and rpwm.value == 0,
          f"sol={lpwm.value} sağ={rpwm.value}")


def test_069_successful_stop_still_idempotent():
    print("\nLEGACY-069 — başarılı kapatma hâlâ idempotent")
    motor = fresh_motor(DEAD_ZONE_MIN_PWM=30)
    drv = motor.MotorDriver()
    drv.set_speed(50, 50)
    check("ilk stop() True", drv.stop() is True)
    check("ikinci stop() True (idempotent)", drv.stop() is True)
    check("kapatma hatası bildirilmiyor", not drv.cleanup_failed)


# ---------------------------------------------------------------- LEGACY-067
def test_067_slow_state_steering_preserved():
    print("\nLEGACY-067 — yavaş durum ölçeklemesi direksiyon farkını silmemeli")
    motor = fresh_motor(DEAD_ZONE_MIN_PWM=30)
    drv = motor.MotorDriver()

    # Denetimin bildirdigi tam senaryo.
    l, r = 60.5133, 54.4867
    scale = 30 / max(abs(l), abs(r), 1)
    sl, sr = l * scale, r * scale
    drv.set_speed(sl, sr)
    lp, rp = drv._left_pwm.value * 100, drv._right_pwm.value * 100
    check("(30, 27.01) girdisi (30,30)'a ESITLENMIYOR",
          abs(lp - rp) > 0.5, f"sol={lp:.2f} sağ={rp:.2f}")

    # Duz gidis hala duz kalmali (esit girdi -> esit cikti)
    drv2 = motor.MotorDriver()
    drv2.set_speed(25, 25)
    lp2, rp2 = drv2._left_pwm.value * 100, drv2._right_pwm.value * 100
    check("eşit girdi hâlâ düz gidiş üretiyor", abs(lp2 - rp2) < 1e-6,
          f"sol={lp2:.2f} sağ={rp2:.2f}")

    # Sifir teker hala sifir kalmali (kasitli pivot korunur)
    drv3 = motor.MotorDriver()
    drv3.set_speed(40, 0)
    check("kasıtlı sıfır teker korunuyor", drv3._right_pwm.value == 0.0,
          f"sağ={drv3._right_pwm.value}")


if __name__ == "__main__":
    install_fake_gpiozero()
    sys.path.insert(0, ".")
    test_068_invalid_deadzone_rejected()
    test_069_failed_stop_retryable()
    test_069_successful_stop_still_idempotent()
    test_067_slow_state_steering_preserved()
    print(f"\n{'='*60}")
    print(f"PASS: {len(PASS)}   FAIL: {len(FAIL)}")
    if FAIL:
        for f in FAIL:
            print(f"  başarısız: {f}")
        sys.exit(1)
    print("Tüm kritik motor regresyonları geçti.")
