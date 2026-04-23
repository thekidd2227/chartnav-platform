# Phase A — PM / RCM Continuity and Integration Path

## 1. Problem solved

The brief flagged that ChartNav risks being perceived as a "chart on an island" — useful at the point of care but disconnected from the practice management (PM) and revenue cycle management (RCM) systems the clinic actually runs on. In ophthalmology, a note that cannot flow to billing is a note that does not get paid, and a product that does not address that flow is a QA burden, not a productivity tool.

This spec takes the honest position: **no PM/RCM integration ships in Phase A.** What ships is (a) a disciplined manual export path that the clinic's existing biller can ingest, and (b) a concrete, field-level integration path for the two PM/RCM systems most common in ophthalmology MSOs (NextGen and AdvancedMD), so buyers can see exactly where we are going.

## 2. Current state

- ChartNav is not a PM system. There is no schedule-of-record, no claim, no charge capture, no ERA/835 handling.
- Signed encounters produce a bundle (see the evidence-chain code path). Today the bundle is not shaped for biller handoff — it carries the SOAP note and metadata but not a structured billing payload.
- Deployment modes in code: `standalone`, `integrated_readthrough` (FHIR R4 read, no EHR write), `integrated_writethrough` (vendor adapter writes — returns 501 when unsupported). `integrated_writethrough` has no real vendor adapters shipped today.
- There is no CPT suggestion engine, no charge capture UI, no claim generation.

## 3. Required state

Two layered outputs:

**3.1 Phase A — interim manual/export path.** On encounter sign, ChartNav produces a handoff bundle the biller imports by hand into their existing PM/RCM:

- `encounter_handoff.json` — structured payload (fields below).
- `encounter_note.pdf` — rendered note.
- `encounter_handoff.csv` — single-row billing line for superbill ingestion.

**3.2 Target API path (post-Phase A, documented in Phase A).** Two adapter targets are named, with payload sketches:

- NextGen (common in mid-size ophthalmology MSOs).
- AdvancedMD (common in single-site and small-MSO ophthalmology).

The payload shape must also map cleanly to X12 837P and to a FHIR R4 `Claim` resource, so that neither vendor target becomes a dead end.

## 4. Acceptance criteria

- `POST /encounters/{id}:export` on a signed encounter returns an export manifest with URLs for `handoff.json`, `note.pdf`, and `handoff.csv`. Unsigned encounters return 409.
- Field-level payload (see 5.1) is stable, versioned (`schema_version: "1.0"`), and documented.
- Pytest: `apps/api/tests/test_handoff_export.py` covers shape, versioning, sign-gate, and RBAC (biller_coder / clinician / admin may export; front_desk / technician may not).
- UI: `data-testid="encounter-export-bundle"` button on a signed encounter, gated by role.
- An example payload for each of NextGen and AdvancedMD is committed in `docs/chartnav/integration/samples/` alongside a mapping table from our canonical payload to each vendor's field names.

## 5. Codex implementation scope

### 5.1 Canonical handoff payload

```json
{
  "schema_version": "1.0",
  "encounter_id": "enc_01HXXXXXXXX",
  "encounter_date": "2026-04-22",
  "org": {
    "id": "org_1",
    "name": "Example Eye Associates",
    "npi_group": "1234567890",
    "tax_id_last4": "1234"
  },
  "provider": {
    "user_id": "usr_42",
    "full_name": "Jane Roe, MD",
    "npi_individual": "9876543210",
    "taxonomy_code": "207W00000X"
  },
  "patient": {
    "mrn": "MRN-00042",
    "dob": "1958-03-14",
    "sex_at_birth": "F",
    "insurance_id_last4": "9921"
  },
  "visit": {
    "chief_complaint": "Blurred vision OD, 2 weeks",
    "template_key": "retina",
    "place_of_service": "11"
  },
  "codes": {
    "cpt": [
      {"code": "92014", "modifiers": [], "units": 1, "provider_entered": true},
      {"code": "92134", "modifiers": ["RT"], "units": 1, "provider_entered": true}
    ],
    "icd10": [
      {"code": "H35.31", "rank": 1}
    ]
  },
  "note": {
    "pdf_url": "https://.../encounter_note.pdf",
    "signed_at": "2026-04-22T19:02:14Z",
    "attestation_hash": "sha256:..."
  }
}
```

Required-field contract:

| Field | Type | Required | Notes |
|---|---|---|---|
| `schema_version` | string | yes | semver |
| `encounter_id` | string | yes | ChartNav ID |
| `encounter_date` | date | yes | clinical visit date |
| `org.npi_group` | string | yes | group NPI |
| `provider.npi_individual` | string | yes | rendering provider |
| `patient.mrn` | string | yes | clinic MRN |
| `patient.dob` | date | yes | for claim eligibility |
| `visit.chief_complaint` | string | yes | |
| `codes.cpt[]` | array | yes (≥1) | provider-entered in v1 |
| `codes.icd10[]` | array | yes (≥1) | ranked |
| `note.attestation_hash` | string | yes | ties payload to signed note |

### 5.2 Code to write

- `apps/api/app/services/handoff_export.py` — canonical payload builder + CSV/PDF emitters.
- `apps/api/app/api/routes.py` — `POST /encounters/{id}:export`.
- `apps/api/app/integrations/vendor_mapping/nextgen.py` and `advancedmd.py` — pure functions that map the canonical payload to the vendor shape. No network I/O in Phase A.
- Documentation: `docs/chartnav/integration/samples/nextgen_example.json`, `advancedmd_example.json`, `x12_837p_sketch.md`, `fhir_claim_sketch.md`.
- Frontend: `apps/web/src/features/encounter/ExportBundleButton.tsx`.

### 5.3 X12 837P sketch (abbreviated)

```
ISA*00*          *00*          *ZZ*CHARTNAVCLINIC *ZZ*PAYERID        *...
GS*HC*CHARTNAVCLINIC*PAYERID*...
ST*837*0001*005010X222A1
BHT*0019*00*0001*20260422*1902*CH
NM1*41*2*EXAMPLE EYE ASSOCIATES*****46*1234567890
...
CLM*ENC01HX*220.00***11:B:1*Y*A*Y*I
HI*ABK:H3531
LX*1
SV1*HC:92014*150.00*UN*1***1
SV1*HC:92134:RT*70.00*UN*1***1
SE*...
```

### 5.4 FHIR `Claim` sketch

```json
{
  "resourceType": "Claim",
  "status": "active",
  "type": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/claim-type", "code": "professional"}]},
  "use": "claim",
  "patient": {"reference": "Patient/MRN-00042"},
  "billablePeriod": {"start": "2026-04-22", "end": "2026-04-22"},
  "provider": {"reference": "Practitioner/npi-9876543210"},
  "diagnosis": [{"sequence": 1, "diagnosisCodeableConcept": {"coding": [{"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "H35.31"}]}}],
  "item": [
    {"sequence": 1, "productOrService": {"coding": [{"system": "http://www.ama-assn.org/go/cpt", "code": "92014"}]}, "unitPrice": {"value": 150.00, "currency": "USD"}},
    {"sequence": 2, "productOrService": {"coding": [{"system": "http://www.ama-assn.org/go/cpt", "code": "92134"}]}, "modifier": [{"coding": [{"code": "RT"}]}], "unitPrice": {"value": 70.00, "currency": "USD"}}
  ]
}
```

## 6. Out of scope / documentation-or-process only

- Live claim submission, clearinghouse contracts (Availity, Waystar, Change Healthcare).
- ERA/835 ingest, denial management, aging reports.
- Patient statement generation and collections.
- Payer eligibility (270/271) — parked.

## 7. Demo honestly now vs. later

**Now:** sign a template-shaped encounter, click **Export Bundle**, open `handoff.csv` in Excel or paste `handoff.json` into the biller's current workflow. Show the mapping to NextGen and AdvancedMD field names as read-only documentation.

**Later:** real NextGen / AdvancedMD adapter; X12 837P generation and submission via a clearinghouse; ERA ingest; denial loop.

## 8. Dependencies

- Phase A Structured Charting and Attestation — `attestation_hash` is required in the payload.
- Phase A Encounter Templates — `template_key` drives `codes.cpt[]` suggestions.
- Phase A RBAC — only `biller_coder`, `clinician`, and `admin` can export.

## 9. Truth limitations

- **No PM/RCM integration ships in Phase A.** Nothing in the pilot sends a claim.
- CPT codes are provider-entered, not auto-generated. No E/M level scoring engine.
- The canonical payload is designed to map cleanly to NextGen and AdvancedMD, but no vendor-certification work has been done. "Integration-ready" is not the same as "integrated."
- HIPAA 5010 compliance of the final X12 output depends on Phase B work with a clearinghouse partner.

## 10. Risks if incomplete

- Without the export bundle, the pilot biller does double entry, and the clinic concludes ChartNav adds work rather than removing it.
- Without a documented integration path, every buyer conversation ends with "call us when you're connected to our PM." The opportunity stalls.
- Without `attestation_hash` tying the payload to the signed note, a biller could claim on a note that was later amended — the exact compliance failure the Structured Charting spec is designed to prevent.
