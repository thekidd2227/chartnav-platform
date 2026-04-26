// Phase 2 item 2 — vitest coverage for AdminDashboard.
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { AdminDashboard } from "../AdminDashboard";
import * as api from "../api";

const me = {
  user_id: 1,
  email: "admin@chartnav.local",
  full_name: "Admin",
  role: "admin",
  organization_id: 1,
  is_authorized_final_signer: false,
} as any;

describe("AdminDashboard", () => {
  beforeEach(() => {
    vi.spyOn(api, "getAdminDashboardSummary").mockResolvedValue({
      encounters_signed_today: 3,
      encounters_signed_7d: 12,
      median_sign_to_export_minutes_7d: 8.5,
      missing_flags_open: 4,
      missing_flag_resolution_rate_14d: 0.75,
      reminders_overdue: 2,
    });
    vi.spyOn(api, "getAdminDashboardTrend").mockResolvedValue({
      series: Array.from({ length: 14 }, (_, i) => ({
        date: `2026-04-${String(i + 13).padStart(2, "0")}`,
        encounters_signed: i,
        missing_flag_resolution_rate: i * 0.05,
      })),
    });
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders six KPI cards with the documented testids", async () => {
    render(<AdminDashboard identity="admin@chartnav.local" me={me} />);
    await waitFor(() => screen.getByTestId("admin-dashboard-root"));
    for (const slug of [
      "signed-today",
      "signed-7d",
      "median-lag",
      "missing-flags-open",
      "missing-flag-resolution-rate",
      "reminders-overdue",
    ]) {
      expect(screen.getByTestId(`kpi-card-${slug}`)).toBeInTheDocument();
    }
  });

  it("renders the trend sparklines block", async () => {
    render(<AdminDashboard identity="admin@chartnav.local" me={me} />);
    await waitFor(() => screen.getByTestId("trend-sparklines"));
    expect(screen.getByTestId("sparkline-signed")).toBeInTheDocument();
    expect(screen.getByTestId("sparkline-resolution-rate")).toBeInTheDocument();
  });

  it("shows a forbidden empty state when API returns 403", async () => {
    (api.getAdminDashboardSummary as any).mockRejectedValueOnce(
      new api.ApiError(
        403,
        "role_cannot_view_admin_dashboard",
        "no"
      )
    );
    render(
      <AdminDashboard
        identity="rev@chartnav.local"
        me={{ ...me, role: "reviewer" } as any}
      />
    );
    await waitFor(() => screen.getByTestId("admin-dashboard-forbidden"));
    expect(screen.getByTestId("admin-dashboard-forbidden")).toHaveTextContent(
      /not available for your role/i
    );
  });
});
