# Executive Summary — ChartNav Controlled Pilot

**Audience:** Ophthalmology practice clinical owner, administrator,
and security/CISO
**Posture:** Controlled fake-data pilot evaluation
**Real-PHI status:** Not approved through this package alone

## What ChartNav delivers

ChartNav supports the **provider-reviewed ophthalmology operating
loop** with structured documentation, deterministic readiness
signals, audit-ready metadata, and a narrow read-only FHIR R4
export. It is designed to work **alongside** the practice's
existing EHR — not replace it — and to keep every clinical
decision with the provider.

In a controlled fake-data pilot, the practice can evaluate:

1. **Clinical spine.** Vitals workup → visit draft → fundus
   chart, with provider review and signed lock. Every signing
   event lands in a metadata-only audit trail; no clinical body
   text reaches the audit log's detail field.
2. **Adaptive subspecialty workspace.** Retina, glaucoma,
   cataract, and comprehensive profiles reorder the Overview
   surface to match the visit. Every panel remains available;
   lower-priority panels are collapsed, never hidden.
3. **Longitudinal clinical intelligence (metadata only).** Anti-
   VEGF rail, glaucoma cockpit, cataract surgical workflow,
   provider action queue, note validation rail, disease staging,
   quality intelligence documentation support, medication safety,
   imaging metadata, and the advanced clinical intelligence
   layer.
4. **Retina visit packet export.** A reproducible metadata-only
   JSON document the practice can share for internal review.
5. **FHIR R4 read-only DocumentReference.** Submission status is
   pinned to `not_submitted`; transport is `none`. ChartNav does
   not submit anything to any external system in this build.

## What ChartNav is not

- **Not** a certified electronic health record.
- **Not** a replacement for the practice's existing EHR.
- **Not** HIPAA-certified, SOC 2-certified, HITRUST-certified, or
  FDA-cleared. (ChartNav supports a practice's HIPAA obligations
  contractually via BAA when a real-PHI pilot is scoped.)
- **Does not** diagnose, recommend treatment, recommend surgery,
  recommend medication changes, recommend IOL choices, or
  recommend imaging modality changes.
- **Does not** interpret fundus photographs, OCT scans, visual
  fields, or any imaging modality.
- **Does not** place orders, send referrals, bill, code, submit
  claims, or message patients.
- **Does not** submit to MIPS, IRIS, CMS, payers, or any external
  registry from this build.
- **Does not** run a production LLM in this build.

These non-claims are enforced by automated safety scanners and a
runtime safety validator on every release.

## How the pilot proceeds

1. **Controlled fake-data demo.** ARCG runs the local demo stack
   against synthetic seed data, walks the practice through the
   workflow, and hands the practice this package.
2. **Practice review.** The practice's clinical, administrative,
   and (if real-PHI is in scope) security owners review the
   evidence index, the GO / NO-GO form, and the no-real-PHI
   attestation.
3. **Decision.**
   - **Scope A controlled fake-data pilot** may proceed once the
     practice clinical owner, administrator, ARCG ops, and ARCG
     commercial owners sign.
   - **Scope B real-PHI pilot** is gated by the joint completion
     of the Phase 93 real-PHI readiness review and the Phase 18
     controlled-pilot go-live checklist (in the repo), plus the
     practice CISO's and ARCG legal's signatures on the
     no-real-PHI attestation.

## Bottom line

ChartNav is a provider-reviewed workflow surface, ready for a
controlled fake-data ophthalmology pilot today, and prepared to
walk a practice through the joint approvals required for a
controlled real-PHI pilot when the practice is ready.
