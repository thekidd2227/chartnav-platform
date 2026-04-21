/**
 * Hardening-lane vitest coverage — focused regression around the
 * currently shipped transcript → findings → draft → signoff wedge
 * and the integrated/native encounter UX.
 *
 * Keeps selectors stable, prefers existing `data-testid`s, and
 * avoids asserting implementation details the tier components
 * already cover elsewhere.
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import {
  Encounter,
  encounterIsNative,
  encounterSourceLabel,
} from "../api";
import { ExamSummary } from "../ExamSummary";
import { TrustBadge, trustKindForNote } from "../TrustBadge";
import { transcriptStatusHelp } from "../NoteWorkspace";

// ---------- source chip + banner labels (pure api helpers) -------------

const baseEncounter: Encounter = {
  id: 42,
  organization_id: 1,
  location_id: 1,
  patient_identifier: "PT-1001",
  patient_name: "Morgan Lee",
  provider_name: "Dr. Carter",
  status: "in_progress",
  scheduled_at: null,
  started_at: null,
  completed_at: null,
  created_at: null,
};

describe("encounterSourceLabel + encounterIsNative", () => {
  it("treats undefined _source as ChartNav (native)", () => {
    const enc: Encounter = { ...baseEncounter };
    expect(encounterIsNative(enc)).toBe(true);
    expect(encounterSourceLabel(enc)).toBe("ChartNav (native)");
  });

  it("chartnav _source is native", () => {
    const enc: Encounter = { ...baseEncounter, _source: "chartnav" };
    expect(encounterIsNative(enc)).toBe(true);
    expect(encounterSourceLabel(enc)).toBe("ChartNav (native)");
  });

  it("fhir _source is external with the FHIR label", () => {
    const enc: Encounter = { ...baseEncounter, _source: "fhir" };
    expect(encounterIsNative(enc)).toBe(false);
    expect(encounterSourceLabel(enc)).toBe("External (FHIR)");
  });

  it("stub _source is external with the stub label", () => {
    const enc: Encounter = { ...baseEncounter, _source: "stub" };
    expect(encounterIsNative(enc)).toBe(false);
    expect(encounterSourceLabel(enc)).toBe("External (stub)");
  });

  it("unknown _source falls back to a generic External label", () => {
    const enc: Encounter = { ...baseEncounter, _source: "epic-vendor-1" };
    expect(encounterIsNative(enc)).toBe(false);
    expect(encounterSourceLabel(enc)).toBe("External (epic-vendor-1)");
  });
});

// ---------- ExamSummary — confidence + missing-data rendering ----------

const baseFindings = {
  id: 1,
  encounter_id: 42,
  input_id: null,
  chief_complaint: "Floaters OD",
  hpi_summary: "Two weeks of new floaters in the right eye.",
  visual_acuity_od: "20/25",
  visual_acuity_os: "20/20",
  iop_od: "16",
  iop_os: "15",
  structured_json: {
    diagnoses: ["PVD OD"],
    plan: "Reassure, RTC 4 weeks, return sooner for flashes/new floaters",
    follow_up_interval: "4 weeks",
    anterior_segment: "Quiet OU",
    posterior_segment: "Attached retina OU; PVD OD",
  },
  extraction_confidence: "medium" as const,
  created_at: "2026-04-20T10:00:00Z",
};

const baseNote = {
  id: 77,
  encounter_id: 42,
  version_number: 1,
  draft_status: "draft" as const,
  note_format: "plain_text" as const,
  note_text: "Draft note body",
  source_input_id: null,
  extracted_findings_id: 1,
  generated_by: "system" as const,
  provider_review_required: true,
  missing_data_flags: [] as string[],
  signed_at: null,
  signed_by_user_id: null,
  exported_at: null,
  created_at: "2026-04-20T10:00:00Z",
  updated_at: "2026-04-20T10:00:00Z",
};

describe("ExamSummary", () => {
  it("renders VA, IOP, diagnoses, plan, and a confidence badge", () => {
    render(
      <ExamSummary
        findings={baseFindings as any}
        note={baseNote as any}
        patientDisplay="Morgan Lee"
        providerDisplay="Dr. Carter"
      />
    );
    expect(screen.getByTestId("exam-summary")).toBeInTheDocument();
    expect(screen.getByTestId("exam-summary-patient")).toHaveTextContent(
      "Morgan Lee"
    );
    expect(screen.getByTestId("exam-summary-va")).toHaveTextContent("20/25");
    expect(screen.getByTestId("exam-summary-va")).toHaveTextContent("20/20");
    expect(screen.getByTestId("exam-summary-iop")).toHaveTextContent("16");
    expect(screen.getByTestId("exam-summary-iop")).toHaveTextContent("15");
    expect(screen.getByTestId("exam-summary-dx")).toHaveTextContent("PVD OD");
    expect(screen.getByTestId("exam-summary-plan")).toHaveTextContent(
      /RTC 4 weeks/
    );
    expect(screen.getByTestId("exam-summary-confidence")).toHaveAttribute(
      "data-kind",
      "ai-medium"
    );
  });

  it("surfaces a missing-data badge when note.missing_data_flags is non-empty", () => {
    render(
      <ExamSummary
        findings={baseFindings as any}
        note={{ ...baseNote, missing_data_flags: ["iop_missing"] } as any}
        patientDisplay="Morgan Lee"
        providerDisplay="Dr. Carter"
      />
    );
    expect(screen.getByTestId("exam-summary-missing")).toHaveTextContent(
      /Missing · 1/
    );
  });

  it("renders structured ophthalmology segments when present", () => {
    render(
      <ExamSummary
        findings={baseFindings as any}
        note={baseNote as any}
        patientDisplay="Morgan Lee"
        providerDisplay="Dr. Carter"
      />
    );
    expect(
      screen.getByTestId("exam-summary-seg-anterior_segment")
    ).toHaveTextContent(/Quiet OU/);
    expect(
      screen.getByTestId("exam-summary-seg-posterior_segment")
    ).toHaveTextContent(/Attached retina/);
  });

  it("renders '—' honestly when key fields are absent", () => {
    const sparse = {
      ...baseFindings,
      visual_acuity_od: null,
      visual_acuity_os: null,
      iop_od: null,
      iop_os: null,
      structured_json: {},
    };
    render(
      <ExamSummary
        findings={sparse as any}
        note={baseNote as any}
        patientDisplay="Morgan Lee"
        providerDisplay="Dr. Carter"
      />
    );
    expect(screen.getByTestId("exam-summary-va")).toHaveTextContent("—");
    expect(screen.getByTestId("exam-summary-iop")).toHaveTextContent("—");
    expect(screen.getByTestId("exam-summary-plan")).toHaveTextContent("—");
  });

  it("shows the empty-state hint when no findings have been extracted", () => {
    render(
      <ExamSummary
        findings={null}
        note={null}
        patientDisplay="Morgan Lee"
        providerDisplay="Dr. Carter"
      />
    );
    expect(screen.getByTestId("exam-summary-empty")).toHaveTextContent(
      /No findings extracted yet/
    );
  });
});

// ---------- trust kind resolver ----------------------------------------

describe("trustKindForNote", () => {
  it("returns 'signed' for a signed or exported note, regardless of confidence", () => {
    const signed = { ...baseNote, draft_status: "signed" as const };
    const exported = { ...baseNote, draft_status: "exported" as const };
    expect(trustKindForNote(signed as any, baseFindings as any)).toBe("signed");
    expect(trustKindForNote(exported as any, baseFindings as any)).toBe(
      "signed"
    );
  });

  it("returns 'manual' when provider has revised or generator=manual", () => {
    expect(
      trustKindForNote(
        { ...baseNote, generated_by: "manual" as const } as any,
        baseFindings as any
      )
    ).toBe("manual");
    expect(
      trustKindForNote(
        { ...baseNote, draft_status: "revised" as const } as any,
        baseFindings as any
      )
    ).toBe("manual");
  });

  it("maps findings extraction_confidence to ai-high/medium/low", () => {
    expect(
      trustKindForNote(baseNote as any, {
        ...baseFindings,
        extraction_confidence: "high",
      } as any)
    ).toBe("ai-high");
    expect(
      trustKindForNote(baseNote as any, {
        ...baseFindings,
        extraction_confidence: "medium",
      } as any)
    ).toBe("ai-medium");
    expect(
      trustKindForNote(baseNote as any, {
        ...baseFindings,
        extraction_confidence: "low",
      } as any)
    ).toBe("ai-low");
  });

  it("falls back to 'draft' when nothing else is known", () => {
    expect(trustKindForNote(baseNote as any, null)).toBe("draft");
  });
});

// ---------- transcript status helper (UI hardening) --------------------

describe("transcriptStatusHelp", () => {
  it("maps every shipped processing state to a non-empty explanation", () => {
    const states = [
      "queued",
      "processing",
      "completed",
      "failed",
      "needs_review",
    ];
    for (const s of states) {
      const help = transcriptStatusHelp(s);
      expect(help.length).toBeGreaterThan(8);
      expect(help.endsWith(".")).toBe(true);
    }
  });

  it("falls back to a generic explanation for unknown states", () => {
    expect(transcriptStatusHelp("anything_else_really")).toMatch(
      /Transcript state/i
    );
  });
});

// ---------- TrustBadge — data-kind + data-testid contract --------------

describe("TrustBadge", () => {
  it("renders a signed badge with the expected label and kind", () => {
    render(<TrustBadge kind="signed" />);
    const el = screen.getByTestId("trust-badge-signed");
    expect(el).toHaveAttribute("data-kind", "signed");
    expect(el).toHaveTextContent(/Signed · immutable/i);
  });

  it("renders a ai-low badge with an 'AI · low' label", () => {
    render(<TrustBadge kind="ai-low" />);
    const el = screen.getByTestId("trust-badge-ai-low");
    expect(el).toHaveAttribute("data-kind", "ai-low");
    expect(el).toHaveTextContent(/AI · low/i);
  });

  it("accepts a custom label + testId for consumer-specific badges", () => {
    render(
      <TrustBadge
        kind="ai-medium"
        label="Findings · medium"
        testId="custom-badge"
      />
    );
    const el = screen.getByTestId("custom-badge");
    expect(el).toHaveAttribute("data-kind", "ai-medium");
    expect(el).toHaveTextContent(/Findings · medium/i);
  });
});
