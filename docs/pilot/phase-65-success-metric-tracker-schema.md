# Phase 65 Pilot Success Metric Tracker Schema

Status: tracker schema
Audience: pilot owner, practice champion, operations reviewer

Use this schema in a spreadsheet or private tracker. Do not store real
PHI in the repo. Track operational workflow signals only.

## Tracker Columns

| Column | Type | Required | Notes |
| --- | --- | --- | --- |
| week_start | date | yes | Monday of pilot week |
| practice_code | text | yes | Use internal code, not patient info |
| pilot_phase | enum | yes | onboarding, monitored_use, paused, exit_review |
| active_users | integer | yes | Count only |
| sessions_attempted | integer | yes | Count only |
| sessions_completed | integer | yes | Count only |
| failed_workflow_attempts | integer | yes | Count save/generate/review/sign failures |
| operator_interventions | integer | yes | Count support assists |
| s1_issues | integer | yes | Any nonzero value triggers stop/review |
| s2_issues | integer | yes | Workflow blockers |
| s3_s4_issues | integer | no | Friction/docs/cosmetic |
| intake_completeness_rate | percent | no | Operational completeness only |
| draft_usefulness_score | number 1-5 | no | Provider rating, not clinical outcome |
| provider_review_burden_score | number 1-5 | no | Lower burden is better; define scale |
| fundus_completeness_score | number 1-5 | no | Drawing completeness after provider review |
| handoff_clarity_score | number 1-5 | no | Staff-reported workflow clarity |
| safety_boundary_near_misses | integer | yes | Demo/real-PHI mixup, forbidden workflow attempt, wrong environment |
| top_friction | text | no | No patient data |
| mitigation_owner | text | no | Internal owner |
| next_action | text | yes | Continue, pause, repair, exit review |

## Metrics Rules

- Do not track clinical outcomes.
- Do not track diagnoses.
- Do not track revenue or guaranteed ROI.
- Do not include patient identifiers.
- Do not paste note text, transcript text, vitals values, or fundus
  findings.
- Use counts, ratings, and workflow observations.

## Minimum Weekly Review

Each week, answer:

- Did any S1 occur?
- Did any S2 remain open at week end?
- Did users complete the scoped workflows?
- Did review/sign/attestation remain intact?
- Did any user request a prohibited workflow?
- Did the practice ask for a scope change?
- Are success metrics trending in a direction the practice values?

## Go / Pause Rules

Continue only if:

- S1 count is zero.
- Open S2 issues are either zero or have accepted workarounds.
- Safety-boundary near misses are reviewed and resolved.
- Practice champion agrees the pilot remains useful.

Pause if:

- Any S1 is open.
- Repeated S2 blocks review/sign.
- Users cannot distinguish demo/fake-data mode from pilot mode.
- Any prohibited workflow becomes a requirement.
