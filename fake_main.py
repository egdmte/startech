# -*- coding: utf-8 -*-
"""3awnt için TAMAMEN SAHTE ve öğretici bir ``main.py`` örneği.

UYARI
=====
Bu dosya gerçek aracın ``main.py`` dosyası değildir. GPIO, Raspberry Pi, kamera,
``surucu.py`` veya gerçek motor kütüphanesi içe aktarmaz. ``FakeMotorDriver`` yalnızca
aldığı sayıları bir Python listesine yazar. Bu nedenle örneği bilgisayarda çalıştırmak
fiziksel araca komut göndermez.

Amaç, 3awnt yöntemlerinin hangi sırayla ve neden kullanıldığını lise öğrencilerinin
izleyebileceği küçük dersler hâlinde göstermektir. Buradaki insan adları ve
``motor_power_off=True`` gibi bilgiler birer yazılım beyanıdır; fiziksel kanıt değildir.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import tempfile

import tawnt


@dataclass(frozen=True)
class DemoResult:
    """Testin, ekrana yazılan cümleleri okumadan sonucu denetlemesini sağlar."""

    legacy_value: int
    offline_assumption_accepted: bool
    sealed_value_state: str
    valid_command: tuple[float, float]
    invalid_command_rejected: bool
    latched_state: str
    reset_state: str
    scanner_findings: int
    fake_motor_history: tuple[tuple[float, float], ...]
    final_module_state: str


class FakeMotorDriver:
    """Gerçek motora dokunmayan, yalnız bellek içinde kayıt tutan sahte sürücü."""

    def __init__(self) -> None:
        self.history: list[tuple[float, float]] = []

    def apply_validated(self, command: tawnt.ValidatedMotorCommand) -> None:
        """Yalnız 3awnt'ın doğruladığı komut nesnesini kabul eder."""

        if not isinstance(command, tawnt.ValidatedMotorCommand):
            raise TypeError(
                "FakeMotorDriver ham sayı kabul etmez; önce validateMotorCommand çağır."
            )
        self.history.append((command.left, command.right))

    def stop(self) -> None:
        """Sahte çıkışa sıfır yazar; fiziksel duruş iddiasında bulunmaz."""

        self.history.append((0.0, 0.0))


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
    tawnt.sifirla()  # Yalnız bu eğitim demosunda dersler birbirine karışmasın diye.

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

    # differenceSkew yalnız 1 piksellik köşe farkını düzeltebilir.
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

    # onShutdown: 3awnt duruş istediğinde sahte sürücünün sıfır yazmasını ister.
    @tawnt.onShutdown
    def stop_fake_driver() -> None:
        driver.stop()

    # defineValue: önce ad ve kurallar tanımlanır.
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

    # dependsOn: çözünürlük değişirse perspektif noktaları STALE olur.
    tawnt.dependsOn(perspective, camera_width)
    # siblingIntAppr: hızların birlikte mantıklı sıralanmasını ister.
    tawnt.siblingIntAppr(
        min_speed, "<=", target_speed, "<=", max_speed
    )
    # requireMeasured: LIVE profilinde MAX_PWM varsayım olamaz.
    tawnt.requireMeasured(max_pwm, profiles=(tawnt.LIVE,))

    # recordValue: değer, kaynak ve insan beyanı kayda girer.
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

    # Kalıcı kilit dosyası yalnız bu geçici çalışma klasörüne yazılır.
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

    # validateBeforeStart doğrular; seal doğrulanmış değerleri kilitler.
    tawnt.validateBeforeStart(profile=tawnt.LIVE)
    tawnt.seal()
    sealed_state = tawnt.valueState(max_pwm)

    # Evre seçimi arming değildir. arm ayrıca açık insan beyanı ister.
    tawnt.enterPhase("LANE_FOLLOWING")
    tawnt.validatePhase("LANE_FOLLOWING")
    tawnt.arm(
        "Egemen",
        live_hardware_authorized=True,
        final_confirmation=True,
    )
    assert tawnt.systemState() == tawnt.ARMED
    assert tawnt.isMotionAllowed() and tawnt.pwmSerbestMi()

    # Ham sayılar sürücüye verilmez. Önce doğrulanmış komut nesnesi alınır.
    requested_left = 40
    requested_right = 45
    command = tawnt.validateMotorCommand(
        requested_left, requested_right, phase="LANE_FOLLOWING"
    )
    driver.apply_validated(command)

    # flushPWM geçici susturur. Farklı evreye geçince geçici susturma kalkabilir.
    tawnt.flushPWM("Öğretici geçici duruş", evre="LANE_FOLLOWING")
    assert tawnt.systemState() == tawnt.MUTED
    tawnt.enterPhase("STOPPED")
    assert not tawnt.isMotionAllowed()
    # evreDegisti eski uyumluluk adıdır; tanımlı evrede enterPhase'i kullanır.
    tawnt.evreDegisti("LANE_FOLLOWING")
    assert tawnt.isMotionAllowed()

    # disarm her zaman sahte sıfır çıkışı ister; sonra tekrar açık arm gerekir.
    tawnt.disarm("Öğretici yeniden-arm örneği")
    tawnt.arm(
        "Egemen",
        live_hardware_authorized=True,
        final_confirmation=True,
    )

    # latchFault ciddi kilittir ve JSON'a yazılır.
    tawnt.latchFault("Öğretici sensör hatası", "Gerçek sensör yoktur")
    latched_state = tawnt.systemState()
    assert tawnt.kilitDurumu() is not None
    assert fault_path.exists()
    assert json.loads(fault_path.read_text(encoding="utf-8"))["active"] is True

    # resetFault fiziksel anahtarı okuyamaz; insanın beyanını şart koşar.
    tawnt.resetFault("Egemen", motor_power_off=True)
    reset_state = tawnt.systemState()

    # Reset doğrudan ARMED yapmaz. Yeniden doğrulama ve arming gerekir.
    tawnt.heartbeat(camera_watchdog)
    tawnt.validateBeforeStart(profile=tawnt.LIVE)
    tawnt.seal()
    tawnt.enterPhase("LANE_FOLLOWING")
    tawnt.arm(
        "Egemen",
        live_hardware_authorized=True,
        final_confirmation=True,
    )

    # Aşırı komut gerçek sürücüye ulaşmadan reddedilir ve LIVE kilidi üretir.
    before_invalid = len(driver.history)
    invalid_rejected = False
    deliberately_invalid_pwm = 500
    try:
        tawnt.validateMotorCommand(
            deliberately_invalid_pwm,
            deliberately_invalid_pwm,
            phase="LANE_FOLLOWING",
        )
    except tawnt.TawntHatasi:
        invalid_rejected = True
    assert invalid_rejected
    # Yalnız shutdown callback'inin sahte (0, 0) kaydı eklenmiş olabilir.
    assert all(pair == (0.0, 0.0) for pair in driver.history[before_invalid:])
    tawnt.resetFault("Egemen", motor_power_off=True)

    # Eski ad: gerçek SIGINT yakalamaz; yalnız ciddi kilit oluşturur.
    tawnt.declareUnexpectedSigint("Öğretici eski API kilidi")
    assert tawnt.systemState() == tawnt.LATCHED_FAULT
    tawnt.resetFault("Egemen", motor_power_off=True)

    # Statik tarama, geçici klasördeki açıkça tehlikeli örneği bulur.
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

    history = tuple(driver.history)
    result = DemoResult(
        legacy_value=57,
        offline_assumption_accepted=True,
        sealed_value_state=sealed_state,
        valid_command=(command.left, command.right),
        invalid_command_rejected=invalid_rejected,
        latched_state=latched_state,
        reset_state=reset_state,
        scanner_findings=len(findings),
        fake_motor_history=history,
        final_module_state=tawnt.BOOT,
    )

    # Eğitim programı bittiğinde süreç-içi örnek durumunu da temizle.
    tawnt.sifirla()
    assert tawnt.systemState() == tawnt.BOOT
    return result


def run_demo(workdir: Path | None = None, verbose: bool = True) -> DemoResult:
    """Bütün dersleri çalıştırır; gerçek donanımla hiçbir bağlantı kurmaz."""

    legacy_value = legacy_names_lesson(verbose=verbose)
    offline_accepted = offline_profile_lesson(verbose=verbose)

    if workdir is None:
        with tempfile.TemporaryDirectory(prefix="3awnt_fake_main_") as temp:
            result = live_safety_lesson(Path(temp), verbose=verbose)
    else:
        workdir = Path(workdir)
        workdir.mkdir(parents=True, exist_ok=True)
        result = live_safety_lesson(workdir, verbose=verbose)

    # Önceki derslerin sonuçlarını da tek sonuç nesnesine açıkça taşı.
    return DemoResult(
        legacy_value=legacy_value,
        offline_assumption_accepted=offline_accepted,
        sealed_value_state=result.sealed_value_state,
        valid_command=result.valid_command,
        invalid_command_rejected=result.invalid_command_rejected,
        latched_state=result.latched_state,
        reset_state=result.reset_state,
        scanner_findings=result.scanner_findings,
        fake_motor_history=result.fake_motor_history,
        final_module_state=tawnt.systemState(),
    )


def main() -> int:
    print("3awnt SAHTE EĞİTİM PROGRAMI — GPIO VE GERÇEK MOTOR YOK")
    result = run_demo(verbose=True)
    print("\n=== SONUÇ ===")
    print("Bütün örnek dersler güvenli sahte sürücüyle tamamlandı.")
    print("Son 3awnt durumu:", result.final_module_state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
