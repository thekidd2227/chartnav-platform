// EyeDiagramPanel — provider-facing retinal diagram workspace.
//
// Phase 5B: replaced the persistence-shell JSON textarea with a real
// SVG OD/OS drawing canvas (RetinalDrawingCanvas). The save/load/sign/
// fork wiring against the existing `/patients/{id}/eye-diagrams` API
// is unchanged — only the editing surface and the findings auto-summary
// behavior are new.

import { useCallback, useEffect, useMemo, useState } from "react";

import {
  ApiError,
  EyeDiagramArtifact,
  createPatientEyeDiagram,
  getPatientEyeDiagram,
  listPatientEyeDiagrams,
  signPatientEyeDiagram,
  updatePatientEyeDiagram,
} from "./api";
import {
  DrawingDocument,
  EMPTY_DRAWING,
  applyAutoSummary,
  migrateUnknownDrawing,
} from "./retinalAnnotations";
import { RetinalDrawingCanvas } from "./RetinalDrawingCanvas";

interface Props {
  identity: string;
  patientId: number;
  encounterId: number | null;
}

type Banner =
  | { kind: "ok"; msg: string }
  | { kind: "error"; msg: string }
  | { kind: "info"; msg: string }
  | null;

function friendly(err: unknown): string {
  if (err instanceof ApiError) return `${err.errorCode}: ${err.reason}`;
  return err instanceof Error ? err.message : String(err);
}

export function EyeDiagramPanel({ identity, patientId, encounterId }: Props) {
  const [items, setItems] = useState<EyeDiagramArtifact[]>([]);
  const [active, setActive] = useState<EyeDiagramArtifact | null>(null);
  const [title, setTitle] = useState<string>("");
  const [findings, setFindings] = useState<string>("");
  const [drawing, setDrawing] = useState<DrawingDocument>(EMPTY_DRAWING);
  const [legacyPayloadWarning, setLegacyPayloadWarning] = useState<boolean>(false);
  const [banner, setBanner] = useState<Banner>(null);
  const [busy, setBusy] = useState(false);

  // --- list + load helpers -------------------------------------------

  const refresh = useCallback(async () => {
    try {
      const res = await listPatientEyeDiagrams(identity, patientId);
      setItems(res.items);
    } catch (err) {
      setBanner({ kind: "error", msg: `Could not load diagrams: ${friendly(err)}` });
    }
  }, [identity, patientId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const resetDraft = useCallback(() => {
    setActive(null);
    setTitle("");
    setFindings("");
    setDrawing(EMPTY_DRAWING);
    setLegacyPayloadWarning(false);
    setBanner(null);
  }, []);

  const loadArtifact = useCallback(
    async (id: number) => {
      try {
        setBusy(true);
        const a = await getPatientEyeDiagram(identity, patientId, id);
        const { doc, recognized } = migrateUnknownDrawing(a.drawing_json);
        setActive(a);
        setTitle(a.title);
        setFindings(a.findings_text);
        setDrawing(doc);
        setLegacyPayloadWarning(!recognized);
        setBanner(null);
      } catch (err) {
        setBanner({ kind: "error", msg: `Load failed: ${friendly(err)}` });
      } finally {
        setBusy(false);
      }
    },
    [identity, patientId]
  );

  const isEditingSigned = active?.is_signed === true;

  const versionHint = useMemo(() => {
    if (!active) return null;
    const parts: string[] = [`v${active.version_number}`];
    if (active.parent_artifact_id != null) {
      parts.push(`forked from #${active.parent_artifact_id}`);
    }
    parts.push(active.is_signed ? "signed" : "unsigned");
    return parts.join(" · ");
  }, [active]);

  // --- save / update / fork / sign -----------------------------------

  const onCanvasChange = useCallback(
    (next: DrawingDocument) => {
      setDrawing(next);
      // Auto-refresh the fenced summary in findings_text whenever the
      // drawing changes. Provider edits outside the fence are preserved.
      setFindings((prev) => applyAutoSummary(prev, next));
    },
    []
  );

  const onSaveNew = useCallback(async () => {
    try {
      setBusy(true);
      const created = await createPatientEyeDiagram(identity, patientId, {
        title,
        findings_text: findings,
        drawing_json: drawing as unknown as Record<string, unknown>,
        encounter_id: encounterId ?? undefined,
      });
      setActive(created);
      setLegacyPayloadWarning(false);
      setBanner({ kind: "ok", msg: `Created v${created.version_number} (#${created.id}).` });
      await refresh();
    } catch (err) {
      setBanner({ kind: "error", msg: `Save failed: ${friendly(err)}` });
    } finally {
      setBusy(false);
    }
  }, [drawing, encounterId, findings, identity, patientId, refresh, title]);

  const onUpdate = useCallback(async () => {
    if (!active) return;
    try {
      setBusy(true);
      const updated = await updatePatientEyeDiagram(
        identity,
        patientId,
        active.id,
        {
          title,
          findings_text: findings,
          drawing_json: drawing as unknown as Record<string, unknown>,
        }
      );
      setActive(updated);
      setLegacyPayloadWarning(false);
      setBanner({ kind: "ok", msg: `Saved (v${updated.version_number}).` });
      await refresh();
    } catch (err) {
      setBanner({ kind: "error", msg: `Update failed: ${friendly(err)}` });
    } finally {
      setBusy(false);
    }
  }, [active, drawing, findings, identity, patientId, refresh, title]);

  const onForkFromSigned = useCallback(async () => {
    if (!active) return;
    try {
      setBusy(true);
      const forked = await updatePatientEyeDiagram(
        identity,
        patientId,
        active.id,
        {
          title,
          findings_text: findings,
          drawing_json: drawing as unknown as Record<string, unknown>,
        },
        { fork: true }
      );
      setActive(forked);
      setLegacyPayloadWarning(false);
      setBanner({
        kind: "ok",
        msg: `New version ${forked.version_number} created (#${forked.id}, parent #${forked.parent_artifact_id}).`,
      });
      await refresh();
    } catch (err) {
      setBanner({ kind: "error", msg: `Fork failed: ${friendly(err)}` });
    } finally {
      setBusy(false);
    }
  }, [active, drawing, findings, identity, patientId, refresh, title]);

  const onSign = useCallback(async () => {
    if (!active) return;
    try {
      setBusy(true);
      const signed = await signPatientEyeDiagram(identity, patientId, active.id);
      setActive(signed);
      setBanner({ kind: "ok", msg: "Signed." });
      await refresh();
    } catch (err) {
      setBanner({ kind: "error", msg: `Sign failed: ${friendly(err)}` });
    } finally {
      setBusy(false);
    }
  }, [active, identity, patientId, refresh]);

  // --- render ---------------------------------------------------------

  return (
    <div className="eye-diagram-panel" data-testid="eye-diagram-panel">
      <header className="eye-diagram-panel__header">
        <h3>Retinal diagram artifacts</h3>
        <p className="eye-diagram-panel__hint">
          OD/OS drawing workspace. Symbols, freehand, and text labels save
          as structured annotations. AI proposals are not part of this PR.
        </p>
      </header>

      {banner && (
        <div
          role="status"
          data-testid="eye-diagram-banner"
          className={`flash flash--${banner.kind}`}
        >
          {banner.msg}
        </div>
      )}

      <section className="eye-diagram-panel__list">
        <div className="eye-diagram-panel__list-header">
          <strong>Saved diagrams</strong>
          <button type="button" onClick={resetDraft} disabled={busy}>
            New
          </button>
        </div>
        {items.length === 0 ? (
          <p className="muted" data-testid="eye-diagram-empty">No diagrams saved yet.</p>
        ) : (
          <ul data-testid="eye-diagram-list">
            {items.map((a) => (
              <li key={a.id}>
                <button
                  type="button"
                  data-testid={`eye-diagram-load-${a.id}`}
                  onClick={() => loadArtifact(a.id)}
                  disabled={busy}
                >
                  #{a.id} · v{a.version_number} · {a.title || "(untitled)"}{" "}
                  {a.is_signed ? "🔒" : ""}
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="eye-diagram-panel__editor">
        <div className="eye-diagram-panel__meta">
          {active ? (
            <>
              <strong>#{active.id}</strong> · {versionHint}
              <span className="muted">
                {" · "}created {active.created_at}
                {active.updated_at !== active.created_at && (
                  <> · updated {active.updated_at}</>
                )}
              </span>
            </>
          ) : (
            <span className="muted">New artifact (unsaved)</span>
          )}
        </div>

        {isEditingSigned && (
          <div
            data-testid="eye-diagram-signed-warning"
            className="flash flash--info"
          >
            This artifact is signed and immutable. Use “Save as new
            version” to amend; the new version will fork from this one.
          </div>
        )}

        {legacyPayloadWarning && (
          <div
            data-testid="eye-diagram-legacy-warning"
            className="flash flash--info"
          >
            This artifact was saved before the drawing canvas existed.
            Its drawing payload is preserved on the server but not
            displayed; saving will replace it with the new canvas
            content.
          </div>
        )}

        <label>
          <span>Title</span>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            disabled={busy}
            data-testid="eye-diagram-title"
          />
        </label>

        <RetinalDrawingCanvas
          value={drawing}
          onChange={onCanvasChange}
          readOnly={isEditingSigned}
        />

        <label>
          <span>Findings</span>
          <textarea
            rows={6}
            value={findings}
            onChange={(e) => setFindings(e.target.value)}
            disabled={busy}
            data-testid="eye-diagram-findings"
          />
        </label>

        <div className="eye-diagram-panel__actions">
          {!active && (
            <button
              type="button"
              onClick={onSaveNew}
              disabled={busy}
              data-testid="eye-diagram-save-new"
            >
              Save new
            </button>
          )}
          {active && !active.is_signed && (
            <>
              <button
                type="button"
                onClick={onUpdate}
                disabled={busy}
                data-testid="eye-diagram-update"
              >
                Save changes
              </button>
              <button
                type="button"
                onClick={onSign}
                disabled={busy}
                data-testid="eye-diagram-sign"
              >
                Sign
              </button>
            </>
          )}
          {active && active.is_signed && (
            <button
              type="button"
              onClick={onForkFromSigned}
              disabled={busy}
              data-testid="eye-diagram-fork"
            >
              Save as new version
            </button>
          )}
        </div>
      </section>
    </div>
  );
}
