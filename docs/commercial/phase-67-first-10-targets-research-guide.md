# ChartNav — Phase 67 First-10 Targets Research Guide

> **What this is.** A 90-minute Monday-morning research workflow
> that produces the first 10 prospect rows for
> `docs/commercial/phase-67-first-pilot-prospect-list-template.md`.
> Concrete actions, not strategic framing. The strategic framing
> already lives in
> `docs/commercial/phase-66-prospect-targeting-brief.md`.

## 0. Pre-flight (5 minutes)

Before starting research, confirm three things:

1. **Phase 63C buyer-demo functional smoke is green** on the
   operator's local stack:
   ```bash
   PHASE63C_API_URL="http://127.0.0.1:8765" \
   PHASE63C_WEB_URL="http://127.0.0.1:5173" \
   bash scripts/demo/phase63c_functional_smoke.sh
   ```
   Expected: `BUYER-DEMO FUNCTIONAL GO: YES`. If the smoke is
   not green, do not research prospects — fix the smoke first.
2. **The four Phase 66 commercial docs are open in tabs:**
   - `phase-66-prospect-targeting-brief.md`
   - `phase-66-founder-led-outreach-templates.md`
   - `phase-66-buyer-discovery-questions.md`
   - `phase-66-what-not-to-promise-cheat-sheet.md`
3. **A blank prospect-list spreadsheet is open** with the 10
   columns from
   `phase-67-first-pilot-prospect-list-template.md` § 1.

## 1. Source order (90 minutes total)

Research in this order. The order is not arbitrary — it
reflects conversion-rate confidence per
`phase-66-prospect-targeting-brief.md` § 5.

### 1.1 Personal network (30 minutes — aim for 4-6 of the 10)

Open the operator's existing contacts (phone contacts, email
archive, message threads with provider friends). For each
contact who is an ophthalmologist, retina specialist,
optometrist with a meaningful ophth referral panel, or a
provider-owner of a small eye-care practice:

1. Confirm specialty tier (Rank 1 retina, Rank 2 glaucoma /
   general ophth, Rank 3 multi-specialty eye-care) using
   `phase-66-prospect-targeting-brief.md` § 1.
2. Confirm the contact is an owner-operator, managing
   physician, or a practice manager / operations lead who can
   make a paid-pilot decision. If the contact is a salaried
   provider with no operational authority, mark `Decision-maker
   role = unknown` and **deprioritize** (do not include in the
   first 10).
3. Capture a one-sentence reason for outreach grounded in real
   shared context: residency / fellowship classmate, conference
   meeting in the last 24 months, prior shared workflow
   discussion, mutual contact who has agreed to refer.
4. Add a row to the prospect list. `Source / referral` =
   `personal-network`; the `Notes` cell names the contact's
   relation in one phrase.

**Time-box: 30 minutes.** If you find 6 strong personal-network
prospects, stop. If you find only 2-3, that's also fine — fill
the rest of the 10 from § 1.2 and § 1.3.

### 1.2 Conference contacts (20 minutes — aim for 2-4 of the 10)

Open the conference-attendee notes from the last 24 months
(ASRS, AAO, ASCRS, AAOPT, AOA, regional chapter meetings).
For each contact whose card / notes survive:

1. Confirm tier per § 1.1 step 1.
2. Confirm owner-operator authority per § 1.1 step 2.
3. If they spoke at the conference and the talk topic
   intersects with documentation burden / structured intake /
   handoff friction / after-hours charting, that's a strong
   warm-path signal. Note the talk title in the `Notes` cell.
4. Add the row. `Source / referral` = `conference (<event +
   year>)`.

If conference notes are thin, skip § 1.2 entirely — do not
fabricate. Move to § 1.3.

### 1.3 LinkedIn search (25 minutes — aim for the remaining 2-4 of the 10)

Open LinkedIn search. Use these exact search patterns (in the
order shown):

1. **Strongest:** `(retina OR vitreoretinal) AND ("private practice" OR "practice owner")` filtered to your region.
2. **Strong:** `(ophthalmology) AND ("practice owner" OR "managing partner")` filtered to your region.
3. **Acceptable:** `(retina specialist OR ophthalmologist) AND ("solo practice" OR "small practice")` filtered to your region.

For each result on the first page that matches:

1. Confirm tier per § 1.1.
2. Look for owner-operator signals in the prospect's profile
   summary: "owner," "founder," "managing partner," "principal
   physician."
3. **Critical:** verify the prospect's published positioning
   does not include a Phase 64 § B disqualifier as their main
   product position (e.g., a provider whose published bio
   emphasises ambient-scribe AI evangelism is a soft
   disqualifier for ChartNav's positioning).
4. Add the row. `Source / referral` = `linkedin-search`;
   `Notes` records the exact search pattern + filter used.

**Do not send connection requests yet.** Research only at this
stage. Day-0 outreach happens via
`phase-67-outreach-execution-log.md` § 1.

### 1.4 Direct research (15 minutes — fill any gaps to reach 10)

If § 1.1 + § 1.2 + § 1.3 produced < 10 prospects, fill the
remaining slots from public practice directories:

- AAO public directory.
- ASRS public member directory.
- State medical-board practice listings.
- Practice websites linked from those directories.

Apply the same tier + authority + disqualifier screen. The
`Source / referral` for these rows is `direct-research (<URL>)`.

**Hard stop at 10.** Do not exceed 10 in the first list.

## 2. Signals that matter (during research)

Per `phase-66-prospect-targeting-brief.md` § 2 / § 3, the
research is looking for:

- **Specialty tier** (Rank 1 / 2 / 3 — Rank 4-5 excluded from
  the first 10).
- **Practice size** (solo-to-3-provider preferred; 4-8 with a
  named champion acceptable).
- **Owner-operator authority** of the named contact.
- **EHR signal** (ModMed / Eye Care Leaders / Compulink /
  Revolution → fit; Epic / Cerner / Oracle Health → defer).
- **Documentation-burden signal** from a published source (talk,
  podcast interview, blog post, public-LinkedIn-post mentioning
  after-hours charting).

## 3. Signals that disqualify (immediately, before adding to list)

If any of these is true from public research, **do not add** the
prospect to the first 10:

- Health-system / academic-medical-center affiliation (Rank 5
  deferred).
- Public positioning as an ambient-scribe evangelist / AI-scribe
  product reseller.
- Public positioning as a HIPAA-compliance consultant /
  vendor (asymmetry creates conflict on the safety frame).
- Active investor / board member of a directly competing
  documentation-tool company.
- Recent public statement requiring HIPAA certification /
  SOC 2 / HITRUST as a procurement precondition.
- Any signal the prospect requires real-PHI processing on day
  one with no security-review tolerance.

Each of these maps to a Phase 64 § B disqualifier and would
predict `closed-no-fit` in Cycle 1. Skip in research.

## 4. What NOT to collect

ChartNav is pre-pilot. Research stays narrow. Do **not** collect:

- **Phone numbers** unless the prospect's practice website
  publishes a main line that's intended for general inbound
  inquiries.
- **Personal email addresses** scraped from non-published
  sources.
- **Home addresses** of any kind.
- **Spouse / family / staff** names of the prospect.
- **Patient counts, revenue figures, financial data** beyond
  what the prospect themselves has publicly published.
- **Medical record system credentials** of any kind. Ever.
- **Personal social media beyond LinkedIn** unless the prospect
  has a public professional Twitter / X / Mastodon account they
  themselves use for ophthalmology content.
- **Photos** of any kind beyond the prospect's professional
  LinkedIn / practice-website headshot.

## 5. Anti-spam rules

- **One platform per prospect for Day-0.** Either email or
  LinkedIn, not both simultaneously.
- **No automation tools** (Apollo, ZoomInfo, Lemlist, Hunter,
  Snov, etc.) for the first 10. Manual research only.
- **No scraped contact lists** of any kind.
- **No bulk email sends** (BCC, mailmerge, sequence tools).
  Each Day-0 send is individually composed.
- **No re-contact after `paused`** without a new substantive
  reason (e.g., a public talk by the prospect that names the
  problem ChartNav addresses).
- **No re-contact after `closed-no-fit`** within 90 days. If
  90 days pass and a disqualifier has genuinely dissolved
  (e.g., the practice's EHR strategy changed), the operator can
  re-research the prospect from scratch.

## 6. Quality gates before § 1 outputs go into outreach

The 10-row list is **not** ready for Day-0 outreach unless all
five gates pass:

1. All 10 rows have non-empty `Ideal target category`,
   `Practice name`, `Location`, `Specialty / workflow fit`,
   `Decision-maker role`, `Source / referral`.
2. At least 50% are from `personal-network` or
   `existing-relationship` (warm paths).
3. Zero rows fire any Phase 64 § B disqualifier from public
   research alone.
4. Zero rows have `Decision-maker role = unknown`.
5. Zero rows mention real PHI, real credentials, or unsupported
   claims in `Notes`.

If any gate fails, fix the row(s) before Day-0. Don't ship
sloppy research into outreach.

## 7. 90-minute time-box discipline

| Block | Time | Output |
|---|---|---|
| Pre-flight checks | 5 min | Smoke green, tabs open, blank list open |
| § 1.1 personal network | 30 min | 4-6 rows |
| § 1.2 conference contacts | 20 min | 2-4 rows |
| § 1.3 LinkedIn search | 25 min | 2-4 rows |
| § 1.4 direct research (fill gaps) | 15 min (or skip) | 0-2 rows |
| § 6 quality gates | 5 min | 10 valid rows |

**If 90 minutes is up and the list has fewer than 10 valid
rows:** ship the list with what you have. Do not stretch the
research session past 2 hours; tiredness produces sloppy
positioning and sloppy positioning trips the safety frame.

## 8. After the list is complete

1. Save the spreadsheet locally. **Do not share the list
   externally** (per `phase-64-outreach-tracker-schema.md` § 0).
2. Open `docs/commercial/phase-67-outreach-execution-log.md` § 1
   and begin Day-0.
3. Set calendar reminders for Day-3 and Day-7 follow-ups per
   prospect.
4. Open `docs/commercial/phase-66-what-not-to-promise-cheat-sheet.md`
   in a side pane and leave it open during every outreach
   session.

## 9. Safety note

- Fake-data demo first.
- Paid pilot subject to security review for any real-PHI use.
- Provider review and sign-off required on every artefact.
- ChartNav is not HIPAA-certified.
- ChartNav is not a certified EHR and does not replace any EHR.
- ChartNav does not diagnose.
- ChartNav does not interpret fundus or OCT images.
- ChartNav does not place orders, send referrals, or message patients.
- ChartNav does not bill or code.
- ChartNav does not integrate with medical devices and does not provide remote patient monitoring.

## Related documents

- `docs/build/current-product-truth.md`
- `docs/commercial/phase-66-prospect-targeting-brief.md`
- `docs/commercial/phase-66-founder-led-outreach-templates.md`
- `docs/commercial/phase-66-buyer-discovery-questions.md`
- `docs/commercial/phase-66-what-not-to-promise-cheat-sheet.md`
- `docs/commercial/phase-67-first-pilot-prospect-list-template.md`
- `docs/commercial/phase-67-outreach-execution-log.md`
