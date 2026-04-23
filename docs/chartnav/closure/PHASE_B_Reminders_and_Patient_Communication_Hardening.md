# Phase B — Reminders and Patient Communication Hardening

## 1. Problem solved
The reminders surface today is pure storage plus a calendar view. There is no concept of a message, no inbound channel, no opt-in/opt-out handling, and no status model for delivery. Pilot buyers cannot safely claim that ChartNav "communicates with patients"; and the architecture does not yet support plugging a real SMS or email vendor without refactoring. This spec lays the track: data model, opt-out precedence, a pluggable provider seam, and an honest UI that never overstates delivery. Real transmission remains deferred to Phase C.

## 2. Current state (honest)
- `reminders` table fields: `id, organization_id, encounter_id, patient_identifier, title, body, due_at, status, completed_at, completed_by, created_by, created_at, updated_at`.
- Six routes in `backend/app/routers/reminders.py`: `GET /reminders`, `POST /reminders`, `GET /reminders/{id}`, `PATCH /reminders/{id}`, `POST /reminders/{id}/complete`, `DELETE /reminders/{id}`.
- UI: month calendar in `frontend/src/routes/Calendar.tsx` plus inline create/edit in `frontend/src/components/reminders/ReminderDrawer.tsx`. No chip, badge, or status beyond `{pending, complete, cancelled}`.
- No outbound delivery. No `messages` table. No opt-in/opt-out storage. No concept of an inbound message.
- `grep -r "twilio\|smtp\|sendgrid" backend/app/` returns zero matches.

## 3. Required state
- A `messages` table models every outbound and inbound communication tied to a patient identifier within an organization.
- A `patient_communication_preferences` table captures channel-level opt-in/opt-out with source attribution ("staff-recorded", "inbound STOP", "intake-form-consent").
- An inbound `STOP` on any channel flips opt-in to false, stamps `opted_out_at`, and cancels any queued outbound for that patient/channel.
- A provider seam exposes `StubProvider` (logs only, returns synthetic provider_message_ids) and a `TwilioProviderSkeleton` that defines the interface but raises `NotImplementedError` on send — wiring is Phase C.
- UI surfaces an opt-out badge on the reminder patient tag when preferences indicate opt-out on the channel that reminder intends to use.
- The word "delivered" in the UI is always qualified: "stub-delivered" when no real provider is wired.

## 4. Acceptance criteria (testable)
- `backend/tests/test_messaging_opt_out.py`:
  - Inbound STOP flips preference to opted_out and cancels queued outbound for that channel.
  - Queued outbound to an opted-out patient transitions to `opt_out` without calling any provider.
  - Re-opting in requires an explicit staff or patient affirmative action; STOP cannot silently revert.
- `backend/tests/test_messages_status_transitions.py`:
  - Valid transitions: `queued → sent → delivered`, `queued → sent → failed`, `queued → opt_out`.
  - Invalid transitions (e.g. `delivered → queued`) return 409.
- `backend/tests/test_messaging_provider_seam.py`:
  - `StubProvider.send()` returns a synthetic ID and writes an event to `workflow_events`.
  - `TwilioProviderSkeleton.send()` raises `NotImplementedError`.
- Playwright `e2e/reminders_opt_out.spec.ts` — reminder drawer shows `data-testid="opt-out-badge"` when the patient is opted out on the relevant channel. Axe-AA pass.
- UI copy assertion: any label reading "Delivered" while using `StubProvider` renders as "Stub-delivered" via a shared component `MessageStatusLabel`.

## 5. Codex implementation scope
Create:
- `backend/app/models/messages.py` — `Message`, `PatientCommunicationPreference` models.
- Migration `backend/alembic/versions/xxxx_phase_b_messaging.py`.
- `backend/app/services/messaging/provider.py` — abstract `MessagingProvider` interface + `StubProvider` + `TwilioProviderSkeleton`.
- `backend/app/services/messaging/dispatcher.py` — respects opt-out precedence, enqueues, updates status.
- `backend/app/services/messaging/inbound.py` — STOP/HELP keyword handling (keyword list per channel).
- `backend/app/routers/messages.py` — `GET /messages` (admin), `GET /patients/{id}/preferences`, `PATCH /patients/{id}/preferences`.
- `frontend/src/components/reminders/OptOutBadge.tsx`, `frontend/src/components/messages/MessageStatusLabel.tsx`.

Modify:
- `backend/app/routers/reminders.py` — on reminder creation, optionally enqueue a message via dispatcher (behind an org-level `messaging_enabled` flag, default false in Phase B).
- `frontend/src/components/reminders/ReminderDrawer.tsx` — show channel selector + opt-out badge.

SQL sketch:
```sql
CREATE TABLE messages (
  id UUID PRIMARY KEY, organization_id UUID NOT NULL,
  reminder_id UUID REFERENCES reminders(id),
  patient_identifier TEXT NOT NULL,
  channel TEXT NOT NULL CHECK (channel IN ('sms_stub','email_stub')),
  direction TEXT NOT NULL CHECK (direction IN ('outbound','inbound')),
  body TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN
    ('queued','sent','failed','opt_out','delivered','read')),
  provider_message_id TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE patient_communication_preferences (
  id UUID PRIMARY KEY, organization_id UUID NOT NULL,
  patient_identifier TEXT NOT NULL,
  channel TEXT NOT NULL,
  opted_in BOOLEAN NOT NULL,
  opted_out_at TIMESTAMPTZ,
  opt_out_source TEXT,
  UNIQUE(organization_id, patient_identifier, channel)
);
```

## 6. Out of scope / process only
- Real SMS or email transmission.
- Two-way threaded messaging UX (inbox, conversation view). Inbound is parsed for opt-out keywords only.
- MMS, attachments, or delivery receipt webhooks.
- Template library and compliance-approved language review.
- Consent UX beyond a single intake consent checkbox and a preferences page.

## 7. Demoable now vs later
- Demoable on ship: create a reminder; show opt-out badge surface; show stub-delivered status chain in the admin message log; simulate an inbound STOP and watch the preference flip.
- Not demoable: a real message arriving on a phone; delivery-rate metrics; patient replying in a conversation.
- Demo scripts must use language like "in pilot we wire a real provider; today this is a stub so we can verify the opt-out logic end-to-end."

## 8. Dependencies
- `messages` is reused by the Post-Visit Summary spec (delivery of the read-only summary link). Those models must land together.
- Admin Dashboard's reminders-overdue KPI is unaffected; it does not read messages.

## 9. Truth limitations
- No real SMS or email is sent in Phase B. The "delivered" status, when produced by `StubProvider`, means "the stub recorded a synthetic delivery" — the UI and logs must never imply carrier-level delivery.
- Opt-out enforcement is only as reliable as the inbound parser. In Phase B we have no real inbound webhook, so STOP is simulated via an admin action and the intake consent checkbox.
- No HIPAA Business Associate Agreement is in place with any messaging vendor because no vendor is wired. Procurement reviews that require a BAA for outbound SMS/email must defer to Phase C.

## 10. Risks if incomplete
- Wiring a real provider without this skeleton leads to opt-out compliance gaps (TCPA, CAN-SPAM), which are enforcement-grade risks, not product risks.
- Without a `messages` table, the Post-Visit Summary delivery flow has nowhere to record status, forcing a parallel mini-model that will need to be merged later.
- Buyers ask "what is the architecture when you go to real SMS?" — having the seam and the stub wired is a credible answer; not having it reads as "we haven't thought about it."
