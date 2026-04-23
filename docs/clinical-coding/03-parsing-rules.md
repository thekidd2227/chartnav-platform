# Parsing Rules

## Input file

CDC/CMS `icd10cm_order_<year>.txt` (fixed-width text, also shipped
as `icd10cm-order-<year>.txt` in some mirrors).

## Column contract (verified against FY2026 release)

| Position (1-indexed) | Slice (0-indexed) | Width | Content |
|----------------------|-------------------|-------|---------|
| 1–5                  | `[0:5]`           | 5     | sequential order number |
| 6                    | `[5]`             | 1     | space |
| 7–14                 | `[6:14]`          | 8     | diagnosis code (no decimal point) |
| 15                   | `[14]`            | 1     | billable flag (`0`/`1`) |
| 16                   | `[15]`            | 1     | space |
| 17–76                | `[16:76]`         | 60    | short description |
| 77                   | `[76]`            | 1     | space |
| 78–end               | `[77:]`           | var   | long description |

A leading '0' in the billable flag position means the row is a
category header (e.g. `H40` for glaucoma), not a billable terminal
code. The parser still yields it so the hierarchy can be built; the
UI downgrades non-billable rows in the result list.

## Derived fields

- **`normalized_code`** — the code with the decimal point stripped,
  uppercased (`H401211`). Used for fast prefix search via `LIKE`.
- **`code`** — decimal-pointed form (`H40.1211`). Humans and
  downstream systems expect this.
- **`chapter_code` / `chapter_title`** — from a constant table in
  `parser.py` (`_CHAPTER_TABLE`). Ranges are stable across years:
  e.g. `H00`–`H59` → chapter VII, "Diseases of the eye and adnexa".
- **`category_code`** — first 3 characters of the code
  (`H40` for `H40.1211`).
- **`parent_code`** — direct parent in the tabular hierarchy:
  - 3-char category → no parent
  - longer → parent is the code with the last character stripped,
    trailing dot removed if present
- **`specificity_flags`** — a deterministic UI-prompt heuristic.
  This is NOT a replacement for the Official Guidelines. Flags:
  - `laterality_required` — H00–H59 eye codes whose terminal
    form is short enough that laterality has not yet been coded.
  - `stage_required` — H40.xxxxx glaucoma codes that are 6 chars
    long (the 7th char encodes stage).
  - `manifestation_detail_required` — diabetes codes in
    E08.3x / E09.3x / E10.3x / E11.3x / E13.3x, which need the
    ophthalmic manifestation detail.

## What the parser does NOT attempt

- It does **not** interpret Official Guidelines exclusion /
  inclusion notes, excludes1/excludes2 brackets, or Code Also /
  Code First hints. Those live in the tabular PDF ICD-10-CM
  release and are not present in the order file.
- It does **not** attempt to associate ICD-10-CM codes with
  CPT / HCPCS codes. The Phase C CPT suggestion layer handles
  that seam separately.
- It does **not** invent codes or backfill missing ones.

## Fixture vs. real release

Tests run against `apps/api/tests/fixtures/icd10cm/icd10cm-order-2026.txt`
(40 ophthalmology rows in the identical fixed-width format). The
fixture shape matches the real file byte-for-byte per column, so
any drift in the real CMS format will cause test failures before
production sees it.
