# ChartNav — Phase 66 Prospect Targeting Brief

> **What this is.** A specialty-tiered, real-world prospect-
> targeting brief for finding the first paid pilot practice.
> Builds on top of `docs/commercial/phase-64-buyer-qualification-
> checklist.md` (which defines the general qualifier + disqualifier
> universe). This brief narrows that universe to the **specific
> practice shapes most likely to engage** in the next 30-90 days
> and the **outreach signals that actually predict fit**.

## 1. First-pilot priority ranking

Prioritize prospects in this order. The ranking is built from
where ChartNav's current capability set (Technician Workup &
Vitals, Provider-Reviewed VisitDraft Assist, Provider-Reviewed
Fundus Drawing Assist, Doctor Review / Signed Lock) lines up
against documented workflow pain.

| Rank | Practice shape | Why first | Outreach posture |
|---|---|---|---|
| 1 | Solo-to-3-provider **retina** practice with a single location and an owner-operator | Highest fit: retina visits use the Fundus Drawing Assist directly; small size keeps pilot scope small; owner can decide on a paid pilot without procurement. | Founder-led email or LinkedIn DM, naming retina workflow specifically. |
| 2 | Solo-to-3-provider **glaucoma / comprehensive ophthalmology** practice with a single location and an owner-operator | Good fit: structured technician intake (vitals + IOP) plus provider-reviewed draft handoff are the main pain. Fundus Drawing Assist is partial-fit (used on photo-screened retina referrals). | Founder-led email, structured-intake hook. |
| 3 | 4-8-provider **multi-specialty eye-care** group with a strong practice manager + a single-pilot champion provider | Workable fit if the champion is a real owner-operator-equivalent decision maker; not first because pilot scope can drift to "rollout" before fit is proven. | Founder-led email; require named clinical champion before scheduling demo. |
| 4 | Subspecialty surgical practice (oculoplastics, cornea, pediatric) | Possible fit if visit-draft workflow matters; lower priority because fundus drawing is rarely used. | Discovery-only outreach until a specific workflow win is named. |
| 5 (deprioritized) | Health-system-affiliated eye-care service line | Procurement complexity outweighs first-pilot value. Revisit after a non-system pilot completes. | No outreach in Phase 66. |

Run Phase 66 outreach in rank order: hit a dozen Rank 1 prospects
before broadening to Rank 2; broaden to Rank 3 only if Rank 1+2
yield no qualified responses after two outreach cycles.

## 2. Specialty-tiered fit signals

Beyond the eight general qualifying signals in
`docs/commercial/phase-64-buyer-qualification-checklist.md` § A,
look for these specialty-tiered signals when researching a
prospect:

### 2.1 Retina (Rank 1)

- Provider records fundus findings as freehand sketches or
  dictated text in the chart today.
- Practice screens for retinal tears / detachments / vitreous
  haemorrhage in clinic.
- Provider does post-injection follow-ups in clinic
  (anti-VEGF cadence drives chart volume).
- Practice has a technician handling intake before the provider
  enters the room.
- Provider mentions after-hours charting as a problem in any
  public post, talk, or interview.

### 2.2 Glaucoma / comprehensive ophthalmology (Rank 2)

- Practice does in-office IOP checks at scale.
- Visual field testing is a recurring intake step.
- Provider mentions "structured intake" or "intake redo" as a
  problem.
- Practice has a stable technician roster (training churn would
  reduce pilot value).
- Practice uses a documented chart template the provider
  signs / locks today.

### 2.3 Multi-specialty eye-care (Rank 3)

- A single named champion provider with explicit authority.
- The champion's subspecialty maps to Rank 1 or Rank 2 above.
- Practice manager is willing to scope a 30/60/90-day pilot to
  one or two providers and one location.
- IT lead is reachable for a security-review conversation
  separately.

## 3. EHR / system signals

What the prospect uses today is a real signal — both for fit and
for what to NOT promise.

| EHR / system | Signal | Outreach posture |
|---|---|---|
| Modernizing Medicine (ModMed / EMA) | Common for ophthalmology + retina. ChartNav is a workflow layer, not a ModMed replacement. | Lead with "alongside your existing EHR." Do not claim ModMed integration. |
| Eye Care Leaders / iMedicWare / Compulink | Common in independent ophthalmology. | Same posture as ModMed. |
| RevolutionEHR | Common in optometry / mixed eye-care. ChartNav is provider-reviewed documentation support, not a Revolution feature. | Same posture. |
| Epic (system-affiliated) | Health-system signal; usually Rank 5 deprioritized. | No outreach in Phase 66. |
| Cerner / Oracle Health | Same as Epic. | No outreach in Phase 66. |
| Custom / homegrown | Possible Rank 2 fit but BAA + integration scope is uncertain. | Discovery only; do not promise integration. |
| No EHR (paper / hybrid) | Disqualifier. ChartNav is not a certified EHR. | Decline politely. |

## 4. Where the disqualifiers live

The hard disqualifiers stay in
`docs/commercial/phase-64-buyer-qualification-checklist.md` § B.
ChartNav does not pursue any of these prospect-side demands:

- certified-EHR replacement demand (ChartNav is not a certified EHR)
- autonomous-scribe demand (ChartNav does not provide an AI scribe)
- real-PHI-on-day-one demand (ChartNav does not process real PHI before security review)
- deep-EHR-writeback demand (ChartNav does not commit to bidirectional EHR writeback in a pilot)
- enterprise procurement demand (ChartNav does not pursue enterprise procurement on day one)
- production LLM demand (ChartNav does not run a production LLM today)
- fundus image interpretation demand (ChartNav does not interpret fundus images)
- device integration / RPM demand (ChartNav does not integrate with medical devices)
- HIPAA-certification-as-precondition demand (ChartNav is not HIPAA-certified)

Phase 66 does not duplicate that list. Any disqualifier from § B
fires → pause the prospect; do not advance from outreach to demo
until the
disqualifier dissolves.

## 5. Outreach sources to use

In rough order of conversion-rate confidence:

1. **Personal network** — provider friends, residency / fellowship
   classmates, referral colleagues.
2. **Conference connections** — ASRS, AAO, ASCRS attendees the
   founder has met in person.
3. **Targeted LinkedIn searches** — `(Retina OR Ophthalmology) AND
   ("owner" OR "practice manager") AND (small practice OR
   private practice)` with state / region filters.
4. **Specialty-society directories** — public-facing member
   directories for ASRS, AAO, ASCRS chapter listings.
5. **Public clinical talks** — provider has spoken about
   documentation burden, intake friction, or after-hours
   charting in the last 24 months.

Do **not** use:

- Purchased contact lists.
- HIPAA-violation news lists (e.g., breach-reporting databases).
- Generic mass-email outreach platforms.
- Cold-call boiler-room patterns.

## 6. Outreach cadence per prospect

- **Cycle 1** — founder-led email or LinkedIn DM. (See
  `phase-66-founder-led-outreach-templates.md`.)
- **Cycle 2 (7-10 business days later)** — single short follow-up
  using the Phase 64 follow-up email
  (`phase-64-follow-up-email-v1.md`) or a one-line LinkedIn DM
  follow-up.
- **Cycle 3** — none. If no reply after Cycle 2, mark the
  prospect's outreach-tracker row `paused` per
  `phase-64-outreach-tracker-schema.md`.

If a prospect responds and qualifies, move to
`phase-66-buyer-discovery-questions.md` for the first call.

## 7. Pilot-ready signals during the demo

When the prospect agrees to a controlled fake-data demo, watch
for these signals during the 15-minute walk:

| Signal | Why it matters |
|---|---|
| Provider voices a specific workflow they own (not "what does it do?" but "where does intake go?") | Owns workflow; can scope a pilot. |
| Provider names a specific user (technician, scribe, midlevel) by role | Pilot scope is real; not theoretical. |
| Provider asks about real-PHI gating instead of demanding it | Understands the safety frame. |
| Provider asks about pilot length / scope (not pricing first) | Engagement, not RFP. |
| Provider says some version of "we'd start with one or two providers" | Right size for first pilot. |

Anti-signals during the demo:

| Anti-signal | Why it matters |
|---|---|
| Provider asks for HIPAA-certification documentation as a precondition | Phase 64 § B disqualifier. |
| Provider asks for an ambient scribe / hands-free workflow | Not a fit; ChartNav does not do that. |
| Provider asks for fundus / OCT image interpretation | Not a fit. |
| Provider asks for production LLM / a specific vendor (GPT, Claude, watsonx) by name as a precondition | Phase 64 § B disqualifier — production LLM is not approved today. |
| Provider asks for a multi-site rollout date during the first call | Pilot is too narrow for them; deprioritize. |

## 8. Safety note

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
- `docs/commercial/phase-64-buyer-qualification-checklist.md` (general qualifier + disqualifier universe)
- `docs/commercial/phase-64-one-page-buyer-brief.md` (what to send first)
- `docs/commercial/phase-66-founder-led-outreach-templates.md`
- `docs/commercial/phase-66-buyer-discovery-questions.md`
- `docs/commercial/phase-66-what-not-to-promise-cheat-sheet.md`
