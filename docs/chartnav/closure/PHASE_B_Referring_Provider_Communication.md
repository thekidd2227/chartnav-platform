# Phase B — Referring Provider Communication

## 1. Problem solved
Ophthalmology is a consultative specialty. A meaningful share of visits are consults initiated by a referring optometrist, primary care physician, or another ophthalmologist. Current workflows assume the consulting clinician produces a structured letter back to the referring provider summarizing findings, assessment, and plan. ChartNav today has no letter generator: post-sign, the note exists as an internal artifact only. Practices fall back to dictation, ad-hoc Word templates, or their EHR's letter module — friction that partially negates the documentation gains ChartNav produces upstream.

This spec adds a first-class referral letter surface so a signed note can be rendered into an operator-branded communication, attached to the encounter's evidence chain, and delivered to the referring provider via download, email (opt-in SMTP), or a fax stub interface.

## 2. Current state (honest)
- No `referring_providers` or `consult_letters` tables exist. `grep -r "referring" app/` in `chartnav-platform/` returns no matches in models, routes, or UI.
- The encounter state machine terminates at `signed` with immutability enforced in `app/services/encounters/state.py`; no downstream artifact generation hooks.
- `note_versions` table carries the signed SOAP payload; there is no renderer beyond the in-app Note Workspace.
- FHIR read-through adapter (`app/services/fhir/readthrough.py`) pulls Patient and Encounter resources for integrated modes; it does not post `DocumentReference`.
- PDF generation is not currently present in `requirements.txt`; `weasyprint` or `reportlab` must be introduced.

## 3. Required state
- Operators can register referring providers (name, practice, NPI-10, phone, fax, email) scoped to their organization.
- From any signed `note_version`, a clinician can render a consult letter bound to a single referring provider.
- Output formats in Phase B: PDF (required), secure download link (required), FHIR `DocumentReference` POST (required only in `integrated_writethrough`; skipped with a recorded reason in other modes).
- Delivery channels: `download` (always), `email` (only if operator has configured SMTP and the referring provider record has a validated email), `fax_stub` (records intent; no bytes transmitted in Phase B).
- Letter is immutable once `sent_at` is set. Re-rendering against the same `note_version_id` + `referring_provider_id` returns the existing artifact.

## 4. Acceptance criteria (testable)
- `backend/tests/test_consult_letters.py` covers: happy-path generation, org scoping (cross-org 404), signed-note precondition (422 on unsigned encounters), idempotent re-render, and post-send immutability (409 on mutation attempt).
- `backend/tests/test_referring_providers_api.py` covers CRUD + NPI-10 validation (digits, Luhn check) + uniqueness per org.
- Playwright spec `e2e/consult_letter.spec.ts` walks: sign note → open ConsultLetterPanel (`data-testid="consult-letter-panel"`) → pick provider (`data-testid="referring-provider-picker"`) → generate → download PDF. Axe-AA must pass on the panel.
- API contract:
  - `GET /referring-providers` → `200 {items: ReferringProvider[]}`
  - `POST /referring-providers` → `201 ReferringProvider`
  - `POST /note-versions/{id}/consult-letter` body `{referring_provider_id, delivery_channel}` → `201 ConsultLetter`
  - `GET /consult-letters/{id}/pdf` → `200 application/pdf`

## 5. Codex implementation scope
Create:
- `backend/app/models/referring_provider.py`, `backend/app/models/consult_letter.py`
- Alembic migration `backend/alembic/versions/xxxx_phase_b_consult_letters.py` adding both tables.
- `backend/app/services/letters/renderer.py` — Jinja2 + WeasyPrint; template at `backend/app/services/letters/templates/consult_letter.html.j2`.
- `backend/app/services/letters/delivery.py` — unified dispatcher (`download`, `email`, `fax_stub`).
- `backend/app/routers/referring_providers.py`, `backend/app/routers/consult_letters.py`; register in `backend/app/main.py`.
- Frontend: `frontend/src/components/notes/ConsultLetterPanel.tsx`, `frontend/src/components/notes/ReferringProviderPicker.tsx`. Mount into `NoteWorkspace.tsx` in the post-sign slot.
- Admin surface: `frontend/src/routes/admin/ReferringProvidersAdmin.tsx`.

Modify:
- `backend/requirements.txt` — add `weasyprint`, `jinja2` (if not present).
- `backend/app/services/fhir/writethrough.py` — add `post_document_reference(consult_letter)` path; only called when mode is `integrated_writethrough`.
- `backend/app/services/evidence/chain.py` — append `consult_letter_rendered` and `consult_letter_delivered` events.

SQL sketch:
```sql
CREATE TABLE referring_providers (
  id UUID PRIMARY KEY, organization_id UUID NOT NULL,
  name TEXT NOT NULL, practice TEXT, npi_10 CHAR(10) NOT NULL,
  phone TEXT, fax TEXT, email TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(organization_id, npi_10)
);
CREATE TABLE consult_letters (
  id UUID PRIMARY KEY, encounter_id UUID NOT NULL,
  note_version_id UUID NOT NULL, referring_provider_id UUID NOT NULL,
  rendered_pdf_storage_ref TEXT NOT NULL,
  delivery_status TEXT NOT NULL,
  delivered_via TEXT NOT NULL CHECK (delivered_via IN ('download','email','fax_stub')),
  sent_at TIMESTAMPTZ, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

## 6. Out of scope / process only
- Real fax transmission (no vendor integration — sFax/Documo/Phaxio are Phase C).
- Letter content personalization beyond the four variable slots in the template.
- Multi-recipient cc to additional providers on a single letter.
- Digital signature embedding in the PDF (relies on the displayed clinician signature block only).

## 7. Demoable now vs later
- Demoable on ship: generate and download a branded PDF from a signed note; attach to evidence chain; view in Admin.
- Demoable only with email opt-in configured: outbound email delivery with delivery status transitions.
- Not demoable: real fax delivery, inbound referral acceptance, bi-directional referral threading.

## 8. Dependencies
- Phase A ophthalmology templates must be signed-off (letter content leans on the Plan/Assessment structure they produce).
- Operator-level SMTP config surface (small admin addition; tracked under Admin Dashboard spec).
- Storage abstraction (`backend/app/services/storage/`) must support PDF blobs with content-addressed keys.

## 9. Truth limitations
- The fax channel is a stub. No transmission occurs; the UI must label this as "Fax queued (stub — no transmission in pilot)."
- Email delivery depends on operator SMTP; we do not operate a shared outbound relay.
- `DocumentReference` write-back is only exercised against partner FHIR endpoints in `integrated_writethrough`; in read-through and standalone modes, the FHIR write is explicitly skipped and logged.
- The letter is not a billable encounter document; it does not replace the signed note in the EHR of record.

## 10. Risks if incomplete
- Without a generator, ChartNav remains an internal-only tool for consult-heavy practices, which is a direct pilot-acceptance blocker for at least two of the three target pilots.
- Manual workarounds (re-typing into external letter tools) erode the documentation-time savings that underwrite ChartNav's ROI claim.
- Delayed referring-provider communication is a known medico-legal exposure point; absence here is a red flag in clinical advisory reviews.
