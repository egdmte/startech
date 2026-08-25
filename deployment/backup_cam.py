#!/usr/bin/env python3
"""Create a consistent online SQLite backup for CAM."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import re
import sqlite3
import tempfile


LABEL = re.compile(r"^[0-9a-z][0-9a-z._-]{0,63}$")


def _integrity(connection: sqlite3.Connection) -> None:
    result = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
    if result != "ok":
        raise RuntimeError(f"SQLite integrity check failed: {result}")


def backup_sqlite(database: Path, destination: Path, *, label: str) -> Path:
    """Use SQLite's online backup API and return the immutable snapshot path."""

    database = database.expanduser().resolve()
    destination = destination.expanduser().resolve()
    if not database.is_file():
        raise FileNotFoundError(f"CAM database does not exist: {database}")
    if not LABEL.fullmatch(label):
        raise ValueError("backup label must contain only lowercase letters, digits, ._- ")
    destination.mkdir(parents=True, exist_ok=True)
    os.chmod(destination, 0o700)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    final = destination / f"cam-{timestamp}-{label}.sqlite3"
    if final.exists():
        raise FileExistsError(f"backup already exists: {final}")

    handle = tempfile.NamedTemporaryFile(
        prefix=".cam-backup-", suffix=".tmp", dir=destination, delete=False
    )
    temporary = Path(handle.name)
    handle.close()
    os.chmod(temporary, 0o600)
    source = target = None
    try:
        source = sqlite3.connect(database.as_uri() + "?mode=ro", uri=True, timeout=10)
        source.execute("PRAGMA query_only = ON")
        _integrity(source)
        target = sqlite3.connect(temporary, timeout=10)
        source.backup(target)
        target.commit()
        _integrity(target)
        target.close()
        target = None
        source.close()
        source = None
        temporary.replace(final)
        os.chmod(final, 0o600)
        digest = hashlib.sha256(final.read_bytes()).hexdigest()
        checksum = final.with_suffix(final.suffix + ".sha256")
        checksum.write_text(f"{digest}  {final.name}\n", encoding="ascii")
        os.chmod(checksum, 0o600)
        return final
    except BaseException:
        if target is not None:
            target.close()
        if source is not None:
            source.close()
        temporary.unlink(missing_ok=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database",
        type=Path,
        default=Path(os.environ.get("CAM_DATABASE", "/srv/startech-cam/shared/cam.sqlite3")),
    )
    parser.add_argument(
        "--destination",
        type=Path,
        default=Path("/srv/startech-cam/shared/backups"),
    )
    parser.add_argument("--label", default="manual")
    args = parser.parse_args()
    print(backup_sqlite(args.database, args.destination, label=args.label))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
