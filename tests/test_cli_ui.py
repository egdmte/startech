"""Behavior tests for the dependency-free STARTECH terminal UI."""

from __future__ import annotations

import io
import unittest

from arac.cli_ui import (
    MenuOption,
    NAVIGATE_BACK,
    NAVIGATE_DOWN,
    NAVIGATE_ENTER,
    NAVIGATE_UP,
    TerminalUI,
    supports_live_navigation,
)


class FakeTerminal(io.StringIO):
    def isatty(self) -> bool:
        return True


class TerminalUiTest(unittest.TestCase):
    OPTIONS = (
        MenuOption("1", "First action", "Explanation for the first action."),
        MenuOption("2", "Second action", "Explanation for the second action."),
        MenuOption("0", "Go back"),
    )

    def test_down_moves_blue_selection_and_enter_chooses_it(self):
        output = FakeTerminal()
        console = TerminalUI(output, color=True)
        keys = iter((NAVIGATE_DOWN, NAVIGATE_ENTER))

        selected = console.choose(
            "TEST MENU",
            self.OPTIONS,
            input_fn=lambda _prompt: "",
            prompt="unused",
            invalid_message="unused",
            key_reader=lambda: next(keys),
            back_key="0",
        )

        rendered = output.getvalue()
        self.assertEqual("2", selected)
        self.assertGreaterEqual(rendered.count("\033[2J\033[H"), 2)
        self.assertIn("> Second action", rendered)
        self.assertIn("Explanation for the second action.", rendered)
        self.assertIn("Up/Down Navigate", rendered)

    def test_navigation_wraps_and_escape_uses_back_option(self):
        output = FakeTerminal()
        console = TerminalUI(output, color=False)
        keys = iter((NAVIGATE_UP, NAVIGATE_ENTER))
        selected = console.choose(
            "TEST MENU",
            self.OPTIONS,
            input_fn=lambda _prompt: "",
            prompt="unused",
            invalid_message="unused",
            key_reader=lambda: next(keys),
            back_key="0",
        )
        self.assertEqual("0", selected)

        selected = console.choose(
            "TEST MENU",
            self.OPTIONS,
            input_fn=lambda _prompt: "",
            prompt="unused",
            invalid_message="unused",
            key_reader=lambda: NAVIGATE_BACK,
            initial_key="2",
            back_key="0",
        )
        self.assertEqual("0", selected)

    def test_typed_fallback_remains_available(self):
        output = io.StringIO()
        console = TerminalUI(output, color=False)
        values = iter(("not-an-option", "2"))
        selected = console.choose(
            "TEST MENU",
            self.OPTIONS,
            input_fn=lambda _prompt: next(values),
            prompt="Choose: ",
            invalid_message="Try again.",
        )
        self.assertEqual("2", selected)
        self.assertIn("Try again.", output.getvalue())
        self.assertNotIn("\033[2J", output.getvalue())

    def test_menu_rejects_invalid_navigation_defaults(self):
        console = TerminalUI(io.StringIO(), color=False)
        with self.assertRaisesRegex(ValueError, "initial menu key"):
            console.choose(
                "TEST MENU",
                self.OPTIONS,
                input_fn=lambda _prompt: "",
                prompt="unused",
                invalid_message="unused",
                key_reader=lambda: NAVIGATE_ENTER,
                initial_key="missing",
            )
        with self.assertRaisesRegex(ValueError, "back menu key"):
            console.choose(
                "TEST MENU",
                self.OPTIONS,
                input_fn=lambda _prompt: "",
                prompt="unused",
                invalid_message="unused",
                key_reader=lambda: NAVIGATE_ENTER,
                back_key="missing",
            )

    def test_live_navigation_requires_both_terminal_streams(self):
        terminal = FakeTerminal()
        plain = io.StringIO()
        self.assertTrue(supports_live_navigation(terminal, input_stream=terminal))
        self.assertFalse(supports_live_navigation(plain, input_stream=terminal))
        self.assertFalse(supports_live_navigation(terminal, input_stream=plain))


if __name__ == "__main__":
    unittest.main(verbosity=2)
