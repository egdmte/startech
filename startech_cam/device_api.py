"""Signed HTTP API used only by registered STARTECH-YAREN installations."""

from __future__ import annotations

from typing import Any

from flask import Blueprint, Response, current_app, jsonify, request

from .device_security import (
    DeviceAuthenticationError,
    device_remote_is_limited,
    issue_device_nonce,
    record_device_attempt,
    verify_and_consume_request,
)
from .device_link import (
    DeviceLinkError,
    authenticate_device_link,
    claim_next_device_job,
    complete_device_job,
    create_device_link,
    revoke_device_link,
    store_capability_report,
    store_device_snapshot,
)
from .security import issue_access_code


device_api_blueprint = Blueprint("device_api", __name__, url_prefix="/api/device/v1")


def _ordered_json(value: dict[str, Any]) -> Response:
    """Preserve nested calibration order across the legacy digest boundary."""

    return current_app.response_class(
        current_app.json.dumps(value, sort_keys=False),
        mimetype="application/json",
    )


def _error(code: str, message: str, status: int):
    return jsonify({"error": {"code": code, "message": message}}), status


def _remote() -> str:
    return (request.remote_addr or "unknown")[:120]


def _object_with_exact_fields(fields: set[str]) -> dict[str, Any] | None:
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or set(payload) != fields:
        return None
    return payload


def _bearer_token() -> str:
    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        return ""
    return authorization[7:]


def _authenticate_link_payload(
    payload: dict[str, Any] | None, *, require_active: bool
) -> tuple[str, str, str]:
    if payload is None:
        raise DeviceLinkError("link request has unexpected fields")
    token = _bearer_token()
    if not token:
        raise DeviceLinkError("device link bearer token is required")
    device_id = payload.get("device_id")
    link_id = payload.get("link_id")
    if not isinstance(device_id, str) or not isinstance(link_id, str):
        raise DeviceLinkError("device_id and link_id must be text")
    state = authenticate_device_link(
        link_id, device_id, token, require_active=require_active
    )
    return device_id, link_id, state


@device_api_blueprint.post("/challenge")
def challenge():
    remote = _remote()
    if device_remote_is_limited(remote):
        return _error("rate_limited", "Too many rejected device requests.", 429)
    payload = _object_with_exact_fields({"device_id"})
    if payload is None:
        record_device_attempt(remote, "challenge", succeeded=False)
        return _error("invalid_request", "A device_id JSON field is required.", 400)
    try:
        nonce, expires_at = issue_device_nonce(payload["device_id"])
    except DeviceAuthenticationError:
        record_device_attempt(remote, "challenge", succeeded=False)
        return _error("device_rejected", "The registered device was not accepted.", 403)
    record_device_attempt(remote, "challenge", succeeded=True)
    return jsonify(
        {
            "algorithm": "Ed25519",
            "challenge": nonce,
            "expires_at": expires_at,
        }
    )


@device_api_blueprint.post("/access-code")
def access_code():
    remote = _remote()
    if device_remote_is_limited(remote):
        return _error("rate_limited", "Too many rejected device requests.", 429)
    raw_body = request.get_data(cache=True)
    payload = _object_with_exact_fields({"device_id", "challenge"})
    signature = request.headers.get("X-STARTECH-Signature", "")
    if payload is None or not signature:
        record_device_attempt(remote, "access-code", succeeded=False)
        return _error("invalid_request", "The signed request is incomplete.", 400)
    try:
        device_id = verify_and_consume_request(
            payload["device_id"], payload["challenge"], signature, raw_body
        )
    except DeviceAuthenticationError:
        record_device_attempt(remote, "access-code", succeeded=False)
        return _error("authentication_failed", "The device request was not accepted.", 401)
    link = create_device_link(device_id)
    try:
        code = issue_access_code(device_id, link_id=link.link_id)
    except Exception:
        revoke_device_link(link.link_id, actor="access-code-failure")
        raise
    record_device_attempt(remote, "access-code", succeeded=True)
    return jsonify(
        {
            "access_code": code,
            "device_id": device_id,
            "expires_at": link.expires_at,
            "link_id": link.link_id,
            "link_token": link.link_token,
            "single_use": True,
        }
    )


@device_api_blueprint.post("/link/poll")
def link_poll():
    remote = _remote()
    payload = _object_with_exact_fields({"device_id", "link_id"})
    try:
        device_id, link_id, state = _authenticate_link_payload(
            payload, require_active=False
        )
        job = None if state != "ACTIVE" else claim_next_device_job(link_id, device_id)
    except DeviceLinkError:
        record_device_attempt(remote, "link-poll", succeeded=False)
        return _error("link_rejected", "The temporary device link was not accepted.", 401)
    return _ordered_json({"state": state, "job": job})


@device_api_blueprint.post("/link/snapshot")
def link_snapshot():
    remote = _remote()
    payload = _object_with_exact_fields(
        {"device_id", "link_id", "captured_at", "document"}
    )
    try:
        device_id, link_id, _state = _authenticate_link_payload(
            payload, require_active=True
        )
        store_device_snapshot(
            link_id,
            device_id,
            captured_at=payload["captured_at"],
            document=payload["document"],
        )
    except DeviceLinkError as exc:
        record_device_attempt(remote, "link-snapshot", succeeded=False)
        return _error("snapshot_rejected", str(exc), 400)
    return jsonify({"accepted": True})


@device_api_blueprint.post("/link/capabilities")
def link_capabilities():
    remote = _remote()
    payload = _object_with_exact_fields({"device_id", "link_id", "report"})
    try:
        device_id, link_id, _state = _authenticate_link_payload(
            payload, require_active=True
        )
        store_capability_report(link_id, device_id, payload["report"])
    except DeviceLinkError as exc:
        record_device_attempt(remote, "link-capabilities", succeeded=False)
        return _error("capabilities_rejected", str(exc), 400)
    return jsonify({"accepted": True})


@device_api_blueprint.post("/link/receipt")
def link_receipt():
    remote = _remote()
    payload = _object_with_exact_fields(
        {"device_id", "link_id", "job_id", "accepted", "receipt"}
    )
    try:
        device_id, link_id, _state = _authenticate_link_payload(
            payload, require_active=True
        )
        if not isinstance(payload["job_id"], str) or not isinstance(
            payload["accepted"], bool
        ) or not isinstance(payload["receipt"], dict):
            raise DeviceLinkError("job receipt fields are invalid")
        changed = complete_device_job(
            link_id,
            device_id,
            payload["job_id"],
            accepted=payload["accepted"],
            receipt=payload["receipt"],
        )
        if not changed:
            raise DeviceLinkError("job is unavailable or already completed")
    except DeviceLinkError as exc:
        record_device_attempt(remote, "link-receipt", succeeded=False)
        return _error("receipt_rejected", str(exc), 400)
    return jsonify({"accepted": True})


@device_api_blueprint.post("/link/close")
def link_close():
    remote = _remote()
    payload = _object_with_exact_fields({"device_id", "link_id"})
    try:
        device_id, link_id, _state = _authenticate_link_payload(
            payload, require_active=False
        )
        if not revoke_device_link(link_id, actor=device_id):
            raise DeviceLinkError("device link was already unavailable")
    except DeviceLinkError:
        record_device_attempt(remote, "link-close", succeeded=False)
        return _error("link_rejected", "The temporary device link was not accepted.", 401)
    return jsonify({"closed": True})


__all__ = ["device_api_blueprint"]
