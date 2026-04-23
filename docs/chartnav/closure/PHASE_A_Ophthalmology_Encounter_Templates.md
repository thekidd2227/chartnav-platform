# Phase A — Ophthalmology Encounter Templates

## 1. Problem solved

The original buyer brief flagged that ChartNav presents as a general clinical note surface, not an ophthalmology-first charting product. A transcript-to-SOAP pipeline without specialty-aware structure is not differentiated in ophthalmology clinics, where documentation shape follows the exam type (retina vs. glaucoma vs. anterior segment vs. routine comprehensive). Without templates, the clinician still does most of the structuring by hand, and the downstream CPT/ICD capture story is weak because the structure that drives coding is missing.

Clinically, ophthalmology documentation is unusually templated — the exam is the same set of measurements repeated across visits, with specialty-specific additions (OCT macula for retina, gonioscopy and disc for glaucoma, etc.). Commercially, template-shaped documentation is what lets ChartNav defend the claim that it is "ophthalmology-first" rather than "a generic scribe pointed at an eye clinic."

## 2. Current state

- The extractor at `apps/api/app/services/soap_extractor.py` is deterministic and ophthalmology-aware: it parses VA OD/OS, IOP in slash form, chief complaint, assessment, plan, and a follow-up interval, and emits `<missing — provider to verify>` markers plus a `missing_data_flags` list on the encounter.
- Encounters have state `draft → provider_review → revised → signed → exported` (see `apps/api/app/models/encounter.py` / state machine in the encounter service). Signed encounters are immutable.
- The 3-tier trust UI (transcript / findings / draft) is wired on the encounter page. Pre-sign checkpoint modal and final typed-name approval are shipped (`data-testid="note-sign"`, `data-testid="pre-sign-modal"`, `data-testid="attest-ack"`).
- There is no `template_key` on `encounters`, no template catalog, and no template-driven section skeleton. The SOAP result is a flat structure, not a specialty-shaped form.

## 3. Required state

Four first-party encounter templates, each pinned to the encounter row at creation time:

1. **Retina** — medical retina focus (AMD, DR, RVO, macular edema).
2. **Glaucoma** — IOP, disc, OCT RNFL, visual field emphasis.
3. **Anterior segment / Cataract** — lens grading, refraction, IOL planning.
4. **General ophthalmology** — routine comprehensive exam.

Each template defines: section order, required vs. optional findings groups, default CPT code candidates surfaced for provider capture (provider-entered, never auto-coded), and likely ICD-10 relevance fields.

## 4. Acceptance criteria

- `GET /encounter-templates` returns a list of four templates with `key`, `display_name`, `sections[]`, `required_findings[]`, `suggested_cpt[]`, `icd10_relevance[]`.
- `POST /encounters` accepts `template_key` and persists it; a missing `template_key` defaults to `general_ophthalmology` and is flagged in `missing_data_flags`.
- Template selector rendered on encounter creation — `data-testid="encounter-template-select"`.
- Draft note renders sections in the order the template dictates; missing required findings appear as `<missing — provider to verify>` and populate `missing_data_flags`.
- New pytest file `apps/api/tests/test_encounter_templates.py` covers: template list endpoint, template attach on create, required-findings flag behavior per template, defaulting behavior.
- Playwright: `qa/e2e/encounter_templates.spec.ts` exercises creating one encounter per template and signing.

## 5. Codex implementation scope

Create `apps/api/app/services/encounter_templates.py`:

```python
TEMPLATES = {
    "retina": Template(
        key="retina",
        display_name="Retina",
        sections=["cc", "hpi", "exam.va", "exam.iop", "exam.pupils",
                  "exam.slit_lamp", "exam.fundus", "imaging.oct_macula",
                  "assessment", "plan", "follow_up"],
        required_findings=["va_od", "va_os", "iop_od", "iop_os",
                           "fundus_od", "fundus_os", "oct_macula"],
        suggested_cpt=["92014", "92134", "92250"],
        icd10_relevance=["H35.3", "H35.81", "E11.3"],
    ),
    "glaucoma": Template(...),
    "anterior_segment_cataract": Template(...),
    "general_ophthalmology": Template(...),
}
```

Modify:

- `apps/api/app/models/encounter.py` — add `template_key TEXT NOT NULL DEFAULT 'general_ophthalmology'`.
- Migration `apps/api/migrations/00XX_add_encounter_template_key.sql`.
- `apps/api/app/api/routes.py` — register `GET /encounter-templates`, extend `POST /encounters` payload.
- `apps/api/app/services/soap_extractor.py` — accept a template and use its `required_findings` to drive `missing_data_flags` instead of a fixed list.
- Frontend: `apps/web/src/features/encounter/TemplatePicker.tsx` + integration in the encounter create flow.

## 6. Out of scope / documentation-or-process only

- Clinical validation of template content — handled by a practicing ophthalmologist advisor sign-off stored in `docs/chartnav/clinical/template_review.md`. Code ships with an advisor-review banner until the signature is recorded.
- Payer-specific coding logic (LCDs, bundling edits) — belongs in the billing program, not Phase A templates.
- Multi-specialty support (oculoplastics, neuro-ophthalmology, pediatric) — parked.

## 7. Demo honestly now vs. later

**Now:** four templates drive section order and required-findings flags; CPT and ICD-10 lists surface as *suggested* picks that the provider selects. `GET /encounter-templates` is live. Each template has a named creator flow.

**Later:** automated CPT suggestion from documented findings; payer-aware code edits; template authoring UI for customers.

## 8. Dependencies

- Phase A Structured Charting and Attestation (templates depend on locked-record semantics and edit-history).
- Phase A RBAC spec (technician vs. clinician permissions on template sections — techs chart VA/IOP, clinicians chart assessment/plan).
- Phase A Tablet Charting (template form layouts must render in iPad Pro 12.9 portrait and landscape).

## 9. Truth limitations

- Templates are **not** clinically validated until the advisor sign-off is recorded.
- No CPT is auto-assigned. All codes displayed are suggestions surfaced for provider entry.
- Templates cover medical retina, primary open-angle glaucoma patterns, routine cataract evaluation, and comprehensive exam — they do **not** cover surgical operative notes, pediatric strabismus workups, neuro-ophthalmic pattern VEP, or oculoplastics.
- No claim of E/M level scoring. Level selection remains the provider's responsibility.

## 10. Risks if incomplete

- Pilot clinicians perceive ChartNav as "just a transcript viewer" and revert to their prior note pattern. Retention in the pilot drops.
- The ophthalmology-first market claim is not defensible under scrutiny from a clinical advisor or a buyer's medical director.
- Downstream coding, charge capture, and analytics all require structure that the templates produce — without templates, every downstream closure item has a weaker foundation.
