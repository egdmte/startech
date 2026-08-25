"""Production CAM pages and configuration workflows."""

from __future__ import annotations

import copy
from datetime import datetime, timezone
import json
import math
from typing import Any

from flask import (
    Blueprint,
    Response,
    abort,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from startech.configuration.combined import combined_config_errors

from .auth import current_actor, has_car_access, login_required
from .db import get_db
from .device_link import (
    DeviceLinkError,
    get_capability_report,
    get_device_job,
    get_device_snapshot,
    queue_device_job,
    validate_calibration_frame_receipt,
)
from .fields import Field, MAC_SECTIONS, SAC_STEPS
from .repository import (
    CalibrationNotFound,
    DraftNotFound,
    InvalidDocument,
    create_draft,
    get_calibration,
    get_draft,
    list_calibrations,
    nested_get,
    nested_set,
    parse_document_text,
    parse_json_value,
    project_sac_speed,
    record_sac_workshop_observation,
    refresh_calibration_stamp,
    publish_draft,
    replace_draft_json,
    save_draft,
    serialize_document,
)
from .security import now_epoch


cam_blueprint = Blueprint("cam", __name__)


def _session_device_link() -> tuple[str, str] | None:
    link_id = session.get("device_link_id")
    device_id = session.get("device_id")
    if (
        not has_car_access()
        or not isinstance(link_id, str)
        or not isinstance(device_id, str)
    ):
        return None
    return link_id, device_id


def _current_device_snapshot() -> dict[str, Any] | None:
    selected = _session_device_link()
    return None if selected is None else get_device_snapshot(*selected)


@cam_blueprint.get("/health")
def health() -> Response:
    get_db().execute("SELECT 1").fetchone()
    return Response('{"status":"ok"}\n', mimetype="application/json")


@cam_blueprint.app_errorhandler(DraftNotFound)
def draft_missing(_error: DraftNotFound) -> tuple[str, int]:
    return render_template("error.html", title="Draft unavailable", message="This draft does not exist or belongs to another session owner."), 404


@cam_blueprint.app_errorhandler(CalibrationNotFound)
def calibration_missing(_error: CalibrationNotFound) -> tuple[str, int]:
    return render_template("error.html", title="Calibration unavailable", message="The requested calibration could not be found."), 404


@cam_blueprint.get("/")
def index() -> Any:
    return redirect(url_for("cam.dashboard"))


@cam_blueprint.get("/dashboard")
@login_required
def dashboard() -> str:
    return render_template(
        "dashboard.html",
        calibrations=list_calibrations()[:5],
        car_linked=_session_device_link() is not None,
    )


@cam_blueprint.get("/diagnostics/cam-bundle.json")
@login_required
def download_cam_diagnostic_bundle() -> Response:
    """Download support evidence without credentials or claimed car telemetry."""

    selected = _session_device_link()
    jobs: list[dict[str, Any]] = []
    snapshot = None
    capabilities = None
    if selected is not None:
        snapshot = get_device_snapshot(*selected)
        capabilities = get_capability_report(*selected)
        rows = get_db().execute(
            """
            SELECT job_id, operation, status, payload_json, receipt_json,
                   created_at, completed_at
            FROM device_jobs WHERE link_id = ? AND device_id = ?
            ORDER BY created_at DESC, job_id DESC LIMIT 25
            """,
            selected,
        ).fetchall()
        for row in rows:
            payload = json.loads(str(row["payload_json"]))
            receipt = (
                None
                if row["receipt_json"] is None
                else json.loads(str(row["receipt_json"]))
            )
            if str(row["operation"]) == "CAPTURE_CALIBRATION_FRAME" and isinstance(
                receipt, dict
            ):
                receipt.pop("image_b64", None)
            jobs.append(
                {
                    "job_id": str(row["job_id"]),
                    "operation": str(row["operation"]),
                    "status": str(row["status"]),
                    "payload": payload,
                    "receipt": receipt,
                    "created_at": int(row["created_at"]),
                    "completed_at": row["completed_at"],
                }
            )

    connection = get_db()
    integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
    counts = {
        table: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
        for table in ("calibrations", "drafts", "device_jobs", "audit_events")
    }
    bundle = {
        "format": "startech-cam-diagnostic-v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "release": str(current_app.config.get("CAM_RELEASE", "development")),
        "scope": "CAM server records and the current temporary YAREN link",
        "limitations": [
            "No physical motion is inferred from software receipts.",
            "KADER vehicle logs are not uploaded by the current link protocol.",
            "Camera JPEG bytes, credentials, access codes, session data, and remote addresses are excluded.",
        ],
        "database": {"integrity": integrity, "counts": counts},
        "linked_device": None
        if selected is None
        else {
            "link_id": selected[0],
            "device_id": selected[1],
            "active_configuration": snapshot,
            "capabilities": capabilities,
            "jobs": jobs,
        },
        "recent_calibrations": list_calibrations()[:25],
    }
    body = json.dumps(bundle, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
    response = Response(body, mimetype="application/json")
    response.headers["Content-Disposition"] = (
        "attachment; filename=startech-cam-diagnostic.json"
    )
    return response


HSV_TARGETS: dict[str, tuple[str, tuple[str | int, ...]]] = {
    "lane-default": (
        "White lane — default",
        ("serit", "beyaz_profiller", "varsayilan"),
    ),
    "lane-dark": (
        "White lane — dark",
        ("serit", "beyaz_profiller", "karanlik"),
    ),
    "lane-normal": (
        "White lane — normal",
        ("serit", "beyaz_profiller", "normal"),
    ),
    "lane-bright": (
        "White lane — bright",
        ("serit", "beyaz_profiller", "parlak"),
    ),
    "orange-car": (
        "Orange car",
        ("renkler", "turuncu_arac", "araliklar", 0),
    ),
    "yellow-car": (
        "Yellow car",
        ("renkler", "sari_arac", "araliklar", 0),
    ),
    "red-light-low": (
        "Red light — low hue",
        ("renkler", "kirmizi_isik", "araliklar", 0),
    ),
    "red-light-high": (
        "Red light — high hue",
        ("renkler", "kirmizi_isik", "araliklar", 1),
    ),
    "green-light": (
        "Green light",
        ("renkler", "yesil_isik", "araliklar", 0),
    ),
    "blue-sign": (
        "Blue sign",
        ("renkler", "mavi_levha", "araliklar", 0),
    ),
    "red-parking-low": (
        "Red parking — low hue",
        ("renkler", "kirmizi_park", "araliklar", 0),
    ),
    "red-parking-high": (
        "Red parking — high hue",
        ("renkler", "kirmizi_park", "araliklar", 1),
    ),
}


def _hsv_range(document: dict[str, Any], target: str) -> dict[str, Any]:
    definition = HSV_TARGETS.get(target)
    if definition is None:
        raise InvalidDocument("choose a supported HSV target")
    current: Any = document["kalibrasyon"]
    for part in definition[1]:
        current = current[part]
    if not isinstance(current, dict) or set(current) != {"alt", "ust"}:
        raise InvalidDocument("the selected HSV target is malformed")
    return current


def _calibration_frame_job(
    draft_id: str, job_id: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    selected = _session_device_link()
    if selected is None:
        raise DeviceLinkError("the YAREN link is no longer available")
    job = get_device_job(job_id, *selected)
    if (
        job is None
        or job["operation"] != "CAPTURE_CALIBRATION_FRAME"
        or job["payload"].get("draft_id") != draft_id
    ):
        raise DeviceLinkError("calibration frame job is unavailable")
    if job["status"] != "ACCEPTED" or not isinstance(job["receipt"], dict):
        raise DeviceLinkError("the live calibration frame has not arrived")
    return job, validate_calibration_frame_receipt(job["receipt"])


@cam_blueprint.route("/camera-calibration", methods=["GET", "POST"])
@login_required
def camera_calibration_start() -> Any:
    snapshot = _current_device_snapshot()
    if snapshot is None:
        flash("Connect YAREN and wait for its active configuration first.", "error")
        return redirect(url_for("cam.dashboard"))
    if request.method == "GET":
        return render_template("camera_calibration_start.html")
    name = request.form.get("name", "").strip()
    try:
        draft_id = create_draft(
            owner=current_actor(),
            workflow="MAC",
            name=name,
            source="CAR",
            source_document=snapshot,
        )
    except (ValueError, InvalidDocument) as exc:
        flash(str(exc), "error")
        return render_template(
            "camera_calibration_start.html", entered_name=name
        ), 400
    return redirect(url_for("cam.camera_calibration_editor", draft_id=draft_id))


@cam_blueprint.post("/camera-calibration/<draft_id>/capture")
@login_required
def capture_camera_calibration_frame(draft_id: str) -> Any:
    _document, _touched, workflow = get_draft(draft_id, current_actor())
    if workflow != "MAC":
        abort(404)
    selected = _session_device_link()
    if selected is None:
        flash("Connect YAREN before requesting a live frame.", "error")
        return redirect(url_for("cam.camera_calibration_editor", draft_id=draft_id))
    requested_at = now_epoch()
    try:
        job_id = queue_device_job(
            *selected,
            "CAPTURE_CALIBRATION_FRAME",
            {"draft_id": draft_id, "requested_at": requested_at},
            actor=current_actor(),
            lifetime_seconds=30,
        )
    except DeviceLinkError as exc:
        flash(str(exc), "error")
        return redirect(url_for("cam.camera_calibration_editor", draft_id=draft_id))
    return redirect(
        url_for("cam.camera_calibration_editor", draft_id=draft_id, job=job_id)
    )


@cam_blueprint.get("/camera-calibration/<draft_id>/jobs/<job_id>")
@login_required
def camera_calibration_job_status(draft_id: str, job_id: str) -> Any:
    _document, _touched, workflow = get_draft(draft_id, current_actor())
    if workflow != "MAC":
        abort(404)
    selected = _session_device_link()
    if selected is None:
        return jsonify({"error": "device link unavailable"}), 409
    job = get_device_job(job_id, *selected)
    if (
        job is None
        or job["operation"] != "CAPTURE_CALIBRATION_FRAME"
        or job["payload"].get("draft_id") != draft_id
    ):
        abort(404)
    return jsonify({"job_id": job_id, "status": job["status"]})


def _points_from_form(width: int, height: int) -> list[list[int]]:
    try:
        points = json.loads(request.form.get("points_json", ""))
    except json.JSONDecodeError as exc:
        raise InvalidDocument("perspective points are not valid JSON") from exc
    if (
        not isinstance(points, list)
        or len(points) != 4
        or any(not isinstance(point, list) or len(point) != 2 for point in points)
        or any(
            isinstance(value, bool) or not isinstance(value, int)
            for point in points
            for value in point
        )
    ):
        raise InvalidDocument("perspective needs four integer [x, y] points")
    if any(
        not 0 <= point[0] <= width or not 0 <= point[1] <= height
        for point in points
    ):
        raise InvalidDocument("perspective points must stay inside the live frame")
    return points


def _hsv_values_from_form() -> tuple[list[int], list[int]]:
    values: list[int] = []
    for name, maximum in (
        ("lower_h", 180),
        ("lower_s", 255),
        ("lower_v", 255),
        ("upper_h", 180),
        ("upper_s", 255),
        ("upper_v", 255),
    ):
        raw = request.form.get(name, "").strip()
        try:
            value = int(raw)
        except ValueError as exc:
            raise InvalidDocument(f"{name} must be a whole number") from exc
        if not 0 <= value <= maximum:
            raise InvalidDocument(f"{name} must be between 0 and {maximum}")
        values.append(value)
    lower, upper = values[:3], values[3:]
    if any(lower[index] > upper[index] for index in range(3)) or lower == upper:
        raise InvalidDocument("HSV lower values must remain below the upper values")
    return lower, upper


@cam_blueprint.route("/camera-calibration/<draft_id>", methods=["GET", "POST"])
@login_required
def camera_calibration_editor(draft_id: str) -> Any:
    document, _touched, workflow = get_draft(draft_id, current_actor())
    if workflow != "MAC":
        abort(404)
    job_id = request.args.get("job", "") or request.form.get("job_id", "")
    job = None
    frame = None
    if job_id:
        selected = _session_device_link()
        if selected is not None:
            candidate = get_device_job(job_id, *selected)
            if (
                candidate is not None
                and candidate["operation"] == "CAPTURE_CALIBRATION_FRAME"
                and candidate["payload"].get("draft_id") == draft_id
            ):
                job = candidate
                if job["status"] == "ACCEPTED" and isinstance(job["receipt"], dict):
                    try:
                        frame = validate_calibration_frame_receipt(job["receipt"])
                    except DeviceLinkError as exc:
                        flash(str(exc), "error")

    calibration = document["kalibrasyon"]
    targets = {
        key: {
            "label": label,
            "lower": list(_hsv_range(document, key)["alt"]),
            "upper": list(_hsv_range(document, key)["ust"]),
        }
        for key, (label, _path) in HSV_TARGETS.items()
    }
    if request.method == "POST":
        try:
            if not job_id:
                raise InvalidDocument("capture a live frame before saving")
            _frame_job, frame = _calibration_frame_job(draft_id, job_id)
            width, height = int(frame["width"]), int(frame["height"])
            camera = calibration["kamera"]
            if [width, height] != [camera["genislik"], camera["yukseklik"]]:
                raise InvalidDocument(
                    "the live frame resolution no longer matches the active profile"
                )
            points = _points_from_form(width, height)
            target = request.form.get("hsv_target", "")
            lower, upper = _hsv_values_from_form()
            updated = copy.deepcopy(document)
            perspective = updated["kalibrasyon"]["perspektif"]
            perspective["olculen_cozunurluk"] = [width, height]
            perspective["kaynak_noktalar"] = points
            selected_range = _hsv_range(updated, target)
            selected_range["alt"] = lower
            selected_range["ust"] = upper
            evidence = updated["oturum_kaniti"]
            evidence.update(
                {
                    "fiziksel_cikis_aktif": False,
                    "fiziksel_dogrulama_yapildi": False,
                    "tam_cikis_onaylandi": False,
                    "prototip_kilidi_onaylandi": False,
                    "mekanik_inceleme": [],
                    "fiziksel_hizalama_dogrulandi": False,
                }
            )
            stamp = updated["kalibrasyon"]["damga"]
            existing_note = str(stamp.get("not") or "").strip()
            evidence_note = (
                f"CAM real frame {frame['sha256']} from {frame['source']} "
                f"at {width}x{height}; driving remains physically unverified."
            )
            stamp["not"] = (
                f"{existing_note} {evidence_note}".strip()
                if existing_note
                else evidence_note
            )
            refresh_calibration_stamp(updated)
            updated["kalibrasyon"]["damga"]["olusturan"] = "CAM real-frame calibration"
            save_draft(
                draft_id,
                current_actor(),
                updated,
                section="camera-calibration",
            )
            tag = publish_draft(draft_id, current_actor())
            selected = _session_device_link()
            install_job = None
            if selected is not None:
                try:
                    install_job = queue_device_job(
                        *selected,
                        "INSTALL_INACTIVE_CONFIGURATION",
                        {"deployment_id": tag, "configuration": get_calibration(tag)},
                        actor=current_actor(),
                    )
                except DeviceLinkError as exc:
                    flash(
                        f"The calibration was created, but YAREN did not accept the "
                        f"inactive-profile job: {exc}",
                        "error",
                    )
            flash(
                "Real-frame calibration created and queued as an inactive YAREN profile."
                if install_job
                else "Real-frame calibration created; reconnect YAREN to sideload it.",
                "success",
            )
            return redirect(url_for("cam.created", tag=tag, job=install_job or ""))
        except (InvalidDocument, DeviceLinkError, ValueError) as exc:
            flash(str(exc), "error")

    return render_template(
        "camera_calibration_editor.html",
        draft_id=draft_id,
        document=document,
        points=calibration["perspektif"]["kaynak_noktalar"],
        targets=targets,
        frame=frame,
        frame_job=job,
    )


def _sac_pending_source() -> tuple[str, str | None]:
    source = session.get("sac_pending_source")
    previous_tag = session.get("sac_pending_previous_tag")
    if source not in {"DEFAULT", "PREVIOUS", "CAR"}:
        return "", None
    if previous_tag is not None and not isinstance(previous_tag, str):
        return "", None
    return source, previous_tag


@cam_blueprint.route("/sac/source", methods=["GET", "POST"])
@login_required
def sac_source() -> Any:
    calibrations = list_calibrations()
    if request.method == "GET":
        return render_template("sac_source.html", calibrations=calibrations)

    source = request.form.get("source", "").upper()
    if source == "CAR":
        if not has_car_access():
            flash(
                "A current YAREN code is required before CAM can contact the car.",
                "error",
            )
            return render_template("sac_source.html", calibrations=calibrations), 400
        if _current_device_snapshot() is None:
            flash(
                "YAREN is connected, but it has not reported an active configuration yet.",
                "error",
            )
            return render_template("sac_source.html", calibrations=calibrations), 409
        session.pop("sac_pending_previous_tag", None)
    elif source == "PREVIOUS":
        previous_tag = request.form.get("previous_tag", "")
        try:
            get_calibration(previous_tag)
        except CalibrationNotFound:
            flash("Choose an existing calibration to copy.", "error")
            return render_template("sac_source.html", calibrations=calibrations), 400
        session["sac_pending_previous_tag"] = previous_tag
    elif source == "DEFAULT":
        session.pop("sac_pending_previous_tag", None)
    else:
        flash("Choose a supported calibration source.", "error")
        return render_template("sac_source.html", calibrations=calibrations), 400

    session["sac_pending_source"] = source
    return redirect(url_for("cam.sac_name"))


@cam_blueprint.route("/sac/name", methods=["GET", "POST"])
@login_required
def sac_name() -> Any:
    source, previous_tag = _sac_pending_source()
    if not source:
        return redirect(url_for("cam.sac_source"))
    if request.method == "GET":
        return render_template("sac_name.html", source=source)

    name = request.form.get("name", "").strip()
    source_document: dict[str, Any] | None = None
    try:
        if source == "PREVIOUS":
            if previous_tag is None:
                raise InvalidDocument("the selected previous calibration is unavailable")
            source_document = get_calibration(previous_tag)
        elif source == "CAR":
            source_document = _current_device_snapshot()
            if source_document is None:
                raise InvalidDocument(
                    "the linked car configuration is no longer available"
                )
        draft_id = create_draft(
            owner=current_actor(),
            workflow="SAC",
            name=name,
            source=source,
            source_document=source_document,
            parent_tag=previous_tag,
        )
    except (ValueError, InvalidDocument, CalibrationNotFound) as exc:
        flash(str(exc), "error")
        return render_template(
            "sac_name.html", source=source, entered_name=name
        ), 400

    session.pop("sac_pending_source", None)
    session.pop("sac_pending_previous_tag", None)
    return redirect(url_for("cam.sac_preflight", draft_id=draft_id))


@cam_blueprint.route("/sac/<draft_id>/preflight", methods=["GET", "POST"])
@login_required
def sac_preflight(draft_id: str) -> Any:
    document, _touched, workflow = get_draft(draft_id, current_actor())
    if workflow != "SAC":
        abort(404)
    if request.method == "POST":
        return redirect(url_for("cam.sac_components", draft_id=draft_id))
    selected = _session_device_link()
    report = None if selected is None else get_capability_report(*selected)
    if report is not None:
        checks = tuple(
            (
                f"{item['module']} — {item['name']}",
                str(item["status"]).lower().replace("_", "-"),
                f"{item['scope']} — {item['detail']}",
            )
            for item in report["results"]
        )
    else:
        checks = (
        (
            "YAREN session",
            "responded" if has_car_access() else "unavailable",
            "CAM has a current device-bound session; capability results are pending."
            if has_car_access()
            else "Continuing without live car access.",
        ),
        (
            "Camera",
            "unavailable",
            "The web server does not probe the Raspberry Pi camera.",
        ),
        (
            "Camera recognition",
            "unverified",
            "No linked-car frame has been processed for this SAC session.",
        ),
        (
            "Motor driver",
            "unverified",
            "Use the bounded workshop control below after linking YAREN.",
        ),
        (
            "Steering system",
            "unavailable",
            "The differential wheel directions have not been physically observed.",
        ),
        (
            "Black box and M3TH",
            "configured",
            "Validation policy is available; hardware behaviour remains unverified.",
        ),
        )
    workshop_job = None
    job_id = request.args.get("job", "")
    if job_id and selected is not None:
        candidate = get_device_job(job_id, *selected)
        if (
            candidate is not None
            and candidate["operation"] == "RUN_BOUNDED_WORKSHOP_COMMAND"
            and candidate["payload"].get("draft_id") == draft_id
        ):
            workshop_job = candidate
    return render_template(
        "sac_preflight.html",
        draft_id=draft_id,
        checks=checks,
        report=report,
        workshop_job=workshop_job,
        car_linked=selected is not None,
        physical_evidence=document["oturum_kaniti"],
    )


def _workshop_number(name: str, minimum: float, maximum: float) -> float:
    raw = request.form.get(name, "").strip()
    try:
        value = float(raw)
    except ValueError as exc:
        raise InvalidDocument(f"{name} must be a number") from exc
    if not math.isfinite(value) or not minimum <= value <= maximum:
        raise InvalidDocument(f"{name} must be between {minimum:g} and {maximum:g}")
    return value


@cam_blueprint.post("/sac/<draft_id>/capabilities/refresh")
@login_required
def refresh_sac_capabilities(draft_id: str) -> Any:
    _document, _touched, workflow = get_draft(draft_id, current_actor())
    if workflow != "SAC":
        abort(404)
    selected = _session_device_link()
    if selected is None:
        flash("Connect the current YAREN device before running live checks.", "error")
        return redirect(url_for("cam.sac_preflight", draft_id=draft_id))
    requested_at = now_epoch()
    try:
        queue_device_job(
            *selected,
            "REQUEST_CAPABILITY_REPORT",
            {"requested_at": requested_at},
            actor=current_actor(),
            lifetime_seconds=30,
        )
    except DeviceLinkError as exc:
        flash(str(exc), "error")
    else:
        flash("A new physical camera and lane-recognition check was queued.", "success")
    return redirect(url_for("cam.sac_preflight", draft_id=draft_id))


@cam_blueprint.post("/sac/<draft_id>/workshop")
@login_required
def run_sac_workshop(draft_id: str) -> Any:
    _document, _touched, workflow = get_draft(draft_id, current_actor())
    if workflow != "SAC":
        abort(404)
    selected = _session_device_link()
    if selected is None:
        flash("Connect the current YAREN device before sending a workshop command.", "error")
        return redirect(url_for("cam.sac_preflight", draft_id=draft_id))
    try:
        left = _workshop_number("left_percent", -35, 35)
        right = _workshop_number("right_percent", -35, 35)
        duration = _workshop_number("duration_seconds", 0.05, 3.0)
        if left == 0 and right == 0:
            raise InvalidDocument("at least one workshop motor value must be non-zero")
        inspection = request.form.getlist("inspection")
        required = {"wheels-secured", "motors-mounted", "path-clear"}
        if len(inspection) != 3 or set(inspection) != required:
            raise InvalidDocument("confirm all three physical workshop conditions")
        issued_at = now_epoch()
        job_id = queue_device_job(
            *selected,
            "RUN_BOUNDED_WORKSHOP_COMMAND",
            {
                "draft_id": draft_id,
                "operator": current_actor(),
                "issued_at": issued_at,
                "expires_at": issued_at + 20,
                "left_percent": left,
                "right_percent": right,
                "duration_seconds": duration,
                "inspection": inspection,
            },
            actor=current_actor(),
            lifetime_seconds=20,
        )
    except (InvalidDocument, DeviceLinkError) as exc:
        flash(str(exc), "error")
        return redirect(url_for("cam.sac_preflight", draft_id=draft_id))
    return redirect(url_for("cam.sac_preflight", draft_id=draft_id, job=job_id))


@cam_blueprint.get("/sac/<draft_id>/jobs/<job_id>")
@login_required
def sac_job_status(draft_id: str, job_id: str) -> Any:
    _document, _touched, workflow = get_draft(draft_id, current_actor())
    if workflow != "SAC":
        abort(404)
    selected = _session_device_link()
    if selected is None:
        return jsonify({"error": "device link unavailable"}), 409
    job = get_device_job(job_id, *selected)
    if (
        job is None
        or job["operation"] != "RUN_BOUNDED_WORKSHOP_COMMAND"
        or job["payload"].get("draft_id") != draft_id
    ):
        abort(404)
    return jsonify(
        {
            "job_id": job["job_id"],
            "status": job["status"],
            "receipt": job["receipt"],
            "completed_at": job["completed_at"],
        }
    )


@cam_blueprint.post("/sac/<draft_id>/workshop/<job_id>/observe")
@login_required
def observe_sac_workshop(draft_id: str, job_id: str) -> Any:
    _document, _touched, workflow = get_draft(draft_id, current_actor())
    if workflow != "SAC":
        abort(404)
    selected = _session_device_link()
    if selected is None:
        flash("The YAREN link is no longer available.", "error")
        return redirect(url_for("cam.sac_preflight", draft_id=draft_id))
    job = get_device_job(job_id, *selected)
    if (
        job is None
        or job["operation"] != "RUN_BOUNDED_WORKSHOP_COMMAND"
        or job["payload"].get("draft_id") != draft_id
    ):
        abort(404)
    if job["status"] != "ACCEPTED" or not isinstance(job["receipt"], dict):
        flash("Only a completed workshop command can receive a physical observation.", "error")
        return redirect(url_for("cam.sac_preflight", draft_id=draft_id, job=job_id))
    observation = request.form.get("observation", "")
    if observation not in {"expected", "unexpected"}:
        flash("Choose whether the physical movement matched the command.", "error")
        return redirect(url_for("cam.sac_preflight", draft_id=draft_id, job=job_id))
    record_sac_workshop_observation(
        draft_id,
        current_actor(),
        job_id=job_id,
        inspection=job["payload"]["inspection"],
        observed_as_expected=observation == "expected",
    )
    flash(
        "Physical movement recorded as observed."
        if observation == "expected"
        else "Unexpected or missing movement recorded; physical verification remains failed.",
        "success" if observation == "expected" else "error",
    )
    return redirect(url_for("cam.sac_preflight", draft_id=draft_id, job=job_id))


@cam_blueprint.get("/sac/<draft_id>/components")
@login_required
def sac_components(draft_id: str) -> str:
    document, touched, workflow = get_draft(draft_id, current_actor())
    if workflow != "SAC":
        abort(404)
    return render_template(
        "sac_components.html",
        draft_id=draft_id,
        document=document,
        touched=touched,
        definitions=SAC_STEPS,
        complete=all(section in touched for section in SAC_STEPS),
    )


def _uploaded_document() -> dict[str, Any] | None:
    upload = request.files.get("configuration")
    if upload is None or not upload.filename:
        return None
    raw = upload.stream.read(1_000_001)
    if len(raw) > 1_000_000:
        raise InvalidDocument("uploaded configuration exceeds one megabyte")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeError as exc:
        raise InvalidDocument("uploaded configuration must be UTF-8 JSON") from exc
    return parse_document_text(text)


@cam_blueprint.route("/new/<workflow>", methods=["GET", "POST"])
@login_required
def new_configuration(workflow: str) -> Any:
    workflow = workflow.upper()
    if workflow not in {"SAC", "MAC"}:
        abort(404)
    if request.method == "GET":
        if workflow == "SAC":
            return redirect(url_for("cam.sac_source"))
        return render_template(
            "new.html",
            workflow=workflow,
            calibrations=list_calibrations(),
        )

    name = request.form.get("name", "").strip()
    source = request.form.get("source", "DEFAULT")
    source_document: dict[str, Any] | None = None
    parent_tag: str | None = None
    try:
        if source == "PREVIOUS":
            tag = request.form.get("previous_tag", "")
            source_document = get_calibration(tag)
            parent_tag = tag
        elif source == "UPLOAD":
            if workflow != "MAC":
                raise InvalidDocument("uploads are available in MAC only")
            source_document = _uploaded_document()
            if source_document is None:
                raise InvalidDocument("choose a merged v2 JSON file")
            source = "PREVIOUS"
        elif source == "CAR":
            if not has_car_access():
                raise InvalidDocument("a current YAREN code is required for car access")
            source_document = _current_device_snapshot()
            if source_document is None:
                raise InvalidDocument(
                    "YAREN has not reported an active configuration yet"
                )
        elif source != "DEFAULT":
            raise InvalidDocument("unknown source")
        draft_id = create_draft(
            owner=current_actor(),
            workflow=workflow,
            name=name,
            source=source,
            source_document=source_document,
            parent_tag=parent_tag,
        )
    except (ValueError, InvalidDocument) as exc:
        flash(str(exc), "error")
        return render_template(
            "new.html",
            workflow=workflow,
            calibrations=list_calibrations(),
            entered_name=name,
        ), 400
    first = next(iter(SAC_STEPS if workflow == "SAC" else MAC_SECTIONS))
    return redirect(url_for("cam.edit_section", workflow=workflow.lower(), draft_id=draft_id, section=first))


def _coerce_field(field: Field) -> Any:
    if field.kind == "checkbox":
        return field.path in request.form
    if field.kind == "multiselect":
        selected = request.form.getlist(field.path)
        allowed = {value for value, _label in field.choices}
        if any(value not in allowed for value in selected):
            raise ValueError(f"{field.label}: unsupported selection")
        return selected
    raw = request.form.get(field.path, "").strip()
    if field.kind == "select":
        allowed = {value for value, _label in field.choices}
        if raw not in allowed:
            raise ValueError(f"{field.label}: unsupported selection")
        if field.path.endswith("yon_derecesi"):
            return int(raw)
        return raw
    if field.kind == "nullable_boolean":
        if raw == "null":
            return None
        if raw in {"true", "false"}:
            return raw == "true"
        raise ValueError(f"{field.label}: choose measured, unmeasured, or unknown")
    if field.kind in {"integer", "range"}:
        try:
            value: Any = int(raw)
        except ValueError as exc:
            raise ValueError(f"{field.label}: enter a whole number") from exc
    elif field.kind == "number":
        try:
            value = float(raw)
        except ValueError as exc:
            raise ValueError(f"{field.label}: enter a number") from exc
    elif field.kind == "json":
        try:
            value = parse_json_value(raw)
        except InvalidDocument as exc:
            raise ValueError(f"{field.label}: {exc}") from exc
    else:
        value = raw
        if not value:
            raise ValueError(f"{field.label}: value is required")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if field.minimum is not None and value < field.minimum:
            raise ValueError(f"{field.label}: minimum is {field.minimum:g}")
        if field.maximum is not None and value > field.maximum:
            raise ValueError(f"{field.label}: maximum is {field.maximum:g}")
        if field.step is not None:
            origin = field.minimum or 0
            steps = (value - origin) / field.step
            if not math.isclose(steps, round(steps), abs_tol=1e-9):
                raise ValueError(f"{field.label}: increment must be {field.step:g}")
    return value


def _field_values(document: dict[str, Any], fields: tuple[Field, ...]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for field in fields:
        value = nested_get(document, field.path)
        if field.kind == "json":
            value = json.dumps(value, ensure_ascii=False, indent=2)
        elif field.kind == "nullable_boolean":
            value = "null" if value is None else str(value).lower()
        values[field.path] = value
    return values


@cam_blueprint.route("/<workflow>/<draft_id>/<section>", methods=["GET", "POST"])
@login_required
def edit_section(workflow: str, draft_id: str, section: str) -> Any:
    workflow_upper = workflow.upper()
    definitions = SAC_STEPS if workflow_upper == "SAC" else MAC_SECTIONS if workflow_upper == "MAC" else None
    if definitions is None or section not in definitions:
        abort(404)
    document, touched, stored_workflow = get_draft(draft_id, current_actor())
    if stored_workflow != workflow_upper:
        abort(404)
    title, description, fields = definitions[section]
    if request.method == "POST":
        updated = copy.deepcopy(document)
        try:
            for field in fields:
                nested_set(updated, field.path, _coerce_field(field))
            if workflow_upper == "SAC":
                project_sac_speed(updated)
            elif any(field.path.startswith("kalibrasyon.") for field in fields):
                refresh_calibration_stamp(updated)
            save_draft(draft_id, current_actor(), updated, section=section)
        except (ValueError, InvalidDocument) as exc:
            flash(str(exc), "error")
            values = {field.path: request.form.get(field.path, "") for field in fields}
            for field in fields:
                if field.kind == "multiselect":
                    values[field.path] = request.form.getlist(field.path)
                elif field.kind == "checkbox":
                    values[field.path] = field.path in request.form
            return render_template(
                "sac_editor.html" if workflow_upper == "SAC" else "editor.html",
                workflow=workflow_upper,
                draft_id=draft_id,
                section=section,
                definitions=definitions,
                title=title,
                description=description,
                fields=fields,
                values=values,
                touched=touched,
            ), 400
        if workflow_upper == "SAC":
            return redirect(url_for("cam.sac_components", draft_id=draft_id))
        keys = list(definitions)
        position = keys.index(section)
        if position + 1 < len(keys):
            return redirect(url_for("cam.edit_section", workflow=workflow, draft_id=draft_id, section=keys[position + 1]))
        return redirect(url_for("cam.summary", workflow=workflow, draft_id=draft_id))

    return render_template(
        "sac_editor.html" if workflow_upper == "SAC" else "editor.html",
        workflow=workflow_upper,
        draft_id=draft_id,
        section=section,
        definitions=definitions,
        title=title,
        description=description,
        fields=fields,
        values=_field_values(document, fields),
        touched=touched,
    )


@cam_blueprint.route("/mac/<draft_id>/variables", methods=["GET", "POST"])
@login_required
def variable_manager(draft_id: str) -> Any:
    document, touched, workflow = get_draft(draft_id, current_actor())
    if workflow != "MAC":
        abort(404)
    if request.method == "POST":
        text = request.form.get("document_json", "")
        try:
            replace_draft_json(draft_id, current_actor(), text, section="variables")
        except InvalidDocument as exc:
            flash(str(exc), "error")
            return render_template("variables.html", draft_id=draft_id, document_json=text, touched=touched), 400
        flash("The merged configuration passed schema and semantic validation.", "success")
        return redirect(url_for("cam.variable_manager", draft_id=draft_id))
    return render_template(
        "variables.html",
        draft_id=draft_id,
        document_json=serialize_document(document),
        touched=touched,
    )


@cam_blueprint.get("/<workflow>/<draft_id>/summary")
@login_required
def summary(workflow: str, draft_id: str) -> str:
    document, touched, stored_workflow = get_draft(draft_id, current_actor())
    if workflow.upper() != stored_workflow:
        abort(404)
    errors = combined_config_errors(document)
    definitions = SAC_STEPS if stored_workflow == "SAC" else MAC_SECTIONS
    missing_sections = (
        [section for section in definitions if section not in touched]
        if stored_workflow == "SAC"
        else []
    )
    return render_template(
        "sac_summary.html" if stored_workflow == "SAC" else "summary.html",
        workflow=stored_workflow,
        draft_id=draft_id,
        document=document,
        document_json=serialize_document(document),
        touched=touched,
        errors=errors,
        missing_sections=missing_sections,
        definitions=definitions,
    )


@cam_blueprint.post("/<workflow>/<draft_id>/publish")
@login_required
def publish(workflow: str, draft_id: str) -> Any:
    _document, _touched, stored_workflow = get_draft(draft_id, current_actor())
    if workflow.upper() != stored_workflow:
        abort(404)
    try:
        tag = publish_draft(draft_id, current_actor())
    except InvalidDocument as exc:
        flash(str(exc), "error")
        return redirect(url_for("cam.summary", workflow=workflow, draft_id=draft_id))
    return redirect(url_for("cam.created", tag=tag))


@cam_blueprint.get("/created/<tag>")
@login_required
def created(tag: str) -> str:
    document = get_calibration(tag)
    job = None
    job_id = request.args.get("job", "")
    selected = _session_device_link()
    if job_id and selected is not None:
        job = get_device_job(job_id, *selected)
    return render_template(
        "sac_created.html"
        if document["profil"]["is_akisi"] == "SAC"
        else "created.html",
        tag=tag,
        document=document,
        device_job=job,
    )


@cam_blueprint.post("/calibrations/<tag>/sideload")
@login_required
def sideload(tag: str) -> Any:
    document = get_calibration(tag)
    selected = _session_device_link()
    if selected is None:
        flash("A current YAREN device link is required for sideloading.", "error")
        return redirect(url_for("cam.created", tag=tag))
    try:
        job_id = queue_device_job(
            *selected,
            "INSTALL_INACTIVE_CONFIGURATION",
            {"deployment_id": tag, "configuration": document},
        )
    except DeviceLinkError as exc:
        flash(str(exc), "error")
        return redirect(url_for("cam.created", tag=tag))
    flash(
        "Queued for inactive installation. YAREN will not select or activate it.",
        "success",
    )
    return redirect(url_for("cam.created", tag=tag, job=job_id))


@cam_blueprint.post("/calibrations/<tag>/edit-mac")
@login_required
def edit_with_mac(tag: str) -> Any:
    source = get_calibration(tag)
    draft_id = create_draft(
        owner=current_actor(),
        workflow="MAC",
        name=f"{source['profil']['ad']} MAC",
        source="PREVIOUS",
        source_document=source,
        parent_tag=tag,
    )
    return redirect(url_for("cam.edit_section", workflow="mac", draft_id=draft_id, section="overview"))


@cam_blueprint.get("/calibrations/<tag>/download")
@login_required
def download(tag: str) -> Response:
    document = get_calibration(tag)
    response = Response(serialize_document(document), mimetype="application/json")
    response.headers["Content-Disposition"] = f'attachment; filename="startech-{tag}.json"'
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@cam_blueprint.get("/history")
@login_required
def history() -> str:
    return render_template("history.html", calibrations=list_calibrations())


__all__ = ["cam_blueprint"]
