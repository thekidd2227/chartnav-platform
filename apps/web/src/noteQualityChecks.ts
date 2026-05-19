// apps/web/src/noteQualityChecks.ts
//
// Rules-based note quality checks for ChartNav's documentation
// workflow. Pure functions only — no DOM, no fetch, no AI, no
// hidden state. Every check is testable with a fixture string.
//
// Design philosophy:
//
//   ChartNav is a workflow layer. Provider review is the source of
//   truth. These checks are **operator-facing guardrails** that flag
//   plausible problems in a draft so a clinician (or a reviewer)
//   does not miss them. They never block, never auto-correct, never
//   hide content, and never replace clinical judgment.
//
//   Severity levels:
//     - "block": the draft should not move to sign-off without the
//       provider acknowledging the flag. UI gates the "ready for
//       sign-off" affordance on these being resolved or
//       acknowledged.
//     - "warn": worth surfacing, but does not block. Examples:
//       missing trailing section, banned-phrase guard.
//     - "info": completeness scoring, low-priority hints.
//
//   None of the rules below are diagnostic AI; they are linters.
//
// What this file does NOT do:
//   - does not diagnose
//   - does not interpret images or vital signs
//   - does not call an LLM
//   - does not write or modify the draft
//   - does not block sign-off on its own — the UI consumes these
//     results and decides what to gate.

export type QualityFlagSeverity = "block" | "warn" | "info";

export type QualityFlagCode =
  | "laterality_conflict"
  | "laterality_mention_no_anchor"
  | "missing_critical_element"
  | "completeness_low"
  | "completeness_partial"
  | "banned_phrase"
  | "contradiction_negation_then_assertion"
  | "duplicate_critical_section"
  | "draft_empty";

export interface QualityFlag {
  code: QualityFlagCode;
  severity: QualityFlagSeverity;
  message: string;
  /** A short user-facing label used for the action chip in the
   *  flags panel (e.g., "Confirm OD/OS"). */
  actionLabel?: string;
  /** Optional region of the draft to highlight in the panel UI.
   *  `start` / `end` are zero-based character offsets into the
   *  draft. Both inclusive of `start`, exclusive of `end`. */
  region?: { start: number; end: number };
}

export interface QualityCheckResult {
  flags: QualityFlag[];
  /** Completeness percent (0–100). Derived from how many of the
   *  required sections (`REQUIRED_SECTIONS` below) are present and
   *  non-empty. Capped at 100. */
  completenessPercent: number;
  /** Convenience boolean: are there any "block" severity flags?
   *  Consumers can use this to gate the "ready for sign-off"
   *  affordance. */
  hasBlockingFlags: boolean;
}

export interface QualityCheckContext {
  /** Encounter laterality if it was set at intake / by the
   *  technician. "OD" / "OS" / "OU" / null. If known, drives the
   *  `laterality_conflict` check. */
  encounterLaterality?: "OD" | "OS" | "OU" | null;
  /** Extracted findings text (from any upstream module). Used by
   *  the contradiction check (rules-based: if the draft says
   *  "no retinal detachment" but the extracted findings string
   *  asserts "retinal detachment", flag it). */
  extractedFindings?: string | null;
  /** Specialty hint so we can scope the required-sections list.
   *  Defaults to "general ophthalmology" if not provided. */
  specialty?:
    | "retina"
    | "glaucoma"
    | "cornea"
    | "cataract"
    | "oculoplastics"
    | "general";
}

/** Required sections per specialty. The completeness score
 *  reflects how many of these section headers are present (case-
 *  insensitive) AND followed by at least one non-blank line of
 *  content. */
const REQUIRED_SECTIONS: Record<
  NonNullable<QualityCheckContext["specialty"]>,
  string[]
> = {
  retina: [
    "Chief complaint",
    "History",
    "Exam",
    "Imaging review",
    "Assessment",
    "Plan",
  ],
  glaucoma: [
    "Chief complaint",
    "History",
    "Exam",
    "Imaging / VF review",
    "Assessment",
    "Plan",
  ],
  cornea: [
    "Chief complaint",
    "History",
    "Exam",
    "Impression",
    "Plan",
  ],
  cataract: [
    "Chief complaint",
    "History",
    "Post-op status",
    "Plan",
  ],
  oculoplastics: [
    "Chief complaint",
    "History",
    "Exam",
    "Impression",
    "Plan",
  ],
  general: [
    "Chief complaint",
    "History",
    "Exam",
    "Assessment",
    "Plan",
  ],
};

/** Phrases that should never appear in a provider-reviewed draft.
 *  ChartNav's claim contract forbids them on the public website;
 *  it would be inconsistent to let them slip into the chart. */
const BANNED_PHRASES: { pattern: RegExp; label: string }[] = [
  { pattern: /\bauto[- ]?graded? DR\b/i, label: "auto-grade DR" },
  { pattern: /\bauto[- ]?interpret(s|ed)?\b/i, label: "auto-interpret" },
  { pattern: /\bautonomous diagnosis\b/i, label: "autonomous diagnosis" },
  { pattern: /\bguaranteed accuracy\b/i, label: "guaranteed accuracy" },
  { pattern: /\bautomatic orders?\b/i, label: "automatic orders" },
  { pattern: /\bautomatic referrals?\b/i, label: "automatic referrals" },
  { pattern: /\bchart fills itself\b/i, label: "chart fills itself" },
  { pattern: /\bnote writes itself\b/i, label: "note writes itself" },
];

/** Laterality tokens we recognise. We deliberately accept both the
 *  formal abbreviations and a handful of common longhand
 *  appearances. The check is conservative — if both OD and OS are
 *  mentioned without an "OU" or "bilateral" anchor and the
 *  encounter laterality is set to a single eye, we flag it for
 *  provider review. */
const LATERALITY_TOKENS = {
  OD: [/\bOD\b/, /\bright eye\b/i],
  OS: [/\bOS\b/, /\bleft eye\b/i],
  OU: [/\bOU\b/, /\bboth eyes\b/i, /\bbilateral\b/i],
};

function matchesAny(text: string, patterns: RegExp[]): boolean {
  return patterns.some((p) => p.test(text));
}

function findFirstMatch(
  text: string,
  pattern: RegExp,
): { start: number; end: number } | null {
  const m = pattern.exec(text);
  if (!m) return null;
  return { start: m.index, end: m.index + m[0].length };
}

/** Detect whether the draft contains a section header (case
 *  insensitive). A header is treated as present if a line starts
 *  with the section name followed by `:` or by a newline within
 *  the next 80 characters. */
function hasSection(text: string, section: string): boolean {
  const lower = text.toLowerCase();
  const needle = section.toLowerCase();
  // Match section header at line start, optionally followed by ":".
  const re = new RegExp(
    `(^|\\n)\\s*${needle.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\b[ \\t]*:?`,
    "i",
  );
  return re.test(lower);
}

/** Detect whether a section header has at least one non-blank line
 *  of content beneath it before the next header / EOF. Used by the
 *  completeness score to ensure a heading isn't just a placeholder.
 *
 *  We need to be careful: the next "section header" on the same
 *  line (e.g., `History: 3 days of floaters`) might LOOK like a
 *  header because it ends in `: <something>`, but it's actually a
 *  one-line section that has its body inline. So we check both:
 *
 *    - a bare header-only line that ENDS in `:` and is short → next
 *      header
 *    - a line that STARTS with one of the known required section
 *      names + `:` → next header (whether or not body follows
 *      inline)
 *
 *  The first check covers `Plan:\n` separators; the second covers
 *  `History: fine\nExam: \n` style where every section is one line.
 *  In both cases, lines following a HEADER+inline-body count
 *  toward that section, not the previous one.
 */
function sectionHasBody(
  text: string,
  section: string,
  knownHeaders: string[] = [],
): boolean {
  const lower = text.toLowerCase();
  const needle = section.toLowerCase().replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  // Find the line containing the header.
  const headerRe = new RegExp(
    `(^|\\n)\\s*${needle}\\b[ \\t]*:?[ \\t]*`,
    "i",
  );
  const m = headerRe.exec(lower);
  if (!m) return false;
  const matchStart = m.index + (m[1] ? m[1].length : 0);
  const matchEnd = m.index + m[0].length;
  // 1. Inline body on the header line: anything non-blank after the
  //    header on the same source line counts as body.
  const sourceLineEnd = text.indexOf("\n", matchEnd);
  const inlineEnd = sourceLineEnd === -1 ? text.length : sourceLineEnd;
  const inline = text.slice(matchEnd, inlineEnd).trim();
  if (inline.length > 0) return true;
  // 2. No inline body — walk subsequent lines. Treat any line that
  //    starts with a known required section header + ":" as the
  //    next section. A bare ":\n" terminator line also counts as a
  //    next header.
  if (sourceLineEnd === -1) return false;
  const after = text.slice(sourceLineEnd + 1);
  const lines = after.split("\n");
  const otherHeaders = knownHeaders.filter(
    (h) => h.toLowerCase() !== section.toLowerCase(),
  );
  for (const raw of lines) {
    const line = raw.trim();
    if (line === "") continue;
    // Is this line a known section header (with or without inline
    // body)?
    const isNextHeader = otherHeaders.some((h) => {
      const escaped = h.toLowerCase().replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      return new RegExp(`^${escaped}\\b[ \\t]*:`, "i").test(line);
    });
    if (isNextHeader) return false;
    // Bare-terminator heuristic: short line ending in `:` with no
    // other content.
    if (line.length <= 60 && /:$/.test(line)) return false;
    // Anything else counts as body.
    return true;
  }
  void matchStart;
  return false;
}

/** Count distinct required sections that are present AND have body
 *  content. Used by the completeness score. */
function completenessCount(
  text: string,
  required: string[],
): number {
  let count = 0;
  for (const s of required) {
    if (hasSection(text, s) && sectionHasBody(text, s, required)) count++;
  }
  return count;
}

/** Detect laterality conflicts:
 *    - draft mentions OD AND OS but no OU / bilateral anchor, while
 *      the encounter is single-eye → flag.
 *    - draft mentions only OD but the encounter is OS (or vice
 *      versa) → flag.
 *    - draft mentions no laterality at all while the encounter
 *      laterality is set → info-level reminder.
 */
function checkLaterality(
  text: string,
  encounterLat: QualityCheckContext["encounterLaterality"],
): QualityFlag[] {
  const flags: QualityFlag[] = [];
  const mentionsOD = matchesAny(text, LATERALITY_TOKENS.OD);
  const mentionsOS = matchesAny(text, LATERALITY_TOKENS.OS);
  const mentionsOU = matchesAny(text, LATERALITY_TOKENS.OU);

  if (encounterLat === "OD" && mentionsOS && !mentionsOU) {
    flags.push({
      code: "laterality_conflict",
      severity: "block",
      message:
        "Encounter laterality is OD, but the draft mentions OS / "
        + "left eye without a bilateral anchor. Confirm before "
        + "sign-off.",
      actionLabel: "Confirm OD/OS",
      region: findFirstMatch(text, LATERALITY_TOKENS.OS[0]) ?? undefined,
    });
  } else if (encounterLat === "OS" && mentionsOD && !mentionsOU) {
    flags.push({
      code: "laterality_conflict",
      severity: "block",
      message:
        "Encounter laterality is OS, but the draft mentions OD / "
        + "right eye without a bilateral anchor. Confirm before "
        + "sign-off.",
      actionLabel: "Confirm OD/OS",
      region: findFirstMatch(text, LATERALITY_TOKENS.OD[0]) ?? undefined,
    });
  } else if (
    encounterLat
    && encounterLat !== "OU"
    && !mentionsOD
    && !mentionsOS
    && !mentionsOU
  ) {
    flags.push({
      code: "laterality_mention_no_anchor",
      severity: "info",
      message:
        `Encounter laterality is ${encounterLat}, but the draft has `
        + "no OD/OS/OU mention. Add an explicit laterality anchor "
        + "where appropriate.",
      actionLabel: "Add laterality",
    });
  }
  return flags;
}

/** Detect rules-based contradictions between the draft and any
 *  extracted findings text. Implementation is intentionally
 *  conservative — we flag clear assertion-vs-negation conflicts on
 *  the same key phrase, not paraphrastic differences. */
function checkContradictions(
  text: string,
  extracted: string | null | undefined,
): QualityFlag[] {
  if (!extracted) return [];
  const flags: QualityFlag[] = [];
  const lowerExtracted = extracted.toLowerCase();
  const lowerDraft = text.toLowerCase();
  const probes = [
    "retinal detachment",
    "retinal tear",
    "vitreous hemorrhage",
    "macular hole",
    "neovascularization",
  ];
  for (const probe of probes) {
    const draftAsserts = new RegExp(
      `(?:^|[^a-z])${probe}(?![a-z])`,
      "i",
    ).test(text) && !new RegExp(
      `(?:no|without|negative for)\\s+${probe}`,
      "i",
    ).test(text);
    const extractedNegates = new RegExp(
      `(?:no|without|negative for)\\s+${probe}`,
      "i",
    ).test(lowerExtracted);
    const draftNegates = new RegExp(
      `(?:no|without|negative for)\\s+${probe}`,
      "i",
    ).test(lowerDraft);
    const extractedAsserts = new RegExp(
      `(?:^|[^a-z])${probe}(?![a-z])`,
      "i",
    ).test(extracted) && !extractedNegates;

    if (draftAsserts && extractedNegates) {
      flags.push({
        code: "contradiction_negation_then_assertion",
        severity: "warn",
        message:
          `Draft asserts "${probe}" but the upstream findings text `
          + "negates it. Reconcile before sign-off.",
        actionLabel: `Reconcile ${probe}`,
        region: findFirstMatch(text, new RegExp(probe, "i")) ?? undefined,
      });
    } else if (draftNegates && extractedAsserts) {
      flags.push({
        code: "contradiction_negation_then_assertion",
        severity: "warn",
        message:
          `Draft negates "${probe}" but the upstream findings text `
          + "asserts it. Reconcile before sign-off.",
        actionLabel: `Reconcile ${probe}`,
        region: findFirstMatch(text, new RegExp(`no\\s+${probe}`, "i")) ?? undefined,
      });
    }
  }
  return flags;
}

/** Banned-phrase guard. Mirrors the public-website claims contract:
 *  the chart should never contain "autonomous diagnosis", "auto-
 *  grade DR", "chart fills itself", etc. — even in a clinician's
 *  own free text. Warn-only; the provider decides. */
function checkBannedPhrases(text: string): QualityFlag[] {
  const flags: QualityFlag[] = [];
  for (const { pattern, label } of BANNED_PHRASES) {
    const region = findFirstMatch(text, pattern);
    if (region) {
      flags.push({
        code: "banned_phrase",
        severity: "warn",
        message:
          `Draft contains "${label}" — this phrase is on the `
          + "ChartNav safe-claims contract. Rephrase before "
          + "sign-off.",
        actionLabel: "Rephrase",
        region,
      });
    }
  }
  return flags;
}

/** Duplicate-section guard: if a draft repeats a critical section
 *  header (e.g., two "Plan:" headers), flag it. */
function checkDuplicateSections(
  text: string,
  required: string[],
): QualityFlag[] {
  const flags: QualityFlag[] = [];
  const lower = text.toLowerCase();
  for (const s of required) {
    const escaped = s.toLowerCase().replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const re = new RegExp(`(^|\\n)\\s*${escaped}\\b[ \\t]*:`, "gi");
    let count = 0;
    while (re.exec(lower) !== null) count++;
    if (count > 1) {
      flags.push({
        code: "duplicate_critical_section",
        severity: "warn",
        message:
          `Draft has ${count} "${s}" section headers. Merge them so `
          + "there is one canonical section per chart record.",
        actionLabel: "Merge sections",
      });
    }
  }
  return flags;
}

/** Top-level entry point. Pure function; the UI calls this on every
 *  draft change (or on every save, depending on cadence) and renders
 *  the returned `flags` + `completenessPercent`. */
export function runNoteQualityChecks(
  draftText: string,
  context: QualityCheckContext = {},
): QualityCheckResult {
  const specialty = context.specialty ?? "general";
  const required = REQUIRED_SECTIONS[specialty];
  const flags: QualityFlag[] = [];

  // 1. Empty draft.
  if (!draftText || draftText.trim().length === 0) {
    flags.push({
      code: "draft_empty",
      severity: "info",
      message:
        "Draft is empty. Insert a specialty template or start "
        + "typing to begin.",
    });
    return { flags, completenessPercent: 0, hasBlockingFlags: false };
  }

  // 2. Missing critical-element flags.
  for (const section of required) {
    if (!hasSection(draftText, section)) {
      flags.push({
        code: "missing_critical_element",
        severity: "warn",
        message:
          `Required section "${section}" is missing. Add it before `
          + "sign-off (the reviewer cannot infer it from context).",
        actionLabel: `Add ${section}`,
      });
    }
  }

  // 3. Completeness scoring.
  const present = completenessCount(draftText, required);
  const completenessPercent = Math.round(
    (present / Math.max(1, required.length)) * 100,
  );
  if (completenessPercent < 60) {
    flags.push({
      code: "completeness_low",
      severity: "warn",
      message:
        `Note is ${completenessPercent}% complete (${present} of `
        + `${required.length} required sections). Provider sign-off `
        + "expected after the missing sections are filled.",
    });
  } else if (completenessPercent < 100) {
    flags.push({
      code: "completeness_partial",
      severity: "info",
      message:
        `Note is ${completenessPercent}% complete (${present} of `
        + `${required.length} required sections).`,
    });
  }

  // 4. Laterality.
  flags.push(...checkLaterality(draftText, context.encounterLaterality));

  // 5. Contradictions.
  flags.push(...checkContradictions(draftText, context.extractedFindings));

  // 6. Banned phrases.
  flags.push(...checkBannedPhrases(draftText));

  // 7. Duplicate critical sections.
  flags.push(...checkDuplicateSections(draftText, required));

  const hasBlockingFlags = flags.some((f) => f.severity === "block");
  return { flags, completenessPercent, hasBlockingFlags };
}

/** Convenience grouping for the UI: counts per severity. */
export function severityCounts(
  result: QualityCheckResult,
): Record<QualityFlagSeverity, number> {
  return result.flags.reduce(
    (acc, f) => {
      acc[f.severity]++;
      return acc;
    },
    { block: 0, warn: 0, info: 0 } as Record<QualityFlagSeverity, number>,
  );
}
