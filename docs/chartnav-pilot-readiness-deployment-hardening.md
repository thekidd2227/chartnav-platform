# ChartNav Pilot Readiness / Deployment Hardening (Phase 14)

Phase 14 is a **pilot-readiness / deployment-hardening phase**. It
is not a new clinical feature, not new medical reasoning, not
orders / coding / referral / patient-messaging work, not EHR
integration, not commercial-deck creation, and not desktop demo
packaging (that belongs to Phase 15).

The goal: prepare ChartNav for safe pilot conversations and
controlled-pilot deployment with ophthalmology offices, without
obvious gaps.

**No new clinical automation. No new schema. No new API surface.
No backend code changes.**

## Purpose

Phase 13 packaged the existing workflow as a five-minute demo for
a buyer / pilot user / advisor / investor. Phase 14 packages the
*next conversations* — pilot qualification, security review, admin
onboarding, deployment, support — so we can move from "the demo
went well" to "we're in a controlled-pilot" without missing safety
or scoping steps.

## Audience

- **Buyer-facing operators** running pilot conversations.
- **Practice operations / IT** preparing to host or co-host a
  controlled-pilot.
- **Practice security / compliance reviewers** evaluating the
  product before any real-PHI exposure.
- **Engineering / on-call** during the pilot.

## Docs produced

Eight new pilot docs under `docs/pilot/`, plus this top-level
contract and a Phase 14 section appended to the foundation doc.

| Doc | Purpose |
|-----|---------|
| `docs/pilot/chartnav-pilot-readiness-checklist.md` | Practical readiness checklist for pilot conversations and pilot setup (scope, data policy, RBAC, audit, retention, backup, deployment, support, exit criteria). |
| `docs/pilot/chartnav-pilot-deployment-guide.md` | Local / staging / controlled-pilot deployment modes, env-var inventory, migration / seed expectations, smoke + rollback checklists, sign-off list. |
| `docs/pilot/chartnav-admin-onboarding-checklist.md` | Sequence from "agreement signed" to "first provider session" — org / admin / clinician / reviewer setup, what to do before real PHI, what NOT to do during the pilot. |
| `docs/pilot/chartnav-security-review-packet.md` | Conservative security packet for the practice's security/compliance reviewer — provider-in-the-loop model, audit redaction posture, org isolation, RBAC, gating items before PHI, BAA / HIPAA language caution. |
| `docs/pilot/chartnav-support-runbook.md` | Severity levels, examples, support workflow, troubleshooting (local + pilot), data-safety incident escalation path, rollback / disable-pilot flow, known limitations. |
| `docs/pilot/chartnav-demo-to-pilot-transition-plan.md` | Demo → discovery → qualification → agreement → readiness → deploy → run → decision. Discovery questions, qualification checklist, timeline template, post-pilot decision framework. |
| `docs/pilot/chartnav-known-limitations-and-non-goals.md` | Blunt buyer-safe summary of what ChartNav is **not** and what it **does not do**. v1 generator limitations. Operational limitations. Items requiring legal / security review. Deferred capabilities. |
| `docs/pilot/chartnav-pilot-success-metrics.md` | Measurement template (10 metrics) with baseline / target / reading / delta. Conversion criteria for paid pilot / paid customer. Explicit "what this template does NOT promise." |

## Readiness tests

- `apps/web/src/test/PilotReadinessClaims.test.tsx` — vitest suite
  asserting:
  - all eight pilot docs (plus this top-level Phase 14 doc) exist
    on disk;
  - each doc includes the required headings;
  - forbidden positive claims (HIPAA compliant, certified EHR,
    autonomous diagnosis, automatic orders, submit referral, etc.)
    appear only inside safe contexts (negative-assertion lines,
    enumerated forbidden-phrase lists, Q&A question headings whose
    answers are negative assertions);
  - the readiness checklist explicitly states "real PHI only after
    proper agreements / security review" or equivalent;
  - the readiness checklist explicitly states the
    provider-review requirement.
- `scripts/check_pilot_readiness.sh` — a small shell script that
  verifies required pilot docs exist, greps for unsafe positive
  claims, and confirms no binary media is checked in under
  `docs/pilot/`. Suitable for ad-hoc local verification or a
  pre-pilot dry-run.

## What was hardened

This phase did not change any clinical behavior. What it hardened
is the *conversation around* the existing behavior:

- **Safe pilot language** — the docs use only the approved
  phrasing list ("provider-reviewed," "documentation support,"
  "ophthalmology-specific," "controlled-pilot," "designed to
  support"). Forbidden marketing claims are documented as such and
  asserted by tests.
- **Deployment expectations** — local / staging / controlled-pilot
  modes are documented with explicit posture for each (PHI
  permitted? auth mode? hosting? backups?). The env-var inventory
  is complete (and free of secrets).
- **Security review gating** — the items required before any real
  PHI are enumerated in one place, in the same words across
  multiple docs (the readiness checklist, the security packet, the
  admin onboarding checklist, and the demo-to-pilot transition
  plan).
- **Support contract** — severity levels, response targets, the
  data-safety incident escalation path, and the rollback /
  disable-pilot flow are documented before they are needed.

## What was intentionally not built

- **No new product feature.** Zero new endpoints, zero new
  components, zero new tables, zero new migrations.
- **No backend code changes.** The Phase 14 PR's `git diff` against
  `apps/api/` (excluding `tests/`) is empty.
- **No commercial deck.** Decks belong out-of-repo. This phase
  produces docs that *support* deck creation, not the deck itself.
- **No website / marketing-site changes.** Out of scope.
- **No desktop demo packaging.** Phase 15 will handle that.
- **No EHR adapter work beyond the existing FHIR adapter shape.**
  EHR integrations are pursued in dedicated phases.
- **No external LLM enabling.** Architecture leaves room; this
  phase does not flip the switch.

## How this relates to Phase 15

Phase 15's mission (per the Phase 13 contract doc's "Phase 14
candidate list" and the demo-to-pilot transition plan) is
**desktop demo packaging and commercial launch readiness**. Phase
14 is the bridge:

- A buyer's first impression is the Phase 13 in-app demo guide and
  the five-minute click path.
- Their second impression — once they ask "can we pilot?" — is the
  Phase 14 docs.
- Phase 15 will then make ChartNav *runnable on a buyer's laptop*
  for the in-room demo, without requiring `make dev` / `make boot`
  expertise.

Without Phase 14, the buyer hears "yes" to the pilot question and
ChartNav has nothing to show beyond the workspace. With Phase 14,
the buyer gets a packet they can hand to their security /
compliance reviewer and a deployment story that sounds boring (in
the good way).

## Known limitations

- **Not all "to confirm" items are answered yet.** The deployment
  guide and the security packet contain explicit "to confirm"
  flags where the answer depends on the practice (audit retention,
  hosting choice, monitoring destination, BAA terms). These are
  intentional placeholders, not docs gaps.
- **Pilot success metrics are templates, not promises.** No
  numeric improvement is claimed. Every metric has placeholders for
  baseline / target / reading / delta filled in by the practice.
- **The docs-claims test is heuristic.** It accepts negative-
  assertion lines, forbidden-list bullet entries, and Q&A question
  headings whose followers are negatives. A pathological doc
  author could craft a positive claim that escapes the classifier.
  The Phase 13 component-level rendered-DOM tests and the
  per-phase audit-redaction tests in earlier phases backstop this.
- **No new test infrastructure.** This phase reuses the existing
  vitest + repo-relative file reading pattern from Phase 13's
  package test.

## Next phase recommendation

**Phase 15 — desktop demo packaging and commercial launch
readiness.** Specifically:

1. A one-click demo runner (Mac / Windows / Linux) that boots a
   local SQLite stack and opens the workspace in the default
   browser — no `make` required.
2. A signed (or at least verifiable) demo build artifact for
   handing to a buyer who wants to "play with it on the plane."
3. Cleanup of the `staging` deploy story for buyer-side preview
   demos that don't run on the buyer's laptop.
4. Optional: a short investor-facing version of the demo workflow
   guide (still safe-language only).

Phase 15 must continue to obey the existing safety contract — no
new clinical features pulled forward, no autonomous diagnosis, no
orders / coding / referral / patient messaging.
