# ChartNav Security Review Packet

This packet is written for a practice's security / compliance
reviewer. It uses **conservative, non-overclaiming language** by
design.

ChartNav **is not** HIPAA-certified, SOC-2-certified, a certified
EHR, or production-ready for PHI by default. ChartNav **is**
designed to support documentation and review workflows in a
provider-in-the-loop model with metadata-only audit, org isolation,
and role-based access control.

This document does not substitute for legal or compliance review.
Items that require legal/security review before PHI are flagged
explicitly.

---

## Product overview

ChartNav is an ophthalmology-specific documentation and review
assistant. The clinical surfaces are:

- AI scribe sessions (provider-reviewed lifecycle).
- Findings-to-retinal-diagram proposal review (read-only
  suggestions).
- OD/OS retinal drawing canvas with signed-artifact immutability.
- Provider-reviewed patient-friendly summary drafts.
- Pre-visit brief (derived view of available chart records).
- Provider action review queue (review tasks only).

Each surface is documented in
`docs/chartnav-patient-chart-foundation.md` and the per-phase
contract docs.

ChartNav **does not** diagnose, order, code, bill, submit referrals,
or message patients. None of those surfaces exist in the product.
This is not a future restriction — it is the current product
contract, asserted by tests.

---

## Provider-in-the-loop model

Every clinical artifact in ChartNav is provider-reviewed:

- Scribe sessions require explicit `review` then `finalize`. Direct
  draft → finalized is rejected.
- Retinal-diagram proposals enter the chart only on explicit
  provider apply. Anything that lands is tagged
  `source=ai_approved` for auditability.
- Signed retinal artifacts are immutable in place; edits create an
  explicit fork.
- Patient summaries require `review` then `finalize`. Finalized and
  discarded are immutable. ChartNav never sends to a patient.
- Provider action items require `accept` before `complete`. Direct
  suggested → completed is rejected. Dismissed and completed are
  immutable.

ChartNav is **not** a clinical decision-maker. The provider is the
decision-maker; ChartNav surfaces structured chart context for the
provider's review.

---

## Audit logging overview

Every mutation across all clinical surfaces emits a row to
`security_audit_events`. Event types are namespaced per surface:

- `eye_diagram_*` (Phase 5B/6)
- `scribe_session_*` (Phase 8)
- `patient_summary_*` (Phase 9)
- `pre_visit_brief_generated` (Phase 10)
- `provider_action_item_*` and `provider_action_items_generated`
  (Phase 11)

The `detail` column is **metadata-only by construction**. The audit
record carries IDs, lifecycle markers (status, action_type,
priority), source IDs, and counts. It **never** carries clinical
body content.

---

## PHI / audit redaction posture

The following fields **never** reach `security_audit_events`:

- chart artifact `findings_text`
- chart artifact `drawing_json`
- scribe session `source_text`, `transcript_text`,
  `draft_note_text`, `structured_note_json`, `review_notes`
- patient summary `plain_language_summary`, `key_findings_json`,
  `next_steps_json`, `questions_json`, `limitations_notice`,
  `review_notes`
- pre-visit brief section bodies (`last_visit_summary`,
  `active_issues`, retinal/scribe excerpts, `pending_items`,
  `suggested_review_items`, `data_gaps`)
- provider action item `title`, `reason`

Sentinel-token regression tests assert this on every PR for every
event type and every clinical-body field. The sentinel tests live
under `apps/api/tests/test_*.py::TestAuditRedaction` and
`apps/api/tests/test_end_to_end_clinical_workflow.py`.

---

## Org isolation posture

Every patient-id-bearing route resolves the patient inside the
caller's organization first. A cross-organization caller sees
`404 patient_not_found` — no existence leak.

Defense in depth: every per-source SELECT re-asserts the org filter
(`AND organization_id = :org`). A stale or wrong patient_id from a
caller produces an empty result, never leaks data from another org.

This posture is asserted by:

- Per-phase cross-org tests (`Test*Security`, `Test*OrgIsolation`).
- The Phase 12 `TestEndToEndOrgIsolation` test which sweeps every
  patient-id-bearing route across all clinical phases against a
  different-org caller.

---

## Role-based access posture

| Role        | Read every clinical surface | Write every clinical surface |
|-------------|-----------------------------|------------------------------|
| `admin`     | Yes                         | Yes                          |
| `clinician` | Yes                         | Yes                          |
| `reviewer`  | Yes                         | **No** — `403 role_forbidden`|

Every route enforces this contract. The Phase 12
`TestReviewerReadOnlyAcrossWorkflow` test sweeps every clinical
write surface and asserts a reviewer's write is rejected on each.

---

## Authentication posture

Authentication is configured by `CHARTNAV_AUTH_MODE`:

- `header` — dev only. Reads `X-User-Email` and resolves from
  `users`. Trivially spoofable; **must not** be used for any
  environment that may hold PHI.
- `bearer` — production. Reads `Authorization: Bearer <jwt>` and
  validates the signature, issuer, audience, and expiry against
  `CHARTNAV_JWT_JWKS_URL`. The token is mapped to a `users` row via
  `CHARTNAV_JWT_USER_CLAIM` (default `email`).

For any controlled-pilot environment, `bearer` mode against a real
OIDC issuer is required.

---

## CI coverage summary

Every PR runs:

- Backend (SQLite) — full alembic migrate + seed + pytest + smoke.
- Backend (Postgres) — parity proof of the same migrations + tests.
- Frontend — typecheck + vitest + production build.
- E2E — Playwright against a booted API + web stack.
- Deploy config — compose + scripts validation.
- Docker — production image build.
- Docs — HTML + PDF regeneration.
- Vercel preview — preview deploy summary.

All eight must be green before merge.

---

## Local / hosted deployment considerations

| Mode               | PHI permitted                                             |
|--------------------|-----------------------------------------------------------|
| `local` (SQLite)   | **No.**                                                    |
| `staging`          | **No.**                                                    |
| `controlled-pilot` | **Only after** the gating items in this packet are signed off. |

See `chartnav-pilot-deployment-guide.md` for full deployment
expectations.

---

## Limitations and open questions

The practice's reviewer should know that today, ChartNav:

- Does **not** carry a HIPAA, SOC 2, HITRUST, or any other
  certification.
- Has **not** been tested against a third-party penetration test in
  the public repo.
- Stores audit `detail` as a free-form text field; the
  metadata-only contract is asserted by code review and tests, not
  by an enforced schema constraint.
- Has a small, ophthalmology-specific clinical-language scan in the
  action queue. It is **not** a primary safety net and is
  documented as such.
- Does **not** enable an external LLM by default. The architecture
  leaves room for one under the same provider-review contract; it
  is documented as deferred and is not enabled.

These limitations are repeated in
`chartnav-known-limitations-and-non-goals.md` so they are easy to
hand to a buyer alone.

---

## Items requiring legal / security review before PHI

The following must be reviewed and signed off by the practice's
legal / security / compliance owner **before** any controlled-pilot
that may hold real PHI:

1. **Business Associate Agreement (BAA)** or equivalent executed
   between the practice and the operating entity.
2. **Authentication mode** — confirm `CHARTNAV_AUTH_MODE=bearer`
   against a real OIDC issuer the practice has approved.
3. **Hosting** — confirm the API host, the database host, and the
   frontend host are each on infrastructure the practice has
   approved.
4. **Audit retention window** — confirm
   `CHARTNAV_AUDIT_RETENTION_DAYS` is set per practice policy.
5. **Backup / restore** — confirm Postgres backups are taken on the
   practice's preferred cadence and that restore has been tested.
6. **Network / data egress** — confirm what the deployment can
   reach (e.g., Whisper API only if approved; otherwise leave
   `CHARTNAV_STT_PROVIDER=stub`).
7. **Logging** — confirm logs are shipped to a destination the
   practice has approved and that no audit `detail` content
   contains PHI.
8. **Incident response** — confirm an escalation path is in place
   (see `chartnav-support-runbook.md`).
9. **Pen test / vuln scan** — confirm whether the practice requires
   one before go-live.

Each item is the practice's call. ChartNav can be configured to
satisfy them; ChartNav does not assume them.

---

## BAA / HIPAA language caution

This document **does not** claim ChartNav is HIPAA-compliant or
HIPAA-certified. Software is not certified to HIPAA — *covered
entities* and *business associates* implement the safeguards HIPAA
requires.

Approved phrasing:

- "designed to support HIPAA-aware data-handling practices"
- "intended to be deployed in a controlled-pilot mode that meets
  the practice's HIPAA posture"
- "requires a BAA before any real PHI is processed"
- "requires legal / security review before PHI"

Forbidden phrasing in any pilot or buyer conversation:

- "HIPAA compliant"
- "HIPAA certified"
- "SOC 2 certified"
- "production-ready for PHI"
- "certified EHR"

The Phase 14 docs-claims test asserts none of these forbidden
positive claims appear in the pilot docs except inside an
enumerated forbidden-list, a negative-assertion line, or a Q&A
question heading whose answer is a negative assertion.
