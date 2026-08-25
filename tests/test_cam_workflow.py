"""End-to-end configuration behaviour tests for production CAM."""

from __future__ import annotations

import base64
import hashlib
import json
import re
import tempfile
import unittest
from pathlib import Path

from startech.configuration.combined import combined_config_errors
from startech.configuration.validation import kisa_ozet_hesapla
from startech_cam import create_app
from startech_cam.db import get_db
from startech_cam.device_link import claim_next_device_job, complete_device_job
from startech_cam.repository import DEFAULT_DOCUMENT, get_draft
from startech_cam.security import now_epoch


TOKEN = re.compile(rb'name="csrf_token" value="([^"]+)"')
DRAFT_LOCATION = re.compile(r"/(sac|mac)/([0-9a-f]{32})/([^/]+)$")


class CamWorkflowTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.app = create_app(
            {
                "TESTING": True,
                "DATABASE": str(Path(self.temporary.name) / "cam.sqlite3"),
                "SECRET_KEY": "workflow-secret-that-is-long-enough-for-tests",
                "CAM_PASSWORD": "school-password",
                "CAM_PASSWORD_HASH": "",
                "SESSION_COOKIE_SECURE": False,
            }
        )
        self.client = self.app.test_client()
        response = self.client.get("/login")
        token = TOKEN.search(response.data).group(1).decode("ascii")
        self.client.post(
            "/login",
            data={"csrf_token": token, "legal_name": "Egemen Yusuf Kayra", "password": "school-password"},
        )
        response = self.client.get("/access")
        token = TOKEN.search(response.data).group(1).decode("ascii")
        self.client.post("/access/offline", data={"csrf_token": token})

    def tearDown(self):
        self.temporary.cleanup()

    def page_token(self, path: str) -> str:
        response = self.client.get(path)
        self.assertEqual(200, response.status_code, path)
        match = TOKEN.search(response.data)
        self.assertIsNotNone(match, path)
        return match.group(1).decode("ascii")

    def post_section(self, path: str, values: dict[str, object]):
        token = self.page_token(path)
        data = {"csrf_token": token, **values}
        response = self.client.post(path, data=data)
        self.assertEqual(302, response.status_code, response.get_data(as_text=True))
        return response

    def start_sac(self, name: str = "School bench") -> str:
        token = self.page_token("/sac/source")
        source = self.client.post(
            "/sac/source",
            data={"csrf_token": token, "source": "DEFAULT"},
        )
        self.assertEqual(302, source.status_code)
        self.assertTrue(source.location.endswith("/sac/name"))

        token = self.page_token("/sac/name")
        named = self.client.post(
            "/sac/name",
            data={"csrf_token": token, "name": name},
        )
        self.assertEqual(302, named.status_code)
        match = DRAFT_LOCATION.search(named.location)
        self.assertIsNotNone(match)
        draft_id = match.group(2)
        self.assertTrue(named.location.endswith(f"/sac/{draft_id}/preflight"))

        token = self.page_token(named.location)
        preflight = self.client.post(
            named.location,
            data={"csrf_token": token},
        )
        self.assertEqual(302, preflight.status_code)
        self.assertTrue(preflight.location.endswith(f"/sac/{draft_id}/components"))
        return draft_id

    def connect_device(self) -> tuple[str, str]:
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
        return link_id, device_id

    def report_active_configuration(self, link_id: str, device_id: str) -> None:
        document = DEFAULT_DOCUMENT.read_text(encoding="utf-8")
        current = now_epoch()
        with self.app.app_context():
            get_db().execute(
                """
                INSERT INTO device_snapshots(
                    link_id, device_id, captured_at, received_at, payload_json
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (link_id, device_id, current, current, document),
            )
            get_db().commit()

    def test_live_camera_editor_creates_and_queues_one_inactive_profile(self):
        link_id, device_id = self.connect_device()
        self.report_active_configuration(link_id, device_id)
        start = self.client.get("/camera-calibration")
        token = TOKEN.search(start.data).group(1).decode("ascii")
        created_draft = self.client.post(
            "/camera-calibration",
            data={"csrf_token": token, "name": "Real workshop frame"},
        )
        self.assertEqual(302, created_draft.status_code)
        draft_id = created_draft.location.rsplit("/", 1)[-1]

        token = self.page_token(created_draft.location)
        queued = self.client.post(
            f"/camera-calibration/{draft_id}/capture",
            data={"csrf_token": token},
        )
        self.assertEqual(302, queued.status_code)
        job_id = queued.location.rsplit("job=", 1)[1]
        jpeg = b"\xff\xd8real-camera-pixels\xff\xd9"
        with self.app.app_context():
            claimed = claim_next_device_job(link_id, device_id)
            self.assertEqual("CAPTURE_CALIBRATION_FRAME", claimed["operation"])
            self.assertTrue(
                complete_device_job(
                    link_id,
                    device_id,
                    job_id,
                    accepted=True,
                    receipt={
                        "format": "jpeg",
                        "width": 840,
                        "height": 630,
                        "source": "usb:0",
                        "frame_id": 7,
                        "captured_at": 123.5,
                        "sha256": hashlib.sha256(jpeg).hexdigest(),
                        "image_b64": base64.b64encode(jpeg).decode("ascii"),
                    },
                )
            )

        editor = self.client.get(queued.location)
        self.assertEqual(200, editor.status_code)
        self.assertIn(b"usb:0", editor.data)
        self.assertIn(b"data-perspective-canvas", editor.data)
        token = TOKEN.search(editor.data).group(1).decode("ascii")
        saved = self.client.post(
            queued.location,
            data={
                "csrf_token": token,
                "job_id": job_id,
                "points_json": "[[199,410],[633,413],[0,630],[840,630]]",
                "hsv_target": "lane-normal",
                "lower_h": "0",
                "lower_s": "0",
                "lower_v": "95",
                "upper_h": "180",
                "upper_s": "110",
                "upper_v": "255",
            },
        )
        self.assertEqual(302, saved.status_code, saved.get_data(as_text=True))
        self.assertRegex(saved.location, r"/created/[0-9a-f]{6}\?job=[0-9a-f]{32}$")
        tag = saved.location.split("/created/", 1)[1].split("?", 1)[0]
        with self.app.app_context():
            row = get_db().execute(
                "SELECT payload_json FROM calibrations WHERE tag = ?", (tag,)
            ).fetchone()
            document = json.loads(row["payload_json"])
            self.assertIn(hashlib.sha256(jpeg).hexdigest(), document["kalibrasyon"]["damga"]["not"])
            self.assertEqual(
                [0, 0, 95],
                document["kalibrasyon"]["serit"]["beyaz_profiller"]["normal"]["alt"],
            )
            self.assertFalse(document["oturum_kaniti"]["fiziksel_dogrulama_yapildi"])
            install = get_db().execute(
                "SELECT status FROM device_jobs WHERE operation = 'INSTALL_INACTIVE_CONFIGURATION'"
            ).fetchone()
            self.assertEqual("PENDING", install["status"])

    def test_sac_queues_one_bounded_real_command_and_records_human_observation(self):
        draft_id = self.start_sac("Physical workshop")
        link_id, device_id = self.connect_device()
        path = f"/sac/{draft_id}/preflight"
        page = self.client.get(path)
        self.assertIn(b"Bounded workshop motor check", page.data)
        self.assertIn(b"Egemen Yusuf Kayra", page.data)
        token = TOKEN.search(page.data).group(1).decode("ascii")
        queued = self.client.post(
            f"/sac/{draft_id}/workshop",
            data={
                "csrf_token": token,
                "left_percent": "10",
                "right_percent": "-8",
                "duration_seconds": "0.25",
                "inspection": ["wheels-secured", "motors-mounted", "path-clear"],
            },
        )
        self.assertEqual(302, queued.status_code)
        job_id = queued.location.rsplit("job=", 1)[1]
        pending = self.client.get(f"{path}?job={job_id}")
        self.assertIn(b"LIVE MOTOR OUTPUT IS QUEUED OR MAY BE ACTIVE", pending.data)
        with self.app.app_context():
            row = get_db().execute(
                "SELECT operation, payload_json, expires_at - created_at AS lifetime FROM device_jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
            self.assertEqual("RUN_BOUNDED_WORKSHOP_COMMAND", row["operation"])
            self.assertLessEqual(row["lifetime"], 20)
            payload = json.loads(row["payload_json"])
            self.assertEqual("Egemen Yusuf Kayra", payload["operator"])
            self.assertEqual(draft_id, payload["draft_id"])
            claimed = claim_next_device_job(link_id, device_id)
            self.assertEqual(job_id, claimed["job_id"])
            complete_device_job(
                link_id,
                device_id,
                job_id,
                accepted=True,
                receipt={
                    "cam_issued_at": payload["issued_at"],
                    "applied_left": 0.1,
                    "applied_right": -0.08,
                    "duration_seconds": 0.25,
                    "stop_requested": True,
                    "physical_motion_observed": False,
                },
            )

        completed = self.client.get(f"{path}?job={job_id}")
        self.assertIn(b"This receipt proves software execution", completed.data)
        token = TOKEN.search(completed.data).group(1).decode("ascii")
        observed = self.client.post(
            f"/sac/{draft_id}/workshop/{job_id}/observe",
            data={"csrf_token": token, "observation": "expected"},
        )
        self.assertEqual(302, observed.status_code)
        with self.app.app_context():
            document, touched, workflow = get_draft(
                draft_id, "Egemen Yusuf Kayra"
            )
        self.assertEqual("SAC", workflow)
        self.assertIn("hardware-evidence", touched)
        self.assertTrue(document["oturum_kaniti"]["fiziksel_dogrulama_yapildi"])
        self.assertTrue(document["oturum_kaniti"]["fiziksel_hizalama_dogrulandi"])

    def test_sac_refuses_motor_job_without_all_physical_conditions(self):
        draft_id = self.start_sac("Rejected workshop")
        self.connect_device()
        path = f"/sac/{draft_id}/preflight"
        token = self.page_token(path)
        rejected = self.client.post(
            f"/sac/{draft_id}/workshop",
            data={
                "csrf_token": token,
                "left_percent": "10",
                "right_percent": "10",
                "duration_seconds": "0.25",
                "inspection": ["wheels-secured", "path-clear"],
            },
        )
        self.assertEqual(302, rejected.status_code)
        with self.app.app_context():
            count = get_db().execute(
                "SELECT COUNT(*) FROM device_jobs WHERE operation = 'RUN_BOUNDED_WORKSHOP_COMMAND'"
            ).fetchone()[0]
        self.assertEqual(0, count)

    def test_sac_persists_each_step_then_publishes_downloadable_v2(self):
        draft_id = self.start_sac()
        base = f"/sac/{draft_id}"

        self.post_section(
            f"{base}/camera",
            {
                "sac_niyeti.kamera.yon_derecesi": "180",
                "sac_niyeti.kamera.yakalama_profili": "640x480",
                "sac_niyeti.kamera.tanima_hassasiyeti": "conservative",
            },
        )
        self.post_section(
            f"{base}/power",
            {
                "sac_niyeti.guc.minimum_hiz_yuzde": "30",
                "sac_niyeti.guc.maksimum_hiz_yuzde": "60",
            },
        )
        self.post_section(
            f"{base}/compute",
            {
                "sac_niyeti.hesaplama.baslangic_onlemi": "individual-buttons",
                "sac_niyeti.hesaplama.servis_durumu": "on",
                "sac_niyeti.hesaplama.m3th_sikiligi": "full",
                "sac_niyeti.hesaplama.etkin_moduller": ["yaren", "arda", "kasim", "m3th"],
            },
        )
        self.post_section(
            f"{base}/drive",
            {
                "sac_niyeti.surus.komut_kaybi_eylemi": "disarm-wait",
                "sac_niyeti.surus.surucu_cikis_modu": "off",
                "sac_niyeti.surus.direksiyon_merkez_yuzde": "0",
                "sac_niyeti.surus.direksiyon_azami_hareket_yuzde": "40",
            },
        )
        response = self.post_section(
            f"{base}/wheel",
            {
                "sac_niyeti.tekerlek.sol_duzeltme_yuzde": "0",
                "sac_niyeti.tekerlek.sag_duzeltme_yuzde": "0",
                "sac_niyeti.tekerlek.sol_yon": "normal",
                "sac_niyeti.tekerlek.sag_yon": "normal",
            },
        )
        self.assertTrue(response.location.endswith(f"/sac/{draft_id}/components"))

        summary_path = f"/sac/{draft_id}/summary"
        summary = self.client.get(summary_path)
        self.assertIn(b"Create", summary.data)
        self.assertIn(b"camera, power, compute, drive, wheel", summary.data)
        token = TOKEN.search(summary.data).group(1).decode("ascii")
        created = self.client.post(
            f"/sac/{draft_id}/publish",
            data={"csrf_token": token},
        )
        self.assertEqual(302, created.status_code)
        tag = created.location.rsplit("/", 1)[-1]

        downloaded = self.client.get(f"/calibrations/{tag}/download")
        self.assertEqual(200, downloaded.status_code)
        self.assertIn("attachment", downloaded.headers["Content-Disposition"])
        document = json.loads(downloaded.get_data(as_text=True))
        self.assertEqual([], combined_config_errors(document))
        self.assertEqual(30, document["ayarlar"]["hiz"]["min"])
        self.assertEqual(60, document["ayarlar"]["hiz"]["max"])
        self.assertEqual(tag, document["profil"]["kimlik"])

        created_page = self.client.get(created.location)
        token = TOKEN.search(created_page.data).group(1).decode("ascii")
        mac = self.client.post(
            f"/calibrations/{tag}/edit-mac",
            data={"csrf_token": token},
        )
        self.assertEqual(302, mac.status_code)
        self.assertIn("/mac/", mac.location)
        self.assertTrue(mac.location.endswith("/overview"))
        mac_draft_id = DRAFT_LOCATION.search(mac.location).group(2)
        self.post_section(
            f"/mac/{mac_draft_id}/motors",
            {
                "kalibrasyon.motor.olculdu": "null",
                "kalibrasyon.motor.sol_trim_dusuk": "0.98",
                "kalibrasyon.motor.sol_trim_yuksek": "1.0",
                "kalibrasyon.motor.sag_trim_dusuk": "1.0",
                "kalibrasyon.motor.sag_trim_yuksek": "1.0",
                "kalibrasyon.motor.olu_bolge_min_pwm": "30",
                "kalibrasyon.motor.olu_bolge_yuzde": "20",
            },
        )
        with self.app.app_context():
            mac_document, touched, workflow = get_draft(
                mac_draft_id, "Egemen Yusuf Kayra"
            )
        self.assertEqual("MAC", workflow)
        self.assertIn("motors", touched)
        self.assertIsNotNone(mac_document["sac_niyeti"])
        self.assertEqual("CAM MAC v0.1", mac_document["kalibrasyon"]["damga"]["olusturan"])
        self.assertEqual(
            kisa_ozet_hesapla(mac_document["kalibrasyon"]),
            mac_document["kalibrasyon"]["damga"]["ozet"],
        )
        summary_path = f"/mac/{mac_draft_id}/summary"
        token = self.page_token(summary_path)
        mac_created = self.client.post(
            f"/mac/{mac_draft_id}/publish", data={"csrf_token": token}
        )
        self.assertEqual(302, mac_created.status_code)
        mac_tag = mac_created.location.rsplit("/", 1)[-1]
        with self.app.app_context():
            lineage = get_db().execute(
                "SELECT parent_tag FROM calibrations WHERE tag = ?", (mac_tag,)
            ).fetchone()
        self.assertEqual(tag, lineage["parent_tag"])

    def test_sac_creation_is_blocked_until_every_section_is_reviewed(self):
        draft_id = self.start_sac("Incomplete")
        summary_path = f"/sac/{draft_id}/summary"
        summary = self.client.get(summary_path)
        self.assertIn(b"Review required", summary.data)
        self.assertIn(b"camera, power, compute, drive, wheel", summary.data)
        self.assertRegex(summary.data, rb"<button[^>]+disabled[^>]*>Create</button>")

        token = TOKEN.search(summary.data).group(1).decode("ascii")
        rejected = self.client.post(
            f"/sac/{draft_id}/publish", data={"csrf_token": token}
        )
        self.assertEqual(302, rejected.status_code)
        self.assertTrue(rejected.location.endswith(summary_path))
        with self.app.app_context():
            self.assertEqual(
                0, get_db().execute("SELECT COUNT(*) FROM calibrations").fetchone()[0]
            )
            self.assertEqual(
                1, get_db().execute("SELECT COUNT(*) FROM drafts").fetchone()[0]
            )

    def test_mac_uses_the_shared_summary_without_requiring_every_section(self):
        token = self.page_token("/new/MAC")
        response = self.client.post(
            "/new/MAC",
            data={"csrf_token": token, "name": "Selective MAC", "source": "DEFAULT"},
        )
        draft_id = DRAFT_LOCATION.search(response.location).group(2)
        summary_path = f"/mac/{draft_id}/summary"
        summary = self.client.get(summary_path)
        self.assertNotIn(b"Review required", summary.data)
        self.assertNotRegex(summary.data, rb"<button[^>]+disabled[^>]*>Create</button>")
        token = TOKEN.search(summary.data).group(1).decode("ascii")
        created = self.client.post(
            f"/mac/{draft_id}/publish", data={"csrf_token": token}
        )
        self.assertEqual(302, created.status_code)
        self.assertIn("/created/", created.location)

    def test_drafts_are_isolated_by_legal_name(self):
        token = self.page_token("/new/MAC")
        response = self.client.post(
            "/new/MAC",
            data={"csrf_token": token, "name": "Owner only", "source": "DEFAULT"},
        )
        draft_id = DRAFT_LOCATION.search(response.location).group(2)

        second = self.app.test_client()
        page = second.get("/login")
        token = TOKEN.search(page.data).group(1).decode("ascii")
        second.post(
            "/login",
            data={"csrf_token": token, "legal_name": "T", "password": "school-password"},
        )
        page = second.get("/access")
        token = TOKEN.search(page.data).group(1).decode("ascii")
        second.post("/access/offline", data={"csrf_token": token})
        unavailable = second.get(f"/mac/{draft_id}/overview")
        self.assertEqual(404, unavailable.status_code)

    def test_variable_manager_rejects_invalid_document_without_replacing_draft(self):
        token = self.page_token("/new/MAC")
        response = self.client.post(
            "/new/MAC",
            data={"csrf_token": token, "name": "Manual", "source": "DEFAULT"},
        )
        draft_id = DRAFT_LOCATION.search(response.location).group(2)
        path = f"/mac/{draft_id}/variables"
        token = self.page_token(path)
        rejected = self.client.post(
            path,
            data={"csrf_token": token, "document_json": '{"sema_surumu": 2, "unknown": true}'},
        )
        self.assertEqual(400, rejected.status_code)
        current = self.client.get(path)
        self.assertIn(b'&#34;profil&#34;', current.data)
        self.assertNotIn(b'&#34;unknown&#34;: true', current.data)

        for invalid in (
            '{"sema_surumu": 2, "sema_surumu": 2}',
            '{"sema_surumu": NaN}',
        ):
            token = self.page_token(path)
            rejected = self.client.post(
                path,
                data={"csrf_token": token, "document_json": invalid},
            )
            self.assertEqual(400, rejected.status_code)


if __name__ == "__main__":
    unittest.main(verbosity=2)
