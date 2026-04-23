# Safety & Compliance Language

## Visible in the UI (verbatim)

Every time the Clinical Coding panel renders, this banner is shown
above the search input:

> **Advisory workflow support.** Clinical Coding Intelligence
> supports your charting workflow. It does not replace clinician
> judgment, guarantee reimbursement, or replace payer policy
> review. You own every code attached to this chart.

Every code-detail card shows the source file + line number and the
active `version_label` + `source_authority`.

## Buyer-safe wording (approved copy)

For use in RFP responses, website copy, and pitch decks:

- "ChartNav surfaces official ICD-10-CM codes from the CDC/NCHS
  release and exposes specialty-aware workflow prompts. The
  clinician remains responsible for selecting and attaching the
  correct code to the chart."
- "ChartNav retains every raw source artifact from the CDC/NCHS
  release. Every code surfaced in the UI carries a visible
  reference to the release version, effective dates, source
  authority, and download timestamp."
- "Clinical Coding Intelligence is an advisory reviewer-assist.
  It is not an autonomous coding engine, not a billing system,
  and does not guarantee payer coverage or reimbursement."

## Wording to avoid

- "Automatic coding" / "AI coding" / "One-click billing"
- "Guaranteed payment" / "Reimbursement-safe"
- "Certified coding software"
- "Replaces your coder"
- "HIPAA-certified" (ChartNav's HIPAA posture is built, not
  externally audited; use "HIPAA-aligned posture" instead)

## Regulatory posture

- The feature is operational software that indexes a public code
  set. It is not a medical device.
- The ingestion pipeline retains the raw CDC/NCHS release for
  audit. Retention is operator-configurable but never deletes
  implicitly.
- Access is role-gated: write operations (favorites upsert / admin
  sync) require admin or clinician roles server-side.
- Audit events are written through the existing ChartNav
  `coding_sync_jobs` audit trail.

## If a payer or auditor asks

- Point them to `GET /admin/clinical-coding/audit` for the full
  version history with checksums + effective dates + source URLs.
- The raw release files are on disk at
  `apps/api/data/icd10cm/raw/<version_label>/`.
- The manifest with per-file SHA-256 is stored on the version row
  in `manifest_json`.
