// Phase 22 — Multi-clinic / multi-provider scaling dashboard.
//
// Admin-facing operational rollup: per-location summaries,
// per-provider summaries, queue counts grouped by status / priority
// / role / queue type. Two side panels render selected
// location-dashboard counts and selected provider-dashboard counts.
//
// Read-only here — there are no admin write controls in this
// component. Writes (assignments / rooms / schedule blocks /
// operating hours) flow through the existing AdminPanel surface in
// a later iteration; this PR ships the read-side rollup so the
// operating picture is visible.

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ApiError,
  LocationDashboardSummary,
  Me,
  MultiClinicSummary,
  ProviderDashboardSummary,
  getAdminMultiClinicSummary,
  getLocationDashboard,
  getProviderDashboard,
  isAdmin,
} from "./api";

interface Props {
  identity: string;
  me: Me;
}

function friendly(err: unknown): string {
  if (err instanceof ApiError) return `${err.errorCode}: ${err.reason}`;
  return err instanceof Error ? err.message : String(err);
}

export function MultiClinicDashboard({ identity, me }: Props) {
  const canRead = isAdmin(me.role);

  if (!canRead) {
    return (
      <section
        className="multi-clinic multi-clinic--blocked"
        data-testid="multi-clinic-blocked"
        aria-label="Multi-clinic dashboard"
      >
        <h2 className="multi-clinic__title">Multi-Clinic Operations</h2>
        <p className="multi-clinic__empty">
          Admin role required to view the multi-clinic operations
          summary. Switch to an admin identity to load this panel.
        </p>
      </section>
    );
  }

  return <MultiClinicForAdmin identity={identity} />;
}

function MultiClinicForAdmin({ identity }: { identity: string }) {
  const [summary, setSummary] = useState<MultiClinicSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedLocation, setSelectedLocation] = useState<number | null>(null);
  const [selectedProvider, setSelectedProvider] = useState<number | null>(null);
  const [locDashboard, setLocDashboard] =
    useState<LocationDashboardSummary | null>(null);
  const [provDashboard, setProvDashboard] =
    useState<ProviderDashboardSummary | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getAdminMultiClinicSummary(identity);
      setSummary(data);
      if (selectedLocation === null && data.locations.length > 0) {
        setSelectedLocation(data.locations[0].location_id);
      }
      if (selectedProvider === null && data.providers.length > 0) {
        setSelectedProvider(data.providers[0].provider_id);
      }
    } catch (e) {
      setError(friendly(e));
    } finally {
      setLoading(false);
    }
  }, [identity, selectedLocation, selectedProvider]);

  useEffect(() => {
    void refresh();
  }, [identity]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (selectedLocation === null) {
      setLocDashboard(null);
      return;
    }
    void getLocationDashboard(identity, selectedLocation)
      .then(setLocDashboard)
      .catch((e) => setError(friendly(e)));
  }, [identity, selectedLocation]);

  useEffect(() => {
    if (selectedProvider === null) {
      setProvDashboard(null);
      return;
    }
    void getProviderDashboard(identity, selectedProvider)
      .then(setProvDashboard)
      .catch((e) => setError(friendly(e)));
  }, [identity, selectedProvider]);

  const totalLocations = summary?.locations.length ?? 0;
  const totalProviders = summary?.providers.length ?? 0;
  const totalOpen = useMemo(() => {
    return (summary?.locations ?? []).reduce(
      (acc, l) => acc + (l.open_queue_items ?? 0),
      0
    );
  }, [summary]);

  return (
    <section
      className="multi-clinic"
      data-testid="multi-clinic"
      aria-label="Multi-clinic dashboard"
    >
      <header className="multi-clinic__header">
        <div>
          <h2 className="multi-clinic__title">
            Multi-Clinic Operations — Admin Rollup
          </h2>
          <p className="multi-clinic__subtitle subtle-note">
            Cross-location, cross-provider operational view.
            Read-only summary built from the work queue, schedule
            blocks, location rooms, and provider-location
            assignments. Metadata only — no clinical body text, no
            billing, no patient messaging.
          </p>
        </div>
        <button
          type="button"
          className="btn"
          data-testid="multi-clinic-refresh"
          onClick={() => void refresh()}
          disabled={loading}
        >
          {loading ? "Refreshing…" : "Refresh"}
        </button>
      </header>

      {error && (
        <div
          className="banner banner--error"
          role="alert"
          data-testid="multi-clinic-error"
        >
          {error}
        </div>
      )}

      {!summary && loading && (
        <p className="multi-clinic__empty" data-testid="multi-clinic-loading">
          Loading multi-clinic summary…
        </p>
      )}

      {summary && (
        <>
          <div className="multi-clinic__cards" data-testid="multi-clinic-cards">
            <SummaryCard
              testid="card-total-locations"
              label="Locations"
              value={totalLocations}
            />
            <SummaryCard
              testid="card-total-providers"
              label="Providers"
              value={totalProviders}
            />
            <SummaryCard
              testid="card-total-open"
              label="Open Queue Items"
              value={totalOpen}
            />
            <SummaryCard
              testid="card-by-queue-type"
              label="Queue Types Active"
              value={Object.keys(summary.queue_by_queue_type).length}
            />
          </div>

          <div className="multi-clinic__split">
            <div className="multi-clinic__panel" data-testid="locations-panel">
              <h3 className="multi-clinic__section">Locations</h3>
              {summary.locations.length === 0 ? (
                <p className="multi-clinic__empty" data-testid="locations-empty">
                  No locations configured yet.
                </p>
              ) : (
                <ul
                  className="multi-clinic__list"
                  data-testid="locations-list"
                >
                  {summary.locations.map((loc) => (
                    <li key={loc.location_id}>
                      <button
                        type="button"
                        className={
                          "multi-clinic__row" +
                          (loc.location_id === selectedLocation
                            ? " multi-clinic__row--active"
                            : "")
                        }
                        data-testid={`location-row-${loc.location_id}`}
                        onClick={() => setSelectedLocation(loc.location_id)}
                      >
                        <span className="multi-clinic__row-label">
                          Location #{loc.location_id}
                        </span>
                        <span className="multi-clinic__pill">
                          {loc.open_queue_items} open
                        </span>
                        <span className="multi-clinic__pill">
                          {loc.active_rooms} rooms
                        </span>
                        <span className="multi-clinic__pill">
                          {loc.schedule_blocks_today} blocks today
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
              {locDashboard && (
                <LocationDashboardCard data={locDashboard} />
              )}
            </div>

            <div className="multi-clinic__panel" data-testid="providers-panel">
              <h3 className="multi-clinic__section">Providers</h3>
              {summary.providers.length === 0 ? (
                <p className="multi-clinic__empty" data-testid="providers-empty">
                  No providers configured yet.
                </p>
              ) : (
                <ul
                  className="multi-clinic__list"
                  data-testid="providers-list"
                >
                  {summary.providers.map((prov) => (
                    <li key={prov.provider_id}>
                      <button
                        type="button"
                        className={
                          "multi-clinic__row" +
                          (prov.provider_id === selectedProvider
                            ? " multi-clinic__row--active"
                            : "")
                        }
                        data-testid={`provider-row-${prov.provider_id}`}
                        onClick={() => setSelectedProvider(prov.provider_id)}
                      >
                        <span className="multi-clinic__row-label">
                          Provider #{prov.provider_id}
                        </span>
                        <span className="multi-clinic__pill">
                          {prov.open_queue_items} open
                        </span>
                        <span className="multi-clinic__pill">
                          {prov.schedule_blocks_today} blocks today
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
              {provDashboard && (
                <ProviderDashboardCard data={provDashboard} />
              )}
            </div>
          </div>

          <h3 className="multi-clinic__section">Queue Aging — Breakdowns</h3>
          <div className="multi-clinic__breakdowns">
            <BreakdownTable
              testid="breakdown-status"
              header="Status"
              rows={summary.queue_by_status}
            />
            <BreakdownTable
              testid="breakdown-priority"
              header="Priority"
              rows={summary.queue_by_priority}
            />
            <BreakdownTable
              testid="breakdown-role"
              header="Assigned role"
              rows={summary.queue_by_assigned_role}
            />
            <BreakdownTable
              testid="breakdown-queue-type"
              header="Queue type"
              rows={summary.queue_by_queue_type}
            />
          </div>
        </>
      )}
    </section>
  );
}

// ---------- subcomponents -------------------------------------------

function LocationDashboardCard({
  data,
}: {
  data: LocationDashboardSummary;
}) {
  const c = data.counts;
  return (
    <div
      className="multi-clinic__detail"
      data-testid="location-dashboard-card"
    >
      <h4 className="multi-clinic__detail-title">
        Location #{data.location_id} — operations
      </h4>
      <dl className="multi-clinic__dl">
        <Field label="Open queue" value={c.open_queue_items} />
        <Field label="Ready for workup" value={c.ready_for_workup} />
        <Field label="Imaging needed" value={c.imaging_needed} />
        <Field label="Ready for doctor" value={c.ready_for_doctor} />
        <Field label="Review needed" value={c.review_needed} />
        <Field label="Active providers" value={c.provider_count} />
        <Field label="Active rooms" value={c.room_count} />
        <Field
          label="Schedule blocks today"
          value={c.active_schedule_blocks_today}
        />
      </dl>
    </div>
  );
}

function ProviderDashboardCard({
  data,
}: {
  data: ProviderDashboardSummary;
}) {
  const c = data.counts;
  return (
    <div
      className="multi-clinic__detail"
      data-testid="provider-dashboard-card"
    >
      <h4 className="multi-clinic__detail-title">
        Provider #{data.provider_id} — workload
      </h4>
      <dl className="multi-clinic__dl">
        <Field label="Assigned queue" value={c.assigned_queue_items} />
        <Field label="Ready for doctor" value={c.ready_for_doctor} />
        <Field label="Imaging review" value={c.imaging_review} />
        <Field label="Sign-off needed" value={c.signoff_needed} />
        <Field label="Review needed" value={c.review_needed} />
        <Field
          label="Schedule blocks today"
          value={c.schedule_blocks_today}
        />
        <Field label="Locations today" value={c.locations_today} />
      </dl>
    </div>
  );
}

function SummaryCard({
  testid,
  label,
  value,
}: {
  testid: string;
  label: string;
  value: number;
}) {
  return (
    <div className="multi-clinic__card" data-testid={testid}>
      <div className="multi-clinic__card-label">{label}</div>
      <div className="multi-clinic__card-value">{value}</div>
    </div>
  );
}

function BreakdownTable({
  testid,
  header,
  rows,
}: {
  testid: string;
  header: string;
  rows: Record<string, number>;
}) {
  const entries = Object.entries(rows).sort(
    (a, b) => b[1] - a[1] || a[0].localeCompare(b[0])
  );
  if (entries.length === 0) {
    return (
      <div className="multi-clinic__breakdown">
        <h4 className="multi-clinic__breakdown-title">{header}</h4>
        <p
          className="multi-clinic__empty"
          data-testid={`${testid}-empty`}
        >
          No data.
        </p>
      </div>
    );
  }
  return (
    <div className="multi-clinic__breakdown">
      <h4 className="multi-clinic__breakdown-title">{header}</h4>
      <table className="multi-clinic__table" data-testid={testid}>
        <thead>
          <tr>
            <th>{header}</th>
            <th>Count</th>
          </tr>
        </thead>
        <tbody>
          {entries.map(([k, v]) => (
            <tr key={k}>
              <td>{k.replace(/_/g, " ")}</td>
              <td>{v}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Field({ label, value }: { label: string; value: number }) {
  return (
    <div className="multi-clinic__field">
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}
