"""Persistence helpers for `chart_artifacts` (retinal diagram shell).

Raw SQL via `app.db`, dialect-portable. Every read/write filters by
`organization_id`; cross-org access returns None without leaking row
existence. `drawing_json` is stored as a JSON-encoded TEXT column and
parsed back to a dict at the boundary.

Versioning rules:
  - First save: version_number = 1, parent_artifact_id = None.
  - Update an unsigned artifact: in-place, updated_at refreshed.
  - Sign: stamps signed_at + signed_by_user_id; record becomes immutable.
  - Edit a signed artifact: caller must use `fork_signed_artifact`,
    which inserts a NEW row whose parent_artifact_id is the original id
    and whose version_number is parent.version_number + 1. The fork
    starts unsigned with the new payload as its initial body.

Re-signing an already-signed artifact raises `ArtifactAlreadySigned`.
The route layer translates that into HTTP 409 artifact_already_signed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import text

from app.db import engine, fetch_one, insert_returning_id, transaction


_TABLE = "chart_artifacts"
ARTIFACT_TYPE_RETINAL_DIAGRAM = "retinal_diagram"


class ArtifactAlreadySigned(Exception):
    """Raised when callers try to mutate or re-sign a signed artifact."""

    def __init__(self, artifact_id: int):
        super().__init__(f"artifact {artifact_id} is signed and immutable")
        self.artifact_id = artifact_id


@dataclass
class ChartArtifact:
    id: int
    created_at: Any
    updated_at: Any
    organization_id: int
    patient_id: int
    encounter_id: Optional[int]
    created_by_user_id: int
    artifact_type: str
    title: str
    findings_text: str
    drawing_json: dict[str, Any]
    version_number: int
    parent_artifact_id: Optional[int]
    signed_at: Optional[Any]
    signed_by_user_id: Optional[int]

    @property
    def is_signed(self) -> bool:
        return self.signed_at is not None

    def to_response(self) -> dict[str, Any]:
        """Boundary-safe shape for JSON responses.

        `drawing_json` is rendered as a real JSON object (not a string)
        so frontends never have to double-parse it.
        """
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "patient_id": self.patient_id,
            "encounter_id": self.encounter_id,
            "created_by_user_id": self.created_by_user_id,
            "artifact_type": self.artifact_type,
            "title": self.title,
            "findings_text": self.findings_text,
            "drawing_json": self.drawing_json,
            "version_number": self.version_number,
            "parent_artifact_id": self.parent_artifact_id,
            "signed_at": _iso(self.signed_at),
            "signed_by_user_id": self.signed_by_user_id,
            "is_signed": self.is_signed,
            "created_at": _iso(self.created_at),
            "updated_at": _iso(self.updated_at),
        }


def _iso(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _decode_drawing(raw: Any) -> dict[str, Any]:
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _row_to_artifact(row: dict[str, Any]) -> ChartArtifact:
    return ChartArtifact(
        id=row["id"],
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
        organization_id=row["organization_id"],
        patient_id=row["patient_id"],
        encounter_id=row.get("encounter_id"),
        created_by_user_id=row["created_by_user_id"],
        artifact_type=row.get("artifact_type", ARTIFACT_TYPE_RETINAL_DIAGRAM),
        title=row.get("title") or "",
        findings_text=row.get("findings_text") or "",
        drawing_json=_decode_drawing(row.get("drawing_json")),
        version_number=int(row.get("version_number") or 1),
        parent_artifact_id=row.get("parent_artifact_id"),
        signed_at=row.get("signed_at"),
        signed_by_user_id=row.get("signed_by_user_id"),
    )


# --- Reads ---------------------------------------------------------------


def list_for_patient(
    *,
    organization_id: int,
    patient_id: int,
    artifact_type: str = ARTIFACT_TYPE_RETINAL_DIAGRAM,
) -> list[ChartArtifact]:
    sql = (
        f"SELECT * FROM {_TABLE} "
        "WHERE organization_id = :org AND patient_id = :pid "
        "AND artifact_type = :atype "
        "ORDER BY created_at DESC, id DESC"
    )
    with engine.connect() as conn:
        rows = conn.execute(
            text(sql),
            {"org": organization_id, "pid": patient_id, "atype": artifact_type},
        ).mappings().all()
    return [_row_to_artifact(dict(r)) for r in rows]


def get_for_patient(
    artifact_id: int,
    *,
    organization_id: int,
    patient_id: int,
) -> Optional[ChartArtifact]:
    row = fetch_one(
        f"SELECT * FROM {_TABLE} "
        "WHERE id = :id AND organization_id = :org AND patient_id = :pid",
        {"id": artifact_id, "org": organization_id, "pid": patient_id},
    )
    return _row_to_artifact(row) if row else None


# --- Writes --------------------------------------------------------------


def create_artifact(
    *,
    organization_id: int,
    patient_id: int,
    encounter_id: Optional[int],
    created_by_user_id: int,
    title: str,
    findings_text: str,
    drawing_json: dict[str, Any],
    artifact_type: str = ARTIFACT_TYPE_RETINAL_DIAGRAM,
) -> ChartArtifact:
    """Insert a brand-new artifact (no parent, version 1, unsigned)."""
    with transaction() as conn:
        new_id = insert_returning_id(
            conn,
            _TABLE,
            {
                "organization_id": organization_id,
                "patient_id": patient_id,
                "encounter_id": encounter_id,
                "created_by_user_id": created_by_user_id,
                "artifact_type": artifact_type,
                "title": title or "",
                "findings_text": findings_text or "",
                "drawing_json": json.dumps(drawing_json or {}),
                "version_number": 1,
                "parent_artifact_id": None,
            },
        )
    artifact = get_for_patient(
        new_id, organization_id=organization_id, patient_id=patient_id
    )
    assert artifact is not None
    return artifact


def update_unsigned_artifact(
    artifact: ChartArtifact,
    *,
    title: Optional[str] = None,
    findings_text: Optional[str] = None,
    drawing_json: Optional[dict[str, Any]] = None,
) -> ChartArtifact:
    """In-place update. Raises ArtifactAlreadySigned for signed rows."""
    if artifact.is_signed:
        raise ArtifactAlreadySigned(artifact.id)

    sets: list[str] = ["updated_at = :now"]
    params: dict[str, Any] = {
        "id": artifact.id,
        "org": artifact.organization_id,
        "now": datetime.now(timezone.utc),
    }
    if title is not None:
        sets.append("title = :title")
        params["title"] = title
    if findings_text is not None:
        sets.append("findings_text = :findings")
        params["findings"] = findings_text
    if drawing_json is not None:
        sets.append("drawing_json = :drawing")
        params["drawing"] = json.dumps(drawing_json)

    with transaction() as conn:
        conn.execute(
            text(
                f"UPDATE {_TABLE} SET {', '.join(sets)} "
                "WHERE id = :id AND organization_id = :org"
            ),
            params,
        )
    refreshed = get_for_patient(
        artifact.id,
        organization_id=artifact.organization_id,
        patient_id=artifact.patient_id,
    )
    assert refreshed is not None
    return refreshed


def fork_signed_artifact(
    parent: ChartArtifact,
    *,
    created_by_user_id: int,
    title: Optional[str] = None,
    findings_text: Optional[str] = None,
    drawing_json: Optional[dict[str, Any]] = None,
) -> ChartArtifact:
    """Create a new unsigned artifact that points back at a signed parent.

    Fields not supplied are inherited from the parent so callers can
    fork with a minimal patch.
    """
    with transaction() as conn:
        new_id = insert_returning_id(
            conn,
            _TABLE,
            {
                "organization_id": parent.organization_id,
                "patient_id": parent.patient_id,
                "encounter_id": parent.encounter_id,
                "created_by_user_id": created_by_user_id,
                "artifact_type": parent.artifact_type,
                "title": title if title is not None else parent.title,
                "findings_text": (
                    findings_text if findings_text is not None else parent.findings_text
                ),
                "drawing_json": json.dumps(
                    drawing_json if drawing_json is not None else parent.drawing_json
                ),
                "version_number": parent.version_number + 1,
                "parent_artifact_id": parent.id,
            },
        )
    forked = get_for_patient(
        new_id,
        organization_id=parent.organization_id,
        patient_id=parent.patient_id,
    )
    assert forked is not None
    return forked


def sign_artifact(
    artifact: ChartArtifact,
    *,
    signing_user_id: int,
) -> ChartArtifact:
    """Stamp signed_at/signed_by. Re-signing raises ArtifactAlreadySigned."""
    if artifact.is_signed:
        raise ArtifactAlreadySigned(artifact.id)

    now = datetime.now(timezone.utc)
    with transaction() as conn:
        conn.execute(
            text(
                f"UPDATE {_TABLE} SET "
                "signed_at = :now, signed_by_user_id = :uid, updated_at = :now "
                "WHERE id = :id AND organization_id = :org"
            ),
            {
                "id": artifact.id,
                "org": artifact.organization_id,
                "uid": signing_user_id,
                "now": now,
            },
        )
    refreshed = get_for_patient(
        artifact.id,
        organization_id=artifact.organization_id,
        patient_id=artifact.patient_id,
    )
    assert refreshed is not None
    return refreshed
