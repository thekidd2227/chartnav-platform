# Pilot training walk-through clip pack

This directory holds the three short walk-through recordings the
pilot training matrix references:

- `clinician.mp4` — encounter create → transcript → SOAP → sign
- `front_desk.mp4` — intake token issuance + reminder CRUD +
  patient-tag hygiene
- `admin.mp4` — admin dashboard tour + user management + 30/60/90
  metrics review

The clips are NOT committed binary blobs (the repo is a code repo,
not a media repo). They are produced on demand by the recording
checklist below and uploaded to the pilot tracker per practice.

## Recording checklist

For each clip:

1. Boot the demo stack:
   ```
   make demo-up
   ```
   This runs the deterministic seed (Phase 2 item 6) so screens are
   stable across recordings.

2. Log in as the role being demonstrated. The seeded identities
   live in the `pilot-demo-eye-clinic` org:
   - `dr.smith@pilot-demo.local` (clinician) — `clinician.mp4`
   - `front@pilot-demo.local`    (front_desk) — `front_desk.mp4`
   - `admin@pilot-demo.local`    (admin)      — `admin.mp4`

3. Record at 1280x800 viewport (default desktop demo size) at 30 fps.

4. Narrate in the first person. Do NOT claim integrations that are
   not wired (no SMS / email delivery, no PM/EHR write-back, no
   CPT / ICD generation).

5. Length budget: 3–7 minutes per clip (the CI duration probe will
   fail if a clip is shorter than 3 or longer than 7).

## Redaction rules

- Use the seeded `PT-DEMO-*` identifiers only. Never record against
  a real-patient database.
- Do not show the raw intake token or the post-visit summary
  read-link in detail; the recording should demonstrate the
  workflow, not capture a usable secret.
- Practice-specific branding (logos, real provider names) must NOT
  appear unless explicitly cleared by the practice for use in
  ARCG marketing collateral.

## Why this directory carries no binaries

`.gitignore` excludes `*.mp4` under `artifacts/video_clips/` so the
repo stays small. Practices receive the clips through the per-pilot
tracker, not through `git`.
