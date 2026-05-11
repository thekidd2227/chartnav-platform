// Phase 21A — Retina + Glaucoma specialty tracking panel.
//
// Renders inside the existing Clinical / Ophthalmology tab (above
// the shortcut grid) without disturbing the existing workspace.
//
// All clinical text is provider-entered and provider-reviewed. The
// panel does NOT diagnose, dose, recommend treatment, place orders,
// generate referrals, message patients, bill, or grade severity. Any
// label that looks numeric (target IOP, latest IOP, cup-to-disc
// ratio) is a value the provider has typed in — not a value ChartNav
// has computed.

import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  ApiError,
  GlaucomaIopCreateInput,
  GlaucomaIopMeasurement,
  GlaucomaTrackingCreateInput,
  GlaucomaTrackingRecord,
  GlaucomaVisualFieldCreateInput,
  GlaucomaVisualFieldTest,
  Me,
  RetinaInjectionCreateInput,
  RetinaInjectionEvent,
  RetinaTrackingCreateInput,
  RetinaTrackingRecord,
  SpecialtyEye,
  SpecialtyEyeOdOs,
  SpecialtyReviewStatus,
  createPatientGlaucomaIopMeasurement,
  createPatientGlaucomaTracking,
  createPatientGlaucomaVisualField,
  createPatientRetinaInjection,
  createPatientRetinaTracking,
  listPatientGlaucomaIopMeasurements,
  listPatientGlaucomaTracking,
  listPatientGlaucomaVisualFields,
  listPatientRetinaInjections,
  listPatientRetinaTracking,
  updatePatientGlaucomaTracking,
  updatePatientRetinaTracking,
} from "./api";

const TRACKING_WRITE_ROLES = new Set(["admin", "clinician"]);
const MEASUREMENT_WRITE_ROLES = new Set(["admin", "clinician", "technician"]);
const READ_ROLES = new Set(["admin", "clinician", "reviewer", "technician"]);

const REVIEW_STATUSES: SpecialtyReviewStatus[] = [
  "draft",
  "needs_review",
  "reviewed",
  "archived",
];

const EYE_VALUES_OD_OS_OU: SpecialtyEye[] = ["OD", "OS", "OU"];
const EYE_VALUES_OD_OS: SpecialtyEyeOdOs[] = ["OD", "OS"];

interface Props {
  identity: string;
  me: Me;
  patientId: number;
  encounterId: number | null;
}

function friendly(err: unknown): string {
  if (err instanceof ApiError) return `${err.errorCode}: ${err.reason}`;
  return err instanceof Error ? err.message : String(err);
}

function isoToShort(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString();
}

export function SpecialtyTrackingPanel({
  identity,
  me,
  patientId,
  encounterId,
}: Props) {
  const canRead = READ_ROLES.has(me.role);
  const canWriteTracking = TRACKING_WRITE_ROLES.has(me.role);
  const canWriteMeasurement = MEASUREMENT_WRITE_ROLES.has(me.role);

  if (!canRead) {
    return (
      <section
        className="specialty-tracking specialty-tracking--blocked"
        data-testid="specialty-tracking-blocked"
        aria-label="Specialty tracking"
      >
        <h2 className="specialty-tracking__title">Specialty Tracking</h2>
        <p className="specialty-tracking__empty">
          Your role does not have access to clinical specialty
          tracking. Switch to a clinical identity to view this panel.
        </p>
      </section>
    );
  }

  return (
    <section
      className="specialty-tracking"
      data-testid="specialty-tracking"
      data-role={me.role}
      aria-label="Specialty tracking"
    >
      <header className="specialty-tracking__header">
        <h2 className="specialty-tracking__title">
          Specialty Tracking — Provider Reviewed
        </h2>
        <p className="specialty-tracking__subtitle subtle-note">
          Longitudinal retina and glaucoma findings the provider
          records. ChartNav does not diagnose, dose, place orders,
          send referrals, message patients, or grade severity
          automatically.
        </p>
      </header>

      <RetinaSection
        identity={identity}
        patientId={patientId}
        encounterId={encounterId}
        canWriteTracking={canWriteTracking}
        canWriteMeasurement={canWriteMeasurement}
      />

      <GlaucomaSection
        identity={identity}
        patientId={patientId}
        encounterId={encounterId}
        canWriteTracking={canWriteTracking}
        canWriteMeasurement={canWriteMeasurement}
      />
    </section>
  );
}

// ----------------------------------------------------------------
// Retina section
// ----------------------------------------------------------------

function RetinaSection({
  identity,
  patientId,
  encounterId,
  canWriteTracking,
  canWriteMeasurement,
}: {
  identity: string;
  patientId: number;
  encounterId: number | null;
  canWriteTracking: boolean;
  canWriteMeasurement: boolean;
}) {
  const [rows, setRows] = useState<RetinaTrackingRecord[]>([]);
  const [injections, setInjections] = useState<RetinaInjectionEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [showInjection, setShowInjection] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [tracking, inj] = await Promise.all([
        listPatientRetinaTracking(identity, patientId),
        listPatientRetinaInjections(identity, patientId),
      ]);
      setRows(tracking.items);
      setInjections(inj.items);
    } catch (e) {
      setError(friendly(e));
    } finally {
      setLoading(false);
    }
  }, [identity, patientId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return (
    <div className="specialty-tracking__section" data-testid="specialty-retina">
      <SectionHead
        title="Retina Tracking"
        action={
          canWriteTracking && (
            <button
              type="button"
              className="btn btn--primary"
              data-testid="retina-add"
              onClick={() => setShowCreate((v) => !v)}
            >
              {showCreate ? "Cancel" : "+ Add retina tracking"}
            </button>
          )
        }
      />

      {error && (
        <div
          className="banner banner--error"
          role="alert"
          data-testid="retina-error"
        >
          {error}
        </div>
      )}

      {showCreate && (
        <RetinaCreateForm
          identity={identity}
          patientId={patientId}
          encounterId={encounterId}
          onCreated={() => {
            setShowCreate(false);
            void refresh();
          }}
        />
      )}

      {loading && rows.length === 0 ? (
        <p className="specialty-tracking__empty" data-testid="retina-loading">
          Loading retina tracking…
        </p>
      ) : rows.length === 0 ? (
        <p className="specialty-tracking__empty" data-testid="retina-empty">
          No retina tracking yet.
        </p>
      ) : (
        <ul className="specialty-tracking__cards" data-testid="retina-cards">
          {rows.map((row) => (
            <RetinaCard
              key={row.id}
              row={row}
              identity={identity}
              patientId={patientId}
              canWriteTracking={canWriteTracking}
              onUpdated={() => void refresh()}
            />
          ))}
        </ul>
      )}

      <SectionHead
        title="Retina Injection History"
        small
        action={
          canWriteMeasurement && (
            <button
              type="button"
              className="btn"
              data-testid="retina-add-injection"
              onClick={() => setShowInjection((v) => !v)}
            >
              {showInjection ? "Cancel" : "+ Add injection event"}
            </button>
          )
        }
      />

      {showInjection && (
        <RetinaInjectionForm
          identity={identity}
          patientId={patientId}
          encounterId={encounterId}
          onCreated={() => {
            setShowInjection(false);
            void refresh();
          }}
        />
      )}

      {injections.length === 0 ? (
        <p
          className="specialty-tracking__empty"
          data-testid="retina-injections-empty"
        >
          No injection events recorded yet.
        </p>
      ) : (
        <table
          className="specialty-tracking__table"
          data-testid="retina-injections"
        >
          <thead>
            <tr>
              <th>Eye</th>
              <th>Medication</th>
              <th>Procedure date</th>
              <th>Notes</th>
            </tr>
          </thead>
          <tbody>
            {injections.map((row) => (
              <tr key={row.id}>
                <td>{row.eye}</td>
                <td>{row.medication ?? "—"}</td>
                <td>{isoToShort(row.procedure_date)}</td>
                <td>{row.notes ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function RetinaCard({
  row,
  identity,
  patientId,
  canWriteTracking,
  onUpdated,
}: {
  row: RetinaTrackingRecord;
  identity: string;
  patientId: number;
  canWriteTracking: boolean;
  onUpdated: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const updateStatus = useCallback(
    async (next: SpecialtyReviewStatus) => {
      setBusy(true);
      setError(null);
      try {
        await updatePatientRetinaTracking(identity, patientId, row.id, {
          review_status: next,
        });
        onUpdated();
      } catch (e) {
        setError(friendly(e));
      } finally {
        setBusy(false);
      }
    },
    [identity, patientId, row.id, onUpdated]
  );

  return (
    <li
      className="specialty-tracking__card"
      data-testid={`retina-card-${row.id}`}
      data-eye={row.eye}
    >
      <div className="specialty-tracking__card-head">
        <span className="specialty-tracking__pill">{row.eye}</span>
        <h4 className="specialty-tracking__card-title">{row.condition}</h4>
        <span
          className={`specialty-tracking__status specialty-tracking__status--${row.review_status}`}
        >
          {row.review_status}
        </span>
      </div>
      <dl className="specialty-tracking__dl">
        <Field label="Severity" value={row.severity} />
        <Field label="Last OCT" value={isoToShort(row.last_oct_at)} />
        <Field label="Last fundus" value={isoToShort(row.last_fundus_at)} />
        <Field
          label="Follow-up interval"
          value={row.follow_up_interval}
        />
        <Field
          label="Injection history summary"
          value={row.injection_history_summary}
          wide
        />
        <Field
          label="Provider assessment"
          value={row.provider_assessment}
          wide
        />
      </dl>
      {error && (
        <div className="banner banner--error" role="alert">
          {error}
        </div>
      )}
      {canWriteTracking ? (
        <div className="specialty-tracking__card-actions">
          <select
            data-testid={`retina-status-select-${row.id}`}
            value={row.review_status}
            disabled={busy}
            onChange={(e) =>
              void updateStatus(e.target.value as SpecialtyReviewStatus)
            }
          >
            {REVIEW_STATUSES.map((s) => (
              <option key={s} value={s}>
                {s.replace(/_/g, " ")}
              </option>
            ))}
          </select>
          {row.review_status !== "reviewed" && (
            <button
              type="button"
              className="btn"
              data-testid={`retina-mark-reviewed-${row.id}`}
              onClick={() => void updateStatus("reviewed")}
              disabled={busy}
            >
              Mark reviewed
            </button>
          )}
        </div>
      ) : (
        <p
          className="subtle-note"
          data-testid={`retina-readonly-${row.id}`}
        >
          Read-only — your role cannot update this record.
        </p>
      )}
    </li>
  );
}

function RetinaCreateForm({
  identity,
  patientId,
  encounterId,
  onCreated,
}: {
  identity: string;
  patientId: number;
  encounterId: number | null;
  onCreated: () => void;
}) {
  const [eye, setEye] = useState<SpecialtyEye>("OD");
  const [condition, setCondition] = useState("");
  const [severity, setSeverity] = useState("");
  const [followUp, setFollowUp] = useState("");
  const [assessment, setAssessment] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = useCallback(async () => {
    if (!condition.trim()) {
      setError("Condition is required.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const input: RetinaTrackingCreateInput = {
        eye,
        condition: condition.trim(),
        severity: severity.trim() || null,
        follow_up_interval: followUp.trim() || null,
        provider_assessment: assessment.trim() || null,
        encounter_id: encounterId,
      };
      await createPatientRetinaTracking(identity, patientId, input);
      onCreated();
    } catch (e) {
      setError(friendly(e));
    } finally {
      setBusy(false);
    }
  }, [
    assessment,
    condition,
    encounterId,
    eye,
    followUp,
    identity,
    patientId,
    onCreated,
    severity,
  ]);

  return (
    <form
      className="specialty-tracking__form"
      data-testid="retina-create-form"
      onSubmit={(e) => {
        e.preventDefault();
        void submit();
      }}
    >
      <FieldRow label="Eye">
        <EyeSelect
          value={eye}
          onChange={setEye}
          allowOu
          testid="retina-create-eye"
        />
      </FieldRow>
      <FieldRow label="Condition">
        <input
          type="text"
          value={condition}
          onChange={(e) => setCondition(e.target.value)}
          required
          maxLength={200}
          data-testid="retina-create-condition"
        />
      </FieldRow>
      <FieldRow label="Severity">
        <input
          type="text"
          value={severity}
          onChange={(e) => setSeverity(e.target.value)}
          maxLength={64}
          data-testid="retina-create-severity"
        />
      </FieldRow>
      <FieldRow label="Follow-up interval">
        <input
          type="text"
          value={followUp}
          onChange={(e) => setFollowUp(e.target.value)}
          maxLength={64}
          placeholder="e.g. 4 weeks"
          data-testid="retina-create-follow-up"
        />
      </FieldRow>
      <FieldRow label="Provider assessment">
        <textarea
          value={assessment}
          onChange={(e) => setAssessment(e.target.value)}
          maxLength={8000}
          rows={3}
          data-testid="retina-create-assessment"
        />
      </FieldRow>
      {error && (
        <div className="banner banner--error" role="alert">
          {error}
        </div>
      )}
      <button
        type="submit"
        className="btn btn--primary"
        disabled={busy}
        data-testid="retina-create-submit"
      >
        {busy ? "Saving…" : "Save retina tracking"}
      </button>
    </form>
  );
}

function RetinaInjectionForm({
  identity,
  patientId,
  encounterId,
  onCreated,
}: {
  identity: string;
  patientId: number;
  encounterId: number | null;
  onCreated: () => void;
}) {
  const [eye, setEye] = useState<SpecialtyEye>("OD");
  const [medication, setMedication] = useState("");
  const [procedureDate, setProcedureDate] = useState("");
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const input: RetinaInjectionCreateInput = {
        eye,
        medication: medication.trim() || null,
        procedure_date: procedureDate || null,
        notes: notes.trim() || null,
        encounter_id: encounterId,
      };
      await createPatientRetinaInjection(identity, patientId, input);
      onCreated();
    } catch (e) {
      setError(friendly(e));
    } finally {
      setBusy(false);
    }
  }, [eye, medication, procedureDate, notes, encounterId, identity, patientId, onCreated]);

  return (
    <form
      className="specialty-tracking__form"
      data-testid="retina-injection-form"
      onSubmit={(e) => {
        e.preventDefault();
        void submit();
      }}
    >
      <FieldRow label="Eye">
        <EyeSelect value={eye} onChange={setEye} allowOu testid="retina-injection-eye" />
      </FieldRow>
      <FieldRow label="Medication">
        <input
          type="text"
          value={medication}
          onChange={(e) => setMedication(e.target.value)}
          maxLength={200}
          data-testid="retina-injection-medication"
        />
      </FieldRow>
      <FieldRow label="Procedure date">
        <input
          type="datetime-local"
          value={procedureDate}
          onChange={(e) => setProcedureDate(e.target.value)}
          data-testid="retina-injection-date"
        />
      </FieldRow>
      <FieldRow label="Notes">
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          maxLength={4000}
          rows={2}
          data-testid="retina-injection-notes"
        />
      </FieldRow>
      {error && (
        <div className="banner banner--error" role="alert">
          {error}
        </div>
      )}
      <button
        type="submit"
        className="btn btn--primary"
        disabled={busy}
        data-testid="retina-injection-submit"
      >
        {busy ? "Saving…" : "Save injection event"}
      </button>
    </form>
  );
}

// ----------------------------------------------------------------
// Glaucoma section
// ----------------------------------------------------------------

function GlaucomaSection({
  identity,
  patientId,
  encounterId,
  canWriteTracking,
  canWriteMeasurement,
}: {
  identity: string;
  patientId: number;
  encounterId: number | null;
  canWriteTracking: boolean;
  canWriteMeasurement: boolean;
}) {
  const [rows, setRows] = useState<GlaucomaTrackingRecord[]>([]);
  const [iops, setIops] = useState<GlaucomaIopMeasurement[]>([]);
  const [vfs, setVfs] = useState<GlaucomaVisualFieldTest[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [showIop, setShowIop] = useState(false);
  const [showVf, setShowVf] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [tracking, iopList, vfList] = await Promise.all([
        listPatientGlaucomaTracking(identity, patientId),
        listPatientGlaucomaIopMeasurements(identity, patientId),
        listPatientGlaucomaVisualFields(identity, patientId),
      ]);
      setRows(tracking.items);
      setIops(iopList.items);
      setVfs(vfList.items);
    } catch (e) {
      setError(friendly(e));
    } finally {
      setLoading(false);
    }
  }, [identity, patientId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return (
    <div
      className="specialty-tracking__section"
      data-testid="specialty-glaucoma"
    >
      <SectionHead
        title="Glaucoma Tracking"
        action={
          canWriteTracking && (
            <button
              type="button"
              className="btn btn--primary"
              data-testid="glaucoma-add"
              onClick={() => setShowCreate((v) => !v)}
            >
              {showCreate ? "Cancel" : "+ Add glaucoma tracking"}
            </button>
          )
        }
      />

      {error && (
        <div
          className="banner banner--error"
          role="alert"
          data-testid="glaucoma-error"
        >
          {error}
        </div>
      )}

      {showCreate && (
        <GlaucomaCreateForm
          identity={identity}
          patientId={patientId}
          encounterId={encounterId}
          onCreated={() => {
            setShowCreate(false);
            void refresh();
          }}
        />
      )}

      {loading && rows.length === 0 ? (
        <p
          className="specialty-tracking__empty"
          data-testid="glaucoma-loading"
        >
          Loading glaucoma tracking…
        </p>
      ) : rows.length === 0 ? (
        <p className="specialty-tracking__empty" data-testid="glaucoma-empty">
          No glaucoma tracking yet.
        </p>
      ) : (
        <ul className="specialty-tracking__cards" data-testid="glaucoma-cards">
          {rows.map((row) => (
            <GlaucomaCard
              key={row.id}
              row={row}
              identity={identity}
              patientId={patientId}
              canWriteTracking={canWriteTracking}
              onUpdated={() => void refresh()}
            />
          ))}
        </ul>
      )}

      <SectionHead
        title="IOP Measurements"
        small
        action={
          canWriteMeasurement && (
            <button
              type="button"
              className="btn"
              data-testid="glaucoma-add-iop"
              onClick={() => setShowIop((v) => !v)}
            >
              {showIop ? "Cancel" : "+ Add IOP"}
            </button>
          )
        }
      />

      {showIop && (
        <IopForm
          identity={identity}
          patientId={patientId}
          encounterId={encounterId}
          onCreated={() => {
            setShowIop(false);
            void refresh();
          }}
        />
      )}

      {iops.length === 0 ? (
        <p
          className="specialty-tracking__empty"
          data-testid="glaucoma-iop-empty"
        >
          No IOP measurements recorded yet.
        </p>
      ) : (
        <table
          className="specialty-tracking__table"
          data-testid="glaucoma-iop-table"
        >
          <thead>
            <tr>
              <th>Eye</th>
              <th>IOP (mmHg)</th>
              <th>Measured at</th>
              <th>Method</th>
            </tr>
          </thead>
          <tbody>
            {iops.map((row) => (
              <tr key={row.id}>
                <td>{row.eye}</td>
                <td>{row.iop_value}</td>
                <td>{isoToShort(row.measured_at)}</td>
                <td>{row.method ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <SectionHead
        title="Visual Field Tests"
        small
        action={
          canWriteMeasurement && (
            <button
              type="button"
              className="btn"
              data-testid="glaucoma-add-vf"
              onClick={() => setShowVf((v) => !v)}
            >
              {showVf ? "Cancel" : "+ Add visual field"}
            </button>
          )
        }
      />

      {showVf && (
        <VisualFieldForm
          identity={identity}
          patientId={patientId}
          encounterId={encounterId}
          onCreated={() => {
            setShowVf(false);
            void refresh();
          }}
        />
      )}

      {vfs.length === 0 ? (
        <p
          className="specialty-tracking__empty"
          data-testid="glaucoma-vf-empty"
        >
          No visual field tests recorded yet.
        </p>
      ) : (
        <table
          className="specialty-tracking__table"
          data-testid="glaucoma-vf-table"
        >
          <thead>
            <tr>
              <th>Eye</th>
              <th>Test type</th>
              <th>Performed</th>
              <th>Reliability</th>
              <th>Progression flag</th>
              <th>Result summary</th>
            </tr>
          </thead>
          <tbody>
            {vfs.map((row) => (
              <tr key={row.id}>
                <td>{row.eye}</td>
                <td>{row.test_type ?? "—"}</td>
                <td>{isoToShort(row.performed_at)}</td>
                <td>{row.reliability ?? "—"}</td>
                <td>{row.progression_flag ?? "—"}</td>
                <td>{row.result_summary ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function GlaucomaCard({
  row,
  identity,
  patientId,
  canWriteTracking,
  onUpdated,
}: {
  row: GlaucomaTrackingRecord;
  identity: string;
  patientId: number;
  canWriteTracking: boolean;
  onUpdated: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const updateStatus = useCallback(
    async (next: SpecialtyReviewStatus) => {
      setBusy(true);
      setError(null);
      try {
        await updatePatientGlaucomaTracking(identity, patientId, row.id, {
          review_status: next,
        });
        onUpdated();
      } catch (e) {
        setError(friendly(e));
      } finally {
        setBusy(false);
      }
    },
    [identity, patientId, row.id, onUpdated]
  );

  return (
    <li
      className="specialty-tracking__card"
      data-testid={`glaucoma-card-${row.id}`}
      data-eye={row.eye}
    >
      <div className="specialty-tracking__card-head">
        <span className="specialty-tracking__pill">{row.eye}</span>
        <h4 className="specialty-tracking__card-title">
          {row.glaucoma_type ?? "Glaucoma"}
        </h4>
        <span
          className={`specialty-tracking__status specialty-tracking__status--${row.review_status}`}
        >
          {row.review_status}
        </span>
      </div>
      <dl className="specialty-tracking__dl">
        <Field
          label="Target IOP"
          value={row.target_iop != null ? `${row.target_iop} mmHg` : null}
        />
        <Field
          label="Latest IOP"
          value={row.latest_iop != null ? `${row.latest_iop} mmHg` : null}
        />
        <Field
          label="Cup-to-disc ratio"
          value={
            row.cup_to_disc_ratio != null
              ? row.cup_to_disc_ratio.toFixed(2)
              : null
          }
        />
        <Field label="RNFL status" value={row.rnfl_status} />
        <Field
          label="Visual field status"
          value={row.visual_field_status}
        />
        <Field
          label="Progression risk"
          value={row.progression_risk_label}
        />
        <Field label="Medication plan" value={row.medication_plan} wide />
        <Field
          label="Provider assessment"
          value={row.provider_assessment}
          wide
        />
      </dl>
      {error && (
        <div className="banner banner--error" role="alert">
          {error}
        </div>
      )}
      {canWriteTracking ? (
        <div className="specialty-tracking__card-actions">
          <select
            data-testid={`glaucoma-status-select-${row.id}`}
            value={row.review_status}
            disabled={busy}
            onChange={(e) =>
              void updateStatus(e.target.value as SpecialtyReviewStatus)
            }
          >
            {REVIEW_STATUSES.map((s) => (
              <option key={s} value={s}>
                {s.replace(/_/g, " ")}
              </option>
            ))}
          </select>
          {row.review_status !== "reviewed" && (
            <button
              type="button"
              className="btn"
              data-testid={`glaucoma-mark-reviewed-${row.id}`}
              onClick={() => void updateStatus("reviewed")}
              disabled={busy}
            >
              Mark reviewed
            </button>
          )}
        </div>
      ) : (
        <p
          className="subtle-note"
          data-testid={`glaucoma-readonly-${row.id}`}
        >
          Read-only — your role cannot update this record.
        </p>
      )}
    </li>
  );
}

function GlaucomaCreateForm({
  identity,
  patientId,
  encounterId,
  onCreated,
}: {
  identity: string;
  patientId: number;
  encounterId: number | null;
  onCreated: () => void;
}) {
  const [eye, setEye] = useState<SpecialtyEye>("OS");
  const [glaucomaType, setGlaucomaType] = useState("");
  const [targetIop, setTargetIop] = useState("");
  const [latestIop, setLatestIop] = useState("");
  const [ratio, setRatio] = useState("");
  const [rnfl, setRnfl] = useState("");
  const [vfStatus, setVfStatus] = useState("");
  const [risk, setRisk] = useState("");
  const [medPlan, setMedPlan] = useState("");
  const [assessment, setAssessment] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const input: GlaucomaTrackingCreateInput = {
        eye,
        glaucoma_type: glaucomaType.trim() || null,
        target_iop: targetIop.trim() ? Number(targetIop) : null,
        latest_iop: latestIop.trim() ? Number(latestIop) : null,
        cup_to_disc_ratio: ratio.trim() ? Number(ratio) : null,
        rnfl_status: rnfl.trim() || null,
        visual_field_status: vfStatus.trim() || null,
        medication_plan: medPlan.trim() || null,
        progression_risk_label: risk.trim() || null,
        provider_assessment: assessment.trim() || null,
        encounter_id: encounterId,
      };
      await createPatientGlaucomaTracking(identity, patientId, input);
      onCreated();
    } catch (e) {
      setError(friendly(e));
    } finally {
      setBusy(false);
    }
  }, [
    eye,
    glaucomaType,
    targetIop,
    latestIop,
    ratio,
    rnfl,
    vfStatus,
    medPlan,
    risk,
    assessment,
    encounterId,
    identity,
    patientId,
    onCreated,
  ]);

  return (
    <form
      className="specialty-tracking__form"
      data-testid="glaucoma-create-form"
      onSubmit={(e) => {
        e.preventDefault();
        void submit();
      }}
    >
      <FieldRow label="Eye">
        <EyeSelect
          value={eye}
          onChange={setEye}
          allowOu
          testid="glaucoma-create-eye"
        />
      </FieldRow>
      <FieldRow label="Glaucoma type">
        <input
          type="text"
          value={glaucomaType}
          onChange={(e) => setGlaucomaType(e.target.value)}
          maxLength={120}
          data-testid="glaucoma-create-type"
        />
      </FieldRow>
      <FieldRow label="Target IOP (mmHg)">
        <input
          type="number"
          min={0}
          max={80}
          step="0.1"
          value={targetIop}
          onChange={(e) => setTargetIop(e.target.value)}
          data-testid="glaucoma-create-target"
        />
      </FieldRow>
      <FieldRow label="Latest IOP (mmHg)">
        <input
          type="number"
          min={0}
          max={80}
          step="0.1"
          value={latestIop}
          onChange={(e) => setLatestIop(e.target.value)}
          data-testid="glaucoma-create-latest"
        />
      </FieldRow>
      <FieldRow label="Cup-to-disc ratio">
        <input
          type="number"
          min={0}
          max={1}
          step="0.05"
          value={ratio}
          onChange={(e) => setRatio(e.target.value)}
          data-testid="glaucoma-create-ratio"
        />
      </FieldRow>
      <FieldRow label="RNFL status">
        <input
          type="text"
          value={rnfl}
          onChange={(e) => setRnfl(e.target.value)}
          maxLength={120}
        />
      </FieldRow>
      <FieldRow label="Visual field status">
        <input
          type="text"
          value={vfStatus}
          onChange={(e) => setVfStatus(e.target.value)}
          maxLength={120}
        />
      </FieldRow>
      <FieldRow label="Progression risk label">
        <input
          type="text"
          value={risk}
          onChange={(e) => setRisk(e.target.value)}
          maxLength={64}
          placeholder="e.g. low / moderate / high"
        />
      </FieldRow>
      <FieldRow label="Medication plan">
        <textarea
          value={medPlan}
          onChange={(e) => setMedPlan(e.target.value)}
          rows={2}
          maxLength={4000}
        />
      </FieldRow>
      <FieldRow label="Provider assessment">
        <textarea
          value={assessment}
          onChange={(e) => setAssessment(e.target.value)}
          rows={3}
          maxLength={8000}
          data-testid="glaucoma-create-assessment"
        />
      </FieldRow>
      {error && (
        <div className="banner banner--error" role="alert">
          {error}
        </div>
      )}
      <button
        type="submit"
        className="btn btn--primary"
        disabled={busy}
        data-testid="glaucoma-create-submit"
      >
        {busy ? "Saving…" : "Save glaucoma tracking"}
      </button>
    </form>
  );
}

function IopForm({
  identity,
  patientId,
  encounterId,
  onCreated,
}: {
  identity: string;
  patientId: number;
  encounterId: number | null;
  onCreated: () => void;
}) {
  const [eye, setEye] = useState<SpecialtyEyeOdOs>("OD");
  const [value, setValue] = useState("");
  const [measuredAt, setMeasuredAt] = useState("");
  const [method, setMethod] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = useCallback(async () => {
    if (!value.trim()) {
      setError("IOP value is required.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const input: GlaucomaIopCreateInput = {
        eye,
        iop_value: Number(value),
        measured_at: measuredAt || null,
        method: method.trim() || null,
        encounter_id: encounterId,
      };
      await createPatientGlaucomaIopMeasurement(identity, patientId, input);
      onCreated();
    } catch (e) {
      setError(friendly(e));
    } finally {
      setBusy(false);
    }
  }, [eye, value, measuredAt, method, encounterId, identity, patientId, onCreated]);

  return (
    <form
      className="specialty-tracking__form specialty-tracking__form--inline"
      data-testid="iop-form"
      onSubmit={(e) => {
        e.preventDefault();
        void submit();
      }}
    >
      <FieldRow label="Eye">
        <EyeSelect value={eye} onChange={setEye} allowOu={false} testid="iop-eye" />
      </FieldRow>
      <FieldRow label="IOP (mmHg)">
        <input
          type="number"
          min={0}
          max={80}
          step="0.1"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          required
          data-testid="iop-value"
        />
      </FieldRow>
      <FieldRow label="Measured at">
        <input
          type="datetime-local"
          value={measuredAt}
          onChange={(e) => setMeasuredAt(e.target.value)}
        />
      </FieldRow>
      <FieldRow label="Method">
        <input
          type="text"
          value={method}
          onChange={(e) => setMethod(e.target.value)}
          maxLength={64}
          placeholder="e.g. Goldmann, iCare"
        />
      </FieldRow>
      {error && (
        <div className="banner banner--error" role="alert">
          {error}
        </div>
      )}
      <button
        type="submit"
        className="btn btn--primary"
        disabled={busy}
        data-testid="iop-submit"
      >
        {busy ? "Saving…" : "Save IOP"}
      </button>
    </form>
  );
}

function VisualFieldForm({
  identity,
  patientId,
  encounterId,
  onCreated,
}: {
  identity: string;
  patientId: number;
  encounterId: number | null;
  onCreated: () => void;
}) {
  const [eye, setEye] = useState<SpecialtyEye>("OD");
  const [testType, setTestType] = useState("");
  const [performedAt, setPerformedAt] = useState("");
  const [reliability, setReliability] = useState("");
  const [progression, setProgression] = useState("");
  const [summary, setSummary] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const input: GlaucomaVisualFieldCreateInput = {
        eye,
        test_type: testType.trim() || null,
        performed_at: performedAt || null,
        reliability: reliability.trim() || null,
        progression_flag: progression.trim() || null,
        result_summary: summary.trim() || null,
        encounter_id: encounterId,
      };
      await createPatientGlaucomaVisualField(identity, patientId, input);
      onCreated();
    } catch (e) {
      setError(friendly(e));
    } finally {
      setBusy(false);
    }
  }, [
    eye,
    testType,
    performedAt,
    reliability,
    progression,
    summary,
    encounterId,
    identity,
    patientId,
    onCreated,
  ]);

  return (
    <form
      className="specialty-tracking__form specialty-tracking__form--inline"
      data-testid="vf-form"
      onSubmit={(e) => {
        e.preventDefault();
        void submit();
      }}
    >
      <FieldRow label="Eye">
        <EyeSelect value={eye} onChange={setEye} allowOu testid="vf-eye" />
      </FieldRow>
      <FieldRow label="Test type">
        <input
          type="text"
          value={testType}
          onChange={(e) => setTestType(e.target.value)}
          maxLength={120}
          placeholder="e.g. 24-2"
        />
      </FieldRow>
      <FieldRow label="Performed">
        <input
          type="datetime-local"
          value={performedAt}
          onChange={(e) => setPerformedAt(e.target.value)}
        />
      </FieldRow>
      <FieldRow label="Reliability">
        <input
          type="text"
          value={reliability}
          onChange={(e) => setReliability(e.target.value)}
          maxLength={64}
        />
      </FieldRow>
      <FieldRow label="Progression flag">
        <input
          type="text"
          value={progression}
          onChange={(e) => setProgression(e.target.value)}
          maxLength={64}
        />
      </FieldRow>
      <FieldRow label="Result summary">
        <textarea
          value={summary}
          onChange={(e) => setSummary(e.target.value)}
          rows={2}
          maxLength={8000}
        />
      </FieldRow>
      {error && (
        <div className="banner banner--error" role="alert">
          {error}
        </div>
      )}
      <button
        type="submit"
        className="btn btn--primary"
        disabled={busy}
        data-testid="vf-submit"
      >
        {busy ? "Saving…" : "Save visual field"}
      </button>
    </form>
  );
}

// ----------------------------------------------------------------
// Shared primitives
// ----------------------------------------------------------------

function SectionHead({
  title,
  small,
  action,
}: {
  title: string;
  small?: boolean;
  action?: ReactNode;
}) {
  return (
    <div
      className={
        "specialty-tracking__sec-head" +
        (small ? " specialty-tracking__sec-head--small" : "")
      }
    >
      <h3 className="specialty-tracking__sec-title">{title}</h3>
      {action ?? null}
    </div>
  );
}

function Field({
  label,
  value,
  wide,
}: {
  label: string;
  value: string | null | undefined;
  wide?: boolean;
}) {
  return (
    <div
      className={
        "specialty-tracking__field" +
        (wide ? " specialty-tracking__field--wide" : "")
      }
    >
      <dt>{label}</dt>
      <dd>{value && value.trim() !== "" ? value : "—"}</dd>
    </div>
  );
}

function FieldRow({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <label className="specialty-tracking__field-row">
      <span>{label}</span>
      {children}
    </label>
  );
}

function EyeSelect<T extends string>({
  value,
  onChange,
  allowOu,
  testid,
}: {
  value: T;
  onChange: (next: T) => void;
  allowOu: boolean;
  testid?: string;
}) {
  const options = useMemo(
    () => (allowOu ? EYE_VALUES_OD_OS_OU : EYE_VALUES_OD_OS),
    [allowOu]
  );
  return (
    <select
      data-testid={testid}
      value={value}
      onChange={(e) => onChange(e.target.value as T)}
    >
      {options.map((o) => (
        <option key={o} value={o}>
          {o}
        </option>
      ))}
    </select>
  );
}
