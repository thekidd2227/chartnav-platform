// AppSpanish.test.tsx
//
// Phase A — vitest coverage for the authenticated-workspace
// Spanish localization. Verifies:
//   - clicking the new Español switcher in the top bar swaps every
//     chrome string we care about (top-bar buttons, sidebar items,
//     filter labels, list empty state, detail empty state, footer);
//   - persistence writes "es" to localStorage under
//     chartnav.language so a refresh keeps the choice;
//   - <html lang> is set to "es" while Spanish is active;
//   - the create-encounter modal renders Spanish labels;
//   - banner messages use the Spanish prefix template;
//   - the English-default render is intact (delegated to the
//     existing App.test.tsx — this file only adds the Spanish
//     surface so we do NOT duplicate that work).
//
// The Spanish render shares the same testids as the English
// render — only the text content changes.

import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../api", async () => {
  const actual = await vi.importActual<typeof import("../api")>("../api");
  return {
    ...actual,
    API_URL: "http://test",
    getMe: vi.fn(),
    listEncounters: vi.fn(),
    listEncountersPage: vi.fn(),
    getEncounter: vi.fn(),
    getEncounterEvents: vi.fn(),
    createEncounterEvent: vi.fn(),
    updateEncounterStatus: vi.fn(),
    listLocations: vi.fn(),
    createEncounter: vi.fn(),
    bridgeEncounter: vi.fn(),
    listEncounterInputs: vi.fn().mockResolvedValue([]),
    listEncounterNotes: vi.fn().mockResolvedValue([]),
    getNoteVersion: vi.fn().mockResolvedValue({ note: null, findings: null }),
    createEncounterInput: vi.fn(),
    generateNoteVersion: vi.fn(),
    patchNoteVersion: vi.fn(),
    submitNoteForReview: vi.fn(),
    signNoteVersion: vi.fn(),
    exportNoteVersion: vi.fn(),
    processEncounterInput: vi.fn(),
    retryEncounterInput: vi.fn(),
    refreshBridgedEncounter: vi.fn(),
    runWorkerTick: vi.fn(),
    drainWorkerQueue: vi.fn(),
    requeueStaleClaims: vi.fn(),
  };
});

import * as api from "../api";
import App from "../App";

const ADMIN1: api.Me = {
  user_id: 1,
  email: "admin@chartnav.local",
  organization_id: 1,
  organization_name: "demo-eye-clinic",
  organization_slug: "demo-eye-clinic",
  full_name: "ChartNav Admin",
  role: "admin",
  user_active: true,
  organization_active: true,
} as unknown as api.Me;

const SAMPLE_ENC: api.Encounter = {
  id: 1,
  organization_id: 1,
  location_id: 1,
  patient_identifier: "PT-1001",
  patient_name: "Morgan Lee",
  provider_name: "Dr. Carter",
  status: "in_progress",
  created_at: "2026-04-18 09:00:00",
  updated_at: "2026-04-18 09:00:00",
} as unknown as api.Encounter;

beforeEach(() => {
  vi.clearAllMocks();
  try {
    window.localStorage.removeItem("chartnav.language");
    // Ensure the default identity resolves cleanly.
    window.localStorage.removeItem("chartnav.devIdentity");
  } catch {
    // ignore
  }
  // Reset html lang so the useEffect cleanup is observable.
  document.documentElement.lang = "en";
  // Clear ?lang from any prior test.
  try {
    window.history.replaceState({}, "", "/");
  } catch {
    // ignore
  }

  (api.getMe as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(ADMIN1);
  (api.listEncountersPage as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
    items: [SAMPLE_ENC],
    total: 1,
    limit: 25,
    offset: 0,
  });
  (api.listLocations as unknown as ReturnType<typeof vi.fn>).mockResolvedValue([
    { id: 1, organization_id: 1, name: "Main Clinic" },
  ]);
  (api.getEncounter as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(SAMPLE_ENC);
  (api.getEncounterEvents as unknown as ReturnType<typeof vi.fn>).mockResolvedValue([]);
});

describe("App — Spanish localization (Phase A)", () => {
  it("English render is the default; switcher shows both options", async () => {
    render(<App />);
    await screen.findByTestId("identity-badge");
    expect(
      screen.getByTestId("open-create-encounter"),
    ).toHaveTextContent("+ New encounter");
    expect(screen.getByTestId("open-admin-panel")).toHaveTextContent("Admin");
    const sw = screen.getByTestId("app-lang-switcher");
    expect(within(sw).getByTestId("app-lang-option-en")).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(within(sw).getByTestId("app-lang-option-es")).toHaveAttribute(
      "aria-pressed",
      "false",
    );
  });

  it("clicking Español swaps top-bar + sidebar + filter strings and persists choice", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByTestId("identity-badge");

    await user.click(screen.getByTestId("app-lang-option-es"));

    // Top bar
    expect(
      screen.getByTestId("open-create-encounter"),
    ).toHaveTextContent("+ Nuevo encuentro");
    expect(screen.getByTestId("open-admin-panel")).toHaveTextContent(
      /Administración/,
    );

    // Identity badge — friendly role + Spanish "Org." prefix
    const badge = screen.getByTestId("identity-badge");
    expect(badge).toHaveTextContent("Identidad");
    expect(badge).toHaveTextContent("Administrador");

    // Sidebar items
    expect(
      screen.getByTestId("sidebar-item-dashboard"),
    ).toHaveTextContent("Panel");
    expect(
      screen.getByTestId("sidebar-item-encounters"),
    ).toHaveTextContent("Encuentros");
    expect(
      screen.getByTestId("sidebar-item-multi-clinic"),
    ).toHaveTextContent(/Multi-clínica/);
    expect(
      screen.getByTestId("sidebar-item-security-readiness"),
    ).toHaveTextContent(/Preparación de seguridad/);

    // Persistence
    expect(window.localStorage.getItem("chartnav.language")).toBe("es");

    // html lang updated
    expect(document.documentElement.lang).toBe("es");
  });

  it("filter labels render in Spanish after switching", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByTestId("identity-badge");
    await user.click(screen.getByTestId("app-lang-option-es"));

    // The filter status select still has English ALLOWED_STATUSES
    // option values (they're enums), but the surrounding label +
    // "Any" option are translated.
    const statusSelect = screen.getByTestId("filter-status");
    const anyOption = within(statusSelect).getByRole("option", {
      name: /Cualquiera/,
    });
    expect(anyOption).toBeInTheDocument();
  });

  it("encounter detail empty state renders Spanish copy with the create hint", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByTestId("identity-badge");
    await user.click(screen.getByTestId("app-lang-option-es"));

    // No selectedId at start → empty pane is shown.
    expect(
      screen.getByText(/Seleccione un encuentro de la lista/i),
    ).toBeInTheDocument();
    const hint = screen.getByTestId("detail-empty-create-hint");
    expect(hint).toHaveTextContent(/\+ Nuevo encuentro/);
    expect(hint).toHaveTextContent(/arriba para crear uno/);
  });

  it("footer renders the Spanish tagline + 'Operado por ARCG Systems'", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByTestId("identity-badge");
    await user.click(screen.getByTestId("app-lang-option-es"));

    const footer = screen.getByTestId("app-footer");
    expect(footer).toHaveTextContent(/Plataforma de flujo clínico/);
    const powered = screen.getByTestId("app-footer-arcg");
    expect(powered).toHaveTextContent(/Operado por\s+ARCG Systems/);
  });

  it("create-encounter modal renders Spanish field labels + buttons", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByTestId("identity-badge");
    await user.click(screen.getByTestId("app-lang-option-es"));

    await user.click(screen.getByTestId("open-create-encounter"));
    const modal = await screen.findByTestId("create-modal");
    expect(within(modal).getByText("Nuevo encuentro")).toBeInTheDocument();
    expect(within(modal).getByText(/ID del paciente \*/)).toBeInTheDocument();
    expect(within(modal).getByText(/Proveedor \*/)).toBeInTheDocument();
    expect(within(modal).getByText(/Ubicación \*/)).toBeInTheDocument();
    expect(within(modal).getByText(/Estado inicial/)).toBeInTheDocument();
    expect(within(modal).getByText("Cancelar")).toBeInTheDocument();
    expect(within(modal).getByText("Crear encuentro")).toBeInTheDocument();
  });

  it("banner messages use Spanish prefixes when the user switches identities", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByTestId("identity-badge");
    await user.click(screen.getByTestId("app-lang-option-es"));

    // Switch to a seeded clin identity.
    const select = screen.getByTestId("identity-select");
    await user.selectOptions(select, "clin@chartnav.local");
    // The banner message uses the Spanish prefix.
    const banner = await screen.findByTestId("banner-info");
    expect(banner).toHaveTextContent(/Identidad cambiada a/);
  });

  it("?lang=es in the URL renders Spanish on first paint", async () => {
    try {
      window.history.replaceState({}, "", "/?lang=es");
    } catch {
      // ignore
    }
    render(<App />);
    await screen.findByTestId("identity-badge");
    expect(
      screen.getByTestId("open-create-encounter"),
    ).toHaveTextContent("+ Nuevo encuentro");
    expect(document.documentElement.lang).toBe("es");
  });

  it("English default stays intact after a Spanish toggle is cleared", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByTestId("identity-badge");
    await user.click(screen.getByTestId("app-lang-option-es"));
    await waitFor(() => {
      expect(
        screen.getByTestId("open-create-encounter"),
      ).toHaveTextContent("+ Nuevo encuentro");
    });
    await user.click(screen.getByTestId("app-lang-option-en"));
    expect(
      screen.getByTestId("open-create-encounter"),
    ).toHaveTextContent("+ New encounter");
    expect(window.localStorage.getItem("chartnav.language")).toBe("en");
    expect(document.documentElement.lang).toBe("en");
  });
});
