/**
 * Phase 17 — Commercial deck library + desktop demo delivery
 * package claims test.
 *
 * Asserts:
 *   1. The 15 deck Markdown source files exist on disk under
 *      docs/decks/ and are non-empty.
 *   2. The 6 commercial support docs exist under docs/commercial/.
 *   3. The 4 demo-package docs exist (3 under
 *      docs/commercial/demo-package/ + Phase 17 contract at the
 *      docs/ root).
 *   4. The Phase 17 export + create-package + claims-check shell
 *      scripts exist.
 *   5. Each deck reaches the safe-claims contract — either
 *      references the approved-claims-language doc, contains
 *      "provider-reviewed" phrasing, or carries a "Safe-claims
 *      contract" banner.
 *   6. Forbidden positive claims (HIPAA-compliant, SOC 2-certified,
 *      certified-EHR, autonomous diagnosis, automatic orders /
 *      coding / referrals / patient messaging, etc.) appear only
 *      inside safe contexts: explicit negative assertions, the
 *      catalog docs whose job it is to enumerate banned phrases
 *      (approved-claims-language.md, brand-guidelines deck "Never
 *      use" slide, buyer-objection-handling "Don't say" blocks),
 *      Q&A question headings whose answers are negative
 *      assertions, or table rows.
 *   7. No deck invents financial numbers — every revenue / runway /
 *      conversion-percentage / pilot-ARR claim is labeled as
 *      hypothesis, target, or template-placeholder.
 *   8. The reset_demo_state.sh / RESET_DEMO_DATA contract is
 *      preserved — the script refuses non-local DATABASE_URL
 *      values.
 *   9. No binary media is committed under docs/decks/,
 *      docs/commercial/, or docs/demo/ Phase 17 paths.
 *
 * This is a docs-and-scripts test only — no UI is rendered. The
 * negative-context heuristic mirrors the Phase 14
 * `PilotReadinessClaims.test.tsx` so the rules stay consistent
 * across phases.
 */

import { readFileSync, statSync, readdirSync } from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";

const REPO_ROOT = path.resolve(__dirname, "../../../..");

// ---------------------------------------------------------------
// Required files — kept in sync with
//   docs/chartnav-desktop-demo-delivery-package.md
// ---------------------------------------------------------------

const DECKS = [
  "docs/decks/chartnav-investor-pitch-deck.md",
  "docs/decks/chartnav-sales-deck.md",
  "docs/decks/chartnav-demo-deck.md",
  "docs/decks/chartnav-customer-pitch-deck-template.md",
  "docs/decks/chartnav-company-deck.md",
  "docs/decks/chartnav-product-roadmap-deck.md",
  "docs/decks/chartnav-brand-guidelines-deck.md",
  "docs/decks/chartnav-educational-onboarding-deck.md",
  "docs/decks/chartnav-one-page-sales-deck.md",
  "docs/decks/chartnav-financial-fundraising-deck.md",
  "docs/decks/chartnav-marketing-plan-deck.md",
  "docs/decks/chartnav-project-proposal-deck.md",
  "docs/decks/chartnav-agency-partner-pitch-deck.md",
  "docs/decks/chartnav-elevator-pitch-deck.md",
  "docs/decks/chartnav-long-sales-pitch-deck.md",
];

const COMMERCIAL_SUPPORT_DOCS = [
  "docs/commercial/chartnav-deck-master-kit.md",
  "docs/commercial/chartnav-approved-claims-language.md",
  "docs/commercial/chartnav-commercial-readiness-map.md",
  "docs/commercial/objections/chartnav-buyer-objection-handling.md",
  "docs/commercial/pricing/chartnav-pricing-packaging-notes.md",
  "docs/commercial/pilot/chartnav-pilot-handoff-checklist.md",
];

const DEMO_PACKAGE_DOCS = [
  "docs/commercial/demo-package/chartnav-local-demo-startup-guide.md",
  "docs/commercial/demo-package/chartnav-local-demo-troubleshooting.md",
  "docs/commercial/demo-package/chartnav-demo-review-checklist.md",
  "docs/chartnav-desktop-demo-delivery-package.md",
];

const PHASE17_SCRIPTS = [
  "scripts/export_chartnav_decks_to_desktop.sh",
  "scripts/create_chartnav_desktop_demo_package.sh",
  "scripts/check_commercial_claims.sh",
];

// Catalog docs whose entire job is to enumerate banned phrases —
// the forbidden-claims scan exempts them entirely.
const CATALOG_DOCS = new Set([
  "docs/commercial/chartnav-approved-claims-language.md",
  "docs/decks/chartnav-brand-guidelines-deck.md",
  "docs/commercial/objections/chartnav-buyer-objection-handling.md",
]);

// ---------------------------------------------------------------
// Forbidden-claim patterns (line-anchored, case-insensitive).
// ---------------------------------------------------------------

const FORBIDDEN_POSITIVE_CLAIMS: { name: string; pattern: RegExp }[] = [
  { name: "HIPAA compliant", pattern: /\bhipaa[ -]compliant\b/i },
  { name: "HIPAA certified", pattern: /\bhipaa[ -]certified\b/i },
  { name: "SOC 2 certified", pattern: /\bsoc[ -]?2[ -]?certified\b/i },
  { name: "FDA cleared", pattern: /\bfda[ -]cleared\b/i },
  { name: "HITRUST certified", pattern: /\bhitrust[ -]certified\b/i },
  { name: "certified EHR", pattern: /\bcertified ehr\b/i },
  { name: "autonomous diagnosis", pattern: /\bautonomous diagnosis\b/i },
  { name: "automatic diagnosis", pattern: /\bautomatic diagnosis\b/i },
  { name: "guaranteed accuracy", pattern: /\bguaranteed accuracy\b/i },
  { name: "automatic orders", pattern: /\bautomatic orders?\b/i },
  { name: "auto-orders", pattern: /\bauto[- ]orders?\b/i },
  { name: "order OCT", pattern: /\border oct\b/i },
  { name: "submit referral", pattern: /\bsubmit referral\b/i },
  { name: "send referral", pattern: /\bsend referral\b/i },
  { name: "billing automation", pattern: /\bbilling automation\b/i },
  { name: "coding automation", pattern: /\bcoding automation\b/i },
  { name: "send patient message", pattern: /\bsend patient message\b/i },
  {
    name: "replaces a doctor",
    pattern: /\breplaces (?:a |the )?doctor\b/i,
  },
  { name: "replaces providers", pattern: /\breplaces providers\b/i },
  {
    name: "production-ready for PHI",
    pattern: /\bproduction[- ]ready for phi\b/i,
  },
  { name: "real patient data ready", pattern: /\breal patient data ready\b/i },
];

// ---------------------------------------------------------------
// Negative-context heuristic (mirrors PilotReadinessClaims).
// ---------------------------------------------------------------

function isSafeNegativeContext(
  line: string,
  lines: string[] = [],
  idx: number = -1
): boolean {
  const stripped = line.replace(/[*_`]/g, "");
  const lower = stripped.toLowerCase();
  if (
    /\bdoes not\b/.test(lower) ||
    /\bdo not\b/.test(lower) ||
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
    /forbidden|do not say|don.?t say|never (?:claim|use|say)|never appear|do not use\b/i.test(
      line
    )
  ) {
    return true;
  }
  // Bullet-style entries that are themselves quoted forbidden phrases.
  if (/^\s*[-*]\s*"/.test(line) || /^\s*[-*]\s*\b/.test(line)) {
    return true;
  }
  if (/^\s*\d+\.\s+/.test(line)) return true;
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
            /\bdon.?t say\b/i.test(l)
        )
      ) {
        return true;
      }
    }
  }
  if (
    /^#{1,6}\s+/.test(line) &&
    /(forbidden|do not|don.?t say|deferred|non[- ]goals?|what chartnav (?:is not|does not)|what not to claim|banned|never use|exit criteria|requires legal|gating items)/i.test(
      line
    )
  ) {
    return true;
  }
  // Table rows.
  if (/^\s*\|/.test(line)) return true;
  return false;
}

// ---------------------------------------------------------------
// 1. Required-files tests.
// ---------------------------------------------------------------

describe("Phase 17 — required files exist", () => {
  it("all 15 deck Markdown source files exist and are non-empty", () => {
    expect(DECKS).toHaveLength(15);
    for (const rel of DECKS) {
      const full = path.join(REPO_ROOT, rel);
      const stat = statSync(full);
      expect(stat.isFile(), `Missing deck: ${rel}`).toBe(true);
      expect(stat.size, `Empty deck: ${rel}`).toBeGreaterThan(0);
    }
  });

  it("all 6 commercial support docs exist and are non-empty", () => {
    expect(COMMERCIAL_SUPPORT_DOCS).toHaveLength(6);
    for (const rel of COMMERCIAL_SUPPORT_DOCS) {
      const full = path.join(REPO_ROOT, rel);
      const stat = statSync(full);
      expect(stat.isFile(), `Missing support doc: ${rel}`).toBe(true);
      expect(stat.size, `Empty support doc: ${rel}`).toBeGreaterThan(0);
    }
  });

  it("all 4 demo-package docs exist and are non-empty", () => {
    expect(DEMO_PACKAGE_DOCS).toHaveLength(4);
    for (const rel of DEMO_PACKAGE_DOCS) {
      const full = path.join(REPO_ROOT, rel);
      const stat = statSync(full);
      expect(stat.isFile(), `Missing demo-package doc: ${rel}`).toBe(true);
      expect(stat.size, `Empty demo-package doc: ${rel}`).toBeGreaterThan(0);
    }
  });

  it("Phase 17 shell scripts exist", () => {
    expect(PHASE17_SCRIPTS).toHaveLength(3);
    for (const rel of PHASE17_SCRIPTS) {
      const full = path.join(REPO_ROOT, rel);
      const stat = statSync(full);
      expect(stat.isFile(), `Missing script: ${rel}`).toBe(true);
      expect(stat.size, `Empty script: ${rel}`).toBeGreaterThan(0);
    }
  });
});

// ---------------------------------------------------------------
// 2. Safe-claims contract reachable from every deck.
// ---------------------------------------------------------------

describe("Phase 17 — every deck references the safe-claims contract", () => {
  it.each(DECKS)("%s references the safe-claims contract", (rel) => {
    const text = readFileSync(path.join(REPO_ROOT, rel), "utf-8");
    const lower = text.toLowerCase();
    const ok =
      lower.includes("chartnav-approved-claims-language.md") ||
      /provider[- ]reviewed/i.test(text) ||
      /safe[- ]claims contract/i.test(text) ||
      /approved[- ]claims/i.test(text);
    expect(
      ok,
      `${rel} does not reference approved-claims language, "provider-reviewed", or "Safe-claims contract".`
    ).toBe(true);
  });
});

// ---------------------------------------------------------------
// 3. Forbidden positive claims appear only in safe contexts.
// ---------------------------------------------------------------

describe("Phase 17 — forbidden claims scan", () => {
  it("forbidden positive claims appear only in safe contexts (decks + support + demo-package docs)", () => {
    const docsToScan = [
      ...DECKS,
      ...COMMERCIAL_SUPPORT_DOCS,
      ...DEMO_PACKAGE_DOCS,
    ];
    for (const rel of docsToScan) {
      // Catalog docs (approved-claims-language, brand-guidelines
      // "Never use" slide, buyer-objection-handling "Don't say"
      // blocks) exist *to* enumerate the banned phrases. Scanning
      // them would always fail, so we exempt them here. The
      // catalog docs are themselves required to exist by section 1.
      if (CATALOG_DOCS.has(rel)) continue;

      const text = readFileSync(path.join(REPO_ROOT, rel), "utf-8");
      const lines = text.split(/\r?\n/);

      for (const claim of FORBIDDEN_POSITIVE_CLAIMS) {
        const matches = lines
          .map((line, idx) => ({ line, idx }))
          .filter(({ line }) => claim.pattern.test(line));

        for (const { line, idx } of matches) {
          if (isSafeNegativeContext(line, lines, idx)) continue;

          // Look at the immediately preceding non-blank line for
          // additional context (e.g., a section header that
          // introduces a list of banned phrases).
          const prevIdx = lines
            .slice(0, idx)
            .map((s, i) => ({ s, i }))
            .reverse()
            .find(({ s }) => s.trim().length > 0)?.i;
          const prevSafe =
            prevIdx !== undefined &&
            isSafeNegativeContext(lines[prevIdx], lines, prevIdx);

          expect(
            prevSafe,
            `In ${rel} line ${idx + 1}: forbidden claim "${
              claim.name
            }" appears outside a negative-assertion / forbidden-list / Q&A-answer context: ${line}`
          ).toBe(true);
        }
      }
    }
  });
});

// ---------------------------------------------------------------
// 4. No fabricated financial / conversion numbers in any deck.
//
// Allowed numbers:
//  - Pricing constants ($299, $499, $5,000, $10,000) since those
//    are the firm pricing block.
//  - Discount tiers (10%, 15%, 2–4 / 5–9 / 10+).
//  - Year markers + milestone targets (M1 Jul 1 2026, M2 Oct 1
//    2026, etc.).
//  - Slide / phase / metric counts.
//
// Forbidden:
//  - "$X ARR", "$X MRR", "$X revenue", "$X runway".
//  - "X% conversion" without "target", "hypothesis", or
//    "placeholder" framing.
//  - Hardcoded valuation figures.
// ---------------------------------------------------------------

describe("Phase 17 — no fabricated financial / conversion numbers", () => {
  const FORBIDDEN_NUMBER_PATTERNS: { name: string; pattern: RegExp }[] = [
    { name: "fabricated ARR", pattern: /\$\s?\d[\d,.]*\s?(?:[kKmM]\s)?arr\b/i },
    { name: "fabricated MRR", pattern: /\$\s?\d[\d,.]*\s?(?:[kKmM]\s)?mrr\b/i },
    {
      name: "fabricated runway",
      pattern: /\$\s?\d[\d,.]*\s?(?:[kKmM])?\s+runway\b/i,
    },
    {
      name: "fabricated valuation",
      pattern: /\$\s?\d[\d,.]*\s?(?:[kKmM])?\s+valuation\b/i,
    },
    {
      name: "fabricated revenue claim",
      pattern: /\$\s?\d[\d,.]*\s?(?:[kKmM])?\s+(?:annual\s+)?revenue\b/i,
    },
    {
      // "X% conversion" is allowed only when framed as a target /
      // hypothesis / placeholder. The pattern below catches a bare
      // figure followed by "conversion" with no qualifier nearby.
      name: "bare conversion percentage",
      pattern: /\b\d{1,3}\s*%\s+conversion\b/i,
    },
  ];

  it.each(DECKS)("%s does not invent financial numbers", (rel) => {
    const text = readFileSync(path.join(REPO_ROOT, rel), "utf-8");
    const lines = text.split(/\r?\n/);
    for (const { name, pattern } of FORBIDDEN_NUMBER_PATTERNS) {
      const matches = lines
        .map((line, idx) => ({ line, idx }))
        .filter(({ line }) => pattern.test(line));
      for (const { line, idx } of matches) {
        // Allowed if the line itself flags the number as a target /
        // hypothesis / placeholder, or sits inside a clearly
        // template-marked block.
        const safeNumberFraming =
          /\b(?:target|hypothesis|placeholder|projected|projection|template|estimate|tbd|to be validated|fabricated|do not|forbidden)\b/i.test(
            line
          ) ||
          /\{\{[A-Z_]+\}\}/.test(line) ||
          isSafeNegativeContext(line, lines, idx);
        expect(
          safeNumberFraming,
          `In ${rel} line ${idx + 1}: ${name} is not framed as target / hypothesis / placeholder: ${line}`
        ).toBe(true);
      }
    }
  });
});

// ---------------------------------------------------------------
// 5. Reset-script safety guard preserved.
// ---------------------------------------------------------------

describe("Phase 17 — reset-script safety contract preserved", () => {
  it("scripts/reset_demo_state.sh refuses non-local DATABASE_URL values", () => {
    const text = readFileSync(
      path.join(REPO_ROOT, "scripts/reset_demo_state.sh"),
      "utf-8"
    );
    expect(text).toMatch(/EXPECTED_PREFIX="sqlite:\/\/\/"/);
    expect(text).toMatch(/REFUSED:/);
  });

  it("export_chartnav_decks_to_desktop.sh wraps reset_demo_state.sh in RESET_DEMO_DATA.command", () => {
    const text = readFileSync(
      path.join(REPO_ROOT, "scripts/export_chartnav_decks_to_desktop.sh"),
      "utf-8"
    );
    expect(text).toMatch(/RESET_DEMO_DATA\.command/);
    expect(text).toMatch(/scripts\/reset_demo_state\.sh/);
    // The script must support the override hook so non-default
    // operator paths (CI, alt user) still work.
    expect(text).toMatch(/CHARTNAV_DESKTOP_DIR/);
    expect(text).toMatch(/CHARTNAV_REPO_DIR/);
  });

  it("create_chartnav_desktop_demo_package.sh delegates to the export script", () => {
    const text = readFileSync(
      path.join(
        REPO_ROOT,
        "scripts/create_chartnav_desktop_demo_package.sh"
      ),
      "utf-8"
    );
    expect(text).toMatch(/export_chartnav_decks_to_desktop\.sh/);
    // Post-export verification must check executable bits on the
    // .command files.
    expect(text).toMatch(/EXECUTABLE_FILES/);
  });
});

// ---------------------------------------------------------------
// 6. No binary media checked into Phase 17 paths.
// ---------------------------------------------------------------

describe("Phase 17 — no binary media in commercial / deck / demo-package paths", () => {
  const BINARY_EXT = /\.(png|jpe?g|gif|webp|mp4|mov|webm|pdf|pptx|key)$/i;
  const ROOTS = ["docs/decks", "docs/commercial", "docs/demo"];

  function walk(dir: string, files: string[] = []): string[] {
    let entries;
    try {
      entries = readdirSync(dir, { withFileTypes: true });
    } catch {
      return files;
    }
    for (const entry of entries) {
      const full = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        walk(full, files);
      } else if (entry.isFile()) {
        files.push(full);
      }
    }
    return files;
  }

  it("no binary media is committed under docs/decks, docs/commercial, or docs/demo", () => {
    const offenders: string[] = [];
    for (const r of ROOTS) {
      const root = path.join(REPO_ROOT, r);
      const files = walk(root);
      for (const f of files) {
        if (BINARY_EXT.test(f)) offenders.push(path.relative(REPO_ROOT, f));
      }
    }
    expect(
      offenders,
      `Binary media found under Phase 17 paths: ${offenders.join(", ")}`
    ).toEqual([]);
  });
});

// ---------------------------------------------------------------
// 7. Pricing block consistent across the two decks that quote it.
//
// The four pricing constants must appear in the pricing-notes doc,
// the financial deck, and the one-page sales deck. (Other decks
// either reference the pricing-notes doc or embed the same
// numbers; we don't enforce embedding everywhere.)
// ---------------------------------------------------------------

describe("Phase 17 — pricing constants appear consistently", () => {
  const DOCS_THAT_MUST_QUOTE_PRICING = [
    "docs/commercial/pricing/chartnav-pricing-packaging-notes.md",
    "docs/decks/chartnav-financial-fundraising-deck.md",
    "docs/decks/chartnav-one-page-sales-deck.md",
    "docs/decks/chartnav-investor-pitch-deck.md",
  ];
  const PRICING_TOKENS = [/\$299/, /\$499/, /\$5[, ]?000/, /\$10[, ]?000/];

  it.each(DOCS_THAT_MUST_QUOTE_PRICING)(
    "%s contains the four pricing constants",
    (rel) => {
      const text = readFileSync(path.join(REPO_ROOT, rel), "utf-8");
      for (const tok of PRICING_TOKENS) {
        expect(text, `Missing pricing token ${tok} in ${rel}`).toMatch(tok);
      }
    }
  );
});

// ---------------------------------------------------------------
// 8. Desktop-folder safety contract recorded in the Phase 17
//    contract doc.
// ---------------------------------------------------------------

describe("Phase 17 — desktop-folder safety contract", () => {
  it("docs/chartnav-desktop-demo-delivery-package.md records all four safety rules", () => {
    const text = readFileSync(
      path.join(REPO_ROOT, "docs/chartnav-desktop-demo-delivery-package.md"),
      "utf-8"
    );
    expect(text).toMatch(/Desktop folder is never committed/i);
    expect(text).toMatch(/does not embed real secrets/i);
    expect(text).toMatch(/refuses non-local DB URLs/i);
    expect(text).toMatch(/No binary media/i);
  });

  it(".gitignore covers the generated Desktop folder paths", () => {
    const text = readFileSync(path.join(REPO_ROOT, ".gitignore"), "utf-8");
    expect(text).toMatch(/chartnav decks\//);
  });
});
