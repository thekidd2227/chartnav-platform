# ChartNav — Controlled Pilot Delivery (README FIRST)

**Audience:** ARCG operator + prospective ophthalmology pilot
practice (clinical owner, administrator, security/CISO)
**Build SHA:** see `artifacts/manifest.txt` (written when the
operator runs the Phase 100 launch gate)
**Posture:** Controlled fake-data pilot. **Not approved for real
PHI** by this package alone.

## What ChartNav is

ChartNav is **provider-reviewed ophthalmology workflow support**.
It helps a practice capture, draft, review, and sign clinical
artifacts (vitals → visit draft → fundus chart) and surfaces
longitudinal intelligence (retina, glaucoma, cataract, FHIR
export readiness) — all from provider-entered structured data.

ChartNav is **not**:

- a certified electronic health record
- a replacement for the practice's existing EHR
- HIPAA-certified, SOC 2-certified, HITRUST-certified, or
  FDA-cleared
- an autonomous-diagnosis, image-interpretation, treatment-
  recommendation, IOL-recommendation, prescription, orders,
  billing, coding, claims-submission, EHR-writeback, or patient-
  messaging surface

These non-claims are enforced by automated safety scanners on
every release.

## What this package contains

This delivery folder is the operator's hand-to-the-practice
bundle for a **controlled fake-data pilot**. Open the files in
order:

| # | File | Audience |
|---|---|---|
| 0 | `README-FIRST.md` (this file) | Everyone |
| 1 | `00-executive-summary.md` | Practice clinical / admin / CISO |
| 2 | `01-controlled-demo-scope.md` | Practice + ARCG ops |
| 3 | `02-buyer-demo-runbook.md` | ARCG operator |
| 4 | `03-demo-talk-track.md` | ARCG operator |
| 5 | `04-evidence-index.md` | Practice CISO + ARCG ops |
| 6 | `05-go-no-go-form.md` | All signers |
| 7 | `06-no-real-phi-attestation.md` | Practice CISO + ARCG legal |
| 8 | `07-local-demo-operator-commands.md` | ARCG operator |
| 9 | `08-known-limitations.md` | Practice + ARCG ops |
| 10 | `09-next-steps-for-practice.md` | Practice + ARCG commercial |
| 11 | `artifacts/README.md` + artifacts/ | Practice CISO |

## Controlled fake-data scope

This package authorizes **fake-data demos only**. The local
demo stack runs against synthetic seed data:

- Local SQLite database at `apps/api/chartnav.db` (loopback only).
- Seeded patient: Morgan Lee · MRN PT-1001 · seeded clinician
  `clin@chartnav.local`.
- Production LLM and live vendor APIs are disabled.

The reset script refuses to run against any non-loopback
`DATABASE_URL`. Demo identities are clearly fake.

## Real-PHI boundary

Real PHI is **not approved** by this package. A practice that
wishes to move from a fake-data demo to a real-PHI controlled
pilot must close every gate in:

- `06-no-real-phi-attestation.md` (the eight required blocks)
- `docs/security/phase-93-real-phi-readiness-review.md` (in the
  repo)
- `docs/pilot/chartnav-controlled-pilot-go-live-checklist.md` (in
  the repo)

with written, dated, attributable evidence. ARCG and the practice
sign jointly.

## How to run demo evidence

ARCG operator workflow (one terminal):

```bash
# 1. From a clean clone of the repo on a workstation:
cd "$HOME/Desktop/ARCG/chartnav-platform"
git checkout main && git pull --ff-only origin main

# 2. Seed local fake-data DB (venv-free; works on a fresh machine):
bash scripts/demo/phase101_local_seed_sqlite.sh

# 3. Start API on 8765 + Web on 5173 (two shells — see
#    07-local-demo-operator-commands.md for the full block).

# 4. Run the release-side launch gate:
bash scripts/release/phase100_controlled_pilot_launch_gate.sh

# 5. Run the buyer-demo evidence capture (no-reset path):
PHASE101_SMOKE_RESET=0 \
PHASE63C_API_URL="http://127.0.0.1:8765" \
PHASE63C_WEB_URL="http://127.0.0.1:5173" \
bash scripts/demo/phase101_mcp_independent_demo_capture.sh
```

Both gate runs write dated bundles under `artifacts/` (in the
repo). The Phase 101 capture writes `summary.txt` +
`no-real-phi-attestation.txt` + `missing-evidence.txt` you can
hand to the practice's CISO.

## Who must approve a real-PHI pilot later

| Role | Required for fake-data pilot? | Required for real-PHI pilot? |
|---|---|---|
| Practice clinical owner | yes | yes |
| Practice administrator | yes | yes |
| Practice security owner / CISO | no | **yes** |
| ARCG ops owner | yes | yes |
| ARCG commercial owner | yes | yes |
| ARCG legal | no | **yes** |

Real-PHI requires a signed BAA, an accepted security review
packet, a production OIDC issuer + audience, production-grade
Postgres with backups + PITR, a practice-approved log
destination, a backup + DR rehearsal within 90 days, an incident
response runbook walk-through, and the practice's written
go-live approval.

## Exact first command for the ARCG operator

```bash
cd "$HOME/Desktop/ARCG/chartnav-platform" \
  && git checkout main && git pull --ff-only origin main \
  && bash scripts/demo/phase101_local_seed_sqlite.sh
```

If that succeeds (`[phase101-local-seed] PASS  apps/api/chartnav.db seeded`),
proceed to `07-local-demo-operator-commands.md` for the rest.
