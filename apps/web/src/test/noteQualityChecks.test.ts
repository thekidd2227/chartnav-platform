// noteQualityChecks.test.ts
//
// Pure-function tests for the rules-based note quality linter.
// Covers:
//   - empty draft → single `draft_empty` info flag, 0% complete
//   - missing critical elements → one warn per missing section
//   - completeness scoring + boundary conditions
//   - laterality conflict (OD encounter vs OS draft mention)
//   - laterality missing anchor (info-level reminder)
//   - banned-phrase guard
//   - duplicate critical section
//   - contradiction guard (draft asserts X, extracted negates X)
//
// All checks are pure functions, so tests do not need mocks, DOM,
// or async setup.

import { describe, expect, it } from "vitest";
import {
  runNoteQualityChecks,
  severityCounts,
  type QualityFlagCode,
} from "../noteQualityChecks";

function codes(result: ReturnType<typeof runNoteQualityChecks>): QualityFlagCode[] {
  return result.flags.map((f) => f.code);
}

describe("noteQualityChecks — empty / minimal", () => {
  it("returns draft_empty + 0% completeness on an empty draft", () => {
    const r = runNoteQualityChecks("");
    expect(codes(r)).toEqual(["draft_empty"]);
    expect(r.completenessPercent).toBe(0);
    expect(r.hasBlockingFlags).toBe(false);
  });

  it("returns draft_empty on a whitespace-only draft", () => {
    const r = runNoteQualityChecks("   \n\n   ");
    expect(codes(r)).toEqual(["draft_empty"]);
  });
});

describe("noteQualityChecks — missing critical sections", () => {
  it("flags every missing required section for general specialty", () => {
    const r = runNoteQualityChecks(
      "Chief complaint: blurry vision\nbody here.\n",
    );
    const missing = r.flags.filter((f) => f.code === "missing_critical_element");
    // General requires Chief complaint, History, Exam, Assessment, Plan.
    // Only Chief complaint is present → 4 flags.
    expect(missing.length).toBe(4);
    expect(missing.map((f) => f.message).join(" ")).toMatch(/History/);
    expect(missing.map((f) => f.message).join(" ")).toMatch(/Exam/);
    expect(missing.map((f) => f.message).join(" ")).toMatch(/Plan/);
  });

  it("does not flag a section that has only the header but no body as present", () => {
    // A header line with no follow-on body counts as not-present
    // for completeness purposes.
    const r = runNoteQualityChecks(
      "Chief complaint:\nHistory: fine\nExam:\nAssessment: fine\nPlan: fine\n",
      { specialty: "general" },
    );
    // The completeness counter requires header + body. So Chief
    // complaint and Exam are present-as-header but no body → both
    // counted as incomplete for the scoring step. But because the
    // header IS present, `missing_critical_element` is NOT fired
    // for them.
    expect(codes(r)).not.toContain("missing_critical_element");
    // 3 sections fully present → 60%.
    expect(r.completenessPercent).toBe(60);
  });
});

describe("noteQualityChecks — completeness scoring", () => {
  const COMPLETE_GENERAL =
    "Chief complaint:\nblurry vision\n"
    + "History:\n3 days of floaters\n"
    + "Exam:\nvitreous syneresis, no retinal tear\n"
    + "Assessment:\nacute PVD\n"
    + "Plan:\nreturn precautions\n";

  it("reports 100% when every required section has a header + body", () => {
    const r = runNoteQualityChecks(COMPLETE_GENERAL);
    expect(r.completenessPercent).toBe(100);
    expect(codes(r)).not.toContain("completeness_low");
    expect(codes(r)).not.toContain("completeness_partial");
  });

  it("flags completeness_partial between 60 and 99 percent", () => {
    const r = runNoteQualityChecks(
      "Chief complaint:\ncc body\n"
      + "History:\nhx body\n"
      + "Exam:\nexam body\n"
      + "Assessment:\na body\n"
      + "Plan:\n",
    );
    expect(r.completenessPercent).toBe(80);
    expect(codes(r)).toContain("completeness_partial");
  });

  it("flags completeness_low when below 60", () => {
    const r = runNoteQualityChecks("Chief complaint:\nblurry vision\n");
    // Only 1 of 5 sections complete → 20%.
    expect(r.completenessPercent).toBe(20);
    expect(codes(r)).toContain("completeness_low");
  });
});

describe("noteQualityChecks — laterality", () => {
  const HEADERS =
    "Chief complaint: x\nHistory: x\nExam: x\nAssessment: x\nPlan: x\n";

  it("flags laterality_conflict block when encounter is OD but draft mentions OS", () => {
    const r = runNoteQualityChecks(HEADERS + "Patient with OS retinal tear.", {
      encounterLaterality: "OD",
    });
    const block = r.flags.find((f) => f.code === "laterality_conflict");
    expect(block).toBeTruthy();
    expect(block!.severity).toBe("block");
    expect(r.hasBlockingFlags).toBe(true);
  });

  it("flags laterality_conflict block when encounter is OS but draft mentions OD", () => {
    const r = runNoteQualityChecks(
      HEADERS + "Patient with OD retinal tear.",
      { encounterLaterality: "OS" },
    );
    const block = r.flags.find((f) => f.code === "laterality_conflict");
    expect(block).toBeTruthy();
    expect(block!.severity).toBe("block");
  });

  it("does NOT flag a conflict when draft mentions both eyes with bilateral anchor", () => {
    const r = runNoteQualityChecks(
      HEADERS
      + "Mild AMD OU. Drusen visible OD and OS — bilateral findings stable.",
      { encounterLaterality: "OD" },
    );
    expect(codes(r)).not.toContain("laterality_conflict");
  });

  it("info-flags when encounter has single-eye laterality but draft has no anchor", () => {
    const r = runNoteQualityChecks(HEADERS, { encounterLaterality: "OD" });
    expect(codes(r)).toContain("laterality_mention_no_anchor");
  });

  it("does not flag laterality when encounter laterality is null", () => {
    const r = runNoteQualityChecks(HEADERS + "Mention OS only.", {});
    expect(codes(r)).not.toContain("laterality_conflict");
    expect(codes(r)).not.toContain("laterality_mention_no_anchor");
  });
});

describe("noteQualityChecks — banned phrases", () => {
  const HEADERS =
    "Chief complaint: x\nHistory: x\nExam: x\nAssessment: x\nPlan: x\n";

  it("warns when the draft contains autonomous diagnosis", () => {
    const r = runNoteQualityChecks(HEADERS + "Autonomous diagnosis suggests AMD.");
    expect(codes(r)).toContain("banned_phrase");
  });

  it("warns on auto-grade DR", () => {
    const r = runNoteQualityChecks(HEADERS + "Auto-grade DR shows mild NPDR.");
    expect(codes(r)).toContain("banned_phrase");
  });

  it("does not flag when the safe-claims contract phrase is absent", () => {
    const r = runNoteQualityChecks(HEADERS + "Routine DR follow-up.");
    expect(codes(r)).not.toContain("banned_phrase");
  });
});

describe("noteQualityChecks — duplicate critical sections", () => {
  it("flags when a required section header appears twice", () => {
    const r = runNoteQualityChecks(
      "Chief complaint: x\nHistory: x\nExam: x\nAssessment: x\nPlan: a\nPlan: b\n",
    );
    expect(codes(r)).toContain("duplicate_critical_section");
  });
});

describe("noteQualityChecks — contradiction guard", () => {
  const HEADERS =
    "Chief complaint: x\nHistory: x\nExam: x\nAssessment: x\nPlan: x\n";

  it("warns when draft asserts retinal detachment but extracted findings negate it", () => {
    const r = runNoteQualityChecks(
      HEADERS + "Retinal detachment confirmed by exam.",
      {
        extractedFindings: "Scleral depressed exam: no retinal detachment.",
      },
    );
    expect(codes(r)).toContain("contradiction_negation_then_assertion");
  });

  it("warns in the inverse direction (draft negates, extracted asserts)", () => {
    const r = runNoteQualityChecks(
      HEADERS + "No retinal tear noted on exam.",
      {
        extractedFindings: "Findings: retinal tear in superior periphery.",
      },
    );
    expect(codes(r)).toContain("contradiction_negation_then_assertion");
  });

  it("does not flag when assertion/negation are consistent", () => {
    const r = runNoteQualityChecks(
      HEADERS + "No retinal detachment.",
      { extractedFindings: "Findings: no retinal detachment." },
    );
    expect(codes(r)).not.toContain("contradiction_negation_then_assertion");
  });

  it("does not flag when extractedFindings is missing", () => {
    const r = runNoteQualityChecks(HEADERS + "Retinal detachment.", {});
    expect(codes(r)).not.toContain("contradiction_negation_then_assertion");
  });
});

describe("noteQualityChecks — severityCounts", () => {
  it("returns the right totals for a mixed set of flags", () => {
    const r = runNoteQualityChecks(
      "Chief complaint: x\nHistory: x\nExam: x\nAssessment: x\nPlan: x\n"
      + "Patient with OS findings.\n"
      + "Autonomous diagnosis suggests something.\n",
      { encounterLaterality: "OD" },
    );
    const counts = severityCounts(r);
    expect(counts.block).toBeGreaterThanOrEqual(1); // laterality_conflict
    expect(counts.warn).toBeGreaterThanOrEqual(1); // banned_phrase
    expect(counts.block + counts.warn + counts.info).toBe(r.flags.length);
  });
});
