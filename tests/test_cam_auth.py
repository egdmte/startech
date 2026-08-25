"""Security behaviour tests for the production CAM service."""

from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path

from startech_cam import create_app
from startech_cam.db import get_db
from startech_cam.device_link import create_device_link
from startech_cam.repository import create_draft, publish_draft
from startech_cam.security import issue_access_code, revoke_access_code


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

    def test_health_reports_the_exact_configured_release(self):
        self.app.config["CAM_RELEASE"] = "a" * 40
        response = self.client.get("/health")
        self.assertEqual(200, response.status_code)
        self.assertEqual(
            {"status": "ok", "release": "a" * 40}, response.get_json()
        )

    def test_configured_single_proxy_sets_the_rate_limit_client_address(self):
        proxy_app = create_app(
            {
                "TESTING": True,
                "DATABASE": str(Path(self.temporary.name) / "proxy.sqlite3"),
                "SECRET_KEY": "proxy-secret-that-is-long-enough-for-tests",
                "CAM_PASSWORD": "school-password",
                "CAM_PASSWORD_HASH": "",
                "SESSION_COOKIE_SECURE": False,
                "CAM_TRUST_PROXY": True,
            }
        )
        client = proxy_app.test_client()
        headers = {
            "X-Forwarded-For": "203.0.113.9",
            "X-Forwarded-Proto": "https",
            "X-Forwarded-Host": "dymtal.avartech.net",
        }
        page = client.get("/login", headers=headers)
        token = TOKEN.search(page.data).group(1).decode("ascii")
        rejected = client.post(
            "/login",
            data={
                "csrf_token": token,
                "legal_name": "Proxy Test",
                "password": "wrong",
            },
            headers=headers,
        )
        self.assertEqual(401, rejected.status_code)
        with proxy_app.app_context():
            recorded = get_db().execute(
                "SELECT remote_address FROM login_attempts ORDER BY id DESC LIMIT 1"
            ).fetchone()["remote_address"]
        self.assertEqual("203.0.113.9", recorded)

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

    def test_linked_code_binds_browser_session_and_logout_revokes_link(self):
        self.login()
        with self.app.app_context():
            connection = get_db()
            connection.execute(
                """
                INSERT INTO registered_devices(
                    device_id, algorithm, public_key_b64, created_at, created_by
                ) VALUES (?, 'Ed25519', ?, 1, 'test')
                """,
                ("YAREN-linked", "A" * 43),
            )
            connection.commit()
            link = create_device_link("YAREN-linked")
            code = issue_access_code("YAREN-linked", link_id=link.link_id)

        token = self.csrf("/access")
        accepted = self.client.post(
            "/access", data={"csrf_token": token, "access_code": code}
        )
        self.assertEqual(302, accepted.status_code)
        with self.client.session_transaction() as browser_session:
            self.assertEqual(link.link_id, browser_session["device_link_id"])
            self.assertEqual("YAREN-linked", browser_session["device_id"])

        with self.app.app_context():
            draft_id = create_draft(
                owner="Egemen Yusuf Kayra",
                workflow="MAC",
                name="Linked sideload test",
            )
            tag = publish_draft(draft_id, "Egemen Yusuf Kayra")
        token = self.csrf(f"/created/{tag}")
        queued = self.client.post(
            f"/calibrations/{tag}/sideload", data={"csrf_token": token}
        )
        self.assertEqual(302, queued.status_code)
        self.assertIn(f"/created/{tag}?job=", queued.location)
        with self.app.app_context():
            job = get_db().execute(
                "SELECT operation, status FROM device_jobs WHERE link_id = ?",
                (link.link_id,),
            ).fetchone()
            self.assertEqual("INSTALL_INACTIVE_CONFIGURATION", job["operation"])
            self.assertEqual("PENDING", job["status"])

        token = self.csrf("/dashboard")
        logged_out = self.client.post("/logout", data={"csrf_token": token})
        self.assertEqual(302, logged_out.status_code)
        with self.app.app_context():
            row = get_db().execute(
                "SELECT revoked_at FROM device_links WHERE link_id = ?",
                (link.link_id,),
            ).fetchone()
            self.assertIsNotNone(row["revoked_at"])
            self.assertEqual(
                "EXPIRED",
                get_db().execute(
                    "SELECT status FROM device_jobs WHERE link_id = ?", (link.link_id,)
                ).fetchone()["status"],
            )

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

    def test_session_deadline_is_enforced_and_not_visually_reset(self):
        self.login()
        dashboard = self.client.get("/dashboard")
        self.assertEqual(200, dashboard.status_code)
        with self.client.session_transaction() as browser_session:
            deadline = browser_session["session_expires_at"]
        self.assertIn(
            f'data-session-expires-at="{deadline}"'.encode(), dashboard.data
        )

        with self.client.session_transaction() as browser_session:
            browser_session["session_expires_at"] = 0
        expired = self.client.get("/dashboard")
        self.assertEqual(302, expired.status_code)
        self.assertIn("/login?next=/dashboard", expired.location)
        with self.client.session_transaction() as browser_session:
            self.assertNotIn("authenticated", browser_session)

    def test_diagnostic_bundle_is_authenticated_and_excludes_credentials(self):
        self.login()
        token = self.csrf("/access")
        self.client.post("/access/offline", data={"csrf_token": token})
        response = self.client.get("/diagnostics/cam-bundle.json")
        self.assertEqual(200, response.status_code)
        self.assertIn("attachment", response.headers["Content-Disposition"])
        bundle = json.loads(response.get_data(as_text=True))
        self.assertEqual("startech-cam-diagnostic-v1", bundle["format"])
        self.assertEqual("ok", bundle["database"]["integrity"])
        self.assertIsNone(bundle["linked_device"])
        body = response.get_data(as_text=True)
        self.assertNotIn("school-password", body)
        self.assertNotIn("remote_address", body)

    def test_external_and_backslash_login_redirects_are_rejected(self):
        for target in ("//example.com", "/%5c%5cexample.com", "https://example.com"):
            client = self.app.test_client()
            page = client.get(f"/login?next={target}")
            token = TOKEN.search(page.data).group(1).decode("ascii")
            response = client.post(
                f"/login?next={target}",
                data={
                    "csrf_token": token,
                    "legal_name": "Egemen",
                    "password": "school-password",
                },
            )
            self.assertEqual(302, response.status_code)
            self.assertTrue(response.location.endswith("/access"), target)

    def test_invalid_access_codes_are_rate_limited_separately(self):
        self.login()
        token = self.csrf("/access")
        for _attempt in range(8):
            rejected = self.client.post(
                "/access",
                data={"csrf_token": token, "access_code": "NOTVALID"},
            )
            self.assertEqual(400, rejected.status_code)
        limited = self.client.post(
            "/access",
            data={"csrf_token": token, "access_code": "NOTVALID"},
        )
        self.assertEqual(429, limited.status_code)

    def test_expired_and_revoked_codes_fail_closed(self):
        self.login()
        with self.app.app_context():
            revoked = issue_access_code("YAREN-revoked")
            self.assertTrue(revoke_access_code(revoked, "school-admin"))
            expired = issue_access_code("YAREN-expired")
            get_db().execute(
                "UPDATE access_codes SET expires_at = 0 WHERE device_id = ?",
                ("YAREN-expired",),
            )
            get_db().commit()

        token = self.csrf("/access")
        for code in (revoked, expired):
            response = self.client.post(
                "/access", data={"csrf_token": token, "access_code": code}
            )
            self.assertEqual(400, response.status_code)

    def test_logout_and_security_headers(self):
        login_page = self.client.get("/login")
        self.assertEqual("DENY", login_page.headers["X-Frame-Options"])
        self.assertIn("default-src 'self'", login_page.headers["Content-Security-Policy"])
        self.login()
        token = self.csrf("/dashboard")
        response = self.client.post("/logout", data={"csrf_token": token})
        self.assertEqual(302, response.status_code)
        self.assertTrue(response.location.endswith("/login"))
        protected = self.client.get("/dashboard")
        self.assertEqual(302, protected.status_code)

    def test_administrative_code_cli_issues_revokes_and_prunes(self):
        runner = self.app.test_cli_runner()
        issued = runner.invoke(args=["issue-access-code", "--device", "YAREN-cli"])
        self.assertEqual(0, issued.exit_code, issued.output)
        code = issued.output.strip()
        self.assertRegex(code, r"^[A-Z0-9]{8}$")

        revoked = runner.invoke(
            args=["revoke-access-code", "--code", code, "--actor", "test-admin"]
        )
        self.assertEqual(0, revoked.exit_code, revoked.output)
        self.assertIn("revoked", revoked.output.lower())
        with self.app.app_context():
            get_db().execute("UPDATE access_codes SET expires_at = 0")
            get_db().commit()
        pruned = runner.invoke(args=["prune-security-records", "--retain-days", "0"])
        self.assertEqual(0, pruned.exit_code, pruned.output)
        self.assertIn("access_codes=1", pruned.output)


if __name__ == "__main__":
    unittest.main(verbosity=2)
