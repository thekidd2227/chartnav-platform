# ChartNav Phase 19J — Final Review Guide

> **What this is:** the human-facing review pack for Phase 19J. Everything below
> is reproducible from a fresh clone. No production publishing required to review.

## TL;DR

| | |
|---|---|
| Branch | `feature/phase-19j-reference-layout-replica` |
| PR | [#28](https://github.com/thekidd2227/chartnav-platform/pull/28) (Draft) |
| Status | Ready for human visual + code review. **Do not merge yet.** |
| Production | `https://chartnavmd.com` already serves the Phase 19J UI + 11 refreshed clips. |

## Repos in scope

| Repo | Path on this Mac | Role |
|---|---|---|
| `thekidd2227/chartnav-platform` | `~/Desktop/ARCG/chartnav-platform` | Demo workspace SPA + API + chartnavmd-site source. PR #28 lives here. |
| `thekidd2227/website` | `~/arcg-live` | `arcgsystems.com` — `/chartnav` is a 301 → chartnavmd.com redirect. |
| Vercel project `chartnavmd-site` | (no local clone needed for review) | Serves `chartnavmd.com`. |

## Startup — local

### 1. API (FastAPI, port 8765)
```bash
cd ~/Desktop/ARCG/chartnav-platform/apps/api
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8765 --log-level warning
```

### 2. Seed the demo DB (idempotent)
```bash
cd ~/Desktop/ARCG/chartnav-platform/apps/api
.venv/bin/python -c "import scripts_seed; scripts_seed.main()"
```

### 3. Web (Vite, port 5173)
```bash
cd ~/Desktop/ARCG/chartnav-platform/apps/web
VITE_API_URL=http://127.0.0.1:8765 npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

### 4. Open the workspace
- `http://127.0.0.1:5173/` → encounter list pre-populated (Jordan Rivera + Morgan Lee).
- Click any encounter row → workspace opens with all 9 tabs.
- Demo identity: `clin@chartnav.local` (defaults to admin if unset). Switch via the IdentityPicker top-right.

## Startup — chartnavmd-site (static)

The static-HTML source lives at:
```
~/Desktop/ARCG/chartnav-platform/apps/web/chartnavmd-site/
```

Local preview (no build step — pure static):
```bash
cd ~/Desktop/ARCG/chartnav-platform/apps/web/chartnavmd-site
python3 -m http.server 8801 --bind 127.0.0.1
# → http://127.0.0.1:8801/
```

Production deploy (operator-only, requires Vercel CLI auth):
```bash
cd ~/Desktop/ARCG/chartnav-platform/apps/web/chartnavmd-site
vercel deploy --prod --yes --scope jeanmaxcharles-3486s-projects
```

## Startup — arcgsystems.com (GitHub Pages)

```bash
cd ~/arcg-live
npm install   # if not yet done
npm run dev   # vite dev server, typically port 5173
```

Production: pushes to `main` deploy automatically via the GitHub Pages action
in `.github/workflows/`. The `/chartnav` route is a redirect — do not invest
visual review there; review on `chartnavmd.com` instead.

## Required env

| Variable | Where | Purpose |
|---|---|---|
| `VITE_API_URL` | web dev server | Defaults to `http://localhost:8000`; we override to `127.0.0.1:8765`. |
| `DATABASE_URL` | api | Defaults to local SQLite `apps/api/chartnav.db`. |
| `VITE_CHARTNAV_LEAD_WEBHOOK` | arcg-live build | Optional, lead-form webhook. Demo OK without it. |

## Where the screenshots / videos live

| Artifact | Location | Tracked? |
|---|---|---|
| 10 review PNGs (5 tabs × 2 viewports) | `qa/screenshots/phase-19j-review/` | ✅ committed in PR #28 |
| Same 10 PNGs, operator-side | `~/Desktop/Chartnav/ChartNav_Media_Review_Final_UI/01_Screenshots/` | ❌ local only |
| `phase-19j-demo.mp4` (1.0 MB workspace tour) | `apps/web/chartnavmd-site/videos/phase-19j-demo.mp4` | ✅ committed |
| `phase-19j-demo.mp4` website mirror | `~/arcg-live/public/chartnav/videos/phase-19j-demo.mp4` | ✅ committed in arcg-live commit `55f47a6` |
| Same on Desktop | `~/Desktop/Chartnav/ChartNav_Media_Review_Final_UI/03_Website_Video_Clips/` | ❌ local only |
| 10 refreshed showcase clips | `apps/web/chartnavmd-site/videos/*.mp4` and `.../chartnav/videos/*.mp4` | ✅ committed in PR #28 |

## How to verify media locally

1. Open the local chartnavmd-site at `http://127.0.0.1:8801/`.
2. Confirm the showcase opens with the Phase 19J workspace tour (`Workspace tour` tag, `The new ChartNav workspace, end to end`).
3. Click `›` in the showcase to advance through clips 2–11. Each one should show the redesigned Phase 19J UI (burgundy sidebar, white cards, teal active accents). None should show legacy UI.
4. On mobile (or DevTools mobile emulation): clips honor `playsinline` + `muted` so they play inline without fullscreen.

## Production verification (already done)

- `chartnavmd.com` → deploy `dpl_65mw8m39GCskNXqEeC6HDdAohvZG` is live.
- All 11 clip URLs return HTTP 200 with the new content-length sizes.
- `/videos/manifest.json` matches the inline manifest in `index.html`.

## Human Review Checklist

### Visual review (against the reference layout)
- [ ] Sidebar: 240 px, deep burgundy, groups CORE / OPERATIONS / CLINICAL / ADMIN / Quick Actions.
- [ ] Sidebar active row carries the 3 px teal `#14b8a6` left stripe.
- [ ] Top header: white, ~52–56 px, search pill centered, identity right.
- [ ] Patient header: name + DOB + MRN + Phone left, Encounter # + status pill + Provider + Location right.
- [ ] Demographic strip: single bordered white row (Gender / Allergies / Conditions / Medications / Last Visit / Next Appt / Provider).
- [ ] Tab bar: 9 tabs visible at 1440 px without scroll.
- [ ] Overview: 4-up row 1 → 4-up row 2 → full-width Timeline.
- [ ] Favorites card: 5 protocol templates listed.
- [ ] Chat tab: recipient selector with role + presence; placeholder updates by recipient.

### Safety review
- [ ] No `Billing`, `CPT`, `Charges`, `Claim`, `Payment`, `Insurance` in visible UI.
- [ ] No `Send to Patient`, no `Place Order`, no `Submit Order`, no `Send Referral`.
- [ ] No autonomous-diagnosis claims; provider-reviewed language present.
- [ ] No `certified EHR` or `HIPAA-compliant` strings (only review-only / review-aware language).
- [ ] No `Chartie` / `Charlie` anywhere.
- [ ] No `localhost:8000` or API URL chip visible during demo (`?demo=1`).

### Showcase clips (chartnavmd.com)
- [ ] All 11 clips show Phase 19J UI (no legacy art).
- [ ] Captions in the showcase describe what's actually in each clip.
- [ ] Auto-rotation cycles through all 11.
- [ ] Manual prev/next nav works.

## Visual QA Checklist (per tab)

| Tab | Expect |
|---|---|
| Overview | 4×3 grid, no broken cards, Timeline spans full width row 3, Favorites lists 5 templates. |
| Clinical / Ophthalmology | Search input + 5 specialty groups (Retina / Cornea / Glaucoma / Oculoplastics / General) + Favorites pinned first. Provider-reviewed footnote. |
| Documentation / EMR/EHR | Stepper (Transcript → Extracted Facts → AI Draft → Final Note) over the embedded NoteWorkspace. |
| Imaging | Upload Imaging / OCT Images / Fundus Photos / Attachments / Imaging Notes / Selected Image Viewer + OD/OS retinal workbench full-width below. |
| Labs / Orders Review | 4 review-only cards (Lab Results / Imaging Orders / Procedure Plan / Review Notes). Allowed actions: View / Mark reviewed / Add note. |
| Calendar | Read-only Scheduled / Started / Completed timestamps + Provider / Location. |
| Communications | Internal staff notes only. Composer + log + history. No patient-send surface. |
| Documents | Local document index with file picker. |
| Chat | Recipient selector (Carter / Patel / Admin / Reviewer). Composer placeholder updates per recipient. Export `.txt` / `.json` / Clear thread. Banner: "Demo-local internal chat — do not enter real PHI." |

## Known non-blocking issues

1. **Header search + Notification / Help / Security icons** are static placeholders (disabled buttons + read-only input). Wiring is intentionally deferred — no backend in scope for this phase.
2. **Pre-existing 69 `vitest` failures** (jsdom localStorage shim issue: `window.localStorage.clear is not a function`). They pre-date this PR, are unrelated to Phase 19J, and live in `ClinicalTabbedWorkspace.test.tsx` + `GuidedDemoMode.test.tsx`. The 20-test `App.test.tsx` suite — which exercises the sidebar contract — passes 100%.
3. **Sidebar pane widens to 360 px below 1100 px viewport** (220 px sidebar + 280 px list). This is intentional graceful-degradation; reference target is desktop ≥1200 px.
4. **`apps/api/.venv/pyvenv.cfg` is permission-protected** in some sandbox environments. Direct bash (`uvicorn`) works; the Vercel `vercel dev` flow does not. Not a production blocker — production runs from CI builds.
5. **`videos/manifest.json` server-side file** lists only entries 0–6 (the new tour + 6 root-level workflow clips). The `/chartnav/videos/*` clips (Calendar / Sign-Off / Reminders / Handoff) appear in the inline `index.html` manifest only. Both are valid for the showcase; the JSON is for back-compat with older crawlers.

## Production deployment notes

- **chartnavmd.com**: Vercel project `chartnavmd-site`. Source-of-truth is `apps/web/chartnavmd-site/` in this repo. Deploy with `vercel deploy --prod` from that dir.
- **arcgsystems.com**: GitHub Pages, deployed automatically from `thekidd2227/website` `main` via `.github/workflows/`.
- **chartnav-platform** (the SPA + API): not yet deployed to a URL — runs locally only. Production deployment is a follow-up phase.

## Deferred items (for follow-up)

- Wire the header search input to a real patient/encounter/chart search.
- Wire the Notifications / Help / Security icon buttons.
- Patient-header reflow at narrow desktop (<1100 px) — currently flex-wraps acceptably.
- `vitest` baseline cleanup (the 69 pre-existing localStorage failures).
- chartnav-platform production deployment plan (not in this PR).

## Phases shipped under this PR

| Phase | Slice | Latest commit |
|---|---|---|
| 19J.A | Shell + visual system | `240416d` |
| 19J.B | Overview 4-up grid | `fa4ee0b` |
| 19J polish | Header icons + Favorites templates | `cd1c898` |
| 19J.C | 3-column shell + patient header reflow + density | `aa6d6dd` |
| 19J.D | Capture + Desktop folder + first clip swap | `234958b` + `e93f85d` |
| 19J.E | All 10 showcase clips refreshed on Phase 19J UI | `8eebf3f` |
| Final | Stabilization pass + this guide | (this commit) |
