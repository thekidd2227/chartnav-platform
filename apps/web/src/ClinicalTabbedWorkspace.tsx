/**
 * ClinicalTabbedWorkspace — Phase 19.
 *
 * Replaces the single-page encounter detail with a 9-tab clinical
 * workspace. The Documentation tab wraps the existing NoteWorkspace
 * (the scribe → review → finalize lifecycle is unchanged). The
 * Imaging tab wraps the existing EyeDiagramPanel (OD/OS retinal
 * diagram). The Chat tab is a frontend-only internal staff chat
 * with .txt / .json export. Every other tab is a properly-labeled
 * read-only review surface with "No data yet" empty states.
 *
 * Safe-claims contract — every label below has been screened
 * against the Phase 17B / 18 forbidden-claims list:
 *
 *   - NO billing / CPT / charges / insurance / claim submission /
 *     coding / payment / revenue-cycle UI.
 *   - NO "Submit order" / "Place order" / "Send referral" /
 *     "Bill" / "Code" buttons. The Labs/Orders Review tab is
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
  type Encounter,
  type Me,
} from "./api";
import { NoteWorkspace } from "./NoteWorkspace";
import { EyeDiagramPanel } from "./EyeDiagramPanel";

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
  | "labs-orders-review"
  | "calendar"
  | "communications"
  | "documents"
  | "chat";

type TabSpec = { id: TabId; label: string };

const TABS: TabSpec[] = [
  { id: "overview", label: "Overview" },
  { id: "clinical", label: "Clinical / Ophthalmology" },
  { id: "documentation", label: "Documentation / EMR-EHR" },
  { id: "imaging", label: "Imaging" },
  { id: "labs-orders-review", label: "Labs / Orders Review" },
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
  const { encounter, identity, me, pendingStatus, onTransition, bannersSlot } =
    props;

  const [active, setActive] = useState<TabId>("overview");

  return (
    <div className="ctw" data-testid="clinical-tabbed-workspace">
      <PatientEncounterHeader encounter={encounter} />
      {bannersSlot}
      <TabBar active={active} onSelect={setActive} />
      <div className="ctw__panel" data-testid={`ctw-panel-${active}`}>
        {active === "overview" && (
          <OverviewTab
            encounter={encounter}
            me={me}
            pendingStatus={pendingStatus}
            onTransition={onTransition}
          />
        )}
        {active === "clinical" && <ClinicalTab />}
        {active === "documentation" && typeof encounter.id === "number" && (
          <NoteWorkspace
            identity={identity}
            me={me}
            encounterId={encounter.id}
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
        )}
        {active === "imaging" && (
          <ImagingTab encounter={encounter} identity={identity} me={me} />
        )}
        {active === "labs-orders-review" && <LabsOrdersReviewTab />}
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
          <span data-testid="ctw-patient-mrn">
            <span className="ctw__meta-label">MRN</span>{" "}
            {encounter.patient_identifier}
          </span>
          <span>
            <span className="ctw__meta-label">Encounter #</span>
            {encounter.id}
          </span>
        </div>
      </div>
      <div className="ctw__encounter-line">
        {/* `detail-status` testid preserved for back-compat with the
            App.test.tsx suite; the visual treatment is the same. */}
        <span
          className="status-pill"
          data-status={encounter.status}
          data-testid="detail-status"
        >
          {encounter.status.replace(/_/g, " ")}
        </span>
        <span data-testid="ctw-encounter-provider">
          <span className="ctw__meta-label">Provider</span>{" "}
          {encounter.provider_name ?? "—"}
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
    </header>
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
}: {
  encounter: Encounter;
  me: Me;
  pendingStatus: string | null;
  onTransition: (status: string) => Promise<void>;
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
        <Field label="Provider">{encounter.provider_name ?? "—"}</Field>
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

      <Card title="Timeline">
        <Field label="Scheduled">{fmt(encounter.scheduled_at)}</Field>
        <Field label="Started">{fmt(encounter.started_at)}</Field>
        <Field label="Completed">{fmt(encounter.completed_at)}</Field>
        <Field label="Created">{fmt(encounter.created_at)}</Field>
      </Card>

      <Card title="Tasks">
        <EmptyState>
          Provider review tasks live in the Documentation tab's action
          review queue. This card surfaces tasks from the practice's
          existing systems if/when wired.
        </EmptyState>
      </Card>

      <Card title="Recent encounters">
        <EmptyState>
          The encounter list lives in the left sidebar. Recent-encounter
          history per patient will surface here once the backend
          endpoint lands.
        </EmptyState>
      </Card>

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

// ---------------------------------------------------------------
// Clinical (Ophthalmology).
// ---------------------------------------------------------------

function ClinicalTab(): JSX.Element {
  const groups: Array<{ name: string; items: string[] }> = [
    {
      name: "Cornea / Anterior segment",
      items: ["Dry eye", "Keratitis", "Corneal abrasion", "Epithelial defect"],
    },
    {
      name: "Retina / AMD / DME",
      items: ["Drusen", "Dot/blot hemorrhage", "Flame hemorrhage", "Microaneurysm"],
    },
    {
      name: "Oculoplastics / Lids / Adnexa",
      items: ["Chalazion", "Blepharitis", "Entropion", "Ectropion"],
    },
    {
      name: "Glaucoma",
      items: ["IOP elevated", "Disc cupping", "Visual field defect"],
    },
  ];

  const [open, setOpen] = useState<string | null>(groups[0].name);
  const [search, setSearch] = useState("");

  const filtered = groups
    .map((g) => ({
      ...g,
      items: g.items.filter((i) =>
        i.toLowerCase().includes(search.toLowerCase())
      ),
    }))
    .filter((g) => g.items.length > 0 || !search);

  return (
    <div className="ctw-clinical" data-testid="ctw-clinical">
      <input
        type="search"
        placeholder="Search clinical shortcuts…"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        data-testid="ctw-clinical-search"
        className="ctw-clinical__search"
      />
      <div className="ctw-clinical__groups">
        {filtered.map((g) => {
          const isOpen = open === g.name || !!search;
          return (
            <details
              key={g.name}
              open={isOpen}
              data-testid={`ctw-clinical-group-${g.name.replace(/\W+/g, "-").toLowerCase()}`}
              onToggle={(e) => {
                if ((e.target as HTMLDetailsElement).open) setOpen(g.name);
              }}
            >
              <summary>{g.name}</summary>
              <ul className="ctw-clinical__items">
                {g.items.map((i) => (
                  <li key={i}>{i}</li>
                ))}
              </ul>
            </details>
          );
        })}
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
// Imaging.
// ---------------------------------------------------------------

function ImagingTab({
  encounter,
  identity,
}: {
  encounter: Encounter;
  identity: string;
  me: Me;
}): JSX.Element {
  const patientId =
    typeof encounter.patient_id === "number" ? encounter.patient_id : null;
  const encounterId =
    typeof encounter.id === "number" ? encounter.id : null;
  return (
    <div className="ctw-imaging" data-testid="ctw-imaging">
      <Card title="OD/OS retinal diagram" wide>
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
      <Card title="Imaging notes">
        <EmptyState>
          OCT, fundus photos, and external imaging will surface here
          when the practice wires a media bucket. ChartNav does not
          order imaging — it views and annotates.
        </EmptyState>
      </Card>
    </div>
  );
}

// ---------------------------------------------------------------
// Labs / Orders Review (REVIEW-ONLY).
// ---------------------------------------------------------------

function LabsOrdersReviewTab(): JSX.Element {
  return (
    <div className="ctw-grid" data-testid="ctw-labs-orders-review">
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
        ChartNav never submits orders, sends referrals, codes, bills,
        or attaches CPT / insurance claims.
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

function ChatTab({
  encounter,
  me,
}: {
  encounter: Encounter;
  me: Me;
}): JSX.Element {
  const storageKey = `chartnav.encounter.${encounter.id}.chat`;
  const [messages, setMessages] = useState<ChatMessage[]>(() => {
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
  const [participant, setParticipant] = useState<
    "Staff" | "Clinician" | "Reviewer"
  >(() =>
    me.role === "clinician"
      ? "Clinician"
      : me.role === "reviewer"
      ? "Reviewer"
      : "Staff"
  );

  useEffect(() => {
    try {
      window.localStorage.setItem(storageKey, JSON.stringify(messages));
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
    setMessages((prev) => [...prev, entry]);
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
          `# Demo-local. Do not paste real PHI.\n` +
          `# Exported ${new Date().toISOString()}\n\n` +
          lines.join("\n"),
      ],
      { type: "text/plain" }
    );
    triggerDownload(blob, `chartnav-chat-encounter-${encounter.id}.txt`);
  }, [messages, encounter.id]);

  const exportJson = useCallback(() => {
    const payload = {
      kind: "chartnav-internal-chat-export",
      encounter_id: encounter.id,
      exported_at: new Date().toISOString(),
      note: "Demo-local. Do not paste real PHI.",
      messages,
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], {
      type: "application/json",
    });
    triggerDownload(blob, `chartnav-chat-encounter-${encounter.id}.json`);
  }, [messages, encounter.id]);

  const clearAll = () => {
    if (
      window.confirm(
        "Clear this encounter's local chat thread? This cannot be undone."
      )
    ) {
      setMessages([]);
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
            No messages yet. Pick a participant role above and send the
            first internal handoff.
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
        placeholder="Internal staff message…"
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
