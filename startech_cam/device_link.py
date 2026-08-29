"""Temporary, closed-operation links between KERİM and one compatible device.

The protocol cannot carry shell, profile activation, continuous steering, or
arbitrary execution requests. The former vehicle client was removed during the LEGACY
reset; these server-side protocol types remain for a future small adapter.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import hmac
import json
import math
import secrets
import sqlite3
from typing import Any, Mapping
import uuid

from flask import current_app

from arac.startech.configuration.combined import combined_config_errors

from .run_events import RUN_CANCELLED, RUN_STATES, RunEvent

from .db import get_db
from .security import audit, now_epoch


ALLOWED_OPERATIONS = frozenset(
    {
        "REQUEST_ACTIVE_CONFIGURATION",
        "REQUEST_CAPABILITY_REPORT",
        "INSTALL_INACTIVE_CONFIGURATION",
        "RUN_BOUNDED_WORKSHOP_COMMAND",
        "CAPTURE_CALIBRATION_FRAME",
        "START_AUTONOMOUS_RUN",
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
MAX_CALIBRATION_JPEG_BYTES = 650_000
MAX_RUN_EVENT_BATCH = 100
class DeviceLinkError(ValueError):
    """Raised when a device link request cannot be accepted safely."""


@dataclass(frozen=True)
class DeviceLinkCredentials:
    link_id: str
    link_token: str
    device_id: str
    expires_at: int


def validate_calibration_frame_receipt(
    receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate one real JPEG receipt before KERİM stores or displays it."""

    expected = {
        "format",
        "width",
        "height",
        "source",
        "frame_id",
        "captured_at",
        "sha256",
        "image_b64",
    }
    if not isinstance(receipt, Mapping) or set(receipt) != expected:
        raise DeviceLinkError("calibration frame receipt has unexpected fields")
    if receipt["format"] != "jpeg":
        raise DeviceLinkError("calibration frame must use JPEG")
    for name, maximum in (("width", 7680), ("height", 4320)):
        value = receipt[name]
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or not 1 <= value <= maximum
        ):
            raise DeviceLinkError(f"calibration frame {name} is invalid")
    source = receipt["source"]
    if not isinstance(source, str) or not source.strip() or len(source) > 120:
        raise DeviceLinkError("calibration frame source is invalid")
    frame_id = receipt["frame_id"]
    if isinstance(frame_id, bool) or not isinstance(frame_id, int) or frame_id < 0:
        raise DeviceLinkError("calibration frame id is invalid")
    captured_at = receipt["captured_at"]
    if (
        isinstance(captured_at, bool)
        or not isinstance(captured_at, (int, float))
        or not math.isfinite(float(captured_at))
        or captured_at < 0
    ):
        raise DeviceLinkError("calibration frame capture time is invalid")
    digest = receipt["sha256"]
    if (
        not isinstance(digest, str)
        or len(digest) != 64
        or any(character not in "0123456789abcdef" for character in digest)
    ):
        raise DeviceLinkError("calibration frame digest is invalid")
    encoded = receipt["image_b64"]
    if not isinstance(encoded, str) or not encoded:
        raise DeviceLinkError("calibration frame image is missing")
    try:
        image = base64.b64decode(encoded, validate=True)
    except (ValueError, TypeError) as exc:
        raise DeviceLinkError("calibration frame image is not valid base64") from exc
    if not 4 <= len(image) <= MAX_CALIBRATION_JPEG_BYTES:
        raise DeviceLinkError("calibration frame JPEG size is invalid")
    if not image.startswith(b"\xff\xd8") or not image.endswith(b"\xff\xd9"):
        raise DeviceLinkError("calibration frame payload is not a complete JPEG")
    if not hmac.compare_digest(hashlib.sha256(image).hexdigest(), digest):
        raise DeviceLinkError("calibration frame digest does not match the JPEG")
    return dict(receipt)


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
    expires_at = issued_at + int(current_app.config["CAM_DEVICE_LINK_IDLE_SECONDS"])
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
    lease_expires_at = current + int(
        current_app.config["CAM_DEVICE_LINK_IDLE_SECONDS"]
    )
    connection = get_db()
    changed = connection.execute(
        """
        UPDATE device_links
        SET activated_at = ?, activated_by = ?, last_seen_at = ?, expires_at = ?
        WHERE link_id = ? AND device_id = ? AND activated_at IS NULL
          AND revoked_at IS NULL AND expires_at > ?
        """,
        (
            current,
            actor[:120],
            current,
            lease_expires_at,
            link_id,
            device_id,
            current,
        ),
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
    """Authenticate one bearer token and refresh its live-device idle lease."""

    current = now_epoch()
    connection = get_db()
    row = connection.execute(
        """
        SELECT token_digest, activated_at, expires_at, revoked_at FROM device_links
        WHERE link_id = ? AND device_id = ?
        """,
        (link_id, device_id),
    ).fetchone()
    supplied = _token_digest(token)
    if row is None or not hmac.compare_digest(str(row["token_digest"]), supplied):
        raise DeviceLinkError("device link was not accepted")
    if row["revoked_at"] is not None:
        state = "CLOSED"
    elif int(row["expires_at"]) <= current:
        state = "EXPIRED"
    else:
        state = "ACTIVE" if row["activated_at"] is not None else "PENDING"
    if require_active and state != "ACTIVE":
        raise DeviceLinkError("device link is not active")
    if state in {"CLOSED", "EXPIRED"}:
        return state
    lease_expires_at = current + int(
        current_app.config["CAM_DEVICE_LINK_IDLE_SECONDS"]
    )
    connection.execute(
        "UPDATE device_links SET last_seen_at = ?, expires_at = ? WHERE link_id = ?",
        (current, lease_expires_at, link_id),
    )
    connection.execute(
        """
        UPDATE access_codes SET expires_at = ?
        WHERE link_id = ? AND consumed_at IS NULL AND revoked_at IS NULL
        """,
        (lease_expires_at, link_id),
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
    if operation == "START_AUTONOMOUS_RUN":
        active_run = connection.execute(
            """
            SELECT job_id FROM device_jobs
            WHERE device_id = ? AND operation = 'START_AUTONOMOUS_RUN'
              AND status IN ('PENDING', 'CLAIMED')
            ORDER BY created_at DESC LIMIT 1
            """,
            (device_id,),
        ).fetchone()
        if active_run is not None:
            raise DeviceLinkError("the vehicle already has an active run request")
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


def _validated_vehicle_run_receipt(receipt: Mapping[str, Any]) -> dict[str, Any]:
    expected = {
        "command_id",
        "operator",
        "state",
        "exit_code",
        "started_at_utc",
        "finished_at_utc",
        "log_file",
        "stop_requested",
        "physical_motion_observed",
    }
    if not isinstance(receipt, Mapping) or set(receipt) != expected:
        raise DeviceLinkError("vehicle run receipt has unexpected fields")
    command_id = receipt["command_id"]
    if (
        not isinstance(command_id, str)
        or len(command_id) != 32
        or any(character not in "0123456789abcdef" for character in command_id)
    ):
        raise DeviceLinkError("vehicle run receipt command id is invalid")
    if receipt["state"] not in RUN_STATES:
        raise DeviceLinkError("vehicle run receipt state is invalid")
    if isinstance(receipt["exit_code"], bool) or not isinstance(receipt["exit_code"], int):
        raise DeviceLinkError("vehicle run receipt exit code is invalid")
    for field in ("operator", "started_at_utc", "finished_at_utc", "log_file"):
        value = receipt[field]
        if not isinstance(value, str) or not value.strip() or len(value) > 240:
            raise DeviceLinkError(f"vehicle run receipt {field} is invalid")
    if not isinstance(receipt["stop_requested"], bool):
        raise DeviceLinkError("vehicle run receipt stop flag is invalid")
    if receipt["physical_motion_observed"] is not False:
        raise DeviceLinkError("vehicle run receipt cannot claim physical observation")
    return dict(receipt)


def store_vehicle_run_events(
    link_id: str,
    device_id: str,
    job_id: str,
    events: object,
) -> bool:
    """Persist an ordered KADER batch and return the current cancel request."""

    if not isinstance(events, list) or len(events) > MAX_RUN_EVENT_BATCH:
        raise DeviceLinkError(
            f"vehicle run events must be a list of at most {MAX_RUN_EVENT_BATCH} records"
        )
    connection = get_db()
    job = connection.execute(
        """
        SELECT operation, status, cancel_requested_at FROM device_jobs
        WHERE job_id = ? AND link_id = ? AND device_id = ?
        """,
        (job_id, link_id, device_id),
    ).fetchone()
    if job is None or str(job["operation"]) != "START_AUTONOMOUS_RUN":
        raise DeviceLinkError("vehicle run job is unavailable")
    if str(job["status"]) != "CLAIMED":
        raise DeviceLinkError("vehicle run job is not active")

    last_row = connection.execute(
        "SELECT MAX(sequence) AS last_sequence FROM vehicle_run_events WHERE job_id = ?",
        (job_id,),
    ).fetchone()
    last_sequence = -1 if last_row["last_sequence"] is None else int(last_row["last_sequence"])
    received_at = now_epoch()
    for raw_event in events:
        try:
            record = RunEvent.from_dict(raw_event)
        except (TypeError, ValueError) as exc:
            raise DeviceLinkError(f"vehicle run event is invalid: {exc}") from exc
        if record.run_id != job_id:
            raise DeviceLinkError("vehicle run event belongs to another run")
        event_json = _canonical_json(record.to_dict())
        if record.sequence <= last_sequence:
            existing = connection.execute(
                """
                SELECT event_json FROM vehicle_run_events
                WHERE job_id = ? AND sequence = ?
                """,
                (job_id, record.sequence),
            ).fetchone()
            if existing is None or not hmac.compare_digest(
                str(existing["event_json"]), event_json
            ):
                raise DeviceLinkError("vehicle run event sequence was reused with different data")
            continue
        if record.sequence != last_sequence + 1:
            raise DeviceLinkError("vehicle run event sequence is not contiguous")
        adam_state = None
        if record.module == "ADAM" and record.kind.value == "STATE":
            candidate = record.data.get("state")
            if candidate in RUN_STATES:
                adam_state = str(candidate)
        connection.execute(
            """
            INSERT INTO vehicle_run_events(
                job_id, sequence, recorded_at, received_at, adam_state, event_json
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                job_id,
                record.sequence,
                record.recorded_at,
                received_at,
                adam_state,
                event_json,
            ),
        )
        last_sequence = record.sequence
    connection.commit()
    return job["cancel_requested_at"] is not None


def request_vehicle_run_cancel(job_id: str, actor: str) -> bool:
    """Request cancellation for one run owned by the authenticated legal name."""

    normalized_actor = actor.strip() if isinstance(actor, str) else ""
    if not normalized_actor:
        raise DeviceLinkError("vehicle run cancellation actor is invalid")
    connection = get_db()
    row = connection.execute(
        """
        SELECT operation, payload_json, status FROM device_jobs WHERE job_id = ?
        """,
        (job_id,),
    ).fetchone()
    if row is None or str(row["operation"]) != "START_AUTONOMOUS_RUN":
        return False
    payload = json.loads(str(row["payload_json"]))
    if payload.get("operator") != normalized_actor:
        return False
    current = now_epoch()
    status = str(row["status"])
    if status == "PENDING":
        receipt = _canonical_json(
            {
                "cancelled": True,
                "state": RUN_CANCELLED,
                "reason": "operator cancelled before vehicle claim",
            }
        )
        changed = connection.execute(
            """
            UPDATE device_jobs
            SET status = 'REJECTED', completed_at = ?, receipt_json = ?,
                cancel_requested_at = ?, cancel_requested_by = ?
            WHERE job_id = ? AND status = 'PENDING'
            """,
            (current, receipt, current, normalized_actor, job_id),
        ).rowcount
    elif status == "CLAIMED":
        changed = connection.execute(
            """
            UPDATE device_jobs
            SET cancel_requested_at = COALESCE(cancel_requested_at, ?),
                cancel_requested_by = COALESCE(cancel_requested_by, ?)
            WHERE job_id = ? AND status = 'CLAIMED'
            """,
            (current, normalized_actor, job_id),
        ).rowcount
    else:
        return False
    connection.commit()
    if changed:
        audit(normalized_actor, "VEHICLE_RUN_CANCEL_REQUESTED", job_id, {})
    return changed == 1


def get_vehicle_run_for_actor(
    job_id: str,
    actor: str,
    *,
    after_sequence: int = -1,
    event_limit: int = 200,
) -> dict[str, Any] | None:
    if (
        isinstance(after_sequence, bool)
        or not isinstance(after_sequence, int)
        or after_sequence < -1
    ):
        raise DeviceLinkError("vehicle run event cursor is invalid")
    if not 1 <= event_limit <= 500:
        raise DeviceLinkError("vehicle run event limit is invalid")
    row = get_db().execute(
        """
        SELECT device_id, payload_json, status, receipt_json, created_at,
               claimed_at, completed_at, cancel_requested_at
        FROM device_jobs
        WHERE job_id = ? AND operation = 'START_AUTONOMOUS_RUN'
        """,
        (job_id,),
    ).fetchone()
    if row is None:
        return None
    payload = json.loads(str(row["payload_json"]))
    normalized_actor = actor.strip() if isinstance(actor, str) else ""
    if payload.get("operator") != normalized_actor:
        return None
    event_rows = get_db().execute(
        """
        SELECT sequence, event_json FROM vehicle_run_events
        WHERE job_id = ? AND sequence > ? ORDER BY sequence LIMIT ?
        """,
        (job_id, after_sequence, event_limit),
    ).fetchall()
    latest = get_db().execute(
        """
        SELECT adam_state FROM vehicle_run_events
        WHERE job_id = ? AND adam_state IS NOT NULL
        ORDER BY sequence DESC LIMIT 1
        """,
        (job_id,),
    ).fetchone()
    created_at = int(row["created_at"])
    return {
        "job_id": job_id,
        "device_id": str(row["device_id"]),
        "payload": payload,
        "status": str(row["status"]),
        "receipt": None
        if row["receipt_json"] is None
        else json.loads(str(row["receipt_json"])),
        "created_at": created_at,
        "created_at_utc": datetime.fromtimestamp(
            created_at, tz=timezone.utc
        ).isoformat(timespec="seconds"),
        "claimed_at": row["claimed_at"],
        "completed_at": row["completed_at"],
        "cancel_requested": row["cancel_requested_at"] is not None,
        "adam_state": None if latest is None else str(latest["adam_state"]),
        "events": [json.loads(str(event["event_json"])) for event in event_rows],
    }


def list_vehicle_runs_for_actor(actor: str, *, limit: int = 10) -> list[dict[str, Any]]:
    normalized_actor = actor.strip() if isinstance(actor, str) else ""
    if not normalized_actor or not 1 <= limit <= 50:
        return []
    rows = get_db().execute(
        """
        SELECT job_id FROM device_jobs
        WHERE operation = 'START_AUTONOMOUS_RUN'
        ORDER BY created_at DESC LIMIT 100
        """
    ).fetchall()
    runs: list[dict[str, Any]] = []
    for row in rows:
        run = get_vehicle_run_for_actor(str(row["job_id"]), normalized_actor, event_limit=1)
        if run is not None:
            runs.append(run)
        if len(runs) >= limit:
            break
    return runs


def complete_device_job(
    link_id: str,
    device_id: str,
    job_id: str,
    *,
    accepted: bool,
    receipt: Mapping[str, Any],
) -> bool:
    job = get_db().execute(
        """
        SELECT operation FROM device_jobs
        WHERE job_id = ? AND link_id = ? AND device_id = ? AND status = 'CLAIMED'
        """,
        (job_id, link_id, device_id),
    ).fetchone()
    if job is None:
        return False
    operation = str(job["operation"])
    if operation == "CAPTURE_CALIBRATION_FRAME":
        receipt = validate_calibration_frame_receipt(receipt)
    elif operation == "START_AUTONOMOUS_RUN" and accepted:
        receipt = _validated_vehicle_run_receipt(receipt)
        if receipt["command_id"] != job_id:
            raise DeviceLinkError("vehicle run receipt command id does not match its job")
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
        SELECT operation, payload_json, status, receipt_json, created_at, completed_at,
               cancel_requested_at
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
        "cancel_requested": row["cancel_requested_at"] is not None,
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
    "get_vehicle_run_for_actor",
    "list_vehicle_runs_for_actor",
    "queue_device_job",
    "request_vehicle_run_cancel",
    "revoke_device_link",
    "store_capability_report",
    "store_device_snapshot",
    "store_vehicle_run_events",
    "validate_calibration_frame_receipt",
]
