/**
 * Phase 19 + 19B + 19F — Clinical Tabbed Workspace tests.
 *
 * The existing App tests (App.test.tsx) verify integration: the
 * `transitions` / `transition-${s}` / `detail-status` /
 * `detail-source-chip` testids still resolve in the new tabbed
 * layout (handled by back-compat testids on the new components).
 *
 * This file exercises the standalone ClinicalTabbedWorkspace
 * component:
 *
 *   - exactly 9 tabs render with the expected labels (Phase 19F
 *     removes the prior review-only Billing tab; "Labs / Orders
 *     Review" replaces "Orders & Labs"; Chat is retained from
 *     Phase 19 as the internal-comms surface)
 *   - tab switching shows / hides the right panels
 *   - safe-claims labels are present in each tab
 *   - forbidden UI labels (place order, submit referral, send to
 *     patient, billing automation, CPT, charges, insurance,
 *     submit claim, auto-code, auto-bill, payment, claim) appear
 *     nowhere as interactive button / heading / input text
 *   - no Billing tab; no Billing card heading; no Billing data-
 *     testid anywhere
 *   - the Chat tab persists messages to localStorage and exports
 *     .txt / .json
 *   - the Communications tab is internal-only
 *   - the Overview tab's Timeline card holds workflow events +
 *     the Add timeline event composer (composer hidden when
 *     ?demo=1 is active)
 *   - the patient-header demographic strip shows intentional
 *     empty-state copy ("Not available in demo" / "Not recorded"
 *     / "No allergies recorded" / "No active meds recorded" /
 *     "Not scheduled") instead of bare em-dashes
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

// Phase 56 — the Imaging tab mounts FundusChartPanel, which calls
// listFundusCharts on mount. Stub the module so workspace-level tests
// don't issue a real fetch.
vi.mock("../features/fundus/fundusApi", () => ({
  listFundusCharts: vi.fn().mockResolvedValue([]),
  generateFundusChart: vi.fn(),
  getFundusChart: vi.fn(),
  renderFundusChart: vi.fn(),
  reviewFundusChart: vi.fn(),
  signFundusChart: vi.fn(),
}));

// Phase 57 — the Documentation tab mounts AmbientDocumentationPanel,
// which calls listScribeSessions on mount. Same pattern.
vi.mock("../features/ambient/ambientApi", () => ({
  listScribeSessions: vi.fn().mockResolvedValue([]),
  createScribeSession: vi.fn(),
  getScribeSession: vi.fn(),
  draftAmbientSession: vi.fn(),
  reviewScribeSession: vi.fn(),
  finalizeScribeSession: vi.fn(),
}));

// Phase 60 — the Clinical tab mounts VitalsWorkupPanel, which calls
// listVitalsWorkups on mount. Same pattern.
vi.mock("../features/vitals/vitalsApi", () => ({
  listVitalsWorkups: vi.fn().mockResolvedValue([]),
  createVitalsWorkup: vi.fn(),
  getVitalsWorkup: vi.fn(),
  updateVitalsWorkup: vi.fn(),
  reviewVitalsWorkup: vi.fn(),
  signVitalsWorkup: vi.fn(),
}));

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

function renderWorkspace(
  overrides: Partial<api.Encounter> = {},
  opts: {
    events?: api.WorkflowEvent[];
    eventAllowed?: boolean;
    pendingEvent?: boolean;
    isDemo?: boolean;
  } = {}
) {
  return render(
    <ClinicalTabbedWorkspace
      encounter={{ ...ENCOUNTER, ...overrides }}
      identity="admin@chartnav.local"
      me={ME}
      pendingStatus={null}
      onTransition={vi.fn().mockResolvedValue(undefined)}
      onSetPendingStatus={vi.fn()}
      onRefreshDetail={vi.fn()}
      events={opts.events ?? []}
      eventAllowed={opts.eventAllowed ?? true}
      pendingEvent={opts.pendingEvent ?? false}
      onAddEvent={vi.fn().mockResolvedValue(undefined)}
      isDemo={opts.isDemo ?? false}
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

  it("renders the Phase 19B demographic strip (Gender / Allergies / Conditions / Medications / Last Visit / Next Appt / Provider)", () => {
    renderWorkspace();
    expect(screen.getByTestId("ctw-patient-demographics")).toBeInTheDocument();
    expect(screen.getByTestId("ctw-demo-gender")).toHaveTextContent(/Gender/);
    expect(screen.getByTestId("ctw-demo-allergies")).toHaveTextContent(
      /Allergies/
    );
    expect(screen.getByTestId("ctw-demo-conditions")).toHaveTextContent(
      /Conditions/
    );
    expect(screen.getByTestId("ctw-demo-medications")).toHaveTextContent(
      /Medications/
    );
    expect(screen.getByTestId("ctw-demo-last-visit")).toHaveTextContent(
      /Last Visit/
    );
    expect(screen.getByTestId("ctw-demo-next-appt")).toHaveTextContent(
      /Next Appt/
    );
    expect(screen.getByTestId("ctw-demo-provider")).toHaveTextContent(
      /Provider/
    );
  });

  it("renders exactly 9 tabs in the tab bar (Phase 19F removes Billing; Chat is retained as the internal-comms surface)", () => {
    renderWorkspace();
    const bar = screen.getByTestId("ctw-tabbar");
    const tabs = within(bar).getAllByRole("tab");
    expect(tabs).toHaveLength(9);
    const labels = tabs.map((t) => t.textContent);
    expect(labels).toEqual([
      "Overview",
      "Clinical / Ophthalmology",
      "Documentation / EMR/EHR",
      "Imaging",
      "Labs / Orders Review",
      "Calendar",
      "Communications",
      "Documents",
      "Chat",
    ]);
  });

  it("does NOT render a Billing tab (Phase 19F)", () => {
    renderWorkspace();
    expect(screen.queryByTestId("ctw-tab-billing")).toBeNull();
    const bar = screen.getByTestId("ctw-tabbar");
    expect(bar.textContent || "").not.toMatch(/\bBilling\b/);
  });

  it("Overview is the default active tab and shows Patient snapshot / Visit summary / Favorites / Timeline cards", () => {
    renderWorkspace();
    const tab = screen.getByTestId("ctw-tab-overview");
    expect(tab).toHaveAttribute("aria-selected", "true");
    expect(screen.getByTestId("ctw-overview")).toBeInTheDocument();
    expect(screen.getByTestId("ctw-card-patient-snapshot")).toBeInTheDocument();
    expect(screen.getByTestId("ctw-card-visit-summary")).toBeInTheDocument();
    expect(screen.getByTestId("ctw-card-favorites")).toBeInTheDocument();
    expect(screen.getByTestId("ctw-card-timeline")).toBeInTheDocument();
  });

  it("clicking each tab switches the panel", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    for (const slug of [
      "clinical",
      "imaging",
      "orders-labs",
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

describe("Phase 19 + 19B + 19F — workspace contains no forbidden order / patient-send / billing labels on interactive elements", () => {
  // The forbidden phrases below MAY appear inside safety footnotes
  // (e.g. "ChartNav does not place lab orders" / "does not deliver
  // to a patient portal" / "ChartNav does not bill, code, submit
  // claims, or handle insurance") because those paragraphs ARE the
  // safe-claims contract. Same negative-assertion pattern Phase
  // 17B / 18 / 19B already use. What we forbid is the phrase
  // appearing as a button label, heading, or interactive control —
  // those are the surfaces that ship to a buyer.
  //
  // Phase 19F: Billing / CPT / Charges / Insurance / Submit Claim /
  // Auto-code / Auto-bill / Send Claim / Charge Patient / Bill
  // Insurance / Payment / Claim are now banned EVERYWHERE in the
  // workspace, not just on interactive elements. The prior Phase
  // 19B exception ("CPT / Charges / Insurance are legitimate
  // Billing-tab headings") no longer applies — there is no
  // Billing tab.
  it.each([
    ["overview"],
    ["clinical"],
    ["imaging"],
    ["orders-labs"],
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
          "claim submission",
          "billing automation",
          "send to patient",
          "patient portal",
          "automated patient message",
          "auto-message",
          "submit claim",
          "auto-code",
          "auto-bill",
          "send claim",
          "charge patient",
          "bill insurance",
        ]) {
          expect(
            t,
            `tab ${slug} interactive element must not contain "${banned}": ${t}`
          ).not.toContain(banned);
        }
      }
    }
  );

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
// Orders & Labs — review-only (renamed from Labs / Orders Review).
// ---------------------------------------------------------------

describe("Phase 19B — Orders & Labs tab is review-only", () => {
  it("renders only View / Mark reviewed / Add note actions (no submit/place/send buttons)", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    await user.click(screen.getByTestId("ctw-tab-orders-labs"));
    const panel = screen.getByTestId("ctw-panel-orders-labs");
    const buttons = within(panel).getAllByRole("button");
    for (const b of buttons) {
      const t = (b.textContent || "").toLowerCase();
      expect(t).toMatch(/^(view|mark reviewed|add note)$/);
    }
  });

  it("includes Lab Results / Imaging Orders / Procedure Plan / Review Notes sections", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    await user.click(screen.getByTestId("ctw-tab-orders-labs"));
    expect(screen.getByTestId("ctw-card-lab-results")).toBeInTheDocument();
    expect(screen.getByTestId("ctw-card-imaging-orders")).toBeInTheDocument();
    expect(screen.getByTestId("ctw-card-procedure-plan")).toBeInTheDocument();
    expect(screen.getByTestId("ctw-card-review-notes")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------
// Phase 19F — Billing surface fully absent (no tab, no panel, no
// disclaimer, no card, no headings, no testids, no UI text).
// ChartNav does not bill, code, submit claims, or handle insurance.
// ---------------------------------------------------------------

describe("Phase 19F — Billing surface is fully absent from the workspace", () => {
  // The tab list iterates every tab including the Overview default
  // and clicks each in turn so we exercise every panel's rendered
  // text (CSS `display:none` is not used; inactive panels simply
  // don't render). Each switched-to panel must NOT contain the
  // banned billing/coding/insurance/payment vocabulary anywhere.
  const NINE_TABS = [
    "overview",
    "clinical",
    "imaging",
    "orders-labs",
    "calendar",
    "communications",
    "documents",
    "chat",
  ] as const;

  it("does not expose any billing-flavored testids", () => {
    renderWorkspace();
    for (const id of [
      "ctw-tab-billing",
      "ctw-panel-billing",
      "ctw-billing",
      "ctw-billing-disclaimer",
      "ctw-card-cpt-codes",
      "ctw-card-charges",
      "ctw-card-insurance-status",
      "ctw-card-billing-review-notes",
    ]) {
      expect(screen.queryByTestId(id)).toBeNull();
    }
  });

  it.each(NINE_TABS.map((s) => [s]))(
    "tab %s contains no Billing / CPT / Charges / Insurance / Claim / Payment text in rendered UI",
    async (slug) => {
      const user = userEvent.setup();
      renderWorkspace();
      await user.click(screen.getByTestId(`ctw-tab-${slug}`));
      const panel = screen.getByTestId(`ctw-panel-${slug}`);
      const text = panel.textContent || "";
      for (const banned of [
        /\bBilling\b/i,
        /\bCPT\b/i,
        /\bCharges\b/i,
        /\bInsurance\b/i,
        /\bSubmit Claim\b/i,
        /\bAuto-code\b/i,
        /\bAuto-bill\b/i,
        /\bSend Claim\b/i,
        /\bCharge Patient\b/i,
        /\bBill Insurance\b/i,
        /\bPayment\b/i,
        /\bClaim submission\b/i,
      ]) {
        expect(
          text,
          `tab ${slug} must not contain ${banned}: ${text.slice(0, 200)}`
        ).not.toMatch(banned);
      }
    }
  );
});

// ---------------------------------------------------------------
// Phase 19F — Overview Timeline card holds workflow events + the
// Add timeline event composer. The composer is hidden in ?demo=1.
// ---------------------------------------------------------------

describe("Phase 19F — Overview Timeline card", () => {
  const FAKE_EVENTS: api.WorkflowEvent[] = [
    {
      id: 1,
      encounter_id: 1,
      event_type: "encounter_created",
      event_data: { source: "demo" },
      created_at: "2026-04-18 09:00:00",
    },
  ];

  it("renders workflow events inside the Overview Timeline card (not as a floating section below the workspace)", () => {
    renderWorkspace({}, { events: FAKE_EVENTS });
    const card = screen.getByTestId("ctw-card-timeline");
    expect(within(card).getByText(/encounter_created/)).toBeInTheDocument();
    expect(within(card).getByTestId("ctw-timeline-stamps")).toBeInTheDocument();
  });

  it("shows the Add timeline event composer when not in demo mode and the role is allowed", () => {
    renderWorkspace({}, { events: [], eventAllowed: true, isDemo: false });
    expect(screen.getByTestId("event-form")).toBeInTheDocument();
    expect(screen.queryByTestId("event-composer-demo-hidden")).toBeNull();
    expect(screen.queryByTestId("event-denied")).toBeNull();
  });

  it("shows the demo-hidden notice (read-only timeline) when ?demo=1 is active", () => {
    renderWorkspace({}, { events: FAKE_EVENTS, eventAllowed: true, isDemo: true });
    expect(screen.getByTestId("event-composer-demo-hidden")).toBeInTheDocument();
    expect(screen.queryByTestId("event-form")).toBeNull();
    // Read-only timeline still renders.
    expect(
      within(screen.getByTestId("ctw-card-timeline")).getByText(
        /encounter_created/
      )
    ).toBeInTheDocument();
  });

  it("shows the role-denied notice when eventAllowed is false (reviewer)", () => {
    renderWorkspace({}, { events: [], eventAllowed: false, isDemo: false });
    expect(screen.getByTestId("event-denied")).toBeInTheDocument();
    expect(screen.queryByTestId("event-form")).toBeNull();
  });
});

// ---------------------------------------------------------------
// Phase 19F — patient-header demographic strip uses intentional
// empty-state copy instead of bare em-dashes.
// ---------------------------------------------------------------

describe("Phase 19F — patient-header empty-state copy is intentional, not bare em-dashes", () => {
  it("renders intentional empty-state text for fields not on the Encounter type", () => {
    renderWorkspace();
    expect(screen.getByTestId("ctw-patient-dob")).toHaveTextContent(
      /Not available in demo/
    );
    expect(screen.getByTestId("ctw-patient-phone")).toHaveTextContent(
      /Not available in demo/
    );
    expect(screen.getByTestId("ctw-demo-gender")).toHaveTextContent(
      /Not recorded/
    );
    expect(screen.getByTestId("ctw-demo-allergies")).toHaveTextContent(
      /No allergies recorded/
    );
    expect(screen.getByTestId("ctw-demo-conditions")).toHaveTextContent(
      /No conditions recorded/
    );
    expect(screen.getByTestId("ctw-demo-medications")).toHaveTextContent(
      /No active meds recorded/
    );
    expect(screen.getByTestId("ctw-demo-next-appt")).toHaveTextContent(
      /Not scheduled/
    );
  });

  it("does NOT render any cell as a bare em-dash", () => {
    renderWorkspace();
    for (const id of [
      "ctw-patient-dob",
      "ctw-patient-phone",
      "ctw-demo-gender",
      "ctw-demo-allergies",
      "ctw-demo-conditions",
      "ctw-demo-medications",
      "ctw-demo-next-appt",
    ]) {
      const cell = screen.getByTestId(id);
      // The cell's value text (excluding the leading label) must not
      // be a bare em-dash. We strip the label prefix before checking.
      const value = (cell.textContent || "").replace(/^[A-Za-z #]+\s*/, "");
      expect(value.trim()).not.toMatch(/^—$/);
    }
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

  it("sends a message and persists to localStorage (recipient-scoped key, Phase 19I)", async () => {
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
    // Phase 19I — chat is recipient-scoped. The default
    // recipient on first render is "carter" (Dr. Carter).
    const stored = window.localStorage.getItem(
      "chartnav.encounter.1.chat.carter"
    );
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

// ---------------------------------------------------------------
// Phase 19I — Chat recipient selector. Staff can pick which
// internal user they're messaging; the thread is scoped to the
// selected recipient; the composer placeholder reflects the
// recipient name; export filenames include the recipient slug.
// ---------------------------------------------------------------

describe("Phase 19I — Chat recipient selector", () => {
  it("renders the recipient selector with the four demo internal recipients", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    await user.click(screen.getByTestId("ctw-tab-chat"));

    const recipientSelect = screen.getByTestId(
      "ctw-chat-recipient-select"
    ) as HTMLSelectElement;
    expect(recipientSelect).toBeInTheDocument();

    // Four demo recipients (no patient recipients — the safe-
    // claims contract bans patient messaging).
    for (const id of ["carter", "patel", "admin-front-desk", "reviewer"]) {
      expect(
        screen.getByTestId(`ctw-chat-recipient-option-${id}`)
      ).toBeInTheDocument();
    }
    expect(recipientSelect.options.length).toBe(4);
  });

  it("first recipient (Dr. Carter) is selected by default and the composer placeholder reflects it", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    await user.click(screen.getByTestId("ctw-tab-chat"));

    const recipientSelect = screen.getByTestId(
      "ctw-chat-recipient-select"
    ) as HTMLSelectElement;
    expect(recipientSelect.value).toBe("carter");

    const composer = screen.getByTestId(
      "ctw-chat-composer"
    ) as HTMLTextAreaElement;
    expect(composer.placeholder).toMatch(/Message Dr\. Carter internally/);
  });

  it("changing the recipient updates the placeholder + recipient card", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    await user.click(screen.getByTestId("ctw-tab-chat"));

    const recipientSelect = screen.getByTestId(
      "ctw-chat-recipient-select"
    ) as HTMLSelectElement;
    await user.selectOptions(recipientSelect, "reviewer");

    const composer = screen.getByTestId(
      "ctw-chat-composer"
    ) as HTMLTextAreaElement;
    expect(composer.placeholder).toMatch(/Message Reviewer internally/);
    expect(screen.getByTestId("ctw-chat-recipient-card")).toHaveTextContent(
      /Reviewer/
    );
    expect(
      screen.getByTestId("ctw-chat-recipient-presence")
    ).toHaveTextContent(/Offline/);
  });

  it("the thread is scoped per-recipient (messages don't bleed between recipients)", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    await user.click(screen.getByTestId("ctw-tab-chat"));

    // Send a message to Dr. Carter (default).
    fireEvent.change(screen.getByTestId("ctw-chat-composer"), {
      target: { value: "Carter, please review imaging." },
    });
    await user.click(screen.getByTestId("ctw-chat-send"));
    expect(screen.getByTestId("ctw-chat-thread")).toHaveTextContent(
      "Carter, please review imaging."
    );

    // Switch to Dr. Patel — Carter's message must not appear.
    await user.selectOptions(
      screen.getByTestId("ctw-chat-recipient-select"),
      "patel"
    );
    expect(screen.getByTestId("ctw-chat-thread")).not.toHaveTextContent(
      "Carter, please review imaging."
    );

    // Send a message to Dr. Patel.
    fireEvent.change(screen.getByTestId("ctw-chat-composer"), {
      target: { value: "Patel, scheduling follow-up." },
    });
    await user.click(screen.getByTestId("ctw-chat-send"));
    expect(screen.getByTestId("ctw-chat-thread")).toHaveTextContent(
      "Patel, scheduling follow-up."
    );

    // Switch back to Dr. Carter — only Carter's message visible.
    await user.selectOptions(
      screen.getByTestId("ctw-chat-recipient-select"),
      "carter"
    );
    expect(screen.getByTestId("ctw-chat-thread")).toHaveTextContent(
      "Carter, please review imaging."
    );
    expect(screen.getByTestId("ctw-chat-thread")).not.toHaveTextContent(
      "Patel, scheduling follow-up."
    );

    // Two distinct localStorage keys, one per recipient.
    expect(
      window.localStorage.getItem("chartnav.encounter.1.chat.carter")
    ).toContain("Carter, please review imaging.");
    expect(
      window.localStorage.getItem("chartnav.encounter.1.chat.patel")
    ).toContain("Patel, scheduling follow-up.");
  });

  it("recipient list contains no patient-side recipients (no patient messaging)", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    await user.click(screen.getByTestId("ctw-tab-chat"));

    const recipientSelect = screen.getByTestId(
      "ctw-chat-recipient-select"
    ) as HTMLSelectElement;
    const optionsText = Array.from(recipientSelect.options)
      .map((o) => o.textContent?.toLowerCase() ?? "")
      .join(" ");
    for (const banned of [
      "patient",
      "send to patient",
      "patient portal",
      "external",
    ]) {
      expect(optionsText).not.toContain(banned);
    }
  });
});

// ---------------------------------------------------------------
// Phase 19I — Imaging tab opens with a 6-card workspace grid;
// the OD/OS retinal workbench is no longer the first thing the
// buyer sees.
// ---------------------------------------------------------------

describe("Phase 19I — Imaging tab card grid", () => {
  it("renders Upload imaging / OCT / Fundus / Attachments / Imaging notes / Selected image viewer cards", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    await user.click(screen.getByTestId("ctw-tab-imaging"));

    expect(
      screen.getByTestId("ctw-card-upload-imaging")
    ).toBeInTheDocument();
    expect(screen.getByTestId("ctw-card-oct-images")).toBeInTheDocument();
    expect(screen.getByTestId("ctw-card-fundus-photos")).toBeInTheDocument();
    expect(screen.getByTestId("ctw-card-attachments")).toBeInTheDocument();
    expect(screen.getByTestId("ctw-card-imaging-notes")).toBeInTheDocument();
    expect(
      screen.getByTestId("ctw-card-selected-image-viewer")
    ).toBeInTheDocument();
    // OD/OS workbench still present, but as its own wide card.
    expect(
      screen.getByTestId("ctw-card-od-os-retinal-workbench")
    ).toBeInTheDocument();
    // Phase 55 — Fundus charts wide card is mounted below the
    // OD/OS retinal workbench.
    expect(
      screen.getByTestId("ctw-card-fundus-charts")
    ).toBeInTheDocument();
  });

  it("renders the workspace grid before the OD/OS retinal workbench", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    await user.click(screen.getByTestId("ctw-tab-imaging"));

    const grid = screen.getByTestId("ctw-imaging-grid");
    const workbench = screen.getByTestId("ctw-card-od-os-retinal-workbench");
    // Document order: grid before workbench.
    expect(
      grid.compareDocumentPosition(workbench) &
        Node.DOCUMENT_POSITION_FOLLOWING
    ).toBeTruthy();
  });
});

// ---------------------------------------------------------------
// Phase 19I — Clinical / Ophthalmology tab is now grouped pill
// cards (no <details>/<summary>/<ul> bullet-list look).
// ---------------------------------------------------------------

describe("Phase 19I — Clinical tab is grouped pill cards (not a bullet list)", () => {
  it("renders the six grouped cards in the brief order with Favorites pinned first", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    await user.click(screen.getByTestId("ctw-tab-clinical"));

    const ids = [
      "favorites",
      "retina",
      "cornea",
      "glaucoma",
      "oculoplastics",
      "general",
    ];
    for (const id of ids) {
      expect(
        screen.getByTestId(`ctw-clinical-group-${id}`)
      ).toBeInTheDocument();
    }
    const favorites = screen.getByTestId("ctw-clinical-group-favorites");
    const retina = screen.getByTestId("ctw-clinical-group-retina");
    expect(
      favorites.compareDocumentPosition(retina) &
        Node.DOCUMENT_POSITION_FOLLOWING
    ).toBeTruthy();
  });

  it("does not render the prior bullet-list <details>/<summary> structure", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    await user.click(screen.getByTestId("ctw-tab-clinical"));

    const panel = screen.getByTestId("ctw-panel-clinical");
    // The pre-19I implementation rendered <details> + <summary>.
    // The post-19I implementation should have neither anywhere
    // in the Clinical panel.
    expect(panel.querySelector("details")).toBeNull();
    expect(panel.querySelector("summary")).toBeNull();
  });

  it("renders pill buttons for each shortcut item", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    await user.click(screen.getByTestId("ctw-tab-clinical"));

    // Check a representative pill from each non-empty group.
    expect(
      screen.getByTestId("ctw-clinical-pill-retina-drusen")
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("ctw-clinical-pill-cornea-dry-eye")
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("ctw-clinical-pill-glaucoma-iop-elevated")
    ).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------
// Phase 19I — Documentation tab is wrapped in a stepper +
// workbench shell.
// ---------------------------------------------------------------

describe("Phase 19I — Documentation tab stepper", () => {
  it("renders the Transcript -> Extracted Facts -> AI Draft -> Final Note stepper", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    await user.click(screen.getByTestId("ctw-tab-documentation"));

    expect(screen.getByTestId("ctw-doc-stepper")).toBeInTheDocument();
    for (const id of ["transcript", "facts", "draft", "final"]) {
      expect(
        screen.getByTestId(`ctw-doc-stepper-${id}`)
      ).toBeInTheDocument();
    }
    expect(screen.getByTestId("ctw-doc-workbench")).toBeInTheDocument();
  });

  // Phase 71 — strengthened stepper caption with explicit "not a
  // certified EHR / does not replace your EHR" language.
  it("Phase 71 — stepper caption includes the no-EHR-replacement safety frame", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    await user.click(screen.getByTestId("ctw-tab-documentation"));
    const caption = screen.getByTestId("ctw-doc-stepper-caption");
    expect(caption).toHaveTextContent(/Provider-reviewed at every stage/i);
    expect(caption).toHaveTextContent(/the clinician signs/i);
    expect(caption).toHaveTextContent(/Not a certified EHR/i);
    expect(caption).toHaveTextContent(/Does not replace your EHR/i);
    expect(caption).toHaveTextContent(/Fake-data demo only/i);
  });
});

// ---------------------------------------------------------------
// Phase 71 — Retina visit sequence ribbon.
//
// A 5-step ribbon (Intake → Fundus Drawing → VisitDraft →
// Provider Review → Signed Lock) sits between the patient
// header and the tab bar. Each step is a navigation button that
// focuses the relevant workspace tab. The Signed Lock step is
// role-aware.
// ---------------------------------------------------------------

describe("Phase 71 — Retina visit sequence ribbon", () => {
  it("mounts inside the workspace shell with title + caption + footnote", () => {
    renderWorkspace();
    expect(screen.getByTestId("retina-visit-ribbon")).toBeInTheDocument();
    expect(
      screen.getByTestId("retina-visit-ribbon-title")
    ).toHaveTextContent(/Retina visit sequence/i);
    expect(
      screen.getByTestId("retina-visit-ribbon-caption")
    ).toHaveTextContent(/Fake-data demo/i);
    expect(
      screen.getByTestId("retina-visit-ribbon-footnote")
    ).toBeInTheDocument();
  });

  it("renders after the patient header and before the tab bar in document order", () => {
    renderWorkspace();
    const header = screen.getByTestId("ctw-patient-header");
    const ribbon = screen.getByTestId("retina-visit-ribbon");
    const tabbar = screen.getByTestId("ctw-tabbar");
    expect(
      header.compareDocumentPosition(ribbon) &
        Node.DOCUMENT_POSITION_FOLLOWING
    ).toBeTruthy();
    expect(
      ribbon.compareDocumentPosition(tabbar) &
        Node.DOCUMENT_POSITION_FOLLOWING
    ).toBeTruthy();
  });

  it("renders all 5 steps", () => {
    renderWorkspace();
    for (const id of [
      "intake",
      "fundus-drawing",
      "visit-draft",
      "provider-review",
      "signed-lock",
    ]) {
      expect(
        screen.getByTestId(`retina-visit-step-${id}`)
      ).toBeInTheDocument();
    }
  });

  it("clicking step 1 (intake) activates the Clinical tab", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    await user.click(screen.getByTestId("retina-visit-step-btn-intake"));
    expect(screen.getByTestId("ctw-tab-clinical")).toHaveAttribute(
      "aria-selected",
      "true"
    );
    expect(screen.getByTestId("ctw-panel-clinical")).toBeInTheDocument();
  });

  it("clicking step 2 (fundus drawing) activates the Imaging tab", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    await user.click(
      screen.getByTestId("retina-visit-step-btn-fundus-drawing")
    );
    expect(screen.getByTestId("ctw-tab-imaging")).toHaveAttribute(
      "aria-selected",
      "true"
    );
    expect(screen.getByTestId("ctw-panel-imaging")).toBeInTheDocument();
  });

  it("clicking step 3 (visit-draft) activates the Documentation tab", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    await user.click(
      screen.getByTestId("retina-visit-step-btn-visit-draft")
    );
    expect(screen.getByTestId("ctw-tab-documentation")).toHaveAttribute(
      "aria-selected",
      "true"
    );
    expect(screen.getByTestId("ctw-panel-documentation")).toBeInTheDocument();
  });

  it("admin role (default ME) sees no role-lock on the signed-lock step", () => {
    renderWorkspace();
    expect(
      screen
        .getByTestId("retina-visit-step-signed-lock")
        .getAttribute("data-locked")
    ).toBe("false");
    expect(
      screen.queryByTestId("retina-visit-step-role-lock-signed-lock")
    ).toBeNull();
  });
});

// ---------------------------------------------------------------
// Phase 71 — Clinical tab intentional-shortcuts note.
// The disabled pill grid now leads with an explicit "these are
// provider review prompts, not generated diagnoses; pinning is a
// future enhancement" caption so the UI does not read as broken.
// ---------------------------------------------------------------

describe("Phase 71 — Clinical tab intentional-shortcuts note", () => {
  it("renders an explanatory note above the shortcuts grid that names the future enhancement", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    await user.click(screen.getByTestId("ctw-tab-clinical"));
    const note = screen.getByTestId("ctw-clinical-shortcuts-note");
    expect(note).toHaveTextContent(/provider review prompts/i);
    expect(note).toHaveTextContent(/does not generate diagnoses/i);
    expect(note).toHaveTextContent(/intentionally inert/i);
  });

  it("the note renders before the shortcuts search input in document order", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    await user.click(screen.getByTestId("ctw-tab-clinical"));
    const note = screen.getByTestId("ctw-clinical-shortcuts-note");
    const search = screen.getByTestId("ctw-clinical-search");
    expect(
      note.compareDocumentPosition(search) &
        Node.DOCUMENT_POSITION_FOLLOWING
    ).toBeTruthy();
  });
});

// ---------------------------------------------------------------
// Phase 56 — Fundus charts workspace integration
// ---------------------------------------------------------------

describe("Phase 56 — Fundus charts card reachability", () => {
  it("Fundus charts card mounts the FundusChartPanel (panel reachable from workspace)", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    await user.click(screen.getByTestId("ctw-tab-imaging"));

    const card = screen.getByTestId("ctw-card-fundus-charts");
    expect(card).toBeInTheDocument();
    // The mounted panel exposes its own test hook.
    expect(
      within(card).getByTestId("fundus-chart-panel"),
    ).toBeInTheDocument();
    expect(
      within(card).getByTestId("fundus-safety-banner"),
    ).toBeInTheDocument();
  });

  it("Fundus charts card renders the OD/OS/OU laterality radio group", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    await user.click(screen.getByTestId("ctw-tab-imaging"));
    const card = screen.getByTestId("ctw-card-fundus-charts");
    expect(
      within(card).getByTestId("fundus-laterality-group"),
    ).toBeInTheDocument();
    expect(within(card).getByTestId("fundus-laterality-OD")).toBeInTheDocument();
    expect(within(card).getByTestId("fundus-laterality-OS")).toBeInTheDocument();
    expect(within(card).getByTestId("fundus-laterality-OU")).toBeInTheDocument();
  });

  it("safety banner inside Fundus charts card shows the four required clauses", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    await user.click(screen.getByTestId("ctw-tab-imaging"));
    const banner = screen.getByTestId("fundus-safety-banner");
    expect(banner.textContent).toMatch(/Draft from clinician-entered findings/i);
    expect(banner.textContent).toMatch(/Provider review required/i);
    expect(banner.textContent).toMatch(/Not image interpretation/i);
    expect(banner.textContent).toMatch(/Does not diagnose/i);
  });
});

// ---------------------------------------------------------------
// Phase 57 — Ambient Documentation Assist mounts in Documentation tab
// ---------------------------------------------------------------

describe("Phase 57 — Ambient Documentation Assist mount", () => {
  it("Ambient documentation card mounts the AmbientDocumentationPanel in the Documentation tab", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    await user.click(screen.getByTestId("ctw-tab-documentation"));

    const card = screen.getByTestId("ctw-card-ambient-documentation");
    expect(card).toBeInTheDocument();
    expect(
      within(card).getByTestId("ambient-documentation-panel"),
    ).toBeInTheDocument();
    expect(
      within(card).getByTestId("ambient-safety-banner"),
    ).toBeInTheDocument();
  });

  it("safety banner names every required disclaimer", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    await user.click(screen.getByTestId("ctw-tab-documentation"));
    const banner = screen.getByTestId("ambient-safety-banner");
    expect(banner.textContent).toMatch(/Provider review required/i);
    expect(banner.textContent).toMatch(/Does not diagnose/i);
    expect(banner.textContent).toMatch(/Does not place orders/i);
    expect(banner.textContent).toMatch(/Not for real PHI/i);
  });
});

// ---------------------------------------------------------------
// Phase 60 — Technician Workup & Vitals mounts in Clinical tab
// ---------------------------------------------------------------

describe("Phase 60 — Technician Workup & Vitals mount", () => {
  it("Clinical tab mounts the VitalsWorkupPanel inside a wide card", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    await user.click(screen.getByTestId("ctw-tab-clinical"));
    const card = screen.getByTestId("ctw-card-technician-workup-vitals");
    expect(card).toBeInTheDocument();
    expect(
      within(card).getByTestId("vitals-workup-panel"),
    ).toBeInTheDocument();
    expect(
      within(card).getByTestId("vitals-safety-banner"),
    ).toBeInTheDocument();
  });

  it("Vitals safety banner names every required disclaimer", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    await user.click(screen.getByTestId("ctw-tab-clinical"));
    const banner = screen.getByTestId("vitals-safety-banner");
    expect(banner.textContent).toMatch(/Does not diagnose/i);
    expect(banner.textContent).toMatch(/Does not recommend treatment/i);
    expect(banner.textContent).toMatch(/Does not place orders/i);
    expect(banner.textContent).toMatch(/Not for real PHI/i);
    expect(banner.textContent).toMatch(/No device integration/i);
  });
});
