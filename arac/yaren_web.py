"""YAREN device identity and signed CAM web-access-code client.

This module authenticates one device to CAM.  It does not import the driver,
camera, steering, or motor layers and cannot arm or move the vehicle.
"""

from __future__ import annotations

import base64
import binascii
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


ALGORITHM = "Ed25519"
PRIVATE_FORMAT = "startech-yaren-device-v1"
PUBLIC_FORMAT = "startech-yaren-public-v1"
SIGNING_DOMAIN = "STARTECH-CAM-DEVICE-V1"
CHALLENGE_PATH = "/api/device/v1/challenge"
ACCESS_CODE_PATH = "/api/device/v1/access-code"
DEFAULT_SERVER = "https://dymtal.avartech.net"


class WebAccessError(ValueError):
    """Raised when identity or remote CAM authentication fails closed."""


@dataclass(frozen=True)
class DeviceIdentity:
    device_id: str
    private_key: Ed25519PrivateKey
    created_at_utc: str

    @property
    def public_key_b64(self) -> str:
        raw = self.private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        return _b64url_encode(raw)


@dataclass(frozen=True)
class WebAccessCode:
    access_code: str
    device_id: str
    expires_at: int
    link_id: str
    link_token: str


PostJson = Callable[[str, bytes, Mapping[str, str], float], dict[str, Any]]


def _b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str, *, expected_length: int, label: str) -> bytes:
    if not isinstance(value, str) or not value or any(character.isspace() for character in value):
        raise WebAccessError(f"{label} is not valid base64url")
    try:
        decoded = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except (ValueError, binascii.Error) as exc:
        raise WebAccessError(f"{label} is not valid base64url") from exc
    if len(decoded) != expected_length:
        raise WebAccessError(f"{label} must decode to {expected_length} bytes")
    return decoded


def normalize_device_id(device_id: str) -> str:
    normalized = device_id.strip() if isinstance(device_id, str) else ""
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._:-")
    if not (1 <= len(normalized) <= 80) or normalized[0] not in set(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    ) or any(character not in allowed for character in normalized):
        raise WebAccessError(
            "device id must use 1-80 letters, numbers, dots, colons, underscores, or hyphens"
        )
    return normalized


def default_identity_path() -> Path:
    configured = os.environ.get("STARTECH_YAREN_IDENTITY", "").strip()
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".startech" / "yaren-device.json"


def default_server_url() -> str:
    return os.environ.get("STARTECH_CAM_URL", DEFAULT_SERVER).strip() or DEFAULT_SERVER


def _private_document(identity: DeviceIdentity) -> dict[str, str]:
    private_bytes = identity.private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return {
        "format": PRIVATE_FORMAT,
        "algorithm": ALGORITHM,
        "device_id": identity.device_id,
        "private_key": _b64url_encode(private_bytes),
        "created_at_utc": identity.created_at_utc,
    }


def public_document(identity: DeviceIdentity) -> dict[str, str]:
    return {
        "format": PUBLIC_FORMAT,
        "algorithm": ALGORITHM,
        "device_id": identity.device_id,
        "public_key": identity.public_key_b64,
    }


def _write_json(path: Path, payload: Mapping[str, Any], *, private: bool, replace: bool) -> None:
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    if private:
        try:
            path.parent.chmod(0o700)
        except OSError:
            pass
    flags = os.O_WRONLY | os.O_CREAT | (os.O_TRUNC if replace else os.O_EXCL)
    mode = 0o600 if private else 0o644
    descriptor = os.open(path, flags, mode)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(payload, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        try:
            path.unlink()
        except OSError:
            pass
        raise
    try:
        path.chmod(mode)
    except OSError:
        pass


def create_device_identity(
    device_id: str,
    identity_path: Path | None = None,
    public_path: Path | None = None,
    *,
    replace: bool = False,
) -> tuple[DeviceIdentity, Path]:
    """Generate a private identity and a separately shareable public artifact."""

    normalized = normalize_device_id(device_id)
    private_path = (identity_path or default_identity_path()).expanduser().resolve()
    exported_path = (
        public_path
        or private_path.with_name(f"{private_path.stem}.pub.json")
    ).expanduser().resolve()
    if private_path == exported_path:
        raise WebAccessError("private identity and public export paths must differ")
    created = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    identity = DeviceIdentity(normalized, Ed25519PrivateKey.generate(), created)
    try:
        _write_json(private_path, _private_document(identity), private=True, replace=replace)
        _write_json(exported_path, public_document(identity), private=False, replace=replace)
    except FileExistsError as exc:
        raise WebAccessError(f"identity output already exists: {exc.filename}") from exc
    except OSError as exc:
        raise WebAccessError(f"could not write device identity: {exc}") from exc
    return identity, exported_path


def load_device_identity(path: Path | None = None) -> DeviceIdentity:
    identity_path = (path or default_identity_path()).expanduser().resolve()
    try:
        payload = json.loads(identity_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise WebAccessError(f"could not read private identity {identity_path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise WebAccessError("private identity is not valid JSON") from exc
    required = {"format", "algorithm", "device_id", "private_key", "created_at_utc"}
    if not isinstance(payload, dict) or set(payload) != required:
        raise WebAccessError("private identity has unexpected fields")
    if payload["format"] != PRIVATE_FORMAT or payload["algorithm"] != ALGORITHM:
        raise WebAccessError("private identity format or algorithm is unsupported")
    device_id = normalize_device_id(payload["device_id"])
    raw_private = _b64url_decode(
        payload["private_key"], expected_length=32, label="private key"
    )
    created = payload["created_at_utc"]
    if not isinstance(created, str) or not created:
        raise WebAccessError("private identity creation time is invalid")
    try:
        private_key = Ed25519PrivateKey.from_private_bytes(raw_private)
    except ValueError as exc:
        raise WebAccessError("private identity key is invalid") from exc
    return DeviceIdentity(device_id, private_key, created)


def canonical_request(
    method: str,
    path: str,
    device_id: str,
    challenge: str,
    body: bytes,
) -> bytes:
    digest = hashlib.sha256(body).hexdigest()
    return (
        f"{SIGNING_DOMAIN}\n{method.upper()}\n{path}\n"
        f"{device_id}\n{challenge}\n{digest}\n"
    ).encode("utf-8")


def _server_root(server_url: str) -> str:
    parsed = urlsplit(server_url.strip())
    if (
        parsed.scheme != "https"
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        raise WebAccessError("CAM server must be an HTTPS origin without a path or credentials")
    return f"https://{parsed.netloc}"


def _post_json(
    url: str,
    body: bytes,
    headers: Mapping[str, str],
    timeout: float,
) -> dict[str, Any]:
    request = Request(
        url,
        data=body,
        method="POST",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "STARTECH-YAREN/1",
            **dict(headers),
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read(64_001)
    except HTTPError as exc:
        raw = exc.read(64_001)
        try:
            payload = json.loads(raw)
            message = payload["error"]["message"]
        except (json.JSONDecodeError, KeyError, TypeError):
            message = f"CAM returned HTTP {exc.code}"
        raise WebAccessError(str(message)) from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise WebAccessError(f"could not reach CAM: {exc}") from exc
    if len(raw) > 64_000:
        raise WebAccessError("CAM response was unexpectedly large")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise WebAccessError("CAM did not return valid JSON") from exc
    if not isinstance(payload, dict):
        raise WebAccessError("CAM response must be a JSON object")
    return payload


def _json_bytes(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def request_web_code(
    server_url: str | None = None,
    identity_path: Path | None = None,
    *,
    timeout: float = 10.0,
    post_json: PostJson | None = None,
) -> WebAccessCode:
    """Request one expiring CAM code using a registered private device key."""

    if timeout <= 0 or timeout > 60:
        raise WebAccessError("timeout must be greater than zero and at most 60 seconds")
    server = _server_root(server_url or default_server_url())
    identity = load_device_identity(identity_path)
    transport = post_json or _post_json
    challenge_body = _json_bytes({"device_id": identity.device_id})
    challenge_response = transport(
        server + CHALLENGE_PATH, challenge_body, {}, timeout
    )
    challenge = challenge_response.get("challenge")
    if not isinstance(challenge, str) or not challenge:
        raise WebAccessError("CAM challenge response is incomplete")
    access_body = _json_bytes(
        {"challenge": challenge, "device_id": identity.device_id}
    )
    signature = identity.private_key.sign(
        canonical_request(
            "POST", ACCESS_CODE_PATH, identity.device_id, challenge, access_body
        )
    )
    response = transport(
        server + ACCESS_CODE_PATH,
        access_body,
        {"X-STARTECH-Signature": _b64url_encode(signature)},
        timeout,
    )
    code = response.get("access_code")
    returned_device = response.get("device_id")
    expires_at = response.get("expires_at")
    link_id = response.get("link_id")
    link_token = response.get("link_token")
    if (
        not isinstance(code, str)
        or len(code) != 8
        or not code.isascii()
        or not code.isalnum()
        or returned_device != identity.device_id
        or not isinstance(expires_at, int)
        or not isinstance(link_id, str)
        or len(link_id) != 32
        or any(character not in "0123456789abcdef" for character in link_id)
        or not isinstance(link_token, str)
        or len(link_token) < 32
        or not link_token.isascii()
    ):
        raise WebAccessError("CAM access-code response is incomplete")
    return WebAccessCode(
        code.upper(), identity.device_id, expires_at, link_id, link_token
    )


__all__ = [
    "ACCESS_CODE_PATH",
    "CHALLENGE_PATH",
    "DeviceIdentity",
    "WebAccessCode",
    "WebAccessError",
    "canonical_request",
    "create_device_identity",
    "default_identity_path",
    "default_server_url",
    "load_device_identity",
    "public_document",
    "request_web_code",
]
