# Object storage

Clinical artifacts (imaging, exports, attachments) are stored as objects, never
as blobs in PostgreSQL. The storage layer is `apps/api/app/storage/`.

## Adapters

| Adapter | Use | Encryption | Presign |
|---|---|---|---|
| `LocalObjectStorage` | dev only (refuses `CHARTNAV_ENV=prod`) | none | n/a (file URLs) |
| `S3ObjectStorage` | staging/production | SSE-KMS (customer-managed key) | short-expiry GET/PUT |

Selected by `CHARTNAV_STORAGE_BACKEND` (`local` | `s3`) via
`get_object_storage(settings)`.

## Controls (enforced in code)

- **Server-controlled keys** — `derive_key(org_id, kind, name)` →
  `org/<org_id>/<kind>/<safe-name>`. Callers never pass raw keys; the org prefix
  makes cross-tenant addressing impossible. Names are sanitized and `..`
  defused.
- **Organization-scoped access** — every read/delete checks
  `key_belongs_to_org`.
- **Encryption** — S3 puts use `ServerSideEncryption=aws:kms` +
  `SSEKMSKeyId`; presigned PUTs require the same. Bucket default encryption +
  TLS-only policy + public-access-block are set in
  `infra/terraform/aws/s3.tf`.
- **Content-type allowlist** + **size limit** + **SHA-256 checksum
  verification** on every `put`.
- **Presigned URLs** with short expiry (clamped ≤ 1 h) for upload/download —
  the app never proxies object bytes for large media.
- **Audit** — the calling service records upload / download-authorization /
  deletion as audit events (metadata only; see `audit-logging.md`).

## Tests

`apps/api/tests/test_object_storage.py` — key derivation + org scoping,
traversal defusing, content-type allowlist, size limit, checksum mismatch,
cross-org refusal, and prod-refusal of the local adapter.

## Not yet operational

- **Malware scanning** is an integration *hook* (e.g. an S3 event → scanner →
  quarantine), not yet wired. `S3ObjectStorage` is a thin boto3 client; it has
  not been exercised against a live bucket in this repo (no AWS creds here).
- **Object Lock** (WORM) for immutable audit exports is designed + commented in
  `s3.tf`, not enabled.
