# ChartNav Admin / User Onboarding Checklist

The sequence to get an ophthalmology practice from "agreement
signed" to "first provider session" without skipping safety steps.

This is a checklist, not a script. Pair with
`chartnav-pilot-readiness-checklist.md` for the upstream readiness
items and `chartnav-support-runbook.md` for support contact
expectations.

---

## Phase 1 — Org setup

- [ ] Create the pilot organization with a unique `slug`.
      Recommended convention: `<practice-shortname>-pilot`.
- [ ] Confirm the organization's name, primary location, and
      preferred timezone.
- [ ] Confirm the deployment mode (`staging` for pre-pilot or
      `controlled-pilot` once gating items are met — see the
      deployment guide).

## Phase 2 — Admin user setup

- [ ] Provision exactly one `admin` user for the practice's
      primary technical contact.
- [ ] Walk the admin through the workspace once.
- [ ] Walk the admin through the demo workflow guide
      (`Show demo workflow guide` in the workspace).
- [ ] Confirm the admin has read the safety statement and the
      "what ChartNav does NOT do" section of
      `chartnav-known-limitations-and-non-goals.md`.

## Phase 3 — Clinician user setup

- [ ] Provision a `clinician` user for each provider who will use
      ChartNav during the pilot.
- [ ] Each clinician completes the demo workflow guide once,
      against the seeded fake demo patient.
- [ ] Each clinician acknowledges (per the practice's preferred
      record-keeping system) the provider-review boundaries and
      the "ChartNav does not …" safety statement.

## Phase 4 — Reviewer (read-only) user setup

If the practice has a non-prescribing reviewer (chart-review nurse,
QA reviewer, billing-reviewer who is read-only on clinical content):

- [ ] Provision a `reviewer` user for each.
- [ ] Confirm with the reviewer that they cannot generate, accept,
      dismiss, or complete any clinical artifact — those write
      surfaces return `403 role_forbidden` for `reviewer`.
- [ ] Confirm the reviewer can read every Phase 6/8/9/10/11 panel.

## Phase 5 — Demo patient workflow

- [ ] With at least one admin and one clinician, run the
      five-minute demo from
      `docs/demo/chartnav-clinical-workflow-demo-script.md`.
- [ ] Verify each panel surfaces its provider-review safety copy.
- [ ] Verify the action queue does not display order / coding /
      referral / patient-message buttons.
- [ ] Reset the dev DB after the demo: `make reset-db`.

## Phase 6 — First-session walkthrough

- [ ] Schedule a 30-minute first-session walkthrough with the
      pilot's primary clinician.
- [ ] Use the seeded fake `demo-eye-clinic` / `PT-1001` patient
      until step 6.10 below is met.
- [ ] Walk through:
      - 6.1 Identity badge / org confirmation.
      - 6.2 Encounter list / encounter row open.
      - 6.3 Demo workflow guide (open + read the safety bullets).
      - 6.4 Scribe session create / process / review / finalize.
      - 6.5 Eye diagram propose / apply / save / sign.
      - 6.6 Patient summary draft / review / finalize.
      - 6.7 Pre-visit brief generate.
      - 6.8 Provider action queue generate / accept / complete /
            dismiss.
      - 6.9 Reset between providers if needed.
      - 6.10 Switch to the practice's chosen pilot patient
            **only after** the security review gating items are
            met (see below).

## Phase 7 — What to do BEFORE using real patient data

Stop here unless **all** of these are true:

- [ ] BAA (or equivalent) has been executed.
- [ ] `chartnav-security-review-packet.md` items have been signed
      off by the practice's security/compliance owner.
- [ ] The deployment is `controlled-pilot` mode (Postgres,
      `bearer` auth, backups, monitoring).
- [ ] The audit retention window has been agreed.
- [ ] Practice users have acknowledged the safety contract.
- [ ] An incident-response contact and escalation path exist
      (see `chartnav-support-runbook.md`).

If any item above is unchecked, the pilot continues against the
seeded fake demo data only.

## Phase 8 — Support contact / process

- [ ] Practice's primary support contact is documented (name,
      email, preferred channel).
- [ ] ChartNav's support contact is documented.
- [ ] Severity levels and response targets are agreed (see
      `chartnav-support-runbook.md`).
- [ ] The practice knows how to file a routine issue and how to
      escalate a data-safety concern.

## Phase 9 — What NOT to do during the pilot

- [ ] Do **not** treat ChartNav as a clinical decision-maker — it
      is documentation support.
- [ ] Do **not** rely on the action queue's clinical-language scan
      as a safety net — it is intentionally narrow and is
      documented as not a primary safety net.
- [ ] Do **not** send the patient summary to a patient — there is
      no patient-send surface in the product.
- [ ] Do **not** use ChartNav to place orders, submit referrals,
      or post billing/coding entries — those surfaces do not
      exist.
- [ ] Do **not** put real PHI into a `local` or `staging`
      environment. Those modes are fake-data only.
- [ ] Do **not** edit a signed retinal artifact in place —
      finalized chart artifacts are immutable; create an explicit
      fork instead.

## Phase 10 — First-week health check

- [ ] After the first week, schedule a 20-minute review with the
      practice's primary clinician.
- [ ] Confirm at least one provider has completed all seven steps
      of the demo workflow guide against a real encounter (only
      after Phase 7 gating).
- [ ] Confirm no support ticket of severity `S1` or `S2` is open.
- [ ] Confirm baseline metrics from
      `chartnav-pilot-success-metrics.md` are being collected.
