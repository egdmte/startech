"""Repository-level integrity tests for production CAM persistence."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from startech_cam import create_app
from startech_cam.db import get_db
from startech_cam.repository import (
    DraftNotFound,
    InvalidDocument,
    create_draft,
    get_calibration,
    parse_document_text,
    parse_json_value,
    publish_draft,
)


class CamRepositoryTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.database = Path(self.temporary.name) / "cam.sqlite3"
        self.app = create_app(
            {
                "TESTING": True,
                "DATABASE": str(self.database),
                "SECRET_KEY": "repository-secret-that-is-long-enough-for-tests",
                "CAM_PASSWORD": "school-password",
                "CAM_PASSWORD_HASH": "",
                "SESSION_COOKIE_SECURE": False,
            }
        )

    def tearDown(self):
        self.temporary.cleanup()

    def test_strict_json_rejects_duplicate_and_non_finite_values(self):
        with self.assertRaisesRegex(InvalidDocument, "duplicate JSON field"):
            parse_json_value('{"field": 1, "field": 2}')
        with self.assertRaisesRegex(InvalidDocument, "non-finite"):
            parse_json_value('{"field": NaN}')
        with self.assertRaisesRegex(InvalidDocument, "root must be an object"):
            parse_document_text("[]")

    def test_publishing_consumes_a_draft_once(self):
        with self.app.app_context():
            draft_id = create_draft(
                owner="Egemen", workflow="MAC", name="One publication"
            )
            tag = publish_draft(draft_id, "Egemen")
            self.assertEqual(tag, get_calibration(tag)["profil"]["kimlik"])
            with self.assertRaises(DraftNotFound):
                publish_draft(draft_id, "Egemen")
            self.assertEqual(
                1, get_db().execute("SELECT COUNT(*) FROM calibrations").fetchone()[0]
            )

    def test_parent_lineage_survives_new_draft_identity(self):
        with self.app.app_context():
            base_draft = create_draft(owner="Egemen", workflow="MAC", name="Base")
            base_tag = publish_draft(base_draft, "Egemen")
            source = get_calibration(base_tag)
            child_draft = create_draft(
                owner="Egemen",
                workflow="MAC",
                name="Child",
                source="PREVIOUS",
                source_document=source,
                parent_tag=base_tag,
            )
            child_tag = publish_draft(child_draft, "Egemen")
            row = get_db().execute(
                "SELECT parent_tag FROM calibrations WHERE tag = ?", (child_tag,)
            ).fetchone()
            self.assertEqual(base_tag, row["parent_tag"])
            self.assertNotEqual(base_tag, child_tag)


class CamDatabaseMigrationTest(unittest.TestCase):
    def test_additive_migration_updates_pre_hardening_database(self):
        with tempfile.TemporaryDirectory() as temporary:
            database = Path(temporary) / "old-cam.sqlite3"
            connection = sqlite3.connect(database)
            connection.executescript(
                """
                CREATE TABLE access_codes (
                    code_digest TEXT PRIMARY KEY,
                    device_id TEXT NOT NULL,
                    issued_at INTEGER NOT NULL,
                    expires_at INTEGER NOT NULL,
                    consumed_at INTEGER,
                    consumed_by TEXT
                );
                CREATE TABLE drafts (
                    draft_id TEXT PRIMARY KEY,
                    owner TEXT NOT NULL,
                    workflow TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    touched_sections_json TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL
                );
                """
            )
            connection.commit()
            connection.close()

            app = create_app(
                {
                    "TESTING": True,
                    "DATABASE": str(database),
                    "SECRET_KEY": "migration-secret-that-is-long-enough-for-tests",
                    "CAM_PASSWORD": "school-password",
                    "CAM_PASSWORD_HASH": "",
                    "SESSION_COOKIE_SECURE": False,
                }
            )
            with app.app_context():
                access_columns = {
                    row[1]
                    for row in get_db().execute("PRAGMA table_info(access_codes)")
                }
                draft_columns = {
                    row[1] for row in get_db().execute("PRAGMA table_info(drafts)")
                }
                attempts_table = get_db().execute(
                    """
                    SELECT name FROM sqlite_master
                    WHERE type = 'table' AND name = 'access_code_attempts'
                    """
                ).fetchone()
            self.assertIn("revoked_at", access_columns)
            self.assertIn("revoked_by", access_columns)
            self.assertIn("parent_tag", draft_columns)
            self.assertIsNotNone(attempts_table)


if __name__ == "__main__":
    unittest.main(verbosity=2)
