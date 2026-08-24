"""Signed HTTP API used only by registered STARTECH-YAREN installations."""

from __future__ import annotations

from typing import Any

from flask import Blueprint, current_app, jsonify, request

from .device_security import (
    DeviceAuthenticationError,
    device_remote_is_limited,
    issue_device_nonce,
    record_device_attempt,
    verify_and_consume_request,
)
from .security import issue_access_code, now_epoch


device_api_blueprint = Blueprint("device_api", __name__, url_prefix="/api/device/v1")


def _error(code: str, message: str, status: int):
    return jsonify({"error": {"code": code, "message": message}}), status


def _remote() -> str:
    return (request.remote_addr or "unknown")[:120]


def _object_with_exact_fields(fields: set[str]) -> dict[str, Any] | None:
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or set(payload) != fields:
        return None
    return payload


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
    code = issue_access_code(device_id)
    record_device_attempt(remote, "access-code", succeeded=True)
    return jsonify(
        {
            "access_code": code,
            "device_id": device_id,
            "expires_at": now_epoch()
            + int(current_app.config["CAM_CODE_LIFETIME_SECONDS"]),
            "single_use": True,
        }
    )


__all__ = ["device_api_blueprint"]
