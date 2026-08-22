"""Dependency-free terminal UI primitives for STARTECH-ARDA.

The UI renders state reported by the underlying operation.  It does not infer that
hardware is safe, arm the vehicle or turn a log message into physical proof.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import TextIO


@dataclass(frozen=True)
class MenuOption:
    """One numbered terminal-menu choice."""

    key: str
    label: str

    def __post_init__(self) -> None:
        if not isinstance(self.key, str) or not self.key.strip():
            raise ValueError("menu key must be non-empty text")
        if not isinstance(self.label, str) or not self.label.strip():
            raise ValueError("menu label must be non-empty text")


class TerminalUI:
    """Portable fixed-width terminal panels, menus, progress and summaries."""

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
    ) -> str:
        choices = tuple(options)
        if not choices:
            raise ValueError("terminal menu needs at least one option")
        keys = {option.key for option in choices}
        if len(keys) != len(choices):
            raise ValueError("terminal menu keys must be unique")

        self.section(title, style=self.BLUE)
        for option in choices:
            self.panel_line(f"[{option.key}]  {option.label}")
        self.rule()

        while True:
            value = input_fn(prompt).strip()
            if value in keys:
                return value
            self.write(invalid_message, style=self.YELLOW)

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
