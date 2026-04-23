# Phase B — Admin Dashboard and Operational Metrics

## 1. Problem solved
Practice administrators and clinician leads cannot answer basic operational questions about ChartNav usage without opening the database: how many encounters were signed today, what is the median time from transcript ingest to signature, how many missing-flag items are aging, and how many reminders are overdue. The current app exposes only a basic KPI pane on the landing route; there is no day-level trend visibility and no place to confirm pilot exit criteria are being met. This blocks the pilot-review cadence (30/60/90) and reduces buyer confidence during demos.

This spec adds an `/admin/dashboard` surface with six KPI cards and a 14-day trend panel, sourced from existing tables — no new storage, pure read path.

## 2. Current state (honest)
- `frontend/src/routes/Dashboard.tsx` renders a small KPI strip (today's encounters, pending flags) from `/encounters/summary`. It does not include trend lines, sign-to-export lag, or reminder-overdue counts.
- `backend/app/routers/encounters.py` exposes `GET /encounters/summary` returning only counts for today; it does not aggregate over a rolling window.
- `workflow_events` is populated with transitions (`created`, `draft_ready`, `pre_sign_checkpoint`, `signed`, `exported`) per `backend/app/services/audit/events.py`. All five transitions carry `created_at` — the data required for lag calculation is present.
- RBAC enforcement lives in `backend/app/security/deps.py` with role enum `{admin, clinician, reviewer, front_desk}`. Front-desk is code-only today.
- Axe-AA release gate is wired in the Playwright run; any new surface must pass.

## 3. Required state
- `/admin/dashboard` route visible to `admin` and clinician-leads (a clinician with the `is_lead` attribute). Reviewer, general clinician, and front_desk see a 403-equivalent empty state with a "not available for your role" message — no cross-role leakage.
- Six KPI cards:
  1. Encounters signed today
  2. Encounters signed in the last 7 days
  3. Median sign-to-export lag (minutes, last 7 days)
  4. Missing-flag open count (all active)
  5. Missing-flag resolution rate (resolved / surfaced, last 14 days, percent)
  6. Reminders overdue (status != complete && due_at < now())
- 14-day trend panel rendered as two side-by-side sparklines:
  - Signed notes per day
  - Missing-flag resolution rate per day
- All values derived from existing tables. No new persistent storage.

## 4. Acceptance criteria (testable)
- `backend/tests/test_admin_dashboard.py` covers:
  - Role-gating: `admin` 200, `clinician` without `is_lead` 403, `reviewer` 403, `front_desk` 403.
  - Org scoping: KPIs exclude other organizations' rows.
  - Empty-state: zero encounters → structured zeros, not nulls.
  - Trend shape: `GET /admin/dashboard/trend?days=14` returns an array of exactly 14 daily buckets, oldest first.
- API contract:
  - `GET /admin/dashboard/summary` → `200 {encounters_signed_today, encounters_signed_7d, median_sign_to_export_minutes_7d, missing_flags_open, missing_flag_resolution_rate_14d, reminders_overdue}`
  - `GET /admin/dashboard/trend?days=14` → `200 {series: [{date, encounters_signed, missing_flag_resolution_rate}]}`
- Playwright: `e2e/admin_dashboard.spec.ts` — log in as admin, assert six cards render with `data-testid="kpi-card-<slug>"`, sparkline container `data-testid="trend-sparklines"` present, Axe-AA pass.
- Performance budget: both endpoints P95 < 300 ms on a 10k-encounter seeded DB.

## 5. Codex implementation scope
Create:
- `backend/app/services/analytics/dashboard_queries.py` — SQL aggregation functions; all pure SELECT against `encounters`, `note_versions`, `reminders`, `workflow_events`.
- `backend/app/routers/admin_dashboard.py` — two GET endpoints above.
- `frontend/src/routes/admin/Dashboard.tsx` — the page.
- `frontend/src/components/admin/KpiCard.tsx`, `frontend/src/components/admin/TrendSparkline.tsx`.
- Nav entry in `frontend/src/components/layout/AdminNav.tsx` under "Operations."

Modify:
- `backend/app/main.py` — register the new router.
- `backend/app/security/deps.py` — add `require_admin_or_clinician_lead` dependency if not present.
- `frontend/src/router.tsx` — register `/admin/dashboard`.

Sketch — median sign-to-export lag:
```sql
WITH events AS (
  SELECT encounter_id,
         MAX(created_at) FILTER (WHERE event_type='signed') AS signed_at,
         MAX(created_at) FILTER (WHERE event_type='exported') AS exported_at
  FROM workflow_events
  WHERE organization_id = :org_id AND created_at > now() - interval '7 days'
  GROUP BY encounter_id
)
SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY
  EXTRACT(EPOCH FROM (exported_at - signed_at))/60)
FROM events WHERE signed_at IS NOT NULL AND exported_at IS NOT NULL;
```

## 6. Out of scope / process only
- Predictive analytics (forecasting sign volume, flag-resolution trending beyond a drawn line).
- Revenue forecasting or CPT-based financial summaries.
- Cohort analysis or provider-level comparison (deferred to Phase C operational analytics).
- Exportable PDF/CSV of the dashboard (if needed, operator screenshots the page for pilot reviews).
- Real-time websocket push; endpoints are polled on an interval.

## 7. Demoable now vs later
- Demoable on ship: full `/admin/dashboard` with six KPIs + 14-day trend lines on seeded data, screen-recorded for the sales deck.
- Demoable only with real pilot traffic: meaningful slopes on the trend lines. On demo data, disclose that trends are seeded examples.
- Not demoable: per-clinician ranking, revenue-linked metrics, predictive alerts.

## 8. Dependencies
- Seed script (`scripts/seed_demo.py`, tracked in the Demo Environment spec) must produce at least 14 days of encounter history for trend lines to render honestly.
- Reminders spec's opt-out and status model does not block this dashboard; reminders-overdue uses only today's table.

## 9. Truth limitations
- The dashboard reflects only ChartNav-observed events. In `integrated_readthrough` mode, encounters written directly in the partner EHR do not appear.
- "Median sign-to-export lag" reflects ChartNav-mediated exports only; if a clinician copies content out of ChartNav manually, that path is not measured.
- The dashboard is operational, not clinical: it does not score documentation quality, coding accuracy, or billing outcomes.

## 10. Risks if incomplete
- Without day-level metrics, pilot exit conversations become anecdotal. Exit-criteria reviews (the 30/60/90 reviews) need objective numbers to land a renewal or convert to paid.
- Buyers consistently ask "can you show me usage?" in diligence calls; absence of this surface is read as product immaturity.
- Admin power-users are the internal champions; unmet reporting needs become the most common Phase C complaint logged in pilot debriefs.
