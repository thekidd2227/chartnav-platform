"""Phase 58 — practice backup / restore / reinstall recovery.

A practice-facing save/restore flow that matches the real product
stack: browser-only Vite+React UI backed by a FastAPI + SQL server.
No electron, no magical local-file access. The honest model is:

  CREATE:  admin calls /admin/practice-backup/create → server
           serializes the org's data to a canonical JSON bundle;
           the browser saves that JSON to disk via a user-initiated
           download. The bundle bytes are NEVER persisted server-
           side — only a metadata record (hash, size, counts).
           This keeps the backup useful after a "delete + reinstall"
           data-loss event (server can lose everything; the
           operator still has the downloaded file).

  RESTORE: admin uploads the saved bundle to
           /admin/practice-backup/restore. Server validates
           envelope, hash, schema version, and target org identity.
           By policy, restore is only accepted into an EMPTY target
           org (no patients, no notes, no encounters). Merging into
           a live org is deliberately out of scope for this pass —
           that requires collision semantics we do not have yet.

  RECOVER: the recovery flow is:
             1. operator creates backup
             2. operator deletes app / reinstalls / rebootstraps
             3. operator signs in to the fresh empty org
             4. operator uploads the backup file
             5. server validates and restores
             6. operator verifies counts + a few spot checks

Included in the bundle (per the data-inclusion contract):
  - organization row
  - users of that org
  - locations / patients / providers
  - encounters + encounter_inputs (transcripts)
  - extracted_findings + note_versions (with every wave 3/7 field)
  - clinician quick comments + favorites
  - clinical shortcut favorites
  - note_transmissions log (historical record; transports
    themselves re-configure per deploy)

Excluded, with explicit reasons (see docs):
  - security_audit_events (volumetric; not required for functional
    restore; re-accumulates naturally)
  - note_evidence_events (hash chain is tied to specific ids on
    the source install; transplanting it breaks integrity — the
    chain re-seeds from future governance events)
  - note_export_snapshots (artifact bytes would bloat the bundle
    to unbounded size)
  - evidence_chain_seals (tied to the source chain; seal history
    is reconstructed by sealing after restore)
  - user_sessions (ephemeral; users re-authenticate)
  - process secrets (HMAC keys, JWT keys — these live in env)

The exclusions are SAFETY-preserving: a restored bundle does not
fraudulently claim a chain of evidence events it never witnessed.
If an operator needs evidence continuity across reinstall, the
individual bundles (phase 55) remain verifiable off-server and the
existing signed bundle export is the forensic record of care.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from sqlalchemy import text

from app.db import fetch_all, fetch_one, transaction


BUNDLE_VERSION = "chartnav.practice_backup.v1"


class RestoreMode(str, Enum):
    """The contract of a restore call.

    This pass ships `empty_target_only`. `merge_preserve_existing`
    is reserved as a future mode for when collision semantics are
    designed; attempting it today returns a clear error.
    """
    empty_target_only = "empty_target_only"
    merge_preserve_existing = "merge_preserve_existing"  # reserved


# ---------------------------------------------------------------------
# Build path
# ---------------------------------------------------------------------

# Columns we serialize. Kept here so every consumer (build + restore
# + validate) agrees on the exact shape and one place governs the
# contract.
_ORG_COLS = "id, name, slug, settings, created_at"
_USER_COLS = (
    "id, organization_id, email, full_name, role, is_active, "
    "invited_at, invitation_token_hash, invitation_expires_at, "
    "invitation_accepted_at, is_authorized_final_signer, created_at"
)
_LOCATION_COLS = "id, organization_id, name, is_active, created_at"
_PATIENT_COLS = (
    "id, organization_id, external_ref, patient_identifier, first_name, "
    "last_name, date_of_birth, sex_at_birth, is_active, created_at"
)
_PROVIDER_COLS = (
    "id, organization_id, external_ref, display_name, npi, specialty, "
    "is_active, created_at"
)
_ENCOUNTER_COLS = (
    "id, organization_id, location_id, patient_identifier, patient_name, "
    "provider_name, status, scheduled_at, started_at, completed_at, "
    "created_at, patient_id, provider_id, external_ref, external_source"
)
_INPUT_COLS = (
    "id, encounter_id, input_type, processing_status, transcript_text, "
    "confidence_summary, source_metadata, created_by_user_id, "
    "retry_count, last_error, last_error_code, started_at, finished_at, "
    "worker_id, claimed_by, claimed_at, created_at, updated_at"
)
_FINDINGS_COLS = (
    "id, encounter_id, input_id, chief_complaint, hpi_summary, "
    "visual_acuity_od, visual_acuity_os, iop_od, iop_os, "
    "structured_json, extraction_confidence, created_at"
)
_NOTE_COLS = (
    "id, encounter_id, version_number, draft_status, note_format, "
    "note_text, generated_note_text, source_input_id, "
    "extracted_findings_id, generated_by, provider_review_required, "
    "missing_data_flags, signed_at, signed_by_user_id, exported_at, "
    "created_at, updated_at, reviewed_at, reviewed_by_user_id, "
    "content_fingerprint, attestation_text, amended_at, "
    "amended_by_user_id, amended_from_note_id, amendment_reason, "
    "superseded_at, superseded_by_note_id, final_approval_status, "
    "final_approved_at, final_approved_by_user_id, "
    "final_approval_signature_text, final_approval_invalidated_at, "
    "final_approval_invalidated_reason"
)


def _iso(v: Any) -> Any:
    if isinstance(v, datetime):
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        return v.isoformat()
    return v


def _rows_for_org(
    cols: str,
    table: str,
    organization_id: int,
) -> list[dict[str, Any]]:
    rows = fetch_all(
        f"SELECT {cols} FROM {table} "
        "WHERE organization_id = :org ORDER BY id",
        {"org": int(organization_id)},
    )
    return [{k: _iso(v) for k, v in r.items()} for r in rows]


def _rows_by_parent(
    cols: str,
    table: str,
    parent_col: str,
    parent_ids: list[int],
) -> list[dict[str, Any]]:
    if not parent_ids:
        return []
    placeholders = ",".join(f":p{i}" for i in range(len(parent_ids)))
    params = {f"p{i}": pid for i, pid in enumerate(parent_ids)}
    rows = fetch_all(
        f"SELECT {cols} FROM {table} "
        f"WHERE {parent_col} IN ({placeholders}) ORDER BY id",
        params,
    )
    return [{k: _iso(v) for k, v in r.items()} for r in rows]


def _canonical_bytes(payload: dict[str, Any]) -> bytes:
    """Deterministic JSON serialization. Same rule set as the
    evidence bundle so the hash is reproducible."""
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")


def _current_schema_version() -> str:
    """Best-effort Alembic head. Falls back to a stable marker so
    a fresh bundle can still be emitted if the alembic version
    table is missing in a weird deploy."""
    try:
        row = fetch_one("SELECT version_num FROM alembic_version LIMIT 1")
        if row:
            return str(row.get("version_num") or "")
    except Exception:
        pass
    return "unknown"


@dataclass(frozen=True)
class BuiltBundle:
    payload: dict[str, Any]
    canonical_bytes: bytes
    hash_sha256: str
    counts: dict[str, int]


def build_backup(
    *,
    organization_id: int,
    issued_by_user_id: Optional[int],
    issued_by_email: Optional[str],
) -> BuiltBundle:
    """Assemble the backup bundle for one org.

    Deterministic given the same row state. The envelope carries
    the bundle version, the source Alembic head, counts, and a
    `body_hash_sha256` over the canonical body. Callers get the
    dict (for JSON response) and the canonical bytes (for the
    `Content-Disposition: attachment` variant).
    """
    org = fetch_one(
        f"SELECT {_ORG_COLS} FROM organizations WHERE id = :id",
        {"id": int(organization_id)},
    )
    if not org:
        raise ValueError(f"organization_id {organization_id} not found")
    org = dict(org)

    # Preserve settings JSON text verbatim — some deploys may store
    # a non-JSON TEXT literal and we shouldn't double-parse / re-emit
    # a subtly different shape. The restore path re-writes this
    # column unchanged.
    raw_settings = org.get("settings")
    if isinstance(raw_settings, (dict, list)):
        settings_raw = json.dumps(raw_settings, sort_keys=True)
    else:
        settings_raw = raw_settings

    org_payload = {
        "id": int(org["id"]),
        "name": org.get("name"),
        "slug": org.get("slug"),
        "settings_json": settings_raw,
        "created_at": _iso(org.get("created_at")),
    }

    users = _rows_for_org(_USER_COLS, "users", organization_id)
    locations = _rows_for_org(_LOCATION_COLS, "locations", organization_id)
    patients = _rows_for_org(_PATIENT_COLS, "patients", organization_id)
    providers = _rows_for_org(_PROVIDER_COLS, "providers", organization_id)
    encounters = _rows_for_org(_ENCOUNTER_COLS, "encounters", organization_id)

    encounter_ids = [int(e["id"]) for e in encounters]
    encounter_inputs = _rows_by_parent(
        _INPUT_COLS, "encounter_inputs", "encounter_id", encounter_ids,
    )
    findings = _rows_by_parent(
        _FINDINGS_COLS, "extracted_findings", "encounter_id", encounter_ids,
    )
    note_versions = _rows_by_parent(
        _NOTE_COLS, "note_versions", "encounter_id", encounter_ids,
    )

    body: dict[str, Any] = {
        "bundle_version": BUNDLE_VERSION,
        "schema_version": _current_schema_version(),
        "organization": org_payload,
        "users": users,
        "locations": locations,
        "patients": patients,
        "providers": providers,
        "encounters": encounters,
        "encounter_inputs": encounter_inputs,
        "extracted_findings": findings,
        "note_versions": note_versions,
        # Intentionally excluded (listed for transparency):
        "excluded": [
            "security_audit_events",
            "note_evidence_events",
            "note_export_snapshots",
            "evidence_chain_seals",
            "user_sessions",
            "process_secrets",
        ],
    }

    canonical = _canonical_bytes(body)
    digest = hashlib.sha256(canonical).hexdigest()

    body["envelope"] = {
        "issued_at": datetime.now(timezone.utc).isoformat(),
        "issued_by_user_id": issued_by_user_id,
        "issued_by_email": issued_by_email,
        "body_hash_sha256": digest,
        "hash_inputs": "json(body,sort_keys,compact,utf8)",
    }

    counts = {
        "users": len(users),
        "locations": len(locations),
        "patients": len(patients),
        "providers": len(providers),
        "encounters": len(encounters),
        "encounter_inputs": len(encounter_inputs),
        "extracted_findings": len(findings),
        "note_versions": len(note_versions),
    }

    # Canonical bytes for the download variant are the POST-envelope
    # canonical serialization so the hash in the envelope matches
    # the pre-envelope body hash (not the full-document hash).
    final_bytes = _canonical_bytes(body)

    return BuiltBundle(
        payload=body,
        canonical_bytes=final_bytes,
        hash_sha256=digest,
        counts=counts,
    )


# ---------------------------------------------------------------------
# Validate path
# ---------------------------------------------------------------------

_REQUIRED_TOP_LEVEL = {
    "bundle_version",
    "schema_version",
    "organization",
    "users",
    "locations",
    "patients",
    "providers",
    "encounters",
    "encounter_inputs",
    "extracted_findings",
    "note_versions",
    "envelope",
}


@dataclass(frozen=True)
class ValidationVerdict:
    ok: bool
    error_code: Optional[str]
    reason: Optional[str]
    bundle_version: Optional[str]
    schema_version: Optional[str]
    source_organization_id: Optional[int]
    recomputed_hash: Optional[str]
    claimed_hash: Optional[str]
    body_hash_ok: Optional[bool]
    counts: dict[str, int]

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "error_code": self.error_code,
            "reason": self.reason,
            "bundle_version": self.bundle_version,
            "schema_version": self.schema_version,
            "source_organization_id": self.source_organization_id,
            "recomputed_hash": self.recomputed_hash,
            "claimed_hash": self.claimed_hash,
            "body_hash_ok": self.body_hash_ok,
            "counts": self.counts,
        }


def validate_backup(
    bundle: Any,
    *,
    expected_organization_id: Optional[int] = None,
) -> ValidationVerdict:
    """Structured validation of an uploaded bundle. Returns a
    verdict; never raises.

    Checks, in order:
      - shape: top-level keys all present
      - body_hash_sha256 recomputation matches envelope claim
      - bundle_version is recognised by this build
      - (optional) source organization id matches the caller's org
    """
    empty_counts = {
        "users": 0, "locations": 0, "patients": 0, "providers": 0,
        "encounters": 0, "encounter_inputs": 0,
        "extracted_findings": 0, "note_versions": 0,
    }

    if not isinstance(bundle, dict):
        return ValidationVerdict(
            ok=False, error_code="malformed_bundle",
            reason="bundle must be a JSON object",
            bundle_version=None, schema_version=None,
            source_organization_id=None,
            recomputed_hash=None, claimed_hash=None,
            body_hash_ok=None, counts=empty_counts,
        )

    missing = _REQUIRED_TOP_LEVEL - set(bundle.keys())
    if missing:
        return ValidationVerdict(
            ok=False, error_code="malformed_bundle",
            reason=f"bundle missing required keys: {sorted(missing)}",
            bundle_version=bundle.get("bundle_version"),
            schema_version=bundle.get("schema_version"),
            source_organization_id=None,
            recomputed_hash=None, claimed_hash=None,
            body_hash_ok=None, counts=empty_counts,
        )

    bv = bundle.get("bundle_version")
    if bv != BUNDLE_VERSION:
        return ValidationVerdict(
            ok=False, error_code="backup_incompatible_bundle_version",
            reason=(
                f"bundle_version {bv!r} is not supported by this "
                f"build (expected {BUNDLE_VERSION!r})"
            ),
            bundle_version=bv,
            schema_version=bundle.get("schema_version"),
            source_organization_id=None,
            recomputed_hash=None, claimed_hash=None,
            body_hash_ok=None, counts=empty_counts,
        )

    # Recompute the body hash.
    body_only = {k: v for k, v in bundle.items() if k != "envelope"}
    canonical = _canonical_bytes(body_only)
    recomputed = hashlib.sha256(canonical).hexdigest()
    envelope = bundle.get("envelope") or {}
    claimed = envelope.get("body_hash_sha256")
    hash_ok = bool(claimed) and (recomputed == claimed)
    if not hash_ok:
        return ValidationVerdict(
            ok=False, error_code="backup_hash_mismatch",
            reason=(
                "envelope.body_hash_sha256 does not match recomputed "
                "hash — the bundle has been tampered with or corrupted"
            ),
            bundle_version=bv,
            schema_version=bundle.get("schema_version"),
            source_organization_id=_src_org_id(bundle),
            recomputed_hash=recomputed, claimed_hash=claimed,
            body_hash_ok=False,
            counts=_count_rows(bundle),
        )

    src_org = _src_org_id(bundle)
    counts = _count_rows(bundle)

    if (
        expected_organization_id is not None
        and src_org is not None
        and int(expected_organization_id) != int(src_org)
    ):
        return ValidationVerdict(
            ok=False, error_code="backup_org_mismatch",
            reason=(
                f"bundle was issued by organization_id {src_org} but "
                f"caller is organization_id {expected_organization_id}"
            ),
            bundle_version=bv,
            schema_version=bundle.get("schema_version"),
            source_organization_id=src_org,
            recomputed_hash=recomputed, claimed_hash=claimed,
            body_hash_ok=True, counts=counts,
        )

    return ValidationVerdict(
        ok=True, error_code=None, reason=None,
        bundle_version=bv,
        schema_version=bundle.get("schema_version"),
        source_organization_id=src_org,
        recomputed_hash=recomputed, claimed_hash=claimed,
        body_hash_ok=True, counts=counts,
    )


def _src_org_id(bundle: dict[str, Any]) -> Optional[int]:
    org = bundle.get("organization") or {}
    try:
        return int(org.get("id")) if org.get("id") is not None else None
    except (TypeError, ValueError):
        return None


def _count_rows(bundle: dict[str, Any]) -> dict[str, int]:
    def _n(k: str) -> int:
        v = bundle.get(k)
        return len(v) if isinstance(v, list) else 0
    return {
        "users": _n("users"),
        "locations": _n("locations"),
        "patients": _n("patients"),
        "providers": _n("providers"),
        "encounters": _n("encounters"),
        "encounter_inputs": _n("encounter_inputs"),
        "extracted_findings": _n("extracted_findings"),
        "note_versions": _n("note_versions"),
    }


# ---------------------------------------------------------------------
# Restore path
# ---------------------------------------------------------------------

class RestoreError(Exception):
    def __init__(self, code: str, reason: str, status_code: int = 409):
        super().__init__(reason)
        self.code = code
        self.reason = reason
        self.status_code = status_code


@dataclass(frozen=True)
class RestoreResult:
    dry_run: bool
    mode: str
    source_organization_id: int
    target_organization_id: int
    applied_counts: dict[str, int]
    skipped_counts: dict[str, int]

    def as_dict(self) -> dict[str, Any]:
        return {
            "dry_run": self.dry_run,
            "mode": self.mode,
            "source_organization_id": self.source_organization_id,
            "target_organization_id": self.target_organization_id,
            "applied_counts": self.applied_counts,
            "skipped_counts": self.skipped_counts,
        }


def target_org_is_empty(organization_id: int) -> bool:
    """True when the org has NO encounters, note_versions, or
    patients. Users + locations may exist (the seed creates them);
    we check the clinical-data tables only."""
    enc = fetch_one(
        "SELECT COUNT(*) AS n FROM encounters WHERE organization_id = :org",
        {"org": int(organization_id)},
    )
    pat = fetch_one(
        "SELECT COUNT(*) AS n FROM patients WHERE organization_id = :org",
        {"org": int(organization_id)},
    )
    note = fetch_one(
        "SELECT COUNT(*) AS n FROM note_versions nv "
        "JOIN encounters e ON e.id = nv.encounter_id "
        "WHERE e.organization_id = :org",
        {"org": int(organization_id)},
    )
    return (
        int(enc["n"] if enc else 0) == 0
        and int(pat["n"] if pat else 0) == 0
        and int(note["n"] if note else 0) == 0
    )


def restore_backup(
    *,
    bundle: dict[str, Any],
    target_organization_id: int,
    mode: str,
    confirm_destructive: bool,
    dry_run: bool,
) -> RestoreResult:
    """Apply a validated bundle to the target org.

    SAFETY:
      - caller must validate() the bundle FIRST
      - mode must be 'empty_target_only'
      - target org must be empty (clinical tables)
      - confirm_destructive must be True unless dry_run
      - dry_run returns the counts without writing

    NOT SAFE, not supported:
      - merge_preserve_existing (returns RestoreError)
      - restoring across org boundaries (caller must pass matching
        target_organization_id; this function does not re-check
        the source-org match — that is route-level)
    """
    mode_enum = (
        RestoreMode.empty_target_only
        if mode == RestoreMode.empty_target_only.value
        else RestoreMode.merge_preserve_existing
    )
    if mode_enum != RestoreMode.empty_target_only:
        raise RestoreError(
            "restore_mode_unsupported",
            f"restore mode {mode!r} is not supported in this build",
            status_code=400,
        )

    if not dry_run and not confirm_destructive:
        raise RestoreError(
            "restore_requires_confirmation",
            "restore is destructive; pass confirm_destructive=true",
            status_code=409,
        )

    if not target_org_is_empty(target_organization_id):
        raise RestoreError(
            "restore_target_not_empty",
            (
                "target organization is not empty (encounters or "
                "patients or notes exist). This build only supports "
                "empty-target-only restore; issue a fresh org first."
            ),
            status_code=409,
        )

    src_org_id = _src_org_id(bundle) or target_organization_id
    applied = {k: 0 for k in (
        "users", "locations", "patients", "providers",
        "encounters", "encounter_inputs", "extracted_findings",
        "note_versions",
    )}
    skipped = {k: 0 for k in applied.keys()}

    if dry_run:
        for k in applied.keys():
            applied[k] = len(bundle.get(k) or [])
        return RestoreResult(
            dry_run=True, mode=mode_enum.value,
            source_organization_id=src_org_id,
            target_organization_id=target_organization_id,
            applied_counts=applied, skipped_counts=skipped,
        )

    with transaction() as conn:
        # 1. Upsert org (same id space is preserved — this is why
        # empty-target is enforced).
        org_block = bundle.get("organization") or {}
        if org_block.get("name"):
            conn.execute(
                text(
                    "UPDATE organizations SET name = :name "
                    "WHERE id = :id"
                ),
                {"id": target_organization_id, "name": org_block["name"]},
            )
        if org_block.get("settings_json") is not None:
            conn.execute(
                text(
                    "UPDATE organizations SET settings = :s "
                    "WHERE id = :id"
                ),
                {
                    "id": target_organization_id,
                    "s": org_block.get("settings_json"),
                },
            )

        # 2. Insert users — skip any whose email already exists.
        for u in bundle.get("users") or []:
            row = conn.execute(
                text("SELECT id FROM users WHERE email = :e"),
                {"e": u.get("email")},
            ).mappings().first()
            if row:
                skipped["users"] += 1
                continue
            conn.execute(
                text(
                    "INSERT INTO users ("
                    " id, organization_id, email, full_name, role, "
                    " is_active, invited_at, invitation_token_hash, "
                    " invitation_expires_at, invitation_accepted_at, "
                    " is_authorized_final_signer, created_at"
                    ") VALUES ("
                    " :id, :org, :email, :full_name, :role, :is_active, "
                    " :invited_at, :invitation_token_hash, "
                    " :invitation_expires_at, :invitation_accepted_at, "
                    " :is_authorized_final_signer, :created_at"
                    ")"
                ),
                {
                    "id": u.get("id"),
                    "org": target_organization_id,
                    "email": u.get("email"),
                    "full_name": u.get("full_name"),
                    "role": u.get("role"),
                    "is_active": bool(u.get("is_active")),
                    "invited_at": u.get("invited_at"),
                    "invitation_token_hash": u.get("invitation_token_hash"),
                    "invitation_expires_at": u.get("invitation_expires_at"),
                    "invitation_accepted_at": u.get("invitation_accepted_at"),
                    "is_authorized_final_signer": bool(
                        u.get("is_authorized_final_signer")
                    ),
                    "created_at": u.get("created_at"),
                },
            )
            applied["users"] += 1

        # 3. Locations / patients / providers — bulk inserts, assume
        # empty target (enforced above).
        for row_dict, table, cols, ccounter in [
            (bundle.get("locations") or [], "locations",
             ["id", "organization_id", "name", "is_active", "created_at"],
             "locations"),
            (bundle.get("patients") or [], "patients",
             ["id", "organization_id", "external_ref",
              "patient_identifier", "first_name", "last_name",
              "date_of_birth", "sex_at_birth", "is_active",
              "created_at"],
             "patients"),
            (bundle.get("providers") or [], "providers",
             ["id", "organization_id", "external_ref", "display_name",
              "npi", "specialty", "is_active", "created_at"],
             "providers"),
        ]:
            for r in row_dict:
                params: dict[str, Any] = {}
                for c in cols:
                    v = (
                        target_organization_id
                        if c == "organization_id"
                        else r.get(c)
                    )
                    params[c] = v
                col_list = ", ".join(cols)
                ph_list = ", ".join(f":{c}" for c in cols)
                conn.execute(
                    text(
                        f"INSERT INTO {table} ({col_list}) "
                        f"VALUES ({ph_list})"
                    ),
                    params,
                )
                applied[ccounter] += 1

        # 4. Encounters → inputs → findings → note_versions. Order
        # matters for FK references; encounter_id is the parent.
        for e in bundle.get("encounters") or []:
            cols = [
                "id", "organization_id", "location_id",
                "patient_identifier", "patient_name", "provider_name",
                "status", "scheduled_at", "started_at", "completed_at",
                "created_at", "patient_id", "provider_id",
                "external_ref", "external_source",
            ]
            params = {
                c: (
                    target_organization_id
                    if c == "organization_id"
                    else e.get(c)
                )
                for c in cols
            }
            conn.execute(
                text(
                    f"INSERT INTO encounters ({', '.join(cols)}) "
                    f"VALUES ({', '.join(':' + c for c in cols)})"
                ),
                params,
            )
            applied["encounters"] += 1

        for i in bundle.get("encounter_inputs") or []:
            cols = [
                "id", "encounter_id", "input_type", "processing_status",
                "transcript_text", "confidence_summary", "source_metadata",
                "created_by_user_id", "retry_count", "last_error",
                "last_error_code", "started_at", "finished_at",
                "worker_id", "claimed_by", "claimed_at",
                "created_at", "updated_at",
            ]
            params = {c: i.get(c) for c in cols}
            conn.execute(
                text(
                    f"INSERT INTO encounter_inputs ({', '.join(cols)}) "
                    f"VALUES ({', '.join(':' + c for c in cols)})"
                ),
                params,
            )
            applied["encounter_inputs"] += 1

        for f in bundle.get("extracted_findings") or []:
            cols = [
                "id", "encounter_id", "input_id", "chief_complaint",
                "hpi_summary", "visual_acuity_od", "visual_acuity_os",
                "iop_od", "iop_os", "structured_json",
                "extraction_confidence", "created_at",
            ]
            params = {c: f.get(c) for c in cols}
            conn.execute(
                text(
                    f"INSERT INTO extracted_findings ({', '.join(cols)}) "
                    f"VALUES ({', '.join(':' + c for c in cols)})"
                ),
                params,
            )
            applied["extracted_findings"] += 1

        for n in bundle.get("note_versions") or []:
            cols = [
                "id", "encounter_id", "version_number", "draft_status",
                "note_format", "note_text", "generated_note_text",
                "source_input_id", "extracted_findings_id",
                "generated_by", "provider_review_required",
                "missing_data_flags", "signed_at", "signed_by_user_id",
                "exported_at", "created_at", "updated_at",
                "reviewed_at", "reviewed_by_user_id", "content_fingerprint",
                "attestation_text", "amended_at", "amended_by_user_id",
                "amended_from_note_id", "amendment_reason",
                "superseded_at", "superseded_by_note_id",
                "final_approval_status", "final_approved_at",
                "final_approved_by_user_id",
                "final_approval_signature_text",
                "final_approval_invalidated_at",
                "final_approval_invalidated_reason",
            ]
            params = {c: n.get(c) for c in cols}
            conn.execute(
                text(
                    f"INSERT INTO note_versions ({', '.join(cols)}) "
                    f"VALUES ({', '.join(':' + c for c in cols)})"
                ),
                params,
            )
            applied["note_versions"] += 1

    return RestoreResult(
        dry_run=False, mode=mode_enum.value,
        source_organization_id=src_org_id,
        target_organization_id=target_organization_id,
        applied_counts=applied, skipped_counts=skipped,
    )


# ---------------------------------------------------------------------
# History
# ---------------------------------------------------------------------

def record_history(
    *,
    organization_id: int,
    event_type: str,
    created_by_user_id: Optional[int],
    created_by_email: Optional[str],
    bundle_version: str,
    schema_version: str,
    artifact_bytes_size: Optional[int],
    artifact_hash_sha256: Optional[str],
    counts: dict[str, int],
    note: Optional[str],
) -> int:
    with transaction() as conn:
        row = conn.execute(
            text(
                "INSERT INTO practice_backup_records ("
                " organization_id, event_type, created_by_user_id, "
                " created_by_email, bundle_version, schema_version, "
                " artifact_bytes_size, artifact_hash_sha256, "
                " encounter_count, note_version_count, user_count, note"
                ") VALUES ("
                " :org, :et, :uid, :email, :bv, :sv, :sz, :h, "
                " :enc, :nv, :users, :note"
                ") RETURNING id"
            ),
            {
                "org": int(organization_id),
                "et": event_type,
                "uid": created_by_user_id,
                "email": created_by_email,
                "bv": bundle_version,
                "sv": schema_version,
                "sz": artifact_bytes_size,
                "h": artifact_hash_sha256,
                "enc": int(counts.get("encounters", 0)),
                "nv": int(counts.get("note_versions", 0)),
                "users": int(counts.get("users", 0)),
                "note": (note or None),
            },
        ).mappings().first()
    return int(row["id"])


def list_history(organization_id: int, limit: int = 100) -> list[dict[str, Any]]:
    rows = fetch_all(
        "SELECT id, event_type, created_by_user_id, created_by_email, "
        "created_at, bundle_version, schema_version, artifact_bytes_size, "
        "artifact_hash_sha256, encounter_count, note_version_count, "
        "user_count, note "
        "FROM practice_backup_records WHERE organization_id = :org "
        "ORDER BY id DESC LIMIT :lim",
        {"org": int(organization_id), "lim": int(limit)},
    )
    out = []
    for r in rows:
        r = dict(r)
        r["created_at"] = _iso(r.get("created_at"))
        out.append(r)
    return out


__all__ = [
    "BUNDLE_VERSION",
    "RestoreMode",
    "BuiltBundle",
    "build_backup",
    "ValidationVerdict",
    "validate_backup",
    "RestoreError",
    "RestoreResult",
    "restore_backup",
    "target_org_is_empty",
    "record_history",
    "list_history",
]
