// Phase 47 — Pilot KPI / ROI scorecard view (admin panel tab).
//
// One focused surface for pilot review. Nothing here invents a
// metric — every number traces back to the /admin/kpi/* endpoints
// which in turn trace back to encounter_inputs + note_versions
// timestamps the product already writes.
//
// Composition:
//   1. Window selector (7d / 30d / 90d / custom hours)
//   2. Compare toggle (before/after current vs. previous window)
//   3. Pilot summary strip (org + date range + volume + headline KPIs)
//   4. Summary KPI cards (counts, latency medians, rates)
//   5. Provider table (one row per provider, sorted by encounters desc)
//   6. Export button → CSV download
//
// Honest states: loading skeleton, empty window copy, error banner.

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ApiError,
  KpiCompare,
  KpiLatencySummary,
  KpiOverview,
  KpiProviders,
  KpiProviderRow,
  Me,
  Organization,
  downloadKpiCsv,
  getKpiCompare,
  getKpiOverview,
  getKpiProviders,
} from "./api";

interface Props {
  identity: string;
  me: Me;
  org: Organization | null;
}

const WINDOW_PRESETS: { label: string; hours: number }[] = [
  { label: "24h",  hours: 24 },
  { label: "7d",   hours: 24 * 7 },
  { label: "30d",  hours: 24 * 30 },
  { label: "90d",  hours: 24 * 90 },
];

// ---------------------------------------------------------------------
// Formatting helpers
// ---------------------------------------------------------------------

function fmtMin(m: number | null | undefined): string {
  if (m == null) return "—";
  if (m < 60) return `${m.toFixed(0)} min`;
  const h = Math.floor(m / 60);
  const r = Math.round(m - h * 60);
  return r === 0 ? `${h}h` : `${h}h ${r}m`;
}

function fmtPct(v: number | null | undefined): string {
  if (v == null) return "—";
  return `${v.toFixed(1)}%`;
}

function fmtInt(n: number | null | undefined): string {
  if (n == null) return "—";
  return n.toLocaleString();
}

function fmtDelta(pct: number | null | undefined, lowerIsBetter: boolean): {
  label: string;
  tone: "ok" | "warn" | "neutral";
} {
  if (pct == null) return { label: "—", tone: "neutral" };
  const rounded = Math.round(pct * 10) / 10;
  if (rounded === 0) return { label: "0.0%", tone: "neutral" };
  const arrow = rounded > 0 ? "▲" : "▼";
  const label = `${arrow} ${Math.abs(rounded).toFixed(1)}%`;
  // Lower is better for latency + missing-data rate; higher is better
  // for export-ready rate. The caller passes the orientation.
  const improved = lowerIsBetter ? rounded < 0 : rounded > 0;
  return { label, tone: improved ? "ok" : "warn" };
}

function fmtRange(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      year: "numeric", month: "short", day: "numeric",
    });
  } catch { return iso; }
}

// ---------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------

export function KpiPane({ identity, me, org }: Props) {
  const [hours, setHours] = useState<number>(24 * 7);
  const [compareOn, setCompareOn] = useState(false);

  const [overview, setOverview] = useState<KpiOverview | null>(null);
  const [providers, setProviders] = useState<KpiProviders | null>(null);
  const [compare, setCompare] = useState<KpiCompare | null>(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [exportPending, setExportPending] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const [exportOk, setExportOk] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      if (compareOn) {
        const [ov, pr, cmp] = await Promise.all([
          getKpiOverview(identity, hours),
          getKpiProviders(identity, hours),
          getKpiCompare(identity, hours),
        ]);
        setOverview(ov);
        setProviders(pr);
        setCompare(cmp);
      } else {
        const [ov, pr] = await Promise.all([
          getKpiOverview(identity, hours),
          getKpiProviders(identity, hours),
        ]);
        setOverview(ov);
        setProviders(pr);
        setCompare(null);
      }
    } catch (e) {
      if (e instanceof ApiError) setError(`${e.status} ${e.errorCode} — ${e.reason}`);
      else if (e instanceof Error) setError(e.message);
      else setError(String(e));
    } finally {
      setLoading(false);
    }
  }, [identity, hours, compareOn]);

  useEffect(() => { load(); }, [load]);

  const onExport = useCallback(async () => {
    setExportError(null);
    setExportOk(null);
    setExportPending(true);
    try {
      const { filename, blob } = await downloadKpiCsv(identity, hours);
      // Trigger the browser download via a synthetic anchor click.
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      setExportOk(`Exported ${filename}`);
    } catch (e) {
      if (e instanceof Error) setExportError(e.message);
      else setExportError(String(e));
    } finally {
      setExportPending(false);
    }
  }, [identity, hours]);

  // Sort providers by encounter volume descending.
  const sortedProviders: KpiProviderRow[] = useMemo(() => {
    const rows = providers?.providers ?? [];
    return [...rows].sort((a, b) => b.encounters - a.encounters);
  }, [providers]);

  return (
    <div className="kpi-pane" data-testid="kpi-pane">
      {/* ------- Toolbar ------- */}
      <div className="kpi-toolbar" role="toolbar" aria-label="Scorecard controls">
        <div className="kpi-toolbar__group">
          <span className="kpi-toolbar__label">Window</span>
          <div
            className="pref-picker"
            role="radiogroup"
            aria-label="Time window"
            data-testid="kpi-window"
          >
            {WINDOW_PRESETS.map((w) => (
              <button
                key={w.hours}
                type="button"
                role="radio"
                aria-checked={hours === w.hours}
                aria-pressed={hours === w.hours}
                data-testid={`kpi-window-${w.hours}`}
                className="pref-picker__btn"
                onClick={() => setHours(w.hours)}
              >
                {w.label}
              </button>
            ))}
          </div>
        </div>
        <div className="kpi-toolbar__group">
          <label className="kpi-toolbar__label">
            <input
              type="checkbox"
              checked={compareOn}
              onChange={(e) => setCompareOn(e.target.checked)}
              data-testid="kpi-compare-toggle"
            />{" "}
            Compare to previous {hoursLabel(hours)}
          </label>
        </div>
        <div className="kpi-toolbar__spacer" />
        <button
          type="button"
          className="btn"
          onClick={load}
          disabled={loading}
          data-testid="kpi-refresh"
          title="Re-fetch the scorecard"
        >
          {loading ? "Refreshing…" : "↻ Refresh"}
        </button>
        <button
          type="button"
          className="btn btn--primary"
          onClick={onExport}
          disabled={exportPending || loading}
          data-testid="kpi-export"
          title="Download the per-provider scorecard as CSV"
        >
          {exportPending ? "Exporting…" : "⬇ Export CSV"}
        </button>
      </div>

      {exportOk && (
        <div className="banner banner--ok" role="status" data-testid="kpi-export-ok">
          {exportOk}
        </div>
      )}
      {exportError && (
        <div className="banner banner--error" role="alert" data-testid="kpi-export-error">
          Export failed: {exportError}
        </div>
      )}
      {error && (
        <div className="banner banner--error" role="alert" data-testid="kpi-error">
          Failed to load scorecard: {error}
        </div>
      )}

      {/* ------- Pilot summary strip ------- */}
      {overview && (
        <PilotSummary
          overview={overview}
          compare={compare}
          orgName={org?.name ?? `Organization #${overview.organization_id}`}
        />
      )}

      {/* ------- Top-level KPI cards ------- */}
      <div className="kpi-grid" data-testid="kpi-cards">
        <KpiCard
          label="Encounters"
          value={fmtInt(overview?.counts.encounters)}
          deltaPct={compare?.deltas.counts_delta.encounters}
          deltaTone="neutral"
          loading={loading}
          testId="kpi-card-encounters"
          sub={`${fmtInt(overview?.counts.signed_notes)} signed · ${fmtInt(overview?.counts.exported_notes)} exported`}
        />
        <KpiCard
          label="Transcript → Draft (median)"
          value={fmtMin(overview?.latency_minutes.transcript_to_draft.median)}
          deltaLabel={
            compare
              ? fmtDelta(
                  compare.deltas.latency_minutes_median_pct_change.transcript_to_draft,
                  true
                )
              : null
          }
          loading={loading}
          testId="kpi-card-t2d"
          sub={subN(overview?.latency_minutes.transcript_to_draft)}
        />
        <KpiCard
          label="Draft → Sign (median)"
          value={fmtMin(overview?.latency_minutes.draft_to_sign.median)}
          deltaLabel={
            compare
              ? fmtDelta(
                  compare.deltas.latency_minutes_median_pct_change.draft_to_sign,
                  true
                )
              : null
          }
          loading={loading}
          testId="kpi-card-d2s"
          sub={subN(overview?.latency_minutes.draft_to_sign)}
        />
        <KpiCard
          label="Total time to signed note (median)"
          value={fmtMin(overview?.latency_minutes.total_time_to_sign.median)}
          deltaLabel={
            compare
              ? fmtDelta(
                  compare.deltas.latency_minutes_median_pct_change.total_time_to_sign,
                  true
                )
              : null
          }
          loading={loading}
          testId="kpi-card-total"
          sub={
            overview?.latency_minutes.total_time_to_sign.p90 != null
              ? `p90 ${fmtMin(overview.latency_minutes.total_time_to_sign.p90)}`
              : "—"
          }
        />
        <KpiCard
          label="Missing-data rate"
          value={fmtPct(overview?.quality.missing_data_rate)}
          deltaLabel={
            compare
              ? fmtDelta(
                  compare.deltas.quality_pct_change.missing_data_rate,
                  true
                )
              : null
          }
          loading={loading}
          testId="kpi-card-missing"
          sub={
            overview
              ? `${overview.quality.notes_with_missing_flags} / ${overview.quality.notes_observed} notes`
              : "—"
          }
        />
        <KpiCard
          label="Export-ready rate"
          value={fmtPct(overview?.quality.export_ready_rate)}
          deltaLabel={
            compare
              ? fmtDelta(
                  compare.deltas.quality_pct_change.export_ready_rate,
                  false
                )
              : null
          }
          loading={loading}
          testId="kpi-card-export-ready"
          sub={
            overview?.quality.avg_revisions_per_signed_note != null
              ? `avg ${overview.quality.avg_revisions_per_signed_note} revisions / signed note`
              : "—"
          }
        />
      </div>

      {/* ------- Provider breakdown ------- */}
      <section className="kpi-provider-block" aria-label="Per-provider breakdown">
        <header className="kpi-provider-block__head">
          <h3>Provider breakdown</h3>
          <span className="subtle-note">
            {providers
              ? `${providers.providers.length} provider${providers.providers.length === 1 ? "" : "s"}`
              : "—"}
          </span>
        </header>

        {loading && !providers && (
          <div className="empty" data-testid="kpi-providers-loading">Loading providers…</div>
        )}

        {!loading && providers && providers.providers.length === 0 && (
          <div className="empty" data-testid="kpi-providers-empty">
            No provider activity in this window.
          </div>
        )}

        {providers && providers.providers.length > 0 && (
          <div className="kpi-table-wrap" data-testid="kpi-providers-table">
            <table className="kpi-table">
              <thead>
                <tr>
                  <th scope="col">Provider</th>
                  <th scope="col">Encounters</th>
                  <th scope="col">Signed</th>
                  <th scope="col">T → Draft median</th>
                  <th scope="col">D → Sign median</th>
                  <th scope="col">Total (median / p90)</th>
                  <th scope="col">Missing-data</th>
                  <th scope="col">Avg revisions</th>
                </tr>
              </thead>
              <tbody>
                {sortedProviders.map((p) => (
                  <tr key={p.provider} data-testid={`kpi-provider-row-${slug(p.provider)}`}>
                    <th scope="row">{p.provider}</th>
                    <td>{fmtInt(p.encounters)}</td>
                    <td>{fmtInt(p.signed_notes)}</td>
                    <td>{fmtMin(p.transcript_to_draft_min.median)}</td>
                    <td>{fmtMin(p.draft_to_sign_min.median)}</td>
                    <td>
                      {fmtMin(p.total_time_to_sign_min.median)}
                      {p.total_time_to_sign_min.p90 != null && (
                        <span className="subtle-note"> / {fmtMin(p.total_time_to_sign_min.p90)}</span>
                      )}
                    </td>
                    <td>{fmtPct(p.missing_data_rate_pct)}</td>
                    <td>
                      {p.avg_revisions_per_signed_note != null
                        ? p.avg_revisions_per_signed_note.toFixed(1)
                        : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <p className="subtle-note" data-testid="kpi-footer-note">
        All numbers derive from the shipped encounter + note timestamps.
        Latency medians use the first completed transcript input and the
        first signed note per encounter. Missing-data rate counts notes
        whose <code>missing_data_flags</code> were non-empty at write time.
        {me.role !== "admin" ? " Admin role required for this view." : ""}
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------

function PilotSummary({
  overview,
  compare,
  orgName,
}: {
  overview: KpiOverview;
  compare: KpiCompare | null;
  orgName: string;
}) {
  const since = fmtRange(overview.window.since);
  const until = fmtRange(overview.window.until);
  const movement =
    compare?.deltas.latency_minutes_median_pct_change.total_time_to_sign ?? null;
  const movementTone = fmtDelta(movement, true);
  return (
    <section
      className="kpi-pilot-summary"
      aria-label="Pilot summary"
      data-testid="kpi-pilot-summary"
    >
      <div>
        <span className="kpi-pilot-summary__eyebrow">Pilot summary</span>
        <h2>{orgName}</h2>
        <p className="subtle-note">
          {since} → {until} · window {Math.round(overview.window.hours)}h
        </p>
      </div>
      <div className="kpi-pilot-summary__stats">
        <div>
          <span className="kpi-pilot-summary__k">Encounters</span>
          <strong>{fmtInt(overview.counts.encounters)}</strong>
        </div>
        <div>
          <span className="kpi-pilot-summary__k">Signed notes</span>
          <strong>{fmtInt(overview.counts.signed_notes)}</strong>
        </div>
        <div>
          <span className="kpi-pilot-summary__k">Exported</span>
          <strong>{fmtInt(overview.counts.exported_notes)}</strong>
        </div>
        <div>
          <span className="kpi-pilot-summary__k">Total time-to-sign</span>
          <strong>{fmtMin(overview.latency_minutes.total_time_to_sign.median)}</strong>
        </div>
        <div>
          <span className="kpi-pilot-summary__k">Export-ready rate</span>
          <strong>{fmtPct(overview.quality.export_ready_rate)}</strong>
        </div>
        {compare && (
          <div>
            <span className="kpi-pilot-summary__k">Movement vs. prior</span>
            <strong data-tone={movementTone.tone}>{movementTone.label}</strong>
          </div>
        )}
      </div>
    </section>
  );
}

function KpiCard({
  label,
  value,
  sub,
  deltaLabel,
  deltaPct,
  deltaTone,
  loading,
  testId,
}: {
  label: string;
  value: string;
  sub?: string;
  deltaLabel?: { label: string; tone: "ok" | "warn" | "neutral" } | null;
  deltaPct?: number | null;
  deltaTone?: "ok" | "warn" | "neutral";
  loading: boolean;
  testId: string;
}) {
  const delta = deltaLabel
    ? deltaLabel
    : deltaPct != null
    ? { label: `${deltaPct >= 0 ? "+" : ""}${deltaPct}`, tone: deltaTone ?? "neutral" }
    : null;
  return (
    <div className="kpi-card" data-testid={testId} aria-busy={loading}>
      <div className="kpi-card__label">{label}</div>
      <div className="kpi-card__value">{loading && value === "—" ? "…" : value}</div>
      {(sub || delta) && (
        <div className="kpi-card__foot">
          {sub && <span className="kpi-card__sub">{sub}</span>}
          {delta && (
            <span className="kpi-card__delta" data-tone={delta.tone}>
              {delta.label}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------

function subN(s: KpiLatencySummary | undefined): string {
  if (!s || s.n === 0) return "n=0";
  return `n=${s.n}`;
}

function hoursLabel(h: number): string {
  if (h === 24) return "24h";
  if (h === 24 * 7) return "7d";
  if (h === 24 * 30) return "30d";
  if (h === 24 * 90) return "90d";
  return `${h}h`;
}

function slug(s: string): string {
  return s.replace(/\s+/g, "-").replace(/[^a-zA-Z0-9-]/g, "").toLowerCase();
}
