import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../api", async () => {
  const actual = await vi.importActual<typeof import("../api")>("../api");
  return {
    ...actual,
    listPatientEyeDiagrams: vi.fn(),
    getPatientEyeDiagram: vi.fn(),
    createPatientEyeDiagram: vi.fn(),
    updatePatientEyeDiagram: vi.fn(),
    signPatientEyeDiagram: vi.fn(),
  };
});

import {
  type EyeDiagramArtifact,
  createPatientEyeDiagram,
  getPatientEyeDiagram,
  listPatientEyeDiagrams,
  signPatientEyeDiagram,
  updatePatientEyeDiagram,
} from "../api";
import { EyeDiagramPanel } from "../EyeDiagramPanel";
import {
  AUTO_SUMMARY_END,
  AUTO_SUMMARY_START,
  type DrawingDocument,
} from "../retinalAnnotations";

const mockedList = vi.mocked(listPatientEyeDiagrams);
const mockedGet = vi.mocked(getPatientEyeDiagram);
const mockedCreate = vi.mocked(createPatientEyeDiagram);
const mockedUpdate = vi.mocked(updatePatientEyeDiagram);
const mockedSign = vi.mocked(signPatientEyeDiagram);

const ARTIFACT_BASE: EyeDiagramArtifact = {
  id: 11,
  organization_id: 1,
  patient_id: 7,
  encounter_id: null,
  created_by_user_id: 2,
  artifact_type: "retinal_diagram",
  title: "Right eye exam",
  findings_text: "IOP 18 mmHg OU.",
  drawing_json: {},
  version_number: 1,
  parent_artifact_id: null,
  signed_at: null,
  signed_by_user_id: null,
  is_signed: false,
  created_at: "2026-05-04T12:00:00+00:00",
  updated_at: "2026-05-04T12:00:00+00:00",
};

const SIGNED_DRAWING: DrawingDocument = {
  schema_version: 1,
  canvas_type: "retinal_diagram",
  annotations: [
    {
      id: "a_seed_1",
      kind: "symbol",
      symbol_type: "drusen",
      eye: "OD",
      x: 0.5,
      y: 0.5,
      color: "#c1121f",
      source: "manual",
      created_at: "2026-05-04T12:00:00+00:00",
    },
  ],
};

function renderPanel() {
  return render(
    <EyeDiagramPanel
      identity="clin@chartnav.local"
      patientId={7}
      encounterId={42}
    />
  );
}

describe("EyeDiagramPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("lists artifacts for the patient", async () => {
    mockedList.mockResolvedValueOnce({
      items: [ARTIFACT_BASE, { ...ARTIFACT_BASE, id: 12, title: "Follow-up" }],
      total: 2,
    });
    renderPanel();

    await waitFor(() => {
      expect(mockedList).toHaveBeenCalledWith("clin@chartnav.local", 7);
    });
    expect(await screen.findByTestId("eye-diagram-load-11")).toBeInTheDocument();
    expect(screen.getByTestId("eye-diagram-load-12")).toBeInTheDocument();
    expect(screen.queryByTestId("eye-diagram-empty")).not.toBeInTheDocument();
  });

  it("renders empty state when no artifacts saved", async () => {
    mockedList.mockResolvedValueOnce({ items: [], total: 0 });
    renderPanel();
    expect(await screen.findByTestId("eye-diagram-empty")).toBeInTheDocument();
  });

  it("loading restores title and findings; canvas mounts", async () => {
    mockedList.mockResolvedValueOnce({ items: [ARTIFACT_BASE], total: 1 });
    mockedGet.mockResolvedValueOnce({
      ...ARTIFACT_BASE,
      drawing_json: SIGNED_DRAWING as unknown as Record<string, unknown>,
    });

    renderPanel();
    const user = userEvent.setup();
    await user.click(await screen.findByTestId("eye-diagram-load-11"));

    await waitFor(() => {
      expect(mockedGet).toHaveBeenCalledWith("clin@chartnav.local", 7, 11);
    });
    expect(screen.getByTestId<HTMLInputElement>("eye-diagram-title").value).toBe(
      "Right eye exam"
    );
    expect(
      screen.getByTestId<HTMLTextAreaElement>("eye-diagram-findings").value
    ).toBe("IOP 18 mmHg OU.");
    expect(screen.getByTestId("rdc-root")).toBeInTheDocument();
    expect(screen.queryByTestId("eye-diagram-legacy-warning")).not.toBeInTheDocument();
    // The seeded annotation should render.
    expect(screen.getByTestId("rdc-annotation-a_seed_1")).toBeInTheDocument();
  });

  it("legacy/unknown drawing_json shows a preserve-warning", async () => {
    mockedList.mockResolvedValueOnce({ items: [ARTIFACT_BASE], total: 1 });
    mockedGet.mockResolvedValueOnce({
      ...ARTIFACT_BASE,
      drawing_json: { strokes: [{ path: "M0 0" }] },
    });
    renderPanel();
    const user = userEvent.setup();
    await user.click(await screen.findByTestId("eye-diagram-load-11"));

    expect(
      await screen.findByTestId("eye-diagram-legacy-warning")
    ).toBeInTheDocument();
  });

  it("save new sends a schema_version 1 drawing payload", async () => {
    mockedList.mockResolvedValue({ items: [], total: 0 });
    mockedCreate.mockResolvedValueOnce({ ...ARTIFACT_BASE, id: 99 });

    renderPanel();
    const user = userEvent.setup();

    const titleInput = await screen.findByTestId<HTMLInputElement>(
      "eye-diagram-title"
    );
    await user.clear(titleInput);
    await user.type(titleInput, "New diagram");

    // Place a drusen symbol on the OD pane via the toolbar + click.
    await user.click(screen.getByTestId("rdc-tool-symbol-drusen"));
    fireEvent.pointerDown(screen.getByTestId("rdc-svg-OD"), {
      clientX: 100,
      clientY: 100,
      pointerId: 1,
    });

    await user.click(screen.getByTestId("eye-diagram-save-new"));

    await waitFor(() => {
      expect(mockedCreate).toHaveBeenCalledTimes(1);
    });
    const [, , payload] = mockedCreate.mock.calls[0];
    expect(payload.title).toBe("New diagram");
    expect(payload.encounter_id).toBe(42);
    const dj = payload.drawing_json as unknown as DrawingDocument;
    expect(dj.schema_version).toBe(1);
    expect(dj.canvas_type).toBe("retinal_diagram");
    expect(dj.annotations).toHaveLength(1);
    expect(dj.annotations[0]).toMatchObject({
      kind: "symbol",
      symbol_type: "drusen",
      eye: "OD",
      source: "manual",
    });
  });

  it("placing a symbol refreshes the findings auto-summary block", async () => {
    mockedList.mockResolvedValue({ items: [], total: 0 });

    renderPanel();
    const user = userEvent.setup();
    const findings = await screen.findByTestId<HTMLTextAreaElement>(
      "eye-diagram-findings"
    );
    fireEvent.change(findings, {
      target: { value: "Provider note line one." },
    });

    await user.click(screen.getByTestId("rdc-tool-symbol-flame_hemorrhage"));
    fireEvent.pointerDown(screen.getByTestId("rdc-svg-OS"), {
      clientX: 50,
      clientY: 30,
      pointerId: 1,
    });

    const updated = screen.getByTestId<HTMLTextAreaElement>(
      "eye-diagram-findings"
    ).value;
    expect(updated).toContain("Provider note line one.");
    expect(updated).toContain(AUTO_SUMMARY_START);
    expect(updated).toContain(AUTO_SUMMARY_END);
    expect(updated).toContain("OS:");
    expect(updated).toContain("flame hemorrhage");
  });

  it("sign action calls signPatientEyeDiagram and reflects signed state", async () => {
    mockedList.mockResolvedValue({ items: [ARTIFACT_BASE], total: 1 });
    mockedGet.mockResolvedValueOnce(ARTIFACT_BASE);
    mockedSign.mockResolvedValueOnce({
      ...ARTIFACT_BASE,
      is_signed: true,
      signed_at: "2026-05-04T13:00:00+00:00",
      signed_by_user_id: 2,
    });

    renderPanel();
    const user = userEvent.setup();
    await user.click(await screen.findByTestId("eye-diagram-load-11"));
    await user.click(await screen.findByTestId("eye-diagram-sign"));

    await waitFor(() => {
      expect(mockedSign).toHaveBeenCalledWith("clin@chartnav.local", 7, 11);
    });
    expect(await screen.findByTestId("eye-diagram-fork")).toBeInTheDocument();
    expect(screen.queryByTestId("eye-diagram-update")).not.toBeInTheDocument();
    expect(
      screen.getByTestId("eye-diagram-signed-warning")
    ).toBeInTheDocument();
    // Read-only canvas note appears.
    expect(screen.getByTestId("rdc-readonly-note")).toBeInTheDocument();
    // Toolbar should be hidden when canvas is read-only.
    expect(screen.queryByTestId("rdc-toolbar")).not.toBeInTheDocument();
  });

  it("editing a signed artifact creates a fork via PATCH ?fork=true", async () => {
    const signed: EyeDiagramArtifact = {
      ...ARTIFACT_BASE,
      drawing_json: SIGNED_DRAWING as unknown as Record<string, unknown>,
      is_signed: true,
      signed_at: "2026-05-04T12:30:00+00:00",
      signed_by_user_id: 2,
    };
    mockedList.mockResolvedValue({ items: [signed], total: 1 });
    mockedGet.mockResolvedValueOnce(signed);
    mockedUpdate.mockResolvedValueOnce({
      ...signed,
      id: 12,
      version_number: 2,
      parent_artifact_id: signed.id,
      is_signed: false,
      signed_at: null,
      signed_by_user_id: null,
      findings_text: "Amended.",
    });

    renderPanel();
    const user = userEvent.setup();
    await user.click(await screen.findByTestId("eye-diagram-load-11"));

    expect(
      await screen.findByTestId("eye-diagram-signed-warning")
    ).toBeInTheDocument();

    const findings = screen.getByTestId<HTMLTextAreaElement>(
      "eye-diagram-findings"
    );
    fireEvent.change(findings, { target: { value: "Amended." } });

    await user.click(await screen.findByTestId("eye-diagram-fork"));

    await waitFor(() => {
      expect(mockedUpdate).toHaveBeenCalledTimes(1);
    });
    const [, , artifactId, body, options] = mockedUpdate.mock.calls[0];
    expect(artifactId).toBe(11);
    expect(body.findings_text).toBe("Amended.");
    expect(options).toEqual({ fork: true });
    // Drawing is preserved on the fork even though we only edited findings.
    const dj = body.drawing_json as unknown as DrawingDocument;
    expect(dj.annotations).toHaveLength(1);
    expect(dj.annotations[0].id).toBe("a_seed_1");
  });
});
