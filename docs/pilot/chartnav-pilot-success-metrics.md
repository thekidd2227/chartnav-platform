# ChartNav Pilot Success Metrics

A measurement template for a controlled-pilot. The metrics below
are **placeholders by design** — each pilot agrees on a small,
representative subset before it starts. Numeric targets are filled
in by the practice and ChartNav together.

This document explicitly avoids fake numeric claims. There are no
"average X% time saved" headline numbers because those depend on
the specific practice, the specific providers, the specific
workflow today, and the specific cohort the pilot uses.

---

## How to use this template

1. With the practice's clinical champion, pick **3 – 5** metrics
   from the catalogue below.
2. Set a **baseline** for each at the start of the pilot.
3. Set a **target** that ChartNav and the practice agree is
   meaningful (e.g., "non-regression," "improvement of any
   magnitude," or a specific number — practice-specific).
4. Set a **measurement cadence** (weekly, mid-pilot, end-of-pilot).
5. Record **reading + delta** at each cadence in the pilot's
   shared tracking document (out-of-repo).

---

## Metric catalogue

### 1. Provider time saved (estimate)

**What:** wall-clock time per encounter spent on documentation +
review activities ChartNav supports (scribe session, retinal
diagram, patient summary, pre-visit chart prep).

**How:** sample. Pick a handful of encounters per week. The
provider self-reports time spent on each activity before and after
adopting ChartNav.

**Caution:** small sample; noisy. Treat as directional, not as a
guaranteed improvement claim.

| | Baseline | Target | Reading | Delta |
|---|---|---|---|---|
| Per-encounter docs time | _____ | _____ | _____ | _____ |

### 2. Documentation completeness

**What:** the percentage of pilot encounters in which all the
practice's required note sections are present.

**How:** sample chart audit. Practice-specific definition of "all
required sections."

| | Baseline | Target | Reading | Delta |
|---|---|---|---|---|
| % encounters with required sections | _____ | _____ | _____ | _____ |

### 3. Retinal diagram usage

**What:** how many encounters during the pilot include a signed
retinal artifact.

**How:** count `chart_artifacts` rows with `signed_at NOT NULL`
within the pilot window for the pilot patients.

| | Baseline | Target | Reading | Delta |
|---|---|---|---|---|
| Signed retinal artifacts / encounter | _____ | _____ | _____ | _____ |

### 4. Scribe session review completion

**What:** how many scribe sessions reach `finalized` state.

**How:** count `scribe_sessions` rows by `status` within the pilot
window. Track `finalized` over `finalized + reviewed + draft`.

| | Baseline | Target | Reading | Delta |
|---|---|---|---|---|
| % scribe sessions finalized | _____ | _____ | _____ | _____ |

### 5. Patient summary review completion

**What:** how many patient summaries reach `finalized` state.

**How:** count `patient_summaries` rows by `status` within the
pilot window.

| | Baseline | Target | Reading | Delta |
|---|---|---|---|---|
| % patient summaries finalized | _____ | _____ | _____ | _____ |

### 6. Pre-visit brief usage

**What:** how often a pre-visit brief is generated for an upcoming
encounter.

**How:** count `pre_visit_brief_generated` audit events per
upcoming encounter. (The brief is on-demand; the audit event is
the durable record.)

| | Baseline | Target | Reading | Delta |
|---|---|---|---|---|
| Brief generations per encounter | _____ | _____ | _____ | _____ |

### 7. Action queue usage

**What:** ratio of action items the provider acts on
(`accepted` + `dismissed` + `completed`) over total
`suggested`.

**How:** count `provider_action_items` rows by `status` within the
pilot window.

| | Baseline | Target | Reading | Delta |
|---|---|---|---|---|
| % action items resolved | _____ | _____ | _____ | _____ |

### 8. Provider satisfaction

**What:** structured survey at mid-pilot and end-of-pilot.

**How:** short Likert-scale + free-form survey delivered to each
pilot provider. Keep it small (< 5 questions).

| | Baseline | Target | Reading | Delta |
|---|---|---|---|---|
| Mean satisfaction (1 – 5) | _____ | _____ | _____ | _____ |

### 9. Safety / issue reports

**What:** count of S1 / S2 support tickets during the pilot.

**How:** see `chartnav-support-runbook.md`. S1 (data-safety) is
catastrophic; S2 (workflow blocker) is the more common indicator
of friction.

| | Baseline | Target | Reading | Delta |
|---|---|---|---|---|
| S1 tickets | 0 (any non-zero is a flag) | 0 | _____ | _____ |
| S2 tickets | n/a | small N | _____ | _____ |

### 10. Workflow fit

**What:** qualitative — does ChartNav fit the practice's existing
charting workflow without forcing a redesign?

**How:** mid-pilot review + end-of-pilot review with the clinical
champion. Capture any workflow change that **would** be needed to
make ChartNav fit better.

This is qualitative; no numeric reading.

---

## Conversion criteria — paid pilot / paid customer

A **continue → paid pilot** decision typically requires:

- [ ] At least one of metrics 1 – 5 shows a non-regression and a
      direction the practice considers meaningful.
- [ ] No `S1` ticket has been filed (or any that was filed has
      been resolved with a regression test).
- [ ] Provider satisfaction is positive (mean ≥ 4 / 5 by default,
      practice-specific override allowed).
- [ ] The clinical champion is willing to advocate for continued
      use.

A **continue → paid customer** decision typically requires:

- [ ] Above plus
- [ ] A signed paid-customer agreement (out-of-repo).
- [ ] A documented production deployment posture per
      `chartnav-pilot-deployment-guide.md` (controlled-pilot
      promoted to production-customer mode — pricing, support
      terms, and data-handling agreements that match a paying
      customer).

---

## What this template does NOT promise

- It does not promise a generic numeric improvement number ("X%
  time saved across all practices"). Every pilot's number is
  practice-specific.
- It does not promise a clinical-quality improvement. ChartNav is
  documentation and review support; clinical decisions are the
  provider's.
- It does not promise revenue / billing / coding improvements.
  ChartNav has no billing surface.
- It does not promise patient-experience improvements. ChartNav
  has no patient-facing surface.

The metrics that ChartNav can credibly move are workflow and
documentation metrics. Anything else is the practice's outcome to
own.
