// Phase 47 — KPI scorecard pane tests.
//
// Covers the contract a pilot review depends on:
//   - window selector swaps the hours query
//   - compare toggle fetches /admin/kpi/compare and surfaces delta chips
//   - KPI cards render values from the overview payload
//   - provider table renders one row per provider, sorted by volume
//   - export button triggers the CSV download helper
//   - empty and error states render honestly

import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../api", async () => {
  const actual = await vi.importActual<typeof import("../api")>("../api");
  return {
    ...actual,
    API_URL: "http://test",
    getKpiOverview: vi.fn(),
    getKpiProviders: vi.fn(),
    getKpiCompare: vi.fn(),
    downloadKpiCsv: vi.fn(),
  };
});

import * as api from "../api";
import { KpiPane } from "../KpiPane";

const ADMIN: api.Me = {
  user_id: 1,
  email: "admin@chartnav.local",
  full_name: "Admin",
  role: "admin",
  organization_id: 1,
};

const ORG: api.Organization = {
  id: 1,
  name: "Demo Eye Clinic",
  slug: "demo-eye-clinic",
  settings: null,
  created_at: "2026-04-01",
};

const OVERVIEW: api.KpiOverview = {
  organization_id: 1,
  window: {
    since: "2026-04-14T00:00:00+00:00",
    until: "2026-04-21T00:00:00+00:00",
    hours: 168,
  },
  counts: { encounters: 24, signed_notes: 18, exported_notes: 14, open_drafts: 4 },
  latency_minutes: {
    transcript_to_draft: { n: 12, median: 8.5, mean: 9.1, p90: 16.0, min: 3.2, max: 20.0 },
    draft_to_sign:       { n: 10, median: 22.0, mean: 26.3, p90: 45.0, min: 6.0, max: 60.0 },
    total_time_to_sign:  { n: 10, median: 32.0, mean: 40.5, p90: 68.0, min: 12.0, max: 90.0 },
  },
  quality: {
    missing_data_rate: 8.3,
    export_ready_rate: 77.8,
    notes_observed: 24,
    notes_with_missing_flags: 2,
    avg_revisions_per_signed_note: 0.6,
  },
};

const PROVIDERS: api.KpiProviders = {
  organization_id: 1,
  window: OVERVIEW.window,
  providers: [
    {
      provider: "Dr. Carter",
      encounters: 18,
      signed_notes: 14,
      notes_observed: 18,
      missing_flag_count: 1,
      missing_data_rate_pct: 5.56,
      transcript_to_draft_min: { n: 10, median: 7.5, mean: 8.0, p90: 12.0, min: 3.2, max: 18.0 },
      draft_to_sign_min:       { n: 10, median: 18.0, mean: 20.0, p90: 30.0, min: 6.0, max: 40.0 },
      total_time_to_sign_min:  { n: 10, median: 28.0, mean: 30.0, p90: 55.0, min: 12.0, max: 70.0 },
      avg_revisions_per_signed_note: 0.5,
    },
    {
      provider: "Dr. Patel",
      encounters: 6,
      signed_notes: 4,
      notes_observed: 6,
      missing_flag_count: 1,
      missing_data_rate_pct: 16.67,
      transcript_to_draft_min: { n: 2, median: 10.0, mean: 10.0, p90: 12.0, min: 8.0, max: 12.0 },
      draft_to_sign_min:       { n: 0, median: null, mean: null, p90: null, min: null, max: null },
      total_time_to_sign_min:  { n: 0, median: null, mean: null, p90: null, min: null, max: null },
      avg_revisions_per_signed_note: null,
    },
  ],
};

const COMPARE: api.KpiCompare = {
  organization_id: 1,
  window_hours: 168,
  current: OVERVIEW,
  previous: {
    ...OVERVIEW,
    window: {
      since: "2026-04-07T00:00:00+00:00",
      until: "2026-04-14T00:00:00+00:00",
      hours: 168,
    },
    counts: { encounters: 20, signed_notes: 12, exported_notes: 8, open_drafts: 6 },
    latency_minutes: {
      transcript_to_draft: { n: 10, median: 12.0, mean: 13.0, p90: 22.0, min: 4.0, max: 30.0 },
      draft_to_sign:       { n: 8,  median: 30.0, mean: 33.0, p90: 55.0, min: 9.0, max: 70.0 },
      total_time_to_sign:  { n: 8,  median: 44.0, mean: 48.0, p90: 80.0, min: 18.0, max: 100.0 },
    },
    quality: {
      missing_data_rate: 15.0,
      export_ready_rate: 66.6,
      notes_observed: 20,
      notes_with_missing_flags: 3,
      avg_revisions_per_signed_note: 0.9,
    },
  },
  deltas: {
    latency_minutes_median_pct_change: {
      transcript_to_draft: -29.17,
      draft_to_sign: -26.67,
      total_time_to_sign: -27.27,
    },
    quality_pct_change: {
      missing_data_rate: -44.67,
      export_ready_rate: 16.82,
    },
    counts_delta: {
      encounters: 4,
      signed_notes: 6,
      exported_notes: 6,
    },
  },
};

beforeEach(() => {
  (api.getKpiOverview as any).mockResolvedValue(OVERVIEW);
  (api.getKpiProviders as any).mockResolvedValue(PROVIDERS);
  (api.getKpiCompare as any).mockResolvedValue(COMPARE);
  (api.downloadKpiCsv as any).mockResolvedValue({
    filename: "chartnav-kpi-org1-168h.csv",
    blob: new Blob(["provider\nDr. Carter"], { type: "text/csv" }),
  });
});

describe("KpiPane", () => {
  it("renders top-level KPI cards from overview payload", async () => {
    render(<KpiPane identity={ADMIN.email} me={ADMIN} org={ORG} />);
    await screen.findByTestId("kpi-pane");

    await waitFor(() => {
      expect(screen.getByTestId("kpi-card-encounters")).toHaveTextContent("24");
      expect(screen.getByTestId("kpi-card-t2d")).toHaveTextContent(/9 min|8 min|8.5/);
      // Draft → Sign median is 22 min → "22 min"
      expect(screen.getByTestId("kpi-card-d2s")).toHaveTextContent("22 min");
      // Total time-to-sign 32 min
      expect(screen.getByTestId("kpi-card-total")).toHaveTextContent("32 min");
      expect(screen.getByTestId("kpi-card-missing")).toHaveTextContent("8.3%");
      expect(screen.getByTestId("kpi-card-export-ready")).toHaveTextContent("77.8%");
    });
  });

  it("renders the pilot summary strip with org name + window", async () => {
    render(<KpiPane identity={ADMIN.email} me={ADMIN} org={ORG} />);
    const strip = await screen.findByTestId("kpi-pilot-summary");
    expect(within(strip).getByText(/Demo Eye Clinic/i)).toBeInTheDocument();
    expect(within(strip).getByText(/Encounters/i)).toBeInTheDocument();
  });

  it("switching the window re-fetches with the new hours", async () => {
    const user = userEvent.setup();
    render(<KpiPane identity={ADMIN.email} me={ADMIN} org={ORG} />);
    await screen.findByTestId("kpi-pane");
    await waitFor(() =>
      expect(api.getKpiOverview).toHaveBeenCalledWith(ADMIN.email, 24 * 7)
    );
    await user.click(screen.getByTestId("kpi-window-24"));
    await waitFor(() =>
      expect(api.getKpiOverview).toHaveBeenCalledWith(ADMIN.email, 24)
    );
  });

  it("compare toggle fetches /admin/kpi/compare and shows delta chips", async () => {
    const user = userEvent.setup();
    render(<KpiPane identity={ADMIN.email} me={ADMIN} org={ORG} />);
    await screen.findByTestId("kpi-pane");
    await user.click(screen.getByTestId("kpi-compare-toggle"));
    await waitFor(() => expect(api.getKpiCompare).toHaveBeenCalled());
    // Negative delta on total-time card → improvement → tone = ok
    await waitFor(() => {
      const card = screen.getByTestId("kpi-card-total");
      const delta = card.querySelector(".kpi-card__delta");
      expect(delta).not.toBeNull();
      expect(delta).toHaveAttribute("data-tone", "ok");
    });
  });

  it("renders the provider table sorted by encounter volume desc", async () => {
    render(<KpiPane identity={ADMIN.email} me={ADMIN} org={ORG} />);
    const table = await screen.findByTestId("kpi-providers-table");
    const rows = table.querySelectorAll("tbody tr");
    expect(rows.length).toBe(2);
    // Dr. Carter (18 encounters) before Dr. Patel (6 encounters)
    expect(rows[0]).toHaveTextContent(/Dr\. Carter/);
    expect(rows[1]).toHaveTextContent(/Dr\. Patel/);
  });

  it("export button calls downloadKpiCsv and reports success", async () => {
    const user = userEvent.setup();
    // jsdom does not implement URL.createObjectURL / revokeObjectURL —
    // stub both so the synthetic-download path does not throw.
    (URL as any).createObjectURL = vi.fn(() => "blob:test");
    (URL as any).revokeObjectURL = vi.fn();
    // Prevent the synthetic anchor's click from triggering jsdom
    // navigation (which would detach the React tree).
    const origCreate = document.createElement.bind(document);
    const createSpy = vi.spyOn(document, "createElement").mockImplementation(
      (tag: string) => {
        const el = origCreate(tag);
        if (String(tag).toLowerCase() === "a") {
          (el as any).click = vi.fn();
        }
        return el as any;
      }
    );
    render(<KpiPane identity={ADMIN.email} me={ADMIN} org={ORG} />);
    await screen.findByTestId("kpi-pane");
    await user.click(screen.getByTestId("kpi-export"));
    await waitFor(() =>
      expect(api.downloadKpiCsv).toHaveBeenCalledWith(ADMIN.email, 24 * 7)
    );
    await waitFor(() =>
      expect(screen.getByTestId("kpi-export-ok")).toHaveTextContent(/Exported/)
    );
    createSpy.mockRestore();
  });

  it("renders an honest error banner when the overview fetch fails", async () => {
    (api.getKpiOverview as any).mockRejectedValueOnce(
      new api.ApiError(500, "internal_error", "db down")
    );
    render(<KpiPane identity={ADMIN.email} me={ADMIN} org={ORG} />);
    await waitFor(() =>
      expect(screen.getByTestId("kpi-error")).toHaveTextContent(/internal_error/)
    );
  });

  it("renders an empty provider state when no providers have activity", async () => {
    (api.getKpiProviders as any).mockResolvedValueOnce({
      organization_id: 1,
      window: OVERVIEW.window,
      providers: [],
    });
    render(<KpiPane identity={ADMIN.email} me={ADMIN} org={ORG} />);
    await waitFor(() =>
      expect(screen.getByTestId("kpi-providers-empty")).toBeInTheDocument()
    );
  });
});
