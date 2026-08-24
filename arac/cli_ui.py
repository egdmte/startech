"""Dependency-free terminal UI primitives for STARTECH-ARDA.

The UI renders state reported by the underlying operation.  It does not infer that
hardware is safe, arm the vehicle or turn a log message into physical proof.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
import os
import select
import sys
from typing import TextIO


NAVIGATE_UP = "up"
NAVIGATE_DOWN = "down"
NAVIGATE_ENTER = "enter"
NAVIGATE_BACK = "back"


def supports_live_navigation(
    output: TextIO,
    *,
    input_stream: TextIO = sys.stdin,
) -> bool:
    """Return whether raw, repaintable keyboard navigation is available."""

    return bool(
        getattr(input_stream, "isatty", lambda: False)()
        and getattr(output, "isatty", lambda: False)()
    )


def _read_windows_key() -> str:
    import msvcrt

    value = msvcrt.getwch()
    if value in {"\x00", "\xe0"}:
        return {
            "H": NAVIGATE_UP,
            "P": NAVIGATE_DOWN,
            "K": NAVIGATE_BACK,
        }.get(msvcrt.getwch(), "")
    if value in {"\r", "\n"}:
        return NAVIGATE_ENTER
    if value in {"\x1b", "\x08", "\x7f"}:
        return NAVIGATE_BACK
    if value == "\x03":
        raise KeyboardInterrupt
    return value if value.isprintable() else ""


def _read_posix_key(input_stream: TextIO) -> str:
    import termios
    import tty

    descriptor = input_stream.fileno()
    original = termios.tcgetattr(descriptor)
    try:
        tty.setraw(descriptor)
        value = os.read(descriptor, 1)
        if value == b"\x03":
            raise KeyboardInterrupt
        if value in {b"\r", b"\n"}:
            return NAVIGATE_ENTER
        if value in {b"\x08", b"\x7f"}:
            return NAVIGATE_BACK
        if value == b"\x1b":
            if not select.select([descriptor], [], [], 0.04)[0]:
                return NAVIGATE_BACK
            if os.read(descriptor, 1) != b"[":
                return NAVIGATE_BACK
            if not select.select([descriptor], [], [], 0.04)[0]:
                return NAVIGATE_BACK
            return {
                b"A": NAVIGATE_UP,
                b"B": NAVIGATE_DOWN,
                b"D": NAVIGATE_BACK,
            }.get(os.read(descriptor, 1), "")
        return value.decode("utf-8", errors="ignore") if value.isascii() else ""
    finally:
        termios.tcsetattr(descriptor, termios.TCSADRAIN, original)


def read_navigation_key(*, input_stream: TextIO = sys.stdin) -> str:
    """Read one navigation action without requiring Enter."""

    if os.name == "nt":
        return _read_windows_key()
    return _read_posix_key(input_stream)


@dataclass(frozen=True)
class MenuOption:
    """One terminal-menu choice with an optional contextual explanation."""

    key: str
    label: str
    description: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.key, str) or not self.key.strip():
            raise ValueError("menu key must be non-empty text")
        if not isinstance(self.label, str) or not self.label.strip():
            raise ValueError("menu label must be non-empty text")
        if not isinstance(self.description, str):
            raise ValueError("menu description must be text")


class TerminalUI:
    """Portable fixed-width terminal panels, menus, progress and summaries."""

    WIDTH = 74
    RESET = "\033[0m"
    BLUE = "\033[1;44;37m"
    GREEN = "\033[1;32m"
    YELLOW = "\033[1;33m"
    RED = "\033[1;31m"
    MUTED = "\033[2m"

    def __init__(
        self,
        stream: TextIO,
        color: bool,
        *,
        interactive: bool | None = None,
    ) -> None:
        self.stream = stream
        self.color = color
        self.interactive = (
            bool(getattr(stream, "isatty", lambda: False)())
            if interactive is None
            else interactive
        )

    def clear(self) -> None:
        """Clear one interactive screen without polluting redirected output."""

        if self.interactive:
            self.stream.write("\033[2J\033[H")
            self.stream.flush()

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

    def section(self, title: str, *, style: str = "") -> None:
        self.write()
        self.rule()
        self.panel_line(title, style=style)
        self.rule()

    def summary(
        self,
        title: str,
        rows: Iterable[tuple[str, object]],
        *,
        style: str = "",
    ) -> None:
        self.section(title, style=style)
        for label, value in rows:
            self.panel_line(f"{label:<18} {value}")
        self.rule()

    def progress(self, current: int, total: int, label: str) -> None:
        if (
            isinstance(current, bool)
            or not isinstance(current, int)
            or isinstance(total, bool)
            or not isinstance(total, int)
            or total <= 0
            or not 0 <= current <= total
        ):
            raise ValueError("progress needs 0 <= current <= positive total")
        width = 28
        filled = round(width * current / total)
        bar = "#" * filled + "." * (width - filled)
        self.write(f"  [{bar}] {current:>5}/{total:<5} {label}")

    def choose(
        self,
        title: str,
        options: Iterable[MenuOption],
        *,
        input_fn: Callable[[str], str],
        prompt: str,
        invalid_message: str,
        key_reader: Callable[[], str] | None = None,
        initial_key: str | None = None,
        back_key: str | None = None,
    ) -> str:
        choices = tuple(options)
        if not choices:
            raise ValueError("terminal menu needs at least one option")
        keys = {option.key for option in choices}
        if len(keys) != len(choices):
            raise ValueError("terminal menu keys must be unique")

        if initial_key is not None and initial_key not in keys:
            raise ValueError("initial menu key must exist in the displayed options")
        if back_key is not None and back_key not in keys:
            raise ValueError("back menu key must exist in the displayed options")

        if key_reader is not None:
            selected = 0
            if initial_key is not None:
                selected = next(
                    index
                    for index, option in enumerate(choices)
                    if option.key == initial_key
                )
            while True:
                self._draw_navigation_menu(title, choices, selected, back_key=back_key)
                value = key_reader()
                if value == NAVIGATE_UP:
                    selected = (selected - 1) % len(choices)
                elif value == NAVIGATE_DOWN:
                    selected = (selected + 1) % len(choices)
                elif value == NAVIGATE_ENTER:
                    return choices[selected].key
                elif value == NAVIGATE_BACK and back_key is not None:
                    return back_key
                elif value in keys:
                    return value

        self.section(title, style=self.BLUE)
        for option in choices:
            self.panel_line(f"[{option.key}]  {option.label}")
        self.rule()

        while True:
            value = input_fn(prompt).strip()
            if value in keys:
                return value
            self.write(invalid_message, style=self.YELLOW)

    def _draw_navigation_menu(
        self,
        title: str,
        choices: tuple[MenuOption, ...],
        selected: int,
        *,
        back_key: str | None,
    ) -> None:
        self.clear()
        self.section(title)
        for index, option in enumerate(choices):
            marker = ">" if index == selected else " "
            self.panel_line(
                f"{marker} {option.label}",
                style=self.BLUE if index == selected else "",
            )
        self.rule()
        description = choices[selected].description.strip()
        if description:
            self.write(f"  {description}", style=self.MUTED)
        back_hint = "  Esc/Backspace Back" if back_key is not None else ""
        self.write(f"  Up/Down Navigate  Enter Select{back_hint}", style=self.MUTED)

    def pause(self, key_reader: Callable[[], str] | None) -> None:
        """Keep an action result visible before repainting the parent menu."""

        if key_reader is None:
            return
        self.write()
        self.write("  Press Enter or Escape to return.", style=self.MUTED)
        while True:
            if key_reader() in {NAVIGATE_ENTER, NAVIGATE_BACK}:
                return

    def ask_non_empty(
        self,
        prompt: str,
        *,
        input_fn: Callable[[str], str],
        invalid_message: str,
    ) -> str:
        while True:
            value = input_fn(prompt).strip()
            if value:
                return value
            self.write(invalid_message, style=self.YELLOW)

    def ask_integer(
        self,
        prompt: str,
        *,
        input_fn: Callable[[str], str],
        minimum: int,
        maximum: int,
        default: int,
        invalid_message: str,
    ) -> int:
        if not minimum <= default <= maximum:
            raise ValueError("integer prompt default must be within its limits")
        while True:
            value = input_fn(prompt).strip()
            if not value:
                return default
            try:
                parsed = int(value)
            except ValueError:
                self.write(invalid_message, style=self.YELLOW)
                continue
            if minimum <= parsed <= maximum:
                return parsed
            self.write(invalid_message, style=self.YELLOW)
