"""
STARTECH-ARDA (ADAM)
Araç Rota ve Davranış Analizi
Autonomous Driving Analysis Module

ARDA is the application entry point. This scaffold presents truthful startup state,
supports simulation work away from the car, and refuses vehicle mode until the
hardware integration receives its own reviewed implementation.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
import os
from pathlib import Path
import sys
from typing import Callable, Sequence, TextIO

if __package__ in {None, ""}:
    repository_root = str(Path(__file__).resolve().parent.parent)
    if repository_root not in sys.path:
        sys.path.insert(0, repository_root)
    from arac.durum import EventType, StateEvent, StateMachine, VehicleState
    from arac.cli_ui import MenuOption, TerminalUI
    from arac.goruntu import SimulatedVisionAnalyzer
    from arac.goz import (
        CameraError,
        CameraProbeResult,
        FramePacket,
        SequenceCamera,
        build_preferred_camera,
        probe_camera,
    )
    from arac.kamera_oturumu import (
        MAX_SESSION_FRAMES,
        PIXEL_FORMAT,
        ReplaySummary,
        SessionManifest,
        inspect_recorded_session,
        record_camera_session,
    )
    from arac.kayit import MemoryBlackBox, RecordKind
    from arac.surucu import BlockedMotorDriver
else:
    from .durum import EventType, StateEvent, StateMachine, VehicleState
    from .cli_ui import MenuOption, TerminalUI
    from .goruntu import SimulatedVisionAnalyzer
    from .goz import (
        CameraError,
        CameraProbeResult,
        FramePacket,
        SequenceCamera,
        build_preferred_camera,
        probe_camera,
    )
    from .kamera_oturumu import (
        MAX_SESSION_FRAMES,
        PIXEL_FORMAT,
        ReplaySummary,
        SessionManifest,
        inspect_recorded_session,
        record_camera_session,
    )
    from .kayit import MemoryBlackBox, RecordKind
    from .surucu import BlockedMotorDriver


APP_VERSION = "0.1.0-scaffold"
EXIT_OK = 0
EXIT_NOT_READY = 2
EXIT_INTERRUPTED = 130

SIMULATION = "simulation"
VEHICLE = "vehicle"
SUPPORTED_MODES = (SIMULATION, VEHICLE)
SUPPORTED_LANGUAGES = ("tr", "en")

TAWNT_FACE = "[o_o]"


TEXT = {
    "en": {
        "title": "Autonomous Driving Analysis Module",
        "turkish_title": "Arac Rota ve Davranis Analizi",
        "mode": "MODE",
        "language": "LANGUAGE",
        "hardware": "HARDWARE",
        "simulation": "SIMULATION",
        "vehicle": "VEHICLE",
        "english": "ENGLISH",
        "turkish": "TURKISH",
        "disconnected": "NOT CONNECTED",
        "state_title": "STARTUP STATE",
        "ready": "READY",
        "simulated": "SIMULATED",
        "blocked": "BLOCKED",
        "pending": "PENDING",
        "cli_label": "ARDA command interface",
        "cli_detail": "Arguments parsed; no driving loop has started.",
        "camera_label": "KASIM/CAMILA camera source",
        "camera_simulated": "A deterministic in-memory frame source is available.",
        "camera_live_pending": (
            "No live source is accepted yet; USB/Pi selection happens when the finite action starts."
        ),
        "camera_replay_pending": (
            "The stored session has not been opened or integrity-checked yet."
        ),
        "camera_missing": "No physical camera provider is connected.",
        "vision_label": "KEREM/CORA vision analyzer",
        "vision_simulated": "Explicit simulation payloads are validated conservatively.",
        "vision_missing": "No physical vision analyzer is connected.",
        "state_label": "DORA/SARA state machine",
        "state_simulated": "Deterministic transitions are available without hardware.",
        "state_missing": "Vehicle-state integration has not been reviewed on the car.",
        "log_label": "KADER/BLAIR black box",
        "log_simulated": "The startup probe records evidence in memory only.",
        "log_missing": "A reviewed on-car log location has not been configured.",
        "motor_label": "OSMAN/MATT motor output",
        "motor_detail": "No physical motor command can leave this scaffold.",
        "tawnt_label": "Tawnt (3awnt) safety layer",
        "tawnt_detail": "Integration awaits separate review; no safety claim is made.",
        "tawnt_standby": "Tawnt is watching the paperwork, not the car.",
        "prompt": "Press Enter to run the selected finite operation, or Ctrl+C to exit.",
        "auto": "Prompt skipped. Automatic vehicle arming remains impossible.",
        "camera_probe_start": (
            "Checking USB camera {index} first, then Raspberry Pi camera if unavailable."
        ),
        "camera_probe_ok": (
            "Camera check passed: source={source}, frames={frames}, "
            "resolution={width}x{height}, elapsed={elapsed:.3f}s."
        ),
        "camera_probe_failed": "Camera check failed closed: {error}",
        "menu_title": "ARDA CAMERA LAB",
        "menu_simulation": "Run the bounded simulation self-check",
        "menu_check": "Check a live camera without saving frames",
        "menu_record": "Record a finite camera session",
        "menu_replay": "Validate and replay a recorded session",
        "menu_exit": "Exit without running an operation",
        "menu_prompt": "Choose 1-5: ",
        "menu_invalid": "Choose one of the displayed numbers.",
        "path_prompt_record": "New session directory: ",
        "path_prompt_replay": "Existing session directory: ",
        "path_invalid": "A non-empty directory path is required.",
        "frames_prompt": "Frame count [120]: ",
        "frames_invalid": "Enter an integer between 1 and 30000.",
        "menu_cancelled": "Menu closed; no camera or motor action was taken.",
        "record_start": (
            "Recording a finite session: USB camera {index} first, then Raspberry Pi."
        ),
        "record_failed": "Camera recording failed closed: {error}",
        "record_complete": "CAMERA SESSION COMPLETE",
        "replay_start": "Validating and replaying every stored frame.",
        "replay_failed": "Recorded session was rejected: {error}",
        "replay_complete": "RECORDED SESSION VERIFIED",
        "session_id": "session",
        "session_path": "directory",
        "session_source": "source",
        "session_frames": "frames",
        "session_resolution": "resolution",
        "session_elapsed": "timeline",
        "session_fps": "observed FPS",
        "session_warnings": "warnings",
        "session_warning_line": "Warning: {warning}",
        "progress_record": "recording {source}",
        "progress_replay": "replaying {source}",
        "self_check_ok": (
            "Bounded self-check passed: DORA={state}, records={records}, motor={motor}."
        ),
        "self_check_failed": "Simulation self-check failed closed: {error}",
        "simulation_ready": (
            "ARDA simulation contracts are ready. No continuous driving loop was started."
        ),
        "vehicle_refused": (
            "Vehicle mode refused: reviewed camera, configuration and motor adapters do not exist yet."
        ),
        "interrupted": "Startup cancelled; no hardware action was taken.",
        "no_input": "Startup refused because confirmation input was unavailable.",
    },
    "tr": {
        "title": "Otonom Sürüş Analiz Modülü",
        "turkish_title": "Araç Rota ve Davranış Analizi",
        "mode": "MOD",
        "language": "DİL",
        "hardware": "DONANIM",
        "simulation": "SIMULASYON",
        "vehicle": "ARAC",
        "english": "İNGİLİZCE",
        "turkish": "TÜRKÇE",
        "disconnected": "BAĞLI DEĞİL",
        "state_title": "BAŞLANGIÇ DURUMU",
        "ready": "HAZIR",
        "simulated": "BENZETİM",
        "blocked": "KAPALI",
        "pending": "BEKLİYOR",
        "cli_label": "ARDA komut arayüzü",
        "cli_detail": "Argümanlar okundu; sürüş döngüsü başlatılmadı.",
        "camera_label": "KASIM/CAMILA kamera kaynağı",
        "camera_simulated": "Belirlenmiş bellek içi kare kaynağı kullanılabilir.",
        "camera_live_pending": (
            "Henüz canlı kaynak kabul edilmedi; sonlu işlem başlarken USB/Pi seçilecek."
        ),
        "camera_replay_pending": (
            "Kayıtlı oturum henüz açılmadı veya bütünlük denetiminden geçmedi."
        ),
        "camera_missing": "Fiziksel kamera sağlayıcısı bağlı değil.",
        "vision_label": "KEREM/CORA görüntü çözümleyicisi",
        "vision_simulated": "Açık simülasyon verileri ihtiyatlı biçimde doğrulanır.",
        "vision_missing": "Fiziksel görüntü çözümleyicisi bağlı değil.",
        "state_label": "DORA/SARA durum makinesi",
        "state_simulated": "Belirlenmiş geçişler donanım olmadan kullanılabilir.",
        "state_missing": "Araç durum entegrasyonu araç üzerinde incelenmedi.",
        "log_label": "KADER/BLAIR karakutusu",
        "log_simulated": "Başlangıç denetimi kanıtları yalnızca belleğe yazar.",
        "log_missing": "İncelenmiş araç içi kayıt konumu ayarlanmadı.",
        "motor_label": "OSMAN/MATT motor çıkışı",
        "motor_detail": "Bu iskeletten fiziksel motor komutu çıkamaz.",
        "tawnt_label": "Tawnt (3awnt) güvenlik katmanı",
        "tawnt_detail": "Entegrasyon ayrı inceleme bekliyor; güvenlik iddiası yoktur.",
        "tawnt_standby": "Tawnt arabayı değil, şimdilik evrakları izliyor.",
        "prompt": "Seçilen sonlu işlemi çalıştırmak için Enter'a basın; çıkmak için Ctrl+C.",
        "auto": "Onay beklemesi atlandı. Otomatik araç arm işlemi hâlâ imkânsız.",
        "camera_probe_start": (
            "Önce USB kamera {index}, kullanılamazsa Raspberry Pi kamerası denetleniyor."
        ),
        "camera_probe_ok": (
            "Kamera denetimi geçti: kaynak={source}, kare={frames}, "
            "çözünürlük={width}x{height}, süre={elapsed:.3f}sn."
        ),
        "camera_probe_failed": "Kamera denetimi güvenli biçimde durdu: {error}",
        "menu_title": "ARDA KAMERA LABORATUVARI",
        "menu_simulation": "Sınırlı simülasyon öz denetimini çalıştır",
        "menu_check": "Kare kaydetmeden canlı kamerayı denetle",
        "menu_record": "Sonlu bir kamera oturumu kaydet",
        "menu_replay": "Kayıtlı bir oturumu doğrula ve yeniden oynat",
        "menu_exit": "İşlem çalıştırmadan çık",
        "menu_prompt": "1-5 arasında seçim yapın: ",
        "menu_invalid": "Gösterilen sayılardan birini seçin.",
        "path_prompt_record": "Yeni oturum klasörü: ",
        "path_prompt_replay": "Mevcut oturum klasörü: ",
        "path_invalid": "Boş olmayan bir klasör yolu gereklidir.",
        "frames_prompt": "Kare sayısı [120]: ",
        "frames_invalid": "1 ile 30000 arasında bir tam sayı girin.",
        "menu_cancelled": "Menü kapatıldı; kamera veya motor işlemi yapılmadı.",
        "record_start": (
            "Sonlu oturum kaydı: önce USB kamera {index}, sonra Raspberry Pi denenir."
        ),
        "record_failed": "Kamera kaydı güvenli biçimde durdu: {error}",
        "record_complete": "KAMERA OTURUMU TAMAMLANDI",
        "replay_start": "Saklanan bütün kareler doğrulanıp yeniden oynatılıyor.",
        "replay_failed": "Kayıtlı oturum reddedildi: {error}",
        "replay_complete": "KAYITLI OTURUM DOĞRULANDI",
        "session_id": "oturum",
        "session_path": "klasör",
        "session_source": "kaynak",
        "session_frames": "kare",
        "session_resolution": "çözünürlük",
        "session_elapsed": "zaman çizgisi",
        "session_fps": "gözlenen FPS",
        "session_warnings": "uyarı",
        "session_warning_line": "Uyarı: {warning}",
        "progress_record": "kaydediliyor {source}",
        "progress_replay": "oynatılıyor {source}",
        "self_check_ok": (
            "Sınırlı öz denetim geçti: DORA={state}, kayıt={records}, motor={motor}."
        ),
        "self_check_failed": "Simülasyon öz denetimi güvenli biçimde durdu: {error}",
        "simulation_ready": (
            "ARDA simülasyon sözleşmeleri hazır. Sürekli sürüş döngüsü başlatılmadı."
        ),
        "vehicle_refused": (
            "Araç modu reddedildi: incelenmiş kamera, ayar ve motor bağdaştırıcıları henüz yok."
        ),
        "interrupted": "Başlangıç iptal edildi; hiçbir donanım işlemi yapılmadı.",
        "no_input": "Onay girdisi bulunamadığı için başlangıç reddedildi.",
    },
}


@dataclass(frozen=True)
class StartupOptions:
    """Validated command-line choices used to render and start the scaffold."""

    mode: str
    language: str
    automatic: bool
    color: bool
    check_camera: bool
    record_camera: Path | None
    replay_camera: Path | None
    interactive: bool
    usb_index: int
    camera_frames: int
    record_frames: int


@dataclass(frozen=True)
class StartupCheck:
    """One truthful line in ARDA's startup-state panel."""

    state: str
    label: str
    detail: str


@dataclass(frozen=True)
class SimulationProbeResult:
    """Truthful outcome of one finite, hardware-free startup exercise."""

    final_state: VehicleState
    observation_valid: bool
    record_count: int
    motor_state: str
    stop_request_count: int


def _non_negative_integer(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("value must be an integer") from exc
    if parsed < 0:
        raise argparse.ArgumentTypeError("value cannot be negative")
    return parsed


def _camera_frame_count(value: str) -> int:
    parsed = _non_negative_integer(value)
    if not 1 <= parsed <= 30:
        raise argparse.ArgumentTypeError("camera frame count must be between 1 and 30")
    return parsed


def _record_frame_count(value: str) -> int:
    parsed = _non_negative_integer(value)
    if not 1 <= parsed <= MAX_SESSION_FRAMES:
        raise argparse.ArgumentTypeError(
            f"record frame count must be between 1 and {MAX_SESSION_FRAMES}"
        )
    return parsed


def build_parser() -> argparse.ArgumentParser:
    """Build ARDA's hardware-free command-line interface."""

    parser = argparse.ArgumentParser(
        prog="startech-arda",
        description="STARTECH-ARDA (ADAM) startup scaffold",
    )
    parser.add_argument(
        "--mode",
        choices=SUPPORTED_MODES,
        default=SIMULATION,
        help="simulation is safe; vehicle currently refuses to start",
    )
    parser.add_argument(
        "--language",
        "--lang",
        choices=SUPPORTED_LANGUAGES,
        default="tr",
        help="CLI language (default: tr)",
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="skip the Enter prompt; this never arms the vehicle",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="disable ANSI terminal colors",
    )
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument(
        "--check-camera",
        action="store_true",
        help="capture a few real frames: USB first, then Raspberry Pi",
    )
    actions.add_argument(
        "--record-camera",
        type=Path,
        metavar="DIRECTORY",
        help="record a finite, non-overwriting camera session",
    )
    actions.add_argument(
        "--replay-camera",
        type=Path,
        metavar="DIRECTORY",
        help="verify and replay every frame in a recorded session",
    )
    actions.add_argument(
        "--interactive",
        action="store_true",
        help="open the numbered camera-lab menu",
    )
    parser.add_argument(
        "--usb-index",
        type=_non_negative_integer,
        default=0,
        help="OpenCV USB camera device index (default: 0)",
    )
    parser.add_argument(
        "--camera-frames",
        type=_camera_frame_count,
        default=3,
        help="frames captured by the finite diagnostic, 1-30 (default: 3)",
    )
    parser.add_argument(
        "--record-frames",
        type=_record_frame_count,
        default=120,
        help="frames stored by --record-camera, 1-30000 (default: 120)",
    )
    parser.add_argument("--version", action="version", version=APP_VERSION)
    return parser


def parse_options(argv: Sequence[str] | None = None) -> StartupOptions:
    """Parse command-line values into a small immutable startup record."""

    args = build_parser().parse_args(argv)
    return StartupOptions(
        mode=args.mode,
        language=args.language,
        automatic=args.auto,
        color=not args.no_color,
        check_camera=args.check_camera,
        record_camera=args.record_camera,
        replay_camera=args.replay_camera,
        interactive=args.interactive,
        usb_index=args.usb_index,
        camera_frames=args.camera_frames,
        record_frames=args.record_frames,
    )


def _supports_color(stream: TextIO, requested: bool) -> bool:
    """Use color only on an interactive terminal that has not opted out."""

    if not requested or os.environ.get("NO_COLOR") is not None:
        return False
    is_a_terminal = getattr(stream, "isatty", lambda: False)
    return bool(is_a_terminal())


def _configure_utf8_terminal() -> None:
    """Prefer UTF-8 for the Turkish CLI without assuming a specific terminal."""

    for stream in (sys.stdin, sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if not callable(reconfigure):
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            # Redirected or embedded streams may reject reconfiguration.
            continue


def _text(language: str, key: str) -> str:
    return TEXT[language][key]


def _build_checks(options: StartupOptions) -> tuple[StartupCheck, ...]:
    language = options.language
    simulated_or_blocked = "simulated" if options.mode == SIMULATION else "blocked"

    def mode_detail(simulation_key: str, vehicle_key: str) -> str:
        return simulation_key if options.mode == SIMULATION else vehicle_key

    if options.check_camera or options.record_camera is not None:
        camera_state = "pending"
        camera_detail = "camera_live_pending"
    elif options.replay_camera is not None:
        camera_state = "pending"
        camera_detail = "camera_replay_pending"
    else:
        camera_state = simulated_or_blocked
        camera_detail = mode_detail("camera_simulated", "camera_missing")

    return (
        StartupCheck(
            _text(language, "ready"),
            _text(language, "cli_label"),
            _text(language, "cli_detail"),
        ),
        StartupCheck(
            _text(language, camera_state),
            _text(language, "camera_label"),
            _text(language, camera_detail),
        ),
        StartupCheck(
            _text(language, simulated_or_blocked),
            _text(language, "vision_label"),
            _text(language, mode_detail("vision_simulated", "vision_missing")),
        ),
        StartupCheck(
            _text(language, simulated_or_blocked),
            _text(language, "state_label"),
            _text(language, mode_detail("state_simulated", "state_missing")),
        ),
        StartupCheck(
            _text(language, simulated_or_blocked),
            _text(language, "log_label"),
            _text(language, mode_detail("log_simulated", "log_missing")),
        ),
        StartupCheck(
            _text(language, "blocked"),
            _text(language, "motor_label"),
            _text(language, "motor_detail"),
        ),
        StartupCheck(
            _text(language, "pending"),
            _text(language, "tawnt_label"),
            _text(language, "tawnt_detail"),
        ),
    )


def run_simulation_probe() -> SimulationProbeResult:
    """Exercise every simulated boundary once without starting a control loop.

    The probe never validates, arms, or applies a motor command. Its driver is the
    fail-closed physical placeholder, and all black-box evidence remains in memory.
    """

    camera = SequenceCamera(
        [
            FramePacket(
                frame_id=0,
                captured_at=0.0,
                source="ARDA-startup-simulation",
                payload={
                    "valid": True,
                    "lane_error": 0.0,
                    "obstacle": False,
                    "confidence": 1.0,
                },
            )
        ]
    )
    camera.open()
    try:
        frame = camera.read_frame()
    finally:
        camera.close()

    observation = SimulatedVisionAnalyzer().analyze(frame)
    states = StateMachine()
    states.apply(StateEvent(EventType.BEGIN_SELF_TEST, occurred_at=1.0))
    snapshot = states.apply(StateEvent(EventType.SELF_TEST_PASSED, occurred_at=2.0))

    black_box = MemoryBlackBox("arda-startup-probe")
    black_box.append(
        RecordKind.FRAME,
        "KASIM",
        {"source": frame.source},
        frame_id=frame.frame_id,
        recorded_at=0.0,
    )
    black_box.append(
        RecordKind.OBSERVATION,
        "KEREM",
        {
            "valid": observation.valid,
            "lane_error": observation.lane_error,
            "obstacle": observation.obstacle,
            "confidence": observation.confidence,
        },
        frame_id=observation.frame_id,
        recorded_at=1.0,
    )
    black_box.append(
        RecordKind.STATE,
        "DORA",
        {"state": snapshot.state.value, "revision": snapshot.revision},
        frame_id=frame.frame_id,
        recorded_at=2.0,
    )

    motor = BlockedMotorDriver()
    motor.stop("ARDA bounded startup probe")
    motor.close()

    return SimulationProbeResult(
        final_state=snapshot.state,
        observation_valid=observation.valid,
        record_count=len(black_box.records),
        motor_state="BLOCKED",
        stop_request_count=len(motor.stop_requests),
    )


def run_camera_diagnostic(options: StartupOptions) -> CameraProbeResult:
    """Run the explicit finite real-camera diagnostic without retaining images."""

    if not isinstance(options, StartupOptions):
        raise TypeError("camera diagnostic needs StartupOptions")
    camera = build_preferred_camera(options.usb_index)
    return probe_camera(camera, frame_count=options.camera_frames)


def run_camera_recording(
    options: StartupOptions,
    *,
    progress: Callable[[int, int, FramePacket], None] | None = None,
) -> SessionManifest:
    """Record exactly the requested live-camera frames and close the source."""

    if not isinstance(options, StartupOptions):
        raise TypeError("camera recording needs StartupOptions")
    if options.record_camera is None:
        raise ValueError("camera recording needs an output directory")
    camera = build_preferred_camera(options.usb_index)
    return record_camera_session(
        camera,
        options.record_camera,
        frame_count=options.record_frames,
        progress=progress,
    )


def run_replay_diagnostic(
    options: StartupOptions,
    *,
    progress: Callable[[int, int, FramePacket], None] | None = None,
) -> ReplaySummary:
    """Decode and integrity-check every frame in the requested stored session."""

    if not isinstance(options, StartupOptions):
        raise TypeError("camera replay needs StartupOptions")
    if options.replay_camera is None:
        raise ValueError("camera replay needs a session directory")
    return inspect_recorded_session(options.replay_camera, progress=progress)


def _render_header(console: TerminalUI, options: StartupOptions) -> None:
    language = options.language
    selected_mode = _text(language, options.mode)
    selected_language = _text(
        language, "turkish" if language == "tr" else "english"
    )

    console.rule()
    console.panel_line(" STARTECH // ARDA (ADAM) ", style=TerminalUI.BLUE)
    console.panel_line(_text(language, "title"))
    console.panel_line(_text(language, "turkish_title"), style=TerminalUI.MUTED)
    console.rule()
    console.panel_line(f"{_text(language, 'mode'):<12} {selected_mode}")
    console.panel_line(f"{_text(language, 'language'):<12} {selected_language}")
    console.panel_line(
        f"{_text(language, 'hardware'):<12} {_text(language, 'disconnected')}"
    )
    console.rule()


def _render_checks(console: TerminalUI, options: StartupOptions) -> None:
    console.write()
    console.write(_text(options.language, "state_title"))
    healthy_states = {
        _text(options.language, "ready"),
        _text(options.language, "simulated"),
    }
    for check in _build_checks(options):
        style = TerminalUI.GREEN if check.state in healthy_states else TerminalUI.YELLOW
        console.write(f"  [{check.state:<9}] {check.label}", style=style)
        console.write(f"              {check.detail}", style=TerminalUI.MUTED)

    console.write()
    console.write(
        f"  {TAWNT_FACE}  {_text(options.language, 'tawnt_standby')}",
        style=TerminalUI.MUTED,
    )


def _interactive_options(
    console: TerminalUI,
    options: StartupOptions,
    input_fn: Callable[[str], str],
) -> StartupOptions | None:
    """Collect one finite menu action without changing motor-mode decisions."""

    language = options.language
    choice = console.choose(
        _text(language, "menu_title"),
        (
            MenuOption("1", _text(language, "menu_simulation")),
            MenuOption("2", _text(language, "menu_check")),
            MenuOption("3", _text(language, "menu_record")),
            MenuOption("4", _text(language, "menu_replay")),
            MenuOption("5", _text(language, "menu_exit")),
        ),
        input_fn=input_fn,
        prompt=_text(language, "menu_prompt"),
        invalid_message=_text(language, "menu_invalid"),
    )
    base = replace(
        options,
        interactive=False,
        check_camera=False,
        record_camera=None,
        replay_camera=None,
    )
    if choice == "1":
        return base
    if choice == "2":
        return replace(base, check_camera=True)
    if choice == "3":
        path = console.ask_non_empty(
            _text(language, "path_prompt_record"),
            input_fn=input_fn,
            invalid_message=_text(language, "path_invalid"),
        )
        frame_count = console.ask_integer(
            _text(language, "frames_prompt"),
            input_fn=input_fn,
            minimum=1,
            maximum=MAX_SESSION_FRAMES,
            default=options.record_frames,
            invalid_message=_text(language, "frames_invalid"),
        )
        return replace(base, record_camera=Path(path), record_frames=frame_count)
    if choice == "4":
        path = console.ask_non_empty(
            _text(language, "path_prompt_replay"),
            input_fn=input_fn,
            invalid_message=_text(language, "path_invalid"),
        )
        return replace(base, replay_camera=Path(path))
    return None


def _progress_renderer(
    console: TerminalUI,
    language: str,
    text_key: str,
) -> Callable[[int, int, FramePacket], None]:
    """Render at most about fifty progress lines for very large recordings."""

    last_rendered = 0

    def render(current: int, total: int, packet: FramePacket) -> None:
        nonlocal last_rendered
        interval = max(1, total // 50)
        if current not in {1, total} and current - last_rendered < interval:
            return
        console.progress(
            current,
            total,
            _text(language, text_key).format(source=packet.source),
        )
        last_rendered = current

    return render


def _session_rows(
    language: str,
    path: Path,
    result: SessionManifest | ReplaySummary,
) -> tuple[tuple[str, object], ...]:
    return (
        (_text(language, "session_id"), result.session_id),
        (_text(language, "session_path"), path),
        (_text(language, "session_source"), result.source),
        (_text(language, "session_frames"), result.frame_count),
        (
            _text(language, "session_resolution"),
            f"{result.width}x{result.height} {getattr(result, 'pixel_format', PIXEL_FORMAT)}",
        ),
        (_text(language, "session_elapsed"), f"{result.elapsed_seconds:.3f}s"),
        (_text(language, "session_fps"), f"{result.observed_fps:.2f}"),
        (_text(language, "session_warnings"), len(result.warnings)),
    )


def _render_session_warnings(
    console: TerminalUI,
    language: str,
    warnings: tuple[str, ...],
) -> None:
    for warning in warnings:
        console.write(
            _text(language, "session_warning_line").format(warning=warning),
            style=TerminalUI.YELLOW,
        )


def run(
    argv: Sequence[str] | None = None,
    *,
    input_fn: Callable[[str], str] = input,
    output: TextIO = sys.stdout,
) -> int:
    """Run the safe ARDA scaffold and return a process-style exit code."""

    options = parse_options(argv)
    console = TerminalUI(output, _supports_color(output, options.color))
    _render_header(console, options)
    _render_checks(console, options)

    if options.mode == VEHICLE:
        console.write()
        console.write(
            _text(options.language, "vehicle_refused"), style=TerminalUI.RED
        )
        return EXIT_NOT_READY

    if options.interactive:
        try:
            selected_options = _interactive_options(console, options, input_fn)
        except KeyboardInterrupt:
            console.write()
            console.write(
                _text(options.language, "interrupted"), style=TerminalUI.YELLOW
            )
            return EXIT_INTERRUPTED
        except EOFError:
            console.write(_text(options.language, "no_input"), style=TerminalUI.RED)
            return EXIT_NOT_READY
        if selected_options is None:
            console.write()
            console.write(
                _text(options.language, "menu_cancelled"), style=TerminalUI.MUTED
            )
            return EXIT_OK
        options = selected_options
    else:
        console.write()
        if options.automatic:
            console.write(_text(options.language, "auto"), style=TerminalUI.YELLOW)
        else:
            console.write(_text(options.language, "prompt"))
            try:
                input_fn("")
            except KeyboardInterrupt:
                console.write()
                console.write(
                    _text(options.language, "interrupted"), style=TerminalUI.YELLOW
                )
                return EXIT_INTERRUPTED
            except EOFError:
                console.write(_text(options.language, "no_input"), style=TerminalUI.RED)
                return EXIT_NOT_READY

    if options.check_camera:
        console.write()
        console.write(
            _text(options.language, "camera_probe_start").format(
                index=options.usb_index
            ),
            style=TerminalUI.YELLOW,
        )
        try:
            camera_result = run_camera_diagnostic(options)
        except CameraError as exc:
            console.write(
                _text(options.language, "camera_probe_failed").format(error=str(exc)),
                style=TerminalUI.RED,
            )
            return EXIT_NOT_READY
        console.write(
            _text(options.language, "camera_probe_ok").format(
                source=camera_result.source,
                frames=camera_result.frame_count,
                width=camera_result.width,
                height=camera_result.height,
                elapsed=camera_result.elapsed_seconds,
            ),
            style=TerminalUI.GREEN,
        )

    if options.record_camera is not None:
        console.write()
        console.write(
            _text(options.language, "record_start").format(index=options.usb_index),
            style=TerminalUI.YELLOW,
        )
        try:
            session = run_camera_recording(
                options,
                progress=_progress_renderer(
                    console, options.language, "progress_record"
                ),
            )
        except KeyboardInterrupt:
            console.write()
            console.write(
                _text(options.language, "interrupted"), style=TerminalUI.YELLOW
            )
            return EXIT_INTERRUPTED
        except CameraError as exc:
            console.write(
                _text(options.language, "record_failed").format(error=str(exc)),
                style=TerminalUI.RED,
            )
            return EXIT_NOT_READY
        console.summary(
            _text(options.language, "record_complete"),
            _session_rows(options.language, options.record_camera, session),
            style=TerminalUI.GREEN,
        )
        _render_session_warnings(console, options.language, session.warnings)
        return EXIT_OK

    if options.replay_camera is not None:
        console.write()
        console.write(
            _text(options.language, "replay_start"), style=TerminalUI.YELLOW
        )
        try:
            replay = run_replay_diagnostic(
                options,
                progress=_progress_renderer(
                    console, options.language, "progress_replay"
                ),
            )
        except KeyboardInterrupt:
            console.write()
            console.write(
                _text(options.language, "interrupted"), style=TerminalUI.YELLOW
            )
            return EXIT_INTERRUPTED
        except CameraError as exc:
            console.write(
                _text(options.language, "replay_failed").format(error=str(exc)),
                style=TerminalUI.RED,
            )
            return EXIT_NOT_READY
        console.summary(
            _text(options.language, "replay_complete"),
            _session_rows(options.language, options.replay_camera, replay),
            style=TerminalUI.GREEN,
        )
        _render_session_warnings(console, options.language, replay.warnings)
        return EXIT_OK

    try:
        probe = run_simulation_probe()
    except Exception as exc:
        console.write()
        console.write(
            _text(options.language, "self_check_failed").format(error=str(exc)),
            style=TerminalUI.RED,
        )
        return EXIT_NOT_READY

    if (
        probe.final_state is not VehicleState.READY
        or not probe.observation_valid
        or probe.motor_state != "BLOCKED"
    ):
        console.write()
        console.write(
            _text(options.language, "self_check_failed").format(
                error="incomplete probe result"
            ),
            style=TerminalUI.RED,
        )
        return EXIT_NOT_READY

    console.write()
    console.write(
        _text(options.language, "self_check_ok").format(
            state=probe.final_state.value,
            records=probe.record_count,
            motor=probe.motor_state,
        ),
        style=TerminalUI.GREEN,
    )
    console.write(
        _text(options.language, "simulation_ready"), style=TerminalUI.GREEN
    )
    return EXIT_OK


def main() -> int:
    """Console-script entry point."""

    _configure_utf8_terminal()
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
