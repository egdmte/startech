"""Registered YAREN identities and replay-resistant device request verification."""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
import secrets
import sqlite3
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from flask import current_app

from .db import get_db
from .security import audit, now_epoch


ALGORITHM = "Ed25519"
SIGNING_DOMAIN = "STARTECH-CAM-DEVICE-V1"
ACCESS_CODE_PATH = "/api/device/v1/access-code"
DEVICE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,79}$")


class DeviceAuthenticationError(ValueError):
    """Raised when a device request cannot be authenticated safely."""


def _b64url_decode(value: str, *, expected_length: int, label: str) -> bytes:
    if not isinstance(value, str) or not value or any(character.isspace() for character in value):
        raise DeviceAuthenticationError(f"{label} is not valid base64url")
    try:
        decoded = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except (ValueError, binascii.Error) as exc:
        raise DeviceAuthenticationError(f"{label} is not valid base64url") from exc
    if len(decoded) != expected_length:
        raise DeviceAuthenticationError(
            f"{label} must decode to {expected_length} bytes"
        )
    return decoded


def _b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def normalize_device_id(device_id: str) -> str:
    normalized = device_id.strip() if isinstance(device_id, str) else ""
    if not DEVICE_ID_PATTERN.fullmatch(normalized):
        raise DeviceAuthenticationError(
            "device id must use 1-80 letters, numbers, dots, colons, underscores, or hyphens"
        )
    return normalized


def canonical_request(
    method: str,
    path: str,
    device_id: str,
    nonce: str,
    body: bytes,
) -> bytes:
    """Return the compatibility-domain bytes signed by YAREN and verified by KERİM."""

    digest = hashlib.sha256(body).hexdigest()
    return (
        f"{SIGNING_DOMAIN}\n{method.upper()}\n{path}\n"
        f"{device_id}\n{nonce}\n{digest}\n"
    ).encode("utf-8")


def parse_public_identity(document: str) -> tuple[str, str]:
    """Read the public JSON artifact produced by ``startech-yaren web-key``."""

    try:
        payload = json.loads(document)
    except json.JSONDecodeError as exc:
        raise DeviceAuthenticationError("public identity is not valid JSON") from exc
    if not isinstance(payload, dict) or set(payload) != {
        "format",
        "algorithm",
        "device_id",
        "public_key",
    }:
        raise DeviceAuthenticationError("public identity has unexpected fields")
    if payload["format"] != "startech-yaren-public-v1" or payload["algorithm"] != ALGORITHM:
        raise DeviceAuthenticationError("public identity format or algorithm is unsupported")
    device_id = normalize_device_id(payload["device_id"])
    public_key = str(payload["public_key"])
    _b64url_decode(public_key, expected_length=32, label="public key")
    return device_id, public_key


def register_device(
    device_id: str,
    public_key_b64: str,
    *,
    actor: str,
    replace: bool = False,
) -> None:
    normalized = normalize_device_id(device_id)
    public_key = _b64url_encode(
        _b64url_decode(public_key_b64, expected_length=32, label="public key")
    )
    connection = get_db()
    existing = connection.execute(
        "SELECT device_id FROM registered_devices WHERE device_id = ?", (normalized,)
    ).fetchone()
    current = now_epoch()
    if existing is not None and not replace:
        raise DeviceAuthenticationError(f"device {normalized!r} is already registered")
    if existing is None:
        connection.execute(
            """
            INSERT INTO registered_devices(
                device_id, algorithm, public_key_b64, created_at, created_by
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (normalized, ALGORITHM, public_key, current, actor[:120]),
        )
        event = "DEVICE_REGISTERED"
    else:
        connection.execute(
            """
            UPDATE registered_devices
            SET public_key_b64 = ?, rotated_at = ?, rotated_by = ?,
                disabled_at = NULL, disabled_by = NULL
            WHERE device_id = ?
            """,
            (public_key, current, actor[:120], normalized),
        )
        connection.execute("DELETE FROM device_nonces WHERE device_id = ?", (normalized,))
        event = "DEVICE_KEY_ROTATED"
    connection.commit()
    audit(actor, event, normalized, {"algorithm": ALGORITHM})


def disable_device(device_id: str, *, actor: str) -> bool:
    normalized = normalize_device_id(device_id)
    connection = get_db()
    current = now_epoch()
    changed = connection.execute(
        """
        UPDATE registered_devices
        SET disabled_at = ?, disabled_by = ?
        WHERE device_id = ? AND disabled_at IS NULL
        """,
        (current, actor[:120], normalized),
    ).rowcount
    if changed:
        connection.execute("DELETE FROM device_nonces WHERE device_id = ?", (normalized,))
    connection.commit()
    if changed:
        audit(actor, "DEVICE_DISABLED", normalized, {})
    return changed == 1


def list_devices() -> list[dict[str, Any]]:
    rows = get_db().execute(
        """
        SELECT device_id, algorithm, created_at, created_by, rotated_at,
               rotated_by, disabled_at, disabled_by
        FROM registered_devices ORDER BY device_id
        """
    ).fetchall()
    return [dict(row) for row in rows]


def device_remote_is_limited(remote_address: str) -> bool:
    cutoff = now_epoch() - int(current_app.config["CAM_DEVICE_REQUEST_WINDOW_SECONDS"])
    row = get_db().execute(
        """
        SELECT COUNT(*) AS attempts FROM device_api_attempts
        WHERE remote_address = ? AND attempted_at >= ?
        """,
        (remote_address, cutoff),
    ).fetchone()
    return int(row["attempts"]) >= int(current_app.config["CAM_DEVICE_REQUEST_LIMIT"])


def record_device_attempt(remote_address: str, action: str, *, succeeded: bool) -> None:
    connection = get_db()
    connection.execute(
        """
        INSERT INTO device_api_attempts(remote_address, action, attempted_at, succeeded)
        VALUES (?, ?, ?, ?)
        """,
        (remote_address[:120], action[:40], now_epoch(), int(succeeded)),
    )
    connection.commit()


def issue_device_nonce(device_id: str) -> tuple[str, int]:
    normalized = normalize_device_id(device_id)
    connection = get_db()
    row = connection.execute(
        """
        SELECT device_id FROM registered_devices
        WHERE device_id = ? AND disabled_at IS NULL
        """,
        (normalized,),
    ).fetchone()
    if row is None:
        raise DeviceAuthenticationError("device is not registered or is disabled")
    current = now_epoch()
    expires_at = current + int(current_app.config["CAM_DEVICE_NONCE_LIFETIME_SECONDS"])
    connection.execute(
        "DELETE FROM device_nonces WHERE expires_at <= ? OR consumed_at IS NOT NULL",
        (current,),
    )
    for _attempt in range(10):
        nonce = secrets.token_urlsafe(32)
        digest = hashlib.sha256(nonce.encode("ascii")).hexdigest()
        try:
            connection.execute(
                """
                INSERT INTO device_nonces(nonce_digest, device_id, issued_at, expires_at)
                VALUES (?, ?, ?, ?)
                """,
                (digest, normalized, current, expires_at),
            )
            connection.commit()
            return nonce, expires_at
        except sqlite3.IntegrityError:
            connection.rollback()
    raise RuntimeError("could not generate a unique device challenge")


def verify_and_consume_request(
    device_id: str,
    nonce: str,
    signature_b64: str,
    body: bytes,
) -> str:
    """Verify one signed request and atomically consume its server nonce."""

    normalized = normalize_device_id(device_id)
    if not isinstance(nonce, str) or not (32 <= len(nonce) <= 128) or not nonce.isascii():
        raise DeviceAuthenticationError("challenge is malformed")
    signature = _b64url_decode(signature_b64, expected_length=64, label="signature")
    nonce_digest = hashlib.sha256(nonce.encode("ascii")).hexdigest()
    connection = get_db()
    row = connection.execute(
        """
        SELECT d.public_key_b64
        FROM registered_devices AS d
        JOIN device_nonces AS n ON n.device_id = d.device_id
        WHERE d.device_id = ? AND d.disabled_at IS NULL
          AND n.nonce_digest = ? AND n.consumed_at IS NULL AND n.expires_at > ?
        """,
        (normalized, nonce_digest, now_epoch()),
    ).fetchone()
    if row is None:
        raise DeviceAuthenticationError("challenge is invalid, expired, or already used")
    public_key_bytes = _b64url_decode(
        str(row["public_key_b64"]), expected_length=32, label="stored public key"
    )
    signed = canonical_request("POST", ACCESS_CODE_PATH, normalized, nonce, body)
    try:
        Ed25519PublicKey.from_public_bytes(public_key_bytes).verify(signature, signed)
    except (InvalidSignature, ValueError) as exc:
        raise DeviceAuthenticationError("device signature was not accepted") from exc
    current = now_epoch()
    changed = connection.execute(
        """
        UPDATE device_nonces SET consumed_at = ?
        WHERE nonce_digest = ? AND device_id = ? AND consumed_at IS NULL AND expires_at > ?
        """,
        (current, nonce_digest, normalized, current),
    ).rowcount
    connection.commit()
    if changed != 1:
        raise DeviceAuthenticationError("challenge was already used")
    audit(normalized, "DEVICE_REQUEST_AUTHENTICATED", ACCESS_CODE_PATH, {})
    return normalized


__all__ = [
    "ACCESS_CODE_PATH",
    "DeviceAuthenticationError",
    "canonical_request",
    "disable_device",
    "device_remote_is_limited",
    "issue_device_nonce",
    "list_devices",
    "normalize_device_id",
    "parse_public_identity",
    "record_device_attempt",
    "register_device",
    "verify_and_consume_request",
]
