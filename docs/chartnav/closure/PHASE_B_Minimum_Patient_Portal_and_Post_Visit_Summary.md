# Phase B — Minimum Patient Portal and Post-Visit Summary

## 1. Problem solved
Ophthalmology visits routinely produce instructions the patient must remember: drop schedules, medication changes, dilation recovery timing, follow-up intervals, and intraocular pressure numbers. Without a written after-visit summary, patients call the practice within 24–48 hours asking the same three questions. Practices today use fragmented solutions — handwritten notes, EHR portal printouts, or nothing. ChartNav already carries the signed note; rendering it into a one-page, patient-readable summary is a low-cost, high-visibility addition.

This spec ships a one-page post-visit summary PDF plus an optional magic-link web view. It intentionally does not introduce a patient login; that is a larger undertaking and not required for a credible pilot.

## 2. Current state (honest)
- `note_versions` carries the signed SOAP payload. No patient-facing rendering exists.
- The only unauthenticated route plan in Phase B is the Digital Intake token surface; there is no existing precedent for an unauthenticated read-only artifact view.
- `reminders` delivery is stub-only; the `messages` table and dispatcher arrive in the companion spec and are reused here for delivery.
- PDF rendering dependency (WeasyPrint) arrives via the Referring-Provider Communication spec; this spec reuses that pipeline.

## 3. Required state
- From any signed note, a clinician (or admin) can generate a post-visit summary. The PDF is deterministic — regenerating produces the same output unless the underlying `note_version_id` differs.
- The generated summary includes: patient name (display name only, not MRN), visit date, provider, top findings (VA right and left, IOP right and left), assessment in plain language (pulled from the deterministic SOAP extractor's plain-language surface), medications broken into `unchanged / new / changed`, follow-up interval, clinician contact block.
- Optional magic-link: a single-use or 30-day-expiry token renders `/summary/{token}` unauthenticated. We choose 30-day expiry + single-device view restriction (the token binds to the first requesting IP-class for the lifetime of the token) to balance usability against casual link forwarding.
- Delivery channels: `download` (always), `email_stub` and `sms_stub` via the `messages` dispatcher when a preference is recorded.

## 4. Acceptance criteria (testable)
- `backend/tests/test_post_visit_summaries.py`:
  - Happy path: signed encounter → `POST /note-versions/{id}/post-visit-summary` → `201` with `pdf_storage_ref` and `read_link_token`.
  - Unsigned note → 422.
  - Cross-org access via token → 404 (never reveal existence).
  - Token expiry: a row with `expires_at < now()` → 410 on `/summary/{token}`.
  - PHI scoping: the unauth endpoint never returns any field for another patient regardless of parameter tampering.
- Playwright `e2e/post_visit_summary.spec.ts` — generate summary, open read-link in an incognito context, verify content rendering, run Axe-AA on the patient-facing view.
- API contract:
  - `POST /note-versions/{id}/post-visit-summary` → `201 PostVisitSummary`
  - `GET /post-visit-summaries/{id}/pdf` (authed) → `200 application/pdf`
  - `GET /summary/{token}` (unauth) → `200 text/html` or `410 Gone`

## 5. Codex implementation scope
Create:
- `backend/app/models/post_visit_summary.py` — `PostVisitSummary` model.
- Migration `backend/alembic/versions/xxxx_phase_b_post_visit_summary.py`.
- `backend/app/services/summaries/renderer.py` — Jinja2 + WeasyPrint; template at `backend/app/services/summaries/templates/post_visit_summary.html.j2`.
- `backend/app/services/summaries/plain_language.py` — thin mapper from the deterministic SOAP extractor's assessment text to patient-readable language (word substitution table + sentence smoothing; no LLM call).
- `backend/app/routers/post_visit_summaries.py` — auth'd generation + PDF download.
- `backend/app/routers/public_summary.py` — unauth `/summary/{token}` HTML view, mounted like `intake_public`.
- `frontend/src/routes/public/SummaryPage.tsx` — unauthenticated, no app shell, print-friendly.
- `frontend/src/components/notes/PostVisitSummaryPanel.tsx` — in Note Workspace post-sign.

Modify:
- `backend/app/services/evidence/chain.py` — add `post_visit_summary_rendered`, `post_visit_summary_viewed`.
- `backend/app/services/messaging/dispatcher.py` — support `summary_link` message kind referencing a token rather than free text.
- `frontend/src/router.tsx` — unauth branch for `/summary/{token}`.

SQL sketch:
```sql
CREATE TABLE post_visit_summaries (
  id UUID PRIMARY KEY, encounter_id UUID NOT NULL,
  note_version_id UUID NOT NULL UNIQUE,
  rendered_pdf_storage_ref TEXT NOT NULL,
  read_link_token TEXT NOT NULL UNIQUE,
  expires_at TIMESTAMPTZ NOT NULL,
  delivered_via TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Content layout (single page):
- Header: practice name, clinician name, visit date.
- "Your visit" section: 2–3 sentence plain-language summary.
- "Your eye measurements": VA OD/OS, IOP OD/OS, pupil findings if present.
- "Your medications": three sub-sections — unchanged, new, changed (with old → new dosage).
- "When to follow up": interval in plain words ("in 4 weeks", not "4/52").
- "Contact us": phone, hours, urgent-eye-problems escalation line.

Testids: `post-visit-summary-panel`, `generate-summary-btn`, `read-link-copy-btn`, `summary-page-root` (unauth view).

## 6. Out of scope / process only
- A full patient portal: login, account, past-visit history, messaging, scheduling, bill pay. None of these are in Phase B.
- Multi-language output. Phase B is English-only.
- Patient-side annotation, questions, or replies.
- Accessibility beyond Axe-AA; no screen-reader walk-through recording.

## 7. Demoable now vs later
- Demoable on ship: generate the PDF from a signed ophthalmology note; open the magic-link in a second browser; show that it renders without login; show the evidence-chain event appearing in admin.
- Not demoable: actual SMS delivery of the link (stub-only); patient account features (do not exist).

## 8. Dependencies
- Referring-Provider Communication spec introduces the WeasyPrint dependency; this spec depends on that landing first or at the same time.
- Messaging spec's `messages` table and dispatcher are required to record `summary_link` outbound intent.
- The deterministic SOAP extractor must emit a `plain_language_assessment` field; if not present, this spec lands a minimal mapper in `summaries/plain_language.py` until the extractor is extended.

## 9. Truth limitations
- This is not a HIPAA-conforming patient portal. It is a read-only view of a single visit behind a time-boxed token. Operators must disclose to patients that the link is an after-visit summary, not a portal.
- No audit of "patient actually viewed this" is possible beyond a best-effort first-GET event; copy-paste-forwarded links produce indistinguishable views.
- The token is not an identity binding. Anyone with the link can open the summary until it expires.
- Plain-language assessment is rule-based, not LLM-generated, to preserve determinism and avoid hallucination risk. This trades nuance for safety.

## 10. Risks if incomplete
- Absence of a patient-visible artifact makes ChartNav feel entirely back-office. Referring providers and practice owners often ask "what does the patient see?" — without an answer, the product story has a visible gap.
- Callback volume post-visit is a recurring small-practice complaint; not addressing it forgoes the most common "thank you" pilot anecdote.
- Building this in Phase C without the messaging seam in place would require retrofitting a parallel delivery path; doing it now keeps the data model clean.
