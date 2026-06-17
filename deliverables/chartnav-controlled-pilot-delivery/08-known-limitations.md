# Known Limitations

**Audience:** Practice clinical owner, administrator, security
owner; ARCG ops + commercial
**Posture:** Honest, customer-facing. Read this before signing
anything in `05-go-no-go-form.md`.

## 1. Fake-data controlled demo only

This delivery package operates against **synthetic seed data**:

- Seeded patient: Morgan Lee · MRN PT-1001 · seeded clinician
  `clin@chartnav.local`.
- Local SQLite database at `apps/api/chartnav.db` (loopback
  only).
- The reset script refuses to run against any non-loopback
  `DATABASE_URL`.

Do **not** evaluate ChartNav against real patient data under
this package.

## 2. Real PHI is not approved

A real-PHI pilot requires the eight blocks in
`06-no-real-phi-attestation.md` Section 4 to close with written,
dated, attributable evidence — plus the in-repo Phase 93
real-PHI readiness review and Phase 18 controlled-pilot go-live
checklist. ChartNav alone cannot authorize real PHI; the
practice's BAA, security review, hosting, identity, logging,
backup, DR, and incident-response approvals are joint
prerequisites.

## 3. Local screenshot / video capture requires extra setup

Optional Playwright-driven screenshots and video clips depend on
three preconditions:

1. `apps/web/node_modules/@playwright/test` installed
   (`cd apps/web && npm ci`).
2. Local stack reachable at `PHASE63C_API_URL` /
   `PHASE63C_WEB_URL`.
3. Chromium installed under `$HOME/.cache/ms-playwright`
   (`cd apps/web && npx playwright install --with-deps chromium`).

If any precondition is missing, the Phase 101 capture script
SKIPs the screenshot row cleanly with the install hint in
`missing-evidence.txt`. Manual screenshots may be dropped into
`artifacts/buyer-demo/<ts>/manual-screenshots/` to fill the gap.

## 4. Demo reset path on some workstations

The default Phase 63C smoke reset path
(`scripts/reset_demo_state.sh` → `make reset-db`) requires
`apps/api/.venv/bin/alembic`. Workstations without that venv must
use the venv-free SQLite seed helper
(`scripts/demo/phase101_local_seed_sqlite.sh`) and run the Phase
101 capture with `PHASE101_SMOKE_RESET=0`. Both paths are
documented in `07-local-demo-operator-commands.md`.

## 5. Provider review required for every clinical artifact

Every vitals workup, visit draft, and fundus chart **must** be
reviewed and signed by the provider before it is final. ChartNav
drafts; the clinician signs. There is no automated signing
surface.

## 6. No autonomous clinical decisions

ChartNav does **not**:

- diagnose
- recommend treatment, surgery, IOL choice, medication changes,
  or imaging modality changes
- interpret fundus photographs, OCT scans, visual fields, or any
  imaging modality

The retina, glaucoma, cataract, and FHIR readiness panels in the
Advanced Clinical Intelligence layer are **metadata projections**
of provider-entered structured data. They display counts and
states, never autonomous conclusions.

## 7. No production EHR writeback

ChartNav lives **alongside** the practice's existing EHR. It does
not write back to the practice's EHR, billing system, or
scheduling system in this build. The Phase 87 FHIR export is
read-only DocumentReference / Encounter; `submission_status` is
pinned to `not_submitted` and `transport` to `none`.

## 8. No payer / registry submission

ChartNav does **not** submit to MIPS, IRIS, CMS, payers, or any
external registry from this build. The Quality Intelligence panel
surfaces specs the provider can review; submission is out of
scope.

## 9. No patient messaging

ChartNav has **no patient-send surface**:

- No email to patients.
- No portal message to patients.
- No SMS / phone integration.
- No automated patient outreach.

The Communications tab is internal-staff-only and persists only
to the operator's local browser.

## 10. No production LLM, no live vendor scripts

Every LLM-shaped surface in this build is deterministic / fake
adapter / disabled. Live STT and live FHIR-write integrations are
gated and not part of any release. Production-LLM enablement is a
separate engineering + vendor-review program.

## 11. Optional intelligence may surface "insufficient data"

The Advanced Clinical Intelligence panel and the per-eye lanes
(retina, glaucoma, cataract) explicitly render `Insufficient
data` banners when no structured data exists for the seeded
patient. This is intentional — ChartNav never synthesizes values.

## 12. Demo identities are clearly fake

`@chartnav.local` identities are present **only** in the
synthetic seed. They must be disabled before any real-PHI go-live
(production OIDC issuer + audience required) — see
`06-no-real-phi-attestation.md` Section 4.4.

## 13. Browser unsigned-app warning (macOS)

The packaged macOS app is **unsigned** for the controlled-pilot
package; right-click → Open is required to launch it. A signed
build is a separate engineering deliverable and is not part of
this package.
