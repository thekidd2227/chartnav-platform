"""FHIR R4 clinical-system adapter.

The first real, honest external adapter. Implements
`ClinicalSystemAdapter` against any FHIR R4 server (Epic, Cerner,
Athena, HAPI, Aidbox, Nextech, open test servers, …). No vendor name
is hard-coded in the core.

Scope (what's implemented):
- `search_patients(query)` → `GET /Patient?name=<query>`
- `fetch_patient(id)`     → `GET /Patient/<id>`
- `fetch_encounter(id)`   → `GET /Encounter/<id>`
  (normalized to ChartNav's internal shape — `patient_id`,
  `provider_name`, `status`)
- Normalizes FHIR resources into ChartNav's JSON-serializable shape so
  the service layer never sees the wire format.

Scope (honest limits):
- `update_encounter_status`: raises `AdapterNotSupported`. FHIR status
  transitions are vendor-dependent and require `Encounter.status`
  constraints we don't claim to own. Add per-vendor adapters on top of
  this one.
- `write_note`: raises `AdapterNotSupported`. `DocumentReference` +
  binary upload is a real integration project.
- `sync_reference_data`: returns zeros; provider sync is per-vendor.

Transport:
- HTTP via `httpx` if available; otherwise `urllib.request`. Both are
  exercised by the test suite via a pluggable `transport=` argument on
  the adapter so fixture transports can short-circuit the network.
- Config-driven: reads `CHARTNAV_FHIR_BASE_URL`,
  `CHARTNAV_FHIR_AUTH_TYPE` (`none` / `bearer`), and
  `CHARTNAV_FHIR_BEARER_TOKEN`.

This adapter MUST be registered via `register_vendor_adapter("fhir",
lambda: FHIRAdapter())` — see `app/integrations/__init__.py`.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Callable, Optional

from app.integrations.base import (
    AdapterError,
    AdapterInfo,
    AdapterNotSupported,
    EncounterListResult,
    SourceOfTruth,
    TransmitResult,
)


Transport = Callable[[str, dict[str, str]], dict[str, Any]]
"""A pluggable HTTP-GET transport for the adapter.

Signature: `(url, headers) -> parsed_json_body`. Tests inject a
fixture transport; production uses `_default_transport` (urllib).
"""


_INFO_BASE = dict(
    key="fhir",
    display_name="FHIR R4",
    description=(
        "Read-through FHIR R4 adapter with generic DocumentReference "
        "transmission. Normalizes Patient, Practitioner, and Encounter "
        "resources into ChartNav's internal shape. The transmission "
        "path POSTs a packaged DocumentReference to the FHIR server's "
        "`/DocumentReference` endpoint — servers that accept R4 writes "
        "(HAPI, Aidbox, Medplum, etc.) will persist it; vendor-specific "
        "EHRs typically require a specialised adapter on top that "
        "handles auth, Encounter linkage rules, and status constraints."
    ),
    supports_patient_read=True,
    supports_patient_write=False,
    supports_encounter_read=True,
    supports_encounter_write=False,
    # `write_note` (free-text seam) remains unsupported; the typed
    # artifact transmission path is the honest write-path today.
    supports_document_write=False,
    supports_document_transmit=True,
    source_of_truth={
        "organization": SourceOfTruth.MIRRORED,
        "location": SourceOfTruth.MIRRORED,
        "user": SourceOfTruth.CHARTNAV,
        "encounter": SourceOfTruth.EXTERNAL,
        "workflow_event": SourceOfTruth.CHARTNAV,
        "patient": SourceOfTruth.EXTERNAL,
        "document": SourceOfTruth.EXTERNAL,
    },
)


# ---------------------------------------------------------------------------
# Write transport (phase 26)
# ---------------------------------------------------------------------------
#
# Tests inject `write_transport=` so they never hit the network. Production
# uses `_default_write_transport` (urllib) which returns a 3-tuple of
# (status_code, body_text, location_header).
#
# Deliberately keeps the write transport separate from the GET transport
# so existing read-path tests and their fixture types don't need to grow
# a method discriminator.

WriteTransport = Callable[
    [str, bytes, dict[str, str]], "tuple[int, str, Optional[str]]"
]


def _default_write_transport(
    url: str, body: bytes, headers: dict[str, str]
) -> "tuple[int, str, Optional[str]]":
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            text = resp.read().decode("utf-8", errors="replace")
            return resp.status, text, resp.headers.get("Location")
    except urllib.error.HTTPError as e:
        # Return the error status + body instead of raising; the service
        # layer persists both success and failure into note_transmissions
        # and expects a TransmitResult, not an exception, for HTTP-level
        # failures. Transport-level failures (DNS, timeout) still raise
        # via URLError below.
        try:
            text = e.read().decode("utf-8", errors="replace")
        except Exception:
            text = f"(no body; {e.reason})"
        return int(e.code), text, None
    except urllib.error.URLError as e:
        raise AdapterError(
            "fhir_transport_error",
            f"could not reach FHIR server at {url}: {e.reason}",
        ) from e


# ---------------------------------------------------------------------------
# Default HTTP transport
# ---------------------------------------------------------------------------

def _default_transport(url: str, headers: dict[str, str]) -> dict[str, Any]:
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read()
    except urllib.error.HTTPError as e:
        raise AdapterError(
            "fhir_http_error",
            f"FHIR server returned HTTP {e.code} for {url}",
        ) from e
    except urllib.error.URLError as e:
        raise AdapterError(
            "fhir_transport_error",
            f"could not reach FHIR server at {url}: {e.reason}",
        ) from e
    try:
        return json.loads(body)
    except json.JSONDecodeError as e:
        raise AdapterError(
            "fhir_invalid_response",
            f"FHIR server returned non-JSON body: {e}",
        ) from e


# ---------------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------------

def _pick_name(resource: dict[str, Any]) -> tuple[str, str]:
    names = resource.get("name") or []
    for use in ("official", "usual", None):
        for n in names:
            if use is None or n.get("use") == use:
                given = " ".join(n.get("given", [])).strip()
                family = (n.get("family") or "").strip()
                if given or family:
                    return given, family
    return "", ""


def _normalize_patient(resource: dict[str, Any]) -> dict[str, Any]:
    given, family = _pick_name(resource)
    identifiers = resource.get("identifier") or []
    mrn = ""
    for ident in identifiers:
        typ = (ident.get("type") or {}).get("text", "")
        code = ""
        for coding in (ident.get("type") or {}).get("coding", []) or []:
            if coding.get("code"):
                code = coding["code"]
                break
        if typ == "MRN" or code == "MR":
            mrn = ident.get("value", "")
            break
    if not mrn and identifiers:
        mrn = identifiers[0].get("value", "")
    return {
        "id": resource.get("id"),
        "source": "fhir",
        "external_ref": resource.get("id"),
        "patient_identifier": mrn,
        "first_name": given,
        "last_name": family,
        "date_of_birth": resource.get("birthDate"),
        "sex_at_birth": resource.get("gender"),
        "display_name": (f"{given} {family}").strip() or resource.get("id", ""),
    }


def _normalize_encounter(
    resource: dict[str, Any],
    *,
    organization_id: int | None = None,
) -> dict[str, Any]:
    # FHIR Encounter.status vocabulary differs from ChartNav's; expose
    # the raw FHIR status and a best-effort ChartNav mapping. Callers
    # that need strict ChartNav semantics should layer their own logic.
    fhir_status = resource.get("status", "")
    mapping = {
        "planned": "scheduled",
        "arrived": "in_progress",
        "triaged": "in_progress",
        "in-progress": "in_progress",
        "onleave": "in_progress",
        "finished": "completed",
        "cancelled": "completed",
    }
    chartnav_status = mapping.get(fhir_status, fhir_status or "scheduled")
    subject_ref = (resource.get("subject") or {}).get("reference", "")
    patient_id = subject_ref.split("/", 1)[1] if subject_ref.startswith("Patient/") else None
    provider_name = ""
    for participant in resource.get("participant", []) or []:
        ind = participant.get("individual") or {}
        if ind.get("display"):
            provider_name = ind["display"]
            break
    # Expose a ChartNav-shape row alongside the FHIR-specific fields
    # so the HTTP layer can serve it directly without another
    # translation pass.
    return {
        "id": resource.get("id"),
        "organization_id": organization_id,
        "location_id": None,
        "patient_identifier": patient_id or "",
        "patient_name": None,
        "provider_name": provider_name,
        "status": chartnav_status,
        "patient_id": None,
        "provider_id": None,
        "scheduled_at": (resource.get("period") or {}).get("start"),
        "started_at": (resource.get("period") or {}).get("start"),
        "completed_at": (resource.get("period") or {}).get("end"),
        "created_at": None,
        "_source": "fhir",
        "_external_ref": resource.get("id"),
        "_fhir_status": fhir_status,
    }


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------

class FHIRAdapter:
    """FHIR R4 read-through adapter."""

    def __init__(
        self,
        *,
        base_url: Optional[str] = None,
        auth_type: Optional[str] = None,
        bearer_token: Optional[str] = None,
        transport: Optional[Transport] = None,
        write_transport: Optional[WriteTransport] = None,
    ) -> None:
        self._base_url = (base_url or os.environ.get("CHARTNAV_FHIR_BASE_URL") or "").rstrip("/")
        self._auth_type = (auth_type or os.environ.get("CHARTNAV_FHIR_AUTH_TYPE") or "none").lower()
        self._bearer_token = bearer_token or os.environ.get("CHARTNAV_FHIR_BEARER_TOKEN")
        self._transport: Transport = transport or _default_transport
        self._write_transport: WriteTransport = write_transport or _default_write_transport

        if not self._base_url:
            raise AdapterError(
                "fhir_not_configured",
                "CHARTNAV_FHIR_BASE_URL is required when "
                "CHARTNAV_INTEGRATION_ADAPTER=fhir",
            )
        if self._auth_type not in {"none", "bearer"}:
            raise AdapterError(
                "fhir_invalid_auth_type",
                f"CHARTNAV_FHIR_AUTH_TYPE must be 'none' or 'bearer' "
                f"(got {self._auth_type!r})",
            )
        if self._auth_type == "bearer" and not self._bearer_token:
            raise AdapterError(
                "fhir_missing_bearer",
                "CHARTNAV_FHIR_AUTH_TYPE=bearer requires "
                "CHARTNAV_FHIR_BEARER_TOKEN",
            )

    # ---------- info ----------
    @property
    def info(self) -> AdapterInfo:
        return AdapterInfo(**_INFO_BASE)

    # ---------- transport helper ----------
    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/fhir+json"}
        if self._auth_type == "bearer" and self._bearer_token:
            headers["Authorization"] = f"Bearer {self._bearer_token}"
        return headers

    def _get(self, path: str) -> dict[str, Any]:
        return self._transport(f"{self._base_url}{path}", self._headers())

    # ---------- patients ----------
    def fetch_patient(self, patient_id: str) -> dict[str, Any]:
        if not patient_id:
            raise AdapterError("invalid_argument", "patient_id is required")
        resource = self._get(f"/Patient/{patient_id}")
        if resource.get("resourceType") != "Patient":
            raise AdapterError(
                "fhir_unexpected_resource",
                f"expected Patient, got {resource.get('resourceType')!r}",
            )
        return _normalize_patient(resource)

    def search_patients(
        self, *, query: str, limit: int = 25
    ) -> list[dict[str, Any]]:
        if not query:
            return []
        from urllib.parse import quote
        bundle = self._get(f"/Patient?name={quote(query)}&_count={limit}")
        if bundle.get("resourceType") != "Bundle":
            raise AdapterError(
                "fhir_unexpected_resource",
                f"expected Bundle, got {bundle.get('resourceType')!r}",
            )
        entries = bundle.get("entry") or []
        out: list[dict[str, Any]] = []
        for e in entries[:limit]:
            resource = e.get("resource") or {}
            if resource.get("resourceType") == "Patient":
                out.append(_normalize_patient(resource))
        return out

    # ---------- encounters ----------
    def list_encounters(
        self,
        *,
        organization_id: int,
        location_id: int | None = None,
        status: str | None = None,
        provider_name: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> EncounterListResult:
        """GET /Encounter?_count=...&status=<mapped>.

        ChartNav status values are mapped back to FHIR status values
        for the server query. We intentionally do NOT support
        `location_id` or `provider_name` pass-through (they have no
        direct FHIR equivalent without vendor-specific extensions) —
        they are applied as a post-filter on the normalized rows so
        the frontend gets predictable semantics in both modes.
        """
        from urllib.parse import quote
        chartnav_to_fhir_status = {
            "scheduled": "planned",
            "in_progress": "in-progress",
            "draft_ready": "in-progress",
            "review_needed": "in-progress",
            "completed": "finished",
        }
        params = [f"_count={int(limit)}"]
        if offset:
            # FHIR uses `_offset` on some servers (HAPI supports it).
            # Vendor adapters override this method when they have a
            # richer search surface.
            params.append(f"_offset={int(offset)}")
        if status and status in chartnav_to_fhir_status:
            params.append(f"status={quote(chartnav_to_fhir_status[status])}")
        qs = "&".join(params)
        bundle = self._get(f"/Encounter?{qs}")
        if bundle.get("resourceType") != "Bundle":
            raise AdapterError(
                "fhir_unexpected_resource",
                f"expected Bundle, got {bundle.get('resourceType')!r}",
            )
        entries = bundle.get("entry") or []
        items: list[dict[str, Any]] = []
        for e in entries:
            resource = e.get("resource") or {}
            if resource.get("resourceType") != "Encounter":
                continue
            items.append(
                _normalize_encounter(resource, organization_id=organization_id)
            )

        # Post-filter for fields FHIR doesn't natively search by.
        if provider_name:
            items = [i for i in items if i.get("provider_name") == provider_name]

        # Prefer Bundle.total when available; otherwise use the count
        # we actually materialized.
        total = int(bundle.get("total") or len(items))
        return EncounterListResult(
            items=items, total=total, limit=int(limit), offset=int(offset)
        )

    def fetch_encounter(self, encounter_id: str) -> dict[str, Any]:
        resource = self._get(f"/Encounter/{encounter_id}")
        if resource.get("resourceType") != "Encounter":
            raise AdapterError(
                "fhir_unexpected_resource",
                f"expected Encounter, got {resource.get('resourceType')!r}",
            )
        return _normalize_encounter(resource)

    def update_encounter_status(
        self, encounter_id: str, new_status: str, *, changed_by: str
    ) -> dict[str, Any]:
        raise AdapterNotSupported(
            "FHIR adapter does not support write-through encounter "
            "status updates; layer a vendor-specific adapter."
        )

    # ---------- documents ----------
    def write_note(
        self,
        *,
        encounter_id: str,
        author_email: str,
        body: str,
        note_type: str = "progress",
    ) -> dict[str, Any]:
        # The typed transmit_artifact path replaces this seam. Keeping
        # write_note explicit and unsupported avoids accidental callers
        # falling through to a free-text write that skips the phase-25
        # provenance packaging.
        raise AdapterNotSupported(
            "FHIR adapter does not implement free-text write_note; "
            "route signed notes through transmit_artifact which "
            "delivers a full DocumentReference with provenance."
        )

    def transmit_artifact(
        self,
        *,
        artifact: dict[str, Any],
        document_reference: dict[str, Any],
        note_version_id: int,
        encounter_external_ref: str | None,
    ) -> TransmitResult:
        """POST a signed-note DocumentReference to the FHIR server.

        Generic R4 behaviour: any server that accepts POST to
        `/DocumentReference` will persist the resource. Vendor EHRs
        with stricter rules (Encounter linkage, status vocab, auth
        scopes) should layer a vendor-specific adapter on top — its
        `transmit_artifact` can re-shape the resource before calling
        through to this one, or override transport entirely.

        Does NOT raise on HTTP-level failure (4xx / 5xx): those are
        persisted as `failed` `TransmitResult`s so the delivery log
        reflects exactly what the remote system said. Transport-level
        failures (DNS, timeout, bad URL) propagate as AdapterError so
        the service layer can decide between retry and surface-to-UI.
        """
        if document_reference.get("resourceType") != "DocumentReference":
            raise AdapterError(
                "invalid_argument",
                "document_reference must be a FHIR DocumentReference",
            )
        body = json.dumps(document_reference, separators=(",", ":")).encode("utf-8")
        headers = {
            "Accept": "application/fhir+json",
            "Content-Type": "application/fhir+json",
            # Carry the ChartNav provenance in a custom header so the
            # remote system can correlate even if it drops the
            # resource-level identifier.
            "X-ChartNav-Note-Version-Id": str(note_version_id),
            "X-ChartNav-Artifact-Hash": (
                (artifact.get("signature") or {}).get("content_hash_sha256")
                or ""
            ),
        }
        if self._auth_type == "bearer" and self._bearer_token:
            headers["Authorization"] = f"Bearer {self._bearer_token}"
        url = f"{self._base_url}/DocumentReference"

        status_code, response_text, location_header = self._write_transport(
            url, body, headers
        )
        snippet = response_text[:1024] if response_text else None

        remote_id: str | None = None
        if location_header:
            # Location: <base>/DocumentReference/123/_history/1 → grab the id.
            parts = [p for p in location_header.split("/") if p]
            if "DocumentReference" in parts:
                i = parts.index("DocumentReference")
                if i + 1 < len(parts):
                    remote_id = parts[i + 1]
        if remote_id is None and response_text:
            # Some servers return the created resource JSON without a
            # Location header; pluck `.id` if present.
            try:
                parsed = json.loads(response_text)
                if isinstance(parsed, dict) and parsed.get("id"):
                    remote_id = str(parsed["id"])
            except (json.JSONDecodeError, ValueError):
                pass

        if 200 <= status_code < 300:
            return TransmitResult(
                status="succeeded",
                response_code=status_code,
                response_snippet=snippet,
                remote_id=remote_id,
            )
        return TransmitResult(
            status="failed",
            response_code=status_code,
            response_snippet=snippet,
            remote_id=remote_id,
            error_code="fhir_transmit_http_error",
            error_reason=(
                f"FHIR server returned HTTP {status_code} on POST "
                f"/DocumentReference"
            ),
        )

    # ---------- reference sync ----------
    def sync_reference_data(self) -> dict[str, int]:
        # Generic FHIR adapter doesn't know which Practitioners/Locations
        # map into the org. Vendor adapters that DO know override this.
        return {"providers": 0, "locations": 0}
