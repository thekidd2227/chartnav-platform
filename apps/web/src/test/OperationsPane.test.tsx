// Phase 53 — Wave 8 OperationsPane tests.
//
// Covers the contract an admin-operator depends on:
//   - overview cards render real server counts
//   - tab switching triggers the right loader
//   - pending-approval queue renders note context and status
//   - identity tab renders the honest "no SCIM" advisory
//   - blocked-notes and identity rows render with category chip,
//     severity color via data attrs, error code, actor, and detail
//   - security-config card flags an unconfigured org
//   - non-admin callers see a restricted placeholder

import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../api", async () => {
  const actual = await vi.importActual<typeof import("../api")>("../api");
  return {
    ...actual,
    API_URL: "http://test",
    getOperationsOverview: vi.fn(),
    getOperationsCategories: vi.fn(),
    getOperationsFinalApprovalQueue: vi.fn(),
    getOperationsBlockedNotes: vi.fn(),
    getOperationsIdentityExceptions: vi.fn(),
    getOperationsSessionExceptions: vi.fn(),
    getOperationsStuckIngest: vi.fn(),
    getOperationsSecurityConfigStatus: vi.fn(),
  };
});

import * as api from "../api";
import { OperationsPane } from "../OperationsPane";

const ADMIN: api.Me = {
  user_id: 1,
  email: "admin@chartnav.local",
  full_name: "Admin",
  role: "admin",
  organization_id: 1,
  is_authorized_final_signer: false,
};

const CLIN: api.Me = { ...ADMIN, user_id: 2, role: "clinician" };

const CATEGORIES: api.OperationsCategoryMeta[] = [
  {
    value: "final_approval_pending",
    label: "Awaiting final physician approval",
    severity: "info",
    next_step: "An authorized doctor must type their name.",
  },
  {
    value: "final_approval_invalidated",
    label: "Final approval invalidated",
    severity: "warning",
    next_step: "Approve the current record of care.",
  },
  {
    value: "governance_sign_blocked",
    label: "Sign blocked by governance",
    severity: "warning",
    next_step: "Resolve missing-data flags then retry.",
  },
  {
    value: "export_blocked",
    label: "Export blocked",
    severity: "warning",
    next_step: "Perform final approval then retry.",
  },
  {
    value: "final_approval_signature_mismatch",
    label: "Final-approval signature mismatch",
    severity: "warning",
    next_step: "Confirm stored name or have the doctor retype.",
  },
  {
    value: "final_approval_unauthorized",
    label: "Unauthorized final-approval attempt",
    severity: "error",
    next_step: "Grant is_authorized_final_signer.",
  },
  {
    value: "identity_unknown_user",
    label: "Identity not mapped to a user",
    severity: "error",
    next_step: "Provision the user.",
  },
  {
    value: "identity_invalid_token",
    label: "Invalid token",
    severity: "warning",
    next_step: "Check JWKS + clock skew.",
  },
  {
    value: "identity_invalid_issuer",
    label: "Token issuer mismatch",
    severity: "warning",
    next_step: "Verify CHARTNAV_JWT_ISSUER.",
  },
  {
    value: "identity_invalid_audience",
    label: "Token audience mismatch",
    severity: "warning",
    next_step: "Verify IdP client registration.",
  },
  {
    value: "identity_missing_user_claim",
    label: "Token missing user claim",
    severity: "warning",
    next_step: "Adjust IdP mapping.",
  },
  {
    value: "identity_cross_org_attempt",
    label: "Cross-org access attempt",
    severity: "warning",
    next_step: "Confirm org assignment.",
  },
  {
    value: "session_revoked_active",
    label: "Session revoked while in use",
    severity: "info",
    next_step: "Expected after admin revoke.",
  },
  {
    value: "session_idle_timeout",
    label: "Session idle timeout",
    severity: "info",
    next_step: "Re-authenticate.",
  },
  {
    value: "session_absolute_timeout",
    label: "Session absolute timeout",
    severity: "info",
    next_step: "Re-authenticate.",
  },
  {
    value: "ingest_stuck",
    label: "Ingest input stuck",
    severity: "warning",
    next_step: "Retry or fix upstream cause.",
  },
  {
    value: "security_policy_unconfigured",
    label: "Security policy unconfigured",
    severity: "info",
    next_step: "Review the Security tab.",
  },
];

const OVERVIEW_EMPTY: api.OperationsOverview = {
  organization_id: 1,
  window_hours: 168,
  since: "2026-04-14T00:00:00+00:00",
  until: "2026-04-21T00:00:00+00:00",
  counts: {
    final_approval_pending: 0,
    final_approval_invalidated: 0,
    governance_sign_blocked: 0,
    export_blocked: 0,
    final_approval_signature_mismatch: 0,
    final_approval_unauthorized: 0,
    identity_unknown_user: 0,
    identity_invalid_token: 0,
    identity_invalid_issuer: 0,
    identity_invalid_audience: 0,
    identity_missing_user_claim: 0,
    identity_cross_org_attempt: 0,
    session_revoked_active: 0,
    session_idle_timeout: 0,
    session_absolute_timeout: 0,
    ingest_stuck: 0,
    security_policy_unconfigured: 1,
  },
  security_policy: {
    session_tracking_configured: false,
    audit_sink_configured: false,
    security_admin_allowlist_configured: false,
    mfa_required: false,
    idle_timeout_minutes: null,
    absolute_timeout_minutes: null,
    audit_sink_mode: "disabled",
    security_admin_allowlist_count: 0,
    unconfigured: true,
  },
  total_open: 1,
};

const OVERVIEW_BUSY: api.OperationsOverview = {
  ...OVERVIEW_EMPTY,
  counts: {
    ...OVERVIEW_EMPTY.counts,
    final_approval_pending: 3,
    governance_sign_blocked: 2,
    identity_unknown_user: 1,
    ingest_stuck: 1,
  },
  total_open: 7,
};

const SEC_STATUS: api.OperationsSecurityPolicyStatus = {
  session_tracking_configured: false,
  audit_sink_configured: false,
  security_admin_allowlist_configured: false,
  mfa_required: false,
  idle_timeout_minutes: null,
  absolute_timeout_minutes: null,
  audit_sink_mode: "disabled",
  security_admin_allowlist_count: 0,
  unconfigured: true,
};

beforeEach(() => {
  vi.clearAllMocks();
  (api.getOperationsCategories as any).mockResolvedValue({
    categories: CATEGORIES,
  });
  (api.getOperationsSecurityConfigStatus as any).mockResolvedValue(SEC_STATUS);
  (api.getOperationsOverview as any).mockResolvedValue(OVERVIEW_EMPTY);
  (api.getOperationsFinalApprovalQueue as any).mockResolvedValue({
    organization_id: 1,
    pending: [],
    invalidated: [],
  });
  (api.getOperationsBlockedNotes as any).mockResolvedValue({
    organization_id: 1,
    hours: 168,
    items: [],
  });
  (api.getOperationsIdentityExceptions as any).mockResolvedValue({
    organization_id: 1,
    hours: 168,
    items: [],
    scim_configured: false,
    oidc_identity_mapping: "email_claim_lookup",
  });
  (api.getOperationsSessionExceptions as any).mockResolvedValue({
    organization_id: 1,
    hours: 168,
    items: [],
  });
  (api.getOperationsStuckIngest as any).mockResolvedValue({
    organization_id: 1,
    items: [],
  });
});

describe("OperationsPane", () => {
  it("non-admin callers see a restricted placeholder", async () => {
    render(<OperationsPane identity="clin@chartnav.local" me={CLIN} />);
    expect(
      await screen.findByTestId("operations-pane-restricted")
    ).toBeInTheDocument();
    // Never triggers the API calls.
    expect(api.getOperationsOverview).not.toHaveBeenCalled();
  });

  it("overview tab renders category counts from server and the security-config card", async () => {
    (api.getOperationsOverview as any).mockResolvedValue(OVERVIEW_BUSY);
    render(<OperationsPane identity="admin@chartnav.local" me={ADMIN} />);
    await waitFor(() =>
      expect(api.getOperationsOverview).toHaveBeenCalledWith(
        "admin@chartnav.local",
        168
      )
    );
    // Counts render.
    const pendingCard = await screen.findByTestId(
      "ops-count-final_approval_pending"
    );
    expect(pendingCard.dataset.count).toBe("3");
    expect(pendingCard.dataset.severity).toBe("info");
    const signBlockedCard = screen.getByTestId(
      "ops-count-governance_sign_blocked"
    );
    expect(signBlockedCard.dataset.count).toBe("2");
    expect(signBlockedCard.dataset.severity).toBe("warning");
    // total_open summary is in the DOM.
    expect(screen.getByTestId("ops-overview-summary")).toHaveTextContent(
      /7 open/
    );
    // Unconfigured security banner renders.
    expect(
      screen.getByTestId("ops-security-config-card").dataset.unconfigured
    ).toBe("true");
    expect(screen.getByTestId("ops-config-unconfigured")).toBeInTheDocument();
  });

  it("window selector changes the hours query on the overview call", async () => {
    render(<OperationsPane identity="admin@chartnav.local" me={ADMIN} />);
    await waitFor(() =>
      expect(api.getOperationsOverview).toHaveBeenCalledWith(
        "admin@chartnav.local",
        168
      )
    );
    const sel = await screen.findByTestId("ops-window-select");
    await userEvent.selectOptions(sel, "24");
    await waitFor(() =>
      expect(api.getOperationsOverview).toHaveBeenLastCalledWith(
        "admin@chartnav.local",
        24
      )
    );
  });

  it("final-approval tab renders pending and invalidated rows with note context", async () => {
    const queue: api.OperationsFinalApprovalQueue = {
      organization_id: 1,
      pending: [
        {
          category: "final_approval_pending",
          severity: "info",
          label: "Awaiting final physician approval",
          next_step: "An authorized doctor must type their name.",
          note_id: 101,
          note_version_number: 2,
          encounter_id: 44,
          actor_user_id: 7,
          draft_status: "signed",
          final_approval_status: "pending",
          occurred_at: "2026-04-20T15:00:00Z",
        },
      ],
      invalidated: [
        {
          category: "final_approval_invalidated",
          severity: "warning",
          label: "Final approval invalidated",
          next_step: "Approve the current record of care.",
          note_id: 88,
          note_version_number: 1,
          encounter_id: 40,
          draft_status: "signed",
          final_approval_status: "invalidated",
          detail: "Superseded by amendment",
          occurred_at: "2026-04-19T11:00:00Z",
        },
      ],
    };
    (api.getOperationsFinalApprovalQueue as any).mockResolvedValue(queue);

    render(<OperationsPane identity="admin@chartnav.local" me={ADMIN} />);
    await userEvent.click(await screen.findByTestId("ops-tab-final-approval"));
    await waitFor(() =>
      expect(api.getOperationsFinalApprovalQueue).toHaveBeenCalled()
    );
    const pending = await screen.findByTestId("ops-final-pending-table");
    expect(within(pending).getByText(/note #101/)).toBeInTheDocument();
    expect(within(pending).getByText(/pending/)).toBeInTheDocument();
    const inval = screen.getByTestId("ops-final-invalidated-table");
    expect(within(inval).getByText(/note #88/)).toBeInTheDocument();
    expect(within(inval).getByText(/Superseded by amendment/)).toBeInTheDocument();
  });

  it("blocked-notes tab renders a row with its category chip, severity, error code, and detail", async () => {
    const resp: api.OperationsListResponse = {
      organization_id: 1,
      hours: 168,
      items: [
        {
          category: "governance_sign_blocked",
          severity: "warning",
          label: "Sign blocked by governance",
          next_step: "Resolve missing-data flags then retry.",
          note_id: 55,
          actor_email: "clin@chartnav.local",
          error_code: "sign_blocked_by_gate",
          detail: "note_id=55 blockers=['note_text_empty']",
          occurred_at: "2026-04-20T10:00:00Z",
        },
      ],
    };
    (api.getOperationsBlockedNotes as any).mockResolvedValue(resp);
    render(<OperationsPane identity="admin@chartnav.local" me={ADMIN} />);
    await userEvent.click(await screen.findByTestId("ops-tab-blocked-notes"));
    const row = await screen.findByTestId("ops-row-governance_sign_blocked");
    expect(row.dataset.severity).toBe("warning");
    expect(within(row).getByText(/clin@chartnav.local/)).toBeInTheDocument();
    expect(within(row).getByText(/sign_blocked_by_gate/)).toBeInTheDocument();
    expect(
      within(row).getByText(/note_id=55 blockers/)
    ).toBeInTheDocument();
  });

  it("identity tab renders the honest SCIM / OIDC advisory", async () => {
    render(<OperationsPane identity="admin@chartnav.local" me={ADMIN} />);
    await userEvent.click(await screen.findByTestId("ops-tab-identity"));
    const advisory = await screen.findByTestId("ops-identity-mapping-advisory");
    expect(advisory).toHaveTextContent(/email_claim_lookup/);
    expect(advisory).toHaveTextContent(/SCIM is/);
    expect(advisory).toHaveTextContent(/not configured/);
  });

  it("identity tab shows empty-state when no events", async () => {
    render(<OperationsPane identity="admin@chartnav.local" me={ADMIN} />);
    await userEvent.click(await screen.findByTestId("ops-tab-identity"));
    expect(
      await screen.findByTestId("ops-identity-empty")
    ).toBeInTheDocument();
  });

  it("security-config tab flags an unconfigured policy", async () => {
    render(<OperationsPane identity="admin@chartnav.local" me={ADMIN} />);
    await userEvent.click(
      await screen.findByTestId("ops-tab-security-config")
    );
    const card = await screen.findByTestId("ops-security-config-card");
    expect(card.dataset.unconfigured).toBe("true");
    expect(screen.getByTestId("ops-config-unconfigured")).toBeInTheDocument();
    // Row-level status flags.
    expect(
      screen.getByTestId("ops-config-session-tracking").dataset.ok
    ).toBe("false");
    expect(screen.getByTestId("ops-config-audit-sink").dataset.ok).toBe(
      "false"
    );
    expect(screen.getByTestId("ops-config-mfa").dataset.ok).toBe("false");
  });

  it("refresh button re-fetches the overview", async () => {
    render(<OperationsPane identity="admin@chartnav.local" me={ADMIN} />);
    await waitFor(() =>
      expect(api.getOperationsOverview).toHaveBeenCalledTimes(1)
    );
    await userEvent.click(await screen.findByTestId("ops-refresh"));
    await waitFor(() =>
      expect(api.getOperationsOverview).toHaveBeenCalledTimes(2)
    );
  });
});
