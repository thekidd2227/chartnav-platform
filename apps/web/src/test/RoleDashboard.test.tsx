// Phase 20C — RoleDashboard tests.
//
// Covers:
//   - Role dispatch: each role renders its own card set + queue.
//   - Admin "view as" selector flips between role views.
//   - Empty queue lists render the placeholder, not undefined.
//   - PHI safety: no patient names, DOB strings, or note bodies leak
//     into the rendered DOM (defense-in-depth — backend already
//     compacts the payload).
//   - Forbidden language scan: dashboard never claims billing,
//     coding, claims, or insurance language.
//   - Header section labels match the ophthalmology lane vocabulary.

import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../api", async () => {
  const actual = await vi.importActual<typeof import("../api")>("../api");
  return {
    ...actual,
    API_URL: "http://test",
    getMyDashboard: vi.fn(),
    getFrontDeskDashboard: vi.fn(),
    getTechnicianDashboard: vi.fn(),
    getDoctorDashboard: vi.fn(),
    getReviewerDashboard: vi.fn(),
    getAdminDashboard: vi.fn(),
  };
});

import * as api from "../api";
import { RoleDashboard } from "../RoleDashboard";

const FRONT_DESK_ME: api.Me = {
  user_id: 10,
  email: "front@chartnav.local",
  full_name: "Frankie Front-Desk",
  role: "front_desk",
  organization_id: 1,
};

const TECH_ME: api.Me = {
  user_id: 11,
  email: "tech@chartnav.local",
  full_name: "Taylor Technician",
  role: "technician",
  organization_id: 1,
};

const DOCTOR_ME: api.Me = {
  user_id: 12,
  email: "clin@chartnav.local",
  full_name: "Casey Clinician",
  role: "clinician",
  organization_id: 1,
};

const REVIEWER_ME: api.Me = {
  user_id: 13,
  email: "rev@chartnav.local",
  full_name: "Riley Reviewer",
  role: "reviewer",
  organization_id: 1,
};

const ADMIN_ME: api.Me = {
  user_id: 14,
  email: "admin@chartnav.local",
  full_name: "ChartNav Admin",
  role: "admin",
  organization_id: 1,
};

const FRONT_DESK_PAYLOAD: api.FrontDeskDashboard = {
  role: "front_desk",
  scope: { organization_id: 1, location_id: null, provider_id: null },
  counts: {
    today_queue_count: 12,
    check_in_pending_count: 4,
    ready_for_workup_count: 3,
    checkout_pending_count: 2,
    follow_up_needed_count: 1,
  },
  recent_or_due_items: [
    {
      id: 100,
      queue_type: "front_desk_check_in",
      priority: "normal",
      status: "open",
      assigned_role: "front_desk",
      assigned_user_id: null,
      patient_id: 1,
      encounter_id: 200,
      provider_id: null,
      location_id: 1,
      due_at: null,
      created_at: "2026-05-09 09:00:00",
      updated_at: "2026-05-09 09:00:00",
    },
  ],
};

const TECH_PAYLOAD: api.TechnicianDashboard = {
  role: "technician",
  scope: { organization_id: 1, location_id: null, provider_id: null },
  counts: {
    workup_pending_count: 5,
    imaging_needed_count: 2,
    dilation_pending_count: 1,
    testing_pending_count: 3,
    ready_for_doctor_count: 4,
  },
  assigned_items: [],
};

const DOCTOR_PAYLOAD: api.DoctorDashboard = {
  role: "clinician",
  scope: { organization_id: 1, location_id: null, provider_id: null },
  counts: {
    ready_for_doctor_count: 4,
    documentation_in_progress_count: 2,
    notes_ready_for_signoff_count: 3,
    high_priority_items_count: 1,
    imaging_ready_for_review_count: 2,
  },
  assigned_provider_items: [
    {
      id: 300,
      queue_type: "doctor_encounter",
      priority: "high",
      status: "in_progress",
      assigned_role: "clinician",
      assigned_user_id: 12,
      patient_id: 1,
      encounter_id: 200,
      provider_id: 7,
      location_id: 1,
      due_at: null,
      created_at: "2026-05-09 10:00:00",
      updated_at: "2026-05-09 10:30:00",
    },
  ],
};

const REVIEWER_PAYLOAD: api.ReviewerDashboard = {
  role: "reviewer",
  scope: { organization_id: 1, location_id: null, provider_id: null },
  counts: {
    notes_awaiting_review_count: 6,
    diagram_proposals_review_count: 1,
    ai_draft_review_count: 3,
    audit_exceptions_count: 0,
    blocked_items_count: 2,
  },
  review_needed_items: [],
};

const ADMIN_PAYLOAD: api.AdminDashboard = {
  role: "admin",
  scope: { organization_id: 1, location_id: null, provider_id: null },
  counts: {
    total_open_queue_items: 25,
    overdue_queue_items: 3,
    unsigned_notes_count: 4,
  },
  work_queue_by_status: { open: 18, in_progress: 7 },
  work_queue_by_priority: { normal: 15, high: 7, urgent: 3 },
  work_queue_by_role: { front_desk: 5, technician: 9, clinician: 8, reviewer: 3 },
  work_queue_by_queue_type: {
    front_desk_check_in: 4,
    technician_workup: 9,
    doctor_encounter: 8,
  },
  location_summary: { active_count: 1 },
  provider_summary: { total_count: 2 },
  role_view_presets_summary: { front_desk: 1, technician: 1 },
};

beforeEach(() => {
  vi.clearAllMocks();
});

function setMyDashboard(payload: api.DashboardSummary) {
  (api.getMyDashboard as any).mockResolvedValue(payload);
}

describe("RoleDashboard — role dispatch", () => {
  it("front desk: renders front-desk lane labels", async () => {
    setMyDashboard(FRONT_DESK_PAYLOAD);
    render(<RoleDashboard identity="front@chartnav.local" me={FRONT_DESK_ME} />);
    await waitFor(() =>
      expect(screen.getByTestId("dashboard-front-desk")).toBeInTheDocument()
    );
    expect(screen.getByTestId("card-today-schedule")).toHaveTextContent("12");
    expect(screen.getByTestId("card-check-in-pending")).toHaveTextContent("4");
    expect(screen.getByTestId("card-ready-for-technician")).toHaveTextContent("3");
    expect(screen.getByTestId("card-checkout")).toHaveTextContent("2");
    expect(screen.getByTestId("card-follow-up")).toHaveTextContent("1");
    // Internal-notes blurb is the policy reminder, not an actual note body.
    expect(screen.getByTestId("front-desk-internal-note")).toHaveTextContent(
      /not shown on the dashboard/i
    );
  });

  it("technician: renders technician lane labels and empty queue text", async () => {
    setMyDashboard(TECH_PAYLOAD);
    render(<RoleDashboard identity="tech@chartnav.local" me={TECH_ME} />);
    await waitFor(() =>
      expect(screen.getByTestId("dashboard-technician")).toBeInTheDocument()
    );
    expect(screen.getByTestId("card-workup-queue")).toHaveTextContent("5");
    expect(screen.getByTestId("card-imaging-needed")).toHaveTextContent("2");
    expect(screen.getByTestId("card-dilation")).toHaveTextContent("1");
    expect(screen.getByTestId("card-testing")).toHaveTextContent("3");
    expect(screen.getByTestId("card-ready-for-doctor")).toHaveTextContent("4");
    expect(screen.getByTestId("technician-queue-empty")).toBeInTheDocument();
  });

  it("doctor: renders MD lane labels + assigned items", async () => {
    setMyDashboard(DOCTOR_PAYLOAD);
    render(<RoleDashboard identity="clin@chartnav.local" me={DOCTOR_ME} />);
    await waitFor(() =>
      expect(screen.getByTestId("dashboard-doctor")).toBeInTheDocument()
    );
    expect(screen.getByTestId("card-ready-for-md")).toHaveTextContent("4");
    expect(screen.getByTestId("card-sign-off")).toHaveTextContent("3");
    expect(screen.getByTestId("card-high-priority")).toHaveTextContent("1");
    const queue = screen.getByTestId("doctor-queue");
    expect(within(queue).getByText(/doctor encounter/i)).toBeInTheDocument();
    expect(within(queue).getByText(/encounter #200/)).toBeInTheDocument();
  });

  it("reviewer: renders review lane labels", async () => {
    setMyDashboard(REVIEWER_PAYLOAD);
    render(<RoleDashboard identity="rev@chartnav.local" me={REVIEWER_ME} />);
    await waitFor(() =>
      expect(screen.getByTestId("dashboard-reviewer")).toBeInTheDocument()
    );
    expect(screen.getByTestId("card-notes-awaiting")).toHaveTextContent("6");
    expect(screen.getByTestId("card-ai-draft")).toHaveTextContent("3");
    expect(screen.getByTestId("card-audit-exceptions")).toHaveTextContent("0");
    expect(screen.getByTestId("card-blocked")).toHaveTextContent("2");
    expect(screen.getByTestId("reviewer-queue-empty")).toBeInTheDocument();
  });

  it("admin: renders aggregates + breakdown tables", async () => {
    setMyDashboard(ADMIN_PAYLOAD);
    render(<RoleDashboard identity="admin@chartnav.local" me={ADMIN_ME} />);
    await waitFor(() =>
      expect(screen.getByTestId("dashboard-admin")).toBeInTheDocument()
    );
    expect(screen.getByTestId("card-open-queue")).toHaveTextContent("25");
    expect(screen.getByTestId("card-overdue")).toHaveTextContent("3");
    expect(screen.getByTestId("card-unsigned-notes")).toHaveTextContent("4");
    expect(screen.getByTestId("card-locations-active")).toHaveTextContent("1");
    expect(screen.getByTestId("card-providers-total")).toHaveTextContent("2");

    const byStatus = screen.getByTestId("admin-by-status");
    expect(within(byStatus).getByText(/^open$/i)).toBeInTheDocument();
    expect(within(byStatus).getByText("18")).toBeInTheDocument();

    const byPriority = screen.getByTestId("admin-by-priority");
    expect(within(byPriority).getByText(/normal/i)).toBeInTheDocument();
  });
});

describe("RoleDashboard — admin view-as switching", () => {
  it("admin can switch view-as to front desk", async () => {
    setMyDashboard(ADMIN_PAYLOAD);
    (api.getFrontDeskDashboard as any).mockResolvedValue(FRONT_DESK_PAYLOAD);
    render(<RoleDashboard identity="admin@chartnav.local" me={ADMIN_ME} />);
    await waitFor(() =>
      expect(screen.getByTestId("dashboard-admin")).toBeInTheDocument()
    );

    const select = screen.getByTestId("dashboard-view-as") as HTMLSelectElement;
    await userEvent.selectOptions(select, "front_desk");

    await waitFor(() =>
      expect(screen.getByTestId("dashboard-front-desk")).toBeInTheDocument()
    );
    expect(api.getFrontDeskDashboard).toHaveBeenCalledWith(
      "admin@chartnav.local"
    );
  });

  it("non-admin does not see view-as selector", async () => {
    setMyDashboard(REVIEWER_PAYLOAD);
    render(<RoleDashboard identity="rev@chartnav.local" me={REVIEWER_ME} />);
    await waitFor(() =>
      expect(screen.getByTestId("dashboard-reviewer")).toBeInTheDocument()
    );
    expect(screen.queryByTestId("dashboard-view-as")).not.toBeInTheDocument();
  });
});

describe("RoleDashboard — error path", () => {
  it("renders an error banner when the request fails", async () => {
    (api.getMyDashboard as any).mockRejectedValue(
      new api.ApiError(403, "role_dashboard_forbidden", "denied")
    );
    render(<RoleDashboard identity="x@y" me={REVIEWER_ME} />);
    await waitFor(() =>
      expect(screen.getByTestId("dashboard-error")).toBeInTheDocument()
    );
    expect(screen.getByTestId("dashboard-error")).toHaveTextContent(
      /role_dashboard_forbidden/
    );
  });
});

describe("RoleDashboard — PHI / forbidden-language safety", () => {
  it("does not render any forbidden billing/insurance vocabulary", async () => {
    setMyDashboard(ADMIN_PAYLOAD);
    const { container } = render(
      <RoleDashboard identity="admin@chartnav.local" me={ADMIN_ME} />
    );
    await waitFor(() =>
      expect(screen.getByTestId("dashboard-admin")).toBeInTheDocument()
    );
    const text = container.textContent?.toLowerCase() ?? "";
    for (const banned of [
      "billing",
      "claim",
      "insurance",
      "copay",
      "co-pay",
      "deductible",
      "cpt",
      "icd-10",
      "icd10",
      "remit",
      "eob",
    ]) {
      expect(text).not.toContain(banned);
    }
  });

  it("does not render patient names, DOB strings, or note bodies", async () => {
    setMyDashboard(DOCTOR_PAYLOAD);
    const { container } = render(
      <RoleDashboard identity="clin@chartnav.local" me={DOCTOR_ME} />
    );
    await waitFor(() =>
      expect(screen.getByTestId("dashboard-doctor")).toBeInTheDocument()
    );
    const text = container.textContent ?? "";
    // Backend payload only carries IDs; ensure the UI never decorates
    // them with names or text-content from the patient record.
    expect(text).not.toMatch(/Morgan/i);
    expect(text).not.toMatch(/Lee/i);
    expect(text).not.toMatch(/\d{4}-\d{2}-\d{2}/); // no DOB-like dates
  });
});
