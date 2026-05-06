# ChartNav Demo-to-Pilot Transition Plan

How to move from a five-minute fake-data demo to a pilot
conversation, then to a controlled-pilot deployment, without
skipping safety or scoping steps.

This is the bridge between Phase 13 (demo packaging) and a paid
customer relationship. The phase numbering is internal; the
practice sees a single coherent path.

---

## Path overview

```
fake-data demo ──► discovery ──► pilot qualification ──►
pilot agreement ──► technical readiness ──►
controlled-pilot deploy ──► pilot run ──► decision
```

Each gate is documented below. None is optional.

---

## Step 1 — Fake-data demo

Use the Phase 13 demo script
(`docs/demo/chartnav-clinical-workflow-demo-script.md`) and the
click path. The demo runs against the seeded
`demo-eye-clinic` / `PT-1001` data only. **No real PHI**, ever.

Outcome: the practice has seen the workflow, the safety contract,
and the demo guide.

---

## Step 2 — Discovery

Follow up the demo with a 30 – 45 minute discovery conversation.
The questions below are not a script — they are reminders of what
to learn before scoping a pilot.

### Practice profile

- How many providers? How many locations?
- What sub-specialties? (Retina / glaucoma / cataract / general
  ophthalmology — ChartNav is ophthalmology-specific but
  sub-specialty fit varies.)
- Approximate encounter volume per provider per day?
- Current charting / scribe situation? (No scribe / human scribe /
  another AI scribe / EHR templates.)

### Workflow fit

- Do providers commonly draw retinal findings? (If not, the
  Phase 5B/6 surface is not the strongest fit.)
- Do providers commonly write patient-friendly summaries today?
- Is there a chart-review / QA reviewer who would benefit from a
  read-only role?
- Is there a pre-visit huddle / chart-prep workflow today? (Phase
  10 fits here.)

### Data / privacy / security

- Existing EHR / chart system?
- Existing BAA partners?
- Hosting preference: on the practice's infrastructure, on a
  managed host, or on ChartNav's hosted controlled-pilot?
- Authentication: existing OIDC issuer? Or does the pilot need a
  separate one?
- Backup / retention preferences?

### Adoption posture

- How much time per encounter is the practice willing to spend
  reviewing AI-suggested content?
- Who is the pilot's clinical champion?
- Who is the pilot's technical owner?
- Who is the pilot's security/compliance owner?

---

## Step 3 — Pilot qualification checklist

A practice is **ready** to pilot when:

- [ ] At least one ophthalmologist is willing to use ChartNav on
      real encounters during the pilot window.
- [ ] A clinical champion is identified.
- [ ] A technical owner is identified.
- [ ] A security/compliance owner is identified.
- [ ] The practice's existing EHR / chart system has a clear
      coexistence story (ChartNav is not the EHR; how will the two
      interact during the pilot — manual copy/paste vs. side-by-
      side review).
- [ ] The practice has acknowledged the
      "What ChartNav does NOT do" list in
      `chartnav-known-limitations-and-non-goals.md`.

If any item is missing, the conversation continues but the pilot
does not start.

---

## Step 4 — Pilot agreement checklist

Before a controlled-pilot deploys:

- [ ] BAA (or equivalent) executed.
- [ ] Pilot scope written: which providers, which patients
      (specific cohort or "all"), which time window, which
      clinical surfaces (Phase 5B/6/8/9/10/11/13 — typically all,
      but a practice may choose to start narrower).
- [ ] Success metrics agreed (see
      `chartnav-pilot-success-metrics.md`).
- [ ] Exit criteria agreed.
- [ ] Hosting decision documented.
- [ ] Audit retention window decided.
- [ ] Backup cadence decided.
- [ ] Incident-response contacts documented per
      `chartnav-support-runbook.md`.
- [ ] Pricing / billing for the pilot agreed (often free or
      minimal for an initial pilot — that is a business decision).

---

## Step 5 — Technical readiness checklist

Before the controlled-pilot deploy, verify against
`chartnav-pilot-deployment-guide.md`:

- [ ] Postgres host is up.
- [ ] API host is up.
- [ ] Frontend host is up.
- [ ] `CHARTNAV_AUTH_MODE=bearer` against a real OIDC issuer.
- [ ] Required env vars are set (without secrets in the repo).
- [ ] Migrations applied.
- [ ] Smoke test passes.
- [ ] CI is green on the deployed commit.
- [ ] Monitoring / log shipping is in place.

---

## Step 6 — Data / privacy / security questions to confirm

Repeat the key items from `chartnav-security-review-packet.md` so
nothing is missed:

- [ ] BAA executed.
- [ ] Authentication mode confirmed (`bearer`).
- [ ] Hosting confirmed.
- [ ] Audit retention confirmed.
- [ ] Backup / restore tested.
- [ ] Network egress confirmed (e.g., Whisper enabled or not).
- [ ] Logging destination confirmed.
- [ ] Incident response contacts confirmed.
- [ ] Pen test / vuln scan scheduled if the practice requires one.

---

## Step 7 — Success criteria

See `chartnav-pilot-success-metrics.md` for the measurement
templates. The practice and ChartNav agree on a small,
representative subset of metrics for this specific pilot —
**do not** claim a generic guaranteed improvement number.

---

## Step 8 — Pilot timeline template

A typical four-to-six-week pilot:

| Week | Focus |
|------|-------|
| 0    | Pilot agreement signed, technical readiness verified, users provisioned. |
| 1    | First-session walkthroughs (per `chartnav-admin-onboarding-checklist.md`). Real encounters begin against fake demo patient first; switch to real cohort once gating is met. |
| 2    | Real-encounter use begins. Daily 5-minute check-in for the first three days. Weekly health check thereafter. |
| 3    | Mid-pilot review — provider satisfaction, workflow fit, support ticket review. |
| 4    | Continue or adjust based on mid-pilot review. |
| 5 – 6 | Pilot wind-down: collect final metrics, run the post-pilot decision framework. |

The practice may set a different timeline. The structure (kick-off
→ first-session → daily check-in → weekly health check →
mid-pilot review → wind-down) stays.

---

## Step 9 — Post-pilot decision framework

At pilot end, the practice and ChartNav meet to decide:

- **Continue → paid pilot** if the agreed success metrics meet the
  conversion criteria and the practice is willing.
- **Pause** if metrics are mixed and a follow-up phase (training,
  workflow change, product improvement) would change the answer.
- **End** if the practice or ChartNav decides the fit is poor.

Outputs of the meeting (recorded out-of-repo in the pilot
agreement document):

- Final metrics report.
- Issue / support ticket summary.
- Decision.
- If "continue": next-step plan + timeline.
- If "pause": what change would unblock.
- If "end": clean exit checklist (deprovision users, retain audit
  per practice policy, archive or delete pilot data per agreement).
