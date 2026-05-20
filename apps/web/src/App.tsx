import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import {
  API_URL,
  ALLOWED_STATUSES,
  ApiError,
  Encounter,
  EncounterFilters,
  EVENT_TYPES,
  Me,
  NewEncounterInput,
  Role,
  WorkflowEvent,
  allowedNextStatuses,
  canCreateEncounter,
  canCreateEvent,
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
  updateEncounterStatus,
} from "./api";
import { AdminPanel } from "./AdminPanel";
import { NoteWorkspace } from "./NoteWorkspace";
import { SEEDED_IDENTITIES, loadIdentity, saveIdentity } from "./identity";
import { isDemoModeEnabled } from "./GuidedDemoMode";
import { shapeEventData } from "./utils/shapeEventData";
import { ClinicalTabbedWorkspace } from "./ClinicalTabbedWorkspace";
import { MultiClinicDashboard } from "./MultiClinicDashboard";
import { RoleDashboard } from "./RoleDashboard";
import { SecurityReadinessPanel } from "./SecurityReadinessPanel";
import { ProductionReadinessPanel } from "./ProductionReadinessPanel";
import {
  buildLanguageHref,
  getAppCopy,
  getCurrentLanguage,
  persistLanguage,
  SUPPORTED_LANGUAGES,
  type AppCopy,
  type Language,
} from "./i18n";

// Phase 20C — single-page top-level view switch. The encounters
// workspace stays the default; the Dashboard CORE entry switches the
// detail pane to the read-only role-based dashboard.
type TopView =
  | "encounters"
  | "dashboard"
  | "multi-clinic"
  | "security-readiness"
  | "production-readiness";

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
  const [topView, setTopView] = useState<TopView>("encounters");

  // Phase A — language is resolved from URL ?lang / path prefix /
  // localStorage / default ("en"). Same resolver the landing page
  // uses, so a user who toggles to Spanish there sees Spanish in
  // the authenticated workspace too. Re-resolves on `popstate`.
  const [language, setLanguage] = useState<Language>(() => getCurrentLanguage());
  useEffect(() => {
    const handler = () => setLanguage(getCurrentLanguage());
    window.addEventListener("popstate", handler);
    return () => window.removeEventListener("popstate", handler);
  }, []);
  const copy = getAppCopy(language);
  // Phase A — keep <html lang> in sync so screen readers + crawlers
  // see the right language attribute on the authenticated app, not
  // just the landing page.
  useEffect(() => {
    if (typeof document === "undefined") return;
    const prev = document.documentElement.lang;
    document.documentElement.lang = language;
    return () => {
      document.documentElement.lang = prev;
    };
  }, [language]);
  const handleLanguageChange = useCallback(
    (next: Language) => {
      setLanguage(next);
      persistLanguage(next);
      if (typeof window !== "undefined") {
        const href = buildLanguageHref(next, {
          pathname: window.location.pathname,
          search: window.location.search,
        });
        try {
          window.history.replaceState({}, "", href);
        } catch {
          // best effort
        }
      }
    },
    [],
  );

  // Pagination
  const PAGE_SIZE = 25;
  const [offset, setOffset] = useState(0);
  const [total, setTotal] = useState(0);

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
    setBanner({
      kind: "info",
      msg: copy.bannerIdentitySwitchedPrefix + email,
    });
  };

  const onTransition = async (status: string) => {
    if (!encounter) return;
    setBanner(null);
    try {
      const updated = await updateEncounterStatus(identity, encounter.id, status);
      setEncounter(updated);
      setEvents(await getEncounterEvents(identity, encounter.id));
      await refreshList();
      setBanner({ kind: "ok", msg: copy.bannerStatusPrefix + status });
    } catch (e) {
      setBanner({ kind: "error", msg: friendly(e) });
    }
  };

  const onAddEvent = async (type: string, raw: string) => {
    if (!encounter) return;
    setBanner(null);
    // Phase 63C — see apps/web/src/utils/shapeEventData.ts. Backend
    // requires manual_note.event_data to be a JSON object; the
    // helper wraps free-text as { note: "..." } and refuses empty
    // input client-side.
    const shaped = shapeEventData(type, raw);
    if ("error" in shaped) {
      if (shaped.error === "empty") {
        setBanner({ kind: "error", msg: "Manual note text cannot be empty." });
      }
      return;
    }
    const data = shaped.ok;
    try {
      await createEncounterEvent(identity, encounter.id, {
        event_type: type,
        event_data: data,
      });
      setEvents(await getEncounterEvents(identity, encounter.id));
      setBanner({
        kind: "ok",
        msg:
          copy.bannerEventAddedPrefix + type + copy.bannerEventAddedSuffix,
      });
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
      msg: copy.bannerEncounterCreatedTemplate
        .replace("{id}", String(created.id))
        .replace("{pid}", created.patient_identifier),
    });
  };

  // ---- render ----------------------------------------------------------

  const canCreate = me ? canCreateEncounter(me.role) : false;
  const canAdmin = me ? isAdmin(me.role) : false;

  return (
    <>
      <header className="app-header">
        <div className="brand">
          <img
            className="brand__logo"
            src="/brand/chartnav-logo.svg"
            alt={copy.brandLogoAlt}
            width="140"
            height="32"
          />
          <span className="sub">{copy.brandSub}</span>
        </div>
        <div className="header-meta">
          <IdentityBadge
            me={me}
            meError={meError}
            meLoading={meLoading}
            copy={copy}
          />
          {/*
            Phase 19 — hide the dev API URL chip in demo mode so a
            buyer / advisor / partner watching a live demo never
            sees `localhost:8000` on screen. The chip stays visible
            in the developer's normal workflow.
          */}
          {!isDemoModeEnabled() && (
            <span className="chip" data-testid="api-chip">
              {copy.apiChipPrefix}{API_URL}
            </span>
          )}
          {canCreate && (
            <button
              className="btn btn--primary"
              onClick={() => setShowCreate(true)}
              data-testid="open-create-encounter"
            >
              {copy.newEncounterButton}
            </button>
          )}
          {canAdmin && (
            <button
              className="btn"
              onClick={() => setShowAdmin(true)}
              data-testid="open-admin-panel"
            >
              {copy.adminButton}
            </button>
          )}
          <IdentityPicker
            value={identity}
            onChange={onIdentityChange}
            copy={copy}
          />
          <AppLanguageSwitcher
            language={language}
            copy={copy}
            onSelect={handleLanguageChange}
          />
        </div>
      </header>

      <div className="layout">
        <aside className="layout__list" data-testid="clinical-sidebar">
          <ClinicalSidebarNav
            canCreate={canCreate}
            onNewEncounter={() => setShowCreate(true)}
            topView={topView}
            onShowDashboard={() => setTopView("dashboard")}
            onShowEncounters={() => setTopView("encounters")}
            onShowMultiClinic={() => setTopView("multi-clinic")}
            canViewMultiClinic={canAdmin}
            onShowSecurityReadiness={() => setTopView("security-readiness")}
            canViewSecurityReadiness={canAdmin}
            onShowProductionReadiness={() =>
              setTopView("production-readiness")
            }
            canViewProductionReadiness={canAdmin}
            copy={copy}
          />
          <FilterBar
            value={filters}
            onChange={(next) => {
              setFilters(next);
              setOffset(0);
            }}
            copy={copy}
          />
          <EncounterList
            rows={encounters}
            loading={listLoading}
            error={listError}
            selectedId={selectedId}
            onSelect={setSelectedId}
            copy={copy}
          />
          {total > PAGE_SIZE && (
            <div className="pagination" data-testid="pagination">
              <button
                className="btn"
                disabled={offset === 0}
                onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                data-testid="page-prev"
              >
                {copy.pagePrev}
              </button>
              <span className="subtle-note" data-testid="page-status">
                {offset + 1}-{Math.min(offset + PAGE_SIZE, total)} {copy.pageOfWord} {total}
              </span>
              <button
                className="btn"
                disabled={offset + PAGE_SIZE >= total}
                onClick={() => setOffset(offset + PAGE_SIZE)}
                data-testid="page-next"
              >
                {copy.pageNext}
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
          {topView === "dashboard" && me ? (
            <RoleDashboard identity={identity} me={me} />
          ) : topView === "multi-clinic" && me ? (
            <MultiClinicDashboard identity={identity} me={me} />
          ) : topView === "production-readiness" && me ? (
            <ProductionReadinessPanel identity={identity} me={me} />
          ) : topView === "security-readiness" && me ? (
            <SecurityReadinessPanel identity={identity} me={me} />
          ) : selectedId == null ? (
            <div className="empty">
              {copy.detailEmpty}
              {canCreate && (
                <>
                  {" "}
                  <span data-testid="detail-empty-create-hint">
                    <strong>{copy.detailEmptyCreateLink}</strong>
                    {copy.detailEmptyCreateSuffix}
                  </span>
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
          copy={copy}
        />
      )}
      {showAdmin && me && isAdmin(me.role) && (
        <AdminPanel
          identity={identity}
          me={me}
          onClose={() => setShowAdmin(false)}
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
          <span>{copy.footerBrandTagline}</span>
        </span>
        <span
          className="app-footer__powered"
          data-testid="app-footer-arcg"
        >
          {copy.footerPoweredByPrefix} <strong>{copy.footerPoweredEntity}</strong>
        </span>
      </footer>
    </>
  );
}

// ---------- subcomponents -------------------------------------------------

/**
 * Phase 19B — clinical-sidebar grouped navigation.
 *
 * Renders the CORE / CLINICAL / OPERATIONS / ADMIN structure
 * shown in the reference design. Only the **Encounters** entry
 * drives behavior today (it scrolls the existing encounter list
 * below into view); the other entries render as visually-correct
 * placeholders with `disabled` + a `title` hint so they read as
 * future-phase scaffolding rather than vaporware.
 *
 * Quick Actions reuses the same pattern: only **New Encounter**
 * is wired today (it opens the existing CreateEncounterModal);
 * the other quick actions render as disabled placeholders.
 *
 * The grouped nav is intentionally non-routing — App.tsx is a
 * single-page app right now. Wiring real routes is a separate
 * phase.
 */
function ClinicalSidebarNav({
  canCreate,
  onNewEncounter,
  topView,
  onShowDashboard,
  onShowEncounters,
  onShowMultiClinic,
  canViewMultiClinic,
  onShowSecurityReadiness,
  canViewSecurityReadiness,
  onShowProductionReadiness,
  canViewProductionReadiness,
  copy,
}: {
  canCreate: boolean;
  onNewEncounter: () => void;
  topView: TopView;
  onShowDashboard: () => void;
  onShowEncounters: () => void;
  onShowMultiClinic: () => void;
  canViewMultiClinic: boolean;
  onShowSecurityReadiness: () => void;
  canViewSecurityReadiness: boolean;
  onShowProductionReadiness: () => void;
  canViewProductionReadiness: boolean;
  copy: AppCopy;
}) {
  return (
    <nav className="sidebar-nav" data-testid="sidebar-nav" aria-label={copy.sidebarNavAriaLabel}>
      <SidebarGroup label={copy.sidebarGroupCore} testid="sidebar-group-core">
        {/* Phase 20C — Dashboard now opens the role-based summary
            view on the right. Existing Encounters behavior is
            unchanged when the user switches back. */}
        <SidebarItem
          testid="sidebar-item-dashboard"
          active={topView === "dashboard"}
          onClick={onShowDashboard}
        >
          {copy.sidebarItemDashboard}
        </SidebarItem>
        <SidebarItem testid="sidebar-item-calendar" disabled>
          {copy.sidebarItemCalendar}
        </SidebarItem>
        <SidebarItem
          testid="sidebar-item-encounters"
          active={topView === "encounters"}
          onClick={onShowEncounters}
        >
          {copy.sidebarItemEncounters}
        </SidebarItem>
      </SidebarGroup>
      <SidebarGroup label={copy.sidebarGroupClinical} testid="sidebar-group-clinical">
        <SidebarItem testid="sidebar-item-patients" disabled>
          {copy.sidebarItemPatients}
        </SidebarItem>
        <SidebarItem testid="sidebar-item-lab-orders" disabled>
          {copy.sidebarItemLabOrders}
        </SidebarItem>
      </SidebarGroup>
      <SidebarGroup label={copy.sidebarGroupOperations} testid="sidebar-group-operations">
        {/* Phase 22 — Multi-Clinic admin rollup. Admin-only;
            non-admin identities see a disabled placeholder. */}
        <SidebarItem
          testid="sidebar-item-multi-clinic"
          active={topView === "multi-clinic"}
          onClick={canViewMultiClinic ? onShowMultiClinic : undefined}
          disabled={!canViewMultiClinic}
        >
          {copy.sidebarItemMultiClinic}
        </SidebarItem>
        <SidebarItem testid="sidebar-item-tasks" disabled>
          {copy.sidebarItemTasks}
        </SidebarItem>
        <SidebarItem testid="sidebar-item-messages" disabled>
          {copy.sidebarItemMessages}
        </SidebarItem>
        <SidebarItem testid="sidebar-item-chat" disabled>
          {copy.sidebarItemChat}
        </SidebarItem>
      </SidebarGroup>
      {/* Phase 19F — Admin no longer surfaces Billing. ChartNav
          does not bill, code, submit claims, or handle insurance.
          Documents replaces Billing as the third Admin item. */}
      <SidebarGroup label={copy.sidebarGroupAdmin} testid="sidebar-group-admin">
        {/* Phase 23 — Security Readiness checklist. Admin-only;
            non-admin identities see a disabled placeholder. */}
        <SidebarItem
          testid="sidebar-item-security-readiness"
          active={topView === "security-readiness"}
          onClick={
            canViewSecurityReadiness ? onShowSecurityReadiness : undefined
          }
          disabled={!canViewSecurityReadiness}
        >
          {copy.sidebarItemSecurityReadiness}
        </SidebarItem>
        {/* Clinic-OS next-phase — production readiness combines
            proof KPIs (live + pending markers) with per-location
            rollout readiness. Admin-only. */}
        <SidebarItem
          testid="sidebar-item-production-readiness"
          active={topView === "production-readiness"}
          onClick={
            canViewProductionReadiness
              ? onShowProductionReadiness
              : undefined
          }
          disabled={!canViewProductionReadiness}
        >
          {copy.sidebarItemProductionReadiness}
        </SidebarItem>
        <SidebarItem testid="sidebar-item-documents" disabled>
          {copy.sidebarItemDocuments}
        </SidebarItem>
        <SidebarItem testid="sidebar-item-reports" disabled>
          {copy.sidebarItemReports}
        </SidebarItem>
        <SidebarItem testid="sidebar-item-settings" disabled>
          {copy.sidebarItemSettings}
        </SidebarItem>
      </SidebarGroup>
      {/* Phase 19F — Quick Actions: dropped Send Message (no
          patient messaging) and New Patient (not in Phase 19F
          spec). Internal Chat Note replaces them as a fast-path
          to the internal-staff Chat tab. */}
      <SidebarGroup label={copy.sidebarGroupQuickActions} testid="sidebar-group-quick-actions">
        <SidebarItem
          testid="sidebar-item-new-encounter"
          onClick={canCreate ? onNewEncounter : undefined}
          disabled={!canCreate}
        >
          {copy.sidebarItemNewEncounter}
        </SidebarItem>
        <SidebarItem testid="sidebar-item-record-dictation" disabled>
          {copy.sidebarItemRecordDictation}
        </SidebarItem>
        <SidebarItem testid="sidebar-item-upload-imaging" disabled>
          {copy.sidebarItemUploadImaging}
        </SidebarItem>
        <SidebarItem testid="sidebar-item-internal-chat-note" disabled>
          {copy.sidebarItemInternalChatNote}
        </SidebarItem>
      </SidebarGroup>
    </nav>
  );
}

function SidebarGroup({
  label,
  testid,
  children,
}: {
  label: string;
  testid: string;
  children: ReactNode;
}) {
  return (
    <div className="sidebar-nav__group" data-testid={testid}>
      <div className="sidebar-nav__group-label">{label}</div>
      <ul className="sidebar-nav__list">{children}</ul>
    </div>
  );
}

function SidebarItem({
  testid,
  active,
  disabled,
  onClick,
  children,
}: {
  testid: string;
  active?: boolean;
  disabled?: boolean;
  onClick?: () => void;
  children: ReactNode;
}) {
  return (
    <li>
      <button
        type="button"
        className={
          "sidebar-nav__item" +
          (active ? " sidebar-nav__item--active" : "") +
          (disabled ? " sidebar-nav__item--disabled" : "")
        }
        data-testid={testid}
        disabled={disabled}
        title={disabled ? "Available in a future phase" : undefined}
        onClick={onClick}
      >
        {children}
      </button>
    </li>
  );
}

function IdentityBadge({
  me,
  meError,
  meLoading,
  copy,
}: {
  me: Me | null;
  meError: string | null;
  meLoading: boolean;
  copy: AppCopy;
}) {
  if (meLoading && !me)
    return (
      <span className="chip" data-testid="identity-loading">
        {copy.identityResolving}
      </span>
    );
  if (meError)
    return (
      <span
        className="chip"
        style={{ color: "var(--danger)" }}
        data-testid="identity-error"
      >
        {copy.identityAuthPrefix}{meError}
      </span>
    );
  if (!me) return <span className="chip">—</span>;
  // Phase 19 — buyer-safe identity chip. The chip carries a small
  // "Identity" eyebrow label so it reads as system info (not a debug
  // dump), and the role + org tokens use friendlier wording. The
  // raw email still travels in the chip's title attribute so an
  // operator can confirm provisioning at a glance, without the email
  // dominating the visible chip.
  const friendlyRole =
    me.role === "admin"
      ? copy.roleAdmin
      : me.role === "clinician"
      ? copy.roleClinician
      : me.role === "reviewer"
      ? copy.roleReviewer
      : me.role === "front_desk"
      ? copy.roleFrontDesk
      : me.role === "technician"
      ? copy.roleTechnician
      : me.role;
  return (
    <span
      className="chip chip--identity"
      data-testid="identity-badge"
      title={`${me.email} · ${me.role} · organization_id=${me.organization_id}`}
    >
      <span className="chip__label">{copy.identityBadgeLabel}</span>
      <span className="chip__value">
        {friendlyRole} · {copy.badgeOrgPrefix} {me.organization_id}
      </span>
    </span>
  );
}

function IdentityPicker({
  value,
  onChange,
  copy,
}: {
  value: string;
  onChange: (email: string) => void;
  copy: AppCopy;
}) {
  const isSeeded = SEEDED_IDENTITIES.some((s) => s.email === value);
  const [custom, setCustom] = useState(isSeeded ? "" : value);
  const [mode, setMode] = useState<"seeded" | "custom">(
    isSeeded ? "seeded" : "custom"
  );
  return (
    <div className="identity-picker">
      <label className="subtle-note" htmlFor="dev-identity">
        {copy.identityPickerLabel}
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
          <option value="__custom__">{copy.identityPickerCustomOption}</option>
        </select>
      ) : (
        <>
          <input
            type="email"
            value={custom}
            placeholder={copy.identityPickerEmailPlaceholder}
            onChange={(e) => setCustom(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && custom.trim()) onChange(custom.trim());
            }}
          />
          <button
            className="btn"
            onClick={() => custom.trim() && onChange(custom.trim())}
          >
            {copy.identityPickerUseButton}
          </button>
          <button className="btn btn--muted" onClick={() => setMode("seeded")}>
            {copy.identityPickerSeededButton}
          </button>
        </>
      )}
    </div>
  );
}

/** Phase A — language switcher rendered next to the identity
 *  picker in the authenticated top bar. Uses <button>s (not <a>s)
 *  so the Phase 16 link-href contract on the landing page also
 *  applies here: only the operator-set hrefs reach the link role. */
function AppLanguageSwitcher({
  language,
  copy,
  onSelect,
}: {
  language: Language;
  copy: AppCopy;
  onSelect: (next: Language) => void;
}) {
  return (
    <nav
      className="app-lang-switcher"
      aria-label={copy.appSwitcherAriaLabel}
      data-testid="app-lang-switcher"
    >
      {SUPPORTED_LANGUAGES.map((opt) => {
        const isActive = opt.code === language;
        const label =
          opt.code === "en"
            ? copy.appSwitcherEnglishLabel
            : copy.appSwitcherSpanishLabel;
        return (
          <button
            key={opt.code}
            type="button"
            className={
              "app-lang-switcher__option"
              + (isActive ? " app-lang-switcher__option--active" : "")
            }
            data-testid={`app-lang-option-${opt.code}`}
            aria-pressed={isActive}
            onClick={() => {
              if (!isActive) onSelect(opt.code);
            }}
          >
            {label}
          </button>
        );
      })}
    </nav>
  );
}

function FilterBar({
  value,
  onChange,
  copy,
}: {
  value: EncounterFilters;
  onChange: (next: EncounterFilters) => void;
  copy: AppCopy;
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
        {copy.filterStatusLabel}
        <select
          data-testid="filter-status"
          value={value.status ?? ""}
          onChange={(e) => update("status", e.target.value || undefined)}
        >
          <option value="">{copy.filterStatusAnyOption}</option>
          {ALLOWED_STATUSES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </label>
      <label>
        {copy.filterProviderLabel}
        <input
          type="text"
          data-testid="filter-provider"
          placeholder={copy.filterProviderPlaceholder}
          value={value.provider_name ?? ""}
          onChange={(e) => update("provider_name", e.target.value || undefined)}
        />
      </label>
      <label>
        {copy.filterLocationLabel}
        <input
          type="number"
          data-testid="filter-location"
          min={1}
          placeholder={copy.filterLocationPlaceholder}
          value={value.location_id ?? ""}
          onChange={(e) => {
            const n = e.target.value ? parseInt(e.target.value, 10) : undefined;
            update("location_id", Number.isNaN(n) ? undefined : n);
          }}
        />
      </label>
      {Object.keys(value).length > 0 && (
        <button className="filter-clear" onClick={() => onChange({})}>
          {copy.filterClearButton}
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
  copy,
}: {
  rows: Encounter[];
  loading: boolean;
  error: string | null;
  selectedId: number | string | null;
  onSelect: (id: number | string) => void;
  copy: AppCopy;
}) {
  if (loading && rows.length === 0)
    return (
      <div className="empty" data-testid="list-loading">
        {copy.encListLoading}
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
        {copy.encListEmpty}
      </div>
    );

  return (
    <div className="enc-list" data-testid="enc-list">
      {rows.map((e) => (
        <div
          key={e.id}
          className={"enc-row" + (selectedId === e.id ? " is-active" : "")}
          onClick={() => onSelect(e.id)}
          role="button"
          tabIndex={0}
          data-testid={`enc-row-${e.id}`}
          onKeyDown={(ev) => {
            if (ev.key === "Enter" || ev.key === " ") onSelect(e.id);
          }}
        >
          <div>
            <div className="enc-row__pid">
              #{e.id} · {e.patient_identifier}
            </div>
            <div className="enc-row__name">{e.patient_name ?? "—"}</div>
            <div className="enc-row__provider">{e.provider_name}</div>
          </div>
          <span className="status-pill" data-status={e.status}>
            {e.status.replace(/_/g, " ")}
          </span>
        </div>
      ))}
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
      {/*
       * Phase 19 — the encounter detail body is now rendered by
       * ClinicalTabbedWorkspace (9 tabs: Overview, Clinical,
       * Documentation, Imaging, Labs/Orders Review, Calendar,
       * Communications, Documents, Chat). The Documentation tab
       * embeds the existing NoteWorkspace; the Imaging tab embeds
       * the existing EyeDiagramPanel. Banners (external encounter,
       * bridged refresh, external-note fallback) still render
       * here so they stay above the tabbed body.
       */}
      {me && nativeEncounter && typeof encounter.id === "number" ? (
        <ClinicalTabbedWorkspace
          encounter={encounter}
          identity={identity}
          me={me}
          pendingStatus={pendingStatus}
          onTransition={async (s) => {
            setPendingStatus(s);
            try {
              await onTransition(s);
            } finally {
              setPendingStatus(null);
            }
          }}
          onSetPendingStatus={setPendingStatus}
          onRefreshDetail={onRefreshDetail}
          /* Phase 19F — Timeline + Add event composer used to render
             below the workspace. They now live inside the Overview
             tab's Timeline card. The composer is hidden when
             ?demo=1 is active so the buyer demo never exposes the
             dev composer (the read-only Timeline still renders). */
          events={events}
          eventAllowed={eventAllowed}
          pendingEvent={pendingEvent}
          onAddEvent={async (type, data) => {
            setPendingEvent(true);
            try {
              await onAddEvent(type, data);
            } finally {
              setPendingEvent(false);
            }
          }}
          isDemo={isDemoModeEnabled()}
          bannersSlot={
            <>
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
            </>
          }
        />
      ) : (
        <>
          {/*
           * Externally-sourced (non-native) encounters or pre-auth
           * states render the original head + banners + bridge
           * fallback message. Once the encounter is bridged into
           * ChartNav (i.e. becomes native), the tabbed workspace
           * above takes over.
           */}
          <div className="detail__head">
            <div>
              <h2>
                #{encounter.id} ·{" "}
                {encounter.patient_name ?? encounter.patient_identifier}
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

          {me && !nativeEncounter && (
            <section
              className="section"
              data-testid="note-workspace-external-note"
            >
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

          {/* Phase 19F — Timeline + Add event are now embedded in
              the Overview tab's Timeline card on the native path.
              For non-native (externally-sourced) encounters the
              tabbed workspace doesn't render, so the legacy
              floating sections stay here so admins can still
              audit + append events while the bridge is pending.
              They are inside the `else` branch so they never
              render alongside the tabbed workspace (which would
              be the buyer-demo "random Add event below tabs"
              regression). */}
          <section className="section">
            <h3>Timeline ({events.length})</h3>
            {events.map((ev) => (
              <div className="event-item" key={ev.id}>
                <div className="event-item__head">
                  <span className="event-item__type">{ev.event_type}</span>
                  <span className="event-item__when">
                    {fmt(ev.created_at)}
                  </span>
                </div>
                <div className="event-item__data">{renderEventData(ev)}</div>
              </div>
            ))}
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
                Your role (<code>{role}</code>) cannot add workflow events.
                Switch to an admin or clinician identity to write.
              </div>
            )}
          </section>
        </>
      )}
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
  copy,
}: {
  identity: string;
  me: Me;
  onCancel: () => void;
  onSubmit: (input: NewEncounterInput) => Promise<void>;
  copy: AppCopy;
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
          <h2 id="create-title">{copy.createModalTitle}</h2>
          <button
            className="btn btn--muted"
            onClick={onCancel}
            disabled={pending}
            aria-label={copy.createModalCloseAria}
          >
            ✕
          </button>
        </div>
        <form className="modal__body event-form" onSubmit={submit}>
          <label>
            {copy.createPatientIdLabel}
            <input
              data-testid="create-patient-id"
              value={patientId}
              onChange={(e) => setPatientId(e.target.value)}
              required
              placeholder={copy.createPatientIdPlaceholder}
            />
          </label>
          <label>
            {copy.createPatientNameLabel}
            <input
              data-testid="create-patient-name"
              value={patientName}
              onChange={(e) => setPatientName(e.target.value)}
              placeholder={copy.createPatientNamePlaceholder}
            />
          </label>
          <label>
            {copy.createProviderLabel}
            <input
              data-testid="create-provider"
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
              required
              placeholder={copy.createProviderPlaceholder}
            />
          </label>
          <label>
            {copy.createLocationLabel}
            {locLoading ? (
              <span className="subtle-note">{copy.createLocationLoading}</span>
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
                <option value="">{copy.createLocationPlaceholder}</option>
                {locations.map((l) => (
                  <option key={l.id} value={l.id}>
                    #{l.id} · {l.name}
                  </option>
                ))}
              </select>
            )}
          </label>
          <label>
            {copy.createStatusLabel}
            <select
              data-testid="create-status"
              value={status}
              onChange={(e) =>
                setStatus(e.target.value as "scheduled" | "in_progress")
              }
            >
              <option value="scheduled">{copy.createStatusScheduled}</option>
              <option value="in_progress">{copy.createStatusInProgress}</option>
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
              {copy.createCancelButton}
            </button>
            <button
              type="submit"
              className="btn btn--primary"
              data-testid="create-submit"
              disabled={!canSubmit}
            >
              {pending ? copy.createSubmitPending : copy.createSubmitButton}
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
