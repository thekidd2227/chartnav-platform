import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

// Mock the entire api module so tests don't hit the network.
vi.mock("../api", async () => {
  const actual =
    await vi.importActual<typeof import("../api")>("../api");
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
    // Phase-19 workspace endpoints — keep App-level tests from
    // blowing up on NoteWorkspace mounting inside the detail pane.
    listEncounterInputs: vi.fn().mockResolvedValue([]),
    listEncounterNotes: vi.fn().mockResolvedValue([]),
    getNoteVersion: vi.fn().mockResolvedValue({ note: null, findings: null }),
    createEncounterInput: vi.fn(),
    generateNoteVersion: vi.fn(),
    patchNoteVersion: vi.fn(),
    submitNoteForReview: vi.fn(),
    signNoteVersion: vi.fn(),
    exportNoteVersion: vi.fn(),
    // Phase 22 — ingestion lifecycle.
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

const ORG1_ENCOUNTERS: api.Encounter[] = [
  {
    id: 1,
    organization_id: 1,
    location_id: 1,
    patient_identifier: "PT-1001",
    patient_name: "Morgan Lee",
    provider_name: "Dr. Carter",
    status: "in_progress",
    scheduled_at: null,
    started_at: "2026-04-18 10:00:00",
    completed_at: null,
    created_at: "2026-04-18 10:00:00",
  },
  {
    id: 2,
    organization_id: 1,
    location_id: 1,
    patient_identifier: "PT-1002",
    patient_name: "Jordan Rivera",
    provider_name: "Dr. Patel",
    status: "review_needed",
    scheduled_at: null,
    started_at: "2026-04-17 10:00:00",
    completed_at: null,
    created_at: "2026-04-17 10:00:00",
  },
];

const ORG2_ENCOUNTERS: api.Encounter[] = [
  {
    id: 3,
    organization_id: 2,
    location_id: 2,
    patient_identifier: "PT-2001",
    patient_name: "Priya Shah",
    provider_name: "Dr. Ahmed",
    status: "scheduled",
    scheduled_at: null,
    started_at: null,
    completed_at: null,
    created_at: "2026-04-17 10:00:00",
  },
];

const ADMIN1: api.Me = {
  user_id: 1,
  email: "admin@chartnav.local",
  full_name: "ChartNav Admin",
  role: "admin",
  organization_id: 1,
  is_authorized_final_signer: false,
};
const CLIN1: api.Me = { ...ADMIN1, user_id: 2, email: "clin@chartnav.local", role: "clinician", full_name: "Casey C." };
const REV1: api.Me = { ...ADMIN1, user_id: 3, email: "rev@chartnav.local", role: "reviewer", full_name: "Riley R." };
const ADMIN2: api.Me = { ...ADMIN1, user_id: 4, email: "admin@northside.local", organization_id: 2, full_name: "Northside Admin" };

function meMock() {
  (api.getMe as unknown as ReturnType<typeof vi.fn>).mockImplementation(
    async (email: string) => {
      switch (email) {
        case "admin@chartnav.local": return ADMIN1;
        case "clin@chartnav.local":  return CLIN1;
        case "rev@chartnav.local":   return REV1;
        case "admin@northside.local":return ADMIN2;
        case "clin@northside.local":
          return { ...CLIN1, user_id: 5, email: "clin@northside.local", organization_id: 2 };
        default:
          throw new api.ApiError(401, "unknown_user", "no user matches X-User-Email");
      }
    }
  );
}

function listMock() {
  (api.listEncounters as unknown as ReturnType<typeof vi.fn>).mockImplementation(
    async (email: string, filters: api.EncounterFilters = {}) => {
      const base = email.endsWith("@northside.local") ? ORG2_ENCOUNTERS : ORG1_ENCOUNTERS;
      let rows = [...base];
      if (filters.status) rows = rows.filter((r) => r.status === filters.status);
      if (filters.provider_name) rows = rows.filter((r) => r.provider_name === filters.provider_name);
      return rows;
    }
  );
  (api.listEncountersPage as unknown as ReturnType<typeof vi.fn>).mockImplementation(
    async (email: string, filters: api.EncounterFilters = {}, page: { limit?: number; offset?: number } = {}) => {
      const base = email.endsWith("@northside.local") ? ORG2_ENCOUNTERS : ORG1_ENCOUNTERS;
      let rows = [...base];
      if (filters.status) rows = rows.filter((r) => r.status === filters.status);
      if (filters.provider_name) rows = rows.filter((r) => r.provider_name === filters.provider_name);
      const total = rows.length;
      const limit = page.limit ?? 25;
      const offset = page.offset ?? 0;
      return { items: rows.slice(offset, offset + limit), total, limit, offset };
    }
  );
}

function detailMock() {
  (api.getEncounter as unknown as ReturnType<typeof vi.fn>).mockImplementation(
    async (_email: string, id: number) => {
      const all = [...ORG1_ENCOUNTERS, ...ORG2_ENCOUNTERS];
      const row = all.find((r) => r.id === id);
      if (!row) throw new api.ApiError(404, "encounter_not_found", "no such encounter in your organization");
      return row;
    }
  );
  (api.getEncounterEvents as unknown as ReturnType<typeof vi.fn>).mockImplementation(
    async (_email: string, id: number) => [
      { id: id * 10, encounter_id: id, event_type: "encounter_created", event_data: { status: "scheduled" }, created_at: "2026-04-18 09:00:00" },
    ]
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  meMock();
  listMock();
  detailMock();
  (api.listLocations as unknown as ReturnType<typeof vi.fn>).mockResolvedValue([
    { id: 1, organization_id: 1, name: "Main Clinic" },
  ]);
});

async function waitForAdminLoaded() {
  render(<App />);
  await screen.findByTestId("identity-badge");
}

// ---------------------------------------------------------------------------

describe("ChartNav frontend", () => {
  it("resolves /me and shows identity badge", async () => {
    await waitForAdminLoaded();
    expect(screen.getByTestId("identity-badge")).toHaveTextContent(
      "admin@chartnav.local · admin · org 1"
    );
  });

  it("renders the brand footer with a subtle Powered by ARCG Systems line", async () => {
    await waitForAdminLoaded();
    const footer = screen.getByTestId("app-footer");
    expect(footer).toHaveTextContent("ChartNav");
    const powered = screen.getByTestId("app-footer-arcg");
    expect(powered).toHaveTextContent(/powered by\s+arcg systems/i);
  });

  it("renders the list from the mocked API", async () => {
    await waitForAdminLoaded();
    const list = await screen.findByTestId("enc-list");
    expect(within(list).getByText("Morgan Lee")).toBeInTheDocument();
    expect(within(list).getByText("Jordan Rivera")).toBeInTheDocument();
  });

  it("status filter passes through to listEncounters and updates the list", async () => {
    const user = userEvent.setup();
    await waitForAdminLoaded();
    await screen.findByTestId("enc-list");

    await user.selectOptions(screen.getByTestId("filter-status"), "in_progress");

    await waitFor(() => {
      const calls = (api.listEncountersPage as any).mock.calls;
      expect(calls.at(-1)?.[1]).toEqual({ status: "in_progress" });
    });
    const list = await screen.findByTestId("enc-list");
    expect(within(list).getByText("Morgan Lee")).toBeInTheDocument();
    expect(within(list).queryByText("Jordan Rivera")).not.toBeInTheDocument();
  });

  it("selecting an encounter loads detail + events", async () => {
    const user = userEvent.setup();
    await waitForAdminLoaded();
    await user.click(await screen.findByTestId("enc-row-1"));

    await screen.findByTestId("encounter-detail");
    expect(screen.getByTestId("detail-status")).toHaveTextContent("In progress");
    // Timeline shows our mocked event_data
    expect(screen.getByText(/encounter_created/)).toBeInTheDocument();
  });

  it("clinician sees the operational transition, not the review one", async () => {
    const user = userEvent.setup();
    await waitForAdminLoaded();
    await user.selectOptions(
      screen.getByTestId("identity-select"),
      "clin@chartnav.local"
    );
    await waitFor(() =>
      expect(screen.getByTestId("identity-badge")).toHaveTextContent("clinician")
    );

    await user.click(await screen.findByTestId("enc-row-1"));
    await screen.findByTestId("encounter-detail");

    // in_progress → draft_ready is clinician's edge
    expect(screen.getByTestId("transition-draft_ready")).toBeInTheDocument();
    // completed is not reachable from in_progress in one edge anyway
    expect(screen.queryByTestId("transition-completed")).not.toBeInTheDocument();
  });

  it("reviewer sees review-stage transition on PT-1002 and no event composer", async () => {
    const user = userEvent.setup();
    await waitForAdminLoaded();
    await user.selectOptions(
      screen.getByTestId("identity-select"),
      "rev@chartnav.local"
    );
    await waitFor(() =>
      expect(screen.getByTestId("identity-badge")).toHaveTextContent("reviewer")
    );

    await user.click(await screen.findByTestId("enc-row-2"));
    await screen.findByTestId("encounter-detail");

    expect(screen.getByTestId("transition-completed")).toBeInTheDocument();
    expect(screen.getByTestId("transition-draft_ready")).toBeInTheDocument();
    expect(screen.getByTestId("event-denied")).toBeInTheDocument();
    expect(screen.queryByTestId("event-form")).not.toBeInTheDocument();
  });

  it("admin sees the Admin button; clinician/reviewer do not", async () => {
    const user = userEvent.setup();
    await waitForAdminLoaded();
    expect(screen.getByTestId("open-admin-panel")).toBeInTheDocument();

    await user.selectOptions(
      screen.getByTestId("identity-select"),
      "clin@chartnav.local"
    );
    await waitFor(() =>
      expect(screen.getByTestId("identity-badge")).toHaveTextContent("clinician")
    );
    expect(screen.queryByTestId("open-admin-panel")).not.toBeInTheDocument();

    await user.selectOptions(
      screen.getByTestId("identity-select"),
      "rev@chartnav.local"
    );
    await waitFor(() =>
      expect(screen.getByTestId("identity-badge")).toHaveTextContent("reviewer")
    );
    expect(screen.queryByTestId("open-admin-panel")).not.toBeInTheDocument();
  });

  it("reviewer cannot see the create-encounter button", async () => {
    const user = userEvent.setup();
    await waitForAdminLoaded();
    // Admin sees the button
    expect(screen.getByTestId("open-create-encounter")).toBeInTheDocument();
    await user.selectOptions(
      screen.getByTestId("identity-select"),
      "rev@chartnav.local"
    );
    await waitFor(() =>
      expect(screen.getByTestId("identity-badge")).toHaveTextContent("reviewer")
    );
    expect(screen.queryByTestId("open-create-encounter")).not.toBeInTheDocument();
  });

  it("admin can open the create modal and submit a new encounter", async () => {
    const created: api.Encounter = {
      id: 99,
      organization_id: 1,
      location_id: 1,
      patient_identifier: "PT-9999",
      patient_name: "Test Patient",
      provider_name: "Dr. New",
      status: "scheduled",
      scheduled_at: null,
      started_at: null,
      completed_at: null,
      created_at: "2026-04-18 12:00:00",
    };
    (api.createEncounter as any).mockResolvedValueOnce(created);
    // After create, the list should include the new row.
    (api.listEncountersPage as any).mockImplementation(async () => ({
      items: [...ORG1_ENCOUNTERS, created], total: 3, limit: 25, offset: 0,
    }));
    (api.getEncounter as any).mockImplementation(async (_: string, id: number) => {
      if (id === 99) return created;
      const all = [...ORG1_ENCOUNTERS, ...ORG2_ENCOUNTERS];
      const row = all.find((r) => r.id === id);
      if (!row) throw new api.ApiError(404, "encounter_not_found", "x");
      return row;
    });

    const user = userEvent.setup();
    await waitForAdminLoaded();

    await user.click(screen.getByTestId("open-create-encounter"));
    await screen.findByTestId("create-modal");

    await user.type(screen.getByTestId("create-patient-id"), "PT-9999");
    await user.type(screen.getByTestId("create-patient-name"), "Test Patient");
    await user.type(screen.getByTestId("create-provider"), "Dr. New");
    // location is auto-selected because there's one option in the mock
    await user.click(screen.getByTestId("create-submit"));

    await waitFor(() => {
      expect(api.createEncounter).toHaveBeenCalledWith("admin@chartnav.local", expect.objectContaining({
        organization_id: 1,
        location_id: 1,
        patient_identifier: "PT-9999",
        patient_name: "Test Patient",
        provider_name: "Dr. New",
      }));
    });
    // Success banner appears
    expect(await screen.findByTestId("banner-ok")).toHaveTextContent("#99");
    // Modal closed
    expect(screen.queryByTestId("create-modal")).not.toBeInTheDocument();
  });

  it("create-encounter failure surfaces the backend error_code + reason", async () => {
    (api.createEncounter as any).mockRejectedValueOnce(
      new api.ApiError(403, "cross_org_access_forbidden", "location does not belong to caller's organization")
    );

    const user = userEvent.setup();
    await waitForAdminLoaded();
    await user.click(screen.getByTestId("open-create-encounter"));
    await screen.findByTestId("create-modal");

    await user.type(screen.getByTestId("create-patient-id"), "PT-9");
    await user.type(screen.getByTestId("create-provider"), "Dr. X");
    await user.click(screen.getByTestId("create-submit"));

    const errorBox = await screen.findByTestId("create-error");
    expect(errorBox).toHaveTextContent("403");
    expect(errorBox).toHaveTextContent("cross_org_access_forbidden");
    // modal stays open on failure so the user can retry
    expect(screen.getByTestId("create-modal")).toBeInTheDocument();
  });

  it("switching identity refetches /me and the list", async () => {
    const user = userEvent.setup();
    await waitForAdminLoaded();
    // Sanity: org1 list
    await screen.findByText("Morgan Lee");

    await user.selectOptions(
      screen.getByTestId("identity-select"),
      "admin@northside.local"
    );

    await waitFor(() => {
      expect(screen.getByTestId("identity-badge")).toHaveTextContent("org 2");
    });
    // org2 encounters surface
    expect(await screen.findByText("Priya Shah")).toBeInTheDocument();
    expect(screen.queryByText("Morgan Lee")).not.toBeInTheDocument();
  });

  it("unknown-user identity surfaces the auth error chip", async () => {
    const user = userEvent.setup();
    await waitForAdminLoaded();

    // Switch into custom-email mode and enter a ghost email.
    await user.selectOptions(screen.getByTestId("identity-select"), "__custom__");
    const emailInput = screen.getByPlaceholderText("user@example.com");
    await user.type(emailInput, "ghost@nowhere.test");
    await user.click(screen.getByRole("button", { name: /use/i }));

    await waitFor(() => {
      expect(screen.getByTestId("identity-error")).toHaveTextContent("unknown_user");
    });
  });

  it("native encounter detail renders a ChartNav source chip and no external banner", async () => {
    const user = userEvent.setup();
    await waitForAdminLoaded();
    await user.click(await screen.findByTestId("enc-row-1"));
    const chip = await screen.findByTestId("detail-source-chip");
    expect(chip).toHaveAttribute("data-source", "chartnav");
    expect(chip).toHaveTextContent(/ChartNav \(native\)/i);
    expect(
      screen.queryByTestId("external-encounter-banner")
    ).not.toBeInTheDocument();
    // Native → transitions visible.
    expect(screen.getByTestId("transitions")).toBeInTheDocument();
  });

  it("externally sourced encounter hides transitions and shows the SoT banner", async () => {
    // Swap the selected encounter to an integrated row.
    const external: api.Encounter = {
      ...ORG1_ENCOUNTERS[0],
      _source: "fhir",
      _external_ref: "ENC-A",
    };
    (api.getEncounter as any).mockResolvedValueOnce(external);
    const user = userEvent.setup();
    await waitForAdminLoaded();
    await user.click(await screen.findByTestId("enc-row-1"));
    await screen.findByTestId("encounter-detail");
    const chip = await screen.findByTestId("detail-source-chip");
    expect(chip).toHaveAttribute("data-source", "fhir");
    expect(chip).toHaveTextContent(/External \(FHIR\)/i);
    expect(
      await screen.findByTestId("external-encounter-banner")
    ).toHaveTextContent(/external EHR/i);
    // External → transitions list + NoteWorkspace both suppressed.
    expect(screen.queryByTestId("transitions")).not.toBeInTheDocument();
    expect(
      screen.queryByTestId("note-workspace")
    ).not.toBeInTheDocument();
    // Phase 21 copy: external-note now mentions bridging.
    expect(
      screen.getByTestId("note-workspace-external-note")
    ).toHaveTextContent(/bridg/i);
    // Bridge button visible for admin + clinician.
    expect(screen.getByTestId("bridge-encounter")).toBeEnabled();
  });

  it("bridge button calls bridgeEncounter with the external ref", async () => {
    const external: api.Encounter = {
      ...ORG1_ENCOUNTERS[0],
      _source: "fhir",
      _external_ref: "ENC-XYZ",
    };
    (api.getEncounter as any).mockResolvedValueOnce(external);
    (api.bridgeEncounter as any).mockResolvedValueOnce({
      ...ORG1_ENCOUNTERS[0],
      id: 999,
      external_ref: "ENC-XYZ",
      external_source: "fhir",
      _bridged: true,
      _source: "chartnav",
      _external_ref: "ENC-XYZ",
      _external_source: "fhir",
    });
    // jsdom's window.location can't have its methods redefined; replace
    // the whole object with a stub for this test.
    const originalLocation = window.location;
    Object.defineProperty(window, "location", {
      configurable: true,
      value: { ...originalLocation, assign: vi.fn(), href: "http://localhost/" },
    });
    try {
      const user = userEvent.setup();
      await waitForAdminLoaded();
      await user.click(await screen.findByTestId("enc-row-1"));
      await screen.findByTestId("encounter-detail");
      await user.click(await screen.findByTestId("bridge-encounter"));
      await waitFor(() =>
        expect(api.bridgeEncounter).toHaveBeenCalledWith(
          ADMIN1.email,
          expect.objectContaining({
            external_ref: "ENC-XYZ",
            external_source: "fhir",
            patient_identifier: expect.any(String),
          })
        )
      );
    } finally {
      Object.defineProperty(window, "location", {
        configurable: true,
        value: originalLocation,
      });
    }
  });

  it("bridged-native encounter shows a refresh banner and dispatches refreshBridgedEncounter", async () => {
    // A native row that carries external_ref = it was bridged.
    const bridged: api.Encounter = {
      ...ORG1_ENCOUNTERS[0],
      _source: "chartnav",
      external_ref: "ENC-BR-1",
      external_source: "stub",
    } as any;
    // Use mockResolvedValue (not Once) so post-refresh re-fetches stay bridged.
    (api.getEncounter as any).mockResolvedValue(bridged);
    (api.refreshBridgedEncounter as any).mockResolvedValue({
      id: 1,
      refreshed: true,
      mirrored: { provider_name: "Stub Provider" },
      skipped_unchanged: [],
    });
    const user = userEvent.setup();
    await waitForAdminLoaded();
    await user.click(await screen.findByTestId("enc-row-1"));
    await screen.findByTestId("encounter-detail");

    const banner = await screen.findByTestId("bridged-refresh-banner");
    expect(banner).toHaveTextContent(/bridged from external/i);
    expect(screen.getByTestId("bridged-external-ref")).toHaveTextContent(
      "ENC-BR-1"
    );
    await user.click(screen.getByTestId("bridged-refresh"));
    await waitFor(() =>
      expect(api.refreshBridgedEncounter).toHaveBeenCalledWith(
        ADMIN1.email, 1
      )
    );
    expect(
      await screen.findByTestId("bridged-refresh-ok")
    ).toHaveTextContent(/provider_name/);
  });

  it("reviewer sees the refresh banner disabled note and no refresh button", async () => {
    const bridged: api.Encounter = {
      ...ORG1_ENCOUNTERS[0],
      _source: "chartnav",
      external_ref: "ENC-BR-R",
      external_source: "stub",
    } as any;
    (api.getEncounter as any).mockResolvedValue(bridged);
    // Wait for initial admin load.
    const user = userEvent.setup();
    await waitForAdminLoaded();
    // Switch to reviewer identity via the existing seeded picker.
    await user.selectOptions(
      screen.getByLabelText(/identity/i),
      "rev@chartnav.local"
    );
    await waitFor(() =>
      expect(screen.getByTestId("identity-badge")).toHaveTextContent(
        /rev@chartnav.local/i
      )
    );
    await user.click(await screen.findByTestId("enc-row-1"));
    await screen.findByTestId("encounter-detail");
    await screen.findByTestId("bridged-refresh-banner");
    expect(screen.queryByTestId("bridged-refresh")).not.toBeInTheDocument();
    expect(
      screen.getByTestId("bridged-refresh-disabled-note")
    ).toHaveTextContent(/cannot refresh/i);
  });

  it("performs a status transition and refreshes detail + events", async () => {
    const updated: api.Encounter = { ...ORG1_ENCOUNTERS[0], status: "draft_ready" };
    (api.updateEncounterStatus as any).mockResolvedValueOnce(updated);
    (api.getEncounterEvents as any).mockResolvedValueOnce([
      { id: 100, encounter_id: 1, event_type: "status_changed", event_data: { old_status: "in_progress", new_status: "draft_ready" }, created_at: "x" },
    ]);

    const user = userEvent.setup();
    await waitForAdminLoaded();
    await user.click(await screen.findByTestId("enc-row-1"));
    await screen.findByTestId("encounter-detail");
    await user.click(screen.getByTestId("transition-draft_ready"));

    await waitFor(() => {
      expect(api.updateEncounterStatus).toHaveBeenCalledWith(
        "admin@chartnav.local", 1, "draft_ready"
      );
    });
    expect(await screen.findByTestId("banner-ok")).toHaveTextContent("draft_ready");
  });
});
