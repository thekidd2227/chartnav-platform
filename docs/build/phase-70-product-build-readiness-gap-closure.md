# Phase 70 - Product Build Readiness: Demo-to-Sell Gap Closure

## 1. Executive summary

ChartNav has no active buyer dependency for this phase. The immediate goal is product maturity before selling, not another buyer-outreach or demo-follow-up artifact.

Phases 64 through 69 created useful commercial and controlled-demo operating materials. Those docs should remain available for later buyer conversations, but the next highest-value work is software hardening: make the existing application feel coherent, persistent, reviewable, and credible enough that a buyer can understand what has actually been built.

Phase 63C changed the readiness baseline in an important way. The live functional smoke now verifies core fake-data workflows over HTTP instead of relying on media capture or screenshots. That proves the controlled demo path can execute locally. It does not prove real-PHI readiness, production readiness, customer readiness, or broad workflow depth.

Recommendation: move to Phase 71 as a coding phase focused on the retina visit workflow wedge. Use the existing Technician Workup, VisitDraft, Fundus Drawing Assist, and signed-lock surfaces as the foundation. Do not add diagnosis, image interpretation, billing, orders, referrals, patient messaging, device integration, or production LLM.

## 2. Current product capability map

| Capability | Current state | Smoke-tested | Demo-only / gated status | Product note |
|---|---:|---:|---|---|
| Core auth, role, and tenant scoping | Implemented for local/dev identities and backend route checks | Partial | Production auth remains outside this report | Admin, clinician, technician, reviewer, and front desk behavior exists in code paths, but buyer-facing role journeys still need polish. |
| Patient and encounter workflow | Implemented | Yes | Fake seeded demo patient is the primary reliable path | Phase 63C verifies Morgan Lee / encounter state after reset. The product still needs stronger patient/encounter consistency and visible recovery when local state drifts. |
| Technician Workup & Structured Vitals | Implemented | Yes | Fake-data demo safe; real-PHI pilot remains gated | Backend routes support create, update, review, sign, immutability, BMI calculation, warnings, and metadata-only audit details. |
| Provider-Reviewed VisitDraft Assist | Implemented for fake/demo transcript workflows | Yes | Fake-data/demo-only unless security gates approve otherwise | The workflow drafts from clinician-provided transcript text and requires provider review and finalization. It is not autonomous documentation. |
| Provider-Reviewed Fundus Drawing Assist | Implemented | Yes | Fake-data/demo clinician-entered findings only | The workflow generates a structured retinal drawing from clinician-entered findings. It is not fundus photo interpretation and does not diagnose. |
| Doctor review, attestation, and signed lock | Implemented across key workflows | Yes | Demo-safe; production policy still gated | Vitals, VisitDraft, and Fundus include review/sign paths. Buyer-visible audit trace needs stronger surfacing. |
| Clinical / Ophthalmology workspace | Implemented as a tabbed product surface | Partial | Some panels are placeholders or disabled | Shortcuts are intentionally disabled review prompts today, which can read as broken unless the UI explains the current state better. |
| Overview | Implemented | Partial | Some cards are planned placeholders | Patient snapshot, status, timeline, and transitions render. Recent encounters, tasks, and favorites contain future-state empty copy. |
| Imaging pipeline metadata | Implemented as review metadata surface | Partial | Real imaging integrations are production-gated | The imaging tab is mostly review/metadata and placeholder surfaces. It does not interpret images or order imaging. |
| Orders / Labs review | Implemented as review-only placeholder surface | Not in Phase 63C smoke | Review-only | Buttons are disabled and safe. There is no order placement, referral, billing, or coding workflow. |
| Calendar | Implemented as read-only encounter scheduling view | Not in Phase 63C smoke | Read-only | ChartNav does not book appointments. |
| Communications | Implemented as local internal-note surface | Not in Phase 63C smoke | Local demo state only | Internal staff notes persist to localStorage. No patient-send behavior exists. |
| Documents | Implemented as local metadata index | Not in Phase 63C smoke | Local demo state only | File metadata can be logged locally. File bytes are not uploaded. |
| Chat | Implemented as local internal staff chat | Not in Phase 63C smoke | Local demo state only | Demo-local internal chat persists to localStorage and has no patient messaging. |
| Billing Review | Not implemented as a product workflow | No | Not a goal | Current code intentionally avoids billing and coding. Any buyer-facing "billing review" language should be treated as a scope risk unless it says review-only and no coding/billing. |
| Demo reset and functional smoke | Implemented | Yes | Local fake-data demo only | `scripts/demo/phase63c_functional_smoke.sh` is the right readiness gate for controlled fake-data demos. |
| Claim scanners and runtime safety | Implemented | Yes, via validation commands | Required before commercial/demo use | Claim and runtime safety checks remain core release gates. |
| FHIR / EHR integration | Seams and docs only | No | Production-gated | ChartNav is not a certified EHR and does not replace a certified EHR. Integration remains a future controlled scope. |
| Production LLM | Not approved | No | Disabled / blocked | No production LLM is approved. Fake-data/demo assist must not be used with real PHI. |

## 3. Buyer-visible product gaps

| Gap | Current observation | Buyer impact | Suggested phase |
|---|---|---|---|
| Persistence and refresh behavior | Phase 63C verifies backend persistence, but the UI still needs a crisp refreshed-state story across Vitals, VisitDraft, and Fundus. | Buyers trust signed workflows only if state survives navigation and refresh without ambiguity. | Phase 71 |
| Patient and encounter consistency | Demo reset can restore the Morgan path, but prior QA found local Maria/QA records after manual use. | A buyer demo can lose credibility if identity, MRN, provider, or encounter number appears inconsistent. | Phase 74 |
| Retina workflow coherence | Strong pieces exist, but they are spread across Clinical, Documentation, Imaging, and Overview tabs. | The product story feels like several tools rather than one retina visit workflow. | Phase 71 |
| Fundus drawing usefulness | Fundus generation, warning, render, review, and sign exist, but the drawing needs stronger editability, legend clarity, and review affordances. | Retina buyers will judge whether the diagram helps a real provider workflow, not just whether an SVG appears. | Phase 72 |
| VisitDraft usefulness | Fake transcript to draft works, but note quality, missing-data handling, editing ergonomics, and retina-specific output need product polish. | Documentation burden is a core pain point. The draft must feel reviewable, not just generated. | Phase 71 |
| Role-based workflow clarity | Backend RBAC exists, and technician cannot sign. UI still needs clearer handoff states between technician, clinician, reviewer, and admin. | Buyers need to understand who does what during a real clinic visit. | Phase 71 / Phase 73 |
| Audit trail visibility | Backend audit minimization exists, and Overview timeline can show events. The signed artifact audit story is not yet a productized panel. | Security-minded buyers will ask what changed, who reviewed, who signed, and what was excluded from logs. | Phase 73 |
| Billing review clarity | The current product avoids billing/coding. Some older surface expectations may still imply billing review. | Any ambiguity around billing/coding creates claim risk and product-scope confusion. | Phase 71 docs/UI language check |
| Onboarding and demo reset reliability | Reset and smoke scripts exist, but the operator path still depends on command-line discipline. | Demo reliability should not rely on memory or hidden local state. | Phase 74 |
| Error handling | Feature clients surface error text, but buyer-grade recovery, retry, empty-state, and "what to do next" handling is uneven. | A transient failure can look like broken product rather than recoverable local demo state. | Phase 71 |
| Production-readiness disclaimers | Safety boundaries exist in docs and many panels, but fake/demo vs pilot vs production can be more consistently labeled in-app. | Buyers may ask whether the software can touch real PHI now. The answer must be gated and consistent. | Phase 71 / Phase 73 |
| Export / share packet | No polished visit packet combines intake, VisitDraft, fundus drawing, signatures, and audit summary. | Buyers often need something concrete to circulate internally after a demo. | Phase 75 |
| EMR/EHR placeholder risk | Documentation / EMR/EHR tab name and placeholder integration language can imply more integration depth than exists. | Buyers may infer EHR writeback or replacement if the UI is not explicit. | Phase 71 |

## 4. Product wedge recommendation

Primary wedge: **A. Retina workflow wedge**.

Reason: the retina workflow wedge combines the strongest shipped surfaces into one specialty-specific buyer story: technician intake, ophthalmology findings, fundus drawing, provider-reviewed VisitDraft, doctor attestation, and signed lock. It is more differentiated than a generic documentation wedge, broader than fundus drawing alone, and more sellable than technician intake alone.

Secondary support wedges:

- **B. Ophthalmology documentation wedge** remains useful as the broader category, but it can sound like a generic documentation product unless anchored to retina workflow proof.
- **C. Fundus drawing assist wedge** is visually memorable, but it is too narrow as the first sellable wedge unless connected to a complete visit.
- **D. Technician intake + provider review wedge** is operationally valuable, but it does not carry the same specialty-specific differentiation by itself.

Product stance for Phase 71: make the fake-data retina visit feel like one coherent, provider-reviewed workflow from intake through signed artifact. Do not add new clinical scope.

## 5. Next five software build phases

### Phase 71 - Retina Visit Workflow Polish

Goal: make the existing retina visit path feel coherent, persistent, and buyer-ready across Overview, Clinical, Documentation, and Imaging.

Primary outcomes:

- Clear visit workflow status across Intake, VisitDraft, Fundus, and Review/Sign.
- Stable seeded-patient and encounter presentation.
- Stronger UI copy for review-only, fake-data, and no-real-PHI boundaries.
- Better recovery states when APIs fail or no artifact exists yet.
- Role-specific clarity for technician entry versus clinician review/sign.

### Phase 72 - Fundus Drawing Assist Usability Upgrade

Goal: make the fundus charting surface more useful as a provider-reviewed drawing tool.

Primary outcomes:

- Better drawing review affordances, legend clarity, laterality display, and signed snapshot.
- Safer edit/re-render path for unsigned charts.
- Clear distinction between clinician-entered findings and generated drawing.
- No image interpretation and no diagnosis language.

### Phase 73 - Provider Review / Signed Lock Audit Trail Upgrade

Goal: productize the review, signature, lock, and metadata-only audit story.

Primary outcomes:

- Buyer-visible artifact timeline for Vitals, VisitDraft, and Fundus.
- Clear signer, reviewer, timestamp, status, and warning-count display.
- Audit detail that remains metadata-only and avoids clinical free text.
- Better support for security-review questions.

### Phase 74 - Demo Reset + Seeded Patient Reliability

Goal: make local demo state deterministic and operator-friendly.

Primary outcomes:

- A reliable reset path for Morgan Lee / PT-1001 / Encounter #1.
- Clear operator checks before a demo starts.
- Stronger guardrails against stale local DB state.
- Optional UI-level demo readiness panel if it can stay fake-data only.

### Phase 75 - Exportable Buyer Demo Evidence Packet

Goal: create a fake-data-only visit packet that a buyer can inspect after a controlled demo.

Primary outcomes:

- Exportable summary of structured intake, VisitDraft, fundus drawing, signed lock, and safety boundaries.
- Clear fake-data labels.
- No PHI, no diagnosis, no image interpretation, no orders, no billing, and no EHR replacement implication.

## 6. Phase 71 implementation plan

### Scope

Phase 71 should be a coding phase, but a narrow one. It should polish the existing retina visit workflow and avoid new product categories.

Likely frontend files:

- `apps/web/src/ClinicalTabbedWorkspace.tsx`
- `apps/web/src/features/vitals/VitalsWorkupPanel.tsx`
- `apps/web/src/features/ambient/AmbientDocumentationPanel.tsx`
- `apps/web/src/features/fundus/FundusChartPanel.tsx`
- `apps/web/src/features/fundus/FundusChartEditor.tsx`
- `apps/web/src/DemoClinicalWorkflowGuide.tsx`
- `apps/web/src/GuidedDemoMode.tsx`
- `apps/web/src/test/ClinicalTabbedWorkspace.test.tsx`
- `apps/web/src/test/VitalsWorkupPanel.test.tsx`
- `apps/web/src/test/AmbientDocumentationPanel.test.tsx`
- `apps/web/src/test/FundusChartPanel.test.tsx`

Likely backend files only if a route support gap is proven:

- `apps/api/app/api/vitals_workup.py`
- `apps/api/app/api/fundus_charts.py`
- `apps/api/app/api/scribe_sessions.py`
- `apps/api/tests/test_vitals_workups.py`
- `apps/api/tests/test_fundus_charts.py`
- `apps/api/tests/test_scribe_sessions.py`

API routes likely reused:

- `GET /api/v1/encounters/{encounter_id}/vitals-workups`
- `POST /api/v1/encounters/{encounter_id}/vitals-workups`
- `POST /api/v1/vitals-workups/{workup_id}/review`
- `POST /api/v1/vitals-workups/{workup_id}/sign`
- `POST /api/v1/encounters/{encounter_id}/fundus-charts/generate`
- `POST /api/v1/fundus-charts/{chart_id}/review`
- `POST /api/v1/fundus-charts/{chart_id}/sign`
- `POST /patients/{patient_id}/scribe-sessions`
- `POST /patients/{patient_id}/scribe-sessions/{session_id}/draft-ambient`
- `POST /patients/{patient_id}/scribe-sessions/{session_id}/review`
- `POST /patients/{patient_id}/scribe-sessions/{session_id}/finalize`

### Acceptance criteria

- The seeded retina visit opens consistently with stable patient, MRN, encounter, provider, and organization context after demo reset.
- A buyer can understand the visit sequence without verbal rescue: Intake, Fundus Drawing, VisitDraft, Provider Review, Signed Lock.
- Vitals, VisitDraft, and Fundus each show clear empty, draft, reviewed, signed, locked, and error states.
- Refreshing the page after creating/reviewing/signing fake-data artifacts preserves visible state.
- Technician role can complete intake but cannot sign clinical artifacts.
- Clinician/admin roles can review/sign where existing backend rules allow.
- Reviewer/front desk limitations are explicit and not silent failures.
- Clinical shortcut pills do not appear broken. If still disabled, the UI must say why and where the active draft lives.
- The Documentation / EMR/EHR tab avoids implying real EHR writeback, EHR replacement, or certified EHR behavior.
- Orders/Labs and any billing-adjacent surfaces remain review-only and do not imply order placement, billing, or coding.
- No product UI says or implies diagnosis, treatment recommendation, image interpretation, autonomous documentation, orders, referrals, patient messaging, billing, coding, production LLM, or real-PHI demo use.

### Tests and smoke required

- Frontend: `cd apps/web && npx tsc --noEmit`
- Frontend: `cd apps/web && npx vitest run`
- Backend targeted tests if route behavior changes: `cd apps/api && .venv/bin/python -m pytest tests/test_vitals_workups.py tests/test_fundus_charts.py tests/test_scribe_sessions.py -q`
- Root safety checks:
  - `bash scripts/check_commercial_claims.sh`
  - `bash scripts/check_demo_claims.sh`
  - `bash scripts/check_website_claims.sh`
  - `bash scripts/test_claim_policy_fixtures.sh`
  - `python3 scripts/check_runtime_safety.py`
  - `git diff --check`
- Live local workflow gate if stack is running:
  - `PHASE63C_API_URL="http://127.0.0.1:8765" PHASE63C_WEB_URL="http://127.0.0.1:5173" bash scripts/demo/phase63c_functional_smoke.sh`

### Safety constraints

- Fake data only unless security/legal/environment gates are complete.
- No real PHI.
- No production LLM.
- No diagnosis.
- No treatment recommendation.
- No image interpretation.
- No EHR replacement language.
- No orders, referrals, patient messaging, billing, or coding.
- No new public marketing copy.
- No deployment.

## 7. Safety and product truth boundaries

ChartNav should continue to be described as a provider-reviewed ophthalmology workflow support layer.

Required boundaries:

- Provider review remains mandatory for clinical artifacts.
- Technician-entered intake is structured intake for provider review.
- VisitDraft Assist remains provider-reviewed and fake-data/demo-only unless later security gates approve a different path.
- Fundus Drawing Assist uses clinician-entered findings to support a structured drawing.
- Fundus Drawing Assist is not image interpretation.
- ChartNav does not diagnose.
- ChartNav does not recommend treatment.
- ChartNav does not place orders.
- ChartNav does not send referrals.
- ChartNav does not send patient messages.
- ChartNav does not bill or code.
- ChartNav is not a certified EHR.
- ChartNav does not replace a certified EHR.
- No production LLM is approved.
- No real PHI should enter fake-data demo adapters or local demo flows.

## 8. Validation

Commands run for this Phase 70 report:

```bash
bash scripts/check_commercial_claims.sh
bash scripts/check_demo_claims.sh
bash scripts/check_website_claims.sh
bash scripts/test_claim_policy_fixtures.sh
python3 scripts/check_runtime_safety.py
git diff --check
```

If the local demo stack is running, also run:

```bash
PHASE63C_API_URL="http://127.0.0.1:8765" PHASE63C_WEB_URL="http://127.0.0.1:5173" bash scripts/demo/phase63c_functional_smoke.sh
```

Results from this Phase 70 run:

| Check | Result |
|---|---|
| `bash scripts/check_commercial_claims.sh` | PASS - 0 fail / 0 warn |
| `bash scripts/check_demo_claims.sh` | PASS - 0 positive-claim hits across 34 demo files |
| `bash scripts/check_website_claims.sh` | PASS - 0 fail / 0 warn |
| `bash scripts/test_claim_policy_fixtures.sh` | PASS |
| `python3 scripts/check_runtime_safety.py` | PASS |
| `git diff --check` | PASS |
| Phase 63C functional smoke | Not run. Frontend returned HTTP 200, but API health at `http://127.0.0.1:8765/health` was not reachable during this audit run. |
