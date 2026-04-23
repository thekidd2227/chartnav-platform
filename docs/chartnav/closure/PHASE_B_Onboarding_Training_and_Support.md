# Phase B — Onboarding, Training, and Support

## 1. Problem solved
A pilot that ships without a runbook, a per-role training path, or a defined support contract degrades to a founder-mediated rescue operation within two weeks. ChartNav has the product substance for a pilot; it does not yet have the operational wrapper. This spec defines an onboarding package, a per-role training matrix, a 30/60/90 cadence runbook, three short recorded walk-throughs, and an honest support tier — business-hours email plus an optional weekly sync, with a published escalation path. No 24/7 claim.

## 2. Current state (honest)
- Documentation today lives in `docs/` and in per-phase reports such as `docs/chartnav/PHASE_A_*.md`. There is no onboarding-specific document.
- The video clip pack under `artifacts/video_clips/` contains short product slices (login, encounter create, transcript-to-SOAP, sign). No role-specific walkthrough exists.
- No severity definitions, no escalation matrix, no response-time commitments exist in committed documentation.
- RBAC is enforced (`admin`, `clinician`, `reviewer`, `front_desk`); training content must respect these roles' surfaces.
- Support today is ad-hoc: the ARCG team responds over the channel the buyer already uses (email, Slack shared channel, phone).

## 3. Required state
- Onboarding package (checklist form) in `docs/pilot/onboarding-checklist.md` covering: kickoff call agenda, technical prerequisites, account provisioning, deployment-mode decision, first five encounters rubric, and week-2 review agenda.
- Training matrix in `docs/pilot/training-matrix.md` — per role × per hour of training — with three recorded walk-throughs referenced:
  - Clinician walkthrough (focus: encounter create → transcript → SOAP → sign)
  - Front-desk walkthrough (focus: intake link issuance, reminder CRUD, patient-tag hygiene)
  - Admin walkthrough (focus: dashboard, user management, pilot metrics review)
- 30/60/90 runbook in `docs/pilot/runbook-30-60-90.md` — exactly what happens on days 1, 7, 14, 30, 60, 90, including what the ARCG team does and what the practice does.
- Support tier document at `docs/pilot/support-tier.md`: business-hours email, optional weekly sync call, three severity levels, response-time commitments per severity, and escalation path to ARCG ops.
- No claim of 24/7 support, on-call rotation, or named customer success manager. Those come with paid conversion, not pilot.

## 4. Acceptance criteria (testable)
- Documents exist, are filled, and link to each other:
  - `docs/pilot/onboarding-checklist.md`
  - `docs/pilot/training-matrix.md`
  - `docs/pilot/runbook-30-60-90.md`
  - `docs/pilot/support-tier.md`
  - `docs/pilot/escalation-matrix.md`
- CI doc lint (`scripts/check_pilot_docs.py`) asserts:
  - Every document contains the required section headings.
  - No `TBD`, `TODO`, or `FIXME` strings.
  - Every file referenced by another pilot doc exists.
- Three walk-through videos exist under `artifacts/video_clips/walkthroughs/` named `clinician.mp4`, `front_desk.mp4`, `admin.mp4`. Each is 3–7 minutes long (checked by a duration probe).
- `docs/pilot/runbook-30-60-90.md` is cross-referenced from the Demo Environment pilot scope template.

## 5. Codex implementation scope
Create:
- `docs/pilot/onboarding-checklist.md`
- `docs/pilot/training-matrix.md` — table with rows per role (clinician, front_desk, admin, reviewer) and columns for Hour 1 / Hour 2 / Self-paced follow-up.
- `docs/pilot/runbook-30-60-90.md`
- `docs/pilot/support-tier.md`
- `docs/pilot/escalation-matrix.md` — Sev-1, Sev-2, Sev-3 definitions with response-time commitments (example: Sev-1 1 business hour, Sev-2 4 business hours, Sev-3 2 business days).
- `scripts/check_pilot_docs.py` — documentation lint.
- `artifacts/video_clips/walkthroughs/README.md` — recording checklist, narration script outline, recording tool, redaction rules.

Modify:
- `.github/workflows/ci.yml` — add a `pilot-docs` job that runs `scripts/check_pilot_docs.py`.
- `docs/chartnav/README.md` (if present) — link to the pilot docs section.

Training matrix sketch:
```markdown
| Role       | Hour 1                          | Hour 2                         | Self-paced                |
|------------|---------------------------------|--------------------------------|---------------------------|
| Clinician  | Encounter lifecycle + sign flow | Missing-flag resolution, templates | Watch clinician.mp4     |
| Front desk | Calendar + reminder CRUD        | Intake token issuance          | Watch front_desk.mp4      |
| Admin      | User/role management            | Dashboard + metrics review     | Watch admin.mp4           |
| Reviewer   | Review queue + approve path     | (n/a in pilot)                 | Watch clinician.mp4       |
```

Severity matrix sketch:
```markdown
| Sev | Definition                                    | Response target  |
|-----|-----------------------------------------------|------------------|
| 1   | Unable to sign or export any encounter        | 1 business hour  |
| 2   | Significant workflow degradation, workaround  | 4 business hours |
| 3   | Minor issue, cosmetic, or question            | 2 business days  |
```

## 6. Out of scope / process only
- Learning management system integration (SCORM, Cornerstone, etc.) — not required for pilot scale.
- Certification tracks, quizzes, competency verification.
- 24/7 support, on-call rotation, shared Slack Connect with SLAs. Paid conversion territory.
- Localized (non-English) training content.
- Named Customer Success Manager as a role — handled by ARCG ops directly during pilot.

## 7. Demoable now vs later
- Demoable on ship: complete pilot-doc bundle printed-to-PDF as a leave-behind; three role walk-throughs playable in the demo; severity matrix on a single slide.
- Not demoable: a ticketing portal; a customer success dashboard; a branded learning path.
- Not demoable: real support-response metrics (no history yet); we show the commitments, not the track record.

## 8. Dependencies
- Admin Dashboard must be live for the admin walk-through to demonstrate a real surface.
- Digital Intake must be live for the front-desk walk-through to show the token issuance flow.
- Post-Visit Summary and Referring-Provider specs must be at least partially landed; the clinician walk-through leans on the end-of-encounter flow.
- Demo Environment seed must be deterministic so that the walkthrough recordings stay stable.

## 9. Truth limitations
- ARCG is the support contact in pilot. There is no third-party service desk, no on-call rotation, no global follow-the-sun coverage. The severity-matrix response times are business-hours commitments and must be stated as such.
- Training content reflects the product at recording date; features added after a recording may not be covered until the clip pack is regenerated.
- We cannot claim SOC 2 / HITRUST-aligned change management around training records in Phase B; training delivery is tracked lightly in the pilot tracker, not in an audited LMS.
- "Weekly sync" is opt-in for the practice; if they do not take it, we do not assume visibility into their usage between the 30/60/90 reviews.

## 10. Risks if incomplete
- Without a defined support tier, every pilot issue defaults to a founder phone call. That does not scale past two concurrent pilots and is the most common reason small-vendor pilots die.
- Without a 30/60/90 runbook, the pilot-exit conversation becomes a renegotiation rather than a confirmation — the data is often fine but the narrative is missing.
- Training gaps produce front-desk errors (intake tokens mis-shared, reminders set on opted-out patients) that erode clinician trust in the product within two weeks, independent of product quality.
- Absence of a written severity matrix is a near-automatic red flag in any buyer-side procurement review.
