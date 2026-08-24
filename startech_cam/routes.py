"""Production CAM pages and configuration workflows."""

from __future__ import annotations

import copy
import json
from typing import Any

from flask import (
    Blueprint,
    Response,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from startech.configuration.combined import combined_config_errors

from .auth import current_actor, has_car_access, login_required
from .db import get_db
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
    project_sac_speed,
    refresh_calibration_stamp,
    publish_draft,
    replace_draft_json,
    save_draft,
    serialize_document,
)


cam_blueprint = Blueprint("cam", __name__)


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
        return render_template(
            "new.html",
            workflow=workflow,
            calibrations=list_calibrations(),
        )

    name = request.form.get("name", "").strip()
    source = request.form.get("source", "DEFAULT")
    source_document: dict[str, Any] | None = None
    try:
        if source == "PREVIOUS":
            tag = request.form.get("previous_tag", "")
            source_document = get_calibration(tag)
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
            raise InvalidDocument("car download is not connected yet; use an exported merged v2 file")
        elif source != "DEFAULT":
            raise InvalidDocument("unknown source")
        draft_id = create_draft(
            owner=current_actor(),
            workflow=workflow,
            name=name,
            source=source,
            source_document=source_document,
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
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{field.label}: invalid JSON ({exc.msg})") from exc
    else:
        value = raw
        if not value:
            raise ValueError(f"{field.label}: value is required")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if field.minimum is not None and value < field.minimum:
            raise ValueError(f"{field.label}: minimum is {field.minimum:g}")
        if field.maximum is not None and value > field.maximum:
            raise ValueError(f"{field.label}: maximum is {field.maximum:g}")
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
                "editor.html",
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
        keys = list(definitions)
        position = keys.index(section)
        if position + 1 < len(keys):
            return redirect(url_for("cam.edit_section", workflow=workflow, draft_id=draft_id, section=keys[position + 1]))
        return redirect(url_for("cam.summary", workflow=workflow, draft_id=draft_id))

    return render_template(
        "editor.html",
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
    return render_template(
        "summary.html",
        workflow=stored_workflow,
        draft_id=draft_id,
        document=document,
        document_json=serialize_document(document),
        touched=touched,
        errors=errors,
        definitions=SAC_STEPS if stored_workflow == "SAC" else MAC_SECTIONS,
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
    return render_template("created.html", tag=tag, document=document)


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
