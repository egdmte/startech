"""Integration tests for registered YAREN device authentication."""

from __future__ import annotations

import base64
import json
import tempfile
import unittest
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from startech_cam import create_app
from startech_cam.db import get_db
from startech_cam.device_security import (
    ACCESS_CODE_PATH,
    canonical_request,
    disable_device,
    register_device,
)
from startech_cam.device_link import queue_device_job
from startech_cam.repository import DEFAULT_DOCUMENT
from startech_cam.security import consume_access_code_grant
from startech.configuration.profiles import ProfileStore
from startech.configuration.validation import kisa_ozet_hesapla


def b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def json_bytes(payload: dict[str, object]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


class CamDeviceApiTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.app = create_app(
            {
                "TESTING": True,
                "DATABASE": str(Path(self.temporary.name) / "cam.sqlite3"),
                "SECRET_KEY": "device-api-secret-that-is-long-enough-for-tests",
                "CAM_PASSWORD": "school-password",
                "CAM_PASSWORD_HASH": "",
                "SESSION_COOKIE_SECURE": False,
                "CAM_DEVICE_REQUEST_LIMIT": 20,
            }
        )
        self.client = self.app.test_client()
        self.device_id = "YAREN-school-car"
        self.private_key = Ed25519PrivateKey.generate()
        public_bytes = self.private_key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )
        with self.app.app_context():
            register_device(
                self.device_id, b64url(public_bytes), actor="test-admin"
            )

    def challenge(self, device_id: str | None = None):
        body = json_bytes({"device_id": device_id or self.device_id})
        return self.client.post(
            "/api/device/v1/challenge", data=body, content_type="application/json"
        )

    def signed_access(
        self,
        challenge: str,
        *,
        private_key: Ed25519PrivateKey | None = None,
        device_id: str | None = None,
        body: bytes | None = None,
        signature: str | None = None,
    ):
        selected_device = device_id or self.device_id
        request_body = body or json_bytes(
            {"challenge": challenge, "device_id": selected_device}
        )
        if signature is None:
            signed = canonical_request(
                "POST", ACCESS_CODE_PATH, selected_device, challenge, request_body
            )
            signature = b64url((private_key or self.private_key).sign(signed))
        return self.client.post(
            ACCESS_CODE_PATH,
            data=request_body,
            content_type="application/json",
            headers={"X-STARTECH-Signature": signature},
        )

    def link_post(self, path: str, payload: dict[str, object], token: str):
        return self.client.post(
            path,
            data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
            content_type="application/json",
            headers={"Authorization": f"Bearer {token}"},
        )

    def test_registered_device_receives_one_single_use_code(self):
        challenge_response = self.challenge()
        self.assertEqual(200, challenge_response.status_code)
        challenge = challenge_response.get_json()["challenge"]
        accepted = self.signed_access(challenge)
        self.assertEqual(200, accepted.status_code, accepted.get_data(as_text=True))
        payload = accepted.get_json()
        self.assertRegex(payload["access_code"], r"^[A-Z0-9]{8}$")
        self.assertEqual(self.device_id, payload["device_id"])
        self.assertTrue(payload["single_use"])
        self.assertRegex(payload["link_id"], r"^[0-9a-f]{32}$")
        self.assertGreaterEqual(len(payload["link_token"]), 32)
        with self.app.app_context():
            self.assertEqual(
                1, get_db().execute("SELECT COUNT(*) FROM access_codes").fetchone()[0]
            )
            stored = get_db().execute(
                "SELECT token_digest FROM device_links WHERE link_id = ?",
                (payload["link_id"],),
            ).fetchone()["token_digest"]
            self.assertNotEqual(payload["link_token"], stored)

        replay = self.signed_access(challenge)
        self.assertEqual(401, replay.status_code)
        with self.app.app_context():
            self.assertEqual(
                1, get_db().execute("SELECT COUNT(*) FROM access_codes").fetchone()[0]
            )

    def test_code_activates_closed_configuration_link_and_close_revokes_it(self):
        challenge = self.challenge().get_json()["challenge"]
        issued = self.signed_access(challenge).get_json()
        base = {"device_id": self.device_id, "link_id": issued["link_id"]}
        pending = self.link_post(
            "/api/device/v1/link/poll", base, issued["link_token"]
        )
        self.assertEqual({"state": "PENDING", "job": None}, pending.get_json())

        with self.app.app_context():
            grant = consume_access_code_grant(issued["access_code"], "student")
            self.assertEqual(issued["link_id"], grant.link_id)

        active = self.link_post(
            "/api/device/v1/link/poll", base, issued["link_token"]
        )
        self.assertEqual({"state": "ACTIVE", "job": None}, active.get_json())

        document = json.loads(DEFAULT_DOCUMENT.read_text(encoding="utf-8"))
        snapshot = self.link_post(
            "/api/device/v1/link/snapshot",
            {**base, "captured_at": 1_800_000_000, "document": document},
            issued["link_token"],
        )
        self.assertEqual(200, snapshot.status_code, snapshot.get_data(as_text=True))
        report = {
            "version": 1,
            "device_id": self.device_id,
            "checked_at": 1_800_000_001,
            "results": [
                {
                    "module": "OSMAN",
                    "name": "Motor driver",
                    "status": "BLOCKED_BY_POLICY",
                    "scope": "Not imported",
                    "detail": "No motor command was sent.",
                    "duration_ms": 0,
                    "facts": {"tested": False},
                }
            ],
        }
        capabilities = self.link_post(
            "/api/device/v1/link/capabilities",
            {**base, "report": report},
            issued["link_token"],
        )
        self.assertEqual(200, capabilities.status_code)

        with self.app.app_context():
            job_id = queue_device_job(
                issued["link_id"],
                self.device_id,
                "INSTALL_INACTIVE_CONFIGURATION",
                {"deployment_id": "c7a2ee", "configuration": document},
            )
        claimed_response = self.link_post(
            "/api/device/v1/link/poll", base, issued["link_token"]
        )
        claimed = claimed_response.get_json()["job"]
        self.assertEqual(job_id, claimed["job_id"])
        self.assertEqual("INSTALL_INACTIVE_CONFIGURATION", claimed["operation"])
        received = claimed["payload"]["configuration"]
        self.assertEqual(
            received["kalibrasyon"]["damga"]["ozet"],
            kisa_ozet_hesapla(received["kalibrasyon"]),
        )
        installed = ProfileStore(
            Path(self.temporary.name) / "received-profiles"
        ).import_combined(received, deployment_id="c7a2ee")
        self.assertEqual(document["profil"]["ad"], installed.manifest.name)
        receipt = self.link_post(
            "/api/device/v1/link/receipt",
            {
                **base,
                "job_id": job_id,
                "accepted": True,
                "receipt": {"installed": True, "active": False},
            },
            issued["link_token"],
        )
        self.assertEqual(200, receipt.status_code)

        closed = self.link_post(
            "/api/device/v1/link/close", base, issued["link_token"]
        )
        self.assertEqual(200, closed.status_code)
        rejected = self.link_post(
            "/api/device/v1/link/poll", base, issued["link_token"]
        )
        self.assertEqual(401, rejected.status_code)

        with self.app.app_context():
            connection = get_db()
            self.assertEqual(
                1,
                connection.execute(
                    "SELECT COUNT(*) FROM device_snapshots WHERE link_id = ?",
                    (issued["link_id"],),
                ).fetchone()[0],
            )
            self.assertEqual(
                "ACCEPTED",
                connection.execute(
                    "SELECT status FROM device_jobs WHERE job_id = ?", (job_id,)
                ).fetchone()["status"],
            )

    def test_changed_body_and_wrong_key_fail_without_consuming_challenge(self):
        challenge = self.challenge().get_json()["challenge"]
        wrong_key = Ed25519PrivateKey.generate()
        rejected = self.signed_access(challenge, private_key=wrong_key)
        self.assertEqual(401, rejected.status_code)

        accepted = self.signed_access(challenge)
        self.assertEqual(200, accepted.status_code)

        second_challenge = self.challenge().get_json()["challenge"]
        original = json_bytes(
            {"challenge": second_challenge, "device_id": self.device_id}
        )
        signature = b64url(
            self.private_key.sign(
                canonical_request(
                    "POST", ACCESS_CODE_PATH, self.device_id, second_challenge, original
                )
            )
        )
        changed = original + b" "
        rejected = self.signed_access(
            second_challenge, body=changed, signature=signature
        )
        self.assertEqual(401, rejected.status_code)

    def test_expired_nonce_and_disabled_device_fail_closed(self):
        challenge = self.challenge().get_json()["challenge"]
        with self.app.app_context():
            get_db().execute("UPDATE device_nonces SET expires_at = 0")
            get_db().commit()
        self.assertEqual(401, self.signed_access(challenge).status_code)

        fresh = self.challenge().get_json()["challenge"]
        with self.app.app_context():
            self.assertTrue(disable_device(self.device_id, actor="test-admin"))
        self.assertEqual(401, self.signed_access(fresh).status_code)
        self.assertEqual(403, self.challenge().status_code)

    def test_api_has_narrow_csrf_exception_and_strict_json(self):
        browser_post = self.client.post(
            "/login", data={"legal_name": "Egemen", "password": "school-password"}
        )
        self.assertEqual(400, browser_post.status_code)
        malformed = self.client.post(
            "/api/device/v1/challenge",
            data=json_bytes({"device_id": self.device_id, "extra": True}),
            content_type="application/json",
        )
        self.assertEqual(400, malformed.status_code)

    def test_device_api_rate_limit_counts_all_requests(self):
        self.app.config["CAM_DEVICE_REQUEST_LIMIT"] = 2
        self.assertEqual(200, self.challenge().status_code)
        self.assertEqual(200, self.challenge().status_code)
        limited = self.challenge()
        self.assertEqual(429, limited.status_code)

    def test_device_management_cli_registers_rotates_lists_and_disables(self):
        replacement = Ed25519PrivateKey.generate()
        public_bytes = replacement.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )
        identity = Path(self.temporary.name) / "replacement.pub.json"
        identity.write_text(
            json.dumps(
                {
                    "format": "startech-yaren-public-v1",
                    "algorithm": "Ed25519",
                    "device_id": "YAREN-second",
                    "public_key": b64url(public_bytes),
                }
            ),
            encoding="utf-8",
        )
        runner = self.app.test_cli_runner()
        registered = runner.invoke(
            args=["register-yaren-device", "--identity", str(identity)]
        )
        self.assertEqual(0, registered.exit_code, registered.output)
        listed = runner.invoke(args=["list-yaren-devices"])
        self.assertIn("YAREN-second\tactive\tEd25519", listed.output)
        rotated = runner.invoke(
            args=["rotate-yaren-device-key", "--identity", str(identity)]
        )
        self.assertEqual(0, rotated.exit_code, rotated.output)
        disabled = runner.invoke(
            args=["disable-yaren-device", "--device", "YAREN-second"]
        )
        self.assertEqual(0, disabled.exit_code, disabled.output)
        listed = runner.invoke(args=["list-yaren-devices"])
        self.assertIn("YAREN-second\tdisabled\tEd25519", listed.output)


if __name__ == "__main__":
    unittest.main(verbosity=2)
