# ChartNav Role-Based Clinic Workflows — Plan

> **Phase scope target:** Phase 20C (build), Phase 20A (this plan).
> **Type:** Planning only. No frontend code, no schema, no
> migrations.

The current ChartNav UI is encounter-centric: pick an encounter,
work the 9-tab clinical workspace. That's correct for clinicians
in the room. It's wrong for the people **around** the encounter
— the front desk team checking patients in, the technician
running the workup, the reviewer clearing the sign-off queue,
the admin watching cross-location throughput.

This plan defines five role-based dashboards that read from the
[structured data layer](./chartnav-structured-data-layer-plan.md)
(work_queue_items, role_view_presets, patient_segments,
patient_problem_list) and from existing tables (encounters,
note_versions, chart_artifacts, scribe_sessions). Every
dashboard uses **eye-clinic lane language** — front desk, tech
workup, VA / IOP / refraction / dilation, ancillary imaging,
MD encounter, recheck, injection, ASC scheduling, checkout,
provider sign-off, chart-closure lag — not generic "workflow"
phrasing.

## The eye-clinic operating cycle

This is the canonical cycle every dashboard is organized around.
It mirrors how a high-volume ophthalmology practice actually
runs a day:

```
Front desk
   ↓ check-in, demographics, insurance verification (existing system)
Technician workup
   ↓ VA, IOP, refraction, dilation prep
Ancillary imaging
   ↓ OCT, fundus, HVF (when ordered upstream)
MD encounter
   ↓ chart review, exam, OD/OS retinal canvas, dictation
Tech recheck / additional testing
   ↓ post-dilation IOP, repeat measurements
Procedure / injection / ASC scheduling
   ↓ in-room procedure or surgical scheduling handoff
Provider sign-off
   ↓ note version signed + transmitted (existing system)
Checkout / follow-up / recall
   ↓ booking, summary delivery (manual; ChartNav never auto-sends)
```

ChartNav already owns the **MD encounter** and **provider sign-off**
phases (NoteWorkspace + scribe sessions + chart_artifacts +
note_versions). The role dashboards expose the **rest of the
cycle** as work surfaces tailored to who's looking.

## Roles supported

| Role | Existing in `users.role`? | Notes |
|---|---|---|
| `admin` | ✅ | already exists; gets the cross-location admin dashboard |
| `clinician` | ✅ | already exists; gets the doctor dashboard |
| `reviewer` | ✅ | already exists; gets the reviewer dashboard |
| `front_desk` | ❌ new | additive role — non-clinical, no patient chart write access |
| `technician` | ❌ new | additive role — workup measurements only, no MD-level write access |

`front_desk` and `technician` are **additive** to the role enum.
They expand `users.role`'s CHECK constraint and add new entries
to the `TRANSITION_ROLES` map. **They do not change anything
existing roles can do.**

## Front Desk Dashboard

**What this role owns:** check-in, demographics / insurance
placeholders (no auto-verification), visit-type confirmation,
checkout + recall queue. **What this role does not own:** any
clinical chart content.

| Lane | Source | Empty-state copy |
|---|---|---|
| **Today's schedule** | `encounters WHERE scheduled_at::date = today AND location_id = caller.location` | "No appointments scheduled today at this location." |
| **Check-in status** | `encounters` joined with check-in events from `workflow_events` | "All checked-in patients are with the technician or MD." |
| **Missing demographics / insurance** | `patient_problem_list` filtered to operational tags + future `patients.insurance_status` if/when wired | "No demographic gaps flagged. (Insurance verification lives in the practice's existing system.)" |
| **Patient communication log (internal only)** | future internal-comms table or existing comms tab | "No internal handoffs yet for this patient. Use the Chat tab for staff-to-staff messages." |
| **Checkout / follow-up queue** | `work_queue_items WHERE queue_type = 'checkout' OR 'recall' AND status = 'open'` | "No open checkouts or recalls." |

**Hard guardrails:**
- ❌ No automatic patient messaging from this view
- ❌ No automatic insurance verification claims
- ❌ No demographic auto-population from external sources
- ✅ Read-only view of clinical state; staff make calls / mail summaries themselves

## Technician Dashboard

**What this role owns:** the workup phase — VA, IOP, refraction,
dilation, room/location assignment, technician notes, handoff to
the doctor. **What this role does not own:** the MD encounter
itself or any sign-off.

| Lane | Source | Empty-state copy |
|---|---|---|
| **Patients ready for workup** | `work_queue_items WHERE queue_type = 'tech_workup' AND status = 'open' AND location_id = caller.location` | "No patients waiting for workup at this location." |
| **VA / IOP / refraction / dilation checklist** | per-encounter checklist surface; reads from `extracted_findings` for current values | "No measurements recorded yet for this encounter." |
| **Imaging needed** | `work_queue_items WHERE queue_type = 'imaging_upload_pending'` joined with [imaging_studies](./chartnav-imaging-pipeline-plan.md) when present | "No imaging requested for this encounter." |
| **Testing queue** | `work_queue_items WHERE queue_type = 'dilation_recheck' OR specialty test queue` | "No post-dilation rechecks pending." |
| **Room / location assignment** | future `location_rooms` (multi-clinic plan) | "No room assigned. (Room management ships in Phase 22.)" |
| **Handoff to doctor** | promotion action: tech marks workup complete → creates `md_ready` queue item for the assigned MD | — |

**Hard guardrails:**
- ❌ No autofill of VA / IOP / refraction / cup-to-disc — the
  technician enters measurements; ChartNav surfaces them
- ❌ No automatic imaging order creation from the tech checklist
- ❌ No clinical interpretation of measurements (e.g., no "IOP
  elevated, alert" auto-flag without provider review)

## Doctor Dashboard

**What this role owns:** the MD encounter — chart review,
exam, OD/OS retinal canvas, dictation, draft, signature.
**What this role already has:** the 9-tab `ClinicalTabbedWorkspace`.
The dashboard is the **outside view** that lets the doctor pick
which encounter to work on next.

| Lane | Source | Empty-state copy |
|---|---|---|
| **Patients ready for MD** | `work_queue_items WHERE queue_type = 'md_ready' AND assigned_user_id = caller.user_id (or unassigned in caller.location)` | "No patients ready to be seen at this location." |
| **Pre-visit brief** | existing `PreVisitBriefPanel` per encounter | (existing copy) |
| **Imaging ready** | `imaging_studies WHERE reviewed_at IS NULL AND patient.assigned_provider = caller` | "No imaging awaiting MD review." |
| **High-priority alerts** | `work_queue_items WHERE priority = 'urgent' AND assigned_user_id = caller` | "No urgent items in your queue." |
| **Documentation status** | `note_versions WHERE encounter.provider = caller AND status IN ('draft', 'review_needed')` | "All notes are signed or in review." |
| **Sign-off queue** | `note_versions WHERE encounter.provider = caller AND status = 'draft_ready'` | "Nothing waiting for your signature." |
| **Clinical shortcuts / favorites** | existing `clinician_shortcut_favorites` chips | (existing copy) |

**Hard guardrails:**
- ❌ No automatic diagnosis / no automatic order generation /
  no automatic referral generation from the dashboard
- ✅ Every alert must be a provider-review prompt, never a
  prescriptive directive
- ✅ Pre-visit brief, action items, summaries remain
  provider-reviewed before any patient-facing artifact

## Reviewer Dashboard

**What this role owns:** clearing the review queue — notes
awaiting reviewer signature, AI draft review, retinal-diagram
proposal review, audit-safe exception handling. The existing
reviewer role can already sign note versions and perform
status transitions; this dashboard surfaces the queue at a
glance.

| Lane | Source | Empty-state copy |
|---|---|---|
| **Notes awaiting review** | `note_versions WHERE status = 'review_needed'` | "Review queue is empty." |
| **AI draft review** | `note_versions WHERE generated_by IN ('ai', 'ai_draft') AND human_reviewed = false` (joins with `ai_governance_log.human_review_status`) | "No AI drafts awaiting human review." |
| **Diagram proposal review** | `chart_artifacts` with unresolved AI proposals from `retinal_proposals` (currently a stateless API; Phase 21A connects it to a queue) | "No retinal-diagram proposals awaiting review." |
| **Audit-safe exceptions** | `security_audit_events WHERE error_code IN ('cross_org_access_forbidden', 'role_forbidden') AND organization_id = caller.org` | "No security exceptions in the past 24 hours." |
| **Review-needed queue** | `work_queue_items WHERE queue_type = 'note_review' AND status = 'open'` | "No review tasks open." |

**Hard guardrails:**
- ❌ No bulk auto-approval of AI drafts
- ❌ No automatic diagnostic assertion
- ✅ Every reviewer action is logged in `ai_governance_log` (for
  AI-derived rows) and `security_audit_events` (for access)
- ✅ Reviewer signature on a `note_version` remains a single
  explicit action, not bulk

## Admin Dashboard

**What this role owns:** cross-location operational visibility,
provider load balancing, sign-off backlog, imaging backlog,
review-queue aging, multi-location summary. Existing
`/admin/deployment/*` endpoints are infrastructure-level
(deployment manifest, jobs, alerts) — this dashboard is
**clinical-operations-level**.

| Lane | Source | Empty-state copy |
|---|---|---|
| **Location throughput** | aggregated `encounters` count by `location_id` and `status` | "No encounters in selected window." |
| **Provider load** | aggregated `encounters` count by `provider_id` and `status` | "No active providers in selected window." |
| **Unsigned notes** | `note_versions WHERE status IN ('draft_ready', 'review_needed') AND age > 24h` | "All notes signed within target window." |
| **Imaging backlog** | `imaging_studies WHERE reviewed_at IS NULL AND age > 24h` | "No imaging backlog." |
| **Review queue aging** | `work_queue_items WHERE queue_type = 'note_review' AND age > sla_minutes` | "No queue items past SLA." |
| **Multi-location summary** | rollups by location | "Single-location org." |

**Hard guardrails:**
- ❌ No automatic clinician productivity scoring beyond raw
  counts (no efficiency rankings, no algorithmic
  performance evaluation)
- ❌ No PHI in the aggregate views — admin sees encounter
  counts, not patient lists by default; drill-down respects
  role permissions
- ✅ Every drill-down enforces `ensure_same_org` + role check
- ✅ Audit row written for every cross-location read

## Filter affordances

Every dashboard supports two filters layered on the role-based
defaults:

- **Location filter** — `location_id IN (caller.allowed_locations)`. Defaults to caller's primary location.
- **Provider filter** — `provider_id = caller.user_id` (clinician), `assigned_user_id = caller.user_id` (technician/reviewer), or `IN admin.location.providers` (admin).

These read from `provider_location_assignments` (when the
[multi-clinic plan](./chartnav-multi-clinic-scaling-plan.md)
ships) — until then they degrade to `caller.organization_id`
scope.

## Saved views (`role_view_presets`)

Each role can save filter + column combinations:

| Role | Example presets |
|---|---|
| Front desk | "Today's schedule" (default) · "Awaiting checkout" · "Pending recalls (7d)" |
| Technician | "Workup queue" (default) · "Awaiting dilation" · "Imaging requested" |
| Doctor | "Today's MD-ready" (default) · "Sign-off backlog" · "Imaging awaiting review" |
| Reviewer | "Review queue" (default) · "AI drafts" · "Diagram proposals" |
| Admin | "Today's throughput" (default) · "Imaging backlog (24h)" · "Sign-off lag (24h)" · "Multi-location summary" |

## What this plan deliberately does not propose

- ❌ **No** automatic patient messaging from any dashboard. Every
  patient-facing communication remains a human action.
- ❌ **No** automatic order generation. Imaging requests, lab
  requests, referrals are surfaced as **review prompts** only.
- ❌ **No** autonomous diagnosis flags. "High-priority alerts" are
  provider-defined queue rules, not algorithmic diagnosis.
- ❌ **No** automatic clinical-decision assertions. The dashboards
  surface state; clinicians decide.
- ❌ **No** automatic IOP / VA / refraction autofill from device imports.
- ❌ **No** automatic billing or coding triggered by dashboard
  actions.

## Where this fits in the existing UI

| Existing surface | Role-dashboard relationship |
|---|---|
| `App.tsx` sidebar (Phase 19F: CORE / CLINICAL / OPERATIONS / ADMIN groups) | The **CORE → Dashboard** entry (currently disabled placeholder) becomes the role-dispatched dashboard route |
| `ClinicalTabbedWorkspace.tsx` (the 9-tab encounter workspace) | Unchanged. Dashboards link **into** it on encounter selection. |
| Phase 19I Chat tab | Unchanged. Internal staff handoff stays where it is. |
| Phase 19F sidebar OPERATIONS group (Tasks · Messages · Chat) | The **Tasks** entry (currently disabled placeholder) becomes the role-filtered work_queue_items view |

## Required tests

- Each dashboard renders the right lanes for the caller's role
- Front-desk role cannot read clinical chart bodies (only operational metadata)
- Technician role cannot sign note versions
- Doctor role sees only their own assigned MD-ready queue by default
- Reviewer role sees the full org review queue (existing behavior)
- Admin role sees cross-location aggregates but every drill-down respects RBAC
- Saved views (`role_view_presets`) are per-org + per-role isolated
- No PHI ever appears in aggregated admin counts
- Every dashboard action emits a `security_audit_events` row when relevant

## Implementation sequence (handoff to roadmap)

This plan assumes the structured data layer ships first
(Phase 20B). Phase 20C builds the dashboards on top. See
[`chartnav-phase-20-22-implementation-roadmap.md`](./chartnav-phase-20-22-implementation-roadmap.md)
for full sequencing.
