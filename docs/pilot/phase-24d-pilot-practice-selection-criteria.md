# Phase 24D — Pilot Practice Selection Criteria

> **Phase:** 24D — Pilot Practice Selection & Outreach Packaging.
> **Audience:** sales engineer / founder running the first 3–5
> ophthalmology pilot conversations.
> **Companion docs:**
> `phase-24d-pilot-outreach-message-bank.md` — email/LinkedIn copy.
> `phase-24d-pilot-discovery-call-script.md` — first call.
> `phase-24d-pilot-fit-scorecard.md` — score each candidate.
> `chartnav-pilot-readiness-checklist.md` — what must be true to
> demo/pilot.
> `chartnav-demo-to-pilot-transition-plan.md` — the gates from
> demo → controlled pilot.

## 1. Purpose

Phase 24C made the Morgan Lee retina demo reliably repeatable. Phase
24D is about choosing the right **practices** to point that demo at.
The cost of a bad-fit pilot is not zero — a buyer who wants
autonomous diagnosis or automatic billing will keep pulling on those
threads even after we say no, and that drains the team. The right
buyer is one whose pain matches what ChartNav coordinates today:
clinic lane handoffs, role-based queue visibility, imaging metadata
review, retina tracking, provider-reviewed documentation, and
internal follow-up tasking — all with fake data first.

This document defines who we **should** spend the next 3–5 demo
slots on, and who we should politely decline.

## 2. Primary pilot target — ophthalmology

ChartNav is ophthalmology-specific by intent. Phase 21C codified the
specialty positioning; Phase 24B/24C built the Morgan Lee retina
follow-up wedge. The first pilots must reinforce that positioning.

- Specialty: ophthalmology only. No optometry-first practices, no
  general primary care.
- Sub-specialty preference: **retina-heavy** practices, or mixed
  ophthalmology practices with a meaningful retina line. Glaucoma /
  cataract-heavy is acceptable as long as the practice has an
  imaging review bottleneck.
- Practice size: **2–10 providers** preferred. Smaller than 2 lacks
  the multi-role coordination problem ChartNav solves. Larger than
  10 introduces enterprise procurement that does not fit a
  controlled fake-data pilot.
- Locations: 1–3. Multi-location is fine and reinforces Phase 22
  multi-clinic positioning, but it is not required.
- Volume: high-volume clinic days (≥ 50 visits/provider/week)
  preferred — that is when the lane handoffs hurt most.
- Pain signals (any two of the following):
  - documentation lag (notes finalize > 24 h post-visit)
  - imaging review coordination problems (OCT/fundus captured but
    not surfaced to MD on time)
  - technician handoff friction (workup not visible to MD until the
    patient is in the chair)
  - follow-up tasking gaps (internal staff missing the follow-up
    window)
  - role visibility gaps (front desk / tech / MD / reviewer all
    using different lists)
- Leadership posture: **open to controlled pilot**, comfortable
  with a fake-data demo first, willing to engage on security review
  before any real PHI is loaded.
- Real-PHI posture: **fake-data demo first**. The practice must be
  able to evaluate ChartNav meaningfully without real patient data.
  Practices that require real PHI on day one are deferred until the
  Phase 23 real-PHI gate is satisfied for them specifically.

## 3. Good-fit segments — five flavors of "yes"

Score a candidate as "yes" if any one of these holds and the
forbidden-list (§4) is empty.

### 3.1 Retina-only or retina-heavy clinic

- ≥ 60 % retina volume, OR a dedicated retina sub-group inside a
  larger ophthalmology practice.
- OCT + fundus photography are core imaging modalities.
- Anti-VEGF injection scheduling is a real operations problem (the
  practice — not ChartNav — owns dosing).
- Likely champion: retina physician or retina ops lead.

### 3.2 Multi-provider ophthalmology practice (2–10)

- ≥ 2 providers sharing technicians and imaging staff.
- Roles already break down to front desk + technician + MD +
  reviewer + admin (Phase 20C taxonomy maps cleanly).
- Likely champion: practice administrator or COO.

### 3.3 Practice administrator / operations-minded buyer

- Decision-maker is administrative, not clinical.
- Pain centered on visibility, role accountability, and follow-up
  task accountability — not on "AI doing more for me."
- Likely champion: practice administrator, COO, or director of
  operations.

### 3.4 Practice with technician lanes and imaging bottlenecks

- Workup → imaging → MD is a real lane (not an unstructured "ask
  the tech to grab the OCT").
- OCT or fundus photo capture is upstream of the MD encounter and
  metadata visibility is patchy.
- Likely champion: technician supervisor + clinical champion
  jointly.

### 3.5 Practice considering AI documentation but cautious

- Already talked to one or more AI-scribe vendors and pulled back
  because of overclaiming, autonomy concerns, or compliance posture.
- Wants to see a product whose safe-claims contract is in the
  product, not in the marketing.
- Likely champion: a clinical champion who personally vetoed
  another AI vendor.

## 4. Bad-fit / not-now — refuse politely

If any one of these is true, decline the pilot or defer until the
relevant gate is satisfied. Do not bend the safe-claims contract to
win the deal.

- **Solo practice with no operational complexity.** ChartNav's
  value lives in cross-role coordination; a one-provider clinic
  does not have the lane handoffs to reward the product.
- **Buyer only wants cheap dictation.** ChartNav is not the cheapest
  scribe. The product wedge is workflow coordination, not
  dictation-only.
- **Buyer wants autonomous diagnosis.** Refuse. ChartNav does not
  diagnose, classify severity, or grade disease.
- **Buyer wants automatic billing / coding / claims.** Refuse.
  ChartNav does not bill, code, or submit claims.
- **Buyer wants immediate real-PHI deployment without BAA / security
  review.** Defer until the Phase 23 real-PHI go-live gate is
  satisfied for that practice (BAA executed, practice security
  review complete, production auth, approved hosting, backups,
  monitoring, incident contacts, written practice approval).
- **Buyer wants device integration as a hard day-one requirement.**
  Defer. ChartNav stores imaging metadata only; specific OCT /
  fundus camera vendor integrations are roadmap items, not current
  state.
- **Buyer wants patient portal / messaging automation.** Refuse.
  ChartNav does not message patients. The only follow-up tasks
  ChartNav creates are internal staff coordination.
- **Buyer wants ChartNav to replace the certified EHR.** Refuse.
  ChartNav is a coordination layer; the practice's EHR remains the
  system of record.

## 5. Ideal buyer persona

| Attribute | Description |
|---|---|
| Title | Practice administrator, COO, retina physician/owner, or director of clinical operations |
| Years in role | ≥ 2 (so they understand the lane cycle, not just the surface UI) |
| Span of control | Authority to approve a fake-data pilot without escalation |
| Pain articulation | Can name at least two specific lane handoffs that fail this week, not just "we need better tools" |
| Posture | Skeptical of AI overclaiming; values operational discipline over hype |
| Real-PHI urgency | Comfortable with a fake-data evaluation phase before BAA / production deploy |

## 6. Roles to identify per practice

For every candidate, name a human in each of these roles before the
demo. Missing roles are not blockers but signal lower readiness.

| Role | Why we need them |
|---|---|
| **Decision maker** | Owns the budget and the contract; signs the pilot agreement. Usually owner or administrator. |
| **Clinical champion** | A provider who will personally vouch for the workflow and absorb the friction of any new tool. Usually a retina or attending MD. |
| **Operations champion** | The person who runs the lane cycle day-to-day. Usually a practice administrator, lead technician, or ops director. |
| **Security / legal gatekeeper** | Approves BAA execution and security review. Usually IT director, compliance officer, or outside counsel. May be the same person as the decision maker in smaller practices. |
| **End-user voices** | At least one front-desk + one technician + one reviewer the team can observe during the pilot. Not required at the discovery stage. |

Map these roles in
`phase-24d-pilot-tracker-template.md` before the discovery call.

## 7. Discovery questions

Use these in the first 30-minute call (`phase-24d-pilot-discovery-call-script.md`
covers cadence and scoring). Ask conversationally; do not interview.

1. How many providers does the practice have, and how do they split
   across retina / glaucoma / cataract / general ophthalmology?
2. How many locations? Same EHR across all of them?
3. Walk me through a typical retina follow-up — who touches the
   patient, in what order, and where does the chart record live at
   each step?
4. What is the typical lag between visit close and note finalize?
   How often does that lag exceed 24 hours?
5. Where does OCT macula / fundus photo metadata live today? Who
   sees it before the MD walks into the room?
6. How does the technician hand the patient off to the MD —
   verbally, via the EHR, via paper, or via something else?
7. What is the internal follow-up tasking process after a retina
   visit closes — who confirms the next visit and how?
8. Who reviews and signs off on the day's notes — the same
   provider, a reviewer, or both?
9. What is the practice's current EHR? Any current AI scribe /
   documentation tool in use or recently evaluated?
10. Who in the practice approves a fake-data pilot? Who would
    approve a real-PHI pilot if we got that far?
11. What is the practice's security review process for new
    software? Has the practice run that process for any AI tool
    recently?

## 8. Red flags

Stop, name the red flag aloud, and either re-scope the conversation
or move to a graceful decline. Do not "manage" the buyer past a red
flag — the safe-claims contract does not survive that.

- The buyer keeps asking variations of "but can it auto-grade DR
  /just diagnose / pick the right anti-VEGF dose?" after one
  explicit "no." Refuse.
- The buyer wants real PHI on day one and is not willing to do a
  fake-data evaluation. Defer.
- The buyer wants ChartNav to replace the certified EHR. Refuse.
- The buyer wants patient messaging or claims submission. Refuse.
- The buyer treats the safe-claims contract as something to
  negotiate. Decline.
- The buyer cannot articulate a single specific lane-cycle pain
  during discovery. Park as a nurture, not a priority pilot.
- The buyer's compliance officer is not reachable and the buyer
  proposes "we'll worry about security later." Defer until the
  gatekeeper is identified.

## 9. Pilot acceptance criteria — what makes a "yes"

A practice is accepted into the priority pilot wave only if **all**
of these hold:

1. Practice fits §2 and at least one §3 segment.
2. Zero items from §4 (forbidden-list) are present.
3. Decision maker + clinical champion + ops champion + security
   gatekeeper are identifiable by name (any one of the four may be
   the same person in a small practice).
4. Pain articulation passes the §7 discovery: the practice can name
   at least two specific, recurring lane handoffs that fail today.
5. Fit score on
   `phase-24d-pilot-fit-scorecard.md` ≥ 24 / 30.
6. Practice can commit to **fake-data evaluation first**, with real
   PHI deferred behind BAA / security review.
7. Practice can stand up a clinical champion willing to sit through
   a 30-minute discovery + 30-minute demo + 60-minute pilot
   onboarding within a four-week window.

Anything below those bars goes to "nurture" or "not-now." That is
fine — saying "yes" to the wrong practice is more expensive than
saying "no" to the right one.

## 10. References

- `phase-24d-pilot-outreach-message-bank.md` — outreach copy.
- `phase-24d-pilot-discovery-call-script.md` — first-call script.
- `phase-24d-demo-invite-and-agenda.md` — demo invite template.
- `phase-24d-post-demo-follow-up-template.md` — post-demo email.
- `phase-24d-pilot-fit-scorecard.md` — score each candidate.
- `phase-24d-pilot-objection-cheat-sheet.md` — buyer-safe answers.
- `phase-24d-pilot-tracker-template.md` — pipeline tracker (no PHI).
- `chartnav-pilot-readiness-checklist.md` — what must be true to
  demo / pilot.
- `chartnav-demo-to-pilot-transition-plan.md` — demo → pilot gates.
- `chartnav-known-limitations-and-non-goals.md` — the product's
  scope contract.
- `docs/security/chartnav-real-phi-go-live-gate.md` — Phase 23
  real-PHI gate (referenced for §4 deferrals).
