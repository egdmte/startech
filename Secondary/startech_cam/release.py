"""Resolve the running source revision without invoking a shell."""

from __future__ import annotations

import os
from pathlib import Path
import re


HEX_COMMIT = re.compile(r"^[0-9a-f]{40}$")
ROOT = Path(__file__).resolve().parent.parent


def _git_directory(root: Path) -> Path | None:
    marker = root / ".git"
    if marker.is_dir():
        return marker
    if marker.is_file():
        text = marker.read_text(encoding="utf-8").strip()
        if text.startswith("gitdir: "):
            target = Path(text[8:])
            return target if target.is_absolute() else (root / target).resolve()
    return None


def _packed_ref(git_directory: Path, reference: str) -> str | None:
    packed = git_directory / "packed-refs"
    if not packed.is_file():
        return None
    for line in packed.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith(("#", "^")):
            continue
        commit, _, name = line.partition(" ")
        if name == reference and HEX_COMMIT.fullmatch(commit):
            return commit
    return None


def resolve_release(root: Path = ROOT) -> str:
    """Return an exact commit SHA, or ``development`` outside a Git checkout."""

    configured = os.environ.get("CAM_RELEASE", "").strip().lower()
    if configured:
        if not HEX_COMMIT.fullmatch(configured):
            raise RuntimeError("CAM_RELEASE must be one full 40-character Git SHA")
        return configured
    git_directory = _git_directory(root)
    if git_directory is None:
        return "development"
    head = (git_directory / "HEAD").read_text(encoding="utf-8").strip()
    if HEX_COMMIT.fullmatch(head):
        return head
    if head.startswith("ref: "):
        reference = head[5:]
        loose = git_directory / reference
        if loose.is_file():
            commit = loose.read_text(encoding="utf-8").strip()
            if HEX_COMMIT.fullmatch(commit):
                return commit
        packed = _packed_ref(git_directory, reference)
        if packed is not None:
            return packed
    return "development"


__all__ = ["resolve_release"]
