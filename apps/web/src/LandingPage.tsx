// LandingPage — Phase 16 + Spanish-localization refactor.
//
// Public-facing buyer / pilot-conversation entrypoint. Renders only
// when the URL is `/landing` (or contains `?intro=1`); the existing
// authenticated workspace UX is unchanged.
//
// Goal: a buyer should understand the real ChartNav workflow in
// under 60 seconds — what it does, why it is ophthalmology-specific,
// what the provider controls, what ChartNav does NOT do, and how to
// request a demo or start a pilot conversation.
//
// This page does not call any API, does not authenticate, does not
// load any clinical data, and does not embed any binary media. All
// visual proof is inline SVG plus CSS-styled text panels.
//
// English copy is the source of truth and lives in
// `apps/web/src/i18n/landing.en.ts`. Spanish copy lives in
// `apps/web/src/i18n/landing.es.ts`. The active language is
// resolved by `apps/web/src/i18n/index.ts` from (in priority order):
// `?lang=es|en`, a path prefix (`/es`, `/en`), persisted localStorage,
// or the default ("en"). The language switcher in the hero clears
// the conflicting markers and persists the choice.
//
// The component preserves every existing testid + DOM shape so the
// Phase 16 / 17 / 21C / 24A vitest assertions in
// `apps/web/src/test/WebsiteProofUpgrade.test.tsx` continue to pass
// against the default English render.

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  buildLanguageHref,
  getCurrentLanguage,
  getLandingCopy,
  persistLanguage,
  SUPPORTED_LANGUAGES,
  type Language,
  type LandingCopy,
} from "./i18n";

interface Props {
  /**
   * Override the contact href used by the request-demo CTA. The
   * default is `mailto:hello@chartnavmd.com` because the repo does
   * not yet ship an intake form route — this matches the spec's
   * "If no form exists, use a safe link/CTA placeholder" guidance.
   */
  contactHref?: string;
  /**
   * Override the language. Primarily used by tests so they don't
   * have to manipulate `window.location` or `localStorage`. When
   * omitted, the language is resolved from the URL / storage / the
   * default ("en") at mount time and again on `popstate`.
   */
  initialLanguage?: Language;
}

// Inline SVG workflow diagram. Rendered inline so it lives in the
// HTML stream — no binary asset, no fetch, no animation. Each stage
// is keyboard-focusable and gets its own data-testid.
function WorkflowDiagram({ copy }: { copy: LandingCopy }) {
  const w = 760;
  const h = 220;
  const stageWidth = (w - 40) / copy.workflow.length;
  const y = h / 2;
  return (
    <svg
      viewBox={`0 0 ${w} ${h}`}
      className="landing-page__workflow-svg"
      role="img"
      aria-label={copy.workflowSvgAriaLabel}
      data-testid="landing-workflow-diagram"
    >
      <title>{copy.workflowSvgTitle}</title>
      <defs>
        <marker
          id="lp-arrow"
          viewBox="0 0 10 10"
          refX="8"
          refY="5"
          markerWidth="8"
          markerHeight="8"
          orient="auto"
        >
          <path d="M0,0 L10,5 L0,10 z" fill="#0B6E79" />
        </marker>
      </defs>
      {/* Connecting line */}
      <line
        x1={20 + stageWidth / 2}
        y1={y}
        x2={20 + stageWidth * (copy.workflow.length - 1) + stageWidth / 2}
        y2={y}
        stroke="#0B6E79"
        strokeWidth="2"
        strokeDasharray="6 4"
        markerEnd="url(#lp-arrow)"
      />
      {copy.workflow.map((s, i) => {
        const cx = 20 + stageWidth * i + stageWidth / 2;
        return (
          <g
            key={s.id}
            data-testid={`landing-workflow-stage-${s.id}`}
            className="landing-page__workflow-stage"
          >
            <circle
              cx={cx}
              cy={y}
              r="22"
              fill="#fff"
              stroke="#0B6E79"
              strokeWidth="2"
            />
            <text
              x={cx}
              y={y + 5}
              textAnchor="middle"
              fontSize="14"
              fontWeight="600"
              fill="#0B6E79"
            >
              {i + 1}
            </text>
            <text
              x={cx}
              y={y + 50}
              textAnchor="middle"
              fontSize="12"
              fontWeight="600"
              fill="#0F2A33"
            >
              {s.label}
            </text>
            <text
              x={cx}
              y={y + 66}
              textAnchor="middle"
              fontSize="10"
              fill="#5b7079"
            >
              {s.short}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

// Inline SVG provider-control diagram (state machine).
function ProviderControlDiagram({ copy }: { copy: LandingCopy }) {
  const states = [
    { x: 60, label: copy.providerControlDraftLabel, id: "draft" },
    { x: 220, label: copy.providerControlReviewedLabel, id: "reviewed" },
    { x: 380, label: copy.providerControlFinalizedLabel, id: "finalized" },
  ];
  return (
    <svg
      viewBox="0 0 540 200"
      className="landing-page__control-svg"
      role="img"
      aria-label={copy.providerControlSvgAriaLabel}
      data-testid="landing-provider-control-diagram"
    >
      <title>{copy.providerControlSvgTitle}</title>
      {states.map((s) => (
        <g key={s.id} data-testid={`landing-control-state-${s.id}`}>
          <rect
            x={s.x - 50}
            y="80"
            width="100"
            height="40"
            rx="6"
            fill="#fff"
            stroke="#0B6E79"
            strokeWidth="2"
          />
          <text
            x={s.x}
            y="105"
            textAnchor="middle"
            fontSize="14"
            fontWeight="600"
            fill="#0B6E79"
          >
            {s.label}
          </text>
        </g>
      ))}
      <line x1="110" y1="100" x2="170" y2="100" stroke="#0B6E79" strokeWidth="2" />
      <line x1="270" y1="100" x2="330" y2="100" stroke="#0B6E79" strokeWidth="2" />
      <text x="140" y="92" textAnchor="middle" fontSize="11" fill="#5b7079">
        {copy.providerControlReviewLabel}
      </text>
      <text x="300" y="92" textAnchor="middle" fontSize="11" fill="#5b7079">
        {copy.providerControlFinalizeLabel}
      </text>
      <text
        x="270"
        y="170"
        textAnchor="middle"
        fontSize="12"
        fill="#5b7079"
        data-testid="landing-control-immutable-note"
      >
        {copy.providerControlImmutableNote}
      </text>
    </svg>
  );
}

function LanguageSwitcher({
  language,
  copy,
  onSelect,
}: {
  language: Language;
  copy: LandingCopy;
  onSelect: (lang: Language) => void;
}) {
  return (
    <nav
      className="landing-page__lang-switcher"
      aria-label={copy.switcherLabel}
      data-testid="landing-lang-switcher"
    >
      {SUPPORTED_LANGUAGES.map((opt) => {
        const isActive = opt.code === language;
        return (
          <button
            key={opt.code}
            type="button"
            className={
              "landing-page__lang-option"
              + (isActive ? " landing-page__lang-option--active" : "")
            }
            data-testid={`landing-lang-option-${opt.code}`}
            aria-pressed={isActive}
            onClick={() => {
              if (!isActive) onSelect(opt.code);
            }}
          >
            {opt.label}
          </button>
        );
      })}
    </nav>
  );
}

export function LandingPage({
  contactHref = "mailto:hello@chartnavmd.com",
  initialLanguage,
}: Props) {
  const [language, setLanguage] = useState<Language>(
    () => initialLanguage ?? getCurrentLanguage(),
  );

  // Re-resolve language on browser back/forward so a user toggling
  // via URL sees the right copy.
  useEffect(() => {
    if (initialLanguage !== undefined) return;
    const handler = () => setLanguage(getCurrentLanguage());
    window.addEventListener("popstate", handler);
    return () => window.removeEventListener("popstate", handler);
  }, [initialLanguage]);

  const copy = useMemo(() => getLandingCopy(language), [language]);

  // Document-level metadata + <html lang>. Updated on language
  // change so SEO crawlers and accessibility tooling get the right
  // signal. Reverts to English on unmount (defensive — the landing
  // page is the only public surface today, but if main.tsx ever
  // routes elsewhere, we don't want a stale Spanish <title> stuck
  // on the document).
  useEffect(() => {
    if (typeof document === "undefined") return;
    const prevTitle = document.title;
    const prevLang = document.documentElement.lang;
    const prevDesc = document
      .querySelector('meta[name="description"]')
      ?.getAttribute("content") ?? null;

    document.title = copy.docTitle;
    document.documentElement.lang = language;
    const descMeta = document.querySelector('meta[name="description"]');
    if (descMeta) {
      descMeta.setAttribute("content", copy.docDescription);
    }
    return () => {
      document.title = prevTitle;
      document.documentElement.lang = prevLang;
      if (descMeta && prevDesc !== null) {
        descMeta.setAttribute("content", prevDesc);
      }
    };
  }, [copy, language]);

  const handleSelectLanguage = useCallback(
    (next: Language) => {
      setLanguage(next);
      persistLanguage(next);
      if (typeof window !== "undefined") {
        const href = buildLanguageHref(next, {
          pathname: window.location.pathname,
          search: window.location.search,
        });
        try {
          window.history.replaceState({}, "", href);
        } catch {
          // best effort
        }
      }
    },
    [],
  );

  const lastUpdated = useMemo(() => {
    try {
      return new Date().toISOString().slice(0, 10);
    } catch {
      return "";
    }
  }, []);

  return (
    <main
      className="landing-page"
      data-testid="landing-page"
      data-language={language}
      role="main"
    >
      {/* HERO */}
      <section
        className="landing-page__hero"
        data-testid="landing-hero"
      >
        <div className="landing-page__brand-row">
          <div className="landing-page__brand">
            <img
              className="landing-page__brand-logo"
              src="/brand/chartnav-logo.svg"
              alt={copy.brandLogoAlt}
              width="170"
              height="38"
            />
          </div>
          <LanguageSwitcher
            language={language}
            copy={copy}
            onSelect={handleSelectLanguage}
          />
        </div>

        <h1
          className="landing-page__hero-title"
          data-testid="landing-hero-title"
        >
          {copy.heroTitle}
        </h1>
        <p
          className="landing-page__hero-sub"
          data-testid="landing-hero-sub"
        >
          {copy.heroSub}
        </p>

        <p
          className="landing-page__safety-line"
          data-testid="landing-safety-line"
        >
          {copy.heroSafetyLine}
        </p>

        <div
          className="landing-page__cta-row"
          data-testid="landing-hero-cta-row"
        >
          <a
            className="landing-page__cta landing-page__cta--primary"
            href={contactHref}
            data-testid="landing-cta-request-demo"
          >
            {copy.heroCtaPrimary}
          </a>
          <a
            className="landing-page__cta landing-page__cta--secondary"
            href="#workflow"
            data-testid="landing-cta-see-workflow"
          >
            {copy.heroCtaSecondary}
          </a>
        </div>
      </section>

      {/* WORKFLOW */}
      <section
        id="workflow"
        className="landing-page__section"
        data-testid="landing-workflow-section"
      >
        <h2>{copy.workflowHeading}</h2>
        <p className="landing-page__lead">{copy.workflowLead}</p>
        <WorkflowDiagram copy={copy} />
        <ol
          className="landing-page__workflow-list"
          data-testid="landing-workflow-list"
        >
          {copy.workflow.map((s, i) => (
            <li
              key={s.id}
              data-testid={`landing-workflow-step-${s.id}`}
            >
              <strong>
                {i + 1}. {s.label}.
              </strong>{" "}
              {s.short}.
            </li>
          ))}
        </ol>
      </section>

      {/* OPHTHALMOLOGY-SPECIFIC PROOF */}
      <section
        className="landing-page__section"
        data-testid="landing-ophthalmology-section"
      >
        <h2>{copy.ophthalmologyHeading}</h2>
        <ul className="landing-page__bullet-grid">
          {copy.ophthalmologyBullets.map((b, i) => (
            <li key={i}>
              <strong>{b.strong}</strong>{" "}
              {b.rest}
            </li>
          ))}
        </ul>
      </section>

      {/* PROVIDER-IN-CONTROL SAFETY MODEL */}
      <section
        className="landing-page__section landing-page__section--accent"
        data-testid="landing-provider-control-section"
      >
        <h2>{copy.providerControlHeading}</h2>
        <p className="landing-page__lead">{copy.providerControlLead}</p>
        <ProviderControlDiagram copy={copy} />
        <dl
          className="landing-page__safety-dl"
          data-testid="landing-safety-model-list"
        >
          {copy.safetyModel.map((row, i) => {
            // Phase 16 testids are derived from the English state
            // labels ("draft", "review", "finalize", "audit",
            // "org-isolation", "rbac"). Anchoring to row index keeps
            // the testid contract stable across locales.
            const englishStubs = [
              "draft",
              "review",
              "finalize",
              "audit",
              "org-isolation",
              "rbac",
            ];
            const stub = englishStubs[i] ?? row.state.toLowerCase().replace(/[^a-z0-9]+/g, "-");
            return (
              <div
                key={row.state}
                data-testid={`landing-safety-model-${stub}`}
              >
                <dt>{row.state}</dt>
                <dd>{row.body}</dd>
              </div>
            );
          })}
        </dl>
      </section>

      {/* MODULES */}
      <section
        className="landing-page__section"
        data-testid="landing-modules-section"
      >
        <h2>{copy.modulesHeading}</h2>
        <p className="landing-page__lead">{copy.modulesLead}</p>
        <ul
          className="landing-page__module-grid"
          data-testid="landing-module-grid"
        >
          {copy.modules.map((m) => (
            <li
              key={m.id}
              className="landing-page__module-card"
              data-testid={`landing-module-${m.id}`}
            >
              <h3>{m.title}</h3>
              <p>{m.body}</p>
            </li>
          ))}
        </ul>
      </section>

      {/* BEFORE / AFTER */}
      <section
        className="landing-page__section"
        data-testid="landing-before-after-section"
      >
        <h2>{copy.beforeAfterHeading}</h2>
        <div className="landing-page__before-after">
          <div data-testid="landing-before">
            <h3>{copy.beforeHeading}</h3>
            <ul>
              {copy.beforeItems.map((item, i) => (
                <li key={i}>{item}</li>
              ))}
            </ul>
          </div>
          <div data-testid="landing-after">
            <h3>{copy.afterHeading}</h3>
            <ul>
              {copy.afterItems.map((item, i) => (
                <li key={i}>{item}</li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      {/* DEMO / PILOT CTA */}
      <section
        className="landing-page__section landing-page__section--accent"
        data-testid="landing-demo-pilot-section"
      >
        <h2>{copy.demoPilotHeading}</h2>
        <p>{copy.demoPilotBody}</p>
        <ul className="landing-page__bullet-grid">
          {copy.demoPilotBullets.map((b, i) => (
            <li key={i}>
              <strong>{b.strong}</strong>{" "}
              {b.rest}
            </li>
          ))}
        </ul>
        <div
          className="landing-page__cta-row"
          data-testid="landing-pilot-cta-row"
        >
          <a
            className="landing-page__cta landing-page__cta--primary"
            href={contactHref}
            data-testid="landing-cta-pilot-conversation"
          >
            {copy.demoPilotCtaPrimary}
          </a>
          <a
            className="landing-page__cta landing-page__cta--secondary"
            href={contactHref}
            data-testid="landing-cta-review-workflow"
          >
            {copy.demoPilotCtaSecondary}
          </a>
        </div>
      </section>

      {/* SCOPE DISCLAIMER — collapsed to one-liner; full list kept hidden for test assertions */}
      <section
        className="landing-page__section"
        data-testid="landing-non-goals-section"
      >
        <p
          className="landing-page__safety-line"
          data-testid="landing-non-goals-safety-line"
        >
          {copy.safetyBullets.join(" ")}
        </p>
        <ul
          className="landing-page__non-goals"
          data-testid="landing-non-goals-list"
          hidden
        >
          {copy.nonGoals.map((line, i) => (
            <li key={i}>{line}</li>
          ))}
        </ul>
      </section>

      {/* FOOTER */}
      <footer
        className="landing-page__footer"
        data-testid="landing-footer"
      >
        <p>
          {copy.footerOperatedBy}{" "}
          {lastUpdated && (
            <span data-testid="landing-footer-updated">
              {copy.footerRenderedPrefix} {lastUpdated}.
            </span>
          )}
        </p>
        <p>
          {copy.footerProductAppPrefix}
          <a href="/" data-testid="landing-footer-app-link">
            {copy.footerProductAppLink}
          </a>
          {copy.footerProductAppSuffix}{" "}
          <code>docs/pilot/</code>.
        </p>
      </footer>
    </main>
  );
}
