"""Composition and command-line entry point for the 3awnt teaching demo."""

from __future__ import annotations

from pathlib import Path
import tempfile

import tawnt

from .driver import DemoResult
from .lessons import legacy_names_lesson, live_safety_lesson, offline_profile_lesson


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
