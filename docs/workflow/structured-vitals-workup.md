# Structured Vitals & Technician Workup

> **Fake / demo only by default.** Real PHI flows through ChartNav only
> in environments approved via the controlled-pilot gate; the demo
> environment is fake-data. ChartNav is not HIPAA compliant. ChartNav
> is not a certified EHR. The vitals workup feature **does not
> diagnose**, **does not recommend treatment**, **does not place
> orders / referrals / patient messages**, **does not bill or code**,
> and **does not integrate with vital-signs devices**.

## What this is

Phase 60 adds a structured intake row to capture vitals + ophthalmology
workup fields at the start of a visit, route them through a
provider-review lifecycle, and lock them on sign. The workup is
**technician-entered** by default (the `technician` role can write
draft / entered rows); the **clinician** marks reviewed and signs.

## What this is NOT

- ❌ Diagnosis. Out-of-range BP / temp / pulse / SpO2 surfaces as a
  "review required" warning, **never** as "hypertensive crisis",
  "fever", "hypoxia", "stroke", etc.
- ❌ Treatment recommendation. The service never says "give X
  medication" or "schedule Y procedure".
- ❌ Orders. `forbidden_actions.orders` is always `false`.
- ❌ Referrals. `forbidden_actions.referrals` is always `false`.
- ❌ Patient messages. `forbidden_actions.patient_message` is always `false`.
- ❌ Billing or coding. `forbidden_actions.billing_or_coding` is always `false`.
- ❌ Device integration. No live BP cuff sync, no thermometer sync,
  no smart-scale sync, no pulse oximeter sync. Every value is manually
  entered. `forbidden_actions.device_integration=false`.
- ❌ Remote patient monitoring. RPM is out of scope.
  `forbidden_actions.remote_patient_monitoring=false`.
- ❌ Auto-sign. `forbidden_actions.auto_sign=false`; sign requires
  explicit `{"attested": true}`.
- ❌ EHR replacement.
- ❌ Production LLM. The service is pure-Python regex + arithmetic.
  No OpenAI, no Anthropic, no IBM watsonx involvement.

## Where the feature lives in the UI

`ClinicalTabbedWorkspace` → **Clinical / Ophthalmology** tab →
**Technician Workup & Vitals** wide card (top of the tab, above the
specialty-tracking panel and shortcut grid).

Card test-id: `ctw-card-technician-workup-vitals`. Panel test-id:
`vitals-workup-panel`.

## Captured fields

### General vitals
- Blood pressure: systolic, diastolic, position (sitting / standing / supine), site (left_arm / right_arm / wrist / other).
- Temperature: value + unit (F / C) + site (oral / temporal / tympanic / axillary / rectal / other).
- Pulse, respiratory rate, oxygen saturation.
- Height + unit (in / cm). Weight + unit (lb / kg). **BMI auto-calculated** server-side when both height and weight are present.
- Pain score (0–10).

### Ophthalmology workup
- Visual acuity OD / OS / OU (free text such as `20/20`, `20/200`, `HM`, `CF`).
- IOP OD / OS (numeric mmHg) + method (applanation / tonopen / icare / other).
- Dilation status (not_dilated / dilated / declined / contraindicated). Dilation timestamp if known.

### Review checks
- `allergies_reviewed` (boolean).
- `medications_reviewed` (boolean).

### Free-text
- `technician_notes` (≤ 4000 chars). Stored on the row; **never** written to the audit `detail` field. Intended for brief structured notes the provider will review.

## Lifecycle

```
draft  →  entered  →  reviewed  →  signed
                                     │
                                     └── immutable; PATCH / review / sign all 409
                       superseded (reserved for future correction / versioning)
```

- **draft** — created via POST; possibly empty; mid-edit.
- **entered** — the technician (or clinician) has finished entry. Set by PATCH with `advance_to_entered=true`.
- **reviewed** — clinician marks reviewed via `POST /vitals-workups/{id}/review`.
- **signed** — clinician signs via `POST /vitals-workups/{id}/sign` with `{"attested": true}`. Row becomes immutable.

The `superseded` state is reserved; no V1 endpoint produces it.

## API contract

| Method | Path | Role | Notes |
|---|---|---|---|
| GET | `/api/v1/encounters/{encounter_id}/vitals-workups` | any in-org | List, newest first. |
| POST | `/api/v1/encounters/{encounter_id}/vitals-workups` | admin / clinician / technician | Create draft. |
| GET | `/api/v1/vitals-workups/{workup_id}` | any in-org | Read. |
| PATCH | `/api/v1/vitals-workups/{workup_id}` | admin / clinician / technician | Update; optional `advance_to_entered=true` advances `draft → entered`. 409 on signed. |
| POST | `/api/v1/vitals-workups/{workup_id}/review` | admin / clinician | `entered → reviewed`. **Technician cannot review.** |
| POST | `/api/v1/vitals-workups/{workup_id}/sign` | admin / clinician | `reviewed → signed`. Requires `{"attested": true}`. **Technician cannot sign.** |

Refusal codes:

- 403 `role_forbidden` — wrong role.
- 404 `encounter_not_found` / `workup_not_found` — cross-org or missing.
- 409 `workup_immutable` — signed.
- 409 `invalid_transition` — wrong status for action.
- 422 `attestation_required` — sign without `attested=true`.
- 422 `invalid_enum` — bad enum value.

## Server-side BMI calculation

Both `height_value`/`height_unit` and `weight_value`/`weight_unit` must
be set. The service normalises to metres + kilograms, computes
`weight_kg / (height_m ** 2)`, rounds to 1 decimal. Returned as the
`bmi` field on every workup response.

If either height or weight is missing, BMI is `null` and the warnings
list surfaces "Height captured but weight missing" or vice versa.

## Warning generation

Each warning is a **review prompt**, never a diagnosis. Examples:

| Trigger | Warning text shape |
|---|---|
| Systolic without diastolic | "Blood pressure systolic captured but diastolic missing; please add diastolic before signing." |
| BP without site / position | "Blood pressure recorded without a site; please specify site (left_arm / right_arm / wrist / other) before signing." |
| Systolic outside 80–180 | "Systolic blood pressure (210) is outside the typical range; provider review required." |
| Pulse outside 40–130 | "Pulse (38) is outside the typical range; provider review required." |
| RR outside 8–30 | "Respiratory rate (5) is outside the typical range; provider review required." |
| SpO2 below 90 | "Oxygen saturation (85) is below the typical range; provider review required." |
| Temperature outside 95.0–100.4 °F (or 35.0–38.0 °C) | "Temperature (103.5°F) is outside the typical range; provider review required." |
| Height without weight | "Height captured but weight missing; BMI cannot be calculated until both are entered." |
| Pain score outside 0–10 | "Pain score (12) is outside the 0-10 scale; please re-enter." |
| IOP OD without OS | "IOP captured for OD but not OS; please add IOP OS or confirm intent before signing." |
| VA OD without OS | "Visual acuity captured for OD but not OS; please add VA OS or confirm intent before signing." |
| IOP without method | "IOP recorded without a method; please specify method (applanation / tonopen / icare / other) before signing." |

The complete list lives in `apps/api/app/services/vitals_workup.py:generate_warnings`. The Phase 60 tests pin that **no** message contains "hypertensive crisis", "hypertension", "stroke", "fever", "sepsis", "hypoxia", "respiratory failure", or any diagnostic / treatment / order language.

## Audit minimisation

The route's audit helper uses `build_audit_detail()` which emits **only** metadata:

```
workup_id=42 encounter_id=7 patient_id=3 status=signed warning_count=2 action=sign
```

The raw BP / temp / pulse / RR / SpO2 / VA / IOP / `technician_notes`
values are **never** written to the audit `detail`. The Phase 60 test
`test_audit_detail_excludes_clinical_body` pins this with a canary
string in `technician_notes` that must not appear in any audit row.

## Tenant isolation

- Every route filters by `organization_id`.
- Cross-org access returns **404** (not 403) so the existence of a row
  in another org is not leaked.
- The encounter must belong to the caller's org; otherwise 404 on the
  list / create.

## Correction / versioning

V1 contract: **signed workups are immutable.** To correct a signed
workup, create a new workup on the same encounter. There is no
in-place edit path and no fork / new-version endpoint. Demo narration
must not imply signed workups can be amended in place.

The `superseded` status is reserved in the lifecycle for a future
correction-and-supersede flow; no V1 endpoint produces it.

## Approved phrases

- "Structured vitals + ophthalmology workup intake."
- "Technician-entered, provider-reviewed, signed."
- "Provider review required at every step."
- "BMI is server-calculated from height and weight."
- "Out-of-range values surface as review prompts, never as diagnosis."
- "Signed workups are immutable."

## Forbidden phrases (claim scanners block these)

- "AI vitals diagnosis"
- "Automatic vitals diagnosis"
- "Vital-sign diagnosis"
- "Treatment recommendation"
- "Automatic treatment recommendation"
- "AI prescribes"
- "AI orders labs"
- "Device integration"
- "Live device integration"
- "Vital-signs device integration"
- "Remote patient monitoring"
- "RPM-ready"
- "Continuous patient monitoring"
- "EHR replacement"
- "HIPAA compliant"

## Related documents

- `docs/build/phase-60-structured-vitals-feature-audit.md` — pre-implementation audit.
- `docs/demo/phase-60-vitals-workup-demo-runbook.md` — operator demo runbook.
- `docs/build/current-product-truth.md` — single source of truth (Technician Workup & Structured Vitals row).
- `docs/commercial/claims-policy.json` — canonical forbidden-phrase manifest.
- `scripts/check_runtime_safety.py` — runtime gate validator.
