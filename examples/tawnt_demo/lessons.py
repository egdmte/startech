"""Three hardware-free lessons showing the 3awnt API in increasing depth."""

from __future__ import annotations

import json
from pathlib import Path

import tawnt

from .driver import DemoResult, FakeMotorDriver


def _say(verbose: bool, title: str, explanation: str) -> None:
    if verbose:
        print("\n=== %s ===" % title)
        print(explanation)


def legacy_names_lesson(verbose: bool = True) -> int:
    """Eski ``introduce → acquire → preacquire`` adlarını gösterir."""

    _say(
        verbose,
        "1. Eski adlar",
        "introduce kuralları tanıtır, acquire değeri kaydeder, "
        "preacquire başlamadan önce kontrol eder.",
    )
    tawnt.sifirla()

    max_pwm = tawnt.introduce("ESKI_MAX_PWM", min=0, max=100)
    kare = tawnt.introduce("ESKI_KARE")
    perspektif = tawnt.introduce("ESKI_PERSPEKTIF")
    min_hiz = tawnt.introduce("ESKI_MIN_HIZ", min=0, max=100)
    hedef_hiz = tawnt.introduce("ESKI_HEDEF_HIZ", min=0, max=100)

    tawnt.identifyRuntimeType(max_pwm, "% PWM")
    tawnt.IsTwinOf(kare, perspektif)
    tawnt.siblingIntAppr(min_hiz, "<=", hedef_hiz)

    tawnt.acquire(
        max_pwm,
        57,
        kaynak=tawnt.OLCULDU,
        kim="Egemen",
        tarih="2026-08-06",
        notu="Bu yalnız öğretici örnek veridir.",
    )
    tawnt.acquire(kare, (640, 480), kaynak=tawnt.DEVRALINDI)
    tawnt.acquire(
        perspektif,
        [(0, 0), (639, 0), (0, 479), (639, 479)],
        kaynak=tawnt.DEVRALINDI,
    )
    tawnt.acquire(min_hiz, 30, kaynak=tawnt.VARSAYILDI)
    tawnt.acquire(hedef_hiz, 45, kaynak=tawnt.VARSAYILDI)

    tawnt.preacquire(max_pwm, kare, perspektif, min_hiz, hedef_hiz)
    value = tawnt.deger(max_pwm)
    corrected, moved = tawnt.differenceSkew(
        [(0, 0), (640, 0), (0, 480), (639, 479)],
        (640, 480),
    )
    assert moved and corrected[-1] == (640, 480)

    if verbose:
        print(tawnt.report())
    return value


def offline_profile_lesson(verbose: bool = True) -> bool:
    """OFFLINE profilinde varsayımların öğretici test için kabulünü gösterir."""

    _say(
        verbose,
        "2. Profiller",
        "OFFLINE bilgisayar testidir, BENCH kontrollü masa testidir, "
        "LIVE gerçek araç için en sıkı yazılım profilidir.",
    )
    tawnt.sifirla()
    test_speed = tawnt.defineValue("TEST_SPEED", min=0, max=100)
    tawnt.recordValue(test_speed, 20, source=tawnt.VARSAYILDI)
    summary = tawnt.validateBeforeStart(profile=tawnt.OFFLINE)
    accepted = summary["state"] == tawnt.READY_UNARMED
    if verbose:
        print("OFFLINE varsayımı kabul etti:", accepted)
        print("BENCH profil sabiti:", tawnt.BENCH)
    return accepted


def live_safety_lesson(workdir: Path, verbose: bool = True) -> DemoResult:
    """V2 değer, evre, watchdog, motor kapısı ve kilit akışını gösterir."""

    _say(
        verbose,
        "3. V2 güvenlik akışı",
        "Bu bölüm LIVE kurallarını kullanır fakat sürücü tamamen sahtedir.",
    )
    tawnt.sifirla()
    driver = FakeMotorDriver()

    @tawnt.onShutdown
    def stop_fake_driver() -> None:
        driver.stop()

    max_pwm = tawnt.defineValue(
        "MAX_PWM",
        min=0,
        max=100,
        preferred=57,
        critical=True,
        aciklama="Sahte motor komutu üst sınırı",
    )
    camera_width = tawnt.defineValue("CAMERA_WIDTH", min=1)
    perspective = tawnt.defineValue("PERSPECTIVE_POINTS")
    min_speed = tawnt.defineValue("MIN_SPEED", min=0, max=100)
    target_speed = tawnt.defineValue("TARGET_SPEED", min=0, max=100)
    max_speed = tawnt.defineValue("MAX_SPEED", min=0, max=100)

    tawnt.identifyRuntimeType(max_pwm, "% PWM")
    tawnt.identifyRuntimeType(min_speed, "% PWM")
    tawnt.identifyRuntimeType(target_speed, "% PWM")
    tawnt.identifyRuntimeType(max_speed, "% PWM")
    tawnt.dependsOn(perspective, camera_width)
    tawnt.siblingIntAppr(min_speed, "<=", target_speed, "<=", max_speed)
    tawnt.requireMeasured(max_pwm, profiles=(tawnt.LIVE,))

    tawnt.recordValue(
        max_pwm,
        57,
        source=tawnt.OLCULDU,
        human="Egemen",
        date="2026-08-06",
        note="EĞİTİM VERİSİDİR; gerçek ölçüm kanıtı değildir.",
    )
    tawnt.recordValue(camera_width, 640, source=tawnt.DEVRALINDI)
    tawnt.recordValue(
        perspective,
        [(0, 0), (639, 0), (0, 479), (639, 479)],
        source=tawnt.DEVRALINDI,
    )
    tawnt.recordValue(min_speed, 30, source=tawnt.VARSAYILDI)
    tawnt.recordValue(target_speed, 45, source=tawnt.VARSAYILDI)
    tawnt.recordValue(max_speed, 57, source=tawnt.VARSAYILDI)

    fault_path = workdir / "fake_fault.json"
    tawnt.configureFaultStore(fault_path)

    camera_watchdog = tawnt.defineWatchdog("fake_camera", timeout_seconds=60.0)
    tawnt.heartbeat(camera_watchdog)
    tawnt.checkWatchdogs((camera_watchdog,))

    tawnt.definePhase(
        "LANE_FOLLOWING",
        motion_allowed=True,
        max_pwm=tawnt.deger(max_pwm),
        max_difference=30,
        max_slew=60,
        required_values=(max_pwm, perspective),
        required_watchdogs=(camera_watchdog,),
    )
    tawnt.definePhase(
        "STOPPED",
        motion_allowed=False,
        max_pwm=0,
        allowed_from=("LANE_FOLLOWING",),
    )

    tawnt.validateBeforeStart(profile=tawnt.LIVE)
    tawnt.seal()
    sealed_state = tawnt.valueState(max_pwm)

    tawnt.enterPhase("LANE_FOLLOWING")
    tawnt.validatePhase("LANE_FOLLOWING")
    tawnt.arm(
        "Egemen",
        live_hardware_authorized=True,
        final_confirmation=True,
    )
    assert tawnt.systemState() == tawnt.ARMED
    assert tawnt.isMotionAllowed() and tawnt.pwmSerbestMi()

    command = tawnt.validateMotorCommand(40, 45, phase="LANE_FOLLOWING")
    driver.apply_validated(command)

    tawnt.flushPWM("Öğretici geçici duruş", evre="LANE_FOLLOWING")
    assert tawnt.systemState() == tawnt.MUTED
    tawnt.enterPhase("STOPPED")
    assert not tawnt.isMotionAllowed()
    tawnt.evreDegisti("LANE_FOLLOWING")
    assert tawnt.isMotionAllowed()

    tawnt.disarm("Öğretici yeniden-arm örneği")
    tawnt.arm(
        "Egemen",
        live_hardware_authorized=True,
        final_confirmation=True,
    )

    tawnt.latchFault("Öğretici sensör hatası", "Gerçek sensör yoktur")
    latched_state = tawnt.systemState()
    assert tawnt.kilitDurumu() is not None
    assert fault_path.exists()
    assert json.loads(fault_path.read_text(encoding="utf-8"))["active"] is True

    tawnt.resetFault("Egemen", motor_power_off=True)
    reset_state = tawnt.systemState()

    tawnt.heartbeat(camera_watchdog)
    tawnt.validateBeforeStart(profile=tawnt.LIVE)
    tawnt.seal()
    tawnt.enterPhase("LANE_FOLLOWING")
    tawnt.arm(
        "Egemen",
        live_hardware_authorized=True,
        final_confirmation=True,
    )

    before_invalid = len(driver.history)
    invalid_rejected = False
    try:
        tawnt.validateMotorCommand(500, 500, phase="LANE_FOLLOWING")
    except tawnt.TawntHatasi:
        invalid_rejected = True
    assert invalid_rejected
    assert all(pair == (0.0, 0.0) for pair in driver.history[before_invalid:])
    tawnt.resetFault("Egemen", motor_power_off=True)

    tawnt.declareUnexpectedSigint("Öğretici eski API kilidi")
    assert tawnt.systemState() == tawnt.LATCHED_FAULT
    tawnt.resetFault("Egemen", motor_power_off=True)

    scanner_dir = workdir / "scanner_case"
    scanner_dir.mkdir(exist_ok=True)
    (scanner_dir / "unsafe_example.py").write_text(
        "motor.value = 1.0\n", encoding="utf-8"
    )
    findings = tawnt.scanDirectMotorWrites(scanner_dir)

    if verbose:
        print("Doğrulanmış sahte komut:", command.left, command.right)
        print("Mühürlü değer durumu:", sealed_state)
        print("Aşırı komut reddedildi:", invalid_rejected)
        print("Statik tarama bulgusu:", findings)
        print("Sahte motor geçmişi:", driver.history)
        print("\n3awnt raporu:\n" + tawnt.report())

    result = DemoResult(
        legacy_value=57,
        offline_assumption_accepted=True,
        sealed_value_state=sealed_state,
        valid_command=(command.left, command.right),
        invalid_command_rejected=invalid_rejected,
        latched_state=latched_state,
        reset_state=reset_state,
        scanner_findings=len(findings),
        fake_motor_history=tuple(driver.history),
        final_module_state=tawnt.BOOT,
    )

    tawnt.sifirla()
    assert tawnt.systemState() == tawnt.BOOT
    return result
