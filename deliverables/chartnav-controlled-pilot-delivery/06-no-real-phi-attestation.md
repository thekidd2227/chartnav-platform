# No-Real-PHI Attestation

**Audience:** Practice security owner / CISO + ARCG legal
**Source of truth:** mirrors `docs/security/phase-100-no-real-phi-attestation.md`
**Posture:** This document, this delivery package, and the
release SHA referenced in `artifacts/manifest.txt` do **not**
authorize real protected health information in any ChartNav
environment.

## 1. Bottom-line attestation

The repository state at the build SHA referenced by this delivery
package **does not authorize real protected health information**
in any ChartNav environment.

- The release-side gates (Phase 88, Phase 93, Phase 100, Phase
  101) PASS results are technical readiness signals only.
- The Phase 100 controlled-pilot launch GO / NO-GO form
  (`05-go-no-go-form.md`) is a decision form, not an
  authorization.
- The evidence index (`04-evidence-index.md`) is a link catalog,
  not an authorization.

A controlled fake-data pilot may proceed under this attestation.
A real-PHI pilot may **not** proceed under this attestation
alone — see Section 4.

## 2. What is technically enforced today

- Local + staging demo stacks refuse non-loopback `DATABASE_URL`
  on reset (`scripts/reset_demo_state.sh`).
- The Phase 88, Phase 93, Phase 100, and Phase 101 gates run only
  against synthetic seed data and reject secrets.
- Every safety scanner (commercial, demo, website, pilot
  readiness, claim policy fixtures, runtime safety) treats the
  product positioning as fake-data only.
- The Phase 87 FHIR export endpoint pins `submission_status` to
  `not_submitted` and `transport` to `none` at the protocol
  layer.
- The Phase 92 advanced clinical intelligence layer surfaces
  five asserted safety boundaries (no autonomous diagnosis, no
  image interpretation, no treatment recommendation, no
  submission, metadata-only).

## 3. Controlled fake-data scope (allowed)

A practice may use ChartNav for any of the following without
additional security sign-off **provided** the data is synthetic
seed data only:

- Operator-led buyer demo using the seeded encounter list.
- Internal rehearsal against the buyer demo runbook.
- Phase 100 buyer demo script walkthroughs (15 or 30 minutes).
- End-to-end functional validation against the seeded patient.
- Screenshot + video clip capture per the existing shot lists,
  with "demo mode — no real PHI" visible in every captured
  frame.

The operator confirms, before each session:

- The browser is on `http://127.0.0.1:5173` or a clearly-labelled
  demo URL.
- All patient identifiers on screen are the seeded fake values.
- No real patient / provider / organization / payer names appear
  on any panel.

## 4. Real-PHI scope (NOT allowed by this attestation alone)

A practice may not use ChartNav with real protected health
information unless **every** gate below is closed with written,
dated, attributable evidence.

### 4.1 BAA + legal

- [ ] Business Associate Agreement executed between the practice
      (covered entity) and ARCG Systems (business associate).
- [ ] Data Processing Addendum signed if the practice requires
      one.
- [ ] Subprocessor list acknowledged
      (`docs/security/chartnav-subprocessor-inventory.md`).

### 4.2 Vendor / LLM

- [ ] LLM provider decision locked to "no production LLM in this
      build" (`docs/security/chartnav-llm-provider-decision-memo.md`).
- [ ] STT vendor readiness reviewed
      (`docs/security/chartnav-stt-vendor-readiness.md`).

### 4.3 Security review

- [ ] Practice security review packet accepted
      (`docs/pilot/chartnav-security-review-packet.md`).
- [ ] HIPAA readiness control matrix walked
      (`docs/security/chartnav-hipaa-readiness-control-matrix.md`).
- [ ] Customer responsibility matrix countersigned
      (`docs/security/chartnav-customer-responsibility-matrix.md`).

### 4.4 Site / hosting

- [ ] Practice-approved hosting region + residency.
- [ ] Production-grade Postgres with backups + PITR.
- [ ] Production OIDC issuer + audience locked; demo identities
      disabled.
- [ ] TLS terminated by a practice-approved load balancer /
      ingress.

### 4.5 Access + logging

- [ ] Named-user roster + role assignments approved by the
      practice administrator.
- [ ] Audit log destination + retention agreed.
- [ ] `CHARTNAV_AUDIT_RETENTION_DAYS` set to the practice-approved
      value.

### 4.6 Backup / DR

- [ ] Backup destination + cadence + retention agreed.
- [ ] Backup + restore + verify rehearsal complete within 90 days.
- [ ] DR drill rehearsed within 90 days.

### 4.7 Incident response

- [ ] Incident response runbook walked
      (`docs/security/chartnav-incident-breach-response-runbook.md`).
- [ ] Practice incident contact + escalation chain on file.
- [ ] ARCG on-call rotation locked for the pilot window.
- [ ] Tabletop exercise rehearsed within 180 days.

### 4.8 Written practice approval

- [ ] Practice clinical owner signs explicit go-live approval.
- [ ] Practice security owner / CISO signs explicit go-live
      approval.
- [ ] Practice administrator signs explicit go-live approval.
- [ ] Go-live date locked in writing.

## 5. What ChartNav still does NOT claim, even at real-PHI go-live

The following non-claims survive every go-live and are enforced
by the safety-scanner suite and the runtime safety scanner on
every release:

- ChartNav is **not** HIPAA-certified, SOC 2-certified,
  HITRUST-certified, or FDA-cleared.
- ChartNav is **not** a certified electronic health record.
- ChartNav does **not** replace the practice's existing EHR.
- ChartNav does **not** diagnose, recommend treatment, recommend
  surgery, recommend medication changes, recommend IOL choices,
  or recommend imaging modality changes.
- ChartNav does **not** interpret fundus photographs, OCT scans,
  visual fields, or any imaging modality.
- ChartNav does **not** place orders, send referrals, bill, code,
  submit claims, or message patients.
- ChartNav does **not** submit to MIPS, IRIS, CMS, payers, or any
  external registry from this build.
- ChartNav does **not** run a production LLM in this build.

## 6. Attestation signatures

By signing below, each party attests that:

1. They have read this no-real-PHI attestation in full.
2. They understand that this delivery package does not authorize
   real PHI in any ChartNav environment.
3. They will not present, market, sell, or operate ChartNav as if
   real PHI is approved under this package alone.
4. They will require a signed Phase 93 real-PHI readiness review
   and a signed Phase 18 controlled-pilot go-live checklist
   before any real-PHI session.

| Role | Name | Signature | Date |
|---|---|---|---|
| ARCG ops owner | ___________________ | ___________________ | __________ |
| ARCG legal | ___________________ | ___________________ | __________ |
| ARCG commercial owner | ___________________ | ___________________ | __________ |
| Practice clinical owner (if engaging) | ___________________ | ___________________ | __________ |
| Practice security owner / CISO (if engaging) | ___________________ | ___________________ | __________ |
| Practice administrator (if engaging) | ___________________ | ___________________ | __________ |

**Effective SHA:** __________ (see `artifacts/manifest.txt`)
**Effective date:** __________
**Next-review date:** __________ (no later than 90 days after the
effective date, or any real-PHI scope change, whichever comes
first).
