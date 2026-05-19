# Phase 59 — Ambient Documentation Demo QA Lockdown Checklist

> Mandatory pre-flight + in-flight + post-flight checklist before
> demoing the Phase 57 Provider-Reviewed Ambient Documentation Assist
> to a customer, partner, or investor. **No real PHI.** **No
> production LLM.** **Provider review required at every step.**
>
> Use this **in addition to** the Phase 57 demo runbook at
> `docs/demo/phase-57-ambient-documentation-demo-runbook.md`. This
> file is the audit trail you complete before going live; the runbook
> is the playbook for what to click and say.

## Release / demo header

- Release / demo ID:
- Commit SHA:
- Branch:
- Operator (name, role):
- Date / time:
- Audience type (internal / partner / customer / investor):

---

## 1. Pre-demo checklist (must all be `[x]` before opening screen-share)

### Environment

- [ ] `CHARTNAV_ENV` is one of `local`, `dev`, `development`, `test`,
      `ci`, `demo`, `fake`, `fake-data`.
- [ ] `CHARTNAV_ENV` is **not** `production`, `controlled-pilot`, or
      `staging`.
- [ ] `CHARTNAV_LLM_ENABLED` is `0` or unset.
- [ ] `CHARTNAV_LLM_REAL_PHI_APPROVED` is `0` or unset.
- [ ] `CHARTNAV_REAL_PHI_ENABLED` is `0` or unset.
- [ ] `CHARTNAV_PILOT_ALLOW_LLM_OPENAI` is `0` or unset.
- [ ] `CHARTNAV_LLM_PROVIDER` is `deterministic_stub` (the production
      default).
- [ ] `CHARTNAV_AMBIENT_DOCUMENTATION_ASSIST` is unset **unless**
      this is an explicit fake-data OpenAI assist demo, in which case
      it is exactly `openai` AND every Phase 52B SAFE-state gate also
      holds.
- [ ] No real `CHARTNAV_OPENAI_API_KEY` is set in the demo shell.
- [ ] No real `CHARTNAV_ANTHROPIC_API_KEY` is set in the demo shell.
- [ ] `DATABASE_URL` points at the local / demo database (not a
      production cluster).

### Patient and transcript

- [ ] Patient is a **fake demo patient** (the seeded
      `demo-eye-clinic` org or equivalent). No real patient name,
      MRN, DOB, address, phone, insurance, or photo is visible on
      screen anywhere.
- [ ] No real audio recording will be played.
- [ ] No real transcript text will be pasted. Only the fake samples
      from `docs/demo/phase-57-ambient-documentation-demo-runbook.md`
      § 5 will be used.

### Safety / runtime checks (must all pass)

- [ ] `python3 scripts/check_runtime_safety.py` → **PASS**.
- [ ] `bash scripts/check_commercial_claims.sh` → **PASSED**.
- [ ] `bash scripts/check_website_claims.sh` → **PASSED**.
- [ ] `bash scripts/check_demo_claims.sh` → **PASSED**.
- [ ] `bash scripts/test_claim_policy_fixtures.sh` → **PASS**.
- [ ] `bash scripts/check_alembic_safety.sh` → **PASSED**.

### UI reachability

- [ ] Open the demo encounter.
- [ ] Click the **Documentation** tab. The
      `ctw-tab-documentation` test-id resolves.
- [ ] Scroll past the Transcript → Extracted Facts → AI Draft → Final
      Note stepper and the `NoteWorkspace` workbench.
- [ ] The wide **"Provider-Reviewed Ambient Documentation Assist"**
      card (`ctw-card-ambient-documentation`) is visible.
- [ ] The card's panel (`ambient-documentation-panel` test-id)
      renders without error.
- [ ] The safety banner (`ambient-safety-banner`) is visible.
- [ ] The "Load demo sample (fake data)" button
      (`ambient-sample-btn`) is visible.
- [ ] Click it. The textarea (`ambient-transcript-text`) fills with
      the standard fake transcript. The button does **not** load any
      real-patient content.

---

## 2. Demo flow checklist (perform in order; tick as you go)

- [ ] **Load sample transcript** — click "Load demo sample". Visible
      result: textarea contains "Demo transcript only. Patient
      reports blurry vision in the right eye for two weeks. …".
- [ ] **Generate provider-review draft** — click "Generate
      provider-review draft". Visible result: status timeline pills
      flip to `Draft → READY FOR REVIEW → reviewed → signed`
      (only the first two highlighted).
- [ ] **Point out safety banner** — read the six clauses aloud:
      "Draft from fake/demo encounter transcript. Provider review
      required. Does not diagnose. Does not place orders. Does not
      send referrals or patient messages. Does not bill or code. Not
      for real PHI."
- [ ] **Point out structured facts** — the structured-facts card
      (`ambient-structured-facts`) shows chief complaint, HPI
      summary, visual acuity (numeric values preserved exactly),
      IOP, imaging metadata, assessment context, plan-as-stated.
- [ ] **Point out missing information** — clear the textarea, paste
      `Demo only. Patient seen for routine visit.`, click Generate.
      The missing-information card now lists 3 items (CC / VA / IOP).
      Say: "ChartNav will not invent values."
- [ ] **Point out safety flags** — clear, paste `Demo only. Patient
      reports floaters OD. VA 20/40 OD, 20/20 OS. IOP 14 OD, 13 OS.
      Provider mentioned referral to retina specialist and CPT code
      92014.`, click Generate. The safety-flags card warns the
      transcript referenced orders / referrals / billing / coding
      and that **ChartNav did NOT execute any of these**.
- [ ] **Point out "What ChartNav did NOT do"** — the
      `ambient-actions-summary` card lists each forbidden action with
      `(false)` next to it. Read at least 3 aloud (e.g. "diagnosis
      (false), orders (false), billing or coding (false)").
- [ ] **Edit draft if supported** — open the
      `ambient-draft-text` details. Show that the draft text is
      readable and editable downstream by the provider. (V1 panel is
      preview-only; future versions may add inline editing — do not
      claim it exists today.)
- [ ] **Review** — return to a clean sample's draft, click "Mark
      Reviewed". Status timeline pill row flips to highlight
      `REVIEWED`. The Review button disables.
- [ ] **Sign / finalize only with attestation** — the purple
      attestation block (`ambient-attestation-block`) appears. Try
      clicking "Sign & Lock Draft" without ticking the checkbox; the
      button stays disabled. Read the attestation aloud, tick the
      checkbox, click "Sign & Lock Draft".
- [ ] **Show signed / locked state** — the action bar is replaced
      with the green `ambient-signed-lock` banner ("Draft signed ·
      locked. Signed drafts are immutable."). All edit controls are
      absent from the DOM. Backend mutation attempts on this session
      now 409.

---

## 3. Required narration phrases

The operator must say these phrases during the demo (or visibly point
to them on screen):

- [ ] "Fake/demo transcript only."
- [ ] "Provider review required."
- [ ] "Not autonomous documentation."
- [ ] "Not diagnosis."
- [ ] "Not image interpretation."
- [ ] "Does not place orders, referrals, or send patient messages."
- [ ] "Does not bill or code."
- [ ] "Not real PHI."
- [ ] **If OpenAI is mentioned**: "ChartNav's optional OpenAI assist
      is fake-data / demo only behind guardrails. ChartNav is not
      'OpenAI-powered'. Production fundus and ambient documentation
      use the deterministic rule-based path."

---

## 4. Stop-demo triggers (any one → halt + reset)

Halt the demo immediately and reset the screen-share if any of the
following are observed:

- [ ] Real patient data appears anywhere on screen (name, MRN, DOB,
      address, phone, photo, real audio, real transcript).
- [ ] `CHARTNAV_ENV` is `production`, `controlled-pilot`, or
      `staging` (visible in env dump or runtime banner).
- [ ] `python3 scripts/check_runtime_safety.py` returns `FAIL` for
      any combination at any point during the demo.
- [ ] A forbidden phrase appears in narration **or** in the UI:
      "hands-free scribing", "autonomous documentation", "AI writes
      the note", "note writes itself", "chart fills itself",
      "OpenAI-powered clinical documentation", "production LLM
      documentation", "real PHI ready", "ambient scribe parity",
      "HIPAA compliant", "EHR replacement".
- [ ] A vendor / network error exposes a secret value (API key, full
      Authorization header, OpenAI organization ID) in a visible
      stack trace, error banner, or browser console.
- [ ] A raw transcript or draft body appears in an audit log line
      visible during the demo.
- [ ] Sign / finalize is observed to succeed **without** the
      attestation checkbox having been ticked (this is a UI bug;
      escalate after halting).
- [ ] Any "diagnosis confirmed", "order placed", "CPT code", "ICD-10
      code", "referral submitted", "patient message sent", or
      "billing code" text appears in the structured facts, draft
      note, or any UI section.

---

## 5. Troubleshooting

| Symptom | Likely cause | Recovery |
|---|---|---|
| API failure / `HTTP 500` on draft-ambient | Backend exception (e.g. transient DB lock). | Retry the click once. If it persists, halt the demo and pull the backend logs (`docker compose logs api -n 200`) for a non-PHI-revealing snippet. |
| `HTTP 404 patient_not_found` | Wrong patient_id or you switched orgs. | Verify the URL patient_id matches an org-1 patient. |
| `HTTP 403 role_forbidden` | Logged in as reviewer / front-desk / technician. | Switch to a clinician identity (`clin@chartnav.local` in the seeded demo). |
| `HTTP 422 fake_data_context_required` | Client mutation set `fake_data_context: false`. | Bug in the client code; the panel never does this. Halt and inspect. |
| `HTTP 409 invalid scribe transition` | Tried to review before draft-ambient, or finalize before review, or re-draft an already-processed session. | Expected. Use a new session, or follow the lifecycle order. |
| Generate button stays disabled | Empty textarea. | Click "Load demo sample". |
| Status timeline does not advance past Draft | Generate failed silently. | Check the `ambient-error` banner. Verify network and runtime safety. |
| `AMBIENT_OPENAI_NOT_DEMO` / `AMBIENT_OPENAI_PRODUCTION` / `AMBIENT_OPENAI_REAL_PHI_APPROVED` / `REAL_PHI_WITH_AMBIENT_OPENAI` / `PRODUCTION_AMBIENT_OPENAI` from runtime safety validator | An ambient-OpenAI gate failed pre-flight. | Halt. Unset `CHARTNAV_AMBIENT_DOCUMENTATION_ASSIST` to return to the deterministic default. |
| `ProviderDisabledError` from the ambient service | OpenAI assist was opted into but a Phase 52B gate is in the UNSAFE state. | Halt. The deterministic default is the demo path; unset the opt-in env var. |
| Claim scanner failure pre-demo | A doc / runbook contains a forbidden phrase. | Halt. Fix the wording before resuming. |
| Sign / finalize succeeds but the signed banner does not appear | Stale chart loaded in the editor (Phase 55-era warnings-refresh class of bug). | Click another saved session in the list and back; the warnings/lock state refresh on chart-id change. |

---

## 6. Post-demo checklist

- [ ] Stop the screen-share before any post-demo Q&A that could
      expose internal state.
- [ ] Reset the local demo database if it received any new sessions
      (`scripts/reset_demo_state.sh`, or the Phase 24B retina-specific
      `scripts/reset_phase24b_retina_demo.sh`, whichever fits the
      demo scope).
- [ ] Unset `CHARTNAV_AMBIENT_DOCUMENTATION_ASSIST` if it was set for
      a fake-data OpenAI assist demo.
- [ ] Run `python3 scripts/check_runtime_safety.py` once more and
      verify `PASS`.
- [ ] File any observed forbidden-phrase or claim-scanner near-miss
      with the runbook author. Updating the runbook is **not** the
      same as merging a code change — claim scanner additions / phrase
      additions should land via a normal PR with all three scanners
      re-run.

---

## 7. Go / no-go

- **Pre-demo decision** (all of § 1 must be `[x]`): pending
- **Post-demo decision** (no stop-demo trigger fired in § 4): pending
- **Approver:** _______________
- **Date:** _______________

---

## Related documents

- `docs/demo/phase-57-ambient-documentation-demo-runbook.md` — what to
  click and say (the playbook).
- `docs/workflow/ambient-documentation-assist.md` — feature contract
  + API reference + safety boundary.
- `docs/build/current-product-truth.md` — Ambient Documentation Assist
  row (single source of truth for status / claim posture / rollback).
- `docs/commercial/claims-policy.json` — canonical forbidden-phrase
  manifest.
- `docs/release/release-evidence-checklist.md` — broader release gate
  template; this file is the ambient-specific subset.
- `scripts/check_runtime_safety.py` — runtime gate (must PASS before
  demo).
