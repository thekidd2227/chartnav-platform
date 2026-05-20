# Phase 64 Buyer Outreach Package Plan

Date: 2026-05-20
Status: planning and audit artifact only
Scope: docs-only plan for safe buyer outreach package creation after Phase 63A stabilizes

## 1. What Phase 64 Is

Phase 64 is the **Buyer Outreach Package** phase.

Goal: prepare controlled, safe outreach materials for paid pilot conversations with realistic ophthalmology buyers after Phase 63A makes the local demo automation and media evidence stable enough to support outreach.

Phase 64 is:

- a commercial-readiness documentation phase;
- a controlled outreach-prep phase;
- a paid-pilot conversation package;
- an internal safety-gated packaging step.

Phase 64 is not:

- a public launch;
- a public website update;
- a real-PHI deployment;
- a production LLM rollout;
- a claim that ChartNav has customer traction, pilot commitments, compliance certification, or final pricing.

## 2. Readiness Gates Before Phase 64 Implementation

Do not start Phase 64 implementation until these gates are known:

| Gate | Required state | Evidence path / check |
|---|---|---|
| Phase 63A stability | Phase 63A local demo automation and actual media capture readiness are complete enough for outreach support. | Phase 63A branch or merged PR notes. |
| Demo media status | Actual demo screenshots/videos exist, or every missing media item is explicitly marked as missing/deferred. | `artifacts/phase-62/`, `artifacts/phase-63/` if present, Phase 63A media index. |
| Dry-run report | A completed dry-run report exists, not only a blank template. | `artifacts/phase-62/dry-runs/` or Phase 63A dry-run output. |
| Buyer-demo decision | GO/NO-GO status is known before outreach materials imply demo readiness. | `docs/demo/phase-62a-buyer-demo-go-no-go-status.md` if present. |
| Safety checks | Claim scanners, runtime safety validator, Alembic safety, and diff hygiene pass. | Validation commands in Section 11. |
| Repo state | No unresolved local conflicts, duplicate branches, or uncommitted implementation changes are mixed into Phase 64. | `git status --short`, PR diff review. |
| Product truth | Current product truth remains accurate and is linked by all outward-facing draft materials. | `docs/build/current-product-truth.md`. |

If any gate is unknown, Phase 64 may proceed only as internal planning. It must not produce outreach-ready copy.

## 3. Required Phase 64 Deliverables

Include exactly these deliverables in the later Phase 64 implementation:

1. one-page buyer brief
2. outreach email v1
3. follow-up email v1
4. short LinkedIn DM script
5. 60-second call opener
6. buyer qualification checklist
7. paid pilot positioning memo
8. pilot success metrics draft
9. objection-handling insert linked to Phase 61 Q&A
10. security-review packet index
11. demo asset index pointing to Phase 63 media
12. internal CRM/outreach tracker schema as markdown table

Do not add extra deliverable types in Phase 64 without a separate approval step.

## 4. Safe Positioning

Frame ChartNav as:

- a provider-reviewed workflow layer for ophthalmology practices;
- structured intake plus transcript-to-draft support plus retinal drawing assist plus doctor review/sign-off;
- a controlled fake-data demo available for buyer review;
- a candidate paid pilot subject to security review for any real-PHI use;
- a workflow layer that works alongside the practice's existing systems rather than replacing them.

Approved capability framing:

- Technician Workup & Vitals: manual structured intake with review prompts.
- Provider-Reviewed VisitDraft Assist: fake/demo clinician-provided transcript to draft for provider review.
- Provider-Reviewed Fundus Drawing Assist: clinician-entered findings to structured retinal diagram.
- Doctor review, attestation, and signed lock.
- Runtime safety validator and claim scanners as internal release-safety controls.

Commercial posture:

- keep outreach narrow and controlled;
- ask for paid pilot conversations, not broad public adoption;
- use fake-data demo evidence first;
- make real-PHI discussions conditional on security review;
- discuss pricing only as a hypothesis or discovery topic unless a separate approved pricing memo exists.

## 5. Forbidden Positioning

The following phrases or claims are blocked for positive use in Phase 64 outreach. They may appear only in an internal forbidden-phrase catalog, negative assertion, or claim-safety review context:

- AI scribe
- hands-free scribing
- ambient listening
- listens to the room
- ignores small talk while capturing findings
- autonomous documentation
- AI writes the note
- diagnostic AI
- fundus image interpretation
- OCT interpretation
- EHR replacement
- HIPAA compliant/certified
- production LLM
- OpenAI/Anthropic/IBM-powered clinical documentation
- automatic coding/billing/orders/referrals/messages
- device integration/RPM

Also block any implication that ChartNav:

- diagnoses;
- interprets fundus photos or OCT;
- recommends treatment;
- places orders, referrals, or messages;
- bills or codes;
- integrates with medical devices or remote patient monitoring;
- is a certified EHR;
- replaces the buyer's existing EHR;
- is approved for real PHI in demo mode;
- has a production LLM path approved today.

## 6. Target Buyer Profile

Prioritize realistic early paid-pilot conversations:

- small to mid-size ophthalmology or retina practices;
- provider-owner, managing physician, practice manager, or operations lead;
- practices with visible documentation burden, handoff friction, or structured-intake inconsistency;
- buyers open to a controlled paid pilot after a fake-data demo;
- buyers who do not require full enterprise procurement on day one;
- practices that can evaluate with limited users/providers and manual success metrics first.

Best-fit discovery signals:

- owner/operator can make or strongly influence pilot decisions;
- practice has a repeatable clinical workflow to test;
- buyer is willing to start with fake-data demo review before real-PHI discussion;
- buyer can define one or two narrow success metrics;
- buyer accepts that ChartNav is a workflow layer, not a system-of-record replacement.

## 7. Non-Target Buyer Profile

Do not prioritize buyers that require:

- full health-system enterprise security package immediately;
- certified EHR replacement;
- autonomous scribe behavior;
- real-PHI production launch immediately;
- deep EHR writeback before a pilot;
- device integration or remote patient monitoring as the core pilot value;
- public compliance certifications as a precondition to a first conversation;
- broad multi-site rollout before a limited controlled pilot.

These buyers may be revisited later after security, integration, procurement, and compliance evidence matures.

## 8. Pilot Offer Boundaries

All pilot framing is hypothetical until approved separately.

Acceptable draft hypotheses:

- 30-day, 60-day, or 90-day controlled pilot;
- fake-data demo first;
- real-PHI use only after security review;
- limited users/providers;
- limited practice locations;
- manual success metrics first;
- no production LLM unless separately approved;
- no device integration, billing/coding, orders, referrals, or patient messaging;
- no EHR writeback commitment unless separately scoped.

Potential pilot success metrics to draft later:

- provider review completion rate;
- structured workup completeness;
- signed-artifact completion;
- provider-reported documentation friction;
- demo workflow completion time;
- number of defects or safety-stop events during the pilot;
- qualitative fit from provider and technician users.

Do not state revenue uplift, ROI guarantee, time savings, customer traction, or clinical outcome improvement as facts.

## 9. Required Evidence Links

The implementation agent should link to these existing repo paths where present:

- `docs/build/current-product-truth.md`
- `docs/demo/phase-61-controlled-buyer-demo-runbook.md`
- `docs/demo/phase-61-buyer-qa-safe-answers.md`
- `docs/demo/phase-62-end-to-end-demo-visit-script.md`
- `docs/demo/phase-62-controlled-buyer-demo-evidence-packet.md`
- `docs/demo/phase-62a-buyer-demo-go-no-go-status.md`
- `artifacts/phase-62/`
- `artifacts/phase-63/` if present after Phase 63A
- `docs/release/release-evidence-checklist.md`

Current observation from this planning branch:

- `docs/demo/phase-62a-buyer-demo-go-no-go-status.md` is present.
- `artifacts/phase-62/` is present.
- `artifacts/phase-63/` was not present on `origin/main` during this planning pass.

## 10. Instructions for the Implementation Agent

When Claude implements Phase 64 later:

- create docs only;
- no public website changes;
- no app/product code;
- no backend/frontend changes;
- no migrations;
- no deploy;
- no real PHI;
- no production LLM;
- no overclaims;
- run claim scanners and runtime safety.

Implementation should stay in `docs/commercial/` unless a specific evidence index needs to point to existing demo artifacts. It should not modify Phase 63 media capture work.

Every document should include a concise safety note:

- fake-data demo first;
- paid pilot subject to security review for real-PHI use;
- provider review and sign-off required;
- no diagnosis, image interpretation, treatment recommendation, orders, referrals, patient messaging, billing, coding, device integration, or RPM.

## 11. Validation Commands

Run these before opening the Phase 64 implementation PR and before merging this planning artifact:

```bash
bash scripts/check_commercial_claims.sh
bash scripts/check_website_claims.sh
bash scripts/check_demo_claims.sh
bash scripts/test_claim_policy_fixtures.sh
python3 scripts/check_runtime_safety.py
bash scripts/check_alembic_safety.sh
git diff --check
```

If system Python cannot run Alembic locally, rerun Alembic safety with the API virtualenv and report both outcomes:

```bash
PYTHON=apps/api/.venv/bin/python bash scripts/check_alembic_safety.sh
```

## 12. Recommended Phase 64 Output Filenames

Tell Claude to create, later, exactly:

- `docs/commercial/phase-64-one-page-buyer-brief.md`
- `docs/commercial/phase-64-outreach-email-v1.md`
- `docs/commercial/phase-64-follow-up-email-v1.md`
- `docs/commercial/phase-64-linkedin-dm-script.md`
- `docs/commercial/phase-64-call-opener.md`
- `docs/commercial/phase-64-buyer-qualification-checklist.md`
- `docs/commercial/phase-64-paid-pilot-positioning.md`
- `docs/commercial/phase-64-pilot-success-metrics.md`
- `docs/commercial/phase-64-security-review-packet-index.md`
- `docs/commercial/phase-64-demo-asset-index.md`
- `docs/commercial/phase-64-outreach-tracker-schema.md`

The objection-handling insert should be included inside the paid pilot positioning memo or the buyer qualification checklist and link back to `docs/demo/phase-61-buyer-qa-safe-answers.md`. Do not create an additional filename for it unless explicitly approved.

## 13. Internal CRM / Outreach Tracker Schema

Use this markdown table schema in the later tracker document:

| Field | Type | Required | Notes |
|---|---|---:|---|
| Practice name | text | yes | Do not add real patient information. |
| Specialty focus | enum/text | yes | Ophthalmology, retina, glaucoma, multi-specialty eye care, other. |
| Buyer contact role | enum/text | yes | Provider-owner, practice manager, operations lead, administrator, other. |
| Contact source | text | yes | Referral, LinkedIn, conference, direct research, existing relationship. |
| Outreach status | enum | yes | Not contacted, contacted, replied, qualified, demo scheduled, demo completed, pilot discussion, paused, closed no-fit. |
| Fit score | integer 1-5 | no | Based on Phase 64 qualification checklist. |
| Primary pain | text | no | Documentation burden, structured intake, handoff friction, demo curiosity, other. |
| Demo readiness | enum | yes | Not ready, fake-data demo ready, dry-run complete, buyer demo complete. |
| Real-PHI discussion requested | yes/no | yes | If yes, route to security review before any real-PHI use. |
| Security review status | enum | yes | Not started, requested, in review, approved for next step, blocked. |
| Pilot hypothesis | text | no | Keep as hypothesis, not a commitment. |
| Next action | text | yes | Concrete follow-up action. |
| Next action date | date | no | Use exact date. |
| Owner | text | yes | Internal owner. |
| Notes | text | no | No PHI, no secrets, no unsupported claims. |

## 14. Merge Recommendation

This planning artifact is safe to merge as docs-only if validation passes.

Recommended next step: Claude may implement Phase 64 **after Phase 63A completes or is stable enough to provide reliable media status**. If Phase 63A media is incomplete, Claude may still create internal outreach-package drafts, but every demo-asset reference must clearly mark missing/deferred media and the package must not be presented as buyer-ready.

Phase 64 implementation should remain docs-only and should not start public outreach until:

- Phase 63A media status is known;
- buyer-demo GO/NO-GO is known;
- the safety checks pass;
- all outreach language is reviewed against `docs/build/current-product-truth.md` and `docs/demo/phase-61-buyer-qa-safe-answers.md`.
