/**
 * Phase 16 — public landing / proof page tests.
 *
 * Asserts the LandingPage renders all required sections, exposes
 * the right CTAs, contains no forbidden positive marketing claims,
 * and no clinical-action button surfaces (no orders, no coding, no
 * referrals, no patient messaging). Also asserts the inline SVG
 * workflow diagram has all seven stages and the provider-control
 * state diagram is present — no binary media is loaded.
 */

import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { LandingPage } from "../LandingPage";

describe("LandingPage — required sections", () => {
  it("renders the landing root with hero + workflow + ophthalmology + safety + modules + before/after + demo + non-goals + footer", () => {
    render(<LandingPage />);
    for (const tid of [
      "landing-page",
      "landing-hero",
      "landing-workflow-section",
      "landing-ophthalmology-section",
      "landing-provider-control-section",
      "landing-modules-section",
      "landing-before-after-section",
      "landing-demo-pilot-section",
      "landing-non-goals-section",
      "landing-footer",
    ]) {
      expect(screen.getByTestId(tid)).toBeInTheDocument();
    }
  });

  it("hero shows positioning sentence + safety line + two CTAs", () => {
    render(<LandingPage />);
    expect(
      screen.getByTestId("landing-hero-title")
    ).toHaveTextContent(/ophthalmology/i);
    expect(
      screen.getByTestId("landing-hero-title")
    ).toHaveTextContent(/provider-reviewed/i);
    expect(screen.getByTestId("landing-safety-line")).toHaveTextContent(
      /Provider-reviewed workflow support/i
    );
    expect(screen.getByTestId("landing-safety-line")).toHaveTextContent(
      /does not diagnose, create orders, send referrals, bill, or message patients/i
    );
    // Two hero CTAs present and clickable.
    const primary = screen.getByTestId("landing-cta-request-demo");
    const secondary = screen.getByTestId("landing-cta-see-workflow");
    expect(primary.tagName).toBe("A");
    expect(secondary.tagName).toBe("A");
    expect(primary).toHaveTextContent(/fake-patient demo/i);
    expect(secondary).toHaveAttribute("href", "#workflow");
  });

  it("respects the contactHref prop on all primary CTAs", () => {
    render(<LandingPage contactHref="https://example.test/intake" />);
    expect(
      screen.getByTestId("landing-cta-request-demo")
    ).toHaveAttribute("href", "https://example.test/intake");
    expect(
      screen.getByTestId("landing-cta-pilot-conversation")
    ).toHaveAttribute("href", "https://example.test/intake");
    expect(
      screen.getByTestId("landing-cta-review-workflow")
    ).toHaveAttribute("href", "https://example.test/intake");
  });
});

describe("LandingPage — workflow diagram", () => {
  it("renders the inline SVG workflow with all seven stages", () => {
    render(<LandingPage />);
    const svg = screen.getByTestId("landing-workflow-diagram");
    expect(svg.tagName.toLowerCase()).toBe("svg");
    // role="img" for screen-reader exposure.
    expect(svg).toHaveAttribute("role", "img");
    // Seven stage nodes; data-testid guarantees stable selectors.
    for (const id of [
      "scribe",
      "proposals",
      "diagram",
      "summary",
      "brief",
      "queue",
      "demo",
    ]) {
      expect(
        screen.getByTestId(`landing-workflow-stage-${id}`)
      ).toBeInTheDocument();
    }
    // Workflow text-list mirrors the SVG.
    const list = screen.getByTestId("landing-workflow-list");
    expect(within(list).getAllByRole("listitem")).toHaveLength(7);
  });

  it("renders the provider-control state diagram (Draft → Reviewed → Finalized) + immutability note", () => {
    render(<LandingPage />);
    const svg = screen.getByTestId("landing-provider-control-diagram");
    expect(svg.tagName.toLowerCase()).toBe("svg");
    for (const id of ["draft", "reviewed", "finalized"]) {
      expect(
        screen.getByTestId(`landing-control-state-${id}`)
      ).toBeInTheDocument();
    }
    expect(
      screen.getByTestId("landing-control-immutable-note")
    ).toHaveTextContent(
      /Finalized artifacts are immutable.*signed retinal artifacts create an explicit fork/i
    );
  });

  it("renders the safety-model row list with five-plus rows", () => {
    render(<LandingPage />);
    const list = screen.getByTestId("landing-safety-model-list");
    // Each row has its own testid prefixed `landing-safety-model-`;
    // the dl has 6 rows (Draft / Review / Finalize / Audit / Org isolation / RBAC).
    for (const stub of [
      "draft",
      "review",
      "finalize",
      "audit",
      "org-isolation",
      "rbac",
    ]) {
      expect(
        within(list).getByTestId(`landing-safety-model-${stub}`)
      ).toBeInTheDocument();
    }
  });
});

describe("LandingPage — modules + before/after + non-goals", () => {
  it("renders eight module cards covering the Phase 6/8/9/10/11/13/14/15 surfaces", () => {
    render(<LandingPage />);
    const grid = screen.getByTestId("landing-module-grid");
    expect(within(grid).getAllByRole("listitem")).toHaveLength(8);
    for (const id of [
      "scribe",
      "proposals",
      "diagram",
      "summary",
      "brief",
      "queue",
      "demo",
      "pilot",
    ]) {
      expect(
        within(grid).getByTestId(`landing-module-${id}`)
      ).toBeInTheDocument();
    }
  });

  it("renders the before / with-ChartNav comparison", () => {
    render(<LandingPage />);
    expect(screen.getByTestId("landing-before")).toHaveTextContent(/Before/);
    expect(screen.getByTestId("landing-after")).toHaveTextContent(
      /With ChartNav/
    );
  });

  it("renders the four 'what ChartNav is not' bullet items", () => {
    render(<LandingPage />);
    const list = screen.getByTestId("landing-non-goals-list");
    // Phase 24A — non-goals expanded from 4 to 9 ophthalmology-specific
    // negative assertions (certified-EHR, HIPAA-certified, autonomous
    // diagnosis, no autofill IOP, no OCT interpretation, no IOL
    // selection, no anti-VEGF dosing, no orders / claims / messaging,
    // no current device-vendor integration).
    expect(within(list).getAllByRole("listitem")).toHaveLength(9);
    // Phase 24A — each negative assertion must appear in the
    // non-goals list. Updated phrasing reflects the ophthalmology-
    // specific Phase 24A copy.
    expect(list).toHaveTextContent(/Not a certified EHR/i);
    expect(list).toHaveTextContent(/Not HIPAA-certified/i);
    expect(list).toHaveTextContent(/Not autonomous diagnosis/i);
    expect(list).toHaveTextContent(/Does not autofill IOP/i);
    expect(list).toHaveTextContent(/Does not interpret OCT/i);
    expect(list).toHaveTextContent(/Does not select IOL power/i);
    expect(list).toHaveTextContent(/Does not place orders, send referrals, submit claims/i);
    expect(list).toHaveTextContent(/Does not send patient messages/i);
    expect(list).toHaveTextContent(/Not a current integration with any specific imaging-device vendor/i);
  });

  it("renders the demo + pilot CTA row with two buttons", () => {
    render(<LandingPage />);
    expect(
      screen.getByTestId("landing-cta-pilot-conversation")
    ).toHaveTextContent(/controlled ophthalmology pilot/i);
    expect(
      screen.getByTestId("landing-cta-review-workflow")
    ).toHaveTextContent(/provider-in-control workflow/i);
  });
});

describe("LandingPage — safety / claims contract", () => {
  it("contains no forbidden positive marketing claims", () => {
    // Each pattern below is rejected only when it appears as a
    // positive claim. Negative-assertion contexts ("Not autonomous
    // diagnosis.", "ChartNav does not …", "Never …") are allowed
    // and the page in fact uses several of them. The lookbehinds
    // in each pattern enforce this.
    render(<LandingPage />);
    const root = screen.getByTestId("landing-page");
    const text = (root.textContent || "").toLowerCase();
    const NEG = "(?<!not\\s)(?<!does not\\s)(?<!never\\s)";
    for (const claim of [
      // Compliance / certification claims are rejected only when
      // positive. The Phase 24A non-goals block intentionally uses
      // "Not HIPAA-certified", "Not a certified EHR", etc. The NEG
      // lookbehind exempts those negative-assertion contexts.
      new RegExp(`${NEG}\\bhipaa[ -]compliant\\b`),
      new RegExp(`${NEG}\\bhipaa[ -]certified\\b`),
      new RegExp(`${NEG}\\bsoc[ -]?2[ -]?certified\\b`),
      new RegExp(`${NEG}\\bproduction[- ]ready for phi\\b`),
      new RegExp(`${NEG}\\breal patient data ready\\b`),
      // Capability claims are rejected only when positive. The
      // page intentionally says "Not a certified EHR replacement",
      // "Not autonomous diagnosis", "does not create orders", etc.
      new RegExp(`${NEG}\\bcertified ehr\\b(?! replacement)(?!\\.)`),
      new RegExp(`${NEG}\\bautonomous diagnosis\\b`),
      new RegExp(`${NEG}\\bautomatic diagnosis\\b`),
      new RegExp(`${NEG}\\bguaranteed accuracy\\b`),
      new RegExp(`${NEG}\\bautomatic orders\\b`),
      new RegExp(`${NEG}\\border oct\\b`),
      new RegExp(`${NEG}\\bsubmit referral\\b`),
      new RegExp(`${NEG}\\bsend patient message\\b`),
      new RegExp(`${NEG}\\breplaces (?:a )?doctor\\b`),
      // Phase 24A — Manus public-claims audit additions.
      // These must NEVER appear as positive claims on the landing
      // page. The negative-assertion non-goals block intentionally
      // uses "does not autofill IOP", "does not interpret OCTs",
      // etc., which are exempted by the NEG lookbehinds.
      /\bhands[- ]free scrib(ing|e)\b/,
      /\bchart fills itself\b/,
      /\bchart writes itself\b/,
      /\bnote fills itself\b/,
      /\bnote writes itself\b/,
      new RegExp(`${NEG}\\breplace[s]? your (ehr|emr)\\b`),
      new RegExp(`${NEG}\\b(ehr|emr) replacement\\b`),
      /\bpowered by ibm\b/,
      /\bpowered by watsonx\b/,
      /\bwatsonx[- ]powered\b/,
      /\bibm[- ]powered\b/,
      /\bbilling[- ]aware coding\b/,
      /\bcoding recommendations\b/,
    ]) {
      expect(text).not.toMatch(claim);
    }
  });

  it("renders no order / coding / referral / patient-message buttons", () => {
    render(<LandingPage />);
    const root = screen.getByTestId("landing-page");
    for (const label of [
      /place order/i,
      /coding/i,
      /icd-?10/i,
      /cpt code/i,
      /\bsend referral\b/i,
      /\bsubmit referral\b/i,
      /\bsend to patient\b/i,
      /\bemail patient\b/i,
      /\bsms patient\b/i,
      /\bportal push\b/i,
      /\bprescribe\b/i,
    ]) {
      expect(
        within(root).queryByRole("button", { name: label })
      ).not.toBeInTheDocument();
    }
  });

  it("contains no autonomous-diagnosis or external-LLM positive claims anywhere on the page", () => {
    // Bare-word `autonomous` is allowed inside the explicit negative
    // assertion "Not autonomous diagnosis."; what we reject here is
    // any *positive* claim that ChartNav is or provides autonomous
    // / automatic / external-LLM behavior, plus any vendor name
    // that suggests an external-LLM dependency in the marketing
    // copy.
    render(<LandingPage />);
    const root = screen.getByTestId("landing-page");
    const text = (root.textContent || "").toLowerCase();
    for (const pattern of [
      /\bopenai\b/,
      /\banthropic\b/,
      /\bgpt[- ]?\d/,
      /\bllm certainty\b/,
      /\bexternal llm\b/,
      // Positive autonomous-* claims. The non-goals list says "Not
      // autonomous diagnosis." which is fine. A line that says
      // "autonomous diagnosis" *without* a leading "Not " or "does
      // not" or "never" would be unsafe.
      /(?<!not\s)(?<!does not\s)(?<!never\s)\bautonomous diagnosis\b/,
      /(?<!not\s)(?<!does not\s)(?<!never\s)\bautomatic diagnosis\b/,
    ]) {
      expect(text).not.toMatch(pattern);
    }
  });

  it("renders no <img> tag pointing at a binary media file checked into the repo", () => {
    render(<LandingPage />);
    const root = screen.getByTestId("landing-page");
    const imgs = within(root).queryAllByRole("img");
    // Only the brand logo (SVG) and the inline SVG diagrams (which
    // are <svg role="img"> not <img>) should be present.
    for (const el of imgs) {
      const src = el.getAttribute("src") || "";
      // No raster formats checked into the page.
      expect(src).not.toMatch(/\.(png|jpe?g|gif|webp|mp4|mov|webm)(\?|$)/i);
    }
  });

  it("provider-review language is present and consistent", () => {
    render(<LandingPage />);
    const root = screen.getByTestId("landing-page");
    const text = (root.textContent || "").toLowerCase();
    expect(text).toMatch(/provider[- ]reviewed/);
    expect(text).toMatch(/explicit provider review/);
    expect(text).toMatch(/does not diagnose/);
    // The hero safety line.
    expect(
      screen.getByTestId("landing-safety-line")
    ).toBeInTheDocument();
    // The non-goals section's safety line restates the contract.
    expect(
      screen.getByTestId("landing-non-goals-safety-line")
    ).toHaveTextContent(/does not diagnose/i);
  });

  it("only contact link is the contactHref / safe placeholder", () => {
    render(<LandingPage contactHref="https://example.test/intake" />);
    const ctas = [
      screen.getByTestId("landing-cta-request-demo"),
      screen.getByTestId("landing-cta-pilot-conversation"),
      screen.getByTestId("landing-cta-review-workflow"),
    ];
    for (const cta of ctas) {
      expect(cta).toHaveAttribute("href", "https://example.test/intake");
    }
    // No raw mailto / external links sneaked in beyond what we
    // configured.
    const root = screen.getByTestId("landing-page");
    const links = within(root).getAllByRole("link");
    for (const link of links) {
      const href = link.getAttribute("href") || "";
      // Allowed: in-page anchor, the configured contact href, the
      // app link in the footer ('/').
      expect(
        /^(https:\/\/example\.test\/intake|#workflow|\/|tel:|mailto:)/.test(
          href
        )
      ).toBe(true);
    }
  });
});

describe("LandingPage — pilot conversation gating", () => {
  it("explicitly states that real PHI requires legal / security review and a BAA", () => {
    render(<LandingPage />);
    const section = screen.getByTestId("landing-demo-pilot-section");
    expect(section).toHaveTextContent(/Business Associate Agreement/i);
    expect(section).toHaveTextContent(/security review/i);
    expect(section).toHaveTextContent(/controlled-pilot/i);
  });

  it("references the pilot readiness packet in the footer", () => {
    render(<LandingPage />);
    const footer = screen.getByTestId("landing-footer");
    expect(footer).toHaveTextContent(/pilot readiness/i);
    expect(footer).toHaveTextContent(/docs\/pilot/);
  });
});
