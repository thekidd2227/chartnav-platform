# ChartNav Demo Click Path

Exact click sequence for the 5-minute demo. Pair with
`chartnav-clinical-workflow-demo-script.md` for spoken cues.

Assumes the local stack is running (`make boot` for the API,
`make web-dev` for the web; or `make dev` for both) with the seeded
demo data loaded (`make reset-db` runs both alembic + seed).

---

## Pre-demo checklist (run once)

1. `make reset-db` — drops and re-seeds the local SQLite dev DB.
2. `make boot` (or `make dev`) — boots the API on `:8000` and the
   web on `:5173`.
3. Open `http://127.0.0.1:5173/?demo=1` in a clean browser window.
   (`?demo=1` enables Guided Demo Mode AND hides the dev API URL
   chip — buyers never see `localhost:8000` on screen.)
4. Confirm the identity chip reads **Identity Admin · Org 1**.
   (Phase 19 — the visible chip is role + org; the email travels
   in the chip's `title` attribute. Hover to confirm
   `admin@chartnav.local`.) If the chip is wrong, use the identity
   selector or set `localStorage.chartnav.devIdentity` and
   refresh.

---

## Tab map (Phase 19F layout — 9 tabs, no Billing)

The encounter detail is a 9-tab clinical workspace. Two tabs
hold the demo content:

| Tab | What's inside | Which steps use it |
|---|---|---|
| **Documentation / EMR/EHR** | Scribe · Patient summary · Pre-visit brief · Provider action queue | Steps 0, 1, 4, 5, 6 |
| **Imaging** | OD/OS retinal diagram | Steps 2, 3 |

Other tabs (Overview · Clinical · Labs / Orders Review ·
Calendar · Communications · Documents · Chat) are not part
of the 5-minute click path. Skip them unless a buyer
specifically asks.

**Phase 19F notes:**
- *Labs / Orders Review* is review-only (View / Mark reviewed
  / Add note). ChartNav does not place lab / imaging /
  procedure orders.
- **Billing is intentionally absent.** ChartNav does not bill,
  code, submit claims, or handle insurance. The Chat tab covers
  internal staff comms; the Communications tab covers internal
  handoffs. CPT / Charges / Insurance / Submit Claim /
  Auto-code / Auto-bill / Send Claim / Charge Patient / Bill
  Insurance / Payment / Claim are forbidden as visible UI
  labels anywhere in the workspace.
- *Chat* remains a frontend-only internal staff thread (Phase
  19); data persists to localStorage on the operator's machine.
  The Chat tab is the buyer-visible replacement for the prior
  review-only Billing surface.

---

## 5-minute click path

### Step 0 · Open the demo workflow guide

| # | Action |
|---|--------|
| 0.1 | Click `enc-row-1` in the encounter list to open Morgan Lee's encounter. |
| 0.2 | Wait for the **clinical tabbed workspace** to load (`clinical-tabbed-workspace` mounts; the default active tab is **Overview**). |
| 0.3 | Click the **Documentation / EMR/EHR** tab so the scribe / summary / brief / action-items panels (`note-workspace`) mount. |
| 0.4 | Scroll past the transcript / findings / draft tiers to the **Demo workflow guide** section. |
| 0.5 | Click the *Show demo workflow guide* button. The seven-step checklist expands. |

Speaking cue: *"Every panel below is provider-reviewed. The guide tells you what we'll click."*

### Step 1 · Scribe session lifecycle

> Tab: **Documentation / EMR/EHR**

| # | Action |
|---|--------|
| 1.1 | (Already on Documentation tab from Step 0.) Scroll to the **Scribe session** panel. |
| 1.2 | Paste the sample source text from the demo script into the *Source text* textarea. |
| 1.3 | Click *Create session*. The session appears as a draft. |
| 1.4 | Click *Process*. The structured note appears. |
| 1.5 | Click *Mark reviewed*. The session moves to `reviewed`. |
| 1.6 | Click *Finalize*. The session moves to `finalized` and the panel switches to read-only. |

Speaking cue: *"Provider review is mandatory. Finalize is explicit."*

### Step 2 · Retinal diagram proposals

> Tab: **Imaging**

| # | Action |
|---|--------|
| 2.1 | Click the **Imaging** tab. The OD/OS retinal diagram panel mounts. |
| 2.2 | If there's no draft artifact, click *New diagram*. |
| 2.3 | Paste the relevant findings text into the *Findings* textarea. |
| 2.4 | Click *Generate proposals from findings*. |
| 2.5 | Review the proposed annotations modal. Click *Apply* on one OD or OS proposal. |

Speaking cue: *"Proposals are read-only suggestions. Anything that lands on the diagram is tagged source=ai_approved."*

### Step 3 · Sign the diagram

> Tab: **Imaging**

| # | Action |
|---|--------|
| 3.1 | (Still on Imaging tab.) In the Eye diagram panel, click *Save*. |
| 3.2 | Click *Sign*. The artifact moves to signed; the panel switches to read-only. |

Speaking cue: *"Signed artifacts are immutable in place. Edits create an explicit fork."*

### Step 4 · Patient-friendly summary

> Tab: **Documentation / EMR/EHR**

| # | Action |
|---|--------|
| 4.1 | Click the **Documentation / EMR/EHR** tab. Scroll to the **Patient summary** panel. |
| 4.2 | Click *Create from finalized scribe* (or paste a scribe session id). |
| 4.3 | Edit the plain-language draft if you want to demonstrate provider control. |
| 4.4 | Click *Mark reviewed*. |
| 4.5 | Click *Finalize*. |

Speaking cue: *"Provider review required. Do not send to patient until finalized — and we never send automatically."*

### Step 5 · Pre-visit brief

> Tab: **Documentation / EMR/EHR**

| # | Action |
|---|--------|
| 5.1 | (Still on Documentation tab.) Scroll to the **Pre-visit brief** panel. |
| 5.2 | Click *Generate*. |
| 5.3 | Show the source-counts tiles, the last-visit recap, and the data-gaps list. |

Speaking cue: *"Source counts > 0 across scribe / summary / signed artifact. The gap list is explicit."*

### Step 6 · Provider action queue

> Tab: **Documentation / EMR/EHR**

| # | Action |
|---|--------|
| 6.1 | (Still on Documentation tab.) Scroll to the **Provider action queue** panel. |
| 6.2 | Click *Generate*. |
| 6.3 | Pick one suggestion and click *Accept*. |
| 6.4 | Pick a different suggestion and click *Dismiss*. |
| 6.5 | On the accepted item, click *Complete*. |

Speaking cue: *"Suggested → accepted → completed; dismissed and completed are immutable. Every transition is the provider's explicit click."*

---

## Reset between demos

If you want a clean slate between back-to-back demos:

```
make reset-db
make seed
```

(`make reset-db` already runs seed — listed twice for clarity.)

This is safe to run repeatedly because the seed is idempotent.

---

## Common gotchas

- **Identity drift** — if the badge shows a different org, the
  workspace will look empty. Use the identity selector or set
  `localStorage.chartnav.devIdentity` and refresh.
- **Stale dev DB** — if a previous demo left finalized artifacts on
  PT-1001, run `make reset-db` to clear them.
- **Browser cache** — the demo guide is a small new component; if
  it doesn't appear, hard-refresh once.
- **Read-only panels surprise** — finalized scribe / summary / signed
  artifact / completed-or-dismissed action items are intentionally
  read-only. That's the contract — call it out as a feature, not a
  bug.

---

## Phase 21C addendum — ophthalmology specialty surfaces

Three new click paths land with Phase 20C / 21A / 21B. The
original click path above is still valid for the Phase 6 → 11
walkthrough. Use the steps below when the live demo includes
the ophthalmology-specialty surfaces.

### Path A — Role-based dashboards *(Phase 20C)*

1. Pick an identity in the header (`admin@chartnav.local`,
   `clin@chartnav.local`, `rev@chartnav.local`,
   `front@chartnav.local`, or `tech@chartnav.local`).
2. Sidebar → CORE → **Dashboard**.
3. The right pane renders the role-specific dashboard. For an
   admin identity, use the **View as** selector to switch
   between front desk / technician / doctor / reviewer / admin
   views. Non-admin identities see only their own role's
   dashboard.
4. Sidebar → CORE → **Encounters** to return to the encounter
   workspace.

### Path B — Retina + glaucoma specialty tracking *(Phase 21A)*

1. Open any patient whose encounter has a native patient row
   (the seeded `PT-1001 Morgan Lee` works).
2. Open the encounter workspace → **Clinical** tab.
3. The **Specialty Tracking** panel renders at the top of the
   Clinical tab.
4. Retina section: click **+ Add retina tracking** (clinician /
   admin only), or **Mark reviewed** on an existing card.
5. Retina injection history: click **+ Add injection event**
   (technician / clinician / admin).
6. Glaucoma section: similar pattern — tracking card, IOP
   measurements table, visual field tests table.
7. Reviewer identity: confirm the Add buttons are absent and
   each card shows the read-only banner.
8. Front desk identity: confirm the panel renders the blocked
   placeholder.

### Path C — Imaging pipeline *(Phase 21B)*

1. Same encounter workspace as Path B.
2. **Imaging** tab.
3. **Imaging Pipeline** panel renders at the top.
4. Click a study in the left-hand list. The right pane shows
   metadata, file table, measurements table, and a review
   workbench.
5. **Mark reviewed** is admin / clinician only. The technician
   identity does not see it; instead the workbench renders a
   read-only note.
6. **+ Add imaging study / + Add file metadata / + Add
   measurement** are available to admin / clinician /
   technician.
7. Reviewer and front desk see no Add buttons.
8. The OD/OS retinal workbench (`EyeDiagramPanel`) is unchanged
   and lives below the pipeline panel.

### Path D — Internal Chat *(existing surface)*

1. Encounter workspace → **Chat** tab.
2. Use the recipient selector to target a staff identity.
3. The pane is internal staff coordination only — there is no
   patient-facing message surface.
