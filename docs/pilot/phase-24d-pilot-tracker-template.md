# Phase 24D — Pilot Tracker Template

> **Phase:** 24D — Pilot Practice Selection & Outreach Packaging.
> **Audience:** founder / sales engineer running the first-wave
> ophthalmology pilot pipeline.
> **Companion docs:**
> `phase-24d-pilot-practice-selection-criteria.md`
> `phase-24d-pilot-discovery-call-script.md`
> `phase-24d-pilot-fit-scorecard.md`

This is the pipeline tracker template. Copy the table into the
team's pipeline tool of choice (Notion, Airtable, Google Sheet,
Linear — any tool that supports tabular columns and free-text
notes) and keep one row per candidate practice.

**Do not store any real PHI in this tracker.** It is a sales /
operations record, not a clinical record. Fields below are
operator-facing only.

---

## Column definitions

| Column | Type | Description |
|---|---|---|
| `practice_name` | string | Practice display name. |
| `specialty_mix` | string | Free text — "retina-heavy / mixed ophth / glaucoma + retina / cataract + general." Match to §3 segments in the selection-criteria doc. |
| `locations` | integer | Number of practice locations. |
| `providers` | integer | Total provider count (MDs + ODs across all locations). |
| `contact_name` | string | Primary contact at the practice. |
| `contact_role` | string | "administrator" / "retina physician" / "ops director" / "IT" / "other." |
| `warm_or_cold` | enum | `warm` (mutual intro) / `cold` (no prior relationship). |
| `source` | string | Mutual connection name, conference, referral channel, etc. |
| `pain_score` | string | The seven `1–5` pain scores from the discovery script (§3): doc-lag / imaging / tech-handoff / follow-up / internal-comm / multi-provider / security-readiness. Format: "3/4/4/5/3/2/3". |
| `security_readiness` | enum | `unknown` / `not yet` / `in progress` / `ready` — based on whether the gatekeeper is identified and willing to run review. |
| `demo_scheduled` | enum | `no` / `yes — [date]` / `cancelled` / `rescheduled`. |
| `demo_completed` | enum | `no` / `yes — [date]`. |
| `objections` | free text | New / repeat objections heard. Map to the cheat sheet entry where possible. Append, do not overwrite. |
| `next_step` | string | Single short next action. "Send security packet" / "Schedule 2nd demo" / "Decline politely" / etc. |
| `pilot_fit_score` | integer | Most recent score from `phase-24d-pilot-fit-scorecard.md` (0–30). |
| `status` | enum | See "Status values" below. |
| `owner` | string | Internal owner for this row (name or team alias). |
| `last_touch` | ISO date | Most recent outbound or inbound contact. Update on every action. |
| `notes` | free text | Operator memory. No PHI. |

---

## Status values

| Status | Meaning |
|---|---|
| `target` | Identified but not yet contacted. |
| `contacted` | First outreach sent; awaiting reply. |
| `replied` | Practice has replied; discovery not yet scheduled. |
| `discovery scheduled` | First call on the calendar. |
| `demo scheduled` | 30-minute fake-data demo on the calendar. |
| `demo completed` | Demo done; awaiting next step. |
| `security review` | Security packet sent; awaiting gatekeeper response or sitting in IT review. |
| `pilot candidate` | Scored ≥ 24 / 30 and ready to enter the controlled-pilot path. |
| `nurture` | Real fit but timing is wrong. Re-touch on a 60–90 day cadence. |
| `not fit` | Politely declined per the selection-criteria forbidden-list or low score. |
| `closed lost` | Was a candidate; engaged then went cold or declined after demo. |

A row never goes back from `closed lost` → `pilot candidate` in
the same calendar quarter without a fresh discovery call (the
context is stale; the pain may have shifted).

---

## Tracker table (copy into your tool)

| practice_name | specialty_mix | locations | providers | contact_name | contact_role | warm_or_cold | source | pain_score | security_readiness | demo_scheduled | demo_completed | objections | next_step | pilot_fit_score | status | owner | last_touch | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| _example: Demo Eye Clinic (synthetic)_ | retina-heavy / mixed ophth | 1 | 4 | _example: A. Admin_ | administrator | warm | _example: founder intro_ | 3/4/4/5/3/2/3 | in progress | yes — 2026-06-01 | no | "Wanted to know if it auto-grades DR — answered no." | "Send security packet to IT director" | 25 | demo scheduled | _example: founder_ | 2026-05-13 | "Strong fit; champion is the retina lead." |
| | | | | | | | | | | | | | | | | | | |
| | | | | | | | | | | | | | | | | | | |
| | | | | | | | | | | | | | | | | | | |
| | | | | | | | | | | | | | | | | | | |

> The synthetic example row uses `demo-eye-clinic` and a
> placeholder admin name. It is for table-shape illustration
> only — replace before sharing the tracker with anyone outside
> the team.

---

## Operating rules

1. **No PHI.** Practice contact info (name, work email, work
   phone) is fine. Patient data is not. Do not log dashboard
   counts from a customer environment in this file; capture
   those in the operator-only debrief notes.
2. **One owner per row.** Multi-owner rows go stale fastest.
3. **Update `last_touch` on every action.** A row with a stale
   `last_touch` (> 14 days) on `contacted` status auto-rolls
   to `nurture` unless the owner explicitly defends it.
4. **Score after every meaningful interaction.** Discovery →
   score. Demo → re-score. Security review → re-score.
   Pilot-fit scores move; capture the latest.
5. **Forbidden-list disqualifiers override scores.** A practice
   that demands autonomous diagnosis, automatic billing, real
   PHI on day one without security review, or device
   integration as a hard day-one requirement does not get into
   `pilot candidate` regardless of score.
6. **`closed lost` is not a failure marker.** It is data. Log
   the reason in `notes` so the next outreach wave benefits.
7. **No exporting to public channels.** This tracker is
   internal-only. Even with no PHI, practice names and pain
   scores should not leave the team.

---

## Suggested cadence

- **Daily (during outreach waves):** review rows in `target` /
  `contacted` / `replied`. Send the next message from
  `phase-24d-pilot-outreach-message-bank.md`. Update
  `last_touch`.
- **Weekly:** review rows in `discovery scheduled` / `demo
  scheduled` / `demo completed`. Confirm next steps are
  scheduled and the right artifact has been sent
  (`chartnav-security-review-packet.md`, etc.).
- **Monthly:** sweep `nurture` rows. Re-score any that have a
  new conversation worth recording; archive the rest with
  `closed lost` + a reason.
- **Quarterly:** retire `closed lost` rows from the active
  table (move to an archive worksheet / table). Refresh the
  team on objection patterns by reviewing the appended notes
  against `phase-24d-pilot-objection-cheat-sheet.md`.

## References

- `phase-24d-pilot-practice-selection-criteria.md`
- `phase-24d-pilot-outreach-message-bank.md`
- `phase-24d-pilot-discovery-call-script.md`
- `phase-24d-demo-invite-and-agenda.md`
- `phase-24d-post-demo-follow-up-template.md`
- `phase-24d-pilot-fit-scorecard.md`
- `phase-24d-pilot-objection-cheat-sheet.md`
- `chartnav-pilot-readiness-checklist.md`
- `chartnav-security-review-packet.md`
- `chartnav-controlled-pilot-go-live-checklist.md`
- `docs/security/chartnav-real-phi-go-live-gate.md`
