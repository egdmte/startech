"""Interface contract tests for the production CAM screens."""

from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

from startech_cam import create_app


TOKEN = re.compile(rb'name="csrf_token" value="([^"]+)"')
DRAFT_LOCATION = re.compile(r"/sac/([0-9a-f]{32})/preflight$")
ASSET_VERSION = re.compile(rb"/static/cam\.css\?v=([0-9a-f]{12})")


class CamInterfaceTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.app = create_app(
            {
                "TESTING": True,
                "DATABASE": str(Path(self.temporary.name) / "cam.sqlite3"),
                "SECRET_KEY": "ui-secret-that-is-long-enough-for-tests",
                "CAM_PASSWORD": "school-password",
                "CAM_PASSWORD_HASH": "",
                "SESSION_COOKIE_SECURE": False,
            }
        )
        self.client = self.app.test_client()

    def tearDown(self):
        self.temporary.cleanup()

    def token(self, path: str) -> str:
        page = self.client.get(path)
        self.assertEqual(200, page.status_code, path)
        match = TOKEN.search(page.data)
        self.assertIsNotNone(match, path)
        return match.group(1).decode("ascii")

    def authenticate(self):
        token = self.token("/login")
        response = self.client.post(
            "/login",
            data={
                "csrf_token": token,
                "legal_name": "Egemen Yusuf Kayra",
                "password": "school-password",
            },
        )
        self.assertEqual(302, response.status_code)
        token = self.token("/access")
        response = self.client.post(
            "/access/offline", data={"csrf_token": token}
        )
        self.assertEqual(302, response.status_code)

    def start_sac(self) -> str:
        token = self.token("/sac/source")
        response = self.client.post(
            "/sac/source",
            data={"csrf_token": token, "source": "DEFAULT"},
        )
        self.assertEqual(302, response.status_code)
        token = self.token("/sac/name")
        response = self.client.post(
            "/sac/name",
            data={"csrf_token": token, "name": "UI contract"},
        )
        self.assertEqual(302, response.status_code)
        match = DRAFT_LOCATION.search(response.location)
        self.assertIsNotNone(match)
        draft_id = match.group(1)
        preflight = self.client.get(response.location)
        self.assertEqual(200, preflight.status_code)
        self.assertIn(b"cam-frame--preflight", preflight.data)
        token_match = TOKEN.search(preflight.data)
        self.assertIsNotNone(token_match)
        token = token_match.group(1).decode("ascii")
        response = self.client.post(
            response.location, data={"csrf_token": token}
        )
        self.assertEqual(302, response.status_code)
        return draft_id

    def test_login_and_access_keep_the_prototype_identity(self):
        login = self.client.get("/login")
        self.assertIn(b'class="login-shell"', login.data)
        self.assertIn(b"Calibrate your STARTECH instance", login.data)
        self.assertIn(b'name="legal_name"', login.data)
        self.assertIn(b'name="password"', login.data)
        self.assertIn(b"family=Inter:opsz,wght@14..32,400..700", login.data)
        version = ASSET_VERSION.search(login.data)
        self.assertIsNotNone(version)
        self.assertIn(
            b'/static/cam.js?v=' + version.group(1),
            login.data,
        )

        token = TOKEN.search(login.data).group(1).decode("ascii")
        self.client.post(
            "/login",
            data={
                "csrf_token": token,
                "legal_name": "Egemen Yusuf Kayra",
                "password": "school-password",
            },
        )
        access = self.client.get("/access")
        self.assertIn(b'class="access-shell"', access.data)
        self.assertIn(b"Egemen Yusuf Kayra", access.data)
        self.assertIn(b"Prove that you possess the code", access.data)
        self.assertIn(b"assets/email.png", access.data)
        self.assertIn(b'action="/access/offline"', access.data)

    def test_dashboard_uses_cam_actions_and_starts_staged_sac(self):
        self.authenticate()
        dashboard = self.client.get("/dashboard")
        self.assertIn(b"Calibration Arrangement and Management Tool", dashboard.data)
        self.assertIn(b"Create a SAC (Service Assisted Calibration)", dashboard.data)
        self.assertIn(b"Create a MAC (Manual Assisted Calibration)", dashboard.data)
        self.assertIn(b'href="/sac/source"', dashboard.data)
        self.assertIn(b"cam-action--primary", dashboard.data)

    def test_sac_stage_flow_preserves_assets_hotspots_and_saved_state(self):
        self.authenticate()
        source = self.client.get("/sac/source")
        version = ASSET_VERSION.search(source.data)
        self.assertIsNotNone(version)
        self.assertIn(
            b'/static/sac.css?v=' + version.group(1),
            source.data,
        )
        sac_styles = self.client.get("/static/sac.css")
        self.assertEqual(200, sac_styles.status_code)
        self.assertIn(b"grid-template-rows: minmax(0, 1fr) auto", sac_styles.data)
        self.assertIn(b"overflow-y: auto", sac_styles.data)
        self.assertIn(
            b".cam-frame--preflight .cam-workflow-footer",
            sac_styles.data,
        )
        sac_styles.close()
        for asset in (b"updatecar.png", b"default.png"):
            self.assertIn(asset, source.data)

        draft_id = self.start_sac()
        components_path = f"/sac/{draft_id}/components"
        components = self.client.get(components_path)
        self.assertIn(b"assets/car.png", components.data)
        self.assertEqual(5, components.data.count(b"car-hotspot--"))
        self.assertIn(b"Review every section first", components.data)

        camera_path = f"/sac/{draft_id}/camera"
        camera = self.client.get(camera_path)
        self.assertIn(b"sac-editor-panel--camera", camera.data)
        self.assertIn(b'name="sac_niyeti.kamera.yon_derecesi"', camera.data)
        token = TOKEN.search(camera.data).group(1).decode("ascii")
        response = self.client.post(
            camera_path,
            data={
                "csrf_token": token,
                "sac_niyeti.kamera.yon_derecesi": "0",
                "sac_niyeti.kamera.yakalama_profili": "640x480",
                "sac_niyeti.kamera.tanima_hassasiyeti": "conservative",
            },
        )
        self.assertEqual(302, response.status_code)
        updated = self.client.get(components_path)
        self.assertRegex(
            updated.data,
            rb"car-hotspot--camera[^\"]*is-saved",
        )

    def test_sac_summary_and_created_screens_have_the_finish_layout(self):
        self.authenticate()
        draft_id = self.start_sac()
        summary = self.client.get(f"/sac/{draft_id}/summary")
        self.assertIn(b"finish-shell", summary.data)
        self.assertIn(b"Calibration is about to be created", summary.data)
        self.assertIn(b"Review required", summary.data)

    def test_sac_preflight_exposes_real_checks_and_a_cancelable_countdown(self):
        self.authenticate()
        draft_id = self.start_sac()
        preflight = self.client.get(f"/sac/{draft_id}/preflight")
        self.assertIn(b"Check the linked car for real", preflight.data)
        self.assertIn(b"data-workshop-form", preflight.data)
        self.assertIn(b"Start 5-second countdown", preflight.data)
        self.assertIn(b"data-workshop-now", preflight.data)
        self.assertIn(b"data-workshop-cancel", preflight.data)
        self.assertIn(b"NOT RUN / NOT OBSERVED", preflight.data)
        script = self.client.get("/static/cam.js")
        self.assertIn(b"HTMLFormElement.prototype.submit.call(form)", script.data)
        self.assertIn(b"window.clearInterval", script.data)

    def test_mac_editor_routes_remain_available(self):
        self.authenticate()
        token = self.token("/new/MAC")
        response = self.client.post(
            "/new/MAC",
            data={
                "csrf_token": token,
                "name": "MAC UI contract",
                "source": "DEFAULT",
            },
        )
        self.assertEqual(302, response.status_code)
        overview = self.client.get(response.location)
        self.assertIn(b"Manual Assisted Calibration", overview.data)
        self.assertIn(b"Variable manager", overview.data)
        self.assertIn(b"Review and publish", overview.data)

    def test_shared_css_and_javascript_keep_the_design_contract(self):
        css_response = self.client.get("/static/cam.css")
        css = css_response.get_data(as_text=True).lower()
        css_response.close()
        self.assertIn("--cam-primary-top: #055cff", css)
        self.assertIn("--cam-primary-bottom: #5d7dfd", css)
        self.assertIn(
            "linear-gradient(180deg, var(--cam-primary-top), var(--cam-primary-bottom))",
            css,
        )
        self.assertIn("inset", css)
        self.assertIn("1.2px", css)
        self.assertIn("font-size: 17px", css)
        self.assertIn("font-size: 14px", css)

        javascript_response = self.client.get("/static/cam.js")
        javascript = javascript_response.get_data(as_text=True)
        javascript_response.close()
        self.assertNotIn("sessionStorage", javascript)
        self.assertIn("data-session-clock", javascript)


if __name__ == "__main__":
    unittest.main(verbosity=2)
