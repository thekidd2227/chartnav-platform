# ChartNav Live-Site Claims Scan — Operator Runbook

**Owner:** ChartNav release engineering
**Cadence:** pre-publish + weekly
**Source of truth:** `scripts/check_live_site_claims.sh` +
  `tests/claim_fixtures/` (fixture suite covered by
  `scripts/test_claim_policy_fixtures.sh`)

## What this runbook is for

The independent audit observed that ChartNav's repo passes every
claim scanner, but `chartnavmd.com` is published outside CI. This
runbook is the manual control loop that keeps the live site honest
between repo commits and the externally-deployed marketing page.

The runbook executes one command:

```
bash scripts/release/check_live_site_claims_snapshot.sh
```

…which captures the live HTML into a dated snapshot, runs
`scripts/check_live_site_claims.sh` against it, and writes a
PASS/FAIL summary to
`artifacts/live-site-snapshots/YYYYMMDD-HHMMSS/summary.txt`.

## When to run

| Event | Operator | Cadence |
|---|---|---|
| Before publishing any landing-page copy change | Editor + Eng | every publish |
| Weekly drift check | Release Eng | every Monday morning UTC |
| Before any pilot/buyer demo that references the live site | Eng | within 24h of demo |
| After an Anthropic / IBM / partner announcement is referenced in copy | Editor | same day |

## Pre-conditions

- The operator is on a workstation with outbound HTTPS to
  `chartnavmd.com`.
- The operator has cloned the repo at a known SHA.
- `curl` is installed.
- The operator is NOT logged in to the live admin / preview surface.
  The script issues an unauthenticated `curl` and never sends
  credentials.

## Forbidden positive-claim families the live-site scanner enforces

These mirror the in-repo `scripts/check_*_claims.sh` policy:

1. **Compliance claims** — "HIPAA compliant", "HIPAA certified",
   "SOC 2 certified", "GDPR compliant", "FDA cleared". ChartNav is
   none of these.
2. **EHR claims** — "certified EHR", "EHR replacement", "replace
   your EHR", "drop-in EHR".
3. **Autonomous-clinical claims** — "autonomous diagnosis", "auto
   diagnosis", "automatic diagnosis", "diagnoses for you",
   "treatment recommendation", "automatic treatment".
4. **Autonomous-image-interpretation claims** — "interprets
   imaging", "reads OCT", "reads fundus", "AI radiology", "AI image
   interpretation".
5. **Autonomous orders / billing / coding / patient messaging** —
   "automatic orders", "auto-bills", "auto-codes", "sends claims",
   "texts patients", "messages patients automatically".
6. **Unsupported customer / proof claims** — "trusted by", "used by
   thousands", "X% revenue uplift", "X% time saved", "across N
   practices" without an explicit sourced reference.
7. **Unsupported IBM / watsonx claims** — "Powered by IBM
   watsonx" / "Powered by IBM" without the approved partnership
   language.

The exact regex set is in `scripts/check_live_site_claims.sh` —
that script is the source of truth; this runbook documents intent.

## Operator workflow

### Pre-publish scan

```bash
cd "$CHARTNAV_REPO_PATH"

# Snapshot + scan in one command.
bash scripts/release/check_live_site_claims_snapshot.sh

# Inspect the summary.
cat artifacts/live-site-snapshots/$(ls -1 artifacts/live-site-snapshots | tail -1)/summary.txt
```

- PASS → safe to publish; record the snapshot directory in the
  release ticket.
- FAIL → open `scanner.log` and the captured `*.html`, locate the
  offending phrase, request a copy edit, re-publish, re-snapshot.

### Weekly drift scan

```bash
cd "$CHARTNAV_REPO_PATH"

# Scan the canonical landing page plus any other pages we publish.
bash scripts/release/check_live_site_claims_snapshot.sh \
  https://chartnavmd.com/

# (Add more URLs as the marketing surface grows. Each becomes a
# separately-captured HTML file in the snapshot directory.)
```

If the scanner fails on a Monday:

1. File a ticket against the marketing repo (or wherever the live
   copy lives).
2. Hold any pending publish until the live page passes.
3. Re-run the snapshot script and attach the resulting dated
   directory path to the ticket.

### Forensic mode (manual capture)

If `curl` cannot reach the live host but the operator needs an
ad-hoc scan (e.g. mobile-only WAF), the operator can capture the
HTML by hand and feed it to the underlying scanner directly:

```bash
# Capture from a browser → Save Page As → /tmp/manual-capture.html
bash scripts/check_live_site_claims.sh /tmp/manual-capture.html
```

The same forbidden-claim set applies.

## Failure modes + recovery

| Symptom | Likely cause | Recovery |
|---|---|---|
| `curl fail: <url>` | network blocked or host down | switch to manual capture (above), or wait + retry |
| `scanner.log` shows a positive-claim hit on language the editor swears was rewritten | live CDN cached an old version | cache-bust via the marketing host; re-snapshot |
| `scanner.log` flags a phrase from a third-party embedded widget | third-party script injected copy | escalate to the marketing host owner; do not silence the scanner |
| Snapshot directory grows large | accumulated weekly snapshots | retain 90 days; older directories may be archived / removed |

## What the runbook is NOT

- This is **not** a substitute for human review of marketing copy.
  The scanner is a regex safety net; an editor with clinical
  context still owns the substance.
- This is **not** automated CI. It is an operator-run control.
- This is **not** a replacement for the in-repo
  `scripts/check_website_claims.sh`, which audits
  repo-controlled docs and runs in CI.

## See also

- `scripts/check_live_site_claims.sh` — underlying scanner.
- `scripts/check_website_claims.sh` — in-repo website doc scanner
  (CI-enforced).
- `docs/website/chartnav-public-claims-drift-policy.md` — policy
  for when and how to update the forbidden-claim set.
- `docs/commercial/chartnav-approved-claims-language.md` — the
  approved positive-language list editors should pull from.
