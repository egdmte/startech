"""Administrative KERİM commands intended for an authenticated VPS shell."""

from __future__ import annotations

from pathlib import Path

import click
from flask import Flask

from .db import init_database
from .device_security import (
    DeviceAuthenticationError,
    disable_device,
    list_devices,
    parse_public_identity,
    register_device,
)
from .security import issue_access_code, prune_security_records, revoke_access_code


def register_cli(app: Flask) -> None:
    @app.cli.command("init-db")
    def init_db_command() -> None:
        """Create missing SQLite tables without deleting existing data."""

        init_database()
        click.echo("KERİM database is ready.")

    @app.cli.command("issue-access-code")
    @click.option("--device", required=True, help="Stable device label shown to the user.")
    def issue_code_command(device: str) -> None:
        """Issue one single-use, fifteen-minute YAREN access code."""

        code = issue_access_code(device)
        click.echo(code)

    @app.cli.command("revoke-access-code")
    @click.option("--code", prompt="Access code", hide_input=True, required=True)
    @click.option("--actor", default="vps-admin", show_default=True)
    def revoke_code_command(code: str, actor: str) -> None:
        """Revoke one unconsumed code without echoing it."""

        if not revoke_access_code(code, actor):
            raise click.ClickException("code is invalid, consumed, or already revoked")
        click.echo("Access code revoked.")

    @app.cli.command("prune-security-records")
    @click.option("--retain-days", type=click.IntRange(min=0), default=7, show_default=True)
    def prune_security_command(retain_days: int) -> None:
        """Delete expired transient security data older than the retention period."""

        deleted = prune_security_records(retain_seconds=retain_days * 24 * 60 * 60)
        click.echo(
            "Deleted "
            + ", ".join(f"{table}={count}" for table, count in deleted.items())
        )

    def read_identity(path: Path) -> tuple[str, str]:
        try:
            return parse_public_identity(path.read_text(encoding="utf-8"))
        except (OSError, DeviceAuthenticationError) as exc:
            raise click.ClickException(str(exc)) from exc

    @app.cli.command("register-yaren-device")
    @click.option(
        "--identity",
        type=click.Path(path_type=Path, exists=True, dir_okay=False, readable=True),
        required=True,
        help="Public identity JSON exported by YAREN.",
    )
    @click.option("--actor", default="vps-admin", show_default=True)
    def register_yaren_device_command(identity: Path, actor: str) -> None:
        """Register a new YAREN public key without receiving its private key."""

        device_id, public_key = read_identity(identity)
        try:
            register_device(device_id, public_key, actor=actor)
        except DeviceAuthenticationError as exc:
            raise click.ClickException(str(exc)) from exc
        click.echo(f"Registered {device_id} with Ed25519.")

    @app.cli.command("rotate-yaren-device-key")
    @click.option(
        "--identity",
        type=click.Path(path_type=Path, exists=True, dir_okay=False, readable=True),
        required=True,
        help="Replacement public identity JSON exported by YAREN.",
    )
    @click.option("--actor", default="vps-admin", show_default=True)
    def rotate_yaren_device_command(identity: Path, actor: str) -> None:
        """Replace one device public key and invalidate its pending challenges."""

        device_id, public_key = read_identity(identity)
        try:
            register_device(device_id, public_key, actor=actor, replace=True)
        except DeviceAuthenticationError as exc:
            raise click.ClickException(str(exc)) from exc
        click.echo(f"Rotated {device_id}; old signatures are no longer accepted.")

    @app.cli.command("disable-yaren-device")
    @click.option("--device", required=True)
    @click.option("--actor", default="vps-admin", show_default=True)
    def disable_yaren_device_command(device: str, actor: str) -> None:
        """Disable a registered device and remove all pending challenges."""

        try:
            changed = disable_device(device, actor=actor)
        except DeviceAuthenticationError as exc:
            raise click.ClickException(str(exc)) from exc
        if not changed:
            raise click.ClickException("device is unknown or already disabled")
        click.echo(f"Disabled {device}.")

    @app.cli.command("list-yaren-devices")
    def list_yaren_devices_command() -> None:
        """List public identity status without displaying public keys."""

        devices = list_devices()
        if not devices:
            click.echo("No YAREN devices are registered.")
            return
        for device in devices:
            state = "disabled" if device["disabled_at"] is not None else "active"
            click.echo(
                f"{device['device_id']}\t{state}\t{device['algorithm']}\t"
                f"created={device['created_at']}"
            )


__all__ = ["register_cli"]
