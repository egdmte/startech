"""Publish one strict repository revision for KERİM's read-only web worker."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile


FORMAT = "startech-published-revision-v1"
HEX_COMMIT = re.compile(r"^[0-9a-f]{40}$")


class PublishedReferenceError(RuntimeError):
    pass


def write_reference(*, git_directory: Path, output: Path, commit: str) -> None:
    normalized = commit.strip().lower()
    if not HEX_COMMIT.fullmatch(normalized):
        raise PublishedReferenceError("commit must be one full lowercase Git SHA")
    resolved_git = git_directory.expanduser().resolve()
    try:
        result = subprocess.run(
            [
                "git",
                f"--git-dir={resolved_git}",
                "rev-parse",
                "--verify",
                f"{normalized}^{{commit}}",
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=15,
            text=True,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PublishedReferenceError(f"Git verification failed: {exc}") from exc
    if result.returncode != 0 or result.stdout.strip().lower() != normalized:
        raise PublishedReferenceError("commit is not an exact object in the selected repository")

    destination = output.expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    document = {
        "format": FORMAT,
        "commit": normalized,
        "updated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    body = (json.dumps(document, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", dir=destination.parent
    )
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--git-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--commit", required=True)
    options = parser.parse_args()
    try:
        write_reference(
            git_directory=options.git_dir,
            output=options.output,
            commit=options.commit,
        )
    except PublishedReferenceError as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
