// Phase 58 — practice backup / restore / reinstall recovery UI.
//
// Narrow admin surface, mounted as a new "Backup" tab in AdminPanel.
// The product is a browser-only web app — there is no desktop shell
// and no filesystem access beyond what the browser hands us. So the
// honest flows are:
//
//   BACKUP  → server assembles a bundle, UI prompts a Save-As
//             download via an object URL.
//   RESTORE → user selects a .json bundle through an <input type=file>,
//             browser reads it, UI posts it to the server for
//             validation and (security-admin-only) restore.
//
// Nothing on this screen mutates server state except the two
// explicit action buttons. The restore form defaults to dry-run +
// unconfirmed so an accidental click cannot destroy anything; the
// user must flip BOTH toggles to confirm destruction.
//
// Intentionally small. Not a redesign. No batch operations, no
// scheduled backups, no automation — those would warrant a full
// admin surface of their own.

import { useCallback, useEffect, useState } from "react";
import {
  ApiError,
  Me,
  PracticeBackupBundle,
  PracticeBackupHistoryRow,
  PracticeBackupRestoreResponse,
  PracticeBackupValidationVerdict,
  createPracticeBackup,
  downloadPracticeBackupBundle,
  getPracticeBackupHistory,
  restorePracticeBackup,
  validatePracticeBackup,
} from "./api";

interface Props {
  identity: string;
  me: Me;
}

function friendly(e: unknown): string {
  if (e instanceof ApiError) return `${e.status} ${e.errorCode} — ${e.reason}`;
  if (e instanceof Error) return e.message;
  return String(e);
}

function fmtBytes(n: number | null): string {
  if (n == null) return "—";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

function fmtTime(iso: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

export function BackupPane({ identity, me }: Props) {
  const canView = me.role === "admin";
  const [history, setHistory] = useState<PracticeBackupHistoryRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [lastCreated, setLastCreated] = useState<string | null>(null);

  // Restore state.
  const [selectedBundle, setSelectedBundle] =
    useState<PracticeBackupBundle | null>(null);
  const [selectedName, setSelectedName] = useState<string | null>(null);
  const [verdict, setVerdict] =
    useState<PracticeBackupValidationVerdict | null>(null);
  const [dryRun, setDryRun] = useState(true);
  const [confirmDestructive, setConfirmDestructive] = useState(false);
  const [restoring, setRestoring] = useState(false);
  const [restoreResult, setRestoreResult] =
    useState<PracticeBackupRestoreResponse | null>(null);

  const loadHistory = useCallback(async () => {
    if (!canView) return;
    try {
      const r = await getPracticeBackupHistory(identity);
      setHistory(r.history);
    } catch (e) {
      setError(friendly(e));
    }
  }, [canView, identity]);

  useEffect(() => {
    void loadHistory();
  }, [loadHistory]);

  if (!canView) {
    return (
      <div data-testid="backup-pane-restricted">
        <p className="subtle-note">
          Backup &amp; restore is restricted to organization admins.
        </p>
      </div>
    );
  }

  const onCreate = async () => {
    setCreating(true);
    setError(null);
    setLastCreated(null);
    try {
      const r = await createPracticeBackup(identity, "");
      const filename = downloadPracticeBackupBundle(
        r.bundle,
        r.hash_sha256,
        me.organization_id,
      );
      setLastCreated(filename);
      await loadHistory();
    } catch (e) {
      setError(friendly(e));
    } finally {
      setCreating(false);
    }
  };

  const onFilePicked = async (file: File) => {
    setError(null);
    setVerdict(null);
    setRestoreResult(null);
    setSelectedBundle(null);
    setSelectedName(file.name);
    try {
      const text = await file.text();
      const parsed = JSON.parse(text) as PracticeBackupBundle;
      setSelectedBundle(parsed);
      const v = await validatePracticeBackup(identity, parsed);
      setVerdict(v);
    } catch (e) {
      setError(friendly(e));
    }
  };

  const onRestore = async () => {
    if (!selectedBundle) return;
    setRestoring(true);
    setError(null);
    setRestoreResult(null);
    try {
      const r = await restorePracticeBackup(identity, selectedBundle, {
        dryRun,
        confirmDestructive,
      });
      setRestoreResult(r);
      if (!r.dry_run) await loadHistory();
    } catch (e) {
      setError(friendly(e));
    } finally {
      setRestoring(false);
    }
  };

  return (
    <div className="backup-pane" data-testid="backup-pane">
      <h2 className="backup-pane__title">Practice backup &amp; restore</h2>
      <p className="subtle-note">
        Backup creates a signed JSON bundle of this organization's clinical
        data that is saved to your computer. Restore imports that bundle
        into an empty organization — delete-and-reinstall recovery flow.
      </p>

      {error && (
        <div
          className="banner banner--error"
          role="alert"
          data-testid="backup-error"
        >
          {error}
        </div>
      )}

      {/* ---------- Create backup ---------- */}

      <section className="backup-pane__section">
        <h3 className="backup-pane__heading">Create backup</h3>
        <p className="subtle-note">
          Assembles the bundle on the server and prompts you to save the
          file locally. The server only keeps a hash + timestamp, not the
          bundle bytes — keep the file somewhere safe.
        </p>
        <div className="row">
          <button
            type="button"
            className="btn btn--primary"
            onClick={() => void onCreate()}
            disabled={creating}
            data-testid="backup-create"
          >
            {creating ? "Assembling…" : "Create backup &amp; download"}
          </button>
        </div>
        {lastCreated && (
          <p
            className="subtle-note"
            data-testid="backup-create-success"
          >
            Downloaded: <code>{lastCreated}</code>
          </p>
        )}
      </section>

      {/* ---------- Restore backup ---------- */}

      <section className="backup-pane__section">
        <h3 className="backup-pane__heading">Restore backup</h3>
        <p className="subtle-note">
          Restore is <strong>empty-target-only</strong>: this organization
          must have no encounters, no patients, and no notes. Dry-run first
          to see what would be imported.
        </p>
        <label className="backup-pane__picker">
          Select backup file (.json)
          <input
            type="file"
            accept="application/json,application/vnd.chartnav.practice-backup+json"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) void onFilePicked(f);
            }}
            data-testid="backup-restore-file"
          />
        </label>
        {selectedName && (
          <p className="subtle-note" data-testid="backup-restore-file-name">
            Selected: <code>{selectedName}</code>
          </p>
        )}

        {verdict && (
          <div
            className={
              "backup-verdict " +
              (verdict.ok ? "backup-verdict--ok" : "backup-verdict--bad")
            }
            data-testid="backup-restore-verdict"
            data-ok={verdict.ok ? "true" : "false"}
          >
            <div>
              <strong>Validation:</strong>{" "}
              {verdict.ok ? "OK" : `FAILED (${verdict.error_code})`}
            </div>
            {verdict.reason && !verdict.ok && (
              <div className="subtle-note">{verdict.reason}</div>
            )}
            <dl className="backup-verdict__meta">
              <div>
                <dt>Bundle version</dt>
                <dd>{verdict.bundle_version || "—"}</dd>
              </div>
              <div>
                <dt>Source schema</dt>
                <dd>{verdict.schema_version || "—"}</dd>
              </div>
              <div>
                <dt>Source org</dt>
                <dd>{verdict.source_organization_id ?? "—"}</dd>
              </div>
              <div>
                <dt>Hash</dt>
                <dd>
                  <code>{(verdict.claimed_hash || "").slice(0, 16)}</code>
                  {verdict.body_hash_ok === false ? " (MISMATCH)" : ""}
                </dd>
              </div>
            </dl>
            <dl className="backup-verdict__counts">
              {Object.entries(verdict.counts).map(([k, n]) => (
                <div key={k}>
                  <dt>{k}</dt>
                  <dd>{n}</dd>
                </div>
              ))}
            </dl>
          </div>
        )}

        {verdict?.ok && (
          <div className="backup-pane__restore-controls">
            <label className="row" style={{ gap: 6 }}>
              <input
                type="checkbox"
                checked={dryRun}
                onChange={(e) => setDryRun(e.target.checked)}
                data-testid="backup-restore-dry-run"
              />{" "}
              Dry run (no writes)
            </label>
            <label className="row" style={{ gap: 6 }}>
              <input
                type="checkbox"
                checked={confirmDestructive}
                onChange={(e) => setConfirmDestructive(e.target.checked)}
                disabled={dryRun}
                data-testid="backup-restore-confirm"
              />{" "}
              I understand this will write the bundle into this empty
              organization
            </label>
            <div className="row" style={{ gap: 8 }}>
              <button
                type="button"
                className="btn btn--primary"
                onClick={() => void onRestore()}
                disabled={
                  restoring ||
                  (!dryRun && !confirmDestructive)
                }
                data-testid="backup-restore-submit"
              >
                {restoring
                  ? "Restoring…"
                  : dryRun
                  ? "Run dry restore"
                  : "Apply restore"}
              </button>
            </div>
          </div>
        )}

        {restoreResult && (
          <div
            className="backup-restore-result"
            data-testid="backup-restore-result"
          >
            <strong>
              {restoreResult.dry_run ? "Dry run" : "Restore applied"}
            </strong>
            {" · "}mode={restoreResult.mode}
            <dl className="backup-verdict__counts">
              {Object.entries(restoreResult.applied_counts).map(([k, n]) => (
                <div key={k}>
                  <dt>{k}</dt>
                  <dd>{n}</dd>
                </div>
              ))}
            </dl>
          </div>
        )}
      </section>

      {/* ---------- History ---------- */}

      <section className="backup-pane__section">
        <h3 className="backup-pane__heading">History</h3>
        <p className="subtle-note">
          Every backup + restore event for this organization. Bundle
          bytes are never persisted — this is metadata only.
        </p>
        {history.length === 0 ? (
          <p className="subtle-note" data-testid="backup-history-empty">
            No backup or restore events yet.
          </p>
        ) : (
          <table className="sec-table" data-testid="backup-history-table">
            <thead>
              <tr>
                <th>When</th>
                <th>Event</th>
                <th>By</th>
                <th>Hash</th>
                <th>Bytes</th>
                <th>Encounters</th>
                <th>Notes</th>
                <th>Schema</th>
              </tr>
            </thead>
            <tbody>
              {history.map((h) => (
                <tr key={h.id}>
                  <td>{fmtTime(h.created_at)}</td>
                  <td>{h.event_type}</td>
                  <td>{h.created_by_email || "—"}</td>
                  <td>
                    <code>
                      {(h.artifact_hash_sha256 || "").slice(0, 12) || "—"}
                    </code>
                  </td>
                  <td>{fmtBytes(h.artifact_bytes_size)}</td>
                  <td>{h.encounter_count ?? "—"}</td>
                  <td>{h.note_version_count ?? "—"}</td>
                  <td>
                    <code>{h.schema_version || "—"}</code>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
