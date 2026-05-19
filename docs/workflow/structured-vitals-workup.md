# Structured Vitals Workup Workflow

Phase 60 adds a structured technician workup and vitals intake surface.
It is a clinical intake record for provider review, not a clinical
decision engine.

## Workflow

1. **Enter intake values** - A technician, clinician, or admin enters
   vitals and ophthalmology workup fields for an encounter.
2. **Save** - `POST /api/v1/encounters/{encounter_id}/vitals-workups`
   creates a `visit_vitals_workups` row scoped to the caller's
   organization.
3. **Review warnings** - The service creates review warnings for
   incomplete or suspicious values. Warnings use review language only.
4. **Review** - A clinician or admin calls
   `POST /api/v1/vitals-workups/{workup_id}/review`. Review is not a
   signature.
5. **Sign** - A clinician or admin calls
   `POST /api/v1/vitals-workups/{workup_id}/sign` with
   `{"attested": true}`. Signed workups are immutable.

## Supported Fields

- General vitals: blood pressure systolic/diastolic, position, site,
  temperature, pulse, respiratory rate, oxygen saturation, height,
  weight, BMI, pain score.
- Ophthalmology workup: VA OD/OS/OU, IOP OD/OS, IOP method, dilation
  status, dilation time.
- Review checks: allergies reviewed, medications reviewed.
- Technician notes.

BMI is calculated by the backend from height and weight when both are
present. The frontend displays the same calculation for operator
feedback before save.

## Warnings

Warnings are non-diagnostic. They are prompts for provider review.

Examples:

- Systolic entered without diastolic.
- BP value entered without site or position.
- Height entered without weight, or weight entered without height.
- IOP OD entered without IOP OS.
- VA OD entered without VA OS.
- Oxygen saturation or temperature outside expected review range.

The warnings must not say hypertensive crisis, fever diagnosis, hypoxia
diagnosis, emergency diagnosis, treatment recommendation, or any similar
clinical-action language.

## Roles

- `admin`, `clinician`, and `technician` can create or update unsigned
  workups.
- `admin` and `clinician` can review and sign.
- `technician` can enter data but cannot sign.
- `reviewer` is read-only.
- `front_desk` cannot mutate this clinical surface.

Cross-organization access returns 404.

## Audit

Create, update, review, and sign emit metadata-only audit events. Audit
detail includes only:

- workup id
- patient id
- encounter id
- status
- warning count

Audit detail must not include BP values, temperature values, pulse, VA,
IOP, technician notes, or other clinical free text.

## Non-Goals

- No diagnosis.
- No treatment recommendation.
- No orders.
- No referrals.
- No patient messaging.
- No billing or coding.
- No device integration.
- No remote patient monitoring claim.
- No OpenAI, Anthropic, IBM watsonx, or other LLM path.
- No real PHI in demo mode.

## Demo Safety

The UI includes a "Load fake demo vitals" button. Those values are
synthetic and contain no name, MRN, DOB, address, phone, or real clinic
identifier. Demo operators must not paste or type real PHI into demo
environments.

## Known Limitations

- No correction/versioning workflow for signed workups yet;
  `superseded` is reserved for a future amendment pattern.
- No device ingestion or EHR writeback.
- No dedicated Intake tab yet; the panel is mounted in the
  Documentation workspace for Phase 60.
