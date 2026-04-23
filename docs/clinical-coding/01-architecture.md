# Clinical Coding Intelligence — Architecture

## Purpose

Advisory ICD-10-CM diagnosis search + ophthalmology-oriented workflow
helpers for the ChartNav clinician and biller/coder surfaces.
**Not autonomous coding. Not a reimbursement guarantee.**

## Boundaries (what this feature does / does not do)

- **Does**
  - Ingest official CDC/NCHS ICD-10-CM release files (via the CMS
    mirror when FTP is blocked).
  - Parse and normalize them into relational tables.
  - Version the code set by effective date so searches always run
    against the release that was valid on the date of service.
  - Expose search, code detail, favorites, specialty quick-picks,
    and a visible audit trail.
  - Surface advisory specificity prompts and claim-support hints
    driven by a structured rules layer.
- **Does not**
  - Auto-code a chart.
  - Bill, claim, or submit to a payer.
  - Guarantee reimbursement, coverage, or medical necessity.
  - Replace the clinician's judgement, payer policy review, or
    certified coding staff.

## Component layout

```
apps/api/app/
├─ lib/icd10cm/
│   ├─ parser.py            # CDC/CMS order-file fixed-width parser
│   └─ fetch.py              # download + checksum + retain raw artifact
├─ services/clinical_coding/
│   ├─ ingest.py             # end-to-end sync pipeline
│   ├─ query.py              # version resolution + search + code detail
│   ├─ favorites.py          # per-provider pinned / usage counters
│   └─ specialty.py          # ophthalmology bundles + advisory rule seed
├─ api/routes.py             # Phase 64 endpoint block
└─ alembic/versions/
    └─ c1c2c3c4cc01_clinical_coding_intelligence.py
apps/api/data/icd10cm/raw/   # retained raw release artifacts (per version)
apps/api/tests/
├─ fixtures/icd10cm/         # small fixed-width fixture for offline tests
└─ test_clinical_coding.py   # 16 contract tests

apps/web/src/features/clinical-coding/
├─ types.ts                   # shared TypeScript contracts
├─ api.ts                     # thin fetch client
└─ ClinicalCodingPanel.tsx    # main screen (left rail / center / right)
```

## Data flow — ingestion

```
[scheduled OR admin] ─→ run_sync()
  │
  ├─ 1. open coding_sync_jobs row (status=running)
  │
  ├─ 2. _find_source(version_label | today)
  │   - picks the release whose [effective_start, effective_end]
  │     window contains today, or the explicit label
  │
  ├─ 3. fetch_release(source)
  │   - http-get the CDC/CMS zip
  │   - unzip, retain ALL files in apps/api/data/icd10cm/raw/<label>/
  │   - SHA-256 each file, build a manifest
  │   - network=False falls through to a local fixture (tests) or the
  │     previously-retained raw copy (re-ingestion)
  │
  ├─ 4. idempotency — if icd10cm_versions already has this label
  │       with parse_status='ready' AND same checksum, SHORT-CIRCUIT
  │
  ├─ 5. upsert icd10cm_versions row (parse_status='parsing')
  │
  ├─ 6. parse_order_file() → yield CodeRecord per line → batch INSERT
  │       into icd10cm_codes + icd10cm_code_relationships
  │
  ├─ 7. parse_status='ready'; if no other active version, activate
  │
  ├─ 8. seed_support_rules() — idempotent; adds default
  │       ophthalmology_support_rules if not already present
  │
  └─ 9. close coding_sync_jobs row (status=succeeded, record counts)
```

## Data flow — read path

```
GET /clinical-coding/version/active
GET /clinical-coding/version/by-date?dateOfService=YYYY-MM-DD
GET /clinical-coding/search?q=…&dateOfService=…
GET /clinical-coding/code/{code}?dateOfService=…
GET /clinical-coding/specialties
GET /clinical-coding/specialty/{tag}/codes

Every read resolves version FIRST (`resolve_version_for_date`),
then constrains every subsequent query to that version_id. The UI
always surfaces which version served the response.
```

## Safety posture (surfaced in UI)

The panel renders a persistent yellow advisory banner:

> Advisory workflow support. Clinical Coding Intelligence supports
> your charting workflow. It does not replace clinician judgment,
> guarantee reimbursement, or replace payer policy review. You own
> every code attached to this chart.

Every code result carries `specificity_flags` chips. Every detail
view surfaces any matching `ophthalmology_support_rules` entries
with their `source_reference` visibly printed.

## Truth limitations

- Source of truth is CDC/NCHS via the CMS mirror. No unofficial
  coding site content is ingested.
- The rules layer draws on CDC Official ICD-10-CM Guidelines and
  clinical coding consensus language. Payer-specific policy
  statements are not asserted; when a rule references CMS LCDs, the
  rule explicitly directs the user to verify the current policy.
- No reimbursement or medical-necessity guarantees are claimed.
- This feature is advisory only and does not replace certified
  coding staff.
