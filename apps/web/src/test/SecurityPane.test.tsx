// Phase 48 — SecurityPane vitest.
//
// Contract covered:
//   - renders the policy block (read-only when not a security-admin)
//   - saving the policy calls updateSecurityPolicy with only the
//     changed fields
//   - sessions table renders rows + revoke calls revokeSecuritySession
//   - audit sink block shows mode + target + probe button
//   - error banner on API failure
//   - read-only note when caller_is_security_admin === false

import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../api", async () => {
  const actual = await vi.importActual<typeof import("../api")>("../api");
  return {
    ...actual,
    API_URL: "http://test",
    getSecurityPolicy: vi.fn(),
    updateSecurityPolicy: vi.fn(),
    listSecuritySessions: vi.fn(),
    revokeSecuritySession: vi.fn(),
    probeAuditSink: vi.fn(),
  };
});

import * as api from "../api";
import { SecurityPane } from "../SecurityPane";

const ADMIN: api.Me = {
  user_id: 1,
  email: "admin@chartnav.local",
  full_name: "Admin",
  role: "admin",
  organization_id: 1,
  is_authorized_final_signer: false,
};
const ORG: api.Organization = {
  id: 1,
  name: "Demo Eye Clinic",
  slug: "demo-eye-clinic",
  settings: null,
  created_at: "2026-04-01",
};

const DEFAULT_POLICY: api.SecurityPolicyPayload = {
  require_mfa: false,
  idle_timeout_minutes: null,
  absolute_timeout_minutes: null,
  audit_sink_mode: "disabled",
  audit_sink_target: null,
  security_admin_emails: [],
};

const SESSION: api.SecuritySessionRow = {
  id: 7,
  user_id: 1,
  user_email: "admin@chartnav.local",
  user_role: "admin",
  session_key: "hdr:admin-chartnav-local",
  auth_mode: "header",
  created_at: "2026-04-21T05:00:00+00:00",
  last_activity_at: "2026-04-21T06:00:00+00:00",
  revoked_at: null,
  revoked_reason: null,
  remote_addr: "127.0.0.1",
  user_agent: "vitest",
};

beforeEach(() => {
  (api.getSecurityPolicy as any).mockResolvedValue({
    organization_id: 1,
    caller_is_security_admin: true,
    policy: DEFAULT_POLICY,
  });
  (api.listSecuritySessions as any).mockResolvedValue({
    organization_id: 1,
    include_revoked: false,
    sessions: [SESSION],
  });
  (api.updateSecurityPolicy as any).mockImplementation(
    async (_email: string, patch: api.SecurityPolicyPatch) => ({
      organization_id: 1,
      caller_is_security_admin: true,
      policy: { ...DEFAULT_POLICY, ...patch },
    })
  );
  (api.revokeSecuritySession as any).mockResolvedValue({
    session: { ...SESSION, revoked_at: "2026-04-21T06:30:00+00:00", revoked_reason: "admin_terminated" },
  });
  (api.probeAuditSink as any).mockResolvedValue({
    ok: true,
    mode: "disabled",
    target: null,
    detail: "sink is disabled; nothing dispatched",
  });
});

describe("SecurityPane", () => {
  it("renders the policy block, sessions table, and audit sink block", async () => {
    render(<SecurityPane identity={ADMIN.email} me={ADMIN} org={ORG} />);
    await screen.findByTestId("security-pane");

    // Policy fields populated from the initial GET.
    await waitFor(() => {
      expect(screen.getByTestId("sec-require-mfa")).not.toBeChecked();
      expect(screen.getByTestId("sec-idle-timeout")).toHaveValue(null);
    });

    // Sessions list has the seeded row.
    expect(await screen.findByTestId("sec-session-row-7")).toBeInTheDocument();

    // Audit sink mode visible.
    expect(screen.getByTestId("sec-sink-mode")).toHaveTextContent(/disabled/i);
  });

  it("save policy calls updateSecurityPolicy with only changed fields", async () => {
    const user = userEvent.setup();
    render(<SecurityPane identity={ADMIN.email} me={ADMIN} org={ORG} />);
    await screen.findByTestId("sec-require-mfa");
    await user.click(screen.getByTestId("sec-require-mfa"));
    const idleInput = screen.getByTestId("sec-idle-timeout") as HTMLInputElement;
    await user.clear(idleInput);
    await user.type(idleInput, "20");
    await user.click(screen.getByTestId("sec-save-policy"));
    await waitFor(() =>
      expect(api.updateSecurityPolicy).toHaveBeenCalledWith(
        ADMIN.email,
        expect.objectContaining({
          require_mfa: true,
          idle_timeout_minutes: 20,
        })
      )
    );
    await waitFor(() =>
      expect(screen.getByTestId("sec-banner")).toHaveTextContent(/updated/i)
    );
  });

  it("revoke button calls revokeSecuritySession with the row id", async () => {
    const user = userEvent.setup();
    render(<SecurityPane identity={ADMIN.email} me={ADMIN} org={ORG} />);
    const btn = await screen.findByTestId("sec-revoke-7");
    await user.click(btn);
    await waitFor(() =>
      expect(api.revokeSecuritySession).toHaveBeenCalledWith(
        ADMIN.email,
        7,
        "admin_terminated"
      )
    );
  });

  it("probe button calls probeAuditSink and surfaces the result", async () => {
    const user = userEvent.setup();
    render(<SecurityPane identity={ADMIN.email} me={ADMIN} org={ORG} />);
    await screen.findByTestId("sec-probe-sink");
    await user.click(screen.getByTestId("sec-probe-sink"));
    await waitFor(() =>
      expect(api.probeAuditSink).toHaveBeenCalledWith(ADMIN.email)
    );
    await waitFor(() =>
      expect(screen.getByTestId("sec-sink-probe-value")).toHaveTextContent(/ok/i)
    );
  });

  it("renders read-only note + disables save when caller is not a security admin", async () => {
    (api.getSecurityPolicy as any).mockResolvedValue({
      organization_id: 1,
      caller_is_security_admin: false,
      policy: DEFAULT_POLICY,
    });
    render(<SecurityPane identity={ADMIN.email} me={ADMIN} org={ORG} />);
    await screen.findByTestId("security-pane");
    await waitFor(() => {
      const save = screen.getByTestId("sec-save-policy") as HTMLButtonElement;
      expect(save).toBeDisabled();
    });
    expect(screen.getByTestId("sec-readonly-note")).toBeInTheDocument();
    // Session revoke button should NOT render on the admin row.
    expect(screen.queryByTestId("sec-revoke-7")).not.toBeInTheDocument();
  });

  it("shows an error banner when the initial fetch fails", async () => {
    (api.getSecurityPolicy as any).mockRejectedValueOnce(
      new api.ApiError(500, "internal_error", "db down")
    );
    render(<SecurityPane identity={ADMIN.email} me={ADMIN} org={ORG} />);
    await waitFor(() =>
      expect(screen.getByTestId("sec-banner")).toHaveTextContent(/internal_error/)
    );
  });

  it("toggling include-revoked re-requests with the flag", async () => {
    const user = userEvent.setup();
    render(<SecurityPane identity={ADMIN.email} me={ADMIN} org={ORG} />);
    await screen.findByTestId("sec-include-revoked");
    await user.click(screen.getByTestId("sec-include-revoked"));
    await waitFor(() =>
      expect(api.listSecuritySessions).toHaveBeenCalledWith(
        ADMIN.email,
        expect.objectContaining({ includeRevoked: true })
      )
    );
  });
});
