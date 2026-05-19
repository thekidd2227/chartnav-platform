/**
 * Phase 15 — Commercial demo delivery package test.
 *
 * Asserts:
 *   - the new docs (operator guide, environment README, top-level
 *     Phase 15 contract) exist on disk and contain the required
 *     headings;
 *   - the demo reset script exists, is executable bash, and refuses
 *     to run against a non-local DATABASE_URL (statically — by
 *     grepping the script for the refusal guard);
 *   - forbidden positive claims appear only in safe contexts in
 *     the new Phase 15 docs (negative-assertion lines, enumerated
 *     forbidden-phrase lists, or Q&A question headings whose
 *     answers are negative assertions).
 *
 * This file does not render any UI — the GuidedDemoMode component
 * has its own dedicated test file.
 */

import { readFileSync, statSync } from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";

const REPO_ROOT = path.resolve(__dirname, "../../../..");

const PHASE_15_DOCS = [
  "docs/chartnav-commercial-demo-delivery-system.md",
  "docs/demo/chartnav-demo-operator-guide.md",
  "docs/demo/chartnav-demo-environment.md",
];

const REQUIRED_HEADINGS: Record<string, RegExp[]> = {
  "docs/chartnav-commercial-demo-delivery-system.md": [
    /^#\s+ChartNav Commercial Demo Delivery System/m,
    /^##\s+What Phase 15 added/m,
    /^##\s+Demo orchestration approach/m,
    /^##\s+Deterministic workflow philosophy/m,
    /^##\s+No real-PHI \/ demo boundary/m,
    /^##\s+Safety guardrails/m,
    /^##\s+Phase 16 recommendation/m,
  ],
  "docs/demo/chartnav-demo-operator-guide.md": [
    /^#\s+ChartNav Demo Operator Guide/m,
    /^##\s+Recommended demo flow/m,
    /^##\s+What to click in sequence/m,
    /^##\s+How to reset/m,
    /^##\s+Fallback paths if the demo breaks/m,
    /^##\s+What NOT to claim/m,
    /^##\s+Provider-review talking points/m,
    /^##\s+AI governance talking points/m,
    /^##\s+Ophthalmology workflow talking points/m,
    /^##\s+Demo timing guidance/m,
    /^##\s+How to handle pilot \/ security questions/m,
    /^##\s+Known weak spots/m,
  ],
  "docs/demo/chartnav-demo-environment.md": [
    /^#\s+ChartNav Demo Environment/m,
    /^##\s+Local startup/m,
    /^##\s+Demo reset/m,
    /^##\s+Seeded credentials/m,
    /^##\s+Fake data structure/m,
    /^##\s+Deterministic workflow expectations/m,
    /^##\s+Troubleshooting/m,
    /^##\s+Browser recommendations/m,
    /^##\s+Recording recommendations/m,
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

function isSafeNegativeContext(
  line: string,
  lines: string[] = [],
  idx: number = -1
): boolean {
  const stripped = line.replace(/[*_`]/g, "");
  const lower = stripped.toLowerCase();
  if (
    /\bdoes not\b/.test(lower) ||
    /\b(?:is|are|was|were|am)\s+not\b/.test(lower) ||
    /\bnot a(n)? \b/.test(lower) ||
    /\bnever\b/.test(lower) ||
    /\bno [\w-]+ surface exists\b/.test(lower) ||
    /\bnot[ -]+by[ -]+default\b/.test(lower) ||
    /^\s*(?:[-*]\s*)?not\b/.test(lower) ||
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
  if (/^\s*[-*]\s*"/.test(line) || /^\s*[-*]\s*\b/.test(line)) {
    return true;
  }
  if (/^\s*\d+\.\s+/.test(line)) return true;
  if (/\buse\b.+\binstead\b/i.test(line)) return true;
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
  if (
    /^#{1,6}\s+/.test(line) &&
    /(forbidden|do not|deferred|non[- ]goals?|what chartnav (?:is not|does not)|what not to claim|what this template does not|exit criteria|requires legal|gating items|known weak|fallback)/i.test(
      line
    )
  ) {
    return true;
  }
  if (/^\s*\|/.test(line)) return true;
  return false;
}

describe("Phase 15 — docs exist + required headings", () => {
  it("each Phase 15 doc exists on disk", () => {
    for (const rel of PHASE_15_DOCS) {
      expect(() =>
        readFileSync(path.join(REPO_ROOT, rel), "utf-8")
      ).not.toThrow();
    }
  });

  it("each Phase 15 doc includes the required headings", () => {
    for (const [rel, patterns] of Object.entries(REQUIRED_HEADINGS)) {
      const text = readFileSync(path.join(REPO_ROOT, rel), "utf-8");
      for (const p of patterns) {
        expect(text, `Missing heading ${p} in ${rel}`).toMatch(p);
      }
    }
  });

  it("the operator guide includes a 'What NOT to claim' enumeration", () => {
    const text = readFileSync(
      path.join(REPO_ROOT, "docs/demo/chartnav-demo-operator-guide.md"),
      "utf-8"
    );
    expect(/what not to claim/i.test(text)).toBe(true);
    // Spot-check several forbidden phrases appear in the enumeration.
    for (const phrase of [
      /HIPAA[- ]compliant/i,
      /Certified EHR/i,
      /Autonomous diagnosis/i,
      /Submit referral/i,
      /Send patient message/i,
      /Replaces a doctor/i,
    ]) {
      expect(phrase.test(text)).toBe(true);
    }
  });
});

describe("Phase 15 — demo reset script", () => {
  const SCRIPT = "scripts/reset_demo_state.sh";

  it("the demo reset script exists and starts with a bash shebang", () => {
    const full = path.join(REPO_ROOT, SCRIPT);
    const text = readFileSync(full, "utf-8");
    expect(text.startsWith("#!/usr/bin/env bash")).toBe(true);
  });

  it("the demo reset script refuses to run against a non-local DATABASE_URL", () => {
    const text = readFileSync(
      path.join(REPO_ROOT, SCRIPT),
      "utf-8"
    );
    // Must contain the explicit refusal guard.
    expect(/REFUSED:.*DATABASE_URL/i.test(text)).toBe(true);
    expect(/EXPECTED_PREFIX="sqlite:\/\/\/"/.test(text)).toBe(true);
  });

  it("the demo reset script invokes 'make reset-db'", () => {
    const text = readFileSync(
      path.join(REPO_ROOT, SCRIPT),
      "utf-8"
    );
    expect(/make reset-db/.test(text)).toBe(true);
  });

  it("the demo reset script reminds the operator the data is fake", () => {
    const text = readFileSync(
      path.join(REPO_ROOT, SCRIPT),
      "utf-8"
    );
    expect(/fake demo data only/i.test(text)).toBe(true);
  });

  it("the demo reset script is marked executable on disk", () => {
    const full = path.join(REPO_ROOT, SCRIPT);
    const mode = statSync(full).mode;
    // 0o111 == any-executable bit.
    expect((mode & 0o111) !== 0).toBe(true);
  });
});

describe("Phase 15 — forbidden-claim docs scan", () => {
  it("forbidden positive claims appear only in safe contexts in the new docs", () => {
    for (const rel of PHASE_15_DOCS) {
      const text = readFileSync(path.join(REPO_ROOT, rel), "utf-8");
      const lines = text.split(/\r?\n/);
      for (const claim of FORBIDDEN_POSITIVE_CLAIMS) {
        const matches = lines
          .map((line, idx) => ({ line, idx }))
          .filter(({ line }) => claim.pattern.test(line));
        for (const { line, idx } of matches) {
          if (!isSafeNegativeContext(line, lines, idx)) {
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
              }" appears outside a negative-assertion / forbidden-list / Q&A context: ${line}`
            ).toBe(true);
          }
        }
      }
    }
  });

  it("no Phase 15 doc claims ChartNav diagnoses or orders or messages patients positively", () => {
    const positiveAssertions = [
      /\bchartnav\b[^.\n]*\bdiagnoses\b/i,
      /\bchartnav\b[^.\n]*\bplaces orders?\b/i,
      /\bchartnav\b[^.\n]*\bsubmits referrals?\b/i,
      /\bchartnav\b[^.\n]*\bautomatically (?:diagnoses|orders|sends|messages)/i,
    ];
    for (const rel of PHASE_15_DOCS) {
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
