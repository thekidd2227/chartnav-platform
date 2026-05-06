# ChartNav Pilot Readiness Checklist

A practical checklist for *pilot conversations* and *pilot setup* with
ophthalmology offices. This document is the source of truth for what
must be true (or explicitly acknowledged) before ChartNav is shown to
or piloted with a real practice.

This is not an EHR replacement plan. ChartNav is a **provider-reviewed
clinical workflow assistant** — documentation support, retinal-diagram
review, scribe sessions, patient-friendly summary drafts, pre-visit
brief, and a provider action review queue. It does not diagnose
autonomously, does not create orders, does not code, does not submit
referrals, and does not message patients.

---

## Product scope

ChartNav is an **ophthalmology-specific documentation and review
assistant**. The clinical workflow surfaces are:

- AI scribe sessions (provider-reviewed lifecycle: draft → reviewed →
  finalized).
- Findings-to-retinal-diagram proposal review (read-only suggestions;
  applied only on explicit provider action).
- OD/OS retinal drawing canvas with signed-artifact immutability.
- Provider-reviewed patient-friendly summaries (never sent to a
  patient automatically).
- Pre-visit brief (derived view of available chart records).
- Provider action review queue (review tasks only — not orders, not
  referrals, not patient messages).

ChartNav is **not**:

- a certified EHR replacement,
- a billing / coding tool,
- an orders system,
- a referral routing system,
- a patient messaging system,
- a primary-care charting assistant.

## Demo / pilot data policy

- **Demo data is fake only.** The current demo runs against the
  seeded `demo-eye-clinic` org with patient `PT-1001` ("Morgan
  Lee"). All names, MRNs, DOBs, NPIs are fake by construction.
- **Real PHI may be used only after** a written agreement (BAA or
  equivalent), a security review, and a documented controlled-
  deployment posture for the practice. See
  `chartnav-security-review-packet.md`.
- **Reset between demos** with `make reset-db` so a previous
  session's edits do not leak into the next demo.

## Provider-review boundaries

Every clinical artifact in ChartNav is provider-reviewed:

- Scribe sessions require `review` then `finalize`. Direct draft →
  finalized is rejected.
- Retinal-diagram proposals enter the chart only after the provider
  explicitly applies them. Anything that lands is tagged
  `source=ai_approved`.
- Signed retinal artifacts are immutable in place; edits create an
  explicit fork.
- Patient summaries require `review` then `finalize`. Finalized and
  discarded are immutable. ChartNav never sends to a patient.
- Provider action items must be `accepted` before `complete`.
  Direct suggested → completed is rejected. Dismissed and completed
  are immutable.

## Roles and permissions

| Role        | Can do                                                                                             |
|-------------|----------------------------------------------------------------------------------------------------|
| `admin`     | Generate, accept, dismiss, complete every clinical artifact. Manage org users/settings.            |
| `clinician` | Generate, accept, dismiss, complete every clinical artifact for their org.                         |
| `reviewer`  | **Read-only** across all clinical surfaces (eye-diagrams / scribe / patient-summary / pre-visit brief / provider-action queue). |

Cross-organization access returns `404 patient_not_found` — there is
no existence leak across orgs. Every per-source SELECT re-asserts
the org filter for defense in depth.

## Admin setup

Before the pilot:

- [ ] Pilot organization is created in ChartNav with a unique
      `slug`.
- [ ] At least one `admin` user is provisioned.
- [ ] At least one `clinician` user is provisioned per active
      provider.
- [ ] `reviewer` users are provisioned for any non-prescribing
      reviewer (e.g., a chart-review nurse or QA reviewer).
- [ ] The pilot's environment is documented:
      `local | staging | controlled-pilot`.
- [ ] CHARTNAV_AUTH_MODE is `bearer` for any environment that may
      hold real PHI; `header` is dev-only.

## User onboarding

See `chartnav-admin-onboarding-checklist.md` for the full sequence.

- [ ] Each user has been walked through the demo workflow guide
      (`Show demo workflow guide` in the workspace).
- [ ] Each user has read the safety statement: "ChartNav supports
      documentation and review workflows. ChartNav does not
      diagnose, order, bill, send referrals, or message patients
      automatically."
- [ ] Each user has signed any practice-internal acknowledgment
      that ChartNav is a documentation assistant, not a clinical
      decision-maker.

## Security review

Before any real-PHI use:

- [ ] BAA (or equivalent) executed between the practice and
      ChartNav's operating entity.
- [ ] Security review completed against
      `chartnav-security-review-packet.md`.
- [ ] Authentication mode is `bearer` (JWT) with a real issuer.
- [ ] Database hosting and backup posture is documented.
- [ ] Audit retention window is documented.

## Audit logging

- [ ] Every mutation across all clinical phases emits a
      metadata-only `security_audit_events` row.
- [ ] Audit `detail` is **never** any clinical body — sentinel-
      token regression tests assert this.
- [ ] Audit retention window is set per practice agreement.
- [ ] Audit log is durable in the pilot environment (not just
      ephemeral local SQLite for any environment that holds PHI).

## Data retention questions

To confirm with each pilot practice:

- [ ] How long should `security_audit_events` rows be retained?
- [ ] Are scribe-session source/transcript/draft texts treated as
      ephemeral (only kept while the session is open) or durable
      (kept for the encounter record)?
- [ ] Are retinal artifacts retained per the practice's existing
      chart-retention policy?
- [ ] Patient summaries: same question.

These are practice-policy decisions; ChartNav can be configured to
respect them but does not assume them.

## Backup / restore expectations

To confirm before the pilot:

- [ ] Database backups are taken on the practice's preferred
      cadence.
- [ ] Backup restore has been tested at least once in the pilot
      environment.
- [ ] No PHI is checked into the repo (this is asserted by the
      forbidden-file scan in CI).

## Deployment environment

See `chartnav-pilot-deployment-guide.md`.

- [ ] Environment is one of: `local`, `staging`, or
      `controlled-pilot`.
- [ ] Required environment variables are inventoried (without
      secrets) — see the deployment guide.
- [ ] Frontend host is documented (Vercel preview vs. self-hosted
      vs. controlled-pilot host).
- [ ] Backend host is documented (compose / Docker / managed).
- [ ] Database is Postgres in any environment that may hold PHI.

## Support process

See `chartnav-support-runbook.md`.

- [ ] A primary support contact exists at the practice.
- [ ] An escalation path exists from the practice to the ChartNav
      operating entity.
- [ ] Severity levels and response targets are agreed.
- [ ] Incident-response plan covers data-safety incidents.

## Known limitations

See `chartnav-known-limitations-and-non-goals.md`.

Highlights the practice should know:

- ChartNav is not a certified EHR.
- The clinical-language scan on the action queue is intentionally
  narrow — it is **not a primary safety net**.
- The pre-visit brief may be incomplete; data gaps are listed
  explicitly.
- The deterministic v1 generators do not invent diagnoses or
  recommendations — providers do.
- No external LLM is invoked.

## Exit criteria for a pilot

The pilot is **complete** (and ready for a continue / pause / end
decision) when one or more of:

- Provider satisfaction has been formally collected (see
  `chartnav-pilot-success-metrics.md`).
- Documentation completeness improvement has been measured against
  baseline.
- Workflow fit / friction has been documented.
- A safety / data-handling incident has occurred and been resolved.
- The pilot agreement's time window has elapsed.

Decisions:

- **Continue → paid pilot** if metrics meet conversion criteria and
  the practice is willing.
- **Pause** if metrics are mixed and a follow-up phase is needed.
- **End** if the practice or ChartNav decides the fit is poor.
