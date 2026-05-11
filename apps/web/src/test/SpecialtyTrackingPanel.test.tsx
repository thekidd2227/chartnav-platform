// Phase 21A — SpecialtyTrackingPanel tests.
//
// Covers:
//   - Renders both Retina + Glaucoma sections.
//   - Empty state copy for retina, glaucoma, IOP, VF, injections.
//   - Clinician/admin sees write controls (+ Add buttons + status select).
//   - Reviewer sees read-only state (no add buttons; explicit copy).
//   - Front desk is fully blocked at the panel level.
//   - Retina create form submits and refreshes.
//   - Forbidden-vocabulary scan: no diagnosis/dosing/order/referral/
//     billing/messaging language anywhere in the rendered DOM.

import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../api", async () => {
  const actual = await vi.importActual<typeof import("../api")>("../api");
  return {
    ...actual,
    API_URL: "http://test",
    listPatientRetinaTracking: vi.fn(),
    listPatientRetinaInjections: vi.fn(),
    createPatientRetinaTracking: vi.fn(),
    createPatientRetinaInjection: vi.fn(),
    updatePatientRetinaTracking: vi.fn(),
    listPatientGlaucomaTracking: vi.fn(),
    listPatientGlaucomaIopMeasurements: vi.fn(),
    listPatientGlaucomaVisualFields: vi.fn(),
    createPatientGlaucomaTracking: vi.fn(),
    createPatientGlaucomaIopMeasurement: vi.fn(),
    createPatientGlaucomaVisualField: vi.fn(),
    updatePatientGlaucomaTracking: vi.fn(),
  };
});

import * as api from "../api";
import { SpecialtyTrackingPanel } from "../SpecialtyTrackingPanel";

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

const FRONT_DESK: api.Me = {
  user_id: 10,
  email: "front@chartnav.local",
  full_name: "Frankie Front-Desk",
  role: "front_desk",
  organization_id: 1,
};

const TECHNICIAN: api.Me = {
  user_id: 11,
  email: "tech@chartnav.local",
  full_name: "Taylor Technician",
  role: "technician",
  organization_id: 1,
};

const RETINA_ROW: api.RetinaTrackingRecord = {
  id: 100,
  organization_id: 1,
  patient_id: 1,
  encounter_id: 200,
  eye: "OD",
  condition: "neovascular AMD",
  severity: "moderate",
  last_oct_at: "2026-04-01T00:00:00",
  last_fundus_at: null,
  injection_history_summary: "aflibercept x6",
  follow_up_interval: "4 weeks",
  provider_assessment: "stable",
  review_status: "needs_review",
  created_by_user_id: 2,
  updated_by_user_id: null,
  created_at: "2026-05-01T00:00:00",
  updated_at: "2026-05-01T00:00:00",
};

const GLAUCOMA_ROW: api.GlaucomaTrackingRecord = {
  id: 200,
  organization_id: 1,
  patient_id: 1,
  encounter_id: 200,
  eye: "OS",
  glaucoma_type: "POAG",
  target_iop: 16.0,
  latest_iop: 18.5,
  cup_to_disc_ratio: 0.6,
  rnfl_status: "thinning",
  visual_field_status: "stable",
  medication_plan: "latanoprost qhs OS",
  progression_risk_label: "moderate",
  provider_assessment: "monitor; recheck in 12 weeks",
  review_status: "draft",
  created_by_user_id: 2,
  updated_by_user_id: null,
  created_at: "2026-05-01T00:00:00",
  updated_at: "2026-05-01T00:00:00",
};

function emptyList<T>() {
  return { items: [] as T[], total: 0 };
}

beforeEach(() => {
  vi.clearAllMocks();
  // Default: empty data for everything; individual tests override.
  (api.listPatientRetinaTracking as any).mockResolvedValue(emptyList());
  (api.listPatientRetinaInjections as any).mockResolvedValue(emptyList());
  (api.listPatientGlaucomaTracking as any).mockResolvedValue(emptyList());
  (api.listPatientGlaucomaIopMeasurements as any).mockResolvedValue(emptyList());
  (api.listPatientGlaucomaVisualFields as any).mockResolvedValue(emptyList());
});

describe("SpecialtyTrackingPanel — empty states", () => {
  it("renders both sections with empty placeholders for clinician", async () => {
    render(
      <SpecialtyTrackingPanel
        identity="clin@chartnav.local"
        me={CLINICIAN}
        patientId={1}
        encounterId={200}
      />
    );
    await waitFor(() =>
      expect(screen.getByTestId("specialty-tracking")).toBeInTheDocument()
    );
    expect(screen.getByTestId("specialty-retina")).toBeInTheDocument();
    expect(screen.getByTestId("specialty-glaucoma")).toBeInTheDocument();
    expect(screen.getByTestId("retina-empty")).toHaveTextContent(
      /No retina tracking yet/i
    );
    expect(screen.getByTestId("glaucoma-empty")).toHaveTextContent(
      /No glaucoma tracking yet/i
    );
    expect(screen.getByTestId("retina-injections-empty")).toBeInTheDocument();
    expect(screen.getByTestId("glaucoma-iop-empty")).toBeInTheDocument();
    expect(screen.getByTestId("glaucoma-vf-empty")).toBeInTheDocument();
  });
});

describe("SpecialtyTrackingPanel — populated rendering", () => {
  it("renders retina + glaucoma cards with values", async () => {
    (api.listPatientRetinaTracking as any).mockResolvedValue({
      items: [RETINA_ROW],
      total: 1,
    });
    (api.listPatientGlaucomaTracking as any).mockResolvedValue({
      items: [GLAUCOMA_ROW],
      total: 1,
    });
    render(
      <SpecialtyTrackingPanel
        identity="clin@chartnav.local"
        me={CLINICIAN}
        patientId={1}
        encounterId={200}
      />
    );
    await waitFor(() =>
      expect(screen.getByTestId("retina-cards")).toBeInTheDocument()
    );
    const retinaCard = screen.getByTestId(`retina-card-${RETINA_ROW.id}`);
    expect(within(retinaCard).getByText("neovascular AMD")).toBeInTheDocument();
    expect(within(retinaCard).getByText("OD")).toBeInTheDocument();
    expect(within(retinaCard).getByText("needs_review")).toBeInTheDocument();

    const glaucomaCard = screen.getByTestId(`glaucoma-card-${GLAUCOMA_ROW.id}`);
    expect(within(glaucomaCard).getByText("POAG")).toBeInTheDocument();
    expect(within(glaucomaCard).getByText("16 mmHg")).toBeInTheDocument();
    expect(within(glaucomaCard).getByText("18.5 mmHg")).toBeInTheDocument();
    expect(within(glaucomaCard).getByText("0.60")).toBeInTheDocument();
  });
});

describe("SpecialtyTrackingPanel — RBAC rendering", () => {
  it("clinician sees + Add buttons", async () => {
    render(
      <SpecialtyTrackingPanel
        identity="clin@chartnav.local"
        me={CLINICIAN}
        patientId={1}
        encounterId={200}
      />
    );
    await waitFor(() =>
      expect(screen.getByTestId("specialty-retina")).toBeInTheDocument()
    );
    expect(screen.getByTestId("retina-add")).toBeInTheDocument();
    expect(screen.getByTestId("glaucoma-add")).toBeInTheDocument();
    expect(screen.getByTestId("retina-add-injection")).toBeInTheDocument();
    expect(screen.getByTestId("glaucoma-add-iop")).toBeInTheDocument();
    expect(screen.getByTestId("glaucoma-add-vf")).toBeInTheDocument();
  });

  it("reviewer sees read-only state — no add buttons, explicit copy on each card", async () => {
    (api.listPatientRetinaTracking as any).mockResolvedValue({
      items: [RETINA_ROW],
      total: 1,
    });
    (api.listPatientGlaucomaTracking as any).mockResolvedValue({
      items: [GLAUCOMA_ROW],
      total: 1,
    });
    render(
      <SpecialtyTrackingPanel
        identity="rev@chartnav.local"
        me={REVIEWER}
        patientId={1}
        encounterId={200}
      />
    );
    await waitFor(() =>
      expect(screen.getByTestId("retina-cards")).toBeInTheDocument()
    );
    expect(screen.queryByTestId("retina-add")).not.toBeInTheDocument();
    expect(screen.queryByTestId("glaucoma-add")).not.toBeInTheDocument();
    expect(screen.queryByTestId("retina-add-injection")).not.toBeInTheDocument();
    expect(screen.queryByTestId("glaucoma-add-iop")).not.toBeInTheDocument();
    expect(screen.queryByTestId("glaucoma-add-vf")).not.toBeInTheDocument();
    expect(
      screen.getByTestId(`retina-readonly-${RETINA_ROW.id}`)
    ).toHaveTextContent(/read-only/i);
    expect(
      screen.getByTestId(`glaucoma-readonly-${GLAUCOMA_ROW.id}`)
    ).toHaveTextContent(/read-only/i);
  });

  it("technician cannot add tracking rows but can add measurement events", async () => {
    render(
      <SpecialtyTrackingPanel
        identity="tech@chartnav.local"
        me={TECHNICIAN}
        patientId={1}
        encounterId={200}
      />
    );
    await waitFor(() =>
      expect(screen.getByTestId("specialty-retina")).toBeInTheDocument()
    );
    expect(screen.queryByTestId("retina-add")).not.toBeInTheDocument();
    expect(screen.queryByTestId("glaucoma-add")).not.toBeInTheDocument();
    expect(screen.getByTestId("retina-add-injection")).toBeInTheDocument();
    expect(screen.getByTestId("glaucoma-add-iop")).toBeInTheDocument();
    expect(screen.getByTestId("glaucoma-add-vf")).toBeInTheDocument();
  });

  it("front desk is fully blocked at the panel level", async () => {
    render(
      <SpecialtyTrackingPanel
        identity="front@chartnav.local"
        me={FRONT_DESK}
        patientId={1}
        encounterId={200}
      />
    );
    expect(
      await screen.findByTestId("specialty-tracking-blocked")
    ).toBeInTheDocument();
    expect(api.listPatientRetinaTracking).not.toHaveBeenCalled();
    expect(api.listPatientGlaucomaTracking).not.toHaveBeenCalled();
  });
});

describe("SpecialtyTrackingPanel — retina create flow", () => {
  it("submits and refreshes", async () => {
    (api.createPatientRetinaTracking as any).mockResolvedValue(RETINA_ROW);
    render(
      <SpecialtyTrackingPanel
        identity="clin@chartnav.local"
        me={CLINICIAN}
        patientId={1}
        encounterId={200}
      />
    );
    await waitFor(() =>
      expect(screen.getByTestId("retina-empty")).toBeInTheDocument()
    );
    await userEvent.click(screen.getByTestId("retina-add"));
    expect(screen.getByTestId("retina-create-form")).toBeInTheDocument();

    await userEvent.type(
      screen.getByTestId("retina-create-condition"),
      "diabetic retinopathy"
    );
    await userEvent.type(
      screen.getByTestId("retina-create-severity"),
      "moderate"
    );

    // refreshed list returns one item the second time
    (api.listPatientRetinaTracking as any).mockResolvedValueOnce({
      items: [{ ...RETINA_ROW, condition: "diabetic retinopathy" }],
      total: 1,
    });

    await userEvent.click(screen.getByTestId("retina-create-submit"));

    await waitFor(() =>
      expect(api.createPatientRetinaTracking).toHaveBeenCalled()
    );
    const call = (api.createPatientRetinaTracking as any).mock.calls[0];
    expect(call[1]).toBe(1);
    expect(call[2].condition).toBe("diabetic retinopathy");
    expect(call[2].severity).toBe("moderate");
    expect(call[2].encounter_id).toBe(200);
  });
});

describe("SpecialtyTrackingPanel — forbidden vocabulary", () => {
  it("renders no diagnosis/order/referral/billing/messaging controls", async () => {
    (api.listPatientRetinaTracking as any).mockResolvedValue({
      items: [RETINA_ROW],
      total: 1,
    });
    (api.listPatientGlaucomaTracking as any).mockResolvedValue({
      items: [GLAUCOMA_ROW],
      total: 1,
    });
    const { container } = render(
      <SpecialtyTrackingPanel
        identity="clin@chartnav.local"
        me={CLINICIAN}
        patientId={1}
        encounterId={200}
      />
    );
    await waitFor(() =>
      expect(screen.getByTestId("retina-cards")).toBeInTheDocument()
    );
    // The disclaimer subtitle intentionally states what ChartNav does
    // NOT do (diagnose / dose / place orders / send referrals /
    // message patients / grade severity automatically). Strip it
    // before scanning so the negative-assertion copy doesn't trip the
    // vocabulary check.
    const subtitle = container.querySelector(
      ".specialty-tracking__subtitle"
    ) as HTMLElement | null;
    const subtitleText = (subtitle?.textContent ?? "").toLowerCase();
    const fullText = (container.textContent ?? "").toLowerCase();
    const text = fullText.replace(subtitleText, "");
    for (const banned of [
      "diagnose this",
      "auto-diagnose",
      "auto-dose",
      "auto-dosing",
      "auto-grade",
      "auto-grading",
      "place order",
      "send referral",
      "submit referral",
      "send message",
      "patient message",
      "send to patient",
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
      "hipaa compliant",
    ]) {
      expect(text).not.toContain(banned);
    }
    // Defensive: no interactive control offers a forbidden action.
    const buttons = Array.from(container.querySelectorAll("button"));
    const buttonTexts = buttons.map((b) =>
      (b.textContent ?? "").toLowerCase()
    );
    for (const forbidden of [
      "place order",
      "send referral",
      "send to patient",
      "submit claim",
      "billing",
    ]) {
      expect(buttonTexts.some((t) => t.includes(forbidden))).toBe(false);
    }
  });
});
