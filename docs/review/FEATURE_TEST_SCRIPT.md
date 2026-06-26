# Feature test script (guided walkthrough)

A 10-minute hands-on pass through the reconciled ChartNav features. Start the
env first (`./scripts/review/start_chartnav_review.sh`) and open
http://localhost:5173.

> The automated `verify_chartnav_review.sh` already checks most of this against
> the API. This script is for **you** to click through the UI.

## 1. Sign in (dev identity)
- Pick `admin@chartnav.local` in the identity selector. You're now in the
  `demo-eye-clinic` org.

## 2. Patient list + chart
- Open the patient list → you should see **Morgan Lee (PT-1001)** and **Jordan
  Rivera (PT-1002)**.
- Open an encounter for Morgan Lee → the **Clinical Tabbed Workspace** loads
  (Overview, Clinical, Documentation, Imaging, …).

## 3. "Open chart" entry point (numeric patient_id only)
- On the **Overview** tab, next to the patient identity/MRN, you should see an
  **"Open chart"** link → it goes to `#/patients/{id}` and opens the
  **Patient Chart**.
- The link renders **only** for a native, numeric internal `patient_id`. For an
  external/bridged encounter (string or null patient_id) the link is **absent**
  (this is covered by `ClinicalTabbedWorkspace.test.tsx`).

## 4. Patient Chart + retina (canonical EyeDiagramPanel)
- In the Patient Chart, open the **Eye Diagrams** section → it embeds the
  canonical **EyeDiagramPanel** (RetinalDrawingCanvas).
- Create a retinal diagram, add findings, **save** → it persists; reopen → it
  reloads. The drawing is stored as **`drawing_json`** (a JSON object), never
  `vector_json`.
- **Sign** the diagram → it becomes immutable; an edit **forks** a new version
  (v2) rather than overwriting the signed one.

## 5. Fundus charting
- Open a fundus chart, add measurements, save, reload → persists. (Mainline
  fundus workflow; LLM guardrails apply — provider-controlled, no autonomous
  interpretation.)

## 6. Roles
- Switch to `rev@chartnav.local` (reviewer). Open the same chart → you can
  **view** but **cannot** create/sign an eye diagram (the API returns 403).

## 7. Cross-tenant isolation
- Switch to `admin@northside.local` (Clinic B). Try to open Clinic A's patient
  (e.g. via the `#/patients/{PT-1001 id}` hash) → you get a **not-found** result
  (non-disclosing 404). Clinic B only sees **Priya Shah (PT-2001)**.

## 8. Audit
- Actions you took (viewing a patient, editing, signing) wrote **audit events**
  (`security_audit_events`) with metadata only — no clinical content / no PHI in
  the audit detail. `verify_chartnav_review.sh` confirms rows exist.

## 9. Note lifecycle (if exercising documentation)
- In the Documentation tab, note review/sign transitions enforce roles
  (clinician/admin sign; reviewer cannot). All AI assistance is
  provider-reviewed — nothing is sent or finalized autonomously.

---
If anything here doesn't behave as described, capture the step + the API log
(`docker compose -f scripts/review/docker-compose.yml logs api`) and note it.
