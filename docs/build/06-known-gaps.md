# Known Gaps & Verification Matrix

## Verification evidence — phase 14

### Local gates

| Gate                                        | Result |
|---------------------------------------------|--------|
| `make verify` (backend)                     | ✅ **110/110 pytest + 9/9 smoke** |
| `cd apps/web && npx tsc --noEmit`           | ✅ clean |
| `cd apps/web && npx vitest run`             | ✅ **25/25** |
| `cd apps/web && npm run build`              | ✅ 184 KB JS / 8.2 KB CSS |
| `cd apps/web && npx playwright test`        | ✅ **12/12** in ~15s |
| `apps/api/.venv/bin/python scripts/build_docs.py` | ✅ HTML + PDF |

### pytest summary (110)

| Suite                       | Count | Notes |
|-----------------------------|:-----:|-------|
| `test_admin.py`             | 20    | admin governance (phase 12) |
| `test_auth.py`              | 5     | header mode |
| `test_auth_modes.py`        | 11    | real JWT bearer |
| `test_control_plane.py`     | 19    | org settings + audit read + invited_at (phase 13 updated for typed settings) |
| `test_invitations.py` ✦     | **20**| **invitations + audit export + event hardening + bulk users (phase 14)** |
| `test_observability.py`     | 3     | `/ready`, `/metrics` |
| `test_operational.py`       | 12    | request id, audit, rate limit, CORS |
| `test_rbac.py`              | 12    | role-gated writes + per-edge transitions |
| `test_scoping.py`           | 8     | org scoping |

### Vitest summary (25)

| File                       | Count | Notes |
|----------------------------|:-----:|-------|
| `App.test.tsx`             | 13    | unchanged |
| `AdminPanel.test.tsx`      | 12    | +3 (invite / bulk summary / audit export) on top of phase 13 |

### Playwright summary (12)

Adds "admin can issue an invitation and download audit CSV" on top of
the 11 scenarios shipped through phase 13.

## Phase-21 additions

- **External encounter → native workflow bridge**: `POST /encounters/bridge` creates/resolves a native row keyed on `(org, external_ref, external_source)`. Idempotent. Frontend bridge button on external encounter detail.
- **Full wedge on bridged row**: transcript ingest + findings + note generate + sign + export all work identically to standalone after bridging.
- **Phase-20 contract preserved**: bridging does NOT reopen encounter state writes — external EHR still owns status in integrated_readthrough.
- **196 pytest** (+11), **45 Vitest** (+1), 17 Playwright + 4 visual (local, refreshed).

## Phase-20 additions

- **Adapter-driven encounter reads**: `/encounters` and `/encounters/{id}` dispatch through `resolve_adapter()`; standalone uses native (same SQL), integrated uses stub/FHIR/vendor. Rows tagged `_source` end-to-end.
- **FHIR encounter list/normalization**: `GET /Encounter?_count=&status=<mapped>` with ChartNav→FHIR status translation.
- **Integrated write gating**: `POST /encounters` refused in both integrated modes (409 `encounter_write_unsupported`); `POST /encounters/{id}/status` refused in readthrough, adapter-dispatched in writethrough (FHIR raises `AdapterNotSupported` → 501 `adapter_write_not_supported`).
- **Frontend SoT UI**: source chip + SoT banner + suppressed transitions + suppressed NoteWorkspace on external encounters; helpers `encounterIsNative` and `encounterSourceLabel`.
- **185 pytest** (+11), **44 Vitest** (+2), 17 Playwright, 4 visual (local, refreshed).

## Phase-19 additions

- **Transcript ingestion**: `encounter_inputs` table + `POST/GET /encounters/{id}/inputs`. Supports `audio_upload` (queued → future STT), `text_paste`, `manual_entry`, `imported_transcript`.
- **Extracted findings**: `extracted_findings` table — structured ophthalmology facts persisted separately from narrative. Confidence + missing-data flags feed the UI's provider-verify checklist.
- **Note versioning**: `note_versions` table with status machine (`draft → provider_review → revised → signed → exported`), immutability after sign, version_number monotonic per encounter, audit trail on every action.
- **Provider review UI**: three-tier `NoteWorkspace` (transcript → findings → draft + signoff) embedded in the encounter detail pane. Reviewer role cannot sign (UI + API).
- **Generator seam**: `app/services/note_generator.py` — deterministic fake today, LLM slot locked at one function, output contract stable.
- **Export/handoff**: text download + clipboard copy + `exported_at` stamp. No EHR write-back (honest: vendor adapters are future work).
- **174 pytest** (+19), **42 Vitest** (+8), 17 Playwright workflow+a11y + 4 visual (local, refreshed).

## Phase-18 additions

- **Native clinical layer**: `patients` + `providers` tables (migration `f6a7b8c9d0e1`); `encounters.patient_id` + `encounters.provider_id` nullable FKs; seed populates real rows and backfills legacy encounters.
- **First real external adapter**: `FHIRAdapter` — generic FHIR R4 read-through (Patient + Encounter). Pluggable transport; bearer auth; honest `AdapterNotSupported` on writes.
- **API**: `GET/POST /patients`, `GET/POST /providers` with mode-aware write gating (`native_write_disabled_in_integrated_mode` in read-through).
- **Frontend**: Patients + Providers admin tabs; integrated_readthrough surfaces a source-of-truth banner and hides create forms.
- **155 pytest** (+24), **34 Vitest** (+3), 17 Playwright + 4 visual (local; refreshed).

## Phase-17 additions

- **Brand-aligned UI**: `--cn-*` token system lifted from the ChartNav marketing site, real logo SVG in the header, Inter typography, subtle "Powered by ARCG Systems" footer, AA-safe muted text (`#475569`). Legacy token names kept as aliases — no component-level rewrites.
- **`chartnav.ai` domain**: safety-net host-based redirect in `arcg-live` (`index.html` + `public/404.html`). Primary 301 mechanism is GoDaddy forwarding, documented in `arcg-live/docs/chartnav-ai-domain-runbook.md`.
- **31 Vitest** (+1), **17 Playwright workflow+a11y**, **4 visual (local)** — visual baselines deliberately regenerated for the new brand look.

## Phase-16 additions

- **Platform modes**: `CHARTNAV_PLATFORM_MODE` wired — `standalone` / `integrated_readthrough` / `integrated_writethrough`. Config validates and refuses impossible combinations at import time.
- **Adapter boundary**: `app/integrations/` with `ClinicalSystemAdapter` protocol + `NativeChartNavAdapter` + `StubClinicalSystemAdapter`. Vendor adapters plug in via `register_vendor_adapter`.
- **`GET /platform`**: surfaces mode + adapter + source-of-truth. Admin panel renders a mode banner.
- **131 pytest** (+13 platform). **30 Vitest** (+2 platform banner). Playwright unchanged.
- **CI hardening rolled in with this phase**: migration boolean default portability (SQLite → Postgres) + vitest lockfile regen (Linux/Node 20). Both reproduced locally against docker postgres and `node:20` container; both now green.

## Phase-15 additions

- **a11y**: 5 axe-core scenarios in CI (`serious`/`critical` blocking). Fixed: event-type `<select>` and inline admin role `<select>` now have aria-labels.
- **Visual regression**: 4 macOS baselines; `make e2e-visual` locally; not in CI (see below).
- **Admin list scaling**: `GET /users`/`/locations` gained `limit`/`offset`/`q`/`role`; UI adds search + pager.
- **Feature flags**: `audit_export` and `bulk_import` in `feature_flags` actually hide the corresponding admin UI buttons (frontend-tested).
- **Retention**: `scripts/audit_retention.py` + `CHARTNAV_AUDIT_RETENTION_DAYS` env; backend tests cover disabled / dry-run / delete.
- **Release compliance**: `chartnav-sbom-<v>.json` + `chartnav-api-<v>.digest.txt` are produced by `release_build.sh` and attached to the GitHub Release.

## Real gaps (prioritized for next phase)

0. **No real LLM wired into the note generator yet** — `app/services/note_generator.py` ships a deterministic regex + SOAP-template fake. The seam is a single function; output contract is locked. Next: swap for a real inference endpoint (or SMART-on-FHIR-aware model).
0. **No audio STT worker** — `audio_upload` inputs stay `queued` forever. Future work: a background worker that fills `transcript_text` and flips processing_status.
0. **No EHR write-back for signed notes** — export is download + clipboard only. FHIR `DocumentReference` writes remain `AdapterNotSupported`; vendor adapters layer real push.
0. **No PDF or HL7 export** — plain text only. Deliberate: honest paste-into-EHR, not a vendor-format we don't own.
0. **No SMART-on-FHIR auth** on the FHIR adapter — `auth_type=bearer` takes a pre-provisioned token. Full SMART launch flow is future work.
0. **No vendor-specific FHIR writer** — generic adapter refuses with `AdapterNotSupported`; 501 surfaces honestly. Epic / Cerner / Athena writers plug in via the registry.
0. **~~No integrated-mode note drafting~~** — **resolved in phase 21**. `POST /encounters/bridge` creates a native row tied to the external one; the full wedge (transcript → findings → draft → sign → export) runs on bridged rows.
0. **No automatic background sync** of external encounter state onto bridged rows — the mirror happens at bridge-time only. A dedicated sync worker is the next natural step.
0. **~~Encounter/status routes still bypass the adapter path~~** in integrated modes — HTTP handlers hit the native DB directly rather than routing through `resolve_adapter()`. Standalone this is a nop (native adapter wraps the same DB); integrated_* needs the handler-level adapter dispatch + translation work in a follow-up phase so FHIR reads can actually surface through `/encounters`.
0. **No vendor-specific FHIR adapter yet** — generic `FHIRAdapter` handles the common case. Epic/Cerner/Athena/Nextech SMART-on-FHIR auth + vendor quirks remain future work. Start with SMART-on-FHIR handshake + Epic sandbox.
0. **FHIR writes are intentionally unsupported** — `update_encounter_status` and `write_note` raise `AdapterNotSupported`. `DocumentReference` + Binary upload is a real project and belongs in a vendor adapter.
0. **No patient chart UI** — Patients tab lists rows and supports create. There's no detail view, encounter-by-patient view, or scheduling surface. Product decision, not a technical one.
0. **Legacy `encounters.provider_name` text isn't automatically reconciled** against the new `providers` table. Operators re-seed or run targeted UPDATEs to backfill `provider_id` for historical rows.

1. **No email delivery** for invitations — admin manually shares the token.
2. **No SSO → users mapping change** (still by `CHARTNAV_JWT_USER_CLAIM`).
3. **Metrics + rate limiter per-process** — multi-worker still needs coordination.
4. **No OpenTelemetry / distributed tracing.**
5. **No log shipping / retention** defined; no audit-table archival.
6. **No CSV export for users or locations** (audit export only).
7. **Forward-only migrations** (acknowledged policy).
8. **No automated staging deploy from CI**.
9. **No signing / SBOM / provenance** on release artifacts.
10. **No JWKS-rotation test, no refresh-token / revocation flow.**
11. **No org-level slug change** (intentional).
12. **No feature-flag consumer yet** — the settings field exists but the app doesn't read it.
13. **No pagination/search on users and locations lists** (fine at current scale).
14. **No visual-regression / a11y audits**.
15. **pytest matrix on Postgres** not wired (fixture env-driven, ready to flip).
16. **No invite-accept screen polish** (redirect to main app on success, proper routing, a11y review) — only the minimal success banner exists.
