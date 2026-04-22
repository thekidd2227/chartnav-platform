# Phase 54 — Canonical Lifecycle and Record-Evidence Unification

Repo: `thekidd2227/chartnav-platform`
Branch: `chartnav-enterprise-integration-wave1`

## What this pass changed

Before Phase 54, the repo carried two parallel lifecycle "truths" in
active use:

- **Canonical:** `app.services.note_lifecycle` (7 states, strict
  transition table, edge roles, release blockers). Used by /sign,
  /review, /amend, /final-approve.
- **Stale:** `NOTE_TRANSITIONS` / `_assert_note_transition` in
  `routes.py` (5 states, no knowledge of `reviewed` or `amended`).
  Used by PATCH `/note-versions/{id}` and POST `/submit-for-review`.

Alongside that, three additional sites made independent lifecycle
decisions:

- PATCH immutability checked `{signed, exported}` — missed
  `amended`, so a signed amendment row was silently PATCH-able in
  place.
- Export route used an inline `{"signed", "amended"}` set check
  instead of `can_transition(..., "exported")`.
- Artifact builder (`note_artifact.py`) required
  `{signed, exported}` — rejected amendment rows even though they
  are the current record of care. FHIR `docStatus` used the same
  stale set, so amendments were published as `"preliminary"` in
  FHIR and superseded originals as `"final"`. Both were wrong.

This pass eliminates every one of those parallel truths.

## Canonical lifecycle changes

### `apps/api/app/api/routes.py`

- Removed `NOTE_TRANSITIONS: dict[str, set[str]]`. Deleted.
- `NOTE_STATUSES` now aliases `LIFECYCLE_STATES` (no local copy;
  the two are the **same frozenset object**, asserted by test).
- `_assert_note_transition(cur, tgt)` is now a thin adapter that
  calls `can_transition(cur, tgt)` from the canonical service.
  Call sites (PATCH + `/submit-for-review`) are unchanged in shape
  but now enforce the canonical 7-state table, including edges to
  `reviewed` and `amended`.
- PATCH immutability set extended to `{signed, exported, amended}`.
  A signed amendment is the current record of care; direct edits
  of its content are now refused with 409 `note_immutable`.
- Export route replaced its inline `{"signed", "amended"}` set check
  with `_canonical_can_transition(status, "exported")`. Same
  external behaviour (409 `note_not_signed` on bad source); same
  rule table as every other lifecycle action.

### `apps/api/app/services/note_amendments.py`

- Amendment reason validator hardened. Still accepts short real
  reasons ("typo", "fix IOP"); now rejects bare placeholders like
  `"...."`, `"----"`, `"1111"`, `"aaaa"`, `"!!!!"` via an
  `amendment_reason_insufficient` error (>= 4 alphanumeric chars
  AND >= 2 distinct). Keyboard-roll strings ("asdf", "qwerty") are
  explicitly *not* blocked by generic heuristics — that is an
  operator-policy concern, documented honestly.
- `amendment_chain()` SELECT extended to include Wave 7 final
  approval columns on every link so consumers see signing AND
  approval state across the entire chain.

## Record-evidence unification

### `apps/api/app/services/note_artifact.py`

- Single DB SELECT now pulls every lifecycle/evidence column the
  artifact envelope needs (Wave 3 attestation + fingerprint +
  amendment + supersession fields; Wave 7 final approval fields).
- Signed-state gate now includes `amended` so amendment rows can
  produce artifacts. The gate references `LIFECYCLE_STATES` via a
  runtime assertion; any future lifecycle-state rename fails at
  import time rather than silently drifting.
- `signature` block gains `attestation_text` and
  `content_fingerprint_sha256` — the Wave 3 frozen fingerprint was
  not previously exposed in the artifact.
- New `final_approval` block in the envelope: `status`,
  `approved_at`, `approved_by_user_id`, `signature_text`,
  `invalidated_at`, `invalidated_reason`. Downstream systems now
  read this block (not `note.draft_status`) to determine whether a
  record has been physician-approved.
- New `lifecycle` block: `state`, `reviewed_at`,
  `reviewed_by_user_id`, `amended_at`, `amended_by_user_id`,
  `amended_from_note_id`, `amendment_reason`, `superseded_at`,
  `superseded_by_note_id`, `is_current_record_of_care`.
- `render_text()` footer now includes a final-approval line (when
  present) and a record-of-care / supersession line so the
  plain-text artifact is evidentiarily equivalent to the JSON and
  FHIR variants.
- `render_fhir_document_reference()` `docStatus` is now correctly
  computed:
  - `amended` for an amendment row
  - `superseded` for a signed-then-amended original
  - `final` for the live signed record of care
  - `preliminary` for anything else
  Legacy code emitted `final` or `preliminary` only, which
  misrepresented amendment and supersession.

## Supersession / amendment evidence hardening

### `apps/api/app/api/routes.py`

`GET /note-versions/{id}/amendment-chain` response extended:

```json
{
  "note_id": 123,
  "chain": [ /* oldest → newest, each link carries signing +
               final approval state */ ],
  "current_record_of_care_note_id": 456,
  "has_invalidated_approval": true
}
```

`current_record_of_care_note_id` is the one link whose
`superseded_at` is NULL — the live tail of the chain. The UI can
anchor its "current record" indicator on this field directly.

`has_invalidated_approval` is true iff any link carries
`final_approval_status == "invalidated"`; reviewers now have a
one-field signal that the chain contains an invalidated approval
without scanning every link.

## UI / API alignment

`apps/web/src/api.ts`:

- `AmendmentChainResponse` extended with
  `current_record_of_care_note_id: number | null` and
  `has_invalidated_approval: boolean`.

No other client-type or UI changes were required for this pass —
the goal was to make the server's lifecycle and evidence model
consistent; the UI continues to consume the same endpoints with the
same field names, just correctly populated.

## Tests added / hardened

New file: `apps/api/tests/test_canonical_lifecycle_wave_integration.py`
— 15 tests:

- `test_routes_no_longer_defines_note_transitions` — asserts the
  stale dict has been removed from routes.py.
- `test_routes_note_statuses_aliases_canonical` — asserts
  `routes.NOTE_STATUSES is LIFECYCLE_STATES`.
- `test_patch_rejects_edit_on_amended_note`
- `test_patch_submit_for_review_uses_canonical_transition`
- `test_export_draft_returns_canonical_invalid`
- `test_artifact_succeeds_on_amended_note`
- `test_artifact_envelope_carries_final_approval_and_lifecycle_blocks`
- `test_artifact_text_includes_final_approval_line`
- `test_artifact_fhir_docstatus_for_amended_and_superseded`
- `test_artifact_fhir_docstatus_final_for_live_signed`
- `test_amendment_rejects_placeholder_reason`
- `test_amendment_accepts_short_real_reason`
- `test_amendment_chain_exposes_current_record_and_invalidation`
- `test_chain_endpoint_cross_org_returns_404`
- `test_no_stale_transitions_dict_in_routes_source` — source-level
  assertion that any contributor who re-adds a parallel
  transition table at the route layer fails CI.

## Validation performed

- `alembic upgrade head` from empty SQLite: clean, head
  `e1f2a304150a`.
- Backend `pytest -q`: **479 passed / 0 failed** (up from 464 — 15
  new canonical-lifecycle tests added).
- `npm run typecheck`: clean.
- `npm test -- --run` (vitest): **194 passed** / 9 files.
- `npm run build`: clean.
- End-to-end enterprise chain (sign → final-approve → export →
  amend → invalidation → artifact → supersession visibility on
  `/amendment-chain` + `/admin/operations/*`) verified by the
  combined suite.

## What remains for later evidence/audit waves

- **Signed-artifact snapshot.** The artifact is computed on-demand
  from the current `note_versions` row. A true immutable snapshot
  (store the issued artifact bytes + hash on first export) remains
  a separate pass.
- **Hash chain across supersession.** Each row has its own
  `content_fingerprint`; chain-level tamper evidence (linking one
  row's fingerprint to the next) is a reasonable follow-up.
- **Keyboard-roll / filler detection on amendment reasons.** This
  is intentionally out of scope for a generic validator; implement
  as an org-level policy module if/when the operator concern is
  real.
- **Retraction / entered-in-error flow.** FHIR has a distinct
  `docStatus="entered-in-error"` branch; ChartNav does not emit
  this today. Adding it requires a new lifecycle transition and is
  out of scope for this pass.

## No duplicate lifecycle truth remains in active use

Asserted by tests. Grepping the repo under `apps/api/` for
`NOTE_TRANSITIONS` or `draft_status in {.*signed.*exported.*}`
constructs returns only:

- `kpi_scorecard.py` — read-only telemetry count of "open drafts"
  (`'draft','provider_review','revised'`). This is legitimate
  business reporting, not a transition decision.
- `deployment_telemetry.py` — same pattern for deployment readout.

Both are reporting sites, not governance sites. No active
governance / gating / export decision branches on a literal state
set any more; every such decision now goes through
`app.services.note_lifecycle`.
