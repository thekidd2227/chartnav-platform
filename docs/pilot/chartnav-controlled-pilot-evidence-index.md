# ChartNav Controlled-Pilot Evidence Index

**Status:** living document — updated per release
**Last updated:** 2026-06-10
**Repo SHA at writing:** `main` after Phase 87 (FHIR Export Layer)
**Phase context:** Phase 88 — Release Hardening + Pilot Evidence Gate

## Purpose

The independent Manus audit observed that ChartNav's buyer-facing
evidence is scattered across many phase documents, each of which is
authoritative in its own slice but none of which gives a buyer / pilot
reviewer a single current-truth answer to "what is this product, what
is built, what is not, and how do I evaluate it safely?"

This document is that single index. Each section is a short
description plus a link to the authoritative source in this repo.

## 1. Product scope

ChartNav is a **provider-reviewed ophthalmology workflow support**
platform with a controlled fake-data demo posture. It supports the
ophthalmology operating loop with structured documentation,
deterministic readiness signals, audit-ready metadata, and a narrow
read-only FHIR R4 export.

ChartNav is **not** any of these:

- a certified electronic health record
- a replacement for the practice's existing EHR
- a HIPAA-compliant / HIPAA-certified product (the policy and
  technical work for that is a separate program)
- an autonomous-diagnosis / autonomous-treatment / autonomous-image-
  interpretation surface
- a billing, coding, claims-submission, or patient-messaging
  platform

These non-claims are enforced by the scanner suite under `scripts/`
and by the claim-fixture suite under `tests/claim_fixtures/`.

## 2. What is built

Phase-by-phase reality (Phase 1 Clinical Spine + Phase 2 Clinical
Intelligence + Phase 87 FHIR Export):

| Surface | Phase | Doc |
|---|---|---|
| Vitals workup | 60 | `docs/build/` |
| Scribe + visit drafts | 65–75 | `docs/build/` |
| Fundus charts (provider-entered findings, never image interpretation) | 56 / 72 | `docs/build/` |
| Provider review + signed lock + audit trail | 73 | `docs/build/phase-73-provider-review-signed-lock-audit-trail.md` |
| Imaging pipeline (metadata + review workflow; no image binaries) | 21B | `docs/build/` |
| Retina visit summary aggregator + cross-artifact metadata-only timeline | 76 | `docs/build/phase-76-retina-visit-summary-aggregator.md` |
| Retina visit packet export | 77 | `docs/build/phase-77-retina-visit-packet-export.md` |
| Anti-VEGF retina operating rail | 78 | `docs/build/phase-78-anti-vegf-retina-operating-rail.md` |
| Glaucoma progression cockpit | 79 | `docs/build/phase-79-glaucoma-progression-cockpit.md` |
| Cataract surgical workflow | 80 | `docs/build/phase-80-cataract-surgical-workflow.md` |
| Provider action item queue (cross-specialty aggregator) | 81 | `docs/build/phase-81-provider-action-item-queue.md` |
| Note validation rail (deterministic checks) | 82 | `docs/build/phase-82-note-validation-rail.md` |
| Acknowledgement persistence + audit trail | 83 | `docs/build/phase-83-pre-sign-acknowledgement-persistence.md` |
| Disease staging protocol engine | 84 | `docs/build/phase-84-disease-staging-protocol-engine.md` |
| Ophthalmic medication safety + adherence | 85 | `docs/build/phase-85-medication-safety-adherence-engine.md` |
| Subspecialty adaptive workspace | 86 | `docs/build/phase-86-subspecialty-adaptive-workspace.md` |
| FHIR R4 read-only export layer | 87 | `docs/build/phase-87-fhir-export-layer.md` |

Every surface above carries a documented safety boundary — the
phase doc states what ChartNav explicitly does NOT do for that
surface. Buyers should read the safety-boundary section of any
surface they intend to evaluate.

## 3. What is intentionally NOT built

- No DICOM ingestion / no HL7 v2 message interfaces.
- No live device integration / no autonomous image classification.
- No EHR write-back.
- No bulk FHIR export ($export, NDJSON).
- No SMART-on-FHIR / OAuth provider flow.
- No production LLM autonomous decision-making.
- No autonomous billing / coding / claims submission.
- No autonomous patient messaging.
- No certified-EHR feature surface.

## 4. Controlled demo posture

ChartNav runs against a deterministic fake-data seed for every
buyer demo. The seed is reproducible (`scripts/reset_demo_state.sh`)
and the demo stack is documented at
`docs/demo/`. The Phase 63C functional smoke
(`scripts/demo/phase63c_functional_smoke.sh`) is the canonical
"does the demo work?" command and is exercised in CI and locally.

No real PHI is processed in the demo posture. The
"This packet was generated from the local fake-data demo
environment" assertion in every retina visit packet
(`apps/api/app/services/retina_visit_packet.py` `SAFETY_BOUNDARIES`)
is the contract.

## 5. Real-PHI gate

A separate readiness program governs the move from the controlled
demo posture to a real-PHI pilot:

`docs/security/chartnav-real-phi-readiness-status.md`

That document is the source of truth for which controls are open vs
closed. No buyer should infer real-PHI readiness from this index —
read the readiness status directly.

## 6. Security review prerequisites

`docs/pilot/chartnav-security-review-packet.md` covers the
prerequisites a practice's security reviewer should walk before any
pilot. Items include:

- BAA preconditions (real PHI is gated behind a BAA program; this
  build does not process real PHI).
- Network posture (controlled-pilot Postgres, validated env
  scripts).
- Org isolation (every endpoint enforces caller-org scoping;
  cross-org returns 404 to prevent existence leak).
- Audit trail (`security_audit_events` is append-only; the
  Phase 73 + Phase 83 contracts are tested).
- Secrets posture (no production secrets in the repo; controlled
  pilot env vars validated by
  `scripts/validate_controlled_pilot_env.sh`).

## 7. Deployment assumptions

`docs/pilot/chartnav-pilot-deployment-guide.md` is the deployment
runbook. Summary:

- Backend: FastAPI on Python 3.11, SQLAlchemy Core, alembic. SQLite
  for the demo posture; Postgres for the controlled pilot.
- Frontend: React 18 + Vite 5 + TypeScript. Static build served by
  the deployment of the operator's choice.
- Infrastructure: docker-compose for the controlled pilot lab; no
  managed-cloud claim. Docker production images build green in CI.

## 8. Claim boundaries

Every public claim ChartNav makes is gated by the scanner suite:

| Scanner | What it scans | Source of truth |
|---|---|---|
| `check_commercial_claims.sh` | `docs/commercial/`, decks, demo package | `tests/claim_fixtures/` |
| `check_demo_claims.sh` | `docs/demo/` | same |
| `check_website_claims.sh` | `docs/website/`, landing copy, i18n | same |
| `check_live_site_claims.sh` | a captured `chartnavmd.com` HTML snapshot | same |
| `test_claim_policy_fixtures.sh` | the fixture suite itself | `tests/claim_fixtures/` |
| `check_runtime_safety.py` | runtime safety combinations | `apps/api/app/services/` |

The Phase 88 release-evidence gate
(`scripts/release/chartnav_release_evidence_gate.sh`) runs all of
them.

## 9. Test evidence commands

The release-grade evidence run is one command:

```bash
bash scripts/release/chartnav_release_evidence_gate.sh
```

It writes a dated artifact directory under
`artifacts/release-evidence/YYYYMMDD-HHMMSS/` carrying:

- `summary.txt` — PASS/FAIL per check + total runtime.
- per-check stdout/stderr logs.
- the exact next recovery command for any failure.

Individual evidence commands a reviewer may want:

```bash
# Backend release gate (tiered, fail-fast, no hangs).
bash scripts/release/backend_release_gate.sh

# Frontend tsc + vitest.
cd apps/web && npx tsc --noEmit && npx vitest run

# Live-site claims snapshot (operator-run; pre-publish + weekly).
bash scripts/release/check_live_site_claims_snapshot.sh

# Phase 63C functional smoke (requires local stack).
PHASE63C_API_URL="http://127.0.0.1:8765" \
PHASE63C_WEB_URL="http://127.0.0.1:5173" \
bash scripts/demo/phase63c_functional_smoke.sh --reset
```

## 10. Known limitations

- Frontend dev-dependency posture: 2 moderate npm-audit advisories
  remain (vite ≤ 6.4.1 + esbuild ≤ 0.24.2). The fix path is a
  separately-sequenced vite 5 → 8 major upgrade. See
  `docs/build/phase-88-dependency-hardening-notes.md` for the
  mitigation rationale.
- FHIR Export Layer is **read-only**. No write-back, no bulk
  export, no SMART discovery. See
  `docs/build/phase-87-fhir-export-layer.md`.
- Subspecialty adaptive workspace **never hides data**. Collapsed
  panels remain accessible via a `<details>` element. See
  `docs/build/phase-86-subspecialty-adaptive-workspace.md`.
- The retina visit packet is reproducible (same encounter state →
  same packet) modulo `generated_at`. The Phase 87 FHIR
  DocumentReference carries a sha256 integrity envelope.

## 11. Pilot entry criteria

Before signing a controlled pilot agreement:

1. Buyer has read this index end-to-end.
2. Buyer has read `docs/pilot/chartnav-known-limitations-and-non-goals.md`.
3. Buyer has read `docs/security/chartnav-real-phi-readiness-status.md`
   and the readiness gates relevant to their environment are either
   met or scheduled.
4. The most recent release-evidence gate run is dated within 14 days
   and is PASS.
5. The most recent live-site claims snapshot is dated within 7 days
   and is PASS.
6. A BAA is signed if real PHI is in scope.
7. A security reviewer has walked the security review packet.
8. ChartNav has a named operator on call for the pilot.

## 12. Pilot no-go criteria

ChartNav should NOT enter a pilot under any of these conditions:

- The buyer expects autonomous diagnosis, autonomous imaging
  interpretation, autonomous orders, autonomous billing, or
  autonomous patient messaging.
- The buyer expects EHR replacement.
- The buyer expects HIPAA / SOC 2 / FDA / GDPR certification today.
- A BAA is required and not yet signed.
- The release-evidence gate or the live-site claims snapshot is
  failing.
- The buyer's deployment environment is not covered by the
  pilot deployment guide.

If any of the above is true at evaluation time, ChartNav should
defer the pilot rather than weaken any of the safety contracts to
fit.

## 13. Authoritative current docs

This index intentionally links only the current-truth documents.
Older planning notes / interim decision memos live under
`docs/build/` and `docs/decks/`; they are not buyer-facing.

- `docs/security/chartnav-real-phi-readiness-status.md` — real-PHI
  readiness gate.
- `docs/security/chartnav-org-isolation-and-cross-tenant-leak-prevention.md`
- `docs/pilot/chartnav-pilot-readiness-checklist.md`
- `docs/pilot/chartnav-pilot-deployment-guide.md`
- `docs/pilot/chartnav-admin-onboarding-checklist.md`
- `docs/pilot/chartnav-security-review-packet.md`
- `docs/pilot/chartnav-support-runbook.md`
- `docs/pilot/chartnav-known-limitations-and-non-goals.md`
- `docs/pilot/chartnav-pilot-success-metrics.md`
- `docs/website/chartnav-public-claims-drift-policy.md`
- `docs/website/chartnav-live-site-claims-scan-runbook.md`
- `docs/commercial/chartnav-approved-claims-language.md`
- `docs/build/phase-87-fhir-export-layer.md`
- `docs/build/phase-86-subspecialty-adaptive-workspace.md`
- `docs/build/phase-85-medication-safety-adherence-engine.md`
- `docs/build/phase-84-disease-staging-protocol-engine.md`
- `docs/build/phase-83-pre-sign-acknowledgement-persistence.md`
- `docs/build/phase-82-note-validation-rail.md`
- `docs/build/phase-81-provider-action-item-queue.md`
- `docs/build/phase-80-cataract-surgical-workflow.md`
- `docs/build/phase-79-glaucoma-progression-cockpit.md`
- `docs/build/phase-78-anti-vegf-retina-operating-rail.md`
- `docs/build/phase-77-retina-visit-packet-export.md`
- `docs/build/phase-76-retina-visit-summary-aggregator.md`
- `docs/build/phase-73-provider-review-signed-lock-audit-trail.md`
- `docs/build/phase-88-dependency-hardening-notes.md`
- `docs/build/phase-88-release-hardening-pilot-evidence-gate.md`

## 14. Update protocol

When a new phase merges into `main`, the engineer responsible for the
phase MUST:

1. Update Section 2 ("What is built") with the new surface row.
2. Update Section 13 ("Authoritative current docs") with the new
   phase doc link.
3. Update the "Last updated" header at the top.
4. Run the release-evidence gate and confirm PASS before claiming
   the row.

Stale rows here are a worse buyer experience than a missing row —
default to under-promising.
