// Phase 78 — Anti-VEGF InjectionCommandPanel tests.

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../features/anti-vegf/antiVegfApi", () => ({
  getInjectionHistory: vi.fn(),
  recordInjection: vi.fn(),
  getReadinessQueue: vi.fn(),
}));

import { getInjectionHistory } from "../features/anti-vegf/antiVegfApi";
import { InjectionCommandPanel } from "../features/anti-vegf/InjectionCommandPanel";
import type {
  AntiVegfHistory,
  AntiVegfInjection,
} from "../features/anti-vegf/antiVegfTypes";

function inj(over: Partial<AntiVegfInjection> = {}): AntiVegfInjection {
  return {
    id: 1,
    organization_id: 1,
    patient_id: 1,
    encounter_id: 1,
    eye: "OD",
    drug_label: "anti_vegf_generic",
    injection_date: "2026-05-01",
    interval_weeks: 4,
    next_due_date: "2026-05-29",
    authorization_status: "approved",
    authorization_expires_on: "2026-12-31",
    lot_number: "DEMO-001",
    notes: null,
    created_by_user_id: 1,
    created_at: "2026-05-01T10:00:00Z",
    updated_at: "2026-05-01T10:00:00Z",
    ...over,
  };
}

function emptyHistory(): AntiVegfHistory {
  return {
    patient_id: 1,
    patient_identifier: "PT-1001",
    patient_name: "Morgan Lee",
    total_count: 0,
    od_count: 0,
    os_count: 0,
    od_history: [],
    os_history: [],
    latest_od: null,
    latest_os: null,
    bilateral: false,
  };
}

function bilateralHistory(): AntiVegfHistory {
  const od1 = inj({ id: 1, eye: "OD", injection_date: "2026-04-01", lot_number: "DEMO-001" });
  const od2 = inj({ id: 2, eye: "OD", injection_date: "2026-05-01", lot_number: "DEMO-002" });
  const os1 = inj({
    id: 3,
    eye: "OS",
    injection_date: "2026-04-15",
    drug_label: "anti_vegf_biosimilar",
    authorization_status: "pending",
    lot_number: "DEMO-003",
  });
  // Sorted DESC by date.
  return {
    patient_id: 1,
    patient_identifier: "PT-1001",
    patient_name: "Morgan Lee",
    total_count: 3,
    od_count: 2,
    os_count: 1,
    od_history: [od2, od1],
    os_history: [os1],
    latest_od: od2,
    latest_os: os1,
    bilateral: true,
  };
}

beforeEach(() => {
  vi.mocked(getInjectionHistory).mockReset();
});

describe("InjectionCommandPanel — baseline", () => {
  it("renders the patient header and bilateral flag from history", async () => {
    vi.mocked(getInjectionHistory).mockResolvedValueOnce(bilateralHistory());
    render(<InjectionCommandPanel patientId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("anti-vegf-patient-meta"),
      ).toBeInTheDocument(),
    );
    const meta = screen.getByTestId("anti-vegf-patient-meta");
    expect(meta.textContent).toMatch(/Morgan Lee/);
    expect(meta.textContent).toMatch(/PT-1001/);
    expect(
      screen.getByTestId("anti-vegf-bilateral-flag").textContent,
    ).toMatch(/Bilateral history/i);
  });

  it("renders separate OD and OS columns with long-form labels", async () => {
    vi.mocked(getInjectionHistory).mockResolvedValueOnce(bilateralHistory());
    render(<InjectionCommandPanel patientId={1} />);
    await waitFor(() =>
      expect(screen.getByTestId("anti-vegf-eye-column-OD")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("anti-vegf-eye-column-OD").textContent).toMatch(
      /OD · Right Eye/,
    );
    expect(screen.getByTestId("anti-vegf-eye-column-OS").textContent).toMatch(
      /OS · Left Eye/,
    );
  });

  it("shows empty-state hint per eye when no history", async () => {
    vi.mocked(getInjectionHistory).mockResolvedValueOnce(emptyHistory());
    render(<InjectionCommandPanel patientId={1} />);
    await waitFor(() =>
      expect(screen.getByTestId("anti-vegf-OD-empty")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("anti-vegf-OD-empty").textContent).toMatch(
      /No injection history recorded for OD/,
    );
    expect(screen.getByTestId("anti-vegf-OS-empty")).toBeInTheDocument();
    expect(
      screen.getByTestId("anti-vegf-bilateral-flag").textContent,
    ).toMatch(/Unilateral history/i);
  });
});

describe("InjectionCommandPanel — readiness chip + auth badge", () => {
  it("renders auth-pending readiness chip when latest record is pending auth", async () => {
    vi.mocked(getInjectionHistory).mockResolvedValueOnce(bilateralHistory());
    render(<InjectionCommandPanel patientId={1} />);
    await waitFor(() =>
      expect(screen.getByTestId("anti-vegf-OS-readiness-chip")).toBeInTheDocument(),
    );
    // OS in bilateralHistory has authorization_status="pending" → chip
    expect(
      screen.getByTestId("anti-vegf-OS-readiness-chip").textContent,
    ).toMatch(/Auth pending/i);
  });

  it("renders auth-expired chip when latest record has expired auth", async () => {
    const h = bilateralHistory();
    h.latest_od = { ...h.latest_od!, authorization_status: "expired" };
    vi.mocked(getInjectionHistory).mockResolvedValueOnce(h);
    render(<InjectionCommandPanel patientId={1} />);
    await waitFor(() =>
      expect(screen.getByTestId("anti-vegf-OD-readiness-chip")).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("anti-vegf-OD-readiness-chip").textContent,
    ).toMatch(/Auth expired/i);
  });

  it("renders Auth badge text in latest panel using long-form label", async () => {
    vi.mocked(getInjectionHistory).mockResolvedValueOnce(bilateralHistory());
    render(<InjectionCommandPanel patientId={1} />);
    await waitFor(() =>
      expect(screen.getByTestId("anti-vegf-OD-auth-badge")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("anti-vegf-OD-auth-badge").textContent).toMatch(
      /Approved/i,
    );
    expect(screen.getByTestId("anti-vegf-OS-auth-badge").textContent).toMatch(
      /Pending/i,
    );
  });
});

describe("InjectionCommandPanel — lot + interval + history", () => {
  it("renders lot number, interval, and next due date", async () => {
    vi.mocked(getInjectionHistory).mockResolvedValueOnce(bilateralHistory());
    render(<InjectionCommandPanel patientId={1} />);
    await waitFor(() =>
      expect(screen.getByTestId("anti-vegf-OD-latest")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("anti-vegf-OD-lot").textContent).toBe("DEMO-002");
    expect(screen.getByTestId("anti-vegf-OD-interval").textContent).toMatch(
      /every 4 weeks/,
    );
    expect(screen.getByTestId("anti-vegf-OD-next-due").textContent).toBe(
      "2026-05-29",
    );
  });

  it("renders earlier-injections list when more than 1 record on an eye", async () => {
    vi.mocked(getInjectionHistory).mockResolvedValueOnce(bilateralHistory());
    render(<InjectionCommandPanel patientId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("anti-vegf-OD-history-list"),
      ).toBeInTheDocument(),
    );
    // Earlier OD record (id=1) appears in the secondary list
    expect(
      screen.getByTestId("anti-vegf-OD-history-item-1"),
    ).toBeInTheDocument();
    // Only 1 OS record → OS has no secondary list
    expect(
      screen.queryByTestId("anti-vegf-OS-history-list"),
    ).toBeNull();
  });
});

describe("InjectionCommandPanel — interaction + safety", () => {
  it("refresh button refetches history", async () => {
    vi.mocked(getInjectionHistory)
      .mockResolvedValueOnce(emptyHistory())
      .mockResolvedValueOnce(bilateralHistory());
    render(<InjectionCommandPanel patientId={1} />);
    await waitFor(() =>
      expect(screen.getByTestId("anti-vegf-OD-empty")).toBeInTheDocument(),
    );
    await userEvent.click(screen.getByTestId("anti-vegf-refresh-btn"));
    await waitFor(() =>
      expect(screen.getByTestId("anti-vegf-OD-latest")).toBeInTheDocument(),
    );
    expect(getInjectionHistory).toHaveBeenCalledTimes(2);
  });

  it("surfaces API errors in the error banner", async () => {
    vi.mocked(getInjectionHistory).mockRejectedValueOnce(
      new Error("HTTP 503 service unavailable"),
    );
    render(<InjectionCommandPanel patientId={1} />);
    await waitFor(() =>
      expect(screen.getByTestId("anti-vegf-error")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("anti-vegf-error").textContent).toMatch(
      /HTTP 503/,
    );
  });

  it("renders the explicit boundary note (no recommendation / no image interpretation)", async () => {
    vi.mocked(getInjectionHistory).mockResolvedValueOnce(bilateralHistory());
    render(<InjectionCommandPanel patientId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("anti-vegf-boundary-note"),
      ).toBeInTheDocument(),
    );
    const note = screen.getByTestId("anti-vegf-boundary-note");
    expect(note.textContent).toMatch(/does not interpret/i);
    expect(note.textContent).toMatch(/does not choose a drug/i);
    expect(note.textContent).toMatch(/provider-entered/i);
  });

  it("does NOT render any forbidden positive clinical claim phrases", async () => {
    vi.mocked(getInjectionHistory).mockResolvedValueOnce(bilateralHistory());
    render(<InjectionCommandPanel patientId={1} />);
    await waitFor(() =>
      expect(screen.getByTestId("anti-vegf-OD-latest")).toBeInTheDocument(),
    );
    const body = (document.body.textContent ?? "").toLowerCase();
    for (const forbidden of [
      "diagnosis confirmed",
      "treatment recommended",
      "order placed",
      "automatic coding",
      "billing code",
      "patient message sent",
      "guaranteed approval",
      "openai-powered",
      "autonomous documentation",
      "ai writes the note",
    ]) {
      expect(body, `forbidden phrase: ${forbidden}`).not.toContain(forbidden);
    }
  });
});
