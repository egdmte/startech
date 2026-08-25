"""Temporary, closed-operation links between CAM and one YAREN device.

The protocol cannot carry shell, profile activation, continuous steering, or
arbitrary execution requests.  Its only physical operation is one short, bounded
SAC workshop command validated again by YAREN, ARDA, TAWNT and OSMAN.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import json
import secrets
import sqlite3
from typing import Any, Mapping
import uuid

from flask import current_app

from startech.configuration.combined import combined_config_errors

from .db import get_db
from .security import audit, now_epoch


ALLOWED_OPERATIONS = frozenset(
    {
        "REQUEST_ACTIVE_CONFIGURATION",
        "REQUEST_CAPABILITY_REPORT",
        "INSTALL_INACTIVE_CONFIGURATION",
        "RUN_BOUNDED_WORKSHOP_COMMAND",
        "CAPTURE_CALIBRATION_FRAME",
    }
)
CAPABILITY_STATUSES = frozenset(
    {
        "LIVE",
        "RESPONDED",
        "UNAVAILABLE",
        "FAILED",
        "UNVERIFIED",
    }
)
MAX_JSON_BYTES = 1_000_000


class DeviceLinkError(ValueError):
    """Raised when a device link request cannot be accepted safely."""


@dataclass(frozen=True)
class DeviceLinkCredentials:
    link_id: str
    link_token: str
    device_id: str
    expires_at: int


def _canonical_json(value: Mapping[str, Any]) -> str:
    # Preserve nested object order.  The legacy v1 calibration stamp is
    # order-sensitive, so sorting a valid document would invalidate it.
    try:
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as exc:
        raise DeviceLinkError("payload must contain only finite JSON values") from exc
    if len(encoded.encode("utf-8")) > MAX_JSON_BYTES:
        raise DeviceLinkError("payload exceeds the one-megabyte limit")
    return encoded


def _token_digest(token: str) -> str:
    if not isinstance(token, str) or len(token) < 32 or not token.isascii():
        raise DeviceLinkError("device link token is malformed")
    secret = str(current_app.config["SECRET_KEY"]).encode("utf-8")
    return hmac.new(secret, token.encode("ascii"), hashlib.sha256).hexdigest()


def create_device_link(device_id: str) -> DeviceLinkCredentials:
    """Create one pending link and return its plaintext token exactly once."""

    connection = get_db()
    device = connection.execute(
        """
        SELECT device_id FROM registered_devices
        WHERE device_id = ? AND disabled_at IS NULL
        """,
        (device_id,),
    ).fetchone()
    if device is None:
        raise DeviceLinkError("device is not registered or is disabled")
    issued_at = now_epoch()
    expires_at = issued_at + int(current_app.config["CAM_CAR_ACCESS_LIFETIME_SECONDS"])
    for _attempt in range(10):
        link_id = uuid.uuid4().hex
        token = secrets.token_urlsafe(32)
        try:
            connection.execute(
                """
                INSERT INTO device_links(
                    link_id, token_digest, device_id, issued_at, expires_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (link_id, _token_digest(token), device_id, issued_at, expires_at),
            )
            connection.commit()
            audit("system", "DEVICE_LINK_ISSUED", device_id, {"link_id": link_id})
            return DeviceLinkCredentials(link_id, token, device_id, expires_at)
        except sqlite3.IntegrityError:
            connection.rollback()
    raise RuntimeError("could not generate a unique device link")


def activate_device_link(link_id: str, *, device_id: str, actor: str) -> bool:
    current = now_epoch()
    connection = get_db()
    changed = connection.execute(
        """
        UPDATE device_links
        SET activated_at = ?, activated_by = ?
        WHERE link_id = ? AND device_id = ? AND activated_at IS NULL
          AND revoked_at IS NULL AND expires_at > ?
        """,
        (current, actor[:120], link_id, device_id, current),
    ).rowcount
    connection.commit()
    if changed:
        audit(actor, "DEVICE_LINK_ACTIVATED", device_id, {"link_id": link_id})
    return changed == 1


def revoke_device_link(link_id: str, *, actor: str) -> bool:
    current = now_epoch()
    connection = get_db()
    row = connection.execute(
        "SELECT device_id FROM device_links WHERE link_id = ?", (link_id,)
    ).fetchone()
    if row is None:
        return False
    changed = connection.execute(
        """
        UPDATE device_links SET revoked_at = ?, revoked_by = ?
        WHERE link_id = ? AND revoked_at IS NULL
        """,
        (current, actor[:120], link_id),
    ).rowcount
    connection.execute(
        """
        UPDATE device_jobs SET status = 'EXPIRED'
        WHERE link_id = ? AND status IN ('PENDING', 'CLAIMED')
        """,
        (link_id,),
    )
    connection.commit()
    if changed:
        audit(actor, "DEVICE_LINK_REVOKED", str(row["device_id"]), {"link_id": link_id})
    return changed == 1


def authenticate_device_link(
    link_id: str,
    device_id: str,
    token: str,
    *,
    require_active: bool,
) -> str:
    """Authenticate one bearer token and return PENDING or ACTIVE."""

    current = now_epoch()
    row = get_db().execute(
        """
        SELECT token_digest, activated_at FROM device_links
        WHERE link_id = ? AND device_id = ? AND revoked_at IS NULL AND expires_at > ?
        """,
        (link_id, device_id, current),
    ).fetchone()
    supplied = _token_digest(token)
    if row is None or not hmac.compare_digest(str(row["token_digest"]), supplied):
        raise DeviceLinkError("device link was not accepted")
    state = "ACTIVE" if row["activated_at"] is not None else "PENDING"
    if require_active and state != "ACTIVE":
        raise DeviceLinkError("device link has not been activated by its access code")
    connection = get_db()
    connection.execute(
        "UPDATE device_links SET last_seen_at = ? WHERE link_id = ?",
        (current, link_id),
    )
    connection.commit()
    return state


def browser_link_is_active(link_id: str, device_id: str) -> bool:
    row = get_db().execute(
        """
        SELECT 1 FROM device_links
        WHERE link_id = ? AND device_id = ? AND activated_at IS NOT NULL
          AND revoked_at IS NULL AND expires_at > ?
        """,
        (link_id, device_id, now_epoch()),
    ).fetchone()
    return row is not None


def store_device_snapshot(
    link_id: str,
    device_id: str,
    *,
    captured_at: int,
    document: Mapping[str, Any],
) -> None:
    if isinstance(captured_at, bool) or not isinstance(captured_at, int) or captured_at <= 0:
        raise DeviceLinkError("snapshot captured_at must be a positive integer")
    errors = combined_config_errors(document)
    if errors:
        raise DeviceLinkError("invalid active configuration: " + "; ".join(errors))
    payload_json = _canonical_json(document)
    connection = get_db()
    connection.execute(
        """
        INSERT INTO device_snapshots(
            link_id, device_id, captured_at, received_at, payload_json
        ) VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(link_id) DO UPDATE SET
            device_id = excluded.device_id,
            captured_at = excluded.captured_at,
            received_at = excluded.received_at,
            payload_json = excluded.payload_json
        """,
        (link_id, device_id, captured_at, now_epoch(), payload_json),
    )
    connection.commit()
    audit(device_id, "DEVICE_SNAPSHOT_RECEIVED", link_id, {"captured_at": captured_at})


def _validate_capability_report(report: Mapping[str, Any], device_id: str) -> str:
    if not isinstance(report, Mapping) or set(report) != {
        "version",
        "device_id",
        "checked_at",
        "results",
    }:
        raise DeviceLinkError("capability report has unexpected fields")
    if report["version"] != 1 or report["device_id"] != device_id:
        raise DeviceLinkError("capability report identity or version is invalid")
    checked_at = report["checked_at"]
    if isinstance(checked_at, bool) or not isinstance(checked_at, int) or checked_at <= 0:
        raise DeviceLinkError("capability report checked_at is invalid")
    results = report["results"]
    if not isinstance(results, list) or not 1 <= len(results) <= 20:
        raise DeviceLinkError("capability report needs between 1 and 20 results")
    expected = {"module", "name", "status", "scope", "detail", "duration_ms", "facts"}
    for result in results:
        if not isinstance(result, Mapping) or set(result) != expected:
            raise DeviceLinkError("capability result has unexpected fields")
        if result["status"] not in CAPABILITY_STATUSES:
            raise DeviceLinkError("capability result has an unknown status")
        for field in ("module", "name", "scope", "detail"):
            value = result[field]
            if not isinstance(value, str) or not value.strip() or len(value) > 500:
                raise DeviceLinkError(f"capability result {field} is invalid")
        duration = result["duration_ms"]
        if isinstance(duration, bool) or not isinstance(duration, int) or duration < 0:
            raise DeviceLinkError("capability result duration_ms is invalid")
        if not isinstance(result["facts"], Mapping):
            raise DeviceLinkError("capability result facts must be an object")
    return _canonical_json(report)


def store_capability_report(
    link_id: str,
    device_id: str,
    report: Mapping[str, Any],
) -> None:
    payload_json = _validate_capability_report(report, device_id)
    checked_at = int(report["checked_at"])
    connection = get_db()
    connection.execute(
        """
        INSERT INTO device_capability_reports(
            link_id, device_id, checked_at, received_at, payload_json
        ) VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(link_id) DO UPDATE SET
            device_id = excluded.device_id,
            checked_at = excluded.checked_at,
            received_at = excluded.received_at,
            payload_json = excluded.payload_json
        """,
        (link_id, device_id, checked_at, now_epoch(), payload_json),
    )
    connection.commit()
    audit(device_id, "DEVICE_CAPABILITIES_RECEIVED", link_id, {"checked_at": checked_at})


def get_device_snapshot(link_id: str, device_id: str) -> dict[str, Any] | None:
    if not browser_link_is_active(link_id, device_id):
        return None
    row = get_db().execute(
        """
        SELECT payload_json FROM device_snapshots
        WHERE link_id = ? AND device_id = ?
        """,
        (link_id, device_id),
    ).fetchone()
    return None if row is None else json.loads(str(row["payload_json"]))


def get_capability_report(link_id: str, device_id: str) -> dict[str, Any] | None:
    if not browser_link_is_active(link_id, device_id):
        return None
    row = get_db().execute(
        """
        SELECT payload_json, received_at FROM device_capability_reports
        WHERE link_id = ? AND device_id = ?
        """,
        (link_id, device_id),
    ).fetchone()
    if row is None:
        return None
    report = json.loads(str(row["payload_json"]))
    report["received_at"] = int(row["received_at"])
    return report


def queue_device_job(
    link_id: str,
    device_id: str,
    operation: str,
    payload: Mapping[str, Any] | None = None,
    *,
    actor: str = "browser",
    lifetime_seconds: int = 15 * 60,
) -> str:
    if operation not in ALLOWED_OPERATIONS:
        raise DeviceLinkError("device operation is not allowed")
    if not browser_link_is_active(link_id, device_id):
        raise DeviceLinkError("device link is not active")
    if not isinstance(actor, str) or not actor.strip() or len(actor) > 120:
        raise DeviceLinkError("device job actor is invalid")
    if (
        isinstance(lifetime_seconds, bool)
        or not isinstance(lifetime_seconds, int)
        or not 1 <= lifetime_seconds <= 15 * 60
    ):
        raise DeviceLinkError("device job lifetime must be between 1 and 900 seconds")
    selected_payload = dict(payload or {})
    payload_json = _canonical_json(selected_payload)
    connection = get_db()
    existing = connection.execute(
        """
        SELECT job_id FROM device_jobs
        WHERE link_id = ? AND operation = ? AND payload_json = ?
          AND status IN ('PENDING', 'CLAIMED', 'ACCEPTED')
        ORDER BY created_at DESC LIMIT 1
        """,
        (link_id, operation, payload_json),
    ).fetchone()
    if existing is not None:
        return str(existing["job_id"])
    job_id = uuid.uuid4().hex
    current = now_epoch()
    link = connection.execute(
        "SELECT expires_at FROM device_links WHERE link_id = ?", (link_id,)
    ).fetchone()
    if link is None:
        raise DeviceLinkError("device link is unavailable")
    connection.execute(
        """
        INSERT INTO device_jobs(
            job_id, link_id, device_id, operation, payload_json,
            created_at, expires_at, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDING')
        """,
        (
            job_id,
            link_id,
            device_id,
            operation,
            payload_json,
            current,
            min(int(link["expires_at"]), current + lifetime_seconds),
        ),
    )
    connection.commit()
    audit(actor.strip(), "DEVICE_JOB_QUEUED", device_id, {"job_id": job_id, "operation": operation})
    return job_id


def claim_next_device_job(link_id: str, device_id: str) -> dict[str, Any] | None:
    current = now_epoch()
    connection = get_db()
    connection.execute(
        """
        UPDATE device_jobs SET status = 'EXPIRED'
        WHERE link_id = ? AND status IN ('PENDING', 'CLAIMED') AND expires_at <= ?
        """,
        (link_id, current),
    )
    row = connection.execute(
        """
        SELECT job_id, operation, payload_json FROM device_jobs
        WHERE link_id = ? AND device_id = ? AND status = 'PENDING' AND expires_at > ?
        ORDER BY created_at, job_id LIMIT 1
        """,
        (link_id, device_id, current),
    ).fetchone()
    if row is None:
        connection.commit()
        return None
    changed = connection.execute(
        """
        UPDATE device_jobs SET status = 'CLAIMED', claimed_at = ?
        WHERE job_id = ? AND status = 'PENDING'
        """,
        (current, row["job_id"]),
    ).rowcount
    connection.commit()
    if changed != 1:
        return None
    return {
        "job_id": str(row["job_id"]),
        "operation": str(row["operation"]),
        "payload": json.loads(str(row["payload_json"])),
    }


def complete_device_job(
    link_id: str,
    device_id: str,
    job_id: str,
    *,
    accepted: bool,
    receipt: Mapping[str, Any],
) -> bool:
    receipt_json = _canonical_json(receipt)
    connection = get_db()
    changed = connection.execute(
        """
        UPDATE device_jobs
        SET status = ?, completed_at = ?, receipt_json = ?
        WHERE job_id = ? AND link_id = ? AND device_id = ? AND status = 'CLAIMED'
        """,
        (
            "ACCEPTED" if accepted else "REJECTED",
            now_epoch(),
            receipt_json,
            job_id,
            link_id,
            device_id,
        ),
    ).rowcount
    connection.commit()
    if changed:
        audit(device_id, "DEVICE_JOB_COMPLETED", job_id, {"accepted": accepted})
    return changed == 1


def get_device_job(job_id: str, link_id: str, device_id: str) -> dict[str, Any] | None:
    row = get_db().execute(
        """
        SELECT operation, payload_json, status, receipt_json, created_at, completed_at
        FROM device_jobs WHERE job_id = ? AND link_id = ? AND device_id = ?
        """,
        (job_id, link_id, device_id),
    ).fetchone()
    if row is None:
        return None
    return {
        "job_id": job_id,
        "operation": str(row["operation"]),
        "payload": json.loads(str(row["payload_json"])),
        "status": str(row["status"]),
        "receipt": None if row["receipt_json"] is None else json.loads(str(row["receipt_json"])),
        "created_at": int(row["created_at"]),
        "completed_at": row["completed_at"],
    }


__all__ = [
    "ALLOWED_OPERATIONS",
    "CAPABILITY_STATUSES",
    "DeviceLinkCredentials",
    "DeviceLinkError",
    "activate_device_link",
    "authenticate_device_link",
    "browser_link_is_active",
    "claim_next_device_job",
    "complete_device_job",
    "create_device_link",
    "get_capability_report",
    "get_device_job",
    "get_device_snapshot",
    "queue_device_job",
    "revoke_device_link",
    "store_capability_report",
    "store_device_snapshot",
]
