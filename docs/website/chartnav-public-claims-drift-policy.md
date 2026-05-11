# ChartNav Public-Claims Drift Policy

> **Phase:** 24A.
> **Type:** Policy + operational runbook for keeping the live
> `chartnavmd.com` deployment consistent with the repo's
> safe-claims contract.

## 1. The problem this policy solves

Manus's audit (May 2026) surfaced a gap:

- **The repo's claims discipline is conservative.** Every shipped
  surface — decks, demo scripts, landing page, objection handling
  — passes the existing `scripts/check_commercial_claims.sh` and
  `scripts/check_website_claims.sh` with 0 fail / 0 warn.
- **The live `chartnavmd.com` deployment, however, was found to
  carry overclaiming language** — "hands-free scribing," "replace
  your EHR," "chart fills itself," "note writes itself,"
  IBM/watsonx-powered framing.
- **Why the gap exists:** the live `chartnavmd.com` site is **not
  in this repo.** It is an externally-deployed static site
  (history references `thekidd2227/chartnavmd-site`, which is
  empty — production runs from CLI-uploaded deploys). The repo's
  pre-commit / CI claims-check scripts cannot see live HTML; they
  scan only repo-controlled docs, decks, and `LandingPage.tsx`.

## 2. What "in scope" means for this policy

| Surface | Repo-controlled? | Drift risk |
|---|---|---|
| `apps/web/src/LandingPage.tsx` (`/landing` or `?intro=1`) | ✅ Yes | Low — scanned by vitest + claims-check |
| `apps/web/index.html` SEO metadata | ✅ Yes | Low — scanned by claims-check |
| `docs/decks/*.md` buyer decks | ✅ Yes | Low — scanned by claims-check + vitest |
| `docs/commercial/**/*.md` | ✅ Yes | Low — scanned by claims-check |
| `docs/security/**/*.md` | ✅ Yes | Low — explicit negative assertions |
| **`chartnavmd.com` production HTML** | ❌ **No** | **HIGH — externally deployed; no automatic gate** |
| Marketing-team-edited landing-page CMS (if any) | ❌ No | High |
| Investor / partner emails | ❌ No | Practice-side risk |

## 3. The Phase 24A drift-detection contract

To close the gap, Phase 24A ships three additions:

### 3.1 `scripts/check_live_site_claims.sh`

Operator captures live HTML out-of-band (`curl -sL https://chartnavmd.com/
-o /tmp/chartnavmd-live.html`) and runs:

```bash
bash scripts/check_live_site_claims.sh /tmp/chartnavmd-live.html
```

The script:

- **Never** fetches the network. The operator captures HTML
  out-of-band.
- **Never** prints secrets.
- Scans for ~50 forbidden positive-claim patterns (hands-free,
  chart fills itself, replace your EHR, powered by IBM /
  watsonx, HIPAA-compliant, certified EHR, autonomous diagnosis,
  auto-interpret OCT, auto-grade DR, auto-select IOL,
  auto-recommend anti-VEGF, automatic charting / orders /
  referrals / coding / billing, patient messaging, submit
  claims, IRIS Registry submission, MIPS submission, etc.).
- Applies the same negative-context guard as
  `check_commercial_claims.sh` — phrases inside "does not", "do
  not", "never", "not …" are exempted.
- Exits non-zero on any positive-claim hit.

Multiple files / directories are supported:

```bash
bash scripts/check_live_site_claims.sh /tmp/chartnavmd-captured/
```

### 3.2 Extended `scripts/check_commercial_claims.sh`

Phase 24A adds 18 tokens to `FORBIDDEN_CAPABILITY` (hands-free
scribing, chart fills itself, note writes itself, replace your
EHR / EMR, EHR / EMR replacement, powered by IBM / watsonx,
billing-aware coding, coding recommendations). Existing
negative-context guard applies.

### 3.3 Strengthened `WebsiteProofUpgrade.test.tsx`

The vitest test that gates the landing page now bans the Phase
24A positive-claim phrases. Negative-assertion contexts ("does
not autofill IOP", "does not replace your EHR") are still
allowed; positive forms break the test.

## 4. Operator workflow — pre-publish + cadence

### 4.1 Before any `chartnavmd.com` content change

```bash
# 1. Capture the proposed live HTML (after the marketing edit
#    but before the publish push):
curl -sL https://staging-chartnavmd.example.com/ \
  -o /tmp/chartnavmd-staging.html

# 2. Run the drift detector:
bash scripts/check_live_site_claims.sh /tmp/chartnavmd-staging.html

# 3. If FAIL → fix the staging copy → re-capture → re-scan.
#    If PASS → safe to publish.
```

### 4.2 Weekly cadence (drift hunt)

```bash
# Capture the current production HTML:
curl -sL https://chartnavmd.com/ -o /tmp/chartnavmd-live-$(date +%Y%m%d).html

# Scan it:
bash scripts/check_live_site_claims.sh /tmp/chartnavmd-live-$(date +%Y%m%d).html

# File the result (PASS or FAIL) in the marketing-side log.
```

### 4.3 Incident: positive claim found on live `chartnavmd.com`

1. Capture the offending HTML immediately.
2. File the incident as SEV-3 (or SEV-2 if the claim is HIPAA /
   certified-EHR / device-vendor — those carry contractual /
   regulatory risk).
3. Roll back the live-site change (via the marketing team's
   deploy tooling).
4. Re-capture and re-scan to confirm the offending copy is gone.
5. Add the specific phrase to `scripts/check_live_site_claims.sh`
   if it isn't already on the list.
6. Post-incident: write a short note to the practice security
   owner if any HIPAA-related claim was live for any duration.

## 5. What this policy does NOT do

- Does **not** publish or modify the live site. Every change to
  `chartnavmd.com` happens through the marketing team's deploy
  tooling. This policy is a drift detector, not a publish path.
- Does **not** scan rich-content surfaces (PDF brochures,
  YouTube transcripts, etc.). Those carry their own drift risk
  and need their own scans.
- Does **not** scan investor / partner emails. Those are
  practice-side governance.
- Does **not** replace human review. The drift detector is a
  regex safety net; specific phrasing or context can still be
  technically clean but commercially misleading.
- Does **not** approve real-PHI deployment. That gate lives in
  `docs/security/chartnav-real-phi-go-live-gate.md`.

## 6. Future hardening

- A CI job could fetch `chartnavmd.com` weekly and run the drift
  detector, posting failures as a GitHub issue. Out of scope for
  Phase 24A (would couple the repo's CI to a live external
  domain). Phase 24B candidate.
- A GitHub-action-based scheduled scan could automate §4.2.
  Phase 24B candidate.
- A marketing-side CMS pre-publish webhook could call the script
  before letting an editor publish. Phase 24B candidate, requires
  the CMS owner to opt in.

## 7. Ownership

- **ChartNav engineering** (this repo): maintains
  `scripts/check_live_site_claims.sh`, the forbidden-phrase
  list, and the vitest tests that gate the in-repo landing page.
- **ChartNav marketing / website owner**: runs the drift
  detector pre-publish + weekly; investigates failures; rolls
  back overclaiming live changes.
- **Practice security owner** (per pilot): receives
  notification if any HIPAA-related claim was live for any
  duration (see §4.3).

## 8. References

- `scripts/check_live_site_claims.sh` — Phase 24A drift detector.
- `scripts/check_commercial_claims.sh` — repo-side gate.
- `scripts/check_website_claims.sh` — landing-page gate.
- `apps/web/src/test/WebsiteProofUpgrade.test.tsx` — vitest gate.
- `apps/web/src/test/CommercialDeckClaims.test.tsx` — deck gate.
- `docs/commercial/chartnav-approved-claims-language.md` — master
  approved-language list.
- `docs/commercial/chartnav-ophthalmology-positioning-language-guide.md`
  — Phase 21C ophthalmology-specific language guide.
- `docs/security/chartnav-real-phi-go-live-gate.md` — Phase 23
  per-practice real-PHI gate.
