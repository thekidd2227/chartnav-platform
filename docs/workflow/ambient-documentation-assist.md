# Provider-Reviewed Ambient Documentation Assist

> **Fake / demo only.** ChartNav is **not** an autonomous documentation
> product. The workflow described here drafts a structured note from a
> fake encounter transcript; the provider must review and sign before
> the draft becomes final. No real PHI flows through this path.
> ChartNav is not HIPAA compliant. ChartNav is not "OpenAI-powered".

## What this is

A narrow Phase 57 workflow that:

1. takes a **fake / demo encounter transcript** the operator pastes
   (or that the existing audio-consent surface produced for the demo),
2. produces a structured provider-review draft note with
   chief complaint, HPI summary, exam facts, assessment context,
   plan-as-stated, safety flags, and a missing-information list,
3. routes the draft through the existing `scribe_sessions` lifecycle
   state machine: `draft → ready_for_review → reviewed → finalized`,
4. requires explicit provider attestation before signing,
5. locks the row at `finalized` — signed drafts are immutable.

The deterministic rule-based path is the production default. An
optional Phase 52B OpenAI fake-data assist exists behind explicit
opt-in env gates (see § "Optional OpenAI fake-data assist" below).

## What this is NOT

- ❌ Autonomous documentation. The provider must review every draft.
- ❌ Hands-free scribing. The operator pastes / loads the transcript.
- ❌ Production LLM. The default is deterministic; the OpenAI seam is
  fake-data only.
- ❌ Real PHI. The API refuses requests with `fake_data_context=false`.
- ❌ Diagnosis. `forbidden_actions.diagnosis` is always `false`.
- ❌ Orders. `forbidden_actions.orders` is always `false`.
- ❌ Referrals. `forbidden_actions.referrals` is always `false`.
- ❌ Patient messages. `forbidden_actions.patient_message` is always `false`.
- ❌ Billing or coding. `forbidden_actions.billing_or_coding` is always `false`.
- ❌ Auto-sign. `forbidden_actions.auto_sign` is always `false`.
- ❌ Image interpretation. `forbidden_actions.image_interpretation` is always `false`.
- ❌ EHR replacement. ChartNav does not replace the patient's EHR of record.
- ❌ "OpenAI-powered". No public material may describe ChartNav this way.

## Where the feature lives in the UI

`ClinicalTabbedWorkspace` → **Documentation tab** → **"Provider-Reviewed
Ambient Documentation Assist"** wide card (below the existing
Transcript → Extracted Facts → AI Draft → Final Note stepper and the
`NoteWorkspace` container).

The card data-testid is `ctw-card-ambient-documentation` and the panel
itself is `ambient-documentation-panel`.

## API contract

| Method | Path | Purpose |
|---|---|---|
| GET | `/patients/{patient_id}/scribe-sessions` | list sessions (existing Phase 8 route) |
| POST | `/patients/{patient_id}/scribe-sessions` | create a session (existing) |
| **POST** | **`/patients/{patient_id}/scribe-sessions/{session_id}/draft-ambient`** | **Phase 57** — run ambient generation against the session's transcript; advance to `ready_for_review`. Body: `{"fake_data_context": true}` |
| POST | `/patients/{patient_id}/scribe-sessions/{session_id}/review` | mark reviewed (existing) |
| POST | `/patients/{patient_id}/scribe-sessions/{session_id}/finalize` | sign (existing); finalized sessions are immutable |

Refusals:

- 422 `fake_data_context_required` — the route refuses if
  `fake_data_context=false`. This is a real-PHI promotion-path guard.
- 403 `role_forbidden` — only `admin` and `clinician` can write. Reviewer / front_desk / technician are read-only or blocked.
- 404 `patient_not_found` — cross-org access returns 404, never 403.
- 409 `invalid_scribe_transition` — `draft-ambient` requires the session
  to be in `draft` status. Sessions already past `draft` cannot be
  re-drafted.
- 409 `scribe_session_immutable` — sessions in terminal states
  (`finalized`, `discarded`) cannot be modified.

## Deterministic extractor

`apps/api/app/services/ambient_documentation.py` exposes
`generate_draft(transcript_text)` as the public seam. The deterministic
path returns:

```json
{
  "structured_facts": {
    "chief_complaint": "<string>",
    "hpi_summary": "<string — paraphrase only, no fabrication>",
    "visual_acuity": "<string preserving 20/xx OD|OS|OU exactly>",
    "iop": "<string preserving numeric values exactly>",
    "imaging_metadata": "<string; '<none mentioned>' if absent>",
    "assessment_context": "<string — facts only>",
    "plan_as_stated": "<string — what the clinician explicitly said>"
  },
  "draft_note": "<string starting with 'DRAFT — provider review required.'>",
  "safety_flags": ["<strings; empty if none>"],
  "missing_information": ["<strings; empty if none>"],
  "requires_provider_review": true,
  "forbidden_actions": {
    "diagnosis": false,
    "orders": false,
    "referrals": false,
    "patient_message": false,
    "billing_or_coding": false,
    "auto_sign": false,
    "image_interpretation": false
  },
  "ai_model_name": "ambient_rule_based_v1"
}
```

The deterministic path never invents missing values — it surfaces them
via the `missing_information` list with the literal placeholder
`<missing - provider to verify>` in the structured facts.

## Optional OpenAI fake-data assist (opt-in)

Set every one of the following to dispatch to the Phase 52B OpenAI
fake-data adapter instead of the deterministic path:

| Env var | Required value |
|---|---|
| `CHARTNAV_AMBIENT_DOCUMENTATION_ASSIST` | exactly `openai` |
| `CHARTNAV_LLM_PROVIDER` | `openai` |
| `CHARTNAV_LLM_ENABLED` | `1` |
| `CHARTNAV_LLM_REAL_PHI_APPROVED` | unset or `0` |
| `CHARTNAV_PILOT_ALLOW_LLM_OPENAI` | unset or `0` |
| `CHARTNAV_OPENAI_API_KEY` | present (never logged) |

If any gate fails under opt-in, the service raises
`ProviderDisabledError` (HTTP 500 propagated through the route). There
is no silent fallback. Anthropic and IBM watsonx remain unwired in the
ambient documentation path.

The OpenAI path emits the same response schema; the service pins
`requires_provider_review=True` and `forbidden_actions` server-side —
the model is **not trusted** to set these.

## Audit minimisation

The route uses the existing `_audit` helper in
`apps/api/app/api/scribe_sessions.py`. The audit `detail` field is
**metadata-only**: `session_id`, `patient_id`, `encounter_id`, `status`,
`linked_artifact_id`. Raw `transcript_text`, `draft_note_text`,
`structured_note_json`, and `review_notes` are **never** written to the
audit log. Phase 57's test
`test_audit_detail_excludes_transcript_text_and_draft_body` pins this
with a canary transcript.

## Correction / versioning

Finalized sessions are immutable. To correct a signed draft, the
operator must create a **new** scribe session with the corrected
transcript and run `draft-ambient` again. There is no in-place edit
path and no fork-and-supersede endpoint in V1. Demo narration must not
imply signed drafts can be amended in place.

## Approved phrases

- "Provider-Reviewed Ambient Documentation Assist"
- "Encounter Transcript to Provider-Review Draft"
- "Clinician-Reviewed Note Drafting"
- "Draft from fake/demo encounter transcript"
- "Provider review required at every step"
- "Does not diagnose / order / refer / message / bill / code"
- "Not for real PHI"

## Forbidden phrases

The three claim scanners (`scripts/check_{commercial,website,demo}_claims.sh`)
block:

- "hands-free scribing"
- "automatic charting"
- "chart fills itself"
- "note writes itself"
- "autonomous documentation"
- "ambient scribe parity"
- "AI writes the note"
- "OpenAI-powered clinical documentation"
- "production LLM documentation"
- "real PHI ready"
- "HIPAA compliant"
- "EHR replacement"
- "automatic orders / referrals / patient messaging / billing / coding"

Saying any of these on a customer call or in source files is the only
way they reach the customer.

## Related documents

- `docs/security/chartnav-openai-fake-data-adapter.md` — Phase 52B
  adapter contract (the gate this feature opts into).
- `docs/build/phase-57-ambient-documentation-feature-audit.md` — the
  pre-implementation audit that justified reusing `scribe_sessions`.
- `docs/demo/phase-57-ambient-documentation-demo-runbook.md` — the
  operator runbook for live demos.
- `docs/workflow/fundus-charting.md` — sibling provider-reviewed
  feature with the same safety posture.
