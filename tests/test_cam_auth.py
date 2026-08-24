"""Security behaviour tests for the production CAM service."""

from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

from startech_cam import create_app
from startech_cam.db import get_db
from startech_cam.security import issue_access_code


TOKEN = re.compile(rb'name="csrf_token" value="([^"]+)"')


class CamAuthTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.app = create_app(
            {
                "TESTING": True,
                "DATABASE": str(Path(self.temporary.name) / "cam.sqlite3"),
                "SECRET_KEY": "test-secret-that-is-long-enough-for-sessions",
                "CAM_PASSWORD": "school-password",
                "CAM_PASSWORD_HASH": "",
                "SESSION_COOKIE_SECURE": False,
            }
        )
        self.client = self.app.test_client()

    def tearDown(self):
        self.temporary.cleanup()

    def csrf(self, path: str) -> str:
        response = self.client.get(path)
        match = TOKEN.search(response.data)
        self.assertIsNotNone(match, path)
        return match.group(1).decode("ascii")

    def login(self, client=None, name: str = "Egemen Yusuf Kayra"):
        client = client or self.client
        response = client.get("/login")
        token = TOKEN.search(response.data).group(1).decode("ascii")
        return client.post(
            "/login",
            data={"csrf_token": token, "legal_name": name, "password": "school-password"},
        )

    def test_csrf_is_required_before_password_processing(self):
        response = self.client.post(
            "/login",
            data={"legal_name": "Egemen", "password": "school-password"},
        )
        self.assertEqual(400, response.status_code)

    def test_password_session_and_single_use_access_code(self):
        response = self.login()
        self.assertEqual(302, response.status_code)
        self.assertTrue(response.location.endswith("/access"))
        with self.app.app_context():
            code = issue_access_code("YAREN-school-car")
            row = get_db().execute("SELECT code_digest FROM access_codes").fetchone()
            self.assertNotEqual(code, row["code_digest"])

        token = self.csrf("/access")
        response = self.client.post(
            "/access",
            data={"csrf_token": token, "access_code": code},
        )
        self.assertEqual(302, response.status_code)
        self.assertTrue(response.location.endswith("/dashboard"))

        second = self.app.test_client()
        self.login(second, "T")
        response = second.get("/access")
        token = TOKEN.search(response.data).group(1).decode("ascii")
        reused = second.post(
            "/access",
            data={"csrf_token": token, "access_code": code},
        )
        self.assertEqual(400, reused.status_code)
        self.assertIn(b"already used", reused.data)

    def test_five_failures_rate_limit_the_remote_address(self):
        for _attempt in range(5):
            token = self.csrf("/login")
            response = self.client.post(
                "/login",
                data={"csrf_token": token, "legal_name": "Egemen", "password": "wrong"},
            )
            self.assertEqual(401, response.status_code)
        token = self.csrf("/login")
        limited = self.client.post(
            "/login",
            data={"csrf_token": token, "legal_name": "Egemen", "password": "wrong"},
        )
        self.assertEqual(429, limited.status_code)


if __name__ == "__main__":
    unittest.main(verbosity=2)
