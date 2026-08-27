# =============================================================================
# camtester.py  —  İnteraktif motor ve tahrik testi (kamera gerekmez)
#
# Doğrudan çalıştır:  python camtester.py
# Tuşlar:  w=ileri  s=geri  a=sol dön  d=sağ dön
#          BOŞLUK=dur  q=çık
# Çalıştırmadan önce TEST_SPEED'i güvenli bir değere ayarlayın.
# =============================================================================
try:
    from gpiozero import Device, DigitalOutputDevice, PWMOutputDevice
    _GPIO_SUPPORTED = True
    _GPIO_ERROR = None
except ImportError:
    _GPIO_SUPPORTED = False
    _GPIO_ERROR = "gpiozero bulunamadı"
    print("[camtester] gpiozero bulunamadı — motor testi çalıştırılamaz")

from time import sleep
import math
import sys

from config import (
    RIGHT_IN1, RIGHT_IN2, LEFT_IN1, LEFT_IN2,
    LEFT_PWM_PIN, RIGHT_PWM_PIN,
)

TEST_SPEED = 0.5    # 0.0 – 1.0
TURN_SPEED = 0.45

# --- Pin kurulumu (config.py ile eşleşir) --------------------------------
right_in1 = right_in2 = left_in1 = left_in2 = None
right_pwm = left_pwm = None
_DEVICES_OPEN = False


def close_devices():
    global right_in1, right_in2, left_in1, left_in2, right_pwm, left_pwm
    global _DEVICES_OPEN
    for dev in (right_in1, right_in2, left_in1, left_in2, right_pwm, left_pwm):
        if dev is None:
            continue
        try:
            dev.close()
        except Exception:
            pass
    right_in1 = right_in2 = left_in1 = left_in2 = None
    right_pwm = left_pwm = None
    _DEVICES_OPEN = False


def open_devices():
    """Gerçek GPIO çıkışlarını yalnızca bir test açıkça başladığında aç."""
    global right_in1, right_in2, left_in1, left_in2, right_pwm, left_pwm
    global _DEVICES_OPEN, _GPIO_ERROR
    if _DEVICES_OPEN:
        return
    if not _GPIO_SUPPORTED:
        raise RuntimeError(_GPIO_ERROR)
    try:
        right_in1 = DigitalOutputDevice(RIGHT_IN1)
        right_in2 = DigitalOutputDevice(RIGHT_IN2)
        left_in1  = DigitalOutputDevice(LEFT_IN1)
        left_in2  = DigitalOutputDevice(LEFT_IN2)
        right_pwm = PWMOutputDevice(RIGHT_PWM_PIN)
        left_pwm  = PWMOutputDevice(LEFT_PWM_PIN)
        factory_type = type(Device.pin_factory)
        if ("mock" in factory_type.__name__.lower()
                or ".mock" in factory_type.__module__.lower()):
            raise RuntimeError("gpiozero mock pin factory gerçek motor çıkışı değildir")
        _DEVICES_OPEN = True
    except Exception as exc:
        close_devices()
        _GPIO_ERROR = str(exc)
        raise RuntimeError(_GPIO_ERROR) from exc


def require_gpio():
    try:
        open_devices()
    except RuntimeError as exc:
        raise RuntimeError(
            f"Motor GPIO donanımı kullanılamıyor ({exc}); "
            "test hareketi gönderilmedi"
        ) from exc


def validate_speed(speed):
    speed = float(speed)
    if not math.isfinite(speed) or not 0.0 <= speed <= 1.0:
        raise ValueError("Motor test hızı 0.0 ile 1.0 arasında ve sonlu olmalı")
    return speed


# --- Temel hareketler -----------------------------------------------------
def stop():
    if not _DEVICES_OPEN:
        return
    for pwm in (right_pwm, left_pwm):
        try:
            pwm.value = 0
        except Exception:
            pass
    for p in (right_in1, right_in2, left_in1, left_in2):
        try:
            p.off()
        except Exception:
            pass


def forward(speed=TEST_SPEED):
    speed = validate_speed(speed)
    require_gpio()
    try:
        right_pwm.value = 0; left_pwm.value = 0
        # Yarış aracının kablolamasında pozitif komut ikinci yön pinidir.
        right_in1.off();  right_in2.on();  right_pwm.value = speed
        left_in1.off();   left_in2.on();   left_pwm.value  = speed
    except Exception:
        stop()
        raise


def backward(speed=TEST_SPEED):
    speed = validate_speed(speed)
    require_gpio()
    try:
        right_pwm.value = 0; left_pwm.value = 0
        right_in1.on();  right_in2.off();  right_pwm.value = speed
        left_in1.on();   left_in2.off();   left_pwm.value  = speed
    except Exception:
        stop()
        raise


def turn_left(speed=TURN_SPEED):
    """Pivot sol: sağ tekerlek geri, sol tekerlek ileri (motor yönü ters olduğu için)."""
    speed = validate_speed(speed)
    require_gpio()
    try:
        right_pwm.value = 0; left_pwm.value = 0
        right_in1.off();  right_in2.on();  right_pwm.value = speed
        left_in1.on();    left_in2.off();  left_pwm.value  = speed
    except Exception:
        stop()
        raise


def turn_right(speed=TURN_SPEED):
    """Pivot sağ: sol tekerlek geri, sağ tekerlek ileri (motor yönü ters olduğu için)."""
    speed = validate_speed(speed)
    require_gpio()
    try:
        right_pwm.value = 0; left_pwm.value = 0
        right_in1.on();   right_in2.off(); right_pwm.value = speed
        left_in1.off();   left_in2.on();   left_pwm.value  = speed
    except Exception:
        stop()
        raise


# --- Otomatik duman testi -------------------------------------------------
def run_smoke_test():
    require_gpio()
    print("=== Motor Duman Testi ===")
    steps = [
        ("İleri  1 s",    forward,     1.0),
        ("Dur    0.5 s",  stop,        0.5),
        ("Geri   1 s",    backward,    1.0),
        ("Dur    0.5 s",  stop,        0.5),
        ("Sol    0.8 s",  turn_left,   0.8),
        ("Dur    0.3 s",  stop,        0.3),
        ("Sağ    0.8 s",  turn_right,  0.8),
        ("Dur",           stop,        0.0),
    ]
    try:
        for label, fn, dur in steps:
            print(f"  {label}")
            fn()
            if dur:
                sleep(dur)
    finally:
        stop()
    print("=== Test tamamlandı ===")


# --- İnteraktif klavye kontrolü ------------------------------------------
def run_interactive():
    try:
        import tty
        import termios
    except ImportError:
        raise RuntimeError(
            "İnteraktif mod gerçek terminal gerektirir; "
            "otomatik motor testi kendiliğinden başlatılmadı"
        )

    fd  = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    print("İnteraktif mod: w/a/s/d = sürüş | BOŞLUK = dur | q = çık")
    try:
        tty.setraw(fd)
        while True:
            ch = sys.stdin.read(1)
            if   ch == 'w': forward()
            elif ch == 's': backward()
            elif ch == 'a': turn_left()
            elif ch == 'd': turn_right()
            elif ch == ' ': stop()
            elif ch == 'q': break
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
        stop()
        print("\nMotorlar durduruldu. Görüşmek üzere.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Motor testi")
    parser.add_argument("--smoke", action="store_true",
                        help="İnteraktif mod yerine otomatik duman testi çalıştır")
    pargs = parser.parse_args()

    try:
        require_gpio()
        if pargs.smoke:
            run_smoke_test()
        else:
            run_interactive()
    except KeyboardInterrupt:
        print("\nKesintiye uğradı.")
    except RuntimeError as exc:
        print(f"\n[camtester] HATA: {exc}")
        sys.exit(1)
    finally:
        try:
            stop()
        finally:
            close_devices()
