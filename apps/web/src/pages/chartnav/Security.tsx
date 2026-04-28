/**
 * /chartnav/security — Security & Governance page
 * Route: /chartnav/security  (indexed, sitemap included)
 *
 * Sections:
 *  1. Hero
 *  2–9. Eight pillar cards (watsonx, rbac, audit, phi, human, isolation, monitoring, enterprise)
 *  10. What We Do Not Claim
 *  11. Security Roadmap
 *  12. CTA
 *
 * Conventions:
 *  - All copy sourced from security.en.json
 *  - Scoped under .chartnav-root via chartnav.css
 *  - No hardcoded strings
 *  - Inline SVG only — no icon library
 *  - No certification or partnership claims
 */

import { Helmet } from 'react-helmet-async';
import { useFormsContext } from '../../components/chartnav/FormsContext';
import content from '../../content/chartnav/security.en.json';

// ── Typed helpers ────────────────────────────────────────────────────────────

type Pillar     = typeof content.pillars[number];
type NoClaim    = typeof content.noClaimSection.items[number];
type RoadmapItem = typeof content.roadmap.items[number];

// ── Icon set ─────────────────────────────────────────────────────────────────

const icons: Record<string, JSX.Element> = {
  watsonx: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <polygon points="12,2 22,7 22,17 12,22 2,17 2,7"
        stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
      <path d="M7 12h10M12 7v10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  ),
  rbac: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <rect x="5" y="11" width="14" height="10" rx="2" stroke="currentColor" strokeWidth="1.5" />
      <path d="M8 11V7a4 4 0 018 0v4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      <circle cx="12" cy="16" r="1.5" fill="currentColor" />
    </svg>
  ),
  audit: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <rect x="3" y="4" width="14" height="16" rx="2" stroke="currentColor" strokeWidth="1.5" />
      <path d="M7 9h7M7 13h5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      <circle cx="18" cy="17" r="3" stroke="currentColor" strokeWidth="1.5" />
      <path d="M20.5 19.5l1.5 1.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  ),
  phi: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.5" />
      <path d="M8 12h8M12 8v8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeDasharray="2 1.5" />
    </svg>
  ),
  human: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle cx="12" cy="8" r="3" stroke="currentColor" strokeWidth="1.5" />
      <path d="M6 20c0-3.314 2.686-6 6-6s6 2.686 6 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      <path d="M16 13l2 2 3-3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ),
  isolation: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <rect x="2" y="7" width="9" height="9" rx="1.5" stroke="currentColor" strokeWidth="1.5" />
      <rect x="13" y="7" width="9" height="9" rx="1.5" stroke="currentColor" strokeWidth="1.5" />
      <path d="M11 11.5h2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeDasharray="1 1" />
      <path d="M11 12.5h2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeDasharray="1 1" opacity="0" />
    </svg>
  ),
  monitoring: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M12 2L2 7l10 5 10-5-10-5z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
      <path d="M2 17l10 5 10-5M2 12l10 5 10-5" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
      <circle cx="19" cy="19" r="3" fill="currentColor" fillOpacity="0.15" stroke="currentColor" strokeWidth="1.5" />
      <path d="M19 17.5v1.5l1 1" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
    </svg>
  ),
  enterprise: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <rect x="3" y="3" width="18" height="18" rx="2" stroke="currentColor" strokeWidth="1.5" />
      <path d="M3 9h18M9 9v12" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  ),
};

const StatusDot = ({ status }: { status: string }) => (
  <span
    className={`cn-roadmap-dot cn-roadmap-dot--${status}`}
    aria-label={status === 'in_progress' ? 'In progress' : 'Planned'}
  />
);

// ── Component ─────────────────────────────────────────────────────────────────

export default function ChartnavSecurity() {
  const { openDemoForm } = useFormsContext();
  const { meta, hero, pillars, noClaimSection, roadmap, cta } = content;

  return (
    <div className="cn-page cn-page--security">
      <Helmet>
        <title>{meta.title}</title>
        <meta name="description" content={meta.description} />
        <meta name="keywords"    content={meta.keywords.join(', ')} />
        <link rel="canonical"    href={`https://arcgsystems.com${meta.canonicalPath}`} />

        {/* OG */}
        <meta property="og:title"       content={meta.title} />
        <meta property="og:description" content={meta.description} />
        <meta property="og:url"         content={`https://arcgsystems.com${meta.canonicalPath}`} />
        <meta property="og:type"        content="website" />
      </Helmet>

      {/* ── 1. Hero ─────────────────────────────────────────────────── */}
      <section className="cn-sec-hero" aria-labelledby="sec-h1">
        <div className="cn-container cn-container--narrow">
          <p className="cn-eyebrow">{hero.eyebrow}</p>
          <h1 id="sec-h1" className="cn-sec-hero__h1">{hero.headline}</h1>
          <p className="cn-sec-hero__sub">{hero.subheadline}</p>
        </div>
      </section>

      {/* ── 2–9. Pillar grid ─────────────────────────────────────────── */}
      <section className="cn-sec-pillars" aria-label="Security capabilities">
        <div className="cn-container">
          <div className="cn-pillars-grid" role="list">
            {pillars.map((p: Pillar) => (
              <article
                key={p.id}
                className="cn-pillar"
                role="listitem"
                aria-labelledby={`pillar-${p.id}`}
              >
                <div className="cn-pillar__icon" aria-hidden="true">
                  {icons[p.id]}
                </div>
                <p className="cn-pillar__eyebrow">{p.eyebrow}</p>
                <h2 id={`pillar-${p.id}`} className="cn-pillar__h">{p.headline}</h2>
                <p className="cn-pillar__body">{p.body}</p>
                {'note' in p && p.note && (
                  <p className="cn-pillar__note">{p.note}</p>
                )}
              </article>
            ))}
          </div>
        </div>
      </section>

      {/* ── 10. What We Do Not Claim ─────────────────────────────────── */}
      <section
        className="cn-sec-noclaim"
        aria-labelledby="noclaim-h"
      >
        <div className="cn-container cn-container--narrow">
          <p className="cn-eyebrow">{noClaimSection.eyebrow}</p>
          <h2 id="noclaim-h" className="cn-sec-h2">{noClaimSection.headline}</h2>
          <p className="cn-sec-intro">{noClaimSection.intro}</p>

          <div className="cn-noclaim-list" role="list">
            {noClaimSection.items.map((item: NoClaim) => (
              <div key={item.label} className="cn-noclaim-item" role="listitem">
                <p className="cn-noclaim-item__label">{item.label}</p>
                <p className="cn-noclaim-item__body">{item.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── 11. Security Roadmap ─────────────────────────────────────── */}
      <section className="cn-sec-roadmap" aria-labelledby="roadmap-h">
        <div className="cn-container cn-container--narrow">
          <p className="cn-eyebrow">{roadmap.eyebrow}</p>
          <h2 id="roadmap-h" className="cn-sec-h2">{roadmap.headline}</h2>
          <p className="cn-sec-intro">{roadmap.intro}</p>

          <ol className="cn-roadmap-list" aria-label="Security roadmap items">
            {roadmap.items.map((item: RoadmapItem) => (
              <li key={item.label} className="cn-roadmap-item">
                <StatusDot status={item.status} />
                <div className="cn-roadmap-item__content">
                  <p className="cn-roadmap-item__label">{item.label}</p>
                  <p className="cn-roadmap-item__body">{item.body}</p>
                </div>
              </li>
            ))}
          </ol>

          <div className="cn-roadmap-legend" aria-label="Status legend">
            <span className="cn-roadmap-legend-item">
              <span className="cn-roadmap-dot cn-roadmap-dot--in_progress" aria-hidden="true" />
              In progress
            </span>
            <span className="cn-roadmap-legend-item">
              <span className="cn-roadmap-dot cn-roadmap-dot--planned" aria-hidden="true" />
              Planned
            </span>
          </div>
        </div>
      </section>

      {/* ── 12. CTA ─────────────────────────────────────────────────── */}
      <section className="cn-sec-cta" aria-labelledby="cta-h">
        <div className="cn-container cn-container--narrow">
          <p className="cn-eyebrow">{cta.eyebrow}</p>
          <h2 id="cta-h" className="cn-sec-cta__h">{cta.headline}</h2>
          <p className="cn-sec-cta__body">{cta.body}</p>
          <div className="cn-cta-pair">
            <a href={cta.primary.href} className="cn-btn cn-btn--primary">
              {cta.primary.label}
            </a>
            <button
              type="button"
              onClick={openDemoForm}
              className="cn-btn cn-btn--ghost"
            >
              {cta.secondary.label}
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}
