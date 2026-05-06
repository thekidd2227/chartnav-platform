// LandingPage — Phase 16.
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
// visual proof is inline SVG plus CSS-styled text panels. All copy
// uses the safe phrasing list documented in
// docs/chartnav-website-proof-upgrade-conversion-layer.md and
// asserted by apps/web/src/test/WebsiteProofUpgrade.test.tsx.
//
// Phase 16 ships only this page, its tests, the CTA contract, and
// docs. No new clinical feature, no backend change, no new schema,
// no external LLM, no orders / coding / referrals / patient
// messaging, no real-PHI claim, no unsupported HIPAA / SOC 2 /
// certified-EHR claim.

import { useMemo } from "react";

interface ModuleCard {
  id: string;
  title: string;
  body: string;
}

const MODULES: ModuleCard[] = [
  {
    id: "scribe",
    title: "AI scribe session lifecycle",
    body:
      "Drafts a structured note from source text or transcript. " +
      "The provider reviews and explicitly finalizes — never automatic. " +
      "Finalized sessions are immutable.",
  },
  {
    id: "proposals",
    title: "Retinal proposal review",
    body:
      "Generates OD/OS annotation proposals from finalized findings " +
      "text. Read-only suggestions; nothing lands on the diagram " +
      "until the provider explicitly applies a proposal.",
  },
  {
    id: "diagram",
    title: "OD/OS retinal drawing canvas",
    body:
      "Provider-authored OD/OS annotations with normalized " +
      "coordinates. Saved artifacts are versioned; signed artifacts " +
      "are immutable in place — edits create an explicit fork.",
  },
  {
    id: "summary",
    title: "Patient-friendly summary",
    body:
      "Plain-language draft built from finalized scribe content. " +
      "The provider edits, reviews, and finalizes. ChartNav never " +
      "sends the summary to the patient.",
  },
  {
    id: "brief",
    title: "Pre-visit clinical brief",
    body:
      "Derived view of available chart records with explicit data " +
      "gaps. Surfaces what is and is not on file before the visit. " +
      "Not a clinical decision.",
  },
  {
    id: "queue",
    title: "Provider action review queue",
    body:
      "Review tasks only — sign unsigned diagram, finalize summary, " +
      "review chart language. Suggested → accepted → completed. " +
      "Dismissed and completed are immutable. Never an order.",
  },
  {
    id: "demo",
    title: "Guided demo mode",
    body:
      "Opt-in (?demo=1) presenter overlay with an 8-step workflow " +
      "stepper, on-screen cues, and Reset. Deterministic by design; " +
      "no API calls; no clinical state side effects.",
  },
  {
    id: "pilot",
    title: "Pilot-readiness package",
    body:
      "Eight-doc pilot packet covering readiness, deployment, " +
      "admin onboarding, security review, support runbook, " +
      "demo→pilot transition, known limitations, success metrics.",
  },
];

interface WorkflowStage {
  id: string;
  label: string;
  short: string;
}

const WORKFLOW: WorkflowStage[] = [
  { id: "scribe", label: "Scribe session", short: "Draft → review → finalize" },
  { id: "proposals", label: "Findings proposals", short: "Read-only suggestions" },
  { id: "diagram", label: "OD/OS diagram", short: "Apply, save, sign" },
  { id: "summary", label: "Patient summary", short: "Provider-reviewed draft" },
  { id: "brief", label: "Pre-visit brief", short: "Derived chart context" },
  { id: "queue", label: "Action review queue", short: "Suggested → accepted → completed" },
  { id: "demo", label: "Guided demo", short: "Pilot-ready" },
];

const SAFETY_BULLETS: string[] = [
  "Provider-reviewed workflow support.",
  "ChartNav does not diagnose, create orders, send referrals, bill, or message patients automatically.",
  "Every clinical artifact requires explicit provider review before it is treated as final.",
];

const NON_GOALS: string[] = [
  "Not a certified EHR replacement.",
  "Not autonomous diagnosis.",
  "Not automatic orders, coding, referrals, or patient messaging.",
  "Not real-PHI production without legal / security review and a BAA.",
];

interface SafetyModelRow {
  state: string;
  body: string;
}

const SAFETY_MODEL: SafetyModelRow[] = [
  {
    state: "Draft",
    body:
      "All AI-assisted artifacts start as a draft for the provider to review. " +
      "Nothing is treated as final until an explicit click.",
  },
  {
    state: "Review",
    body:
      "Provider edits and explicitly marks the artifact reviewed. " +
      "Required before finalize.",
  },
  {
    state: "Finalize",
    body:
      "Explicit finalize stamps the artifact and renders it immutable. " +
      "Re-edits to a signed retinal artifact create an explicit fork.",
  },
  {
    state: "Audit",
    body:
      "Every mutation emits a metadata-only audit row. Section bodies, " +
      "summary text, scribe text, and brief sections never reach the audit log.",
  },
  {
    state: "Org isolation",
    body:
      "Cross-organization access returns 404 patient_not_found. " +
      "Every per-source SELECT re-asserts the org filter for defense in depth.",
  },
  {
    state: "RBAC",
    body:
      "Admin and clinician can write across the workflow. Reviewer is " +
      "read-only. Reviewer write attempts return 403 role_forbidden.",
  },
];

// Inline SVG workflow diagram. Rendered inline so it lives in the
// HTML stream — no binary asset, no fetch, no animation. Each stage
// is keyboard-focusable and gets its own data-testid.
function WorkflowDiagram() {
  const w = 760;
  const h = 220;
  const stageWidth = (w - 40) / WORKFLOW.length;
  const y = h / 2;
  return (
    <svg
      viewBox={`0 0 ${w} ${h}`}
      className="landing-page__workflow-svg"
      role="img"
      aria-label="ChartNav ophthalmology clinical workflow"
      data-testid="landing-workflow-diagram"
    >
      <title>ChartNav ophthalmology clinical workflow</title>
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
        x2={20 + stageWidth * (WORKFLOW.length - 1) + stageWidth / 2}
        y2={y}
        stroke="#0B6E79"
        strokeWidth="2"
        strokeDasharray="6 4"
        markerEnd="url(#lp-arrow)"
      />
      {WORKFLOW.map((s, i) => {
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
function ProviderControlDiagram() {
  return (
    <svg
      viewBox="0 0 540 200"
      className="landing-page__control-svg"
      role="img"
      aria-label="Provider-in-control state model"
      data-testid="landing-provider-control-diagram"
    >
      <title>Provider-in-control state model</title>
      {[
        { x: 60, label: "Draft", id: "draft" },
        { x: 220, label: "Reviewed", id: "reviewed" },
        { x: 380, label: "Finalized", id: "finalized" },
      ].map((s) => (
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
        review
      </text>
      <text x="300" y="92" textAnchor="middle" fontSize="11" fill="#5b7079">
        finalize
      </text>
      <text
        x="270"
        y="170"
        textAnchor="middle"
        fontSize="12"
        fill="#5b7079"
        data-testid="landing-control-immutable-note"
      >
        Finalized artifacts are immutable. Re-edits to signed retinal artifacts create an explicit fork.
      </text>
    </svg>
  );
}

interface Props {
  /**
   * Override the contact href used by the request-demo CTA. The
   * default is `mailto:hello@chartnavmd.com` because the repo does
   * not yet ship an intake form route — this matches the spec's
   * "If no form exists, use a safe link/CTA placeholder" guidance.
   */
  contactHref?: string;
}

export function LandingPage({
  contactHref = "mailto:hello@chartnavmd.com",
}: Props) {
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
      role="main"
    >
      {/* HERO */}
      <section
        className="landing-page__hero"
        data-testid="landing-hero"
      >
        <div className="landing-page__brand">
          <img
            className="landing-page__brand-logo"
            src="/brand/chartnav-logo.svg"
            alt="ChartNav"
            width="170"
            height="38"
          />
        </div>

        <h1
          className="landing-page__hero-title"
          data-testid="landing-hero-title"
        >
          ChartNav is an ophthalmology-specific clinical workflow
          assistant — provider-reviewed at every step.
        </h1>
        <p
          className="landing-page__hero-sub"
          data-testid="landing-hero-sub"
        >
          Help your providers review documentation, retinal findings,
          OD/OS diagrams, patient summaries, pre-visit context, and
          action queues — without giving up control.
        </p>

        <p
          className="landing-page__safety-line"
          data-testid="landing-safety-line"
        >
          Provider-reviewed workflow support. ChartNav does not
          diagnose, create orders, send referrals, bill, or message
          patients automatically.
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
            Request a fake-patient demo
          </a>
          <a
            className="landing-page__cta landing-page__cta--secondary"
            href="#workflow"
            data-testid="landing-cta-see-workflow"
          >
            See how the workflow works
          </a>
        </div>
      </section>

      {/* WORKFLOW */}
      <section
        id="workflow"
        className="landing-page__section"
        data-testid="landing-workflow-section"
      >
        <h2>From note to retina-ready chart</h2>
        <p className="landing-page__lead">
          Seven explicit steps. The provider drives every transition.
        </p>
        <WorkflowDiagram />
        <ol
          className="landing-page__workflow-list"
          data-testid="landing-workflow-list"
        >
          {WORKFLOW.map((s, i) => (
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
        <h2>Built for ophthalmology, end to end</h2>
        <ul className="landing-page__bullet-grid">
          <li>
            <strong>OD/OS retinal canvas.</strong> Normalized
            coordinates per eye pane. Drawing, signing, and forking
            are first-class concepts — not features bolted onto a
            generic SOAP-note generator.
          </li>
          <li>
            <strong>Findings vocabulary that matches the chart.</strong>
            {" "}Drusen, dot/blot hemorrhage, flame hemorrhage,
            microaneurysm, neovascularization. Not a primary-care
            shortcut library.
          </li>
          <li>
            <strong>Superior / inferior / nasal / temporal
            placement.</strong>{" "}
            Annotations carry their position relative to the macula
            and disc on each eye, so a follow-up provider sees the
            same picture you saw.
          </li>
          <li>
            <strong>Provider-reviewed diagram signing.</strong> Signed
            artifacts are immutable in place. Edits create an explicit
            fork with a parent pointer; the original signature
            survives.
          </li>
          <li>
            <strong>Ophthalmology-flavored documentation flow.</strong>
            {" "}Closed structured-note vocabulary (chief complaint,
            HPI, exam, assessment, plan). The patient-friendly
            summary template composes from already-stored ophthalmic
            content (visual acuity, IOP, plan, follow-up).
          </li>
        </ul>
      </section>

      {/* PROVIDER-IN-CONTROL SAFETY MODEL */}
      <section
        className="landing-page__section landing-page__section--accent"
        data-testid="landing-provider-control-section"
      >
        <h2>The provider controls every step</h2>
        <p className="landing-page__lead">
          Drafts wait for explicit review. Finalize is a click.
          Signed artifacts are immutable. ChartNav surfaces structured
          chart context — the provider decides.
        </p>
        <ProviderControlDiagram />
        <dl
          className="landing-page__safety-dl"
          data-testid="landing-safety-model-list"
        >
          {SAFETY_MODEL.map((row) => (
            <div
              key={row.state}
              data-testid={`landing-safety-model-${row.state.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}
            >
              <dt>{row.state}</dt>
              <dd>{row.body}</dd>
            </div>
          ))}
        </dl>
      </section>

      {/* MODULES */}
      <section
        className="landing-page__section"
        data-testid="landing-modules-section"
      >
        <h2>What's in the workflow</h2>
        <p className="landing-page__lead">
          Eight modules. All built. All provider-reviewed.
        </p>
        <ul
          className="landing-page__module-grid"
          data-testid="landing-module-grid"
        >
          {MODULES.map((m) => (
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
        <h2>Before ChartNav · With ChartNav</h2>
        <div className="landing-page__before-after">
          <div data-testid="landing-before">
            <h3>Before</h3>
            <ul>
              <li>Free-form notes drift across the chart.</li>
              <li>Retinal findings live in narrative text only.</li>
              <li>OD/OS diagrams are paper or one-off.</li>
              <li>Patient-friendly summaries are written from scratch.</li>
              <li>No structured pre-visit chart prep.</li>
            </ul>
          </div>
          <div data-testid="landing-after">
            <h3>With ChartNav</h3>
            <ul>
              <li>Structured ophthalmology note vocabulary, provider-reviewed.</li>
              <li>Retinal findings tied to OD/OS canvas annotations.</li>
              <li>OD/OS diagrams versioned and signed; edits fork explicitly.</li>
              <li>Patient summary drafts composed from finalized chart content.</li>
              <li>Pre-visit brief surfaces source counts and explicit gaps.</li>
            </ul>
          </div>
        </div>
      </section>

      {/* DEMO / PILOT CTA */}
      <section
        className="landing-page__section landing-page__section--accent"
        data-testid="landing-demo-pilot-section"
      >
        <h2>Built for pilot conversations</h2>
        <p>
          Live demos run on fake demo data only. Real patient data
          requires a Business Associate Agreement (or equivalent),
          a security review of the deployment posture, and a
          controlled-pilot mode — see the pilot readiness packet for
          gating items.
        </p>
        <ul className="landing-page__bullet-grid">
          <li>
            <strong>Live fake-patient demo.</strong> Five minutes,
            seven steps, every step provider-reviewed.
          </li>
          <li>
            <strong>Controlled pilot conversation.</strong> Pilot
            readiness checklist, deployment guide, security review
            packet — buyer-safe phrasing throughout.
          </li>
          <li>
            <strong>Provider-in-control workflow.</strong> Discuss
            how the draft / review / finalize state model fits your
            ophthalmology practice.
          </li>
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
            Discuss a controlled ophthalmology pilot
          </a>
          <a
            className="landing-page__cta landing-page__cta--secondary"
            href={contactHref}
            data-testid="landing-cta-review-workflow"
          >
            Review the provider-in-control workflow
          </a>
        </div>
      </section>

      {/* WHAT CHARTNAV IS NOT */}
      <section
        className="landing-page__section"
        data-testid="landing-non-goals-section"
      >
        <h2>What ChartNav is not</h2>
        <ul
          className="landing-page__non-goals"
          data-testid="landing-non-goals-list"
        >
          {NON_GOALS.map((line, i) => (
            <li key={i}>{line}</li>
          ))}
        </ul>
        <p
          className="landing-page__safety-line"
          data-testid="landing-non-goals-safety-line"
        >
          {SAFETY_BULLETS.join(" ")}
        </p>
      </section>

      {/* FOOTER */}
      <footer
        className="landing-page__footer"
        data-testid="landing-footer"
      >
        <p>
          ChartNav is operated by ARCG. {lastUpdated && (
            <span data-testid="landing-footer-updated">
              Page rendered {lastUpdated}.
            </span>
          )}
        </p>
        <p>
          The product app is at{" "}
          <a href="/" data-testid="landing-footer-app-link">
            the ChartNav workspace
          </a>
          . The Phase 13 demo guide and Phase 15 Guided Demo Mode
          are opt-in there. The pilot readiness packet lives under
          <code>docs/pilot/</code>.
        </p>
      </footer>
    </main>
  );
}
