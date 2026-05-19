# Phase 60 Vitals Workup Demo Runbook

## Goal

Show a structured technician workup and vitals intake flow that is
provider-reviewed and signed/locked. Use fake demo values only.

## Pre-Demo Checks

- Confirm the environment is a local or staging demo environment.
- Confirm no real PHI is used.
- Run claim scanners before customer-facing rehearsal.
- Confirm the backend has migrated to a single Alembic head.
- Confirm no production LLM is enabled.

## Click Path

1. Open an encounter in the clinical workspace.
2. Go to Documentation / EMR/EHR.
3. Find **Technician Workup & Vitals**.
4. Click **Load fake demo vitals**.
5. Point out the sections:
   - General vitals.
   - Ophthalmology workup.
   - Review checks.
   - Technician notes.
   - Warnings.
   - Status timeline.
6. Save the workup.
7. Mark it reviewed.
8. Check the attestation box.
9. Sign the workup.
10. Show the signed/locked state and confirm edit controls are hidden.

## Demo Narration

Safe phrasing:

- "This is structured intake for provider review."
- "A technician can enter the workup; a clinician reviews and signs."
- "The system calculates BMI and highlights review warnings."
- "Signing locks the workup."
- "Audit events store metadata only."

## What Not To Say

- ChartNav diagnoses from vitals.
- ChartNav recommends treatment.
- ChartNav places orders.
- ChartNav sends patient messages.
- ChartNav creates billing code output.
- ChartNav provides device integration.
- ChartNav provides remote patient monitoring.
- ChartNav uses production LLMs for vitals.
- ChartNav is HIPAA compliant.
- ChartNav replaces an EHR.

## Safety Boundaries

- Not autonomous diagnosis.
- Not image interpretation.
- Not production LLM.
- No real PHI.
- No treatment recommendation.
- No orders, referrals, patient messages, billing, or coding.
- No device integration.
- No remote patient monitoring claim.

## Operator Notes

- Use only the fake demo sample button or synthetic values.
- If a warning appears, narrate it as a review prompt.
- If an API error appears, do not improvise a clinical explanation;
  pause and report the issue.
- Do not paste real patient identifiers or real clinic data into the
  technician notes field.
