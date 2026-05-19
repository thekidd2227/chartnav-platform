# Phase 61 — Controlled Buyer Demo Checklist

> Use this as the pre-flight + in-flight + post-flight checklist
> alongside `docs/demo/phase-61-controlled-buyer-demo-runbook.md`.
> The runbook is the playbook; this file is the audit trail the
> operator completes before, during, and after every buyer demo.

## Release / demo header

- Release / demo ID:
- Current `main` SHA (paste `git log --oneline -1` output):
- Branch:
- Operator (name, role):
- Narrator (if separate):
- Buyer / audience:
- Date / time:

---

## 1. Pre-demo (must all be `[x]` before opening screen-share)

### Environment

- [ ] `git checkout main && git pull --ff-only origin main && git status --short` clean.
- [ ] `CHARTNAV_ENV` is `local` / `dev` / `demo` / `test` —
      **never** `production` / `staging` / `controlled-pilot`.
- [ ] `CHARTNAV_LLM_ENABLED` is `0` or unset.
- [ ] `CHARTNAV_LLM_REAL_PHI_APPROVED` is `0` or unset.
- [ ] `CHARTNAV_REAL_PHI_ENABLED` is `0` or unset.
- [ ] `CHARTNAV_LLM_PROVIDER` is `deterministic_stub` (default).
- [ ] `CHARTNAV_FUNDUS_DRAFTING_ASSIST` is unset (unless this is the
      separate OpenAI fake-data fundus assist demo).
- [ ] `CHARTNAV_AMBIENT_DOCUMENTATION_ASSIST` is unset (same).
- [ ] No real `CHARTNAV_OPENAI_API_KEY` / `CHARTNAV_ANTHROPIC_API_KEY`
      in the shell.
- [ ] `DATABASE_URL` points at the local / demo database.

### Fake-data discipline

- [ ] Seeded demo patient (Morgan Lee, `PT-1001`, encounter `#1`) is
      the only patient used.
- [ ] No real names / DOB / MRN / phone / address / insurance / photo
      will be entered in any panel.
- [ ] Vitals will be populated only via **Load fake demo vitals**
      (or by typing synthetic values).
- [ ] Ambient transcript will be populated only via **Load demo sample
      (fake data)** (or by typing synthetic text).
- [ ] Fundus findings will be populated only via demo sample chips
      (or by typing synthetic clinician findings).

### Safety gates (every command must PASS)

- [ ] `python3 scripts/check_runtime_safety.py` → **PASS**.
- [ ] `bash scripts/check_commercial_claims.sh` → **PASSED**.
- [ ] `bash scripts/check_website_claims.sh` → **PASSED**.
- [ ] `bash scripts/check_demo_claims.sh` → **PASSED**.
- [ ] `bash scripts/test_claim_policy_fixtures.sh` → **PASS** (sync + fixtures).
- [ ] `bash scripts/check_alembic_safety.sh` → **PASSED**.

### UI / browser

- [ ] Browser zoom = 100%.
- [ ] No real `.env` file is open in any visible editor.
- [ ] Side terminal is ready with `python3 scripts/check_runtime_safety.py`.
- [ ] Demo reset script identified for cleanup:
      `scripts/reset_demo_state.sh` (general)
      or `scripts/reset_phase24b_retina_demo.sh` (retina-only).
- [ ] Optional: backup screenshots of the three signed artefacts
      taken in case of a live demo failure.

### Identity

- [ ] Demo driver is `clin@chartnav.local` (clinician) by default.
- [ ] Technician identity `tech@chartnav.local` available for the
      Vitals scene if running technician-only steps.
- [ ] No production identities are available in the demo browser.

---

## 2. During demo

### Fake-data discipline (re-confirm in-flight)

- [ ] No real names appearing in any header / breadcrumb / encounter
      summary.
- [ ] No real DOB / MRN / phone / address visible.
- [ ] Vitals entries are the fake demo values from the sample button.
- [ ] Ambient transcript is the fake demo sample.
- [ ] Fundus findings come from the four demo-safe sample chips.

### Narration discipline (re-confirm in-flight)

- [ ] Warnings explained as **review prompts**, not as diagnoses.
- [ ] **Review vs Sign** distinction explicitly narrated on each surface.
- [ ] Sign action gated on the attestation checkbox each time;
      never demonstrated as a one-click action.
- [ ] **Signed-lock banner** + "Signed artefacts are immutable"
      narrated on each surface.
- [ ] "What ChartNav did NOT do" card read aloud on at least one
      surface, listing at least three of the `(false)` entries.
- [ ] Runtime safety validator demonstrated live (Scene 6).
- [ ] **No forbidden claim** from § 9 of the runbook appears in
      narration or in any UI surface during the demo.

### Forbidden-claim scan (in-flight self-check)

- [ ] No "HIPAA compliant" / "HIPAA certified".
- [ ] No "EHR replacement" / "replaces your EHR".
- [ ] No "autonomous documentation" / "autonomous diagnosis" /
      "autonomous interpretation".
- [ ] No "hands-free scribing" / "ambient scribe parity" /
      "AI writes the note" / "note writes itself" / "chart fills itself".
- [ ] No "OpenAI-powered" / "GPT-powered" / "Claude-powered" /
      "Anthropic-powered" / "IBM watsonx-powered" clinical
      documentation claim.
- [ ] No "treatment recommendation" / "AI prescribes" /
      "AI orders labs".
- [ ] No "fundus image interpretation" / "OCT interpretation" /
      "AI interprets fundus".
- [ ] No "device integration" / "live device integration" /
      "vital-signs device integration" / "BP cuff integration".
- [ ] No "remote patient monitoring" / "RPM-ready" /
      "continuous patient monitoring".
- [ ] No "automatic billing" / "automatic coding" /
      "coding recommendations".
- [ ] No "automatic orders" / "automatic referrals" /
      "patient messaging" / "send patient message".
- [ ] No "real PHI ready" / "production-ready for PHI" /
      "BAA-ready by default".
- [ ] No "guaranteed ROI" / "ROI guarantee".
- [ ] No competitor-superiority claim (no "better than X" / "X
      replacement" / "X-killer").

### Stop-demo trigger check (any one → halt + reset)

- [ ] Real patient data on screen → **HALT**.
- [ ] Production env banner visible → **HALT**.
- [ ] Runtime safety validator FAIL → **HALT**.
- [ ] Forbidden phrase in narration or UI → **HALT**.
- [ ] Secret value in stack trace / error banner / console → **HALT**.
- [ ] Raw transcript / draft body / vitals value in audit log line → **HALT**.
- [ ] Sign succeeds without attestation checkbox → **HALT** (UI regression).
- [ ] Diagnosis / treatment / order / billing / coding / referral /
      patient-message text in any UI surface → **HALT**.

---

## 3. Post-demo

### Cleanup

- [ ] Stop the screen-share before any post-demo Q&A that could
      expose internal state.
- [ ] Reset the local demo database:
      `bash scripts/reset_demo_state.sh` (or
      `bash scripts/reset_phase24b_retina_demo.sh` if retina was
      shown).
- [ ] Unset any session env vars set for fake-data testing.
- [ ] Re-run `python3 scripts/check_runtime_safety.py` — verify PASS.

### Buyer questions

- [ ] Questions captured into the follow-up channel.
- [ ] Each question categorised:
   - [ ] **Product** (UI / workflow / feature gap) →
         product backlog.
   - [ ] **Security** (auth / RBAC / PHI / compliance) →
         security review queue.
   - [ ] **Commercial** (pricing / contracts / pilot terms) →
         commercial follow-up.
- [ ] No buyer-specific promises were made during the demo.
- [ ] No vendor / partner claims were made
      (OpenAI / Anthropic / IBM watsonx / Whisper / FHIR vendors / etc.).

### Privacy

- [ ] No real PHI was processed or retained from the demo.
- [ ] No screenshots / recordings contain anything but fake demo
      data.
- [ ] No exported audit logs contain anything but fake demo data.
- [ ] If demo was recorded, the recording is marked "fake demo data"
      and reviewed before any sharing.

### Near-miss reporting

- [ ] If any stop-demo trigger fired, or a forbidden phrase was narrowly
      avoided, file the near-miss with the runbook author. The
      runbook is updated via a normal PR; do not edit live.

---

## 4. Go / no-go

- **Pre-demo decision** (all of § 1 must be `[x]`): pending / GO / NO-GO
- **Post-demo decision** (no stop-demo trigger fired in § 2): pending / CLEAN / INCIDENT
- **Approver:** _______________
- **Date:** _______________

---

## Related documents

- `docs/demo/phase-61-controlled-buyer-demo-runbook.md` — what to click and say (the playbook).
- `docs/demo/phase-61-buyer-qa-safe-answers.md` — Q&A safe answers.
- `docs/demo/phase-61-demo-storyboard.md` — operator storyboard.
- `docs/release/release-evidence-checklist.md` — release-gate template (broader scope).
- `docs/build/current-product-truth.md` — single source of truth.
- `docs/commercial/claims-policy.json` — canonical manifest.
- `scripts/check_runtime_safety.py` — runtime gate (must PASS before demo).
