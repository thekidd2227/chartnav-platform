// EyeDiagramPanel — minimal JSON-shell UI for retinal diagram artifacts.
//
// This is the persistence shell, not a drawing canvas. The drawing
// payload is edited as raw JSON in a textarea so providers (and tests)
// can save/load arbitrary structured drawings while the canvas widget
// is built in a follow-up. AI proposal apply/reject is intentionally
// out of scope for this PR.

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

const EMPTY_DRAWING_JSON = "{}";

function prettyJson(value: unknown): string {
  try {
    return JSON.stringify(value ?? {}, null, 2);
  } catch {
    return EMPTY_DRAWING_JSON;
  }
}

function parseDrawingJson(input: string): { ok: true; value: Record<string, unknown> } | { ok: false; reason: string } {
  const trimmed = input.trim();
  if (!trimmed) return { ok: true, value: {} };
  try {
    const parsed = JSON.parse(trimmed);
    if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) {
      return { ok: false, reason: "drawing_json must be a JSON object." };
    }
    return { ok: true, value: parsed as Record<string, unknown> };
  } catch (err) {
    return { ok: false, reason: `drawing_json is not valid JSON (${(err as Error).message}).` };
  }
}

function friendly(err: unknown): string {
  if (err instanceof ApiError) return `${err.errorCode}: ${err.reason}`;
  return err instanceof Error ? err.message : String(err);
}

export function EyeDiagramPanel({ identity, patientId, encounterId }: Props) {
  const [items, setItems] = useState<EyeDiagramArtifact[]>([]);
  const [active, setActive] = useState<EyeDiagramArtifact | null>(null);
  const [title, setTitle] = useState<string>("");
  const [findings, setFindings] = useState<string>("");
  const [drawingText, setDrawingText] = useState<string>(EMPTY_DRAWING_JSON);
  const [banner, setBanner] = useState<Banner>(null);
  const [busy, setBusy] = useState(false);

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
    setDrawingText(EMPTY_DRAWING_JSON);
    setBanner(null);
  }, []);

  const loadArtifact = useCallback(
    async (id: number) => {
      try {
        setBusy(true);
        const a = await getPatientEyeDiagram(identity, patientId, id);
        setActive(a);
        setTitle(a.title);
        setFindings(a.findings_text);
        setDrawingText(prettyJson(a.drawing_json));
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
    if (active.is_signed) {
      parts.push("signed");
    } else {
      parts.push("unsigned");
    }
    return parts.join(" · ");
  }, [active]);

  const onSaveNew = useCallback(async () => {
    const parsed = parseDrawingJson(drawingText);
    if (!parsed.ok) {
      setBanner({ kind: "error", msg: parsed.reason });
      return;
    }
    try {
      setBusy(true);
      const created = await createPatientEyeDiagram(identity, patientId, {
        title,
        findings_text: findings,
        drawing_json: parsed.value,
        encounter_id: encounterId ?? undefined,
      });
      setActive(created);
      setBanner({ kind: "ok", msg: `Created v${created.version_number} (#${created.id}).` });
      await refresh();
    } catch (err) {
      setBanner({ kind: "error", msg: `Save failed: ${friendly(err)}` });
    } finally {
      setBusy(false);
    }
  }, [drawingText, encounterId, findings, identity, patientId, refresh, title]);

  const onUpdate = useCallback(async () => {
    if (!active) return;
    const parsed = parseDrawingJson(drawingText);
    if (!parsed.ok) {
      setBanner({ kind: "error", msg: parsed.reason });
      return;
    }
    try {
      setBusy(true);
      const updated = await updatePatientEyeDiagram(
        identity,
        patientId,
        active.id,
        { title, findings_text: findings, drawing_json: parsed.value }
      );
      setActive(updated);
      setBanner({ kind: "ok", msg: `Saved (v${updated.version_number}).` });
      await refresh();
    } catch (err) {
      setBanner({ kind: "error", msg: `Update failed: ${friendly(err)}` });
    } finally {
      setBusy(false);
    }
  }, [active, drawingText, findings, identity, patientId, refresh, title]);

  const onForkFromSigned = useCallback(async () => {
    if (!active) return;
    const parsed = parseDrawingJson(drawingText);
    if (!parsed.ok) {
      setBanner({ kind: "error", msg: parsed.reason });
      return;
    }
    try {
      setBusy(true);
      const forked = await updatePatientEyeDiagram(
        identity,
        patientId,
        active.id,
        { title, findings_text: findings, drawing_json: parsed.value },
        { fork: true }
      );
      setActive(forked);
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
  }, [active, drawingText, findings, identity, patientId, refresh, title]);

  const onSign = useCallback(async () => {
    if (!active) return;
    try {
      setBusy(true);
      const signed = await signPatientEyeDiagram(identity, patientId, active.id);
      setActive(signed);
      setBanner({ kind: "ok", msg: `Signed.` });
      await refresh();
    } catch (err) {
      setBanner({ kind: "error", msg: `Sign failed: ${friendly(err)}` });
    } finally {
      setBusy(false);
    }
  }, [active, identity, patientId, refresh]);

  return (
    <div className="eye-diagram-panel" data-testid="eye-diagram-panel">
      <header className="eye-diagram-panel__header">
        <h3>Retinal diagram artifacts</h3>
        <p className="eye-diagram-panel__hint">
          Persistence shell. Drawing payload is plain JSON; the canvas
          widget and AI proposals land in a later PR.
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
            This artifact is signed and immutable. Saving will create a
            new version that points back at this one as its parent.
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

        <label>
          <span>Findings</span>
          <textarea
            rows={4}
            value={findings}
            onChange={(e) => setFindings(e.target.value)}
            disabled={busy}
            data-testid="eye-diagram-findings"
          />
        </label>

        <label>
          <span>Drawing JSON</span>
          <textarea
            rows={8}
            value={drawingText}
            onChange={(e) => setDrawingText(e.target.value)}
            disabled={busy}
            data-testid="eye-diagram-drawing-json"
            spellCheck={false}
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
