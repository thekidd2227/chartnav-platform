// Phase 2 item 2 — Admin dashboard.
//
// Spec: docs/chartnav/closure/PHASE_B_Admin_Dashboard_and_Operational_Metrics.md
//
// Renders six KPI cards (`data-testid="kpi-card-<slug>"`) and a
// 14-day sparkline pair (`data-testid="trend-sparklines"`). Forbidden
// roles see a documented "not available for your role" empty state
// rather than a blank page.
import { useEffect, useState } from "react";
import {
  AdminDashboardSummary,
  AdminDashboardTrend,
  ApiError,
  Me,
  getAdminDashboardSummary,
  getAdminDashboardTrend,
} from "./api";

interface KpiCardProps {
  slug: string;
  label: string;
  value: string;
  hint?: string;
}

function KpiCard({ slug, label, value, hint }: KpiCardProps) {
  return (
    <div
      className="kpi-card"
      data-testid={`kpi-card-${slug}`}
      role="group"
      aria-label={label}
    >
      <div className="kpi-card__label">{label}</div>
      <div className="kpi-card__value">{value}</div>
      {hint && <div className="kpi-card__hint">{hint}</div>}
    </div>
  );
}

interface SparklineProps {
  testId: string;
  label: string;
  values: number[];
  format?: (n: number) => string;
}

function Sparkline({ testId, label, values, format }: SparklineProps) {
  const fmt = format || ((n: number) => String(n));
  const maxV = values.reduce((m, v) => Math.max(m, v), 0) || 1;
  return (
    <div className="sparkline" data-testid={testId}>
      <div className="sparkline__label">{label}</div>
      <svg viewBox={`0 0 ${values.length * 12} 36`} role="img" aria-label={label}>
        <polyline
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          points={values
            .map((v, i) => `${i * 12 + 6},${36 - (v / maxV) * 30 - 3}`)
            .join(" ")}
        />
      </svg>
      <div className="sparkline__last">last: {fmt(values[values.length - 1] ?? 0)}</div>
    </div>
  );
}

export interface AdminDashboardProps {
  identity: string;
  me: Me | null;
}

export function AdminDashboard({ identity, me }: AdminDashboardProps) {
  const [summary, setSummary] = useState<AdminDashboardSummary | null>(null);
  const [trend, setTrend] = useState<AdminDashboardTrend | null>(null);
  const [forbidden, setForbidden] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setForbidden(false);
    setError(null);
    Promise.all([
      getAdminDashboardSummary(identity),
      getAdminDashboardTrend(identity, 14),
    ])
      .then(([s, t]) => {
        if (cancelled) return;
        setSummary(s);
        setTrend(t);
      })
      .catch((e: unknown) => {
        if (cancelled) return;
        if (e instanceof ApiError && e.status === 403) {
          setForbidden(true);
        } else {
          setError(
            e instanceof Error ? e.message : "Failed to load admin dashboard"
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [identity]);

  if (forbidden) {
    return (
      <div
        className="admin-dashboard admin-dashboard--forbidden"
        data-testid="admin-dashboard-forbidden"
      >
        Admin dashboard is not available for your role
        {me ? ` (${me.role})` : ""}. Ask an administrator if you need
        access.
      </div>
    );
  }
  if (loading) {
    return <div className="admin-dashboard">Loading admin dashboard…</div>;
  }
  if (error) {
    return (
      <div className="admin-dashboard admin-dashboard--error">
        {error}
      </div>
    );
  }
  if (!summary || !trend) return null;

  const lagText = summary.median_sign_to_export_minutes_7d === null
    ? "no exports yet"
    : `${summary.median_sign_to_export_minutes_7d} min`;
  const ratePct = `${Math.round(summary.missing_flag_resolution_rate_14d * 100)}%`;

  return (
    <section
      className="admin-dashboard"
      data-testid="admin-dashboard-root"
      aria-label="Admin dashboard"
    >
      <header className="admin-dashboard__head">
        <h2>Admin dashboard</h2>
        <p className="admin-dashboard__hint">
          Operational metrics derived from ChartNav-observed events
          only. Encounters written directly in the partner EHR (in
          <code> integrated_readthrough </code> mode) are not visible
          here.
        </p>
      </header>
      <div className="admin-dashboard__cards">
        <KpiCard slug="signed-today" label="Encounters signed today"
          value={String(summary.encounters_signed_today)} />
        <KpiCard slug="signed-7d" label="Encounters signed (7 days)"
          value={String(summary.encounters_signed_7d)} />
        <KpiCard slug="median-lag" label="Median sign→export lag (7d)"
          value={lagText} />
        <KpiCard slug="missing-flags-open" label="Missing flags open"
          value={String(summary.missing_flags_open)} />
        <KpiCard slug="missing-flag-resolution-rate"
          label="Flag resolution rate (14d)" value={ratePct} />
        <KpiCard slug="reminders-overdue" label="Reminders overdue"
          value={String(summary.reminders_overdue)} />
      </div>
      <div className="admin-dashboard__trend" data-testid="trend-sparklines">
        <Sparkline
          testId="sparkline-signed"
          label="Signed notes per day"
          values={trend.series.map((b) => b.encounters_signed)}
        />
        <Sparkline
          testId="sparkline-resolution-rate"
          label="Missing-flag resolution rate per day"
          values={trend.series.map((b) => b.missing_flag_resolution_rate)}
          format={(n) => `${Math.round(n * 100)}%`}
        />
      </div>
    </section>
  );
}
