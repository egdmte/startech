"""Administrative CAM commands intended for an authenticated VPS shell."""

from __future__ import annotations

import click
from flask import Flask

from .db import init_database
from .security import issue_access_code


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


__all__ = ["register_cli"]
