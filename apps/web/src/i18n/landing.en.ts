// apps/web/src/i18n/landing.en.ts
//
// English copy for the ChartNav public landing page. This is the
// source of truth — every string here matches the Phase 16 / 17 /
// 21C / 24A landing page byte-for-byte, so the existing
// WebsiteProofUpgrade vitest assertions stay green after the Spanish
// localization refactor.
//
// Do not edit individual strings without updating:
//   - apps/web/src/test/WebsiteProofUpgrade.test.tsx
//   - scripts/check_website_claims.sh (required-phrase list)
//   - docs/website/chartnav-spanish-localization-style-guide.md
// in the same commit.

import type { LandingCopy, ModuleCard, SafetyModelRow, WorkflowStage } from "./types";

const MODULES: ModuleCard[] = [
  {
    id: "scribe",
    title: "AI scribe session lifecycle",
    body:
      "Drafts a structured note from source text or transcript. " +
      "The provider reviews and explicitly finalizes — never automatic. " +
      "Finalized sessions are immutable.",
  },
  {
    id: "proposals",
    title: "Retinal proposal review",
    body:
      "Generates OD/OS annotation proposals from finalized findings " +
      "text. Read-only suggestions; nothing lands on the diagram " +
      "until the provider explicitly applies a proposal.",
  },
  {
    id: "diagram",
    title: "OD/OS retinal drawing canvas",
    body:
      "Provider-authored OD/OS annotations with normalized " +
      "coordinates. Saved artifacts are versioned; signed artifacts " +
      "are immutable in place — edits create an explicit fork.",
  },
  {
    id: "summary",
    title: "Patient-friendly summary",
    body:
      "Plain-language draft built from finalized scribe content. " +
      "The provider edits, reviews, and finalizes. ChartNav never " +
      "sends the summary to the patient.",
  },
  {
    id: "brief",
    title: "Pre-visit clinical brief",
    body:
      "Derived view of available chart records with explicit data " +
      "gaps. Surfaces what is and is not on file before the visit. " +
      "Not a clinical decision.",
  },
  {
    id: "queue",
    title: "Provider action review queue",
    body:
      "Review tasks only — sign unsigned diagram, finalize summary, " +
      "review chart language. Suggested → accepted → completed. " +
      "Dismissed and completed are immutable. Never an order.",
  },
  {
    id: "demo",
    title: "Guided demo mode",
    body:
      "Opt-in (?demo=1) presenter overlay with an 8-step workflow " +
      "stepper, on-screen cues, and Reset. Deterministic by design; " +
      "no API calls; no clinical state side effects.",
  },
  {
    id: "pilot",
    title: "Pilot-readiness package",
    body:
      "Eight-doc pilot packet covering readiness, deployment, " +
      "admin onboarding, security review, support runbook, " +
      "demo→pilot transition, known limitations, success metrics.",
  },
];

const WORKFLOW: WorkflowStage[] = [
  { id: "scribe", label: "Scribe session", short: "Draft → review → finalize" },
  { id: "proposals", label: "Findings proposals", short: "Read-only suggestions" },
  { id: "diagram", label: "OD/OS diagram", short: "Apply, save, sign" },
  { id: "summary", label: "Patient summary", short: "Provider-reviewed draft" },
  { id: "brief", label: "Pre-visit brief", short: "Derived chart context" },
  { id: "queue", label: "Action review queue", short: "Suggested → accepted → completed" },
  { id: "demo", label: "Guided demo", short: "Pilot-ready" },
];

const SAFETY_MODEL: SafetyModelRow[] = [
  {
    state: "Draft",
    body:
      "All AI-assisted artifacts start as a draft for the provider to review. " +
      "Nothing is treated as final until an explicit click.",
  },
  {
    state: "Review",
    body:
      "Provider edits and explicitly marks the artifact reviewed. " +
      "Required before finalize.",
  },
  {
    state: "Finalize",
    body:
      "Explicit finalize stamps the artifact and renders it immutable. " +
      "Re-edits to a signed retinal artifact create an explicit fork.",
  },
  {
    state: "Audit",
    body:
      "Every mutation emits a metadata-only audit row. Section bodies, " +
      "summary text, scribe text, and brief sections never reach the audit log.",
  },
  {
    state: "Org isolation",
    body:
      "Cross-organization access returns 404 patient_not_found. " +
      "Every per-source SELECT re-asserts the org filter for defense in depth.",
  },
  {
    state: "RBAC",
    body:
      "Admin and clinician can write across the workflow. Reviewer is " +
      "read-only. Reviewer write attempts return 403 role_forbidden.",
  },
];

const NON_GOALS: string[] = [
  "Not a certified EHR. ChartNav sits alongside your existing EHR; it does not replace it.",
  "Not HIPAA-certified. Real-PHI pilot requires BAA, security review, production auth, approved hosting, monitoring, backups, incident contacts, and written practice approval.",
  "Not autonomous diagnosis. Provider interpretation stays with the clinician.",
  "Does not autofill IOP, refraction, or cup-to-disc ratio.",
  "Does not interpret OCT scans, fundus photographs, or visual fields.",
  "Does not select IOL power or anti-VEGF dosing.",
  "Does not place orders, send referrals, submit claims, or handle insurance.",
  "Does not send patient messages automatically. No patient-facing surface.",
  "Not a current integration with any specific imaging-device vendor.",
];

const SAFETY_BULLETS: string[] = [
  "Provider-reviewed workflow support.",
  "ChartNav does not diagnose, create orders, send referrals, bill, or message patients automatically.",
  "Every clinical artifact requires explicit provider review before it is treated as final.",
];

export const LANDING_EN: LandingCopy = {
  docTitle:
    "ChartNav MD — Ophthalmology Workflow + Provider-Reviewed Documentation",
  docDescription:
    "ChartNav is the clinical workflow layer for ophthalmology practices. Role-based clinic dashboards, retina and glaucoma tracking, imaging metadata review, OD/OS retinal diagram, and provider-reviewed documentation — provider-controlled at every step. Not a certified EHR replacement. Not HIPAA-certified by default.",

  brandLogoAlt: "ChartNav",

  heroTitle:
    "ChartNav is the clinical workflow layer for ophthalmology practices — provider-reviewed at every step.",
  heroSub:
    "Front desk to tech workup to imaging review to provider sign-off — built for eye-care lanes. Role-based clinic dashboards, structured retina and glaucoma tracking, an imaging metadata pipeline, OD/OS retinal diagram review, and provider-reviewed documentation in one workspace. Provider-reviewed at every step. Provider-controlled at every transition.",
  heroSafetyLine:
    "Provider-reviewed workflow support. ChartNav does not diagnose, create orders, send referrals, bill, or message patients automatically. ChartNav does not interpret OCTs, fundus photos, or visual fields. ChartNav does not submit claims or handle insurance.",
  heroCtaPrimary: "Request a fake-patient demo",
  heroCtaSecondary: "See how the workflow works",

  workflowHeading: "From note to retina-ready chart",
  workflowLead: "Seven explicit steps. The provider drives every transition.",
  workflow: WORKFLOW,
  workflowSvgAriaLabel: "ChartNav ophthalmology clinical workflow",
  workflowSvgTitle: "ChartNav ophthalmology clinical workflow",

  ophthalmologyHeading: "Built for ophthalmology, end to end",
  ophthalmologyBullets: [
    {
      strong: "OD/OS retinal canvas.",
      rest:
        "Normalized coordinates per eye pane. Drawing, signing, and forking are first-class concepts — not features bolted onto a generic SOAP-note generator.",
    },
    {
      strong: "Findings vocabulary that matches the chart.",
      rest:
        "Drusen, dot/blot hemorrhage, flame hemorrhage, microaneurysm, neovascularization. Not a primary-care shortcut library.",
    },
    {
      strong: "Superior / inferior / nasal / temporal placement.",
      rest:
        "Annotations carry their position relative to the macula and disc on each eye, so a follow-up provider sees the same picture you saw.",
    },
    {
      strong: "Provider-reviewed diagram signing.",
      rest:
        "Signed artifacts are immutable in place. Edits create an explicit fork with a parent pointer; the original signature survives.",
    },
    {
      strong: "Ophthalmology-flavored documentation flow.",
      rest:
        "Closed structured-note vocabulary (chief complaint, HPI, exam, assessment, plan). The patient-friendly summary template composes from already-stored ophthalmic content (visual acuity, IOP, plan, follow-up).",
    },
  ],

  providerControlHeading: "The provider controls every step",
  providerControlLead:
    "Drafts wait for explicit review. Finalize is a click. Signed artifacts are immutable. ChartNav surfaces structured chart context — the provider decides.",
  providerControlSvgAriaLabel: "Provider-in-control state model",
  providerControlSvgTitle: "Provider-in-control state model",
  providerControlReviewLabel: "review",
  providerControlFinalizeLabel: "finalize",
  providerControlImmutableNote:
    "Finalized artifacts are immutable. Re-edits to signed retinal artifacts create an explicit fork.",
  providerControlDraftLabel: "Draft",
  providerControlReviewedLabel: "Reviewed",
  providerControlFinalizedLabel: "Finalized",
  safetyModel: SAFETY_MODEL,

  modulesHeading: "What's in the workflow",
  modulesLead: "Eight modules. All built. All provider-reviewed.",
  modules: MODULES,

  beforeAfterHeading: "Before ChartNav · With ChartNav",
  beforeHeading: "Before",
  afterHeading: "With ChartNav",
  beforeItems: [
    "Free-form notes drift across the chart.",
    "Retinal findings live in narrative text only.",
    "OD/OS diagrams are paper or one-off.",
    "Patient-friendly summaries are written from scratch.",
    "No structured pre-visit chart prep.",
  ],
  afterItems: [
    "Structured ophthalmology note vocabulary, provider-reviewed.",
    "Retinal findings tied to OD/OS canvas annotations.",
    "OD/OS diagrams versioned and signed; edits fork explicitly.",
    "Patient summary drafts composed from finalized chart content.",
    "Pre-visit brief surfaces source counts and explicit gaps.",
  ],

  demoPilotHeading: "Built for pilot conversations",
  demoPilotBody:
    "Live demos run on fake demo data only. Real patient data requires a Business Associate Agreement (or equivalent), a security review of the deployment posture, and a controlled-pilot mode — see the pilot readiness packet for gating items.",
  demoPilotBullets: [
    {
      strong: "Live fake-patient demo.",
      rest: "Five minutes, seven steps, every step provider-reviewed.",
    },
    {
      strong: "Controlled pilot conversation.",
      rest:
        "Pilot readiness checklist, deployment guide, security review packet — buyer-safe phrasing throughout.",
    },
    {
      strong: "Provider-in-control workflow.",
      rest:
        "Discuss how the draft / review / finalize state model fits your ophthalmology practice.",
    },
  ],
  demoPilotCtaPrimary: "Discuss a controlled ophthalmology pilot",
  demoPilotCtaSecondary: "Review the provider-in-control workflow",

  nonGoalsHeading: "What ChartNav is not",
  nonGoals: NON_GOALS,
  safetyBullets: SAFETY_BULLETS,

  footerOperatedBy: "ChartNav is operated by ARCG.",
  footerRenderedPrefix: "Page rendered",
  footerProductAppPrefix: "The product app is at ",
  footerProductAppLink: "the ChartNav workspace",
  footerProductAppSuffix:
    ". The Phase 13 demo guide and Phase 15 Guided Demo Mode are opt-in there. The pilot readiness packet lives under",

  switcherLabel: "Language",
  switcherEnglishLabel: "English",
  switcherSpanishLabel: "Español",
};
