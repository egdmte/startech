"""Closed-protocol tests for YAREN's temporary CAM configuration link."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from arac.yaren_link import (
    CLOSE_PATH,
    LinkRunResult,
    close_temporary_link,
    run_temporary_link,
)
from arac.yaren_web import WebAccessCode
from startech.configuration.profiles import ProfileStore


PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = PROJECT_ROOT / "config" / "examples"


class YarenTemporaryLinkTest(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "profiles"
        self.store = ProfileStore(self.root)
        active = self.store.import_pair(
            EXAMPLES / "kalibrasyon-v1.ornek.json",
            EXAMPLES / "ayarlar-v1.ornek.json",
            name="Active school baseline",
        )
        self.store.activate_profile(
            active.manifest.profile_id,
            warning_digest=active.manifest.warning_digest,
            reviewer="test student",
        )
        self.active_id = active.manifest.profile_id
        self.access = WebAccessCode(
            "R4ND0M8Z",
            "YAREN-school-car",
            1004,
            "a" * 32,
            "temporary-link-token-with-enough-entropy",
        )

    def test_install_job_creates_inactive_immutable_profile(self):
        document = json.loads(
            (EXAMPLES / "yapilandirma-v2.ornek.json").read_text(encoding="utf-8")
        )
        polls = [
            {"state": "PENDING", "job": None},
            {"state": "ACTIVE", "job": None},
            {
                "state": "ACTIVE",
                "job": {
                    "job_id": "b" * 32,
                    "operation": "INSTALL_INACTIVE_CONFIGURATION",
                    "payload": {
                        "deployment_id": "c7a2ee",
                        "configuration": document,
                    },
                },
            },
            {"state": "ACTIVE", "job": None},
        ]
        calls: list[tuple[str, dict[str, object], str]] = []

        def transport(url, payload, token, _timeout):
            calls.append((url, dict(payload), token))
            if url.endswith("/poll"):
                return polls.pop(0)
            return {"accepted": True}

        moment = [1000]

        def sleep(_seconds: float) -> None:
            moment[0] += 1

        def capabilities(device_id: str, **_kwargs):
            return {
                "version": 1,
                "device_id": device_id,
                "checked_at": moment[0],
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

        result = run_temporary_link(
            self.access,
            profile_root=self.root,
            server_url="https://cam.example.test",
            poll_interval=1.0,
            transport=transport,
            capability_collector=capabilities,
            epoch=lambda: moment[0],
            sleep=sleep,
        )

        self.assertEqual(LinkRunResult("EXPIRED", 1, 0), result)
        self.assertEqual(self.active_id, self.store.load_active_profile().manifest.profile_id)
        profiles = self.store.list_profiles(include_archived=False)
        self.assertEqual(2, len(profiles))
        receipt_payloads = [
            payload for url, payload, _token in calls if url.endswith("/receipt")
        ]
        self.assertEqual(1, len(receipt_payloads))
        self.assertTrue(receipt_payloads[0]["accepted"])
        self.assertFalse(receipt_payloads[0]["receipt"]["active"])
        self.assertTrue(any(url.endswith("/snapshot") for url, *_rest in calls))
        self.assertTrue(any(url.endswith("/capabilities") for url, *_rest in calls))
        self.assertTrue(all(token == self.access.link_token for _url, _body, token in calls))

    def test_close_uses_only_the_authenticated_link_identity(self):
        captured: list[tuple[str, dict[str, object], str, float]] = []

        def transport(url, payload, token, timeout):
            captured.append((url, dict(payload), token, timeout))
            return {"closed": True}

        close_temporary_link(
            self.access,
            server_url="https://cam.example.test",
            timeout=3.0,
            transport=transport,
        )
        self.assertEqual(1, len(captured))
        url, payload, token, timeout = captured[0]
        self.assertTrue(url.endswith(CLOSE_PATH))
        self.assertEqual(
            {"device_id": self.access.device_id, "link_id": self.access.link_id},
            payload,
        )
        self.assertEqual(self.access.link_token, token)
        self.assertEqual(3.0, timeout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
