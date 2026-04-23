# Phase B — Digital Intake

## 1. Problem solved
Today, the front desk types patient demographics, chief complaint, current medications, allergies, and history-of-present-illness into the Create Encounter modal while the patient waits. This introduces three recurring problems: transcription errors in med/allergy lists, bottlenecks at arrival, and rework when the patient corrects information during the encounter. Practices expect a pre-visit intake surface that the patient fills out on their own device before the appointment, so the front desk reviews rather than authors.

This spec adds a lightweight, token-based, unauthenticated intake surface and a staff review flow that promotes accepted intakes into a draft patient + pending encounter record.

## 2. Current state (honest)
- The only patient-facing surface today is the read-only post-visit summary (specced separately in this Phase B batch). There is no intake form and no unauthenticated route in `frontend/src/router.tsx`.
- Patient creation happens inside `frontend/src/components/encounters/CreateEncounterModal.tsx`, which calls `POST /encounters` with inline patient fields.
- There is no rate limiter, no token model, and no SMS/email outbound path in the codebase. `grep -r "rate_limit" backend/app/` returns nothing in the middleware layer.
- `workflow_events` logs encounter creation but has no concept of an intake origin.

## 3. Required state
- Staff (admin or front_desk) issues an intake token; copies the resulting unauthenticated URL and shares it out-of-band (text, email, patient portal link in their existing scheduling tool).
- Patient opens `/intake/{token}`, completes the form in one submit, sees a confirmation screen.
- On submit, an `intake_submissions` row is persisted with `status = pending_review`.
- Staff sees pending submissions in an admin queue; accepting creates (or reuses) a patient identifier candidate and pre-fills a new draft encounter; rejecting marks the submission and optionally writes a reason.
- Tokens are single-use: a successful submit sets `used_at`; subsequent GETs of the same token return 410 Gone. Tokens expire after 72 hours regardless of use.

## 4. Acceptance criteria (testable)
- `backend/tests/test_intake_tokens.py`:
  - Token rotation: issuing a second token for the same candidate identifier does not invalidate the first until used or expired.
  - Rate limit: more than 10 GETs on `/intakes/{token}` in 60s → `429`.
  - PHI hygiene: error responses never echo the candidate patient identifier or any submitted payload field.
  - Cross-org isolation: a token for org A cannot be redeemed by a submit carrying an org-B-scoped accept call.
- `backend/tests/test_intake_submissions.py`:
  - Accept path writes the draft patient and returns the new `patient_id`.
  - Reject path leaves the submission with `status = rejected` and a reason string, no patient created.
- API contract:
  - `POST /intakes/tokens` (admin|front_desk) → `201 {token, url, expires_at}`
  - `GET /intakes/{token}` (unauth, time-boxed) → `200 {form_schema, organization_branding}` or `410`
  - `POST /intakes/{token}/submit` (unauth) → `201 {submission_id}`
  - `POST /intakes/{id}/accept` (staff) → `201 {patient_id, draft_encounter_id}`
- Playwright: `e2e/intake.spec.ts` walks the full path issuer → patient submit → staff accept; Axe-AA on both patient and admin surfaces.

## 5. Codex implementation scope
Create:
- `backend/app/models/intake.py` — `IntakeToken`, `IntakeSubmission` models.
- Migration `backend/alembic/versions/xxxx_phase_b_intake.py`.
- `backend/app/routers/intake_public.py` — unauth routes, mounted with no auth dependency and a dedicated rate limit decorator.
- `backend/app/routers/intake_admin.py` — staff routes (issue token, list pending, accept, reject).
- `backend/app/services/intake/tokens.py` — hashing (HMAC-SHA256 with per-org salt), verification, expiry.
- `backend/app/middleware/rate_limit.py` — simple fixed-window in-process limiter; redis-backed is Phase C.
- `frontend/src/routes/public/IntakePage.tsx` — single route for `/intake/{token}`, no app shell.
- `frontend/src/routes/admin/IntakeQueue.tsx` — staff review surface.
- `frontend/src/components/intake/IntakeForm.tsx` — form fields (demographics, reason-for-visit, current meds list, allergies list, HPI textarea, consent checkbox).

Modify:
- `backend/app/main.py` — register routers; mount `intake_public` before the auth middleware.
- `frontend/src/router.tsx` — add unauthenticated `/intake/{token}` branch, separate layout from the app shell.

SQL sketch:
```sql
CREATE TABLE intake_tokens (
  id UUID PRIMARY KEY, token_hash TEXT NOT NULL UNIQUE,
  organization_id UUID NOT NULL,
  patient_identifier_candidate TEXT,
  expires_at TIMESTAMPTZ NOT NULL, used_at TIMESTAMPTZ,
  created_by UUID NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE intake_submissions (
  id UUID PRIMARY KEY, token_id UUID NOT NULL REFERENCES intake_tokens(id),
  payload_json JSONB NOT NULL,
  submitted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  status TEXT NOT NULL CHECK (status IN ('pending_review','accepted','rejected')),
  reason TEXT
);
```

UI testids: `intake-form`, `intake-consent-checkbox`, `intake-submit`, `intake-queue-row`, `intake-accept-btn`, `intake-reject-btn`.

## 6. Out of scope / process only
- SMS or email delivery of the intake link. Staff copy-paste from the issuance modal in Phase B.
- Multi-session save/resume; the form is single-sitting.
- Insurance capture / insurance card upload (Phase C).
- Photo-ID capture; this is not an identity-verification surface.
- Accessibility translation into non-English languages beyond what `i18n` scaffolding already supports.

## 7. Demoable now vs later
- Demoable on ship: staff issues token → new tab → patient-perspective form → submit → staff accepts → draft encounter appears pre-filled. Full loop on a laptop with one browser profile.
- Not demoable: an actual SMS arriving on the patient's phone with the link; we tell buyers the delivery channel is Phase C.

## 8. Dependencies
- Rate limiter must land before first `pilot/integrated_readthrough` partner exposes the public route to the internet.
- Branding fields on `organizations` (logo URL, display name) should be available; if not, the surface falls back to a neutral ChartNav header.
- CSRF exemption for `/intake/*` — this is an unauthenticated, public, token-scoped surface and cannot use session CSRF.

## 9. Truth limitations
- This is not a portal. Patients cannot log in, view past submissions, or edit a submitted form.
- No identity verification beyond possession of the token. A shared link is a shared capability; operators must treat tokens as semi-sensitive.
- No HIPAA audit-level identity binding occurs at the patient side; the accepting staff member remains the accountable party in `workflow_events`.
- Accepted data is treated as patient self-report until the clinician confirms during the visit. The note templates must not auto-promote meds/allergies into the final note without clinician review.

## 10. Risks if incomplete
- Without digital intake, ChartNav's "documentation-time savings" claim remains upstream-only (clinician-side). Practices benchmarking against Phreesia, Luma, Klara, or an EHR-native intake will discount ChartNav's value.
- Front-desk friction is the most visible pain point in small-practice demos; not addressing it leaves the competitive story incomplete.
- Token-handling mistakes (predictable tokens, no expiry, echoing PHI in errors) become security findings during the first enterprise diligence. Getting this right in Phase B costs less than retrofitting later.
