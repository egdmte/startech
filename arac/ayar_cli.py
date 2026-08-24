"""Terminal manager for STARTECH-YAREN calibration/settings profiles.

The interface manages local configuration evidence only.  Selecting a profile is
not vehicle arming and is never presented as a safe-to-drive decision.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import os
from pathlib import Path
import sys
from typing import Callable, Mapping, Sequence, TextIO

if __package__ in {None, ""}:
    repository_root = str(Path(__file__).resolve().parent.parent)
    if repository_root not in sys.path:
        sys.path.insert(0, repository_root)
    from arac.cli_ui import MenuOption, TerminalUI
    from arac.yaren_web import (
        create_device_identity,
        default_identity_path,
        default_server_url,
        request_web_code,
    )
    from arac.yaren_link import close_temporary_link, run_temporary_link
else:
    from .cli_ui import MenuOption, TerminalUI
    from .yaren_web import (
        create_device_identity,
        default_identity_path,
        default_server_url,
        request_web_code,
    )
    from .yaren_link import close_temporary_link, run_temporary_link

from startech.configuration.profiles import (
    ProfileError,
    ProfileLocation,
    ProfileStore,
)


EXIT_OK = 0
EXIT_INVALID = 2
EXIT_INTERRUPTED = 130

EDITABLE_SETTINGS: dict[str, type[int] | type[float]] = {
    "kontrol.kp": float,
    "kontrol.kd": float,
    "kontrol.ki": float,
    "kontrol.integral_max": float,
    "kontrol.deriv_cap": int,
    "hiz.hedef": int,
    "hiz.min": int,
    "hiz.max": int,
    "hiz.k_speed": float,
    "olay.yakin_roi_orani": float,
}


def _supports_color(stream: TextIO, requested: bool) -> bool:
    if not requested or os.environ.get("NO_COLOR") is not None:
        return False
    return bool(getattr(stream, "isatty", lambda: False)())


def _number(value: object, expected: type[int] | type[float], path: str):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{path} needs a JSON number")
    if not math.isfinite(value):
        raise ValueError(f"{path} must be finite")
    if expected is int:
        if not isinstance(value, int):
            raise ValueError(f"{path} needs an integer")
        return value
    return float(value)


def parse_setting_assignment(assignment: str) -> tuple[str, int | float]:
    """Parse one restricted ``path=JSON-number`` settings edit."""

    if not isinstance(assignment, str) or "=" not in assignment:
        raise ValueError("settings edit must use path=value")
    path, raw_value = (part.strip() for part in assignment.split("=", 1))
    if path not in EDITABLE_SETTINGS:
        allowed = ", ".join(EDITABLE_SETTINGS)
        raise ValueError(f"unsupported settings path {path!r}; choose: {allowed}")
    try:
        value = json.loads(raw_value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path} needs a valid JSON number") from exc
    return path, _number(value, EDITABLE_SETTINGS[path], path)


def apply_setting_assignments(
    settings: Mapping[str, object], assignments: Sequence[str]
) -> dict[str, object]:
    """Return a deep-copied settings object with restricted edits applied."""

    if not isinstance(settings, Mapping):
        raise TypeError("settings must be a mapping")
    result = copy.deepcopy(dict(settings))
    seen: set[str] = set()
    if not assignments:
        raise ValueError("at least one settings edit is required")
    for assignment in assignments:
        path, value = parse_setting_assignment(assignment)
        if path in seen:
            raise ValueError(f"duplicate settings edit: {path}")
        seen.add(path)
        section, field = path.split(".", 1)
        result[section][field] = value
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="startech-yaren",
        description=(
            "Manage immutable STARTECH calibration/settings profiles. "
            "Selection does not arm the vehicle."
        ),
    )
    parser.add_argument(
        "--profile-root",
        type=Path,
        help="registry directory (defaults to the OS-local STARTECH directory)",
    )
    parser.add_argument("--no-color", action="store_true")
    commands = parser.add_subparsers(dest="command")

    commands.add_parser("interactive", help="open the guided settings menu")
    commands.add_parser("list", help="list installed and archived profiles")

    show = commands.add_parser("show", help="show one profile or the active profile")
    show_group = show.add_mutually_exclusive_group(required=True)
    show_group.add_argument("--profile")
    show_group.add_argument("--active", action="store_true")

    import_command = commands.add_parser("import", help="install a JSON pair")
    import_command.add_argument("calibration", type=Path)
    import_command.add_argument("settings", type=Path)
    import_command.add_argument("--name", required=True)
    import_command.add_argument("--note", default="")
    import_command.add_argument("--camera-session")

    settings_command = commands.add_parser(
        "settings", help="create a new settings revision from a parent profile"
    )
    settings_command.add_argument("parent")
    settings_command.add_argument("--name", required=True)
    settings_command.add_argument("--note", default="")
    settings_command.add_argument(
        "--set",
        action="append",
        dest="assignments",
        required=True,
        metavar="PATH=VALUE",
    )

    activate = commands.add_parser("activate", help="select an installed profile")
    activate.add_argument("profile")
    activate.add_argument("--warning-digest")
    activate.add_argument("--reviewer")

    compare = commands.add_parser("compare", help="compare two profile pairs")
    compare.add_argument("left")
    compare.add_argument("right")

    diagnose = commands.add_parser("diagnose", help="check the active selection")
    diagnose.add_argument("--camera-width", type=int)
    diagnose.add_argument("--camera-height", type=int)

    commands.add_parser("history", help="show selection history")

    archive = commands.add_parser("archive", help="archive an inactive profile")
    archive.add_argument("profile")

    restore = commands.add_parser("restore", help="restore an archived profile")
    restore.add_argument("profile")

    export = commands.add_parser("export", help="export a verified profile directory")
    export.add_argument("profile")
    export.add_argument("destination", type=Path)

    web_key = commands.add_parser(
        "web-key", help="create the private YAREN identity used to authenticate to CAM"
    )
    web_key.add_argument("--device", required=True, help="stable registered device ID")
    web_key.add_argument("--identity-file", type=Path)
    web_key.add_argument("--public-output", type=Path)
    web_key.add_argument(
        "--replace",
        action="store_true",
        help="replace both identity files for an intentional key rotation",
    )

    web_code = commands.add_parser(
        "web-code", help="request one single-use CAM access code"
    )
    web_code.add_argument("--server", default=None)
    web_code.add_argument("--identity-file", type=Path)
    web_code.add_argument("--timeout", type=float, default=10.0)
    web_code.add_argument("--poll-interval", type=float, default=2.0)
    return parser


def _profile_rows(profile) -> tuple[tuple[str, object], ...]:
    manifest = profile.manifest
    return (
        ("profile", manifest.profile_id),
        ("name", manifest.name),
        ("location", profile.location.value),
        ("source", manifest.source_type),
        ("parent", manifest.parent_profile_id or "-"),
        ("created", manifest.created_at_utc),
        ("camera", f"{manifest.width}x{manifest.height}"),
        ("warnings", len(manifest.warnings)),
        ("calibration", manifest.calibration_sha256),
        ("settings", manifest.settings_sha256),
    )


def _show_profile(console: TerminalUI, profile) -> None:
    console.summary("YAREN PROFILE", _profile_rows(profile), style=TerminalUI.BLUE)
    for warning in profile.manifest.warnings:
        console.write(f"  ! {warning}", style=TerminalUI.YELLOW)
    if profile.manifest.warnings:
        console.write(
            f"  warning digest: {profile.manifest.warning_digest}",
            style=TerminalUI.MUTED,
        )


def _list_profiles(console: TerminalUI, store: ProfileStore) -> None:
    profiles = store.list_profiles()
    console.section("YAREN PROFILES", style=TerminalUI.BLUE)
    if not profiles:
        console.panel_line("No installed or archived profiles.")
    for item in profiles:
        marker = "I" if item.location is ProfileLocation.INSTALLED else "A"
        console.panel_line(
            f"[{marker}] {item.profile_id}  {item.name}  "
            f"{item.width}x{item.height}  warnings={item.warning_count}"
        )
    console.rule()


def _show_active(console: TerminalUI, store: ProfileStore) -> None:
    selection = store.load_active_selection()
    profile = store.load_active_profile()
    _show_profile(console, profile)
    console.write(f"  selected revision: {selection.revision}")
    console.write("  state: SELECTED (this is not a safe-to-drive claim)")


def _run_command(args, console: TerminalUI, store: ProfileStore) -> int:
    if args.command == "list":
        _list_profiles(console, store)
    elif args.command == "show":
        if args.active:
            _show_active(console, store)
        else:
            _show_profile(console, store.load_profile(args.profile))
    elif args.command == "import":
        profile = store.import_pair(
            args.calibration,
            args.settings,
            name=args.name,
            note=args.note,
            camera_session_id=args.camera_session,
        )
        _show_profile(console, profile)
        console.write("Installed for review; it was not selected.", style=TerminalUI.GREEN)
    elif args.command == "settings":
        parent = store.load_profile(args.parent, include_archived=False)
        settings = apply_setting_assignments(parent.settings, args.assignments)
        profile = store.create_settings_variant(
            parent.manifest.profile_id,
            settings,
            name=args.name,
            note=args.note,
        )
        _show_profile(console, profile)
        console.write("New settings revision installed; parent unchanged.", style=TerminalUI.GREEN)
    elif args.command == "activate":
        selection = store.activate_profile(
            args.profile,
            reviewer=args.reviewer,
            warning_digest=args.warning_digest,
        )
        console.summary(
            "PROFILE SELECTED",
            (
                ("profile", selection.profile_id),
                ("revision", selection.revision),
                ("selected", selection.selected_at_utc),
                ("reviewer", selection.warning_reviewer or "not required"),
                ("vehicle", "NOT ARMED"),
            ),
            style=TerminalUI.GREEN,
        )
    elif args.command == "compare":
        differences = store.compare_profiles(args.left, args.right)
        console.section("YAREN COMPARISON", style=TerminalUI.BLUE)
        if not differences:
            console.panel_line("No calibration or settings differences.")
        for difference in differences:
            console.panel_line(
                f"{difference.path}: {difference.left!r} -> {difference.right!r}"
            )
        console.rule()
    elif args.command == "diagnose":
        if (args.camera_width is None) != (args.camera_height is None):
            raise ValueError("camera width and height must be provided together")
        dimensions = None
        if args.camera_width is not None:
            dimensions = (args.camera_width, args.camera_height)
        diagnosis = store.diagnose_active(camera_dimensions=dimensions)
        console.summary(
            "ACTIVE PROFILE DIAGNOSIS",
            (
                ("valid", diagnosis.valid),
                ("profile", diagnosis.profile_id or "-"),
                ("errors", len(diagnosis.errors)),
                ("warnings", len(diagnosis.warnings)),
                ("vehicle", "NOT ARMED"),
            ),
            style=TerminalUI.GREEN if diagnosis.valid else TerminalUI.RED,
        )
        for error in diagnosis.errors:
            console.write(f"  ERROR: {error}", style=TerminalUI.RED)
        for warning in diagnosis.warnings:
            console.write(f"  WARNING: {warning}", style=TerminalUI.YELLOW)
        if not diagnosis.valid:
            return EXIT_INVALID
    elif args.command == "history":
        console.section("YAREN SELECTION HISTORY", style=TerminalUI.BLUE)
        history = store.activation_history()
        if not history:
            console.panel_line("No selection history.")
        for entry in history:
            state = "COMMITTED" if entry.committed else "ORPHANED"
            selection = entry.selection
            console.panel_line(
                f"r{selection.revision} {selection.profile_id} "
                f"{selection.selected_at_utc} {state}"
            )
        console.rule()
    elif args.command == "archive":
        profile = store.archive_profile(args.profile)
        console.write(f"Archived {profile.manifest.profile_id}.", style=TerminalUI.GREEN)
    elif args.command == "restore":
        profile = store.restore_profile(args.profile)
        console.write(f"Restored {profile.manifest.profile_id}.", style=TerminalUI.GREEN)
    elif args.command == "export":
        destination = store.export_profile(args.profile, args.destination)
        console.write(f"Exported verified profile to {destination}.", style=TerminalUI.GREEN)
    elif args.command == "web-key":
        private_path = args.identity_file or default_identity_path()
        identity, public_path = create_device_identity(
            args.device,
            private_path,
            args.public_output,
            replace=args.replace,
        )
        console.summary(
            "YAREN WEB IDENTITY CREATED",
            (
                ("device", identity.device_id),
                ("algorithm", "Ed25519"),
                ("private", private_path.expanduser().resolve()),
                ("public", public_path),
                ("vehicle", "NOT ARMED"),
            ),
            style=TerminalUI.GREEN,
        )
        console.write(
            "Register only the public JSON on CAM. Never copy or upload the private file.",
            style=TerminalUI.YELLOW,
        )
    elif args.command == "web-code":
        code = request_web_code(
            args.server,
            args.identity_file,
            timeout=args.timeout,
        )
        console.summary(
            "CAM WEB ACCESS CODE",
            (
                ("device", code.device_id),
                ("code", code.access_code),
                ("expires at", code.expires_at),
                ("use", "single use"),
                ("vehicle", "NOT ARMED"),
            ),
            style=TerminalUI.GREEN,
        )
        try:
            run_temporary_link(
                code,
                profile_root=store.root,
                server_url=args.server,
                timeout=args.timeout,
                poll_interval=args.poll_interval,
                status=lambda message: console.write(message, style=TerminalUI.MUTED),
            )
        except KeyboardInterrupt:
            close_temporary_link(
                code,
                server_url=args.server,
                timeout=min(args.timeout, 5.0),
            )
            raise
    else:
        raise ValueError("a YAREN command is required")
    return EXIT_OK


def _ask(console: TerminalUI, input_fn: Callable[[str], str], prompt: str) -> str:
    return console.ask_non_empty(
        prompt,
        input_fn=input_fn,
        invalid_message="A non-empty value is required.",
    )


def _interactive(
    console: TerminalUI,
    store: ProfileStore,
    input_fn: Callable[[str], str],
) -> int:
    while True:
        choice = console.choose(
            "STARTECH-YAREN // CONFIGURATION",
            (
                MenuOption("1", "List profiles"),
                MenuOption("2", "Show active profile and diagnosis"),
                MenuOption("3", "Import calibration.json + ayarlar.json"),
                MenuOption("4", "Create a settings revision"),
                MenuOption("5", "Select an installed profile"),
                MenuOption("6", "Compare two profiles"),
                MenuOption("7", "Archive an inactive profile"),
                MenuOption("8", "Restore an archived profile"),
                MenuOption("9", "Export a verified profile"),
                MenuOption("10", "Request a temporary CAM web code"),
                MenuOption("0", "Exit without arming the vehicle"),
            ),
            input_fn=input_fn,
            prompt="Choose 0-10: ",
            invalid_message="Choose one of the displayed numbers.",
        )
        try:
            if choice == "0":
                console.write("YAREN closed; the vehicle remains unarmed.")
                return EXIT_OK
            if choice == "1":
                _list_profiles(console, store)
            elif choice == "2":
                _show_active(console, store)
                diagnosis = store.diagnose_active()
                console.write(f"  integrity diagnosis: {'PASS' if diagnosis.valid else 'FAIL'}")
            elif choice == "3":
                calibration = Path(_ask(console, input_fn, "kalibrasyon.json path: "))
                settings = Path(_ask(console, input_fn, "ayarlar.json path: "))
                name = _ask(console, input_fn, "Profile name: ")
                profile = store.import_pair(calibration, settings, name=name)
                _show_profile(console, profile)
                console.write("Installed for review; it was not selected.")
            elif choice == "4":
                parent_id = _ask(console, input_fn, "Parent profile ID: ")
                parent = store.load_profile(parent_id, include_archived=False)
                name = _ask(console, input_fn, "New revision name: ")
                console.write("Editable fields:")
                for path in EDITABLE_SETTINGS:
                    console.write(f"  {path}")
                console.write("Enter path=value edits. Submit a blank line when finished.")
                assignments: list[str] = []
                while True:
                    assignment = input_fn("setting> ").strip()
                    if not assignment:
                        break
                    parse_setting_assignment(assignment)
                    assignments.append(assignment)
                settings = apply_setting_assignments(parent.settings, assignments)
                profile = store.create_settings_variant(
                    parent.manifest.profile_id, settings, name=name
                )
                _show_profile(console, profile)
                console.write("New revision installed; parent unchanged.")
            elif choice == "5":
                profile_id = _ask(console, input_fn, "Installed profile ID: ")
                profile = store.load_profile(profile_id, include_archived=False)
                reviewer = None
                digest = None
                if profile.manifest.warnings:
                    _show_profile(console, profile)
                    console.write(
                        "Type ACK only after reviewing every warning. "
                        "Selection still does not arm the vehicle.",
                        style=TerminalUI.YELLOW,
                    )
                    if input_fn("Acknowledgement: ").strip() != "ACK":
                        console.write("Selection cancelled.", style=TerminalUI.YELLOW)
                        continue
                    reviewer = _ask(console, input_fn, "Reviewer name: ")
                    digest = profile.manifest.warning_digest
                selection = store.activate_profile(
                    profile_id, reviewer=reviewer, warning_digest=digest
                )
                console.write(
                    f"Selected {selection.profile_id}; vehicle remains unarmed.",
                    style=TerminalUI.GREEN,
                )
            elif choice == "6":
                left = _ask(console, input_fn, "First profile ID: ")
                right = _ask(console, input_fn, "Second profile ID: ")
                differences = store.compare_profiles(left, right)
                console.section("YAREN COMPARISON")
                for item in differences:
                    console.panel_line(f"{item.path}: {item.left!r} -> {item.right!r}")
                if not differences:
                    console.panel_line("No differences.")
                console.rule()
            elif choice == "7":
                profile_id = _ask(console, input_fn, "Inactive profile ID: ")
                store.archive_profile(profile_id)
                console.write(f"Archived {profile_id}.")
            elif choice == "8":
                profile_id = _ask(console, input_fn, "Archived profile ID: ")
                store.restore_profile(profile_id)
                console.write(f"Restored {profile_id}.")
            elif choice == "9":
                profile_id = _ask(console, input_fn, "Profile ID: ")
                destination = Path(_ask(console, input_fn, "New export directory: "))
                store.export_profile(profile_id, destination)
                console.write(f"Exported to {destination}.")
            elif choice == "10":
                console.write(
                    f"CAM server: {default_server_url()}", style=TerminalUI.MUTED
                )
                console.write(
                    f"Private identity: {default_identity_path()}",
                    style=TerminalUI.MUTED,
                )
                code = request_web_code()
                console.summary(
                    "CAM WEB ACCESS CODE",
                    (
                        ("device", code.device_id),
                        ("code", code.access_code),
                        ("expires at", code.expires_at),
                        ("vehicle", "NOT ARMED"),
                    ),
                    style=TerminalUI.GREEN,
                )
                try:
                    run_temporary_link(
                        code,
                        profile_root=store.root,
                        status=lambda message: console.write(
                            message, style=TerminalUI.MUTED
                        ),
                    )
                except KeyboardInterrupt:
                    close_temporary_link(code)
                    raise
        except (ProfileError, ValueError, OSError) as exc:
            console.write(f"YAREN refused the operation: {exc}", style=TerminalUI.RED)


def run(
    argv: Sequence[str] | None = None,
    *,
    input_fn: Callable[[str], str] = input,
    output: TextIO = sys.stdout,
) -> int:
    args = build_parser().parse_args(argv)
    console = TerminalUI(output, _supports_color(output, not args.no_color))
    store = ProfileStore(args.profile_root)
    command = args.command or "interactive"
    args.command = command
    try:
        if command == "interactive":
            return _interactive(console, store, input_fn)
        return _run_command(args, console, store)
    except KeyboardInterrupt:
        console.write(
            "YAREN interrupted; the vehicle remains unarmed.",
            style=TerminalUI.YELLOW,
        )
        return EXIT_INTERRUPTED
    except EOFError:
        console.write("YAREN stopped because input ended; no selection was changed.", style=TerminalUI.RED)
        return EXIT_INVALID
    except (ProfileError, ValueError, OSError) as exc:
        console.write(f"YAREN refused the operation: {exc}", style=TerminalUI.RED)
        return EXIT_INVALID


def main() -> int:
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
