# ChartNav Subprocessor Inventory

> **Phase:** 23.
> **Type:** Working inventory template. ChartNav lists every
> subprocessor that could touch ePHI. Practice security owner
> reviews line-by-line during their security review.
>
> **No vendor is marked "Approved for PHI" unless a BAA is
> actually documented in the practice's records and the
> practice's security owner has signed off.**

## Status legend

| Status | Meaning |
|---|---|
| **Pending** | Vendor not yet engaged for this practice. |
| **Required** | BAA required and must be executed before real PHI. |
| **Executed** | BAA signed and filed. |
| **Disabled / not applicable** | Service not enabled for this deployment. |
| **Unknown** | Status unclear; must resolve before real PHI. |

---

## Inventory

| # | Vendor | Purpose | Data categories | ePHI involved? | BAA status | Security review status | Approved for PHI? | Renewal / review date | Notes |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `__________` *(cloud hosting)* | Production application + Postgres hosting | Configuration, application memory, DB at rest, DB in transit, ePHI | Yes | Required / Executed | Practice review required | `__________` | `__________` | Required for any real PHI |
| 2 | `__________` *(managed Postgres if separate)* | Database hosting | DB at rest, DB in transit, ePHI | Yes | Required / Executed | Practice review required | `__________` | `__________` | Required when DB hosting is separate from app hosting |
| 3 | `__________` *(object / file storage)* | Imaging `storage_uri` destination (Phase 21B is metadata-only; binaries live in the practice's storage) | File metadata, optionally PHI-bearing binaries (practice-owned) | Practice-dependent | Practice owns BAA with their storage vendor | Practice review | Practice-dependent | `__________` | ChartNav does not store image binaries |
| 4 | `__________` *(email)* | Transactional email (e.g. user invitations) | Email addresses, invitation links | **No** — no PHI in any ChartNav email | Not required (current architecture) | Confirm during Gate 2 of `chartnav-real-phi-go-live-gate.md` | Not applicable | `__________` | Re-evaluate if a future feature would send PHI |
| 5 | OpenAI Whisper *(STT — disabled by default)* | Speech-to-text for AI scribe session | Audio + transcript, may contain PHI | **Yes — if enabled** | Required if enabled, otherwise disabled | Practice approval required to enable | Disabled by default; override gate `CHARTNAV_PILOT_ALLOW_STT_OPENAI_WHISPER` | `__________` | Default state is disabled |
| 6 | `__________` *(AI / LLM if enabled)* | AI draft generation / proposal review | Prompt / output, may contain PHI | **Yes — if external LLM enabled** | Required if enabled | Practice approval required to enable | Disabled by default (ChartNav's default is deterministic) | `__________` | `ai_governance_log` stores hashed prompts/outputs only — even with an external LLM, ChartNav's own audit trail is metadata-only |
| 7 | `__________` *(logging / monitoring)* | Application log forwarding + alerting | Metadata audit, application logs | **Should be no** — ChartNav writes metadata-only | Recommended for defense-in-depth | Practice review | `__________` | `__________` | Re-evaluate if log destination's retention or content policy could surface PHI |
| 8 | `__________` *(backup storage)* | Encrypted Postgres backup destination | Postgres dump | **Yes** | Required | Practice review required | `__________` | `__________` | Required for any real PHI |
| 9 | `__________` *(analytics)* | Product / web analytics | None (today) | **No** — no analytics integration in ChartNav today | Not applicable | `__________` | Not applicable | `__________` | Re-evaluate if analytics is added |
| 10 | Vercel *(preview deploys)* | Preview deployment for review | Demo fake-data only | **No** — Vercel previews are demo-only | Not required for previews | Practice review not required for previews | Not applicable for previews | `__________` | Vercel is for preview deploys only, not real PHI production |

---

## Practice review walk-through

For every row above, the practice security owner walks the line
during real-PHI Gate 7:

1. Confirm vendor name is filled in.
2. Confirm "ePHI involved?" answer matches the practice's
   understanding.
3. Confirm BAA status. If **Required** and not **Executed**, this
   is a blocking gate.
4. Confirm "Approved for PHI?" reflects the practice's written
   approval.
5. Confirm renewal / review date is set.
6. Confirm any free-text notes are accurate.

## Vendor change process

When ChartNav adds a subprocessor that may touch ePHI:

1. Add a row to this inventory.
2. Update `chartnav-baa-vendor-readiness-checklist.md`.
3. Update `chartnav-phi-data-flow-map.md`.
4. Notify the practice security owner with 30 days' notice
   (BAA-defined timing applies if shorter / longer).
5. Wait for practice acceptance before routing ePHI through the
   new vendor.

## Vendor removal process

When ChartNav removes a subprocessor:

1. Confirm no ePHI is in transit through the vendor.
2. Confirm no historical PHI remains in the vendor's stored
   artifacts.
3. Mark the row "Removed `[date]`" rather than deleting it (audit
   trail).
4. Notify the practice.

---

## Not on this list (intentional)

- **Patient-facing vendors** — ChartNav has no patient-facing
  surface, so no patient-facing vendor relationships.
- **Billing / claims / payment vendors** — ChartNav does not bill,
  so no billing-vendor relationships.
- **Device-vendor adapters (Cirrus / Spectralis / Triton / Optos /
  IOLMaster / Humphrey / Topcon)** — ChartNav has no current
  device-vendor adapters. None are listed because none exist. If
  one ships in the future, it gets a row here first.
