# artifacts/

This directory is the **fillable** evidence pointer area for this
delivery package. It is intentionally **almost empty** in the
zipped package — the operator populates it on the workstation
that runs the demo.

## What lives here

| File | Who fills it | When |
|---|---|---|
| `README.md` (this file) | already in package | n/a |
| `manifest.txt` | ARCG operator | after running the Phase 100 launch gate + Phase 101 capture (Sections 5–6 of `07-local-demo-operator-commands.md`) |

## What the operator does NOT include here

Per the delivery hard rules, the operator must **not** drop any
of the following into this folder before handing it to the
practice:

- `.env*` files or any file containing real credentials / API
  keys
- `node_modules/` or dependency caches
- Database files (`*.db`, `*.sqlite`, `*.sqlite-journal`)
- Real-PHI artifacts of any kind
- Local git metadata (`.git/`, `.gitconfig`, `.gitignore` global)

## Recommended `manifest.txt` template

After Sections 5 and 6 of `07-local-demo-operator-commands.md`
succeed, paste the dated paths the gates printed into a
`manifest.txt` at this location. Suggested template:

```
ChartNav Controlled Pilot — Evidence Manifest
captured_at:  <YYYY-MM-DDTHH:MM:SSZ>
operator:     <ARCG ops operator name>
workstation:  <hostname>
repo_sha:     <git rev-parse HEAD>
branch:       main

Phase 88 release evidence gate
  dir:  artifacts/release-evidence/<ts>/
  summary: artifacts/release-evidence/<ts>/summary.txt
  result: PASS / FAIL

Phase 100 controlled-pilot launch gate
  dir:  artifacts/phase-100-controlled-pilot-launch/<ts>/
  summary: artifacts/phase-100-controlled-pilot-launch/<ts>/summary.txt
  go-no-go: artifacts/phase-100-controlled-pilot-launch/<ts>/go-no-go.txt
  result: PASS / FAIL · CONDITIONAL GO / NO-GO

Phase 101 buyer-demo evidence capture
  dir:  artifacts/buyer-demo/<ts>/
  summary: artifacts/buyer-demo/<ts>/summary.txt
  attestation: artifacts/buyer-demo/<ts>/no-real-phi-attestation.txt
  missing-evidence: artifacts/buyer-demo/<ts>/missing-evidence.txt
  result: PASS / FAIL · CONDITIONAL GO / NO-GO

Phase 63C functional smoke (embedded in Phase 101 bundle)
  log: artifacts/buyer-demo/<ts>/O1-phase63c-smoke.log
  result: 20 pass / 0 fail · BUYER-DEMO FUNCTIONAL GO: YES / NO / SKIPPED

Optional Playwright capture
  result: PASS / SKIP (reason)

Manual screenshots
  dir:  artifacts/buyer-demo/<ts>/manual-screenshots/
  files: <list>

Confirmations
  - No real PHI processed.
  - No production LLM enabled.
  - No publish / no GitHub release / no notarization upload.
  - .env files not touched.
  - Demo banner "demo mode — no real PHI" visible in every captured frame.

Operator signature: ______________________
Date:                ______________________
```

## How the practice's CISO reads this

The practice's CISO opens `manifest.txt`, then walks the dated
paths (kept either on the operator's workstation or in a folder
zipped + delivered out-of-band per the practice's preference).
The `04-evidence-index.md` document in this delivery folder
explains what each artifact contains.
