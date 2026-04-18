import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../api", async () => {
  const actual = await vi.importActual<typeof import("../api")>("../api");
  return {
    ...actual,
    API_URL: "http://test",
    listUsers: vi.fn(),
    listUsersPage: vi.fn(),
    createUser: vi.fn(),
    updateUser: vi.fn(),
    deactivateUser: vi.fn(),
    listLocations: vi.fn(),
    listLocationsPage: vi.fn(),
    createLocation: vi.fn(),
    updateLocation: vi.fn(),
    deactivateLocation: vi.fn(),
    getOrganization: vi.fn(),
    updateOrganization: vi.fn(),
    listAuditEvents: vi.fn(),
    inviteUser: vi.fn(),
    bulkCreateUsers: vi.fn(),
    downloadAuditExport: vi.fn(),
  };
});

import * as api from "../api";
import { AdminPanel } from "../AdminPanel";

const ADMIN1: api.Me = {
  user_id: 1,
  email: "admin@chartnav.local",
  full_name: "Org1 Admin",
  role: "admin",
  organization_id: 1,
};

const USERS: api.User[] = [
  {
    id: 1,
    organization_id: 1,
    email: "admin@chartnav.local",
    full_name: "Admin A",
    role: "admin",
    is_active: 1,
    invited_at: null,
    created_at: "2026-04-18 01:00:00",
  },
  {
    id: 2,
    organization_id: 1,
    email: "clin@chartnav.local",
    full_name: "Casey",
    role: "clinician",
    is_active: 1,
    invited_at: null,
    created_at: "2026-04-18 01:00:00",
  },
];

const LOCATIONS: api.Location[] = [
  {
    id: 1,
    organization_id: 1,
    name: "Main Clinic",
    is_active: 1,
    created_at: "2026-04-18 01:00:00",
  },
];

beforeEach(() => {
  vi.clearAllMocks();
  (api.listUsers as any).mockResolvedValue(USERS);
  (api.listLocations as any).mockResolvedValue(LOCATIONS);
  (api.listUsersPage as any).mockResolvedValue({
    items: USERS, total: USERS.length, limit: 25, offset: 0,
  });
  (api.listLocationsPage as any).mockResolvedValue({
    items: LOCATIONS, total: LOCATIONS.length, limit: 25, offset: 0,
  });
  (api.getOrganization as any).mockResolvedValue({
    id: 1,
    name: "Demo Eye Clinic",
    slug: "demo-eye-clinic",
    settings: { timezone: "America/New_York" },
    created_at: "2026-04-18 01:00:00",
  });
  (api.listAuditEvents as any).mockResolvedValue({
    items: [
      {
        id: 10,
        event_type: "cross_org_access_forbidden",
        request_id: "abc1234567",
        actor_email: "admin@chartnav.local",
        actor_user_id: 1,
        organization_id: 1,
        path: "/encounters",
        method: "GET",
        error_code: "cross_org_access_forbidden",
        detail: "requested organization...",
        remote_addr: "127.0.0.1",
        created_at: "2026-04-18 05:00:00",
      },
    ],
    total: 1,
    limit: 25,
    offset: 0,
  });
});

describe("AdminPanel", () => {
  it("lists users on load", async () => {
    render(<AdminPanel identity={ADMIN1.email} me={ADMIN1} onClose={() => {}} />);
    await screen.findByTestId("admin-users-table");
    const table = screen.getByTestId("admin-users-table");
    expect(within(table).getByText("admin@chartnav.local")).toBeInTheDocument();
    expect(within(table).getByText("clin@chartnav.local")).toBeInTheDocument();
  });

  it("submits create-user form and refreshes", async () => {
    const newUser: api.User = {
      id: 99,
      organization_id: 1,
      email: "new@chartnav.local",
      full_name: "New",
      role: "reviewer",
      is_active: 1,
      invited_at: "2026-04-18 02:00:00",
      created_at: "2026-04-18 02:00:00",
    };
    (api.createUser as any).mockResolvedValueOnce(newUser);
    (api.listUsers as any).mockResolvedValueOnce([...USERS, newUser]);
    (api.listUsersPage as any).mockResolvedValueOnce({
      items: [...USERS, newUser],
      total: USERS.length + 1,
      limit: 25,
      offset: 0,
    });

    const user = userEvent.setup();
    render(<AdminPanel identity={ADMIN1.email} me={ADMIN1} onClose={() => {}} />);
    await screen.findByTestId("admin-users-table");

    await user.type(screen.getByTestId("admin-user-email"), "new@chartnav.local");
    await user.type(screen.getByTestId("admin-user-name"), "New");
    await user.selectOptions(screen.getByTestId("admin-user-role"), "reviewer");
    await user.click(screen.getByTestId("admin-user-submit"));

    await waitFor(() => {
      expect(api.createUser).toHaveBeenCalledWith("admin@chartnav.local", {
        email: "new@chartnav.local",
        full_name: "New",
        role: "reviewer",
      });
    });
    expect(await screen.findByTestId("admin-banner-ok")).toHaveTextContent(
      "new@chartnav.local"
    );
  });

  it("surfaces backend error on create failure", async () => {
    (api.createUser as any).mockRejectedValueOnce(
      new api.ApiError(409, "user_email_taken", "email already in use")
    );
    const user = userEvent.setup();
    render(<AdminPanel identity={ADMIN1.email} me={ADMIN1} onClose={() => {}} />);
    await screen.findByTestId("admin-users-table");

    await user.type(screen.getByTestId("admin-user-email"), "dup@chartnav.local");
    await user.click(screen.getByTestId("admin-user-submit"));

    const banner = await screen.findByTestId("admin-banner-error");
    expect(banner).toHaveTextContent("409");
    expect(banner).toHaveTextContent("user_email_taken");
  });

  it("disables self-edit in the user row", async () => {
    render(<AdminPanel identity={ADMIN1.email} me={ADMIN1} onClose={() => {}} />);
    await screen.findByTestId("admin-users-table");
    // Row for self (id=1): role select is disabled, deactivate button is disabled.
    const select = screen.getByTestId("admin-user-role-1") as HTMLSelectElement;
    expect(select.disabled).toBe(true);
    const deactivate = screen.getByTestId("admin-user-deactivate-1") as HTMLButtonElement;
    expect(deactivate.disabled).toBe(true);
  });

  it("creates a location via the locations tab", async () => {
    const newLoc: api.Location = {
      id: 2,
      organization_id: 1,
      name: "Downtown",
      is_active: 1,
      created_at: "2026-04-18 02:00:00",
    };
    (api.createLocation as any).mockResolvedValueOnce(newLoc);
    (api.listLocations as any).mockResolvedValueOnce([...LOCATIONS, newLoc]);
    (api.listLocationsPage as any).mockResolvedValueOnce({
      items: [...LOCATIONS, newLoc],
      total: LOCATIONS.length + 1,
      limit: 25,
      offset: 0,
    });

    const user = userEvent.setup();
    render(<AdminPanel identity={ADMIN1.email} me={ADMIN1} onClose={() => {}} />);
    await screen.findByTestId("admin-users-table");

    await user.click(screen.getByTestId("admin-tab-locations"));
    await screen.findByTestId("admin-locations-table");

    await user.type(screen.getByTestId("admin-loc-name"), "Downtown");
    await user.click(screen.getByTestId("admin-loc-submit"));

    await waitFor(() => {
      expect(api.createLocation).toHaveBeenCalledWith("admin@chartnav.local", "Downtown");
    });
  });

  it("organization tab loads current org and saves edits", async () => {
    const user = userEvent.setup();
    render(<AdminPanel identity={ADMIN1.email} me={ADMIN1} onClose={() => {}} />);
    await user.click(await screen.findByTestId("admin-tab-organization"));

    const nameInput = await screen.findByTestId("admin-org-name") as HTMLInputElement;
    expect(nameInput.value).toBe("Demo Eye Clinic");
    const slugInput = screen.getByTestId("admin-org-slug") as HTMLInputElement;
    expect(slugInput.readOnly).toBe(true);

    // Mutate name and submit.
    (api.updateOrganization as any).mockResolvedValueOnce({
      id: 1,
      name: "Demo Eye Clinic (Renamed)",
      slug: "demo-eye-clinic",
      settings: { timezone: "America/New_York" },
      created_at: "2026-04-18 01:00:00",
    });
    await user.clear(nameInput);
    await user.type(nameInput, "Demo Eye Clinic (Renamed)");
    await user.click(screen.getByTestId("admin-org-submit"));

    await waitFor(() => {
      expect(api.updateOrganization).toHaveBeenCalledWith(
        "admin@chartnav.local",
        expect.objectContaining({ name: "Demo Eye Clinic (Renamed)" })
      );
    });
    expect(await screen.findByTestId("admin-banner-ok")).toHaveTextContent(
      /Organization saved/
    );
  });

  it("organization settings non-object input shows a local error", async () => {
    const user = userEvent.setup();
    render(<AdminPanel identity={ADMIN1.email} me={ADMIN1} onClose={() => {}} />);
    await user.click(await screen.findByTestId("admin-tab-organization"));
    const ta = await screen.findByTestId("admin-org-settings") as HTMLTextAreaElement;
    await user.clear(ta);
    // user-event treats square brackets as keyboard modifiers; paste instead.
    await user.click(ta);
    await user.paste("[1,2,3]");
    await user.click(screen.getByTestId("admin-org-submit"));
    const banner = await screen.findByTestId("admin-banner-error");
    expect(banner).toHaveTextContent(/extensions JSON/);
    // We must NOT have called the backend.
    expect(api.updateOrganization).not.toHaveBeenCalled();
  });

  it("audit tab loads and filters by event_type", async () => {
    const user = userEvent.setup();
    render(<AdminPanel identity={ADMIN1.email} me={ADMIN1} onClose={() => {}} />);
    await user.click(await screen.findByTestId("admin-tab-audit"));

    await screen.findByTestId("admin-audit-table");
    // "cross_org_access_forbidden" appears in both the event_type column
    // and the error_code column, so scope the assertion to the row.
    expect(screen.getByTestId("admin-audit-row-10")).toHaveTextContent(
      "cross_org_access_forbidden"
    );

    await user.type(
      screen.getByTestId("admin-audit-event-type"),
      "invalid_token"
    );

    await waitFor(() => {
      const calls = (api.listAuditEvents as any).mock.calls;
      const last = calls.at(-1);
      expect(last?.[1]).toEqual({ event_type: "invalid_token" });
    });
  });

  it("admin can issue an invitation from a user row", async () => {
    (api.inviteUser as any).mockResolvedValueOnce({
      user_id: 2,
      invitation_token: "fake-token-xxx",
      invitation_expires_at: "2026-04-25T10:00:00Z",
      ttl_days: 7,
    });
    const user = userEvent.setup();
    render(<AdminPanel identity={ADMIN1.email} me={ADMIN1} onClose={() => {}} />);
    await screen.findByTestId("admin-users-table");

    await user.click(screen.getByTestId("admin-user-invite-2"));

    await waitFor(() => {
      expect(api.inviteUser).toHaveBeenCalledWith("admin@chartnav.local", 2);
    });
    const tokenBox = await screen.findByTestId("admin-invite-token");
    expect(tokenBox).toHaveTextContent("fake-token-xxx");
  });

  it("admin bulk-import surfaces created/skipped/errors summary", async () => {
    (api.bulkCreateUsers as any).mockResolvedValueOnce({
      created: [{ id: 101, email: "new@chartnav.local", role: "clinician" }],
      skipped: [{ row: 1, email: "admin@chartnav.local", error_code: "user_email_taken" }],
      errors: [{ row: 2, email: "bad@chartnav.local", error_code: "invalid_role" }],
      summary: { requested: 3, created: 1, skipped: 1, errors: 1 },
    });

    const user = userEvent.setup();
    render(<AdminPanel identity={ADMIN1.email} me={ADMIN1} onClose={() => {}} />);
    await screen.findByTestId("admin-users-table");

    await user.click(screen.getByTestId("admin-user-bulk-open"));
    await screen.findByTestId("admin-user-bulk-modal");
    await user.click(screen.getByTestId("admin-user-bulk-submit"));

    const summary = await screen.findByTestId("admin-user-bulk-summary");
    expect(summary).toHaveTextContent("Created 1");
    expect(summary).toHaveTextContent("Skipped 1");
    expect(summary).toHaveTextContent("Errors 1");
  });

  it("audit tab triggers CSV export with current filters", async () => {
    const user = userEvent.setup();
    render(<AdminPanel identity={ADMIN1.email} me={ADMIN1} onClose={() => {}} />);
    await user.click(await screen.findByTestId("admin-tab-audit"));
    await screen.findByTestId("admin-audit-table");

    await user.type(screen.getByTestId("admin-audit-event-type"), "unknown_user");
    // wait for the refresh that comes from the filter change
    await waitFor(() => {
      const calls = (api.listAuditEvents as any).mock.calls;
      expect(calls.at(-1)?.[1]).toEqual({ event_type: "unknown_user" });
    });

    await user.click(screen.getByTestId("admin-audit-export"));
    await waitFor(() => {
      expect(api.downloadAuditExport).toHaveBeenCalledWith(
        "admin@chartnav.local",
        { event_type: "unknown_user" }
      );
    });
  });

  it("feature flag `audit_export=false` hides the Export CSV button", async () => {
    (api.getOrganization as any).mockResolvedValue({
      id: 1,
      name: "Demo Eye Clinic",
      slug: "demo-eye-clinic",
      settings: { feature_flags: { audit_export: false } },
      created_at: "2026-04-18 01:00:00",
    });
    const user = userEvent.setup();
    render(<AdminPanel identity={ADMIN1.email} me={ADMIN1} onClose={() => {}} />);
    await user.click(await screen.findByTestId("admin-tab-audit"));
    await screen.findByTestId("admin-audit-table");
    expect(screen.queryByTestId("admin-audit-export")).not.toBeInTheDocument();
    expect(screen.getByTestId("admin-audit-refresh")).toBeInTheDocument();
  });

  it("feature flag `bulk_import=false` hides the Bulk import button", async () => {
    (api.getOrganization as any).mockResolvedValue({
      id: 1,
      name: "Demo Eye Clinic",
      slug: "demo-eye-clinic",
      settings: { feature_flags: { bulk_import: false } },
      created_at: "2026-04-18 01:00:00",
    });
    render(<AdminPanel identity={ADMIN1.email} me={ADMIN1} onClose={() => {}} />);
    await screen.findByTestId("admin-users-table");
    expect(screen.queryByTestId("admin-user-bulk-open")).not.toBeInTheDocument();
  });

  it("admin list search field dispatches listUsersPage with q param", async () => {
    const user = userEvent.setup();
    render(<AdminPanel identity={ADMIN1.email} me={ADMIN1} onClose={() => {}} />);
    await screen.findByTestId("admin-users-table");
    await user.type(screen.getByTestId("admin-user-search"), "clin");
    await waitFor(() => {
      const calls = (api.listUsersPage as any).mock.calls;
      expect(calls.at(-1)?.[1]?.q).toBe("clin");
    });
  });

  it("audit tab surfaces backend 403 as error banner", async () => {
    (api.listAuditEvents as any).mockRejectedValueOnce(
      new api.ApiError(403, "role_admin_required", "admin only")
    );
    const user = userEvent.setup();
    render(<AdminPanel identity={ADMIN1.email} me={ADMIN1} onClose={() => {}} />);
    await user.click(await screen.findByTestId("admin-tab-audit"));

    const banner = await screen.findByTestId("admin-banner-error");
    expect(banner).toHaveTextContent("403");
    expect(banner).toHaveTextContent("role_admin_required");
  });
});
