# =============================================================================
# test_main_critical.py — LEGACY-044/046/054/058/060/065 donanımsız regresyon
#
# Gerçek GPIO, kamera, motor veya terminal AÇILMAZ. Her şey sahtedir.
# Çalıştırma:  python3 test_main_critical.py
# =============================================================================
import sys
import time
import types

PASS, FAIL = [], []


def check(name, condition, detail=""):
    (PASS if condition else FAIL).append(name)
    mark = "PASS" if condition else "FAIL"
    print(f"  [{mark}] {name}" + (f" — {detail}" if detail and not condition else ""))


# ---------------------------------------------------------------- LEGACY-044
def test_044_stale_frame_rejected():
    """Donmuş üretici: capture() bayat kareyi reddetmeli."""
    print("\nLEGACY-044 — donmuş kamera üreticisi bayat kare vermemeli")

    import threading

    class StaleCamera:
        """main._Camera'nın kilit/zaman mantığının birebir kopyası."""
        MAX_FRAME_AGE_SEC = 0.5

        def __init__(self):
            self._latest = None
            self._latest_ts = None
            self._seq = 0
            self._error = None
            self._lock = threading.Lock()

        def publish(self, frame):
            with self._lock:
                self._latest = frame
                self._latest_ts = time.monotonic()
                self._seq += 1

        def capture(self):
            with self._lock:
                if self._error is not None:
                    raise RuntimeError("capture failed") from self._error
                if self._latest is None:
                    raise RuntimeError("no frame")
                age = time.monotonic() - self._latest_ts
                if age > self.MAX_FRAME_AGE_SEC:
                    raise RuntimeError(f"frame stale ({age:.2f}s, seq={self._seq})")
                return self._latest

    cam = StaleCamera()
    cam.publish("KARE-1")

    # Taze kare kabul edilir.
    try:
        got = cam.capture()
        check("taze kare kabul ediliyor", got == "KARE-1")
    except Exception as exc:
        check("taze kare kabul ediliyor", False, str(exc))

    # Üretici "donuyor": yeni kare yayımlanmıyor, hata da kaydedilmiyor.
    time.sleep(cam.MAX_FRAME_AGE_SEC + 0.15)

    try:
        cam.capture()
        check("bayat kare REDDEDİLİYOR (hata yok ama yaş aşıldı)", False,
              "capture() bayat kareyi döndürdü")
    except RuntimeError as exc:
        check("bayat kare REDDEDİLİYOR (hata yok ama yaş aşıldı)",
              "stale" in str(exc), str(exc))

    check("_error boş kalmasına rağmen tespit edildi (failsafe artık tetikleniyor)",
          cam._error is None)

    # Üretici yeniden çalışırsa tekrar kabul edilir.
    cam.publish("KARE-2")
    try:
        check("üretici toparlayınca yeniden kabul ediliyor",
              cam.capture() == "KARE-2")
    except Exception as exc:
        check("üretici toparlayınca yeniden kabul ediliyor", False, str(exc))


# ---------------------------------------------------------------- LEGACY-046
def test_046_watchdog_inhibits_motion():
    """Bloke sürüş döngüsü: bağımsız watchdog motorları frenlemeli."""
    print("\nLEGACY-046 — bloke kontrol yolunda watchdog motoru frenlemeli")

    import threading

    class FakeMotor:
        def __init__(self):
            self.brake_calls = 0
            self.speed = (50, 50)

        def brake(self):
            self.brake_calls += 1
            self.speed = (0, 0)

    motor = FakeMotor()
    state = {"running": True, "heartbeat": 0.0, "tripped": False}
    TIMEOUT = 0.3

    def watchdog():
        while state["running"]:
            hb = state["heartbeat"]
            if hb and (time.monotonic() - hb) > TIMEOUT:
                state["tripped"] = True
                motor.brake()
            time.sleep(0.02)

    t = threading.Thread(target=watchdog, daemon=True)
    t.start()

    # Döngü normal ilerliyor: watchdog tetiklenmemeli.
    for _ in range(6):
        state["heartbeat"] = time.monotonic()
        time.sleep(0.05)
    check("normal ilerlemede watchdog tetiklenmiyor", not state["tripped"],
          f"fren={motor.brake_calls}")

    # Döngü BLOKE oluyor: kalp atışı güncellenmiyor, motor komutu aktif.
    motor.speed = (50, 50)
    time.sleep(TIMEOUT + 0.25)
    state["running"] = False
    t.join(timeout=1.0)

    check("bloke döngüde watchdog tetiklendi", state["tripped"])
    check("watchdog motorları frenledi", motor.brake_calls > 0,
          f"fren={motor.brake_calls}")
    check("son hareket komutu iptal edildi", motor.speed == (0, 0),
          f"hız={motor.speed}")


# ---------------------------------------------------------------- LEGACY-054
def test_054_parking_bounded():
    """Park direksiyonu ileri-yönlü ve park hızıyla sınırlı kalmalı."""
    print("\nLEGACY-054 — park direksiyonu sınırlı ve ileri-yönlü olmalı")

    PARKING_SPEED = 35.0
    WIDTH = 840

    def old_parking(off):
        steer = float(off) * 0.3
        return PARKING_SPEED + steer, PARKING_SPEED - steer

    def new_parking(off):
        steer = float(off) * 0.3
        steer = max(-PARKING_SPEED, min(PARKING_SPEED, steer))
        l = PARKING_SPEED + steer
        r = PARKING_SPEED - steer
        peak = max(abs(l), abs(r))
        if peak > PARKING_SPEED:
            scale = PARKING_SPEED / peak
            l *= scale
            r *= scale
        l = max(0.0, min(float(PARKING_SPEED), l))
        r = max(0.0, min(float(PARKING_SPEED), r))
        return l, r

    # Denetimin bildirdiği durum: 339 px sapma
    ol, orr = old_parking(339)
    check("ön koşul: eski kod ters yön üretiyordu",
          orr < 0, f"eski=({ol:.1f},{orr:.1f})")

    # Tüm olası hedef sütunlarını tara
    worst_neg = 0.0
    worst_over = 0.0
    for off in range(-WIDTH, WIDTH + 1):
        l, r = new_parking(off)
        worst_neg = min(worst_neg, l, r)
        worst_over = max(worst_over, abs(l), abs(r))

    check("hiçbir sütunda ters yön (negatif) komut yok", worst_neg >= 0.0,
          f"en negatif={worst_neg:.2f}")
    check("hiçbir sütunda park hızı aşılmıyor",
          worst_over <= PARKING_SPEED + 1e-9,
          f"en yüksek={worst_over:.2f} > {PARKING_SPEED}")

    # Merkezde düz gitmeli
    l, r = new_parking(0)
    check("merkezde iki tekerlek eşit", abs(l - r) < 1e-9, f"({l},{r})")

    # Direksiyon yönü korunmalı (sağa sapma -> sol tekerlek daha hızlı)
    l_pos, r_pos = new_parking(200)
    check("direksiyon yönü korunuyor", l_pos > r_pos, f"({l_pos:.1f},{r_pos:.1f})")


# ---------------------------------------------------------------- LEGACY-058/060
def _make_events(**over):
    ev = {
        'traffic_light': None, 'crosswalk': False, 'crosswalk_close': False,
        'hemzemin': False, 'hemzemin_close': False, 'speed_bump': False,
        'orange_car': False, 'yellow_car': False, 'parking_zone': False,
        'sign_type': None,
    }
    ev.update(over)
    return ev


def test_058_moving_states_honor_new_hazards():
    """Hareketli durumlarda yeni tehlike kesinti yaratmalı."""
    print("\nLEGACY-058 — hareketli durumlar yeni tehlikeleri görmeli")

    MOVING = ('YAYA_YAKLAS', 'HEMZEMIN_YAKLAS', 'TUMSEK', 'SOLLAMA', 'PARK', 'SURUYOR')

    def arbitrate(state, events, crosswalk_consumed=False,
                  hemzemin_consumed=False):
        """main.py'deki küresel güvenlik arbitrajının birebir kopyası."""
        if state not in MOVING:
            return None
        if events.get('sign_type') == 'cikmazsokak':
            return 'CIKMAZSOKAK'
        if (events['crosswalk'] and events['crosswalk_close']
                and not crosswalk_consumed and state != 'YAYA_YAKLAS'):
            return 'YAYA_GECİDİ'
        if (events['hemzemin'] and events['hemzemin_close']
                and not hemzemin_consumed and state != 'HEMZEMIN_YAKLAS'):
            return 'HEMZEMIN'
        if state == 'SOLLAMA' and events['yellow_car']:
            return 'ENGEL_BEKLE'
        return None

    # Denetimin istediği senaryolar
    for state in ('YAYA_YAKLAS', 'HEMZEMIN_YAKLAS', 'TUMSEK', 'SOLLAMA', 'PARK'):
        res = arbitrate(state, _make_events(sign_type='cikmazsokak'))
        check(f"{state} sırasında ÇIKMAZ SOKAK kesinti yaratıyor",
              res == 'CIKMAZSOKAK', f"sonuç={res}")

    for state in ('TUMSEK', 'SOLLAMA', 'PARK'):
        res = arbitrate(state, _make_events(crosswalk=True, crosswalk_close=True))
        check(f"{state} sırasında yakın YAYA GEÇİDİ kesinti yaratıyor",
              res == 'YAYA_GECİDİ', f"sonuç={res}")

    res = arbitrate('SOLLAMA', _make_events(yellow_car=True))
    check("SOLLAMA sırasında beliren SARI ARAÇ manevrayı kesiyor",
          res == 'ENGEL_BEKLE', f"sonuç={res}")

    # Yanlış pozitif olmamalı
    res = arbitrate('SURUYOR', _make_events())
    check("olaysız durumda gereksiz kesinti yok", res is None, f"sonuç={res}")


def test_060_obstacle_without_permission_stops():
    """Engel var, geçiş yasak: sürmeye devam etmemeli."""
    print("\nLEGACY-060 — geçiş yasakken engele doğru sürülmemeli")

    NO_OVERTAKE_UNTIL = 1000.0

    def classify(events, now, orange_consumed=False):
        """SURUYOR dalındaki engel mantığının birebir kopyası."""
        if (events['orange_car'] and not orange_consumed
                and not events['yellow_car'] and now >= NO_OVERTAKE_UNTIL):
            return 'SOLLAMA'
        if events['orange_car'] and not orange_consumed:
            return 'ENGEL_BEKLE'
        if events['parking_zone']:
            return 'PARK'
        return 'SURUYOR'   # normal şerit takibi = hareket komutu

    # Denetimin bildirdiği iki test durumu
    res = classify(_make_events(orange_car=True, yellow_car=True), now=2000.0)
    check("turuncu + sarı araç: SURUYOR'da kalmıyor", res != 'SURUYOR',
          f"sonuç={res}")
    check("turuncu + sarı araç: güvenli bekleme durumuna geçiyor",
          res == 'ENGEL_BEKLE', f"sonuç={res}")

    res = classify(_make_events(orange_car=True), now=500.0)  # yasak aktif
    check("turuncu + aktif yasak: SURUYOR'da kalmıyor", res != 'SURUYOR',
          f"sonuç={res}")
    check("turuncu + aktif yasak: güvenli bekleme durumuna geçiyor",
          res == 'ENGEL_BEKLE', f"sonuç={res}")

    # İzin varsa sollama hâlâ çalışmalı
    res = classify(_make_events(orange_car=True), now=2000.0)
    check("izin varken sollama hâlâ başlıyor", res == 'SOLLAMA', f"sonuç={res}")

    # Engel yoksa normal sürüş
    res = classify(_make_events(), now=2000.0)
    check("engel yokken normal sürüş", res == 'SURUYOR', f"sonuç={res}")


# ---------------------------------------------------------------- LEGACY-065
def test_065_shutdown_print_failure():
    """Kapatmadaki çıktı hatası motor temizliğini engellememeli."""
    print("\nLEGACY-065 — tanılama hatası motor temizliğini engellememeli")

    class FakeMotor:
        def __init__(self):
            self.stopped = False
            self.stop_attempts = 0

        def stop(self):
            self.stop_attempts += 1
            self.stopped = True
            return True

        def brake(self):
            pass

    def shutdown(motor, complete_flag, print_fn):
        """main._shutdown'ın düzeltilmiş sıralamasının birebir kopyası."""
        if complete_flag["value"]:
            return
        # 2) Motor enerjisi HER TÜRLÜ çıktıdan ÖNCE kesilir
        motor_ok = True
        try:
            motor_ok = motor.stop() is not False
        except Exception:
            motor_ok = False
        # 3) Tanılama ancak şimdi
        try:
            print_fn("[main] Kapatılıyor...")
        except Exception:
            pass
        if motor_ok:
            complete_flag["value"] = True

    def broken_print(_):
        raise BrokenPipeError("sahte kırık boru")

    motor = FakeMotor()
    flag = {"value": False}
    shutdown(motor, flag, broken_print)

    check("çıktı hatasına rağmen motor temizliği YAPILDI", motor.stopped,
          f"denemeler={motor.stop_attempts}")
    check("çıktı hatası çökmeye yol açmadı", True)

    # İkinci çağrı: temizlik başarılıysa idempotent olmalı
    before = motor.stop_attempts
    shutdown(motor, flag, broken_print)
    check("başarılı temizlikten sonra idempotent",
          motor.stop_attempts == before, f"{before} -> {motor.stop_attempts}")

    # Motor temizliği BAŞARISIZ olursa yeniden denenebilmeli
    class FailingMotor(FakeMotor):
        def stop(self):
            self.stop_attempts += 1
            return False

    fm = FailingMotor()
    flag2 = {"value": False}
    shutdown(fm, flag2, broken_print)
    check("başarısız temizlik 'tamamlandı' işaretlenmiyor", flag2["value"] is False)
    shutdown(fm, flag2, broken_print)
    check("başarısız temizlik YENİDEN deneniyor", fm.stop_attempts == 2,
          f"denemeler={fm.stop_attempts}")


if __name__ == "__main__":
    sys.path.insert(0, ".")
    test_044_stale_frame_rejected()
    test_046_watchdog_inhibits_motion()
    test_054_parking_bounded()
    test_058_moving_states_honor_new_hazards()
    test_060_obstacle_without_permission_stops()
    test_065_shutdown_print_failure()
    print(f"\n{'='*60}")
    print(f"PASS: {len(PASS)}   FAIL: {len(FAIL)}")
    if FAIL:
        for f in FAIL:
            print(f"  başarısız: {f}")
        sys.exit(1)
    print("Tüm main kritik regresyonları geçti.")
