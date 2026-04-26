# FHIR R4 `Claim` resource sketch — ChartNav v1.0 canonical payload mapping

**Truth boundary:** this is a documentation sketch. ChartNav does not
post FHIR `Claim` resources to a payer or to a clearinghouse in
Phase A. The shape below is what a future adapter (Phase B/C) would
emit so a clearinghouse or PM system can consume it without bespoke
glue per ChartNav release.

```json
{
  "resourceType": "Claim",
  "status": "active",
  "type": {
    "coding": [
      {
        "system": "http://terminology.hl7.org/CodeSystem/claim-type",
        "code": "professional"
      }
    ]
  },
  "use": "claim",
  "patient": {"reference": "Patient/MRN-00042"},
  "billablePeriod": {
    "start": "2026-04-22",
    "end": "2026-04-22"
  },
  "provider": {"reference": "Practitioner/npi-9876543210"},
  "diagnosis": [
    {
      "sequence": 1,
      "diagnosisCodeableConcept": {
        "coding": [
          {
            "system": "http://hl7.org/fhir/sid/icd-10-cm",
            "code": "H35.31"
          }
        ]
      }
    }
  ],
  "item": [
    {
      "sequence": 1,
      "productOrService": {
        "coding": [
          {
            "system": "http://www.ama-assn.org/go/cpt",
            "code": "92014"
          }
        ]
      },
      "unitPrice": {"value": 150.00, "currency": "USD"}
    },
    {
      "sequence": 2,
      "productOrService": {
        "coding": [
          {
            "system": "http://www.ama-assn.org/go/cpt",
            "code": "92134"
          }
        ]
      },
      "modifier": [
        {"coding": [{"code": "RT"}]}
      ],
      "unitPrice": {"value": 70.00, "currency": "USD"}
    }
  ]
}
```

## Mapping table

| ChartNav payload field | FHIR Claim path |
|---|---|
| `patient.mrn` | `patient.reference` (with the local MRN-namespace prefix) |
| `provider.npi_individual` | `provider.reference` (with the npi- namespace prefix) |
| `encounter_date` | `billablePeriod.start` and `.end` |
| `codes.icd10[].code` | `diagnosis[*].diagnosisCodeableConcept.coding[*].code` (system: `http://hl7.org/fhir/sid/icd-10-cm`) |
| `codes.cpt[].code` | `item[*].productOrService.coding[*].code` (system: `http://www.ama-assn.org/go/cpt`) |
| `codes.cpt[].modifiers` | `item[*].modifier[*].coding[*].code` |
| `note.attestation_hash` | not represented in `Claim`; carried in a sibling `Provenance` resource if needed |

## What this is not

- A running FHIR posting client.
- A statement that ChartNav implements US Core or any specific FHIR
  Implementation Guide.
- A reimbursement guarantee.

ChartNav remains an advisory documentation surface in Phase A. The
canonical JSON, CSV, and PDF artifacts produced by
`POST /encounters/{id}/export` are the authoritative ChartNav-side
deliverables.
