"""Public surface of the hardware-free 3awnt teaching demonstration."""

from .cli import main, run_demo
from .driver import DemoResult, FakeMotorDriver
from .lessons import legacy_names_lesson, live_safety_lesson, offline_profile_lesson

__all__ = [
    "DemoResult",
    "FakeMotorDriver",
    "legacy_names_lesson",
    "live_safety_lesson",
    "main",
    "offline_profile_lesson",
    "run_demo",
]
