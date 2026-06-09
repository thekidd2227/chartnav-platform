// Phase 77 — Retina Visit Packet panel tests.

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../features/retina-summary/retinaSummaryApi", () => ({
  getRetinaVisitPacket: vi.fn(),
  getRetinaVisitSummary: vi.fn(),
}));

import { getRetinaVisitPacket } from "../features/retina-summary/retinaSummaryApi";
import { RetinaVisitPacketPanel } from "../features/retina-summary/RetinaVisitPacketPanel";
import type { RetinaVisitPacket } from "../features/retina-summary/retinaPacketTypes";

const SAFETY_KEYS = [
  "not_certified_ehr",
  "not_ehr_replacement",
  "no_autonomous_diagnosis",
  "no_autonomous_image_interpretation",
  "no_autonomous_billing_or_coding",
  "no_autonomous_signing",
  "provider_review_required",
  "no_real_phi",
  "metadata_only_audit_trail",
] as const;

function emptyPacket(over: Partial<RetinaVisitPacket> = {}): RetinaVisitPacket {
  return {
    schema_version: "chartnav.retina_visit_packet/1.0",
    generated_at: "2026-06-09T08:00:00Z",
    demo_mode: true,
    encounter: {
      id: 1,
      patient_id: 1,
      patient_identifier: "PT-1001",
      patient_name: "Morgan Lee",
      organization_id: 1,
      status: "in_progress",
      started_at: "2026-05-19T06:00:00Z",
    },
    intake: { count: 0, latest_id: null, latest_status: null },
    visit_draft: { count: 0, latest_id: null, latest_status: null },
    fundus: { count: 0, latest_id: null, latest_status: null },
    review_sign_lock: {
      vitals_signed: false,
      visit_draft_signed: false,
      fundus_signed: false,
      all_signed: false,
      blockers: [],
    },
    evidence_timeline: [],
    artifact_hashes: [
      { section: "intake", algorithm: "sha256", hash: "a".repeat(64), hash_short: "a".repeat(12) },
      { section: "visit_draft", algorithm: "sha256", hash: "b".repeat(64), hash_short: "b".repeat(12) },
      { section: "fundus", algorithm: "sha256", hash: "c".repeat(64), hash_short: "c".repeat(12) },
    ],
    role_capabilities: {
      role: "clinician",
      can_review: true,
      can_sign: true,
      can_create_intake: true,
      explainer: "Clinician can review and sign clinical artifacts.",
    },
    safety_boundaries: SAFETY_KEYS.map((k) => ({
      key: k,
      asserted: true,
      statement: `Boundary statement for ${k}.`,
    })),
    audit_disclosure:
      "ChartNav records metadata-only audit events: who created, reviewed, and signed each artifact, and when. The audit trail does not store clinical free text.",
    ...over,
  };
}

function sealedPacket(): RetinaVisitPacket {
  return emptyPacket({
    intake: { count: 1, latest_id: 5, latest_status: "signed" },
    visit_draft: { count: 1, latest_id: 3, latest_status: "finalized" },
    fundus: { count: 1, latest_id: 7, latest_status: "signed" },
    review_sign_lock: {
      vitals_signed: true,
      visit_draft_signed: true,
      fundus_signed: true,
      all_signed: true,
      blockers: [],
    },
    evidence_timeline: [
      {
        artifact_type: "vitals_workup",
        event_type: "signed",
        timestamp: "2026-05-19T07:00:00Z",
        ref_id: 5,
        actor_display_name: "Casey Clinician",
        actor_role: "clinician",
      },
    ],
  });
}

beforeEach(() => {
  vi.mocked(getRetinaVisitPacket).mockReset();
});

describe("RetinaVisitPacketPanel — base render", () => {
  it("renders header, banner, and schema version before any packet is built", () => {
    render(<RetinaVisitPacketPanel encounterId={1} />);
    expect(
      screen.getByTestId("retina-visit-packet-panel"),
    ).toBeInTheDocument();
    expect(screen.getByTestId("retina-packet-schema-version").textContent).toMatch(
      /chartnav\.retina_visit_packet\/1\.0/,
    );
    expect(screen.getByTestId("retina-packet-banner").textContent).toMatch(
      /metadata only/i,
    );
    // Copy / download buttons start disabled until packet is built.
    expect(screen.getByTestId("retina-packet-copy-btn")).toBeDisabled();
    expect(screen.getByTestId("retina-packet-download-btn")).toBeDisabled();
  });

  it("Build button fetches and shows artifact counts + evidence count + sealed state", async () => {
    vi.mocked(getRetinaVisitPacket).mockResolvedValueOnce(sealedPacket());
    render(<RetinaVisitPacketPanel encounterId={1} />);
    await userEvent.click(screen.getByTestId("retina-packet-build-btn"));
    await waitFor(() =>
      expect(screen.getByTestId("retina-packet-meta")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("retina-packet-count-intake").textContent).toBe("1");
    expect(screen.getByTestId("retina-packet-count-visit-draft").textContent).toBe("1");
    expect(screen.getByTestId("retina-packet-count-fundus").textContent).toBe("1");
    expect(screen.getByTestId("retina-packet-evidence-count").textContent).toBe("1");
    expect(screen.getByTestId("retina-packet-sealed-state").textContent).toMatch(
      /All Signed/i,
    );
  });

  it("shows Pending Signatures when not all artifacts are signed", async () => {
    vi.mocked(getRetinaVisitPacket).mockResolvedValueOnce(emptyPacket());
    render(<RetinaVisitPacketPanel encounterId={1} />);
    await userEvent.click(screen.getByTestId("retina-packet-build-btn"));
    await waitFor(() =>
      expect(screen.getByTestId("retina-packet-sealed-state")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("retina-packet-sealed-state").textContent).toMatch(
      /Pending Signatures/i,
    );
  });
});

describe("RetinaVisitPacketPanel — safety boundaries", () => {
  it("renders all 9 safety boundary statements", async () => {
    vi.mocked(getRetinaVisitPacket).mockResolvedValueOnce(sealedPacket());
    render(<RetinaVisitPacketPanel encounterId={1} />);
    await userEvent.click(screen.getByTestId("retina-packet-build-btn"));
    await waitFor(() =>
      expect(
        screen.getByTestId("retina-packet-safety-boundaries"),
      ).toBeInTheDocument(),
    );
    for (const k of SAFETY_KEYS) {
      expect(
        screen.getByTestId(`retina-packet-boundary-${k}`),
      ).toBeInTheDocument();
    }
  });
});

describe("RetinaVisitPacketPanel — artifact hashes", () => {
  it("renders the three section hashes", async () => {
    vi.mocked(getRetinaVisitPacket).mockResolvedValueOnce(sealedPacket());
    render(<RetinaVisitPacketPanel encounterId={1} />);
    await userEvent.click(screen.getByTestId("retina-packet-build-btn"));
    await waitFor(() =>
      expect(screen.getByTestId("retina-packet-hashes")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("retina-packet-hash-intake")).toBeInTheDocument();
    expect(
      screen.getByTestId("retina-packet-hash-visit_draft"),
    ).toBeInTheDocument();
    expect(screen.getByTestId("retina-packet-hash-fundus")).toBeInTheDocument();
  });
});

describe("RetinaVisitPacketPanel — preview + copy + download", () => {
  it("preview opens after build and shows the packet JSON", async () => {
    vi.mocked(getRetinaVisitPacket).mockResolvedValueOnce(sealedPacket());
    render(<RetinaVisitPacketPanel encounterId={1} />);
    await userEvent.click(screen.getByTestId("retina-packet-build-btn"));
    await waitFor(() =>
      expect(
        screen.getByTestId("retina-packet-preview-details"),
      ).toBeInTheDocument(),
    );
    const pre = screen.getByTestId("retina-packet-preview");
    expect(pre.textContent).toMatch(/chartnav\.retina_visit_packet\/1\.0/);
    expect(pre.textContent).toMatch(/Morgan Lee/);
  });

  it("Copy button writes JSON to clipboard and flips to Copied", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      value: { writeText },
      configurable: true,
    });
    vi.mocked(getRetinaVisitPacket).mockResolvedValueOnce(sealedPacket());
    render(<RetinaVisitPacketPanel encounterId={1} />);
    await userEvent.click(screen.getByTestId("retina-packet-build-btn"));
    await waitFor(() =>
      expect(screen.getByTestId("retina-packet-copy-btn")).not.toBeDisabled(),
    );
    await userEvent.click(screen.getByTestId("retina-packet-copy-btn"));
    await waitFor(() =>
      expect(screen.getByTestId("retina-packet-copy-btn").textContent).toMatch(
        /Copied/,
      ),
    );
    expect(writeText).toHaveBeenCalledOnce();
    const arg = (writeText.mock.calls[0]?.[0] as string) ?? "";
    expect(arg).toMatch(/chartnav\.retina_visit_packet\/1\.0/);
  });

  it("Download button creates an anchor with the packet filename", async () => {
    vi.mocked(getRetinaVisitPacket).mockResolvedValueOnce(sealedPacket());
    const createObjectURL = vi.fn().mockReturnValue("blob:mock");
    const revokeObjectURL = vi.fn();
    Object.defineProperty(URL, "createObjectURL", {
      value: createObjectURL,
      configurable: true,
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      value: revokeObjectURL,
      configurable: true,
    });
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click");

    render(<RetinaVisitPacketPanel encounterId={42} />);
    await userEvent.click(screen.getByTestId("retina-packet-build-btn"));
    await waitFor(() =>
      expect(
        screen.getByTestId("retina-packet-download-btn"),
      ).not.toBeDisabled(),
    );
    await userEvent.click(screen.getByTestId("retina-packet-download-btn"));
    expect(createObjectURL).toHaveBeenCalledOnce();
    expect(clickSpy).toHaveBeenCalledOnce();
    expect(revokeObjectURL).toHaveBeenCalledOnce();
    clickSpy.mockRestore();
  });
});

describe("RetinaVisitPacketPanel — error + safety", () => {
  it("surfaces API errors in the error banner without crashing", async () => {
    vi.mocked(getRetinaVisitPacket).mockRejectedValueOnce(
      new Error("HTTP 503 service unavailable"),
    );
    render(<RetinaVisitPacketPanel encounterId={1} />);
    await userEvent.click(screen.getByTestId("retina-packet-build-btn"));
    await waitFor(() =>
      expect(screen.getByTestId("retina-packet-error")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("retina-packet-error").textContent).toMatch(
      /HTTP 503/,
    );
  });

  it("does NOT render forbidden clinical-text fragments", async () => {
    vi.mocked(getRetinaVisitPacket).mockResolvedValueOnce(sealedPacket());
    render(<RetinaVisitPacketPanel encounterId={1} />);
    await userEvent.click(screen.getByTestId("retina-packet-build-btn"));
    await waitFor(() =>
      expect(screen.getByTestId("retina-packet-preview")).toBeInTheDocument(),
    );
    const body = (document.body.textContent ?? "").toLowerCase();
    for (const forbidden of [
      "transcript_text",
      "draft_note",
      "findings_json",
      "drawing_json",
      "technician_notes",
    ]) {
      expect(body, `forbidden phrase: ${forbidden}`).not.toContain(forbidden);
    }
  });
});
