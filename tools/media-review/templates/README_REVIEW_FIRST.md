# ChartNav Media Review — Phase 19G

> **Read this first.** This folder is staged for Jean-Max's
> visual approval of the post-Phase-19F demo UI before any
> final-delivery folder is overwritten and before any
> chartnavmd.com content is replaced. **Nothing here is
> published yet.**

## Status snapshot

| Item | State |
|---|---|
| Latest main commit at capture time | `50dc86a` (Phase 19F merge) |
| Final-delivery folder | **NOT overwritten** in this phase |
| Live chartnavmd.com | **NOT updated** in this phase |
| Legacy Desktop folders | **NOT deleted** in this phase |
| Real PHI used anywhere | **No** — fake/demo seed data only |
| Repo | nothing committed under this folder; screenshots / videos live on Desktop only |

## What changed in the UI vs the previous capture

Phase 19F is the post-billing-removal final clinical demo UI. Vs.
the previous capture you should see:

- **Exactly 9 tabs** in the workspace tab bar — no Billing.
  Order: Overview · Clinical / Ophthalmology · Documentation /
  EMR/EHR · Imaging · Labs / Orders Review · Calendar ·
  Communications · Documents · **Chat**.
- **No Billing item** in the sidebar ADMIN group. ADMIN now
  reads Documents · Reports · Settings.
- **No Send Message** in Quick Actions. Quick Actions now reads
  New Encounter · Record Dictation · Upload Imaging · Internal
  Chat Note.
- **Chat** moved into the OPERATIONS sidebar group alongside
  Tasks · Messages.
- **Patient header demographic strip** uses intentional
  empty-state copy ("Not available in demo" / "No allergies
  recorded" / "No active meds recorded" / "Not scheduled")
  instead of bare em-dashes.
- **Burgundy sidebar** with teal active stripe (Phase 19E),
  red micro-accent on the patient header, subtle red-tinted
  hover shadow on cards.
- **Timeline** + **Add timeline event** composer live inside
  the Overview tab's Timeline card. The composer is hidden in
  `?demo=1` mode (a "demo-hidden" notice replaces it; the
  read-only timeline still renders).
- **No Billing / CPT / Charges / Insurance / Submit Claim /
  Auto-code / Auto-bill / Send Claim / Charge Patient / Bill
  Insurance / Payment / Claim** vocabulary anywhere in
  rendered UI.
- **No Submit Order / Place Order / Send Referral / Send to
  Patient / Patient Portal** interactive controls anywhere.

## Review order

Walk the folder in this exact order:

1. **`01_Screenshots/`** — 12 PNGs of the Phase 19F UI.
   Confirm tabs, sidebar, demographic strip, burgundy palette,
   intentional empty states.
2. **`02_Website_Selected/`** — the 5 best screenshots
   pre-named for chartnavmd.com use.
3. **`03_Website_Video_Clips/`** — 6 short MP4 clips for
   chartnavmd.com. **Capture is manual** — see
   `CLIP_CAPTURE_INSTRUCTIONS/` for exact recording steps.
4. **`04_Demo_Clip_Instructions/`** — sales/demo clip runbook
   (separate from the website clips).
5. **`06_Manifest/media_manifest.md`** — every file in this
   folder, intended placement, and a default `Approved? No`
   column for sign-off.
6. **`07_Ready_For_ChartNavMD_After_Approval/`** — staging
   area. Files copied here are queued for chartnavmd.com
   replacement **only after explicit approval**; the live
   site is not touched until Jean-Max sign-off.

## Approval workflow

1. Walk the folders above.
2. Mark each row in `06_Manifest/media_manifest.md`
   `Approved? = Yes / No / Reshoot` with notes.
3. For approved rows that are flagged for chartnavmd.com,
   confirm the file is also in `07_Ready_For_ChartNavMD_After_Approval/`.
4. Hand back: "approved — proceed to delivery overwrite" OR
   "reshoot the following: …".

## Hard guardrails preserved

- No real PHI; fake/demo seed only.
- Final-delivery folder untouched.
- chartnavmd.com untouched.
- Legacy Desktop folders untouched (still available as the
  fallback baseline if a reshoot is needed).
- No screenshots / videos committed to the repo.
- Phase 17B / 18 / 19 / 19B / 19F safe-claims contract intact.
- Phase 17D `--cn-primary` token-sync intact.
- Phase 19E burgundy + teal + red brand accents intact.
- Phase 19F billing-surface absence intact.

If any screenshot contradicts any of the above, flag it on
`06_Manifest/media_manifest.md` and stop — do not proceed to
website replacement until the divergence is resolved.
