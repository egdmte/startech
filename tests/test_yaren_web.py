"""Tests for YAREN's private device identity and signed CAM client."""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest
from urllib.parse import urlsplit

from arac.yaren_web import (
    WebAccessError,
    create_device_identity,
    load_device_identity,
    request_web_code,
)
from startech_cam import create_app
from startech_cam.device_security import parse_public_identity, register_device


class YarenWebTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def test_identity_separates_private_and_shareable_public_material(self):
        private_path = self.root / "identity.json"
        identity, public_path = create_device_identity(
            "YAREN-school-car", private_path
        )
        loaded = load_device_identity(private_path)
        self.assertEqual(identity.device_id, loaded.device_id)
        self.assertEqual(identity.public_key_b64, loaded.public_key_b64)
        private_document = json.loads(private_path.read_text(encoding="utf-8"))
        public_document = json.loads(public_path.read_text(encoding="utf-8"))
        self.assertIn("private_key", private_document)
        self.assertNotIn("private_key", public_document)
        self.assertEqual(identity.public_key_b64, public_document["public_key"])
        if os.name != "nt":
            self.assertEqual(0o600, private_path.stat().st_mode & 0o777)

        with self.assertRaisesRegex(WebAccessError, "already exists"):
            create_device_identity("YAREN-school-car", private_path)

    def test_client_and_server_interoperate_with_exact_signed_bytes(self):
        private_path = self.root / "identity.json"
        _identity, public_path = create_device_identity(
            "YAREN-school-car", private_path
        )
        app = create_app(
            {
                "TESTING": True,
                "DATABASE": str(self.root / "cam.sqlite3"),
                "SECRET_KEY": "yaren-web-secret-that-is-long-enough-for-tests",
                "CAM_PASSWORD": "school-password",
                "CAM_PASSWORD_HASH": "",
                "SESSION_COOKIE_SECURE": False,
            }
        )
        device_id, public_key = parse_public_identity(
            public_path.read_text(encoding="utf-8")
        )
        with app.app_context():
            register_device(device_id, public_key, actor="test-admin")
        client = app.test_client()

        def post_json(url, body, headers, _timeout):
            response = client.post(
                urlsplit(url).path,
                data=body,
                content_type="application/json",
                headers=dict(headers),
            )
            if response.status_code >= 400:
                raise WebAccessError(response.get_json()["error"]["message"])
            return response.get_json()

        access = request_web_code(
            "https://cam.example.test",
            private_path,
            post_json=post_json,
        )
        self.assertEqual("YAREN-school-car", access.device_id)
        self.assertRegex(access.access_code, r"^[A-Z0-9]{8}$")

    def test_client_requires_https_origin_and_valid_private_identity(self):
        private_path = self.root / "identity.json"
        create_device_identity("YAREN-school-car", private_path)
        for invalid in (
            "http://cam.example.test",
            "https://user@cam.example.test",
            "https://cam.example.test/path",
        ):
            with self.subTest(invalid=invalid):
                with self.assertRaisesRegex(WebAccessError, "HTTPS origin"):
                    request_web_code(invalid, private_path, post_json=lambda *_: {})

        private_path.write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(WebAccessError, "unexpected fields"):
            load_device_identity(private_path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
