"""Outbound YAREN client for configuration and bounded SAC workshop jobs."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import json
import math
from pathlib import Path
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from startech.configuration.combined import merge_v1_pair
from startech.configuration.profiles import ProfileStore

from .atolye import WorkshopCommand, WorkshopReceipt, execute_workshop_command
from .yaren_diagnostics import collect_capability_report
from .yaren_web import WebAccessCode, default_server_url


POLL_PATH = "/api/device/v1/link/poll"
SNAPSHOT_PATH = "/api/device/v1/link/snapshot"
CAPABILITIES_PATH = "/api/device/v1/link/capabilities"
RECEIPT_PATH = "/api/device/v1/link/receipt"
CLOSE_PATH = "/api/device/v1/link/close"
ALLOWED_OPERATIONS = frozenset(
    {
        "REQUEST_ACTIVE_CONFIGURATION",
        "REQUEST_CAPABILITY_REPORT",
        "INSTALL_INACTIVE_CONFIGURATION",
        "RUN_BOUNDED_WORKSHOP_COMMAND",
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
    workshop_log_dir: str | Path = Path("runs"),
    status: StatusCallback = lambda _message: None,
    epoch: Callable[[], int] = lambda: int(time.time()),
    sleep: Callable[[float], None] = time.sleep,
) -> LinkRunResult:
    """Maintain one link until expiry; Ctrl+C is handled by the CLI caller."""

    if timeout <= 0 or timeout > 60:
        raise YarenLinkError("timeout must be greater than zero and at most 60 seconds")
    if poll_interval < 0.1 or poll_interval > 30:
        raise YarenLinkError("poll interval must be between 0.1 and 30 seconds")
    server = _server_root(server_url or default_server_url())
    selected_transport = transport or _http_transport
    store = ProfileStore(profile_root)
    synchronized = False
    accepted_jobs = 0
    rejected_jobs = 0
    while epoch() < access.expires_at:
        response = selected_transport(
            server + POLL_PATH,
            _base_payload(access),
            access.link_token,
            timeout,
        )
        if set(response) != {"state", "job"} or response["state"] not in {
            "PENDING",
            "ACTIVE",
        }:
            raise YarenLinkError("CAM link poll response is malformed")
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
                else:
                    command = _workshop_command(job_id, payload, now=epoch())
                    executed = workshop_executor(
                        command,
                        profile_root=profile_root,
                        log_dir=Path(workshop_log_dir),
                    )
                    if not isinstance(executed, WorkshopReceipt):
                        raise YarenLinkError("workshop executor returned an invalid receipt")
                    receipt = executed.to_dict()
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
    status("The temporary CAM link expired. The vehicle remains unarmed.")
    return LinkRunResult("EXPIRED", accepted_jobs, rejected_jobs)


__all__ = [
    "ALLOWED_OPERATIONS",
    "CAPABILITIES_PATH",
    "CLOSE_PATH",
    "LinkRunResult",
    "POLL_PATH",
    "RECEIPT_PATH",
    "SNAPSHOT_PATH",
    "YarenLinkError",
    "active_configuration_document",
    "close_temporary_link",
    "run_temporary_link",
]
