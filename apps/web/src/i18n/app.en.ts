// apps/web/src/i18n/app.en.ts
//
// English copy for the authenticated ChartNav workspace chrome.
// This is the source of truth — every string here matches what the
// app rendered before the Phase A localization refactor, byte-for-
// byte, so existing vitest + Playwright assertions stay green.
//
// Do not edit any string here without updating:
//   - the matching key in apps/web/src/i18n/app.es.ts
//   - any test (apps/web/src/test/App.test.tsx, apps/web/tests/e2e/*)
//     that pins the exact phrase
// in the same commit.

import type { AppCopy } from "./types";

export const APP_EN: AppCopy = {
  // Top bar
  brandLogoAlt: "ChartNav",
  brandSub: "Workflow",
  apiChipPrefix: "API ",
  newEncounterButton: "+ New encounter",
  adminButton: "Admin",

  // Identity badge / picker
  identityBadgeLabel: "Identity",
  identityResolving: "resolving identity…",
  identityAuthPrefix: "auth: ",
  identityPickerLabel: "identity",
  identityPickerCustomOption: "Custom email…",
  identityPickerEmailPlaceholder: "user@example.com",
  identityPickerUseButton: "use",
  identityPickerSeededButton: "seeded",

  // Friendly role labels
  roleAdmin: "Admin",
  roleClinician: "Clinician",
  roleReviewer: "Reviewer",
  roleFrontDesk: "Front Desk",
  roleTechnician: "Technician",
  badgeOrgPrefix: "Org",

  // Sidebar nav
  sidebarNavAriaLabel: "Clinical navigation",
  sidebarGroupCore: "Core",
  sidebarGroupClinical: "Clinical",
  sidebarGroupOperations: "Operations",
  sidebarGroupAdmin: "Admin",
  sidebarGroupQuickActions: "Quick Actions",
  sidebarItemDashboard: "Dashboard",
  sidebarItemCalendar: "Calendar",
  sidebarItemEncounters: "Encounters",
  sidebarItemPatients: "Patients",
  sidebarItemLabOrders: "Lab / Orders",
  sidebarItemMultiClinic: "Multi-Clinic",
  sidebarItemTasks: "Tasks",
  sidebarItemMessages: "Messages",
  sidebarItemChat: "Chat",
  sidebarItemSecurityReadiness: "Security Readiness",
  sidebarItemProductionReadiness: "Production Readiness",
  sidebarItemDocuments: "Documents",
  sidebarItemReports: "Reports",
  sidebarItemSettings: "Settings",
  sidebarItemNewEncounter: "New Encounter",
  sidebarItemRecordDictation: "Record Dictation",
  sidebarItemUploadImaging: "Upload Imaging",
  sidebarItemInternalChatNote: "Internal Chat Note",

  // Filter bar
  filterStatusLabel: "Status",
  filterStatusAnyOption: "Any",
  filterProviderLabel: "Provider",
  filterProviderPlaceholder: "Dr. Carter",
  filterLocationLabel: "Location ID",
  filterLocationPlaceholder: "—",
  filterClearButton: "clear",

  // Encounter list
  encListLoading: "Loading…",
  encListEmpty: "No encounters match these filters.",

  // Pagination
  pagePrev: "← Prev",
  pageNext: "Next →",
  pageOfWord: "of",

  // Detail empty state
  detailEmpty:
    "Select an encounter from the list to see details, events, and allowed actions.",
  detailEmptyCreateLink: "+ New encounter",
  detailEmptyCreateSuffix: " above to create one.",

  // Detail loading
  detailLoading: "Loading…",

  // Banners
  bannerIdentitySwitchedPrefix: "Identity switched to ",
  bannerStatusPrefix: "Status → ",
  bannerEventAddedPrefix: "Event '",
  bannerEventAddedSuffix: "' added",
  bannerEncounterCreatedTemplate: "Encounter #{id} created ({pid})",

  // Footer
  footerBrandTagline: "Clinical workflow platform",
  footerPoweredByPrefix: "Powered by",
  footerPoweredEntity: "ARCG Systems",

  // Create-encounter modal
  createModalTitle: "New encounter",
  createModalCloseAria: "Close",
  createPatientIdLabel: "Patient ID *",
  createPatientIdPlaceholder: "PT-1234",
  createPatientNameLabel: "Patient name",
  createPatientNamePlaceholder: "Jane Doe",
  createProviderLabel: "Provider *",
  createProviderPlaceholder: "Dr. Carter",
  createLocationLabel: "Location *",
  createLocationLoading: "loading locations…",
  createLocationPlaceholder: "Select a location",
  createStatusLabel: "Initial status",
  createStatusScheduled: "scheduled",
  createStatusInProgress: "in_progress",
  createCancelButton: "Cancel",
  createSubmitButton: "Create encounter",
  createSubmitPending: "Creating…",

  // Switcher in the authenticated top bar
  appSwitcherAriaLabel: "Language",
  appSwitcherEnglishLabel: "English",
  appSwitcherSpanishLabel: "Español",
};
