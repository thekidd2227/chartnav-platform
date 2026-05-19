# Phase 54 Fundus/OpenAI Safety Audit

> Scope: docs/test audit only. No product code was changed. No real PHI
> was processed. No public marketing claims were added.
>
> Starting point: current `main` after:
> - `5dbd313` Phase 52B OpenAI fake-data adapter
> - `a01b592` AI-assisted fundus charting V1

## 1. Current Merged Feature Summary

Two adjacent but separate features are now merged:

1. **AI-assisted fundus charting V1**
   - Adds encounter-scoped fundus chart endpoints.
   - Uses `rule_based_v1`, a deterministic parser over clinician-entered findings text.
   - Produces structured `drawing_json`, warnings, and rendered SVG diagrams.
   - Preserves a draft -> reviewed -> signed lifecycle.
   - Signed charts are immutable in place.
   - Requests are organization-scoped and role-gated.

2. **Phase 52B OpenAI fake-data adapter**
   - Adds an OpenAI chat provider behind explicit fake-data guardrails.
   - Keeps `DeterministicStubProvider` as the default selector.
   - Refuses real-PHI mode and refuses `CHARTNAV_PILOT_ALLOW_LLM_OPENAI=1`.
   - Requires `LLMRequest.fake_data_context=True` and
     `LLMRequest.requires_provider_review=True`.
   - Implements only `draft_provider_review_note`; other provider methods remain
     unimplemented for this phase.

Production posture: no production LLM should be enabled. The OpenAI adapter is
fake-data/demo-only and must not be promoted by environment flag flips.

## 2. Fundus Charting Safety Posture

Current posture is acceptable for a deterministic, provider-reviewed charting aid:

- Input is clinician-entered findings text, not raw images.
- V1 parser is deterministic and does not require an external model or API.
- Generated output is a draft chart artifact, not a signed clinical conclusion.
- Warnings surface missing laterality, missing clock hour, or unrecognized findings.
- Review and sign endpoints preserve human attestation.
- Signed charts are blocked from in-place mutation.
- Cross-organization access is tested as a 404 path.

Required boundary: fundus charting must not become autonomous diagnosis or image
interpretation. It must not interpret fundus photos, grade disease, recommend
treatment, or infer findings from an image. The chart should remain a structured
rendering of clinician-entered findings until a separately approved clinical,
legal, security, and validation phase says otherwise.

## 3. OpenAI Fake-Data Adapter Safety Posture

Current posture is conservative:

- Default provider remains deterministic.
- OpenAI is not the production note workflow.
- Real-PHI mode is refused by design.
- Pilot/production allow semantics are intentionally inverted for this fake-data
  adapter: `CHARTNAV_PILOT_ALLOW_LLM_OPENAI=1` blocks activation.
- API keys are presence-checked and tested not to leak through failure logs.
- Tests use mocked transports, so CI should not call a live vendor.
- Prompt content is wrapped in data blocks to reduce prompt-injection risk.
- Output contract requires provider review and forbids diagnosis, orders, patient
  messages, billing, and coding.

The adapter is acceptable only as a fake-data evaluation surface. It is not a
production LLM path and must not be treated as a PHI go-live shortcut.

## 4. Overlap/Risk Between Both Features

Primary overlap risk is interpretation by operators, buyers, or future developers:

- The fundus feature says "AI-assisted" and "generate chart"; the OpenAI docs say
  OpenAI conditionally passed fake-data evaluation. Together, this can be
  misread as "OpenAI generates or interprets fundus charts."
- The fundus workflow doc mentions a future LLM-backed model, but does not
  explicitly tie that future work to the real-PHI, provider-review, and no-image-
  interpretation gates.
- Both features touch ophthalmology workflows. Without stronger docs, a future PR
  could accidentally route fundus findings through the generic LLM provider seam.
- Buyer-facing claim risk increases if "AI-assisted fundus charting" is shortened
  into "AI fundus interpretation" or "AI diagnosis."

Risk rating: moderate documentation/positioning risk, low immediate production
runtime risk based on current tests and default selector behavior.

## 5. Missing Tests

Recommended gaps to close:

- Add a fundus regression test proving chart generation does not instantiate or
  select an LLM provider.
- Add unsafe-language fixtures for fundus findings text, such as "diagnose retinal
  detachment" or prompt-injection-like strings, and assert the parser treats them
  as text rather than instructions.
- Add audit-log regression coverage that findings text and `drawing_json` do not
  land in security audit event payloads.
- Add role coverage for reviewer/read-only behavior if the product contract
  intends reviewers to be unable to create, review, or sign fundus charts.
- Add malformed/unsupported `drawing_json` renderer tests so bad shapes fail
  predictably instead of producing misleading SVG.
- Extend committed eval tests for the F3 missing-VA/IOP false-positive cleanup
  described in the Option A results.
- Add a docs/claims regression that scanner phrase lists include fundus-specific
  overclaims, not only generic OCT/LLM overclaims.

No backend product tests were added in this audit branch.

## 6. Missing Docs

Recommended doc gaps:

- Update `docs/workflow/fundus-charting.md` to explicitly say the feature does
  not diagnose, interpret images, grade disease, recommend treatment, or read
  fundus photos.
- Add a short cross-link from fundus charting docs to the LLM provider decision
  docs stating that V1 fundus charting is not OpenAI-backed.
- Add an operator warning that "future LLM-backed model" is not approval to route
  real PHI or fundus charting through a live vendor.
- Add a correction/rejection workflow note for generated fundus charts before
  review/sign.
- Add public-safe wording for fundus charting, for example: "provider-reviewed
  retinal diagram drafting from clinician-entered findings."

## 7. Claim-Risk Scan Findings

Existing scanners already blocked broad high-risk claims:

- HIPAA-compliant / HIPAA-certified / SOC 2 certified.
- OpenAI-powered, GPT-powered, Claude-powered, or LLM-powered clinical
  documentation.
- LLM-powered diagnosis, AI diagnosis, autonomous documentation, autonomous
  clinical reasoning.
- OCT auto-interpretation and autonomous imaging interpretation.

Gap found: fundus-specific overclaims were not named directly. This branch adds
scanner phrases for:

- fundus image interpretation
- fundus photo interpretation
- retinal image interpretation
- AI interprets fundus
- autonomous fundus interpretation
- fundus diagnosis
- AI-generated fundus diagnosis

Residual risk: the claim scanners mainly cover public/deck/demo surfaces, not
all internal docs. That is acceptable for catalog/security docs, but public copy
should keep using the scanner-backed surfaces as the source of truth.

## 8. Recommended Follow-Up Tests

1. **No-LLM fundus generation test**
   - Patch or monkeypatch the LLM selector to fail if called during fundus chart
     generation.
   - Assert fundus charting remains deterministic.

2. **Fundus unsafe-text fixture tests**
   - Inputs: autonomous diagnosis requests, billing/code requests, image-
     interpretation requests, and prompt-injection strings.
   - Expected result: warnings or no recognized chart elements, never diagnosis
     or treatment output.

3. **Audit minimization test**
   - Generate a fundus chart with a recognizable fake finding.
   - Assert security audit event metadata includes only allowed metadata such as
     chart id, laterality, and warning count.

4. **Claim scanner fixture test**
   - Add a small test fixture with positive fundus overclaims and negative
     allowed phrasing so the scanner behavior is pinned.

## 9. Recommended Follow-Up Docs

1. Update the fundus workflow doc with explicit non-goals.
2. Add an LLM/fundus separation note to the OpenAI fake-data adapter doc.
3. Add approved fundus copy to the commercial claims language doc.
4. Add an operator runbook entry: "Do not connect fundus charting to a production
   LLM; do not process real PHI through fake-data adapters."

## 10. Production LLM Statement

No production LLM should be enabled. The merged OpenAI adapter is fake-data/demo
only, guarded by environment and per-request checks, and must not be used with
real PHI. A production LLM path would require a separate implementation, BAA and
vendor review, security/legal approval, eval coverage, audit updates, operator
runbooks, and explicit practice approval.

## 11. Fundus Autonomy Statement

Fundus charting must not become autonomous diagnosis or image interpretation.
It may assist with provider-reviewed diagram drafting from clinician-entered
findings. It must not interpret fundus photographs, infer disease from images,
grade severity, recommend treatment, create orders, code, bill, message patients,
or bypass clinician review and attestation.

## 12. PR Overlap Assessment

This audit branch should not overlap Claude's implementation PR at the product
code level. It does not edit:

- `apps/api/app/services/fundus_chart_ai.py`
- `apps/api/app/services/llm_provider.py`
- `apps/api/app/api/fundus_charts.py`
- frontend product components

Overlap is limited to documentation and claim-scanner guardrails.
