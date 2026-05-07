/**
 * Phase 19 — Clinical Tabbed Workspace tests.
 *
 * The existing App tests (App.test.tsx) verify integration: the
 * `transitions` / `transition-${s}` / `detail-status` /
 * `detail-source-chip` testids still resolve in the new tabbed
 * layout (handled by back-compat testids on the new components).
 *
 * This file exercises the standalone ClinicalTabbedWorkspace
 * component:
 *
 *   - 9 tabs render with the expected labels
 *   - tab switching shows / hides the right panels
 *   - safe-claims labels are present in each tab
 *   - forbidden UI labels (place order, submit referral, send to
 *     patient, CPT, billing, etc.) appear nowhere in any tab
 *   - the Chat tab persists messages to localStorage and exports
 *     .txt / .json
 *   - the Communications tab is internal-only
 */

import { render, screen, within, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../api", async () => {
  const actual =
    await vi.importActual<typeof import("../api")>("../api");
  return {
    ...actual,
    API_URL: "http://test",
    listEncounterInputs: vi.fn().mockResolvedValue([]),
    listEncounterNotes: vi.fn().mockResolvedValue([]),
    getNoteVersion: vi
      .fn()
      .mockResolvedValue({ note: null, findings: null }),
    listPatientEyeDiagrams: vi.fn().mockResolvedValue({ items: [] }),
  };
});

import * as api from "../api";
import { ClinicalTabbedWorkspace } from "../ClinicalTabbedWorkspace";

const ENCOUNTER: api.Encounter = {
  id: 1,
  organization_id: 1,
  location_id: 1,
  patient_identifier: "PT-1001",
  patient_name: "Morgan Lee",
  provider_name: "Dr. Carter",
  status: "in_progress",
  scheduled_at: "2026-04-18 09:00:00",
  started_at: "2026-04-18 10:00:00",
  completed_at: null,
  created_at: "2026-04-18 09:00:00",
  patient_id: 42,
};

const ME: api.Me = {
  user_id: 1,
  email: "admin@chartnav.local",
  full_name: "ChartNav Admin",
  role: "admin",
  organization_id: 1,
};

function renderWorkspace(overrides: Partial<api.Encounter> = {}) {
  return render(
    <ClinicalTabbedWorkspace
      encounter={{ ...ENCOUNTER, ...overrides }}
      identity="admin@chartnav.local"
      me={ME}
      pendingStatus={null}
      onTransition={vi.fn().mockResolvedValue(undefined)}
      onSetPendingStatus={vi.fn()}
      onRefreshDetail={vi.fn()}
    />
  );
}

beforeEach(() => {
  window.localStorage.clear();
});
afterEach(() => {
  window.localStorage.clear();
});

// ---------------------------------------------------------------
// Tab inventory + switching.
// ---------------------------------------------------------------

describe("Phase 19 — Clinical tabbed workspace", () => {
  it("renders the patient header with MRN, encounter #, status, provider, location", () => {
    renderWorkspace();
    const head = screen.getByTestId("ctw-patient-header");
    expect(head).toHaveTextContent("Morgan Lee");
    expect(head).toHaveTextContent("PT-1001");
    expect(head).toHaveTextContent("Encounter #1");
    expect(head).toHaveTextContent("Dr. Carter");
    expect(head).toHaveTextContent("Location");
  });

  it("renders all 9 tabs in the tab bar", () => {
    renderWorkspace();
    const bar = screen.getByTestId("ctw-tabbar");
    const tabs = within(bar).getAllByRole("tab");
    expect(tabs).toHaveLength(9);
    const labels = tabs.map((t) => t.textContent);
    expect(labels).toEqual([
      "Overview",
      "Clinical / Ophthalmology",
      "Documentation / EMR-EHR",
      "Imaging",
      "Labs / Orders Review",
      "Calendar",
      "Communications",
      "Documents",
      "Chat",
    ]);
  });

  it("Overview is the default active tab and shows Patient snapshot / Visit summary cards", () => {
    renderWorkspace();
    const tab = screen.getByTestId("ctw-tab-overview");
    expect(tab).toHaveAttribute("aria-selected", "true");
    expect(screen.getByTestId("ctw-overview")).toBeInTheDocument();
    expect(screen.getByTestId("ctw-card-patient-snapshot")).toBeInTheDocument();
    expect(screen.getByTestId("ctw-card-visit-summary")).toBeInTheDocument();
  });

  it("clicking each tab switches the panel", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    for (const slug of [
      "clinical",
      "imaging",
      "labs-orders-review",
      "calendar",
      "communications",
      "documents",
      "chat",
    ]) {
      await user.click(screen.getByTestId(`ctw-tab-${slug}`));
      expect(screen.getByTestId(`ctw-panel-${slug}`)).toBeInTheDocument();
    }
  });

  it("preserves the legacy `detail-status`, `detail-source-chip`, `transitions` testids on the new layout", () => {
    renderWorkspace();
    expect(screen.getByTestId("detail-status")).toBeInTheDocument();
    expect(screen.getByTestId("detail-source-chip")).toBeInTheDocument();
    // The transitions row lives on the Overview tab (the default).
    expect(screen.getByTestId("transitions")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------
// Safe-claims contract — forbidden UI labels appear NOWHERE.
// ---------------------------------------------------------------

describe("Phase 19 — workspace contains no forbidden order / billing / patient-send labels on interactive elements", () => {
  // The forbidden phrases below MAY appear inside safety footnotes
  // (e.g. "ChartNav does not place lab orders" / "does not deliver
  // to a patient portal") because those paragraphs ARE the safe-
  // claims contract. Same negative-assertion pattern Phase 17B and
  // Phase 18 already use. What we forbid is the phrase appearing
  // as a button label, heading, or interactive control — those are
  // the surfaces that ship to a buyer.
  it.each([
    ["overview"],
    ["clinical"],
    ["imaging"],
    ["labs-orders-review"],
    ["calendar"],
    ["communications"],
    ["documents"],
    ["chat"],
  ])(
    "tab %s has no forbidden labels on buttons / headings / inputs",
    async (slug) => {
      const user = userEvent.setup();
      renderWorkspace();
      await user.click(screen.getByTestId(`ctw-tab-${slug}`));
      const panel = screen.getByTestId(`ctw-panel-${slug}`);
      const interactive: HTMLElement[] = [
        ...within(panel).queryAllByRole("button"),
        ...within(panel).queryAllByRole("heading"),
        ...within(panel).queryAllByRole("link"),
        ...within(panel).queryAllByRole("textbox"),
        ...within(panel).queryAllByRole("tab"),
      ];
      for (const el of interactive) {
        const t = (el.textContent || "").toLowerCase();
        for (const banned of [
          "submit order",
          "place order",
          "send referral",
          "submit referral",
          "cpt code",
          "claim submission",
          "insurance claim",
          "billing automation",
          "send to patient",
          "patient portal",
          "automated patient message",
          "auto-message",
        ]) {
          expect(
            t,
            `tab ${slug} interactive element must not contain "${banned}": ${t}`
          ).not.toContain(banned);
        }
      }
    }
  );

  it("there is no 'Billing' tab", () => {
    renderWorkspace();
    expect(screen.queryByTestId("ctw-tab-billing")).not.toBeInTheDocument();
    const labels = within(screen.getByTestId("ctw-tabbar"))
      .getAllByRole("tab")
      .map((t) => (t.textContent || "").toLowerCase());
    expect(labels).not.toContain("billing");
  });

  it("the 'Communications' surface uses negative-assertion safety language only (the words 'patient portal' and 'send to patient' may appear in negative-context safety footnotes by design)", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    await user.click(screen.getByTestId("ctw-tab-communications"));
    const panel = screen.getByTestId("ctw-panel-communications");
    const text = panel.textContent || "";
    // If the phrase "patient portal" appears, it must appear in a
    // negative-assertion context (does not deliver, no patient-send,
    // no external delivery, etc.).
    if (/patient portal/i.test(text)) {
      expect(text).toMatch(
        /(does not\s+(deliver|send|message|push|route)|no patient[- ]send|no external)/i
      );
    }
    if (/send to patient/i.test(text)) {
      expect(text).toMatch(
        /(does not\s+send|no patient[- ]send|no external|never)/i
      );
    }
  });
});

// ---------------------------------------------------------------
// Labs / Orders Review — review-only.
// ---------------------------------------------------------------

describe("Phase 19 — Labs / Orders Review tab is review-only", () => {
  it("renders only View / Mark reviewed / Add note actions (no submit/place/send buttons)", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    await user.click(screen.getByTestId("ctw-tab-labs-orders-review"));
    const panel = screen.getByTestId("ctw-panel-labs-orders-review");
    const buttons = within(panel).getAllByRole("button");
    for (const b of buttons) {
      const t = (b.textContent || "").toLowerCase();
      expect(t).toMatch(/^(view|mark reviewed|add note)$/);
    }
  });

  it("includes Lab Results / Imaging Orders / Procedure Plan / Review Notes sections", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    await user.click(screen.getByTestId("ctw-tab-labs-orders-review"));
    expect(screen.getByTestId("ctw-card-lab-results")).toBeInTheDocument();
    expect(screen.getByTestId("ctw-card-imaging-orders")).toBeInTheDocument();
    expect(screen.getByTestId("ctw-card-procedure-plan")).toBeInTheDocument();
    expect(screen.getByTestId("ctw-card-review-notes")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------
// Communications — internal only.
// ---------------------------------------------------------------

describe("Phase 19 — Communications tab is internal-only", () => {
  it("does NOT expose any patient-send / external-delivery interactive surface", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    await user.click(screen.getByTestId("ctw-tab-communications"));
    const panel = screen.getByTestId("ctw-panel-communications");
    // No button / link with a patient-send label.
    for (const banned of [
      /send to patient/i,
      /patient portal/i,
      /external message delivery/i,
      /automated patient message/i,
    ]) {
      expect(within(panel).queryByRole("button", { name: banned })).toBeNull();
      expect(within(panel).queryByRole("link", { name: banned })).toBeNull();
    }
  });

  it("adds an internal note that persists to localStorage and renders it", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    await user.click(screen.getByTestId("ctw-tab-communications"));
    const composer = screen.getByTestId("ctw-comms-composer");
    fireEvent.change(composer, {
      target: { value: "Handoff: please review the encounter notes." },
    });
    await user.click(screen.getByTestId("ctw-comms-add"));
    expect(screen.getByTestId("ctw-comms-list")).toHaveTextContent(
      "Handoff: please review the encounter notes."
    );
    const stored = window.localStorage.getItem(
      "chartnav.encounter.1.internalNotes"
    );
    expect(stored).toBeTruthy();
    expect(stored).toContain("Handoff: please review the encounter notes.");
  });
});

// ---------------------------------------------------------------
// Chat — frontend-only, demo-local.
// ---------------------------------------------------------------

describe("Phase 19 — Chat tab is internal staff chat (demo-local)", () => {
  it("renders the demo-local PHI banner + Staff/Clinician/Reviewer participants + composer", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    await user.click(screen.getByTestId("ctw-tab-chat"));
    expect(screen.getByTestId("ctw-chat-banner")).toHaveTextContent(
      /Demo-local internal chat — do not enter real PHI/i
    );
    expect(screen.getByTestId("ctw-chat-participant-staff")).toBeInTheDocument();
    expect(
      screen.getByTestId("ctw-chat-participant-clinician")
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("ctw-chat-participant-reviewer")
    ).toBeInTheDocument();
    expect(screen.getByTestId("ctw-chat-composer")).toBeInTheDocument();
  });

  it("sends a message and persists to localStorage", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    await user.click(screen.getByTestId("ctw-tab-chat"));
    fireEvent.change(screen.getByTestId("ctw-chat-composer"), {
      target: { value: "Quick handoff to clinician for review" },
    });
    await user.click(screen.getByTestId("ctw-chat-send"));
    expect(screen.getByTestId("ctw-chat-thread")).toHaveTextContent(
      "Quick handoff to clinician for review"
    );
    const stored = window.localStorage.getItem("chartnav.encounter.1.chat");
    expect(stored).toBeTruthy();
    expect(stored).toContain("Quick handoff to clinician for review");
  });

  it("export buttons are present and labelled .txt / .json", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    await user.click(screen.getByTestId("ctw-tab-chat"));
    expect(screen.getByTestId("ctw-chat-export-txt")).toHaveTextContent(
      /\.txt/
    );
    expect(screen.getByTestId("ctw-chat-export-json")).toHaveTextContent(
      /\.json/
    );
  });
});
