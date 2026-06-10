/**
 * ClinicalTabbedWorkspace — Phase 19 + 19B + 19F.
 *
 * Replaces the single-page encounter detail with a 9-tab clinical
 * workspace. The Documentation tab wraps the existing NoteWorkspace
 * (scribe → review → finalize is unchanged). The Imaging tab wraps
 * the existing EyeDiagramPanel (OD/OS retinal diagram). The Chat
 * tab is a frontend-only internal staff chat with .txt / .json
 * export. Every other tab is a properly-labeled read-only review
 * surface with intentional empty-state copy.
 *
 * Phase 19F removes the Billing tab entirely. ChartNav does not
 * bill, code, submit claims, or handle insurance; the prior
 * "review-only Billing tab" was a buyer-trust risk and is
 * replaced by the existing Chat tab as the internal-comms
 * surface. The Communications tab covers internal staff handoffs.
 *
 * Safe-claims contract — every interactive label below has been
 * screened against the Phase 17B / 18 forbidden-claims list:
 *
 *   - NO Billing surface at all. ChartNav does not bill, code,
 *     submit claims, or handle insurance. CPT / Charges /
 *     Insurance / Submit Claim / Auto-code / Auto-bill / Send
 *     Claim / Charge Patient / Bill Insurance / Payment / Claim
 *     are forbidden as visible UI labels anywhere in the
 *     workspace.
 *   - NO "Submit order" / "Place order" / "Send referral" /
 *     "Bill" / "Code" interactive buttons. The Orders & Labs tab is
 *     review-only ("View" / "Mark reviewed" / "Add note").
 *   - NO "Send to patient" / "Patient portal" / "External message
 *     delivery" / "Automated patient message" surfaces. The
 *     Communications tab is internal staff only.
 *   - Chat is labelled "Demo-local internal chat — do not enter
 *     real PHI." and persists only to localStorage on the
 *     operator's machine. No backend round-trip, no patient
 *     messaging.
 *
 * The original NoteWorkspace (`./NoteWorkspace`) is unchanged —
 * this component embeds it inside the Documentation tab.
 */

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";

import {
  encounterSourceLabel,
  allowedNextStatuses,
  EVENT_TYPES,
  type Encounter,
  type Me,
  type WorkflowEvent,
} from "./api";
import { NoteWorkspace } from "./NoteWorkspace";
import { EyeDiagramPanel } from "./EyeDiagramPanel";
import { ImagingPipelinePanel } from "./ImagingPipelinePanel";
import { SpecialtyTrackingPanel } from "./SpecialtyTrackingPanel";
import { FundusChartPanel } from "./features/fundus/FundusChartPanel";
import { AmbientDocumentationPanel } from "./features/ambient/AmbientDocumentationPanel";
import { VitalsWorkupPanel } from "./features/vitals/VitalsWorkupPanel";
import { ProviderActionItemQueue } from "./features/action-queue/ProviderActionItemQueue";
import { InjectionCommandPanel } from "./features/anti-vegf/InjectionCommandPanel";
import { NoteValidationRail } from "./features/note-validation/NoteValidationRail";
import { CataractSurgicalWorkflowPanel } from "./features/cataract/CataractSurgicalWorkflowPanel";
import { GlaucomaProgressionCockpit } from "./features/glaucoma/GlaucomaProgressionCockpit";
import { RetinaVisitPacketPanel } from "./features/retina-summary/RetinaVisitPacketPanel";
import { RetinaVisitSummaryPanel } from "./features/retina-summary/RetinaVisitSummaryPanel";
import {
  RetinaVisitSequenceRibbon,
  type RetinaVisitTabId,
} from "./RetinaVisitSequenceRibbon";

// Local fmt — same shape as App.tsx::fmt. Inlined to avoid a
// shared-utility refactor that would balloon Phase 19's diff.
function fmt(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso.replace(" ", "T"));
  if (isNaN(d.getTime())) return iso;
  return d.toLocaleString();
}

// ---------------------------------------------------------------
// Tab catalog.
// ---------------------------------------------------------------

type TabId =
  | "overview"
  | "clinical"
  | "documentation"
  | "imaging"
  | "orders-labs"
  | "calendar"
  | "communications"
  | "documents"
  | "chat";

type TabSpec = { id: TabId; label: string };

// Phase 19F — exactly 9 tabs. The Billing tab removed in this
// phase; ChartNav does not bill, code, submit claims, or handle
// insurance, so the prior review-only Billing tab is replaced by
// the existing Chat (internal staff) and Communications (internal
// handoffs) surfaces.
const TABS: TabSpec[] = [
  { id: "overview", label: "Overview" },
  { id: "clinical", label: "Clinical / Ophthalmology" },
  { id: "documentation", label: "Documentation / EMR/EHR" },
  { id: "imaging", label: "Imaging" },
  { id: "orders-labs", label: "Labs / Orders Review" },
  { id: "calendar", label: "Calendar" },
  { id: "communications", label: "Communications" },
  { id: "documents", label: "Documents" },
  { id: "chat", label: "Chat" },
];

// ---------------------------------------------------------------
// Top-level component.
// ---------------------------------------------------------------

export interface ClinicalTabbedWorkspaceProps {
  encounter: Encounter;
  identity: string;
  me: Me;
  pendingStatus: string | null;
  onTransition: (status: string) => Promise<void>;
  onSetPendingStatus: (s: string | null) => void;
  onRefreshDetail: () => void;
  /**
   * Phase 19F — Timeline (workflow events) + the Add timeline event
   * composer used to render below the workspace in App.tsx. They
   * are now embedded inside the Overview tab's Timeline card so
   * the demo doesn't show a floating "Add event" section after the
   * tab system. The composer is hidden when `isDemo === true`
   * (the read-only Timeline still renders) so the buyer demo
   * doesn't expose a free-text dev composer.
   */
  events: WorkflowEvent[];
  eventAllowed: boolean;
  pendingEvent: boolean;
  onAddEvent: (type: string, data: string) => Promise<void> | void;
  isDemo: boolean;
  /**
   * The original encounter-detail rendered an "external encounter"
   * banner and a "bridged refresh" banner above the body. To avoid
   * duplicating those code paths, the parent App.tsx still renders
   * those banners — this component only owns the per-tab body.
   */
  bannersSlot?: ReactNode;
}

export function ClinicalTabbedWorkspace(
  props: ClinicalTabbedWorkspaceProps
): JSX.Element {
  const {
    encounter,
    identity,
    me,
    pendingStatus,
    onTransition,
    bannersSlot,
    events,
    eventAllowed,
    pendingEvent,
    onAddEvent,
    isDemo,
  } = props;

  const [active, setActive] = useState<TabId>("overview");

  return (
    <div className="ctw" data-testid="clinical-tabbed-workspace">
      <PatientEncounterHeader encounter={encounter} />
      {bannersSlot}
      <RetinaVisitSequenceRibbon
        me={me}
        onJumpToTab={(tabId: RetinaVisitTabId) => setActive(tabId)}
      />
      <TabBar active={active} onSelect={setActive} />
      <div className="ctw__panel" data-testid={`ctw-panel-${active}`}>
        {active === "overview" && (
          <OverviewTab
            encounter={encounter}
            me={me}
            pendingStatus={pendingStatus}
            onTransition={onTransition}
            events={events}
            eventAllowed={eventAllowed}
            pendingEvent={pendingEvent}
            onAddEvent={onAddEvent}
            isDemo={isDemo}
          />
        )}
        {active === "clinical" && (
          <ClinicalTab identity={identity} me={me} encounter={encounter} />
        )}
        {active === "documentation" && typeof encounter.id === "number" && (
          <DocumentationTab
            identity={identity}
            me={me}
            encounter={encounter}
          />
        )}
        {active === "imaging" && (
          <ImagingTab encounter={encounter} identity={identity} me={me} />
        )}
        {active === "orders-labs" && <OrdersLabsTab />}
        {active === "calendar" && <CalendarTab encounter={encounter} />}
        {active === "communications" && (
          <CommunicationsTab encounter={encounter} me={me} />
        )}
        {active === "documents" && <DocumentsTab encounter={encounter} />}
        {active === "chat" && <ChatTab encounter={encounter} me={me} />}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------
// Patient + encounter sticky header.
// ---------------------------------------------------------------

function PatientEncounterHeader({
  encounter,
}: {
  encounter: Encounter;
}): JSX.Element {
  // Phase 19F — replace the bare em-dash placeholders with
  // intentional empty-state copy so the demo doesn't read as
  // unfinished. The Encounter type still doesn't carry DOB /
  // phone / gender / allergies / conditions / medications / next
  // appointment; rather than invent fake PHI, every absent field
  // labels its own absence ("Not available in demo" /
  // "Not recorded" / "No allergies recorded" / "No active meds
  // recorded" / "Not scheduled"). Last Visit + Provider remain
  // wired to real (seeded) encounter data when present.
  const lastVisit = encounter.completed_at
    ? fmt(encounter.completed_at)
    : "No prior visit on file";
  const provider = encounter.provider_name ?? "Not assigned";
  return (
    <header
      className="ctw__patient-header"
      data-testid="ctw-patient-header"
    >
      <div className="ctw__patient-line">
        <h2 className="ctw__patient-name">
          {encounter.patient_name ?? encounter.patient_identifier}
        </h2>
        <div className="ctw__patient-meta">
          <span data-testid="ctw-patient-dob">
            <span className="ctw__meta-label">DOB</span>{" "}
            <span className="ctw__meta-empty">Not available in demo</span>
          </span>
          <span data-testid="ctw-patient-mrn">
            <span className="ctw__meta-label">MRN</span>{" "}
            {encounter.patient_identifier}
          </span>
          <span data-testid="ctw-patient-phone">
            <span className="ctw__meta-label">Phone</span>{" "}
            <span className="ctw__meta-empty">Not available in demo</span>
          </span>
        </div>
        <div className="ctw__encounter-line">
          <span data-testid="ctw-encounter-number">
            <span className="ctw__meta-label">Encounter #</span>
            {encounter.id}
          </span>
          {/* `detail-status` testid preserved for back-compat with
              App.test.tsx; the visual treatment is the same. */}
          <span
            className="status-pill"
            data-status={encounter.status}
            data-testid="detail-status"
          >
            {encounter.status.replace(/_/g, " ")}
          </span>
          <span data-testid="ctw-encounter-provider">
            <span className="ctw__meta-label">Provider</span>{" "}
            {provider}
          </span>
          <span data-testid="ctw-encounter-location">
            <span className="ctw__meta-label">Location</span> #
            {encounter.location_id}
          </span>
          {/* `detail-source-chip` testid preserved for back-compat. */}
          <span
            className="source-chip"
            data-testid="detail-source-chip"
            data-source={encounter._source ?? "chartnav"}
          >
            {encounterSourceLabel(encounter)}
          </span>
        </div>
      </div>
      <div
        className="ctw__demographics"
        data-testid="ctw-patient-demographics"
      >
        <DemographicCell label="Gender" testid="ctw-demo-gender" empty>
          Not recorded
        </DemographicCell>
        <DemographicCell label="Allergies" testid="ctw-demo-allergies" empty>
          No allergies recorded
        </DemographicCell>
        <DemographicCell label="Conditions" testid="ctw-demo-conditions" empty>
          No conditions recorded
        </DemographicCell>
        <DemographicCell label="Medications" testid="ctw-demo-medications" empty>
          No active meds recorded
        </DemographicCell>
        <DemographicCell label="Last Visit" testid="ctw-demo-last-visit">
          {lastVisit}
        </DemographicCell>
        <DemographicCell label="Next Appt" testid="ctw-demo-next-appt" empty>
          Not scheduled
        </DemographicCell>
        <DemographicCell label="Provider" testid="ctw-demo-provider">
          {provider}
        </DemographicCell>
      </div>
    </header>
  );
}

function DemographicCell({
  label,
  testid,
  children,
  empty,
}: {
  label: string;
  testid: string;
  children: ReactNode;
  empty?: boolean;
}): JSX.Element {
  return (
    <div className="ctw__demo-cell" data-testid={testid}>
      <span className="ctw__demo-label">{label}</span>
      <span
        className={
          "ctw__demo-value" + (empty ? " ctw__demo-value--empty" : "")
        }
      >
        {children}
      </span>
    </div>
  );
}

// ---------------------------------------------------------------
// Tab bar.
// ---------------------------------------------------------------

function TabBar({
  active,
  onSelect,
}: {
  active: TabId;
  onSelect: (t: TabId) => void;
}): JSX.Element {
  return (
    <nav className="ctw__tabbar" role="tablist" data-testid="ctw-tabbar">
      {TABS.map((t) => (
        <button
          key={t.id}
          type="button"
          role="tab"
          aria-selected={active === t.id}
          className={
            "ctw__tab" + (active === t.id ? " ctw__tab--active" : "")
          }
          data-testid={`ctw-tab-${t.id}`}
          onClick={() => onSelect(t.id)}
        >
          {t.label}
        </button>
      ))}
    </nav>
  );
}

// ---------------------------------------------------------------
// Overview.
// ---------------------------------------------------------------

function OverviewTab({
  encounter,
  me,
  pendingStatus,
  onTransition,
  events,
  eventAllowed,
  pendingEvent,
  onAddEvent,
  isDemo,
}: {
  encounter: Encounter;
  me: Me;
  pendingStatus: string | null;
  onTransition: (status: string) => Promise<void>;
  events: WorkflowEvent[];
  eventAllowed: boolean;
  pendingEvent: boolean;
  onAddEvent: (type: string, data: string) => Promise<void> | void;
  isDemo: boolean;
}): JSX.Element {
  const role = me.role;
  const nativeEncounter =
    encounter._source === "chartnav" || encounter._source === undefined;
  const nextStatuses = nativeEncounter
    ? allowedNextStatuses(role, encounter.status)
    : [];

  return (
    <div className="ctw-grid" data-testid="ctw-overview">
      <Card title="Patient snapshot">
        <Field label="Name">
          {encounter.patient_name ?? encounter.patient_identifier}
        </Field>
        <Field label="MRN">{encounter.patient_identifier}</Field>
        <Field label="Provider">
          {encounter.provider_name ?? "Not assigned"}
        </Field>
      </Card>

      <Card title="Visit summary">
        <Field label="Encounter #">{encounter.id}</Field>
        <Field label="Status">
          <span className="status-pill" data-status={encounter.status}>
            {encounter.status.replace(/_/g, " ")}
          </span>
        </Field>
        <Field label="Organization">#{encounter.organization_id}</Field>
        <Field label="Location">#{encounter.location_id}</Field>
      </Card>

      <Card title="Alerts">
        <EmptyState>
          No active alerts. ChartNav surfaces audit-friendly
          provider-review prompts only — never autonomous-diagnosis
          alerts.
        </EmptyState>
      </Card>

      <Card title="Recent encounters">
        <EmptyState>
          The encounter list lives in the left sidebar. Recent-encounter
          history per patient will surface here once the backend
          endpoint lands.
        </EmptyState>
      </Card>

      <Card title="Tasks">
        <EmptyState>
          Provider review tasks live in the Documentation tab's action
          review queue. This card surfaces tasks from the practice's
          existing systems if/when wired.
        </EmptyState>
      </Card>

      <Card title="Favorites">
        <EmptyState>
          Pin frequently-used clinical shortcuts and templates here.
          The library lives in the Clinical / Ophthalmology tab and
          syncs into this panel once a clinician marks favorites.
        </EmptyState>
      </Card>

      <Card title="Timeline" wide>
        <div
          className="ctw-timeline__stamps"
          data-testid="ctw-timeline-stamps"
        >
          <Field label="Scheduled">{fmt(encounter.scheduled_at)}</Field>
          <Field label="Started">{fmt(encounter.started_at)}</Field>
          <Field label="Completed">{fmt(encounter.completed_at)}</Field>
          <Field label="Created">{fmt(encounter.created_at)}</Field>
        </div>
        <h4 className="ctw-timeline__heading" data-testid="ctw-timeline-heading">
          Timeline ({events.length})
        </h4>
        {events.length > 0 ? (
          <ul className="ctw-timeline__events">
            {events.map((ev) => (
              <li className="event-item" key={ev.id}>
                <div className="event-item__head">
                  <span className="event-item__type">{ev.event_type}</span>
                  <span className="event-item__when">{fmt(ev.created_at)}</span>
                </div>
                <div className="event-item__data">{renderEventData(ev)}</div>
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState>
            No timeline events recorded yet for this encounter.
          </EmptyState>
        )}
        <TimelineEventComposer
          eventAllowed={eventAllowed}
          pendingEvent={pendingEvent}
          onAddEvent={onAddEvent}
          isDemo={isDemo}
          role={role}
        />
      </Card>

      {nativeEncounter && (
        <section
          className="ctw-card ctw-card--wide"
          data-testid="ctw-card-provider-action-queue"
        >
          <ProviderActionItemQueue />
        </section>
      )}

      {nativeEncounter && typeof encounter.id === "number" && (
        <section
          className="ctw-card ctw-card--wide"
          data-testid="ctw-card-note-validation-rail"
        >
          <NoteValidationRail encounterId={encounter.id} />
        </section>
      )}

      {nativeEncounter && typeof encounter.id === "number" && (
        <section
          className="ctw-card ctw-card--wide"
          data-testid="ctw-card-retina-visit-summary"
        >
          <RetinaVisitSummaryPanel encounterId={encounter.id} />
        </section>
      )}

      {nativeEncounter && typeof encounter.id === "number" && (
        <section
          className="ctw-card ctw-card--wide"
          data-testid="ctw-card-retina-visit-packet"
        >
          <RetinaVisitPacketPanel encounterId={encounter.id} />
        </section>
      )}

      {nativeEncounter && typeof encounter.patient_id === "number" && (
        <section
          className="ctw-card ctw-card--wide"
          data-testid="ctw-card-anti-vegf-injection"
        >
          <InjectionCommandPanel patientId={encounter.patient_id} />
        </section>
      )}

      {nativeEncounter && typeof encounter.patient_id === "number" && (
        <section
          className="ctw-card ctw-card--wide"
          data-testid="ctw-card-glaucoma-cockpit"
        >
          <GlaucomaProgressionCockpit patientId={encounter.patient_id} />
        </section>
      )}

      {nativeEncounter && typeof encounter.patient_id === "number" && (
        <section
          className="ctw-card ctw-card--wide"
          data-testid="ctw-card-cataract-workflow"
        >
          <CataractSurgicalWorkflowPanel patientId={encounter.patient_id} />
        </section>
      )}

      <Card title="Allowed transitions" wide>
        {nextStatuses.length > 0 ? (
          // `transitions` + `transition-${s}` testids preserved for
          // back-compat with App.test.tsx.
          <div className="actions" data-testid="transitions">
            {nextStatuses.map((s) => (
              <button
                key={s}
                type="button"
                className="btn btn--primary"
                data-testid={`transition-${s}`}
                disabled={pendingStatus !== null}
                onClick={() => onTransition(s)}
              >
                {pendingStatus === s ? "…" : `Move to ${s.replace(/_/g, " ")}`}
              </button>
            ))}
          </div>
        ) : (
          <EmptyState>
            No transitions available from{" "}
            <code>{encounter.status}</code> for role <code>{role}</code>.
          </EmptyState>
        )}
      </Card>
    </div>
  );
}

// Phase 19F — Add timeline event composer. Was a floating section
// in App.tsx below the workspace; now embedded inside Overview's
// Timeline card. Hidden in `?demo=1` so the buyer demo never sees
// the dev composer (the read-only timeline still renders).
// Preserves the `event-form` / `event-denied` / `event-type` /
// `event-data` / `event-submit` testids App.test.tsx asserts on.
function TimelineEventComposer({
  eventAllowed,
  pendingEvent,
  onAddEvent,
  isDemo,
  role,
}: {
  eventAllowed: boolean;
  pendingEvent: boolean;
  onAddEvent: (type: string, data: string) => Promise<void> | void;
  isDemo: boolean;
  role: Me["role"];
}): JSX.Element {
  if (isDemo) {
    return (
      <div
        className="subtle-note ctw-timeline__demo-note"
        data-testid="event-composer-demo-hidden"
      >
        Add timeline event is hidden in demo mode. The timeline above
        is read-only.
      </div>
    );
  }
  if (!eventAllowed) {
    return (
      <div className="subtle-note" data-testid="event-denied">
        Your role (<code>{role}</code>) cannot add workflow events.
        Switch to an admin or clinician identity to write.
      </div>
    );
  }
  return (
    <div className="ctw-timeline__composer">
      <h4 className="ctw-timeline__composer-heading">Add timeline event</h4>
      <TimelineEventForm
        pending={pendingEvent}
        onSubmit={(type, data) => onAddEvent(type, data)}
      />
    </div>
  );
}

function TimelineEventForm({
  pending,
  onSubmit,
}: {
  pending: boolean;
  onSubmit: (type: string, data: string) => void | Promise<void>;
}): JSX.Element {
  const [type, setType] = useState("");
  const [data, setData] = useState("");
  const disabled = !type.trim() || pending;
  return (
    <form
      className="event-form"
      data-testid="event-form"
      onSubmit={async (e) => {
        e.preventDefault();
        if (disabled) return;
        await onSubmit(type.trim(), data);
        setType("");
        setData("");
      }}
    >
      <select
        aria-label="Event type"
        data-testid="event-type"
        value={type}
        onChange={(e) => setType(e.target.value)}
        required
      >
        <option value="" disabled>
          Select event type…
        </option>
        {EVENT_TYPES.map((t) => (
          <option key={t} value={t}>
            {t}
          </option>
        ))}
      </select>
      <textarea
        data-testid="event-data"
        placeholder='event_data (optional JSON, e.g. {"comment":"..."})'
        value={data}
        onChange={(e) => setData(e.target.value)}
      />
      <div className="row">
        <button
          type="submit"
          className="btn btn--primary"
          disabled={disabled}
          data-testid="event-submit"
        >
          {pending ? "Appending…" : "Append event"}
        </button>
        <span className="subtle-note">
          JSON is parsed if valid; otherwise sent as a string.
        </span>
      </div>
    </form>
  );
}

function renderEventData(ev: WorkflowEvent): string {
  const d = ev.event_data;
  if (d == null) return "—";
  if (typeof d === "string") return d;
  if (typeof d === "object") {
    return Object.entries(d as Record<string, unknown>)
      .map(
        ([k, v]) =>
          `${k}: ${typeof v === "object" ? JSON.stringify(v) : String(v)}`
      )
      .join("  ·  ");
  }
  return String(d);
}

// ---------------------------------------------------------------
// Clinical (Ophthalmology).
// ---------------------------------------------------------------

function ClinicalTab({
  identity,
  me,
  encounter,
}: {
  identity: string;
  me: Me;
  encounter: Encounter;
}): JSX.Element {
  // Phase 21A — Specialty Tracking (Retina + Glaucoma) renders at
  // the top of the Clinical tab when the encounter is linked to a
  // native patient. The shortcut grid below is unchanged.
  //
  // Phase 19I — Clinical / Ophthalmology surface restructured
  // from a `<details><summary><ul>` bullet-list (which read as
  // a raw HTML page in screenshot review) into a grid of
  // Cards with pill-button shortcuts. Favorites is pinned
  // first per the Phase 19I brief; other groups follow the
  // brief order. Pills are visually buttons but are
  // intentionally inert (disabled) — these are review-prompt
  // shortcuts the clinician will pin into a draft, not
  // diagnoses ChartNav generates.
  const patientId =
    typeof encounter.patient_id === "number" ? encounter.patient_id : null;
  const encounterId =
    typeof encounter.id === "number" ? encounter.id : null;
  const groups: Array<{ id: string; name: string; items: string[] }> = [
    {
      id: "favorites",
      name: "Favorites",
      items: [], // Empty by default; a clinician pins entries here.
    },
    {
      id: "retina",
      name: "Retina / AMD / DME",
      items: [
        "Drusen",
        "Dot/blot hemorrhage",
        "Flame hemorrhage",
        "Microaneurysm",
        "Macular edema",
        "Subretinal fluid",
      ],
    },
    {
      id: "cornea",
      name: "Cornea / Anterior Segment",
      items: [
        "Dry eye",
        "Keratitis",
        "Corneal abrasion",
        "Epithelial defect",
        "Pterygium",
        "Anterior chamber depth",
      ],
    },
    {
      id: "glaucoma",
      name: "Glaucoma",
      items: [
        "IOP elevated",
        "Disc cupping",
        "Visual field defect",
        "Optic disc pallor",
      ],
    },
    {
      id: "oculoplastics",
      name: "Oculoplastics / Lids / Adnexa",
      items: [
        "Chalazion",
        "Blepharitis",
        "Entropion",
        "Ectropion",
        "Ptosis",
      ],
    },
    {
      id: "general",
      name: "General Ophthalmology",
      items: [
        "Conjunctivitis",
        "Allergic conjunctivitis",
        "Visual acuity decreased",
        "Refraction change",
      ],
    },
  ];

  const [search, setSearch] = useState("");
  const q = search.trim().toLowerCase();

  const filtered = groups.map((g) => ({
    ...g,
    items: q ? g.items.filter((i) => i.toLowerCase().includes(q)) : g.items,
  }));

  return (
    <div className="ctw-clinical" data-testid="ctw-clinical">
      {encounterId !== null && (
        <section
          className="ctw-card ctw-card--wide"
          data-testid="ctw-card-technician-workup-vitals"
        >
          <h3 className="ctw-card__title">Technician Workup &amp; Vitals</h3>
          <div className="ctw-card__body">
            <VitalsWorkupPanel encounterId={encounterId} />
          </div>
        </section>
      )}
      {patientId !== null && (
        <SpecialtyTrackingPanel
          identity={identity}
          me={me}
          patientId={patientId}
          encounterId={encounterId}
        />
      )}
      <p
        className="ctw-clinical__shortcuts-note"
        data-testid="ctw-clinical-shortcuts-note"
      >
        These shortcuts are provider review prompts — common ophthalmology
        findings the clinician pins into the active draft from the
        Documentation tab. ChartNav does not generate diagnoses. Pinning to
        Favorites is a future enhancement; the pills are intentionally inert
        today.
      </p>
      <input
        type="search"
        placeholder="Search clinical shortcuts…"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        data-testid="ctw-clinical-search"
        className="ctw-clinical__search"
      />
      <div className="ctw-grid ctw-clinical__grid">
        {filtered.map((g) => (
          <section
            key={g.id}
            className={
              "ctw-card ctw-clinical__group" +
              (g.id === "favorites" ? " ctw-clinical__group--favorites" : "")
            }
            data-testid={`ctw-clinical-group-${g.id}`}
          >
            <h3 className="ctw-card__title">{g.name}</h3>
            <div className="ctw-card__body">
              {g.items.length === 0 ? (
                <EmptyState>
                  {g.id === "favorites"
                    ? "Pin shortcuts you use most often. Selected pills appear here on subsequent visits."
                    : q
                    ? "No shortcuts match the search."
                    : "No shortcuts in this group yet."}
                </EmptyState>
              ) : (
                <div
                  className="ctw-clinical__pills"
                  data-testid={`ctw-clinical-pills-${g.id}`}
                >
                  {g.items.map((i) => (
                    <button
                      key={i}
                      type="button"
                      className="ctw-clinical__pill"
                      disabled
                      title="Pin into the active draft from the Documentation tab"
                      data-testid={`ctw-clinical-pill-${g.id}-${i
                        .toLowerCase()
                        .replace(/\W+/g, "-")}`}
                    >
                      {i}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </section>
        ))}
      </div>
      <p className="ctw__footnote">
        Provider-reviewed workflow support. ChartNav does not diagnose,
        create orders, send referrals, bill, or message patients
        automatically. Clinical shortcuts surface review prompts only.
      </p>
    </div>
  );
}

// ---------------------------------------------------------------
// Documentation — wraps NoteWorkspace in a polished workbench
// shell with a Transcript → Extracted Facts → AI Draft → Final
// Note stepper header (Phase 19I). NoteWorkspace itself is
// untouched (Phase 17/18/19 contract).
// ---------------------------------------------------------------

const DOC_STEPS = [
  { id: "transcript", label: "Transcript" },
  { id: "facts", label: "Extracted Facts" },
  { id: "draft", label: "AI Draft" },
  { id: "final", label: "Final Note" },
] as const;

function DocumentationTab({
  identity,
  me,
  encounter,
}: {
  identity: string;
  me: Me;
  encounter: Encounter;
}): JSX.Element {
  return (
    <div
      className="ctw-documentation"
      data-testid="ctw-documentation"
    >
      <header
        className="ctw-doc-stepper"
        data-testid="ctw-doc-stepper"
        aria-label="Documentation workflow stages"
      >
        <ol className="ctw-doc-stepper__steps">
          {DOC_STEPS.map((s, idx) => (
            <li
              key={s.id}
              className="ctw-doc-stepper__step"
              data-testid={`ctw-doc-stepper-${s.id}`}
            >
              <span className="ctw-doc-stepper__index">{idx + 1}</span>
              <span className="ctw-doc-stepper__label">{s.label}</span>
            </li>
          ))}
        </ol>
        <p
          className="ctw-doc-stepper__caption"
          data-testid="ctw-doc-stepper-caption"
        >
          Provider-reviewed at every stage. ChartNav drafts; the clinician
          signs. Not a certified EHR. Does not replace your EHR or write
          back automatically. Fake-data demo only.
        </p>
      </header>
      <div
        className="ctw-doc-workbench"
        data-testid="ctw-doc-workbench"
      >
        <NoteWorkspace
          identity={identity}
          me={me}
          encounterId={encounter.id as number}
          patientId={
            typeof encounter.patient_id === "number"
              ? encounter.patient_id
              : null
          }
          patientDisplay={
            encounter.patient_name ?? encounter.patient_identifier
          }
          providerDisplay={encounter.provider_name}
        />
      </div>
      <section
        className="ctw-card ctw-card--wide"
        data-testid="ctw-card-ambient-documentation"
      >
        <h3 className="ctw-card__title">
          Provider-Reviewed Ambient Documentation Assist
        </h3>
        <div className="ctw-card__body">
          {typeof encounter.patient_id === "number" ? (
            <AmbientDocumentationPanel
              patientId={encounter.patient_id}
              encounterId={
                typeof encounter.id === "number" ? encounter.id : undefined
              }
            />
          ) : (
            <div className="ctw-empty">
              Ambient documentation drafting is available once the
              encounter is bridged into ChartNav with a native patient
              row.
            </div>
          )}
        </div>
      </section>
    </div>
  );
}

// ---------------------------------------------------------------
// Imaging.
// ---------------------------------------------------------------

function ImagingTab({
  encounter,
  identity,
  me,
}: {
  encounter: Encounter;
  identity: string;
  me: Me;
}): JSX.Element {
  // Phase 19I — Imaging tab restructure. Top-level surface
  // shows the imaging *workspace* (Upload / OCT / Fundus /
  // Attachments / Imaging Notes / Selected Image Viewer) so
  // a buyer doesn't land on the raw OD/OS retinal canvas as
  // the first thing on the tab. The OD/OS Retinal Workbench
  // moves to the bottom inside a polished wide card so it
  // still demos prominently but is framed as one tool inside
  // a broader imaging surface.
  const patientId =
    typeof encounter.patient_id === "number" ? encounter.patient_id : null;
  const encounterId =
    typeof encounter.id === "number" ? encounter.id : null;
  return (
    <div className="ctw-imaging" data-testid="ctw-imaging">
      {/* Phase 21B — Imaging pipeline (metadata + review workflow).
          Renders at the top of the Imaging tab so the structured
          study list is the first thing a clinician/technician sees.
          The placeholder cards below remain as documentation of
          future surfaces; the OD/OS retinal workbench stays at the
          bottom. */}
      <ImagingPipelinePanel
        identity={identity}
        me={me}
        patientId={patientId}
        encounterId={encounterId}
      />
      <div className="ctw-grid" data-testid="ctw-imaging-grid">
        <Card title="Upload imaging">
          <EmptyState>
            Drag-and-drop OCT, fundus, or external imaging from the
            practice's media bucket. ChartNav views and annotates
            uploaded studies — it does not order imaging.
          </EmptyState>
        </Card>
        <Card title="OCT images">
          <EmptyState>
            OCT studies attached to this encounter surface here once
            the practice's OCT integration is wired. Demo placeholder.
          </EmptyState>
        </Card>
        <Card title="Fundus photos">
          <EmptyState>
            Fundus photographs surface here from the practice's
            existing imaging workflow. Demo placeholder.
          </EmptyState>
        </Card>
        <Card title="Attachments">
          <EmptyState>
            Outside-image attachments (referral PDFs, scanned reports)
            land here. Demo placeholder.
          </EmptyState>
        </Card>
        <Card title="Imaging notes">
          <EmptyState>
            Provider notes attached to a study or scan. Use the
            review-only annotation surface below.
          </EmptyState>
        </Card>
        <Card title="Selected image viewer">
          <EmptyState>
            Click an imaging tile above to load it here. ChartNav
            renders the study read-only; provider review is required
            before any finding lands in the draft note.
          </EmptyState>
        </Card>
      </div>
      <Card title="OD/OS retinal workbench" wide>
        {patientId !== null ? (
          <EyeDiagramPanel
            identity={identity}
            patientId={patientId}
            encounterId={encounterId}
          />
        ) : (
          <EmptyState>
            Retinal diagram is available once the encounter is bridged
            into ChartNav with a native patient row.
          </EmptyState>
        )}
      </Card>
      <Card title="Fundus charts" wide>
        {encounterId !== null ? (
          <FundusChartPanel encounterId={encounterId} />
        ) : (
          <EmptyState>
            Fundus charting is available once the encounter is bridged
            into ChartNav with a native encounter row.
          </EmptyState>
        )}
      </Card>
      <p className="ctw__footnote">
        ChartNav does not order imaging. Studies surface here from the
        practice's existing imaging workflow; ChartNav views,
        annotates, and routes provider-reviewed findings into the
        draft note.
      </p>
    </div>
  );
}

// ---------------------------------------------------------------
// Orders & Labs (REVIEW-ONLY).
// ---------------------------------------------------------------

function OrdersLabsTab(): JSX.Element {
  return (
    <div className="ctw-grid" data-testid="ctw-orders-labs">
      <Card title="Lab Results">
        <EmptyState>
          Review-only view of lab results sent into ChartNav from the
          practice's lab system. ChartNav does not place lab orders.
        </EmptyState>
        <ReviewOnlyActionRow />
      </Card>
      <Card title="Imaging Orders">
        <EmptyState>
          Review-only view of imaging orders the practice's EHR has
          sent into ChartNav. ChartNav does not place imaging orders.
        </EmptyState>
        <ReviewOnlyActionRow />
      </Card>
      <Card title="Procedure Plan">
        <EmptyState>
          Review-only view of procedure plans entered upstream.
          Procedure orders, scheduling, and consent live in the
          practice's EHR — ChartNav does not manage them.
        </EmptyState>
        <ReviewOnlyActionRow />
      </Card>
      <Card title="Review Notes" wide>
        <EmptyState>
          Provider review notes attached to lab / imaging / procedure
          items. Use <strong>Add note</strong> after reviewing each
          item; <strong>Mark reviewed</strong> closes the review row.
        </EmptyState>
        <ReviewOnlyActionRow />
      </Card>
      <p className="ctw__footnote">
        Allowed actions on this tab: <strong>View</strong>,{" "}
        <strong>Mark reviewed</strong>, <strong>Add note</strong>.
        ChartNav never submits orders, sends referrals, or auto-codes
        / auto-bills items reviewed here.
      </p>
    </div>
  );
}

function ReviewOnlyActionRow(): JSX.Element {
  return (
    <div className="ctw-actions" data-testid="ctw-review-actions">
      <button type="button" className="btn btn--ghost" disabled>
        View
      </button>
      <button type="button" className="btn btn--ghost" disabled>
        Mark reviewed
      </button>
      <button type="button" className="btn btn--ghost" disabled>
        Add note
      </button>
    </div>
  );
}

// ---------------------------------------------------------------
// Calendar (read-only view of the encounter's scheduling info).
// ---------------------------------------------------------------

function CalendarTab({ encounter }: { encounter: Encounter }): JSX.Element {
  return (
    <div className="ctw-grid" data-testid="ctw-calendar">
      <Card title="Scheduled time">
        <Field label="Scheduled">{fmt(encounter.scheduled_at)}</Field>
        <Field label="Started">{fmt(encounter.started_at)}</Field>
        <Field label="Completed">{fmt(encounter.completed_at)}</Field>
      </Card>
      <Card title="Provider assignment">
        <Field label="Provider">{encounter.provider_name ?? "—"}</Field>
        <Field label="Location">#{encounter.location_id}</Field>
      </Card>
      <Card title="Calendar surface">
        <EmptyState>
          Calendar is a read-only view of encounter scheduling info.
          ChartNav does not book appointments — booking lives in the
          practice's existing scheduling system.
        </EmptyState>
      </Card>
    </div>
  );
}

// ---------------------------------------------------------------
// Communications (INTERNAL ONLY — no patient send).
// ---------------------------------------------------------------

interface InternalNote {
  id: string;
  author: string;
  role: string;
  body: string;
  created_at: string;
}

function CommunicationsTab({
  encounter,
  me,
}: {
  encounter: Encounter;
  me: Me;
}): JSX.Element {
  const storageKey = `chartnav.encounter.${encounter.id}.internalNotes`;
  const [notes, setNotes] = useState<InternalNote[]>(() => {
    try {
      const raw = window.localStorage.getItem(storageKey);
      if (!raw) return [];
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  });
  const [draft, setDraft] = useState("");

  useEffect(() => {
    try {
      window.localStorage.setItem(storageKey, JSON.stringify(notes));
    } catch {
      // ignore
    }
  }, [notes, storageKey]);

  const addNote = () => {
    const text = draft.trim();
    if (!text) return;
    const entry: InternalNote = {
      id: `n_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`,
      author: me.full_name ?? me.email ?? "Staff",
      role: me.role,
      body: text,
      created_at: new Date().toISOString(),
    };
    setNotes((prev) => [...prev, entry]);
    setDraft("");
  };

  return (
    <div className="ctw-comms" data-testid="ctw-communications">
      <Card title="Internal notes" wide>
        <p className="ctw__footnote">
          Internal staff notes only. ChartNav does not send messages
          to patients, does not deliver to a patient portal, and does
          not route external messages. Stored locally on this device
          only — do not enter real PHI.
        </p>
        <div className="ctw-comms__list" data-testid="ctw-comms-list">
          {notes.length === 0 ? (
            <EmptyState>
              No internal notes yet. Add a staff handoff note below.
            </EmptyState>
          ) : (
            notes.map((n) => (
              <div
                key={n.id}
                className="ctw-comms__entry"
                data-testid={`ctw-comms-entry-${n.id}`}
              >
                <div className="ctw-comms__entry-head">
                  <strong>{n.author}</strong>{" "}
                  <span className="ctw__meta-label">{n.role}</span>{" "}
                  <span className="ctw__meta-label">
                    {new Date(n.created_at).toLocaleString()}
                  </span>
                </div>
                <div className="ctw-comms__entry-body">{n.body}</div>
              </div>
            ))
          )}
        </div>
        <textarea
          className="ctw-comms__composer"
          placeholder="Staff handoff / internal note…"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          data-testid="ctw-comms-composer"
          rows={3}
        />
        <div className="ctw-actions">
          <button
            type="button"
            className="btn btn--primary"
            onClick={addNote}
            data-testid="ctw-comms-add"
          >
            Add note
          </button>
        </div>
      </Card>
      <Card title="Communication log">
        <EmptyState>
          Read-only log of internal staff communications. Routed
          patient comms (phone calls, postal mail, portal messages)
          live in the practice's existing systems.
        </EmptyState>
      </Card>
      <Card title="Message history">
        <EmptyState>
          Internal staff message history surfaces here. ChartNav has
          no patient-send surface and never auto-messages patients.
        </EmptyState>
      </Card>
    </div>
  );
}

// ---------------------------------------------------------------
// Documents.
// ---------------------------------------------------------------

interface DocEntry {
  id: string;
  name: string;
  size: number;
  uploaded_at: string;
}

function DocumentsTab({ encounter }: { encounter: Encounter }): JSX.Element {
  const storageKey = `chartnav.encounter.${encounter.id}.docs`;
  const [docs, setDocs] = useState<DocEntry[]>(() => {
    try {
      const raw = window.localStorage.getItem(storageKey);
      if (!raw) return [];
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  });
  const fileRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    try {
      window.localStorage.setItem(storageKey, JSON.stringify(docs));
    } catch {
      // ignore
    }
  }, [docs, storageKey]);

  const handleFiles = (files: FileList | null) => {
    if (!files) return;
    const entries: DocEntry[] = [];
    for (const f of Array.from(files)) {
      entries.push({
        id: `d_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`,
        name: f.name,
        size: f.size,
        uploaded_at: new Date().toISOString(),
      });
    }
    setDocs((prev) => [...prev, ...entries]);
    if (fileRef.current) fileRef.current.value = "";
  };

  return (
    <div className="ctw-docs" data-testid="ctw-documents">
      <Card title="Document index" wide>
        <p className="ctw__footnote">
          Local document index. File metadata stored on this device
          only; file bytes are not uploaded to ChartNav. Real document
          storage requires the practice's approved object store.
        </p>
        <input
          ref={fileRef}
          type="file"
          multiple
          onChange={(e) => handleFiles(e.target.files)}
          data-testid="ctw-docs-input"
        />
        <ul className="ctw-docs__list" data-testid="ctw-docs-list">
          {docs.length === 0 ? (
            <EmptyState>
              No documents yet. Use the file picker above to log a
              filename.
            </EmptyState>
          ) : (
            docs.map((d) => (
              <li
                key={d.id}
                className="ctw-docs__entry"
                data-testid={`ctw-docs-entry-${d.id}`}
              >
                <strong>{d.name}</strong>{" "}
                <span className="ctw__meta-label">
                  {formatBytes(d.size)} ·{" "}
                  {new Date(d.uploaded_at).toLocaleString()}
                </span>
              </li>
            ))
          )}
        </ul>
      </Card>
    </div>
  );
}

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

// ---------------------------------------------------------------
// Chat — INTERNAL STAFF ONLY, frontend-only, demo-local.
// ---------------------------------------------------------------

interface ChatMessage {
  id: string;
  participant: "Staff" | "Clinician" | "Reviewer";
  author: string;
  body: string;
  created_at: string;
}

// Phase 19I — internal staff recipients available in the Chat
// tab. These are demo-local (no backend round-trip); the
// dropdown lets the operator scope the thread to a single
// recipient so the export captures one conversation rather
// than a single concatenated log. No patient-side recipients
// — the safe-claims contract bans patient messaging.
const CHAT_RECIPIENTS: Array<{
  id: string;
  name: string;
  role: string;
  presence: "online" | "offline" | "away";
}> = [
  { id: "carter", name: "Dr. Carter", role: "Clinician", presence: "online" },
  { id: "patel", name: "Dr. Patel", role: "Clinician", presence: "away" },
  { id: "admin-front-desk", name: "Admin", role: "Front Desk", presence: "online" },
  { id: "reviewer", name: "Reviewer", role: "Reviewer", presence: "offline" },
];

function ChatTab({
  encounter,
  me,
}: {
  encounter: Encounter;
  me: Me;
}): JSX.Element {
  // Phase 19I — recipient-scoped storage. Each recipient has
  // its own thread keyed by encounter + recipient id.
  const [recipientId, setRecipientId] = useState<string>(
    CHAT_RECIPIENTS[0].id
  );
  const recipient =
    CHAT_RECIPIENTS.find((r) => r.id === recipientId) ?? CHAT_RECIPIENTS[0];

  const storageKey =
    `chartnav.encounter.${encounter.id}.chat.${recipientId}`;
  const [messagesByRecipient, setMessagesByRecipient] = useState<
    Record<string, ChatMessage[]>
  >({});

  // Lazy-load the active thread from localStorage when the
  // recipient changes (or first render).
  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(storageKey);
      const parsed = raw ? JSON.parse(raw) : [];
      setMessagesByRecipient((prev) => ({
        ...prev,
        [recipientId]: Array.isArray(parsed) ? parsed : [],
      }));
    } catch {
      setMessagesByRecipient((prev) => ({ ...prev, [recipientId]: [] }));
    }
  }, [recipientId, storageKey]);

  const messages = messagesByRecipient[recipientId] ?? [];

  const [draft, setDraft] = useState("");
  const [participant, setParticipant] = useState<
    "Staff" | "Clinician" | "Reviewer"
  >(() =>
    me.role === "clinician"
      ? "Clinician"
      : me.role === "reviewer"
      ? "Reviewer"
      : "Staff"
  );

  // Persist the active thread when it changes.
  useEffect(() => {
    try {
      window.localStorage.setItem(
        storageKey,
        JSON.stringify(messages)
      );
    } catch {
      // ignore
    }
  }, [messages, storageKey]);

  const sendMessage = () => {
    const text = draft.trim();
    if (!text) return;
    const entry: ChatMessage = {
      id: `c_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`,
      participant,
      author: me.full_name ?? me.email ?? "Staff",
      body: text,
      created_at: new Date().toISOString(),
    };
    setMessagesByRecipient((prev) => ({
      ...prev,
      [recipientId]: [...(prev[recipientId] ?? []), entry],
    }));
    setDraft("");
  };

  const exportTxt = useCallback(() => {
    const lines = messages.map(
      (m) =>
        `[${new Date(m.created_at).toLocaleString()}] ` +
        `${m.participant} (${m.author}): ${m.body}`
    );
    const blob = new Blob(
      [
        `# ChartNav internal chat — encounter #${encounter.id}\n` +
          `# Recipient: ${recipient.name} (${recipient.role})\n` +
          `# Demo-local. Do not paste real PHI.\n` +
          `# Exported ${new Date().toISOString()}\n\n` +
          lines.join("\n"),
      ],
      { type: "text/plain" }
    );
    triggerDownload(
      blob,
      `chartnav-chat-encounter-${encounter.id}-${recipient.id}.txt`
    );
  }, [messages, encounter.id, recipient]);

  const exportJson = useCallback(() => {
    const payload = {
      kind: "chartnav-internal-chat-export",
      encounter_id: encounter.id,
      recipient: {
        id: recipient.id,
        name: recipient.name,
        role: recipient.role,
      },
      exported_at: new Date().toISOString(),
      note: "Demo-local. Do not paste real PHI.",
      messages,
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], {
      type: "application/json",
    });
    triggerDownload(
      blob,
      `chartnav-chat-encounter-${encounter.id}-${recipient.id}.json`
    );
  }, [messages, encounter.id, recipient]);

  const clearAll = () => {
    if (
      window.confirm(
        `Clear the chat thread with ${recipient.name}? This cannot be undone.`
      )
    ) {
      setMessagesByRecipient((prev) => ({ ...prev, [recipientId]: [] }));
    }
  };

  return (
    <div className="ctw-chat" data-testid="ctw-chat">
      <div
        className="ctw-chat__banner"
        data-testid="ctw-chat-banner"
      >
        Demo-local internal chat — do not enter real PHI.
      </div>

      {/* Phase 19I — recipient selector. Scopes the thread,
          composer placeholder, and export filename to one
          internal staff member. No patient recipients are
          listed; the safe-claims contract bans patient
          messaging. */}
      <div
        className="ctw-chat__recipient"
        data-testid="ctw-chat-recipient"
      >
        <label
          htmlFor="ctw-chat-recipient-select"
          className="ctw__meta-label"
        >
          Send internal message to
        </label>
        <select
          id="ctw-chat-recipient-select"
          className="ctw-chat__recipient-select"
          data-testid="ctw-chat-recipient-select"
          value={recipientId}
          onChange={(e) => setRecipientId(e.target.value)}
        >
          {CHAT_RECIPIENTS.map((r) => (
            <option
              key={r.id}
              value={r.id}
              data-testid={`ctw-chat-recipient-option-${r.id}`}
            >
              {r.name} — {r.role}
            </option>
          ))}
        </select>
        <div
          className="ctw-chat__recipient-card"
          data-testid="ctw-chat-recipient-card"
        >
          <span className="ctw-chat__recipient-name">
            {recipient.name}
          </span>
          <span className="ctw-chat__recipient-role">
            {recipient.role}
          </span>
          <span
            className={
              "ctw-chat__recipient-presence ctw-chat__recipient-presence--" +
              recipient.presence
            }
            data-presence={recipient.presence}
            data-testid="ctw-chat-recipient-presence"
          >
            {recipient.presence === "online"
              ? "Online"
              : recipient.presence === "away"
              ? "Away"
              : "Offline"}
          </span>
        </div>
      </div>

      <div className="ctw-chat__participants" data-testid="ctw-chat-participants">
        <span className="ctw__meta-label">Speaking as</span>
        {(["Staff", "Clinician", "Reviewer"] as const).map((p) => (
          <button
            key={p}
            type="button"
            className={
              "btn btn--ghost" +
              (participant === p ? " btn--selected" : "")
            }
            data-testid={`ctw-chat-participant-${p.toLowerCase()}`}
            onClick={() => setParticipant(p)}
          >
            {p}
          </button>
        ))}
      </div>
      <div className="ctw-chat__thread" data-testid="ctw-chat-thread">
        {messages.length === 0 ? (
          <EmptyState>
            No messages yet with {recipient.name}. Pick a participant
            role above and send the first internal handoff.
          </EmptyState>
        ) : (
          messages.map((m) => (
            <div
              key={m.id}
              className="ctw-chat__message"
              data-participant={m.participant}
              data-testid={`ctw-chat-message-${m.id}`}
            >
              <div className="ctw-chat__message-head">
                <strong>{m.author}</strong>{" "}
                <span className="ctw__meta-label">{m.participant}</span>{" "}
                <span className="ctw__meta-label">
                  {new Date(m.created_at).toLocaleString()}
                </span>
              </div>
              <div className="ctw-chat__message-body">{m.body}</div>
            </div>
          ))
        )}
      </div>
      <textarea
        className="ctw-chat__composer"
        placeholder={`Message ${recipient.name} internally…`}
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        data-testid="ctw-chat-composer"
        rows={2}
      />
      <div className="ctw-actions">
        <button
          type="button"
          className="btn btn--primary"
          onClick={sendMessage}
          data-testid="ctw-chat-send"
        >
          Send
        </button>
        <button
          type="button"
          className="btn btn--ghost"
          onClick={exportTxt}
          data-testid="ctw-chat-export-txt"
        >
          Export chat (.txt)
        </button>
        <button
          type="button"
          className="btn btn--ghost"
          onClick={exportJson}
          data-testid="ctw-chat-export-json"
        >
          Export chat (.json)
        </button>
        <button
          type="button"
          className="btn btn--ghost"
          onClick={clearAll}
          data-testid="ctw-chat-clear"
        >
          Clear thread
        </button>
      </div>
      <p className="ctw__footnote">
        Internal staff chat only. No patient-send surface. No external
        delivery. No automated patient messaging. The thread persists
        only in this browser's localStorage and is intended for
        operator demos and rehearsals.
      </p>
    </div>
  );
}

// Phase 19F — the prior review-only Billing tab is removed.
// ChartNav does not bill, code, submit claims, or handle
// insurance. The Chat tab covers internal staff comms; the
// Communications tab covers internal handoffs. CPT / Charges /
// Insurance / Submit Claim / Auto-code / Auto-bill / Send Claim /
// Charge Patient / Bill Insurance / Payment / Claim are forbidden
// as visible UI labels everywhere in the workspace.

function triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 0);
}

// ---------------------------------------------------------------
// Shared building blocks.
// ---------------------------------------------------------------

function Card({
  title,
  children,
  wide,
}: {
  title: string;
  children: ReactNode;
  wide?: boolean;
}): JSX.Element {
  return (
    <section
      className={"ctw-card" + (wide ? " ctw-card--wide" : "")}
      data-testid={`ctw-card-${title.toLowerCase().replace(/\W+/g, "-")}`}
    >
      <h3 className="ctw-card__title">{title}</h3>
      <div className="ctw-card__body">{children}</div>
    </section>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}): JSX.Element {
  return (
    <div className="ctw-field">
      <span className="ctw-field__label">{label}</span>
      <span className="ctw-field__value">{children}</span>
    </div>
  );
}

function EmptyState({ children }: { children: ReactNode }): JSX.Element {
  return <div className="ctw-empty">{children}</div>;
}

// Exported for tests so the test file can iterate the tab list
// without redeclaring it.
export const __TABS_FOR_TEST = TABS;
