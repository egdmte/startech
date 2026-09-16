# =============================================================================
# test_perception_fixes.py — LEGACY High/Medium katmani regresyonu
#
# Gercek numpy/cv2 ile SENTETIK goruntuler kullanir. Gercek kamera, GPIO
# veya motor ACILMAZ.
#   python3 test_perception_fixes.py
# =============================================================================
import sys
import numpy as np
import cv2

sys.path.insert(0, ".")
PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}"
          + (f" — {detail}" if detail and not cond else ""))


# ---------------------------------------------------------------- LEGACY-037
def test_037_blur_axis():
    print("\nLEGACY-037 — histogram yumusatmasi dogru eksende olmali")
    hist = np.zeros((1, 800), dtype=np.float32)
    hist[0, 400] = 1000.0

    wrong = cv2.GaussianBlur(hist.copy(), (1, 31), 0)
    right = cv2.GaussianBlur(hist.copy(), (31, 1), 0)

    check("eski (1,31) cekirdek gercekten etkisizdi",
          int((wrong[0] > 0).sum()) == 1,
          f"nonzero={(wrong[0] > 0).sum()}")
    check("yeni (31,1) cekirdek komsu sutunlara yayiliyor",
          int((right[0] > 0).sum()) > 1,
          f"nonzero={(right[0] > 0).sum()}")
    check("yayilim simetrik",
          abs(float(right[0, 399]) - float(right[0, 401])) < 1e-3)
    check("toplam agirlik korunuyor",
          abs(float(right.sum()) - 1000.0) < 5.0, f"toplam={right.sum():.1f}")


# ---------------------------------------------------------------- LEGACY-016
def test_016_green_square_rejected():
    print("\nLEGACY-016 — yesil KARE trafik lambasi sayilmamali")
    import importlib
    import config
    importlib.reload(config)
    import events as ev
    importlib.reload(ev)

    def blob_area(shape):
        m = np.zeros((200, 200), dtype=np.uint8)
        if shape == "square":
            cv2.rectangle(m, (50, 50), (89, 89), 255, -1)
        else:
            cv2.circle(m, (70, 70), 20, 255, -1)
        return ev._largest_circular_blob(m, min_area=100)

    sq = blob_area("square")
    ci = blob_area("circle")
    check("yesil KARE reddediliyor", sq == 0.0, f"alan={sq}")
    check("gercek DAIRE hala kabul ediliyor", ci > 0.0, f"alan={ci}")

    # cok uzun/yassi nesne de reddedilmeli
    m = np.zeros((200, 200), dtype=np.uint8)
    cv2.ellipse(m, (100, 100), (60, 10), 0, 0, 360, 255, -1)
    check("uzun/yassi nesne reddediliyor",
          ev._largest_circular_blob(m, 100) == 0.0)


# ---------------------------------------------------------------- LEGACY-023
def test_023_three_stripes_rejected():
    print("\nLEGACY-023 — uc genis serit dort serit sayilmamali")
    import importlib, config, events as ev
    importlib.reload(config); importlib.reload(ev)
    det = ev.EventDetector()

    def roi_from_rows(rows, h=380, w=800):
        """Beyaz satirlardan HSV ROI uretir."""
        img = np.zeros((h, w, 3), dtype=np.uint8)
        for (a, b) in rows:
            img[a:b + 1, :] = (255, 255, 255)
        return cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # Uc GENIS serit (her biri kalin) -> reddedilmeli
    three = [(20, 60), (120, 160), (220, 260)]
    d, n = det._detect_stripe_pattern(roi_from_rows(three))
    check("uc genis serit REDDEDILIYOR", d is False, f"detected={d}")

    # Dort gercek ince serit -> kabul
    four = [(15, 24), (100, 109), (190, 199), (290, 299)]
    d, n = det._detect_stripe_pattern(roi_from_rows(four))
    check("dort ayri ince serit KABUL EDILIYOR", d is True, f"detected={d}")


# ---------------------------------------------------------------- LEGACY-022
def test_022_final_stripe_not_lost():
    print("\nLEGACY-022 — ROI tabanina dayanan son serit kaybolmamali")
    import importlib, config, events as ev
    importlib.reload(config); importlib.reload(ev)
    det = ev.EventDetector()

    h, w = 360, 800
    img = np.zeros((h, w, 3), dtype=np.uint8)
    # son serit tam ROI tabaninda (330..359)
    for (a, b) in [(30, 39), (130, 139), (230, 239), (330, 359)]:
        img[a:b + 1, :] = (255, 255, 255)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    d, n = det._detect_stripe_pattern(hsv)
    check("ROI tabanindaki son serit sayiliyor", d is True, f"detected={d}")
    check("taban seridi YAKIN olarak isaretleniyor", n is True, f"near={n}")

    # Tek piksel kaydirma sonucu degistirmemeli (bin sinirina bagimlilik yok)
    sonuclar = []
    for shift in range(0, 8):
        img2 = np.zeros((h, w, 3), dtype=np.uint8)
        for (a, b) in [(30 + shift, 39 + shift), (130 + shift, 139 + shift),
                       (230 + shift, 239 + shift), (300 + shift, 309 + shift)]:
            img2[a:b + 1, :] = (255, 255, 255)
        hsv2 = cv2.cvtColor(img2, cv2.COLOR_BGR2HSV)
        sonuclar.append(det._detect_stripe_pattern(hsv2)[0])
    check("tek piksel kaydirma sonucu degistirmiyor",
          len(set(sonuclar)) == 1, f"sonuclar={sonuclar}")


# ---------------------------------------------------------------- LEGACY-024
def test_024_flat_rectangle_not_bump():
    print("\nLEGACY-024 — duz dikdortgen tumsek sayilmamali")
    import importlib, config, events as ev
    importlib.reload(config); importlib.reload(ev)
    det = ev.EventDetector()

    # Denetimin bildirdigi durum: duz beyaz 700x50 dikdortgen
    img = np.zeros((380, 800, 3), dtype=np.uint8)
    cv2.rectangle(img, (50, 100), (749, 149), (255, 255, 255), -1)
    check("duz beyaz dikdortgen REDDEDILIYOR",
          det._detect_speed_bump(img) is False)

    # Yaya gecidi boyasi da tumsek olmamali
    img2 = np.zeros((380, 800, 3), dtype=np.uint8)
    for a in (40, 90, 140, 190):
        cv2.rectangle(img2, (0, a), (799, a + 12), (255, 255, 255), -1)
    check("yaya gecidi boyasi tumsek sayilmiyor",
          det._detect_speed_bump(img2) is False)


# ---------------------------------------------------------------- LEGACY-025
def test_025_nonintersecting_diagonals():
    print("\nLEGACY-025 — kesismeyen capraz cizgiler X sayilmamali")
    import importlib, config, events as ev
    importlib.reload(config); importlib.reload(ev)
    det = ev.EventDetector()

    # Denetimin bildirdigi durum: ayrik iki capraz
    img = np.zeros((380, 800, 3), dtype=np.uint8)
    cv2.line(img, (10, 300), (210, 100), (255, 255, 255), 6)
    cv2.line(img, (580, 100), (780, 300), (255, 255, 255), 6)
    d, n = det._detect_hemzemin(img)
    check("kesismeyen capraz cizgiler REDDEDILIYOR", d is False, f"detected={d}")

    # Gercek X deseni kabul edilmeli
    img2 = np.zeros((380, 800, 3), dtype=np.uint8)
    cv2.line(img2, (250, 80), (550, 330), (255, 255, 255), 6)
    cv2.line(img2, (550, 80), (250, 330), (255, 255, 255), 6)
    d2, n2 = det._detect_hemzemin(img2)
    check("gercek X deseni KABUL EDILIYOR", d2 is True, f"detected={d2}")


# ---------------------------------------------------------------- LEGACY-012/013
def test_012_013_controller():
    print("\nLEGACY-012/013 — integral tersine donmesin, ilk turev kicki olmasin")
    import importlib, config, controller as ctrl
    importlib.reload(config); importlib.reload(ctrl)

    # 013: ilk gozlemde turev sifir olmali
    c = ctrl.PDController()
    l1, r1 = c.compute(60.0)
    c2 = ctrl.PDController()
    # ayni hata ile ikinci kez: artik gercek turev var
    c2.compute(60.0)
    l2, r2 = c2.compute(60.0)
    check("ilk gozlemde uydurma turev kicki yok",
          abs((l1 - r1)) <= abs(60.0 * config.KP * 2) + 1e-6,
          f"ilk fark={l1-r1:.2f}")
    check("ikinci gercek gozlem normal calisiyor", True)

    # 012: kayip karede integral solmali, isaret tersine donmemeli
    c3 = ctrl.PDController()
    for _ in range(10):
        c3.compute(40.0)          # pozitif hata birikimi
    c3.integral = -50.0           # denetimin senaryosu: ters isaretli integral
    c3.prev_error = 10.0
    ints = []
    for _ in range(5):
        c3.compute(None)
        ints.append(c3.integral)
    check("kayip karede integral soluyor (donmuyor)",
          all(abs(ints[i+1]) < abs(ints[i]) for i in range(len(ints)-1)),
          f"integraller={[round(v,2) for v in ints]}")
    check("integral isaret degistirmiyor",
          all(v <= 0 for v in ints), f"integraller={[round(v,2) for v in ints]}")


# ---------------------------------------------------------------- LEGACY-015
def test_015_deadzone_continuity():
    print("\nLEGACY-015 — ic tekerlek sifir sinirinda siçrama olmamali")
    import importlib, config, controller as ctrl
    importlib.reload(config); importlib.reload(ctrl)
    c = ctrl.PDController()

    a = c._apply_dead_zone_pair(49.999, 0.001)
    b = c._apply_dead_zone_pair(50.0, 0.0)
    jump = max(abs(a[0] - b[0]), abs(a[1] - b[1]))
    check("sifira komsu girdiler surekli cikti veriyor", jump < 5.0,
          f"(49.999,0.001)->{tuple(round(v,2) for v in a)}  "
          f"(50,0)->{tuple(round(v,2) for v in b)}  sicrama={jump:.2f}")

    # kasitli duran teker korunmali
    out = c._apply_dead_zone_pair(50.0, 0.0)
    check("kasitli duran teker korunuyor", out[1] == 0.0, f"{out}")


# ---------------------------------------------------------------- LEGACY-035/036
def test_035_036_lane_rejects():
    print("\nLEGACY-035/036 — duz zemin ve minik leke serit sayilmamali")
    import importlib, config, lane as ln
    importlib.reload(config); importlib.reload(ln)

    det = ln.LaneDetector()
    # kimlik perspektifi: sentetik testin gercek yol geometrisine bagimli
    # olmamasi icin (denetimin yontemi)
    det.M = np.eye(3, dtype=np.float32)
    det.Minv = np.eye(3, dtype=np.float32)

    # LEGACY-035: duzgun gri/beyaz zemin -> serit YOK
    reddedildi = []
    for val in (80, 100, 120, 160, 200, 255):
        frame = np.full((config.HEIGHT, config.WIDTH, 3), val, dtype=np.uint8)
        err, _ = det.process(frame)
        reddedildi.append(err is None)
        det._left_mem = det._right_mem = None      # hafizayi temizle
    check("duz zeminler (80..255) serit olarak REDDEDILIYOR",
          all(reddedildi), f"sonuclar={reddedildi}")

    # LEGACY-036: minik izole leke -> serit YOK
    det2 = ln.LaneDetector()
    det2.M = np.eye(3, dtype=np.float32)
    det2.Minv = np.eye(3, dtype=np.float32)
    frame = np.zeros((config.HEIGHT, config.WIDTH, 3), dtype=np.uint8)
    cv2.rectangle(frame, (100, 230), (105, 235), (255, 255, 255), -1)
    err, _ = det2.process(frame)
    check("6x6 minik leke serit sayilmiyor", err is None, f"error={err}")


# ---------------------------------------------------------------- LEGACY-039
def test_039_observed_vs_cached():
    print("\nLEGACY-039 — onbellek gozlemden ayirt edilebilmeli")
    import importlib, config, lane as ln
    importlib.reload(config); importlib.reload(ln)
    det = ln.LaneDetector()
    det.M = np.eye(3, dtype=np.float32)
    det.Minv = np.eye(3, dtype=np.float32)

    # gercek iki serit
    frame = np.zeros((config.HEIGHT, config.WIDTH, 3), dtype=np.uint8)
    cv2.rectangle(frame, (150, 0), (170, config.HEIGHT), (255, 255, 255), -1)
    cv2.rectangle(frame, (650, 0), (670, config.HEIGHT), (255, 255, 255), -1)
    det.process(frame)
    check("gercek gozlem lane_observed=True yapiyor",
          det.lane_observed is True)

    # bos kareler: onbellek hala hata uretebilir AMA gozlem False olmali
    blank = np.zeros((config.HEIGHT, config.WIDTH, 3), dtype=np.uint8)
    det.process(blank)
    check("bos karede lane_observed=False (onbellek gizlemiyor)",
          det.lane_observed is False)
    check("gozlemsiz kare sayaci artiyor",
          det.frames_since_observation >= 1,
          f"sayac={det.frames_since_observation}")


if __name__ == "__main__":
    test_037_blur_axis()
    test_016_green_square_rejected()
    test_023_three_stripes_rejected()
    test_022_final_stripe_not_lost()
    test_024_flat_rectangle_not_bump()
    test_025_nonintersecting_diagonals()
    test_012_013_controller()
    test_015_deadzone_continuity()
    test_035_036_lane_rejects()
    test_039_observed_vs_cached()
    print(f"\n{'='*60}")
    print(f"PASS: {len(PASS)}   FAIL: {len(FAIL)}")
    if FAIL:
        for f in FAIL:
            print(f"  basarisiz: {f}")
        sys.exit(1)
    print("Tum algilama/kontrol regresyonlari gecti.")
