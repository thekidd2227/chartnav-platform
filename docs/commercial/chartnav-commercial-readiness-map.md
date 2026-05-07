# ChartNav Commercial Readiness Map

> What's commercially ready, what's demo-ready, what's pilot-
> ready, and what's not yet ready. Use to set realistic buyer /
> investor expectations.

---

## What exists now (built and on `main`)

### Product

- 8 modules in production code, all phase-numbered and
  documented:
  - Phase 6 — findings-to-retinal-diagram proposal review.
  - Phase 8 — AI scribe session lifecycle.
  - Phase 9 — provider-reviewed patient-friendly summaries.
  - Phase 10 — provider-facing pre-visit brief.
  - Phase 11 — provider action review queue.
  - Phase 12 — end-to-end clinical workflow smoke review (tests
    only, no new product surface).
  - Phase 13 — demo-ready clinical workflow package.
  - Phase 14 — pilot readiness / deployment hardening (docs
    only).
  - Phase 15 — commercial demo delivery system (Guided Demo
    Mode).
  - Phase 16 — website proof upgrade + conversion layer
    (landing page).

### Commercial

- 15 deck Markdown source files (Phase 17 — this work).
- 6 commercial support docs (master kit, claims language,
  objections, pricing, pilot handoff, this readiness map).
- 4 demo-package docs (startup, troubleshooting, review checklist,
  desktop delivery contract).
- Public landing page at `/?intro=1`.
- In-product Guided Demo Mode at `/?demo=1`.
- Pilot readiness packet (8 docs from Phase 14).
- Demo operator guide + demo environment README.

---

## What is demo-ready

✅ ChartNav is demo-ready today against fake demo data.

- Local stack boots via `make dev` (Phase 14 deployment guide).
- Guided Demo Mode renders the 7-stage workflow stepper with
  presenter cues.
- Demo reset script (`scripts/reset_demo_state.sh`) refuses
  non-local DB URLs and clears browser-side demo state.
- Phase 13 demo guide collapsible (default) on every workspace
  load.
- Phase 16 landing page accessible at `?intro=1` for buyer
  self-discovery.
- Phase 17 desktop demo package script
  (`scripts/export_chartnav_decks_to_desktop.sh`,
  `scripts/create_chartnav_desktop_demo_package.sh`) produces a
  presenter-ready folder on the operator's Mac.

---

## What is pilot-ready

✅ ChartNav is pilot-ready against fake data and (after gating)
real PHI.

- Pilot readiness packet (8 docs from Phase 14).
- Three deployment modes documented: local / staging /
  controlled-pilot.
- BAA + security review gating items enumerated and consistent
  across the readiness checklist, security packet, admin
  onboarding, demo-to-pilot transition plan, and pilot handoff
  checklist.
- Pilot fee firm at $10,000 flat for a 4–6 week pilot.
- Pilot success metrics template covers 10 metrics with
  baseline / target / cadence fields.
- Post-pilot decision framework (continue → paid pilot, pause,
  end).

What's pilot-blocking until provided per practice:

- Practice must execute a BAA.
- Practice must approve hosting / auth / audit retention /
  backups / monitoring.
- Practice must identify clinical champion + technical owner +
  security/compliance owner.
- Optional pen test / vuln scan if the practice requires one.

---

## What is not yet ready

⚠️ The following are **not** ready and are explicitly deferred.

### Operational

- **Paid pilot conversion data.** No paid pilots have run yet.
  Pricing is a hypothesis until validated.
- **Numeric ROI claims** for the website / decks. We use
  placeholders in the customer pitch template; no fabricated
  numbers anywhere.
- **First paying customer.** Target M3 = Q4 2026.
- **Multi-practice deployment.** Target M4 = Q4 2026.

### Product

- **External LLM source** under the same provider-review
  contract — deferred.
- **Specialty-specific risk scoring** (glaucoma progression,
  AMD progression, post-op infection risk, etc.) — deferred.
- **Patient-portal delivery** of any kind — deferred.
- **Orders / coding / billing** — deferred (and explicitly
  out-of-scope for this phase numbering).
- **Automated follow-up creation** (no calendar writes) —
  deferred.
- **Longitudinal trend analytics** across encounters — deferred.
- **EHR adapter integrations** beyond the existing FHIR adapter
  shape — deferred per practice.
- **Team queues / task-assignment routing** — deferred.

### Compliance

- **HIPAA certification** — software is not certified to HIPAA;
  covered entities and business associates implement HIPAA.
- **SOC 2 certification** — not pursued at this stage.
- **FDA clearance** — not pursued; ChartNav is documentation
  support, not a clinical decision device.
- **HITRUST** — not pursued at this stage.

### Sales / partner

- **Partner economics** (referral fee, pilot revenue share,
  customer revenue share, co-branded materials) — discussed per
  partner agreement, not published.
- **Public price page** — pricing is in commercial decks +
  conversations, not on the public website.
- **Out-of-repo media library** (screenshots, video clips) —
  shot list exists; media production is out of scope for the
  repo.
- **Commercial deck PDFs / .pptx files** — repo carries
  Markdown source; PDF / pitch-tool conversion happens
  out-of-repo.

---

## Recommended next actions

For sales:

1. Run the live fake-patient demo with at least one
   ophthalmology practice via the Phase 16 landing page.
2. Collect pilot agreement terms from the first practice that
   says yes; don't wait for a hypothetical "perfect" practice.
3. Sign the first paid pilot — target July 1, 2026.

For commercial:

1. Validate the pricing range against pilot agreements.
2. Track pilot conversion data from M1 (July 1, 2026) onward.
3. Update the pricing-notes doc only after operating data
   confirms or contradicts the hypothesis.

For partner / agency:

1. Identify 2–3 partner candidates with existing ophthalmology
   relationships.
2. Have 1:1 partner economics conversations (no public partner
   table).
3. Co-attend the first paid pilot with the partner who made
   the intro.

For investors:

1. Use `chartnav-investor-pitch-deck.md` (14 slides) +
   `chartnav-financial-fundraising-deck.md` (8 slides).
2. Stage and amount discussed live; not printed in deck.
3. No outside investors to date.

For federal-healthcare-adjacent buyers:

1. Use `chartnav-company-deck.md` with the credibility slide.
2. Reference SDVOSB + Mann-Grandstaff VA past performance.
3. Frame certifications as attaching to the operating entity,
   not the software product.

---

## Phase 18 candidate

**Phase 18 — first paid pilot or paid customer.** Operations
work, not new product. Required: signed pilot agreement,
controlled-pilot infrastructure stood up, real-PHI gating items
met, live success-metrics tracking. Target M1 = July 1, 2026.

Phase 18 must continue to obey the existing safety contract — no
new clinical features pulled forward, no autonomous diagnosis,
no orders / coding / referrals / patient messaging.
