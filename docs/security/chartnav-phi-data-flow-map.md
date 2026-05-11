# ChartNav PHI Data Flow Map

> **Phase:** 23.
> **Type:** Architectural data-flow reference. Tracks every place
> ePHI may live or transit in a controlled-pilot deployment.
> Practice security owner uses this to verify their threat model
> matches ChartNav's architecture.

## Legend

| Symbol | Meaning |
|---|---|
| 🔴 **PHI-bearing** | This component holds or transmits ePHI when real PHI is in use. |
| 🟡 **Metadata-only** | Only IDs / status / counts; no clinical body text. |
| ⚪ **Not approved for PHI** | This component is fake-data-only by construction. |
| ↗ **External egress** | Data leaves the controlled-pilot environment. Requires BAA. |
| 🔒 **BAA required** | Vendor BAA must be executed before real PHI flows here. |

---

## Layer 1 — Browser

| Component | Status | Notes |
|---|---|---|
| User session token (bearer JWT) | 🟡 | Identity provider token; contains user identity but no clinical data |
| Encounter chart in DOM | 🔴 | Live rendered chart includes ePHI |
| Local storage / session storage | 🟡 | ChartNav uses localStorage only for the dev-identity selector; no PHI persisted |
| Service worker / cache | ⚪ | None used today |

## Layer 2 — API / application server

| Component | Status | Notes |
|---|---|---|
| FastAPI app process memory | 🔴 | Request bodies + response bodies contain ePHI in active sessions |
| `app.audit.record` writer | 🟡 | Writes metadata-only audit; sentinel tests verify clinical text is never serialized |
| `app.retention` worker | 🟡 | Reads/writes `security_audit_events` |
| Request logging middleware | 🟡 | Logs path, method, status, duration, request id, user email, organization id — no body |
| Health-check endpoint | ⚪ | No PHI ever |
| Admin security endpoints (`/admin/security/{ai-activity, events, posture, readiness}`) | 🟡 | Admin-only; returns metadata-only audit / posture |

## Layer 3 — Database (Postgres)

| Table | Status | Notes |
|---|---|---|
| `patients` | 🔴 | Patient identifier, demographics |
| `encounters` | 🔴 | Encounter records |
| `providers` | 🟡 | Provider directory (work-related identifiers) |
| `locations` | 🟡 | Location names (work-related, not PHI by default) |
| `note_versions` | 🔴 | Immutable signed clinical notes |
| `chart_artifacts` | 🔴 | OD/OS retinal diagrams |
| `transcripts` | 🔴 | Source transcripts (raw text may carry PHI) |
| `extracted_findings` | 🔴 | Structured findings |
| `scribe_sessions` | 🔴 | AI scribe session metadata + transcript references |
| `patient_summaries` | 🔴 | Patient-friendly summary text |
| `pre_visit_briefs` | 🔴 | Pre-visit brief text |
| `provider_action_items` | 🟡 | Review tasks — metadata only by contract |
| `retina_tracking`, `retina_injection_events` | 🔴 | Clinical fields incl. provider assessment text |
| `glaucoma_tracking`, `glaucoma_iop_measurements`, `glaucoma_visual_field_tests` | 🔴 | Clinical fields |
| `imaging_studies`, `imaging_files`, `imaging_measurements` | 🟡 + 🔴 | Metadata only at the row level; `notes` field on `imaging_studies` may carry PHI |
| `provider_location_assignments`, `location_rooms`, `provider_schedule_blocks`, `clinic_operating_hours` | 🟡 | Operational metadata only |
| `work_queue_items` | 🟡 | Queue metadata; `payload_json` may contain references; never rendered into audit detail |
| `patient_segments`, `patient_tags`, `patient_problem_list` | 🔴 | Patient-linked structured data |
| `security_audit_events` | 🟡 | Audit event metadata; `detail` is metadata-only by contract |
| `ai_governance_log` | 🟡 | Hashed prompts / outputs only; never raw text |

## Layer 4 — Backups

| Component | Status | Notes |
|---|---|---|
| `scripts/backup_controlled_pilot_postgres.sh` output | 🔴 🔒 | Full Postgres dump contains ePHI. Encrypted at the hosting layer; destination must be an approved storage backend (BAA required). |
| `scripts/verify_controlled_pilot_backup.sh` | 🟡 | Verifies file exists + checksum; no decryption / no PHI inspection |
| `scripts/restore_controlled_pilot_postgres.sh` | 🔴 🔒 | Restore reads encrypted backup; requires explicit confirmation |

## Layer 5 — Imaging files *(Phase 21B)*

| Component | Status | Notes |
|---|---|---|
| `imaging_files.storage_uri` | 🟡 | URI reference only; ChartNav stores no binaries |
| Practice-owned storage backend | 🔴 ↗ 🔒 | Image binaries live here; ChartNav never touches them. Practice owns the BAA with this vendor if separate from hosting. |
| `data:image/...;base64` URIs | ⚪ | **Rejected** by `_no_data_url` Pydantic validator. Belt-and-suspenders against accidental binary upload. |

## Layer 6 — Speech-to-text *(disabled by default)*

| Component | Status | Notes |
|---|---|---|
| `app.services.stt_provider` stub (default) | ⚪ | Deterministic placeholder; no external egress |
| OpenAI Whisper (gate: `CHARTNAV_PILOT_ALLOW_STT_OPENAI_WHISPER`) | 🔴 ↗ 🔒 | If enabled, audio + transcript egress to OpenAI. Requires BAA + practice approval. |
| `none` mode | ⚪ | Explicit "no STT"; audio uploads fail honestly |

## Layer 7 — AI / LLM draft generation

| Component | Status | Notes |
|---|---|---|
| Deterministic draft generator (default) | ⚪ | No external LLM call; pattern-matched template fill |
| External LLM (if enabled) | 🔴 ↗ 🔒 | Prompt + output may carry PHI. Requires BAA + practice approval. |
| `ai_governance_log` | 🟡 | Hashed prompts / outputs only; never raw text |

## Layer 8 — Support process

| Component | Status | Notes |
|---|---|---|
| Support ticket body | ⚪ | **No PHI permitted.** See `chartnav-support-phi-handling-policy.md`. |
| Support evidence channel | 🔴 🔒 | If a PHI-bearing screenshot or log becomes necessary, transit through a practice-approved secure channel — never the ticket body. |
| ChartNav support team access | 🟡 | Read-only access to the practice's controlled-pilot environment requires explicit practice approval. |

## Layer 9 — Export process

| Component | Status | Notes |
|---|---|---|
| Signed retinal artifact export | 🔴 | Provider-initiated; explicit click; immutable |
| Note version export | 🔴 | Provider-initiated; explicit click |
| Audit log export | 🟡 | Admin-initiated; metadata only |
| Configuration export | ⚪ | No PHI |

---

## End-to-end flow during a real-PHI encounter

1. **Browser ↔ API** — TLS-only; bearer JWT signed by the
   practice's identity provider. 🔴 in flight.
2. **API ↔ Postgres** — within the controlled-pilot VPC. 🔴 at
   rest.
3. **Audit write** — `app.audit.record` writes metadata-only
   detail to `security_audit_events`. 🟡.
4. **Backup** — scheduled Postgres dump to approved storage
   destination. 🔴 at rest 🔒.
5. **Imaging** — provider uploads a study to the practice's
   storage backend. ChartNav records the `storage_uri`, file
   name, content type, size, checksum. **No binary in ChartNav.**
6. **STT / LLM** — disabled by default. If enabled, ↗ + 🔒.
7. **Provider review + sign** — signed retinal artifact becomes
   immutable; edits create explicit forks. 🔴 at rest.
8. **Audit retention** — `scripts/audit_retention.py` enforces
   `CHARTNAV_AUDIT_RETENTION_DAYS` cadence.

## Out-of-band flows (intentional non-flows)

- ChartNav does **not** send patient messages. No patient-facing
  channel exists.
- ChartNav does **not** submit orders, referrals, or claims.
- ChartNav does **not** bill, code, or interact with payers.
- ChartNav does **not** publish to `chartnavmd.com` from this
  deployment. The website is a separate static deploy with no
  PHI.
- ChartNav does **not** interpret OCT, fundus, or visual field
  images. The imaging-pipeline status workflow is provider-driven.

---

## How to update this map

When a new component is added to ChartNav that could touch ePHI:

1. Add the component to the layer above where it fits.
2. Mark its status with one of the four legend symbols.
3. If 🔒 BAA-required, also update `chartnav-subprocessor-inventory.md`
   and `chartnav-baa-vendor-readiness-checklist.md`.
4. Notify the practice security owner with reasonable lead time
   (BAA-defined if specified).
