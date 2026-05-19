/**
 * Phase 14 — Pilot readiness / claims docs test.
 *
 * Asserts the eight pilot docs (plus the top-level Phase 14
 * contract) exist on disk, contain the required headings, and
 * obey the safe-pilot-language contract:
 *   - forbidden positive claims appear only inside safe contexts
 *     (negative-assertion lines, enumerated forbidden-phrase
 *     lists, or Q&A question headings whose answers are negative
 *     assertions);
 *   - the pilot readiness checklist explicitly states
 *     "real PHI only after proper agreements / security review"
 *     or equivalent;
 *   - the pilot readiness checklist explicitly states the
 *     provider-review requirement.
 *
 * This file is a docs-only test — no UI is rendered. We piggyback
 * on the same context-aware classifier shape used by the Phase 13
 * `DemoClinicalWorkflowPackage.test.tsx` so the rules stay
 * consistent across phases.
 */

import { readFileSync } from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";

const REPO_ROOT = path.resolve(__dirname, "../../../..");

const PILOT_DOCS = [
  "docs/chartnav-pilot-readiness-deployment-hardening.md",
  "docs/pilot/chartnav-pilot-readiness-checklist.md",
  "docs/pilot/chartnav-pilot-deployment-guide.md",
  "docs/pilot/chartnav-admin-onboarding-checklist.md",
  "docs/pilot/chartnav-security-review-packet.md",
  "docs/pilot/chartnav-support-runbook.md",
  "docs/pilot/chartnav-demo-to-pilot-transition-plan.md",
  "docs/pilot/chartnav-known-limitations-and-non-goals.md",
  "docs/pilot/chartnav-pilot-success-metrics.md",
];

const REQUIRED_HEADINGS: Record<string, RegExp[]> = {
  "docs/chartnav-pilot-readiness-deployment-hardening.md": [
    /^#\s+ChartNav Pilot Readiness \/ Deployment Hardening/m,
    /^##\s+Audience/m,
    /^##\s+Docs produced/m,
    /^##\s+Readiness tests/m,
    /^##\s+What was hardened/m,
    /^##\s+What was intentionally not built/m,
    /^##\s+How this relates to Phase 15/m,
  ],
  "docs/pilot/chartnav-pilot-readiness-checklist.md": [
    /^#\s+ChartNav Pilot Readiness Checklist/m,
    /^##\s+Product scope/m,
    /^##\s+Demo \/ pilot data policy/m,
    /^##\s+Provider-review boundaries/m,
    /^##\s+Roles and permissions/m,
    /^##\s+Security review/m,
    /^##\s+Audit logging/m,
    /^##\s+Exit criteria for a pilot/m,
  ],
  "docs/pilot/chartnav-pilot-deployment-guide.md": [
    /^#\s+ChartNav Pilot Deployment Guide/m,
    /^##\s+Deployment modes/m,
    /^##\s+Environment variables/m,
    /^##\s+Local demo deployment/m,
    /^##\s+Staging pilot deployment/m,
    /^##\s+Controlled-pilot deployment/m,
    /^##\s+Smoke test checklist/m,
    /^##\s+Rollback checklist/m,
  ],
  "docs/pilot/chartnav-admin-onboarding-checklist.md": [
    /^#\s+ChartNav Admin \/ User Onboarding Checklist/m,
    /^##\s+Phase 1 — Org setup/m,
    /^##\s+Phase 7 — What to do BEFORE using real patient data/m,
    /^##\s+Phase 9 — What NOT to do during the pilot/m,
  ],
  "docs/pilot/chartnav-security-review-packet.md": [
    /^#\s+ChartNav Security Review Packet/m,
    /^##\s+Provider-in-the-loop model/m,
    /^##\s+Audit logging overview/m,
    /^##\s+PHI \/ audit redaction posture/m,
    /^##\s+Org isolation posture/m,
    /^##\s+Role-based access posture/m,
    /^##\s+Items requiring legal \/ security review before PHI/m,
    /^##\s+BAA \/ HIPAA language caution/m,
  ],
  "docs/pilot/chartnav-support-runbook.md": [
    /^#\s+ChartNav Support Runbook/m,
    /^##\s+Severity levels/m,
    /^##\s+Support workflow/m,
    /^##\s+Data-safety incident escalation/m,
    /^##\s+Rollback \/ disable pilot/m,
  ],
  "docs/pilot/chartnav-demo-to-pilot-transition-plan.md": [
    /^#\s+ChartNav Demo-to-Pilot Transition Plan/m,
    /^##\s+Step 3 — Pilot qualification checklist/m,
    /^##\s+Step 4 — Pilot agreement checklist/m,
    /^##\s+Step 5 — Technical readiness checklist/m,
    /^##\s+Step 9 — Post-pilot decision framework/m,
  ],
  "docs/pilot/chartnav-known-limitations-and-non-goals.md": [
    /^#\s+ChartNav Known Limitations and Non-Goals/m,
    /^##\s+What ChartNav is not/m,
    /^##\s+What ChartNav does not do/m,
    /^##\s+v1 generator limitations/m,
    /^##\s+What is deferred/m,
  ],
  "docs/pilot/chartnav-pilot-success-metrics.md": [
    /^#\s+ChartNav Pilot Success Metrics/m,
    /^##\s+Metric catalogue/m,
    /^##\s+Conversion criteria — paid pilot \/ paid customer/m,
    /^##\s+What this template does NOT promise/m,
  ],
};

const FORBIDDEN_POSITIVE_CLAIMS: { name: string; pattern: RegExp }[] = [
  { name: "HIPAA compliant", pattern: /\bhipaa[ -]compliant\b/i },
  { name: "HIPAA certified", pattern: /\bhipaa[ -]certified\b/i },
  { name: "SOC 2 certified", pattern: /\bsoc[ -]?2[ -]?certified\b/i },
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
  {
    name: "production-ready for PHI",
    pattern: /\bproduction[- ]ready for phi\b/i,
  },
];

/**
 * A line is a "safe context" for a forbidden claim if it is clearly
 * a negative assertion, an enumerated forbidden-phrase entry, a
 * buyer-Q&A question heading whose answer is a negative assertion,
 * or guidance that explicitly tells the reader to use a different
 * phrase instead.
 */
function isSafeNegativeContext(
  line: string,
  lines: string[] = [],
  idx: number = -1
): boolean {
  // Strip markdown bold/italic markers so word-boundary matches
  // catch `**not**` and `*not*` forms.
  const stripped = line.replace(/[*_`]/g, "");
  const lower = stripped.toLowerCase();
  if (
    /\bdoes not\b/.test(lower) ||
    /\b(?:is|are|was|were|am)\s+not\b/.test(lower) ||
    /\bnot a(n)? \b/.test(lower) ||
    /\bnever\b/.test(lower) ||
    /\bno [\w-]+ surface exists\b/.test(lower) ||
    /\bnot[ -]+by[ -]+default\b/.test(lower) ||
    // Bullet / sentence starting with "Not" after markdown-strip
    // (e.g., "- Not production-ready for PHI by default.").
    /^\s*(?:[-*]\s*)?not\b/.test(lower) ||
    // "no autonomous diagnosis", "no automatic orders" — comma-list
    // style negative enumeration. Cheap heuristic: a `no ` token
    // appears somewhere on the line and the line has no positive
    // verb like "claims", "promises", "guarantees".
    (/\bno\b/.test(lower) &&
      !/\bis (?:hipaa|certified|production)\b/.test(lower) &&
      !/\b(?:claims|promises|guarantees)\b/.test(lower))
  ) {
    return true;
  }
  if (
    /forbidden|do not say|never (?:claim|use|say)|never appear|never\b/i.test(
      line
    )
  ) {
    return true;
  }
  // Bullet-style entries that are themselves quoted forbidden phrases.
  if (/^\s*[-*]\s*"/.test(line) || /^\s*[-*]\s*\b/.test(line)) {
    return true;
  }
  // Numbered list entries inside a deferred / forbidden enumeration.
  if (/^\s*\d+\.\s+/.test(line)) return true;
  // "Use *X* instead" style guidance.
  if (/\buse\b.+\binstead\b/i.test(line)) return true;
  // Markdown question heading — the answer follows.
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
  // Headers introducing a list of forbidden / deferred items —
  // accept any heading whose text contains "forbidden", "do not",
  // "deferred", "non-goals", "what chartnav is not", "what chartnav
  // does not do", or "what not to claim".
  if (
    /^#{1,6}\s+/.test(line) &&
    /(forbidden|do not|deferred|non[- ]goals?|what chartnav (?:is not|does not)|what not to claim|what this template does not|exit criteria|requires legal|gating items)/i.test(
      line
    )
  ) {
    return true;
  }
  // Table-row entries in a forbidden / deferred table.
  if (/^\s*\|/.test(line)) return true;
  return false;
}

describe("Pilot readiness — docs exist + required headings", () => {
  it("all pilot docs exist on disk", () => {
    for (const rel of PILOT_DOCS) {
      const full = path.join(REPO_ROOT, rel);
      expect(() => readFileSync(full, "utf-8")).not.toThrow();
    }
  });

  it("each pilot doc includes the required headings", () => {
    for (const [rel, patterns] of Object.entries(REQUIRED_HEADINGS)) {
      const text = readFileSync(path.join(REPO_ROOT, rel), "utf-8");
      for (const p of patterns) {
        expect(text, `Missing heading ${p} in ${rel}`).toMatch(p);
      }
    }
  });
});

describe("Pilot readiness — forbidden-claim docs scan", () => {
  it("forbidden positive claims appear only in safe contexts", () => {
    for (const rel of PILOT_DOCS) {
      const text = readFileSync(path.join(REPO_ROOT, rel), "utf-8");
      const lines = text.split(/\r?\n/);
      for (const claim of FORBIDDEN_POSITIVE_CLAIMS) {
        const matches = lines
          .map((line, idx) => ({ line, idx }))
          .filter(({ line }) => claim.pattern.test(line));
        for (const { line, idx } of matches) {
          if (!isSafeNegativeContext(line, lines, idx)) {
            // Look at the immediately preceding non-blank line for
            // additional context (e.g., a section header that
            // introduces a list of forbidden items).
            const prevIdx = lines
              .slice(0, idx)
              .map((s, i) => ({ s, i }))
              .reverse()
              .find(({ s }) => s.trim().length > 0)?.i;
            const safe =
              prevIdx !== undefined &&
              isSafeNegativeContext(lines[prevIdx], lines, prevIdx);
            expect(
              safe,
              `In ${rel} line ${idx + 1}: forbidden claim "${
                claim.name
              }" appears outside a negative-assertion / forbidden-list / Q&A-answer context: ${line}`
            ).toBe(true);
          }
        }
      }
    }
  });

  it("no doc claims ChartNav diagnoses, orders, codes, refers, or messages patients positively", () => {
    const positiveAssertions = [
      /\bchartnav\b[^.\n]*\bdiagnoses\b/i,
      /\bchartnav\b[^.\n]*\bplaces orders?\b/i,
      /\bchartnav\b[^.\n]*\bsubmits referrals?\b/i,
      /\bchartnav\b[^.\n]*\bcodes (?:visits|encounters|claims)\b/i,
      /\bchartnav\b[^.\n]*\bbills\s+(?!automatically)/i,
      /\bchartnav\b[^.\n]*\bautomatically (?:diagnoses|orders|sends|messages)/i,
    ];
    for (const rel of PILOT_DOCS) {
      const text = readFileSync(path.join(REPO_ROOT, rel), "utf-8");
      const lines = text.split(/\r?\n/);
      for (const p of positiveAssertions) {
        for (let idx = 0; idx < lines.length; idx++) {
          const line = lines[idx];
          if (p.test(line) && !isSafeNegativeContext(line, lines, idx)) {
            expect(
              false,
              `In ${rel} line ${idx + 1}: positive claim about ChartNav doing the forbidden thing: ${line}`
            ).toBe(true);
          }
        }
      }
    }
  });
});

describe("Pilot readiness — required content guarantees", () => {
  it("the readiness checklist explicitly gates real PHI on agreements / security review", () => {
    const text = readFileSync(
      path.join(
        REPO_ROOT,
        "docs/pilot/chartnav-pilot-readiness-checklist.md"
      ),
      "utf-8"
    );
    // At least one statement that ties real-PHI use to a written
    // agreement plus a security review gate.
    expect(
      /real phi[\s\S]{0,200}agreement[\s\S]{0,200}security review|written agreement[\s\S]{0,200}security review[\s\S]{0,200}real phi/i.test(
        text
      ) ||
        /BAA[\s\S]{0,400}security review/i.test(text),
      "expected the pilot readiness checklist to gate real PHI on agreements + security review"
    ).toBe(true);
  });

  it("the readiness checklist explicitly states the provider-review requirement", () => {
    const text = readFileSync(
      path.join(
        REPO_ROOT,
        "docs/pilot/chartnav-pilot-readiness-checklist.md"
      ),
      "utf-8"
    );
    expect(
      /provider[- ]review/i.test(text) &&
        /every clinical artifact in chartnav is provider[- ]reviewed|provider-review boundaries/i.test(
          text
        ),
      "expected the pilot readiness checklist to state the provider-review requirement"
    ).toBe(true);
  });

  it("the security packet explicitly enumerates items requiring legal / security review before PHI", () => {
    const text = readFileSync(
      path.join(
        REPO_ROOT,
        "docs/pilot/chartnav-security-review-packet.md"
      ),
      "utf-8"
    );
    expect(
      /items requiring legal \/ security review before phi/i.test(text),
      "expected the security packet to enumerate gating items"
    ).toBe(true);
    expect(
      /\bBAA\b/i.test(text),
      "expected the security packet to mention BAA"
    ).toBe(true);
  });

  it("the limitations doc states ChartNav is not a certified EHR and does not diagnose autonomously", () => {
    const text = readFileSync(
      path.join(
        REPO_ROOT,
        "docs/pilot/chartnav-known-limitations-and-non-goals.md"
      ),
      "utf-8"
    );
    expect(/not a certified ehr/i.test(text)).toBe(true);
    expect(
      /does not diagnose autonomously|not autonomous diagnosis|provider diagnoses/i.test(
        text
      )
    ).toBe(true);
  });

  it("the success-metrics doc disclaims fake numeric promises", () => {
    const text = readFileSync(
      path.join(
        REPO_ROOT,
        "docs/pilot/chartnav-pilot-success-metrics.md"
      ),
      "utf-8"
    );
    expect(
      /what this template does not promise|does not promise[\s\S]{0,200}numeric|no.*headline numbers|placeholder/i.test(
        text
      )
    ).toBe(true);
  });
});
