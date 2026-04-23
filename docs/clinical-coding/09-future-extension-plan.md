# Future Extension Plan — Ophthalmology Claim-Support Mappings

This document outlines the next-layer work for the
ophthalmology-oriented advisory rule set. Everything here is
**out of scope for v1** and stays out of the shipping marketing
copy until the work actually lands.

## Phase 1 (shipped in v1)

- 8 seeded rules across retina / glaucoma / cataract / cornea /
  oculoplastics / general.
- Specificity prompts for the most common ophthalmology code
  families (H40.11% POAG, H35.3% AMD, E11.3% diabetic retinopathy,
  H25% cataract, H16.0% corneal ulcer, H02.40% ptosis, Z01.0%
  vision exam).
- One claim-support hint for the glaucoma testing → H40% link.
- All rules carry a `source_reference` and explicitly direct the
  clinician to verify current payer policy when relevant.

## Phase 2 — next

1. **Expand rule coverage across the full H00–H59 chapter.**
   - Target ~40 rules covering the top 80% of specialty volume.
   - Continue sourcing from CDC Official ICD-10-CM Guidelines; do
     not import proprietary AAO Coding Coach text verbatim.
2. **Add laterality-specific prompts as structured output.**
   - Instead of a freeform `specificity_prompt` string, expose a
     structured JSON prompt set the frontend can render as
     checkboxes.
   - Each prompt carries its ICD sub-position contract (e.g.
     "position 5 encodes laterality" for H40.11X1).
3. **Couple the support-rule layer to the CPT suggestion engine
   (Phase C).**
   - When a clinician selects a glaucoma diagnosis, the CPT layer
     surfaces the matching 92xxx diagnostic testing codes with
     a deterministic rule ID.
   - Coupling is read-only; clinicians accept each link manually.

## Phase 3 — LCD-aware rules (operator-maintained)

1. **Add an `lcd_policies` table** scoped per payer + region + date
   window. Each row holds a machine-readable policy excerpt and a
   link to the published LCD.
2. **Extend `ophthalmology_support_rules`** with an optional
   `lcd_policy_id` FK. When a hint references an LCD, the UI
   renders the policy's effective window and direct link.
3. **LCD ingestion is operator-triggered and manual.** Do not
   silently scrape CMS LCD pages. Operators paste the policy
   excerpt + URL into an admin form.

## Explicit non-goals

- Cross-payer coverage rules. Coverage depends on the payer's
  policy; we do not model commercial-payer rules.
- National Correct Coding Initiative (NCCI) edits.
- Modifier logic (−25, −59, −RT/−LT, etc.).
- Historical claims analytics.
- Machine-learning-driven code suggestion. The deterministic rule
  layer is easier to audit and aligns with the AI governance
  policy in `docs/chartnav/closure/PHASE_C_AI_Governance.md`.

## How new rules are added

1. Draft the rule in a PR. Body must include:
   - `specialty_tag`
   - `workflow_area` (`specificity_prompt` or `claim_support_hint`)
   - `diagnosis_code_pattern` (LIKE form)
   - `advisory_hint`, `specificity_prompt`, `source_reference`
2. Review by a clinical advisor before merge. If no advisor is
   named at merge time, the rule ships with
   `is_active = 0` until cleared.
3. Migration to insert. Rules ship as migrations, not fixtures, so
   the source of truth is reproducible across environments.

## Open questions

- Should rules be versioned by the ICD-10-CM release they reference,
  or kept version-independent? v1 keeps them version-independent
  because patterns (e.g. `H40.11%`) are stable across yearly
  updates. If CDC renames a category, rules need review.
- Do we need an operator UI to toggle rules without a migration?
  v1 does not; an `is_active` flag is flipped via direct SQL. Phase
  3 should add an admin screen once clinical advisors are
  involved.
