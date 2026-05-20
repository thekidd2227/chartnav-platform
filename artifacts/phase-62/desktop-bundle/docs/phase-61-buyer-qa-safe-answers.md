# Phase 61 — Buyer Q&A Safe Answers

> Read end-to-end before any controlled buyer demo. Every answer
> below is aligned with `docs/build/current-product-truth.md`. If
> that doc changes, this sheet must be re-aligned in the same PR.
> No legal / compliance attestation. No buyer-specific promises.
> Demonstrated in a fake / demo environment with no real PHI.

The "What to say" lines are operator-safe approximations the
operator can read aloud. The "Why" lines anchor the answer in the
canonical product-truth posture. Operators must not embellish.

---

## 1. "Is this an EHR?"

- **What to say:** "No. ChartNav is a provider-reviewed workflow
  layer that sits alongside your EHR. It captures structured intake,
  drafts notes, and drafts retinal diagrams — every one as a
  reviewable artefact the clinician signs."
- **Why:** Product truth: "ChartNav is not a certified EHR."

## 2. "Does ChartNav replace our EHR?"

- **What to say:** "No. ChartNav does not replace your EHR.
  The EHR remains the system of record. ChartNav drafts artefacts
  that the clinician reviews, signs, and forwards into your EHR via
  the existing workflows."
- **Why:** Product truth: "ChartNav does not replace a certified
  EHR." Claim scanners block "EHR replacement" / "replaces your
  EHR".

## 3. "Is ChartNav HIPAA compliant?"

- **What to say:** "Not by default. ChartNav today is a
  fake-data demo / development surface; real PHI use is gated behind
  a controlled-pilot process with its own security and access
  controls. We can walk you through the runtime safety validator,
  the audit posture, and the controlled-pilot gate; we don't make
  a HIPAA-compliance claim out of the box."
- **Why:** Claim scanners block "HIPAA compliant" / "HIPAA
  certified". The product-truth doc explicitly says ChartNav is
  designed to support HIPAA-aware workflows; it is **not**
  certified.

## 4. "Can this use real PHI?"

- **What to say:** "Only in environments that have gone through
  our controlled-pilot gate. The demo you're seeing right now is
  fake data. Real PHI use requires specific environment variables
  (`CHARTNAV_REAL_PHI_ENABLED`) plus a documented security review;
  the runtime safety validator refuses unsafe combinations like
  real-PHI + fake-data adapters or real-PHI in a stub integration."
- **Why:** `scripts/check_runtime_safety.py` enforces the gates;
  product truth says "No real PHI should use fake-data/demo
  adapters."

## 5. "Is this an ambient scribe?"

- **What to say:** "No. We don't ship hands-free scribing or
  ambient-scribe parity claims. We do have a fake-data
  transcript-to-draft assist that takes a clinician's typed or
  pasted transcript and drafts a structured provider-review note;
  the clinician reviews and signs every draft. We do not record
  audio in real time."
- **Why:** Claim scanners block "hands-free scribing", "ambient
  scribe parity", "autonomous documentation".

## 6. "Does this listen to the exam room?"

- **What to say:** "No. ChartNav does not record audio in the
  exam room. The ambient documentation feature processes a fake /
  demo transcript pasted into the workspace, not live audio."
- **Why:** No live audio ingest. The Phase 35 stub transcriber
  exists as a seam; live STT vendors are gated by
  `CHARTNAV_STT_PROVIDER` + vendor-approval env vars.

## 7. "Does it diagnose?"

- **What to say:** "No. ChartNav drafts structured artefacts from
  what the clinician entered. Out-of-range vital signs surface as
  review prompts, never as diagnostic conclusions. The Vitals and
  Ambient signed artefacts each carry a 'What ChartNav did NOT do'
  panel that lists diagnosis as `(false)`; Fundus Charting V1
  enforces the same posture through warnings, provider review/sign,
  signed-lock state, and the claim scanners — without a per-response
  forbidden-actions object today."
- **Why:** Claim scanners block "autonomous diagnosis" /
  "AI diagnoses" / "vital-sign diagnosis". Server-side
  `forbidden_actions.diagnosis=false` on every ambient and vitals
  response. Fundus does not expose a `forbidden_actions` field in
  V1; the "no diagnosis" guarantee comes from the surrounding
  product boundaries (no diagnostic language in warnings; provider
  review + sign + signed-lock; claim-scanner-blocked vocabulary).

## 8. "Does it interpret fundus photos or OCT?"

- **What to say:** "No. ChartNav drafts a structured retinal
  diagram from the clinician's typed findings — not from a photo.
  There is no computer vision step, no OCT auto-interpretation, no
  fundus-photo grading. Fundus warnings ask the clinician to
  confirm missing detail; they're review prompts, not findings."
- **Why:** Claim scanners block "fundus image interpretation" /
  "OCT interpretation" / "AI interprets fundus". Fundus V1 does
  not expose a `forbidden_actions` map; the image-interpretation
  guarantee comes from the deterministic `rule_based_v1` parser
  (no image input at all), the warnings panel, the provider
  review/sign flow, and the claim-scanner vocabulary block.

## 9. "Does it recommend treatment?"

- **What to say:** "No. ChartNav does not recommend treatment.
  Plan-as-stated in the ambient draft is exactly what the clinician
  said in the transcript; ChartNav does not extend it. The Ambient
  and Vitals 'What ChartNav did NOT do' panels list treatment
  recommendation as `(false)`."
- **Why:** Claim scanners block "treatment recommendation" /
  "AI prescribes". `forbidden_actions.treatment_recommendation`
  is pinned `false` server-side on the ambient and vitals
  responses. Fundus V1 does not return a `forbidden_actions`
  object; the no-treatment-recommendation posture is enforced via
  the deterministic parser (the fundus output contains drawing
  data only — no recommendation field exists in the schema) and
  the claim scanners.

## 10. "Does it place orders?"

- **What to say:** "No. ChartNav does not place orders. The
  Ambient and Vitals signed-artefact panels show orders as
  `(false)`. If a clinician's transcript mentions an order, the
  Ambient surface flags it as a safety prompt — not as an
  executed order."
- **Why:** Claim scanners block "automatic orders".
  `forbidden_actions.orders=false` on the ambient and vitals
  responses. The fundus surface stores drawing data only; there
  is no orders field in any fundus response schema.

## 11. "Does it send referrals or patient messages?"

- **What to say:** "No. ChartNav does not send referrals and
  does not message patients. The Ambient and Vitals signed-artefact
  panels show referrals and patient messages as `(false)`.
  Referrals and messaging stay in your existing EHR / patient-portal
  workflows."
- **Why:** Claim scanners block "automatic referrals" /
  "patient messaging" / "send patient message". Fundus V1 has no
  referral or messaging field in any response schema.

## 12. "Does it bill or code?"

- **What to say:** "No. ChartNav does not bill or code. We do
  not generate CPT or ICD-10 codes, we do not suggest billing
  codes, and we do not submit claims. The Ambient and Vitals
  signed-artefact panels show billing-or-coding as `(false)`."
- **Why:** Claim scanners block "automatic billing" /
  "automatic coding" / "billing-aware coding" /
  "coding recommendations" / "claims submission". Fundus V1 has
  no billing or coding field in any response schema.

## 13. "Is OpenAI used?"

- **What to say:** "Not in production. Our production default
  is a deterministic rule-based path with no LLM call. We have a
  fake-data OpenAI adapter behind multiple environment gates —
  it's a controlled evaluation surface for fundus and ambient
  documentation, not a production workflow. Flipping the gates
  toward production fails the runtime safety validator. ChartNav
  is not 'OpenAI-powered.'"
- **Why:** Phase 52B adapter is fake-data only; runtime safety
  validator codes
  `LLM_OPENAI_PRODUCTION`, `FUNDUS_OPENAI_NOT_DEMO`,
  `AMBIENT_OPENAI_NOT_DEMO`, etc. all refuse production / non-demo
  use. Claim scanners block "OpenAI-powered clinical documentation".

## 14. "Is IBM watsonx used?"

- **What to say:** "No. The IBM watsonx adapter is explicitly
  blocked at the provider selector. We ran a fake-data smoke test
  for evaluation; production, real-PHI, and pilot use remain
  unapproved. ChartNav is not 'IBM watsonx-powered.'"
- **Why:** `select_default_provider` raises NotImplementedError on
  `ibm_watsonx`. Runtime safety validator codes
  `LLM_PROVIDER_BLOCKED`. Claim scanners block any
  "IBM watsonx-powered" / "Watson makes ChartNav HIPAA compliant"
  phrasing.

## 15. "Can this work with our EHR?"

- **What to say:** "Yes, via integration adapters. ChartNav
  supports a stub / FHIR / read-through / write-through platform
  mode, governed by `CHARTNAV_PLATFORM_MODE` and
  `CHARTNAV_INTEGRATION_ADAPTER`. Today's production integration is
  read-through; write-through is gated behind explicit pilot
  approval. The runtime safety validator refuses unsupported vendor
  / mode combinations."
- **Why:** Platform-mode infrastructure is present (Phase 26 et
  al.); the workflow doc and product-truth row are explicit about
  what's gated.

## 16. "What is ready now vs gated?"

- **What to say:** "Ready now: provider-reviewed intake (vitals),
  transcript-to-draft (ambient documentation), structured fundus
  charting (clinician findings → diagram), signed-and-locked
  artefacts, metadata-only audit, runtime safety validator, claim
  policy manifest. Gated behind controlled-pilot: real-PHI use,
  production LLM activation, write-through EHR integration. The
  product-truth doc has the full row-by-row status."
- **Why:** Capability index in `docs/build/current-product-truth.md`.

## 17. "What would a pilot require?"

- **What to say:** "A controlled-pilot process: a documented
  scope, a security review, the runtime safety validator passing
  for the pilot environment, an updated release-evidence checklist
  per release, and an explicit decision on which features are in
  scope. Real PHI use, production LLM activation, write-through
  EHR integration, and live device integration are not authorised
  by default and would be addressed per pilot."
- **Why:** Controlled-pilot infrastructure (Phase 18) +
  release-evidence checklist + runtime safety validator + product-
  truth statuses. No buyer-specific promises here — the operator
  refers them to the security / commercial follow-up channels.

## 18. "What data is audited?"

- **What to say:** "Every workflow action — create, update,
  review, sign — writes an audit row. The audit `detail` is
  **metadata-only**: row id, encounter id, patient id, status,
  warning count, action. Raw vitals values, raw transcript text,
  raw fundus drawings, technician notes, and similar clinical
  body fields are never written to the audit log. We have a
  canary regression test per surface to prove that."
- **Why:** Phase 56 audit canary (fundus), Phase 57 audit canary
  (ambient), Phase 60 audit canary (vitals). The `app/audit.py`
  module never logs secrets either.

## 19. "What happens when a provider signs?"

- **What to say:** "Sign requires an explicit attestation
  checkbox — there is no one-click sign. After signing, the
  artefact becomes immutable: PATCH and any sign-twice attempt
  return 409, and the UI removes every edit control from the DOM.
  Each surface stores a signed-by-user id and a signed-at
  timestamp. Corrections start a new artefact on the same
  encounter; there is no in-place edit of a signed artefact today."
- **Why:** Phase 55+ contract; tested per-surface.

## 20. "What is the rollback / disable path?"

- **What to say:** "Each feature has a documented disable path
  in its product-truth row. Examples: unset
  `CHARTNAV_FUNDUS_DRAFTING_ASSIST` to return the fundus path to
  the deterministic default; remove the vitals-workup router
  registration to disable the vitals surface and downgrade the
  Alembic head one step; revert the workspace mount to remove the
  Clinical-tab or Documentation-tab card. The release-evidence
  checklist captures which disable path applies per release."
- **Why:** `docs/build/current-product-truth.md`'s "Rollback /
  disable path" column on every row.

---

## Notes for the operator

- If a buyer presses on a "What if you said X?" hypothetical (e.g.
  "What if you claimed HIPAA?" or "What if you replaced our EHR?"),
  the safe answer is: *"We don't make that claim. Today's posture
  is in the product-truth doc; any change to the posture goes
  through a documented internal review."*
- If a buyer asks for a claim **not** covered above, do not
  improvise. Either:
  1. Map the question to one of the 20 entries above and read that
     answer, or
  2. Capture the question for follow-up and note: *"Let me come back
     to you on that with the right context."*
- The operator never quotes a percentage, never quotes a benchmark
  number, never quotes a customer reference, never quotes a vendor
  partnership status that hasn't been signed.

---

## Related documents

- `docs/demo/phase-61-controlled-buyer-demo-runbook.md` — master operator runbook.
- `docs/demo/phase-61-buyer-demo-checklist.md` — pre/during/post checklist.
- `docs/demo/phase-61-demo-storyboard.md` — operator storyboard.
- `docs/build/current-product-truth.md` — single source of truth.
- `docs/commercial/claims-policy.json` — canonical manifest.
- `docs/security/chartnav-openai-fake-data-adapter.md` — Phase 52B contract.
- `docs/security/chartnav-llm-vendor-evaluation.md` — vendor posture.
- `docs/workflow/structured-vitals-workup.md`, `ambient-documentation-assist.md`, `fundus-charting.md` — feature contracts.
