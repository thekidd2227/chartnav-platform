// ProductionReadinessPanel.test.tsx
//
// Verifies the production-readiness panel:
//   - admins see proof KPIs + rollout readiness + specialty template
//     coverage
//   - non-admins see a blocked notice and no panel data
//   - pending KPIs render with a `pending` status (no fabricated
//     numbers)
//   - rollout rows surface the right role-coverage counts and a
//     "ready" flag only when every required role is present AND the
//     fake-data demo wedge is detected.

import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import * as api from "../api";
import { ProductionReadinessPanel } from "../ProductionReadinessPanel";

vi.mock("../api", async () => {
  const actual = await vi.importActual<typeof import("../api")>("../api");
  return {
    ...actual,
    getAdminDashboard: vi.fn(),
    listLocations: vi.fn(),
    listUsers: vi.fn(),
  };
});

const ADMIN_ME: api.Me = {
  email: "admin@chartnav.local",
  full_name: "ChartNav Admin",
  role: "admin",
  organization_id: 1,
  organization_slug: "demo-eye-clinic",
} as unknown as api.Me;

const CLIN_ME: api.Me = {
  email: "clin@chartnav.local",
  full_name: "Casey Clinician",
  role: "clinician",
  organization_id: 1,
  organization_slug: "demo-eye-clinic",
} as unknown as api.Me;

const ADMIN_DASHBOARD: api.AdminDashboard = {
  role: "admin",
  scope: { organization_id: 1 } as api.DashboardScope,
  counts: {
    total_open_queue_items: 12,
    overdue_queue_items: 2,
    unsigned_notes_count: 3,
  },
  work_queue_by_status: { open: 12 },
  work_queue_by_queue_type: { check_in: 3 },
  work_queue_by_priority: { normal: 10, high: 2 },
  work_queue_by_role: { front_desk: 4 },
  location_summary: { active_count: 1 },
  provider_summary: { total_count: 2 },
  role_view_presets_summary: {},
} as api.AdminDashboard;

const LOCATIONS: api.Location[] = [
  { id: 1, organization_id: 1, name: "Main Clinic", is_active: true, created_at: "2026-05-14" } as api.Location,
];

const USERS_FULL_COVERAGE: api.User[] = [
  { id: 1, organization_id: 1, email: "admin@chartnav.local", full_name: "Admin", role: "admin", is_active: 1, invited_at: null, created_at: "" },
  { id: 2, organization_id: 1, email: "clin@chartnav.local", full_name: "Clin", role: "clinician", is_active: 1, invited_at: null, created_at: "" },
  { id: 3, organization_id: 1, email: "rev@chartnav.local", full_name: "Rev", role: "reviewer", is_active: 1, invited_at: null, created_at: "" },
  { id: 4, organization_id: 1, email: "front@chartnav.local", full_name: "Front", role: "front_desk", is_active: 1, invited_at: null, created_at: "" },
  { id: 5, organization_id: 1, email: "tech@chartnav.local", full_name: "Tech", role: "technician", is_active: 1, invited_at: null, created_at: "" },
];

const USERS_MISSING_REVIEWER: api.User[] = USERS_FULL_COVERAGE.filter(
  (u) => u.role !== "reviewer",
);

beforeEach(() => {
  vi.clearAllMocks();
  (api.getAdminDashboard as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(ADMIN_DASHBOARD);
  (api.listLocations as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(LOCATIONS);
  (api.listUsers as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(USERS_FULL_COVERAGE);
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("ProductionReadinessPanel — non-admin", () => {
  it("renders the blocked notice for clinician users", () => {
    render(
      <ProductionReadinessPanel identity={CLIN_ME.email} me={CLIN_ME} />,
    );
    expect(
      screen.getByTestId("production-readiness-blocked"),
    ).toBeInTheDocument();
    // No KPI grid for non-admins.
    expect(
      screen.queryByTestId("production-readiness-kpi-grid"),
    ).toBeNull();
    // The mock API methods are not called for non-admins.
    expect(api.getAdminDashboard).not.toHaveBeenCalled();
  });
});

describe("ProductionReadinessPanel — admin (live + pending KPIs)", () => {
  it("renders the KPI grid with live counts + explicit pending markers", async () => {
    render(
      <ProductionReadinessPanel identity={ADMIN_ME.email} me={ADMIN_ME} />,
    );
    await waitFor(() => {
      expect(
        screen.getByTestId("production-readiness-kpi-grid"),
      ).toBeInTheDocument();
    });
    expect(
      screen.getByTestId("production-readiness-kpi-open-queue"),
    ).toHaveTextContent("12");
    expect(
      screen.getByTestId("production-readiness-kpi-overdue"),
    ).toHaveTextContent("2");
    expect(
      screen.getByTestId("production-readiness-kpi-unsigned-notes"),
    ).toHaveTextContent("3");
    expect(
      screen.getByTestId("production-readiness-kpi-non-overdue-share"),
    ).toHaveTextContent("83%");
    // Pending KPIs render with the "pending" / "future" text and a
    // pending status attribute — never a fabricated number.
    expect(
      screen.getByTestId("production-readiness-kpi-edit-burden"),
    ).toHaveAttribute("data-status", "pending");
    expect(
      screen.getByTestId("production-readiness-kpi-denied-claim-correlation"),
    ).toHaveAttribute("data-status", "pending");
  });

  it("renders the rollout table with a `ready` row when full role coverage + fake-data demo wedge present", async () => {
    render(
      <ProductionReadinessPanel identity={ADMIN_ME.email} me={ADMIN_ME} />,
    );
    await waitFor(() => {
      expect(
        screen.getByTestId("production-readiness-rollout-table"),
      ).toBeInTheDocument();
    });
    // The unassigned bucket holds every seeded user (User has no
    // location_id field), so the "Main Clinic" row shows zero
    // coverage and the unassigned row holds the full coverage.
    const unassigned = screen.getByTestId(
      "production-readiness-rollout-row-_unassigned",
    );
    expect(within(unassigned).getByText("ready")).toBeInTheDocument();
  });

  it("renders `gaps` for a location missing a required role", async () => {
    (api.listUsers as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      USERS_MISSING_REVIEWER,
    );
    render(
      <ProductionReadinessPanel identity={ADMIN_ME.email} me={ADMIN_ME} />,
    );
    await waitFor(() => {
      expect(
        screen.getByTestId("production-readiness-rollout-table"),
      ).toBeInTheDocument();
    });
    const unassigned = screen.getByTestId(
      "production-readiness-rollout-row-_unassigned",
    );
    expect(within(unassigned).getByText("gaps")).toBeInTheDocument();
  });

  it("renders the specialty template coverage cards (one per specialty)", async () => {
    render(
      <ProductionReadinessPanel identity={ADMIN_ME.email} me={ADMIN_ME} />,
    );
    await waitFor(() => {
      expect(
        screen.getByTestId("production-readiness-specialty-grid"),
      ).toBeInTheDocument();
    });
    for (const sp of ["retina", "glaucoma", "cornea", "cataract", "oculoplastics"]) {
      expect(
        screen.getByTestId(`production-readiness-specialty-${sp}`),
      ).toBeInTheDocument();
    }
  });

  it("surfaces an error banner if a backend call fails", async () => {
    (api.getAdminDashboard as unknown as ReturnType<typeof vi.fn>).mockRejectedValueOnce(
      new api.ApiError(500, "internal_error", "internal"),
    );
    render(
      <ProductionReadinessPanel identity={ADMIN_ME.email} me={ADMIN_ME} />,
    );
    await waitFor(() => {
      expect(
        screen.getByTestId("production-readiness-error"),
      ).toBeInTheDocument();
    });
  });
});
