# ChartNav Demo Environment (Phase 15)

How to boot, reset, and run the local stack for a sales-demo or
recording session. Pair with
`chartnav-demo-operator-guide.md` for the on-screen orchestration
(Guided Demo Mode + reset script) and
`chartnav-clinical-workflow-demo-script.md` for the spoken cues.

This environment is **fake-data only**. It is not a pilot
environment. It will refuse to ingest real PHI by construction —
see `docs/pilot/chartnav-pilot-deployment-guide.md`.

---

## Local startup

From the repo root:

```
make install         # one-time: creates the venv + installs deps
make web-install     # one-time: installs the frontend deps
make reset-db        # idempotent: alembic migrate + seed
make dev             # boots backend (:8000) + frontend (:5173) together
```

If `make dev` is too noisy in your shell, boot them separately:

```
make boot            # API on :8000
# in a second shell:
make web-dev         # web on :5173
```

Open the workspace at `http://127.0.0.1:5173/`. To enable Guided
Demo Mode for this session, append `?demo=1`:

```
http://127.0.0.1:5173/?demo=1
```

---

## Demo reset

Two levels of reset are supported.

### Stepper-only reset (no DB touch)

Click **Reset demo** in the Guided Demo Mode controls. The stepper
returns to Step 1; no clinical data is touched.

### Full demo reset (DB + browser state)

```
bash scripts/reset_demo_state.sh
```

What it does:

1. Refuses to run if `DATABASE_URL` is set to anything other than
   the local `sqlite:///<path>` default — the script is dev-only.
2. Runs `make reset-db` (alembic migrate + seed against the local
   dev SQLite).
3. Prints a short DevTools snippet for clearing browser-side demo
   state (`localStorage.removeItem("chartnav.demoStep")`,
   `chartnav.demoMode`, optionally `chartnav.devIdentity`).
4. Prints fake-demo-only reminders.

After the script runs, hard-refresh the browser to be safe.

---

## Seeded credentials

The seeded `demo-eye-clinic` org ships with three users:

| Email                       | Role        | Default password |
|-----------------------------|-------------|------------------|
| `admin@chartnav.local`      | `admin`     | n/a — dev auth   |
| `clin@chartnav.local`       | `clinician` | n/a — dev auth   |
| `rev@chartnav.local`        | `reviewer`  | n/a — dev auth   |

Local dev mode uses `CHARTNAV_AUTH_MODE=header` — there is no
password. The browser stores the active identity at
`localStorage.chartnav.devIdentity`. The identity selector in the
top bar lets you switch between seeded users.

A second seeded org (`northside-retina`) ships with
`admin@northside.local` and `clin@northside.local`. It is used for
cross-org integration tests; you can ignore it during a buyer
demo.

**Dev `header` auth is not safe for any environment that may hold
PHI.** See `docs/pilot/chartnav-pilot-deployment-guide.md`.

---

## Fake data structure

| Org slug             | Users                                                   | Patients                                                         | Encounters / events                              |
|----------------------|---------------------------------------------------------|------------------------------------------------------------------|--------------------------------------------------|
| `demo-eye-clinic`    | `admin@chartnav.local`, `clin@chartnav.local`, `rev@chartnav.local` | `PT-1001` (Morgan Lee), `PT-1002` (Jordan Rivera)               | 2 seeded encounters with workflow events         |
| `northside-retina`   | `admin@northside.local`, `clin@northside.local`         | `PT-2001` (Priya Shah)                                           | 1 seeded encounter                               |

All names, MRNs, DOBs, and NPIs are fake by construction. Source
text for the scribe paste is ad-hoc fake from the demo script. No
real patient data exists in this repo.

### Demo patient — Morgan Lee (PT-1001)

- Female, DOB `1962-03-14` (fake).
- Encounter status: `in_progress`.
- Provider: Dr. Carter (fake).
- Workflow events seeded: `encounter_created` →
  `status_changed` → `note_draft_requested`.

This is the patient the 5-minute and 10-minute demo scripts
target.

### Other fake patient — Jordan Rivera (PT-1002)

- Male, DOB `1954-11-02` (fake).
- Encounter status: `review_needed`.
- Provider: Dr. Patel (fake).
- Workflow events seeded with a fuller lifecycle.

Use Jordan if you want to demo the action queue or the pre-visit
brief against a chart that already has a finalized note draft.

---

## Deterministic workflow expectations

Guided Demo Mode is deterministic by design:

- The 8 steps render in a fixed order, with fixed labels and
  fixed cues.
- The stepper has no hidden timers and no animations.
- "Next step" / "Previous step" / "Reset demo" are the only state
  transitions; no other action moves the stepper.
- Step state lives in browser `localStorage` (`chartnav.demoStep`);
  there is no API call.

What the stepper does **not** do:

- It does not click clinical-panel buttons for you.
- It does not generate clinical artifacts.
- It does not modify any seeded data.
- It does not interact with real APIs or external services.

---

## Troubleshooting

| Symptom | First thing to try |
|---------|--------------------|
| `make boot` fails with "address already in use" | Another API is on `:8000`. Stop it or use `uvicorn --port 8001`. |
| `make web-dev` fails with "address already in use" | Another web server is on `:5173`. Stop it. |
| Workspace shows "Could not load …" banners | Confirm `:8000` answers `GET /health`. Boot the API. |
| Identity selector empty | Run `make seed`. The selector reads from the seeded `users` table. |
| Demo guide / Demo Mode missing | Confirm an encounter is selected. Both surfaces gate on `patientId !== null`. |
| Pre-visit brief shows zero counts | Run the scribe + diagram + summary lifecycles first; the brief is a *derived view* of those records. |
| Action queue empty after Generate | Confirm a finalized scribe / signed artifact / finalized summary exists. The clinical-language scan only runs against finalized chart text. |
| Stepper resets after refresh | `localStorage` is disabled in the browser. Re-enable it or use a normal browser window. |
| Reset script refuses to run | `DATABASE_URL` is set to a non-`sqlite:///` value. Unset it before running the script. |

---

## Browser recommendations

- **Chrome / Edge (Chromium)** — the primary supported browser.
  Playwright e2e runs against Chromium.
- **Firefox** — works for the demo. No formal support claim.
- **Safari** — works for the demo. No formal support claim.

For a recorded demo, prefer Chrome with the bookmarks bar hidden,
DevTools closed, and the page zoom at 100 %.

---

## Recording recommendations

This repo does **not** ship video files or screenshots. The video
shot list at `chartnav-video-clip-shot-list.md` is editorial only.
For recording sessions:

- **Resolution**: 1920 × 1080. The workspace renders cleanly at
  100 % zoom; 110 % is fine for talking-head overlays.
- **Browser chrome**: hide bookmarks bar; close DevTools; close
  unrelated tabs; use a clean profile so identity / browser
  history don't appear.
- **Pre-roll**: add a one-second clean shot of the workspace
  before the first interaction so the editor has something to
  fade-in from.
- **Audio**: prefer voice-over recorded separately from screen
  capture so retakes are cheap.
- **Captions**: add captions for every spoken safety guardrail
  ("does not diagnose, order, bill, send referrals, or message
  patients automatically"). Captions are accessibility *and* a
  hedge against bad audio.

### OBS / Zoom

- **OBS**: window-capture the browser, not display-capture, so
  notification toasts from other apps don't end up in the clip.
- **Zoom**: prefer screen sharing the *browser window* rather than
  the full screen. Set the Zoom thumbnail to a corner that does
  not occlude the Demo Mode badge or the panel banner copy.

Do not let unsafe phrasing land in a recording. Watch for any of
these examples in tooltips, captions, or on-screen badges:

- a "HIPAA compliant" tooltip
- an "autonomous diagnosis" caption
- a badge that names an external LLM

If you spot any of those, stop the take and re-record. Do not
edit around it.
