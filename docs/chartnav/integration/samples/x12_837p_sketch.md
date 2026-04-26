# X12 837P sketch — ChartNav v1.0 canonical payload mapping

**Truth boundary:** this is a documentation sketch, not a 5010-certified
generator. ChartNav does not transmit X12 in Phase A. HIPAA 5010
compliance of any eventual real X12 output depends on Phase B work
with a clearinghouse partner (Availity, Waystar, Change Healthcare,
or equivalent).

The payload fields below are sourced from the v1.0 canonical handoff
payload (see `docs/chartnav/closure/PHASE_A_PM_RCM_Continuity_and_Integration_Path.md`
§5.1) so a clearinghouse adapter built later can map deterministically.

```
ISA*00*          *00*          *ZZ*CHARTNAVCLINIC *ZZ*PAYERID        *...
GS*HC*CHARTNAVCLINIC*PAYERID*...
ST*837*0001*005010X222A1
BHT*0019*00*0001*20260422*1902*CH

NM1*41*2*EXAMPLE EYE ASSOCIATES*****46*1234567890           ; org.name + org.npi_group
PER*IC*CONTACT*TE*5555550100

NM1*40*2*PAYER NAME*****46*PAYERID

HL*1**20*1
NM1*85*2*EXAMPLE EYE ASSOCIATES*****XX*1234567890           ; billing provider
N3*123 EXAMPLE LANE
N4*ANYTOWN*CA*94000

HL*2*1*22*1
SBR*P*18*GR123456*PLAN NAME*****CI

NM1*IL*1*PATIENT*SAMPLE****MI*INSID000042                   ; patient.mrn / insurance_id
N3*1 PATIENT LANE
N4*ANYTOWN*CA*94000
DMG*D8*19580314*F                                            ; patient.dob / sex_at_birth

CLM*ENC01HX*220.00***11:B:1*Y*A*Y*I                          ; encounter_id / place_of_service

HI*ABK:H3531                                                 ; codes.icd10[0]

NM1*82*1*ROE*JANE****XX*9876543210                           ; provider.npi_individual
PRV*PE*PXC*207W00000X                                        ; provider.taxonomy_code

LX*1
SV1*HC:92014*150.00*UN*1***1                                 ; codes.cpt[0]
DTP*472*D8*20260422
LX*2
SV1*HC:92134:RT*70.00*UN*1***1                               ; codes.cpt[1] + modifier
DTP*472*D8*20260422

SE*N*0001
GE*1*1
IEA*1*000000001
```

## Mapping table

| ChartNav payload field | X12 segment / element |
|---|---|
| `org.name`, `org.npi_group` | NM1*85 (billing provider) and NM1*41 |
| `provider.full_name`, `provider.npi_individual` | NM1*82 (rendering) |
| `provider.taxonomy_code` | PRV*PE*PXC |
| `patient.mrn`, `patient.display_name` | NM1*IL |
| `patient.dob`, `patient.sex_at_birth` | DMG*D8 |
| `visit.place_of_service` | CLM segment, position 5 |
| `codes.cpt[].code` | SV1 segment HC:* |
| `codes.cpt[].modifiers` | SV1 segment HC:CODE:MODIFIER |
| `codes.icd10[].code` | HI segment ABK / ABF |
| `encounter_id` | CLM segment ID |
| `note.attestation_hash` | not represented in 837P; retained as a ChartNav-side audit anchor |

## What this is not

- A running X12 generator.
- A submission path (no SOAP/MIME envelope, no clearinghouse credentials).
- A reimbursement guarantee.
- A statement that ChartNav is HIPAA 5010-compliant.

The signed JSON payload (`/encounters/{id}/export?fmt=json`) plus the
PDF rendering remain the authoritative artifacts ChartNav ships in
Phase A.
