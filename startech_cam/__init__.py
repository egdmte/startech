"""Production web application for STARTECH calibration management.

CAM creates and validates configuration files.  It deliberately has no import of
the vehicle driver layer and no route that can arm or move the physical car.
"""

from __future__ import annotations

from datetime import timedelta
import os
from pathlib import Path
from typing import Any

from flask import Flask, request
from werkzeug.middleware.proxy_fix import ProxyFix

from . import db


def _environment(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    """Create CAM with explicit, fail-closed production configuration."""

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        DATABASE=_environment(
            "CAM_DATABASE", str(Path(app.instance_path) / "cam.sqlite3")
        ),
        SECRET_KEY=_environment("CAM_SESSION_SECRET"),
        CAM_PASSWORD=_environment("CAM_PASSWORD"),
        CAM_PASSWORD_HASH=_environment("CAM_PASSWORD_HASH"),
        CAM_CODE_LIFETIME_SECONDS=15 * 60,
        CAM_LOGIN_LIMIT=5,
        CAM_LOGIN_WINDOW_SECONDS=15 * 60,
        CAM_TRUST_PROXY=_environment("CAM_TRUST_PROXY", "0") == "1",
        MAX_CONTENT_LENGTH=1_000_000,
        PERMANENT_SESSION_LIFETIME=timedelta(minutes=15),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=_environment("CAM_COOKIE_SECURE", "1") != "0",
    )
    if test_config:
        app.config.update(test_config)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    Path(str(app.config["DATABASE"])).expanduser().resolve().parent.mkdir(
        parents=True, exist_ok=True
    )
    _validate_configuration(app)
    if app.config["CAM_TRUST_PROXY"]:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    db.init_app(app)

    from .auth import auth_blueprint
    from .routes import cam_blueprint

    app.register_blueprint(auth_blueprint)
    app.register_blueprint(cam_blueprint)

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
        )
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "style-src 'self' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "script-src 'self'; img-src 'self' data:; "
            "object-src 'none'; base-uri 'self'; frame-ancestors 'none'; "
            "form-action 'self'",
        )
        if request.is_secure:
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        if request.endpoint and request.endpoint not in {"static"}:
            response.headers.setdefault("Cache-Control", "no-store")
        return response

    from .cli import register_cli

    register_cli(app)
    with app.app_context():
        db.init_database()
    return app


def _validate_configuration(app: Flask) -> None:
    if app.config.get("TESTING"):
        return
    secret = str(app.config.get("SECRET_KEY") or "")
    if len(secret) < 32:
        raise RuntimeError("CAM_SESSION_SECRET must contain at least 32 characters")
    if not (app.config.get("CAM_PASSWORD") or app.config.get("CAM_PASSWORD_HASH")):
        raise RuntimeError("CAM_PASSWORD or CAM_PASSWORD_HASH must be configured")


__all__ = ["create_app"]
