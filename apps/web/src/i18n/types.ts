// apps/web/src/i18n/types.ts
//
// Type shape for the ChartNav public landing-page copy. The English
// locale is the source of truth; every other locale (currently
// Spanish only) must populate every key.
//
// This file is dependency-free and ships no runtime — keeping the
// public website bundle small (no i18next, no react-intl).

export type Language = "en" | "es";

export interface ModuleCard {
  id: string;
  title: string;
  body: string;
}

export interface WorkflowStage {
  id: string;
  label: string;
  short: string;
}

export interface SafetyModelRow {
  state: string;
  body: string;
}

export interface LandingCopy {
  // Document-level metadata (set on <title> and <meta description>
  // via a useEffect when the active language is not the default).
  docTitle: string;
  docDescription: string;

  // Brand logo alt text.
  brandLogoAlt: string;

  // Hero.
  heroTitle: string;
  heroSub: string;
  heroSafetyLine: string;
  heroCtaPrimary: string;
  heroCtaSecondary: string;

  // Workflow section.
  workflowHeading: string;
  workflowLead: string;
  workflow: WorkflowStage[];
  workflowSvgAriaLabel: string;
  workflowSvgTitle: string;

  // Ophthalmology proof section.
  ophthalmologyHeading: string;
  ophthalmologyBullets: { strong: string; rest: string }[];

  // Provider-in-control section.
  providerControlHeading: string;
  providerControlLead: string;
  providerControlSvgAriaLabel: string;
  providerControlSvgTitle: string;
  providerControlReviewLabel: string;
  providerControlFinalizeLabel: string;
  providerControlImmutableNote: string;
  // The state-machine state labels rendered inside the SVG boxes.
  providerControlDraftLabel: string;
  providerControlReviewedLabel: string;
  providerControlFinalizedLabel: string;
  safetyModel: SafetyModelRow[];

  // Modules section.
  modulesHeading: string;
  modulesLead: string;
  modules: ModuleCard[];

  // Before / with-ChartNav comparison.
  beforeAfterHeading: string;
  beforeHeading: string;
  afterHeading: string;
  beforeItems: string[];
  afterItems: string[];

  // Demo / pilot CTA section.
  demoPilotHeading: string;
  demoPilotBody: string;
  demoPilotBullets: { strong: string; rest: string }[];
  demoPilotCtaPrimary: string;
  demoPilotCtaSecondary: string;

  // Non-goals section.
  nonGoalsHeading: string;
  nonGoals: string[];
  safetyBullets: string[];

  // Footer.
  footerOperatedBy: string;
  footerRenderedPrefix: string;
  footerProductAppPrefix: string;
  footerProductAppLink: string;
  footerProductAppSuffix: string;

  // Language switcher.
  switcherLabel: string;
  switcherEnglishLabel: string;
  switcherSpanishLabel: string;
}
