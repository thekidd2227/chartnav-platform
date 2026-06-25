import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../api", async () => {
  const actual = await vi.importActual<typeof import("../api")>("../api");
  return {
    ...actual,
    API_URL: "http://test",
    getPatient: vi.fn(),
    patchPatient: vi.fn(),
    listPatientEncounters: vi.fn(),
    listPatientChartSections: vi.fn(),
  };
});

// PatientChart embeds the canonical EyeDiagramPanel for the retina surface
// (mainline-wins reconciliation). Stub it so this shell test stays focused
// on the chart shell; the panel has its own test (EyeDiagramPanel.test.tsx).
vi.mock("../EyeDiagramPanel", () => ({
  EyeDiagramPanel: (props: { patientId: number }) => (
    <div data-testid="eye-diagram-panel-stub" data-patient={props.patientId}>
      EyeDiagramPanel
    </div>
  ),
}));

import * as api from "../api";
import { PatientChart } from "../PatientChart";

const ME_ADMIN: api.Me = {
  user_id: 1,
  email: "admin@chartnav.local",
  full_name: "Admin",
  role: "admin",
  organization_id: 1,
};

const PATIENT_BASE: api.Patient = {
  id: 42,
  organization_id: 1,
  external_ref: null,
  patient_identifier: "PT-1001",
  first_name: "Morgan",
  last_name: "Lee",
  date_of_birth: "1962-03-14",
  sex_at_birth: "female",
  is_active: true,
  created_at: "2026-04-18 10:00:00",
  middle_name: null,
  preferred_name: null,
  display_name: null,
  pronouns: "she/her",
  gender_identity: null,
  preferred_language: "en",
  race: null,
  ethnicity: null,
  email: "morgan@example.com",
  phone: "+1-555-0100",
  address_line1: "123 Vision Way",
  address_line2: null,
  address_city: "Austin",
  address_state: "TX",
  address_postal_code: "78701",
  address_country: null,
  emergency_contact_name: "Pat Lee",
  emergency_contact_phone: "+1-555-0199",
  emergency_contact_relationship: "spouse",
  insurance_metadata: null,
  updated_at: null,
};

const ENCOUNTERS: api.Encounter[] = [
  {
    id: 9,
    organization_id: 1,
    location_id: 1,
    patient_identifier: "PT-1001",
    patient_name: "Morgan Lee",
    provider_name: "Dr. Carter",
    status: "in_progress",
    scheduled_at: null,
    started_at: null,
    completed_at: null,
    created_at: "2026-04-29 10:00:00",
  },
];

const SECTIONS: api.ChartSection[] = [
  { key: "overview", label: "Overview", status: "active", description: "Demographics" },
  { key: "encounters", label: "Encounters", status: "active", description: "All encounters" },
  { key: "allergies", label: "Allergies", status: "placeholder", description: "Allergies" },
  { key: "medications", label: "Medications", status: "placeholder", description: "Meds" },
  { key: "labs", label: "Labs", status: "placeholder", description: "Labs" },
  { key: "radiology", label: "Radiology", status: "placeholder", description: "Imaging" },
  { key: "orders", label: "Orders", status: "placeholder", description: "Orders" },
  { key: "documents", label: "Documents", status: "placeholder", description: "Docs" },
  { key: "consults", label: "Consults / H&P", status: "placeholder", description: "Consults" },
  { key: "isolation", label: "Isolation", status: "placeholder", description: "Isolation" },
  { key: "eye_diagrams", label: "Eye Diagrams", status: "active", description: "Retinal" },
];

beforeEach(() => {
  vi.mocked(api.getPatient).mockResolvedValue({ ...PATIENT_BASE });
  vi.mocked(api.listPatientEncounters).mockResolvedValue(ENCOUNTERS);
  vi.mocked(api.listPatientChartSections).mockResolvedValue({
    patient_id: 42,
    sections: SECTIONS,
  });
});

afterEach(() => {
  vi.clearAllMocks();
});

describe("PatientChart shell", () => {
  it("renders header + tabs and lands on Overview by default", async () => {
    render(
      <PatientChart
        identity="admin@chartnav.local"
        me={ME_ADMIN}
        patientId={42}
        onClose={() => {}}
      />
    );

    expect(await screen.findByTestId("patient-name")).toHaveTextContent("Morgan Lee");
    expect(screen.getByTestId("patient-mrn")).toHaveTextContent("PT-1001");
    expect(screen.getByTestId("patient-dob")).toHaveTextContent("1962-03-14");
    expect(screen.getByTestId("patient-sex")).toHaveTextContent("female");

    for (const key of [
      "overview", "encounters", "allergies", "medications", "labs",
      "radiology", "orders", "documents", "consults", "isolation", "eye_diagrams",
    ]) {
      expect(screen.getByTestId(`chart-tab-${key}`)).toBeInTheDocument();
    }

    expect(screen.getByTestId("overview-panel")).toBeInTheDocument();
    expect(screen.getByTestId("fact-email")).toHaveTextContent(
      "morgan@example.com"
    );
  });

  it("switches to Encounters tab and lists encounters", async () => {
    render(
      <PatientChart
        identity="admin@chartnav.local"
        me={ME_ADMIN}
        patientId={42}
        onClose={() => {}}
      />
    );
    await screen.findByTestId("overview-panel");
    await userEvent.click(screen.getByTestId("chart-tab-encounters"));
    expect(screen.getByTestId("encounters-panel")).toBeInTheDocument();
    expect(screen.getByTestId("enc-row-9")).toBeInTheDocument();
  });

  it("placeholder sections are honest about not being implemented", async () => {
    render(
      <PatientChart
        identity="admin@chartnav.local"
        me={ME_ADMIN}
        patientId={42}
        onClose={() => {}}
      />
    );
    await screen.findByTestId("overview-panel");
    await userEvent.click(screen.getByTestId("chart-tab-medications"));
    expect(screen.getByTestId("placeholder-medications")).toHaveTextContent(
      /Not implemented yet/i
    );
  });

  it("Eye Diagrams tab embeds the canonical EyeDiagramPanel", async () => {
    render(
      <PatientChart
        identity="admin@chartnav.local"
        me={ME_ADMIN}
        patientId={42}
        onClose={() => {}}
      />
    );
    await screen.findByTestId("overview-panel");
    await userEvent.click(screen.getByTestId("chart-tab-eye_diagrams"));
    const panel = await screen.findByTestId("eye-diagram-panel-stub");
    expect(panel).toBeInTheDocument();
    expect(panel).toHaveAttribute("data-patient", "42");
  });

  it("reviewer cannot edit overview (panel enforces its own RBAC)", async () => {
    const reviewer: api.Me = { ...ME_ADMIN, role: "reviewer" };
    render(
      <PatientChart
        identity="rev@chartnav.local"
        me={reviewer}
        patientId={42}
        onClose={() => {}}
      />
    );
    await screen.findByTestId("overview-panel");
    expect(screen.queryByTestId("overview-edit")).not.toBeInTheDocument();

    await userEvent.click(screen.getByTestId("chart-tab-eye_diagrams"));
    expect(await screen.findByTestId("eye-diagram-panel-stub")).toBeInTheDocument();
  });

  it("editing demographics calls patchPatient and re-renders Overview", async () => {
    vi.mocked(api.patchPatient).mockResolvedValue({
      ...PATIENT_BASE,
      phone: "+1-555-0202",
    });
    render(
      <PatientChart
        identity="admin@chartnav.local"
        me={ME_ADMIN}
        patientId={42}
        onClose={() => {}}
      />
    );
    await screen.findByTestId("overview-panel");
    await userEvent.click(screen.getByTestId("overview-edit"));
    expect(screen.getByTestId("overview-editor")).toBeInTheDocument();

    const phone = screen.getByTestId("field-phone");
    await userEvent.clear(phone);
    await userEvent.type(phone, "+1-555-0202");
    await userEvent.click(screen.getByTestId("overview-save"));

    await waitFor(() => {
      expect(api.patchPatient).toHaveBeenCalledWith(
        "admin@chartnav.local",
        42,
        expect.objectContaining({ phone: "+1-555-0202" })
      );
    });
    expect(await screen.findByTestId("fact-phone")).toHaveTextContent(
      "+1-555-0202"
    );
  });
});
