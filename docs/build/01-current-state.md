# ChartNav — Current State

**As of:** 2026-04-18 (phase: external encounter → native workflow bridge)

## Repo layout (relevant)

```
chartnav-platform/
├── .github/workflows/{ci.yml,release.yml}
├── Makefile
├── scripts/                 # build_docs · verify · pg_verify · release_build · staging_*
│                            # audit_retention · sbom
├── apps/
│   ├── api/
│   │   ├── app/
│   │   │   ├── main.py · config.py · db.py · auth.py · authz.py
│   │   │   ├── audit.py · retention.py · logging_config.py · middleware.py · metrics.py
│   │   │   ├── integrations/    # adapter boundary (phase 16)
│   │   │   │   ├── __init__.py  # resolve_adapter + vendor registry (FHIR registered)
│   │   │   │   ├── base.py      # ClinicalSystemAdapter protocol + errors
│   │   │   │   ├── native.py    # NativeChartNavAdapter (patient/provider ops, phase 18)
│   │   │   │   ├── stub.py      # StubClinicalSystemAdapter
│   │   │   │   └── fhir.py      # FHIRAdapter — FHIR R4 read-through (phase 18)
│   │   │   ├── services/        # domain service seam (phase 19)
│   │   │   │   └── note_generator.py  # regex fake today; LLM slot in, shape locked
│   │   │   └── api/routes.py    # + /inputs + /notes/generate + /note-versions/* (phase 19)
│   │   ├── alembic/versions/    # 9 migrations through b8c9d0e1f203
│   │   ├── tests/               # 196 pytest (+11 encounter bridge)
│   │   └── Dockerfile · entrypoint.sh · .env.example
│   └── web/
│       ├── src/
│       │   ├── App.tsx · AdminPanel.tsx · InviteAccept.tsx · api.ts
│       │   ├── identity.ts · styles.css · main.tsx
│       │   ├── NoteWorkspace.tsx  # 3-tier trust model UI (phase 19)
│       │   └── test/            # 44 Vitest (+2 source-of-truth UI)
│       ├── public/brand/        # ChartNav logo + mark + favicon SVGs (phase 17)
│       └── tests/e2e/
│           ├── workflow.spec.ts (12)
│           ├── a11y.spec.ts (5)   # axe-core — hard gate in CI
│           └── visual.spec.ts (4) # screenshot regression — local only
├── infra/docker/{dev,prod,staging}.yml
└── docs/build/ 01 … 28
```

## Runtime baseline

- Backend: FastAPI + SQLAlchemy Core + PyJWT.
- Frontend: Vite 5 + React 18 + TypeScript + Vitest + Playwright.
- Auth: `header` (dev) or `bearer` (prod JWT via JWKS).
- RBAC: `admin` / `clinician` / `reviewer` (CHECK-constrained).
- Error envelope: `{"detail": {"error_code": "...", "reason": "..."}}`.
- **a11y**: axe-core baseline covering app shell, encounter list/detail, admin panel, invite page. `serious`/`critical` violations are blocking.
- **Visual regression**: 4 macOS-baseline screenshots; `maxDiffPixelRatio: 0.02`. Local gate; CI skips (OS-specific pixels).
- **Admin list scaling**: `GET /users`/`/locations` now take `limit`, `offset`, `q`, role (+users). `X-Total-Count` headers. UI has search + Prev/Next pagers on Users + Locations tabs.
- **Feature flags**: `organization.settings.feature_flags.audit_export` and `.bulk_import` actually gate the corresponding admin buttons.
- **Audit retention**: `scripts/audit_retention.py` prunes old rows per `CHARTNAV_AUDIT_RETENTION_DAYS`; the app never silently prunes.
- **Release compliance**: SBOM (`chartnav-sbom-<v>.json`) + image digest (`chartnav-api-<v>.digest.txt`) in every release bundle, attached to the GitHub Release.
- **Platform mode** (phase 16): `CHARTNAV_PLATFORM_MODE` ∈ {`standalone`, `integrated_readthrough`, `integrated_writethrough`}. Adapter boundary (`ClinicalSystemAdapter`) separates ChartNav core from any external EHR/EMR. Ships `NativeChartNavAdapter` (standalone) + `StubClinicalSystemAdapter` (integrated placeholder) + **`FHIRAdapter`** (phase 18). Vendor adapters plug in via `register_vendor_adapter`. Config fails loudly on misconfig. `GET /platform` surfaces mode + adapter + source-of-truth to the UI.
- **Native clinical layer** (phase 18): `patients` and `providers` tables are org-scoped, soft-active, and carry `external_ref` for integrated-mode mirroring. `encounters.patient_id` + `encounters.provider_id` are nullable FKs so the legacy text fields (`patient_identifier`, `provider_name`) continue to render. Standalone mode persists and queries via the native adapter; `integrated_readthrough` refuses native writes with a clear error code.
- **FHIR adapter** (phase 18): real R4 read-through over a pluggable transport. Normalizes Patient + Encounter resources into ChartNav's internal shape (status mapping, participant display, MRN extraction, birthDate/gender passthrough). Write paths raise `AdapterNotSupported` honestly. Config: `CHARTNAV_FHIR_BASE_URL`, `CHARTNAV_FHIR_AUTH_TYPE`, `CHARTNAV_FHIR_BEARER_TOKEN`.
- **External encounter → native workflow bridge** (phase 21): `POST /encounters/bridge` get-or-creates a native `encounters` row keyed on `(organization_id, external_ref, external_source)` for externally-sourced encounters. Idempotent. Preserves the phase-20 contract — the external EHR still owns encounter state; the bridge only unlocks ChartNav-native workflow (transcript → findings → draft → sign → export). Refused in standalone mode. Frontend surfaces a **Bridge to ChartNav** action on external encounter detail; after bridging, the encounter flips to `_source="chartnav"` and the full `NoteWorkspace` is available.
- **Adapter-driven encounters** (phase 20): `GET /encounters` and `GET /encounters/{id}` dispatch through the resolved adapter. Standalone → native adapter (same SQL as before). Integrated → adapter-owned rows tagged `_source` (`chartnav` / `fhir` / `stub` / vendor). Write gating is mode-aware: `POST /encounters` returns 409 `encounter_write_unsupported` in both integrated modes; `POST /encounters/{id}/status` returns 409 in read-through and dispatches through the adapter in write-through (501 `adapter_write_not_supported` when the adapter raises `AdapterNotSupported`). Frontend surfaces a source-of-truth chip + SoT banner; status controls and the note workspace are suppressed on external encounters.
- **Transcript → note drafting → signoff** (phase 19): three org-scoped tables (`encounter_inputs`, `extracted_findings`, `note_versions`), a note-generator service seam at `app/services/note_generator.py` (deterministic fake today; LLM plugs in at one function, output contract locked), provider review workspace in the frontend with three visually distinct trust tiers (transcript → findings → draft → signed), status state machine (`draft → provider_review → revised → signed → exported`), immutability after sign, audit events on every meaningful action, text download + clipboard export.
- **Brand alignment** (phase 17): product UI uses the ChartNav marketing site's exact token set (`--cn-*`). Inter typography, teal `#0B6E79` primary, real logo SVG in the header, subtle `Powered by ARCG Systems` footer. Axe-AA contrast preserved.
- **Domain**: `chartnav.ai` → `https://arcgsystems.com/chartnav/` via GoDaddy 301 forwarding (external) + in-repo host-based safety-net in `arcg-live`. Runbook: `arcg-live/docs/chartnav-ai-domain-runbook.md`.
- Alembic head: `b8c9d0e1f203` (phase 21 — encounters.external_ref + external_source + unique bridge constraint).

## Testing layers

| Layer                | Tool         | Count | Notes |
|----------------------|--------------|:-----:|-------|
| pytest               | pytest       |  196  | +11 encounter bridge (idempotent get-or-create + full wedge on bridged row) |
| shell smoke          | smoke.sh     |   9   | unchanged |
| Vitest               | vitest       |  45   | +1 bridge-button dispatches bridgeEncounter |
| Playwright workflow  | @playwright  |  12   | unchanged contract |
| Playwright a11y      | @axe-core/playwright | 5 | NEW |
| Playwright visual    | Playwright snapshots | 4 | NEW (local only) |
| staging              | staging_verify.sh | 9 | unchanged |

## Verified working endpoints

No new endpoints this phase. `GET /users` and `GET /locations` gained
`q`/`role`/`limit`/`offset` query parameters + pagination headers;
older callers that pass no params still see the first 100 rows.

## Automation

- `make verify` → 196 pytest + 9 smoke
- `make web-verify` → 45 vitest + typecheck + build
- `make e2e` → 12 workflow + 5 a11y + 4 visual (local)
- `make e2e-a11y` / `make e2e-visual` / `make e2e-visual-update`
- `make audit-prune ARGS="--days 90 --dry-run"`
- `make sbom` → `dist/release/_sbom.json`
- `make pg-verify` / `make staging-*` / `make release-build VERSION=v0.1.0`
- `make dev` — backend + frontend together
- CI: backend-sqlite + frontend + deploy-config in parallel; e2e (workflow + a11y) gates on backend + frontend; backend-postgres + docker-build + docs chain on backend-sqlite.
