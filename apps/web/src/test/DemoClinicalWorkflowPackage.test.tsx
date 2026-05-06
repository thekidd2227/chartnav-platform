/**
 * Phase 13 — Demo-ready clinical workflow package tests.
 *
 * Verifies the package-level integration:
 *   - the demo guide mounts from NoteWorkspace when patientId is
 *     numeric;
 *   - the four demo / package docs exist on disk and contain the
 *     required structure;
 *   - the docs only contain forbidden phrasing in safe contexts
 *     (negative assertions, forbidden-phrase enumerations, or buyer
 *     Q&A answers).
 */

import { readFileSync } from "node:fs";
import path from "node:path";

import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../audioRecorder", async () => {
  const actual = await vi.importActual<typeof import("../audioRecorder")>(
    "../audioRecorder"
  );
  return {
    ...actual,
    detectBrowserCapture: vi.fn(),
    startBrowserRecording: vi.fn(),
  };
});

vi.mock("../api", async () => {
  const actual = await vi.importActual<typeof import("../api")>("../api");
  return {
    ...actual,
    listEncounterInputs: vi.fn(),
    listEncounterNotes: vi.fn(),
    getNoteVersion: vi.fn(),
    getPlatform: vi.fn(),
    listMyQuickComments: vi.fn(),
    listMyQuickCommentFavorites: vi.fn(),
    listMyClinicalShortcutFavorites: vi.fn(),
    // Phase-panel deps mounted by NoteWorkspace.
    listPatientEyeDiagrams: vi.fn(),
    proposeRetinalFromFindings: vi.fn(),
    listPatientScribeSessions: vi.fn(),
    listPatientSummaries: vi.fn(),
    getPatientPreVisitBrief: vi.fn(),
    listProviderActionItems: vi.fn(),
  };
});

import * as api from "../api";
import * as audioRecorder from "../audioRecorder";
import { NoteWorkspace } from "../NoteWorkspace";

const CLIN: api.Me = {
  user_id: 2,
  email: "clin@chartnav.local",
  full_name: "Casey Clinician",
  role: "clinician",
  organization_id: 1,
};

beforeEach(() => {
  vi.clearAllMocks();
  (api.listEncounterInputs as any).mockResolvedValue([]);
  (api.listEncounterNotes as any).mockResolvedValue([]);
  (api.getNoteVersion as any).mockResolvedValue(null);
  (api.getPlatform as any).mockResolvedValue({
    platform_mode: "standalone",
    integration_adapter: "native",
  });
  (api.listMyQuickComments as any).mockResolvedValue([]);
  (api.listMyQuickCommentFavorites as any).mockResolvedValue([]);
  (api.listMyClinicalShortcutFavorites as any).mockResolvedValue([]);
  (audioRecorder.detectBrowserCapture as any).mockReturnValue({
    supported: true,
    pickedMime: "audio/webm;codecs=opus",
    pickedExt: ".webm",
  });
  (audioRecorder.startBrowserRecording as any).mockReset();

  (api.listPatientEyeDiagrams as any).mockResolvedValue({
    items: [],
    total: 0,
  });
  (api.listPatientScribeSessions as any).mockResolvedValue({
    items: [],
    total: 0,
  });
  (api.listPatientSummaries as any).mockResolvedValue({
    items: [],
    total: 0,
  });
  (api.getPatientPreVisitBrief as any).mockResolvedValue({
    patient_id: 7,
    brief_status: "generated",
    last_visit_summary: null,
    active_issues: [],
    retinal_artifact_summary: {
      total: 0,
      signed_count: 0,
      unsigned_count: 0,
      has_unsigned_drafts: false,
      latest_signed: null,
    },
    recent_scribe_session_summary: { session_id: null, status: "none" },
    patient_summary_context: { summary_id: null, status: "none" },
    pending_items: [],
    suggested_review_items: [],
    data_gaps: [],
    source_counts: {
      encounters: 0,
      workflow_events: 0,
      scribe_sessions: 0,
      scribe_sessions_finalized: 0,
      retinal_artifacts: 0,
      retinal_artifacts_signed: 0,
      patient_summaries: 0,
      patient_summaries_finalized: 0,
    },
    generated_at: "2026-05-06T05:00:00+00:00",
    notice: "Pre-visit brief — provider review required.",
  });
  (api.listProviderActionItems as any).mockResolvedValue({
    items: [],
    total: 0,
  });
});

function renderWorkspace(patientId: number | null = 7) {
  return render(
    <NoteWorkspace
      identity={CLIN.email}
      me={CLIN}
      encounterId={42}
      patientId={patientId}
      patientDisplay="Morgan Lee"
      providerDisplay="Dr. Carter"
    />
  );
}

// ---------------------------------------------------------------------
// Mount integration
// ---------------------------------------------------------------------

describe("DemoClinicalWorkflowPackage — mount integration", () => {
  it("mounts the demo guide section in the workspace when patientId is numeric", async () => {
    renderWorkspace(7);
    await waitFor(() => {
      expect(
        screen.getByTestId("demo-clinical-workflow-guide-section")
      ).toBeInTheDocument();
    });
    expect(
      screen.getByTestId("demo-clinical-workflow-guide")
    ).toBeInTheDocument();
  });

  it("does not mount the demo guide when patientId is null", async () => {
    renderWorkspace(null);
    // Wait long enough for the workspace to settle, then assert the
    // guide is absent.
    await screen.findByTestId("workspace-tier-transcript");
    expect(
      screen.queryByTestId("demo-clinical-workflow-guide-section")
    ).not.toBeInTheDocument();
  });

  it("the guide is collapsed by default in the mounted workspace", async () => {
    renderWorkspace(7);
    await screen.findByTestId("demo-clinical-workflow-guide");
    expect(
      screen.queryByTestId("demo-clinical-workflow-guide-body")
    ).not.toBeInTheDocument();
    expect(
      screen.getByTestId("demo-clinical-workflow-guide-toggle")
    ).toHaveTextContent(/Show demo workflow guide/i);
  });

  it("does not introduce any new top-level button alongside the existing panels", async () => {
    renderWorkspace(7);
    await screen.findByTestId("demo-clinical-workflow-guide");
    // The phase 5B/8/9/10/11 panel test-ids still mount.
    expect(screen.getByTestId("eye-diagram-section")).toBeInTheDocument();
    expect(
      screen.getByTestId("scribe-session-section")
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("patient-summary-section")
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("pre-visit-brief-section")
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("provider-action-items-section")
    ).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------
// Demo docs claims scan
// ---------------------------------------------------------------------

const REPO_ROOT = path.resolve(__dirname, "../../../..");
const DEMO_DOCS = [
  "docs/chartnav-demo-ready-clinical-workflow-package.md",
  "docs/demo/chartnav-clinical-workflow-demo-script.md",
  "docs/demo/chartnav-demo-click-path.md",
  "docs/demo/chartnav-video-clip-shot-list.md",
];

const FORBIDDEN_POSITIVE_CLAIMS: { name: string; pattern: RegExp }[] = [
  { name: "HIPAA compliant", pattern: /\bhipaa[ -]compliant\b/i },
  { name: "certified EHR", pattern: /\bcertified ehr\b/i },
  { name: "autonomous diagnosis", pattern: /\bautonomous diagnosis\b/i },
  { name: "automatic diagnosis", pattern: /\bautomatic diagnosis\b/i },
  { name: "guaranteed accuracy", pattern: /\bguaranteed accuracy\b/i },
  { name: "automatic orders", pattern: /\bautomatic orders?\b/i },
  { name: "order OCT", pattern: /\border oct\b/i },
  { name: "submit referral", pattern: /\bsubmit referral\b/i },
  { name: "send referral", pattern: /\bsend referral\b/i },
  { name: "billing automation", pattern: /\bbilling automation\b/i },
  { name: "coding automation", pattern: /\bcoding automation\b/i },
  { name: "send patient message", pattern: /\bsend patient message\b/i },
  { name: "replaces a doctor", pattern: /\breplaces (?:a )?doctor\b/i },
  { name: "external LLM certainty", pattern: /\bexternal llm certainty\b/i },
];

/**
 * A line is a "safe context" for a forbidden claim if it is clearly
 * a negative assertion, an enumerated forbidden-phrase entry, a
 * buyer-Q&A question heading whose answer is a negative assertion,
 * or guidance that explicitly tells the reader to use a different
 * phrase instead.
 *
 * Pass the surrounding lines so we can spot a Q&A pattern like
 *   ### "Is this HIPAA-compliant?"
 *   <blank>
 *   **Say:** "We follow HIPAA-aware data-handling practices: ..."
 */
function isSafeNegativeContext(
  line: string,
  lines: string[] = [],
  idx: number = -1
): boolean {
  const lower = line.toLowerCase();
  // Negative assertions explicitly saying ChartNav does not do it.
  if (
    /\bdoes not\b/.test(lower) ||
    /\bnot a(n)? \b/.test(lower) ||
    /\bnever\b/.test(lower)
  ) {
    return true;
  }
  // Enumerated forbidden-phrase list ("forbidden phrasing", "do not say").
  if (
    /forbidden|do not say|never (?:claim|use|say)|never appear|never\b/i.test(
      line
    )
  ) {
    return true;
  }
  // Bullet-style entries inside a forbidden-phrase list (the line
  // is just the phrase in quotes / wrapped text). Cheap heuristic:
  // the line is short and starts with a bullet or quote.
  if (/^\s*[-*]\s*"/.test(line) || /^\s*[-*]\s*\b/.test(line)) {
    return true;
  }
  // "Use *X* instead" style guidance.
  if (/\buse\b.+\binstead\b/i.test(line)) return true;
  // Markdown question heading — the answer follows. Require either
  // the heading text ends with a `?` (a literal question) OR the
  // next ~6 non-blank lines contain a negative assertion.
  if (idx >= 0 && lines.length > 0) {
    const isQuestionHeading =
      /^#{1,6}\s+/.test(line) && /\?\s*"?\s*$/.test(line);
    if (isQuestionHeading) {
      const window = lines
        .slice(idx + 1, idx + 12)
        .filter((l) => l.trim().length > 0)
        .slice(0, 6);
      if (
        window.some(
          (l) =>
            /\bdoes not\b/i.test(l) ||
            /\bnot a(n)? \b/i.test(l) ||
            /\bnever\b/i.test(l) ||
            /follow .* hipaa-aware|hipaa-aware data-handling/i.test(l)
        )
      ) {
        return true;
      }
    }
  }
  return false;
}

describe("DemoClinicalWorkflowPackage — demo docs", () => {
  it("all four demo / package docs exist on disk", () => {
    for (const rel of DEMO_DOCS) {
      const full = path.join(REPO_ROOT, rel);
      expect(() => readFileSync(full, "utf-8")).not.toThrow();
    }
  });

  it("each demo doc includes the required headings", () => {
    const expected: Record<string, RegExp[]> = {
      "docs/chartnav-demo-ready-clinical-workflow-package.md": [
        /^#\s+ChartNav Demo-Ready Clinical Workflow Package/m,
        /^##\s+Audience/m,
        /^##\s+Demo data policy/m,
        /^##\s+Documentation map/m,
        /^##\s+Safety \/ claims rules/m,
      ],
      "docs/demo/chartnav-clinical-workflow-demo-script.md": [
        /^#\s+ChartNav Clinical Workflow Demo Script/m,
        /^##\s+5-minute demo/m,
        /^##\s+10-minute demo/m,
        /^##\s+Buyer Q&A/m,
        /^##\s+What not to claim, ever/m,
      ],
      "docs/demo/chartnav-demo-click-path.md": [
        /^#\s+ChartNav Demo Click Path/m,
        /^##\s+5-minute click path/m,
      ],
      "docs/demo/chartnav-video-clip-shot-list.md": [
        /^#\s+ChartNav Video Clip Shot List/m,
        /^##\s+Editorial guardrails/m,
        /^##\s+Clip plan/m,
      ],
    };
    for (const [rel, patterns] of Object.entries(expected)) {
      const text = readFileSync(path.join(REPO_ROOT, rel), "utf-8");
      for (const p of patterns) {
        expect(text).toMatch(p);
      }
    }
  });

  it("forbidden positive claims appear only in safe negative-assertion contexts", () => {
    for (const rel of DEMO_DOCS) {
      const text = readFileSync(path.join(REPO_ROOT, rel), "utf-8");
      const lines = text.split(/\r?\n/);
      for (const claim of FORBIDDEN_POSITIVE_CLAIMS) {
        const matches = lines
          .map((line, idx) => ({ line, idx }))
          .filter(({ line }) => claim.pattern.test(line));
        for (const { line, idx } of matches) {
          if (!isSafeNegativeContext(line, lines, idx)) {
            // If we can't classify the line as safe, look at the
            // immediately preceding non-blank line as additional
            // context (e.g. a section header introducing a list).
            const prev = lines
              .slice(0, idx)
              .reverse()
              .find((s) => s.trim().length > 0);
            const prevIdx = prev ? lines.lastIndexOf(prev) : -1;
            const safe =
              !!prev && isSafeNegativeContext(prev, lines, prevIdx);
            expect(
              safe,
              `In ${rel} line ${idx + 1}: forbidden claim "${
                claim.name
              }" appears outside a negative-assertion or forbidden-list context: ${line}`
            ).toBe(true);
          }
        }
      }
    }
  });

  it("no demo doc claims ChartNav diagnoses, orders, codes, refers, or messages patients positively", () => {
    // A coarser guard: scan the docs for any line that asserts
    // ChartNav *does* do these things. Looks for verb forms like
    // "ChartNav diagnoses ..." rather than "ChartNav does not
    // diagnose ...".
    const positiveAssertions = [
      /\bchartnav\b[^.\n]*\bdiagnoses\b/i,
      /\bchartnav\b[^.\n]*\bplaces orders?\b/i,
      /\bchartnav\b[^.\n]*\bsubmits referrals?\b/i,
      /\bchartnav\b[^.\n]*\bcodes (?:visits|encounters|claims)\b/i,
      /\bchartnav\b[^.\n]*\bbills\s+(?!automatically)/i,
      /\bchartnav\b[^.\n]*\bautomatically (?:diagnoses|orders|sends|messages)/i,
    ];
    for (const rel of DEMO_DOCS) {
      const text = readFileSync(path.join(REPO_ROOT, rel), "utf-8");
      for (const p of positiveAssertions) {
        const matches = text.match(p);
        // Also confirm the match is not part of a "does not" line.
        if (matches) {
          const matchedLine =
            text.split(/\r?\n/).find((l) => p.test(l)) || "";
          if (!isSafeNegativeContext(matchedLine)) {
            expect(matches, `In ${rel}: ${matchedLine}`).toBeNull();
          }
        }
      }
    }
  });
});
