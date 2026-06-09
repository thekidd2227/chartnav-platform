// Phase 81 — Provider Action Item Queue tests.

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../features/action-queue/actionQueueApi", () => ({
  getProviderActionQueue: vi.fn(),
}));

import { getProviderActionQueue } from "../features/action-queue/actionQueueApi";
import { ProviderActionItemQueue } from "../features/action-queue/ProviderActionItemQueue";
import type {
  ActionQueueItem,
  ProviderActionQueue,
} from "../features/action-queue/actionQueueTypes";

function item(over: Partial<ActionQueueItem> = {}): ActionQueueItem {
  return {
    item_id: "anti_vegf:injection_due_today:1",
    patient_id: 1,
    patient_identifier: "PT-1001",
    patient_name: "Morgan Lee",
    encounter_id: 1,
    laterality: "OD",
    specialty_source: "anti_vegf",
    category: "injection_due_today",
    label: "Injection due today",
    detail:
      "Provider-entered cadence for OD: last injection 2026-05-12, next due 2026-06-09, authorization approved.",
    status: "due_today",
    priority_bucket: "same_day",
    source_artifact_id: 1,
    created_at: "2026-05-12T10:00:00Z",
    due_at: "2026-06-09",
    insufficient_data: false,
    requires_provider_review: true,
    ...over,
  };
}

function emptyQueue(): ProviderActionQueue {
  return {
    generated_at: "2026-06-09T14:00:00Z",
    organization_id: 1,
    demo_mode: true,
    buckets: {
      same_day: [],
      this_week: [],
      routine: [],
      informational: [],
    },
    totals: { same_day: 0, this_week: 0, routine: 0, informational: 0 },
    total_items: 0,
    sources_present: [],
    disclosure:
      "Workflow queue from provider-entered data. Bucket assignment is a documented deterministic rule — not an autonomous urgency decision. ChartNav does not diagnose, does not recommend treatment or surgery, and does not interpret images. Provider review required for every item.",
  };
}

function richQueue(): ProviderActionQueue {
  const sameDay = item();
  const thisWeek = item({
    item_id: "cataract:preop_signals_incomplete:3",
    laterality: "OS",
    specialty_source: "cataract",
    category: "preop_signals_incomplete",
    label: "Pre-op signals incomplete for planned surgery",
    detail:
      "Surgery planned 2026-08-01 for OS; open signals: biometry not reviewed, consent in_progress.",
    status: "incomplete",
    priority_bucket: "this_week",
    source_artifact_id: 3,
    due_at: "2026-08-01",
    insufficient_data: true,
  });
  const routine = item({
    item_id: "signed_lock:fundus_unsigned:7",
    laterality: "OD",
    specialty_source: "signed_lock",
    category: "fundus_unsigned",
    label: "Fundus chart awaiting provider signature",
    detail:
      "Fundus chart #7 (OD) is draft and has not been signed. Provider review and signature required.",
    status: "draft",
    priority_bucket: "routine",
    source_artifact_id: 7,
    due_at: null,
  });
  const informational = item({
    item_id: "glaucoma:data_incomplete:1",
    laterality: "OU",
    specialty_source: "glaucoma",
    category: "glaucoma_data_incomplete",
    label: "IOP on file without VF / OCT RNFL metadata",
    detail:
      "IOP measurements exist but no visual-field or OCT RNFL study metadata is on file.",
    status: "insufficient_data",
    priority_bucket: "informational",
    source_artifact_id: null,
    due_at: null,
    insufficient_data: true,
  });
  return {
    ...emptyQueue(),
    buckets: {
      same_day: [sameDay],
      this_week: [thisWeek],
      routine: [routine],
      informational: [informational],
    },
    totals: { same_day: 1, this_week: 1, routine: 1, informational: 1 },
    total_items: 4,
    sources_present: ["anti_vegf", "cataract", "glaucoma", "signed_lock"],
  };
}

beforeEach(() => {
  vi.mocked(getProviderActionQueue).mockReset();
});

describe("ProviderActionItemQueue — base render", () => {
  it("renders header, boundary banner, refresh button", async () => {
    vi.mocked(getProviderActionQueue).mockResolvedValueOnce(emptyQueue());
    render(<ProviderActionItemQueue />);
    await waitFor(() =>
      expect(
        screen.getByTestId("provider-action-item-queue"),
      ).toBeInTheDocument(),
    );
    const banner = screen.getByTestId("action-queue-banner");
    expect(banner.textContent).toMatch(
      /Workflow queue from provider-entered data/i,
    );
    expect(banner.textContent).toMatch(
      /Does not diagnose or recommend treatment/i,
    );
    expect(banner.textContent).toMatch(/Provider review required/i);
    expect(screen.getByTestId("action-queue-refresh-btn")).toBeInTheDocument();
  });

  it("renders all four bucket sections with empty states when no items", async () => {
    vi.mocked(getProviderActionQueue).mockResolvedValueOnce(emptyQueue());
    render(<ProviderActionItemQueue />);
    await waitFor(() =>
      expect(
        screen.getByTestId("action-queue-bucket-same_day"),
      ).toBeInTheDocument(),
    );
    for (const bucket of [
      "same_day",
      "this_week",
      "routine",
      "informational",
    ]) {
      expect(
        screen.getByTestId(`action-queue-bucket-${bucket}`),
      ).toBeInTheDocument();
      expect(
        screen.getByTestId(`action-queue-bucket-${bucket}-empty`),
      ).toBeInTheDocument();
    }
    expect(screen.getByTestId("action-queue-total").textContent).toMatch(
      /0 open items/,
    );
  });
});

describe("ProviderActionItemQueue — items + badges", () => {
  it("places items in their bucket sections with counts", async () => {
    vi.mocked(getProviderActionQueue).mockResolvedValueOnce(richQueue());
    render(<ProviderActionItemQueue />);
    await waitFor(() =>
      expect(
        screen.getByTestId("action-item-anti_vegf:injection_due_today:1"),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("action-queue-bucket-same_day-count").textContent,
    ).toMatch(/1 item/);
    expect(
      screen.getByTestId(
        "action-item-cataract:preop_signals_incomplete:3",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("action-item-signed_lock:fundus_unsigned:7"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("action-item-glaucoma:data_incomplete:1"),
    ).toBeInTheDocument();
    expect(screen.getByTestId("action-queue-total").textContent).toMatch(
      /4 open items/,
    );
  });

  it("shows laterality badges (OD / OS / OU) on items", async () => {
    vi.mocked(getProviderActionQueue).mockResolvedValueOnce(richQueue());
    render(<ProviderActionItemQueue />);
    await waitFor(() =>
      expect(
        screen.getByTestId(
          "action-item-anti_vegf:injection_due_today:1-laterality",
        ),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId(
        "action-item-anti_vegf:injection_due_today:1-laterality",
      ).textContent,
    ).toBe("OD");
    expect(
      screen.getByTestId(
        "action-item-cataract:preop_signals_incomplete:3-laterality",
      ).textContent,
    ).toBe("OS");
    expect(
      screen.getByTestId("action-item-glaucoma:data_incomplete:1-laterality")
        .textContent,
    ).toBe("OU");
  });

  it("shows source, status, insufficient-data, and review badges", async () => {
    vi.mocked(getProviderActionQueue).mockResolvedValueOnce(richQueue());
    render(<ProviderActionItemQueue />);
    await waitFor(() =>
      expect(
        screen.getByTestId(
          "action-item-cataract:preop_signals_incomplete:3-source",
        ),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId(
        "action-item-cataract:preop_signals_incomplete:3-source",
      ).textContent,
    ).toMatch(/Cataract/);
    expect(
      screen.getByTestId(
        "action-item-cataract:preop_signals_incomplete:3-status",
      ).textContent,
    ).toMatch(/incomplete/);
    expect(
      screen.getByTestId(
        "action-item-cataract:preop_signals_incomplete:3-insufficient",
      ).textContent,
    ).toMatch(/Insufficient data/i);
    expect(
      screen.getByTestId(
        "action-item-anti_vegf:injection_due_today:1-review",
      ).textContent,
    ).toMatch(/Provider review required/i);
  });

  it("shows patient identity and sources summary", async () => {
    vi.mocked(getProviderActionQueue).mockResolvedValueOnce(richQueue());
    render(<ProviderActionItemQueue />);
    await waitFor(() =>
      expect(
        screen.getByTestId(
          "action-item-anti_vegf:injection_due_today:1-patient",
        ),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId(
        "action-item-anti_vegf:injection_due_today:1-patient",
      ).textContent,
    ).toMatch(/Morgan Lee/);
    expect(
      screen.getByTestId("action-queue-sources").textContent,
    ).toMatch(/Anti-VEGF, Cataract, Glaucoma, Signed lock/);
  });
});

describe("ProviderActionItemQueue — interaction + safety", () => {
  it("refresh button refetches the queue", async () => {
    vi.mocked(getProviderActionQueue)
      .mockResolvedValueOnce(emptyQueue())
      .mockResolvedValueOnce(richQueue());
    render(<ProviderActionItemQueue />);
    await waitFor(() =>
      expect(
        screen.getByTestId("action-queue-bucket-same_day-empty"),
      ).toBeInTheDocument(),
    );
    await userEvent.click(screen.getByTestId("action-queue-refresh-btn"));
    await waitFor(() =>
      expect(
        screen.getByTestId("action-item-anti_vegf:injection_due_today:1"),
      ).toBeInTheDocument(),
    );
    expect(getProviderActionQueue).toHaveBeenCalledTimes(2);
  });

  it("surfaces API errors in the error banner", async () => {
    vi.mocked(getProviderActionQueue).mockRejectedValueOnce(
      new Error("HTTP 503 service unavailable"),
    );
    render(<ProviderActionItemQueue />);
    await waitFor(() =>
      expect(screen.getByTestId("action-queue-error")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("action-queue-error").textContent).toMatch(
      /HTTP 503/,
    );
  });

  it("renders the deterministic-rule disclosure verbatim", async () => {
    vi.mocked(getProviderActionQueue).mockResolvedValueOnce(richQueue());
    render(<ProviderActionItemQueue />);
    await waitFor(() =>
      expect(
        screen.getByTestId("action-queue-disclosure"),
      ).toBeInTheDocument(),
    );
    const d = screen.getByTestId("action-queue-disclosure");
    expect(d.textContent).toMatch(/deterministic rule/i);
    expect(d.textContent).toMatch(/not an autonomous urgency decision/i);
    expect(d.textContent).toMatch(/does not diagnose/i);
  });

  it("does NOT render forbidden clinical-decision phrases", async () => {
    vi.mocked(getProviderActionQueue).mockResolvedValueOnce(richQueue());
    render(<ProviderActionItemQueue />);
    await waitFor(() =>
      expect(
        screen.getByTestId("action-item-anti_vegf:injection_due_today:1"),
      ).toBeInTheDocument(),
    );
    const body = (document.body.textContent ?? "").toLowerCase();
    for (const forbidden of [
      "diagnosis confirmed",
      "treatment recommended",
      "surgery recommended",
      "urgent escalation",
      "order placed",
      "billing code",
      "iol power",
      "rapid progression",
      "ai prioritized",
    ]) {
      expect(body, `forbidden phrase: ${forbidden}`).not.toContain(forbidden);
    }
  });
});
