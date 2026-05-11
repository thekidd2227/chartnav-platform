// Phase 23 — SecurityReadinessPanel tests.

import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../api", async () => {
  const actual = await vi.importActual<typeof import("../api")>("../api");
  return {
    ...actual,
    API_URL: "http://test",
    getSecurityReadiness: vi.fn(),
  };
});

import * as api from "../api";
import { SecurityReadinessPanel } from "../SecurityReadinessPanel";

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

const READINESS: api.SecurityReadinessSummary = {
  organization_id: 1,
  auth_mode: "configured",
  database_kind: "configured",
  audit_retention_configured: "configured",
  cors_explicit_configured: "configured",
  jwt_issuer_configured: "configured",
  jwt_audience_configured: "configured",
  jwt_jwks_url_configured: "configured",
  stt_provider: "disabled",
  backup_config_documented: "external_required",
  logging_config_documented: "external_required",
  monitoring_config_documented: "external_required",
  incident_contacts_documented: "external_required",
  baa_status_configured: "external_required",
  vendor_review_status_configured: "external_required",
  real_phi_go_live_gate_status: "external_required",
  compliance_attestation:
    "ChartNav is not HIPAA-certified. ChartNav is not approved for real PHI by default. This endpoint reports metadata-only environment shape; it does not attest to compliance.",
};

beforeEach(() => {
  vi.clearAllMocks();
  (api.getSecurityReadiness as any).mockResolvedValue(READINESS);
});

describe("SecurityReadinessPanel — RBAC", () => {
  it("non-admin renders blocked placeholder and makes no API call", () => {
    render(<SecurityReadinessPanel identity="clin@x" me={CLINICIAN} />);
    expect(
      screen.getByTestId("security-readiness-blocked")
    ).toBeInTheDocument();
    expect(api.getSecurityReadiness).not.toHaveBeenCalled();
  });
});

describe("SecurityReadinessPanel — admin rendering", () => {
  it("renders every status row + disclaimer", async () => {
    render(<SecurityReadinessPanel identity="admin@x" me={ADMIN} />);
    await waitFor(() =>
      expect(screen.getByTestId("security-readiness-list")).toBeInTheDocument()
    );
    for (const key of [
      "auth_mode",
      "database_kind",
      "audit_retention_configured",
      "stt_provider",
      "real_phi_go_live_gate_status",
    ]) {
      expect(screen.getByTestId(`readiness-row-${key}`)).toBeInTheDocument();
    }
    const disclaimer = screen.getByTestId("security-readiness-disclaimer");
    expect(disclaimer).toHaveTextContent(/not HIPAA-certified/i);
    expect(disclaimer).toHaveTextContent(/not approved for real PHI/i);
  });

  it("error path renders error banner", async () => {
    (api.getSecurityReadiness as any).mockRejectedValue(
      new api.ApiError(403, "role_forbidden", "denied")
    );
    render(<SecurityReadinessPanel identity="admin@x" me={ADMIN} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("security-readiness-error")
      ).toBeInTheDocument()
    );
  });
});

describe("SecurityReadinessPanel — forbidden compliance claims", () => {
  it("does not render HIPAA-compliant / certified-EHR claims outside the negative disclaimer", async () => {
    const { container } = render(
      <SecurityReadinessPanel identity="admin@x" me={ADMIN} />
    );
    await waitFor(() =>
      expect(screen.getByTestId("security-readiness-list")).toBeInTheDocument()
    );
    // Strip the disclaimer (negative-assertion copy) and the subtitle
    // (also a negative-context disclaimer) before scanning.
    const disclaimer = container.querySelector(
      ".security-readiness__disclaimer"
    ) as HTMLElement | null;
    const subtitle = container.querySelector(
      ".security-readiness__subtitle"
    ) as HTMLElement | null;
    const disclaimerText = (disclaimer?.textContent ?? "").toLowerCase();
    const subtitleText = (subtitle?.textContent ?? "").toLowerCase();
    const fullText = (container.textContent ?? "").toLowerCase();
    let text = fullText
      .replace(disclaimerText, "")
      .replace(subtitleText, "");
    for (const banned of [
      "hipaa compliant",
      "hipaa-compliant",
      "hipaa certified",
      "soc 2 certified",
      "certified ehr",
      "approved for real phi",
      "real phi ready",
      "production-ready for phi",
      "baa executed",
      "pen tested",
      "security approved",
    ]) {
      expect(text).not.toContain(banned);
    }
  });
});
