"""Closed-protocol tests for YAREN's temporary CAM configuration link."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from arac.atolye import WorkshopCommand, WorkshopReceipt
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

    @staticmethod
    def capabilities(device_id: str, **_kwargs):
        return {
            "version": 1,
            "device_id": device_id,
            "checked_at": 1000,
            "results": [],
        }

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
                        "status": "UNVERIFIED",
                        "scope": "Not operated by this report",
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

    def test_bounded_workshop_job_reaches_the_real_executor_and_returns_receipt(self):
        payload = {
            "draft_id": "d" * 32,
            "operator": "Ada Lovelace",
            "issued_at": 1000,
            "expires_at": 1020,
            "left_percent": 12.0,
            "right_percent": -8.0,
            "duration_seconds": 0.25,
            "inspection": ["wheels-secured", "motors-mounted", "path-clear"],
        }
        polls = [
            {"state": "ACTIVE", "job": {
                "job_id": "e" * 32,
                "operation": "RUN_BOUNDED_WORKSHOP_COMMAND",
                "payload": payload,
            }},
            {"state": "ACTIVE", "job": None},
        ]
        receipts = []
        executed: list[WorkshopCommand] = []
        moment = [1000]

        def transport(url, body, _token, _timeout):
            if url.endswith("/poll"):
                return polls.pop(0)
            if url.endswith("/receipt"):
                receipts.append(dict(body))
            return {"accepted": True}

        def executor(command, **_kwargs):
            executed.append(command)
            return WorkshopReceipt(
                command_id=command.command_id,
                operator=command.operator,
                source=command.source,
                cam_issued_at=command.cam_issued_at,
                profile_id=self.active_id,
                requested_left_percent=command.left_percent,
                requested_right_percent=command.right_percent,
                applied_left=0.12,
                applied_right=-0.08,
                duration_seconds=command.duration_seconds,
                started_at_utc="2026-08-24T12:00:00+00:00",
                finished_at_utc="2026-08-24T12:00:00.250+00:00",
                stop_requested=True,
                run_id="workshop-e",
            )

        def sleep(_seconds):
            moment[0] += 4

        result = run_temporary_link(
            self.access,
            profile_root=self.root,
            server_url="https://cam.example.test",
            transport=transport,
            capability_collector=self.capabilities,
            workshop_executor=executor,
            epoch=lambda: moment[0],
            sleep=sleep,
        )

        self.assertEqual(LinkRunResult("EXPIRED", 1, 0), result)
        self.assertEqual(1, len(executed))
        self.assertEqual("Ada Lovelace", executed[0].operator)
        self.assertEqual("CAM_SAC", executed[0].source)
        self.assertTrue(receipts[0]["accepted"])
        self.assertTrue(receipts[0]["receipt"]["stop_requested"])
        self.assertFalse(receipts[0]["receipt"]["physical_motion_observed"])

    def test_calibration_frame_job_uses_injected_live_collector(self):
        polls = [
            {
                "state": "ACTIVE",
                "job": {
                    "job_id": "a" * 32,
                    "operation": "CAPTURE_CALIBRATION_FRAME",
                    "payload": {"draft_id": "d" * 32, "requested_at": 1000},
                },
            }
        ]
        receipts = []
        collector_calls = []
        moment = [1000]

        def transport(url, body, _token, _timeout):
            if url.endswith("/poll"):
                return polls.pop(0)
            if url.endswith("/receipt"):
                receipts.append(dict(body))
            return {"accepted": True}

        def collector(**kwargs):
            collector_calls.append(kwargs)
            return {
                "format": "jpeg",
                "width": 840,
                "height": 630,
                "source": "usb:0",
                "frame_id": 4,
                "captured_at": 55.5,
                "sha256": "b" * 64,
                "image_b64": "/9j/2Q==",
            }

        result = run_temporary_link(
            self.access,
            profile_root=self.root,
            server_url="https://cam.example.test",
            transport=transport,
            capability_collector=self.capabilities,
            calibration_frame_collector=collector,
            usb_index=2,
            epoch=lambda: moment[0],
            sleep=lambda _seconds: moment.__setitem__(0, moment[0] + 5),
        )

        self.assertEqual(LinkRunResult("EXPIRED", 1, 0), result)
        self.assertEqual(2, collector_calls[0]["usb_index"])
        self.assertEqual("usb:0", receipts[0]["receipt"]["source"])
        self.assertTrue(receipts[0]["accepted"])

    def test_expired_workshop_job_is_rejected_before_the_executor(self):
        polls = [{"state": "ACTIVE", "job": {
            "job_id": "f" * 32,
            "operation": "RUN_BOUNDED_WORKSHOP_COMMAND",
            "payload": {
                "draft_id": "d" * 32,
                "operator": "Ada Lovelace",
                "issued_at": 950,
                "expires_at": 970,
                "left_percent": 10,
                "right_percent": 10,
                "duration_seconds": 0.25,
                "inspection": ["wheels-secured", "motors-mounted", "path-clear"],
            },
        }}]
        receipt = []
        moment = [1000]

        def transport(url, body, _token, _timeout):
            if url.endswith("/poll"):
                return polls.pop(0)
            if url.endswith("/receipt"):
                receipt.append(dict(body))
            return {"accepted": True}

        result = run_temporary_link(
            self.access,
            profile_root=self.root,
            server_url="https://cam.example.test",
            transport=transport,
            capability_collector=self.capabilities,
            workshop_executor=lambda *_args, **_kwargs: self.fail("executor called"),
            epoch=lambda: moment[0],
            sleep=lambda _seconds: moment.__setitem__(0, moment[0] + 5),
        )
        self.assertEqual(LinkRunResult("EXPIRED", 0, 1), result)
        self.assertFalse(receipt[0]["accepted"])
        self.assertIn("expired", receipt[0]["receipt"]["error"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
