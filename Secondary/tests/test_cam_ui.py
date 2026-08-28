"""Interface contract tests for the production CAM screens."""

from __future__ import annotations

import re
import json
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
import zipfile

from startech_cam import create_app
from startech_cam.db import get_db
from startech_cam.repository import create_draft, publish_draft
from startech_cam.security import now_epoch


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

    def create_mac_calibration(self) -> str:
        with self.app.app_context():
            draft_id = create_draft(
                owner="Egemen Yusuf Kayra",
                workflow="MAC",
                name="Release profile",
            )
            return publish_draft(draft_id, "Egemen Yusuf Kayra")

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
        self.assertIn(b"Connect to YAREN for remote configuration", access.data)
        self.assertIn(b"assets/email.png", access.data)
        self.assertIn(b"Skip for now", access.data)
        self.assertIn(b'action="/logout"', access.data)

    def test_dashboard_uses_kerim_actions_and_starts_staged_sac(self):
        self.authenticate()
        dashboard = self.client.get("/dashboard")
        self.assertIn("Kalibrasyon Erişim, Revizyon İnceleme Merkezi".encode(), dashboard.data)
        self.assertIn(b"Create a SAC (Service Assisted Calibration)", dashboard.data)
        self.assertIn(b"Create a MAC (Manual Assisted Calibration)", dashboard.data)
        self.assertIn(b'href="/sac/source"', dashboard.data)
        self.assertIn(b"cam-action--primary", dashboard.data)
        self.assertIn(b'href="/vehicle-release"', dashboard.data)
        self.assertIn(b'href="/vehicle-run"', dashboard.data)
        self.assertIn(b'href="/open-source"', dashboard.data)
        self.assertIn(b"assets/reicon.svg", dashboard.data)
        for icon in (
            b"#ri-settings4",
            b"#ri-edit",
            b"#ri-folder-connect",
            b"#ri-package",
            b"#ri-history",
            b"#ri-bug",
        ):
            self.assertIn(icon, dashboard.data)

        credits = self.client.get("/open-source")
        self.assertEqual(200, credits.status_code)
        self.assertIn(b"Free and open-source software", credits.data)
        self.assertIn(b"Reicon 1.2.0", credits.data)
        self.assertIn(b"MIT", credits.data)
        self.assertIn(b"3awnt", credits.data)
        self.assertIn(b"GPL-3.0", credits.data)
        self.assertNotIn(b"not an active KER\xc4\xb0M dependency", credits.data)
        self.assertNotIn(b"security guarantee", credits.data)
        self.assertIn(b'rel="noopener noreferrer"', credits.data)

    def test_vehicle_run_page_queues_one_real_arda_request_and_uses_the_animation(self):
        self.authenticate()
        link_id = "a" * 32
        device_id = "YAREN-school-car"
        current = now_epoch()
        with self.app.app_context():
            connection = get_db()
            connection.execute(
                """
                INSERT INTO registered_devices(
                    device_id, algorithm, public_key_b64, created_at, created_by
                ) VALUES (?, 'Ed25519', ?, ?, 'test')
                """,
                (device_id, "A" * 43, current),
            )
            connection.execute(
                """
                INSERT INTO device_links(
                    link_id, token_digest, device_id, issued_at, expires_at,
                    activated_at, activated_by, last_seen_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'test', ?)
                """,
                (link_id, "b" * 64, device_id, current, current + 600, current, current),
            )
            connection.commit()
        with self.client.session_transaction() as browser_session:
            browser_session["device_id"] = device_id
            browser_session["device_link_id"] = link_id

        token = self.token("/vehicle-run")
        started = self.client.post(
            "/vehicle-run",
            data={
                "csrf_token": token,
                "confirm_physical_run": "yes",
                "mute_buzzer": "yes",
            },
        )
        self.assertEqual(302, started.status_code)
        self.assertRegex(started.location, r"/vehicle-runs/[0-9a-f]{32}$")
        page = self.client.get(started.location)
        self.assertEqual(200, page.status_code)
        self.assertIn(b"assets/run-received.gif", page.data)
        self.assertIn(b"data-vehicle-run", page.data)
        self.assertIn(b"data-run-log", page.data)
        self.assertIn(b"Cancel vehicle run", page.data)
        with self.app.app_context():
            job = get_db().execute(
                """
                SELECT operation, payload_json, status FROM device_jobs
                WHERE operation = 'START_AUTONOMOUS_RUN'
                """
            ).fetchone()
            self.assertEqual("PENDING", job["status"])
            payload = json.loads(job["payload_json"])
            self.assertEqual("Egemen Yusuf Kayra", payload["operator"])
            self.assertEqual(30, payload["countdown_seconds"])
            self.assertTrue(payload["mute_buzzer"])

        script = self.client.get("/static/cam.js").get_data()
        self.assertIn(b"data-vehicle-run", page.data)
        self.assertIn(b"countdownTemplate", script)
        self.assertIn(b"RUN_HALT_NOCON", script)

    def test_vehicle_release_builds_an_exact_zip_without_claiming_a_test(self):
        self.authenticate()
        tag = self.create_mac_calibration()
        page = self.client.get(f"/vehicle-release?profile={tag}")
        self.assertEqual(200, page.status_code)
        self.assertIn(b"Uncommitted server files are excluded", page.data)
        self.assertIn(b"Installation is a separate step", page.data)
        token = TOKEN.search(page.data).group(1).decode("ascii")
        commit = str(self.app.config["CAM_RELEASE"])
        changed = self.client.post(
            "/vehicle-release",
            data={
                "csrf_token": token,
                "profile": tag,
                "source": "server",
                "expected_commit": "0" * 40,
            },
        )
        self.assertEqual(409, changed.status_code)
        response = self.client.post(
            "/vehicle-release",
            data={
                "csrf_token": token,
                "profile": tag,
                "source": "server",
                "expected_commit": commit,
            },
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual("application/zip", response.mimetype)
        self.assertEqual(commit, response.headers["X-STARTECH-Git-Commit"])
        self.assertEqual(tag, response.headers["X-STARTECH-Profile"])
        with zipfile.ZipFile(BytesIO(response.data)) as archive:
            manifest = archive.read("KERIM_RELEASE/manifest.json")
            self.assertIn(b"PHYSICALLY UNVERIFIED", manifest)
            self.assertIn(commit.encode(), manifest)
        with self.app.app_context():
            event = get_db().execute(
                "SELECT actor, detail_json FROM audit_events "
                "WHERE event_type = 'VEHICLE_RELEASE_DOWNLOADED'"
            ).fetchone()
            self.assertIsNotNone(event)
            self.assertEqual("Egemen Yusuf Kayra", event["actor"])
            self.assertIn(tag, event["detail_json"])

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
        self.assertIn(b"width: min(578px, calc(100% - 48px))", sac_styles.data)
        sac_styles.close()
        for icon in (b"#ri-refresh", b"#ri-car"):
            self.assertIn(icon, source.data)
        self.assertNotIn(b"updatecar.png", source.data)
        reicon = self.client.get("/static/assets/reicon.svg")
        self.assertEqual(200, reicon.status_code)
        self.assertIn(b'id="ri-camera"', reicon.data)
        self.assertIn(b'id="ri-desktop-download"', reicon.data)
        self.assertIn(b'id="ri-copy"', reicon.data)
        reicon.close()

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
        self.assertIn(b"Check the connected car", preflight.data)
        self.assertIn(b"data-workshop-form", preflight.data)
        self.assertIn(b"Start 7-second countdown", preflight.data)
        self.assertIn(b"LIVE MOTOR OUTPUT may start", preflight.data)
        self.assertIn(b"data-workshop-now", preflight.data)
        self.assertIn(b"data-workshop-cancel", preflight.data)
        self.assertIn(b"PHYSICALLY UNVERIFIED", preflight.data)
        script = self.client.get("/static/cam.js")
        script_data = script.get_data()
        script.close()
        self.assertIn(b"HTMLFormElement.prototype.submit.call(form)", script_data)
        self.assertIn(b"window.clearInterval", script_data)
        self.assertIn(b"const workshopDelaySeconds = 7", script_data)

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

    def test_mac_workflow_renders_the_complete_turkish_copy(self):
        self.authenticate()
        token = self.token("/dashboard")
        response = self.client.post(
            "/language",
            data={
                "csrf_token": token,
                "language": "tr",
                "next": "/new/MAC",
            },
            follow_redirects=True,
        )
        self.assertEqual(200, response.status_code)
        self.assertIn("Manuel Asistanlı Kalibrasyon - Arayüz v0.1".encode(), response.data)
        self.assertIn("Kalibrasyon için bir isim girin".encode(), response.data)
        self.assertIn("Birleşik v2 JSON yükle".encode(), response.data)

        token = TOKEN.search(response.data).group(1).decode("ascii")
        started = self.client.post(
            "/new/MAC",
            data={
                "csrf_token": token,
                "name": "Türkçe MAC",
                "source": "DEFAULT",
            },
        )
        self.assertEqual(302, started.status_code)
        match = re.search(r"/mac/([0-9a-f]{32})/overview$", started.location)
        self.assertIsNotNone(match)
        draft_id = match.group(1)

        expected_copy = {
            "overview": ("Genel bakış", "Kalibrasyon kimliği ve sahibi."),
            "camera": ("Kamera", "v1 kalibrasyon sözleşmesinde kullanılan fiziksel kamera değerleri."),
            "perspective": ("Perspektif", "Ölçülen çözünürlük [genişlik, yükseklik]"),
            "recognition": ("Tespit", "Şerit tespit eşikleri ve aydınlatma profilleri."),
            "colors": ("Renkler", "Tespit edilen nesnelerin HSV aralıkları"),
            "motors": ("Motorlar", "FİZİKSEL OLARAK DOĞRULANMADI"),
            "steering": ("Dönüş", "PD/PID denetleyici değerleri."),
            "speed": ("Hız", "asgari, hedef ve azami PWM komut yüzdeleri"),
            "event-response": ("Olay tepkisi", "Olay yönetiminde kullanılan yakın bölge eşiği."),
        }
        for section, snippets in expected_copy.items():
            page = self.client.get(f"/mac/{draft_id}/{section}")
            self.assertEqual(200, page.status_code, section)
            for snippet in snippets:
                self.assertIn(snippet.encode(), page.data, section)

        variables = self.client.get(f"/mac/{draft_id}/variables")
        self.assertEqual(200, variables.status_code)
        self.assertIn("Değişken yönetimi".encode(), variables.data)
        self.assertIn("Birleşik v2 JSON".encode(), variables.data)
        self.assertIn("doğrudan düzenleyin".encode(), variables.data)

        summary = self.client.get(f"/mac/{draft_id}/summary")
        self.assertEqual(200, summary.status_code)
        self.assertIn("Kalibrasyon oluşturulmak üzere".encode(), summary.data)
        self.assertIn("Doğrulanmış birleşik JSON".encode(), summary.data)

        token = TOKEN.search(summary.data).group(1).decode("ascii")
        created = self.client.post(
            f"/mac/{draft_id}/publish",
            data={"csrf_token": token},
            follow_redirects=True,
        )
        self.assertEqual(200, created.status_code)
        self.assertIn("Oluşturuldu!".encode(), created.data)
        self.assertIn("MAC kalibrasyonu oluşturuldu".encode(), created.data)

    def test_language_switch_is_real_and_survives_login(self):
        login = self.client.get("/login")
        token = TOKEN.search(login.data).group(1).decode("ascii")
        switched = self.client.post(
            "/language",
            data={
                "csrf_token": token,
                "language": "tr",
                "next": "/login",
            },
            follow_redirects=True,
        )
        self.assertEqual(200, switched.status_code)
        self.assertIn(b'<html lang="tr">', switched.data)
        self.assertIn("STARTECH aracınızı kalibre edin".encode(), switched.data)
        self.assertIn("Yasal isminiz".encode(), switched.data)

        token = TOKEN.search(switched.data).group(1).decode("ascii")
        response = self.client.post(
            "/login",
            data={
                "csrf_token": token,
                "legal_name": "Egemen Yusuf Kayra",
                "password": "school-password",
            },
        )
        self.assertEqual(302, response.status_code)
        dashboard = self.client.get("/dashboard")
        self.assertIn(b'<html lang="tr">', dashboard.data)
        self.assertIn("Başlamak için bir seçenek seçin".encode(), dashboard.data)
        self.assertIn("Çıkış yap".encode(), dashboard.data)

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
        self.assertIn("--cam-control-radius: 9px", css)
        self.assertIn("inset 0 2px 11.8px", css)
        self.assertIn("0 0 7.6px", css)
        self.assertIn(".primary-button::after", css)
        self.assertIn("font-size: 17px", css)
        self.assertIn("font-size: 14px", css)
        self.assertIn(".reicon", css)

        javascript_response = self.client.get("/static/cam.js")
        javascript = javascript_response.get_data(as_text=True)
        javascript_response.close()
        self.assertNotIn("sessionStorage", javascript)
        self.assertNotIn("data-session-clock", javascript)


if __name__ == "__main__":
    unittest.main(verbosity=2)
