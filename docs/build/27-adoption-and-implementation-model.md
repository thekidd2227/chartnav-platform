# Adoption & Implementation Model

How a clinic moves onto ChartNav without ripping out what they have.

## 1. Adoption paths

ChartNav supports **two entry points** — neither is a "rip and replace":

### Path A — Overlay (integrated mode)

The clinic keeps its existing EHR/EMR. ChartNav runs next to it and
reads through an adapter for encounters/patients, while writing
workflow, coding, and documentation activity back into ChartNav's own
tables. Over time, more operations can be pushed back through the
adapter into the incumbent system.

```
Day 1   → CHARTNAV_PLATFORM_MODE=integrated_readthrough  (observe-only)
Day 30  → CHARTNAV_PLATFORM_MODE=integrated_writethrough (push notes / status)
Day 90+ → add coding push, reference data sync, etc. via vendor adapter
```

### Path B — Standalone (adopt-as-EMR mode)

The clinic has no incumbent EHR/EMR, or is replacing one. ChartNav is
the system of record. The native adapter persists everything to the
ChartNav database.

```
Day 1   → CHARTNAV_PLATFORM_MODE=standalone
Day 30  → native patients table (next build phase)
Day 90+ → full documentation, coding, billing extensions
```

Both paths use **the same ChartNav core**. The difference is
adapter configuration, not code.

## 2. What ChartNav owns vs what the EMR owns

| Object                    | `standalone`     | `integrated_readthrough`     | `integrated_writethrough` |
|---------------------------|------------------|------------------------------|---------------------------|
| Organization / tenant     | ChartNav         | ChartNav (mirrored)          | ChartNav (mirrored)       |
| Location                  | ChartNav         | ChartNav (mirrored)          | ChartNav (mirrored)       |
| User / role / auth        | ChartNav         | ChartNav                     | ChartNav                  |
| Patient                   | *(roadmap)*      | External EHR                 | External EHR              |
| Encounter                 | ChartNav         | External EHR (fetched via adapter) | External EHR (updated via adapter) |
| Workflow events           | ChartNav         | ChartNav                     | ChartNav                  |
| Coding / billing metadata | ChartNav         | ChartNav (surface)           | Pushed through adapter    |
| Documents / notes         | ChartNav (as workflow_events) | External EHR (read-only) | Pushed through adapter    |
| Audit trail               | ChartNav         | ChartNav                     | ChartNav                  |

Audit and identity are **always ChartNav-owned**. That boundary is
intentional: every operator action through the ChartNav surface
needs to be auditable regardless of whether the underlying write
landed in the EHR or the ChartNav DB.

## 3. Implementation sequence

Recommended sequence for a vendor adapter:

1. **Read-only scan.** Implement `fetch_patient`, `fetch_encounter`,
   `search_patients`. Boot in `integrated_readthrough`. Operator
   can verify patient/encounter lookups without a risk of writing.
2. **Reference sync.** Implement `sync_reference_data`. Populate
   ChartNav-side provider and location caches so the UI isn't
   blank.
3. **Status write.** Implement `update_encounter_status`. Flip to
   `integrated_writethrough`. The operator now drives the
   incumbent EMR from ChartNav's workflow UI.
4. **Documentation push.** Implement `write_note`. ChartNav becomes
   the documentation surface; notes land in the incumbent EMR.
5. **Coding / billing.** Vendor-specific and out of scope for the
   core protocol today — extend `ClinicalSystemAdapter` with a
   targeted method when a concrete caller exists. Don't speculate.

Each step is independently shippable. A clinic can stop at any point.

## 4. Deployment posture per mode

| Concern              | `standalone`           | `integrated_*`                   |
|----------------------|------------------------|----------------------------------|
| DB                   | Postgres (ChartNav)    | Postgres (ChartNav) + vendor transport |
| Auth                 | ChartNav JWT / header  | ChartNav JWT / header            |
| Backup / DR          | Clinic owns the DB     | Clinic owns ChartNav DB; vendor owns EMR data |
| PHI surface          | All clinical data in ChartNav | Clinical data transits via adapter; cached in ChartNav only when necessary |
| Regulatory posture   | Full EMR / EHR         | Workflow overlay (regulatory surface follows the incumbent) |

## 5. Migration out

Because standalone data is persisted in a plain Postgres schema
described in `04-data-model.md`, an eventual export to a commercial
EMR is a SQL job + mapping table, not a proprietary migration. Forward
compatibility is explicit: forward-only Alembic migrations, clear
column semantics, no opaque blobs.

## 6. What ChartNav is **not** claiming

- Not a certified EHR today.
- Not HIPAA/SOC2/ISO attested by a third party today — those belong
  to the deployment context, and the platform's operational
  hardening (audit, RBAC, JWT, request tracing) is the input, not
  the certification.
- Not a turnkey FHIR server — the adapter boundary is FHIR-friendly,
  but the translation is the vendor adapter's job.

This document is the operator-facing contract. The engineering
contract lives in `26-platform-mode-and-interoperability.md`.
