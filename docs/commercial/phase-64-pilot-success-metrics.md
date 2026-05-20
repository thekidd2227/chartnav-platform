# ChartNav — Pilot Success Metrics Draft (Phase 64)

> **Practical, manually-measurable metrics for a controlled paid
> pilot.** No clinical outcome claims, no revenue claims, no ROI
> guarantees. The goal is to define narrow workflow signals the
> buyer can observe themselves.

## 1. How to use this list

Pick **one or two metrics** with the buyer during a pilot-scoping
conversation (see
`docs/commercial/phase-64-paid-pilot-positioning.md` § 5). Do not
pick all of them — the controlled pilot is intentionally narrow.
Every metric below is **manually measured by the practice** in
the early pilot; ChartNav does not ship automated KPI dashboards
for these metrics today.

If the practice wants a metric that is not on this list, write it
down in the tracker as "candidate metric — needs scoping" and do
not commit to it until the team reviews it for safety + scope.

## 2. Metrics in scope

### 2.1 Documentation turnaround time
**What it measures.** Wall-clock time from technician-completes-
intake to clinician-signs-final-artefact for the encounters that
went through ChartNav vs a comparable baseline cohort.

**How to capture.** Manual stopwatch / timestamps the practice
records on its own. ChartNav surfaces `created_at` /
`reviewed_at` / `signed_at` on signed artefacts; the practice can
read those from the artefact view.

**Why this is safe.** It measures workflow timing, not clinical
outcomes. No diagnosis claim is implied.

### 2.2 Technician intake completeness
**What it measures.** Proportion of structured intake fields the
technician completed during the pilot encounters (vitals, visual
acuity, IOP, allergies-reviewed, medications-reviewed, etc.)
relative to a baseline.

**How to capture.** Manual count from the signed vitals workup
in ChartNav vs the practice's existing intake template.

**Why this is safe.** Completeness is a process metric, not a
clinical outcome.

### 2.3 Provider review burden
**What it measures.** Subjective provider-reported friction score
(1–5) on the VisitDraft review-and-sign step at end-of-week
during the pilot.

**How to capture.** Single-question end-of-week pulse to the
clinician(s) in the pilot. The team logs the score in the
tracker.

**Why this is safe.** It captures provider experience, not
clinical decision-making. No autonomous-documentation claim is
implied.

### 2.4 VisitDraft usefulness
**What it measures.** Proportion of generated VisitDrafts the
clinician accepted as the starting point of the final signed
note vs the proportion the clinician discarded and rewrote from
scratch.

**How to capture.** The clinician marks a flag at sign time
("accepted draft as starting point — yes / no"). The practice
counts.

**Why this is safe.** Provider remains the author. The metric
quantifies whether the draft helped or did not — it does not
imply the AI wrote the final note.

### 2.5 Fundus drawing completeness
**What it measures.** Proportion of fundus charts where the
clinician-entered findings text produced a structured retinal
diagram that the clinician then accepted (with or without manual
edits) vs charts where the clinician started over manually.

**How to capture.** Manual count of generated charts that
proceeded to review and sign vs. those discarded.

**Why this is safe.** Fundus Drawing Assist is clinician-entered
findings to structured diagram. No image interpretation, no
diagnosis, no auto-grading is claimed by this metric.

### 2.6 Workflow handoff clarity
**What it measures.** Subjective practice-reported clarity (1–5)
of the technician → provider → signed-chart handoff during the
pilot.

**How to capture.** End-of-pilot survey to the technician and
the clinician separately. Compare to baseline if available.

**Why this is safe.** It is a workflow-fit signal, not a clinical
or compliance signal.

### 2.7 Safety / claim-boundary adherence
**What it measures.** Number of stop-demo / safety-trigger events
during the pilot:

- any real PHI displayed on screen during a demo pass;
- any forbidden phrase appearing in operator narration or on
  screen;
- any sign / finalize succeeding without the attestation checkbox
  ticked;
- any vendor / network error exposing a secret in a stack trace.

**How to capture.** Operator log in the dated dry-run report
(`artifacts/phase-62/dry-runs/<date>/report.md`) plus the
practice's own observation log for live pilot use.

**Target.** Zero events. Any event triggers a halt-and-review.

**Why this is safe.** It directly enforces the safety frame.

## 3. Metrics intentionally NOT in scope

The following are blocked from being committed as pilot success
metrics. They imply outcomes ChartNav does not produce and
violate the safety frame:

- **Clinical outcome improvements** of any kind (vision,
  intraocular pressure control, surgical outcomes, disease
  progression). ChartNav does not affect these directly and does
  not diagnose.
- **Revenue uplift / ROI / reimbursement gains.** Pricing remains
  a discovery topic; revenue effects are not in scope.
- **Time savings as a guaranteed number.** Documentation
  turnaround time (§ 2.1) is a measurement, not a guarantee.
- **Compliance / certification readiness as a metric.** ChartNav
  is not HIPAA-certified; the pilot does not change that.
- **Number of orders / referrals / patient messages sent.**
  ChartNav does not place orders, send referrals, or message
  patients.
- **Number of imaging studies interpreted.** ChartNav does not
  interpret fundus photos, OCT images, or other imaging.
- **Number of charts auto-signed without provider review.**
  ChartNav has no auto-sign path.

If a prospective buyer asks for any of these as a contract
metric, decline politely and route to the qualification
checklist's "disqualifiers" section.

## 4. Metrics review cadence

| Cadence | Owner | Action |
|---|---|---|
| End of each pilot week | Practice operations lead | Log the chosen metric(s) plus any safety event. |
| End of pilot | Practice operations lead + ChartNav team | Joint review. No new claims may be added retroactively. |
| Post-pilot | ChartNav team | Update internal tracker + decide on next step. **No public customer-reference claim** without the practice's explicit, written approval. |

## Safety note

- Fake-data demo first.
- Paid pilot subject to security review for any real-PHI use.
- Provider review and sign-off required on every artefact.
- ChartNav is not HIPAA-certified.
- ChartNav is not a certified EHR and does not replace any EHR.
- ChartNav does not diagnose.
- ChartNav does not interpret fundus or OCT images.
- ChartNav does not place orders, send referrals, or message patients.
- ChartNav does not bill or code.
- ChartNav does not integrate with medical devices and does not provide remote patient monitoring.

## Related documents

- `docs/build/current-product-truth.md`
- `docs/commercial/phase-64-paid-pilot-positioning.md`
- `docs/commercial/phase-64-security-review-packet-index.md`
- `docs/commercial/phase-64-demo-asset-index.md`
- `docs/release/release-evidence-checklist.md`
