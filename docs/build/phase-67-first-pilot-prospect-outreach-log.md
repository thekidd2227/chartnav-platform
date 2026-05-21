# Phase 67 — First Pilot Prospect Outreach Log (Build Report)

> **Status: docs-only commercial-execution increment. Manual
> outreach readiness GO** (subject to the existing safety
> frame). No product code, no backend, no frontend, no API, no
> migration, no demo-script change, no public website change,
> no deploy, no real PHI, no production LLM, no new claims, no
> customer-traction claims.

## 1. What Phase 67 adds on top of Phase 64 / 66

Phase 64 shipped the **canonical outreach assets** (tracker
schema, 11 email / call / DM templates, buyer qualification,
pilot positioning, success metrics, security-review index, demo
asset index). Phase 66 shipped the **founder-led overlay**
(specialty-tiered prospect targeting, founder-voice emails,
15-question discovery, what-not-to-promise cheat sheet).

Phase 67 is the **week-1 execution layer** sitting on top.
Where Phase 64 / 66 answer "what to send" and "how to position,"
Phase 67 answers "what to do Monday morning, in 90 minutes, to
get the first 10 prospects into a structured cadence."

Phase 67 deliberately does NOT duplicate Phase 64 / 66:

| Phase 67 doc | What's new vs Phase 64 / 66 |
|---|---|
| `phase-67-first-pilot-prospect-list-template.md` | **Simpler 10-row starter form** with only the 10 minimum columns needed for the first week. Phase 64's `outreach-tracker-schema.md` has 22 columns and is the ongoing system; Phase 67 is the day-one starter. Includes 10 pre-shaped empty rows. |
| `phase-67-outreach-execution-log.md` | **Day 0 / Day 3 / Day 7 / Day 14 sequence** with explicit decision trees per day, routing for reply / no-reply / bounce / OOO, logging discipline per touch, and the Cycle 1 close-out review. Phase 64 has the templates but not the cadence + logging discipline. |
| `phase-67-first-10-targets-research-guide.md` | **90-minute concrete research workflow** with per-source time-boxes (30 min personal network → 20 min conference contacts → 25 min LinkedIn → 15 min direct research), explicit "what NOT to collect" privacy rules, and anti-spam rules. Phase 66 § 5 named the sources strategically; Phase 67 specifies the workflow tactically. |

## 2. Files changed

| Path | Lines | Kind |
|---|---:|---|
| `docs/commercial/phase-67-first-pilot-prospect-list-template.md` | 110 | New |
| `docs/commercial/phase-67-outreach-execution-log.md` | 230 | New |
| `docs/commercial/phase-67-first-10-targets-research-guide.md` | 213 | New |
| `docs/build/phase-67-first-pilot-prospect-outreach-log.md` | (this) | New build report |
| `scripts/check_commercial_claims.sh` | +5 / 0 | Extend SUPPORT FILES list from 21 to 24 docs |

## 3. Safety notes

- **No customer-traction claims.** Phase 67 docs explicitly
  state ChartNav is pre-pilot. The prospect-list starter table
  is 10 *empty* rows; no real practice name appears in any doc.
- **No claim that any practice has agreed to pilot.** The
  outreach execution log's § 8 close-out review explicitly
  blocks publishing or quoting results without explicit founder
  sign-off.
- **No private personal data scraped.** § 4 of the research
  guide names exactly what NOT to collect (phone, home address,
  spouse, patient counts, EHR credentials, off-LinkedIn social).
- **No spammy outreach.** § 5 of the research guide bans
  automation tools (Apollo / ZoomInfo / Lemlist / Hunter /
  Snov), scraped contact lists, bulk sends, and re-contact
  after `paused` or `closed-no-fit`.
- **No unsafe claims about ChartNav.** All three Phase 67 docs
  carry the canonical safety-note bullets and reference
  `phase-66-what-not-to-promise-cheat-sheet.md` for live-call
  guard.
- **No archived Phase 62 artifacts modified.** Per the brief.
- **No product functionality change.** No file under
  `apps/api/` or `apps/web/` touched. No demo script touched.
  No migration. No claim policy. No public website.

## 4. Scanner results

- `scripts/check_commercial_claims.sh` — **PASS (0 fail / 0 warn across 24 docs)** — was 21, now 24
- `scripts/check_demo_claims.sh` — PASS (0 hits across 34 demo files)
- `scripts/check_website_claims.sh` — PASS (0 fail / 0 warn)
- `scripts/test_claim_policy_fixtures.sh` — PASS
- `scripts/check_runtime_safety.py` — PASS
- `scripts/check_alembic_safety.sh` — PASS
- `git diff --check` — clean

## 5. Phase 63C buyer-demo smoke

**Not run from this sandbox** (no live API/web stack). Behavior
preserved by construction — no API route, schema, service
module, migration, claim policy, demo / capture / smoke script
touched.

Last operator-side outcome on this `main` baseline (`f5dab0e`,
Phase 66):
```
Phase 63C functional smoke: 20 pass / 0 fail
BUYER-DEMO FUNCTIONAL GO: YES
```

## 6. Final GO / NO-GO for starting manual outreach

**Repo-side: GO.** Phase 67 adds the week-1 execution layer
with full safety-frame coverage. All 6 scanner gates pass.

**Operator-side: GO when the operator has completed these four
steps, in this order:**

1. **Confirm Phase 63C smoke is green** on the iMac stack
   (per `phase-67-first-10-targets-research-guide.md` § 0
   pre-flight).
2. **Run the 90-minute research workflow** in
   `phase-67-first-10-targets-research-guide.md` § 1 to produce
   10 valid prospect rows.
3. **Verify the 5 quality gates** in
   `phase-67-first-10-targets-research-guide.md` § 6 (all 10
   rows complete, at least 50% warm-path, zero Phase 64 § B
   disqualifiers fired from research, zero `unknown` decision
   makers, zero PHI / forbidden phrases in `Notes`).
4. **Memorise the three emergency phrases** from
   `phase-66-what-not-to-promise-cheat-sheet.md` § J.

When all four hold, begin Day 0 per
`phase-67-outreach-execution-log.md` § 1.

## 7. Exact next iMac commands after PR review

```bash
export CHARTNAV_REPO_PATH="$HOME/Desktop/ARCG/chartnav-platform"
cd "$CHARTNAV_REPO_PATH"
git checkout main
git pull origin main
git log --oneline -1
```

Expected HEAD after PR #<NN> merges: `<merge sha>
docs(commercial): add first pilot prospect outreach log (#NN)`.

Re-confirm the smoke (should remain green — no code touched):

```bash
PHASE63C_API_URL="http://127.0.0.1:8765" \
PHASE63C_WEB_URL="http://127.0.0.1:5173" \
bash scripts/demo/phase63c_functional_smoke.sh
```

Then read the Phase 67 packet in this order:

```bash
open docs/commercial/phase-67-first-10-targets-research-guide.md
open docs/commercial/phase-67-first-pilot-prospect-list-template.md
open docs/commercial/phase-67-outreach-execution-log.md
open docs/build/phase-67-first-pilot-prospect-outreach-log.md
```

Then block 90 minutes Monday morning and execute the research
workflow.

## 8. What's NOT in scope for Phase 67 (deferred)

- **Phase 65D** Pilot Support / Incident Workflow deepening —
  waits for a real prospective pilot practice.
- **Phase 65C** Limited Pilot Instrumentation deepening — same.
- **Phase 65E** Pilot Exit Criteria deepening — same.
- **A real prospect list** — Phase 67 ships templates and the
  research workflow; the operator produces the actual list at
  engagement time.
- **CRM integration** — Phase 67 stays on flat-file / spreadsheet
  workflow per the Phase 64 outreach-tracker-schema's posture.
- **Any product, backend, frontend, API, schema, migration,
  scanner-policy, demo-script, or public-website change.**

## 9. Hard constraints honored

- No customer-traction claims invented.
- No claim that any practice has agreed to pilot.
- No private personal data added.
- No unsafe claims.
- No claim ChartNav is an EHR replacement, billing engine,
  diagnostic AI, autonomous scribe, HIPAA-certified product, or
  production PHI system.
- No product functionality change.
- No archived Phase 62 artifacts restored, committed, or
  modified.

## Related documents

- `docs/build/current-product-truth.md`
- `docs/build/phase-66-controlled-buyer-outreach-packet.md`
- `docs/commercial/phase-64-outreach-tracker-schema.md` (full ongoing tracker schema)
- `docs/commercial/phase-66-prospect-targeting-brief.md`
- `docs/commercial/phase-66-founder-led-outreach-templates.md`
- `docs/commercial/phase-66-what-not-to-promise-cheat-sheet.md`
- `docs/commercial/phase-67-first-pilot-prospect-list-template.md`
- `docs/commercial/phase-67-outreach-execution-log.md`
- `docs/commercial/phase-67-first-10-targets-research-guide.md`
