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
3. Open `http://127.0.0.1:5173` in a clean browser window.
4. Confirm the identity badge shows `admin@chartnav.local · org 1`.
   (If not, use the identity selector to pick that user.)

---

## 5-minute click path

### Step 0 · Open the demo workflow guide

| # | Action |
|---|--------|
| 0.1 | Click `enc-row-1` in the encounter list to open Morgan Lee's encounter. |
| 0.2 | Wait for the workspace to load (`note-workspace` mounts). |
| 0.3 | Scroll down past the transcript / findings / draft tiers to the **Demo workflow guide** section. |
| 0.4 | Click the *Show demo workflow guide* button. The seven-step checklist expands. |

Speaking cue: *"Every panel below is provider-reviewed. The guide tells you what we'll click."*

### Step 1 · Scribe session lifecycle

| # | Action |
|---|--------|
| 1.1 | Scroll to the **Scribe session** panel. |
| 1.2 | Paste the sample source text from the demo script into the *Source text* textarea. |
| 1.3 | Click *Create session*. The session appears as a draft. |
| 1.4 | Click *Process*. The structured note appears. |
| 1.5 | Click *Mark reviewed*. The session moves to `reviewed`. |
| 1.6 | Click *Finalize*. The session moves to `finalized` and the panel switches to read-only. |

Speaking cue: *"Provider review is mandatory. Finalize is explicit."*

### Step 2 · Retinal diagram proposals

| # | Action |
|---|--------|
| 2.1 | Scroll to the **Eye diagram** panel. |
| 2.2 | If there's no draft artifact, click *New diagram*. |
| 2.3 | Paste the relevant findings text into the *Findings* textarea. |
| 2.4 | Click *Generate proposals from findings*. |
| 2.5 | Review the proposed annotations modal. Click *Apply* on one OD or OS proposal. |

Speaking cue: *"Proposals are read-only suggestions. Anything that lands on the diagram is tagged source=ai_approved."*

### Step 3 · Sign the diagram

| # | Action |
|---|--------|
| 3.1 | In the same Eye diagram panel, click *Save*. |
| 3.2 | Click *Sign*. The artifact moves to signed; the panel switches to read-only. |

Speaking cue: *"Signed artifacts are immutable in place. Edits create an explicit fork."*

### Step 4 · Patient-friendly summary

| # | Action |
|---|--------|
| 4.1 | Scroll to the **Patient summary** panel. |
| 4.2 | Click *Create from finalized scribe* (or paste a scribe session id). |
| 4.3 | Edit the plain-language draft if you want to demonstrate provider control. |
| 4.4 | Click *Mark reviewed*. |
| 4.5 | Click *Finalize*. |

Speaking cue: *"Provider review required. Do not send to patient until finalized — and we never send automatically."*

### Step 5 · Pre-visit brief

| # | Action |
|---|--------|
| 5.1 | Scroll to the **Pre-visit brief** panel. |
| 5.2 | Click *Generate*. |
| 5.3 | Show the source-counts tiles, the last-visit recap, and the data-gaps list. |

Speaking cue: *"Source counts > 0 across scribe / summary / signed artifact. The gap list is explicit."*

### Step 6 · Provider action queue

| # | Action |
|---|--------|
| 6.1 | Scroll to the **Provider action queue** panel. |
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
