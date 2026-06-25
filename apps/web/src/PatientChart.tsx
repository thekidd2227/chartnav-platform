import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ApiError,
  ChartSection,
  Encounter,
  Me,
  Patient,
  PatientPatchBody,
  getPatient,
  listPatientChartSections,
  listPatientEncounters,
  patchPatient,
} from "./api";
import { EyeDiagramPanel } from "./EyeDiagramPanel";

interface PatientChartProps {
  identity: string;
  me: Me | null;
  patientId: number;
  onClose: () => void;
}

type SectionKey = string;

export function PatientChart({
  identity,
  me,
  patientId,
  onClose,
}: PatientChartProps) {
  const [patient, setPatient] = useState<Patient | null>(null);
  const [encounters, setEncounters] = useState<Encounter[]>([]);
  const [sections, setSections] = useState<ChartSection[]>([]);
  const [activeKey, setActiveKey] = useState<SectionKey>("overview");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [p, encs, secs] = await Promise.all([
        getPatient(identity, patientId),
        listPatientEncounters(identity, patientId),
        listPatientChartSections(identity, patientId),
      ]);
      setPatient(p);
      setEncounters(encs);
      setSections(secs.sections);
    } catch (e) {
      setError(friendly(e));
    } finally {
      setLoading(false);
    }
  }, [identity, patientId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const activeSection = useMemo(
    () => sections.find((s) => s.key === activeKey) ?? sections[0] ?? null,
    [sections, activeKey]
  );

  if (loading && !patient) {
    return (
      <div className="patient-chart" data-testid="patient-chart">
        <div className="empty">Loading patient chart…</div>
      </div>
    );
  }

  if (error || !patient) {
    return (
      <div className="patient-chart" data-testid="patient-chart">
        <div
          className="banner banner--error"
          role="alert"
          data-testid="patient-chart-error"
        >
          {error ?? "Patient not found."}
        </div>
        <button className="btn" onClick={onClose} data-testid="chart-back">
          ← Back to workflow
        </button>
      </div>
    );
  }

  return (
    <div className="patient-chart" data-testid="patient-chart">
      <PatientChartHeader patient={patient} onClose={onClose} />
      <div className="patient-chart__layout">
        <SectionSidebar
          sections={sections}
          activeKey={activeKey}
          onSelect={setActiveKey}
        />
        <section className="patient-chart__panel" data-testid="chart-panel">
          {activeSection && (
            <SectionPanel
              section={activeSection}
              patient={patient}
              encounters={encounters}
              identity={identity}
              me={me}
              onPatientUpdated={(p) => setPatient(p)}
            />
          )}
        </section>
      </div>
    </div>
  );
}

// -----------------------------------------------------------------
// Header
// -----------------------------------------------------------------

function PatientChartHeader({
  patient,
  onClose,
}: {
  patient: Patient;
  onClose: () => void;
}) {
  const fullName = displayName(patient);
  const ageStr = ageFromDob(patient.date_of_birth);
  const dobStr = patient.date_of_birth ?? "—";
  const status = isActive(patient.is_active) ? "active" : "inactive";

  return (
    <header className="patient-chart__header" data-testid="patient-chart-header">
      <div className="patient-chart__heading">
        <button
          className="btn btn--muted"
          onClick={onClose}
          data-testid="chart-back"
          aria-label="Back to workflow"
        >
          ←
        </button>
        <div>
          <h1 data-testid="patient-name">{fullName}</h1>
          <div className="patient-chart__sub">
            <span data-testid="patient-mrn">MRN {patient.patient_identifier}</span>
            <span aria-hidden="true">·</span>
            <span data-testid="patient-dob">DOB {dobStr}{ageStr ? ` (${ageStr})` : ""}</span>
            {patient.sex_at_birth && (
              <>
                <span aria-hidden="true">·</span>
                <span data-testid="patient-sex">{patient.sex_at_birth}</span>
              </>
            )}
            <span aria-hidden="true">·</span>
            <span
              className={`status-pill`}
              data-testid="patient-status"
              data-status={status}
            >
              {status}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
}

// -----------------------------------------------------------------
// Sidebar
// -----------------------------------------------------------------

function SectionSidebar({
  sections,
  activeKey,
  onSelect,
}: {
  sections: ChartSection[];
  activeKey: SectionKey;
  onSelect: (key: SectionKey) => void;
}) {
  return (
    <nav
      className="patient-chart__nav"
      aria-label="Chart sections"
      data-testid="chart-nav"
    >
      <ul>
        {sections.map((s) => (
          <li key={s.key}>
            <button
              type="button"
              className={
                "chart-tab" + (s.key === activeKey ? " is-active" : "")
              }
              onClick={() => onSelect(s.key)}
              data-testid={`chart-tab-${s.key}`}
              data-status={s.status}
            >
              <span className="chart-tab__label">{s.label}</span>
              {s.status !== "active" && (
                <span
                  className="chart-tab__badge"
                  data-testid={`chart-tab-badge-${s.key}`}
                >
                  {s.status === "placeholder" ? "soon" : "off"}
                </span>
              )}
            </button>
          </li>
        ))}
      </ul>
    </nav>
  );
}

// -----------------------------------------------------------------
// Section panels
// -----------------------------------------------------------------

function SectionPanel({
  section,
  patient,
  encounters,
  identity,
  me,
  onPatientUpdated,
}: {
  section: ChartSection;
  patient: Patient;
  encounters: Encounter[];
  identity: string;
  me: Me | null;
  onPatientUpdated: (p: Patient) => void;
}) {
  if (section.key === "overview") {
    return (
      <OverviewPanel
        patient={patient}
        identity={identity}
        me={me}
        onPatientUpdated={onPatientUpdated}
      />
    );
  }
  if (section.key === "encounters") {
    return <EncountersPanel encounters={encounters} />;
  }
  if (section.key === "eye_diagrams") {
    // Mainline-wins: embed the canonical EyeDiagramPanel (RetinalDrawingCanvas
    // + RetinalProposalReview, backed by /patients/{id}/eye-diagrams on
    // chart_artifacts.drawing_json). The chart isn't encounter-scoped, so no
    // encounter context is passed. RBAC is enforced server-side.
    return (
      <EyeDiagramPanel
        identity={identity}
        patientId={patient.id}
        encounterId={null}
      />
    );
  }
  return <PlaceholderPanel section={section} />;
}

function PlaceholderPanel({ section }: { section: ChartSection }) {
  return (
    <div
      className="empty"
      data-testid={`placeholder-${section.key}`}
      data-section-status={section.status}
    >
      <h2 style={{ marginTop: 0 }}>{section.label}</h2>
      <p>{section.description}</p>
      <p className="subtle-note">
        <strong>Not implemented yet.</strong>
        {section.future_module
          ? ` Tracked under ${section.future_module}.`
          : ""}
      </p>
    </div>
  );
}

// -----------------------------------------------------------------
// Overview
// -----------------------------------------------------------------

function OverviewPanel({
  patient,
  identity,
  me,
  onPatientUpdated,
}: {
  patient: Patient;
  identity: string;
  me: Me | null;
  onPatientUpdated: (p: Patient) => void;
}) {
  const [editing, setEditing] = useState(false);
  const canEdit = me?.role === "admin" || me?.role === "clinician";

  if (editing && canEdit) {
    return (
      <OverviewEditor
        patient={patient}
        identity={identity}
        onCancel={() => setEditing(false)}
        onSaved={(p) => {
          onPatientUpdated(p);
          setEditing(false);
        }}
      />
    );
  }

  return (
    <div data-testid="overview-panel">
      <div className="patient-chart__section-head">
        <h2>Overview</h2>
        {canEdit && (
          <button
            className="btn"
            onClick={() => setEditing(true)}
            data-testid="overview-edit"
          >
            Edit demographics
          </button>
        )}
      </div>
      <dl className="detail__facts" data-testid="overview-facts">
        <Fact label="Legal name" value={`${patient.first_name} ${patient.last_name}`} />
        <Fact label="Preferred name" value={patient.preferred_name} />
        <Fact label="Pronouns" value={patient.pronouns} />
        <Fact label="DOB" value={patient.date_of_birth} />
        <Fact label="Sex at birth" value={patient.sex_at_birth} />
        <Fact label="Gender identity" value={patient.gender_identity} />
        <Fact label="Preferred language" value={patient.preferred_language} />
        <Fact label="Race" value={patient.race} />
        <Fact label="Ethnicity" value={patient.ethnicity} />
        <Fact label="Email" value={patient.email} />
        <Fact label="Phone" value={patient.phone} />
        <Fact
          label="Address"
          value={[
            patient.address_line1,
            patient.address_line2,
            [patient.address_city, patient.address_state, patient.address_postal_code]
              .filter(Boolean)
              .join(", "),
            patient.address_country,
          ]
            .filter(Boolean)
            .join(" • ") || null}
        />
        <Fact
          label="Emergency contact"
          value={
            patient.emergency_contact_name
              ? `${patient.emergency_contact_name}` +
                (patient.emergency_contact_relationship
                  ? ` (${patient.emergency_contact_relationship})`
                  : "") +
                (patient.emergency_contact_phone
                  ? ` — ${patient.emergency_contact_phone}`
                  : "")
              : null
          }
        />
        <Fact label="External ref" value={patient.external_ref} />
      </dl>
    </div>
  );
}

function Fact({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div data-testid={`fact-${label.toLowerCase().replace(/\s+/g, "-")}`}>
      <dt>{label}</dt>
      <dd>{value || <span className="subtle-note">—</span>}</dd>
    </div>
  );
}

function OverviewEditor({
  patient,
  identity,
  onCancel,
  onSaved,
}: {
  patient: Patient;
  identity: string;
  onCancel: () => void;
  onSaved: (p: Patient) => void;
}) {
  const [form, setForm] = useState<PatientPatchBody>(() => ({
    first_name: patient.first_name,
    last_name: patient.last_name,
    middle_name: patient.middle_name ?? null,
    preferred_name: patient.preferred_name ?? null,
    pronouns: patient.pronouns ?? null,
    gender_identity: patient.gender_identity ?? null,
    preferred_language: patient.preferred_language ?? null,
    race: patient.race ?? null,
    ethnicity: patient.ethnicity ?? null,
    email: patient.email ?? null,
    phone: patient.phone ?? null,
    address_line1: patient.address_line1 ?? null,
    address_city: patient.address_city ?? null,
    address_state: patient.address_state ?? null,
    address_postal_code: patient.address_postal_code ?? null,
    emergency_contact_name: patient.emergency_contact_name ?? null,
    emergency_contact_phone: patient.emergency_contact_phone ?? null,
    emergency_contact_relationship: patient.emergency_contact_relationship ?? null,
  }));
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const update = (key: keyof PatientPatchBody, v: string) => {
    setForm((prev) => ({ ...prev, [key]: v.trim() === "" ? null : v }));
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setPending(true);
    setError(null);
    try {
      const updated = await patchPatient(identity, patient.id, form);
      onSaved(updated);
    } catch (err) {
      setError(friendly(err));
    } finally {
      setPending(false);
    }
  };

  return (
    <form
      onSubmit={submit}
      data-testid="overview-editor"
      className="overview-editor"
    >
      <div className="patient-chart__section-head">
        <h2>Edit demographics</h2>
      </div>
      <div className="overview-editor__grid">
        <Field label="First name" value={form.first_name ?? ""} onChange={(v) => update("first_name", v)} />
        <Field label="Last name" value={form.last_name ?? ""} onChange={(v) => update("last_name", v)} />
        <Field label="Preferred name" value={form.preferred_name ?? ""} onChange={(v) => update("preferred_name", v)} />
        <Field label="Pronouns" value={form.pronouns ?? ""} onChange={(v) => update("pronouns", v)} />
        <Field label="Gender identity" value={form.gender_identity ?? ""} onChange={(v) => update("gender_identity", v)} />
        <Field label="Preferred language" value={form.preferred_language ?? ""} onChange={(v) => update("preferred_language", v)} />
        <Field label="Race" value={form.race ?? ""} onChange={(v) => update("race", v)} />
        <Field label="Ethnicity" value={form.ethnicity ?? ""} onChange={(v) => update("ethnicity", v)} />
        <Field label="Email" value={form.email ?? ""} onChange={(v) => update("email", v)} type="email" />
        <Field label="Phone" value={form.phone ?? ""} onChange={(v) => update("phone", v)} />
        <Field label="Address line 1" value={form.address_line1 ?? ""} onChange={(v) => update("address_line1", v)} />
        <Field label="City" value={form.address_city ?? ""} onChange={(v) => update("address_city", v)} />
        <Field label="State" value={form.address_state ?? ""} onChange={(v) => update("address_state", v)} />
        <Field label="Postal code" value={form.address_postal_code ?? ""} onChange={(v) => update("address_postal_code", v)} />
        <Field label="Emergency contact" value={form.emergency_contact_name ?? ""} onChange={(v) => update("emergency_contact_name", v)} />
        <Field label="Emergency phone" value={form.emergency_contact_phone ?? ""} onChange={(v) => update("emergency_contact_phone", v)} />
        <Field label="Relationship" value={form.emergency_contact_relationship ?? ""} onChange={(v) => update("emergency_contact_relationship", v)} />
      </div>
      {error && (
        <div className="banner banner--error" role="alert" data-testid="overview-edit-error">
          {error}
        </div>
      )}
      <div className="row" style={{ justifyContent: "flex-end", gap: 8, marginTop: 12 }}>
        <button
          type="button"
          className="btn btn--muted"
          onClick={onCancel}
          disabled={pending}
        >
          Cancel
        </button>
        <button
          type="submit"
          className="btn btn--primary"
          disabled={pending}
          data-testid="overview-save"
        >
          {pending ? "Saving…" : "Save"}
        </button>
      </div>
    </form>
  );
}

function Field({
  label,
  value,
  onChange,
  type,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
}) {
  return (
    <label>
      <span>{label}</span>
      <input
        type={type ?? "text"}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        data-testid={`field-${label.toLowerCase().replace(/\s+/g, "-")}`}
      />
    </label>
  );
}

// -----------------------------------------------------------------
// Encounters
// -----------------------------------------------------------------

function EncountersPanel({ encounters }: { encounters: Encounter[] }) {
  return (
    <div data-testid="encounters-panel">
      <h2>Encounters ({encounters.length})</h2>
      {encounters.length === 0 ? (
        <div className="empty" data-testid="encounters-empty">
          No encounters on file.
        </div>
      ) : (
        <table className="enc-table" data-testid="enc-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Status</th>
              <th>Provider</th>
              <th>Scheduled</th>
              <th>Created</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {encounters.map((e) => (
              <tr key={String(e.id)} data-testid={`enc-row-${e.id}`}>
                <td>#{e.id}</td>
                <td>
                  <span className="status-pill" data-status={e.status}>
                    {e.status.replace(/_/g, " ")}
                  </span>
                </td>
                <td>{e.provider_name}</td>
                <td>{fmt(e.scheduled_at)}</td>
                <td>{fmt(e.created_at)}</td>
                <td>
                  <a
                    href={`?encounter=${e.id}`}
                    className="btn btn--muted"
                    data-testid={`open-enc-${e.id}`}
                  >
                    Open
                  </a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

// -----------------------------------------------------------------
// Helpers
// -----------------------------------------------------------------

function displayName(p: Patient): string {
  if (p.display_name) return p.display_name;
  if (p.preferred_name) return `${p.preferred_name} ${p.last_name}`;
  return `${p.first_name} ${p.last_name}`;
}

function isActive(v: number | boolean): boolean {
  if (typeof v === "boolean") return v;
  return v !== 0;
}

function ageFromDob(dob: string | null): string | null {
  if (!dob) return null;
  const d = new Date(dob);
  if (Number.isNaN(d.getTime())) return null;
  const now = new Date();
  let age = now.getFullYear() - d.getFullYear();
  const m = now.getMonth() - d.getMonth();
  if (m < 0 || (m === 0 && now.getDate() < d.getDate())) age--;
  return `${age}y`;
}

function fmt(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(String(iso).replace(" ", "T"));
  if (isNaN(d.getTime())) return iso;
  return d.toLocaleString();
}

function friendly(e: unknown): string {
  if (e instanceof ApiError) return `${e.status} ${e.errorCode} — ${e.reason}`;
  if (e instanceof Error) return e.message;
  return String(e);
}
