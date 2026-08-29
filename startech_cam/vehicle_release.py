"""Build exact, offline vehicle source/profile bundles for KERİM.

The browser may read and archive Git objects, but it never updates the checkout
that is currently serving KERİM.  A bundle is source evidence plus one immutable
configuration; creating or extracting it does not install, activate, arm, or run
the vehicle.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from io import BytesIO
import json
from pathlib import Path
import re
import subprocess
from typing import Any, Iterable
import zipfile

from arac.startech.configuration.combined import split_v2

from .legacy_config import LegacyConfigError, generate_legacy_config


ROOT = Path(__file__).resolve().parent.parent
HEX_COMMIT = re.compile(r"^[0-9a-f]{40}$")
GIT_NAME = re.compile(r"^[A-Za-z0-9._/-]+$")
PUBLISHED_REFERENCE_FORMAT = "startech-published-revision-v1"
ARCHIVE_PATHS = ("LEGACY",)


class VehicleReleaseError(RuntimeError):
    """A release source or archive could not be proven and was rejected."""


@dataclass(frozen=True)
class Revision:
    commit: str
    committed_at_utc: str
    source: str

    @property
    def short(self) -> str:
        return self.commit[:7]


@dataclass(frozen=True)
class ReleaseSources:
    server: Revision
    repository: Revision | None
    relation: str
    server_dirty: bool
    remote_current: bool
    remote_error: str | None = None

    @property
    def differs(self) -> bool:
        return self.repository is not None and self.server.commit != self.repository.commit


@dataclass(frozen=True)
class VehicleBundle:
    body: bytes
    filename: str
    sha256: str
    commit: str
    profile_tag: str


def _checked_name(kind: str, value: str) -> str:
    normalized = value.strip()
    if (
        not normalized
        or normalized.startswith("-")
        or not GIT_NAME.fullmatch(normalized)
        or ".." in normalized.split("/")
    ):
        raise VehicleReleaseError(f"invalid Git {kind}")
    return normalized


def _git(
    root: Path,
    arguments: Iterable[str],
    *,
    timeout: float,
    binary: bool = False,
    check: bool = True,
) -> bytes | str:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *arguments],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise VehicleReleaseError(f"Git operation failed: {exc}") from exc
    if check and result.returncode != 0:
        error = result.stderr.decode("utf-8", errors="replace").strip()
        raise VehicleReleaseError(error or "Git rejected the requested operation")
    if binary:
        return result.stdout
    return result.stdout.decode("utf-8", errors="strict").strip()


def _revision(root: Path, reference: str, source: str, timeout: float) -> Revision:
    commit = str(
        _git(root, ["rev-parse", "--verify", f"{reference}^{{commit}}"], timeout=timeout)
    ).lower()
    if not HEX_COMMIT.fullmatch(commit):
        raise VehicleReleaseError(f"{source} did not resolve to one exact commit")
    committed_at = str(
        _git(root, ["show", "-s", "--format=%cI", commit], timeout=timeout)
    )
    try:
        parsed = datetime.fromisoformat(committed_at).astimezone(timezone.utc)
    except ValueError as exc:
        raise VehicleReleaseError(f"{source} commit time is invalid") from exc
    return Revision(commit, parsed.isoformat(timespec="seconds"), source)


def _published_revision(
    root: Path,
    reference_file: Path,
    source: str,
    timeout: float,
) -> Revision:
    try:
        raw = reference_file.read_bytes()
    except OSError as exc:
        raise VehicleReleaseError("published repository reference is unavailable") from exc
    if len(raw) > 4096:
        raise VehicleReleaseError("published repository reference is too large")

    def reject_duplicate(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise VehicleReleaseError("published repository reference has duplicate fields")
            result[key] = value
        return result

    try:
        document = json.loads(raw.decode("utf-8"), object_pairs_hook=reject_duplicate)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise VehicleReleaseError("published repository reference is invalid") from exc
    if not isinstance(document, dict) or set(document) != {
        "format",
        "commit",
        "updated_at_utc",
    }:
        raise VehicleReleaseError("published repository reference fields are invalid")
    if document["format"] != PUBLISHED_REFERENCE_FORMAT:
        raise VehicleReleaseError("published repository reference format is unsupported")
    commit = document["commit"]
    updated = document["updated_at_utc"]
    if not isinstance(commit, str) or not HEX_COMMIT.fullmatch(commit):
        raise VehicleReleaseError("published repository commit is invalid")
    if not isinstance(updated, str):
        raise VehicleReleaseError("published repository reference time is invalid")
    try:
        parsed_update = datetime.fromisoformat(updated)
    except ValueError as exc:
        raise VehicleReleaseError("published repository reference time is invalid") from exc
    if parsed_update.tzinfo is None:
        raise VehicleReleaseError("published repository reference time needs a UTC offset")
    return _revision(root, commit, source, timeout)


def _is_ancestor(root: Path, older: str, newer: str, timeout: float) -> bool:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "merge-base", "--is-ancestor", older, newer],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise VehicleReleaseError(f"Git comparison failed: {exc}") from exc
    if result.returncode not in {0, 1}:
        raise VehicleReleaseError("Git could not compare the two revisions")
    return result.returncode == 0


def inspect_release_sources(
    *,
    root: Path = ROOT,
    server_reference: str = "HEAD",
    remote: str = "origin",
    branch: str = "master",
    remote_label: str = "published repository",
    reference_file: Path | None = None,
    refresh_remote: bool = True,
    timeout: float = 20.0,
) -> ReleaseSources:
    """Inspect the running/server revision and one freshly fetched repository ref."""

    resolved_root = root.expanduser().resolve()
    if not (resolved_root / ".git").exists():
        raise VehicleReleaseError("the configured release source is not a Git checkout")
    checked_remote = _checked_name("remote", remote)
    checked_branch = _checked_name("branch", branch)
    checked_label = remote_label.strip()
    if not checked_label or len(checked_label) > 80:
        raise VehicleReleaseError("repository label must contain 1 to 80 characters")
    server = _revision(resolved_root, server_reference, "server", timeout)
    dirty = bool(
        _git(
            resolved_root,
            ["status", "--porcelain", "--untracked-files=normal"],
            timeout=timeout,
        )
    )

    remote_current = False
    remote_error: str | None = None
    repository: Revision | None = None
    remote_reference = f"refs/remotes/{checked_remote}/{checked_branch}"
    if reference_file is not None and reference_file.is_file():
        try:
            repository = _published_revision(
                resolved_root,
                reference_file.expanduser().resolve(),
                checked_label,
                timeout,
            )
            remote_current = True
        except VehicleReleaseError:
            repository = None
            remote_error = f"{checked_label} reference is invalid or stale."
    elif refresh_remote:
        destination = f"+refs/heads/{checked_branch}:{remote_reference}"
        try:
            _git(
                resolved_root,
                ["fetch", "--quiet", "--no-tags", checked_remote, destination],
                timeout=timeout,
            )
            remote_current = True
        except VehicleReleaseError:
            remote_error = f"{checked_label} refresh failed or timed out."

    else:
        repository = None

    if repository is None and remote_error is None:
        try:
            repository = _revision(
                resolved_root, remote_reference, checked_label, timeout
            )
        except VehicleReleaseError:
            repository = None

    if repository is None:
        relation = "remote-unavailable"
    elif server.commit == repository.commit:
        relation = "same"
    elif _is_ancestor(resolved_root, server.commit, repository.commit, timeout):
        relation = "server-behind"
    elif _is_ancestor(resolved_root, repository.commit, server.commit, timeout):
        relation = "server-ahead"
    else:
        relation = "diverged"
    return ReleaseSources(
        server=server,
        repository=repository,
        relation=relation,
        server_dirty=dirty,
        remote_current=remote_current,
        remote_error=remote_error,
    )


def _json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
    ).encode("utf-8")


def _archive(root: Path, commit: str, timeout: float) -> bytes:
    if not HEX_COMMIT.fullmatch(commit):
        raise VehicleReleaseError("bundle commit must be one full Git SHA")
    for required in ARCHIVE_PATHS:
        _git(root, ["cat-file", "-e", f"{commit}:{required}"], timeout=timeout)
    return bytes(
        _git(
            root,
            [
                "archive",
                "--format=zip",
                "--prefix=startech-vehicle/",
                commit,
                "--",
                *ARCHIVE_PATHS,
            ],
            timeout=timeout,
            binary=True,
        )
    )


def build_vehicle_bundle(
    *,
    root: Path,
    revision: Revision,
    profile_tag: str,
    document: dict[str, Any],
    timeout: float = 30.0,
    now: datetime | None = None,
) -> VehicleBundle:
    """Build a source archive plus one KERİM configuration profile."""

    if (
        len(profile_tag) != 6
        or any(character not in "0123456789abcdef" for character in profile_tag)
    ):
        raise VehicleReleaseError("profile tag is invalid")
    calibration, settings = split_v2(document)
    combined_bytes = _json_bytes(document)
    calibration_bytes = _json_bytes(calibration)
    settings_bytes = _json_bytes(settings)
    archive = _archive(root.expanduser().resolve(), revision.commit, timeout)
    generated = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    with zipfile.ZipFile(BytesIO(archive)) as source_archive:
        try:
            template = source_archive.read(
                "startech-vehicle/LEGACY/config.py"
            ).decode("utf-8")
            generated_config = generate_legacy_config(
                template, document, profile_tag=profile_tag
            ).encode("utf-8")
        except (KeyError, UnicodeDecodeError, LegacyConfigError) as exc:
            raise VehicleReleaseError(
                f"selected revision cannot receive this KERİM profile: {exc}"
            ) from exc

        rebuilt = BytesIO()
        with zipfile.ZipFile(rebuilt, "w", compression=zipfile.ZIP_DEFLATED) as target:
            for item in source_archive.infolist():
                if item.filename == "startech-vehicle/LEGACY/config.py":
                    target.writestr(item, generated_config)
                else:
                    target.writestr(item, source_archive.read(item.filename))

    profile = document["profil"]
    manifest = {
        "format": "startech-vehicle-release-v1",
        "generated_at_utc": generated.isoformat(timespec="seconds"),
        "source": {
            "selected_from": revision.source,
            "git_commit": revision.commit,
            "committed_at_utc": revision.committed_at_utc,
        },
        "profile": {
            "kerim_tag": profile_tag,
            "name": profile["ad"],
            "workflow": profile["is_akisi"],
            "combined_sha256": hashlib.sha256(combined_bytes).hexdigest(),
            "calibration_sha256": hashlib.sha256(calibration_bytes).hexdigest(),
            "settings_sha256": hashlib.sha256(settings_bytes).hexdigest(),
        },
        "physical_status": "PHYSICALLY UNVERIFIED",
        "limitations": [
            "The generated LEGACY/config.py has not been tested on the unavailable car.",
            "Creating this archive does not start the car.",
        ],
    }
    instructions = f"""STARTECH vehicle release

Source commit: {revision.commit}
KERİM profile: {profile_tag} ({profile['ad']})
Physical status: PHYSICALLY UNVERIFIED

The selected KERİM values are already written into LEGACY/config.py in this bundle.
GPIO pins, timing values and canon logic not represented by KERİM are preserved from
the selected Git revision. The JSON copies are included so the source values remain
readable.

The car is currently unavailable, so the generated configuration remains physically
unverified. Creating or extracting this bundle does not start the car.
"""

    output = rebuilt
    with zipfile.ZipFile(output, "a", compression=zipfile.ZIP_DEFLATED) as bundle:
        bundle.writestr("KERIM_RELEASE/manifest.json", _json_bytes(manifest))
        bundle.writestr("KERIM_RELEASE/yapilandirma-v2.json", combined_bytes)
        bundle.writestr("KERIM_RELEASE/kalibrasyon-v1.json", calibration_bytes)
        bundle.writestr("KERIM_RELEASE/ayarlar-v1.json", settings_bytes)
        bundle.writestr("KERIM_RELEASE/INSTALL.txt", instructions.encode("utf-8"))
    body = output.getvalue()
    filename = f"startech-vehicle-{revision.short}-{profile_tag}.zip"
    return VehicleBundle(
        body=body,
        filename=filename,
        sha256=hashlib.sha256(body).hexdigest(),
        commit=revision.commit,
        profile_tag=profile_tag,
    )


__all__ = [
    "ReleaseSources",
    "Revision",
    "VehicleBundle",
    "VehicleReleaseError",
    "build_vehicle_bundle",
    "inspect_release_sources",
]
