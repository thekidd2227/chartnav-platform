# ChartNav Commercial Launch Package (Phase 17)

> Top-level contract for the Phase 17 commercial launch package.
> Phase 17 ships the ChartNav commercial deck library, the
> commercial support docs, the local demo launcher, and the
> desktop demo delivery package script.
>
> Phase 17 is **docs-and-tooling only**. No new clinical
> automation. No backend changes. No new schema. No external
> LLM. No real-PHI claim. No unsupported HIPAA / SOC 2 / FDA /
> certified-EHR claim. No binary media in the repo.

---

## Goal

After Phase 16 the public landing page tells a buyer what
ChartNav is in under 60 seconds. Phase 17 gives the operator
the rest of the commercial surface they need to actually run
sales conversations:

- 17 deck Markdown source files spanning every recurring sales
  / investor / partner / onboarding scenario (Phase 17 + 17B —
  the original 15 decks plus the buyer-demo / operator-demo
  split introduced in 17B).
- 6 commercial support docs (master kit, approved-claims
  language, objections, pricing, pilot handoff, readiness map).
- 4 demo-package docs (local demo startup guide, troubleshooting,
  review checklist, desktop demo delivery contract).
- 3 shell scripts that produce a presenter-ready Desktop folder
  with one double-click `START_CHARTNAV.command`,
  `STOP_CHARTNAV.command`, and `RESET_DEMO_DATA.command` files.
- 1 vitest suite that asserts every deck / support doc /
  demo-package doc / script exists, references the safe-claims
  contract, contains no forbidden positive claims, invents no
  financial numbers, and preserves the local-DB safety guard.

A presenter on the operator's Mac should be able to open
`/Users/jean-maxcharles/Desktop/chartnav decks/`, find every
commercial deck and demo doc in one organized folder, double-
click `START_CHARTNAV.command` to boot ChartNav locally, run
the demo, and double-click `STOP_CHARTNAV.command` and
`RESET_DEMO_DATA.command` to tear down — without going hunting
in the repo.

---

## Audience

- ChartNav operators (Jean-Max + Maria) running live
  buyer / investor / partner conversations.
- Future ChartNav employees who need to know which deck to use
  for which audience and what claims they can and cannot make.
- Pilot practices reviewing ChartNav before signing a BAA.

---

## What Phase 17 ships

### 17 deck Markdown source files (`docs/decks/`)

Each is a slide-by-slide Markdown source — title, audience,
purpose, CTA, content, speaker notes, visual cue, safe-claims
note. The operator (or a downstream pitch tool) renders them
into the final visual format out-of-repo.

Phase 17B adds **Clinical Signal Filtering** as the prime
buyer-facing feature line ("Filters conversation. Captures
findings. Builds the diagram.") on every deck where it is
buyer-relevant, and splits the original combined demo deck into
a **buyer demo deck** (no terminal commands or repo paths) and
an **operator demo deck** (internal pre-flight rehearsal only).

| Deck | Audience | SDVOSB / VA framing |
|---|---|---|
| `chartnav-investor-pitch-deck.md` | Investors / advisors | yes |
| `chartnav-sales-deck.md` | Private-practice ophthalmology | no |
| `chartnav-demo-deck.md` | **Index** — routes to buyer or operator deck | no |
| `chartnav-buyer-demo-deck.md` | Used **during** a live buyer demo | no |
| `chartnav-operator-demo-deck.md` | **Internal** rehearsal — never shown to a buyer | no |
| `chartnav-customer-pitch-deck-template.md` | Per-practice template | no |
| `chartnav-company-deck.md` | Mixed — slide 8 is the federal credibility track | yes (slide 8 only) |
| `chartnav-product-roadmap-deck.md` | Investors + practices | no |
| `chartnav-brand-guidelines-deck.md` | Internal | catalog of banned phrases |
| `chartnav-educational-onboarding-deck.md` | Pilot users | no |
| `chartnav-one-page-sales-deck.md` | Email follow-up | no |
| `chartnav-financial-fundraising-deck.md` | Investors | optional |
| `chartnav-marketing-plan-deck.md` | Internal | yes |
| `chartnav-project-proposal-deck.md` | Per-practice template | no |
| `chartnav-agency-partner-pitch-deck.md` | Agencies / advisors | yes |
| `chartnav-elevator-pitch-deck.md` | 60-second pitch | no |
| `chartnav-long-sales-pitch-deck.md` | Detailed sales | no |

### 6 commercial support docs (`docs/commercial/`)

| Doc | Purpose |
|---|---|
| `chartnav-deck-master-kit.md` | Master narrative, buyer personas, reusable slide language |
| `chartnav-approved-claims-language.md` | Approved / forbidden / caution table; substitution map |
| `chartnav-commercial-readiness-map.md` | What's demo-ready / pilot-ready / not yet ready |
| `objections/chartnav-buyer-objection-handling.md` | 12 common objections with safe answers |
| `pricing/chartnav-pricing-packaging-notes.md` | Per-provider / per-practice / pilot / discount tiers |
| `pilot/chartnav-pilot-handoff-checklist.md` | Demo → pilot transition gate |

### 4 demo-package docs

| Doc | Purpose |
|---|---|
| `docs/commercial/demo-package/chartnav-local-demo-startup-guide.md` | One-time setup + boot the stack + open the right URL + reset between demos + stop the stack |
| `docs/commercial/demo-package/chartnav-local-demo-troubleshooting.md` | 12 common issues with first-line fixes |
| `docs/commercial/demo-package/chartnav-demo-review-checklist.md` | 24h / 1h / 5min / during / after demo dry-run checklist |
| `docs/chartnav-desktop-demo-delivery-package.md` | Source-of-truth contract for the Desktop folder |

### 3 shell scripts (`scripts/`)

| Script | Behavior |
|---|---|
| `export_chartnav_decks_to_desktop.sh` | Builds the Desktop folder from the source-of-truth contract. Idempotent. Generates README + 3 .command files + marks them executable. |
| `create_chartnav_desktop_demo_package.sh` | Thin orchestrator — runs the export, then verifies every expected file landed and every .command file is executable. |
| `check_commercial_claims.sh` | Pre-merge sanity check: required files exist, no forbidden positive claims, every deck references the safe-claims contract, the local-DB guard is intact, the .gitignore covers the Desktop folder, no binary media slips. |

### 1 vitest test (`apps/web/src/test/`)

`CommercialDeckClaims.test.tsx` — 96 assertions across 12
describe blocks (Phase 17 + 17B):

1. Required files exist (17 decks + 6 support + 4 demo-package +
   3 scripts).
2. Every deck references the safe-claims contract.
3. Forbidden positive claims appear only in safe contexts (the
   approved-claims-language / brand-guidelines "Never use" /
   buyer-objection-handling "Don't say" catalog docs are
   exempted).
4. No deck invents financial numbers (revenue / runway /
   valuation / bare conversion percentages).
5. The reset-script safety guard is preserved (refuses non-local
   `DATABASE_URL`).
6. No binary media is committed under `docs/decks/`,
   `docs/commercial/`, or `docs/demo/`.
7. Pricing constants ($299 / $499 / $5,000 / $10,000) appear
   consistently in the four decks that quote pricing.
8. The Desktop-folder safety contract is recorded in the Phase 17
   contract doc and the Desktop folder is in `.gitignore`.
9. **Phase 17B — Clinical Signal Filtering surfaces in every
   buyer-relevant deck** (the brand-guidelines / operator-demo /
   index decks are exempt by path).
10. **Phase 17B — buyer-facing decks contain no repo-leak /
    operator-only references** (no terminal commands, no repo
    paths, no `?demo=1` / `?intro=1` query strings, no
    operator's-note phrasing).
11. **Phase 17B — every deck declares Audience + Purpose +
    CTA** in its front-matter so any operator can pick up any
    deck cold.
12. **Phase 17B — operator-demo deck stays internal-only** and
    the buyer-demo deck contains no `START_CHARTNAV` /
    `STOP_CHARTNAV` / `RESET_DEMO_DATA` references or
    `make dev` commands.

---

## What Phase 17 deliberately does not ship

- **Binary deck exports.** The repo carries Markdown source. PDF
  / .pptx / .key conversion happens out-of-repo.
- **A separate marketing or pitch site.** The public website is
  the React app at `apps/web/`. Phase 16 added the landing
  page; Phase 17 does not change it.
- **Out-of-repo media.** Screenshots, video clips, voice-over
  recordings — captured by the operator out-of-repo per the
  Phase 13 / 16 shot lists.
- **Real PHI in any environment.** Local demo is fake-data only
  by construction; the reset script refuses non-local
  `DATABASE_URL`.
- **New clinical automation.** No orders, coding, referrals, or
  patient messaging. No autonomous diagnosis. No external LLM.
- **Pricing changes.** The pricing block locked in this phase is
  a hypothesis until paid-pilot data validates it. The pricing-
  notes doc explicitly enumerates what is hypothesis vs. firm.

---

## Safe-claims contract

Every deck and every support doc obeys the same approved-claims
language used by Phases 13 / 14 / 15 / 16:

- **Forbidden positive claims** — HIPAA-compliant, HIPAA-
  certified, SOC 2-certified, HITRUST-certified, FDA-cleared,
  certified EHR, autonomous diagnosis, automatic diagnosis,
  guaranteed accuracy, automatic orders, order OCT, submit
  referral, send referral, billing automation, coding
  automation, send patient message, replaces a doctor,
  production-ready for PHI, real patient data ready.
- **Allowed framings** — "ChartNav does not …", "Not …",
  "Never …", explicit forbidden-phrase enumerations under a
  "Never use" / "Don't say" header, Q&A question headings whose
  answers are negative assertions, and table rows in a
  forbidden-list table.
- **Catalog docs exempted** — `chartnav-approved-claims-
  language.md`, `chartnav-brand-guidelines-deck.md` slide 5
  ("Never use"), and `chartnav-buyer-objection-handling.md`
  ("Don't say:" blocks) exist *to* enumerate banned phrases.
  The vitest suite and the claims-check script both exempt
  them by path.

The vitest suite at `apps/web/src/test/CommercialDeckClaims.test.tsx`
is authoritative. The shell script at
`scripts/check_commercial_claims.sh` is a lightweight pre-merge
sanity check.

---

## SDVOSB / VA past-performance framing

ARCG Systems (the operating entity) carries SDVOSB / HUBZone /
DBE / MBE / SBE / NMSDC certifications attached to the operating
company, not to the software product. Mann-Grandstaff VA Medical
Center past performance attaches to ARCG Systems' federal
contracting work, not to ChartNav clinically.

Per the Q25 contract, this credibility framing appears only on:

- `chartnav-investor-pitch-deck.md` (slide 11 — "Moat +
  credibility"),
- `chartnav-company-deck.md` (slide 7 — "Operating-entity
  credibility"),
- `chartnav-agency-partner-pitch-deck.md`,
- `chartnav-marketing-plan-deck.md` (internal go-to-market plan).

It does **not** appear on the private-practice sales deck, the
demo deck, the customer pitch template, the one-page sales deck,
or the long sales pitch deck — those are clinical-buyer audiences
for whom federal credentials are not the relevant signal.

---

## Pricing contract

The pricing block is locked across this phase:

- **Per-provider monthly subscription:** $299–$499 per provider
  per month (range published; specific tier set per practice
  agreement).
- **Per-practice flat tier:** $5,000 per practice per month flat
  (covers up to the agreed provider count; over-cap usage
  bills per-provider).
- **Pilot fee:** $10,000 flat for a 4–6 week pilot. Pilot fees
  are not discounted.
- **Multi-practice annual discounts:** 2–4 practices = 10% off,
  5–9 practices = 15% off, 10+ practices = enterprise terms.

Pricing is a **hypothesis** until paid-pilot data validates it.
The pricing-notes doc enumerates what is firm (the pilot fee,
the discount tier breakpoints) and what needs validation (the
per-provider / per-practice numbers themselves).

---

## Milestones

The roadmap deck and the financial deck both quote the same
target dates:

- **M1 — first paid pilot** (target Jul 1, 2026).
- **M2 — second paid pilot** (target Oct 1, 2026).
- **M3 — first paying customer post-pilot** (target Q4 2026).
- **M4 — multi-practice deployment** (target Q4 2026).

These are targets, not committed delivery dates. The decks frame
them as such; the vitest suite enforces that framing.

---

## Desktop demo delivery package

`scripts/export_chartnav_decks_to_desktop.sh` produces the
Desktop folder at `/Users/jean-maxcharles/Desktop/chartnav
decks/` (override via `CHARTNAV_DESKTOP_DIR`). The folder
structure and source-of-truth mapping is locked in
`docs/chartnav-desktop-demo-delivery-package.md`:

```
chartnav decks/
├── README.md
├── 00_START_HERE/
├── 01_Decks/
├── 02_One_Pagers/
├── 03_Demo_Package/
├── 04_Pilot_Sales/
├── 05_Objection_Handling/
├── 06_Pricing_Packaging/
├── 07_Website_Proof/
├── 08_Local_Demo_Launcher/
└── 09_Review_Checklists/
```

The launcher folder (`08_Local_Demo_Launcher/`) ships three
double-click scripts:

| Script | Behavior |
|---|---|
| `START_CHARTNAV.command` | Opens Terminal, `cd`s into the repo at `/Users/jean-maxcharles/Desktop/ARCG/chartnav-platform` (override via `CHARTNAV_REPO_DIR`), runs `make dev`, opens the browser to `http://localhost:5173/?demo=1`. |
| `STOP_CHARTNAV.command` | Sends SIGTERM to processes bound to `:8000` (API) and `:5173` (frontend). Does not kill unrelated processes. |
| `RESET_DEMO_DATA.command` | Wraps `bash scripts/reset_demo_state.sh`. The underlying script refuses to run if `DATABASE_URL` is not a local `sqlite:///<path>`. |

All three are marked executable by the export script.

---

## Safety rules baked into the export

1. The Desktop folder is **never committed** to the repo. The
   generated paths are listed in `.gitignore`. The repo source is
   the only source of truth.
2. The export script does **not embed real secrets**. It reads
   only from `docs/`, `scripts/`, and the brand assets — all of
   which are already public-safe.
3. The reset script **refuses non-local DB URLs**. The
   `EXPECTED_PREFIX="sqlite:///"` guard in
   `scripts/reset_demo_state.sh` gates the
   `RESET_DEMO_DATA.command`.
4. **No binary media** is generated by the export. Every file on
   the Desktop is a Markdown / shell / text file copy of a
   Markdown / shell / text file from the repo.

---

## Re-export workflow

Whenever any source doc updates:

```
bash scripts/export_chartnav_decks_to_desktop.sh
```

…or the verifying wrapper:

```
bash scripts/create_chartnav_desktop_demo_package.sh
```

The script is idempotent. Running it twice produces the same
Desktop folder state.

---

## How Phase 17 relates to Phase 18

Phase 18 is **first paid pilot or paid customer** — operations
work, not new product. Required: signed pilot agreement,
controlled-pilot infrastructure stood up, real-PHI gating items
met, live success-metrics tracking. Target M1 = July 1, 2026.

Phase 18 must continue to obey the existing safety contract —
no new clinical features pulled forward, no autonomous
diagnosis, no orders / coding / referrals / patient messaging.

The Phase 17 commercial launch package is the inventory Phase 18
sells from. If a Phase 18 conversation needs a deck that does
not yet exist (e.g., a one-page hospital-system memo), the
right move is to add the deck source to `docs/decks/`, update
the source-of-truth contract in
`docs/chartnav-desktop-demo-delivery-package.md`, and re-run
the export — not to invent the deck out-of-repo.

---

## Test contract

```
cd apps/web
npx vitest run src/test/CommercialDeckClaims.test.tsx
```

Expected: **96 tests passed.**

```
bash scripts/check_commercial_claims.sh
```

Expected: **PASSED — 0 fail / 0 warn.**

```
bash scripts/export_chartnav_decks_to_desktop.sh
```

Expected: 41 source files copied · 1 README + 3 .command files
generated · 4 presentation-assets docs copied · **17 branded
PPTX presentations generated** under `01_Decks/PPTX/` and
`02_One_Pagers/PPTX/` (Phase 17D) · summary tree printed.
(Phase 17 = 39 source files; Phase 17B adds the buyer-demo +
operator-demo decks for a total of 41; Phase 17D adds the PPTX
outputs and the `10_Presentation_Assets/` folder.)

---

## Phase 17 deliverable summary

- 17 deck Markdown source files (`docs/decks/`) — original 15
  + Phase 17B buyer-demo / operator-demo split.
- 6 commercial support docs (`docs/commercial/`).
- 4 demo-package docs (3 under
  `docs/commercial/demo-package/` + this contract at the
  `docs/` root + the desktop-delivery contract at the `docs/`
  root).
- 3 shell scripts (`scripts/export_chartnav_decks_to_desktop.sh`,
  `scripts/create_chartnav_desktop_demo_package.sh`,
  `scripts/check_commercial_claims.sh`).
- 1 vitest claims-tests file
  (`apps/web/src/test/CommercialDeckClaims.test.tsx`).
- This top-level contract.
- A foundation-doc Phase 17 section.

The Desktop folder is the *consumed* output of Phase 17, not
part of the repo's source tree.
