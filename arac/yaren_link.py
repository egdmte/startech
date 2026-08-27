"""Outbound YAREN client for configuration and bounded SAC workshop jobs."""

from __future__ import annotations

import base64
from collections.abc import Callable, Mapping
from dataclasses import dataclass
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from startech.configuration.combined import merge_v1_pair
from startech.configuration.profiles import ProfileStore

from .adam import (
    RunControl,
    VehicleRunCommand,
    VehicleRunReceipt,
    execute_vehicle_run,
)
from .atolye import WorkshopCommand, WorkshopReceipt, execute_workshop_command
from .goz import CameraSource, build_preferred_camera
from .yaren_diagnostics import collect_capability_report
from .yaren_web import WebAccessCode, default_server_url


POLL_PATH = "/api/device/v1/link/poll"
SNAPSHOT_PATH = "/api/device/v1/link/snapshot"
CAPABILITIES_PATH = "/api/device/v1/link/capabilities"
RECEIPT_PATH = "/api/device/v1/link/receipt"
RUN_EVENTS_PATH = "/api/device/v1/link/run-events"
CLOSE_PATH = "/api/device/v1/link/close"
MAX_CALIBRATION_JPEG_BYTES = 650_000
ALLOWED_OPERATIONS = frozenset(
    {
        "REQUEST_ACTIVE_CONFIGURATION",
        "REQUEST_CAPABILITY_REPORT",
        "INSTALL_INACTIVE_CONFIGURATION",
        "RUN_BOUNDED_WORKSHOP_COMMAND",
        "CAPTURE_CALIBRATION_FRAME",
        "START_AUTONOMOUS_RUN",
    }
)
WORKSHOP_INSPECTION = frozenset(
    {"wheels-secured", "motors-mounted", "path-clear"}
)
WORKSHOP_PAYLOAD_FIELDS = frozenset(
    {
        "draft_id",
        "operator",
        "issued_at",
        "expires_at",
        "left_percent",
        "right_percent",
        "duration_seconds",
        "inspection",
    }
)
VEHICLE_RUN_PAYLOAD_FIELDS = frozenset(
    {
        "operator",
        "issued_at",
        "expires_at",
        "countdown_seconds",
        "mode",
        "mute_buzzer",
    }
)


class YarenLinkError(ValueError):
    """Raised when CAM or a link job violates the closed protocol."""


@dataclass(frozen=True)
class LinkRunResult:
    state: str
    accepted_jobs: int
    rejected_jobs: int


LinkTransport = Callable[[str, Mapping[str, Any], str, float], dict[str, Any]]
StatusCallback = Callable[[str], None]
WorkshopExecutor = Callable[..., WorkshopReceipt]
CalibrationFrameCollector = Callable[..., dict[str, Any]]
VehicleRunExecutor = Callable[..., VehicleRunReceipt]


def collect_calibration_frame(
    *,
    profile_root: str | Path | None,
    usb_index: int = 0,
    camera_builder: Callable[..., CameraSource] = build_preferred_camera,
) -> dict[str, Any]:
    """Capture and encode one real frame using the selected YAREN profile.

    There is deliberately no generated or recorded fallback here.  If neither
    configured live camera can supply a frame, the CAM job is rejected.
    """

    store = ProfileStore(profile_root)
    active = store.load_active_profile()
    camera_config = active.calibration["kamera"]
    width = int(camera_config["genislik"])
    height = int(camera_config["yukseklik"])
    camera = camera_builder(
        usb_index,
        size=(width, height),
        bgr_output=bool(camera_config["bgr_cikis"]),
        rotate_180=bool(camera_config["dondur_180"]),
    )
    try:
        camera.open()
        packet = camera.read_frame()
    finally:
        camera.close()

    shape = getattr(packet.payload, "shape", None)
    if not isinstance(shape, tuple) or len(shape) < 2:
        raise YarenLinkError("live calibration frame has no image dimensions")
    actual_height, actual_width = int(shape[0]), int(shape[1])
    if (actual_width, actual_height) != (width, height):
        raise YarenLinkError("live calibration frame does not match the active profile")

    try:
        cv2 = importlib.import_module("cv2")
        bgr = cv2.cvtColor(packet.payload, cv2.COLOR_RGB2BGR)
    except (ImportError, AttributeError, TypeError, ValueError) as exc:
        raise YarenLinkError(f"live calibration frame could not be encoded: {exc}") from exc

    encoded_bytes = b""
    for quality in (85, 70, 55):
        accepted, encoded = cv2.imencode(
            ".jpg", bgr, [int(cv2.IMWRITE_JPEG_QUALITY), quality]
        )
        if not accepted or encoded is None:
            continue
        encoded_bytes = encoded.tobytes()
        if 0 < len(encoded_bytes) <= MAX_CALIBRATION_JPEG_BYTES:
            break
    if not encoded_bytes:
        raise YarenLinkError("OpenCV refused to encode the live calibration frame")
    if len(encoded_bytes) > MAX_CALIBRATION_JPEG_BYTES:
        raise YarenLinkError("live calibration frame exceeds CAM's transfer limit")

    return {
        "format": "jpeg",
        "width": actual_width,
        "height": actual_height,
        "source": packet.source,
        "frame_id": packet.frame_id,
        "captured_at": packet.captured_at,
        "sha256": hashlib.sha256(encoded_bytes).hexdigest(),
        "image_b64": base64.b64encode(encoded_bytes).decode("ascii"),
    }


def _validate_calibration_frame_request(
    payload: Mapping[str, Any], *, now: int
) -> None:
    if set(payload) != {"draft_id", "requested_at"}:
        raise YarenLinkError("calibration frame job has unexpected fields")
    draft_id = payload["draft_id"]
    requested_at = payload["requested_at"]
    if (
        not isinstance(draft_id, str)
        or len(draft_id) != 32
        or any(character not in "0123456789abcdef" for character in draft_id)
    ):
        raise YarenLinkError("calibration frame draft id is invalid")
    if isinstance(requested_at, bool) or not isinstance(requested_at, int):
        raise YarenLinkError("calibration frame request time is invalid")
    if requested_at > now + 5 or requested_at < now - 60:
        raise YarenLinkError("calibration frame request is outside its live window")


def _workshop_command(
    job_id: str,
    payload: Mapping[str, Any],
    *,
    now: int,
) -> WorkshopCommand:
    """Validate the exact, short-lived CAM command before motor code is called."""

    if set(payload) != WORKSHOP_PAYLOAD_FIELDS:
        raise YarenLinkError("workshop command has unexpected fields")
    draft_id = payload["draft_id"]
    operator = payload["operator"]
    issued_at = payload["issued_at"]
    expires_at = payload["expires_at"]
    inspection = payload["inspection"]
    if (
        not isinstance(draft_id, str)
        or len(draft_id) != 32
        or any(character not in "0123456789abcdef" for character in draft_id)
    ):
        raise YarenLinkError("workshop draft id is invalid")
    if not isinstance(operator, str) or operator != operator.strip():
        raise YarenLinkError("workshop operator is invalid")
    if (
        isinstance(issued_at, bool)
        or not isinstance(issued_at, int)
        or isinstance(expires_at, bool)
        or not isinstance(expires_at, int)
    ):
        raise YarenLinkError("workshop command times must be integer epochs")
    if issued_at > now + 5:
        raise YarenLinkError("workshop command issue time is in the future")
    if issued_at < now - 30 or expires_at <= now:
        raise YarenLinkError("workshop command expired")
    if expires_at <= issued_at or expires_at - issued_at > 30:
        raise YarenLinkError("workshop command lifetime is invalid")
    if (
        not isinstance(inspection, list)
        or len(inspection) != len(WORKSHOP_INSPECTION)
        or set(inspection) != WORKSHOP_INSPECTION
        or any(not isinstance(item, str) for item in inspection)
    ):
        raise YarenLinkError("workshop physical inspection is incomplete")
    for name in ("left_percent", "right_percent", "duration_seconds"):
        value = payload[name]
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
        ):
            raise YarenLinkError(f"workshop {name} must be a finite number")
    try:
        return WorkshopCommand(
            command_id=job_id,
            operator=operator,
            left_percent=float(payload["left_percent"]),
            right_percent=float(payload["right_percent"]),
            duration_seconds=float(payload["duration_seconds"]),
            source="CAM_SAC",
            cam_issued_at=issued_at,
        )
    except ValueError as exc:
        raise YarenLinkError(str(exc)) from exc


def _vehicle_run_command(
    job_id: str,
    payload: Mapping[str, Any],
    *,
    now: int,
) -> VehicleRunCommand:
    """Validate a closed autonomous-run request before ADAM is opened."""

    if set(payload) != VEHICLE_RUN_PAYLOAD_FIELDS:
        raise YarenLinkError("vehicle run request has unexpected fields")
    operator = payload["operator"]
    issued_at = payload["issued_at"]
    expires_at = payload["expires_at"]
    if (
        not isinstance(operator, str)
        or operator != operator.strip()
        or not 2 <= len(operator) <= 120
    ):
        raise YarenLinkError("vehicle run operator is invalid")
    if (
        isinstance(issued_at, bool)
        or not isinstance(issued_at, int)
        or isinstance(expires_at, bool)
        or not isinstance(expires_at, int)
    ):
        raise YarenLinkError("vehicle run times must be integer epochs")
    if issued_at > now + 5 or issued_at < now - 60:
        raise YarenLinkError("vehicle run request is outside its live window")
    if expires_at <= now or expires_at <= issued_at or expires_at - issued_at > 90:
        raise YarenLinkError("vehicle run request lifetime is invalid")
    try:
        return VehicleRunCommand(
            command_id=job_id,
            operator=operator,
            issued_at=issued_at,
            countdown_seconds=payload["countdown_seconds"],
            mode=payload["mode"],
            mute_buzzer=payload["mute_buzzer"],
        )
    except (TypeError, ValueError) as exc:
        raise YarenLinkError(str(exc)) from exc


def _server_root(server_url: str) -> str:
    from urllib.parse import urlsplit

    parsed = urlsplit(server_url.strip())
    if (
        parsed.scheme != "https"
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        raise YarenLinkError("CAM server must be an HTTPS origin without a path")
    return f"https://{parsed.netloc}"


def _http_transport(
    url: str,
    payload: Mapping[str, Any],
    token: str,
    timeout: float,
) -> dict[str, Any]:
    body = json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")
    request = Request(
        url,
        data=body,
        method="POST",
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "STARTECH-YAREN-LINK/1",
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read(1_000_001)
    except HTTPError as exc:
        raw = exc.read(64_001)
        try:
            message = json.loads(raw)["error"]["message"]
        except (json.JSONDecodeError, KeyError, TypeError):
            message = f"CAM returned HTTP {exc.code}"
        raise YarenLinkError(str(message)) from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise YarenLinkError(f"could not reach CAM: {exc}") from exc
    if len(raw) > 1_000_000:
        raise YarenLinkError("CAM response exceeded one megabyte")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise YarenLinkError("CAM did not return valid JSON") from exc
    if not isinstance(value, dict):
        raise YarenLinkError("CAM response must be a JSON object")
    return value


def active_configuration_document(store: ProfileStore) -> dict[str, Any]:
    """Export the selected v1 pair as a valid, non-physical merged v2 snapshot."""

    profile = store.load_active_profile()
    evidence = {
        "fiziksel_cikis_aktif": False,
        "fiziksel_dogrulama_yapildi": False,
        "tam_cikis_onaylandi": False,
        "prototip_kilidi_onaylandi": False,
        "mekanik_inceleme": [],
        "fiziksel_hizalama_dogrulandi": False,
    }
    return merge_v1_pair(
        profile.calibration,
        profile.settings,
        name=profile.manifest.name,
        source="CAR",
        sac_intent=None,
        session_evidence=evidence,
        workflow="IMPORT",
    )


def _base_payload(access: WebAccessCode) -> dict[str, str]:
    return {"device_id": access.device_id, "link_id": access.link_id}


def _send_snapshot(
    server: str,
    access: WebAccessCode,
    store: ProfileStore,
    transport: LinkTransport,
    timeout: float,
    epoch: Callable[[], int],
) -> dict[str, Any]:
    document = active_configuration_document(store)
    transport(
        server + SNAPSHOT_PATH,
        {
            **_base_payload(access),
            "captured_at": epoch(),
            "document": document,
        },
        access.link_token,
        timeout,
    )
    return document


def _send_capabilities(
    server: str,
    access: WebAccessCode,
    profile_root: str | Path | None,
    transport: LinkTransport,
    timeout: float,
    capability_collector: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    report = capability_collector(access.device_id, profile_root=profile_root)
    transport(
        server + CAPABILITIES_PATH,
        {**_base_payload(access), "report": report},
        access.link_token,
        timeout,
    )
    return report


def _send_receipt(
    server: str,
    access: WebAccessCode,
    job_id: str,
    accepted: bool,
    receipt: Mapping[str, Any],
    transport: LinkTransport,
    timeout: float,
) -> None:
    transport(
        server + RECEIPT_PATH,
        {
            **_base_payload(access),
            "job_id": job_id,
            "accepted": accepted,
            "receipt": dict(receipt),
        },
        access.link_token,
        timeout,
    )


def close_temporary_link(
    access: WebAccessCode,
    *,
    server_url: str | None = None,
    timeout: float = 5.0,
    transport: LinkTransport | None = None,
) -> None:
    """Best-effort authenticated revocation used when YAREN is interrupted."""

    server = _server_root(server_url or default_server_url())
    selected_transport = transport or _http_transport
    selected_transport(
        server + CLOSE_PATH,
        _base_payload(access),
        access.link_token,
        timeout,
    )


def _job_fields(job: object) -> tuple[str, str, dict[str, Any]]:
    if not isinstance(job, dict) or set(job) != {"job_id", "operation", "payload"}:
        raise YarenLinkError("CAM job has unexpected fields")
    job_id = job["job_id"]
    operation = job["operation"]
    payload = job["payload"]
    if (
        not isinstance(job_id, str)
        or len(job_id) != 32
        or not isinstance(operation, str)
        or operation not in ALLOWED_OPERATIONS
        or not isinstance(payload, dict)
    ):
        raise YarenLinkError("CAM job is malformed or not allowed")
    return job_id, operation, payload


class _RunEventReporter:
    """Batch local KADER records while using the upload as the live-link heartbeat."""

    def __init__(
        self,
        *,
        server: str,
        access: WebAccessCode,
        job_id: str,
        transport: LinkTransport,
        timeout: float,
        status: StatusCallback,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.server = server
        self.access = access
        self.job_id = job_id
        self.transport = transport
        self.timeout = timeout
        self.status = status
        self.clock = clock
        self.next_sequence = 0
        self.last_sent_at = float("-inf")
        self.connection_lost = False

    def __call__(self, black_box: Any, force: bool) -> RunControl:
        if self.connection_lost:
            return RunControl.CONNECTION_LOST
        records = getattr(black_box, "records", None)
        if not isinstance(records, tuple):
            raise YarenLinkError("vehicle run reporter needs a KADER black box")
        now = self.clock()
        pending = records[self.next_sequence :]
        if not force and len(pending) < 50 and now - self.last_sent_at < 0.25:
            return RunControl.ACTIVE
        sent_request = False
        try:
            while pending or (force and not sent_request):
                batch = pending[:100]
                response = self.transport(
                    self.server + RUN_EVENTS_PATH,
                    {
                        **_base_payload(self.access),
                        "job_id": self.job_id,
                        "events": [record.to_dict() for record in batch],
                    },
                    self.access.link_token,
                    self.timeout,
                )
                if set(response) != {"accepted", "cancel_requested"} or response["accepted"] is not True:
                    raise YarenLinkError("KERİM rejected the vehicle run heartbeat")
                sent_request = True
                self.next_sequence += len(batch)
                self.last_sent_at = self.clock()
                if response["cancel_requested"] is True:
                    return RunControl.CANCEL_REQUESTED
                if response["cancel_requested"] is not False:
                    raise YarenLinkError("KERİM returned an invalid vehicle run control state")
                pending = records[self.next_sequence :]
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            self.connection_lost = True
            self.status(f"Vehicle run heartbeat failed: {exc}")
            return RunControl.CONNECTION_LOST
        return RunControl.ACTIVE


def run_temporary_link(
    access: WebAccessCode,
    *,
    profile_root: str | Path | None = None,
    server_url: str | None = None,
    timeout: float = 10.0,
    poll_interval: float = 2.0,
    transport: LinkTransport | None = None,
    capability_collector: Callable[..., dict[str, Any]] = collect_capability_report,
    workshop_executor: WorkshopExecutor = execute_workshop_command,
    vehicle_run_executor: VehicleRunExecutor = execute_vehicle_run,
    calibration_frame_collector: CalibrationFrameCollector = collect_calibration_frame,
    usb_index: int = 0,
    workshop_log_dir: str | Path = Path("runs"),
    adam_port: str | None = None,
    status: StatusCallback = lambda _message: None,
    epoch: Callable[[], int] = lambda: int(time.time()),
    sleep: Callable[[float], None] = time.sleep,
) -> LinkRunResult:
    """Maintain one link while CAM accepts the authenticated YAREN heartbeat."""

    if timeout <= 0 or timeout > 60:
        raise YarenLinkError("timeout must be greater than zero and at most 60 seconds")
    if poll_interval < 0.1 or poll_interval > 30:
        raise YarenLinkError("poll interval must be between 0.1 and 30 seconds")
    if isinstance(usb_index, bool) or not isinstance(usb_index, int) or usb_index < 0:
        raise YarenLinkError("USB camera index must be a non-negative integer")
    if adam_port is not None and (not isinstance(adam_port, str) or not adam_port.strip()):
        raise YarenLinkError("ADAM serial port must be non-empty text when supplied")
    server = _server_root(server_url or default_server_url())
    selected_transport = transport or _http_transport
    selected_adam_port = (adam_port or os.environ.get("STARTECH_ADAM_SERIAL_PORT", "")).strip()
    store = ProfileStore(profile_root)
    synchronized = False
    accepted_jobs = 0
    rejected_jobs = 0
    while True:
        response = selected_transport(
            server + POLL_PATH,
            _base_payload(access),
            access.link_token,
            timeout,
        )
        if set(response) != {"state", "job"} or response["state"] not in {
            "PENDING",
            "ACTIVE",
            "CLOSED",
            "EXPIRED",
        }:
            raise YarenLinkError("CAM link poll response is malformed")
        if response["state"] in {"CLOSED", "EXPIRED"}:
            final_state = str(response["state"])
            status(
                "The CAM link closed. The vehicle remains unarmed."
                if final_state == "CLOSED"
                else "The inactive CAM link lease expired. The vehicle remains unarmed."
            )
            return LinkRunResult(final_state, accepted_jobs, rejected_jobs)
        if response["state"] == "PENDING":
            status("Waiting for the random code to be entered in CAM.")
            sleep(poll_interval)
            continue

        if not synchronized:
            status("Code accepted. Reporting configuration and safe capability checks.")
            try:
                _send_snapshot(
                    server, access, store, selected_transport, timeout, epoch
                )
                status("Active configuration reported to CAM.")
            except Exception as exc:
                status(f"Active configuration could not be reported: {exc}")
            _send_capabilities(
                server,
                access,
                profile_root,
                selected_transport,
                timeout,
                capability_collector,
            )
            status("Capability report sent to CAM; motor and steering were not operated.")
            synchronized = True

        job = response["job"]
        if job is not None:
            job_id = "unknown"
            try:
                job_id, operation, payload = _job_fields(job)
                if operation == "REQUEST_ACTIVE_CONFIGURATION":
                    _send_snapshot(
                        server, access, store, selected_transport, timeout, epoch
                    )
                    receipt: dict[str, Any] = {"reported": True}
                elif operation == "REQUEST_CAPABILITY_REPORT":
                    _send_capabilities(
                        server,
                        access,
                        profile_root,
                        selected_transport,
                        timeout,
                        capability_collector,
                    )
                    receipt = {"reported": True}
                elif operation == "INSTALL_INACTIVE_CONFIGURATION":
                    if set(payload) != {"deployment_id", "configuration"}:
                        raise YarenLinkError("installation job has unexpected fields")
                    deployment_id = payload["deployment_id"]
                    configuration = payload["configuration"]
                    if not isinstance(configuration, dict):
                        raise YarenLinkError("installation configuration must be an object")
                    installed = store.import_combined(
                        configuration, deployment_id=deployment_id
                    )
                    receipt = {
                        "profile_id": installed.manifest.profile_id,
                        "installed": True,
                        "active": False,
                    }
                elif operation == "CAPTURE_CALIBRATION_FRAME":
                    _validate_calibration_frame_request(payload, now=epoch())
                    receipt = calibration_frame_collector(
                        profile_root=profile_root,
                        usb_index=usb_index,
                    )
                    if not isinstance(receipt, dict):
                        raise YarenLinkError(
                            "calibration frame collector returned an invalid receipt"
                        )
                elif operation == "RUN_BOUNDED_WORKSHOP_COMMAND":
                    command = _workshop_command(job_id, payload, now=epoch())
                    executed = workshop_executor(
                        command,
                        profile_root=profile_root,
                        log_dir=Path(workshop_log_dir),
                    )
                    if not isinstance(executed, WorkshopReceipt):
                        raise YarenLinkError("workshop executor returned an invalid receipt")
                    receipt = executed.to_dict()
                else:
                    command = _vehicle_run_command(job_id, payload, now=epoch())
                    reporter = _RunEventReporter(
                        server=server,
                        access=access,
                        job_id=job_id,
                        transport=selected_transport,
                        timeout=timeout,
                        status=status,
                    )
                    status(
                        f"KERİM requested autonomous run {job_id}. Live logs: "
                        f"{server}/vehicle-runs/{job_id}"
                    )
                    executed_run = vehicle_run_executor(
                        command,
                        heartbeat=reporter,
                        adam_port=selected_adam_port,
                        profile_root=profile_root,
                        usb_index=usb_index,
                        log_dir=Path(workshop_log_dir),
                        status=status,
                    )
                    if not isinstance(executed_run, VehicleRunReceipt):
                        raise YarenLinkError("vehicle run executor returned an invalid receipt")
                    if reporter.connection_lost:
                        status(
                            "KERİM became unavailable. The car recorded RUN_HALT_NOCON "
                            "locally and requires manual activation."
                        )
                        return LinkRunResult(
                            "CONNECTION_LOST", accepted_jobs, rejected_jobs
                        )
                    receipt = executed_run.to_dict()
                _send_receipt(
                    server,
                    access,
                    job_id,
                    True,
                    receipt,
                    selected_transport,
                    timeout,
                )
                accepted_jobs += 1
                status(f"Accepted bounded CAM job {job_id}.")
            except Exception as exc:
                rejected_jobs += 1
                if job_id != "unknown":
                    _send_receipt(
                        server,
                        access,
                        job_id,
                        False,
                        {"error": str(exc)[:500]},
                        selected_transport,
                        timeout,
                    )
                status(f"Rejected CAM job {job_id}: {exc}")
        sleep(poll_interval)


__all__ = [
    "ALLOWED_OPERATIONS",
    "CAPABILITIES_PATH",
    "CLOSE_PATH",
    "MAX_CALIBRATION_JPEG_BYTES",
    "LinkRunResult",
    "POLL_PATH",
    "RECEIPT_PATH",
    "RUN_EVENTS_PATH",
    "SNAPSHOT_PATH",
    "YarenLinkError",
    "active_configuration_document",
    "collect_calibration_frame",
    "close_temporary_link",
    "execute_vehicle_run",
    "run_temporary_link",
]
