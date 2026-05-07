# ChartNav Product Roadmap Deck

> 8 slides. Frames what's done, what's near-term, and what's
> deferred.

---

## Slide 1 — Cover

- **Title:** ChartNav product roadmap.
- **Visual:** logo only.

## Slide 2 — Completed Phases (build proof)

- **Title:** What's already on `main`.
- **Content:**
  - Phase 6 — findings-to-retinal-diagram proposal review.
  - Phase 8 — AI scribe session lifecycle.
  - Phase 9 — provider-reviewed patient-friendly summaries.
  - Phase 10 — provider-facing pre-visit brief.
  - Phase 11 — provider action review queue.
  - Phase 12 — end-to-end clinical workflow smoke review.
  - Phase 13 — demo-ready clinical workflow package.
  - Phase 14 — pilot readiness / deployment hardening.
  - Phase 15 — commercial demo delivery system.
  - Phase 16 — website proof upgrade + conversion layer.
- **Speaker notes:** Each phase has a contract doc in the repo.
- **Visual:** 10-row timeline.

## Slide 3 — Current capabilities

- **Title:** What ChartNav can do today.
- **Content:**
  - Provider-reviewed scribe lifecycle.
  - Provider-applied retinal proposals + OD/OS canvas + signed
    artifacts.
  - Provider-finalized patient-friendly summary draft.
  - On-demand pre-visit brief.
  - Provider action review queue (review tasks only).
  - Guided demo mode and pilot-readiness packet.
- **Speaker notes:** All eight modules render in production code.
- **Visual:** 6-bullet card.

## Slide 4 — Phase 17 (this work)

- **Title:** Commercial deck library + desktop demo package.
- **Content:**
  - 15 deck source files (Markdown).
  - Commercial support docs (claims language, objections, pricing,
    pilot handoff, readiness map).
  - Desktop export script that produces a single review folder
    on the operator's Mac at
    `/Users/jean-maxcharles/Desktop/chartnav decks`.
  - START / STOP / RESET .command files.
  - No new clinical automation, no backend changes.
- **Speaker notes:** Phase 17 is delivery + operator UX, not a
  new product.
- **Visual:** 5-bullet card.

## Slide 5 — Milestones

- **Title:** Near-term milestones.
- **Content:**
  - **M1 — first paid pilot:** July 1, 2026.
  - **M2 — five paid pilots:** October 1, 2026.
  - **M3 — first paying customer (post-pilot):** Q4 2026.
  - **M4 — multi-practice deployment:** Q4 2026.
- **Speaker notes:** Milestones are operations work, not new
  product.
- **Visual:** 4-row milestone table.

## Slide 6 — Deferred (high-risk areas)

- **Title:** Deferred — not promised.
- **Content:**
  - External LLM source under same provider-review contract.
  - Specialty-specific risk scoring (glaucoma, AMD, post-op
    infection).
  - Patient-portal delivery.
  - Orders / coding / billing.
  - Automated follow-up creation.
  - Longitudinal trend analytics.
  - EHR adapter integrations beyond FHIR shape.
  - Team queues / task assignment.
- **Speaker notes:** Saying "deferred" is a feature, not a flaw.
- **Visual:** 8-bullet card.

## Slide 7 — Why provider control stays central

- **Title:** Provider-in-control is the moat.
- **Content:**
  - Every artifact has explicit draft → review → finalize.
  - Signed artifacts are immutable in place.
  - Audit metadata-only.
  - Closed action-type vocabulary (no order can sneak in).
  - Cross-org isolation enforced by both code and CI tests.
- **Speaker notes:** This is what makes the moat hard to copy.
- **Visual:** 5-bullet card.

## Slide 8 — Roadmap risks

- **Title:** What could derail the roadmap.
- **Content:**
  - Pilot conversion timing (M1, M2 dates above are targets).
  - External-LLM safety contract design (when added).
  - Practice security review duration.
  - Hosting decisions per practice.
- **Speaker notes:** Be honest. No fake risks, no hidden risks.
- **Visual:** 4-bullet card.
