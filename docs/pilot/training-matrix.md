# ChartNav pilot training matrix

> **How to use:** the matrix is a per-role training plan. Each row
> is a single staff member; the columns are training hours. Walk-
> through videos live under
> `artifacts/video_clips/walkthroughs/{role}.mp4` and are referenced
> from this matrix.

## Matrix

| Role         | Hour 1                                          | Hour 2                                       | Self-paced follow-up                  |
|--------------|--------------------------------------------------|----------------------------------------------|---------------------------------------|
| Clinician    | Encounter lifecycle + sign flow (Phase A item 3) | Missing-flag resolution + specialty templates | Watch `clinician.mp4`                 |
| Front desk   | Calendar + reminder CRUD                        | Intake token issuance + queue review (Phase 2 item 3) | Watch `front_desk.mp4`         |
| Admin        | User / role management + clinician-lead grant   | Admin dashboard + 30/60/90 metrics review (Phase 2 item 2) | Watch `admin.mp4`           |
| Reviewer     | Review queue + approval path                    | (n/a in pilot scope)                         | Watch `clinician.mp4`                 |
| Technician   | Vitals + pre-charting workflow (Phase A item 2) | (n/a in pilot scope)                         | Watch `clinician.mp4`                 |
| Biller-coder | Code edit surface + handoff export (Phase A item 4) | (n/a in pilot scope)                       | Watch `clinician.mp4`                 |

## What each role does NOT need to learn in pilot

- **Clinicians** do not need to learn the admin dashboard. The
  Operations entry point is hidden unless `is_lead = true` (and
  even then it is optional reading).
- **Front-desk** does not need to learn the consult-letter flow —
  that is clinician-driven post-sign.
- **Reviewer** does not need to learn the post-visit summary
  generator (clinician + admin only).
- **No one** needs SMS-vendor onboarding; the Phase B messaging
  layer is stub-only and the UI labels it that way.

## Walk-through clip pack

Three short walk-throughs live under
`artifacts/video_clips/walkthroughs/`:

- `clinician.mp4` — encounter create → transcript → SOAP → sign
- `front_desk.mp4` — intake token issuance + reminder CRUD +
  patient-tag hygiene
- `admin.mp4` — dashboard tour + user management + metrics review

Recording checklist + redaction rules:
[`artifacts/video_clips/walkthroughs/README.md`](../../artifacts/video_clips/walkthroughs/README.md).

## Recording cadence

- Clip-pack is regenerated when the Phase A or Phase 2 surfaces
  change in a way that breaks the prior recording. The CI workflow
  flags stale recordings; see
  `.github/workflows/ci.yml` (`pilot-docs` job).
- Training content reflects the product at recording date; we do
  NOT claim every feature added after a recording is covered.
- We do NOT issue completion certificates or maintain an LMS for
  pilot training. Track delivery in the per-pilot tracker.
