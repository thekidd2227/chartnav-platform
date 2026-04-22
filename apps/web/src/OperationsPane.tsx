// Phase 53 — Wave 8 enterprise operations & exceptions control plane.
//
// Restrained admin-facing tab that aggregates the operational
// exception state of an org into a single usable surface:
//
//   - Overview counters (fed by /admin/operations/overview)
//   - Final-approval queue (pending + invalidated)
//   - Blocked-notes queue (sign-blocked / export-blocked / denial)
//   - Identity / access-denial events
//   - Session governance events
//   - Stuck-ingest inputs
//   - Security-policy configuration card
//
// Intentionally NOT theatrical:
//   - no charts, no trends, no vanity metrics
//   - every number ties to a real audit event or a live note row
//   - every row carries a remediation hint the operator can act on
//   - unknown-category rows degrade gracefully (show the server
//     label verbatim) so adding a new category on the API side does
//     not crash the UI

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ApiError,
  Me,
  OperationsCategoryMeta,
  OperationsFinalApprovalQueue,
  OperationsIdentityResponse,
  OperationsItem,
  OperationsListResponse,
  OperationsOverview,
  OperationsSecurityPolicyStatus,
  getOperationsBlockedNotes,
  getOperationsCategories,
  getOperationsFinalApprovalQueue,
  getOperationsIdentityExceptions,
  getOperationsOverview,
  getOperationsSecurityConfigStatus,
  getOperationsSessionExceptions,
  getOperationsStuckIngest,
} from "./api";

interface Props {
  identity: string;
  me: Me;
}

type OpsTab =
  | "overview"
  | "final-approval"
  | "blocked-notes"
  | "identity"
  | "sessions"
  | "ingest"
  | "security-config";

const TAB_LABELS: Record<OpsTab, string> = {
  overview: "Overview",
  "final-approval": "Final approval",
  "blocked-notes": "Blocked notes",
  identity: "Identity",
  sessions: "Sessions",
  ingest: "Ingest",
  "security-config": "Security config",
};

const WINDOW_OPTIONS: Array<{ label: string; hours: number }> = [
  { label: "Last 24 hours", hours: 24 },
  { label: "Last 7 days", hours: 168 },
  { label: "Last 14 days", hours: 336 },
  { label: "Last 30 days", hours: 720 },
];

function fmtTime(iso: string | null | undefined): string {
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

export function OperationsPane({ identity, me }: Props) {
  const [tab, setTab] = useState<OpsTab>("overview");
  const [hours, setHours] = useState<number>(168);
  const [overview, setOverview] = useState<OperationsOverview | null>(null);
  const [faQueue, setFaQueue] =
    useState<OperationsFinalApprovalQueue | null>(null);
  const [blocked, setBlocked] = useState<OperationsListResponse | null>(null);
  const [identity_, setIdentityData] =
    useState<OperationsIdentityResponse | null>(null);
  const [sessions, setSessions] = useState<OperationsListResponse | null>(null);
  const [ingest, setIngest] = useState<OperationsListResponse | null>(null);
  const [securityStatus, setSecurityStatus] =
    useState<OperationsSecurityPolicyStatus | null>(null);
  const [categories, setCategories] = useState<OperationsCategoryMeta[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  // Loose guard — the SERVER is the authoritative check. We render
  // a polite placeholder for non-admins instead of making the API
  // call that we know will 403.
  const canView = me.role === "admin";

  const loadAll = useCallback(async () => {
    if (!canView) return;
    setLoading(true);
    setError(null);
    try {
      const [ov, cats, sec] = await Promise.all([
        getOperationsOverview(identity, hours),
        getOperationsCategories(identity),
        getOperationsSecurityConfigStatus(identity),
      ]);
      setOverview(ov);
      setCategories(cats.categories);
      setSecurityStatus(sec);
    } catch (e) {
      setError(friendly(e));
    } finally {
      setLoading(false);
    }
  }, [canView, identity, hours]);

  const loadFinalApproval = useCallback(async () => {
    if (!canView) return;
    try {
      setFaQueue(await getOperationsFinalApprovalQueue(identity, 100));
    } catch (e) {
      setError(friendly(e));
    }
  }, [canView, identity]);

  const loadBlocked = useCallback(async () => {
    if (!canView) return;
    try {
      setBlocked(await getOperationsBlockedNotes(identity, hours, 200));
    } catch (e) {
      setError(friendly(e));
    }
  }, [canView, identity, hours]);

  const loadIdentity = useCallback(async () => {
    if (!canView) return;
    try {
      setIdentityData(await getOperationsIdentityExceptions(identity, hours, 200));
    } catch (e) {
      setError(friendly(e));
    }
  }, [canView, identity, hours]);

  const loadSessions = useCallback(async () => {
    if (!canView) return;
    try {
      setSessions(await getOperationsSessionExceptions(identity, hours, 200));
    } catch (e) {
      setError(friendly(e));
    }
  }, [canView, identity, hours]);

  const loadIngest = useCallback(async () => {
    if (!canView) return;
    try {
      setIngest(await getOperationsStuckIngest(identity, 50));
    } catch (e) {
      setError(friendly(e));
    }
  }, [canView, identity]);

  useEffect(() => {
    void loadAll();
  }, [loadAll]);

  useEffect(() => {
    if (tab === "final-approval") void loadFinalApproval();
    else if (tab === "blocked-notes") void loadBlocked();
    else if (tab === "identity") void loadIdentity();
    else if (tab === "sessions") void loadSessions();
    else if (tab === "ingest") void loadIngest();
  }, [tab, loadFinalApproval, loadBlocked, loadIdentity, loadSessions, loadIngest]);

  const categoryByValue = useMemo(() => {
    const m: Record<string, OperationsCategoryMeta> = {};
    for (const c of categories) m[c.value] = c;
    return m;
  }, [categories]);

  if (!canView) {
    return (
      <div className="ops-pane" data-testid="operations-pane-restricted">
        <p className="subtle-note">
          Operations view is restricted to organization admins.
        </p>
      </div>
    );
  }

  return (
    <div className="ops-pane" data-testid="operations-pane">
      <header className="ops-pane__head">
        <h2 className="ops-pane__title">Operations</h2>
        <div className="ops-pane__controls">
          <label className="ops-pane__window">
            Window
            <select
              value={hours}
              onChange={(e) => setHours(parseInt(e.target.value, 10))}
              data-testid="ops-window-select"
            >
              {WINDOW_OPTIONS.map((opt) => (
                <option key={opt.hours} value={opt.hours}>
                  {opt.label}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            className="btn btn--muted"
            onClick={() => void loadAll()}
            disabled={loading}
            data-testid="ops-refresh"
          >
            {loading ? "Refreshing…" : "↻ Refresh"}
          </button>
        </div>
      </header>

      {error && (
        <div className="banner banner--error" role="alert" data-testid="ops-error">
          {error}
        </div>
      )}

      <nav className="ops-tabs" role="tablist" aria-label="Operations tabs">
        {(Object.keys(TAB_LABELS) as OpsTab[]).map((t) => (
          <button
            key={t}
            type="button"
            role="tab"
            aria-selected={tab === t}
            className={`ops-tab ${tab === t ? "ops-tab--active" : ""}`}
            onClick={() => setTab(t)}
            data-testid={`ops-tab-${t}`}
          >
            {TAB_LABELS[t]}
            {tab === t ? null : <OpsTabBadge tab={t} overview={overview} />}
          </button>
        ))}
      </nav>

      <div className="ops-tab-body">
        {tab === "overview" && (
          <OverviewTab
            overview={overview}
            categoryByValue={categoryByValue}
            securityStatus={securityStatus}
          />
        )}
        {tab === "final-approval" && (
          <FinalApprovalTab queue={faQueue} categoryByValue={categoryByValue} />
        )}
        {tab === "blocked-notes" && (
          <ItemListTab
            testid="ops-list-blocked"
            response={blocked}
            categoryByValue={categoryByValue}
            emptyCopy="No blocked sign or export attempts in this window."
          />
        )}
        {tab === "identity" && (
          <IdentityTab data={identity_} categoryByValue={categoryByValue} />
        )}
        {tab === "sessions" && (
          <ItemListTab
            testid="ops-list-sessions"
            response={sessions}
            categoryByValue={categoryByValue}
            emptyCopy="No session revocations or timeouts in this window."
          />
        )}
        {tab === "ingest" && (
          <ItemListTab
            testid="ops-list-ingest"
            response={ingest}
            categoryByValue={categoryByValue}
            emptyCopy="No stuck ingest inputs."
          />
        )}
        {tab === "security-config" && (
          <SecurityConfigTab status={securityStatus} />
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------
// Tab body components
// ---------------------------------------------------------------------

function OpsTabBadge({
  tab,
  overview,
}: {
  tab: OpsTab;
  overview: OperationsOverview | null;
}) {
  if (!overview) return null;
  const counts = overview.counts;
  let n = 0;
  if (tab === "final-approval") {
    n =
      (counts.final_approval_pending || 0) +
      (counts.final_approval_invalidated || 0);
  } else if (tab === "blocked-notes") {
    n =
      (counts.governance_sign_blocked || 0) +
      (counts.export_blocked || 0) +
      (counts.final_approval_signature_mismatch || 0) +
      (counts.final_approval_unauthorized || 0);
  } else if (tab === "identity") {
    n =
      (counts.identity_unknown_user || 0) +
      (counts.identity_invalid_token || 0) +
      (counts.identity_invalid_issuer || 0) +
      (counts.identity_invalid_audience || 0) +
      (counts.identity_missing_user_claim || 0) +
      (counts.identity_cross_org_attempt || 0);
  } else if (tab === "sessions") {
    n =
      (counts.session_revoked_active || 0) +
      (counts.session_idle_timeout || 0) +
      (counts.session_absolute_timeout || 0);
  } else if (tab === "ingest") {
    n = counts.ingest_stuck || 0;
  } else if (tab === "security-config") {
    n = overview.security_policy.unconfigured ? 1 : 0;
  } else if (tab === "overview") {
    n = 0; // no badge on the overview tab itself
  }
  if (n === 0) return null;
  return (
    <span className="ops-tab__badge" data-testid={`ops-tab-badge-${tab}`}>
      {n}
    </span>
  );
}

function OverviewTab({
  overview,
  categoryByValue,
  securityStatus,
}: {
  overview: OperationsOverview | null;
  categoryByValue: Record<string, OperationsCategoryMeta>;
  securityStatus: OperationsSecurityPolicyStatus | null;
}) {
  if (!overview) {
    return (
      <p className="subtle-note" data-testid="ops-overview-loading">
        Loading operational state…
      </p>
    );
  }
  const buckets: Array<{
    heading: string;
    keys: Array<keyof OperationsOverview["counts"] | string>;
  }> = [
    {
      heading: "Governance",
      keys: [
        "final_approval_pending",
        "final_approval_invalidated",
        "governance_sign_blocked",
        "export_blocked",
        "final_approval_signature_mismatch",
        "final_approval_unauthorized",
      ],
    },
    {
      heading: "Identity & sessions",
      keys: [
        "identity_unknown_user",
        "identity_invalid_token",
        "identity_invalid_issuer",
        "identity_invalid_audience",
        "identity_missing_user_claim",
        "identity_cross_org_attempt",
        "session_revoked_active",
        "session_idle_timeout",
        "session_absolute_timeout",
      ],
    },
    {
      heading: "Infrastructure",
      keys: [
        "ingest_stuck",
        "security_policy_unconfigured",
        // Phase 55 — evidence-chain integrity. Surfaced in the
        // overview so admins see chain breakage without having to
        // call /admin/operations/evidence-chain-verify explicitly.
        "evidence_chain_broken",
        // Phase 56 — external evidence sink + export snapshot
        // operational visibility.
        "evidence_sink_delivery_failed",
        "export_snapshot_missing",
        // Phase 57 — signing keyring posture + retry backlog.
        "evidence_signing_inconsistent",
        "evidence_sink_retry_pending",
        // Phase 59 — sink failures that auto-retry will not clear.
        "evidence_sink_permanent_failure",
      ],
    },
  ];
  return (
    <div data-testid="ops-overview">
      <p className="subtle-note" data-testid="ops-overview-summary">
        {overview.total_open === 0
          ? "No open operational exceptions in this window."
          : `${overview.total_open} open operational exception${
              overview.total_open === 1 ? "" : "s"
            } (noisy session/token categories excluded).`}
      </p>
      {buckets.map((b) => (
        <section className="ops-bucket" key={b.heading}>
          <h3 className="ops-bucket__heading">{b.heading}</h3>
          <div className="ops-bucket__cards">
            {b.keys.map((k) => {
              const count = overview.counts[k as string] || 0;
              const meta = categoryByValue[k as string];
              return (
                <div
                  className="ops-card"
                  key={k as string}
                  data-testid={`ops-count-${k as string}`}
                  data-count={count}
                  data-severity={meta?.severity || "info"}
                >
                  <div className="ops-card__count">{count}</div>
                  <div className="ops-card__label">
                    {meta?.label || String(k)}
                  </div>
                  {meta?.next_step ? (
                    <div className="ops-card__hint">{meta.next_step}</div>
                  ) : null}
                </div>
              );
            })}
          </div>
        </section>
      ))}
      {securityStatus ? (
        <SecurityConfigInline status={securityStatus} />
      ) : null}
    </div>
  );
}

function FinalApprovalTab({
  queue,
  categoryByValue,
}: {
  queue: OperationsFinalApprovalQueue | null;
  categoryByValue: Record<string, OperationsCategoryMeta>;
}) {
  if (!queue) return <p className="subtle-note">Loading…</p>;
  return (
    <div data-testid="ops-final-approval">
      <h3 className="ops-section__heading">
        Pending approval ({queue.pending.length})
      </h3>
      {queue.pending.length === 0 ? (
        <p className="subtle-note">No notes awaiting final approval.</p>
      ) : (
        <ItemTable
          items={queue.pending}
          categoryByValue={categoryByValue}
          testid="ops-final-pending-table"
        />
      )}
      <h3 className="ops-section__heading">
        Invalidated approvals ({queue.invalidated.length})
      </h3>
      {queue.invalidated.length === 0 ? (
        <p className="subtle-note">No invalidated approvals.</p>
      ) : (
        <ItemTable
          items={queue.invalidated}
          categoryByValue={categoryByValue}
          testid="ops-final-invalidated-table"
        />
      )}
    </div>
  );
}

function ItemListTab({
  response,
  categoryByValue,
  emptyCopy,
  testid,
}: {
  response: OperationsListResponse | null;
  categoryByValue: Record<string, OperationsCategoryMeta>;
  emptyCopy: string;
  testid: string;
}) {
  if (!response) return <p className="subtle-note">Loading…</p>;
  if (response.items.length === 0)
    return (
      <p className="subtle-note" data-testid={`${testid}-empty`}>
        {emptyCopy}
      </p>
    );
  return (
    <ItemTable
      items={response.items}
      categoryByValue={categoryByValue}
      testid={`${testid}-table`}
    />
  );
}

function IdentityTab({
  data,
  categoryByValue,
}: {
  data: OperationsIdentityResponse | null;
  categoryByValue: Record<string, OperationsCategoryMeta>;
}) {
  if (!data) return <p className="subtle-note">Loading…</p>;
  return (
    <div data-testid="ops-identity">
      <div className="ops-advisory" data-testid="ops-identity-mapping-advisory">
        <p>
          <strong>OIDC identity mapping:</strong>{" "}
          <code>{data.oidc_identity_mapping}</code>.{" "}
          SCIM is{" "}
          <strong>{data.scim_configured ? "configured" : "not configured"}</strong>{" "}
          in this build. Failures below are real denial events; there is no
          provisioning-conflict queue because no provisioning source is wired up.
        </p>
      </div>
      {data.items.length === 0 ? (
        <p className="subtle-note" data-testid="ops-identity-empty">
          No identity-denial events in this window.
        </p>
      ) : (
        <ItemTable
          items={data.items}
          categoryByValue={categoryByValue}
          testid="ops-identity-table"
        />
      )}
    </div>
  );
}

function ItemTable({
  items,
  categoryByValue,
  testid,
}: {
  items: OperationsItem[];
  categoryByValue: Record<string, OperationsCategoryMeta>;
  testid: string;
}) {
  return (
    <table className="ops-table" data-testid={testid}>
      <thead>
        <tr>
          <th>When</th>
          <th>Category</th>
          <th>Actor</th>
          <th>Context</th>
          <th>Error code</th>
          <th>Detail</th>
        </tr>
      </thead>
      <tbody>
        {items.map((it, idx) => {
          const meta = categoryByValue[it.category];
          return (
            <tr
              key={`${it.category}-${idx}-${it.occurred_at || ""}`}
              data-testid={`ops-row-${it.category}`}
              data-severity={it.severity}
            >
              <td>{fmtTime(it.occurred_at)}</td>
              <td>
                <span
                  className="ops-chip"
                  data-severity={it.severity}
                  title={meta?.next_step || it.next_step}
                >
                  {meta?.label || it.label || it.category}
                </span>
              </td>
              <td>{it.actor_email || "—"}</td>
              <td>
                {it.note_id ? (
                  <span>
                    note #{it.note_id}
                    {it.final_approval_status
                      ? ` · ${it.final_approval_status}`
                      : ""}
                  </span>
                ) : it.encounter_id ? (
                  <span>encounter #{it.encounter_id}</span>
                ) : (
                  "—"
                )}
              </td>
              <td>
                <code>{it.error_code || "—"}</code>
              </td>
              <td className="ops-table__detail">{it.detail || "—"}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

function SecurityConfigTab({
  status,
}: {
  status: OperationsSecurityPolicyStatus | null;
}) {
  if (!status) return <p className="subtle-note">Loading…</p>;
  return (
    <div data-testid="ops-security-config">
      <SecurityConfigInline status={status} />
    </div>
  );
}

function SecurityConfigInline({
  status,
}: {
  status: OperationsSecurityPolicyStatus;
}) {
  const rows: Array<{
    label: string;
    ok: boolean;
    detail: string;
    testid: string;
  }> = [
    {
      label: "Session tracking",
      ok: status.session_tracking_configured,
      detail: status.session_tracking_configured
        ? `idle=${status.idle_timeout_minutes ?? "—"}m, absolute=${
            status.absolute_timeout_minutes ?? "—"
          }m`
        : "no idle or absolute timeout configured",
      testid: "ops-config-session-tracking",
    },
    {
      label: "Audit sink",
      ok: status.audit_sink_configured,
      detail: `mode=${status.audit_sink_mode}`,
      testid: "ops-config-audit-sink",
    },
    {
      label: "Security-admin allowlist",
      ok: status.security_admin_allowlist_configured,
      detail: `${status.security_admin_allowlist_count} email(s) on the allowlist`,
      testid: "ops-config-admin-allowlist",
    },
    {
      label: "MFA required",
      ok: status.mfa_required,
      detail: status.mfa_required ? "enforced" : "not enforced",
      testid: "ops-config-mfa",
    },
  ];
  return (
    <section
      className="ops-config"
      data-testid="ops-security-config-card"
      data-unconfigured={status.unconfigured ? "true" : "false"}
    >
      <h3 className="ops-section__heading">Security policy</h3>
      {status.unconfigured ? (
        <div className="banner banner--info" data-testid="ops-config-unconfigured">
          This organization has no enterprise security settings configured.
          Session timeouts, the audit sink, and the security-admin allowlist
          are all off. Review the Security tab to enable what you need.
        </div>
      ) : null}
      <dl className="ops-config__list">
        {rows.map((r) => (
          <div
            key={r.label}
            className="ops-config__row"
            data-ok={r.ok ? "true" : "false"}
            data-testid={r.testid}
          >
            <dt>{r.label}</dt>
            <dd>
              <span className="ops-config__status">
                {r.ok ? "configured" : "not configured"}
              </span>
              <span className="ops-config__detail">{r.detail}</span>
            </dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
