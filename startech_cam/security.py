"""Authentication, CSRF, access-code, and audit helpers."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import sqlite3
import string
import time
from typing import Any

from flask import current_app, session
from werkzeug.security import check_password_hash

from .db import get_db


CODE_ALPHABET = string.ascii_uppercase + string.digits


def now_epoch() -> int:
    return int(time.time())


def verify_password(candidate: str) -> bool:
    """Compare against the configured hash, or the explicitly configured raw secret."""

    configured_hash = str(current_app.config.get("CAM_PASSWORD_HASH") or "")
    if configured_hash:
        try:
            return check_password_hash(configured_hash, candidate)
        except (ValueError, TypeError):
            return False
    configured = str(current_app.config.get("CAM_PASSWORD") or "")
    return bool(configured) and hmac.compare_digest(configured, candidate)


def csrf_token() -> str:
    token = session.get("csrf_token")
    if not isinstance(token, str) or len(token) < 32:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


def csrf_matches(candidate: str | None) -> bool:
    expected = session.get("csrf_token")
    return (
        isinstance(expected, str)
        and isinstance(candidate, str)
        and hmac.compare_digest(expected, candidate)
    )


def remote_is_limited(remote_address: str) -> bool:
    cutoff = now_epoch() - int(current_app.config["CAM_LOGIN_WINDOW_SECONDS"])
    row = get_db().execute(
        """
        SELECT COUNT(*) AS failures
        FROM login_attempts
        WHERE remote_address = ? AND attempted_at >= ? AND succeeded = 0
        """,
        (remote_address, cutoff),
    ).fetchone()
    return int(row["failures"]) >= int(current_app.config["CAM_LOGIN_LIMIT"])


def access_code_remote_is_limited(remote_address: str) -> bool:
    cutoff = now_epoch() - int(current_app.config["CAM_ACCESS_CODE_WINDOW_SECONDS"])
    row = get_db().execute(
        """
        SELECT COUNT(*) AS failures
        FROM access_code_attempts
        WHERE remote_address = ? AND attempted_at >= ? AND succeeded = 0
        """,
        (remote_address, cutoff),
    ).fetchone()
    return int(row["failures"]) >= int(current_app.config["CAM_ACCESS_CODE_LIMIT"])


def record_login(remote_address: str, *, succeeded: bool) -> None:
    connection = get_db()
    connection.execute(
        "INSERT INTO login_attempts(remote_address, attempted_at, succeeded) VALUES (?, ?, ?)",
        (remote_address, now_epoch(), int(succeeded)),
    )
    if succeeded:
        connection.execute(
            "DELETE FROM login_attempts WHERE remote_address = ? AND succeeded = 0",
            (remote_address,),
        )
    connection.commit()


def record_access_code_attempt(remote_address: str, *, succeeded: bool) -> None:
    connection = get_db()
    connection.execute(
        """
        INSERT INTO access_code_attempts(remote_address, attempted_at, succeeded)
        VALUES (?, ?, ?)
        """,
        (remote_address, now_epoch(), int(succeeded)),
    )
    if succeeded:
        connection.execute(
            "DELETE FROM access_code_attempts WHERE remote_address = ? AND succeeded = 0",
            (remote_address,),
        )
    connection.commit()


def _code_digest(code: str) -> str:
    secret = str(current_app.config["SECRET_KEY"]).encode("utf-8")
    return hmac.new(secret, code.encode("ascii"), hashlib.sha256).hexdigest()


def _normalize_code(code: str) -> str | None:
    normalized = "".join(code.upper().split())
    if len(normalized) != 8 or any(
        character not in CODE_ALPHABET for character in normalized
    ):
        return None
    return normalized


def issue_access_code(device_id: str) -> str:
    """Create a single-use code.  The plaintext is returned exactly once."""

    normalized_device = device_id.strip()
    if not normalized_device or len(normalized_device) > 80:
        raise ValueError("device id must contain between 1 and 80 characters")
    issued_at = now_epoch()
    expires_at = issued_at + int(current_app.config["CAM_CODE_LIFETIME_SECONDS"])
    connection = get_db()
    for _attempt in range(10):
        code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(8))
        try:
            connection.execute(
                """
                INSERT INTO access_codes(code_digest, device_id, issued_at, expires_at)
                VALUES (?, ?, ?, ?)
                """,
                (_code_digest(code), normalized_device, issued_at, expires_at),
            )
            connection.commit()
            audit("system", "ACCESS_CODE_ISSUED", normalized_device, {"expires_at": expires_at})
            return code
        except sqlite3.IntegrityError:
            connection.rollback()
    raise RuntimeError("could not generate a unique access code")


def consume_access_code(code: str, actor: str) -> str | None:
    normalized = _normalize_code(code)
    if normalized is None:
        return None
    connection = get_db()
    current = now_epoch()
    row = connection.execute(
        """
        SELECT device_id FROM access_codes
        WHERE code_digest = ?
          AND consumed_at IS NULL
          AND revoked_at IS NULL
          AND expires_at > ?
        """,
        (_code_digest(normalized), current),
    ).fetchone()
    if row is None:
        return None
    changed = connection.execute(
        """
        UPDATE access_codes SET consumed_at = ?, consumed_by = ?
        WHERE code_digest = ? AND consumed_at IS NULL AND revoked_at IS NULL
        """,
        (current, actor, _code_digest(normalized)),
    ).rowcount
    connection.commit()
    if changed != 1:
        return None
    device_id = str(row["device_id"])
    audit(actor, "ACCESS_CODE_CONSUMED", device_id, {})
    return device_id


def revoke_access_code(code: str, actor: str) -> bool:
    """Revoke an unconsumed code without storing or logging its plaintext."""

    normalized = _normalize_code(code)
    if normalized is None:
        return False
    connection = get_db()
    current = now_epoch()
    row = connection.execute(
        """
        SELECT device_id FROM access_codes
        WHERE code_digest = ? AND consumed_at IS NULL AND revoked_at IS NULL
        """,
        (_code_digest(normalized),),
    ).fetchone()
    if row is None:
        return False
    changed = connection.execute(
        """
        UPDATE access_codes SET revoked_at = ?, revoked_by = ?
        WHERE code_digest = ? AND consumed_at IS NULL AND revoked_at IS NULL
        """,
        (current, actor[:120], _code_digest(normalized)),
    ).rowcount
    connection.commit()
    if changed != 1:
        return False
    audit(actor, "ACCESS_CODE_REVOKED", str(row["device_id"]), {})
    return True


def prune_security_records(*, retain_seconds: int = 7 * 24 * 60 * 60) -> dict[str, int]:
    """Remove expired transient security rows while keeping audit evidence."""

    if retain_seconds < 0:
        raise ValueError("retain_seconds cannot be negative")
    cutoff = now_epoch() - retain_seconds
    connection = get_db()
    deleted = {
        "login_attempts": connection.execute(
            "DELETE FROM login_attempts WHERE attempted_at < ?", (cutoff,)
        ).rowcount,
        "access_code_attempts": connection.execute(
            "DELETE FROM access_code_attempts WHERE attempted_at < ?", (cutoff,)
        ).rowcount,
        "access_codes": connection.execute(
            """
            DELETE FROM access_codes
            WHERE expires_at < ?
            """,
            (cutoff,),
        ).rowcount,
        "device_nonces": connection.execute(
            "DELETE FROM device_nonces WHERE expires_at < ?", (cutoff,)
        ).rowcount,
        "device_api_attempts": connection.execute(
            "DELETE FROM device_api_attempts WHERE attempted_at < ?", (cutoff,)
        ).rowcount,
    }
    connection.commit()
    return deleted


def audit(actor: str, event_type: str, subject: str, detail: dict[str, Any]) -> None:
    connection = get_db()
    connection.execute(
        """
        INSERT INTO audit_events(happened_at, actor, event_type, subject, detail_json)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            now_epoch(),
            actor[:120],
            event_type[:80],
            subject[:160],
            json.dumps(detail, ensure_ascii=False, sort_keys=True),
        ),
    )
    connection.commit()


__all__ = [
    "access_code_remote_is_limited",
    "audit",
    "consume_access_code",
    "csrf_matches",
    "csrf_token",
    "issue_access_code",
    "now_epoch",
    "prune_security_records",
    "record_access_code_attempt",
    "record_login",
    "remote_is_limited",
    "revoke_access_code",
    "verify_password",
]
