# Phase 24D — Pilot Fit Scorecard

> **Phase:** 24D — Pilot Practice Selection & Outreach Packaging.
> **Audience:** sales / founder triaging the first 3–5 candidate
> ophthalmology practices.
> **Companion docs:**
> `phase-24d-pilot-practice-selection-criteria.md` — who qualifies.
> `phase-24d-pilot-discovery-call-script.md` — where the scores
> come from.
> `phase-24d-pilot-tracker-template.md` — record the result.

Score each candidate practice **once** after the discovery call,
**once** after the demo, and **once** after the security-review
handoff. The numbers move; the recommendation is whichever score
is most recent.

The scorecard is not a marketing tool. It is a decision tool —
the cost of dragging a poor-fit practice through a controlled
pilot is high (operator time, distraction from real fits, and
pressure on the safe-claims contract). Use it.

---

## Score scale (per category)

| Score | Meaning |
|---|---|
| **0** | no fit — the buyer is explicitly opposed or the category does not apply |
| **1** | weak — pain exists but is small or unarticulated |
| **2** | moderate — pain is real and the practice can name it |
| **3** | strong — pain is sharp, named, and the practice has tried to fix it |

Total possible score: **30** (10 categories × 3).

---

## Scoring table

| # | Category | What you're scoring | Score (0–3) | Notes |
|---|---|---|---|---|
| 1 | **Operational pain severity** | How much does the lane-cycle pain cost the practice today (hours / week, missed visits, staff frustration)? | | |
| 2 | **Retina / imaging workflow fit** | Does the practice have retina-heavy or imaging-heavy volume that maps onto the Morgan Lee wedge (OCT macula, fundus photo, retina tracking, follow-up cadence)? | | |
| 3 | **Documentation / sign-off pain** | Is documentation lag and sign-off bottleneck a named, recurring problem? | | |
| 4 | **Multi-role coordination pain** | Do front desk + technician + MD + reviewer use different lists today, with handoffs that drop? | | |
| 5 | **Leadership urgency** | Is the decision maker actively prioritizing this problem (not "eventually")? | | |
| 6 | **Security / legal readiness** | Can the practice run a security review on a controlled-pilot tool inside a reasonable window (~30 days)? | | |
| 7 | **Pilot champion availability** | Is there a named clinical champion willing to sit through onboarding, give weekly feedback, and tolerate change? | | |
| 8 | **Ability to start fake-data evaluation** | Is the practice comfortable with the **fake-data evaluation phase first** before any real PHI is loaded? | | |
| 9 | **Willingness to provide feedback** | Will the practice commit to a 30-min weekly feedback call during the pilot? Will they share friction logs? | | |
| 10 | **Commercial potential** | If the pilot succeeds, can this practice plausibly become a paying customer at our target pricing? | | |
| | **Total** | sum of all 10 | **/30** | |

---

## Recommendation by total score

| Total | Recommendation | What to do next |
|---|---|---|
| **24–30** | **Priority pilot.** | Send security packet today; schedule the demo (or second demo); name an owner in the tracker. Move into the first wave. |
| **16–23** | **Nurture / second wave.** | Add to the nurture list. Check in every 60 days with one short relevant update. Re-score after the next conversation. |
| **8–15** | **Poor fit now.** | Politely decline the pilot. Offer to reconnect if any of the §4 red flags in the selection-criteria doc resolve. Do not consume more operator time. |
| **0–7** | **Do not pursue.** | Use Variant 8 ("Not a fit") in the message bank. Close the row in the tracker as `not fit`. |

A practice that scores below **24** but is the founder's personal
contact still does not get into the priority wave by default —
relationship asymmetry is the most expensive bias in pilot
selection. Use the score as evidence to defer politely.

---

## Mandatory disqualifiers (override the total)

Any one of these collapses the practice to "do not pursue"
regardless of the numeric score. Mark the disqualifier in the
tracker `notes` column.

- **No real PHI until gates complete.** If the practice will not
  do a fake-data evaluation phase and demands real PHI on day
  one, the candidate is disqualified until the Phase 23 real-PHI
  gate is satisfied.
- **No pilot if the buyer requires unsupported automation.** If
  any of "autonomous diagnosis," "automatic OCT interpretation,"
  "auto-grade DR," "auto-select IOL," "auto-recommend anti-VEGF,"
  "automatic orders," "automatic referrals," "automatic patient
  messaging," "automatic coding," "automatic billing," or
  "claims submission" is a day-one requirement, the candidate is
  disqualified.
- **No pilot if the buyer wants device integration as a day-one
  requirement.** ChartNav stores imaging metadata only.
- **No pilot if the buyer expects ChartNav to be a certified
  EHR or to replace the certified EHR.** The product is a
  workflow layer.
- **No pilot if the buyer expects ChartNav to be HIPAA compliant
  or HIPAA certified out of the box.** The product is not
  marketed as either. Real-PHI use is gated per practice via the
  Phase 23 readiness gate.

---

## Scoring example (illustrative, fully synthetic)

A retina-heavy 4-provider practice with named clinical champion,
documented technician handoff friction, willing to run a
fake-data evaluation, security gatekeeper identified:

| # | Category | Score | Reasoning |
|---|---|---|---|
| 1 | Operational pain severity | 3 | Technician handoff and follow-up tasking each cost > 2 h / day. |
| 2 | Retina / imaging workflow fit | 3 | Retina is 70 % of volume; OCT + fundus daily. |
| 3 | Documentation / sign-off pain | 2 | Note finalize > 24 h about 40 % of visits. |
| 4 | Multi-role coordination pain | 3 | Five named lane handoffs that drop weekly. |
| 5 | Leadership urgency | 2 | Administrator is prioritizing this quarter. |
| 6 | Security / legal readiness | 2 | IT director identified; can run review in ~30 days. |
| 7 | Pilot champion availability | 3 | Clinical champion (retina MD) volunteered on the discovery call. |
| 8 | Ability to start fake-data evaluation | 3 | Comfortable with fake-data evaluation phase. |
| 9 | Willingness to provide feedback | 2 | Will commit to weekly 30-min feedback calls. |
| 10 | Commercial potential | 2 | Plausible at target pricing if pilot succeeds. |
| | **Total** | **25 / 30** | **Priority pilot.** |

No mandatory disqualifiers triggered. Move into the first wave.

## References

- `phase-24d-pilot-practice-selection-criteria.md`
- `phase-24d-pilot-discovery-call-script.md`
- `phase-24d-pilot-tracker-template.md`
- `phase-24d-pilot-objection-cheat-sheet.md`
- `chartnav-pilot-readiness-checklist.md`
- `chartnav-known-limitations-and-non-goals.md`
- `chartnav-pilot-success-metrics.md`
- `docs/security/chartnav-real-phi-go-live-gate.md`
