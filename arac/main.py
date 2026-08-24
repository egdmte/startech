"""STARTECH-ARDA (ADAM): operate the real lane-following car.

The default screen is deliberately small: observe, bench-test, drive, or open
YAREN/CAM.  Simulation and test harnesses are not vehicle modes.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
import secrets
import sys
import time
from typing import Any, TextIO

import tawnt

if __package__ in {None, ""}:
    root = str(Path(__file__).resolve().parent.parent)
    if root not in sys.path:
        sys.path.insert(0, root)

from arac.ayar import ActiveConfiguration, load_active_configuration
from arac.ayar_cli import run as run_yaren_cli
from arac.atolye import WorkshopCommand, execute_workshop_command
from arac.cli_ui import MenuOption, TerminalUI
from arac.goruntu import LaneObservation, LaneVisionAnalyzer
from arac.goz import CameraSource, build_preferred_camera
from arac.kayit import JsonlBlackBox, RecordKind
from arac.surucu import (
    ControllerSettings,
    GpioStartButton,
    GpioZeroMotorDriver,
    LaneController,
    MotorDriver,
    OutputWatchdog,
    validate_request,
)


APP_VERSION = "1.0.0-vehicle-core"
EXIT_OK = 0
EXIT_ERROR = 2
EXIT_INTERRUPTED = 130
LANE_PHASE = "LANE_FOLLOW"


@dataclass(frozen=True)
class StartupOptions:
    action: str
    profile_root: Path | None
    usb_index: int
    frames: int
    preview: bool
    operator: str | None
    confirm_output: bool
    start: str
    bench_left: float
    bench_right: float
    bench_seconds: float
    log_dir: Path
    color: bool


def _bounded_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if not 0 <= parsed <= 1_000_000:
        raise argparse.ArgumentTypeError("must be between 0 and 1000000")
    return parsed


def _bench_percent(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a number") from exc
    if not -35 <= parsed <= 35:
        raise argparse.ArgumentTypeError("bench output is limited to -35..35 percent")
    return parsed


def _bench_seconds(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a number") from exc
    if not 0.05 <= parsed <= 3.0:
        raise argparse.ArgumentTypeError("bench duration is limited to 0.05..3 seconds")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m arac.main",
        description="ARDA live lane observation and real vehicle control",
    )
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--observe", action="store_true", help="show live lane perception")
    action.add_argument("--drive", action="store_true", help="run live autonomous lane following")
    action.add_argument("--bench", action="store_true", help="apply one bounded workshop motor command")
    action.add_argument("--yaren", action="store_true", help="open the full YAREN/CAM gateway")
    action.add_argument("--interactive", action="store_true", help="open the ARDA menu (default)")
    parser.add_argument("--profile-root", type=Path, help="YAREN profile registry")
    parser.add_argument("--usb-index", type=int, default=0)
    parser.add_argument("--frames", type=_bounded_int, default=0, help="stop after N frames; 0 means until Q/Ctrl-C")
    parser.add_argument("--no-preview", action="store_true", help="do not open an OpenCV preview window")
    parser.add_argument("--operator", help="operator's legal name for physical output logs")
    parser.add_argument("--confirm-output", action="store_true", help="confirm that physical motor output is intended")
    parser.add_argument("--start", choices=("button", "enter"), default="button", help="live-drive start control")
    parser.add_argument("--left", type=_bench_percent, default=0.0, dest="bench_left")
    parser.add_argument("--right", type=_bench_percent, default=0.0, dest="bench_right")
    parser.add_argument("--seconds", type=_bench_seconds, default=0.5, dest="bench_seconds")
    parser.add_argument("--log-dir", type=Path, default=Path("runs"))
    parser.add_argument("--no-color", action="store_true")
    return parser


def parse_options(argv: Sequence[str] | None = None) -> StartupOptions:
    parser = build_parser()
    args = parser.parse_args(argv)
    selected = [
        name for name in ("observe", "drive", "bench", "yaren", "interactive")
        if getattr(args, name)
    ]
    action = selected[0] if selected else "interactive"
    if action in {"drive", "bench"}:
        if not isinstance(args.operator, str) or not args.operator.strip():
            parser.error(f"--{action} requires --operator with the operator's legal name")
        if not args.confirm_output:
            parser.error(f"--{action} requires --confirm-output")
    if args.usb_index < 0:
        parser.error("--usb-index must be non-negative")
    return StartupOptions(
        action=action,
        profile_root=args.profile_root,
        usb_index=args.usb_index,
        frames=args.frames,
        preview=not args.no_preview,
        operator=args.operator.strip() if isinstance(args.operator, str) else None,
        confirm_output=bool(args.confirm_output),
        start=args.start,
        bench_left=args.bench_left,
        bench_right=args.bench_right,
        bench_seconds=args.bench_seconds,
        log_dir=args.log_dir,
        color=not args.no_color,
    )


def _camera_for(configuration: ActiveConfiguration, usb_index: int) -> CameraSource:
    camera = configuration.calibration["kamera"]
    return build_preferred_camera(
        usb_index,
        size=configuration.camera_dimensions,
        bgr_output=bool(camera["bgr_cikis"]),
        rotate_180=bool(camera["dondur_180"]),
    )


def _show_debug(observation: LaneObservation) -> bool:
    """Show an RGB debug frame; return False when Q or Escape is pressed."""

    if observation.debug_frame is None:
        return True
    import cv2

    display = cv2.cvtColor(observation.debug_frame, cv2.COLOR_RGB2BGR)
    cv2.imshow("ARDA - live lane perception (Q to stop)", display)
    return (cv2.waitKey(1) & 0xFF) not in {ord("q"), ord("Q"), 27}


def _close_preview() -> None:
    try:
        import cv2

        cv2.destroyAllWindows()
    except Exception:
        pass


def run_observation(
    options: StartupOptions,
    *,
    configuration: ActiveConfiguration | None = None,
    camera: CameraSource | None = None,
    analyzer: LaneVisionAnalyzer | None = None,
    output: TextIO = sys.stdout,
    preview_fn: Callable[[LaneObservation], bool] = _show_debug,
) -> int:
    """Run production perception against a live camera, with no motor driver."""

    configuration = configuration or load_active_configuration(options.profile_root)
    camera = camera or _camera_for(configuration, options.usb_index)
    analyzer = analyzer or LaneVisionAnalyzer(configuration.calibration)
    count = 0
    camera.open()
    try:
        while options.frames == 0 or count < options.frames:
            observation = analyzer.analyze(camera.read_frame())
            count += 1
            state = (
                f"error={observation.error_px:+.1f}px confidence={observation.confidence:.2f}"
                if observation.valid else f"STOP: {observation.reason}"
            )
            print(f"frame {observation.frame_id}: {state}", file=output)
            if options.preview and not preview_fn(observation):
                break
    finally:
        camera.close()
        if options.preview:
            _close_preview()
    return EXIT_OK


def _new_black_box(options: StartupOptions, action: str) -> JsonlBlackBox:
    options.log_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    run_id = f"{action}-{stamp}"
    return JsonlBlackBox(options.log_dir / f"{run_id}.jsonl", run_id)


def _log(
    black_box: JsonlBlackBox,
    kind: RecordKind,
    module: str,
    data: dict[str, Any],
    *,
    frame_id: int | None = None,
) -> None:
    black_box.append(kind, module, data, frame_id=frame_id)


def _wait_for_start(
    method: str,
    *,
    input_fn: Callable[[str], str],
    button_factory: Callable[[], GpioStartButton],
) -> GpioStartButton | None:
    if method == "enter":
        input_fn("Press Enter to arm lane following...")
        return None
    button = button_factory()
    button.wait()
    return button


def run_drive(
    options: StartupOptions,
    *,
    configuration: ActiveConfiguration | None = None,
    camera: CameraSource | None = None,
    analyzer: LaneVisionAnalyzer | None = None,
    controller: LaneController | None = None,
    driver: MotorDriver | None = None,
    input_fn: Callable[[str], str] = input,
    button_factory: Callable[[], GpioStartButton] = GpioStartButton,
    output: TextIO = sys.stdout,
    preview_fn: Callable[[LaneObservation], bool] = _show_debug,
) -> int:
    """Run camera -> KEREM -> controller -> TAWNT -> GPIO -> KADER."""

    if not options.operator or not options.confirm_output:
        raise ValueError("live drive needs an operator legal name and output confirmation")
    configuration = configuration or load_active_configuration(options.profile_root)
    camera = camera or _camera_for(configuration, options.usb_index)
    analyzer = analyzer or LaneVisionAnalyzer(configuration.calibration)
    settings = ControllerSettings.from_mapping(configuration.settings)
    controller = controller or LaneController(settings, phase=LANE_PHASE)
    black_box = _new_black_box(options, "drive")
    driver = driver or GpioZeroMotorDriver(configuration.calibration["motor"])
    button: GpioStartButton | None = None
    output_watchdog = OutputWatchdog(driver)
    armed = False
    count = 0

    try:
        driver.stop("pre-start electrical stop")
        tawnt.sifirla()
        tawnt.onShutdown(lambda: driver.stop("TAWNT zero callback"))
        options.log_dir.mkdir(parents=True, exist_ok=True)
        tawnt.configureFaultStore(options.log_dir / "tawnt-fault.json")
        tawnt.defineWatchdog("camera", timeout_seconds=0.5)
        tawnt.defineWatchdog("control", timeout_seconds=0.5)
        tawnt.definePhase(
            LANE_PHASE,
            motion_allowed=True,
            allow_reverse=False,
            allow_pivot=False,
            max_pwm=settings.maximum_speed / 100.0,
            max_difference=settings.maximum_speed / 100.0,
            required_watchdogs=("camera", "control"),
        )
        camera.open()
        # Prove the configured camera and lane pipeline can produce one result
        # before waiting for the human/physical start control.
        analyzer.analyze(camera.read_frame())
        button = _wait_for_start(
            options.start, input_fn=input_fn, button_factory=button_factory
        )
        tawnt.heartbeat("camera")
        tawnt.heartbeat("control")
        tawnt.validateBeforeStart(profile=tawnt.LIVE)
        tawnt.enterPhase(LANE_PHASE)
        tawnt.arm(
            options.operator or "",
            live_hardware_authorized=True,
            final_confirmation=True,
        )
        armed = True
        output_watchdog.start()
        _log(black_box, RecordKind.STATE, "ARDA", {
            "state": "ARMED", "operator": options.operator,
            "profile_id": configuration.profile_id,
        })
        print("ARDA armed. Live lane following has control; Q/Ctrl-C stops.", file=output)

        while options.frames == 0 or count < options.frames:
            frame = camera.read_frame()
            # Check the age accumulated inside the blocking read before
            # refreshing either heartbeat.
            tawnt.checkWatchdogs(("camera", "control"))
            tawnt.heartbeat("camera")
            observation = analyzer.analyze(frame)
            _log(
                black_box, RecordKind.OBSERVATION, "KEREM",
                observation.record_data(), frame_id=frame.frame_id,
            )
            tawnt.heartbeat("control")
            request = controller.compute(observation)
            _log(black_box, RecordKind.MOTOR_REQUEST, "ARDA", {
                "left": request.left, "right": request.right,
                "phase": request.phase, "reason": request.reason,
            }, frame_id=frame.frame_id)
            validated = validate_request(request)
            final_command = driver.apply(validated) or validated.command
            output_watchdog.touch()
            _log(black_box, RecordKind.MOTOR_ACCEPTED, "OSMAN", {
                "left": final_command.left, "right": final_command.right,
                "phase": final_command.phase,
            }, frame_id=frame.frame_id)
            count += 1
            if options.preview and not preview_fn(observation):
                break
    except KeyboardInterrupt:
        driver.stop("operator interrupt")
        _log(black_box, RecordKind.INFO, "ARDA", {"reason": "operator interrupt"})
        return EXIT_INTERRUPTED
    except Exception as exc:
        # Physical stop request comes first. Evidence is written only afterwards.
        driver.stop(f"drive fault: {type(exc).__name__}")
        try:
            _log(black_box, RecordKind.FAULT, "ARDA", {
                "type": type(exc).__name__, "message": str(exc),
            })
        except Exception:
            pass
        raise
    finally:
        output_watchdog.close()
        driver.stop("drive loop ended")
        if armed:
            tawnt.disarm("drive loop ended")
        try:
            camera.close()
        finally:
            if button is not None:
                button.close()
            driver.close()
            if options.preview:
                _close_preview()
    return EXIT_OK


def run_bench(
    options: StartupOptions,
    *,
    configuration: ActiveConfiguration | None = None,
    driver: MotorDriver | None = None,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> int:
    """Apply one explicitly bounded workshop command, then electrically stop."""

    if not options.operator or not options.confirm_output:
        raise ValueError("bench output needs an operator legal name and output confirmation")
    command = WorkshopCommand(
        command_id=secrets.token_hex(16),
        operator=options.operator,
        left_percent=options.bench_left,
        right_percent=options.bench_right,
        duration_seconds=options.bench_seconds,
        source="ARDA_CLI",
    )
    execute_workshop_command(
        command,
        profile_root=options.profile_root,
        configuration=configuration,
        driver=driver,
        log_dir=options.log_dir,
        clock=clock,
        sleep=sleep,
    )
    return EXIT_OK


def run_configuration_menu(
    options: StartupOptions,
    *,
    input_fn: Callable[[str], str] = input,
    output: TextIO = sys.stdout,
) -> int:
    arguments: list[str] = []
    if options.profile_root is not None:
        arguments.extend(("--root", str(options.profile_root)))
    arguments.append("interactive")
    return run_yaren_cli(arguments, input_fn=input_fn, output=output)


def _interactive_options(
    options: StartupOptions,
    *,
    input_fn: Callable[[str], str],
    output: TextIO,
) -> StartupOptions | None:
    ui = TerminalUI(output, options.color)
    choice = ui.choose(
        "ARDA — CAR CONTROL",
        (
            MenuOption("1", "Observe live lanes", "camera + KEREM; no motor output"),
            MenuOption("2", "Bench motor command", "bounded physical workshop output"),
            MenuOption("3", "Drive", "live lane following on the existing car"),
            MenuOption("4", "YAREN / CAM", "configuration and calibration gateway"),
            MenuOption("5", "Exit"),
        ),
        input_fn=input_fn,
        prompt="Choose 1-5: ",
        invalid_message="Choose one of the displayed numbers.",
    )
    if choice == "5":
        return None
    if choice == "1":
        return replace(options, action="observe")
    if choice == "4":
        return replace(options, action="yaren")

    operator = input_fn("Operator legal name: ").strip()
    if not operator:
        raise ValueError("physical output needs the operator's legal name")
    confirmation = input_fn("Type OUTPUT to confirm physical motor output: ").strip()
    if confirmation != "OUTPUT":
        raise ValueError("physical output was not confirmed")
    if choice == "3":
        return replace(
            options, action="drive", operator=operator, confirm_output=True
        )
    left = _bench_percent(input_fn("Left motor percent (-35..35): "))
    right = _bench_percent(input_fn("Right motor percent (-35..35): "))
    seconds = _bench_seconds(input_fn("Duration seconds (0.05..3): "))
    return replace(
        options,
        action="bench",
        operator=operator,
        confirm_output=True,
        bench_left=left,
        bench_right=right,
        bench_seconds=seconds,
    )


def run(
    options: StartupOptions | Sequence[str],
    *,
    input_fn: Callable[[str], str] = input,
    output: TextIO = sys.stdout,
) -> int:
    selected = options if isinstance(options, StartupOptions) else parse_options(options)
    if selected.action == "interactive":
        chosen = _interactive_options(selected, input_fn=input_fn, output=output)
        if chosen is None:
            return EXIT_OK
        selected = chosen
    if selected.action == "observe":
        return run_observation(selected, output=output)
    if selected.action == "drive":
        return run_drive(selected, input_fn=input_fn, output=output)
    if selected.action == "bench":
        return run_bench(selected)
    if selected.action == "yaren":
        return run_configuration_menu(selected, input_fn=input_fn, output=output)
    raise ValueError(f"unknown ARDA action: {selected.action}")


def main(argv: Sequence[str] | None = None) -> int:
    try:
        return run(parse_options(argv))
    except KeyboardInterrupt:
        return EXIT_INTERRUPTED
    except Exception as exc:
        print(f"ARDA stopped: {exc}", file=sys.stderr)
        return EXIT_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
