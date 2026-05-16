// apps/web/src/i18n/app.es.ts
//
// Spanish (Latin American neutral, formal "usted") copy for the
// authenticated ChartNav workspace chrome — Phase A.
//
// Style guide: docs/website/chartnav-spanish-localization-style-guide.md
//
// Same shape as app.en.ts. Every claim-bearing label preserves the
// safe-claims contract: no positive HIPAA / certified-EHR claims,
// no "automatic orders" framing, etc. Phase A scope is chrome —
// these strings don't make clinical claims, but if any future
// string would, run scripts/check_website_claims.sh + style guide.

import type { AppCopy } from "./types";

export const APP_ES: AppCopy = {
  // Top bar
  brandLogoAlt: "ChartNav",
  brandSub: "Flujo de trabajo",
  apiChipPrefix: "API ",
  newEncounterButton: "+ Nuevo encuentro",
  adminButton: "Administración",

  // Identity badge / picker
  identityBadgeLabel: "Identidad",
  identityResolving: "resolviendo identidad…",
  identityAuthPrefix: "autenticación: ",
  identityPickerLabel: "identidad",
  identityPickerCustomOption: "Correo personalizado…",
  identityPickerEmailPlaceholder: "usuario@ejemplo.com",
  identityPickerUseButton: "usar",
  identityPickerSeededButton: "preconfigurada",

  // Friendly role labels
  roleAdmin: "Administrador",
  roleClinician: "Clínico",
  roleReviewer: "Revisor",
  roleFrontDesk: "Recepción",
  roleTechnician: "Técnico",
  badgeOrgPrefix: "Org.",

  // Sidebar nav
  sidebarNavAriaLabel: "Navegación clínica",
  sidebarGroupCore: "Principal",
  sidebarGroupClinical: "Clínico",
  sidebarGroupOperations: "Operaciones",
  sidebarGroupAdmin: "Administración",
  sidebarGroupQuickActions: "Acciones rápidas",
  sidebarItemDashboard: "Panel",
  sidebarItemCalendar: "Calendario",
  sidebarItemEncounters: "Encuentros",
  sidebarItemPatients: "Pacientes",
  sidebarItemLabOrders: "Laboratorio / Órdenes",
  sidebarItemMultiClinic: "Multi-clínica",
  sidebarItemTasks: "Tareas",
  sidebarItemMessages: "Mensajes",
  sidebarItemChat: "Chat interno",
  sidebarItemSecurityReadiness: "Preparación de seguridad",
  sidebarItemProductionReadiness: "Preparación de producción",
  sidebarItemDocuments: "Documentos",
  sidebarItemReports: "Reportes",
  sidebarItemSettings: "Configuración",
  sidebarItemNewEncounter: "Nuevo encuentro",
  sidebarItemRecordDictation: "Grabar dictado",
  sidebarItemUploadImaging: "Cargar imágenes",
  sidebarItemInternalChatNote: "Nota interna del equipo",

  // Filter bar
  filterStatusLabel: "Estado",
  filterStatusAnyOption: "Cualquiera",
  filterProviderLabel: "Proveedor",
  filterProviderPlaceholder: "Dr. Carter",
  filterLocationLabel: "ID de ubicación",
  filterLocationPlaceholder: "—",
  filterClearButton: "limpiar",

  // Encounter list
  encListLoading: "Cargando…",
  encListEmpty: "Ningún encuentro coincide con estos filtros.",

  // Pagination
  pagePrev: "← Anterior",
  pageNext: "Siguiente →",
  pageOfWord: "de",

  // Detail empty state
  detailEmpty:
    "Seleccione un encuentro de la lista para ver los detalles, los eventos y las acciones permitidas.",
  detailEmptyCreateLink: "+ Nuevo encuentro",
  detailEmptyCreateSuffix: " arriba para crear uno.",

  // Detail loading
  detailLoading: "Cargando…",

  // Banners
  bannerIdentitySwitchedPrefix: "Identidad cambiada a ",
  bannerStatusPrefix: "Estado → ",
  bannerEventAddedPrefix: "Evento '",
  bannerEventAddedSuffix: "' agregado",
  bannerEncounterCreatedTemplate: "Encuentro #{id} creado ({pid})",

  // Footer
  footerBrandTagline: "Plataforma de flujo clínico",
  footerPoweredByPrefix: "Operado por",
  footerPoweredEntity: "ARCG Systems",

  // Create-encounter modal
  createModalTitle: "Nuevo encuentro",
  createModalCloseAria: "Cerrar",
  createPatientIdLabel: "ID del paciente *",
  createPatientIdPlaceholder: "PT-1234",
  createPatientNameLabel: "Nombre del paciente",
  createPatientNamePlaceholder: "Juana Pérez",
  createProviderLabel: "Proveedor *",
  createProviderPlaceholder: "Dr. Carter",
  createLocationLabel: "Ubicación *",
  createLocationLoading: "cargando ubicaciones…",
  createLocationPlaceholder: "Seleccione una ubicación",
  createStatusLabel: "Estado inicial",
  createStatusScheduled: "agendado",
  createStatusInProgress: "en progreso",
  createCancelButton: "Cancelar",
  createSubmitButton: "Crear encuentro",
  createSubmitPending: "Creando…",

  // Switcher in the authenticated top bar
  appSwitcherAriaLabel: "Idioma",
  appSwitcherEnglishLabel: "English",
  appSwitcherSpanishLabel: "Español",
};
