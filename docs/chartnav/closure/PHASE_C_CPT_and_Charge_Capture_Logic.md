# Phase C — CPT Suggestion and Charge Capture Logic

## 1. Problem solved
Ophthalmology encounters carry unusually high coding density: nearly every
visit blends an E/M decision (92002 / 92004 / 92012 / 92014) with one or
more 92xxx diagnostic procedures (visual field, OCT, fundus photography).
ChartNav today produces a clean, signed note, but a biller or coder still
has to re-read the note to translate structured findings into billable
codes. That re-read is where revenue slips and compliance risk enters:
missed procedures, over-selected E/M levels, and undocumented rationale.

ChartNav's role is not to bill. It is to surface a deterministic,
reviewer-first suggestion tied directly to what the physician already
documented, so the revenue cycle team sees what the chart actually
supports before a claim is ever touched.

## 2. Current state
- Signed notes are produced by the deterministic SOAP extractor
  (`backend/app/services/soap_extractor.py`) with provider-verify flags
  for any field the extractor could not confidently fill.
- The encounter state machine (`encounters` table, `workflow_events`
  table) already records transitions through `draft → ready_for_signature
  → signed`.
- Final physician approval is captured; `workflow_events` records the
  signing user, timestamp, and note version.
- No table exists for code suggestions. No UI surface exists for the
  biller/coder role. There is no CPT, ICD-link, or modifier logic in the
  codebase today.
- There is no X12, no 837, no claim scrubbing, and no payer-specific
  rule engine. The product is a chart, not a clearinghouse.

## 3. Required state
A deterministic CPT suggestion layer that runs at note-sign time and
writes a reviewable suggestion record with full rule provenance. Every
suggestion is explainable in plain English, every accept/reject is a
logged event, and nothing reaches a billing system without explicit
human action.

Mapping scope (v1):
- `92002` new patient intermediate; `92004` new patient comprehensive
- `92012` established intermediate; `92014` established comprehensive
- `92083` visual field (threshold); `92133` OCT optic nerve;
  `92134` OCT retina
- `92250` fundus photography (external imaging test)
- 65xxx surgical codes are explicitly out of scope in v1

Deterministic rule basis:
- New-vs-established is decided by counting prior signed encounters for
  the same patient at the same organization within the last three years.
- Comprehensive vs intermediate is decided by the presence of documented
  dilated exam plus fundus evaluation plus decision-complexity markers
  from the structured findings block.
- Procedure codes (`92083 / 92133 / 92134 / 92250`) fire only when the
  corresponding structured finding block is populated in the signed note
  and the provider-verify flag for that block is cleared.

Every suggestion ships with a rule IDs array and a human-readable
"because" list rendered in the UI.

## 4. Acceptance criteria
- New table `cpt_suggestions` exists with the columns defined in Section 5.
- Endpoint `POST /encounters/{encounter_id}/cpt/suggest` returns a
  deterministic result for a signed note and is idempotent per
  `note_version_id`.
- Endpoint `POST /encounters/{encounter_id}/cpt/{suggestion_id}/accept`
  and `/reject` write a `workflow_events` row with
  `event_type in ('cpt_suggestion_accepted','cpt_suggestion_rejected')`.
- Pytest file `backend/tests/test_cpt_suggester.py` contains at least 12
  fixture-driven cases asserting exact `code` and `rule_ids_json` output.
- Frontend surface uses `data-testid="cpt-suggestion-panel"`,
  `data-testid="cpt-suggestion-row-{code}"`,
  `data-testid="cpt-suggestion-because-list"`,
  `data-testid="cpt-suggestion-accept-btn"`,
  `data-testid="cpt-suggestion-reject-btn"`.
- Only roles `biller_coder` and `clinic_admin` can accept or reject; the
  signing clinician may dispute through a separate "clinician-dispute"
  action which does not mutate acceptance state.
- No suggestion ever auto-accepts. No network call ever leaves the
  deployment boundary from this code path.

## 5. Codex implementation scope
Create:
- `backend/app/models/cpt_suggestion.py`
- `backend/app/services/cpt_suggester/__init__.py`
- `backend/app/services/cpt_suggester/rules.py`
- `backend/app/services/cpt_suggester/engine.py`
- `backend/app/routes/cpt_suggestions.py`
- `backend/alembic/versions/xxxx_cpt_suggestions.py`
- `backend/tests/test_cpt_suggester.py`
- `frontend/src/components/cpt/CptSuggestionPanel.tsx`
- `frontend/src/components/cpt/CptBecauseList.tsx`
- `frontend/src/api/cpt.ts`
- `frontend/tests/cpt.test.tsx`

Modify:
- `backend/app/routes/__init__.py` to register the new router
- `frontend/src/pages/SignedNote.tsx` to mount the panel post-sign
- `backend/app/services/workflow_events.py` to add the two new event types

SQL sketch:

```sql
CREATE TABLE cpt_suggestions (
  id UUID PRIMARY KEY,
  organization_id UUID NOT NULL,
  encounter_id UUID NOT NULL REFERENCES encounters(id),
  note_version_id UUID NOT NULL,
  code TEXT NOT NULL,
  confidence TEXT NOT NULL CHECK (confidence IN ('low','med','high')),
  rule_ids_json JSONB NOT NULL,
  because_text TEXT NOT NULL,
  accepted_by_user_id UUID NULL,
  accepted_at TIMESTAMPTZ NULL,
  rejected_by_user_id UUID NULL,
  rejected_at TIMESTAMPTZ NULL,
  rejected_reason TEXT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (note_version_id, code)
);
CREATE INDEX ON cpt_suggestions (organization_id, encounter_id);
```

## 6. Out of scope / documentation-or-process only
- NCCI edits, LCD/NCD checks, payer-specific rules, modifier logic
  (-25, -59, laterality) are explicitly deferred.
- ICD-10 suggestion is out of scope in v1; ICD codes are already carried
  from the signed note and shown alongside the CPT panel as read-only.
- No direct push to any practice management or clearinghouse system.
- No fee schedule, no RVU lookup, no expected-reimbursement display.

## 7. What can be demoed honestly now vs later
Now, with stub data: the signed-note surface, the extractor, and the
three-tier trust UI. We can walk a buyer through a finished note and
narrate "this is where the suggestion panel will attach."

After Codex ships this scope: live demo of a signed chart producing
`92004` plus `92134` with a visible rule chain, a biller accepting the
suggestion, and a `workflow_events` entry appearing in the audit tab.

Not demoable, and we will not claim: payer acceptance, coding-
certification-grade accuracy, or fee calculation.

## 8. Dependencies
- Phase A signed-note extractor must continue to populate the
  structured findings block used by the comprehensive-vs-intermediate
  rule.
- Prior-encounter lookup depends on the existing `encounters` and
  `patients` tables being scoped by `organization_id`.
- Biller/coder role must exist in RBAC; add if absent in the same PR.

## 9. Truth limitations
ChartNav is not a certified coding engine. The suggestion layer is a
rule-based aid for reviewer attention. We will not market this as
automated coding, AI coding, or claim generation. No payer has
certified these rules, and we will not imply otherwise in any deck,
demo, or written material.

## 10. Risks if incomplete
- Buyers treat ChartNav as "a nicer note" and push back on seat cost
  because no revenue-cycle lift is visible.
- Billers continue re-reading charts; time-to-bill does not improve and
  the ROI story collapses during pilot readouts.
- Competitors with even a crude coding hint gain a talking-point edge
  despite inferior clinical workflow.
