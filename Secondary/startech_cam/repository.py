"""Persistence and validation boundary for KERİM configuration documents."""

from __future__ import annotations

import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import secrets
import sqlite3
from typing import Any
import uuid

from startech.configuration.combined import (
    combined_config_errors,
    combined_schema_errors,
)
from startech.configuration.validation import kisa_ozet_hesapla

from .db import get_db
from .fields import SAC_STEPS
from .security import audit, now_epoch


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DOCUMENT = ROOT / "config" / "examples" / "yapilandirma-v2.ornek.json"
MAX_JSON_BYTES = 1_000_000
SAC_PHYSICAL_INSPECTION = ("wheels-secured", "motors-mounted", "path-clear")


class CamRepositoryError(RuntimeError):
    """Base class for a rejected KERİM repository operation."""


class DraftNotFound(CamRepositoryError):
    pass


class InvalidDocument(CamRepositoryError, ValueError):
    pass


class CalibrationNotFound(CamRepositoryError):
    pass


def _duplicate_guard(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise InvalidDocument(f"duplicate JSON field: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise InvalidDocument(f"non-finite JSON number is forbidden: {value}")


def parse_document_text(
    text: str, *, refresh_calibration_digest: bool = False
) -> dict[str, Any]:
    value = parse_json_value(text)
    if not isinstance(value, dict):
        raise InvalidDocument("configuration root must be an object")
    if refresh_calibration_digest:
        schema_errors = combined_schema_errors(value)
        if schema_errors:
            raise InvalidDocument("; ".join(schema_errors))
        refresh_calibration_stamp(value)
    errors = combined_config_errors(value)
    if errors:
        raise InvalidDocument("; ".join(errors))
    return value


def parse_json_value(text: str) -> Any:
    """Parse a strict JSON value for both full documents and MAC fragments."""

    if len(text.encode("utf-8")) > MAX_JSON_BYTES:
        raise InvalidDocument("JSON exceeds the one-megabyte limit")
    try:
        value = json.loads(
            text,
            object_pairs_hook=_duplicate_guard,
            parse_constant=_reject_constant,
        )
    except InvalidDocument:
        raise
    except json.JSONDecodeError as exc:
        raise InvalidDocument(f"invalid JSON at line {exc.lineno}: {exc.msg}") from exc
    return value


def serialize_document(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + "\n"


def _default_document() -> dict[str, Any]:
    return parse_document_text(DEFAULT_DOCUMENT.read_text(encoding="utf-8"))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _prepare_profile(
    document: dict[str, Any],
    *,
    name: str,
    workflow: str,
    source: str,
    preserve_sac: bool,
) -> None:
    profile = document["profil"]
    profile.update(
        {
            "ad": name,
            "is_akisi": workflow,
            "kaynak": source,
            "olusturuldu_utc": _utc_now(),
            "kimlik": secrets.token_hex(3),
        }
    )
    if workflow == "SAC" and document.get("sac_niyeti") is None:
        baseline = json.loads(DEFAULT_DOCUMENT.read_text(encoding="utf-8"))
        document["sac_niyeti"] = copy.deepcopy(baseline["sac_niyeti"])
        document["oturum_kaniti"] = copy.deepcopy(baseline["oturum_kaniti"])
    elif workflow == "MAC" and not preserve_sac:
        document["sac_niyeti"] = None
        document["oturum_kaniti"].update(
            {
                "fiziksel_cikis_aktif": False,
                "fiziksel_dogrulama_yapildi": False,
                "tam_cikis_onaylandi": False,
                "prototip_kilidi_onaylandi": False,
                "mekanik_inceleme": [],
                "fiziksel_hizalama_dogrulandi": False,
            }
        )


def create_draft(
    *,
    owner: str,
    workflow: str,
    name: str,
    source: str = "DEFAULT",
    source_document: dict[str, Any] | None = None,
    parent_tag: str | None = None,
) -> str:
    if workflow not in {"SAC", "MAC"}:
        raise ValueError("workflow must be SAC or MAC")
    normalized_name = name.strip()
    if not normalized_name or len(normalized_name) > 80:
        raise ValueError("configuration name must contain between 1 and 80 characters")
    if parent_tag is not None and (
        len(parent_tag) != 6
        or any(character not in "0123456789abcdef" for character in parent_tag)
    ):
        raise ValueError("parent calibration tag is invalid")
    document = copy.deepcopy(source_document) if source_document is not None else _default_document()
    _prepare_profile(
        document,
        name=normalized_name,
        workflow=workflow,
        source=source,
        preserve_sac=source_document is not None,
    )
    errors = combined_config_errors(document)
    if errors:
        raise InvalidDocument("; ".join(errors))
    draft_id = uuid.uuid4().hex
    current = now_epoch()
    get_db().execute(
        """
        INSERT INTO drafts(
            draft_id, owner, workflow, payload_json, touched_sections_json,
            parent_tag, created_at, updated_at
        ) VALUES (?, ?, ?, ?, '[]', ?, ?, ?)
        """,
        (
            draft_id,
            owner,
            workflow,
            serialize_document(document),
            parent_tag,
            current,
            current,
        ),
    )
    get_db().commit()
    audit(
        owner,
        "DRAFT_CREATED",
        draft_id,
        {"workflow": workflow, "source": source, "parent_tag": parent_tag},
    )
    return draft_id


def get_draft(draft_id: str, owner: str) -> tuple[dict[str, Any], list[str], str]:
    row = get_db().execute(
        """
        SELECT payload_json, touched_sections_json, workflow
        FROM drafts WHERE draft_id = ? AND owner = ?
        """,
        (draft_id, owner),
    ).fetchone()
    if row is None:
        raise DraftNotFound(draft_id)
    document = parse_document_text(str(row["payload_json"]))
    touched = json.loads(str(row["touched_sections_json"]))
    return document, list(touched), str(row["workflow"])


def save_draft(
    draft_id: str,
    owner: str,
    document: dict[str, Any],
    *,
    section: str,
) -> None:
    errors = combined_config_errors(document)
    if errors:
        raise InvalidDocument("; ".join(errors))
    _current, touched, _workflow = get_draft(draft_id, owner)
    if section not in touched:
        touched.append(section)
    changed = get_db().execute(
        """
        UPDATE drafts
        SET payload_json = ?, touched_sections_json = ?, updated_at = ?
        WHERE draft_id = ? AND owner = ?
        """,
        (
            serialize_document(document),
            json.dumps(touched, ensure_ascii=False),
            now_epoch(),
            draft_id,
            owner,
        ),
    ).rowcount
    get_db().commit()
    if changed != 1:
        raise DraftNotFound(draft_id)
    audit(owner, "DRAFT_UPDATED", draft_id, {"section": section})


def record_sac_workshop_observation(
    draft_id: str,
    owner: str,
    *,
    job_id: str,
    inspection: list[str],
    observed_as_expected: bool,
) -> None:
    """Record human physical observation separately from the software receipt."""

    if (
        not isinstance(job_id, str)
        or len(job_id) != 32
        or any(character not in "0123456789abcdef" for character in job_id)
    ):
        raise InvalidDocument("workshop job id is invalid")
    if (
        not isinstance(inspection, list)
        or len(inspection) != len(SAC_PHYSICAL_INSPECTION)
        or set(inspection) != set(SAC_PHYSICAL_INSPECTION)
    ):
        raise InvalidDocument("physical inspection record is incomplete")
    if not isinstance(observed_as_expected, bool):
        raise InvalidDocument("physical observation must be explicit")
    document, _touched, workflow = get_draft(draft_id, owner)
    if workflow != "SAC":
        raise InvalidDocument("physical workshop observations belong to SAC drafts")
    evidence = document["oturum_kaniti"]
    evidence["mekanik_inceleme"] = list(SAC_PHYSICAL_INSPECTION)
    evidence["fiziksel_dogrulama_yapildi"] = observed_as_expected
    evidence["fiziksel_hizalama_dogrulandi"] = observed_as_expected
    evidence["fiziksel_cikis_aktif"] = False
    save_draft(draft_id, owner, document, section="hardware-evidence")
    audit(
        owner,
        "SAC_WORKSHOP_OBSERVATION",
        draft_id,
        {"job_id": job_id, "observed_as_expected": observed_as_expected},
    )


def replace_draft_json(draft_id: str, owner: str, text: str, *, section: str) -> None:
    document = parse_document_text(text, refresh_calibration_digest=True)
    _existing, _touched, workflow = get_draft(draft_id, owner)
    if document["profil"]["is_akisi"] != workflow:
        raise InvalidDocument("uploaded workflow does not match this draft")
    save_draft(draft_id, owner, document, section=section)


def list_calibrations() -> list[dict[str, Any]]:
    rows = get_db().execute(
        """
        SELECT tag, name, workflow, owner, created_at, parent_tag
        FROM calibrations ORDER BY created_at DESC, tag DESC
        """
    ).fetchall()
    return [dict(row) for row in rows]


def get_calibration(tag: str) -> dict[str, Any]:
    row = get_db().execute(
        "SELECT payload_json FROM calibrations WHERE tag = ?",
        (tag,),
    ).fetchone()
    if row is None:
        raise CalibrationNotFound(tag)
    return parse_document_text(str(row["payload_json"]))


def publish_draft(draft_id: str, owner: str) -> str:
    connection = get_db()
    try:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            """
            SELECT payload_json, touched_sections_json, workflow, parent_tag
            FROM drafts WHERE draft_id = ? AND owner = ?
            """,
            (draft_id, owner),
        ).fetchone()
        if row is None:
            raise DraftNotFound(draft_id)
        document = parse_document_text(str(row["payload_json"]))
        touched = set(json.loads(str(row["touched_sections_json"])))
        workflow = str(row["workflow"])
        if workflow == "SAC":
            missing = [section for section in SAC_STEPS if section not in touched]
            if missing:
                raise InvalidDocument(
                    "review every SAC section before creation; missing: "
                    + ", ".join(missing)
                )
        errors = combined_config_errors(document)
        if errors:
            raise InvalidDocument("; ".join(errors))

        for _attempt in range(10):
            tag = secrets.token_hex(3)
            document["profil"]["kimlik"] = tag
            document["profil"]["olusturuldu_utc"] = _utc_now()
            try:
                connection.execute(
                    """
                    INSERT INTO calibrations(
                        tag, name, workflow, owner, payload_json, created_at, parent_tag
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        tag,
                        document["profil"]["ad"],
                        workflow,
                        owner,
                        serialize_document(document),
                        now_epoch(),
                        row["parent_tag"],
                    ),
                )
                break
            except sqlite3.IntegrityError:
                continue
        else:
            raise RuntimeError("could not allocate a unique calibration tag")

        deleted = connection.execute(
            "DELETE FROM drafts WHERE draft_id = ? AND owner = ?",
            (draft_id, owner),
        ).rowcount
        if deleted != 1:
            raise DraftNotFound(draft_id)
        connection.commit()
    except BaseException:
        connection.rollback()
        raise
    audit(
        owner,
        "CALIBRATION_CREATED",
        tag,
        {"workflow": workflow, "parent_tag": row["parent_tag"]},
    )
    return tag


def nested_get(document: dict[str, Any], path: str) -> Any:
    current: Any = document
    for part in path.split("."):
        current = current[part]
    return current


def nested_set(document: dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    current: Any = document
    for part in parts[:-1]:
        current = current[part]
    current[parts[-1]] = value


def project_sac_speed(document: dict[str, Any]) -> None:
    """Project the stable SAC power intent into the existing v1 speed fields."""

    intent = document.get("sac_niyeti")
    if not isinstance(intent, dict):
        raise InvalidDocument("SAC intent is missing")
    power = intent["guc"]
    speed = document["ayarlar"]["hiz"]
    minimum = power["minimum_hiz_yuzde"]
    maximum = power["maksimum_hiz_yuzde"]
    speed["min"] = minimum
    speed["max"] = maximum
    speed["hedef"] = min(max(speed["hedef"], minimum), maximum)


def refresh_calibration_stamp(document: dict[str, Any]) -> None:
    """Regenerate the existing v1 digest after a deliberate MAC edit."""

    calibration = document.get("kalibrasyon")
    if not isinstance(calibration, dict) or not isinstance(calibration.get("damga"), dict):
        raise InvalidDocument("calibration stamp is missing")
    stamp = calibration["damga"]
    stamp["zaman"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    stamp["olusturan"] = "KERİM MAC v0.1"
    stamp["ozet"] = kisa_ozet_hesapla(calibration)


__all__ = [
    "CalibrationNotFound",
    "CamRepositoryError",
    "DraftNotFound",
    "InvalidDocument",
    "create_draft",
    "get_calibration",
    "get_draft",
    "list_calibrations",
    "nested_get",
    "nested_set",
    "parse_document_text",
    "parse_json_value",
    "publish_draft",
    "project_sac_speed",
    "record_sac_workshop_observation",
    "refresh_calibration_stamp",
    "replace_draft_json",
    "save_draft",
    "serialize_document",
]
