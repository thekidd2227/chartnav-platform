# ChartNav vs. Cora — Honest Positioning (Phase 25A)

> **Status:** internal positioning brief. This document describes
> ChartNav's posture *as built today*. It is **not** marketing copy.
> Public-facing language must be reviewed against the claim-guard
> scripts in `apps/web/scripts/` before publication.

## TL;DR

We do not compete with Cora on AI-physician-agent demos. We
compete on the **honest lane**: a deterministic, auditable, locally-
runnable ophthalmology workflow that captures what happens in the
exam room and produces a clean note draft a clinician can sign.

We make narrower claims, on purpose. The shipped product:

1. **Captures patient audio consent before recording.** Microphone
   permission is not patient consent. (GH-001)
2. **Reports STT provider state via admin readiness.** The default
   stub never sends audio off-box; an OpenAI Whisper provider is
   wired but is **off by default** and requires operator sign-off.
   ChartNav does **not** auto-attest that real-PHI use is permitted.
   (GH-002)
3. **Prunes stored audio on operator-defined retention windows.**
   The pruner is operator-driven (no daemon), dry-run by default,
   and audits each deletion as a structured event. (GH-003)
4. **Refuses to autonomously diagnose, order, refer, code, or
   bill.** Decision support surfaces are flagged, gated by
   reviewer/clinician roles, and never finalize an action.
5. **Returns metadata-only audits.** Patient identifiers and
   transcript bodies are never in audit detail rows.

## What we explicitly do NOT claim

The following claims are **off-limits** in ChartNav marketing,
demos, sales decks, and product copy. Each maps to a check in
`apps/web/scripts/check_forbidden_claims.mjs` or the Phase 25A
extensions in this branch.

| Forbidden claim | Why |
| --- | --- |
| "HIPAA-compliant" / "HIPAA-certified" | ChartNav has no compliance attestation. Operators sign BAAs and complete vendor reviews off-runtime. |
| "Certified EHR" | ChartNav is not a certified EHR (ONC, etc.). |
| "Beats Cora" / "Replaces Cora" / "Cora killer" | We do not benchmark against Cora. Different categories. |
| "AI physician" / "AI doctor" / "Autonomous diagnosis" | ChartNav never autonomously diagnoses. |
| "Treats patients" / "Prescribes" / "Orders labs/imaging" | ChartNav does none of these. |
| "Production-ready for real PHI" (without operator sign-off) | The real-PHI go-live gate is human-only. |
| "Approved for real PHI by default" | Default mode is demo; uploads are blocked without consent and STT defaults to stub. |

The Cora-comparison line is the new addition for Phase 25A (GH-012).
The existing guards covered the others.

## Where we *do* play

| Capability | ChartNav | Cora-style agent |
| --- | --- | --- |
| Local-first deploy | Yes (sqlite/postgres, on-box STT stub) | No |
| Operator can audit every AI call | Yes (ai_governance_log, append-only) | Varies |
| Patient audio consent gate in upload path | Yes (Phase 25A) | N/A — no recording |
| Bring-your-own STT (stub / whisper / none) | Yes (Phase 35) | N/A |
| Refuses to diagnose / order / bill | Yes, by design | Different positioning |
| Specialty: ophthalmology (OD/OS retinal, IOP, visual acuity, imaging artifacts) | Yes (Phases 21A/B, 24B) | General-purpose |
| Multi-clinic scaling (org isolation enforced at service boundary) | Yes (Phase 22) | Varies |
| Cross-org 404 (no existence leak) | Yes | Varies |

## How the workflow lines up against an AI-agent product

Cora-style "AI physician" demos run the entire visit. ChartNav stays
on **one side of the line**: capture → transcribe → extract → draft.
The clinician runs the visit and signs the note. We don't move that
line, even when a customer asks.

```
   Patient interaction               ChartNav            Clinician
   ─────────────────────             ─────────────       ───────────
   1. Front-desk check-in    ───►   consent capture
   2. Doctor + patient talk  ───►   audio upload + STT
   3. Exam findings spoken   ───►   findings extraction
   4. Note assembled         ───►   draft generation
   5. Doctor reviews         ◄───   sign / revise        signs note
   6. Action items / refs    ───►   provider action       reviews +
                                     review queue        executes
```

Steps 5 and 6 are where Cora-style products try to take over. We
don't. Action items surface, but a human reviews and decides.

## What changed in Phase 25A

The audit produced 12 backlog items; the fast-win subset shipped in
this PR is:

- **GH-001** — encounter-level audio consent gate.
- **GH-002** — `/admin/security/stt-readiness` admin endpoint.
- **GH-003** — `scripts/prune_audio_retention.py` operator script.
- **GH-004** — backend mirror of `noteQualityChecks` (web → api).
- **GH-006** — clinical safety eval harness in `tests/evals/`.
- **GH-007** — `chart_context.py` interface + stub adapter.
- **GH-008** — `chart_conflicts.py` service for cross-source
  inconsistency surfacing.
- **GH-010** — this positioning doc.
- **GH-011** — demo-mode capability banner (backend label + UI).
- **GH-012** — Cora-comparison language added to claim guards.

The doc keeps growing with every audit cycle. Don't delete entries;
add a new dated section if positioning changes.

## Authoring notes

- This doc lives at `docs/product/chartnav-vs-cora-positioning.md`.
- It must not contain PHI, patient identifiers, or transcript
  fragments.
- Edits do not require a migration, but they DO require a
  re-review of `apps/web/scripts/check_forbidden_claims.mjs` to
  make sure new content does not introduce a forbidden phrase.
