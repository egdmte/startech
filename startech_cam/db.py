"""SQLite lifecycle and schema for KERİM."""

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
    link_id TEXT,
    issued_at INTEGER NOT NULL,
    expires_at INTEGER NOT NULL,
    consumed_at INTEGER,
    consumed_by TEXT,
    revoked_at INTEGER,
    revoked_by TEXT
);
CREATE INDEX IF NOT EXISTS access_codes_expiry ON access_codes(expires_at);

CREATE TABLE IF NOT EXISTS registered_devices (
    device_id TEXT PRIMARY KEY,
    algorithm TEXT NOT NULL CHECK (algorithm = 'Ed25519'),
    public_key_b64 TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    created_by TEXT NOT NULL,
    rotated_at INTEGER,
    rotated_by TEXT,
    disabled_at INTEGER,
    disabled_by TEXT
);

CREATE TABLE IF NOT EXISTS device_nonces (
    nonce_digest TEXT PRIMARY KEY,
    device_id TEXT NOT NULL,
    issued_at INTEGER NOT NULL,
    expires_at INTEGER NOT NULL,
    consumed_at INTEGER,
    FOREIGN KEY (device_id) REFERENCES registered_devices(device_id)
);
CREATE INDEX IF NOT EXISTS device_nonces_device_expiry
    ON device_nonces(device_id, expires_at);

CREATE TABLE IF NOT EXISTS device_api_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    remote_address TEXT NOT NULL,
    action TEXT NOT NULL,
    attempted_at INTEGER NOT NULL,
    succeeded INTEGER NOT NULL CHECK (succeeded IN (0, 1))
);
CREATE INDEX IF NOT EXISTS device_api_attempts_remote_time
    ON device_api_attempts(remote_address, attempted_at);

CREATE TABLE IF NOT EXISTS device_links (
    link_id TEXT PRIMARY KEY,
    token_digest TEXT NOT NULL UNIQUE,
    device_id TEXT NOT NULL,
    issued_at INTEGER NOT NULL,
    expires_at INTEGER NOT NULL,
    activated_at INTEGER,
    activated_by TEXT,
    last_seen_at INTEGER,
    revoked_at INTEGER,
    revoked_by TEXT,
    FOREIGN KEY (device_id) REFERENCES registered_devices(device_id)
);
CREATE INDEX IF NOT EXISTS device_links_device_expiry
    ON device_links(device_id, expires_at);

CREATE TABLE IF NOT EXISTS device_snapshots (
    link_id TEXT PRIMARY KEY,
    device_id TEXT NOT NULL,
    captured_at INTEGER NOT NULL,
    received_at INTEGER NOT NULL,
    payload_json TEXT NOT NULL,
    FOREIGN KEY (link_id) REFERENCES device_links(link_id),
    FOREIGN KEY (device_id) REFERENCES registered_devices(device_id)
);

CREATE TABLE IF NOT EXISTS device_capability_reports (
    link_id TEXT PRIMARY KEY,
    device_id TEXT NOT NULL,
    checked_at INTEGER NOT NULL,
    received_at INTEGER NOT NULL,
    payload_json TEXT NOT NULL,
    FOREIGN KEY (link_id) REFERENCES device_links(link_id),
    FOREIGN KEY (device_id) REFERENCES registered_devices(device_id)
);

CREATE TABLE IF NOT EXISTS device_jobs (
    job_id TEXT PRIMARY KEY,
    link_id TEXT NOT NULL,
    device_id TEXT NOT NULL,
    operation TEXT NOT NULL CHECK (operation IN (
        'REQUEST_ACTIVE_CONFIGURATION',
        'REQUEST_CAPABILITY_REPORT',
        'INSTALL_INACTIVE_CONFIGURATION',
        'RUN_BOUNDED_WORKSHOP_COMMAND',
        'CAPTURE_CALIBRATION_FRAME',
        'START_AUTONOMOUS_RUN'
    )),
    payload_json TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    expires_at INTEGER NOT NULL,
    claimed_at INTEGER,
    completed_at INTEGER,
    status TEXT NOT NULL CHECK (status IN (
        'PENDING', 'CLAIMED', 'ACCEPTED', 'REJECTED', 'EXPIRED'
    )),
    receipt_json TEXT,
    cancel_requested_at INTEGER,
    cancel_requested_by TEXT,
    FOREIGN KEY (link_id) REFERENCES device_links(link_id),
    FOREIGN KEY (device_id) REFERENCES registered_devices(device_id)
);
CREATE INDEX IF NOT EXISTS device_jobs_link_status
    ON device_jobs(link_id, status, created_at);

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
    _create_vehicle_run_events(connection)
    connection.commit()


def _column_names(connection: sqlite3.Connection, table: str) -> set[str]:
    return {
        str(row[1])
        for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
    }


def _migrate_existing_database(connection: sqlite3.Connection) -> None:
    """Apply additive migrations required by older KERİM SQLite files."""

    access_code_columns = _column_names(connection, "access_codes")
    if "revoked_at" not in access_code_columns:
        connection.execute("ALTER TABLE access_codes ADD COLUMN revoked_at INTEGER")
    if "revoked_by" not in access_code_columns:
        connection.execute("ALTER TABLE access_codes ADD COLUMN revoked_by TEXT")
    if "link_id" not in access_code_columns:
        connection.execute("ALTER TABLE access_codes ADD COLUMN link_id TEXT")

    draft_columns = _column_names(connection, "drafts")
    if "parent_tag" not in draft_columns:
        connection.execute("ALTER TABLE drafts ADD COLUMN parent_tag TEXT")

    jobs_sql_row = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'device_jobs'"
    ).fetchone()
    jobs_sql = "" if jobs_sql_row is None else str(jobs_sql_row[0] or "")
    if (
        "RUN_BOUNDED_WORKSHOP_COMMAND" not in jobs_sql
        or "CAPTURE_CALIBRATION_FRAME" not in jobs_sql
        or "START_AUTONOMOUS_RUN" not in jobs_sql
    ):
        connection.execute("ALTER TABLE device_jobs RENAME TO device_jobs_legacy")
        connection.execute(
            """
            CREATE TABLE device_jobs (
                job_id TEXT PRIMARY KEY,
                link_id TEXT NOT NULL,
                device_id TEXT NOT NULL,
                operation TEXT NOT NULL CHECK (operation IN (
                    'REQUEST_ACTIVE_CONFIGURATION',
                    'REQUEST_CAPABILITY_REPORT',
                    'INSTALL_INACTIVE_CONFIGURATION',
                    'RUN_BOUNDED_WORKSHOP_COMMAND',
                    'CAPTURE_CALIBRATION_FRAME',
                    'START_AUTONOMOUS_RUN'
                )),
                payload_json TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                expires_at INTEGER NOT NULL,
                claimed_at INTEGER,
                completed_at INTEGER,
                status TEXT NOT NULL CHECK (status IN (
                    'PENDING', 'CLAIMED', 'ACCEPTED', 'REJECTED', 'EXPIRED'
                )),
                receipt_json TEXT,
                cancel_requested_at INTEGER,
                cancel_requested_by TEXT,
                FOREIGN KEY (link_id) REFERENCES device_links(link_id),
                FOREIGN KEY (device_id) REFERENCES registered_devices(device_id)
            )
            """
        )
        connection.execute(
            """
            INSERT INTO device_jobs(
                job_id, link_id, device_id, operation, payload_json, created_at,
                expires_at, claimed_at, completed_at, status, receipt_json
            )
            SELECT
                job_id, link_id, device_id, operation, payload_json, created_at,
                expires_at, claimed_at, completed_at, status, receipt_json
            FROM device_jobs_legacy
            """
        )
        connection.execute("DROP TABLE device_jobs_legacy")
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS device_jobs_link_status
            ON device_jobs(link_id, status, created_at)
            """
        )
    else:
        job_columns = _column_names(connection, "device_jobs")
        if "cancel_requested_at" not in job_columns:
            connection.execute(
                "ALTER TABLE device_jobs ADD COLUMN cancel_requested_at INTEGER"
            )
        if "cancel_requested_by" not in job_columns:
            connection.execute(
                "ALTER TABLE device_jobs ADD COLUMN cancel_requested_by TEXT"
            )


def _create_vehicle_run_events(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS vehicle_run_events (
            job_id TEXT NOT NULL,
            sequence INTEGER NOT NULL CHECK (sequence >= 0),
            recorded_at REAL NOT NULL CHECK (recorded_at >= 0),
            received_at INTEGER NOT NULL,
            adam_state TEXT,
            event_json TEXT NOT NULL,
            PRIMARY KEY (job_id, sequence),
            FOREIGN KEY (job_id) REFERENCES device_jobs(job_id)
        );
        CREATE INDEX IF NOT EXISTS vehicle_run_events_received
            ON vehicle_run_events(job_id, sequence);
        """
    )


def init_app(app: Flask) -> None:
    app.teardown_appcontext(close_db)


__all__ = ["get_db", "init_app", "init_database"]
