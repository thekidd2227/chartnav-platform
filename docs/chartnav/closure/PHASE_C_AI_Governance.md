# Phase C — AI Governance Policy

## 1. Problem solved
Every buyer conversation in 2026 ends on the same question: "How does
your AI work, and is it safe?" The honest answer is the one that wins
this segment. ChartNav is not a generative product today; pretending
otherwise is both untrue and, in healthcare procurement, immediately
disqualifying. A written governance policy, shipped with the product,
converts a perceived vulnerability into a procurement advantage.

## 2. Current state
- ChartNav's note generator is a deterministic regex-based SOAP
  extractor in `backend/app/services/soap_extractor.py`. It does not
  call an LLM and does not invent values.
- An LLM seam exists at `backend/app/services/llm_client.py` but is not
  wired into any production code path. No prompts, no completions, no
  outbound model traffic in shipped builds.
- Missing or low-confidence fields become provider-verify flags. The
  pre-sign checkpoint refuses `sign` transitions while flags are
  unacknowledged.
- The STT layer is currently a stub emitting `[stub-transcript]` and is
  labeled as such in the UI. This is a truth-preserving placeholder,
  not a claim of voice capability.
- Standalone mode performs no outbound traffic to third-party model
  providers by design.

## 3. Required state
A published, buyer-safe AI governance policy that covers how ChartNav
treats AI today and, when the LLM seam is activated, the non-negotiable
guardrails the product will enforce. The policy is shipped in-repo, is
linked from the pricing page and the security posture doc, and maps to
concrete code locations.

Policy must state plainly:
- The current extractor is deterministic and cannot invent values.
- Any future LLM use is opt-in per deployment and per encounter.
- Human review before physician sign is non-negotiable and technically
  enforced by the encounter state machine, not by policy alone.
- In standalone mode, no patient data leaves the customer's deployment.
- In integrated modes, egress is limited to the configured FHIR
  endpoint and, if activated, the explicitly selected LLM vendor.

## 4. Acceptance criteria
- `docs/chartnav/policy/ai-governance.md` exists as the canonical
  policy, with the ten required sections in Section 5 below.
- `docs/chartnav/policy/ai-governance-buyer-safe.md` exists as the
  short, publishable version suitable for the marketing site and RFP
  responses.
- Pricing page renders a link to the buyer-safe version.
- A pytest integration test asserts the pre-sign checkpoint refuses to
  transition an encounter with open provider-verify flags:
  `backend/tests/test_pre_sign_checkpoint.py::test_refuses_sign_with_open_flags`.
- A release-compliance checklist item confirms "AI governance version
  tag matches product version tag" and blocks release if mismatched.

## 5. Codex implementation scope
Create:
- `docs/chartnav/policy/ai-governance.md` (full internal + buyer policy)
- `docs/chartnav/policy/ai-governance-buyer-safe.md` (short version)
- `docs/chartnav/policy/ai-incident-response.md`
- `docs/chartnav/policy/model-versioning.md`
- `backend/app/config/ai_governance.py` — reads a single
  `AI_MODE` env var with allowed values `off`, `local_deterministic`,
  `vendor_llm` and surfaces it in the `/health` and `/about` endpoints
- Modify `frontend/src/components/SystemBanner.tsx` to render the
  current `AI_MODE` when not `off`

Required policy sections (both versions):
1. Scope and definitions
2. What AI does and does not do in ChartNav today
3. Data handling and data residency
4. Safety gates and human-in-the-loop
5. Vendor management criteria for future LLM selection
6. Incident response for AI-caused harm or drift
7. Model versioning and change control
8. Audit log retention for AI-touched encounters
9. Patient and clinician transparency
10. Policy review cadence and ownership

## 6. Out of scope / documentation-or-process only
- Third-party AI safety certification. We will not apply for or claim
  any such certification in v1.
- Formal model-risk-management framework (e.g. NIST AI RMF mapping).
  This is a Phase D consideration.
- Red-team reports against an LLM that is not wired.

## 7. What can be demoed honestly now vs later
Now: the deterministic extractor, the provider-verify flags, the
pre-sign checkpoint, the in-UI "deterministic extractor" label, and
the governance document itself. The demo script should say the words
"we do not use an LLM in this build" and point at the banner.

Later, when the LLM seam is activated: per-encounter opt-in UI, prompt
and response logging surface, vendor identity shown to the clinician
before generation, and an explicit "regenerate without LLM" fallback.

## 8. Dependencies
- `backend/app/services/llm_client.py` remains inert until governance
  version 1.1 ships.
- `system_banner` component must read `AI_MODE` at runtime, not build
  time, so a deployment can flip modes without a frontend rebuild.

## 9. Truth limitations
- No independent third-party has audited ChartNav's AI posture. This
  policy is self-published.
- Governance is only as strong as the deployment operator's adherence.
  In standalone mode, the operator controls the environment; we cannot
  attest to their internal controls.
- "Deterministic" means rule-based and reproducible; it does not mean
  infallible. Extractor bugs can and will occur and will be handled
  through the normal defect process.

## 10. Risks if incomplete
- Procurement teams conflate ChartNav with generative clinical tools
  and apply a stricter-than-necessary review, slowing every deal.
- Clinicians distrust the extractor because they cannot tell what it is
  doing, eroding adoption during pilot.
- A future LLM activation, absent this policy, would be treated as a
  material product change and reset the procurement clock.

## Appendix — buyer-safe wording block

The following wording is approved for the website, sales decks, and
RFP responses verbatim:

"ChartNav generates its clinical note draft using a deterministic,
rule-based extractor. The extractor cannot invent clinical values; any
field it cannot confidently populate becomes an explicit provider-
verify flag that the physician must acknowledge before signing. No
large language model is wired into shipped ChartNav builds today. If
your deployment later activates an LLM option, every encounter is
reviewed and signed by a licensed clinician, every model interaction
is logged, and no patient data leaves your deployment without your
explicit configuration."
