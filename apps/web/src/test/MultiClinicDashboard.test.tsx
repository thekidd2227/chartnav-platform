// Phase 22 — MultiClinicDashboard tests.
//
// Covers:
//   - Non-admin role renders the blocked placeholder and never calls
//     the admin summary endpoint.
//   - Admin renders summary cards, locations list, providers list,
//     breakdown tables.
//   - Selecting a location/provider fetches and renders the detail
//     card.
//   - Empty states render when no locations / providers exist.
//   - Forbidden vocabulary (billing / claims / patient messaging /
//     submit order / etc.) is absent from the interactive surface.

import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../api", async () => {
  const actual = await vi.importActual<typeof import("../api")>("../api");
  return {
    ...actual,
    API_URL: "http://test",
    getAdminMultiClinicSummary: vi.fn(),
    getLocationDashboard: vi.fn(),
    getProviderDashboard: vi.fn(),
  };
});

import * as api from "../api";
import { MultiClinicDashboard } from "../MultiClinicDashboard";

const ADMIN: api.Me = {
  user_id: 1,
  email: "admin@chartnav.local",
  full_name: "ChartNav Admin",
  role: "admin",
  organization_id: 1,
};

const CLINICIAN: api.Me = {
  user_id: 2,
  email: "clin@chartnav.local",
  full_name: "Casey Clinician",
  role: "clinician",
  organization_id: 1,
};

const REVIEWER: api.Me = {
  user_id: 3,
  email: "rev@chartnav.local",
  full_name: "Riley Reviewer",
  role: "reviewer",
  organization_id: 1,
};

const SUMMARY: api.MultiClinicSummary = {
  organization_id: 1,
  locations: [
    {
      location_id: 1,
      open_queue_items: 5,
      ready_for_doctor: 2,
      active_rooms: 4,
      schedule_blocks_today: 3,
    },
    {
      location_id: 2,
      open_queue_items: 0,
      ready_for_doctor: 0,
      active_rooms: 0,
      schedule_blocks_today: 0,
    },
  ],
  providers: [
    { provider_id: 10, open_queue_items: 4, schedule_blocks_today: 2 },
    { provider_id: 11, open_queue_items: 1, schedule_blocks_today: 0 },
  ],
  queue_by_status: { open: 4, in_progress: 1 },
  queue_by_priority: { normal: 3, high: 2 },
  queue_by_assigned_role: { clinician: 3, technician: 2 },
  queue_by_queue_type: {
    ready_for_doctor: 2,
    imaging_review: 1,
    workup: 2,
  },
};

const LOC_DASH: api.LocationDashboardSummary = {
  location_id: 1,
  organization_id: 1,
  counts: {
    open_queue_items: 5,
    ready_for_workup: 1,
    imaging_needed: 1,
    ready_for_doctor: 2,
    review_needed: 1,
    provider_count: 2,
    room_count: 4,
    active_schedule_blocks_today: 3,
  },
};

const PROV_DASH: api.ProviderDashboardSummary = {
  provider_id: 10,
  organization_id: 1,
  counts: {
    assigned_queue_items: 4,
    ready_for_doctor: 2,
    imaging_review: 1,
    signoff_needed: 1,
    review_needed: 0,
    schedule_blocks_today: 2,
    locations_today: 1,
  },
};

beforeEach(() => {
  vi.clearAllMocks();
  (api.getAdminMultiClinicSummary as any).mockResolvedValue(SUMMARY);
  (api.getLocationDashboard as any).mockResolvedValue(LOC_DASH);
  (api.getProviderDashboard as any).mockResolvedValue(PROV_DASH);
});

describe("MultiClinicDashboard — RBAC", () => {
  it("non-admin renders blocked placeholder and makes no API calls", () => {
    render(<MultiClinicDashboard identity="clin@x" me={CLINICIAN} />);
    expect(screen.getByTestId("multi-clinic-blocked")).toBeInTheDocument();
    expect(api.getAdminMultiClinicSummary).not.toHaveBeenCalled();
  });

  it("reviewer is also blocked", () => {
    render(<MultiClinicDashboard identity="rev@x" me={REVIEWER} />);
    expect(screen.getByTestId("multi-clinic-blocked")).toBeInTheDocument();
  });
});

describe("MultiClinicDashboard — admin rendering", () => {
  it("renders summary cards + locations + providers + breakdowns", async () => {
    render(<MultiClinicDashboard identity="admin@x" me={ADMIN} />);
    await waitFor(() =>
      expect(screen.getByTestId("multi-clinic-cards")).toBeInTheDocument()
    );

    expect(screen.getByTestId("card-total-locations")).toHaveTextContent("2");
    expect(screen.getByTestId("card-total-providers")).toHaveTextContent("2");
    expect(screen.getByTestId("card-total-open")).toHaveTextContent("5");

    const locations = screen.getByTestId("locations-list");
    expect(within(locations).getByTestId("location-row-1")).toBeInTheDocument();
    expect(within(locations).getByTestId("location-row-2")).toBeInTheDocument();

    const providers = screen.getByTestId("providers-list");
    expect(within(providers).getByTestId("provider-row-10")).toBeInTheDocument();
    expect(within(providers).getByTestId("provider-row-11")).toBeInTheDocument();

    // Default selection picks location 1 + provider 10 — detail cards render.
    await waitFor(() =>
      expect(
        screen.getByTestId("location-dashboard-card")
      ).toBeInTheDocument()
    );
    await waitFor(() =>
      expect(
        screen.getByTestId("provider-dashboard-card")
      ).toBeInTheDocument()
    );

    expect(screen.getByTestId("breakdown-status")).toBeInTheDocument();
    expect(screen.getByTestId("breakdown-priority")).toBeInTheDocument();
    expect(screen.getByTestId("breakdown-role")).toBeInTheDocument();
    expect(screen.getByTestId("breakdown-queue-type")).toBeInTheDocument();
  });

  it("clicking a different location refetches the location dashboard", async () => {
    render(<MultiClinicDashboard identity="admin@x" me={ADMIN} />);
    await waitFor(() =>
      expect(screen.getByTestId("location-row-2")).toBeInTheDocument()
    );
    await userEvent.click(screen.getByTestId("location-row-2"));
    await waitFor(() =>
      expect(api.getLocationDashboard).toHaveBeenCalledWith("admin@x", 2)
    );
  });

  it("empty state renders when there are no locations", async () => {
    (api.getAdminMultiClinicSummary as any).mockResolvedValue({
      ...SUMMARY,
      locations: [],
      providers: [],
    });
    render(<MultiClinicDashboard identity="admin@x" me={ADMIN} />);
    await waitFor(() =>
      expect(screen.getByTestId("locations-empty")).toBeInTheDocument()
    );
    expect(screen.getByTestId("providers-empty")).toBeInTheDocument();
  });
});

describe("MultiClinicDashboard — error path", () => {
  it("renders the error banner on API failure", async () => {
    (api.getAdminMultiClinicSummary as any).mockRejectedValue(
      new api.ApiError(403, "multi_clinic_role_forbidden", "denied")
    );
    render(<MultiClinicDashboard identity="admin@x" me={ADMIN} />);
    await waitFor(() =>
      expect(screen.getByTestId("multi-clinic-error")).toBeInTheDocument()
    );
    expect(screen.getByTestId("multi-clinic-error")).toHaveTextContent(
      /multi_clinic_role_forbidden/
    );
  });
});

describe("MultiClinicDashboard — forbidden vocabulary", () => {
  it("interactive surface has no billing / claims / patient-messaging language", async () => {
    const { container } = render(
      <MultiClinicDashboard identity="admin@x" me={ADMIN} />
    );
    await waitFor(() =>
      expect(screen.getByTestId("multi-clinic-cards")).toBeInTheDocument()
    );
    // Strip the disclaimer subtitle (negative-assertion copy) before
    // scanning so the disclaimer itself doesn't trip the check.
    const subtitle = container.querySelector(
      ".multi-clinic__subtitle"
    ) as HTMLElement | null;
    const subtitleText = (subtitle?.textContent ?? "").toLowerCase();
    const fullText = (container.textContent ?? "").toLowerCase();
    const text = fullText.replace(subtitleText, "");

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
      "auto-code",
      "auto-bill",
      "send to patient",
      "patient portal",
      "patient message",
      "submit order",
      "send referral",
      "hipaa compliant",
    ]) {
      expect(text).not.toContain(banned);
    }

    const buttons = Array.from(container.querySelectorAll("button"));
    const buttonTexts = buttons.map((b) =>
      (b.textContent ?? "").toLowerCase()
    );
    for (const forbidden of [
      "billing",
      "submit order",
      "send referral",
      "send to patient",
      "submit claim",
    ]) {
      expect(buttonTexts.some((t) => t.includes(forbidden))).toBe(false);
    }
  });
});
