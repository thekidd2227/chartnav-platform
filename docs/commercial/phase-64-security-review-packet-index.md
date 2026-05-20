# ChartNav — Security Review Packet Index (Phase 64)

> **Index of evidence we can share with a buyer's security team
> before any real-PHI use.** Every entry below points at a real
> doc in this repo or a real script the buyer can run. We do
> **not** claim HIPAA / SOC 2 / HITRUST / FDA certification.
> Security review is required before any real-PHI use.

## 0. What this packet is and is not

**Is:** an honest inventory of the safety controls, runtime
gates, claim scanners, and documented product-truth statements
ChartNav can demonstrate today.

**Is not:** a HIPAA / SOC 2 / HITRUST / FDA-certified attestation.
ChartNav is designed to support HIPAA-aware data-handling
practices and is BAA-ready before any real-PHI use; certification
is operational, not vendor-conferred.

If the buyer's security team requires formal third-party
certification as a precondition to any conversation, this is the
disqualifier and the conversation pauses (see
`docs/commercial/phase-64-buyer-qualification-checklist.md` § B).

## 1. Index

Every row below names a document or script that already exists in
the repo and what it proves.

### A. Product truth + claim safety

| Path | What it proves |
|---|---|
| `docs/build/current-product-truth.md` | The single source of truth for what ChartNav is and is not. Every commercial doc in Phase 64 references this file. |
| `docs/commercial/chartnav-approved-claims-language.md` | Approved phrasing for capability / compliance / vendor positioning. Forbidden ↔ approved-phrase table. |
| `docs/commercial/claims-policy.json` | Canonical claims-policy manifest synchronized with all three claim scanners. |
| `docs/commercial/objections/chartnav-buyer-objection-handling.md` | Phase 17 buyer-objection responses — safe by default. |
| `docs/demo/phase-61-buyer-qa-safe-answers.md` | 20-question buyer Q&A bank, every answer aligned with `current-product-truth.md`. |

### B. Runtime safety + scanners

| Path | What it proves |
|---|---|
| `scripts/check_runtime_safety.py` | Runtime safety validator. Refuses unsafe env combinations (real-PHI gate flipped on without security review, production LLM in a non-production env, etc.). Returns PASS on this branch. |
| `scripts/check_commercial_claims.sh` | Phase 17 commercial-claims scanner. Greps every deck + commercial support doc for forbidden positive claims (HIPAA-compliant, SOC 2-certified, autonomous diagnosis, etc.). Returns 0 fail / 0 warn on this branch. |
| `scripts/check_website_claims.sh` | Public landing-page claims scanner. Returns 0 fail / 0 warn on this branch. |
| `scripts/check_demo_claims.sh` | Demo-surface claims scanner. Covers the buyer-demo runbook, narration script, shot lists, and Phase 63 reports. 0 hits across all scanned files. |
| `scripts/test_claim_policy_fixtures.sh` | Sync check between the claims-policy manifest and all three scanners; behavioural fixtures. |
| `scripts/check_alembic_safety.sh` | Verifies a clean Alembic upgrade against a temp DB and refuses raw / SQLite-only migration patterns. |

### C. Release evidence + demo readiness

| Path | What it proves |
|---|---|
| `docs/release/release-evidence-checklist.md` | The artefacts the team gathers before any release-relevant claim is made externally. |
| `docs/demo/phase-62-controlled-buyer-demo-evidence-packet.md` | What the buyer-demo evidence packet must contain. |
| `docs/demo/phase-62a-buyer-demo-go-no-go-status.md` | One-page GO / NO-GO snapshot for the buyer demo. |
| `docs/build/phase-63c-demo-critical-functional-repair-report.md` | Phase 63C functional repair report — frontend API routing fixes, demo DB auto-migrate, manual_note payload shaping, and the introduction of the functional smoke gate. |
| `docs/build/phase-63c1-functional-smoke-500-repair-report.md` | Phase 63C-1 — enhanced smoke + regression tests pinning the smoke payloads. |
| `docs/build/phase-63c2-vitals-smoke-transition-repair-report.md` | Phase 63C-2 — vitals state-machine transition pinned in the smoke + a regression test for the full lifecycle. |
| `scripts/demo/phase63c_functional_smoke.sh` | The buyer-demo functional gate. Honest, HTTP-level, exits 0 only when Vitals / VisitDraft / Fundus + manual_note shape all pass. Latest local run: `BUYER-DEMO FUNCTIONAL GO: YES` at `8d2b6dd`. |
| `artifacts/phase-62/screenshots/` | 30 captured screenshots from a real Playwright run against the live local stack. |
| `artifacts/phase-62/video-clips/` | 12 captured video clips from the same run. |

### D. Data-handling and tenancy posture

| Path | What it proves |
|---|---|
| `apps/api/app/main.py` | CORS allow-list scoped to local dev origins by default. `X-User-Email`, `X-Request-ID` allowed; production LLM gate not flipped. |
| `apps/api/app/audit.py` | Append-only security audit events for auth denials and sensitive state transitions. |
| `apps/api/scripts_seed.py` | Idempotent fake-data seed; **no real PHI** is shipped in the repo. |
| `apps/api/alembic/versions/` | Versioned, reversible schema migrations. Alembic safety scanner refuses raw CREATE TABLE patterns. |

### E. Operator demo bundle

| Path | What it proves |
|---|---|
| `artifacts/phase-62/desktop-bundle/.chartnav-demo-env` | Bootstrap env file. Forces deterministic stub provider, `CHARTNAV_LLM_ENABLED=0`, real-PHI gates off. Explicitly unsets vendor API keys. |
| `artifacts/phase-62/desktop-bundle/run-safety-checks.sh` | One-command wrapper that runs all six safety gates before opening any buyer demo. Refuses production / staging / controlled-pilot env. |
| `artifacts/phase-62/desktop-bundle/start-api.sh` | Bundle API wrapper. Auto-migrates + idempotently seeds before booting. Refuses production env and real-PHI gates. |

## 2. What we can demonstrate live in a security review

- Run all six safety scanners and show the PASS output.
- Run the Phase 63C functional smoke and show
  `BUYER-DEMO FUNCTIONAL GO: YES`.
- Walk the buyer-demo visit script end-to-end on the seeded fake
  patient (Morgan Lee / PT-1001).
- Show the "What ChartNav did NOT do" panel returning each
  disallowed action with `(false)`.
- Show that no vendor API key is read by the deterministic stub
  path.
- Show that `CHARTNAV_LLM_ENABLED=0` is the bundle default and
  that the wrappers refuse to boot with it set to `1`.
- Walk the runtime-safety validator's refusal cases.

## 3. What we cannot demonstrate (yet)

- A third-party HIPAA / SOC 2 / HITRUST / FDA attestation.
  ChartNav does not hold those certifications today.
- A signed BAA on the first call. BAA discussions are
  conditional on a completed security review.
- A production LLM path approved for clinical text. The vendor
  evaluation work (OpenAI / Anthropic / IBM watsonx) is exactly
  that — vendor evaluation, never advertised as a shipped
  production capability.
- ChartNav does not provide an ambient scribe.
- ChartNav does not capture exam-room audio.
- ChartNav does not provide fundus image interpretation.
- ChartNav does not provide OCT interpretation.
- ChartNav does not provide automatic orders, referrals, or patient messages.
- ChartNav does not provide billing or coding.
- ChartNav does not provide device integration.
- ChartNav does not provide remote patient monitoring.
- None of those are in scope.

## 4. How a security review starts

1. The buyer's security lead reads `current-product-truth.md`
   and this index.
2. We schedule a 30-minute walk-through of § 2.
3. The buyer's security lead sends their internal questionnaire.
4. We respond in writing, citing the paths above.
5. If the response is acceptable, the legal step is the BAA
   conversation.
6. Real-PHI use cannot start before the BAA is executed.

## Safety note

- Fake-data demo first.
- Paid pilot subject to security review for any real-PHI use.
- Provider review and sign-off required on every artefact.
- ChartNav is designed to support HIPAA-aware data-handling practices and is BAA-ready before any real-PHI use.
- ChartNav is not HIPAA-certified.
- ChartNav is not a certified EHR and does not replace any EHR.
- ChartNav does not diagnose.
- ChartNav does not interpret fundus or OCT images.
- ChartNav does not place orders, send referrals, or message patients.
- ChartNav does not bill or code.
- ChartNav does not integrate with medical devices and does not provide remote patient monitoring.

## Related documents

- `docs/build/current-product-truth.md`
- `docs/release/release-evidence-checklist.md`
- `docs/commercial/phase-64-paid-pilot-positioning.md`
- `docs/commercial/phase-64-demo-asset-index.md`
- `docs/commercial/phase-64-buyer-qualification-checklist.md`
