# Ingestion Flow

## Official sources

Declared in `apps/api/app/lib/icd10cm/fetch.py` as
`CDC_NCHS_RELEASE_SOURCES`. Each entry carries `version_label`,
`source_authority` ("CDC/NCHS" or "CMS"), `source_url`,
`release_date`, `effective_start`, `effective_end`, and the
expected `primary_order_file` name.

Current catalog (extend as new releases publish):

| Label | Authority | Effective | Source URL |
|-------|-----------|-----------|------------|
| ICD-10-CM FY2025 | CMS | 2024-10-01 → 2025-09-30 | `https://www.cms.gov/files/zip/2025-code-descriptions-tabular-order.zip` |
| ICD-10-CM FY2026 (October 2025) | CMS | 2025-10-01 → 2026-03-31 | `https://www.cms.gov/files/zip/2026-code-descriptions-tabular-order.zip` |
| ICD-10-CM FY2026 (April 2026 Update) | CMS | 2026-04-01 → 2026-09-30 | catalog records the stable CMS ICD-10-CM hub (`https://www.cms.gov/medicare/coding-billing/icd-10-codes`); operator overrides the exact zip URL at sync time (see below) |

### Operator override for the April update

The exact CMS file URL for the April mid-year update is not stable before publication. Until the operator confirms the published zip:

- the ingestion pipeline uses the committed fixture at
  `apps/api/tests/fixtures/icd10cm/icd10cm-order-2026-april.txt` and labels
  the resulting version accordingly (`source_authority = "CMS (local fixture)"`);
- a real-data sync requires either (a) `POST /admin/clinical-coding/sync`
  with `{"version_label": "ICD-10-CM FY2026 (April 2026 Update)", "allow_network": true}`
  after the catalog `source_url` has been edited to the published zip, or
  (b) pre-staging the raw artifacts into
  `apps/api/data/icd10cm/raw/ICD-10-CM_FY2026_(April_2026_Update)/` and
  re-running the sync with `allow_network=false`.

### Why two rows for FY2026

CDC/NCHS/CMS publishes ICD-10-CM on a fiscal-year cycle starting
each October 1, with a mid-year addendum effective the following
April 1. The October release is **superseded** on April 1 — not
extended indefinitely. Treating the October release as open-ended
silently maps April-1-or-later encounters to the outdated code set
and hides any newly-added codes. The two-row model preserves the
correct effective window per date of service.

These are the stable CMS mirror URLs. The CDC/NCHS FTP paths
(`ftp.cdc.gov/pub/Health_Statistics/NCHS/Publications/ICD10CM/`)
hold the same content and are acceptable; CMS mirrors are used in
practice because many corporate networks block FTP.

## Triggers

- **Scheduled.** Operator wires the ingestion into a cron or
  scheduled job. Minimum cadence: once per quarter. Recommended
  cadence: once per month to catch mid-year addenda.
- **Manual admin-triggered.** `POST /admin/clinical-coding/sync`
  with admin role + optional `version_label`.

## Idempotency

1. Re-running an already-ingested `version_label` with the same
   `checksum_sha256` short-circuits; the response is
   `"status": "skipped_already_ready"`.
2. Re-running with a new checksum (CMS addenda update) re-ingests:
   - clears prior `icd10cm_codes` + `icd10cm_code_relationships`
     rows for that `version_id`
   - re-parses the new primary file
   - writes a new checksum + `parsed_at`
3. `coding_sync_jobs` always records a row per attempt with
   `started_at`, `completed_at`, `files_downloaded`,
   `records_parsed`, `bytes_downloaded`, and (on failure)
   `error_log`.

## Raw artifact retention

Every downloaded file is written verbatim to
`apps/api/data/icd10cm/raw/<safe_version_label>/`. Operators must
retain this directory for audit purposes; the service never deletes
raw files. If operators need to prune disk, they should archive to
object storage and restore on demand.

Each version's `manifest_json` column in `icd10cm_versions` holds
the per-file `sha256` + byte size, so any tampering can be detected
by re-checksumming the files on disk.

## Offline / fixture fallback

When network fetch fails (sandboxes, corporate proxies), the service
falls back to a fixture at
`apps/api/tests/fixtures/icd10cm/icd10cm-order-2026.txt`. When the
fallback is used, the version row's `source_authority` is labeled
`"CMS (local fixture)"` so downstream audit can tell. A later real
sync supersedes the fixture-authoritative row transparently.

## Error handling

`run_sync` wraps the work in a try/except; on any exception it
writes `status=failed` + the exception class and message into
`coding_sync_jobs.error_log`, then re-raises. The route returns
`500 sync_failed` with the rendered message so operators see the
cause in the admin audit tab.
