"""Strict local registry for STARTECH calibration/settings profile pairs.

The registry joins existing v1 ``kalibrasyon.json`` and ``ayarlar.json`` files with
an external ``profil.json`` envelope.  Installing or selecting a profile never arms
the vehicle and never upgrades an unverified value into a physical measurement.
"""

from __future__ import annotations

from collections.abc import Mapping
import copy
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
from typing import Any, Callable
import uuid

from jsonschema import Draft202012Validator

from .combined import combined_config_errors, split_v2
from .validation import (
    ayarlar_uyarilari,
    ayarlari_dogrula,
    kalibrasyon_uyarilari,
    kalibrasyonu_dogrula,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PROFILE_SCHEMA_PATH = PROJECT_ROOT / "config" / "schema" / "profil-v1.schema.json"
PROFILE_SCHEMA_VERSION = 1
ACTIVE_SCHEMA_VERSION = 1
CALIBRATION_NAME = "kalibrasyon.json"
SETTINGS_NAME = "ayarlar.json"
PROFILE_NAME = "profil.json"
ACTIVE_NAME = "aktif-profil.json"
MAX_JSON_BYTES = 1_000_000
_IDENTIFIER = re.compile(r"^[0-9a-f]{32}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class ProfileError(RuntimeError):
    """Base error for a profile operation that cannot be completed safely."""


class InvalidJsonFile(ProfileError, ValueError):
    """Raised for malformed, duplicate, oversized or non-object JSON input."""


class InvalidProfile(ProfileError, ValueError):
    """Raised when profile metadata or its paired JSON values are invalid."""


class ProfileIntegrityError(ProfileError):
    """Raised when installed bytes no longer match their recorded hashes."""


class ProfileNotFound(ProfileError, FileNotFoundError):
    """Raised when a requested profile identifier is not installed or archived."""


class ProfileAlreadyExists(ProfileError, FileExistsError):
    """Raised when an operation would overwrite an existing profile or export."""


class WarningAcknowledgementRequired(ProfileError):
    """Raised when activation warnings were not acknowledged exactly."""


class ActiveProfileError(ProfileError):
    """Raised when the active pointer is missing, malformed or inconsistent."""


class ActiveProfileArchiveError(ProfileError):
    """Raised when code attempts to archive the selected profile."""


class ProfileLocation(str, Enum):
    INSTALLED = "INSTALLED"
    ARCHIVED = "ARCHIVED"


@dataclass(frozen=True)
class ProfileManifest:
    """Immutable metadata joining one calibration/settings pair."""

    profile_id: str
    name: str
    created_at_utc: str
    source_type: str
    parent_profile_id: str | None
    camera_session_id: str | None
    note: str
    calibration_sha256: str
    settings_sha256: str
    width: int
    height: int
    bgr_output: bool
    rotate_180: bool
    warnings: tuple[str, ...]
    warning_digest: str

    @property
    def schema_version(self) -> int:
        return PROFILE_SCHEMA_VERSION

    def to_dict(self) -> dict[str, object]:
        return {
            "sema_surumu": self.schema_version,
            "profil_kimligi": self.profile_id,
            "ad": self.name,
            "olusturuldu_utc": self.created_at_utc,
            "kaynak": {
                "tur": self.source_type,
                "ebeveyn_profil_kimligi": self.parent_profile_id,
                "kamera_oturumu_kimligi": self.camera_session_id,
                "not": self.note,
            },
            "kalibrasyon": {
                "dosya": CALIBRATION_NAME,
                "sha256": self.calibration_sha256,
                "sema_surumu": 1,
            },
            "ayarlar": {
                "dosya": SETTINGS_NAME,
                "sha256": self.settings_sha256,
                "sema_surumu": 1,
            },
            "uyumluluk": {
                "kamera_genislik": self.width,
                "kamera_yukseklik": self.height,
                "bgr_cikis": self.bgr_output,
                "dondur_180": self.rotate_180,
            },
            "uyarilar": list(self.warnings),
            "uyari_ozeti": self.warning_digest,
        }

    @classmethod
    def from_dict(cls, value: object) -> "ProfileManifest":
        errors = profile_schema_errors(value)
        if errors:
            raise InvalidProfile("; ".join(errors))
        assert isinstance(value, dict)
        source = value["kaynak"]
        calibration = value["kalibrasyon"]
        settings = value["ayarlar"]
        compatibility = value["uyumluluk"]
        manifest = cls(
            profile_id=value["profil_kimligi"],
            name=value["ad"],
            created_at_utc=value["olusturuldu_utc"],
            source_type=source["tur"],
            parent_profile_id=source["ebeveyn_profil_kimligi"],
            camera_session_id=source["kamera_oturumu_kimligi"],
            note=source["not"],
            calibration_sha256=calibration["sha256"],
            settings_sha256=settings["sha256"],
            width=compatibility["kamera_genislik"],
            height=compatibility["kamera_yukseklik"],
            bgr_output=compatibility["bgr_cikis"],
            rotate_180=compatibility["dondur_180"],
            warnings=tuple(value["uyarilar"]),
            warning_digest=value["uyari_ozeti"],
        )
        _require_utc(manifest.created_at_utc, "olusturuldu_utc")
        if _warning_digest(manifest.warnings) != manifest.warning_digest:
            raise InvalidProfile("uyari_ozeti does not match profile warnings")
        return manifest


@dataclass(frozen=True)
class ActiveSelection:
    """Authoritative, atomic pointer to one validated installed profile."""

    revision: int
    selection_id: str
    profile_id: str
    selected_at_utc: str
    calibration_sha256: str
    settings_sha256: str
    warning_digest: str
    previous_selection_id: str | None
    warning_reviewer: str | None
    warning_reviewed_at_utc: str | None

    def to_dict(self) -> dict[str, object]:
        approval: dict[str, str] | None = None
        if self.warning_reviewer is not None:
            approval = {
                "onaylayan": self.warning_reviewer,
                "zaman_utc": self.warning_reviewed_at_utc or "",
                "uyari_ozeti": self.warning_digest,
            }
        return {
            "sema_surumu": ACTIVE_SCHEMA_VERSION,
            "revizyon": self.revision,
            "secim_kimligi": self.selection_id,
            "profil_kimligi": self.profile_id,
            "secildi_utc": self.selected_at_utc,
            "kalibrasyon_sha256": self.calibration_sha256,
            "ayarlar_sha256": self.settings_sha256,
            "uyari_ozeti": self.warning_digest,
            "onceki_secim_kimligi": self.previous_selection_id,
            "uyari_onayi": approval,
        }

    @classmethod
    def from_dict(cls, value: object) -> "ActiveSelection":
        item = _strict_object(
            value,
            {
                "sema_surumu",
                "revizyon",
                "secim_kimligi",
                "profil_kimligi",
                "secildi_utc",
                "kalibrasyon_sha256",
                "ayarlar_sha256",
                "uyari_ozeti",
                "onceki_secim_kimligi",
                "uyari_onayi",
            },
            "active profile pointer",
        )
        if item["sema_surumu"] != ACTIVE_SCHEMA_VERSION:
            raise ActiveProfileError("unsupported active-profile schema version")
        revision = item["revizyon"]
        if isinstance(revision, bool) or not isinstance(revision, int) or revision <= 0:
            raise ActiveProfileError("active revision must be a positive integer")
        selection_id = _identifier(item["secim_kimligi"], "secim_kimligi")
        profile_id = _identifier(item["profil_kimligi"], "profil_kimligi")
        selected_at = _require_utc(item["secildi_utc"], "secildi_utc")
        calibration_hash = _hash_text(
            item["kalibrasyon_sha256"], "kalibrasyon_sha256"
        )
        settings_hash = _hash_text(item["ayarlar_sha256"], "ayarlar_sha256")
        warning_digest = _hash_text(item["uyari_ozeti"], "uyari_ozeti")
        previous = item["onceki_secim_kimligi"]
        if previous is not None:
            previous = _identifier(previous, "onceki_secim_kimligi")

        reviewer: str | None = None
        reviewed_at: str | None = None
        approval = item["uyari_onayi"]
        if approval is not None:
            approval_item = _strict_object(
                approval,
                {"onaylayan", "zaman_utc", "uyari_ozeti"},
                "warning approval",
            )
            reviewer = _text(approval_item["onaylayan"], "onaylayan", maximum=80)
            reviewed_at = _require_utc(approval_item["zaman_utc"], "zaman_utc")
            if approval_item["uyari_ozeti"] != warning_digest:
                raise ActiveProfileError("warning approval digest does not match")

        return cls(
            revision=revision,
            selection_id=selection_id,
            profile_id=profile_id,
            selected_at_utc=selected_at,
            calibration_sha256=calibration_hash,
            settings_sha256=settings_hash,
            warning_digest=warning_digest,
            previous_selection_id=previous,
            warning_reviewer=reviewer,
            warning_reviewed_at_utc=reviewed_at,
        )


@dataclass(frozen=True)
class LoadedProfile:
    """A profile whose envelope, pair, hashes and current warnings agree."""

    manifest: ProfileManifest
    calibration: dict[str, Any]
    settings: dict[str, Any]
    location: ProfileLocation
    directory: Path


@dataclass(frozen=True)
class ProfileSummary:
    profile_id: str
    name: str
    location: ProfileLocation
    warning_count: int
    width: int
    height: int


@dataclass(frozen=True)
class ProfileDifference:
    path: str
    left: object
    right: object


@dataclass(frozen=True)
class HistoryEntry:
    selection: ActiveSelection
    committed: bool


@dataclass(frozen=True)
class ActiveDiagnosis:
    valid: bool
    profile_id: str | None
    errors: tuple[str, ...]
    warnings: tuple[str, ...]


def _load_trusted_schema() -> dict[str, Any]:
    try:
        value = json.loads(PROFILE_SCHEMA_PATH.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"profile schema could not be loaded: {exc}") from exc
    if not isinstance(value, dict):
        raise RuntimeError("profile schema root must be an object")
    Draft202012Validator.check_schema(value)
    return value


PROFILE_SCHEMA = _load_trusted_schema()


def profile_schema_errors(value: object) -> list[str]:
    validator = Draft202012Validator(PROFILE_SCHEMA)
    errors = sorted(
        validator.iter_errors(value),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    result = []
    for error in errors:
        path = ".".join(str(part) for part in error.absolute_path) or "<kok>"
        result.append(f"{path}: {error.message}")
    return result


def _duplicate_guard(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise InvalidJsonFile(f"duplicate JSON field: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise InvalidJsonFile(f"non-finite JSON number is forbidden: {value}")


def _read_json_bytes(path: Path, *, maximum: int = MAX_JSON_BYTES) -> tuple[dict[str, Any], bytes]:
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise InvalidJsonFile(f"could not inspect JSON file {path}: {exc}") from exc
    if size > maximum:
        raise InvalidJsonFile(f"JSON file exceeds {maximum} bytes: {path}")
    try:
        raw = path.read_bytes()
        text = raw.decode("utf-8-sig")
        value = json.loads(
            text,
            object_pairs_hook=_duplicate_guard,
            parse_constant=_reject_constant,
        )
    except InvalidJsonFile:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise InvalidJsonFile(f"could not read JSON file {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise InvalidJsonFile(f"JSON root must be an object: {path}")
    try:
        stored = _storage_bytes(value)
    except (TypeError, ValueError) as exc:
        raise InvalidJsonFile(f"JSON value is not finite or serializable: {path}") from exc
    return value, stored


def _storage_bytes(value: object) -> bytes:
    # Field order is deliberately preserved.  The legacy six-character
    # calibration stamp is order-sensitive, so sorting an otherwise equivalent
    # calibration object would invalidate that existing v1 contract.
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            indent=2,
        )
        + "\n"
    ).encode("utf-8")


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _warning_digest(warnings: tuple[str, ...]) -> str:
    return _sha256(
        json.dumps(
            list(warnings),
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
    )


def _strict_object(value: object, fields: set[str], name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ActiveProfileError(f"{name} must be a JSON object")
    keys = set(value)
    missing = fields - keys
    unknown = keys - fields
    if missing:
        raise ActiveProfileError(f"{name} missing fields: {', '.join(sorted(missing))}")
    if unknown:
        raise ActiveProfileError(f"{name} unknown fields: {', '.join(sorted(unknown))}")
    return value


def _identifier(value: object, name: str) -> str:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise InvalidProfile(f"{name} must contain 32 lowercase hexadecimal characters")
    return value


def _hash_text(value: object, name: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise InvalidProfile(f"{name} must contain a full lowercase SHA-256 value")
    return value


def _text(value: object, name: str, *, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InvalidProfile(f"{name} must be non-empty text")
    result = value.strip()
    if len(result) > maximum:
        raise InvalidProfile(f"{name} cannot exceed {maximum} characters")
    return result


def _optional_text(value: object, name: str, *, maximum: int) -> str | None:
    if value is None:
        return None
    return _text(value, name, maximum=maximum)


def _require_utc(value: object, name: str) -> str:
    if not isinstance(value, str):
        raise InvalidProfile(f"{name} must be an ISO UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise InvalidProfile(f"{name} must be an ISO UTC timestamp") from exc
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise InvalidProfile(f"{name} must use UTC +00:00")
    return value


def _utc_text(now: Callable[[], datetime]) -> str:
    value = now()
    if not isinstance(value, datetime):
        raise TypeError("clock must return datetime")
    if value.tzinfo is None:
        raise ValueError("clock must return a timezone-aware datetime")
    return value.astimezone(timezone.utc).isoformat()


def _atomic_write(path: Path, payload: bytes) -> None:
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary.write_bytes(payload)
        os.replace(temporary, path)
    except OSError as exc:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise ProfileError(f"could not atomically write {path}: {exc}") from exc


def _profile_warnings(calibration: dict[str, Any], settings: dict[str, Any]) -> tuple[str, ...]:
    warnings = kalibrasyon_uyarilari(calibration)
    warnings.extend(ayarlar_uyarilari(settings, calibration))
    return tuple(sorted(set(warnings)))


def _validate_pair(calibration: dict[str, Any], settings: dict[str, Any]) -> tuple[str, ...]:
    errors = [f"kalibrasyon: {item}" for item in kalibrasyonu_dogrula(calibration)]
    errors.extend(f"ayarlar: {item}" for item in ayarlari_dogrula(settings))
    return tuple(errors)


def default_profile_root(
    *,
    environment: Mapping[str, str] | None = None,
    platform_name: str | None = None,
    home: Path | None = None,
) -> Path:
    """Return an OS-local profile root outside the repository by default."""

    env = os.environ if environment is None else environment
    explicit = env.get("STARTECH_PROFILE_ROOT")
    if explicit:
        return Path(explicit).expanduser()
    selected_platform = os.name if platform_name is None else platform_name
    selected_home = Path.home() if home is None else Path(home)
    if selected_platform == "nt":
        base = Path(env.get("LOCALAPPDATA", selected_home / "AppData" / "Local"))
        return base / "STARTECH" / "configuration"
    base = Path(env.get("XDG_CONFIG_HOME", selected_home / ".config"))
    return base / "startech" / "configuration"


class ProfileStore:
    """Filesystem-backed profile registry with immutable installed pairs."""

    def __init__(
        self,
        root: str | Path | None = None,
        *,
        id_factory: Callable[[], str] = lambda: uuid.uuid4().hex,
        selection_id_factory: Callable[[], str] = lambda: uuid.uuid4().hex,
        now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self.root = default_profile_root() if root is None else Path(root)
        self._id_factory = id_factory
        self._selection_id_factory = selection_id_factory
        self._now = now

    @property
    def profiles_directory(self) -> Path:
        return self.root / "profiles"

    @property
    def archive_directory(self) -> Path:
        return self.root / "archive"

    @property
    def history_directory(self) -> Path:
        return self.root / "history"

    @property
    def staging_directory(self) -> Path:
        return self.root / ".staging"

    @property
    def active_path(self) -> Path:
        return self.root / ACTIVE_NAME

    def _initialize(self) -> None:
        try:
            for directory in (
                self.profiles_directory,
                self.archive_directory,
                self.history_directory,
                self.staging_directory,
            ):
                directory.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise ProfileError(f"profile registry could not be initialized: {exc}") from exc

    def _new_id(self, factory: Callable[[], str], name: str) -> str:
        return _identifier(factory(), name)

    def _locate(
        self, profile_id: str, *, include_archived: bool = True
    ) -> tuple[Path, ProfileLocation]:
        selected = _identifier(profile_id, "profil_kimligi")
        installed = self.profiles_directory / selected
        archived = self.archive_directory / selected
        if installed.is_dir() and archived.is_dir():
            raise ProfileIntegrityError("profile exists in installed and archive locations")
        if installed.is_dir():
            return installed, ProfileLocation.INSTALLED
        if include_archived and archived.is_dir():
            return archived, ProfileLocation.ARCHIVED
        raise ProfileNotFound(f"profile not found: {selected}")

    def _load_stored_json(self, path: Path) -> tuple[dict[str, Any], bytes]:
        value, canonical = _read_json_bytes(path)
        try:
            actual = path.read_bytes()
        except OSError as exc:
            raise ProfileIntegrityError(f"stored profile file is unreadable: {path}") from exc
        if actual != canonical:
            raise ProfileIntegrityError(f"stored profile file is not canonical: {path.name}")
        return value, actual

    def load_profile(
        self,
        profile_id: str,
        *,
        include_archived: bool = True,
    ) -> LoadedProfile:
        directory, location = self._locate(
            profile_id, include_archived=include_archived
        )
        manifest_value, manifest_bytes = self._load_stored_json(directory / PROFILE_NAME)
        del manifest_bytes
        manifest = ProfileManifest.from_dict(manifest_value)
        if manifest.profile_id != directory.name:
            raise ProfileIntegrityError("profile directory and manifest identifiers differ")

        calibration, calibration_bytes = self._load_stored_json(
            directory / CALIBRATION_NAME
        )
        settings, settings_bytes = self._load_stored_json(directory / SETTINGS_NAME)
        if _sha256(calibration_bytes) != manifest.calibration_sha256:
            raise ProfileIntegrityError("stored calibration hash does not match profile")
        if _sha256(settings_bytes) != manifest.settings_sha256:
            raise ProfileIntegrityError("stored settings hash does not match profile")
        errors = _validate_pair(calibration, settings)
        if errors:
            raise ProfileIntegrityError("; ".join(errors))
        warnings = _profile_warnings(calibration, settings)
        if warnings != manifest.warnings:
            raise ProfileIntegrityError("current warnings do not match profile envelope")
        camera = calibration["kamera"]
        compatibility = (
            camera["genislik"],
            camera["yukseklik"],
            camera["bgr_cikis"],
            camera["dondur_180"],
        )
        recorded_compatibility = (
            manifest.width,
            manifest.height,
            manifest.bgr_output,
            manifest.rotate_180,
        )
        if compatibility != recorded_compatibility:
            raise ProfileIntegrityError("camera compatibility does not match profile envelope")
        return LoadedProfile(
            manifest=manifest,
            calibration=calibration,
            settings=settings,
            location=location,
            directory=directory,
        )

    def list_profiles(self, *, include_archived: bool = True) -> tuple[ProfileSummary, ...]:
        summaries: list[ProfileSummary] = []
        locations = [(self.profiles_directory, ProfileLocation.INSTALLED)]
        if include_archived:
            locations.append((self.archive_directory, ProfileLocation.ARCHIVED))
        for base, location in locations:
            if not base.exists():
                continue
            for directory in sorted(base.iterdir(), key=lambda path: path.name):
                if not directory.is_dir() or not _IDENTIFIER.fullmatch(directory.name):
                    continue
                loaded = self.load_profile(
                    directory.name, include_archived=include_archived
                )
                summaries.append(
                    ProfileSummary(
                        profile_id=loaded.manifest.profile_id,
                        name=loaded.manifest.name,
                        location=location,
                        warning_count=len(loaded.manifest.warnings),
                        width=loaded.manifest.width,
                        height=loaded.manifest.height,
                    )
                )
        return tuple(
            sorted(summaries, key=lambda item: (item.location.value, item.name, item.profile_id))
        )

    def import_pair(
        self,
        calibration_path: str | Path,
        settings_path: str | Path,
        *,
        name: str,
        note: str = "",
        camera_session_id: str | None = None,
    ) -> LoadedProfile:
        calibration, _unused_calibration = _read_json_bytes(Path(calibration_path))
        settings, _unused_settings = _read_json_bytes(Path(settings_path))
        return self._install_values(
            calibration,
            settings,
            name=name,
            note=note,
            source_type="IMPORT",
            parent_profile_id=None,
            camera_session_id=camera_session_id,
        )

    def import_combined(
        self,
        document: dict[str, Any],
        *,
        deployment_id: str,
    ) -> LoadedProfile:
        """Install one valid merged v2 document without selecting it.

        Repeating the same deployment is idempotent.  Reusing its identifier for
        different bytes fails closed instead of silently replacing a profile.
        """

        if (
            not isinstance(deployment_id, str)
            or not re.fullmatch(r"[A-Za-z0-9._:-]{1,80}", deployment_id)
        ):
            raise InvalidProfile("deployment id is malformed")
        errors = combined_config_errors(document)
        if errors:
            raise InvalidProfile("; ".join(errors))
        calibration, settings = split_v2(document)
        calibration_hash = _sha256(_storage_bytes(calibration))
        settings_hash = _sha256(_storage_bytes(settings))
        note = f"CAM deployment {deployment_id}"
        for summary in self.list_profiles(include_archived=False):
            loaded = self.load_profile(summary.profile_id, include_archived=False)
            if loaded.manifest.note != note:
                continue
            if (
                loaded.manifest.calibration_sha256 != calibration_hash
                or loaded.manifest.settings_sha256 != settings_hash
            ):
                raise ProfileIntegrityError(
                    "deployment id already belongs to different configuration bytes"
                )
            return loaded
        return self._install_values(
            calibration,
            settings,
            name=str(document["profil"]["ad"]),
            note=note,
            source_type="IMPORT",
            parent_profile_id=None,
            camera_session_id=None,
        )

    def create_settings_variant(
        self,
        parent_profile_id: str,
        settings: dict[str, Any],
        *,
        name: str,
        note: str = "",
    ) -> LoadedProfile:
        parent = self.load_profile(parent_profile_id, include_archived=False)
        return self._install_values(
            copy.deepcopy(parent.calibration),
            copy.deepcopy(settings),
            name=name,
            note=note,
            source_type="SETTINGS_VARIANT",
            parent_profile_id=parent.manifest.profile_id,
            camera_session_id=parent.manifest.camera_session_id,
        )

    def _install_values(
        self,
        calibration: dict[str, Any],
        settings: dict[str, Any],
        *,
        name: str,
        note: str,
        source_type: str,
        parent_profile_id: str | None,
        camera_session_id: str | None,
    ) -> LoadedProfile:
        selected_name = _text(name, "profile name", maximum=80)
        if not isinstance(note, str) or len(note) > 500:
            raise InvalidProfile("profile note must be text no longer than 500 characters")
        selected_session = _optional_text(
            camera_session_id, "camera session id", maximum=128
        )
        errors = _validate_pair(calibration, settings)
        if errors:
            raise InvalidProfile("; ".join(errors))
        calibration_bytes = _storage_bytes(calibration)
        settings_bytes = _storage_bytes(settings)
        if len(calibration_bytes) > MAX_JSON_BYTES or len(settings_bytes) > MAX_JSON_BYTES:
            raise InvalidJsonFile("canonical profile JSON exceeds the file-size limit")
        warnings = _profile_warnings(calibration, settings)
        camera = calibration["kamera"]
        profile_id = self._new_id(self._id_factory, "profile id")
        if parent_profile_id is not None:
            parent_profile_id = _identifier(parent_profile_id, "parent profile id")
        manifest = ProfileManifest(
            profile_id=profile_id,
            name=selected_name,
            created_at_utc=_utc_text(self._now),
            source_type=source_type,
            parent_profile_id=parent_profile_id,
            camera_session_id=selected_session,
            note=note,
            calibration_sha256=_sha256(calibration_bytes),
            settings_sha256=_sha256(settings_bytes),
            width=camera["genislik"],
            height=camera["yukseklik"],
            bgr_output=camera["bgr_cikis"],
            rotate_180=camera["dondur_180"],
            warnings=warnings,
            warning_digest=_warning_digest(warnings),
        )
        manifest_value = manifest.to_dict()
        schema_errors = profile_schema_errors(manifest_value)
        if schema_errors:
            raise InvalidProfile("; ".join(schema_errors))

        self._initialize()
        target = self.profiles_directory / profile_id
        if target.exists() or (self.archive_directory / profile_id).exists():
            raise ProfileAlreadyExists(f"profile identifier already exists: {profile_id}")
        staging = self.staging_directory / f"{profile_id}-{uuid.uuid4().hex}"
        try:
            staging.mkdir(parents=False, exist_ok=False)
            (staging / CALIBRATION_NAME).write_bytes(calibration_bytes)
            (staging / SETTINGS_NAME).write_bytes(settings_bytes)
            (staging / PROFILE_NAME).write_bytes(_storage_bytes(manifest_value))
            os.replace(staging, target)
        except OSError as exc:
            raise ProfileError(
                f"profile installation failed; staging was not activated: {exc}"
            ) from exc
        return self.load_profile(profile_id, include_archived=False)

    def _read_active_pointer(self) -> ActiveSelection:
        if not self.active_path.is_file():
            raise ActiveProfileError("no active profile has been selected")
        value, _canonical = _read_json_bytes(self.active_path)
        try:
            return ActiveSelection.from_dict(value)
        except (InvalidProfile, ActiveProfileError) as exc:
            raise ActiveProfileError(str(exc)) from exc

    def activate_profile(
        self,
        profile_id: str,
        *,
        reviewer: str | None = None,
        warning_digest: str | None = None,
    ) -> ActiveSelection:
        loaded = self.load_profile(profile_id, include_archived=False)
        warnings = loaded.manifest.warnings
        reviewed_at: str | None = None
        selected_reviewer: str | None = None
        if warnings:
            if warning_digest != loaded.manifest.warning_digest:
                raise WarningAcknowledgementRequired(
                    "activation requires the exact current warning digest"
                )
            try:
                selected_reviewer = _text(
                    reviewer, "warning reviewer", maximum=80
                )
            except InvalidProfile as exc:
                raise WarningAcknowledgementRequired(
                    "activation warnings require a named reviewer"
                ) from exc
            reviewed_at = _utc_text(self._now)

        previous: ActiveSelection | None = None
        if self.active_path.exists():
            previous = self._read_active_pointer()
        selection = ActiveSelection(
            revision=1 if previous is None else previous.revision + 1,
            selection_id=self._new_id(self._selection_id_factory, "selection id"),
            profile_id=loaded.manifest.profile_id,
            selected_at_utc=_utc_text(self._now),
            calibration_sha256=loaded.manifest.calibration_sha256,
            settings_sha256=loaded.manifest.settings_sha256,
            warning_digest=loaded.manifest.warning_digest,
            previous_selection_id=(
                None if previous is None else previous.selection_id
            ),
            warning_reviewer=selected_reviewer,
            warning_reviewed_at_utc=reviewed_at,
        )
        self._initialize()
        history_path = self.history_directory / f"{selection.selection_id}.json"
        if history_path.exists():
            raise ProfileAlreadyExists("selection history identifier already exists")
        payload = _storage_bytes(selection.to_dict())
        _atomic_write(history_path, payload)
        _atomic_write(self.active_path, payload)
        return self.load_active_selection()

    def load_active_selection(self) -> ActiveSelection:
        selection = self._read_active_pointer()
        loaded = self.load_profile(selection.profile_id, include_archived=False)
        expected = (
            loaded.manifest.calibration_sha256,
            loaded.manifest.settings_sha256,
            loaded.manifest.warning_digest,
        )
        actual = (
            selection.calibration_sha256,
            selection.settings_sha256,
            selection.warning_digest,
        )
        if expected != actual:
            raise ActiveProfileError("active pointer no longer matches its profile")
        if loaded.manifest.warnings and selection.warning_reviewer is None:
            raise ActiveProfileError("active warning-bearing profile lacks review evidence")
        history_path = self.history_directory / f"{selection.selection_id}.json"
        if not history_path.is_file():
            raise ActiveProfileError("active selection has no matching history entry")
        history_value, _canonical = _read_json_bytes(history_path)
        history_selection = ActiveSelection.from_dict(history_value)
        if history_selection != selection:
            raise ActiveProfileError("active pointer and history entry differ")
        return selection

    def load_active_profile(self) -> LoadedProfile:
        selection = self.load_active_selection()
        return self.load_profile(selection.profile_id, include_archived=False)

    def diagnose_active(
        self,
        *,
        camera_dimensions: tuple[int, int] | None = None,
    ) -> ActiveDiagnosis:
        try:
            selection = self.load_active_selection()
            loaded = self.load_profile(selection.profile_id, include_archived=False)
        except ProfileError as exc:
            return ActiveDiagnosis(False, None, (str(exc),), ())
        errors: list[str] = []
        if camera_dimensions is not None:
            if (
                not isinstance(camera_dimensions, tuple)
                or len(camera_dimensions) != 2
                or any(
                    isinstance(item, bool) or not isinstance(item, int) or item <= 0
                    for item in camera_dimensions
                )
            ):
                raise ValueError("camera dimensions must contain two positive integers")
            if camera_dimensions != (loaded.manifest.width, loaded.manifest.height):
                errors.append(
                    "active calibration resolution does not match the observed camera"
                )
        return ActiveDiagnosis(
            valid=not errors,
            profile_id=loaded.manifest.profile_id,
            errors=tuple(errors),
            warnings=loaded.manifest.warnings,
        )

    def activation_history(self) -> tuple[HistoryEntry, ...]:
        entries: dict[str, ActiveSelection] = {}
        if self.history_directory.exists():
            for path in sorted(self.history_directory.glob("*.json")):
                try:
                    value, _canonical = _read_json_bytes(path)
                    selection = ActiveSelection.from_dict(value)
                except ProfileError:
                    continue
                if path.stem == selection.selection_id:
                    entries[selection.selection_id] = selection

        committed: set[str] = set()
        try:
            cursor: str | None = self._read_active_pointer().selection_id
        except ProfileError:
            cursor = None
        while cursor is not None and cursor in entries and cursor not in committed:
            committed.add(cursor)
            cursor = entries[cursor].previous_selection_id
        return tuple(
            HistoryEntry(selection=item, committed=item.selection_id in committed)
            for item in sorted(
                entries.values(), key=lambda value: (value.revision, value.selected_at_utc)
            )
        )

    def archive_profile(self, profile_id: str) -> LoadedProfile:
        loaded = self.load_profile(profile_id, include_archived=False)
        if self.active_path.exists():
            active = self._read_active_pointer()
            if active.profile_id == loaded.manifest.profile_id:
                raise ActiveProfileArchiveError("the active profile cannot be archived")
        self._initialize()
        target = self.archive_directory / loaded.manifest.profile_id
        if target.exists():
            raise ProfileAlreadyExists("archive destination already exists")
        try:
            os.replace(loaded.directory, target)
        except OSError as exc:
            raise ProfileError(f"profile could not be archived: {exc}") from exc
        return self.load_profile(loaded.manifest.profile_id, include_archived=True)

    def restore_profile(self, profile_id: str) -> LoadedProfile:
        loaded = self.load_profile(profile_id, include_archived=True)
        if loaded.location is not ProfileLocation.ARCHIVED:
            raise InvalidProfile("profile is not archived")
        target = self.profiles_directory / loaded.manifest.profile_id
        if target.exists():
            raise ProfileAlreadyExists("restore destination already exists")
        try:
            os.replace(loaded.directory, target)
        except OSError as exc:
            raise ProfileError(f"profile could not be restored: {exc}") from exc
        return self.load_profile(loaded.manifest.profile_id, include_archived=False)

    def export_profile(self, profile_id: str, destination: str | Path) -> Path:
        loaded = self.load_profile(profile_id, include_archived=True)
        target = Path(destination)
        if target.exists():
            raise ProfileAlreadyExists(f"export destination already exists: {target}")
        temporary = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(loaded.directory, temporary)
            os.replace(temporary, target)
        except OSError as exc:
            raise ProfileError(f"profile export failed without overwriting: {exc}") from exc
        return target

    def compare_profiles(self, left_id: str, right_id: str) -> tuple[ProfileDifference, ...]:
        left = self.load_profile(left_id, include_archived=True)
        right = self.load_profile(right_id, include_archived=True)
        left_values = {
            "kalibrasyon": left.calibration,
            "ayarlar": left.settings,
        }
        right_values = {
            "kalibrasyon": right.calibration,
            "ayarlar": right.settings,
        }
        flat_left = _flatten(left_values)
        flat_right = _flatten(right_values)
        differences = []
        for path in sorted(set(flat_left) | set(flat_right)):
            left_value = flat_left.get(path, "<MISSING>")
            right_value = flat_right.get(path, "<MISSING>")
            if left_value != right_value:
                differences.append(ProfileDifference(path, left_value, right_value))
        return tuple(differences)


def _flatten(value: object, path: str = "") -> dict[str, object]:
    if isinstance(value, Mapping):
        result: dict[str, object] = {}
        for key in sorted(value):
            child = f"{path}.{key}" if path else str(key)
            result.update(_flatten(value[key], child))
        return result
    if isinstance(value, list):
        result = {}
        for index, item in enumerate(value):
            result.update(_flatten(item, f"{path}[{index}]"))
        return result
    if isinstance(value, float) and not math.isfinite(value):
        raise InvalidProfile(f"non-finite value at {path}")
    return {path: value}
