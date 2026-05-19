import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../api", async () => {
  const actual = await vi.importActual<typeof import("../api")>("../api");
  return {
    ...actual,
    listProviderActionItems: vi.fn(),
    generateProviderActionItems: vi.fn(),
    acceptProviderActionItem: vi.fn(),
    dismissProviderActionItem: vi.fn(),
    completeProviderActionItem: vi.fn(),
  };
});

import {
  ApiError,
  ProviderActionItem,
  acceptProviderActionItem,
  completeProviderActionItem,
  dismissProviderActionItem,
  generateProviderActionItems,
  listProviderActionItems,
} from "../api";
import { ProviderActionItemsPanel } from "../ProviderActionItemsPanel";

const mockedList = vi.mocked(listProviderActionItems);
const mockedGenerate = vi.mocked(generateProviderActionItems);
const mockedAccept = vi.mocked(acceptProviderActionItem);
const mockedDismiss = vi.mocked(dismissProviderActionItem);
const mockedComplete = vi.mocked(completeProviderActionItem);

function makeItem(overrides: Partial<ProviderActionItem> = {}): ProviderActionItem {
  return {
    id: 1001,
    organization_id: 1,
    patient_id: 7,
    encounter_id: 42,
    source_type: "scribe_session",
    source_id: 50,
    action_type: "review_scribe_session",
    priority: "medium",
    title: "Review scribe session #50",
    reason: "A scribe session is ready for provider review.",
    status: "suggested",
    created_by_system: true,
    generated_batch_id: "batch-abc",
    accepted_by_user_id: null,
    dismissed_by_user_id: null,
    completed_by_user_id: null,
    accepted_at: null,
    dismissed_at: null,
    completed_at: null,
    created_at: "2026-05-05T18:00:00+00:00",
    updated_at: "2026-05-05T18:00:00+00:00",
    is_terminal: false,
    ...overrides,
  };
}

function renderPanel() {
  return render(
    <ProviderActionItemsPanel
      identity="clin@chartnav.local"
      patientId={7}
      encounterId={42}
    />
  );
}

describe("ProviderActionItemsPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the provider-review banner copy", async () => {
    mockedList.mockResolvedValueOnce({ items: [], total: 0 });
    renderPanel();
    const banner = await screen.findByTestId(
      "provider-action-items-banner-copy"
    );
    expect(banner).toHaveTextContent(/review required/i);
    expect(banner).toHaveTextContent(/does not create orders/i);
    expect(banner).toHaveTextContent(/send referrals/i);
    expect(banner).toHaveTextContent(/message patients/i);
    expect(banner).toHaveTextContent(/take action automatically/i);
  });

  it("auto-loads on mount and shows the empty state when there are no items", async () => {
    mockedList.mockResolvedValueOnce({ items: [], total: 0 });
    renderPanel();
    await waitFor(() => {
      expect(mockedList).toHaveBeenCalledWith(
        "clin@chartnav.local",
        7,
        {}
      );
    });
    expect(
      await screen.findByTestId("provider-action-items-empty")
    ).toHaveTextContent(/no action items match/i);
  });

  it("Generate button calls the API and refreshes the list", async () => {
    mockedList.mockResolvedValueOnce({ items: [], total: 0 });
    mockedGenerate.mockResolvedValueOnce({
      batch_id: "batch-abc",
      generated_count: 2,
      created_count: 2,
      reused_count: 0,
      items: [makeItem({ id: 1001 }), makeItem({ id: 1002 })],
    });
    mockedList.mockResolvedValueOnce({
      items: [makeItem({ id: 1001 }), makeItem({ id: 1002 })],
      total: 2,
    });

    renderPanel();
    const user = userEvent.setup();
    await screen.findByTestId("provider-action-items-empty");

    await user.click(screen.getByTestId("provider-action-items-generate"));

    await waitFor(() => {
      expect(mockedGenerate).toHaveBeenCalledWith("clin@chartnav.local", 7);
    });
    const banner = await screen.findByTestId("provider-action-items-banner");
    expect(banner).toHaveTextContent(/Generated 2 new \(reused 0\)/);
  });

  it("renders the list of action items with title, priority, status, reason", async () => {
    mockedList.mockResolvedValueOnce({
      items: [
        makeItem({
          id: 1001,
          priority: "high",
          status: "suggested",
          title: "Review chart language for retinal detachment",
          reason: "Chart text contains language that may need provider review.",
        }),
      ],
      total: 1,
    });
    renderPanel();

    expect(
      await screen.findByTestId("provider-action-item-1001-title")
    ).toHaveTextContent("Review chart language for retinal detachment");
    expect(
      screen.getByTestId("provider-action-item-1001-priority")
    ).toHaveTextContent("High");
    expect(
      screen.getByTestId("provider-action-item-1001-status")
    ).toHaveTextContent("Suggested");
    expect(
      screen.getByTestId("provider-action-item-1001-reason")
    ).toHaveTextContent(/Chart text contains language/);
  });

  it("filter dropdowns issue list calls with the chosen filters", async () => {
    mockedList.mockResolvedValueOnce({ items: [], total: 0 });
    mockedList.mockResolvedValueOnce({ items: [], total: 0 });
    renderPanel();
    await screen.findByTestId("provider-action-items-empty");

    fireEvent.change(
      screen.getByTestId("provider-action-items-filter-status"),
      { target: { value: "accepted" } }
    );

    await waitFor(() => {
      expect(mockedList).toHaveBeenLastCalledWith(
        "clin@chartnav.local",
        7,
        { status: "accepted" }
      );
    });
  });

  it("suggested item shows Accept + Dismiss only", async () => {
    mockedList.mockResolvedValueOnce({
      items: [makeItem({ id: 1001, status: "suggested" })],
      total: 1,
    });
    renderPanel();
    await screen.findByTestId("provider-action-item-1001");
    expect(
      screen.getByTestId("provider-action-item-1001-accept")
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("provider-action-item-1001-dismiss")
    ).toBeInTheDocument();
    expect(
      screen.queryByTestId("provider-action-item-1001-complete")
    ).not.toBeInTheDocument();
    expect(
      screen.queryByTestId("provider-action-item-1001-readonly")
    ).not.toBeInTheDocument();
  });

  it("accepted item shows Complete + Dismiss only", async () => {
    mockedList.mockResolvedValueOnce({
      items: [makeItem({ id: 1001, status: "accepted" })],
      total: 1,
    });
    renderPanel();
    await screen.findByTestId("provider-action-item-1001");
    expect(
      screen.getByTestId("provider-action-item-1001-complete")
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("provider-action-item-1001-dismiss")
    ).toBeInTheDocument();
    expect(
      screen.queryByTestId("provider-action-item-1001-accept")
    ).not.toBeInTheDocument();
  });

  it("completed item is read-only", async () => {
    mockedList.mockResolvedValueOnce({
      items: [
        makeItem({
          id: 1001,
          status: "completed",
          is_terminal: true,
          completed_at: "2026-05-05T19:00:00+00:00",
        }),
      ],
      total: 1,
    });
    renderPanel();
    await screen.findByTestId("provider-action-item-1001");
    expect(
      screen.getByTestId("provider-action-item-1001-readonly")
    ).toBeInTheDocument();
    expect(
      screen.queryByTestId("provider-action-item-1001-accept")
    ).not.toBeInTheDocument();
    expect(
      screen.queryByTestId("provider-action-item-1001-complete")
    ).not.toBeInTheDocument();
    expect(
      screen.queryByTestId("provider-action-item-1001-dismiss")
    ).not.toBeInTheDocument();
  });

  it("dismissed item is read-only", async () => {
    mockedList.mockResolvedValueOnce({
      items: [
        makeItem({
          id: 1001,
          status: "dismissed",
          is_terminal: true,
          dismissed_at: "2026-05-05T19:00:00+00:00",
        }),
      ],
      total: 1,
    });
    renderPanel();
    await screen.findByTestId("provider-action-item-1001");
    expect(
      screen.getByTestId("provider-action-item-1001-readonly")
    ).toBeInTheDocument();
  });

  it("Accept button calls acceptProviderActionItem and refreshes", async () => {
    mockedList.mockResolvedValueOnce({
      items: [makeItem({ id: 1001, status: "suggested" })],
      total: 1,
    });
    mockedAccept.mockResolvedValueOnce(
      makeItem({ id: 1001, status: "accepted" })
    );
    mockedList.mockResolvedValueOnce({
      items: [makeItem({ id: 1001, status: "accepted" })],
      total: 1,
    });

    renderPanel();
    const user = userEvent.setup();
    await screen.findByTestId("provider-action-item-1001");

    await user.click(screen.getByTestId("provider-action-item-1001-accept"));

    await waitFor(() => {
      expect(mockedAccept).toHaveBeenCalledWith(
        "clin@chartnav.local",
        7,
        1001
      );
    });
  });

  it("Dismiss button calls dismissProviderActionItem", async () => {
    mockedList.mockResolvedValueOnce({
      items: [makeItem({ id: 1001 })],
      total: 1,
    });
    mockedDismiss.mockResolvedValueOnce(
      makeItem({ id: 1001, status: "dismissed", is_terminal: true })
    );
    mockedList.mockResolvedValueOnce({
      items: [makeItem({ id: 1001, status: "dismissed", is_terminal: true })],
      total: 1,
    });

    renderPanel();
    const user = userEvent.setup();
    await screen.findByTestId("provider-action-item-1001");

    await user.click(screen.getByTestId("provider-action-item-1001-dismiss"));

    await waitFor(() => {
      expect(mockedDismiss).toHaveBeenCalledWith(
        "clin@chartnav.local",
        7,
        1001
      );
    });
  });

  it("Complete button calls completeProviderActionItem", async () => {
    mockedList.mockResolvedValueOnce({
      items: [makeItem({ id: 1001, status: "accepted" })],
      total: 1,
    });
    mockedComplete.mockResolvedValueOnce(
      makeItem({ id: 1001, status: "completed", is_terminal: true })
    );
    mockedList.mockResolvedValueOnce({
      items: [makeItem({ id: 1001, status: "completed", is_terminal: true })],
      total: 1,
    });

    renderPanel();
    const user = userEvent.setup();
    await screen.findByTestId("provider-action-item-1001");

    await user.click(
      screen.getByTestId("provider-action-item-1001-complete")
    );

    await waitFor(() => {
      expect(mockedComplete).toHaveBeenCalledWith(
        "clin@chartnav.local",
        7,
        1001
      );
    });
  });

  it("API error shows a safe banner message", async () => {
    mockedList.mockResolvedValueOnce({ items: [], total: 0 });
    mockedGenerate.mockRejectedValueOnce(
      new ApiError(403, "role_forbidden", "role 'reviewer' cannot generate")
    );
    renderPanel();
    const user = userEvent.setup();
    await screen.findByTestId("provider-action-items-empty");

    await user.click(screen.getByTestId("provider-action-items-generate"));

    const banner = await screen.findByTestId("provider-action-items-banner");
    expect(banner).toHaveTextContent(/Generate failed/);
    expect(banner).toHaveTextContent(/role_forbidden/);
    expect(banner.textContent).not.toMatch(/autonomous/i);
  });

  it("renders no order/coding/referral/patient-message buttons", async () => {
    mockedList.mockResolvedValueOnce({
      items: [makeItem({ id: 1001 })],
      total: 1,
    });
    renderPanel();
    await screen.findByTestId("provider-action-item-1001");
    expect(
      screen.queryByRole("button", { name: /place order/i })
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /coding/i })
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /referral/i })
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /send to patient/i })
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /email patient/i })
    ).not.toBeInTheDocument();
  });

  it("contains no autonomous-diagnosis or external-LLM language", async () => {
    mockedList.mockResolvedValueOnce({
      items: [makeItem({ id: 1001 })],
      total: 1,
    });
    renderPanel();
    await screen.findByTestId("provider-action-item-1001");
    const root = screen.getByTestId("provider-action-items-panel");
    expect(root.textContent).not.toMatch(/autonomous/i);
    expect(root.textContent).not.toMatch(/diagnos(?:e|is|ing)/i);
    expect(root.textContent).not.toMatch(/openai|anthropic|gpt|llm/i);
  });
});
