// Phase 20C — Role-based clinic dashboards.
//
// Single file, role-dispatched. The user's role decides which
// subcomponent renders. Admin can switch between role views via the
// optional `viewAs` selector. Each subcomponent renders read-only
// summary cards built from `/dashboards/*` payloads — no PHI bodies,
// no encounter actions, no scheduling.
//
// Lane language is ophthalmology-specific to match the seeded clinics
// (front desk → tech workup → VA / IOP / refraction → MD encounter →
// review). The component never invents counts: every number flows
// from the backend response.

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ApiError,
  DashboardRole,
  DashboardSummary,
  FrontDeskDashboard,
  TechnicianDashboard,
  DoctorDashboard,
  ReviewerDashboard,
  AdminDashboard,
  DashboardQueueItemCompact,
  Me,
  getMyDashboard,
  getFrontDeskDashboard,
  getTechnicianDashboard,
  getDoctorDashboard,
  getReviewerDashboard,
  getAdminDashboard,
  isAdmin,
} from "./api";

type ViewAs = DashboardRole | "me";

const ROLE_OPTIONS: { value: DashboardRole; label: string }[] = [
  { value: "front_desk", label: "Front Desk" },
  { value: "technician", label: "Technician" },
  { value: "clinician", label: "Doctor" },
  { value: "reviewer", label: "Reviewer" },
  { value: "admin", label: "Admin" },
];

function roleLabel(role: DashboardRole): string {
  return ROLE_OPTIONS.find((o) => o.value === role)?.label ?? role;
}

export function RoleDashboard({
  identity,
  me,
}: {
  identity: string;
  me: Me;
}) {
  const canSwitch = isAdmin(me.role);
  const [viewAs, setViewAs] = useState<ViewAs>("me");
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      let payload: DashboardSummary;
      if (viewAs === "me") {
        payload = await getMyDashboard(identity);
      } else {
        payload = await fetchDashboardForRole(identity, viewAs);
      }
      setData(payload);
    } catch (e) {
      const msg =
        e instanceof ApiError ? `${e.errorCode}: ${e.reason}` : String(e);
      setError(msg);
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [identity, viewAs]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <section
      className="role-dashboard"
      data-testid="role-dashboard"
      data-role={data?.role ?? me.role}
      aria-label="Role dashboard"
    >
      <header className="role-dashboard__header">
        <div>
          <h2 className="role-dashboard__title">
            Dashboard · {roleLabel((data?.role ?? me.role) as DashboardRole)}
          </h2>
          <p className="role-dashboard__subtitle subtle-note">
            Read-only operations summary. Counts come from the active
            work queue and notes pipeline; no clinical text is shown
            here.
          </p>
        </div>
        <div className="role-dashboard__actions">
          {canSwitch && (
            <label className="role-dashboard__view-as">
              <span className="role-dashboard__view-as-label">View as</span>
              <select
                data-testid="dashboard-view-as"
                value={viewAs}
                onChange={(e) => setViewAs(e.target.value as ViewAs)}
              >
                <option value="me">My role ({roleLabel(me.role as DashboardRole)})</option>
                {ROLE_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </label>
          )}
          <button
            type="button"
            className="btn"
            data-testid="dashboard-refresh"
            onClick={() => void load()}
            disabled={loading}
          >
            {loading ? "Refreshing…" : "Refresh"}
          </button>
        </div>
      </header>

      {error && (
        <div
          className="banner banner--error"
          role="alert"
          data-testid="dashboard-error"
        >
          {error}
        </div>
      )}

      {!error && !data && loading && (
        <div className="role-dashboard__empty" data-testid="dashboard-loading">
          Loading dashboard…
        </div>
      )}

      {data && <DashboardBody data={data} />}
    </section>
  );
}

async function fetchDashboardForRole(
  identity: string,
  role: DashboardRole
): Promise<DashboardSummary> {
  switch (role) {
    case "front_desk":
      return getFrontDeskDashboard(identity);
    case "technician":
      return getTechnicianDashboard(identity);
    case "clinician":
      return getDoctorDashboard(identity);
    case "reviewer":
      return getReviewerDashboard(identity);
    case "admin":
      return getAdminDashboard(identity);
  }
}

function DashboardBody({ data }: { data: DashboardSummary }) {
  switch (data.role) {
    case "front_desk":
      return <FrontDeskDashboardView data={data} />;
    case "technician":
      return <TechnicianDashboardView data={data} />;
    case "clinician":
      return <DoctorDashboardView data={data} />;
    case "reviewer":
      return <ReviewerDashboardView data={data} />;
    case "admin":
      return <AdminDashboardView data={data} />;
  }
}

// ---------- role-specific views -----------------------------------------

function FrontDeskDashboardView({ data }: { data: FrontDeskDashboard }) {
  const c = data.counts;
  return (
    <div className="role-dashboard__body" data-testid="dashboard-front-desk">
      <CardGrid>
        <CountCard
          testid="card-today-schedule"
          label="Today's Schedule"
          value={c.today_queue_count}
        />
        <CountCard
          testid="card-check-in-pending"
          label="Check-In Pending"
          value={c.check_in_pending_count}
        />
        <CountCard
          testid="card-ready-for-technician"
          label="Ready for Technician"
          value={c.ready_for_workup_count}
        />
        <CountCard
          testid="card-checkout"
          label="Checkout"
          value={c.checkout_pending_count}
        />
        <CountCard
          testid="card-follow-up"
          label="Follow-Up"
          value={c.follow_up_needed_count}
        />
      </CardGrid>
      <SectionHeader>Recent &amp; Due Items</SectionHeader>
      <QueueItemList
        items={data.recent_or_due_items}
        emptyText="Nothing recent or due in the front-desk lane."
        testid="front-desk-recent"
      />
      <p
        className="role-dashboard__note subtle-note"
        data-testid="front-desk-internal-note"
      >
        Internal notes and patient messaging are not shown on the
        dashboard. Use the Encounters workspace for clinical detail.
      </p>
    </div>
  );
}

function TechnicianDashboardView({ data }: { data: TechnicianDashboard }) {
  const c = data.counts;
  return (
    <div className="role-dashboard__body" data-testid="dashboard-technician">
      <CardGrid>
        <CountCard
          testid="card-workup-queue"
          label="Workup Queue"
          value={c.workup_pending_count}
        />
        <CountCard
          testid="card-imaging-needed"
          label="Imaging Needed"
          value={c.imaging_needed_count}
        />
        <CountCard
          testid="card-dilation"
          label="Dilation"
          value={c.dilation_pending_count}
        />
        <CountCard
          testid="card-testing"
          label="Testing (VA / IOP / Refraction)"
          value={c.testing_pending_count}
        />
        <CountCard
          testid="card-ready-for-doctor"
          label="Ready for Doctor"
          value={c.ready_for_doctor_count}
        />
      </CardGrid>
      <SectionHeader>My Queue</SectionHeader>
      <QueueItemList
        items={data.assigned_items}
        emptyText="No technician items assigned to you right now."
        testid="technician-queue"
      />
    </div>
  );
}

function DoctorDashboardView({ data }: { data: DoctorDashboard }) {
  const c = data.counts;
  return (
    <div className="role-dashboard__body" data-testid="dashboard-doctor">
      <CardGrid>
        <CountCard
          testid="card-ready-for-md"
          label="Ready for MD"
          value={c.ready_for_doctor_count}
        />
        <CountCard
          testid="card-pre-visit-briefs"
          label="Pre-Visit Briefs"
          value={c.documentation_in_progress_count}
        />
        <CountCard
          testid="card-imaging-ready"
          label="Imaging Ready for Review"
          value={c.imaging_ready_for_review_count}
        />
        <CountCard
          testid="card-sign-off"
          label="Sign-Off Queue"
          value={c.notes_ready_for_signoff_count}
        />
        <CountCard
          testid="card-high-priority"
          label="High-Priority Clinical Items"
          value={c.high_priority_items_count}
          tone={c.high_priority_items_count > 0 ? "warn" : "default"}
        />
      </CardGrid>
      <SectionHeader>My Encounters</SectionHeader>
      <QueueItemList
        items={data.assigned_provider_items}
        emptyText="No encounters waiting on you right now."
        testid="doctor-queue"
      />
    </div>
  );
}

function ReviewerDashboardView({ data }: { data: ReviewerDashboard }) {
  const c = data.counts;
  return (
    <div className="role-dashboard__body" data-testid="dashboard-reviewer">
      <CardGrid>
        <CountCard
          testid="card-notes-awaiting"
          label="Notes Awaiting Review"
          value={c.notes_awaiting_review_count}
        />
        <CountCard
          testid="card-diagram-proposals"
          label="Diagram Proposal Review"
          value={c.diagram_proposals_review_count}
        />
        <CountCard
          testid="card-ai-draft"
          label="AI Draft Review"
          value={c.ai_draft_review_count}
        />
        <CountCard
          testid="card-audit-exceptions"
          label="Audit Exceptions"
          value={c.audit_exceptions_count}
          tone={c.audit_exceptions_count > 0 ? "warn" : "default"}
        />
        <CountCard
          testid="card-blocked"
          label="Blocked Items"
          value={c.blocked_items_count}
          tone={c.blocked_items_count > 0 ? "warn" : "default"}
        />
      </CardGrid>
      <SectionHeader>Items Needing Review</SectionHeader>
      <QueueItemList
        items={data.review_needed_items}
        emptyText="Review queue is clear."
        testid="reviewer-queue"
      />
    </div>
  );
}

function AdminDashboardView({ data }: { data: AdminDashboard }) {
  const c = data.counts;
  return (
    <div className="role-dashboard__body" data-testid="dashboard-admin">
      <CardGrid>
        <CountCard
          testid="card-open-queue"
          label="Open Queue Items"
          value={c.total_open_queue_items}
        />
        <CountCard
          testid="card-overdue"
          label="Overdue Items"
          value={c.overdue_queue_items}
          tone={c.overdue_queue_items > 0 ? "warn" : "default"}
        />
        <CountCard
          testid="card-unsigned-notes"
          label="Unsigned Notes"
          value={c.unsigned_notes_count}
        />
        <CountCard
          testid="card-locations-active"
          label="Active Locations"
          value={data.location_summary.active_count}
        />
        <CountCard
          testid="card-providers-total"
          label="Providers"
          value={data.provider_summary.total_count}
        />
      </CardGrid>

      <SectionHeader>Queue Aging — by Status</SectionHeader>
      <BreakdownTable
        rows={data.work_queue_by_status}
        labelHeader="Status"
        testid="admin-by-status"
      />

      <SectionHeader>Provider Load — by Queue Type</SectionHeader>
      <BreakdownTable
        rows={data.work_queue_by_queue_type}
        labelHeader="Queue type"
        testid="admin-by-queue-type"
      />

      <SectionHeader>By Priority</SectionHeader>
      <BreakdownTable
        rows={data.work_queue_by_priority}
        labelHeader="Priority"
        testid="admin-by-priority"
      />

      <SectionHeader>By Assigned Role</SectionHeader>
      <BreakdownTable
        rows={data.work_queue_by_role}
        labelHeader="Role"
        testid="admin-by-role"
      />

      <SectionHeader>Role Views — Configuration</SectionHeader>
      <BreakdownTable
        rows={data.role_view_presets_summary}
        labelHeader="Role"
        testid="admin-role-views"
        emptyText="No role view presets configured yet."
      />
    </div>
  );
}

// ---------- shared primitives ------------------------------------------

function CardGrid({ children }: { children: React.ReactNode }) {
  return <div className="role-dashboard__cards">{children}</div>;
}

function CountCard({
  label,
  value,
  testid,
  tone = "default",
}: {
  label: string;
  value: number;
  testid: string;
  tone?: "default" | "warn";
}) {
  return (
    <div
      className={
        "role-dashboard__card" +
        (tone === "warn" ? " role-dashboard__card--warn" : "")
      }
      data-testid={testid}
    >
      <div className="role-dashboard__card-label">{label}</div>
      <div className="role-dashboard__card-value">{value}</div>
    </div>
  );
}

function SectionHeader({ children }: { children: React.ReactNode }) {
  return <h3 className="role-dashboard__section">{children}</h3>;
}

function QueueItemList({
  items,
  emptyText,
  testid,
}: {
  items: DashboardQueueItemCompact[];
  emptyText: string;
  testid: string;
}) {
  if (!items.length) {
    return (
      <p
        className="role-dashboard__empty"
        data-testid={`${testid}-empty`}
      >
        {emptyText}
      </p>
    );
  }
  return (
    <ul
      className="role-dashboard__queue"
      data-testid={testid}
    >
      {items.map((it) => (
        <QueueItemRow key={it.id} item={it} />
      ))}
    </ul>
  );
}

function QueueItemRow({ item }: { item: DashboardQueueItemCompact }) {
  return (
    <li className="role-dashboard__queue-item">
      <span className="role-dashboard__queue-type">
        {item.queue_type.replace(/_/g, " ")}
      </span>
      <span
        className={
          "role-dashboard__pill role-dashboard__pill--priority-" + item.priority
        }
      >
        {item.priority}
      </span>
      <span
        className={
          "role-dashboard__pill role-dashboard__pill--status-" + item.status
        }
      >
        {item.status}
      </span>
      {item.due_at && (
        <span className="role-dashboard__due">
          Due {formatDue(item.due_at)}
        </span>
      )}
      <span className="role-dashboard__ids subtle-note">
        {item.encounter_id != null && <>encounter #{item.encounter_id}</>}
        {item.encounter_id != null && item.provider_id != null && " · "}
        {item.provider_id != null && <>provider #{item.provider_id}</>}
      </span>
    </li>
  );
}

function BreakdownTable({
  rows,
  labelHeader,
  testid,
  emptyText = "No data.",
}: {
  rows: Record<string, number>;
  labelHeader: string;
  testid: string;
  emptyText?: string;
}) {
  const entries = useMemo(
    () =>
      Object.entries(rows).sort(
        (a, b) => b[1] - a[1] || a[0].localeCompare(b[0])
      ),
    [rows]
  );
  if (!entries.length) {
    return (
      <p
        className="role-dashboard__empty"
        data-testid={`${testid}-empty`}
      >
        {emptyText}
      </p>
    );
  }
  return (
    <table
      className="role-dashboard__table"
      data-testid={testid}
    >
      <thead>
        <tr>
          <th>{labelHeader}</th>
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
  );
}

function formatDue(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString();
}
