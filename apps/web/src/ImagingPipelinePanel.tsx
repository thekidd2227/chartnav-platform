// Phase 21B — Ophthalmology imaging pipeline foundation panel.
//
// Renders inside the existing Imaging tab in ClinicalTabbedWorkspace.
// METADATA + REVIEW WORKFLOW ONLY. The panel does NOT upload binary
// files, does NOT claim integrations with any specific device or
// vendor, does NOT autonomously interpret images, does NOT diagnose,
// place orders, send referrals, message patients, or bill.
//
// Studies, file metadata, and structured measurements are all
// provider- or technician-entered. The OD/OS retinal workbench
// (EyeDiagramPanel) continues to own annotated review and lives in
// the same Imaging tab below this panel.

import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  ApiError,
  ImagingEye,
  ImagingFileCreateInput,
  ImagingFileKind,
  ImagingFileMetadata,
  ImagingMeasurement,
  ImagingMeasurementCreateInput,
  ImagingMeasurementSource,
  ImagingModality,
  ImagingStudy,
  ImagingStudyCreateInput,
  ImagingStudyStatus,
  Me,
  createImagingStudyFile,
  createImagingStudyMeasurement,
  createPatientImagingStudy,
  listImagingStudyFiles,
  listImagingStudyMeasurements,
  listPatientImagingStudies,
  markImagingStudyReviewed,
  updateImagingStudy,
} from "./api";

const READ_ROLES = new Set(["admin", "clinician", "reviewer", "technician"]);
const CREATE_ROLES = new Set(["admin", "clinician", "technician"]);
const REVIEW_ROLES = new Set(["admin", "clinician"]);

const MODALITY_OPTIONS: { value: ImagingModality; label: string }[] = [
  { value: "oct_macula", label: "OCT macula" },
  { value: "oct_rnfl", label: "OCT RNFL" },
  { value: "fundus_photo", label: "Fundus photo" },
  { value: "widefield_fundus", label: "Widefield fundus" },
  { value: "visual_field_24_2", label: "Visual field 24-2" },
  { value: "visual_field_10_2", label: "Visual field 10-2" },
  { value: "biometry_packet", label: "Biometry packet" },
  { value: "external_pdf", label: "External PDF report" },
  { value: "other", label: "Other" },
];

const STATUS_OPTIONS: ImagingStudyStatus[] = [
  "pending_upload",
  "uploaded",
  "ready_for_review",
  "reviewed",
  "archived",
];

const EYE_OPTIONS: ImagingEye[] = ["OD", "OS", "OU", "NA"];

const FILE_KIND_OPTIONS: { value: ImagingFileKind; label: string }[] = [
  { value: "image", label: "Image" },
  { value: "report_pdf", label: "Report PDF" },
  { value: "raw_export", label: "Raw export" },
];

const SOURCE_OPTIONS: ImagingMeasurementSource[] = [
  "manual",
  "demo",
  "imported_metadata",
];

interface Props {
  identity: string;
  me: Me;
  patientId: number | null;
  encounterId: number | null;
}

function friendly(err: unknown): string {
  if (err instanceof ApiError) return `${err.errorCode}: ${err.reason}`;
  return err instanceof Error ? err.message : String(err);
}

function modalityLabel(m: string): string {
  return MODALITY_OPTIONS.find((o) => o.value === m)?.label ?? m;
}

function isoToShort(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString();
}

function bytesToHuman(n: number | null | undefined): string {
  if (n == null) return "—";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  if (n < 1024 * 1024 * 1024)
    return `${(n / 1024 / 1024).toFixed(1)} MB`;
  return `${(n / 1024 / 1024 / 1024).toFixed(2)} GB`;
}

export function ImagingPipelinePanel({
  identity,
  me,
  patientId,
  encounterId,
}: Props) {
  const canRead = READ_ROLES.has(me.role);
  const canCreate = CREATE_ROLES.has(me.role);
  const canReview = REVIEW_ROLES.has(me.role);

  if (!canRead) {
    return (
      <section
        className="imaging-pipeline imaging-pipeline--blocked"
        data-testid="imaging-pipeline-blocked"
        aria-label="Imaging pipeline"
      >
        <h2 className="imaging-pipeline__title">Imaging Pipeline</h2>
        <p className="imaging-pipeline__empty">
          Your role does not have access to clinical imaging. Switch
          to a clinical identity to view this panel.
        </p>
      </section>
    );
  }

  if (patientId === null) {
    return (
      <section
        className="imaging-pipeline imaging-pipeline--unavailable"
        data-testid="imaging-pipeline-unavailable"
        aria-label="Imaging pipeline"
      >
        <h2 className="imaging-pipeline__title">Imaging Pipeline</h2>
        <p className="imaging-pipeline__empty">
          Imaging records become available once the encounter is
          bridged into ChartNav with a native patient row.
        </p>
      </section>
    );
  }

  return (
    <ImagingPipelineForPatient
      identity={identity}
      patientId={patientId}
      encounterId={encounterId}
      canCreate={canCreate}
      canReview={canReview}
    />
  );
}

// ----------------------------------------------------------------
// Studies + selected-study detail
// ----------------------------------------------------------------

function ImagingPipelineForPatient({
  identity,
  patientId,
  encounterId,
  canCreate,
  canReview,
}: {
  identity: string;
  patientId: number;
  encounterId: number | null;
  canCreate: boolean;
  canReview: boolean;
}) {
  const [studies, setStudies] = useState<ImagingStudy[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);

  const refreshStudies = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await listPatientImagingStudies(identity, patientId);
      setStudies(res.items);
      if (selectedId === null && res.items.length > 0) {
        setSelectedId(res.items[0].id);
      }
    } catch (e) {
      setError(friendly(e));
    } finally {
      setLoading(false);
    }
  }, [identity, patientId, selectedId]);

  useEffect(() => {
    void refreshStudies();
  }, [identity, patientId]); // eslint-disable-line react-hooks/exhaustive-deps

  const selected = useMemo(
    () => studies.find((s) => s.id === selectedId) ?? null,
    [studies, selectedId]
  );

  return (
    <section
      className="imaging-pipeline"
      data-testid="imaging-pipeline"
      aria-label="Imaging pipeline"
    >
      <header className="imaging-pipeline__header">
        <div>
          <h2 className="imaging-pipeline__title">
            Imaging Pipeline — Metadata &amp; Review Workflow
          </h2>
          <p className="imaging-pipeline__subtitle subtle-note">
            Structured records of device-derived studies the practice
            captures upstream. ChartNav stores metadata only — no image
            binaries, no device integrations, no autonomous
            interpretation, and no automatic orders, referrals, or
            patient messaging.
          </p>
        </div>
        {canCreate && (
          <button
            type="button"
            className="btn btn--primary"
            data-testid="imaging-add-study"
            onClick={() => setShowCreate((v) => !v)}
          >
            {showCreate ? "Cancel" : "+ Add imaging study"}
          </button>
        )}
      </header>

      {error && (
        <div
          className="banner banner--error"
          role="alert"
          data-testid="imaging-error"
        >
          {error}
        </div>
      )}

      {showCreate && (
        <StudyCreateForm
          identity={identity}
          patientId={patientId}
          encounterId={encounterId}
          onCreated={() => {
            setShowCreate(false);
            void refreshStudies();
          }}
        />
      )}

      <div className="imaging-pipeline__split">
        <div
          className="imaging-pipeline__list"
          data-testid="imaging-study-list-col"
        >
          <h3 className="imaging-pipeline__section">Imaging studies</h3>
          {loading && studies.length === 0 ? (
            <p className="imaging-pipeline__empty" data-testid="imaging-loading">
              Loading imaging studies…
            </p>
          ) : studies.length === 0 ? (
            <p
              className="imaging-pipeline__empty"
              data-testid="imaging-studies-empty"
            >
              No imaging studies yet.
            </p>
          ) : (
            <ul
              className="imaging-pipeline__study-list"
              data-testid="imaging-studies"
            >
              {studies.map((s) => (
                <li key={s.id}>
                  <button
                    type="button"
                    className={
                      "imaging-pipeline__study-row" +
                      (s.id === selectedId
                        ? " imaging-pipeline__study-row--active"
                        : "")
                    }
                    data-testid={`imaging-study-row-${s.id}`}
                    onClick={() => setSelectedId(s.id)}
                  >
                    <span className="imaging-pipeline__study-modality">
                      {modalityLabel(s.modality)}
                    </span>
                    <span className="imaging-pipeline__pill">{s.eye}</span>
                    <span
                      className={`imaging-pipeline__status imaging-pipeline__status--${s.status}`}
                    >
                      {s.status.replace(/_/g, " ")}
                    </span>
                    <span className="imaging-pipeline__study-date subtle-note">
                      {isoToShort(s.captured_at)}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div
          className="imaging-pipeline__detail"
          data-testid="imaging-study-detail"
        >
          {selected ? (
            <StudyDetail
              study={selected}
              identity={identity}
              canCreate={canCreate}
              canReview={canReview}
              onChanged={() => void refreshStudies()}
            />
          ) : (
            <p
              className="imaging-pipeline__empty"
              data-testid="imaging-detail-empty"
            >
              Select a study from the list to see its files,
              measurements, and review workbench.
            </p>
          )}
        </div>
      </div>
    </section>
  );
}

// ----------------------------------------------------------------
// Study detail (files + measurements + review)
// ----------------------------------------------------------------

function StudyDetail({
  study,
  identity,
  canCreate,
  canReview,
  onChanged,
}: {
  study: ImagingStudy;
  identity: string;
  canCreate: boolean;
  canReview: boolean;
  onChanged: () => void;
}) {
  const [files, setFiles] = useState<ImagingFileMetadata[]>([]);
  const [measurements, setMeasurements] = useState<ImagingMeasurement[]>([]);
  const [loading, setLoading] = useState(false);
  const [showFile, setShowFile] = useState(false);
  const [showMeasurement, setShowMeasurement] = useState(false);
  const [reviewError, setReviewError] = useState<string | null>(null);
  const [reviewBusy, setReviewBusy] = useState(false);
  const [reviewNotes, setReviewNotes] = useState(study.notes ?? "");

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [f, m] = await Promise.all([
        listImagingStudyFiles(identity, study.id),
        listImagingStudyMeasurements(identity, study.id),
      ]);
      setFiles(f.items);
      setMeasurements(m.items);
    } finally {
      setLoading(false);
    }
  }, [identity, study.id]);

  useEffect(() => {
    void refresh();
    setReviewNotes(study.notes ?? "");
  }, [refresh, study.notes]);

  const markReviewed = useCallback(async () => {
    setReviewBusy(true);
    setReviewError(null);
    try {
      await markImagingStudyReviewed(identity, study.id, {
        notes: reviewNotes || null,
      });
      onChanged();
    } catch (e) {
      setReviewError(friendly(e));
    } finally {
      setReviewBusy(false);
    }
  }, [identity, study.id, reviewNotes, onChanged]);

  return (
    <div className="imaging-pipeline__study">
      <header className="imaging-pipeline__study-head">
        <h3 className="imaging-pipeline__study-title">
          {modalityLabel(study.modality)} · {study.eye}
        </h3>
        <span
          className={`imaging-pipeline__status imaging-pipeline__status--${study.status}`}
          data-testid={`imaging-study-status-${study.id}`}
        >
          {study.status.replace(/_/g, " ")}
        </span>
        {study.status === "reviewed" && (
          <span
            className="imaging-pipeline__reviewed-badge"
            data-testid={`imaging-reviewed-${study.id}`}
          >
            ✓ Reviewed {isoToShort(study.reviewed_at)}
          </span>
        )}
      </header>

      <dl className="imaging-pipeline__dl">
        <Field label="Captured at" value={isoToShort(study.captured_at)} />
        <Field
          label="Reviewer"
          value={
            study.reviewed_by_user_id != null
              ? `user #${study.reviewed_by_user_id}`
              : null
          }
        />
        <Field label="Reviewed at" value={isoToShort(study.reviewed_at)} />
        <Field label="Notes" value={study.notes} wide />
      </dl>

      <h4 className="imaging-pipeline__sec">
        File metadata
        {canCreate && (
          <button
            type="button"
            className="btn"
            data-testid="imaging-add-file"
            onClick={() => setShowFile((v) => !v)}
          >
            {showFile ? "Cancel" : "+ Add file metadata"}
          </button>
        )}
      </h4>
      {showFile && (
        <FileCreateForm
          identity={identity}
          studyId={study.id}
          onCreated={() => {
            setShowFile(false);
            void refresh();
          }}
        />
      )}
      {loading && files.length === 0 ? (
        <p className="imaging-pipeline__empty">Loading files…</p>
      ) : files.length === 0 ? (
        <p
          className="imaging-pipeline__empty"
          data-testid="imaging-files-empty"
        >
          No files recorded for this study.
        </p>
      ) : (
        <table
          className="imaging-pipeline__table"
          data-testid="imaging-files-table"
        >
          <thead>
            <tr>
              <th>Kind</th>
              <th>File name</th>
              <th>Content type</th>
              <th>Size</th>
              <th>Storage</th>
            </tr>
          </thead>
          <tbody>
            {files.map((f) => (
              <tr key={f.id}>
                <td>{f.file_kind.replace(/_/g, " ")}</td>
                <td>{f.file_name}</td>
                <td>{f.content_type ?? "—"}</td>
                <td>{bytesToHuman(f.size_bytes)}</td>
                <td>{f.storage_uri ? "linked" : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <h4 className="imaging-pipeline__sec">
        Measurements
        {canCreate && (
          <button
            type="button"
            className="btn"
            data-testid="imaging-add-measurement"
            onClick={() => setShowMeasurement((v) => !v)}
          >
            {showMeasurement ? "Cancel" : "+ Add measurement"}
          </button>
        )}
      </h4>
      {showMeasurement && (
        <MeasurementCreateForm
          identity={identity}
          studyId={study.id}
          onCreated={() => {
            setShowMeasurement(false);
            void refresh();
          }}
        />
      )}
      {measurements.length === 0 ? (
        <p
          className="imaging-pipeline__empty"
          data-testid="imaging-measurements-empty"
        >
          No measurements recorded for this study.
        </p>
      ) : (
        <table
          className="imaging-pipeline__table"
          data-testid="imaging-measurements-table"
        >
          <thead>
            <tr>
              <th>Type</th>
              <th>Eye</th>
              <th>Value</th>
              <th>Unit</th>
              <th>Source</th>
            </tr>
          </thead>
          <tbody>
            {measurements.map((m) => (
              <tr key={m.id}>
                <td>{m.measurement_type.replace(/_/g, " ")}</td>
                <td>{m.eye}</td>
                <td>{m.value}</td>
                <td>{m.unit ?? "—"}</td>
                <td>{m.source.replace(/_/g, " ")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <h4 className="imaging-pipeline__sec">Review workbench</h4>
      <div
        className="imaging-pipeline__review"
        data-testid="imaging-review-workbench"
      >
        <label className="imaging-pipeline__field-row">
          <span>Review notes</span>
          <textarea
            value={reviewNotes}
            onChange={(e) => setReviewNotes(e.target.value)}
            rows={3}
            maxLength={8000}
            data-testid="imaging-review-notes"
            disabled={!canReview}
          />
        </label>
        {reviewError && (
          <div className="banner banner--error" role="alert">
            {reviewError}
          </div>
        )}
        {canReview ? (
          <button
            type="button"
            className="btn btn--primary"
            data-testid="imaging-mark-reviewed"
            onClick={() => void markReviewed()}
            disabled={reviewBusy || study.status === "reviewed"}
          >
            {study.status === "reviewed"
              ? "Already reviewed"
              : reviewBusy
              ? "Marking reviewed…"
              : "Mark reviewed"}
          </button>
        ) : (
          <p className="subtle-note" data-testid="imaging-review-readonly">
            Read-only — only admin or clinician roles can mark a study
            reviewed.
          </p>
        )}
      </div>

      <p
        className="imaging-pipeline__open-canvas-hint subtle-note"
        data-testid="imaging-open-canvas-hint"
      >
        Open the OD/OS retinal diagram workbench below to annotate
        findings on a study and sign them into the encounter note.
      </p>
    </div>
  );
}

// ----------------------------------------------------------------
// Forms
// ----------------------------------------------------------------

function StudyCreateForm({
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
  const [modality, setModality] = useState<ImagingModality>("oct_macula");
  const [eye, setEye] = useState<ImagingEye>("OD");
  const [studyStatus, setStudyStatus] =
    useState<ImagingStudyStatus>("uploaded");
  const [capturedAt, setCapturedAt] = useState("");
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const input: ImagingStudyCreateInput = {
        modality,
        eye,
        status: studyStatus,
        captured_at: capturedAt || null,
        notes: notes.trim() || null,
        encounter_id: encounterId,
      };
      await createPatientImagingStudy(identity, patientId, input);
      onCreated();
    } catch (e) {
      setError(friendly(e));
    } finally {
      setBusy(false);
    }
  }, [
    modality,
    eye,
    studyStatus,
    capturedAt,
    notes,
    encounterId,
    identity,
    patientId,
    onCreated,
  ]);

  return (
    <form
      className="imaging-pipeline__form"
      data-testid="imaging-study-create-form"
      onSubmit={(e) => {
        e.preventDefault();
        void submit();
      }}
    >
      <FieldRow label="Modality">
        <select
          value={modality}
          onChange={(e) => setModality(e.target.value as ImagingModality)}
          data-testid="imaging-create-modality"
        >
          {MODALITY_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </FieldRow>
      <FieldRow label="Eye">
        <select
          value={eye}
          onChange={(e) => setEye(e.target.value as ImagingEye)}
          data-testid="imaging-create-eye"
        >
          {EYE_OPTIONS.map((o) => (
            <option key={o} value={o}>
              {o}
            </option>
          ))}
        </select>
      </FieldRow>
      <FieldRow label="Status">
        <select
          value={studyStatus}
          onChange={(e) =>
            setStudyStatus(e.target.value as ImagingStudyStatus)
          }
          data-testid="imaging-create-status"
        >
          {STATUS_OPTIONS.map((o) => (
            <option key={o} value={o}>
              {o.replace(/_/g, " ")}
            </option>
          ))}
        </select>
      </FieldRow>
      <FieldRow label="Captured at">
        <input
          type="datetime-local"
          value={capturedAt}
          onChange={(e) => setCapturedAt(e.target.value)}
          data-testid="imaging-create-captured"
        />
      </FieldRow>
      <FieldRow label="Notes">
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          rows={2}
          maxLength={8000}
          data-testid="imaging-create-notes"
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
        data-testid="imaging-create-submit"
      >
        {busy ? "Saving…" : "Save imaging study"}
      </button>
    </form>
  );
}

function FileCreateForm({
  identity,
  studyId,
  onCreated,
}: {
  identity: string;
  studyId: number;
  onCreated: () => void;
}) {
  const [fileKind, setFileKind] = useState<ImagingFileKind>("image");
  const [fileName, setFileName] = useState("");
  const [storageUri, setStorageUri] = useState("");
  const [contentType, setContentType] = useState("");
  const [sizeBytes, setSizeBytes] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = useCallback(async () => {
    if (!fileName.trim()) {
      setError("File name is required.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const input: ImagingFileCreateInput = {
        file_kind: fileKind,
        file_name: fileName.trim(),
        storage_uri: storageUri.trim() || null,
        content_type: contentType.trim() || null,
        size_bytes: sizeBytes.trim() ? Number(sizeBytes) : null,
      };
      await createImagingStudyFile(identity, studyId, input);
      onCreated();
    } catch (e) {
      setError(friendly(e));
    } finally {
      setBusy(false);
    }
  }, [
    fileKind,
    fileName,
    storageUri,
    contentType,
    sizeBytes,
    identity,
    studyId,
    onCreated,
  ]);

  return (
    <form
      className="imaging-pipeline__form imaging-pipeline__form--inline"
      data-testid="imaging-file-form"
      onSubmit={(e) => {
        e.preventDefault();
        void submit();
      }}
    >
      <FieldRow label="Kind">
        <select
          value={fileKind}
          onChange={(e) => setFileKind(e.target.value as ImagingFileKind)}
          data-testid="imaging-file-kind"
        >
          {FILE_KIND_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </FieldRow>
      <FieldRow label="File name">
        <input
          type="text"
          value={fileName}
          onChange={(e) => setFileName(e.target.value)}
          maxLength={500}
          required
          data-testid="imaging-file-name"
        />
      </FieldRow>
      <FieldRow label="Storage URI">
        <input
          type="text"
          value={storageUri}
          onChange={(e) => setStorageUri(e.target.value)}
          maxLength={1024}
          placeholder="s3://practice-bucket/..."
          data-testid="imaging-file-storage"
        />
      </FieldRow>
      <FieldRow label="Content type">
        <input
          type="text"
          value={contentType}
          onChange={(e) => setContentType(e.target.value)}
          maxLength={200}
          placeholder="application/dicom"
        />
      </FieldRow>
      <FieldRow label="Size (bytes)">
        <input
          type="number"
          min={0}
          value={sizeBytes}
          onChange={(e) => setSizeBytes(e.target.value)}
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
        data-testid="imaging-file-submit"
      >
        {busy ? "Saving…" : "Save file metadata"}
      </button>
    </form>
  );
}

function MeasurementCreateForm({
  identity,
  studyId,
  onCreated,
}: {
  identity: string;
  studyId: number;
  onCreated: () => void;
}) {
  const [type, setType] = useState("central_macular_thickness");
  const [eye, setEye] = useState<ImagingEye>("OD");
  const [value, setValue] = useState("");
  const [unit, setUnit] = useState("microns");
  const [source, setSource] = useState<ImagingMeasurementSource>("manual");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = useCallback(async () => {
    if (!type.trim() || !value.trim()) {
      setError("Measurement type and value are required.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const input: ImagingMeasurementCreateInput = {
        measurement_type: type.trim(),
        eye,
        value: value.trim(),
        unit: unit.trim() || null,
        source,
      };
      await createImagingStudyMeasurement(identity, studyId, input);
      onCreated();
    } catch (e) {
      setError(friendly(e));
    } finally {
      setBusy(false);
    }
  }, [type, eye, value, unit, source, identity, studyId, onCreated]);

  return (
    <form
      className="imaging-pipeline__form imaging-pipeline__form--inline"
      data-testid="imaging-measurement-form"
      onSubmit={(e) => {
        e.preventDefault();
        void submit();
      }}
    >
      <FieldRow label="Measurement type">
        <input
          type="text"
          value={type}
          onChange={(e) => setType(e.target.value)}
          maxLength={120}
          required
          data-testid="imaging-measurement-type"
        />
      </FieldRow>
      <FieldRow label="Eye">
        <select
          value={eye}
          onChange={(e) => setEye(e.target.value as ImagingEye)}
          data-testid="imaging-measurement-eye"
        >
          {EYE_OPTIONS.map((o) => (
            <option key={o} value={o}>
              {o}
            </option>
          ))}
        </select>
      </FieldRow>
      <FieldRow label="Value">
        <input
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          maxLength={64}
          required
          data-testid="imaging-measurement-value"
        />
      </FieldRow>
      <FieldRow label="Unit">
        <input
          type="text"
          value={unit}
          onChange={(e) => setUnit(e.target.value)}
          maxLength={32}
        />
      </FieldRow>
      <FieldRow label="Source">
        <select
          value={source}
          onChange={(e) =>
            setSource(e.target.value as ImagingMeasurementSource)
          }
          data-testid="imaging-measurement-source"
        >
          {SOURCE_OPTIONS.map((o) => (
            <option key={o} value={o}>
              {o.replace(/_/g, " ")}
            </option>
          ))}
        </select>
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
        data-testid="imaging-measurement-submit"
      >
        {busy ? "Saving…" : "Save measurement"}
      </button>
    </form>
  );
}

// ----------------------------------------------------------------
// Shared primitives
// ----------------------------------------------------------------

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
        "imaging-pipeline__field" +
        (wide ? " imaging-pipeline__field--wide" : "")
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
    <label className="imaging-pipeline__field-row">
      <span>{label}</span>
      {children}
    </label>
  );
}
