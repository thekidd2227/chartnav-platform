/**
 * RetinaVisitSequenceRibbon — Phase 71.
 *
 * A buyer-visible 5-step sequence ribbon that explains the retina
 * visit path across the existing tabbed workspace. Each step is a
 * navigation button that focuses the workspace tab where that
 * stage of the visit happens. The ribbon is explanatory —
 * ChartNav does not advance state automatically and does not
 * derive live status from the API. The artifact-level status
 * (draft / entered / reviewed / signed / locked) continues to
 * live inside each panel (Vitals, Fundus, Ambient Documentation).
 *
 * Safety-frame contract:
 *   - Provider-reviewed at every stage. ChartNav drafts; the
 *     clinician signs.
 *   - Fake-data demo only. Not for real PHI.
 *   - Not a certified EHR. Does not replace an EHR.
 *   - Does not diagnose, place orders, send referrals, message
 *     patients, bill, or code.
 *   - The "Signed Lock" step is role-aware. Roles that cannot
 *     sign (technician / reviewer / front_desk) see an explicit
 *     "Requires clinician or admin" affordance rather than a
 *     silent button.
 */

import type { Me, Role } from "./api";

export type RetinaVisitTabId =
  | "overview"
  | "clinical"
  | "documentation"
  | "imaging";

export interface RetinaVisitStep {
  id:
    | "intake"
    | "fundus-drawing"
    | "visit-draft"
    | "provider-review"
    | "signed-lock";
  ordinal: number;
  label: string;
  short: string;
  tab: RetinaVisitTabId;
}

export const RETINA_VISIT_STEPS: RetinaVisitStep[] = [
  {
    id: "intake",
    ordinal: 1,
    label: "Intake",
    short: "Technician Workup & Vitals",
    tab: "clinical",
  },
  {
    id: "fundus-drawing",
    ordinal: 2,
    label: "Fundus Drawing",
    short: "Provider-Reviewed Fundus Drawing Assist",
    tab: "imaging",
  },
  {
    id: "visit-draft",
    ordinal: 3,
    label: "VisitDraft",
    short: "Provider-Reviewed VisitDraft Assist",
    tab: "documentation",
  },
  {
    id: "provider-review",
    ordinal: 4,
    label: "Provider Review",
    short: "Mark each artifact reviewed",
    tab: "documentation",
  },
  {
    id: "signed-lock",
    ordinal: 5,
    label: "Signed Lock",
    short: "Clinician signs; artifacts become immutable",
    tab: "documentation",
  },
];

const SIGNING_ROLES: ReadonlySet<Role> = new Set<Role>([
  "clinician",
  "admin",
]);

function roleFootnote(role: Role): string {
  if (SIGNING_ROLES.has(role)) {
    return "Signed in as a role that can review and sign clinical artifacts. Provider review remains explicit at every step.";
  }
  if (role === "technician") {
    return "Technician role — can complete intake and enter findings, but cannot sign clinical artifacts. Hand off to a clinician for review and signing.";
  }
  if (role === "reviewer") {
    return "Reviewer role — read-only review across artifacts. Cannot sign. Hand off to a clinician for signing.";
  }
  if (role === "front_desk") {
    return "Front-desk role — encounter and scheduling visibility only. Clinical artifacts require a clinician.";
  }
  return "This role cannot sign clinical artifacts. Hand off to a clinician for review and signing.";
}

interface Props {
  me: Me;
  onJumpToTab: (tabId: RetinaVisitTabId) => void;
}

export function RetinaVisitSequenceRibbon({
  me,
  onJumpToTab,
}: Props): JSX.Element {
  const canSign = SIGNING_ROLES.has(me.role);
  return (
    <section
      className="retina-visit-ribbon"
      data-testid="retina-visit-ribbon"
      aria-label="Retina visit sequence"
    >
      <header className="retina-visit-ribbon__head">
        <h3
          className="retina-visit-ribbon__title"
          data-testid="retina-visit-ribbon-title"
        >
          Retina visit sequence
        </h3>
        <p
          className="retina-visit-ribbon__caption"
          data-testid="retina-visit-ribbon-caption"
        >
          Fake-data demo. Provider-reviewed at every stage. ChartNav drafts;
          the clinician signs. Not a certified EHR. Does not diagnose, place
          orders, send referrals, message patients, bill, or code.
        </p>
      </header>
      <ol
        className="retina-visit-ribbon__steps"
        data-testid="retina-visit-ribbon-steps"
      >
        {RETINA_VISIT_STEPS.map((step) => {
          const isSignStep = step.id === "signed-lock";
          const lockedForRole = isSignStep && !canSign;
          return (
            <li
              key={step.id}
              className={
                "retina-visit-ribbon__step" +
                (lockedForRole ? " retina-visit-ribbon__step--locked" : "")
              }
              data-testid={`retina-visit-step-${step.id}`}
              data-locked={lockedForRole ? "true" : "false"}
            >
              <button
                type="button"
                className="retina-visit-ribbon__step-btn"
                onClick={() => onJumpToTab(step.tab)}
                data-testid={`retina-visit-step-btn-${step.id}`}
                aria-label={
                  `Step ${step.ordinal} of ${RETINA_VISIT_STEPS.length}: ` +
                  `${step.label} — ${step.short}. Opens ${step.tab} tab.`
                }
              >
                <span
                  className="retina-visit-ribbon__ordinal"
                  aria-hidden="true"
                >
                  {step.ordinal}
                </span>
                <span className="retina-visit-ribbon__label">
                  {step.label}
                </span>
                <span className="retina-visit-ribbon__short">
                  {step.short}
                </span>
                {lockedForRole && (
                  <span
                    className="retina-visit-ribbon__role-lock"
                    data-testid={`retina-visit-step-role-lock-${step.id}`}
                  >
                    Requires clinician or admin
                  </span>
                )}
              </button>
            </li>
          );
        })}
      </ol>
      <p
        className="retina-visit-ribbon__footnote"
        data-testid="retina-visit-ribbon-footnote"
      >
        {roleFootnote(me.role)}
      </p>
    </section>
  );
}
