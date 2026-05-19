# ChartNav Real PHI Go-Live Gate

> **Phase:** 23.
> **Authority:** This document is the **single gate** between
> demo/fake-data deployment and real-PHI controlled-pilot
> deployment. Every checkbox must close before any real PHI is
> processed.
>
> **ChartNav is not approved for real PHI by default. ChartNav is
> not HIPAA-certified. This gate exists so a practice's security
> owner has a single artifact to walk during their review.**

This is **the** real-PHI gate. The HIPAA readiness control
matrix (`chartnav-hipaa-readiness-control-matrix.md`) lists
*what controls exist*; this doc lists *what must close* for a
specific practice to start.

Do not skip items. Do not infer items. Do not retroactively
check items.

---

## Pre-conditions (before kickoff)

- [ ] Practice has been briefed that ChartNav is not approved for
      real PHI by default and is not HIPAA-certified.
- [ ] Practice has reviewed the demo on fake data
      (`PT-1001 Morgan Lee` seeded encounter).
- [ ] Practice has identified a security owner who will own the
      go-live process from their side.

## Gate 1 — Legal / contractual

- [ ] **BAA executed** between ChartNav (ARCG Systems) and the
      practice. Counter-signed. Filed.
- [ ] **BAA executed** between ChartNav and every subprocessor
      that may touch ePHI (see
      `chartnav-subprocessor-inventory.md`).
- [ ] Practice has counter-signed the
      `chartnav-customer-responsibility-matrix.md` so both sides
      agree on who owns what.

## Gate 2 — Identity / auth

- [ ] **`CHARTNAV_AUTH_MODE=bearer`** in production (no header
      auth).
- [ ] `CHARTNAV_JWT_ISSUER`, `CHARTNAV_JWT_AUDIENCE`,
      `CHARTNAV_JWT_JWKS_URL` configured against the practice's
      identity provider.
- [ ] **MFA enforced** at the identity provider.
- [ ] Practice has assigned ChartNav roles
      (`admin / clinician / reviewer / technician / front_desk`)
      to each pilot user.
- [ ] No shared accounts. No service accounts with PHI access.
- [ ] Identity provider session timeout configured.
- [ ] `scripts/validate_controlled_pilot_env.sh` passes.

## Gate 3 — Hosting

- [ ] Production is hosted in an approved environment per the
      practice's hosting policy.
- [ ] **Postgres** is the database in production (no SQLite).
- [ ] HTTPS-only deployment. TLS terminated by a managed
      endpoint.
- [ ] CORS configured to the practice's known origins (no
      wildcard).
- [ ] Hosting provider's BAA is on file.
- [ ] No PHI in environment-variable values printed by any tool
      or log.

## Gate 4 — Backups

- [ ] `scripts/backup_controlled_pilot_postgres.sh` configured
      to write to an approved storage destination.
- [ ] Backup encryption confirmed at the hosting layer.
- [ ] **Restore test executed** against a non-production
      environment by the practice or a designated operator.
      Result documented.
- [ ] Backup verification (`scripts/verify_controlled_pilot_backup.sh`)
      scheduled.
- [ ] RPO and RTO documented (practice-agreed values; defaults
      are placeholders).
- [ ] Backup failure monitoring configured (alert destination on
      file).

## Gate 5 — Monitoring + logging

- [ ] Application logs forwarded to an approved sink (no PHI in
      log bodies; ChartNav writes metadata-only).
- [ ] Audit-event volume monitored (`security_audit_events` row
      count over time).
- [ ] Health-check endpoint monitored.
- [ ] Alert destination on file (paging contact for the
      practice's on-call security owner).
- [ ] Monitoring documentation (`chartnav-monitoring-logging-readiness.md`)
      reviewed and accepted by the practice.

## Gate 6 — Audit retention

- [ ] `CHARTNAV_AUDIT_RETENTION_DAYS` set to the practice's
      agreed value.
- [ ] `scripts/audit_retention.py` scheduled.
- [ ] Audit retention duration documented in the BAA or a side
      letter.
- [ ] Practice has confirmed that audit events are
      metadata-only and contain no PHI bodies.

## Gate 7 — Vendor / subprocessor review

- [ ] `chartnav-subprocessor-inventory.md` reviewed line-by-line
      with the practice's security owner.
- [ ] Every "BAA required" vendor has a BAA on file.
- [ ] STT / AI / LLM PHI egress: either **disabled** (default)
      or **practice-approved in writing** with the
      `CHARTNAV_PILOT_ALLOW_STT_OPENAI_WHISPER` override (or
      equivalent) recorded.

## Gate 8 — Incident response

- [ ] Practice has provided incident-response contact (name,
      email, phone, on-call).
- [ ] ChartNav has provided incident-response contact (Jean-Max
      Charles or designated successor).
- [ ] `chartnav-incident-breach-response-runbook.md` reviewed by
      the practice.
- [ ] Practice has reviewed the breach-notification timelines in
      the runbook with their own legal counsel (timelines are
      placeholders without legal review).

## Gate 9 — Support / operational

- [ ] Practice support contact identified.
- [ ] `chartnav-support-phi-handling-policy.md` reviewed.
- [ ] No-PHI-in-support-tickets rule acknowledged by both sides.
- [ ] Practice has a secure evidence-handling channel for any
      PHI-bearing screenshot / log if one becomes necessary.

## Gate 10 — Written approval

- [ ] Practice security owner signs an explicit "OK to start real
      PHI on [start date]" written approval. Email is acceptable
      if archived.
- [ ] **Real PHI start date** is set after every gate above is
      checked.

---

## What this gate does NOT make ChartNav

This gate does not make ChartNav:

- HIPAA-compliant in any certified sense.
- A certified EHR.
- SOC 2-attested.
- FDA-cleared.
- HITRUST-certified.
- Pen-tested unless a separate pen test has occurred and is
  filed.
- Production-ready for PHI in any context other than the
  specific practice that completed this gate.

This gate is a **per-practice** artifact. Every new practice
runs through it independently.

---

## What this gate is

A working document the practice's security owner walks during
their own security review. It captures the joint pre-conditions
for a real-PHI controlled pilot. It is not an attestation; it is
a contract for how the launch is structured.
