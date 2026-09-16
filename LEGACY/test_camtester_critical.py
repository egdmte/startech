# =============================================================================
# test_camtester_critical.py — LEGACY-008 / 007 / 009 donanımsız regresyon
#
# Gerçek terminal, gerçek GPIO veya gerçek motor AÇILMAZ.
# Çalıştırma:  python3 test_camtester_critical.py
# =============================================================================
import sys
import types

PASS, FAIL = [], []


def check(name, condition, detail=""):
    (PASS if condition else FAIL).append(name)
    mark = "PASS" if condition else "FAIL"
    print(f"  [{mark}] {name}" + (f" — {detail}" if detail and not condition else ""))


# ---------------------------------------------------------------- sahte cihazlar
class FakePWM:
    def __init__(self, pin):
        self.pin = pin
        self.value = 0.0
        self.closed = False

    def close(self):
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


def install_fakes():
    mod = types.ModuleType("gpiozero")
    mod.DigitalOutputDevice = FakePin
    mod.PWMOutputDevice = FakePWM

    class Device:
        pin_factory = FakeFactory()
    mod.Device = Device
    sys.modules["gpiozero"] = mod


class FakeStdin:
    """Belirtilen karakterleri sırayla verir, sonra EOF ('') döndürür."""

    def __init__(self, chars, eof_after=True):
        self.chars = list(chars)
        self.eof_after = eof_after
        self.reads = 0
        self.max_reads = 5000

    def fileno(self):
        return 0

    def read(self, n=1):
        self.reads += 1
        if self.reads > self.max_reads:
            raise RuntimeError("SONSUZ DÖNGÜ: okuma sınırı aşıldı")
        if self.chars:
            return self.chars.pop(0)
        return '' if self.eof_after else 'x'


def install_fake_tty(call_log):
    """tty/termios'u sahteler; tcsetattr çağrı sırasını kaydeder."""
    tty_mod = types.ModuleType("tty")
    tty_mod.setraw = lambda fd: call_log.append("setraw")

    term_mod = types.ModuleType("termios")
    term_mod.TCSADRAIN = 1
    term_mod.tcgetattr = lambda fd: ["saved"]
    term_mod.tcsetattr = lambda fd, when, old: call_log.append("tcsetattr")

    sys.modules["tty"] = tty_mod
    sys.modules["termios"] = term_mod


def fresh_camtester():
    for m in ("camtester", "config"):
        sys.modules.pop(m, None)
    import camtester
    return camtester


# ---------------------------------------------------------------- LEGACY-008
def run_interactive_with(chars, eof_after=True):
    """run_interactive'i sahte girdiyle çalıştır; (camtester, log) döndür."""
    call_log = []
    install_fake_tty(call_log)
    cam = fresh_camtester()

    fake_in = FakeStdin(chars, eof_after=eof_after)
    real_stdin = sys.stdin
    sys.stdin = fake_in
    try:
        cam.run_interactive()
        timed_out = False
    except RuntimeError as exc:
        if "SONSUZ DÖNGÜ" in str(exc):
            timed_out = True
        else:
            raise
    finally:
        sys.stdin = real_stdin
    return cam, call_log, fake_in, timed_out


def test_008_ctrl_c():
    print("\nLEGACY-008 — ham modda Ctrl+C (\\x03) derhal durdurup çıkmalı")
    cam, log, fake_in, timed_out = run_interactive_with(['w', '\x03'])
    check("Ctrl+C sonsuz döngüye girmiyor", not timed_out)
    check("Ctrl+C sonrası çıkıldı (okuma sayısı sınırlı)", fake_in.reads <= 3,
          f"okuma={fake_in.reads}")
    check("Ctrl+C sonrası sağ PWM sıfır", cam.right_pwm.value == 0,
          f"PWM={cam.right_pwm.value}")
    check("Ctrl+C sonrası sol PWM sıfır", cam.left_pwm.value == 0,
          f"PWM={cam.left_pwm.value}")


def test_008_eof():
    print("\nLEGACY-008 — EOF derhal durdurup çıkmalı")
    cam, log, fake_in, timed_out = run_interactive_with(['w'])
    check("EOF sonsuz döngüye girmiyor", not timed_out)
    check("EOF sonrası çıkıldı", fake_in.reads <= 3, f"okuma={fake_in.reads}")
    check("EOF sonrası sağ PWM sıfır", cam.right_pwm.value == 0,
          f"PWM={cam.right_pwm.value}")
    check("EOF sonrası sol PWM sıfır", cam.left_pwm.value == 0,
          f"PWM={cam.left_pwm.value}")


def test_008_normal_quit_still_works():
    print("\nLEGACY-008 — normal 'q' çıkışı bozulmamalı")
    cam, log, fake_in, timed_out = run_interactive_with(['w', 'q'])
    check("'q' ile temiz çıkış", not timed_out)
    check("'q' sonrası PWM sıfır", cam.right_pwm.value == 0)


# ---------------------------------------------------------------- LEGACY-009
def test_009_stop_before_terminal_restore():
    print("\nLEGACY-009 — motor durdurma terminal geri yüklemeden ÖNCE olmalı")
    order = []
    call_log = []

    tty_mod = types.ModuleType("tty")
    tty_mod.setraw = lambda fd: None
    term_mod = types.ModuleType("termios")
    term_mod.TCSADRAIN = 1
    term_mod.tcgetattr = lambda fd: ["saved"]

    def slow_restore(fd, when, old):
        order.append("tcsetattr")
    term_mod.tcsetattr = slow_restore
    sys.modules["tty"] = tty_mod
    sys.modules["termios"] = term_mod

    cam = fresh_camtester()
    real_stop = cam.stop

    def logging_stop():
        order.append("stop")
        return real_stop()
    cam.stop = logging_stop

    fake_in = FakeStdin(['w', 'q'])
    real_stdin = sys.stdin
    sys.stdin = fake_in
    try:
        cam.run_interactive()
    finally:
        sys.stdin = real_stdin

    check("stop() en az bir kez çağrıldı", "stop" in order, f"sıra={order}")
    if "stop" in order and "tcsetattr" in order:
        check("stop(), tcsetattr'dan ÖNCE çağrıldı",
              order.index("stop") < order.index("tcsetattr"), f"sıra={order}")
    else:
        check("stop(), tcsetattr'dan ÖNCE çağrıldı", False, f"sıra={order}")


def test_009_restore_failure_does_not_suppress_stop():
    print("\nLEGACY-009 — terminal geri yükleme hatası durdurmayı engellememeli")
    order = []
    tty_mod = types.ModuleType("tty")
    tty_mod.setraw = lambda fd: None
    term_mod = types.ModuleType("termios")
    term_mod.TCSADRAIN = 1
    term_mod.tcgetattr = lambda fd: ["saved"]

    def failing_restore(fd, when, old):
        order.append("tcsetattr")
        raise OSError("sahte terminal geri yükleme hatası")
    term_mod.tcsetattr = failing_restore
    sys.modules["tty"] = tty_mod
    sys.modules["termios"] = term_mod

    cam = fresh_camtester()
    fake_in = FakeStdin(['w', 'q'])
    real_stdin = sys.stdin
    sys.stdin = fake_in
    try:
        cam.run_interactive()
        raised = False
    except Exception:
        raised = True
    finally:
        sys.stdin = real_stdin

    check("geri yükleme hatası çökmeye yol açmadı", not raised)
    check("geri yükleme başarısızken bile PWM sıfır",
          cam.right_pwm.value == 0 and cam.left_pwm.value == 0,
          f"sağ={cam.right_pwm.value} sol={cam.left_pwm.value}")


# ---------------------------------------------------------------- LEGACY-007
def test_007_invalid_speed_stops_first():
    print("\nLEGACY-007 — geçersiz hız önceki hareketi bırakmamalı")
    cam = fresh_camtester()
    cam.open_devices()
    cam.forward(0.5)
    before = cam.right_pwm.value
    check("ön koşul: PWM 0.5'te", abs(before - 0.5) < 1e-9, f"PWM={before}")

    for label, bad in (("NaN", float("nan")),
                       ("sonsuz", float("inf")),
                       ("aralık dışı 1.5", 1.5),
                       ("negatif -0.2", -0.2)):
        cam.forward(0.5)          # tekrar hareket ettir
        try:
            cam.forward(bad)
            raised = False
        except (ValueError, TypeError):
            raised = True
        after = cam.right_pwm.value
        check(f"forward({label}) hata veriyor", raised)
        check(f"forward({label}) sonrası PWM sıfırlandı (komut kalmadı)",
              after == 0, f"PWM={after}")


def test_007_import_does_not_open_gpio():
    print("\nEk — içe aktarma tek başına GPIO açmamalı")
    cam = fresh_camtester()
    check("import sonrası cihazlar kapalı", cam._DEVICES_OPEN is False)
    check("import sonrası pin nesnesi yok", cam.right_pwm is None)


if __name__ == "__main__":
    install_fakes()
    sys.path.insert(0, ".")
    test_008_ctrl_c()
    test_008_eof()
    test_008_normal_quit_still_works()
    test_009_stop_before_terminal_restore()
    test_009_restore_failure_does_not_suppress_stop()
    test_007_invalid_speed_stops_first()
    test_007_import_does_not_open_gpio()
    print(f"\n{'='*60}")
    print(f"PASS: {len(PASS)}   FAIL: {len(FAIL)}")
    if FAIL:
        for f in FAIL:
            print(f"  başarısız: {f}")
        sys.exit(1)
    print("Tüm camtester kritik regresyonları geçti.")
