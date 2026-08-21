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
import sys
from typing import Callable, Sequence, TextIO


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
        "camera_simulated": "A simulator can be connected in a later slice.",
        "camera_missing": "No physical camera provider is connected.",
        "motor_label": "OSMAN/MATT motor output",
        "motor_detail": "No physical motor command can leave this scaffold.",
        "tawnt_label": "Tawnt (3awnt) safety layer",
        "tawnt_detail": "Integration awaits separate review; no safety claim is made.",
        "tawnt_standby": "Tawnt is watching the paperwork, not the car.",
        "prompt": "Press Enter to open the simulation scaffold, or Ctrl+C to exit.",
        "auto": "Prompt skipped. Automatic vehicle arming remains impossible.",
        "simulation_ready": (
            "ARDA simulation scaffold is ready. Camera and driving loops are not implemented."
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
        "camera_simulated": "Daha sonraki bir adımda simülatör bağlanabilir.",
        "camera_missing": "Fiziksel kamera sağlayıcısı bağlı değil.",
        "motor_label": "OSMAN/MATT motor çıkışı",
        "motor_detail": "Bu iskeletten fiziksel motor komutu çıkamaz.",
        "tawnt_label": "Tawnt (3awnt) güvenlik katmanı",
        "tawnt_detail": "Entegrasyon ayrı inceleme bekliyor; güvenlik iddiası yoktur.",
        "tawnt_standby": "Tawnt arabayı değil, şimdilik evrakları izliyor.",
        "prompt": "Simülasyon iskelesini açmak için Enter'a basın; çıkmak için Ctrl+C.",
        "auto": "Onay beklemesi atlandı. Otomatik araç arm işlemi hâlâ imkânsız.",
        "simulation_ready": (
            "ARDA simülasyon iskelesi hazır. Kamera ve sürüş döngüleri uygulanmadı."
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


@dataclass(frozen=True)
class StartupCheck:
    """One truthful line in ARDA's startup-state panel."""

    state: str
    label: str
    detail: str


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
    camera_state = "simulated" if options.mode == SIMULATION else "blocked"
    camera_detail = (
        "camera_simulated" if options.mode == SIMULATION else "camera_missing"
    )
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

    console.write()
    console.write(_text(options.language, "simulation_ready"), style=Console.GREEN)
    return EXIT_OK


def main() -> int:
    """Console-script entry point."""

    _configure_utf8_terminal()
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
