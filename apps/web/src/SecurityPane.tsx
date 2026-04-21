// Phase 48 — enterprise control-plane wave 2 admin surface.
//
// Four honest sub-blocks, one per backend concern:
//   1. Security policy (read + edit — MFA, idle/absolute timeout,
//      audit sink, security-admin allowlist)
//   2. Audit sink status + test probe
//   3. Active + revoked sessions (list + admin-initiated revoke)
//
// Defaults to read-only when the caller is admin but NOT a security
// admin (e.g. not on the org's `security_admin_emails` allowlist).
// Every write/revoke action surfaces a success or error banner.
// No compliance theater — if the backend returns disabled / empty,
// the UI says so plainly.

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ApiError,
  AuditSinkMode,
  AuditSinkProbeResponse,
  Me,
  Organization,
  SecurityPolicyPayload,
  SecurityPolicyResponse,
  SecuritySessionRow,
  getSecurityPolicy,
  listSecuritySessions,
  probeAuditSink,
  revokeSecuritySession,
  updateSecurityPolicy,
} from "./api";

interface Props {
  identity: string;
  me: Me;
  org: Organization | null;
}

type Banner = { kind: "ok" | "error" | "info"; msg: string } | null;

// --------------------------------------------------------------------

export function SecurityPane({ identity, me, org }: Props) {
  const [policy, setPolicy] = useState<SecurityPolicyPayload | null>(null);
  const [isSecAdmin, setIsSecAdmin] = useState(false);
  const [sessions, setSessions] = useState<SecuritySessionRow[]>([]);
  const [includeRevoked, setIncludeRevoked] = useState(false);
  const [loading, setLoading] = useState(false);
  const [banner, setBanner] = useState<Banner>(null);
  const [probe, setProbe] = useState<AuditSinkProbeResponse | null>(null);
  const [savingPolicy, setSavingPolicy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setBanner(null);
    try {
      const [p, s] = await Promise.all([
        getSecurityPolicy(identity),
        listSecuritySessions(identity, { includeRevoked, limit: 200 }),
      ]);
      setPolicy(p.policy);
      setIsSecAdmin(p.caller_is_security_admin);
      setSessions(s.sessions);
    } catch (e) {
      setBanner({ kind: "error", msg: friendly(e) });
    } finally {
      setLoading(false);
    }
  }, [identity, includeRevoked]);

  useEffect(() => {
    load();
  }, [load]);

  const onSavePolicy = useCallback(
    async (patch: Partial<SecurityPolicyPayload>) => {
      setSavingPolicy(true);
      setBanner(null);
      try {
        const r = await updateSecurityPolicy(identity, patch as any);
        setPolicy(r.policy);
        setIsSecAdmin(r.caller_is_security_admin);
        setBanner({ kind: "ok", msg: "Security policy updated." });
      } catch (e) {
        setBanner({ kind: "error", msg: friendly(e) });
      } finally {
        setSavingPolicy(false);
      }
    },
    [identity]
  );

  const onRevoke = useCallback(
    async (sessionId: number) => {
      setBanner(null);
      try {
        await revokeSecuritySession(identity, sessionId, "admin_terminated");
        setBanner({ kind: "ok", msg: `Session #${sessionId} revoked.` });
        // Keep include-revoked view the same; just refresh.
        await load();
      } catch (e) {
        setBanner({ kind: "error", msg: friendly(e) });
      }
    },
    [identity, load]
  );

  const onProbe = useCallback(async () => {
    setBanner(null);
    setProbe(null);
    try {
      const r = await probeAuditSink(identity);
      setProbe(r);
    } catch (e) {
      setBanner({ kind: "error", msg: friendly(e) });
    }
  }, [identity]);

  return (
    <div className="sec-pane" data-testid="security-pane">
      <div className="sec-pane__head">
        <h3>Security control plane</h3>
        <span className="subtle-note">
          {org?.name ?? `Organization #${me.organization_id}`}
          {isSecAdmin ? " · security-admin" : " · read-only (not a security-admin)"}
        </span>
      </div>

      {banner && (
        <div
          className={`banner banner--${banner.kind}`}
          role={banner.kind === "error" ? "alert" : "status"}
          data-testid="sec-banner"
        >
          {banner.msg}
        </div>
      )}

      <PolicyBlock
        policy={policy}
        canEdit={isSecAdmin}
        loading={loading || savingPolicy}
        onSave={onSavePolicy}
      />

      <AuditSinkBlock
        policy={policy}
        canEdit={isSecAdmin}
        probe={probe}
        onProbe={onProbe}
      />

      <SessionsBlock
        sessions={sessions}
        loading={loading}
        includeRevoked={includeRevoked}
        onToggleRevoked={() => setIncludeRevoked((v) => !v)}
        canRevoke={isSecAdmin}
        onRevoke={onRevoke}
        onRefresh={load}
      />
    </div>
  );
}

// --------------------------------------------------------------------
// Policy block
// --------------------------------------------------------------------

function PolicyBlock({
  policy,
  canEdit,
  loading,
  onSave,
}: {
  policy: SecurityPolicyPayload | null;
  canEdit: boolean;
  loading: boolean;
  onSave: (patch: Partial<SecurityPolicyPayload>) => Promise<void> | void;
}) {
  const [requireMfa, setRequireMfa] = useState(false);
  const [idle, setIdle] = useState<string>("");
  const [absolute, setAbsolute] = useState<string>("");
  const [admins, setAdmins] = useState<string>("");

  useEffect(() => {
    if (!policy) return;
    setRequireMfa(policy.require_mfa);
    setIdle(policy.idle_timeout_minutes != null ? String(policy.idle_timeout_minutes) : "");
    setAbsolute(
      policy.absolute_timeout_minutes != null
        ? String(policy.absolute_timeout_minutes)
        : ""
    );
    setAdmins((policy.security_admin_emails ?? []).join(", "));
  }, [policy]);

  if (!policy) {
    return (
      <section className="sec-block" aria-label="Security policy">
        <header className="sec-block__head">
          <h4>Policy</h4>
          <span className="subtle-note">Loading…</span>
        </header>
      </section>
    );
  }

  const submit = async () => {
    const patch: Partial<SecurityPolicyPayload> = {};
    if (requireMfa !== policy.require_mfa) patch.require_mfa = requireMfa;
    const idleNum = idle.trim() === "" ? null : Number(idle);
    const absNum = absolute.trim() === "" ? null : Number(absolute);
    if (idleNum !== policy.idle_timeout_minutes) patch.idle_timeout_minutes = idleNum;
    if (absNum !== policy.absolute_timeout_minutes)
      patch.absolute_timeout_minutes = absNum;
    const adminList = admins
      .split(/[,;\n]+/)
      .map((s) => s.trim())
      .filter(Boolean);
    const currentAdmins = [...(policy.security_admin_emails ?? [])].sort().join("\n");
    const proposedAdmins = [...adminList].sort().join("\n");
    if (proposedAdmins !== currentAdmins) patch.security_admin_emails = adminList;
    if (Object.keys(patch).length === 0) return;
    await onSave(patch);
  };

  return (
    <section className="sec-block" aria-label="Security policy">
      <header className="sec-block__head">
        <h4>Policy</h4>
        <span className="subtle-note">
          Persisted in <code>organizations.settings</code>
        </span>
      </header>

      <div className="sec-policy__grid">
        <label className="sec-field sec-field--check">
          <input
            type="checkbox"
            checked={requireMfa}
            onChange={(e) => setRequireMfa(e.target.checked)}
            disabled={!canEdit}
            data-testid="sec-require-mfa"
          />
          <span>
            <strong>Require MFA</strong>
            <span className="subtle-note">
              Enforced in bearer-mode via the JWT MFA/AMR claim. Header-mode is permissive.
            </span>
          </span>
        </label>

        <label className="sec-field">
          <span>
            <strong>Idle timeout (minutes)</strong>
            <span className="subtle-note">Blank = off.</span>
          </span>
          <input
            type="number"
            min={1}
            max={43200}
            value={idle}
            onChange={(e) => setIdle(e.target.value)}
            disabled={!canEdit}
            data-testid="sec-idle-timeout"
          />
        </label>

        <label className="sec-field">
          <span>
            <strong>Absolute timeout (minutes)</strong>
            <span className="subtle-note">
              Maximum session lifetime from creation. Blank = off.
            </span>
          </span>
          <input
            type="number"
            min={1}
            max={43200}
            value={absolute}
            onChange={(e) => setAbsolute(e.target.value)}
            disabled={!canEdit}
            data-testid="sec-absolute-timeout"
          />
        </label>

        <label className="sec-field sec-field--wide">
          <span>
            <strong>Security-admin emails</strong>
            <span className="subtle-note">
              Comma-separated. Empty list = any admin is a security-admin
              (fresh-org default). Populated list = only listed admins may
              change security policy, revoke sessions, or test the sink.
            </span>
          </span>
          <textarea
            rows={2}
            value={admins}
            onChange={(e) => setAdmins(e.target.value)}
            disabled={!canEdit}
            data-testid="sec-admin-allowlist"
            placeholder="secops@practice.example, cto@practice.example"
          />
        </label>
      </div>

      <div className="sec-block__actions">
        <button
          type="button"
          className="btn btn--primary"
          disabled={!canEdit || loading}
          onClick={submit}
          data-testid="sec-save-policy"
        >
          {loading ? "Saving…" : "Save policy"}
        </button>
        {!canEdit && (
          <span className="subtle-note" data-testid="sec-readonly-note">
            Read-only — you are not listed as a security-admin for this org.
          </span>
        )}
      </div>
    </section>
  );
}

// --------------------------------------------------------------------
// Audit sink block
// --------------------------------------------------------------------

function AuditSinkBlock({
  policy,
  canEdit,
  probe,
  onProbe,
}: {
  policy: SecurityPolicyPayload | null;
  canEdit: boolean;
  probe: AuditSinkProbeResponse | null;
  onProbe: () => Promise<void> | void;
}) {
  const mode: AuditSinkMode = policy?.audit_sink_mode ?? "disabled";
  const target = policy?.audit_sink_target ?? null;
  return (
    <section className="sec-block" aria-label="Audit sink">
      <header className="sec-block__head">
        <h4>Audit sink</h4>
        <span
          className="sec-pill"
          data-sink-mode={mode}
          data-testid="sec-sink-mode"
        >
          {mode}
        </span>
      </header>
      <dl className="sec-kv">
        <div>
          <dt>Mode</dt>
          <dd data-testid="sec-sink-mode-value">{mode}</dd>
        </div>
        <div>
          <dt>Target</dt>
          <dd data-testid="sec-sink-target-value">{target ?? "—"}</dd>
        </div>
        <div>
          <dt>Last probe</dt>
          <dd data-testid="sec-sink-probe-value">
            {probe ? (
              <span data-tone={probe.ok ? "ok" : "error"}>
                {probe.ok ? "ok" : "fail"} · {probe.detail}
              </span>
            ) : (
              "—"
            )}
          </dd>
        </div>
      </dl>
      <div className="sec-block__actions">
        <button
          type="button"
          className="btn"
          onClick={onProbe}
          disabled={!canEdit}
          data-testid="sec-probe-sink"
          title="Fire a heartbeat event through the configured sink"
        >
          Test sink
        </button>
        <span className="subtle-note">
          JSONL and HTTPS webhook transports are supported today.
        </span>
      </div>
    </section>
  );
}

// --------------------------------------------------------------------
// Sessions block
// --------------------------------------------------------------------

function SessionsBlock({
  sessions,
  loading,
  includeRevoked,
  onToggleRevoked,
  canRevoke,
  onRevoke,
  onRefresh,
}: {
  sessions: SecuritySessionRow[];
  loading: boolean;
  includeRevoked: boolean;
  onToggleRevoked: () => void;
  canRevoke: boolean;
  onRevoke: (id: number) => Promise<void> | void;
  onRefresh: () => Promise<void> | void;
}) {
  const sorted = useMemo(
    () =>
      [...sessions].sort((a, b) =>
        (b.last_activity_at || "").localeCompare(a.last_activity_at || "")
      ),
    [sessions]
  );
  return (
    <section className="sec-block" aria-label="Sessions">
      <header className="sec-block__head">
        <h4>Sessions</h4>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <label className="subtle-note">
            <input
              type="checkbox"
              checked={includeRevoked}
              onChange={onToggleRevoked}
              data-testid="sec-include-revoked"
            />{" "}
            Include revoked
          </label>
          <button
            type="button"
            className="btn btn--muted"
            onClick={onRefresh}
            disabled={loading}
            data-testid="sec-refresh-sessions"
          >
            {loading ? "Refreshing…" : "↻ Refresh"}
          </button>
        </div>
      </header>

      {!loading && sorted.length === 0 && (
        <div className="empty" data-testid="sec-sessions-empty">
          No sessions tracked yet. Session governance is a no-op until
          idle / absolute timeouts are configured for this org.
        </div>
      )}

      {sorted.length > 0 && (
        <div className="sec-table-wrap">
          <table className="sec-table" data-testid="sec-sessions-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>User</th>
                <th>Role</th>
                <th>Auth</th>
                <th>Created</th>
                <th>Last activity</th>
                <th>State</th>
                <th>IP</th>
                <th aria-label="Actions" />
              </tr>
            </thead>
            <tbody>
              {sorted.map((s) => (
                <tr key={s.id} data-testid={`sec-session-row-${s.id}`}>
                  <td>#{s.id}</td>
                  <td>{s.user_email}</td>
                  <td>{s.user_role}</td>
                  <td>{s.auth_mode}</td>
                  <td>{fmtTime(s.created_at)}</td>
                  <td>{fmtTime(s.last_activity_at)}</td>
                  <td>
                    {s.revoked_at ? (
                      <span className="sec-pill" data-sink-mode="revoked">
                        revoked · {s.revoked_reason ?? "—"}
                      </span>
                    ) : (
                      <span className="sec-pill" data-sink-mode="active">active</span>
                    )}
                  </td>
                  <td>{s.remote_addr ?? "—"}</td>
                  <td>
                    {canRevoke && !s.revoked_at && (
                      <button
                        type="button"
                        className="btn btn--muted"
                        onClick={() => onRevoke(s.id)}
                        data-testid={`sec-revoke-${s.id}`}
                      >
                        Revoke
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

// --------------------------------------------------------------------
// Helpers
// --------------------------------------------------------------------

function fmtTime(iso: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

function friendly(e: unknown): string {
  if (e instanceof ApiError) return `${e.status} ${e.errorCode} — ${e.reason}`;
  if (e instanceof Error) return e.message;
  return String(e);
}
