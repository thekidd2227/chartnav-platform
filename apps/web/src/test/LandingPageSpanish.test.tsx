// LandingPageSpanish.test.tsx
//
// Vitest coverage for the Spanish localization of the ChartNav
// public landing page. Verifies:
//   1. <LandingPage initialLanguage="es" /> renders Spanish copy
//      everywhere the English version renders English copy
//      (hero, workflow, modules, non-goals, footer).
//   2. The language switcher renders both options, marks the active
//      language with aria-pressed=true, and toggles to the other
//      language on click.
//   3. The document <title>, <html lang>, and <meta name=description>
//      are updated to match the active language.
//   4. No forbidden Spanish positive claim appears in the rendered
//      DOM. The strings are checked against a permissive
//      negative-context window so the non-goals enumeration ("No
//      cuenta con certificación HIPAA") is treated as a negative
//      assertion, not a positive claim.
//   5. The English-only Phase 16 / 17 / 21C / 24A assertions still
//      hold for the default English render (covered by the
//      existing WebsiteProofUpgrade.test.tsx — this file only adds
//      the Spanish surface so it does NOT duplicate that work).

import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, beforeEach } from "vitest";
import { LandingPage } from "../LandingPage";

beforeEach(() => {
  // Reset language persistence between tests so a previous test
  // does not leak its localStorage state into the next.
  try {
    window.localStorage.removeItem("chartnav.language");
  } catch {
    // ignore — jsdom always supports localStorage
  }
  // Reset document title + html lang so the useEffect cleanup is
  // observable in isolation.
  document.title = "ChartNav test harness";
  document.documentElement.lang = "en";
  // jsdom does not parse index.html's <meta> tags; the production
  // page does. Inject (or reset) a <meta name="description"> so the
  // LandingPage useEffect has something to update.
  let desc = document.querySelector('meta[name="description"]');
  if (!desc) {
    desc = document.createElement("meta");
    desc.setAttribute("name", "description");
    document.head.appendChild(desc);
  }
  desc.setAttribute("content", "test harness");
});

describe("LandingPage — Spanish rendering", () => {
  it("renders Spanish hero copy when initialLanguage=es", () => {
    render(<LandingPage initialLanguage="es" />);
    expect(screen.getByTestId("landing-hero-title")).toHaveTextContent(
      /capa de flujo operativo para clínicas oftalmológicas/i,
    );
    expect(screen.getByTestId("landing-hero-title")).toHaveTextContent(
      /revisada por el proveedor/i,
    );
    expect(screen.getByTestId("landing-hero-sub")).toHaveTextContent(
      /preparación administrativa/i,
    );
    expect(screen.getByTestId("landing-hero-sub")).toHaveTextContent(
      /paneles por rol/i,
    );
    expect(screen.getByTestId("landing-safety-line")).toHaveTextContent(
      /no diagnostica/i,
    );
    expect(screen.getByTestId("landing-safety-line")).toHaveTextContent(
      /no presenta reclamaciones/i,
    );
  });

  it("renders Spanish CTAs", () => {
    render(<LandingPage initialLanguage="es" />);
    expect(
      screen.getByTestId("landing-cta-request-demo"),
    ).toHaveTextContent(/demo con paciente ficticio/i);
    expect(
      screen.getByTestId("landing-cta-see-workflow"),
    ).toHaveTextContent(/cómo funciona el flujo/i);
    expect(
      screen.getByTestId("landing-cta-pilot-conversation"),
    ).toHaveTextContent(/piloto oftalmológico controlado/i);
    expect(
      screen.getByTestId("landing-cta-review-workflow"),
    ).toHaveTextContent(/proveedor en control/i);
  });

  it("renders Spanish workflow stage labels with the same 7 ids", () => {
    render(<LandingPage initialLanguage="es" />);
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
        screen.getByTestId(`landing-workflow-stage-${id}`),
      ).toBeInTheDocument();
    }
    const list = screen.getByTestId("landing-workflow-list");
    expect(within(list).getAllByRole("listitem")).toHaveLength(7);
    expect(list).toHaveTextContent(/Sesión de transcripción/i);
    expect(list).toHaveTextContent(/Diagrama OD\/OS/i);
    expect(list).toHaveTextContent(/Demo guiado/i);
  });

  it("renders the Spanish non-goals list with 9 items and key negative assertions", () => {
    render(<LandingPage initialLanguage="es" />);
    const list = screen.getByTestId("landing-non-goals-list");
    // Non-goals list is kept in the DOM for automated assertions but
    // rendered with the HTML hidden attribute. Use { hidden: true }
    // to include it in the role query.
    expect(within(list).getAllByRole("listitem", { hidden: true })).toHaveLength(9);
    expect(list).toHaveTextContent(/No es un EHR certificado/i);
    expect(list).toHaveTextContent(/No cuenta con certificación HIPAA/i);
    expect(list).toHaveTextContent(/No realiza diagnóstico autónomo/i);
    expect(list).toHaveTextContent(/No completa automáticamente la PIO/i);
    expect(list).toHaveTextContent(/No interpreta exámenes de OCT/i);
    expect(list).toHaveTextContent(
      /No selecciona la potencia de la lente intraocular/i,
    );
    expect(list).toHaveTextContent(
      /No coloca órdenes, no envía referencias, no presenta reclamaciones/i,
    );
    expect(list).toHaveTextContent(/No envía mensajes automáticos al paciente/i);
    expect(list).toHaveTextContent(
      /No es una integración actual con ningún proveedor específico de dispositivos/i,
    );
  });

  it("renders the Spanish footer copy + product app link", () => {
    render(<LandingPage initialLanguage="es" />);
    const footer = screen.getByTestId("landing-footer");
    expect(footer).toHaveTextContent(/ChartNav es operado por ARCG/);
    expect(footer).toHaveTextContent(/espacio de trabajo de ChartNav/);
    expect(footer).toHaveTextContent(/docs\/pilot/);
    expect(footer).toHaveTextContent(/preparación para piloto/i);
  });

  it("sets document.title, html lang, and meta description to the Spanish copy", () => {
    render(<LandingPage initialLanguage="es" />);
    expect(document.title).toMatch(
      /ChartNav MD — Flujo clínico oftalmológico/i,
    );
    expect(document.documentElement.lang).toBe("es");
    const desc = document
      .querySelector('meta[name="description"]')
      ?.getAttribute("content");
    expect(desc).toMatch(/coordinar flujos de trabajo oftalmológicos/i);
    expect(desc).toMatch(/No es un EHR certificado/i);
  });
});

describe("LandingPage — language switcher", () => {
  it("renders English + Spanish options with active state", () => {
    render(<LandingPage initialLanguage="en" />);
    const sw = screen.getByTestId("landing-lang-switcher");
    const en = within(sw).getByTestId("landing-lang-option-en");
    const es = within(sw).getByTestId("landing-lang-option-es");
    expect(en).toHaveAttribute("aria-pressed", "true");
    expect(es).toHaveAttribute("aria-pressed", "false");
  });

  it("clicking Español swaps the rendered copy and persists to localStorage", async () => {
    const user = userEvent.setup();
    render(<LandingPage initialLanguage="en" />);
    // English hero is up.
    expect(screen.getByTestId("landing-hero-title")).toHaveTextContent(
      /clinical workflow layer for ophthalmology/i,
    );
    await user.click(screen.getByTestId("landing-lang-option-es"));
    // Spanish hero is now up.
    expect(screen.getByTestId("landing-hero-title")).toHaveTextContent(
      /capa de flujo operativo para clínicas oftalmológicas/i,
    );
    expect(screen.getByTestId("landing-page")).toHaveAttribute(
      "data-language",
      "es",
    );
    expect(window.localStorage.getItem("chartnav.language")).toBe("es");
  });

  it("clicking English toggles back from Spanish", async () => {
    const user = userEvent.setup();
    render(<LandingPage initialLanguage="es" />);
    expect(screen.getByTestId("landing-hero-title")).toHaveTextContent(
      /capa de flujo operativo/i,
    );
    await user.click(screen.getByTestId("landing-lang-option-en"));
    expect(screen.getByTestId("landing-hero-title")).toHaveTextContent(
      /clinical workflow layer for ophthalmology/i,
    );
    expect(window.localStorage.getItem("chartnav.language")).toBe("en");
  });

  it("renders switcher options as <button> not <a> (no extra link href surface)", () => {
    render(<LandingPage initialLanguage="en" />);
    const sw = screen.getByTestId("landing-lang-switcher");
    const buttons = within(sw).getAllByRole("button");
    expect(buttons).toHaveLength(2);
    // No anchors inside the switcher — keeps the Phase 16 link-href
    // contract intact (only mailto/#workflow/'/' are allowed).
    expect(within(sw).queryAllByRole("link")).toHaveLength(0);
  });
});

describe("LandingPage — Spanish claim-safety", () => {
  // Forbidden Spanish positive claims must NEVER appear in the
  // rendered DOM outside an explicit negative-context window.
  const FORBIDDEN_ES: RegExp[] = [
    /cumple con HIPAA/i,
    /certificación HIPAA(?! por defecto)/i, // "No cuenta con certificación HIPAA" is allowed
    /certificado HIPAA/i,
    /EHR certificado(?!\.\s+ChartNav)/i, // "No es un EHR certificado." is allowed
    /reemplaza (su|el) (EHR|EMR)/i,
    /diagnóstico autónomo(?!\.\s+La interpretación)/i,
    /diagnóstico automático/i,
    /interpretación autónoma de imágenes/i,
    /interpretación automática de imágenes/i,
    /interpretación automática de OCT/i,
    /calificación automática de retinopathía/i,
    /recomienda anti-VEGF/i,
    /selecciona potencia de lente/i,
    /órdenes automáticas/i,
    /referencias automáticas/i,
    /mensajes automáticos al paciente(?!\.\s+No)/i,
    /codificación automática/i,
    /facturación automática/i,
    /envío de reclamaciones/i,
    /la nota se escribe sola/i,
    /la historia clínica se completa sola/i,
  ];

  it("renders no forbidden Spanish positive claim outside negative context", () => {
    render(<LandingPage initialLanguage="es" />);
    const root = screen.getByTestId("landing-page");
    const text = root.textContent ?? "";
    // The non-goals section legitimately uses negative phrasings
    // like "No realiza diagnóstico autónomo" — we strip that
    // negative wrapper, then re-scan to ensure no naked positive
    // claim survives.
    const negativized = text
      .replace(/No es un EHR certificado/gi, "")
      .replace(/No cuenta con certificación HIPAA/gi, "")
      .replace(/No realiza diagnóstico autónomo/gi, "")
      .replace(/No interpreta exámenes de OCT/gi, "")
      .replace(/No selecciona la potencia/gi, "")
      .replace(/No coloca órdenes/gi, "")
      .replace(/No envía mensajes automáticos al paciente/gi, "")
      .replace(/no envía referencias/gi, "")
      .replace(/no presenta reclamaciones/gi, "")
      .replace(/no es una integración actual/gi, "")
      .replace(/no factura ni envía mensajes automáticos al paciente/gi, "");
    for (const re of FORBIDDEN_ES) {
      expect(negativized).not.toMatch(re);
    }
  });

  it("includes the BAA + security-review boilerplate verbatim in Spanish", () => {
    render(<LandingPage initialLanguage="es" />);
    const section = screen.getByTestId("landing-demo-pilot-section");
    expect(section).toHaveTextContent(/Acuerdo de Asociado Comercial/i);
    expect(section).toHaveTextContent(/revisión de seguridad/i);
    expect(section).toHaveTextContent(/piloto controlado/i);
  });

  it("non-goals safety line restates the contract in Spanish", () => {
    render(<LandingPage initialLanguage="es" />);
    expect(
      screen.getByTestId("landing-non-goals-safety-line"),
    ).toHaveTextContent(/no diagnostica/i);
    expect(
      screen.getByTestId("landing-non-goals-safety-line"),
    ).toHaveTextContent(/revisado por el proveedor/i);
  });
});

describe("LandingPage — English default remains intact", () => {
  it("default render (no initialLanguage prop, no URL, no storage) is English", () => {
    render(<LandingPage />);
    expect(screen.getByTestId("landing-hero-title")).toHaveTextContent(
      /clinical workflow layer for ophthalmology/i,
    );
    expect(screen.getByTestId("landing-page")).toHaveAttribute(
      "data-language",
      "en",
    );
  });
});
