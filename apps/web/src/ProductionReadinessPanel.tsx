// apps/web/src/ProductionReadinessPanel.tsx
//
// ChartNav production-readiness surface — combines:
//
//   A. PROOF metrics (Phase 6 of the brief) — operationally truthful
//      KPIs derived from existing admin dashboard + multi-clinic
//      data. Metrics ChartNav cannot honestly calculate today
//      (denied-claim correlation, real edit-burden timestamps) are
//      marked as "pending — N samples needed" rather than fabricated.
//
//   B. ROLLOUT readiness (Phase 7 of the brief) — per-location
//      checklist: role coverage (front_desk / technician / clinician
//      / reviewer / admin invited?), specialty templates ready,
//      fake-data demo seeded, security review packet status. Built
//      from existing user roles + locations + role view presets +
//      Phase 24B wedge presence.
//
// Visible only to admins (RBAC mirrors the Security Readiness
// panel). The page surfaces real data when it exists and pending
// markers everywhere else — no fabrication.
//
// Non-goals (matched to the public claim contract):
//   - does not submit anything
//   - does not auto-grade adoption or auto-approve a rollout
//   - does not modify users, locations, role view presets, or
//     specialty template availability — read-only surface

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ApiError,
  type AdminDashboard,
  type Location,
  type Me,
  type Role,
  getAdminDashboard,
  listLocations,
  listUsers,
  isAdmin,
  type User,
} from "./api";
import {
  SPECIALTY_TEMPLATES,
  SPECIALTY_TEMPLATE_SPECIALTIES,
  type SpecialtyTemplateSpecialty,
} from "./specialtyTemplates";

const REQUIRED_ROLES: Role[] = [
  "admin",
  "clinician",
  "reviewer",
  "front_desk",
  "technician",
];

interface ProofKPI {
  id: string;
  label: string;
  value: string;
  hint: string;
  status: "live" | "pending" | "warn";
}

interface RolloutLocationRow {
  locationId: number | "_unassigned";
  locationName: string;
  roleCoverage: Record<Role, number>;
  specialtyTemplateCount: number;
  fakeDataDemoSeeded: boolean;
  /** Derived overall readiness: every required role has >= 1 user,
   *  at least one specialty template, and the fake-data demo is
   *  present. */
  readyForControlledPilot: boolean;
}

interface Props {
  identity: string;
  me: Me;
}

export function ProductionReadinessPanel({ identity, me }: Props) {
  const adminAllowed = isAdmin(me.role);
  const [admin, setAdmin] = useState<AdminDashboard | null>(null);
  const [locations, setLocations] = useState<Location[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!adminAllowed) return;
    setLoading(true);
    setError(null);
    try {
      const [a, l, u] = await Promise.all([
        getAdminDashboard(identity),
        listLocations(identity),
        listUsers(identity),
      ]);
      setAdmin(a as AdminDashboard);
      setLocations(l);
      setUsers(u);
    } catch (e) {
      const msg =
        e instanceof ApiError ? `${e.errorCode}: ${e.reason}` : String(e);
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [identity, adminAllowed]);

  useEffect(() => {
    void load();
  }, [load]);

  const proofKpis = useMemo<ProofKPI[]>(() => {
    if (!admin) return [];
    const counts = admin.counts;
    const totalOpen = counts.total_open_queue_items ?? 0;
    const overdue = counts.overdue_queue_items ?? 0;
    const unsigned = counts.unsigned_notes_count ?? 0;
    const sameDayPct =
      totalOpen === 0
        ? null
        : Math.max(
            0,
            Math.round(((totalOpen - overdue) / totalOpen) * 100),
          );
    return [
      {
        id: "open-queue",
        label: "Open queue items",
        value: String(totalOpen),
        hint:
          "Live count from the admin dashboard. Higher in-progress "
          + "is normal during clinic hours; persistent overdue is the "
          + "actionable signal.",
        status: "live",
      },
      {
        id: "overdue",
        label: "Overdue items",
        value: String(overdue),
        hint:
          "Queue rows past their due_at. A non-zero count indicates "
          + "lane handoffs are stuck — front-desk / technician / MD / "
          + "reviewer cannot drain it on their own.",
        status: overdue > 0 ? "warn" : "live",
      },
      {
        id: "unsigned-notes",
        label: "Unsigned notes",
        value: String(unsigned),
        hint:
          "Notes drafted but not yet signed. Sign-off remains an "
          + "explicit provider action; ChartNav never finalizes a "
          + "note on the provider's behalf.",
        status: "live",
      },
      {
        id: "non-overdue-share",
        label: "Non-overdue share",
        value: sameDayPct === null ? "—" : `${sameDayPct}%`,
        hint:
          sameDayPct === null
            ? "No open queue items right now — this rate computes when items exist."
            : "Share of open queue items that are not yet overdue. Same-day-signed proxy until a true signed_within_24h metric ships.",
        status: sameDayPct === null ? "pending" : "live",
      },
      {
        id: "edit-burden",
        label: "Edit burden after AI draft",
        value: "pending",
        hint:
          "Median per-note edit count between AI draft and provider "
          + "finalize. Pending — needs a longitudinal scribe-session "
          + "edit-event seam (Phase 25 candidate). Today the live "
          + "data does not include the per-event diff size.",
        status: "pending",
      },
      {
        id: "denied-claim-correlation",
        label: "Denied-claim correlation",
        value: "future",
        hint:
          "Correlation between ChartNav-coordinated notes and "
          + "claim-denial rates. ChartNav does not bill, code, or "
          + "submit claims today; this metric is a future capability "
          + "gated on the practice's RCM integration, not on "
          + "ChartNav itself.",
        status: "pending",
      },
    ];
  }, [admin]);

  const rolloutRows = useMemo<RolloutLocationRow[]>(() => {
    // Group users by primary location_id. Many seeded users have no
    // location assignment today (they are org-scoped, not location-
    // scoped); we surface them in an "_unassigned" pseudo-row so the
    // operator can see whether every location actually has every
    // required role covered.
    const byLoc = new Map<number | "_unassigned", User[]>();
    for (const u of users) {
      // Phase 22 users carry an optional location_id we surface
      // permissively — if absent, we bucket under _unassigned.
      const locId =
        (u as User & { location_id?: number | null }).location_id ?? null;
      const key: number | "_unassigned" = locId ?? "_unassigned";
      const arr = byLoc.get(key) ?? [];
      arr.push(u);
      byLoc.set(key, arr);
    }

    const rows: RolloutLocationRow[] = [];
    // Real locations first, ordered by id.
    const ordered = [...locations].sort((a, b) => a.id - b.id);
    for (const loc of ordered) {
      const usersForLoc = byLoc.get(loc.id) ?? [];
      rows.push(buildRow(loc.id, loc.name, usersForLoc));
    }
    // Append the _unassigned bucket if it has users.
    const unassigned = byLoc.get("_unassigned") ?? [];
    if (unassigned.length > 0) {
      rows.push(buildRow("_unassigned", "Unassigned / org-scoped", unassigned));
    }
    return rows;
  }, [users, locations]);

  if (!adminAllowed) {
    return (
      <section
        className="production-readiness production-readiness--blocked"
        data-testid="production-readiness-blocked"
      >
        <h2 className="production-readiness__title">Production readiness</h2>
        <p className="production-readiness__empty">
          The production-readiness surface is admin-only. Switch to
          an admin identity (or ask your admin) to view it.
        </p>
      </section>
    );
  }

  return (
    <section
      className="production-readiness"
      data-testid="production-readiness"
      aria-label="Production readiness"
    >
      <header className="production-readiness__header">
        <div>
          <h2 className="production-readiness__title">
            Production readiness
          </h2>
          <p className="production-readiness__subtitle subtle-note">
            Proof metrics + per-location rollout. Live data where the
            current backend supports it; pending markers everywhere
            else. ChartNav does not fabricate analytics — when a
            metric is not derivable today, it is flagged as pending.
          </p>
        </div>
        <button
          type="button"
          className="btn"
          data-testid="production-readiness-refresh"
          onClick={() => void load()}
          disabled={loading}
        >
          {loading ? "Refreshing…" : "Refresh"}
        </button>
      </header>

      {error && (
        <div
          className="banner banner--error"
          role="alert"
          data-testid="production-readiness-error"
        >
          {error}
        </div>
      )}

      <section
        className="production-readiness__section"
        data-testid="production-readiness-proof"
      >
        <h3 className="production-readiness__section-title">
          Proof metrics
        </h3>
        <p className="production-readiness__lead subtle-note">
          ChartNav's measurable operational signals for the live
          organization. Counts come from the active admin dashboard;
          provider, time-of-day, and edit-burden breakdowns are
          pending until the longitudinal seam ships.
        </p>
        {!admin ? (
          <p
            className="production-readiness__empty"
            data-testid="production-readiness-proof-empty"
          >
            {loading
              ? "Loading admin dashboard…"
              : "Admin dashboard unavailable; refresh to try again."}
          </p>
        ) : (
          <ul
            className="production-readiness__kpi-grid"
            data-testid="production-readiness-kpi-grid"
          >
            {proofKpis.map((k) => (
              <li
                key={k.id}
                className={
                  "production-readiness__kpi "
                  + `production-readiness__kpi--${k.status}`
                }
                data-testid={`production-readiness-kpi-${k.id}`}
                data-status={k.status}
              >
                <span className="production-readiness__kpi-label">
                  {k.label}
                </span>
                <span className="production-readiness__kpi-value">
                  {k.value}
                </span>
                <span className="production-readiness__kpi-hint subtle-note">
                  {k.hint}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section
        className="production-readiness__section"
        data-testid="production-readiness-rollout"
      >
        <h3 className="production-readiness__section-title">
          Rollout readiness — by location
        </h3>
        <p className="production-readiness__lead subtle-note">
          Per-location adoption signal: which of the five required
          roles have a user, how many specialty templates are
          available for the practice's clinicians, and whether the
          fake-data demo wedge is seeded. Real-PHI deployment is
          still gated by{" "}
          <code>docs/security/chartnav-real-phi-go-live-gate.md</code>.
        </p>
        {rolloutRows.length === 0 ? (
          <p
            className="production-readiness__empty"
            data-testid="production-readiness-rollout-empty"
          >
            {loading
              ? "Loading rollout data…"
              : "No locations available for this organization."}
          </p>
        ) : (
          <table
            className="production-readiness__table"
            data-testid="production-readiness-rollout-table"
          >
            <thead>
              <tr>
                <th>Location</th>
                {REQUIRED_ROLES.map((r) => (
                  <th key={r}>{roleLabel(r)}</th>
                ))}
                <th>Templates</th>
                <th>Demo wedge</th>
                <th>Ready</th>
              </tr>
            </thead>
            <tbody>
              {rolloutRows.map((row) => (
                <tr
                  key={String(row.locationId)}
                  data-testid={`production-readiness-rollout-row-${String(row.locationId)}`}
                >
                  <td>{row.locationName}</td>
                  {REQUIRED_ROLES.map((r) => (
                    <td
                      key={r}
                      data-testid={`production-readiness-rollout-cell-${String(row.locationId)}-${r}`}
                    >
                      <span
                        className={
                          "production-readiness__role-pill "
                          + (row.roleCoverage[r] > 0
                            ? "production-readiness__role-pill--ok"
                            : "production-readiness__role-pill--missing")
                        }
                      >
                        {row.roleCoverage[r]}
                      </span>
                    </td>
                  ))}
                  <td
                    data-testid={`production-readiness-rollout-templates-${String(row.locationId)}`}
                  >
                    {row.specialtyTemplateCount}
                  </td>
                  <td
                    data-testid={`production-readiness-rollout-demo-${String(row.locationId)}`}
                  >
                    {row.fakeDataDemoSeeded ? "yes" : "no"}
                  </td>
                  <td
                    data-testid={`production-readiness-rollout-ready-${String(row.locationId)}`}
                    className={
                      row.readyForControlledPilot
                        ? "production-readiness__ready-cell production-readiness__ready-cell--ready"
                        : "production-readiness__ready-cell production-readiness__ready-cell--not-ready"
                    }
                  >
                    {row.readyForControlledPilot ? "ready" : "gaps"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section
        className="production-readiness__section"
        data-testid="production-readiness-template-coverage"
      >
        <h3 className="production-readiness__section-title">
          Specialty template coverage
        </h3>
        <p className="production-readiness__lead subtle-note">
          Templates currently available to clinicians, grouped by
          specialty. The clinician chooses whether to insert one;
          ChartNav does not auto-apply a template.
        </p>
        <ul
          className="production-readiness__specialty-grid"
          data-testid="production-readiness-specialty-grid"
        >
          {SPECIALTY_TEMPLATE_SPECIALTIES.map((sp) => {
            const count = SPECIALTY_TEMPLATES.filter(
              (t) => t.specialty === sp,
            ).length;
            return (
              <li
                key={sp}
                className="production-readiness__specialty-card"
                data-testid={`production-readiness-specialty-${sp}`}
              >
                <span className="production-readiness__specialty-label">
                  {specialtyLabel(sp)}
                </span>
                <span className="production-readiness__specialty-count">
                  {count}
                </span>
              </li>
            );
          })}
        </ul>
      </section>
    </section>
  );
}

function buildRow(
  locationId: number | "_unassigned",
  locationName: string,
  users: User[],
): RolloutLocationRow {
  const coverage: Record<Role, number> = {
    admin: 0,
    clinician: 0,
    reviewer: 0,
    front_desk: 0,
    technician: 0,
  };
  for (const u of users) {
    if (u.role in coverage) {
      coverage[u.role as Role]++;
    }
  }
  // Phase 24B fake-data demo wedge proxy: today's seeded users have
  // no `location_id` field, so an org-scoped admin user with the
  // `@chartnav.local` domain counts as the demo-wedge signal for
  // any row this bucket of users belongs to. A future Phase 25+
  // surface can read a real `phase_24b_wedge_seeded` flag from the
  // backend and tighten this heuristic.
  const allRolesPresent = (Object.keys(coverage) as Role[]).every(
    (r) => coverage[r] > 0,
  );
  const fakeDataDemoSeeded =
    allRolesPresent
    && users.some(
      (u) =>
        u.email.toLowerCase().endsWith("@chartnav.local")
        && u.role === "admin",
    );
  const specialtyTemplateCount = SPECIALTY_TEMPLATES.length;
  const readyForControlledPilot =
    allRolesPresent && specialtyTemplateCount > 0 && fakeDataDemoSeeded;
  return {
    locationId,
    locationName,
    roleCoverage: coverage,
    specialtyTemplateCount,
    fakeDataDemoSeeded,
    readyForControlledPilot,
  };
}

function roleLabel(r: Role): string {
  if (r === "front_desk") return "Front desk";
  if (r === "technician") return "Tech";
  if (r === "clinician") return "MD";
  if (r === "reviewer") return "Rev";
  return "Admin";
}

function specialtyLabel(s: SpecialtyTemplateSpecialty): string {
  if (s === "retina") return "Retina";
  if (s === "glaucoma") return "Glaucoma";
  if (s === "cornea") return "Cornea";
  if (s === "cataract") return "Cataract";
  return "Oculoplastics";
}
