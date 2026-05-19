# ChartNav BAA / Vendor Readiness Checklist

> **Phase:** 23.
> **Type:** Working checklist. **Not** an attestation. **No real
> vendor is marked approved unless a BAA is actually documented
> in the practice's records.**

## Status legend

| Status | Meaning |
|---|---|
| **Pending** | Vendor not yet engaged for this practice. |
| **Required — not executed** | BAA required but not yet signed. **Blocks real PHI.** |
| **Required — executed** | BAA signed and filed. |
| **Not required** | Vendor does not touch ePHI. |
| **Unknown** | Vendor relationship unclear; must be resolved before real PHI. |

---

## Vendor categories

### Cloud hosting vendor

- Vendor name: `__________`
- Service purpose: production application + database hosting
- ePHI access: **Yes** (database storage, application memory)
- BAA required: **Yes**
- BAA executed: `__________`
- PHI egress approved: not applicable (hosting is the deployment
  environment, not egress)
- Notes: practice procurement file should hold the BAA

### Database hosting vendor *(if separate from cloud hosting)*

- Vendor name: `__________`
- Service purpose: managed Postgres
- ePHI access: **Yes**
- BAA required: **Yes**
- BAA executed: `__________`
- Notes: required because Postgres holds ePHI in production

### Object / file storage vendor *(if used)*

- Vendor name: `__________`
- Service purpose: imaging-pipeline `storage_uri` destination
  (Phase 21B stores **metadata only** — the file binary lives in
  the practice's storage backend)
- ePHI access: **depends on practice configuration.** ChartNav
  does not store image binaries; the storage URI points at the
  practice's own bucket. If that bucket is the practice's
  responsibility, ChartNav's BAA does not extend to it.
- BAA required: **practice-dependent** — required if the storage
  vendor is contracted *by ChartNav*. Otherwise the practice
  owns the BAA with their storage vendor.
- BAA executed: `__________`

### Email vendor *(if any)*

- Vendor name: `__________`
- Service purpose: transactional email (e.g. user invitations)
- ePHI access: **must be no.** ChartNav invitation emails do not
  contain PHI. If a future feature would send PHI via email, BAA
  becomes required.
- BAA required: **No** (current architecture)
- BAA executed: not applicable
- Notes: confirm during Gate 2 that no invitation template
  carries PHI

### STT / transcription vendor *(if enabled)*

- Vendor name: OpenAI Whisper / future provider
- Service purpose: speech-to-text for AI scribe session
- ePHI access: **Yes** (transcript may contain PHI)
- BAA required: **Yes** — unless STT is disabled
- BAA executed: `__________`
- PHI egress approved: **must be `__________` and recorded.**
  Default is **disabled.** The `CHARTNAV_PILOT_ALLOW_STT_OPENAI_WHISPER`
  override gate exists in `validate_controlled_pilot_env.sh`.

### AI / LLM vendor *(if enabled)*

- Vendor name: `__________`
- Service purpose: AI draft generation / proposal review
- ePHI access: **practice-configurable.** Current default
  generates drafts deterministically (no external LLM). If an
  external LLM is enabled, BAA becomes required.
- BAA required: **Yes** — only if LLM is enabled
- BAA executed: `__________`
- PHI egress approved: `__________`
- Notes: `ai_governance_log` stores **hashed** prompts/outputs
  only. Even with an external LLM, ChartNav's own audit trail is
  metadata-only.

### Logging / monitoring vendor

- Vendor name: `__________`
- Service purpose: application log forwarding + monitoring +
  alerting
- ePHI access: **must be no.** ChartNav writes metadata-only
  audit events; application logs should not carry PHI. If the
  log destination's retention or content policy could surface
  PHI by accident, BAA becomes required.
- BAA required: **practice-dependent** — recommend yes for
  defense-in-depth
- BAA executed: `__________`

### Backup storage vendor

- Vendor name: `__________`
- Service purpose: encrypted backup storage destination for
  `scripts/backup_controlled_pilot_postgres.sh`
- ePHI access: **Yes** (Postgres dump contains ePHI)
- BAA required: **Yes**
- BAA executed: `__________`
- Encryption-at-rest confirmed: `__________`
- Notes: backups are encrypted at the hosting layer; the
  destination storage must also be an approved environment

### Analytics vendor *(if any)*

- Vendor name: `__________`
- Service purpose: product / web analytics
- ePHI access: **must be no.** ChartNav has no analytics-vendor
  integration today. If one is added, ensure it never receives
  PHI.
- BAA required: **No** (current architecture)
- BAA executed: not applicable

---

## Per-vendor due-diligence checklist

For every vendor marked "Required — executed," confirm:

- [ ] BAA signed by both parties and filed in the practice's
      records.
- [ ] Vendor's security posture (SOC 2 or equivalent) reviewed.
- [ ] Vendor's data-residency commitments documented.
- [ ] Vendor's subprocessor list reviewed against ChartNav's own
      subprocessor inventory.
- [ ] Vendor's breach-notification timelines documented.
- [ ] Vendor's incident contact captured.
- [ ] Renewal / review date set.

## Blocking gate

A real-PHI go-live cannot proceed if any "BAA required" vendor
is still in "Required — not executed" or "Unknown" status. See
`chartnav-real-phi-go-live-gate.md` Gate 1 and Gate 7.
