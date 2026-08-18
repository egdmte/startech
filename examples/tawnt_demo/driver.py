"""Result model and memory-only motor driver used by the 3awnt lessons."""

from __future__ import annotations

from dataclasses import dataclass

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
