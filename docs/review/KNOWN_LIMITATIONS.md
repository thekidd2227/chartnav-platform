# Known limitations (local review)

Honest scope of the review environment. This is a **demo/review** build, not
production and **not** a compliance artifact.

## Environment
- **Dev identity selection** (`X-User-Email` header auth) — anyone can pick any
  seeded user, no password. Production uses real OIDC/JWT with IdP-enforced MFA;
  the app **refuses** header auth when `CHARTNAV_ENV=prod`.
- **Synthetic data only** — deterministic seed (Morgan Lee, Jordan Rivera,
  Priya Shah, etc.). No real patients, no PHI.
- **No live external services** — no real EHR/FHIR, fax, pharmacy, payment,
  email, or live AI calls in this environment.
- Local secrets in the compose file are throwaway placeholders, not real
  credentials.

## Object storage / MinIO
- **MinIO** runs as the S3-compatible store and its private bucket is created,
  **but object storage is not yet wired into any feature**. Retinal diagrams
  store their drawing as `drawing_json` (a JSON column in PostgreSQL), not as
  objects. The API uses the local filesystem storage adapter. So neither MinIO
  nor the storage layer is exercised by a clinical feature yet — the abstraction
  + tests exist (`apps/api/app/storage/`, `test_object_storage.py`), the
  feature wiring (and MinIO `endpoint_url`/path-style support + malware scanning)
  is future work.

## Not a clinical/production system
- ChartNav **does not** diagnose, interpret images autonomously, select
  medications, or bill. All clinical content + AI assistance is
  **provider-controlled and provider-reviewed**.
- **No HIPAA / BAA / SOC 2 / FDA** claim. No security review or penetration test
  has been completed. The hosted SaaS architecture (`infra/terraform/aws/`) is
  **not provisioned** and has not been `terraform validate`/`plan`-run here.
- PostgreSQL row-level security is **designed but not implemented**; tenant
  isolation is enforced at the application/service layer (and tested).

## Build / runtime notes
- First `start` builds images (a few minutes) and installs deps; later starts
  are cached.
- The committed API `Dockerfile` default `CMD` runs uvicorn directly (no
  auto-migrate); the **review compose** runs migration + seed as separate
  one-shot steps before serving, and production runs migration as a separate
  task. Don't rely on `docker run <api-image>` to migrate.
- Frontend full unit suite should be run with `--no-file-parallelism` (or a
  per-worker `--localstorage-file`) under Node 25 due to an experimental-
  localStorage parallelism quirk — not a product bug.
