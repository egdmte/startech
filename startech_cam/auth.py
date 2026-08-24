"""Password session and one-time YAREN access-code routes."""

from __future__ import annotations

from functools import wraps
from typing import Any, Callable, TypeVar, cast
from urllib.parse import unquote, urlsplit

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from .security import (
    access_code_remote_is_limited,
    audit,
    consume_access_code_grant,
    csrf_matches,
    csrf_token,
    now_epoch,
    record_access_code_attempt,
    record_login,
    remote_is_limited,
    verify_password,
)


auth_blueprint = Blueprint("auth", __name__)
F = TypeVar("F", bound=Callable[..., Any])


def login_required(view: F) -> F:
    @wraps(view)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        if not session_is_active():
            expired = bool(session.get("authenticated"))
            actor = current_actor()
            if expired:
                _revoke_session_link(actor)
                audit(actor, "SESSION_EXPIRED", "session", {})
                session.clear()
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)

    return cast(F, wrapped)


def current_actor() -> str:
    value = session.get("legal_name")
    return str(value) if isinstance(value, str) and value else "anonymous"


def session_is_active() -> bool:
    expires_at = session.get("session_expires_at", 0)
    return (
        bool(session.get("authenticated"))
        and isinstance(expires_at, int)
        and expires_at > now_epoch()
    )


def has_car_access() -> bool:
    expires_at = session.get("car_access_expires_at", 0)
    session_valid = (
        session_is_active()
        and isinstance(expires_at, int)
        and expires_at > now_epoch()
    )
    link_id = session.get("device_link_id")
    device_id = session.get("device_id")
    if not session_valid or not isinstance(link_id, str) or not isinstance(device_id, str):
        return False
    from .device_link import browser_link_is_active

    return browser_link_is_active(link_id, device_id)


def _revoke_session_link(actor: str) -> None:
    link_id = session.get("device_link_id")
    if isinstance(link_id, str):
        from .device_link import revoke_device_link

        revoke_device_link(link_id, actor=actor)


def _safe_local_target(value: str) -> str:
    decoded = unquote(value)
    parsed = urlsplit(decoded)
    if (
        not decoded.startswith("/")
        or decoded.startswith("//")
        or "\\" in decoded
        or parsed.scheme
        or parsed.netloc
        or any(ord(character) < 32 for character in decoded)
    ):
        return ""
    return value


@auth_blueprint.app_context_processor
def inject_auth_context() -> dict[str, Any]:
    return {
        "csrf_token": csrf_token,
        "current_actor": current_actor(),
        "has_car_access": has_car_access(),
        "session_expires_at": session.get("session_expires_at", 0),
    }


@auth_blueprint.before_app_request
def protect_unsafe_requests() -> None:
    # The device API has no browser session.  Bootstrap uses Ed25519 over a
    # single-use nonce; the resulting short-lived link uses its bearer token.
    if request.blueprint == "device_api":
        return
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        if not csrf_matches(request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")):
            abort(400, "The form expired or its CSRF token is invalid.")


@auth_blueprint.route("/login", methods=["GET", "POST"])
def login() -> Any:
    if session_is_active():
        return redirect(url_for("cam.dashboard"))
    if session.get("authenticated"):
        _revoke_session_link(current_actor())
        audit(current_actor(), "SESSION_EXPIRED", "session", {})
        session.clear()
    if request.method == "GET":
        return render_template("login.html")

    remote = request.remote_addr or "unknown"
    if remote_is_limited(remote):
        abort(429, "Too many failed login attempts. Wait fifteen minutes.")
    name = request.form.get("legal_name", "").strip()
    password = request.form.get("password", "")
    accepted = 1 <= len(name) <= 120 and verify_password(password)
    record_login(remote, succeeded=accepted)
    if not accepted:
        flash("The name or password was not accepted.", "error")
        return render_template("login.html", legal_name=name), 401

    session.clear()
    session.permanent = True
    session["authenticated"] = True
    session["legal_name"] = name
    session["session_expires_at"] = now_epoch() + int(
        current_app.config["CAM_SESSION_LIFETIME_SECONDS"]
    )
    csrf_token()
    audit(name, "LOGIN", remote, {})
    next_url = _safe_local_target(request.args.get("next", ""))
    if next_url:
        return redirect(next_url)
    return redirect(url_for("auth.access"))


@auth_blueprint.post("/logout")
@login_required
def logout() -> Any:
    actor = current_actor()
    _revoke_session_link(actor)
    audit(actor, "LOGOUT", "session", {})
    session.clear()
    return redirect(url_for("auth.login"))


@auth_blueprint.route("/access", methods=["GET", "POST"])
@login_required
def access() -> Any:
    if request.method == "GET":
        return render_template("access.html")
    remote = request.remote_addr or "unknown"
    if access_code_remote_is_limited(remote):
        abort(429, "Too many invalid YAREN codes. Wait fifteen minutes.")
    code = request.form.get("access_code", "")
    grant = consume_access_code_grant(code, current_actor())
    record_access_code_attempt(remote, succeeded=grant is not None)
    if grant is None:
        flash("That YAREN code is invalid, expired, or already used.", "error")
        return render_template("access.html"), 400
    _revoke_session_link(current_actor())
    session["device_id"] = grant.device_id
    if grant.link_id is not None:
        session["device_link_id"] = grant.link_id
    else:
        session.pop("device_link_id", None)
    session_deadline = int(session["session_expires_at"])
    access_deadline = now_epoch() + int(
        current_app.config["CAM_CAR_ACCESS_LIFETIME_SECONDS"]
    )
    session["car_access_expires_at"] = min(session_deadline, access_deadline)
    if grant.link_id is None:
        flash(
            f"Code accepted for {grant.device_id}, but it did not include a live YAREN link.",
            "success",
        )
    else:
        flash(f"Connected to {grant.device_id} for this session.", "success")
    return redirect(url_for("cam.dashboard"))


@auth_blueprint.post("/access/offline")
@login_required
def continue_offline() -> Any:
    _revoke_session_link(current_actor())
    session.pop("device_id", None)
    session.pop("device_link_id", None)
    session.pop("car_access_expires_at", None)
    audit(current_actor(), "OFFLINE_MODE", "session", {})
    return redirect(url_for("cam.dashboard"))


__all__ = [
    "auth_blueprint",
    "current_actor",
    "has_car_access",
    "login_required",
    "session_is_active",
]
