import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  API_URL,
  ALLOWED_STATUSES,
  ApiError,
  Encounter,
  EncounterFilters,
  EVENT_TYPES,
  Me,
  NewEncounterInput,
  Patient,
  Role,
  WorkflowEvent,
  allowedNextStatuses,
  canCreateEncounter,
  canCreateEvent,
  canReadClinicalContent,
  bridgeEncounter,
  createEncounter,
  createEncounterEvent,
  encounterIsNative,
  encounterSourceLabel,
  getEncounter,
  refreshBridgedEncounter,
  getEncounterEvents,
  getMe,
  isAdmin,
  listEncountersPage,
  listLocations,
  listPatients,
  updateEncounterStatus,
} from "./api";
import { AdminPanel } from "./AdminPanel";
import { NoteWorkspace } from "./NoteWorkspace";
import { SEEDED_IDENTITIES, loadIdentity, saveIdentity } from "./identity";
import {
  Density,
  ThemeMode,
  applyPreferences,
  loadDensity,
  loadTheme,
  saveDensity,
  saveTheme,
} from "./preferences";
import { PreferenceControls } from "./PreferenceControls";
import {
  CommandAction,
  CommandPalette,
  useCommandPaletteShortcut,
} from "./CommandPalette";
import { Timeline } from "./Timeline";
import { DayView } from "./DayView";
import { Calendar, addMonths, startOfMonth } from "./Calendar";
import { RemindersPanel } from "./RemindersPanel";
import { Reminder, listReminders } from "./api";
import { ClinicalCodingPanel } from "./features/clinical-coding/ClinicalCodingPanel";
import { WallDisplay } from "./WallDisplay";
import { EncounterSlip } from "./EncounterSlip";
// ROI wave 1 — operational queue + triage cards + role split.
import { QueuePresets } from "./QueuePresets";
import { ReadinessBadge } from "./ReadinessBadge";
import {
  QueuePreset,
  QUEUE_PRESETS,
  deriveReadiness,
  presetsForAudience,
} from "./readiness";

type Banner =
  | { kind: "ok"; msg: string }
  | { kind: "error"; msg: string }
  | { kind: "info"; msg: string }
  | null;

export default function App() {
  const [identity, setIdentity] = useState<string>(() => loadIdentity());
  const [me, setMe] = useState<Me | null>(null);
  const [meLoading, setMeLoading] = useState(true);
  const [meError, setMeError] = useState<string | null>(null);

  const [filters, setFilters] = useState<EncounterFilters>({});
  const [encounters, setEncounters] = useState<Encounter[]>([]);
  const [listError, setListError] = useState<string | null>(null);
  const [listLoading, setListLoading] = useState(false);

  const [selectedId, setSelectedId] = useState<number | string | null>(null);
  const [encounter, setEncounter] = useState<Encounter | null>(null);
  const [events, setEvents] = useState<WorkflowEvent[]>([]);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  const [banner, setBanner] = useState<Banner>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [showAdmin, setShowAdmin] = useState(false);

  // Pagination
  const PAGE_SIZE = 25;
  const [offset, setOffset] = useState(0);
  const [total, setTotal] = useState(0);

  // Phase 38 — visual prefs + command palette + day view + bulk + wall + slip.
  const [density, setDensity] = useState<Density>(() => loadDensity());
  const [theme, setTheme] = useState<ThemeMode>(() => loadTheme());
  useEffect(() => { applyPreferences(density, theme); }, [density, theme]);

  const [cmdkOpen, setCmdkOpen] = useState(false);
  useCommandPaletteShortcut(() => setCmdkOpen(true));

  const [view, setView] = useState<"list" | "day" | "month" | "coding">(() => {
    try {
      const v = localStorage.getItem("chartnav.view");
      return v === "day" || v === "month" || v === "coding" ? v : "list";
    } catch { return "list"; }
  });
  useEffect(() => { try { localStorage.setItem("chartnav.view", view); } catch {} }, [view]);
  const [dayDate, setDayDate] = useState<Date>(() => new Date());

  // Phase 63 — Calendar / Reminders state.
  const [monthStart, setMonthStart] = useState<Date>(() => startOfMonth(new Date()));
  const [reminders, setReminders] = useState<Reminder[]>([]);
  const [remindersReloadTick, setRemindersReloadTick] = useState(0);
  useEffect(() => {
    let cancelled = false;
    // Fetch reminders across statuses so the calendar can show
    // both pending and completed chips on the correct day.
    listReminders(identity, { status: "pending" as any })
      .then(async (pending) => {
        const completed = await listReminders(identity, { status: "completed" as any })
          .catch(() => [] as Reminder[]);
        if (!cancelled) setReminders([...pending, ...completed]);
      })
      .catch(() => { if (!cancelled) setReminders([]); });
    return () => { cancelled = true; };
  }, [identity, remindersReloadTick]);
  const reloadReminders = useCallback(
    () => setRemindersReloadTick((t) => t + 1),
    [],
  );
  const onSelectPatient = useCallback((patientIdentifier: string) => {
    // Find the first (newest) encounter for this patient in the
    // currently-loaded page; fall back to switching to list.
    const match = encounters.find(
      (e) => e.patient_identifier === patientIdentifier,
    );
    if (match) {
      setView("list");
      setSelectedId(match.id);
    } else {
      setView("list");
      setFilters((f) => ({ ...f, q: patientIdentifier }));
    }
  }, [encounters]);
  const [showWall, setShowWall] = useState(false);
  const [showSlipFor, setShowSlipFor] = useState<Encounter | null>(null);
  const [bulkSelected, setBulkSelected] = useState<Set<string>>(new Set());

  // ROI wave 1 — queue preset state. Applied as a client-side
  // predicate on top of the existing filter/pagination. Default is
  // "all" so nothing changes for existing flows until the user opts in.
  const [queuePreset, setQueuePreset] = useState<QueuePreset>("all");

  // Shared locations cache, used by the wall display, encounter slip,
  // and the create-encounter modal. Loads once per identity; the
  // modal still provides its own loading indicator for first paint.
  const [locationsCache, setLocationsCache] = useState<
    { id: number; organization_id: number; name: string; is_active: number | boolean; created_at: string }[]
  >([]);
  useEffect(() => {
    let cancelled = false;
    listLocations(identity)
      .then((rows) => { if (!cancelled) setLocationsCache(rows as any); })
      .catch(() => { if (!cancelled) setLocationsCache([]); });
    return () => { cancelled = true; };
  }, [identity]);

  // ROI wave 1 — item 8. Role-aware default experience:
  //   front_desk → day view + scheduling-oriented presets
  //   reviewer / clinician / admin → list view + clinical presets
  //
  // Only adjust on first `me` resolve so the user's later manual
  // switches are preserved. We persist the view per-identity so
  // returning doctors keep their last choice.
  const roleInitRef = useRef<string | null>(null);
  useEffect(() => {
    if (!me) return;
    if (roleInitRef.current === me.email) return;
    roleInitRef.current = me.email;
    // Only force a default when the user hasn't already chosen.
    let stored: string | null = null;
    try { stored = localStorage.getItem(`chartnav.view.${me.email}`); } catch {}
    if (!stored) {
      if (me.role === "front_desk") setView("day");
      else setView("list");
    }
    let storedPreset: string | null = null;
    try { storedPreset = localStorage.getItem(`chartnav.preset.${me.email}`); } catch {}
    if (!storedPreset) {
      // Only force an opinionated default for front desk — they
      // benefit from seeing arriving patients first. Clinical roles
      // keep "all" so existing flows (and vitest expectations) stay
      // unchanged.
      if (me.role === "front_desk") setQueuePreset("arriving_soon");
      else setQueuePreset("all");
    } else if (QUEUE_PRESETS.some((p) => p.key === storedPreset)) {
      setQueuePreset(storedPreset as QueuePreset);
    }
  }, [me]);
  // Persist per-user choices so role-driven defaults don't overwrite
  // an explicit user preference on next login.
  useEffect(() => {
    if (!me) return;
    try { localStorage.setItem(`chartnav.view.${me.email}`, view); } catch {}
  }, [view, me]);
  useEffect(() => {
    if (!me) return;
    try { localStorage.setItem(`chartnav.preset.${me.email}`, queuePreset); } catch {}
  }, [queuePreset, me]);

  // Audience driving the QueuePresets surface.
  const presetAudience: "all" | "front_desk" | "clinical" = useMemo(() => {
    if (!me) return "all";
    if (me.role === "front_desk") return "front_desk";
    return "clinical";
  }, [me]);

  // Apply preset + compute per-preset counts against the current
  // loaded page. Counts are a live badge, not a server query.
  const nowMs = useMemo(() => Date.now(), [encounters]);
  const presetCounts = useMemo(() => {
    const counts: Partial<Record<QueuePreset, number>> = {};
    for (const p of QUEUE_PRESETS) {
      counts[p.key] = encounters.filter((e) => p.match(e, nowMs)).length;
    }
    return counts;
  }, [encounters, nowMs]);
  const visibleEncounters = useMemo(() => {
    const preset = QUEUE_PRESETS.find((p) => p.key === queuePreset);
    if (!preset) return encounters;
    return encounters.filter((e) => preset.match(e, nowMs));
  }, [encounters, queuePreset, nowMs]);

  // ---- loaders ---------------------------------------------------------

  const refreshMe = useCallback(async () => {
    setMeLoading(true);
    setMeError(null);
    try {
      setMe(await getMe(identity));
    } catch (e) {
      setMe(null);
      setMeError(friendly(e));
    } finally {
      setMeLoading(false);
    }
  }, [identity]);

  const refreshList = useCallback(async () => {
    setListLoading(true);
    setListError(null);
    try {
      const { items, total: t } = await listEncountersPage(
        identity,
        filters,
        { limit: PAGE_SIZE, offset }
      );
      setEncounters(items);
      setTotal(t);
      if (selectedId && !items.some((r) => r.id === selectedId)) {
        setSelectedId(null);
        setEncounter(null);
        setEvents([]);
      }
    } catch (e) {
      setEncounters([]);
      setListError(friendly(e));
    } finally {
      setListLoading(false);
    }
  }, [identity, filters, selectedId, offset]);

  // Track the id currently rendered in the detail pane without
  // tying `refreshDetail` to the `encounter` state value — depending
  // on `encounter` would cause an infinite re-fetch loop.
  const loadedEncounterIdRef = useRef<string | null>(null);

  const refreshDetail = useCallback(
    async (id: number | string | null) => {
      if (id == null) {
        loadedEncounterIdRef.current = null;
        setEncounter(null);
        setEvents([]);
        setDetailError(null);
        return;
      }
      // Only show the "Loading…" fallback on the FIRST load for this
      // id; subsequent re-fetches (e.g. after a bridged-refresh or
      // status transition) keep the detail pane mounted so child
      // components that hold UI state (banner messages, draft edits)
      // don't get unmounted mid-flow.
      const isInitial = loadedEncounterIdRef.current !== String(id);
      if (isInitial) setDetailLoading(true);
      setDetailError(null);
      try {
        const [enc, evs] = await Promise.all([
          getEncounter(identity, id),
          getEncounterEvents(identity, id),
        ]);
        setEncounter(enc);
        setEvents(evs);
        loadedEncounterIdRef.current = String(id);
      } catch (e) {
        loadedEncounterIdRef.current = null;
        setEncounter(null);
        setEvents([]);
        setDetailError(friendly(e));
      } finally {
        if (isInitial) setDetailLoading(false);
      }
    },
    [identity]
  );

  useEffect(() => {
    refreshMe();
  }, [refreshMe]);
  useEffect(() => {
    refreshList();
  }, [refreshList]);
  useEffect(() => {
    refreshDetail(selectedId);
  }, [selectedId, refreshDetail]);

  // ---- handlers --------------------------------------------------------

  const onIdentityChange = (email: string) => {
    if (email === identity) return;
    setIdentity(email);
    saveIdentity(email);
    setSelectedId(null);
    setEncounter(null);
    setEvents([]);
    setShowCreate(false);
    setShowAdmin(false);
    setOffset(0);
    setBanner({ kind: "info", msg: `Identity switched to ${email}` });
  };

  const onTransition = async (status: string) => {
    if (!encounter) return;
    setBanner(null);
    try {
      const updated = await updateEncounterStatus(identity, encounter.id, status);
      setEncounter(updated);
      setEvents(await getEncounterEvents(identity, encounter.id));
      await refreshList();
      setBanner({ kind: "ok", msg: `Status → ${status}` });
    } catch (e) {
      setBanner({ kind: "error", msg: friendly(e) });
    }
  };

  const onAddEvent = async (type: string, raw: string) => {
    if (!encounter) return;
    setBanner(null);
    let data: unknown = undefined;
    const trimmed = raw.trim();
    if (trimmed) {
      try {
        data = JSON.parse(trimmed);
      } catch {
        data = trimmed;
      }
    }
    try {
      await createEncounterEvent(identity, encounter.id, {
        event_type: type,
        event_data: data,
      });
      setEvents(await getEncounterEvents(identity, encounter.id));
      setBanner({ kind: "ok", msg: `Event '${type}' added` });
    } catch (e) {
      setBanner({ kind: "error", msg: friendly(e) });
    }
  };

  const onCreateEncounter = async (input: NewEncounterInput) => {
    setBanner(null);
    const created = await createEncounter(identity, input);
    await refreshList();
    setSelectedId(created.id);
    setShowCreate(false);
    setBanner({
      kind: "ok",
      msg: `Encounter #${created.id} created (${created.patient_identifier})`,
    });
  };

  // Bulk actions (B4) — fan out a single status across selected rows.
  // Runs sequentially to keep audit/telemetry messages legible; the
  // API already handles concurrent writes but the UI feels steadier
  // this way.
  const onBulkTransition = async (status: string) => {
    const ids = Array.from(bulkSelected);
    if (!ids.length) return;
    setBanner({ kind: "info", msg: `Applying ${status} to ${ids.length} encounter${ids.length === 1 ? "" : "s"}…` });
    let ok = 0; let err = 0;
    for (const id of ids) {
      try {
        await updateEncounterStatus(identity, isNaN(Number(id)) ? id : Number(id), status);
        ok += 1;
      } catch { err += 1; }
    }
    setBulkSelected(new Set());
    await refreshList();
    if (selectedId != null) await refreshDetail(selectedId);
    setBanner({
      kind: err === 0 ? "ok" : "error",
      msg: `Bulk ${status}: ${ok} ok${err ? `, ${err} failed` : ""}`,
    });
  };

  // ---- render ----------------------------------------------------------

  const canCreate = me ? canCreateEncounter(me.role) : false;
  const canAdmin = me ? isAdmin(me.role) : false;
  const canClinical = me ? canReadClinicalContent(me.role) : true;

  // Command palette actions. Must be recomputed any time the user's
  // role, the selected encounter, or feature flags change; that keeps
  // the surface honest ("Sign note" only appears when signing would
  // actually work).
  const cmdkActions: CommandAction[] = useMemo(() => {
    const xs: CommandAction[] = [];
    xs.push({
      id: "nav-list",
      label: "Switch to list view",
      section: "Navigation",
      kbd: "L",
      when: view !== "list",
      run: () => setView("list"),
    });
    xs.push({
      id: "nav-day",
      label: "Switch to day view (today's board)",
      section: "Navigation",
      kbd: "D",
      keywords: "schedule calendar today",
      when: view !== "day",
      run: () => setView("day"),
    });
    xs.push({
      id: "nav-wall",
      label: "Open wall display (rooms & waiting)",
      section: "Navigation",
      keywords: "waiting rooms board big screen",
      when: !showWall,
      run: () => setShowWall(true),
    });
    if (canCreate) {
      xs.push({
        id: "new-encounter",
        label: "New encounter",
        section: "Encounters",
        kbd: "N",
        when: !showCreate,
        run: () => setShowCreate(true),
      });
    }
    if (canAdmin) {
      xs.push({
        id: "open-admin",
        label: "Open admin panel",
        section: "Navigation",
        when: !showAdmin,
        run: () => setShowAdmin(true),
      });
    }
    if (encounter) {
      xs.push({
        id: "print-slip",
        label: `Print encounter slip #${encounter.id}`,
        section: "Encounter",
        keywords: "slip print paper hand off",
        run: () => setShowSlipFor(encounter),
      });
      if (encounterIsNative(encounter) && me) {
        for (const next of allowedNextStatuses(me.role, encounter.status)) {
          xs.push({
            id: `trans-${next}`,
            label: `Move to ${next.replace(/_/g, " ")}`,
            section: "Encounter",
            context: `from ${encounter.status}`,
            run: () => onTransition(next),
          });
        }
      }
    }
    xs.push({
      id: "pref-dark",
      label: "Switch to dark theme",
      section: "Preferences",
      when: theme !== "dark",
      run: () => setTheme("dark"),
    });
    xs.push({
      id: "pref-light",
      label: "Switch to light theme",
      section: "Preferences",
      when: theme !== "light",
      run: () => setTheme("light"),
    });
    xs.push({
      id: "pref-system",
      label: "Follow system theme",
      section: "Preferences",
      when: theme !== "system",
      run: () => setTheme("system"),
    });
    xs.push({
      id: "pref-comfortable",
      label: "Density · comfortable",
      section: "Preferences",
      when: density !== "comfortable",
      run: () => setDensity("comfortable"),
    });
    xs.push({
      id: "pref-default",
      label: "Density · default",
      section: "Preferences",
      when: density !== "default",
      run: () => setDensity("default"),
    });
    xs.push({
      id: "pref-compact",
      label: "Density · compact",
      section: "Preferences",
      when: density !== "compact",
      run: () => setDensity("compact"),
    });
    return xs;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [view, showWall, showCreate, showAdmin, canCreate, canAdmin, encounter, me, density, theme]);

  return (
    <>
      <header className="app-header">
        <div className="brand">
          <img
            className="brand__logo"
            src="/brand/chartnav-logo.svg"
            alt="ChartNav"
            width="140"
            height="32"
          />
          <span className="sub">Workflow</span>
        </div>
        <div className="header-meta">
          <IdentityBadge me={me} meError={meError} meLoading={meLoading} />
          {me && (
            <span
              className="role-chip"
              data-role={me.role}
              data-testid="role-chip"
              title={
                me.role === "front_desk"
                  ? "Front desk workspace — scheduling oriented"
                  : me.role === "reviewer"
                  ? "Reviewer workspace — chart review"
                  : me.role === "clinician"
                  ? "Clinician workspace — charting"
                  : "Admin workspace"
              }
            >
              {me.role === "front_desk"
                ? "Front desk"
                : me.role.charAt(0).toUpperCase() + me.role.slice(1)}
            </span>
          )}
          <span className="chip">API {API_URL}</span>
          <div
            className="pref-picker"
            role="tablist"
            aria-label="View"
            data-testid="view-toggle"
          >
            <button
              type="button"
              className="pref-picker__btn"
              role="tab"
              aria-pressed={view === "list"}
              data-testid="view-list"
              onClick={() => setView("list")}
            >
              List
            </button>
            <button
              type="button"
              className="pref-picker__btn"
              role="tab"
              aria-pressed={view === "day"}
              data-testid="view-day"
              onClick={() => setView("day")}
            >
              Day
            </button>
            <button
              type="button"
              className="pref-picker__btn"
              role="tab"
              aria-pressed={view === "month"}
              data-testid="view-month"
              onClick={() => setView("month")}
            >
              Month
            </button>
            <button
              type="button"
              className="pref-picker__btn"
              role="tab"
              aria-pressed={view === "coding"}
              data-testid="view-coding"
              onClick={() => setView("coding")}
              title="Clinical Coding Intelligence"
            >
              Coding
            </button>
          </div>
          <button
            type="button"
            className="btn"
            onClick={() => setShowWall(true)}
            data-testid="open-wall"
            title="Open wall display"
          >
            Wall
          </button>
          <button
            type="button"
            className="btn btn--muted"
            onClick={() => setCmdkOpen(true)}
            title="Command palette · ⌘K"
            data-testid="open-cmdk"
          >
            ⌘K
          </button>
          {canCreate && (
            <button
              className="btn btn--primary"
              onClick={() => setShowCreate(true)}
              data-testid="open-create-encounter"
            >
              + New encounter
            </button>
          )}
          {canAdmin && (
            <button
              className="btn"
              onClick={() => setShowAdmin(true)}
              data-testid="open-admin-panel"
            >
              Admin
            </button>
          )}
          <PreferenceControls
            density={density}
            theme={theme}
            onDensity={(d) => { setDensity(d); saveDensity(d); }}
            onTheme={(t) => { setTheme(t); saveTheme(t); }}
          />
          <IdentityPicker value={identity} onChange={onIdentityChange} />
        </div>
      </header>

      <div className="layout">
        <aside
          className="layout__list"
          data-role={
            me?.role === "front_desk"
              ? "front_desk"
              : me?.role === "reviewer" || me?.role === "clinician"
              ? "clinical"
              : undefined
          }
        >
          <QueuePresets
            presets={presetsForAudience(presetAudience)}
            value={queuePreset}
            counts={presetCounts}
            onChange={setQueuePreset}
          />
          <FilterBar
            value={filters}
            onChange={(next) => {
              setFilters(next);
              setOffset(0);
            }}
          />
          {bulkSelected.size > 0 && (
            <div className="bulk-toolbar" data-testid="bulk-toolbar" role="toolbar" aria-label="Bulk actions">
              <span className="bulk-toolbar__count" data-testid="bulk-count">
                {bulkSelected.size} selected
              </span>
              <button
                className="btn"
                onClick={() => onBulkTransition("in_progress")}
                data-testid="bulk-in-progress"
                title="Check in / move to in_progress"
              >
                Check in
              </button>
              <button
                className="btn"
                onClick={() => onBulkTransition("completed")}
                data-testid="bulk-completed"
                title="Mark completed (only valid from review_needed)"
              >
                Complete
              </button>
              <button
                className="btn btn--muted"
                onClick={() => setBulkSelected(new Set())}
                data-testid="bulk-clear"
              >
                Clear
              </button>
            </div>
          )}
          <EncounterList
            rows={visibleEncounters}
            loading={listLoading}
            error={listError}
            selectedId={selectedId}
            onSelect={setSelectedId}
            bulkSelected={bulkSelected}
            onBulkToggle={(id) => {
              const key = String(id);
              setBulkSelected((prev) => {
                const next = new Set(prev);
                if (next.has(key)) next.delete(key);
                else next.add(key);
                return next;
              });
            }}
          />
          {total > PAGE_SIZE && (
            <div className="pagination" data-testid="pagination">
              <button
                className="btn"
                disabled={offset === 0}
                onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                data-testid="page-prev"
              >
                ← Prev
              </button>
              <span className="subtle-note" data-testid="page-status">
                {offset + 1}-{Math.min(offset + PAGE_SIZE, total)} of {total}
              </span>
              <button
                className="btn"
                disabled={offset + PAGE_SIZE >= total}
                onClick={() => setOffset(offset + PAGE_SIZE)}
                data-testid="page-next"
              >
                Next →
              </button>
            </div>
          )}
        </aside>

        <section className="layout__detail">
          {banner && (
            <div
              className={`banner banner--${banner.kind}`}
              role={banner.kind === "error" ? "alert" : "status"}
              data-testid={`banner-${banner.kind}`}
            >
              {banner.msg}
            </div>
          )}
          {view === "coding" ? (
            <ClinicalCodingPanel
              identity={identity}
              role={me?.role ?? "clinician"}
            />
          ) : view === "month" ? (
            <div className="month-view" data-testid="month-view">
              <Calendar
                monthStart={monthStart}
                encounters={encounters}
                reminders={reminders}
                onMonthPrev={() => setMonthStart((d) => addMonths(d, -1))}
                onMonthNext={() => setMonthStart((d) => addMonths(d, 1))}
                onMonthToday={() => setMonthStart(startOfMonth(new Date()))}
                onSelectEncounter={(id) => { setSelectedId(id); setView("list"); }}
                onSelectPatient={onSelectPatient}
              />
              <RemindersPanel
                identity={identity}
                onPatientSelect={onSelectPatient}
                onMutation={reloadReminders}
              />
            </div>
          ) : view === "day" ? (
            <DayView
              encounters={visibleEncounters}
              date={dayDate}
              onDateChange={setDayDate}
              onPick={(id) => { setSelectedId(id); setView("list"); }}
            />
          ) : selectedId == null ? (
            <div className="empty">
              Select an encounter from the list to see details, events, and allowed actions.
              {canCreate && (
                <>
                  {" "}
                  Or click <strong>+ New encounter</strong> above to create one.
                </>
              )}
            </div>
          ) : (
            <EncounterDetail
              loading={detailLoading}
              error={detailError}
              encounter={encounter}
              events={events}
              me={me}
              identity={identity}
              onTransition={onTransition}
              onAddEvent={onAddEvent}
              onRefreshDetail={() => refreshDetail(selectedId)}
              onPrintSlip={(e) => setShowSlipFor(e)}
            />
          )}
        </section>
      </div>

      {showCreate && me && (
        <CreateEncounterModal
          identity={identity}
          me={me}
          onCancel={() => setShowCreate(false)}
          onSubmit={onCreateEncounter}
        />
      )}
      {showAdmin && me && isAdmin(me.role) && (
        <AdminPanel
          identity={identity}
          me={me}
          onClose={() => setShowAdmin(false)}
        />
      )}

      <CommandPalette
        open={cmdkOpen}
        actions={cmdkActions}
        onClose={() => setCmdkOpen(false)}
      />

      {showWall && (
        <WallDisplay
          encounters={encounters}
          locations={locationsCache as any}
          onClose={() => setShowWall(false)}
        />
      )}

      {showSlipFor && (
        <EncounterSlip
          encounter={showSlipFor}
          location={
            locationsCache.find((l) => l.id === showSlipFor.location_id) as any ?? null
          }
          onClose={() => setShowSlipFor(null)}
        />
      )}

      <footer
        className="app-footer"
        role="contentinfo"
        data-testid="app-footer"
      >
        <span className="app-footer__brand">
          <strong>ChartNav</strong>
          <span aria-hidden="true"> · </span>
          <span>Clinical workflow platform</span>
        </span>
        <span
          className="app-footer__powered"
          data-testid="app-footer-arcg"
        >
          Powered by <strong>ARCG Systems</strong>
        </span>
      </footer>
    </>
  );
}

// ---------- subcomponents -------------------------------------------------

function IdentityBadge({
  me,
  meError,
  meLoading,
}: {
  me: Me | null;
  meError: string | null;
  meLoading: boolean;
}) {
  if (meLoading && !me)
    return (
      <span className="chip" data-testid="identity-loading">
        resolving identity…
      </span>
    );
  if (meError)
    return (
      <span
        className="chip"
        style={{ color: "var(--danger)" }}
        data-testid="identity-error"
      >
        auth: {meError}
      </span>
    );
  if (!me) return <span className="chip">—</span>;
  return (
    <span className="chip" data-testid="identity-badge">
      {me.email} · {me.role} · org {me.organization_id}
    </span>
  );
}

function IdentityPicker({
  value,
  onChange,
}: {
  value: string;
  onChange: (email: string) => void;
}) {
  const isSeeded = SEEDED_IDENTITIES.some((s) => s.email === value);
  const [custom, setCustom] = useState(isSeeded ? "" : value);
  const [mode, setMode] = useState<"seeded" | "custom">(
    isSeeded ? "seeded" : "custom"
  );
  return (
    <div className="identity-picker">
      <label className="subtle-note" htmlFor="dev-identity">
        identity
      </label>
      {mode === "seeded" ? (
        <select
          id="dev-identity"
          data-testid="identity-select"
          value={value}
          onChange={(e) => {
            if (e.target.value === "__custom__") {
              setMode("custom");
              return;
            }
            onChange(e.target.value);
          }}
        >
          {SEEDED_IDENTITIES.map((s) => (
            <option key={s.email} value={s.email}>
              {s.label} · {s.email}
            </option>
          ))}
          <option value="__custom__">Custom email…</option>
        </select>
      ) : (
        <>
          <input
            type="email"
            value={custom}
            placeholder="user@example.com"
            onChange={(e) => setCustom(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && custom.trim()) onChange(custom.trim());
            }}
          />
          <button
            className="btn"
            onClick={() => custom.trim() && onChange(custom.trim())}
          >
            use
          </button>
          <button className="btn btn--muted" onClick={() => setMode("seeded")}>
            seeded
          </button>
        </>
      )}
    </div>
  );
}

function FilterBar({
  value,
  onChange,
}: {
  value: EncounterFilters;
  onChange: (next: EncounterFilters) => void;
}) {
  const update = <K extends keyof EncounterFilters>(
    key: K,
    v: EncounterFilters[K] | undefined
  ) => {
    const next = { ...value };
    if (v === undefined || v === "" || (typeof v === "number" && Number.isNaN(v))) {
      delete (next as any)[key];
    } else {
      (next as any)[key] = v;
    }
    onChange(next);
  };

  return (
    <div className="filters">
      <label>
        Status
        <select
          data-testid="filter-status"
          value={value.status ?? ""}
          onChange={(e) => update("status", e.target.value || undefined)}
        >
          <option value="">Any</option>
          {ALLOWED_STATUSES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </label>
      <label>
        Provider
        <input
          type="text"
          data-testid="filter-provider"
          placeholder="Dr. Carter"
          value={value.provider_name ?? ""}
          onChange={(e) => update("provider_name", e.target.value || undefined)}
        />
      </label>
      <label>
        Location ID
        <input
          type="number"
          data-testid="filter-location"
          min={1}
          placeholder="—"
          value={value.location_id ?? ""}
          onChange={(e) => {
            const n = e.target.value ? parseInt(e.target.value, 10) : undefined;
            update("location_id", Number.isNaN(n) ? undefined : n);
          }}
        />
      </label>
      {Object.keys(value).length > 0 && (
        <button className="filter-clear" onClick={() => onChange({})}>
          clear
        </button>
      )}
    </div>
  );
}

function EncounterList({
  rows,
  loading,
  error,
  selectedId,
  onSelect,
  bulkSelected,
  onBulkToggle,
}: {
  rows: Encounter[];
  loading: boolean;
  error: string | null;
  selectedId: number | string | null;
  onSelect: (id: number | string) => void;
  bulkSelected?: Set<string>;
  onBulkToggle?: (id: number | string) => void;
}) {
  if (loading && rows.length === 0)
    return (
      <div className="empty" data-testid="list-loading">
        Loading…
      </div>
    );
  if (error)
    return (
      <div
        className="empty"
        style={{ color: "var(--danger)" }}
        data-testid="list-error"
      >
        {error}
      </div>
    );
  if (!rows.length)
    return (
      <div className="empty" data-testid="list-empty">
        No encounters match these filters.
      </div>
    );

  const now = Date.now();
  return (
    <div className="enc-list" data-testid="enc-list">
      {rows.map((e) => {
        const r = deriveReadiness(e, now);
        const activityIso =
          e.started_at ?? e.scheduled_at ?? e.created_at ?? null;
        return (
        <div
          key={e.id}
          className={"enc-card enc-row" + (selectedId === e.id ? " is-active" : "")}
          onClick={() => onSelect(e.id)}
          role="button"
          tabIndex={0}
          data-testid={`enc-row-${e.id}`}
          onKeyDown={(ev) => {
            if (ev.key === "Enter" || ev.key === " ") onSelect(e.id);
          }}
        >
          {onBulkToggle && (
            <input
              type="checkbox"
              className="enc-row__select enc-card__select"
              aria-label={`Select encounter ${e.id}`}
              data-testid={`enc-row-select-${e.id}`}
              checked={bulkSelected?.has(String(e.id)) ?? false}
              onClick={(ev) => ev.stopPropagation()}
              onChange={() => onBulkToggle(e.id)}
            />
          )}
          <div className="enc-card__body">
            <div className="enc-card__top">
              <span className="enc-row__pid enc-card__id">
                #{e.id} · {e.patient_identifier}
              </span>
              <span className="enc-row__name enc-card__name">
                {e.patient_name ?? "—"}
              </span>
            </div>
            <div className="enc-card__meta">
              <span className="enc-row__provider">{e.provider_name}</span>
              {e.location_id != null && <span>· Loc #{e.location_id}</span>}
              {e._source && e._source !== "chartnav" && (
                <span className="enc-card__src" title={`source=${e._source}`}>
                  · {String(e._source)}
                </span>
              )}
              {activityIso && (
                <span className="enc-card__age" title={activityIso}>
                  · {relativeAge(activityIso, now)}
                </span>
              )}
            </div>
          </div>
          <div className="enc-card__pills">
            <ReadinessBadge r={r} />
            <span className="status-pill" data-status={e.status}>
              {e.status.replace(/_/g, " ")}
            </span>
          </div>
        </div>
      );
      })}
    </div>
  );
}

function EncounterDetail({
  loading,
  error,
  encounter,
  events,
  me,
  identity,
  onTransition,
  onAddEvent,
  onRefreshDetail,
  onPrintSlip,
}: {
  loading: boolean;
  error: string | null;
  encounter: Encounter | null;
  events: WorkflowEvent[];
  me: Me | null;
  identity: string;
  onTransition: (status: string) => Promise<void> | void;
  onAddEvent: (type: string, data: string) => Promise<void> | void;
  onRefreshDetail: () => void;
  onPrintSlip?: (e: Encounter) => void;
}) {
  const [pendingStatus, setPendingStatus] = useState<string | null>(null);
  const [pendingEvent, setPendingEvent] = useState(false);

  if (loading) return <div className="empty">Loading…</div>;
  if (error)
    return (
      <div className="banner banner--error" role="alert">
        {error}
      </div>
    );
  if (!encounter) return null;

  const role: Role | null = me?.role ?? null;
  const nativeEncounter = encounterIsNative(encounter);
  // Status transitions are only meaningful when ChartNav owns the
  // row. Integrated-mode encounters live in the external EHR; the
  // backend returns `encounter_write_unsupported` when called.
  const nextStatuses =
    role && nativeEncounter ? allowedNextStatuses(role, encounter.status) : [];
  const eventAllowed = role ? canCreateEvent(role) : false;

  return (
    <div data-testid="encounter-detail">
      <div className="detail__head">
        <div>
          <h2>
            #{encounter.id} · {encounter.patient_name ?? encounter.patient_identifier}
          </h2>
          <div className="sub">
            {encounter.patient_identifier} · {encounter.provider_name}
          </div>
        </div>
        <div className="detail__head-right">
          <span
            className="status-pill"
            data-status={encounter.status}
            data-testid="detail-status"
          >
            {encounter.status.replace(/_/g, " ")}
          </span>
          <span
            className="source-chip"
            data-testid="detail-source-chip"
            data-source={encounter._source ?? "chartnav"}
          >
            {encounterSourceLabel(encounter)}
          </span>
        </div>
      </div>

      {!nativeEncounter && (
        <ExternalEncounterBanner
          identity={identity}
          encounter={encounter}
          canBridge={role === "admin" || role === "clinician"}
        />
      )}

      {nativeEncounter && (encounter as any).external_ref && (
        <BridgedEncounterRefreshBanner
          identity={identity}
          encounter={encounter}
          canRefresh={role === "admin" || role === "clinician"}
          onRefreshed={onRefreshDetail}
        />
      )}

      <dl className="detail__facts">
        <div><dt>Organization</dt><dd>#{encounter.organization_id}</dd></div>
        <div><dt>Location</dt><dd>#{encounter.location_id}</dd></div>
        <div><dt>Scheduled</dt><dd>{fmt(encounter.scheduled_at)}</dd></div>
        <div><dt>Started</dt><dd>{fmt(encounter.started_at)}</dd></div>
        <div><dt>Completed</dt><dd>{fmt(encounter.completed_at)}</dd></div>
        <div><dt>Created</dt><dd>{fmt(encounter.created_at)}</dd></div>
      </dl>

      <section className="section">
        <h3>Allowed transitions ({role ?? "—"})</h3>
        {nextStatuses.length ? (
          <div className="actions" data-testid="transitions">
            {nextStatuses.map((s) => (
              <button
                key={s}
                className="btn btn--primary"
                data-testid={`transition-${s}`}
                disabled={pendingStatus !== null}
                onClick={async () => {
                  setPendingStatus(s);
                  try {
                    await onTransition(s);
                  } finally {
                    setPendingStatus(null);
                  }
                }}
              >
                {pendingStatus === s ? "…" : `Move to ${s.replace(/_/g, " ")}`}
              </button>
            ))}
          </div>
        ) : (
          <div className="subtle-note">
            No transitions available from <code>{encounter.status}</code> for role{" "}
            <code>{role}</code>. (The backend is the source of truth — it will
            reject anything it disallows.)
          </div>
        )}
      </section>

      {me && nativeEncounter && typeof encounter.id === "number" && me.role !== "front_desk" && (
        <section className="section">
          <NoteWorkspace
            identity={identity}
            me={me}
            encounterId={encounter.id}
            patientDisplay={
              encounter.patient_name ?? encounter.patient_identifier
            }
            providerDisplay={encounter.provider_name}
          />
        </section>
      )}
      {me?.role === "front_desk" && (
        <section className="section" data-testid="note-workspace-frontdesk-blocked">
          <div className="subtle-note">
            Front desk doesn't read clinical content. Use the actions
            above to check in, reschedule, or print the encounter slip.
          </div>
        </section>
      )}
      {me && me.role !== "front_desk" && !nativeEncounter && (
        <section className="section" data-testid="note-workspace-external-note">
          <div className="subtle-note">
            Note drafting on an externally-sourced encounter requires
            bridging it into ChartNav first. Use the{" "}
            <strong>Bridge to ChartNav</strong> action above — once
            bridged, the full transcript → findings → draft → signoff
            workflow is available here while the encounter shell
            continues to live in the external EHR.
          </div>
        </section>
      )}

      <section className="section">
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <h3 style={{ margin: 0 }}>Timeline ({events.length})</h3>
          {onPrintSlip && (
            <button
              type="button"
              className="btn btn--muted"
              onClick={() => onPrintSlip(encounter)}
              data-testid="print-slip-button"
              title="Print encounter slip"
            >
              Print slip
            </button>
          )}
        </div>
        <Timeline events={events} />
      </section>

      <section className="section">
        <h3>Add event</h3>
        {eventAllowed ? (
          <EventComposer
            pending={pendingEvent}
            onSubmit={async (type, data) => {
              setPendingEvent(true);
              try {
                await onAddEvent(type, data);
              } finally {
                setPendingEvent(false);
              }
            }}
          />
        ) : (
          <div className="subtle-note" data-testid="event-denied">
            Your role (<code>{role}</code>) cannot add workflow events. Switch
            to an admin or clinician identity to write.
          </div>
        )}
      </section>
    </div>
  );
}

function EventComposer({
  pending,
  onSubmit,
}: {
  pending: boolean;
  onSubmit: (type: string, data: string) => void | Promise<void>;
}) {
  const [type, setType] = useState("");
  const [data, setData] = useState("");
  const disabled = !type.trim() || pending;
  return (
    <form
      className="event-form"
      data-testid="event-form"
      onSubmit={async (e) => {
        e.preventDefault();
        if (disabled) return;
        await onSubmit(type.trim(), data);
        setType("");
        setData("");
      }}
    >
      <select
        aria-label="Event type"
        data-testid="event-type"
        value={type}
        onChange={(e) => setType(e.target.value)}
        required
      >
        <option value="" disabled>Select event type…</option>
        {EVENT_TYPES.map((t) => (
          <option key={t} value={t}>{t}</option>
        ))}
      </select>
      <textarea
        data-testid="event-data"
        placeholder='event_data (optional JSON, e.g. {"comment":"..."})'
        value={data}
        onChange={(e) => setData(e.target.value)}
      />
      <div className="row">
        <button
          type="submit"
          className="btn btn--primary"
          disabled={disabled}
          data-testid="event-submit"
        >
          {pending ? "Appending…" : "Append event"}
        </button>
        <span className="subtle-note">
          JSON is parsed if valid; otherwise sent as a string.
        </span>
      </div>
    </form>
  );
}

function CreateEncounterModal({
  identity,
  me,
  onCancel,
  onSubmit,
}: {
  identity: string;
  me: Me;
  onCancel: () => void;
  onSubmit: (input: NewEncounterInput) => Promise<void>;
}) {
  const [patientId, setPatientId] = useState("");
  const [patientName, setPatientName] = useState("");
  const [provider, setProvider] = useState("");
  const [locationId, setLocationId] = useState<number | "">("");
  const [status, setStatus] =
    useState<"scheduled" | "in_progress">("scheduled");

  const [locations, setLocations] = useState<
    { id: number; organization_id: number; name: string }[]
  >([]);
  const [locLoading, setLocLoading] = useState(true);
  const [locError, setLocError] = useState<string | null>(null);

  // Patient typeahead (B3) — enriches the free-text flow without
  // removing it. Front desk picks an existing row; clinician can
  // still type a net-new identifier.
  const [patientQuery, setPatientQuery] = useState("");
  const [patientSuggestions, setPatientSuggestions] = useState<Patient[]>([]);
  const [patientSearchPending, setPatientSearchPending] = useState(false);
  useEffect(() => {
    const q = patientQuery.trim();
    if (q.length < 2) {
      setPatientSuggestions([]);
      return;
    }
    setPatientSearchPending(true);
    let cancelled = false;
    const h = setTimeout(async () => {
      try {
        const rows = await listPatients(identity, { q, limit: 8 });
        if (!cancelled) setPatientSuggestions(rows);
      } catch {
        if (!cancelled) setPatientSuggestions([]);
      } finally {
        if (!cancelled) setPatientSearchPending(false);
      }
    }, 200);
    return () => { cancelled = true; clearTimeout(h); };
  }, [patientQuery, identity]);

  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      setLocLoading(true);
      setLocError(null);
      try {
        const rows = await listLocations(identity);
        setLocations(rows);
        if (rows.length === 1) setLocationId(rows[0].id);
      } catch (e) {
        setLocError(friendly(e));
      } finally {
        setLocLoading(false);
      }
    })();
  }, [identity]);

  const canSubmit =
    !pending &&
    patientId.trim() !== "" &&
    provider.trim() !== "" &&
    typeof locationId === "number";

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    setPending(true);
    setError(null);
    try {
      await onSubmit({
        organization_id: me.organization_id,
        location_id: locationId as number,
        patient_identifier: patientId.trim(),
        patient_name: patientName.trim() || null,
        provider_name: provider.trim(),
        status,
      });
      // parent closes the modal on success
    } catch (err) {
      setError(friendly(err));
    } finally {
      setPending(false);
    }
  };

  return (
    <div
      className="modal-backdrop"
      role="dialog"
      aria-modal="true"
      aria-labelledby="create-title"
      data-testid="create-modal"
      onClick={(e) => {
        if (e.target === e.currentTarget && !pending) onCancel();
      }}
    >
      <div className="modal">
        <div className="modal__head">
          <h2 id="create-title">New encounter</h2>
          <button
            className="btn btn--muted"
            onClick={onCancel}
            disabled={pending}
            aria-label="Close"
          >
            ✕
          </button>
        </div>
        <form className="modal__body event-form" onSubmit={submit}>
          <label>
            Find patient
            <input
              type="text"
              data-testid="create-patient-search"
              value={patientQuery}
              onChange={(e) => setPatientQuery(e.target.value)}
              placeholder="Name or MRN — type to search the patients table"
              aria-describedby="create-patient-search-help"
            />
          </label>
          {patientQuery.trim().length >= 2 && (
            <div
              data-testid="create-patient-suggestions"
              style={{
                maxHeight: 200,
                overflowY: "auto",
                border: "1px solid var(--cn-line)",
                borderRadius: "var(--cn-radius-md)",
                background: "var(--cn-surface-alt)",
              }}
            >
              {patientSearchPending && (
                <div className="subtle-note" style={{ padding: "8px 10px" }}>
                  searching…
                </div>
              )}
              {!patientSearchPending && patientSuggestions.length === 0 && (
                <div className="subtle-note" style={{ padding: "8px 10px" }}>
                  No match. Enter a new identifier below to create a walk-in.
                </div>
              )}
              {patientSuggestions.map((p) => {
                const name = [p.first_name, p.last_name].filter(Boolean).join(" ") || `#${p.id}`;
                return (
                  <button
                    key={p.id}
                    type="button"
                    className="dayview__card"
                    style={{ width: "100%", textAlign: "left", border: 0 }}
                    data-testid={`create-patient-suggestion-${p.id}`}
                    onClick={() => {
                      setPatientId(p.patient_identifier || p.external_ref || `PT-${p.id}`);
                      setPatientName(name);
                      setPatientQuery("");
                      setPatientSuggestions([]);
                    }}
                  >
                    <span className="dayview__card__main">
                      <span className="dayview__card__name">{name}</span>
                      <span className="dayview__card__meta">
                        {[p.patient_identifier, p.external_ref, p.date_of_birth]
                          .filter(Boolean)
                          .join(" · ")}
                      </span>
                    </span>
                  </button>
                );
              })}
            </div>
          )}
          <span id="create-patient-search-help" className="subtle-note">
            Selecting a patient pre-fills the identifier + name below.
            A net-new identifier still works for walk-ins.
          </span>
          <label>
            Patient ID *
            <input
              data-testid="create-patient-id"
              value={patientId}
              onChange={(e) => setPatientId(e.target.value)}
              required
              placeholder="PT-1234"
            />
          </label>
          <label>
            Patient name
            <input
              data-testid="create-patient-name"
              value={patientName}
              onChange={(e) => setPatientName(e.target.value)}
              placeholder="Jane Doe"
            />
          </label>
          <label>
            Provider *
            <input
              data-testid="create-provider"
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
              required
              placeholder="Dr. Carter"
            />
          </label>
          <label>
            Location *
            {locLoading ? (
              <span className="subtle-note">loading locations…</span>
            ) : locError ? (
              <span style={{ color: "var(--danger)" }}>{locError}</span>
            ) : (
              <select
                data-testid="create-location"
                value={locationId === "" ? "" : String(locationId)}
                onChange={(e) =>
                  setLocationId(e.target.value ? parseInt(e.target.value, 10) : "")
                }
                required
              >
                <option value="">Select a location</option>
                {locations.map((l) => (
                  <option key={l.id} value={l.id}>
                    #{l.id} · {l.name}
                  </option>
                ))}
              </select>
            )}
          </label>
          <label>
            Initial status
            <select
              data-testid="create-status"
              value={status}
              onChange={(e) =>
                setStatus(e.target.value as "scheduled" | "in_progress")
              }
            >
              <option value="scheduled">scheduled</option>
              <option value="in_progress">in_progress</option>
            </select>
          </label>
          {error && (
            <div className="banner banner--error" role="alert" data-testid="create-error">
              {error}
            </div>
          )}
          <div className="row" style={{ justifyContent: "flex-end" }}>
            <button
              type="button"
              className="btn btn--muted"
              onClick={onCancel}
              disabled={pending}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn--primary"
              data-testid="create-submit"
              disabled={!canSubmit}
            >
              {pending ? "Creating…" : "Create encounter"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ---------- pure helpers --------------------------------------------------

function fmt(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso.replace(" ", "T"));
  if (isNaN(d.getTime())) return iso;
  return d.toLocaleString();
}

/** Short relative-time helper for triage cards. */
function relativeAge(iso: string | null | undefined, now: number): string {
  if (!iso) return "";
  const d = new Date(iso.replace(" ", "T"));
  if (isNaN(d.getTime())) return "";
  const diff = now - d.getTime();
  const abs = Math.abs(diff);
  const m = 60 * 1000;
  const h = 60 * m;
  const day = 24 * h;
  const tag = diff >= 0 ? "ago" : "from now";
  if (abs < 60 * 1000) return `just now`;
  if (abs < h) return `${Math.round(abs / m)}m ${tag}`;
  if (abs < day) return `${Math.round(abs / h)}h ${tag}`;
  return `${Math.round(abs / day)}d ${tag}`;
}

function renderEventData(ev: WorkflowEvent): string {
  const d = ev.event_data;
  if (d == null) return "—";
  if (typeof d === "string") return d;
  if (typeof d === "object") {
    return Object.entries(d as Record<string, unknown>)
      .map(([k, v]) => `${k}: ${typeof v === "object" ? JSON.stringify(v) : String(v)}`)
      .join("  ·  ");
  }
  return String(d);
}

function friendly(e: unknown): string {
  if (e instanceof ApiError) return `${e.status} ${e.errorCode} — ${e.reason}`;
  if (e instanceof Error) return e.message;
  return String(e);
}

// ---------------------------------------------------------------------
// External encounter banner + bridge action (phase 21)
// ---------------------------------------------------------------------

function ExternalEncounterBanner({
  identity,
  encounter,
  canBridge,
}: {
  identity: string;
  encounter: Encounter;
  canBridge: boolean;
}) {
  const [pending, setPending] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const externalRef =
    (encounter as any)._external_ref ?? String(encounter.id);
  const externalSource = (encounter as any)._source ?? "fhir";

  const onBridge = async () => {
    setPending(true);
    setErr(null);
    try {
      const bridged = await bridgeEncounter(identity, {
        external_ref: String(externalRef),
        external_source: String(externalSource),
        patient_identifier: encounter.patient_identifier,
        patient_name: encounter.patient_name,
        provider_name: encounter.provider_name,
        status: encounter.status,
      });
      // Rewire URL hash so the detail pane reloads against the
      // native id; the App-level selectedId picker reads on mount
      // via the row click, but we explicitly navigate by reload
      // so the workspace mounts with the native id.
      const url = new URL(window.location.href);
      url.searchParams.set("encounter", String(bridged.id));
      window.location.assign(url.toString());
    } catch (e) {
      if (e instanceof ApiError) setErr(`${e.status} ${e.errorCode} — ${e.reason}`);
      else if (e instanceof Error) setErr(e.message);
      else setErr(String(e));
    } finally {
      setPending(false);
    }
  };

  return (
    <div
      className="banner banner--info"
      data-testid="external-encounter-banner"
      role="note"
      data-source={String(externalSource)}
      data-external-ref={String(externalRef)}
      data-disabled-reason="encounter_owned_by_external_ehr"
    >
      <div>
        <strong>This encounter lives in the external EHR.</strong> Status
        transitions and encounter-level edits remain disabled in this mode.
        Bridge it into ChartNav to unlock the full transcript → findings →
        note → signoff workflow while the external EHR keeps owning the
        encounter shell.
      </div>
      {canBridge && (
        <div className="actions" style={{ marginTop: 10 }}>
          <button
            className="btn btn--primary"
            onClick={onBridge}
            disabled={pending}
            data-testid="bridge-encounter"
          >
            {pending ? "Bridging…" : "Bridge to ChartNav"}
          </button>
          {err && (
            <span className="subtle-note" data-testid="bridge-error">
              {err}
            </span>
          )}
        </div>
      )}
      {!canBridge && (
        <p className="subtle-note" data-testid="bridge-disabled-note">
          Reviewer role cannot bridge encounters. Ask an admin or clinician.
        </p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------
// Bridged-encounter refresh banner (phase 23)
// ---------------------------------------------------------------------

function BridgedEncounterRefreshBanner({
  identity,
  encounter,
  canRefresh,
  onRefreshed,
}: {
  identity: string;
  encounter: Encounter;
  canRefresh: boolean;
  onRefreshed: () => void;
}) {
  const [pending, setPending] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const externalRef = (encounter as any).external_ref;
  const externalSource = (encounter as any).external_source;

  if (!externalRef) return null;

  const onRefresh = async () => {
    if (typeof encounter.id !== "number") return;
    setPending(true);
    setMsg(null);
    setErr(null);
    try {
      const res = await refreshBridgedEncounter(identity, encounter.id);
      if (res.refreshed) {
        const fields = Object.keys(res.mirrored).join(", ");
        setMsg(`Refreshed ${fields} from the external system.`);
      } else {
        setMsg("External shell unchanged — nothing to mirror.");
      }
      onRefreshed();
    } catch (e) {
      if (e instanceof ApiError) setErr(`${e.status} ${e.errorCode} — ${e.reason}`);
      else if (e instanceof Error) setErr(e.message);
      else setErr(String(e));
    } finally {
      setPending(false);
    }
  };

  return (
    <div
      className="banner banner--info"
      role="note"
      data-testid="bridged-refresh-banner"
    >
      <div>
        <strong>Bridged from external ({externalSource}):</strong>{" "}
        <code data-testid="bridged-external-ref">{externalRef}</code>. ChartNav
        owns the workflow; the external EHR owns the encounter shell. Refresh
        to re-fetch patient / provider / status from the source.
      </div>
      <div className="actions" style={{ marginTop: 8 }}>
        {canRefresh && (
          <button
            type="button"
            className="btn"
            onClick={onRefresh}
            disabled={pending}
            data-testid="bridged-refresh"
          >
            {pending ? "Refreshing…" : "Refresh from external"}
          </button>
        )}
        {!canRefresh && (
          <span
            className="subtle-note"
            data-testid="bridged-refresh-disabled-note"
          >
            Reviewer role cannot refresh. Ask an admin or clinician.
          </span>
        )}
        {msg && (
          <span className="subtle-note" data-testid="bridged-refresh-ok">
            {msg}
          </span>
        )}
        {err && (
          <span className="subtle-note" data-testid="bridged-refresh-error">
            {err}
          </span>
        )}
      </div>
    </div>
  );
}
