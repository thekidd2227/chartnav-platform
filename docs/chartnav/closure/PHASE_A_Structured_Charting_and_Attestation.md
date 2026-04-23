# Phase A — Structured Charting and Attestation

## 1. Problem solved

Buyers reviewing ChartNav for a clinical pilot need two guarantees before they will run a single real patient through it: (a) a signed note cannot be silently changed, and (b) every change that did happen is reconstructible. The brief flagged that ChartNav's immutability and attestation story lives partly in `note_versions` and partly in implicit behavior, and is not yet spec-complete at the row level. A medical record platform without an enforced locked-after-sign contract and a readable edit history is not pilotable in an MSO-scale ophthalmology practice.

Clinically, the attestation is the provider stating, under their name, that they performed or reviewed the services described and that the documentation is accurate. It is not a formality — it is what makes the record billable and defensible.

## 2. Current state

- `note_versions` stores versioned note content. The active note is recoverable; prior drafts are retained.
- Encounter state machine enforces `draft → provider_review → revised → signed → exported`. Once `signed`, writes to the note body are refused at the service layer.
- `security_audit_events` records security-relevant actions; `workflow_events` records state transitions.
- Pre-sign checkpoint: modal with an explicit ack checkbox (`data-testid="attest-ack"`), and the provider must type their exact stored name before sign resolves.
- `attestation_text` exists on the encounter and is written at sign time.
- Gaps: immutability is enforced for the note body but not uniformly for other encounter-row fields (e.g. `template_key`, `chief_complaint_struct`, `assessment_struct`, `plan_struct`). There is no first-class `encounter_revisions` table exposing a field-level diff. The reviewer role can read the encounter but has no explicit edit-history view.

## 3. Required state

- **Row-level lock.** After `signed`, PATCH on `encounters` and on all child structured tables is refused with a single typed error.
- **Edit history.** A new `encounter_revisions` table captures every mutation on the encounter row and its structured children, with before/after JSON and actor identity, from encounter creation through sign.
- **Attestation record.** The attestation becomes its own row (`encounter_attestations`) rather than a free-text column, so it is auditable independently of the note body.
- **Reviewer visibility.** Reviewer role can read `encounter_revisions` and `encounter_attestations` for any encounter in their org.

## 4. Acceptance criteria

- `PATCH /encounters/{id}` and `PATCH /encounters/{id}/structured/*` on a signed encounter return HTTP 409 with body `{"error_code": "ENCOUNTER_LOCKED_AFTER_SIGN", "signed_at": "..."}`.
- Every transition (`draft → provider_review → revised → signed → exported`) writes a row to `workflow_events` and, if data changed, to `encounter_revisions`.
- `GET /encounters/{id}/revisions` returns the full revision list, newest first, visible to roles `admin`, `clinician` (author or same-org), and `reviewer` (same-org). Forbidden for `front_desk` and `technician`.
- Signed attestation row contains: `attested_by_user_id`, `typed_name`, `attested_at`, `attestation_text`, `encounter_snapshot_hash`. Re-sign attempts refused.
- Pytest: `apps/api/tests/test_encounter_immutability.py`, `apps/api/tests/test_encounter_revisions.py`, `apps/api/tests/test_attestation_record.py`.
- UI: revision history panel on the encounter page — `data-testid="encounter-revisions-panel"` — gated by role.

## 5. Codex implementation scope

New tables:

```sql
CREATE TABLE encounter_revisions (
  id             INTEGER PRIMARY KEY,
  encounter_id   INTEGER NOT NULL REFERENCES encounters(id),
  actor_user_id  INTEGER NOT NULL REFERENCES users(id),
  field_path     TEXT NOT NULL,          -- e.g. "assessment_struct.plan"
  before_json    TEXT,                   -- JSON snapshot of the value
  after_json     TEXT,
  changed_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  reason         TEXT                    -- optional free-text (e.g. "reviewer correction")
);

CREATE TABLE encounter_attestations (
  id                        INTEGER PRIMARY KEY,
  encounter_id              INTEGER NOT NULL UNIQUE REFERENCES encounters(id),
  attested_by_user_id       INTEGER NOT NULL REFERENCES users(id),
  typed_name                TEXT NOT NULL,
  attestation_text          TEXT NOT NULL,
  encounter_snapshot_hash   TEXT NOT NULL,   -- sha256 of canonicalized encounter JSON
  attested_at               TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

Modify:

- `apps/api/app/services/encounter_service.py` — central guard `_assert_not_signed(encounter)` called from every mutating entry point; wrap structured-field writers in a revision emitter.
- `apps/api/app/api/routes.py` — new `GET /encounters/{id}/revisions`, update `POST /encounters/{id}:sign` to write the attestation row and compute `encounter_snapshot_hash`.
- `apps/api/app/core/audit.py` — helper `record_revision(encounter_id, actor, field_path, before, after)`.
- Frontend: `apps/web/src/features/encounter/RevisionsPanel.tsx` and a reviewer-visible route.

## 6. Out of scope / documentation-or-process only

- Long-term records retention schedule, deletion rules, and legal-hold policy — belong in `docs/chartnav/policy/records_retention.md`, not in Phase A code.
- E-signature legal sufficiency opinion (ESIGN, UETA) — captured in a signed counsel memo, not implemented in code beyond typed-name + hash.
- Co-signing workflow for residents / fellows — parked to Phase B.

## 7. Demo honestly now vs. later

**Now:** sign an encounter, show that PATCH is refused, open the revisions panel and walk through every pre-sign edit, show the attestation row with the snapshot hash and typed name.

**Later:** multi-party co-sign, amendments after sign via an addendum workflow (separate row, clearly labeled), cryptographic timestamping via an external time-stamp authority.

## 8. Dependencies

- Phase A RBAC spec (reviewer role must be able to read revisions; technician must not).
- Phase A Encounter Templates (structured fields whose edits need tracking).
- Evidence chain / HMAC signing code already in tree is used to compute `encounter_snapshot_hash` deterministically.

## 9. Truth limitations

- Immutability is enforced at the application layer, not at the database layer. A direct DB write bypasses it. This is standard for SQLite-backed pilots; production Postgres deployments should add row-level security or a deny-by-default trigger — tracked separately.
- `encounter_snapshot_hash` is a tamper-evidence signal, not a legal trusted timestamp. We do not (yet) anchor it to an external TSA.
- Edit history is ChartNav-internal. It does not retroactively apply to edits made in an external EHR in `integrated_readthrough` mode.

## 10. Risks if incomplete

- A pilot clinic signs a note, then someone (tech, clinician, admin) edits a structured field. Without row-level lock, the change is silent. A single audit finding here ends a pilot and any reference-ability in the market.
- Reviewers cannot tell what changed between provider review and sign. The QA loop stops functioning.
- The attestation becomes ambiguous — if the text is free-form on the encounter row and can be rewritten, its legal weight collapses.
