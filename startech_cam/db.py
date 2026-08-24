"""SQLite lifecycle and schema for CAM."""

from __future__ import annotations

import sqlite3

from flask import Flask, current_app, g


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS login_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    remote_address TEXT NOT NULL,
    attempted_at INTEGER NOT NULL,
    succeeded INTEGER NOT NULL CHECK (succeeded IN (0, 1))
);
CREATE INDEX IF NOT EXISTS login_attempts_remote_time
    ON login_attempts(remote_address, attempted_at);

CREATE TABLE IF NOT EXISTS access_code_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    remote_address TEXT NOT NULL,
    attempted_at INTEGER NOT NULL,
    succeeded INTEGER NOT NULL CHECK (succeeded IN (0, 1))
);
CREATE INDEX IF NOT EXISTS access_code_attempts_remote_time
    ON access_code_attempts(remote_address, attempted_at);

CREATE TABLE IF NOT EXISTS access_codes (
    code_digest TEXT PRIMARY KEY,
    device_id TEXT NOT NULL,
    issued_at INTEGER NOT NULL,
    expires_at INTEGER NOT NULL,
    consumed_at INTEGER,
    consumed_by TEXT,
    revoked_at INTEGER,
    revoked_by TEXT
);
CREATE INDEX IF NOT EXISTS access_codes_expiry ON access_codes(expires_at);

CREATE TABLE IF NOT EXISTS drafts (
    draft_id TEXT PRIMARY KEY,
    owner TEXT NOT NULL,
    workflow TEXT NOT NULL CHECK (workflow IN ('SAC', 'MAC')),
    payload_json TEXT NOT NULL,
    touched_sections_json TEXT NOT NULL,
    parent_tag TEXT,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS calibrations (
    tag TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    workflow TEXT NOT NULL CHECK (workflow IN ('SAC', 'MAC', 'IMPORT')),
    owner TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    parent_tag TEXT
);
CREATE INDEX IF NOT EXISTS calibrations_created_at ON calibrations(created_at DESC);

CREATE TABLE IF NOT EXISTS audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    happened_at INTEGER NOT NULL,
    actor TEXT NOT NULL,
    event_type TEXT NOT NULL,
    subject TEXT NOT NULL,
    detail_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS audit_events_time ON audit_events(happened_at DESC);
"""


def get_db() -> sqlite3.Connection:
    """Return the request-local database connection."""

    if "cam_db" not in g:
        connection = sqlite3.connect(
            current_app.config["DATABASE"],
            detect_types=sqlite3.PARSE_DECLTYPES,
            timeout=10,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        g.cam_db = connection
    return g.cam_db


def close_db(_error: BaseException | None = None) -> None:
    connection = g.pop("cam_db", None)
    if connection is not None:
        connection.close()


def init_database() -> None:
    connection = get_db()
    connection.executescript(SCHEMA)
    _migrate_existing_database(connection)
    connection.commit()


def _column_names(connection: sqlite3.Connection, table: str) -> set[str]:
    return {
        str(row[1])
        for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
    }


def _migrate_existing_database(connection: sqlite3.Connection) -> None:
    """Apply additive migrations required by older CAM SQLite files."""

    access_code_columns = _column_names(connection, "access_codes")
    if "revoked_at" not in access_code_columns:
        connection.execute("ALTER TABLE access_codes ADD COLUMN revoked_at INTEGER")
    if "revoked_by" not in access_code_columns:
        connection.execute("ALTER TABLE access_codes ADD COLUMN revoked_by TEXT")

    draft_columns = _column_names(connection, "drafts")
    if "parent_tag" not in draft_columns:
        connection.execute("ALTER TABLE drafts ADD COLUMN parent_tag TEXT")


def init_app(app: Flask) -> None:
    app.teardown_appcontext(close_db)


__all__ = ["get_db", "init_app", "init_database"]
