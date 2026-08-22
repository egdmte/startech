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
from dataclasses import dataclass
import os
from pathlib import Path
import sys
from typing import Callable, Sequence, TextIO

if __package__ in {None, ""}:
    repository_root = str(Path(__file__).resolve().parent.parent)
    if repository_root not in sys.path:
        sys.path.insert(0, repository_root)
    from arac.durum import EventType, StateEvent, StateMachine, VehicleState
    from arac.goruntu import SimulatedVisionAnalyzer
    from arac.goz import (
        CameraError,
        CameraProbeResult,
        FramePacket,
        SequenceCamera,
        build_preferred_camera,
        probe_camera,
    )
    from arac.kayit import MemoryBlackBox, RecordKind
    from arac.surucu import BlockedMotorDriver
else:
    from .durum import EventType, StateEvent, StateMachine, VehicleState
    from .goruntu import SimulatedVisionAnalyzer
    from .goz import (
        CameraError,
        CameraProbeResult,
        FramePacket,
        SequenceCamera,
        build_preferred_camera,
        probe_camera,
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
        "prompt": "Press Enter to open the simulation scaffold, or Ctrl+C to exit.",
        "auto": "Prompt skipped. Automatic vehicle arming remains impossible.",
        "camera_probe_start": (
            "Checking USB camera {index} first, then Raspberry Pi camera if unavailable."
        ),
        "camera_probe_ok": (
            "Camera check passed: source={source}, frames={frames}, "
            "resolution={width}x{height}, elapsed={elapsed:.3f}s."
        ),
        "camera_probe_failed": "Camera check failed closed: {error}",
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
        "prompt": "Simülasyon iskelesini açmak için Enter'a basın; çıkmak için Ctrl+C.",
        "auto": "Onay beklemesi atlandı. Otomatik araç arm işlemi hâlâ imkânsız.",
        "camera_probe_start": (
            "Önce USB kamera {index}, kullanılamazsa Raspberry Pi kamerası denetleniyor."
        ),
        "camera_probe_ok": (
            "Kamera denetimi geçti: kaynak={source}, kare={frames}, "
            "çözünürlük={width}x{height}, süre={elapsed:.3f}sn."
        ),
        "camera_probe_failed": "Kamera denetimi güvenli biçimde durdu: {error}",
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
    usb_index: int
    camera_frames: int


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


class Console:
    """Small terminal renderer with optional ANSI color and fixed-width panels."""

    WIDTH = 74
    RESET = "\033[0m"
    BLUE = "\033[1;44;37m"
    GREEN = "\033[1;32m"
    YELLOW = "\033[1;33m"
    RED = "\033[1;31m"
    MUTED = "\033[2m"

    def __init__(self, stream: TextIO, color: bool) -> None:
        self.stream = stream
        self.color = color

    def write(self, text: str = "", *, style: str = "") -> None:
        if self.color and style:
            text = f"{style}{text}{self.RESET}"
        print(text, file=self.stream)

    def rule(self) -> None:
        self.write("+" + "-" * (self.WIDTH - 2) + "+")

    def panel_line(self, text: str = "", *, style: str = "") -> None:
        available = self.WIDTH - 4
        clipped = text if len(text) <= available else text[: available - 3] + "..."
        self.write(f"| {clipped:<{available}} |", style=style)


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
    parser.add_argument(
        "--check-camera",
        action="store_true",
        help="capture a few real frames: USB first, then Raspberry Pi",
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
        usb_index=args.usb_index,
        camera_frames=args.camera_frames,
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

    return (
        StartupCheck(
            _text(language, "ready"),
            _text(language, "cli_label"),
            _text(language, "cli_detail"),
        ),
        StartupCheck(
            _text(language, simulated_or_blocked),
            _text(language, "camera_label"),
            _text(language, mode_detail("camera_simulated", "camera_missing")),
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


def _render_header(console: Console, options: StartupOptions) -> None:
    language = options.language
    selected_mode = _text(language, options.mode)
    selected_language = _text(
        language, "turkish" if language == "tr" else "english"
    )

    console.rule()
    console.panel_line(" STARTECH // ARDA (ADAM) ", style=Console.BLUE)
    console.panel_line(_text(language, "title"))
    console.panel_line(_text(language, "turkish_title"), style=Console.MUTED)
    console.rule()
    console.panel_line(f"{_text(language, 'mode'):<12} {selected_mode}")
    console.panel_line(f"{_text(language, 'language'):<12} {selected_language}")
    console.panel_line(
        f"{_text(language, 'hardware'):<12} {_text(language, 'disconnected')}"
    )
    console.rule()


def _render_checks(console: Console, options: StartupOptions) -> None:
    console.write()
    console.write(_text(options.language, "state_title"))
    healthy_states = {
        _text(options.language, "ready"),
        _text(options.language, "simulated"),
    }
    for check in _build_checks(options):
        style = Console.GREEN if check.state in healthy_states else Console.YELLOW
        console.write(f"  [{check.state:<9}] {check.label}", style=style)
        console.write(f"              {check.detail}", style=Console.MUTED)

    console.write()
    console.write(
        f"  {TAWNT_FACE}  {_text(options.language, 'tawnt_standby')}",
        style=Console.MUTED,
    )


def run(
    argv: Sequence[str] | None = None,
    *,
    input_fn: Callable[[str], str] = input,
    output: TextIO = sys.stdout,
) -> int:
    """Run the safe ARDA scaffold and return a process-style exit code."""

    options = parse_options(argv)
    console = Console(output, _supports_color(output, options.color))
    _render_header(console, options)
    _render_checks(console, options)

    if options.mode == VEHICLE:
        console.write()
        console.write(_text(options.language, "vehicle_refused"), style=Console.RED)
        return EXIT_NOT_READY

    console.write()
    if options.automatic:
        console.write(_text(options.language, "auto"), style=Console.YELLOW)
    else:
        console.write(_text(options.language, "prompt"))
        try:
            input_fn("")
        except KeyboardInterrupt:
            console.write()
            console.write(_text(options.language, "interrupted"), style=Console.YELLOW)
            return EXIT_INTERRUPTED
        except EOFError:
            console.write(_text(options.language, "no_input"), style=Console.RED)
            return EXIT_NOT_READY

    if options.check_camera:
        console.write()
        console.write(
            _text(options.language, "camera_probe_start").format(
                index=options.usb_index
            ),
            style=Console.YELLOW,
        )
        try:
            camera_result = run_camera_diagnostic(options)
        except CameraError as exc:
            console.write(
                _text(options.language, "camera_probe_failed").format(error=str(exc)),
                style=Console.RED,
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
            style=Console.GREEN,
        )

    try:
        probe = run_simulation_probe()
    except Exception as exc:
        console.write()
        console.write(
            _text(options.language, "self_check_failed").format(error=str(exc)),
            style=Console.RED,
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
            style=Console.RED,
        )
        return EXIT_NOT_READY

    console.write()
    console.write(
        _text(options.language, "self_check_ok").format(
            state=probe.final_state.value,
            records=probe.record_count,
            motor=probe.motor_state,
        ),
        style=Console.GREEN,
    )
    console.write(_text(options.language, "simulation_ready"), style=Console.GREEN)
    return EXIT_OK


def main() -> int:
    """Console-script entry point."""

    _configure_utf8_terminal()
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
