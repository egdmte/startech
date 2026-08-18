# -*- coding: utf-8 -*-
"""Backward-compatible launcher for the hardware-free 3awnt teaching demo."""

from examples.tawnt_demo import (
    DemoResult,
    FakeMotorDriver,
    legacy_names_lesson,
    live_safety_lesson,
    main,
    offline_profile_lesson,
    run_demo,
)

__all__ = [
    "DemoResult",
    "FakeMotorDriver",
    "legacy_names_lesson",
    "live_safety_lesson",
    "main",
    "offline_profile_lesson",
    "run_demo",
]


if __name__ == "__main__":
    raise SystemExit(main())
