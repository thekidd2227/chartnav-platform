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

/**
 * Phase A — authenticated-workspace chrome.
 *
 * Covers the top bar, sidebar nav, encounter list + filters,
 * encounter detail empty-state, banners, pagination, footer,
 * identity picker, and the create-encounter modal. Larger panels
 * (RoleDashboard, NoteWorkspace, AdminPanel, ClinicalTabbedWorkspace,
 * specialty trackers) are NOT in this surface — they'll arrive in
 * Phase B/C with their own typed slices.
 *
 * English copy is byte-identical to the prior inline strings so
 * every existing vitest assertion stays green by default. The
 * Spanish variant uses neutral Latin American Spanish with formal
 * "usted" tone, matching the landing-page style guide.
 */
export interface AppCopy {
  // Top bar.
  brandLogoAlt: string;
  brandSub: string;
  apiChipPrefix: string;
  newEncounterButton: string;
  adminButton: string;

  // Identity badge / picker.
  identityBadgeLabel: string;
  identityResolving: string;
  identityAuthPrefix: string;
  identityPickerLabel: string;
  identityPickerCustomOption: string;
  identityPickerEmailPlaceholder: string;
  identityPickerUseButton: string;
  identityPickerSeededButton: string;

  // Friendly role labels.
  roleAdmin: string;
  roleClinician: string;
  roleReviewer: string;
  roleFrontDesk: string;
  roleTechnician: string;
  badgeOrgPrefix: string;

  // Sidebar nav.
  sidebarNavAriaLabel: string;
  sidebarGroupCore: string;
  sidebarGroupClinical: string;
  sidebarGroupOperations: string;
  sidebarGroupAdmin: string;
  sidebarGroupQuickActions: string;
  sidebarItemDashboard: string;
  sidebarItemCalendar: string;
  sidebarItemEncounters: string;
  sidebarItemPatients: string;
  sidebarItemLabOrders: string;
  sidebarItemMultiClinic: string;
  sidebarItemTasks: string;
  sidebarItemMessages: string;
  sidebarItemChat: string;
  sidebarItemSecurityReadiness: string;
  sidebarItemProductionReadiness: string;
  sidebarItemDocuments: string;
  sidebarItemReports: string;
  sidebarItemSettings: string;
  sidebarItemNewEncounter: string;
  sidebarItemRecordDictation: string;
  sidebarItemUploadImaging: string;
  sidebarItemInternalChatNote: string;

  // Filter bar.
  filterStatusLabel: string;
  filterStatusAnyOption: string;
  filterProviderLabel: string;
  filterProviderPlaceholder: string;
  filterLocationLabel: string;
  filterLocationPlaceholder: string;
  filterClearButton: string;

  // Encounter list.
  encListLoading: string;
  encListEmpty: string;

  // Pagination.
  pagePrev: string;
  pageNext: string;
  /** Localized word rendered between offset and total:
   *  English "of", Spanish "de". */
  pageOfWord: string;

  // Detail empty state.
  detailEmpty: string;
  detailEmptyCreateLink: string;
  detailEmptyCreateSuffix: string;

  // Detail loading.
  detailLoading: string;

  // Banners (the dynamic parts of `Banner.msg` strings are
  // assembled from these prefixes/suffixes so both locales render
  // grammatically).
  bannerIdentitySwitchedPrefix: string;
  bannerStatusPrefix: string;
  bannerEventAddedPrefix: string;
  bannerEventAddedSuffix: string;
  /** Template with `{id}` and `{pid}` substitution markers. */
  bannerEncounterCreatedTemplate: string;

  // Footer.
  footerBrandTagline: string;
  footerPoweredByPrefix: string;
  footerPoweredEntity: string;

  // Create-encounter modal.
  createModalTitle: string;
  createModalCloseAria: string;
  createPatientIdLabel: string;
  createPatientIdPlaceholder: string;
  createPatientNameLabel: string;
  createPatientNamePlaceholder: string;
  createProviderLabel: string;
  createProviderPlaceholder: string;
  createLocationLabel: string;
  createLocationLoading: string;
  createLocationPlaceholder: string;
  createStatusLabel: string;
  createStatusScheduled: string;
  createStatusInProgress: string;
  createCancelButton: string;
  createSubmitButton: string;
  createSubmitPending: string;

  // Switcher in the authenticated top bar.
  appSwitcherAriaLabel: string;
  appSwitcherEnglishLabel: string;
  appSwitcherSpanishLabel: string;
}
