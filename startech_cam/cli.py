"""Administrative CAM commands intended for an authenticated VPS shell."""

from __future__ import annotations

import click
from flask import Flask

from .db import init_database
from .security import issue_access_code, prune_security_records, revoke_access_code


def register_cli(app: Flask) -> None:
    @app.cli.command("init-db")
    def init_db_command() -> None:
        """Create missing SQLite tables without deleting existing data."""

        init_database()
        click.echo("CAM database is ready.")

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


__all__ = ["register_cli"]
